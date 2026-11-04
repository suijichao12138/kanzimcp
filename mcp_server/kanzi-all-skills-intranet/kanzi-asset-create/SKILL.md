---
name: kanzi-asset-create
description: Kanzi 创建素材：颜色笔刷（Color Brush）、纹理（Texture/SingleTexture）、字体（FontFamily）。含完整类型名、@color:/@list: 前缀、关键坑。创建 Resource 资源条目见 kanzi-resource-create；设置引用见 kanzi-resource-set。
---

## 🚫 命名铁律（创建前必读）

> 创建任何东西（节点/动画/别名/条目）时，**名字禁止特殊字符**：`\` `/` `|` `.` `:` `*` `?` `"` `'` `<` `>` 空格。
> **允许中文，推荐英文**（中文名可用，但英文更稳妥，避免跨工具编码问题）。
> 不要以数字开头（部分 API 限制）。
> 错误：`text/header` `bg.1` `a|b` `C:\temp` `new node`；正确：`text_header` `bg_1` `标题文本` `header-text`。

# 创建素材（颜色刷 / 纹理 / 字体）

> 素材 = 在工程 Brushes / Textures / Font Families 库里创建的独立对象：**颜色刷、纹理、字体**。
> 它们不是 Resource 条目（Resource 条目 = ResourceDictionary 里的条目，见 kanzi-resource-create）。

### 🔍 创建前查重（幂等，2026-10-26 加，协议铁律第17条）

> 子会话可能被重派重试，**不假设本次任务全新**。创建素材前先查对应库是否已存在同名对象，**已存在则跳过创建**，回报注明「N 个已存在跳过」。注意 `GenerateUniqueChildName` 会**自动加 `_1/_2` 后缀造新名**，不能用它来规避查重。

```python
# Brushes 库：get_BrushLibrary → get_Children，比对颜色刷名
mcp kz_invoke target=@project method=get_BrushLibrary
mcp kz_invoke target=<Brushes ref> method=get_Children
# → 本次要创建的颜色刷名已存在 → 跳过

# Textures 库：@project.get_Children() 里 name=="Textures" → get_Children（含子库），比对纹理名
# Font Families 库：@project.get_Children() 里 name=="Font Families" → get_Children，比对字体名
```

## 一、创建颜色笔刷（Color Brush）

> 在工程 **Brushes 库** 里新建颜色刷并设 RGBA 颜色。颜色刷是 UI 前景色/背景色的常用素材。

### ⚠️ 最关键的坑：CreateBrush 是在 `@project` 上调，不是在 BrushLibrary 上！

`CreateBrush` 是 **Project 的方法**，不是 BrushLibrary 的方法。在 BrushLibrary 上调会报 "找不到方法 CreateBrush"。

签名（官方插件 API）：`CreateBrush(string name, BrushLibrary parent, BrushTypeEnum brushType)`，颜色刷用 `BrushTypeEnum.COLOR`。

### 两步流程

**第1步：创建 Color Brush**
```python
# 定位 Brushes 库（拿 BrushLibrary 引用）
mcp kz_invoke target=@project method=get_BrushLibrary        # → <Brushes库ref> (BrushLibraryPluginWrapper, 编号每次连接变)

# 在 @project 上调 CreateBrush：名字, Brushes库, BrushTypeEnum.COLOR
mcp kz_invoke target=@project method=CreateBrush args=["@string:Color Brush_9BA014", "<Brushes库ref>", "@enum:COLOR"]
# → 返回 ref_id = <新颜色刷ref> (BrushPluginWrapper)
# 名字用 GenerateUniqueChildName；重名会自动加 _1/_2 后缀（如 Color Brush_9BA014_1）
```

**第2步：设置颜色 `Set("ColorBrush.Color", "@color:AARRGGBB")`**
```python
mcp kz_invoke target=<新颜色刷ref> method=Set args=["ColorBrush.Color", "@color:#FF9BA014"]   # ✅ R155 G160 B20 A255
# @color: 前缀解析成 System.Windows.Media.Color（WPF Color 对象）
# 读回验证：get_Item → Color 对象，再 ToString() → #FF9BA013 之类 #AARRGGBB
```

### ⚠️🌟 关键坑

**1. `CreateBrush` 的三个必要参数**
- `name`：笔刷名，用 `@string:` 前缀（有空格）。
- `parent`：Brushes 库对象引用（`@project.get_BrushLibrary` 拿到）。
- `brushType`：**用 `@enum:COLOR`**（或 BrushType 对象引用）。裸字符串 `ColorBrush`、`@enum:ColorBrush` 都报 "找不到与参数匹配的 CreateBrush"。
  - 枚举值对照：**COLOR**(颜色刷)、CONTENT、MATERIAL、TEXTURE；枚举名要看 BrushTypeEnum。

