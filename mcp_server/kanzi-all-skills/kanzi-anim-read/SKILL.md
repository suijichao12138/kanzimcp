---
name: kanzi-anim-read
description: Kanzi 动画数据读取：定位动画库、读动画数据库/动画项属性、读 target property、动画项/动画组关键字段。创建动画见 kanzi-anim-create。
---

# 读动画数据

## 定位两个动画库

```python
# Animation Data 库 = project.get_AnimationLibrary()
mcp kz_invoke target=@project method=get_AnimationLibrary
# 返回库内全部动画项（AnimationPluginWrapper）：实验工程 24 个，如 Internal.ctrlState / Internal.stateAnimationOpacity

# Animation Clips 库 = project.get_Children() 里 name=="Animation Clips"
# 返回动画组（AnimationClipPluginWrapper）：实验工程 17 个，如 01circle_innerRadius
```

## ⚠️ 函数名大小写铁律（2026-08-08 老隋指正，最关键！）

bridge 的 `kz_invoke` **只认大写 C# 方法名**。写错大小写 = 找不到方法：

| 想表达 | 正确写法 | 小写（❌ 找不到） |
|---|---|---|
| 读属性值 | **`Get(属性名)`** | `get("")` ❌ |
| 属性索引器 | **`get_Item(属性名)`** | `get_item("")` ❌ |
| 列出子项 | **`get_Items()`**（无参） | `get_items()` ❌ |

- `Get` / `GetItem` / `GetItems`（首字母大写的方法）中**只有 `Get` 存在**；`GetItem`/`GetItems` 不存在。
- 属性 getter 是 `get_` 前缀（小写）+ 首字母大写属性名（`get_Name`/`get_Item`/`get_Items`）。
- **实测铁证**：`Get("Name")` ✅ 返回动画名；`get`/`get_item`/`get_items`/`GetItem`/`GetItems` 全部 ❌ 找不到方法。

## 🆕 读动画数据库 / 动画项属性（2026-08-08 实测）

### Animation Data 库对象（AnimationLibraryPluginWrapper，= `@project.get_AnimationLibrary()`）

```python
mcp kz_invoke target=@project method=get_AnimationLibrary   # 返回库对象（如 @obj44）
```

| 函数 | 参数 | 用途 | 实测 |
|---|---|---|---|
| `get_Children()` / `get_Items()` | 无参 | 列出库内全部动画项 | ✅ |
| `get_Name()` / `get_Path()` | 无参 | 库名/路径（"Animation Data"） | ✅ |
| `get_Parent()` / `get_Project()` | 无参 | 父对象 @project | ✅ |
| `get_Properties()` / `get_PropertyTypes()` | 无参 | 属性类型集合 | ✅ |
| **`Get(属性名)`** | 字符串 | **按属性名读属性值** | ✅（`Get("Name")`→"Animation Data"） |
| `get_Item(属性名)` | 字符串 | 属性索引器（同 Get 语义） | ✅ |
| `HasProperty(属性名)` | 字符串 | 判断属性是否存在 | ✅ |
| `GetAddableProperties()` | 无参 | 可添加的属性类型列表 | ✅ |
| `AddProperty(...)` / `RemoveProperty(...)` | PropertyType | 加/删属性 | ✅ |

> ⚠️ `get_Item`/`Get` 是**属性索引器**（按属性名取属性值），**不能**传子项名/整数索引（报 not found / 参数不匹配）。列子项要用 `get_Children()`/`get_Items()`。

### 读动画项（AnimationPluginWrapper）的属性 —— **`Get(属性名)`**

```python
mcp kz_invoke target=/Animation Data/Animation_test method=Get args=["属性名"]
```

Animation_test 上 `Get(属性名)` **实测能读到的属性**：
| 属性名 | 返回 |
|---|---|
| `Name` | ✅ 动画名（如 "Animation_test"） |
| `AnimationTargetPropertyName` | ✅ target 属性类型包装（如 IntPropertyTypePluginWrapper，**见下节**） |
| `ImportedFrom` / `IDInImportSource` | ✅ 调用成功（多为空值） |
| `AnimationDataChildReferences` | ✅（动画**组**上有内容；动画**项**上为空） |

> ⚠️ `Get("Internal.ctrlState")` 在动画项上会报 not found——`Internal.ctrlState` 是 target property，**不应**直接当动画项属性 Get，要走下节的 target property 路径。

## 🆕 读 target property（动画的目标属性）—— 关键路径（2026-08-08 老隋指正）

