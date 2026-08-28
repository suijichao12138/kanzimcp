---
name: kanzi-resource-create
description: Kanzi Studio 资源创建（从 kanzi-ui skill 独立抽出）。创建颜色笔刷（Color Brush，@project.CreateBrush + @color:）、创建纹理（Texture/SingleTexture，@type:完整类型名 + TextureImage 绑图）、创建字体（FontFamily，@list: 绑 FontFiles）、以及资源定位（Brushes/Textures 库找刷子和图片）。所有资源项都通过 @project.CreateProjectItem/CreateBrush 创建在对应库下。
---

# Kanzi 资源创建

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



> 从 `kanzi-ui` skill 独立抽出的「资源创建」部分。涵盖了在工程各资源库里新建资源的完整方法：**颜色笔刷 / 纹理 / 字体**。全部为 2026-08-07 v6/v7 实测打通。

## 接入方式（内网 HTTP MCP）

通过内网 HTTP MCP server（`relay_nlp_http/kz_mcp_http.py`）连接 Kanzi Studio 插件，直接调用 MCP 工具，无需本地客户端脚本。

- **HTTP MCP**：`http://10.10.118.152:9001/mcp`（请求头 `X-Kanzi-User: <用户名>`，白名单见 users.json，如 `suijichao`）
- **中继通道**：`ws://10.10.118.152:58080/<用户名>`（relay_multi 监听 58080，路径决定连哪台 Kanzi，须与 kz_mcp_http.py 一致）
- **调用**：直接调用 MCP 工具 `kz_invoke` 等，参数 `{"target":..., "method":..., "args":[...]}`
- **参数格式**：`{"name":"kz_invoke","arguments":{"target":"<ref或路径>","method":"<方法>","args":[...]}}`
- 返回 `ref_id = @objN` 自动进对象缓存，`@objN` 可作后续 target（重启 Studio 后编号失效，须重新枚举）
- 示例中的 `mcp kz_invoke target=X method=Y args=[...]` 等价于直接调用 MCP 工具 `kz_invoke`（参数 `{"target":"X","method":"Y","args":[...]}`）`
- 下面示例中的 `mcp kz_invoke ...` 即上一条（中继桥 `kz_invoke` 工具）的简写，参数遵循 v4 标识符。

---

## 核心总原则

1. **所有资源项都通过 `@project`（ActiveProject）创建**，不是在各库对象上建（`CreateBrush`/`CreateProjectItem` 都是 Project 的方法）。
2. **泛型 T 用 `@type:完整类型名`** 传入，必须是完整类型名（短名/错命名空间都失败）。
3. **图片、字体等资源必须从 Kanzi Studio 里获得**（不用磁盘路径），用 `get_Children` 遍历定位。
4. **`@obj` 引用每次连接/重启 Studio 都会重新编号**，每次连上必须重新枚举定位，不能硬编码旧 ref。
5. **保存**：`@studio.get_Commands()` 拿 `GeneratedCommandInvoker` → `SaveProject("@project")`（@project 上无 SaveProject 方法，必须走 invoker）。

---

## 一、创建颜色笔刷（Color Brush）

> 在工程 **Brushes 库** 里新建颜色刷并设 RGBA 颜色。颜色刷是 UI 前景色/背景色的常用资源。

### ⚠️ 最关键的坑：CreateBrush 是在 `@project` 上调，不是在 BrushLibrary 上！

`CreateBrush` 是 **Project 的方法**，不是 BrushLibrary 的方法。在 BrushLibrary 上调会报 "找不到方法 CreateBrush"。

签名（官方插件 API）：`CreateBrush(string name, BrushLibrary parent, BrushTypeEnum brushType)`，颜色刷用 `BrushTypeEnum.COLOR`。

### 两步流程

**第1步：创建 Color Brush**
```python
# 定位 Brushes 库（拿 BrushLibrary 引用）
mcp kz_invoke target=@project method=get_BrushLibrary        # → @obj2 (BrushLibraryPluginWrapper)