**2. 颜色属性名是 `ColorBrush.Color`（只存在于 Color Brush）**
- 类型 `System.Windows.Media.Color`（验证：`get_PropertyTypes` 里有 `name = ColorBrush.Color`，fullType 含 `System.Windows.Media.Color`）。
- **只接受 Color 值对象**，不接受字符串！试遍 `@string:#FF9BA014`、`@color:`、裸字符串、`@int:` 全报 "given value cannot be converted to studio internal property value"。
- **必须用 `@color:` 前缀传**。

**3. ⚠️ 平台舍入：B 通道可能差 1**
- `@color:#FF9BA014`（B=14）读回 `#FF9BA013`（B=13）。WPF/Kanzi sRGB→scRGB→sRGB 浮点往返固有舍入，不是 `@color:` 解析问题。
- 纯黑/纯白/纯红等边界色（0x00/0xFF）精确无舍入；只有中间值会 ±1。UI 用途差 1 可忽略；需精确可传相邻值补偿。

### 完整实测示例

```python
# 1. 拿 Brushes 库
mcp kz_invoke target=@project method=get_BrushLibrary   # → <Brushes库ref>
# 2. 创建颜色刷（@project 上调 CreateBrush）
mcp kz_invoke target=@project method=CreateBrush args=["@string:Color Brush_9BA014", "<Brushes库ref>", "@enum:COLOR"]   # → <新颜色刷ref>
# 3. 设颜色 R=155 G=160 B=20 A=255
mcp kz_invoke target=<新颜色刷ref> method=Set args=["ColorBrush.Color", "@color:#FF9BA014"]
# 4. 读回验证
mcp kz_invoke target=<新颜色刷ref> method=get_Item args=["ColorBrush.Color"]        # → <Color对象ref> (Color, 编号每次连接变)
mcp kz_invoke target=<Color对象ref> method=ToString args=[]                             # → #FF9BA013
mcp kz_invoke target=<Color对象ref> method=get_R args=[]   # R=155
# 5. 保存
mcp kz_invoke target=@studio method=get_Commands  # → <命令执行器ref> (GeneratedCommandInvoker)
mcp kz_invoke target=<命令执行器ref> method=SaveProject args=["@project"]   # ✅ 保存落盘
```

### 要点
- `CreateBrush` 是 @project 的方法，不是 BrushLibrary！
- brushType 用 `@enum:COLOR`；设色用 `Set("ColorBrush.Color", "@color:#AARRGGBB")`。
- `@color:` 前缀：解析 `AARRGGBB`（8位）或 `RRGGBB`（6位，A=255），`#` 可有可无。
- 删除多余测试 brush：对 brush 引用调 `Delete()` 成功。
- 保存：`@studio.get_Commands()` → `SaveProject(@project)`。

## 二、创建纹理（Texture / SingleTexture）

> 创建一个 `SingleTexture`（纹理）并绑定图片文件。纹理是图片在工程 Textures 库里的项（实例是 `SingleTexturePluginWrapper`）。

### ⚠️🌟 最关键的坑：泛型 T 必须用**完整类型名**

推荐用 `CreateProjectItem<SingleTexture>(name, textureLibrary)`。MCP 里泛型 T 用 `@type:` 前缀，**必须是完整类型名**：

| 写法 | 结果 |
|---|---|
| `@type:Rightware.Kanzi.Studio.PluginInterface.SingleTexture` | ✅ 成功 |
| `@type:SingleTexture`（短名）| ❌ 报 `Argument projectItemType must extend...` |
| `@type:Rightware.Kanzi.SingleTexture`（少 Studio.PluginInterface）| ❌ ResolveTypeByName 失败 |

### 一、纹理创建到【文件夹下】（如 adas 文件夹）
```python
# 1. 拿 TextureLibrary + 目标文件夹（adas）引用
mcp kz_invoke target=@project method=get_TextureLibrary   # → <顶层纹理库ref>
mcp kz_invoke target=<顶层纹理库ref> method=get_Children           # → 子库 adas = <adas文件夹ref>
# 2. 创建纹理（父容器 = <adas文件夹ref>）
mcp kz_invoke target=@project method=CreateProjectItem args=["@type:Rightware.Kanzi.Studio.PluginInterface.SingleTexture", "@string:green_sig_num", "<adas文件夹ref>"]
# → ✅ <新纹理ref>，Path = Textures/adas/green_sig_num
```

