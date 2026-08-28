---
name: kanzi-material-brush
description: Kanzi Studio 创建「参数化渐变材质笔刷」的完整流程（Material + MaterialType + MaterialBrush 三层关联，含顶点/片元双着色器、uniform 属性、binding）。2026-08-11 完整实测打通。适用于 HMI 工程要新建一个带红→黄（或任意两色）渐变的可复用材质刷。所有命令走中继桥（ws://10.10.118.152:58080，kz_invoke）。
---

# Kanzi 创建材质笔刷（参数化渐变）

## 🚀 多工程切换（2026-08-17 实测打通，v12）

bridge 支持多工程操作。默认 `@project` 指向 ActiveProject，可在多工程间随时切换，两种方式：

**① `kz_select_project` 切换 `@project` 作用目标（推荐）**
```json
{"name":"kz_select_project","arguments":{"name":"hmi-alarm"}}
// ✅ 已切换到工程: hmi-alarm（之后 @project 相关操作作用于该工程；ActiveProject 不变）

{"name":"kz_select_project","arguments":{"name":""}}
// ✅ 已切回 ActiveProject: cluster_hmi
```

**② `@proj:<工程名>[/路径]` 前缀独立引用某工程（不切 @project）**
```json
{"name":"kz_invoke","arguments":{"target":"@proj:hmi-alarm/Prefabs/warning","method":"get_Name","args":[]}}
```

**要点：**
- `kz_list_projects` 列出所有已打开工程（标 `[Active]` / `[Primary]`）。
- **select 到哪个工程就操作哪个；与工程是否 Active 无关**——次级工程上读写（建节点/保存）都正常。
- 切到某工程后，`/Screens/...`、`/Prefabs/...` 等路径都指该工程；要回 ActiveProject 再 select 空串。
- 全程 **ActiveProject 不变**（方案 A 承诺），不打扰你在 Studio 正编辑的工程。



> **2026-08-11 完整实测打通**。新建一个带「红→黄渐变」参数化 shader 的可复用材质刷。
> 三层关联：`Brush → MaterialBrush.Material → Material → MaterialType`。
> **一律用新名字，不污染现有工程**（progressBar/progressBarMaterial/redYellow 都不动）。

---

## 0. 前置：接入中继桥 + 定位库

```bash
# 接入：内网 HTTP MCP（relay_nlp_http/kz_mcp_http.py） http://10.10.118.152:9001/mcp，请求头 X-Kanzi-User: <用户名>
# 中继通道：ws://10.10.118.152:58080/<用户名>；调用 = 直接调 MCP 工具 kz_invoke（参数 {"target":"<ref或路径>","method":"<方法>","args":[...]}）

# 建立连接后先 initialize(protocolVersion=2024-11-05)，再：
kz_invoke target=@project method=get_Children          # → Material Types 库 @objMT
kz_invoke target=@project method=get_MaterialLibrary   # → Materials 库 @objMatLib
kz_invoke target=@project method=get_BrushLibrary      # → Brushes 库 @objBrushLib
```

> ⚠️ `@objN` 引用每次重连/重启 Studio 都会重新编号，**必须先枚举定位**，勿硬编码跨连接使用。
> 定位库用 `get_Children` 后按 `name = Material Types / Materials / Brushes` 匹配。

---

## 1. 创建 MaterialType + 写双着色器（⚠️ 最关键：顶点+片元都要改）

