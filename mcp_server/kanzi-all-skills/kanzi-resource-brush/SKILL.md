---
name: kanzi-resource-brush
description: Kanzi 创建颜色笔刷（Color Brush）：@project.CreateBrush + @color:，两步流程，关键坑。
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