### 二、纹理创建到【根目录下】（Texture 顶层）
```python
# 父容器 = <顶层纹理库ref>（不是 adas）
mcp kz_invoke target=@project method=CreateProjectItem args=["@type:Rightware.Kanzi.Studio.PluginInterface.SingleTexture", "@string:green_sig_num_tl", "<顶层纹理库ref>"]
# → ✅ <新纹理ref>，Path = Textures/green_sig_num_tl
```
> **第 3 参（父容器）决定位置**：传文件夹 → `Textures/adas/xxx`；传顶层 → `Textures/xxx`。

### 三、创建文件夹（子库）及子文件夹
> 纹理文件夹 = `CreateProjectItem` + 泛型 T 用 **`TextureLibrary`** 完整类型名（TextureLibrary 既是顶层库类型，也是子库/文件夹类型）。

```python
# Texture 顶层建文件夹（父 = <顶层纹理库ref>）
mcp kz_invoke target=@project method=CreateProjectItem args=["@type:Rightware.Kanzi.Studio.PluginInterface.TextureLibrary", "@string:__texdir_test__", "<顶层纹理库ref>"]
# → ✅ <新文件夹ref>，Path = Textures/__texdir_test__
# 文件夹内再建子文件夹（父 = <新文件夹ref>）
mcp kz_invoke target=@project method=CreateProjectItem args=["@type:Rightware.Kanzi.Studio.PluginInterface.TextureLibrary", "@string:__sub_dir__", "<新文件夹ref>"]
# → ✅ <新子文件夹ref>，Path = Textures/__texdir_test__/__sub_dir__
```

| 创建目标 | 泛型 @type: 完整类型名（只差这一处！） |
|---|---|
| 纹理 | `Rightware.Kanzi.Studio.PluginInterface.**SingleTexture**` |
| 文件夹(子库) | `Rightware.Kanzi.Studio.PluginInterface.**TextureLibrary**` |

### 四、获取图片（不走磁盘路径）
> 图片必须从 Kanzi Studio 里获得，不能用磁盘路径。`ImageDirectory.GetChild("xxx.png")` 会报「不明确的匹配」（反射桥重载歧义），**用 `get_Children` 遍历最可靠**。

```python
# 1. 拿 ImageDirectory
mcp kz_invoke target=@project method=get_ImageDirectory   # → <ImageDirectory ref>
# 2. 找图片所在子文件夹（如 adas）
mcp kz_invoke target=<ImageDirectory ref> method=get_Children          # → adas = <adas图片夹ref>
# 3. 找目标图片（green_sig_num.png）
mcp kz_invoke target=<adas图片夹ref> method=get_Children          # → green_sig_num.png = <图片ref>
# 图片的 get_Path = Resource Files/Images/adas/green_sig_num.png
```

### 🌟 识别图片是【图片】还是【文件夹】
遍历 ImageDirectory 时每项可能是图片也可能是子文件夹，**必须区分**（图片才建纹理，文件夹要递归进去）：

| 特征 | 图片文件 | 子文件夹 |
|---|---|---|
| **ProjectItemType name** | `ImageFile` | `ImageDirectory` |
| **CLR fullType** | `...ImageFilePluginWrapper` | `...ImageDirectoryPluginWrapper` |
| **名字带扩展名** `.png/.jpg/.dds` | ✅ 是 | ❌ |
| **名字无扩展名**（如 day/night） | ❌ | ✅ |

> 推荐判断：先看名字有无扩展名（快），再配合 fullType 确认。枚举遇文件夹就递归进去，为里面图片也建纹理（子文件夹结构同步建到纹理库）。

### 五、设置图片（绑定到纹理）
> 属性名是 **`TextureImage`**，不是 `SingleTexture.Image` / `Image`（那两个都不存在）。

```python
mcp kz_invoke target=<新纹理ref> method=Set args=["TextureImage", "<图片ref>"]   # ✅
# 读回：get_Item("TextureImage") → <图片ref> 即成功
```
> 纹理可用属性（get_Properties 确认）：`TextureImage`、`ImportedFrom`、`IDInImportSource`、`GpuResourceMemoryType`、`TextureMinificationFilter`、`TextureMagnificationFilter`、`TextureFormat`、`TextureWrapMode`、`TextureAnisotropyType`、`Name`。

