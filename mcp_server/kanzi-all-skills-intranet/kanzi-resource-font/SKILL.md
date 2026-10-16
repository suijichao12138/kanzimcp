---
name: kanzi-resource-font
description: Kanzi 创建字体（FontFamily）+ 资源定位（找 brush 和图片）。
---

## 三、创建字体（Font Family）

> 在 FontFamilies 库创建 `FontFamily` 并绑定字体文件（FontFiles = List<FontFile>）。两条链路：创建字体 + 绑字体文件。

### 1. 定位字体相关资源
```python
@project.get_FontFamilyLibrary()   # → FontFamilyLibrary (现有: MiSans-Medium等), 如 @obj2
@project.get_FontDirectory()        # → FontDirectory (字体文件: xxx.ttf), 如 @obj9
# FontDirectory 里是字体文件: MiSans-Medium.ttf / MiSans-Regular.ttf 等，需 get_Children 遍历拿到 ref
```

### 2. 创建字体（FontFamily 完整类型名）
```python
# 泛型 T = 完整类型名 Rightware.Kanzi.Studio.PluginInterface.FontFamily（同纹理 SingleTexture 套路）
@project.CreateProjectItem(
    "@type:Rightware.Kanzi.Studio.PluginInterface.FontFamily",
    "@string:__font_test__",        # 唯一名(重名报 existing，可先 GenerateUniqueChildName)
    "@obj2")                         # 父容器 = FontFamilyLibrary（不是 FontDirectory！字创建在库下）
# → @obj8 (FontFamilyPluginWrapper) ✅
# 字体属性只有 2 个: FontFiles、Name
```

### 3. 绑定字体文件（FontFiles = List<FontFile>，用 @list: 前缀）
> ⚠️ FontFiles 是【集合类型 List<FontFile>】，不能直接 Set 单个 @obj 引用！

```python
# v7 起反射桥支持 @list: 前缀构造 List<T>:
#   @list:类型名@obj1,@obj2  → List<T>
#   @list:@obj1,@obj2        → List<object> (无类型名)
# 类型名 = 元素类型(接口/类)，如 Rightware.Kanzi.Studio.PluginInterface.FontFile(接口,可收实现类型)
@obj8.Set("FontFiles", "@list:Rightware.Kanzi.Studio.PluginInterface.FontFile@obj10,@obj11")  # 绑 2 个 ✅
```

### 4. 读回验证 + 保存
```python
@obj8.Get("FontFiles")  # 单绑 ['@obj10']，双绑 ['@obj10','@obj11']
# 注意: get_Item/Get 对集合属性只显示尾部一个(反射桥摊开)，要看完整看返回的 refs 列表
@studio.get_Commands()  # → GeneratedCommandInvoker
invoker.SaveProject("@project")  # ✅（@project 上无 SaveProject，必须走 invoker）
```

> **@obj 引用每次连接/重启动态重新编号**：连上后必须用 get_FontFamilyLibrary / get_FontDirectory / get_Children 重新枚举定位。
> **@list: 支持任意集合属性**（不只 FontFiles）：凡文档要求传 List<T> 的参数，都能用 `@list:类型名@obj1,@obj2` 构造。

---

## 五、资源定位（在工程里找 brush 和图片）

```python
# 颜色刷资源：Brushes 库（@obj113）
mcp kz_invoke target=@obj113 method=get_Children
# → Color Brush_FFFFFF = @obj5736, Color Brush_000000 = @obj5735

# 图片资源：Textures 库（@obj140）→ 子库 adas（@obj5784）
mcp kz_invoke target=@obj5784 method=get_Children
# → green_sig_num = @obj5831 (get_Path = Textures/adas/green_sig_num)
# 注意：资源 ref 每次连接 Studio 动态分配，需重新定位，不能硬编码
```

---

## 关键点回顾

- 文本（string）用 `@string:` 直接值，或用 `KzResourceID:`；图片/颜色（ResourceReference）用 `@obj` 或 `KzResourceID:`。
- **一律用 `KzResourceID:` 前缀**表示 resource 引用（勿用 `resourceID:`）。
- 创建普通节点用 `kz_create_node type=TextBlock2D/Image2D`（非占位符）——节点创建见本体 `kanzi-ui` skill。
- **创建 MaterialType/Material/MaterialBrush** → **本 skill「四、创建材质笔刷」**（完整 6 步流程 + 各步坑）。
- 🌟 **材质笔刷最大坑**：**顶点着色器（.vert）和片元着色器（.frag）两个都要 SetText**，且都要与之前创建逐字一致。顶点要传 `vTexCoord = kzTextureCoordinate0`（否则渐变出不来）；片元要 `precision highp float;` + `varying vTexCoord;` + main 内 `precision mediump float;`。
- 🌟 **默认色设在 Material/Brush 上**（`Set("shader.colorStart", "@color:...")`），**不是 MaterialType 上**。
- 保存走 GeneratedCommandInvoker（`@studio.get_Commands()` → `SaveProject`），勿用 ExecuteCommand。

## 相关

- 节点创建/属性设置/文本图片颜色设置 → `kanzi-ui` skill（本 skill 的母体）
- 保存/导出 → `kanzi-save-export` skill
- `@color:` / `@list:` / `@type:` / `@enum:` 等 v4 参数标识符 → `kanzi-ui` skill 文末总表