```bash
# 1.1 创建 MaterialType（泛型 @type 用完整类型名，父 = Material Types 库）
kz_invoke target=@project method=CreateProjectItem \
  args=["@type:Rightware.Kanzi.Studio.PluginInterface.MaterialType",
        "@string:kzGradientType_yy",          # 新名字(别冲突)
        "@objMT"]
# → @objMT2（MaterialTypePluginWrapper，自动带 1 个 Uniform binding: getProjectionCameraWorldMatrix）

# 1.2 定位本 MaterialType 的 Vertex + Fragment Shader 子项
kz_invoke target=@objMT2 method=get_Children   # → Vertex Shader=@objVS, Fragment Shader=@objFS

# 1.3 ⚠️⚠️ 两个着色器都要 SetText！缺一都不出渐变
#  (a) 顶点着色器：必须传 vTexCoord（kzTextureCoordinate0 → vTexCoord），否则 UV 没值、渐变出不来
kz_invoke target=@objVS method=SetText args=["@string:precision highp float;\nattribute vec3 kzPosition;\nattribute vec2 kzTextureCoordinate0;\nuniform highp mat4 kzProjectionCameraWorldMatrix;\nvarying mediump vec2 vTexCoord;\nvoid main()\n{\n    precision mediump float;\n    vTexCoord = kzTextureCoordinate0;\n    gl_Position = kzProjectionCameraWorldMatrix * vec4(kzPosition.xyz, 1.0);\n}\n"]
#  (b) 片元着色器：文件头 precision+varying + main内 precision（三处都要）
kz_invoke target=@objFS method=SetText args=["@string:precision highp float;\nvarying mediump vec2 vTexCoord;\nuniform vec4 colorStart;\nuniform vec4 colorEnd;\nvoid main()\n{\n    precision mediump float;\n    gl_FragColor = mix(colorStart, colorEnd, clamp(vTexCoord.x, 0.0, 1.0));\n}\n"]

# 1.4 读回验证（两个都 GetText）
kz_invoke target=@objVS method=GetText
kz_invoke target=@objFS method=GetText

# 1.5 shader 正确 → Studio 自动重读并暴露 uniform：
kz_invoke target=@objMT2 method=Get args=["@string:Uniforms"]  # → colorStart / colorEnd 的 ShaderVariableInfo（@objCS/@objCE）
```

### ⚠️ 两个正确 shader 的完整源码（对照复制，务必逐字一致）

```glsl
// 顶点着色器 .vert.glsl —— 必须传 vTexCoord！
precision highp float;
attribute vec3 kzPosition;
attribute vec2 kzTextureCoordinate0;
uniform highp mat4 kzProjectionCameraWorldMatrix;
varying mediump vec2 vTexCoord;
void main()
{
    precision mediump float;
    vTexCoord = kzTextureCoordinate0;
    gl_Position = kzProjectionCameraWorldMatrix * vec4(kzPosition.xyz, 1.0);
}

// 片元着色器 .frag.glsl —— 渐变核心
precision highp float;
varying mediump vec2 vTexCoord;
uniform vec4 colorStart;
uniform vec4 colorEnd;
void main()
{
    precision mediump float;
    gl_FragColor = mix(colorStart, colorEnd, clamp(vTexCoord.x, 0.0, 1.0));
}
```

### 🌟 最容易踩的 3 个坑（老隋连续指正）
1. **片元着色器缺 `vTexCoord` 声明**（`varying mediump vec2 vTexCoord;`）→ 编译失败、uniform 读不出（Get("Uniforms") 只有 kzProjectionCameraWorldMatrix）。
2. **片元着色器 main 内缺 `precision mediump float;`** → uniform 能暴露但渲染不对。
3. **顶点着色器没传 `vTexCoord`**（缺 `attribute kzTextureCoordinate0` / `varying vTexCoord` / `vTexCoord = kzTextureCoordinate0`）→ **最隐蔽**：uniform 暴露、binding 对、材质 brush 都建了，但渐变就是出不来（片元里 vTexCoord.x 没值）。

> 「改 shader（文件或 SetText）后 Studio 会自动重读暴露出 uniform，若没出来就是 shader 本身不对」。

---

## 2. 加属性到 MaterialTypePropertyTypes（MTPT）