### 六、完整流程示例（建夹→建纹理→绑图）
```python
# 前提：TextureLibrary=<顶层纹理库ref>, adas=<adas文件夹ref>, ImageDirectory=<ImageDirectory ref>, adas图=<adas图片夹ref>
# 1. 图片引用：green_sig_num.png = <图片ref>（get_Children 遍历）
# 2. 在 adas 下创建纹理
@project.CreateProjectItem("@type:Rightware.Kanzi.Studio.PluginInterface.SingleTexture", "@string:green_sig_num", "<adas文件夹ref>")  # → <新纹理ref>
# 3. 绑图
<新纹理ref>.Set("TextureImage", "<图片ref>")
# 4. 读回验证：<新纹理ref>.get_Item("TextureImage") → <图片ref>
# 5. 保存：@studio.get_Commands() → SaveProject("@project")
```
> **重名规则**：同一文件夹下不能有同名纹理；重名报 `A child with the name "xxx" already exists`。不同文件夹重名不冲突。创建前可用 `GenerateUniqueChildName(name)` 拿唯一名。

## 三、创建字体（Font Family）

> 在 FontFamilies 库创建 `FontFamily` 并绑定字体文件（FontFiles = List<FontFile>）。两条链路：创建字体 + 绑字体文件。

### 1. 定位字体相关库
```python
@project.get_FontFamilyLibrary()   # → <FontFamilyLibrary ref> (现有: MiSans-Medium等)
@project.get_FontDirectory()        # → <FontDirectory ref> (字体文件: xxx.ttf)
# FontDirectory 里是字体文件: MiSans-Medium.ttf / MiSans-Regular.ttf 等，需 get_Children 遍历拿到 ref
```

### 2. 创建字体（FontFamily 完整类型名）
```python
# 泛型 T = 完整类型名 Rightware.Kanzi.Studio.PluginInterface.FontFamily（同纹理 SingleTexture 套路）
@project.CreateProjectItem(
    "@type:Rightware.Kanzi.Studio.PluginInterface.FontFamily",
    "@string:__font_test__",        # 唯一名(重名报 existing，可先 GenerateUniqueChildName)
    "<FontFamilyLibrary ref>")                         # 父容器 = FontFamilyLibrary（不是 FontDirectory！字创建在库下）
# → <新字体ref> (FontFamilyPluginWrapper) ✅
# 字体属性只有 2 个: FontFiles、Name
```

### 3. 绑定字体文件（FontFiles = List<FontFile>，用 @list: 前缀）
> ⚠️ FontFiles 是【集合类型 List<FontFile>】，不能直接 Set 单个 @obj 引用！

```python
# v7 起反射桥支持 @list: 前缀构造 List<T>:
#   @list:类型名@obj1,@obj2  → List<T>
#   @list:@obj1,@obj2        → List<object> (无类型名)
# 类型名 = 元素类型(接口/类)，如 Rightware.Kanzi.Studio.PluginInterface.FontFile(接口,可收实现类型)
<新字体ref>.Set("FontFiles", "@list:Rightware.Kanzi.Studio.PluginInterface.FontFile<字体文件1ref>,<字体文件2ref>")  # 绑 2 个 ✅
```

### 4. 读回验证 + 保存
```python
<新字体ref>.Get("FontFiles")  # 单绑 [<字体文件1ref>]，双绑 [<字体文件1ref>,<字体文件2ref>]
# 注意: get_Item/Get 对集合属性只显示尾部一个(反射桥摊开)，要看完整看返回的 refs 列表
@studio.get_Commands()  # → GeneratedCommandInvoker
invoker.SaveProject("@project")  # ✅（@project 上无 SaveProject，必须走 invoker）
```

> **@obj 引用每次连接动态重新编号**（⚠️ **助手绝不重启 Studio**）：连上后必须用 get_FontFamilyLibrary / get_FontDirectory / get_Children 重新枚举定位。
> **@list: 支持任意集合属性**（不只 FontFiles）：凡文档要求传 List<T> 的参数，都能用 `@list:类型名@obj1,@obj2` 构造。

---

## 通用要点

- 文本（string）用 `@string:` 直接值；设置引用用 `KzResourceID:`（勿用 `resourceID:`）。
- 保存走 GeneratedCommandInvoker（`@studio.get_Commands()` → `SaveProject`），勿用 ExecuteCommand。
- `@color:` / `@list:` / `@type:` / `@enum:` 等 v4 参数标识符 → `kanzi-studio-mcp` skill（v4 参数标识符总表）。
- 设置节点上的引用（颜色刷/字体/状态机）→ `kanzi-resource-set` skill。
- 创建 Resource 资源条目（ResourceDictionary）→ `kanzi-resource-create` skill。
