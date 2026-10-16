---
name: kanzi-resource-texture
description: Kanzi 创建纹理（Texture/SingleTexture）：完整类型名、文件夹/根目录创建、建子库、获取/绑定图片。
---
## 🚫 命名铁律（创建前必读）

> 创建任何东西（节点/资源/动画/别名/条目）时，**名字禁止特殊字符**：`\` `/` `|` `.` `:` `*` `?` `"` `'` `<` `>` 空格。
> **允许中文，推荐英文**（中文名可用，但英文更稳妥，避免跨工具编码问题）。
> 不要以数字开头（部分 API 限制）。
> 错误：`text/header` `bg.1` `a|b` `C:\temp` `new node`；正确：`text_header` `bg_1` `标题文本` `header-text`。

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