```bash
# 2.1 拿 MTPT（= DynamicClass，单个对象，用 kz_get_raw_ref）
kz_get_raw_ref target=@objMT2 method=Get args=["@string:MaterialTypePropertyTypes"]   # → @objDynClass

# 2.2 用 AddDynamicPropertyType 把 colorStart/colorEnd 属性加进去
#  （用已有的全局 ColorDynamicPropertyType——progressBar/redYellow 的 shader.colorStart/colorEnd 是全局共享的同一 ref）
kz_invoke target=@objDynClass method=AddDynamicPropertyType args=["@obj:<colorStart属性ref>"]
kz_invoke target=@objDynClass method=AddDynamicPropertyType args=["@obj:<colorEnd属性ref>"]

# 2.3 验证
kz_invoke target=@objDynClass method=get_PropertyTypes   # → 应显示 shader.colorStart / shader.colorEnd
```

> 🌟 **坑**：`Get("MaterialTypePropertyTypes")` 返回的是**单个 DynamicClass 对象**（不是 IEnumerable），用 `kz_get_raw_ref` 拿。
> DynamicClass 方法含：`AddDynamicPropertyType` / `AddDynamicPropertyTypes` / `RemoveDynamicPropertyType` / `ClearPropertyTypes` / `get_PropertyTypes` / `AddDynamicPropertyTypesFrom` / `ContainsDynamicPropertyType`。
> colorStart/colorEnd **属性对象**可复用 progressBar/redYellow 已有的（全局共享的 ColorDynamicPropertyType），不必自建。

---

## 3. 创建 Uniform bindings（从自身复制 + set_Code + set_Target）

> 目标：colorStart/colorEnd 绑定到正确 Uniform。判定正确：`TargetType=Uniform` + `Target=对应 ShaderVariableInfo` + `DisplayCode={./shader.colorXXX}` + `Property=null`。

```bash
# 3.1 拿本 MaterialType 自带的 Uniform binding（Property=null 那个，如 getProjectionCameraWorldMatrix）
kz_invoke target=@objMT2 method=get_Bindings   # → @objSelf（code=getProjectionCameraWorldMatrix()）

# 3.2 从自身复制（CreateBinding 的 (Binding sourceBinding) 重载，不依赖 progressBar）
kz_invoke target=@objMT2 method=CreateBinding args=["@obj:<@objSelf>"]
# → @objNew，继承 Uniform 性质（TargetType=Uniform）

# 3.3 改 DisplayCode
kz_invoke target=@objNew method=set_Code args=["@string:{./shader.colorStart}"]
# colorEnd 同理：set_Code("{./shader.colorEnd}")

# 3.4 ⚠️必须改 Target 为对应 ShaderVariableInfo（Uniforms 里的 colorStart/colorEnd）——复制会继承源 Target！
kz_get_raw_ref target=@objNew method=get_WrappedItem   # → @objNewBI（BindingItem）
kz_invoke target=@objNewBI method=set_Target args=["@obj:<@objCS>"]   # colorStart 绑定 → 对应 ShaderVariableInfo
kz_invoke target=@objNewEndBI  method=set_Target args=["@obj:<@objCE>"] # colorEnd 绑定 → 对应 ShaderVariableInfo

# 3.5 验证（每个都应正确）
kz_get_raw_ref target=@objNewBI method=get_TargetType          # Uniform  ← 关键
kz_get_raw_ref target=@objNewBI method=get_Target              # colorStart/colorEnd ShaderVariableInfo
kz_get_raw_ref target=@objNewBI method=get_IsBindingActive     # True
kz_get_raw_ref target=@objNewBI method=get_IsBindingEnabled    # True
```

> 🌟 **关键**：`CreateBinding` 复制会继承源 BindingItem 的 Target（如 getProjection 的 ShaderVariableInfo），**不 set_Target 就指错**。`set_Target` 要在 **WrappedItem（BindingItem）** 上调（不是 binding wrapper 上）。
> `CreateBinding` 两个重载：`(Property,Enum,String)` 建普通属性绑定；`(Binding sourceBinding)` 从源绑定复制（本流程用这个）。

---

## 4. 创建 Material + MaterialBrush（三层关联 + 设默认色）

