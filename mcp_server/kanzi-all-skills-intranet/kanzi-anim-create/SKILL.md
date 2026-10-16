---
name: kanzi-anim-create
description: Kanzi 创建动画：动画数据库/动画项读取、创建动画对象（裸类型名+完整路径）、完整流程+命名规则、@anim: 子片段引用。
---
## 🚫 命名铁律（创建前必读）

> 创建任何东西（节点/资源/动画/别名/条目）时，**名字禁止特殊字符**：`\` `/` `|` `.` `:` `*` `?` `"` `'` `<` `>` 空格。
> **允许中文，推荐英文**（中文名可用，但英文更稳妥，避免跨工具编码问题）。
> 不要以数字开头（部分 API 限制）。
> 错误：`text/header` `bg.1` `a|b` `C:\temp` `new node`；正确：`text_header` `bg_1` `标题文本` `header-text`。

## 核心概念：Kanzi 动画分两层（2026-08-06 老隋指正）

- **Animation Data**：存放单一关键帧动画。例：`Internal.ctrlState`、`Internal.stateAnimationOpacity`。
- **Animation Clips**：存放动画组（AnimationClip 容器），可引用多个 Animation Data 下的动画组合成复杂动画。

> ⚠️ 曾经误把两层混为一谈。动画数据是"关键帧"，动画组是"容器/编排"，两者职责不同。

## 接入方式（本机中继桥）

通过中继 WebSocket 连接 Kanzi Studio 插件。客户端 `kanzi-mcp-client.mjs`（本 skill 目录上级即 workspace 根目录）。

- **中继**：`ws://123.57.85.81:58080`，channel = `openclaw-main`
- **调用**：`node kanzi-mcp-client.mjs '<tools/call 参数 JSON>'`
- **参数格式**：`{"name":"kz_invoke","arguments":{"target":"<ref或路径>","method":"<方法>","args":[...]}}`
- 返回 `ref_id = @objN` 自动进对象缓存，`@objN` 可作后续 target（重启 Studio 后编号失效，须重新枚举）
- 示例中的 `mcp kz_invoke target=X method=Y args=[...]` 等价于 `node kanzi-mcp-client.mjs '{"name":"kz_invoke","arguments":{"target":"X","method":"Y","args":[...]}}'
- 调用统一走 `kz_invoke`，参数遵循 v4 标识符（@type/@int/@string/@enum/@obj/@anim 等）。

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

## 创建动画对象（⭐ 2026-08-08 复测：正确姿势 = 裸类型名 + 完整路径 parent）

**关键结论**：创建动画/动画组/子片段**全部能成功**。但参数有讲究：

| 写法 | 结果 |
|---|---|
| `@type:AnimationClip` 前缀 | ❌ 失败（当前 bridge 版本不识别 `@type:` 前缀，被当字面字符串） |
| 裸字符串 `"AnimationClip"` + `@obj` parent | ⚠️ **不稳定**（时好时坏，跟 ObjectRegistry 状态有关） |
| **裸字符串 + 完整路径 parent** | ✅ **稳定成功（推荐）** |

```python
# ✅ 建动画数据项 (Animation Data 库下) —— 完整路径 parent + 裸类型
mcp kz_invoke target=@project method=CreateProjectItem args=["Animation","__TEST_ANIM_OP_","/Animation Data"]
# ✅ 返回 AnimationPluginWrapper

# ✅ 建动画组 (Animation Clips 库下)
mcp kz_invoke target=@project method=CreateProjectItem args=["AnimationClip","__TEST_CLIP_OP_","/Animation Clips"]
# ✅ 返回 AnimationClipPluginWrapper