# 在 @project 上调 CreateBrush：名字, Brushes库, BrushTypeEnum.COLOR
mcp kz_invoke target=@project method=CreateBrush args=["@string:Color Brush_9BA014", "@obj2", "@enum:COLOR"]
# → 返回 ref_id = @obj49 (BrushPluginWrapper)
# 名字用 GenerateUniqueChildName；重名会自动加 _1/_2 后缀（如 Color Brush_9BA014_1）
```

**第2步：设置颜色 `Set("ColorBrush.Color", "@color:AARRGGBB")`**
```python
mcp kz_invoke target=@obj49 method=Set args=["ColorBrush.Color", "@color:#FF9BA014"]   # ✅ R155 G160 B20 A255
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
mcp kz_invoke target=@project method=get_BrushLibrary   # → @obj2
# 2. 创建颜色刷（@project 上调 CreateBrush）
mcp kz_invoke target=@project method=CreateBrush args=["@string:Color Brush_9BA014", "@obj2", "@enum:COLOR"]   # → @obj49
# 3. 设颜色 R=155 G=160 B=20 A=255
mcp kz_invoke target=@obj49 method=Set args=["ColorBrush.Color", "@color:#FF9BA014"]
# 4. 读回验证
mcp kz_invoke target=@obj49 method=get_Item args=["ColorBrush.Color"]        # → @obj54 (Color)
mcp kz_invoke target=@obj54 method=ToString args=[]                             # → #FF9BA013
mcp kz_invoke target=@obj54 method=get_R args=[]   # R=155
# 5. 保存
mcp kz_invoke target=@studio method=get_Commands  # → @obj67 (GeneratedCommandInvoker)
mcp kz_invoke target=@obj67 method=SaveProject args=["@project"]   # ✅ 保存落盘
```

### 要点
- `CreateBrush` 是 @project 的方法，不是 BrushLibrary！
- brushType 用 `@enum:COLOR`；设色用 `Set("ColorBrush.Color", "@color:#AARRGGBB")`。
- `@color:` 前缀：解析 `AARRGGBB`（8位）或 `RRGGBB`（6位，A=255），`#` 可有可无。
- 删除多余测试 brush：对 brush 引用调 `Delete()` 成功。
- 保存：`@studio.get_Commands()` → `SaveProject(@project)`。

---

## 二、创建纹理（Texture / SingleTexture）

> 创建一个 `SingleTexture`（纹理）资源并绑定图片文件。纹理是图片在工程 Textures 库里的资源项（实例是 `SingleTexturePluginWrapper`）。

### ⚠️🌟 最关键的坑：泛型 T 必须用**完整类型名**

老隋给的是 `CreateProjectItem<SingleTexture>(name, textureLibrary)`。MCP 里泛型 T 用 `@type:` 前缀，**必须是完整类型名**：

| 写法 | 结果 |
|---|---|
| `@type:Rightware.Kanzi.Studio.PluginInterface.SingleTexture` | ✅ 成功 |
| `@type:SingleTexture`（短名）| ❌ 报 `Argument projectItemType must extend...` |
| `@type:Rightware.Kanzi.SingleTexture`（少 Studio.PluginInterface）| ❌ ResolveTypeByName 失败 |

### 一、纹理创建到【文件夹下】（如 adas 文件夹）
```python
# 1. 拿 TextureLibrary + 目标文件夹（adas）引用
mcp kz_invoke target=@project method=get_TextureLibrary   # → @obj69（顶层库）
mcp kz_invoke target=@obj69 method=get_Children           # → 子库 adas = @obj221
# 2. 创建纹理（父容器 = adas 文件夹 @obj221）
mcp kz_invoke target=@project method=CreateProjectItem args=["@type:Rightware.Kanzi.Studio.PluginInterface.SingleTexture", "@string:green_sig_num", "@obj221"]
# → ✅ @obj1094，Path = Textures/adas/green_sig_num
```

### 二、纹理创建到【根目录下】（Texture 顶层）
```python
# 父容器 = 顶层 TextureLibrary @obj69（不是 adas）
mcp kz_invoke target=@project method=CreateProjectItem args=["@type:Rightware.Kanzi.Studio.PluginInterface.SingleTexture", "@string:green_sig_num_tl", "@obj69"]
# → ✅ @obj1095，Path = Textures/green_sig_num_tl
```
> **第 3 参（父容器）决定位置**：传文件夹 → `Textures/adas/xxx`；传顶层 → `Textures/xxx`。

### 三、创建文件夹（子库）及子文件夹
> 纹理文件夹 = `CreateProjectItem` + 泛型 T 用 **`TextureLibrary`** 完整类型名（TextureLibrary 既是顶层库类型，也是子库/文件夹类型）。

```python
# Texture 顶层建文件夹（父 = @obj69）
mcp kz_invoke target=@project method=CreateProjectItem args=["@type:Rightware.Kanzi.Studio.PluginInterface.TextureLibrary", "@string:__texdir_test__", "@obj69"]
# → ✅ @obj1097，Path = Textures/__texdir_test__
# 文件夹内再建子文件夹（父 = 刚建的文件夹 @obj1097）
mcp kz_invoke target=@project method=CreateProjectItem args=["@type:Rightware.Kanzi.Studio.PluginInterface.TextureLibrary", "@string:__sub_dir__", "@obj1097"]
# → ✅ @obj1098，Path = Textures/__texdir_test__/__sub_dir__
```

