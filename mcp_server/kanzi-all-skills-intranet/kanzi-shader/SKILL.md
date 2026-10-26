---
name: kanzi-shader
description: Kanzi Studio Shader 操作 skill（给 nlp/Copilot 用）—— 通过 MCP 在 Kanzi Studio 里定位/修改/创建 MaterialType 的 shader、属性到 uniform 的绑定、Material/MaterialBrush 三层关联、验证与保存。触发场景：写/改 Kanzi 材质 shader、让材质属性驱动 shader、排查 shader 不生效。GLSL 怎么写由 Copilot 自行决定，本 skill 只给操作流程与关键点；完整语法表用 kanzidocmcp 查官方文档（见参考章节）。
---

# Kanzi Shader 操作（MCP，给 nlp 用）

> **用途**：nlp_worker（Copilot）通过 MCP 在 Kanzi Studio 里操作 shader 的完整步骤。
> **触发**：涉及 Kanzi shader / 材质着色器 / 改 MaterialType 的 shader / 建带 shader 的材质时。
> **依据**：2026-08-11 渐变材质实测打通 + 官方文档 kanzidocmcp 4.1.1（参考，按需查）。

---

## 0. 前置：接入 + 定位库

> ⚠️ **地址规则**：若环境已配置好相关 MCP（如 nlp_worker config.yaml 的 `mcp_servers` 或部署机已建网关），**必须使用已配置的 MCP 地址**；`<kz_mcp_http机IP>` 仅为通用占位符（未配置时的示例写法）。

```bash
# HTTP MCP 连接
POST http://<kz_mcp_http机IP>:9001/mcp（Header X-Kanzi-User: suijichao），JSON-RPC tools/call 调 kz_invoke

# 定位三个库
kz_invoke target=@project method=get_Children          # → Material Types 库 @objMT
kz_invoke target=@project method=get_MaterialLibrary   # → Materials 库 @objMatLib
kz_invoke target=@project method=get_BrushLibrary      # → Brushes 库 @objBrushLib
```

> ⚠️ `@objN` 引用每次重连都会重新编号，**必须先枚举定位**，勿硬编码。⚠️ **助手绝不重启 Studio**（会造成未保存内容丢失且断连）。

---

## 1. Shader 资源模型（一句话搞懂）

```
MaterialType（含 Vertex Shader + Fragment Shader 子项，可选 Geometry/Tessellation）
  ├─ MTPT（MaterialTypePropertyTypes）定义该材质可用属性（如 shader.colorStart）
  ├─ Uniform binding：把 MTPT 属性值写进 shader 的 uniform（DisplayCode={./shader.colorXXX}）
  └─ Material 引用 MaterialType（设默认属性值）
        └─ MaterialBrush 引用 Material（挂到节点用）
```

- shader 语言 = OpenGL ES GLSL（`.vert.glsl` 顶点 / `.frag.glsl` 片元）
- **MaterialType 定义材质能用哪些属性，属性通过 Uniform binding 驱动 shader uniform** —— 这是核心机制。
- 改 shader 文件（或 SetText）后 Studio 自动重编译：错误看 Log，Preview 红色 = shader 无效。

---

## 2. 定位 MaterialType 的 shader 子项

```bash
kz_invoke target=@project method=CreateProjectItem \
  args=["@type:Rightware.Kanzi.Studio.PluginInterface.MaterialType",
        "@string:<新名字>", "@objMT"]        # → @objMT2（新建时）
# 已有 MaterialType：@objMT2 = 上面 get_Children 匹配到的

kz_invoke target=@objMT2 method=get_Children   # → Vertex Shader=@objVS, Fragment Shader=@objFS
```

---

## 3. 修改 shader 内容（SetText / GetText）

```bash
# 读当前 shader（改前先读，避免覆盖已有内容）
kz_invoke target=@objVS method=GetText
kz_invoke target=@objFS method=GetText

# 写入新 GLSL（@string: 后面是完整 GLSL 源码，含 \n 转义）
kz_invoke target=@objVS method=SetText args=["@string:<GLSL源码>"]
kz_invoke target=@objFS method=SetText args=["@string:<GLSL源码>"]

# 验证（两个都读回）
kz_invoke target=@objVS method=GetText
kz_invoke target=@objFS method=GetText

# shader 正确 → Studio 自动重读并暴露 uniform：
kz_invoke target=@objMT2 method=Get args=["@string:Uniforms"]  # → 各 uniform 的 ShaderVariableInfo
```

