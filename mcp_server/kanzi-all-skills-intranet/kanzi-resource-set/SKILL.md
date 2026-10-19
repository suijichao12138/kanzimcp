---
name: kanzi-resource-set
description: Kanzi 设置资源引用（把已创建的 resource 赋给节点的 ResourceReference 属性）：前景色/背景色 ForegroundBrush/BackgroundBrush、图片 Image2D.Image、九宫格图块、字体 Node.FontFamily、状态机 Node.StateManager。含 KzResourceID/@obj 设值规则。不包含资源创建（见 kanzi-resource-create/brush/texture/font）。
---

# 设置资源引用（ResourceReference 属性）

> 把**已存在的资源**（颜色刷/图片/字体/状态机）赋给节点属性。值用 `@obj<引用>` 或 `KzResourceID:资源名`。
> **创建**资源 → `kanzi-resource-create` / `kanzi-resource-brush` / `kanzi-resource-texture` / `kanzi-resource-font`。

## 🌟 颜色规则（重要）

> **Text Block 2D 显示文本的颜色 → 用 `Node2D.ForegroundBrush` 属性设置**（颜色刷）。
> **`Font Color` 只能给 Text Block 3D 文本设置颜色，不能设置 Text Block 2D 的颜色**。给 TextBlock2D 设 Font Color 无效。

## 🌟 最重要的规则（老隋强调，务必记住）

> **无论你看到/想用的是 `resource:xxx`、`KzResourceID:xxx` 还是 `resourceID:xxx`，实际设置时一律写成 `KzResourceID:xxx`。**
> ⚠️ 不要写 `resourceID:xxx`——少 `Kz` 前缀会失败！这个坑实测踩了很久。

## ResourceReference 属性设值规则

| 写法 | Foreground/Bg Brush | Image / 九宫格图块 |
|------|:---:|:---:|
| **`KzResourceID:资源名`** | ✅ | ✅ |
| **`@obj资源对象引用`** | ✅ | ✅（最稳） |
| **完整路径** `Textures/adas/xxx` | ❌ | ✅ |
| `resourceID:xxx`（无Kz） | ❌ | ❌ |
| `@brush:`/`@image:`/`@texture:` | ❌ | ❌ |
| 相对路径 `adas/xxx` | ❌ | ❌（Null） |

> ⚠️ **读回 Null 可能是时序延迟**：设完立即读回可能显示 `< Null >`，延迟约 1 秒再读就稳定为资源名。别被瞬时 Null 误导判定失败。

## 通用设置流程（三步）

```python
# 1. AddProperty（ResourceReference 属性需先加）
mcp kz_invoke target=@节点 method=AddProperty args=["Node2D.ForegroundBrush"]
# 2. 定位资源拿 @obj 引用（Brushes/Textures/Font Families 库 get_Children）
#    颜色刷：Brushes 库 get_Children → Color Brush_FFFFFF = @obj5736
#    图片：  Textures 库 → 子库 → get_Children → green_sig_num = @obj5831
#    字体：  Font Families 文件夹 → get_Children → MiSans-Medium = @obj308
# 3. 设置（两种等价写法）
mcp kz_invoke target=@节点 method=set_Item args=["Node2D.ForegroundBrush","@obj5736"]          # 写法A：@obj 引用（最稳）
mcp kz_invoke target=@节点 method=set_Item args=["Node2D.ForegroundBrush","KzResourceID:FFFFFF"] # 写法B：资源名
```

## 各属性速查

| 属性 | 类型 | 说明 |
|------|------|------|
| `Node2D.ForegroundBrush` | ResourceReference | 文本/节点前景色（2D 文本颜色用它！）|
| `Node2D.BackgroundBrush` | ResourceReference | 节点背景色（不是 Background/BackgroundColor/BackdropBrush，那些不存在）|
| `Image2D.Image` | ResourceReference | Image2D 节点的图片 |
| `NinePatchImage2D.ImageTopLeft/Top/TopRight/Left/Center/Right/BottomLeft/Bottom/BottomRight` | ResourceReference | 九宫格 9 块图（NinePatchImage2D 节点自带，创建即带）|
| `Node.FontFamily` | ResourceReference | 文本字体（Font Families 库）|
| `Node.StateManager` | ResourceReference | 状态机引用（State Managers 库）|

## 定位资源（在工程里找 brush/图片/字体）

```python
# 颜色刷：Brushes 库
mcp kz_invoke target=@project method=get_Children   # 找 "Brushes" 行 → @objXX
mcp kz_invoke target=@objXX method=get_Children     # → Color Brush_FFFFFF = @obj5736
# 图片：Textures 库 → 子库
mcp kz_invoke target=@project method=get_Children   # 找 "Textures" 行 → @objXX
mcp kz_invoke target=@objXX method=get_Children     # 子库 → @objYY
mcp kz_invoke target=@objYY method=get_Children     # → green_sig_num = @obj5831
# 字体：Font Families 文件夹
mcp kz_invoke target=@project method=get_Children   # 找 "Font Families" 行 → @objXX
mcp kz_invoke target=@objXX method=get_Children     # → MiSans-Medium = @obj308
```

> 创建颜色刷/纹理/字体 → `kanzi-resource-brush` / `kanzi-resource-texture` / `kanzi-resource-font`。
> 创建 Resource 资源条目（ResourceDictionary）→ `kanzi-resource-create`。