| 创建目标 | 泛型 @type: 完整类型名（只差这一处！） |
|---|---|
| 纹理 | `Rightware.Kanzi.Studio.PluginInterface.**SingleTexture**` |
| 文件夹(子库) | `Rightware.Kanzi.Studio.PluginInterface.**TextureLibrary**` |

### 四、获取图片（不走磁盘路径）
> 图片必须从 Kanzi Studio 里获得，不能用磁盘路径。`ImageDirectory.GetChild("xxx.png")` 会报「不明确的匹配」（反射桥重载歧义），**用 `get_Children` 遍历最可靠**。

```python
# 1. 拿 ImageDirectory
mcp kz_invoke target=@project method=get_ImageDirectory   # → @obj882
# 2. 找图片所在子文件夹（如 adas）
mcp kz_invoke target=@obj882 method=get_Children          # → adas = @obj891
# 3. 找目标图片（green_sig_num.png）
mcp kz_invoke target=@obj891 method=get_Children          # → green_sig_num.png = @obj1071
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
mcp kz_invoke target=@obj1094 method=Set args=["TextureImage", "@obj1071"]   # ✅
# 读回：get_Item("TextureImage") → @obj1071 即成功
```
> 纹理可用属性（get_Properties 确认）：`TextureImage`、`ImportedFrom`、`IDInImportSource`、`GpuResourceMemoryType`、`TextureMinificationFilter`、`TextureMagnificationFilter`、`TextureFormat`、`TextureWrapMode`、`TextureAnisotropyType`、`Name`。

### 六、完整流程示例（建夹→建纹理→绑图）
```python
# 前提：TextureLibrary=@obj69, adas=@obj221, ImageDirectory=@obj882, adas图=@obj891
# 1. 图片引用：green_sig_num.png = @obj1071（get_Children 遍历）
# 2. 在 adas 下创建纹理
@project.CreateProjectItem("@type:Rightware.Kanzi.Studio.PluginInterface.SingleTexture", "@string:green_sig_num", "@obj221")  # → @obj1094
# 3. 绑图
@obj1094.Set("TextureImage", "@obj1071")
# 4. 读回验证：@obj1094.get_Item("TextureImage") → @obj1071
# 5. 保存：@studio.get_Commands() → SaveProject("@project")
```
> **重名规则**（老隋强调）：同一文件夹下不能有同名纹理；重名报 `A child with the name "xxx" already exists`。不同文件夹重名不冲突。创建前可用 `GenerateUniqueChildName(name)` 拿唯一名。

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

## 四、创建材质笔刷（Material + MaterialType + MaterialBrush，参数化渐变 shader）

> **2026-08-11 完整流程实测打通**（v8）。目标：新建一个带「红→黄渐变」参数化 shader 的可复用材质刷。三层关联：`Brush → MaterialBrush.Material → Material → MaterialType`。**新建名字，不污染现有工程**（progressBar/progressBarMaterial/redYellow 都不动）。

### 4.1 定位库
```bash
kz_invoke target=@project method=get_Children       # Material Types 库 → @objMT
kz_invoke target=@project method=get_MaterialLibrary # Materials 库 → @objMatLib
kz_invoke target=@project method=get_BrushLibrary    # Brushes 库 → @objBrushLib
```