### ⚠️ 操作级关键点（不遵守必失败，实测）

1. **顶点+片元两个 shader 都要 SetText**，缺一效果出不来。
2. **顶点 shader 必须传 vTexCoord**（`attribute kzTextureCoordinate0` → `varying vTexCoord` → `vTexCoord = kzTextureCoordinate0`），否则片元里 UV 没值 —— **最隐蔽**：uniform 暴露、绑定对、材质都建了，但效果就是没有。
3. **片元 shader 必须**：文件头 `precision highp float;` + `varying` 声明 + main 内 `precision mediump float;`（缺了要么编译失败要么渲染不对）。

> 判断法则：「改 shader 后 Studio 自动重读暴露出 uniform，若没出来就是 shader 本身不对」。

---

## 4. 属性 → uniform 绑定（让 Material 属性驱动 shader）

### 4.1 加属性到 MTPT

```bash
kz_get_raw_ref target=@objMT2 method=Get args=["@string:MaterialTypePropertyTypes"]   # → @objDynClass

# 用 AddDynamicPropertyType 加属性（可复用已有全局 ColorDynamicPropertyType）
kz_invoke target=@objDynClass method=AddDynamicPropertyType args=["@obj:<属性ref>"]

kz_invoke target=@objDynClass method=get_PropertyTypes   # 验证 → shader.colorXXX
```

> **坑**：`Get("MaterialTypePropertyTypes")` 返回**单个 DynamicClass 对象**（非 IEnumerable），用 `kz_get_raw_ref` 拿。

### 4.2 创建 Uniform binding（从自身复制 + set_Code + set_Target）

```bash
# 拿本 MaterialType 自带 Uniform binding（Property=null 那个）
kz_invoke target=@objMT2 method=get_Bindings   # → @objSelf

# 从自身复制（CreateBinding (Binding) 重载）→ 继承 Uniform 性质
kz_invoke target=@objMT2 method=CreateBinding args=["@obj:<@objSelf>"]   # → @objNew

# 改 DisplayCode（绑到材质属性）
kz_invoke target=@objNew method=set_Code args=["@string:{./shader.colorStart}"]

# ⚠️ 必须改 Target 为对应 ShaderVariableInfo（复制会继承源 Target！）
kz_get_raw_ref target=@objNew method=get_WrappedItem   # → @objNewBI（BindingItem）
kz_invoke target=@objNewBI method=set_Target args=["@obj:<对应uniform的ShaderVariableInfo>"]

# 验证
kz_get_raw_ref target=@objNewBI method=get_TargetType          # Uniform  ← 关键
kz_get_raw_ref target=@objNewBI method=get_Target              # 对应 ShaderVariableInfo
kz_get_raw_ref target=@objNewBI method=get_IsBindingActive     # True
kz_get_raw_ref target=@objNewBI method=get_IsBindingEnabled    # True
```

> **关键**：`CreateBinding` 复制继承源 Target，**不 set_Target 就指错**。`set_Target` 在 **WrappedItem（BindingItem）** 上调。
> 判定正确：`TargetType=Uniform` + `Target=正确 ShaderVariableInfo` + `DisplayCode={./shader.colorXXX}` + `Property=null`。
> 绑定表达式细节 → `kanzi-binding` skill。

---

## 5. Material + MaterialBrush 三层关联 + 设默认值

> **创建 Material/MaterialBrush/MaterialType 三层关联的完整流程 → `kanzi-material-brush` skill**。
> shader 场景只需记住关键点：
> - Material 关联 MaterialType：`Set("MaterialType", @objMT)`
> - MaterialBrush 关联 Material：`Set("MaterialBrush.Material", @objMat)`
> - **设 shader 默认值：在 Material/Brush 上 `Set("shader.colorXXX", @color:...)`，不是 MaterialType 上！**
> - 例：`Set("shader.colorStart", "@color:#FFFF0000")`