**`Internal.ctrlState` 是 Animation_test 的 target property 属性值**，正确读取路径：

```python
# 1) 拿到 target 属性类型包装
mcp kz_invoke target=/Animation Data/Animation_test method=Get args=["AnimationTargetPropertyName"]
# → ref_id = @obj61, type = IntPropertyTypePluginWrapper, name = Internal.ctrlState

# 2) 在包装上用 get_ 前缀读名字（不是 Get！包装对象上 Get 找不到）
mcp kz_invoke target=@obj61 method=get_Name        # → ✅ Internal.ctrlState
mcp kz_invoke target=@obj61 method=get_DisplayName # → ✅ Internal.ctrlState-内部使用
```

- **target 属性类型**由 `AnimationTargetPropertyName` 返回：Int 型 → `IntPropertyTypePluginWrapper`，Float 型 → `FloatPropertyTypePluginWrapper`（不同动画 target 不同类型）。
- 包装对象上读名字用 **`get_Name`/`get_DisplayName`**（在包装上 `Get` / `GetValue` / `get_Value` 都找不到）。
- target 属性名 = `<对象>.<属性>` 形式（如 `Internal.ctrlState`），DisplayName 常带 `-内部使用` 后缀。

### `AnimationTargetPropertyAttributeEnum`（实测枚举值）

| 值 | 含义 |
|----|------|
| 0 | TRANSLATION_X（⚠️ 不是 WHOLE_PROPERTY！） |
| ... | ... |
| **9** | **WHOLE_PROPERTY** |

> ⚠️ 教训（MEMORY.md）：曾脑补 0=WHOLE_PROPERTY，实际 **0=TRANSLATION_X，WHOLE_PROPERTY=9**。枚举值必须查源，别猜。完整顺序：NONE/TRANSLATION_XYZ/SCALE_XYZ/ROTATION_ZYX/WHOLE_PROPERTY/COLOR_RGBA/VECTOR_XYZW/ROTATION。

## 动画项（Animation）关键字段

```python
# get_WrappedItem → DynamicProperty 列表里能看到：
mcp kz_invoke target=@动画项 method=get_WrappedItem

# 读属性统一用 Get(属性名)（见上），或 get_Item(属性名)。
# Target 相关：AnimationTargetPropertyName（拿 target 包装，见上节）/ AnimationTargetPropertyAttribute（WHOLE_PROPERTY 枚举）
# AnimationOriginalTargetPropertyAttribute
# Name / CreationTime / ImportedFrom 等通用字段
```

> ⚠️ **动画项没有** keyframe/segment/track 属性可 get/set_Item 直接访问——关键帧数据在底层 DynamicProperty 里，public 接口摸不到。
> ⚠️ **关键帧读取边界（2026-08-08 实测确认）**：`Get` 在动画项上能读的属性**只有** Name / AnimationTargetPropertyName / ImportedFrom / IDInImportSource / AnimationDataChildReferences；Keyframes / TargetProperty / Value / Data / StartTime / EndTime / Duration / Interpolation **全部属性名不存在**。关键帧数据**无法**通过插件读，只能 Animation Clip Editor(GUI) 看。

### `AnimationTargetPropertyAttributeEnum`（实测枚举值）

| 值 | 含义 |
|----|------|
| 0 | TRANSLATION_X（⚠️ 不是 WHOLE_PROPERTY！） |
| ... | ... |
| **9** | **WHOLE_PROPERTY** |

> ⚠️ 教训（MEMORY.md）：曾脑补 0=WHOLE_PROPERTY，实际 **0=TRANSLATION_X，WHOLE_PROPERTY=9**。枚举值必须查源，别猜。完整顺序：NONE/TRANSLATION_XYZ/SCALE_XYZ/ROTATION_ZYX/WHOLE_PROPERTY/COLOR_RGBA/VECTOR_XYZW/ROTATION。

## 动画组（AnimationClip）字段

```python
mcp kz_invoke target=@动画组 method=get_WrappedItem
# AnimationClipProperties:
#   AnimationClipStartTime / AnimationClipEndTime / AutoSizeToContent / EditRootNode
#   AnimationDataChildReferences → 被引用的 AnimationPluginWrapper 列表（"Clip 包含动画"的机制）
```

> 实测现有动画组 `01circle_innerRadius`：引用方式 = `AnimationDataChildReferences` 直接指向 `InnerRadius_1`（无 childclip），`AnimationClipStartTime=0` / `EndTime=2.5`。