### 4.2 创建 MaterialType（参数化 shader）
```bash
# 1) 建 MaterialType（泛型 @type 用完整类型名，父 = Material Types 库）
kz_invoke target=@project method=CreateProjectItem args=["@type:Rightware.Kanzi.Studio.PluginInterface.MaterialType", "@string:kzGradientType_yy", "@objMT"]
# → @objMT2（MaterialTypePluginWrapper，自动带 1 个 Uniform binding：getProjectionCameraWorldMatrix）

# 2) 定位它的 Vertex + Fragment Shader 子项
kz_invoke target=@objMT2 method=get_Children   # → Vertex Shader = @objVS, Fragment Shader = @objFS

# 3) ⚠️⚠️ 两个着色器都要 SetText！缺一都不出渐变
#    (a) 顶点着色器：必须传 vTexCoord（kzTextureCoordinate0 → vTexCoord）！否则 UV 没值、渐变出不来
kz_invoke target=@objVS method=SetText args=["@string:precision highp float;\nattribute vec3 kzPosition;\nattribute vec2 kzTextureCoordinate0;\nuniform highp mat4 kzProjectionCameraWorldMatrix;\nvarying mediump vec2 vTexCoord;\nvoid main()\n{\n    precision mediump float;\n    vTexCoord = kzTextureCoordinate0;\n    gl_Position = kzProjectionCameraWorldMatrix * vec4(kzPosition.xyz, 1.0);\n}\n"]
#    (b) 片元着色器：precision + varying + main内precision（三处都要）
kz_invoke target=@objFS method=SetText args=["@string:precision highp float;\nvarying mediump vec2 vTexCoord;\nuniform vec4 colorStart;\nuniform vec4 colorEnd;\nvoid main()\n{\n    precision mediump float;\n    gl_FragColor = mix(colorStart, colorEnd, clamp(vTexCoord.x, 0.0, 1.0));\n}\n"]
# 读回验证：GetText（两个都读）
kz_invoke target=@objVS method=GetText
kz_invoke target=@objFS method=GetText

# 4) shader 正确 → Studio 自动重读并暴露 uniform：
kz_invoke target=@objMT2 method=Get args=["@string:Uniforms"]   # → colorStart / colorEnd 的 ShaderVariableInfo（@objCS/@objCE）
```
> 🌟 **最关键坑（老隋连续 3 次指正）**：「改 shader 后 Studio 自动重读暴露出 uniform，若没出来就是 shader 本身不对」。**片段着色器 + 顶点着色器两个都要与之前创建（如 redYellow）逐字一致**（直接 GetText redYellow 对照抄）：
> 1. **片元着色器**：文件头 `precision highp float;` + `varying mediump vec2 vTexCoord;`，**且 main 内再加 `precision mediump float;`**。缺头 → 编译失败、uniform 读不出；缺 main 内 → uniform 暴露但渲染不对。
> 2. **顶点着色器（最易漏，老隋「还有一个 .vert.glsl」指正）**：**必须传递 vTexCoord**！要有 `attribute vec2 kzTextureCoordinate0;` + `varying mediump vec2 vTexCoord;` + main 里 `vTexCoord = kzTextureCoordinate0;`。若顶点着色器没传 UV，片元里 `vTexCoord.x` 永远没值 → **uniform 暴露了、binding 也对、材质也建了，但渐变就是出不来**。
> 正确完整版（两个 shader 都要）：
> ```glsl
> // 顶点着色器 .vert.glsl
> precision highp float;
> attribute vec3 kzPosition;
> attribute vec2 kzTextureCoordinate0;
> uniform highp mat4 kzProjectionCameraWorldMatrix;
> varying mediump vec2 vTexCoord;
> void main()
> {
>     precision mediump float;
>     vTexCoord = kzTextureCoordinate0;
>     gl_Position = kzProjectionCameraWorldMatrix * vec4(kzPosition.xyz, 1.0);
> }
> // 片元着色器 .frag.glsl
> precision highp float;
> varying mediump vec2 vTexCoord;
> uniform vec4 colorStart;
> uniform vec4 colorEnd;
> void main()
> {
>     precision mediump float;
>     gl_FragColor = mix(colorStart, colorEnd, clamp(vTexCoord.x, 0.0, 1.0));
> }
> ```

### 4.3 加属性到 MaterialTypePropertyTypes（MTPT）
```bash
# 拿 MTPT（DynamicClass）
kz_get_raw_ref target=@objMT2 method=Get args=["@string:MaterialTypePropertyTypes"]   # → @objDynClass
# 把 colorStart/colorEnd 属性加进去（用已有的全局 ColorDynamicPropertyType，见下方 note）
kz_invoke target=@objDynClass method=AddDynamicPropertyType args=["@obj:<colorStart属性ref>"]
kz_invoke target=@objDynClass method=AddDynamicPropertyType args=["@obj:<colorEnd属性ref>"]
# 验证
kz_invoke target=@objDynClass method=get_PropertyTypes   # → shader.colorStart / shader.colorEnd
```
> 🌟 **坑**：`Get("MaterialTypePropertyTypes")` 返回的是**单个 DynamicClass 对象**（不是 IEnumerable），用 `kz_get_raw_ref` 拿。其方法含：`AddDynamicPropertyType` / `AddDynamicPropertyTypes` / `RemoveDynamicPropertyType` / `ClearPropertyTypes` / `get_PropertyTypes` / `AddDynamicPropertyTypesFrom` / `ContainsDynamicPropertyType`。
> **colorStart/colorEnd 属性对象**：progressBar/redYellow 的 MTPT 里已有 `shader.colorStart` / `shader.colorEnd`（**全局共享的 ColorDynamicPropertyType**，同一 ref）。可直接把这些已有属性类型 `AddDynamicPropertyType` 到新 MTPT，无需自建（不用在 MaterialType 对象上 Set colorStart，那里没这个实例属性）。