---

## 6. 写 GLSL 时需要知道的官方要点（不是教程，是操作必需）

> 完整语法/函数/属性表 → 用 kanzidocmcp 现查（见 §7），不要背。

- **默认 uniform（名字匹配即自动传值，直接用即可）**：
  - `kzProjectionCameraWorldMatrix`（mat4，局部→屏幕，顶点 shader 必用）
  - `kzTime`（float，动画/调试用）
  - `ContentTexture`（sampler2D，节点提供的纹理）、`RenderOpacity`（float，2D 节点透明度）
  - `kzCameraPosition`（vec3，相机位置）等
- **顶点属性语义名（Kanzi 自动映射，别乱起名）**：`kzPosition` / `kzNormal` / `kzTextureCoordinate0`~3 / `kzColor0`~3 / `kzTangent` 等。
- **精度**：顶点/片元声明 `precision highp float;`；移动端用中/低精度省性能。

---

## 7. 官方文档参考（用 kanzidocmcp 查）

**方法**：`kanzi_doc_mcp` 端点（`http://<kz_mcp_http机IP>:9001/kanzi_doc_mcp`，头 `X-Kanzi-User: suijichao`）→ `search_docs(query)` 定位 → `get_page(page_url)` 取全文 → `ask_question(question)` 问细节。

**常用页面**（4.1.1）：
- Shaders 总览：`.../working-with/shaders/shaders.html`（shader 类型、自带库）
- Editing shaders：`.../working-with/shaders/editing-shaders.html`（**属性/attribute/uniform 完整表、Shader Source Editor**）
- Using material types：`.../working-with/materials/using-material-types.html`（属性类型↔shader）
- Shader include library：`.../working-with/shaders/shader-include-library.html`（#include 复用）
- Shader graphs：`.../working-with/shader-graphs/shader-graphs.html`（可视化编辑器，实验特性）
- Shaders best practices：`.../best-practices/shaders/shaders-best-practices.html`（性能优化）
- 绑定表达式：`.../working-with/bindings/reference-for-bindings-expressions.html`

---

## 8. 验证 + 保存

```bash
# 完整链条验证
kz_invoke target=@objDynClass method=get_PropertyTypes   # shader.colorStart/End
kz_invoke target=@objMat method=Get args=["@string:MaterialType"]             # → @objMT2
kz_invoke target=@objBrush method=Get args=["@string:MaterialBrush.Material"] # → Material
kz_invoke target=@objMat method=Get args=["@string:shader.colorStart"]        # → Color ref
kz_invoke target=<ColorRef> method=ToString                                    # → #FFFF0000

# 保存（必须 GeneratedCommandInvoker，铁律）
kz_invoke target=@studio method=get_Commands    # → @objInvoker
kz_invoke target=@objInvoker method=SaveProject args=["@project"]
```

---

## 9. 关键要点速查

1. **顶点+片元两个 shader 都要改**；顶点必须传 `vTexCoord`，片元必须 precision+varying+main 内 precision。
2. **属性→uniform 靠 MTPT + Uniform binding**（`{./shader.colorXXX}` 语法），不是直接写死在 GLSL。
3. **CreateBinding 复制会继承源 Target，set_Target 必须在 WrappedItem 上调**。
4. **shader 默认值设在 Material/Brush 上**（`Set("shader.colorXXX")`），不是 MaterialType 上。
5. **新名字，不污染**现有工程资源。
6. **保存走 GeneratedCommandInvoker**。
7. **`@objN` 引用动态编号，连上先枚举定位**。
8. **改 shader 后 Studio 自动重编译**；Log 看错误，Preview 红色 = 无效。
9. **GLSL 语法/完整表用 kanzidocmcp 现查**，别背、别猜。

## 相关

- 材质笔刷三层完整流程（含双 shader 源码示例）→ `kanzi-material-brush`
- 绑定表达式 / CreateBinding → `kanzi-binding`
- 节点创建 / 属性设置 / `@color:` 标识符 → `kanzi-node-create` / `kanzi-prop-set`
- 保存/导出 → `kanzi-save-export`