```bash
# 4.1 创建 Material（Materials 库），关联 MaterialType
kz_invoke target=@project method=CreateProjectItem \
  args=["@type:Rightware.Kanzi.Studio.PluginInterface.Material",
        "@string:kzGradientMaterial_yy", "@objMatLib"]
# → @objMat
kz_invoke target=@objMat method=Set args=["MaterialType", "@objMT2"]

# 4.2 创建 MaterialBrush（CreateBrush 是 @project 方法，brushType 用 @enum:MATERIAL），关联 Material
kz_invoke target=@project method=CreateBrush \
  args=["@string:kzGradientBrush_yy", "@objBrushLib", "@enum:MATERIAL"]
# → @objBrush
kz_invoke target=@objBrush method=Set args=["MaterialBrush.Material", "@objMat"]

# 4.3 ⚠️设 shader 默认色：在 Material/Brush 上 Set("shader.colorStart")，不是 MaterialType 上（MaterialType 无此实例属性）！
kz_invoke target=@objMat method=Set args=["shader.colorStart", "@color:#FFFF0000"]   # 红
kz_invoke target=@objMat method=Set args=["shader.colorEnd",   "@color:#FFFFFF00"]   # 黄
# (Brush @objBrush 上 Set 同样生效)
```

---

## 5. 完整链条验证 + 保存

```bash
# MaterialType MTPT 属性
kz_invoke target=@objDynClass method=get_PropertyTypes   # shader.colorStart / shader.colorEnd
# Material → MaterialType
kz_invoke target=@objMat method=Get args=["@string:MaterialType"]             # → @objMT2
# Brush → Material
kz_invoke target=@objBrush method=Get args=["@string:MaterialBrush.Material"] # → 关联 Material
# 颜色读回（Color 对象 ref → ToString → #AARRGGBB）
kz_invoke target=@objMat method=Get args=["@string:shader.colorStart"]   # → Color ref
kz_invoke target=<ColorRef> method=ToString                             # → #FFFF0000（红）
# 保存（必须走 GeneratedCommandInvoker，铁律）
kz_invoke target=@studio method=get_Commands    # → @objInvoker
kz_invoke target=@objInvoker method=SaveProject args=["@project"]
```

---

## 关键要点回顾

1. **顶点 + 片元两个着色器都要改**：顶点传 `vTexCoord = kzTextureCoordinate0`（渐变必需）；片元 `precision highp float;` + `varying vTexCoord;` + main 内 `precision mediump float;`。都需与已有正确 shader 逐字一致。
2. **Uniform binding 用「从自身复制 + set_Code + set_Target」**，不依赖其他 MaterialType（progressBar）。
3. **set_Target 是必须的**：复制会继承源 BindingItem 的 Target，必须改成 colorStart/colorEnd 对应 ShaderVariableInfo，否则绑定指错。在 WrappedItem（BindingItem）上调。
4. **判断正确 Uniform binding**：`TargetType=Uniform` + `Target=正确 ShaderVariableInfo` + `DisplayCode={./shader.colorXXX}` + `Property=null`。
5. **CreateBinding 重载**：`(Property,Enum,String)` 普通；`(Binding sourceBinding)` 从源复制。
6. **默认色设在 Material/Brush 上**（`Set("shader.colorStart", "@color:...")`），不是 MaterialType 上。
7. **全新建名字，不污染**现有 progressBar / progressBarMaterial / redYellow 等。
8. **保存走 GeneratedCommandInvoker**（`@studio.get_Commands()` → `SaveProject`），勿用 ExecuteCommand。
9. **`@objN` 引用每次重连/重启动态编号**，连上必须先枚举定位。
10. **MaterialTypePropertyTypes** = 单个 DynamicClass 对象，用 `AddDynamicPropertyType` 加 colorStart/colorEnd（复用已有的全局 ColorDynamicPropertyType）。

## 相关

- 颜色笔刷 / 纹理 / 字体等其它资源创建 → `kanzi-resource-create` skill
- 节点创建/属性设置 → `kanzi-ui` skill
- 保存/导出 → `kanzi-save-export` skill
- `@color:` / `@list:` / `@type:` / `@enum:` 等参数标识符 → `kanzi-ui` skill 文末总表