### 4.4 创建 Uniform bindings（从自身复制 + set_Code + set_Target）
> **目标**：colorStart/colorEnd 绑定到正确 Uniform。判定正确 Uniform binding：`TargetType=Uniform` + `Target=对应 ShaderVariableInfo` + `DisplayCode={./shader.colorXXX}` + `Property=null`。
```bash
# 1) 拿本 MaterialType 自带的 Uniform binding（Property=null 那个，如 getProjectionCameraWorldMatrix）
kz_invoke target=@objMT2 method=get_Bindings   # → @objSelf（code=getProjectionCameraWorldMatrix()）

# 2) 从自身复制（CreateBinding(sourceBinding) 重载，不依赖 progressBar）
kz_invoke target=@objMT2 method=CreateBinding args=["@obj:<@objSelf>"]
# → @objNew，继承 Uniform 性质（TargetType=Uniform）

# 3) 改 DisplayCode
kz_invoke target=@objNew method=set_Code args=["@string:{./shader.colorStart}"]
# colorEnd 同理：set_Code("{./shader.colorEnd}")

# 4) ⚠️必须改 Target 为对应的 ShaderVariableInfo（Uniforms 里的 colorStart/colorEnd）——复制会继承源的 Target！
kz_get_raw_ref target=@objNew method=get_WrappedItem   # → @objNewBI（BindingItem）
kz_invoke target=@objNewBI method=set_Target args=["@obj:<@objCS>"]   # colorStart 绑定 → 对应 ShaderVariableInfo
kz_invoke target=@objNewEndBI  method=set_Target args=["@obj:<@objCE>"] # colorEnd 绑定 → 对应 ShaderVariableInfo
```
> 🌟 **关键**：`CreateBinding` 复制会继承源 BindingItem 的 Target（如 getProjection 的 ShaderVariableInfo），**不 set_Target 就指错**。`set_Target` 要在 **WrappedItem（BindingItem）** 上调（不是 binding wrapper 上）。
> `CreateBinding` 有两个重载：`(Property,Enum,String)` 建普通属性绑定；`(Binding sourceBinding)` 从源绑定复制（本次用这个）。

### 4.5 创建 Material + MaterialBrush（三层关联 + 设默认色）
```bash
# 1) 创建 Material（Materials 库）
kz_invoke target=@project method=CreateProjectItem args=["@type:Rightware.Kanzi.Studio.PluginInterface.Material", "@string:kzGradientMaterial_yy", "@objMatLib"]
# → @objMat
# 关联 MaterialType
kz_invoke target=@objMat method=Set args=["MaterialType", "@objMT2"]

# 2) 创建 MaterialBrush（CreateBrush 是 @project 方法，brushType 用 @enum:MATERIAL）
kz_invoke target=@project method=CreateBrush args=["@string:kzGradientBrush_yy", "@objBrushLib", "@enum:MATERIAL"]
# → @objBrush
# 关联 Material
kz_invoke target=@objBrush method=Set args=["MaterialBrush.Material", "@objMat"]

# 3) ⚠️设 shader 默认色：在 Material/Brush 上 Set("shader.colorStart")，不是 MaterialType 上（MaterialType 无此实例属性）！
kz_invoke target=@objMat method=Set args=["shader.colorStart", "@color:#FFFF0000"]   # 红
kz_invoke target=@objMat method=Set args=["shader.colorEnd",   "@color:#FFFFFF00"]   # 黄
# (Brush @objBrush 上 Set 同样生效)
```

### 4.6 完整链条验证 + 保存
```bash
# MaterialType MTPT 属性
kz_invoke target=@objDynClass method=get_PropertyTypes   # shader.colorStart / shader.colorEnd
# Material → MaterialType
kz_invoke target=@objMat method=Get args=["@string:MaterialType"]            # → @objMT2
# Brush → Material
kz_invoke target=@objBrush method=Get args=["@string:MaterialBrush.Material"] # → 关联 Material
# 颜色读回（Color 对象 ref → ToString → #AARRGGBB）
kz_invoke target=@objMat method=Get args=["@string:shader.colorStart"]  # → Color ref
kz_invoke target=<ColorRef> method=ToString                                # → #FFFF0000（红）
# 保存（GeneratedCommandInvoker，铁律）
kz_invoke target=@studio method=get_Commands    # → @objInvoker
kz_invoke target=@objInvoker method=SaveProject args=["@project"]
```

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