# ✅ 建子片段 (动画组下) —— 关键引用通路
mcp kz_invoke target=@project method=CreateProjectItem args=["AnimationChildClip","__TEST_CC_B_","/Animation Clips/<组名>"]
# ✅ 返回 AnimationChildClipPluginWrapper
```

**实测验证（2026-08-08）**：三种类型全部创建成功并确认返回正确的 PluginWrapper 类型。
⚠️ parent 必须用**完整路径字符串**（`/Animation Data`、`/Animation Clips`、`/Animation Clips/<组名>`），用 `@obj` 引用编号会漂移导致时好时坏。skill 早期示例里的 `@type:`/`@obj:` 前缀写法是误导，当前版本不适用。

**清理测试残留**：库项可直接 `Delete`（不走节点树）：
```python
mcp kz_invoke target=@动画项ref method=Delete args=[]
# ✅ 返回 True；Animation Data / Animation Clips 库清理后回 24 / 17 项
```

## ⭐ 关键突破：子片段引用动画（`@anim:` 资源名）

```python
# 让 AnimationChildClip 指向某个动画项
mcp kz_invoke target=@动画ChildClip method=set_Item args=["AnimationChildClipTargetItem","@anim:InnerRadius_1"]
# ✅ 实测成功 —— ChildClip 指向动画
```

**为什么 `@anim:` 能成功、其他方式失败：**
- `@anim:名称` 是 Kanzi 内部资源引用格式；bridge 原样透传字符串，Studio 侧自动解析成引用对象。
- 之前试过 `@obj3` / 节点路径 / 纯数字 全部报 "cannot be converted to studio internal property value"——因为那是传对象引用/裸值，不是资源引用。

## ⭐ 创建动画完整流程 + 命名规则（⭐ 2026-08-11 老隋定稿，重建动画/建新动画必看）

> 老隋要求：**动画名用全名**（带 `Internal.` 前缀），**新建前必须先获取所有动画名**，存在同名就在后边加 `_1`/`_2` 依次叠加。

### 命名规则（铁律）
1. **动画名 = 目标属性的全名**（带 `Internal.` 前缀）。例：目标 `Internal.ctrlState` → 动画名 `Internal.ctrlState`；目标 `Internal.stateAnimationOpacity` → 动画名 `Internal.stateAnimationOpacity`。
2. **新建前先获取所有动画名**（Animation Data 库 `get_Children()`/`get_Items()`）。
3. 若存在**同名**，后边加 **`_1`**；`_1` 也被占则加 **`_2`**……依次递增叠加（`Internal.ctrlState` 被占 → `Internal.ctrlState_1` → 也被占 → `Internal.ctrlState_2`）。

> ⚠️ 2026-08-11 教训：新建动画报「找不到与参数 (String,String,AnimationLibraryPluginWrapper) 匹配的 CreateProjectItem」**多半是同名冲突**的误导性报错（同名时 Studio 抛异常，bridge 吞成"参数不匹配"）。**先怀疑重名，去获取当前动画名核对，别当成参数格式问题。**

### 完整流程（重建整个动画：2 个动画 + 1 个动画组 Test）

```python
# 0) 先获取 Animation Data / Animation Clips 库 ref（每次连接现取，ref 会漂移）
animLib = @project.get_AnimationLibrary()          # Animation Data 库
clipsLib = @project.get_Children()里 name=="Animation Clips" 的项  # Animation Clips 库

# 1) 列出所有动画名，按命名规则算出不冲突的新名（同名加 _1/_2）
mcp kz_invoke target=@animLib method=get_Children   # 返回全部动画名

# 2) 创建动画（parent 用完整路径字符串，稳定）
mcp kz_invoke target=@project method=CreateProjectItem args=["Animation","Internal.ctrlState_2","/Animation Data"]
mcp kz_invoke target=@project method=CreateProjectItem args=["Animation","Internal.stateAnimationOpacity_1","/Animation Data"]
# ✅ 返回 AnimationPluginWrapper

# 3) 给每个动画设 target property（用现存真动画的 target 包装对象引用 @objN）
#    从 @project 现存同名真动画 Internal.ctrlState 的 AnimationTargetPropertyName 拿 IntPropertyTypePluginWrapper
mcp kz_invoke target=@新动画 method=set_Item args=["AnimationTargetPropertyName","@obj包装ref"]   # 注意 ref 已含 @，不要再拼 @

# 4) 加关键帧（自带 kz_modify_animation 工具）
mcp kz_modify_animation { animation:"@新动画ref", action:"add", keyframes:[{time:0,value:0},{time:1,value:20},{time:2,value:0}] }

# 5) 创建 Animation Clip 动画组
mcp kz_invoke target=@project method=CreateProjectItem args=["AnimationClip","Test","/Animation Clips"]

# 6) 让动画组引用动画 —— 用 GeneratedCommandInvoker（命令执行器）的 ReparentProjectItem
cmds = @studio.get_Commands()                      # → GeneratedCommandInvoker
mcp kz_invoke target=@cmds method=ReparentProjectItem args=["Animation Data/Internal.ctrlState_2","Animation Clips/Test"]
mcp kz_invoke target=@cmds method=ReparentProjectItem args=["Animation Data/Internal.stateAnimationOpacity_1","Animation Clips/Test"]

# 7) 验证引用
mcp kz_invoke target=@Test组 method=get_Item args=["AnimationDataChildReferences"]  # → 返回引用的动画列表
```

### 关键避坑（2026-08-11 实测）
- **ReparentProjectItem 的宿主 = GeneratedCommandInvoker**（`@studio.get_Commands()`），不是 @project/@projectItem/库对象！在错误宿主上会报「找不到方法 'ReparentProjectItem'」。（这条 kanzi-save-export 早记过"必须用 GeneratedCommandInvoker"——先查 skill，别乱试宿主。）
- **CreateProjectItem parent**：用**完整路径字符串** `/Animation Data`。⚠️ 2026-08-11 实测：库对象已注册后，`/Animation Data` 会被 GetNodeByPath 解析成库对象 → 报参数不匹配（时好时坏）；此时可改用**库对象引用 @objN** 当 parent（实测稳定）。总之路径字符串失败就换 @obj parent，不要改代码。
- **set_Item 传对象引用**：ref 本身已含 `@`（如 `@obj86`），不要再拼 `@`（否则 `@@obj86` 双前缀解析失败，target 设不上）。
- **target 默认落在 Node3D.LayoutTransformation**，不会自动关联到 Internal.*（除非恰好命名匹配）；必须用现存真动画的 target 包装对象引用 set_Item。
- **动画组 Reparent 后不要用 get_Children 验证**（引用不在 children 里），用 `get_Item("AnimationDataChildReferences")`。
