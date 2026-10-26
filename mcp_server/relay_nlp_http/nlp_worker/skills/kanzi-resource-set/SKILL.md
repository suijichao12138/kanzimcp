---
name: kanzi-resource-set
description: Kanzi 设置节点的资源引用：前景色/背景色 ForegroundBrush/BackgroundBrush（颜色刷）、字体 Node.FontFamily、状态机 Node.StateManager。引用写法：直接引用素材对象用 @obj；引用 Resource 条目用 KzResourceID。创建资源见 kanzi-resource-create；创建素材见 kanzi-asset-create。
---

# 设置资源引用（ResourceReference 属性）

> 把**已存在的素材/资源**（颜色刷/字体/状态机）赋给节点属性。引用有两种写法，按你引用的对象类型选：
> - **直接引用素材/资源对象**（Brushes/Font Families 库里的对象）→ 用 `@obj<引用>`
> - **引用 Resource 条目**（ResourceDictionary 里注册的条目）→ 用 `KzResourceID:资源名`
>
> **创建** Resource 条目 → `kanzi-resource-create`；**创建素材**（颜色刷/纹理/字体）→ `kanzi-asset-create`。
> **设置图片**（Image2D.Image / 九宫格）→ `kanzi-prop-set`（属性设置里的图片章节）。

## 🌟 颜色规则（重要）

> **Text Block 2D 显示文本的颜色 → 用 `Node2D.ForegroundBrush` 属性设置**（颜色刷）。
> **`Font Color` 只能给 Text Block 3D 文本设置颜色，不能设置 Text Block 2D 的颜色**。给 TextBlock2D 设 Font Color 无效。

## 🌟 引用写法（按引用的对象类型选，别混）

| 你引用的是… | 写法 | 说明 |
|---|---|---|
| **素材/资源对象**（Brushes/Font Families 库里的对象） | `@obj<引用>` | 先 get_Children 拿到对象的 @obj 引用 |
| **Resource 条目**（ResourceDictionary 里的条目） | `KzResourceID:资源名` | resourceID 名标识 |

> ⚠️ 前缀拼写：是 `KzResourceID:`，不是 `resourceID:` / `resource:`（少 `Kz` 会失败，这个坑实测踩了很久）。

## ResourceReference 属性设值规则

| 写法 | Foreground/Bg Brush | FontFamily / StateManager |
|------|:---:|:---:|
| **`@obj资源对象引用`**（直接引用素材对象） | ✅（最稳） | ✅（最稳） |
| **`KzResourceID:资源名`**（引用 Resource 条目） | ✅ | ✅ |
| `resourceID:xxx`（无Kz） | ❌ | ❌ |
| `@brush:` | ❌ | ❌ |

> ⚠️ **读回 Null 可能是时序延迟**：设完立即读回可能显示 `< Null >`，延迟约 1 秒再读就稳定为资源名。别被瞬时 Null 误导判定失败。

## 通用设置流程（三步）

```python
# 1. AddProperty（ResourceReference 属性需先加）
mcp kz_invoke target=@节点 method=AddProperty args=["Node2D.ForegroundBrush"]
# 2. 定位资源拿 @obj 引用（Brushes/Font Families 库 get_Children）
#    颜色刷：Brushes 库 get_Children → Color Brush_FFFFFF = @obj5736
#    字体：  Font Families 文件夹 → get_Children → MiSans-Medium = @obj308
# 3. 设置（两种写法，按引用对象类型选）
mcp kz_invoke target=@节点 method=set_Item args=["Node2D.ForegroundBrush","@obj5736"]          # 写法A：@obj 直接引用素材对象（最稳）
mcp kz_invoke target=@节点 method=set_Item args=["Node2D.ForegroundBrush","KzResourceID:FFFFFF"] # 写法B：KzResourceID 引用 Resource 条目
```

## 各属性速查

| 属性 | 类型 | 说明 |
|------|------|------|
| `Node2D.ForegroundBrush` | ResourceReference | 文本/节点前景色（2D 文本颜色用它！）|
| `Node2D.BackgroundBrush` | ResourceReference | 节点背景色（不是 Background/BackgroundColor/BackdropBrush，那些都不存在）|
| `Node.FontFamily` | ResourceReference | 文本字体（Font Families 库）|
| `Node.StateManager` | ResourceReference | 状态机引用（State Managers 库）|

## 定位资源（在工程里找 brush/字体）

```python
# 颜色刷：Brushes 库
mcp kz_invoke target=@project method=get_Children   # 找 "Brushes" 行 → @objXX
mcp kz_invoke target=@objXX method=get_Children     # → Color Brush_FFFFFF = @obj5736
# 字体：Font Families 文件夹
mcp kz_invoke target=@project method=get_Children   # 找 "Font Families" 行 → @objXX
mcp kz_invoke target=@objXX method=get_Children     # → MiSans-Medium = @obj308
```

> 创建颜色刷/纹理/字体等素材 → `kanzi-asset-create`。
> 创建 Resource 资源条目（ResourceDictionary）→ `kanzi-resource-create`。
