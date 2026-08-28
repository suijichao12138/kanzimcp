---
name: kanzi-animation
description: Kanzi Studio 动画创建与配置。Animation Data（单一关键帧动画）/ Animation Clips（动画组）两层结构、动画库定位（get_AnimationLibrary / Animation Clips 库）、动画项与动画组字段、Timeline Sequences 库的 TimelineSequence/TimelineEntry（关键帧！）、AnimationChildClip 子片段引用（@anim: 资源名）、AnimationPlayer 动画播放器的创建与 Timeline 关联（在节点上建播放器、指向 Animation Clip）、用 DispatchMessageAction 控制动画启停（Play/Stop 消息，Trigger 里追加动作）、当前能力边界（动画组引用动画 AnimationDataChildReferences 现可通过 ReparentProjectItem 完整路径实现）。
---

# Kanzi 动画

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



## 核心概念：Kanzi 动画分两层（2026-08-06 老隋指正）

- **Animation Data**：存放单一关键帧动画。例：`Internal.ctrlState`、`Internal.stateAnimationOpacity`。
- **Animation Clips**：存放动画组（AnimationClip 容器），可引用多个 Animation Data 下的动画组合成复杂动画。

> ⚠️ 曾经误把两层混为一谈。动画数据是"关键帧"，动画组是"容器/编排"，两者职责不同。

## 接入方式（内网 HTTP MCP）

通过内网 HTTP MCP server（`relay_nlp_http/kz_mcp_http.py`）连接 Kanzi Studio 插件，直接调用 MCP 工具，无需本地客户端脚本。

- **HTTP MCP**：`http://10.10.118.152:9001/mcp`（请求头 `X-Kanzi-User: <用户名>`，白名单见 users.json，如 `suijichao`）
- **中继通道**：`ws://10.10.118.152:58080/<用户名>`（relay_multi 监听 58080，路径决定连哪台 Kanzi，须与 kz_mcp_http.py 一致）
- **调用**：直接调用 MCP 工具 `kz_invoke` 等，参数 `{"target":..., "method":..., "args":[...]}`
- **参数格式**：`{"name":"kz_invoke","arguments":{"target":"<ref或路径>","method":"<方法>","args":[...]}}`
- 返回 `ref_id = @objN` 自动进对象缓存，`@objN` 可作后续 target（重启 Studio 后编号失效，须重新枚举）
- 示例中的 `mcp kz_invoke target=X method=Y args=[...]` 等价于直接调用 MCP 工具 `kz_invoke`（参数 `{"target":"X","method":"Y","args":[...]}`）
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

## ⭐ AnimationPlayer 动画播放器（创建 + 关联动画，2026-08-07 实测打通）

### 1. 找到 AnimationPlayer 组件类型
在 **NodeComponentTypeLibrary.get_Items()** 枚举（不是 GetTreeItemsAsList）：
```python
mcp kz_invoke target=@NodeComponentTypes库 method=get_Items
# 实测含: @obj357 Kanzi.AnimationPlayer  ← 标准动画播放器
#         @obj369 Kanzi.PropertyDrivenAnimationPlayer  ← 属性驱动播放器
```

### 2. 在目标节点上创建 AnimationPlayer 组件
warning 节点有 `CreateNodeComponent(String, NodeComponentType)` 方法：
```python
mcp kz_invoke target=/Screens/.../warning method=CreateNodeComponent args=["AnimationPlayer","@obj357"]
# ✅ 成功, 返回 NodeComponentPluginWrapper, 自动命名 AnimationPlayer
```
⚠️ **Node component 库定位**：`@project.get_Children()` 里 name=="NodeComponentTypes" 的那个；库也有 `get_Items()`（同 get_Children）。引用号每次连接重分配。

### 3. AnimationPlayer 属性槽位（get_Item 读 / set_Item 写）
| 槽位名 | 类型 | 默认 | 说明 |
|---|---|---|---|
| `AnimationPlayer.Timeline` | ResourceReference`1 | 空 | **要播放的动画时序（关键）** |
| `AnimationPlayer.AutoplayEnabled` | Bool | False | 是否自动播放 |
| `AnimationPlayer.RelativePlayback` | Bool | False | 相对播放 |
| `AnimationPlayer.RestoreOriginalValuesAfterPlayback` | Bool | False | 播后还原 |
| `AnimationPlayer.PlaybackMode` | Enum | NORMAL | NORMAL/REVERSE/PING_PONG |
| `AnimationPlayer.DurationScale` | Float | 1 | 播放时长倍率 |
| `AnimationPlayer.RepeatCount` | Int | 1 | 循环次数 |

### 4. 让播放器使用指定的 Animation Clip（Timeline 关联）
```python
# clip = 目标动画组的引用（Animation Clips 库里枚举得到，如 "Animation Clip 1HZ"=@obj157）
# 直接用对象引用传参数即可（不需要 @anim 前缀）
mcp kz_invoke target=@播放器 method=set_Item args=["AnimationPlayer.Timeline","@obj157"]
# ✅ 实测成功

# 验证引用指向: 读回 Timeline 引用对象的 ToString()
mcp kz_invoke target=@播放器 method=get_Item args=["AnimationPlayer.Timeline"]
#   拿到 ResourceReference 引用(如 @obj3870)后:
mcp kz_invoke target=@obj3870 method=ToString
#   返回 "Animation Clip 1HZ"  →  确认正确指向目标动画组
```

**✨ 关键验证方法**：ResourceReference 没有 get_Target/get_ReferencedItem，用 `ToString()` 确认指向（返回被引用资源的名称）。

### 5. 播放行为参数（如需控制播放方式）
- **自动循环播放**（如 1HZ 闪烁）：`AutoplayEnabled=True` + `RepeatCount`（无限循环 Kanzi 常用很大数或特定枚举）。
- **由触发器/状态控制播一次**：保持 `AutoplayEnabled=False`，用 MessageTrigger 发 `AnimationPlayer.Play` 消息启播（见下）。
- 当前工程无现成 AnimationPlayer 实例可参照（2026-08-07 实测确认）。

### 6. 循环播放 + 倍速（在 Play action 的消息参数里配，2026-08-07 实测）
⚠️ **正确位置**：不要在 AnimationPlayer 组件上设！要在 **DispatchMessageAction(Play) 的消息参数 `AnimationPlayer.PlayMessageArguments.*`** 里设（UI 上就是那个 action 的属性面板）。组件属性是默认播放配置，action 消息参数才是本次 Play 的具体行为。
```python
# Play action (DispatchMessageAction, MessageType=Play) 的槽位:
#   @objXXX AnimationPlayer.PlayMessageArguments.PlaybackMode
#   @objXXX AnimationPlayer.PlayMessageArguments.DurationScale
#   @objXXX AnimationPlayer.PlayMessageArguments.RepeatCount

# 3倍速 = DurationScale
mcp kz_invoke target=@PlayAction method=set_Item args=["AnimationPlayer.PlayMessageArguments.DurationScale","@float:3"]

# 循环(Infinite) = RepeatCount 设 0  (UI 勾选 Infinite 即此值; ⚠️ Kanzi不允许<0, 0才是Infinite, 不是-1!)
mcp kz_invoke target=@PlayAction method=set_Item args=["AnimationPlayer.PlayMessageArguments.RepeatCount","0"]

# PlaybackMode: NORMAL(正向)/REVERSE(反向)/PING_PONG(往返)
```
✅ **已配置** (cluster_hmi warning 节点 分支B !=0 的 Play action, 2026-08-07): **RepeatCount=0(Infinite 无限循环)** + DurationScale=3(3倍速) + PlaybackMode=NORMAL。组件属性已复位回默认(RepeatCount=1/DurationScale=1)。

> ⚠️ **Infinite 就是 RepeatCount=0**（老隋指正 2026-08-07）：Kanzi Studio **不允许设置 <0 的数**（set -1 会报错）。之前误以为 -1 是 Infinite，错的。**0 = Infinite 勾选值**。

## ⭐ 用 DispatchMessageAction 控制动画启停（Trigger 里追加动作，2026-08-07 实测打通）

### 需求场景
已有 OnPropertyChangedTrigger 判断 warning.value==0/!=0，想**再追加一个动作**：==0 时停止动画、!=0 时开始动画。

### 关键：动画启停靠「消息」，不是 SetProperty
AnimationPlayer 无 Play/Stop 属性可设（反射看不到）。启用停靠**派发消息**：
- **开始** = `Message.AnimationPlayer.Play`
- **停止** = `Message.AnimationPlayer.Stop`
（还有 Resume/Pause/Started/Stopped/Completed）

### 1. 找到 DispatchMessageAction 类型
```python
# TriggerActionType 库 get_Items() 里有 (不是 GetTreeItemsAsList):
mcp kz_invoke target=@TriggerActionTypes库 method=get_Items
# → @obj3810 Kanzi.DispatchMessageAction
```

### 2. 在 trigger 里追加 action（每次连接引用重分配，需现定位 trigger）
```python
mcp kz_invoke target=@triggerRef method=CreateAction args=["@obj3810"]
# → 返回新 DispatchMessageAction
```

### 3. 设置消息类型 MessageType（⚠️ 缓存时序坑）
```python
# 从 MessageTypes 库 get_Items() 拿到 Play/Stop 消息引用 (get_Items 才有全部187个内置消息! get_Children 只有自定义的4个)
mcp kz_invoke target=@obj129 method=get_Items   # MessageTypes 库
# → @obj3881 Message.AnimationPlayer.Play  /  @obj3884 Message.AnimationPlayer.Stop

# 设置前必须先多次 get_Name 预热缓存, 否则报参数类型错误!
for _ in range(3): mcp kz_invoke target=@obj3884 method=get_Name
mcp kz_invoke target=@DispatchAction method=set_DispatchMessageActionMessageType args=["@obj3884"]  # Stop
```
⚠️ **缓存时序坑**：`set_DispatchMessageActionMessageType` 有时报 `类型"System.String"无法转换为...MessageType`。因为 get_Items 新枚举出的 @obj 引用 bridge 缓存可能还没切成 MessageTypePluginWrapper 类型。**解决：set 前对消息引用多次 get_Name 预热缓存**（2-3次可靠），再 set 就成功。

> 💡 **名字显示差异（2026-08-07 老隋确认）**：脚本创建的 DispatchMessageAction 默认名显示为 `Message.AnimationPlayer.Play`/`Stop`；而 UI 里手动创建（Dispatch Message Action → Animation Player → Start/Stop）默认名显示为 `Animation Player:Start`/`Stop`。**底层消息类型完全相同，功能等价，只是显示的默认名字不同，不是创建错了。**

### 4. RoutingTarget（消息发往目标节点）—— 默认即可！
```python
# 新建 DispatchMessageAction 的默认 RoutingTarget = 挂载 trigger 的节点自身 (RelativePath=".")
# 例: trigger在warning上 → 默认RT指向warning → AnimationPlayer组件在warning上 → 消息被正确处理
# 不需要改动默认值!
```
⚠️ set_RoutingTarget 只接受 `@node:相对路径` 形式（如 `@node:../..`），绝对路径/纯路径/对象引用全失败。**但默认值已正确（指向节点自身），通常无需设置。**

### 5. 完整示例（双分支）
```python
# 分支A trigger(warning.value==0): SetPropertyAction(text=0) + DispatchMessageAction(Stop)
# 分支B trigger(warning.value!=0): SetPropertyAction(text=1) + DispatchMessageAction(Play)
# 两 trigger 各含: Condition + SetPropertyAction + DispatchMessageAction(消息)  三个子项
```

## ⭐ 关键帧（在 Animation Data 内部，非 Timeline！2026-08-08 模型纠偏）

> ⚠️ 老隋纠正：**关键帧在 Animation Data 内部**，Animation Data = 单一关键帧动画（定义 keyframes + target property）。
> **Animation Clip = 组合多个 Animation Data**（"一个组合可以包含很多 animation"）。
> Timeline Entry / Timeline Sequence 是**另一套**（操纵动画的：重复/缩放/targeting/blending），**不是关键帧本体，不要碰**（老隋："我现在只要 animationclip 和 animation，不要其他的"）。

### 实测证据：现有动画组确实引用多个 Animation（Clip 组合的本质）
| 动画组 | 引用动画数 |
|---|---|
| 01circle_scale | 3（SCALE_X/Y/Z）|
| modern_sett_navi scale | 2 |
| 其余多数 | 1 |
引用存于 `AnimationDataChildReferences`。✅ Kanzi 能力存在（现有组能引多个），缺的是 bridge 写通道。

> ⚠️ 曾误入歧途（2026-08-08 上午）：往 Timeline Sequences 库建 TimelineSequence/TimelineEntry 并当成"关键帧"，是**认知错误**。Timeline Entry 不是关键帧本体，是操纵动画的容器。已废弃该方向。

### ✅ 重大突破：动画组引用动画（AnimationDataChildReferences）—— 用 ReparentProjectItem 实现（2026-08-08）

> **之前卡住的核心难点已解决**：让 Animation Clip 引用 Animation。**正确方法是 `ReparentProjectItem` + 两个完整路径字符串参数**（不是 @obj 引用、不是 `set_Item("AnimationDataChildReferences",...)`）。老隋在 Studio GUI 实测确认：`01circle_innerRadius` 已成功引用到 `adas.num`。

```python
# 拿命令执行器
@studio.get_Commands() → GeneratedCommandInvoker (@obj2)

# ReparentProjectItem(动画完整路径, 动画组完整路径) → 让动画组引用动画 ✅
kz_invoke target=@obj2 method=ReparentProjectItem \
  args=["Animation Data/adas.num", "Animation Clips/01circle_innerRadius"]
→ ✅ 调用成功（无返回值）
```

**用法铁律（贯穿整个踩坑）**：
1. 两个参数**都必须是完整路径字符串**（`Animation Data/xxx`、`Animation Clips/xxx`），**不带开头 `/`，也用不得 @obj 引用**。
2. 用 @obj 引用调用会报「Adding child animations is not supported」——但**路径字符串调用返回成功**且真正建立引用。
3. 返回「✅ 调用成功」即代表真的建立了**引用**关系（不是层级移动）——不要用 `get_Children` 验证（动画组的引用不在 children 里，get_Children 查空是正常的）。**正确验证方式：
   ```
   # 读动画组引用的动画列表（关键验证方法！不是 get_ 方法，是 get_Item 索引器）
   clip.get_Item("AnimationDataChildReferences")  # → 返回引用的动画列表，每项含 ref_id + name
   # 例: 01circle_innerRadius → [InnerRadius_1(原有), adas.num(Reparent新加)]
   # 注: get_AnimationDataChildReferences（get_ 前缀）在 wrapper 上找不到，用 get_Item 才对
   ```
4. ⚠️ 但注意：用 get_Parent 查动画项仍是原库（这里 adas.num 的 parent 仍是 Animation Data）——Reparent 建立的是**引用**，动画项物理位置不变。

**之前失败的老路（勿再试）**：
- ❌ `clip.set_Item("AnimationDataChildReferences", <任何形式>)` 失败——`@anim:`/`@obj`/路径都不行，报 "cannot be converted to studio internal property value"。这是引用集合属性，bridge 纯反射没法直接构造属性值封装。
- ❌ `ReparentProjectItem` 用 @obj 引用当参数 → 报「Adding child animations is not supported」。

> **老总结修正**：创建（Animation/AnimationClip/AnimationChildClip/**TimelineSequence/TimelineEntry**）✅ 全通；子片段引用动画项 ✅；关键帧创建+时间字段配置 ✅；**动画组引用动画（AnimationDataChildReferences）✅ 现可用——用 ReparentProjectItem 完整路径。**

## 反编译 PluginInterface.dll 的动画公开接口（dnfile 解析）

- `Animation` / `AnimationProperties`（动画项：AnimationTargetPropertyName/Attribute, AnimationDataChildReferences）
- `AnimationClip` / `AnimationClipProperties`（动画组：StartTime/EndTime/AutoSizeToContent/EditRootNode）
- `AnimationChildClip` / `AnimationChildClipProperties`（子片段：**AnimationChildClipTargetItem** ← 关键引用属性）
- `TimelineEntry` / `TimelineSequence` / `TimelineEntryTarget`（关键帧结构）

## 已实测验证清单
- ✅ AnimationPlayer 组件创建（CreateNodeComponent + @obj357 类型）→ warning 节点成功
- ✅ Timeline 关联：set_Item("AnimationPlayer.Timeline", @obj157) → ToString() "Animation Clip 1HZ" 验证通过（2026-08-07）
- ✅ DispatchMessageAction 控制动画启停：trigger 追加 action，MessageType=Play/Stop，默认 RoutingTarget 指向节点自身（2026-08-07）
- ✅ MessageTypes 库 get_Items() 含全部 187 个内置消息；Play/Stop = Message.AnimationPlayer.Play/Stop
- ✅ set_DispatchMessageActionMessageType 需先多次 get_Name 预热缓存（时序坑）
- ✅ 循环+倍速：**在 Play action 的 PlayMessageArguments 里设** **RepeatCount=0(Infinite 循环)** + DurationScale=3(3倍速)；组件属性复位回默认（2026-08-07）
  - ⚠️ 不是设在 AnimationPlayer 组件；**Infinite=RepeatCount 0**（Kanzi不允许<0，不是-1）
- ✅ 创建 Animation / AnimationClip / AnimationChildClip：**用裸类型名 + 完整路径 parent 全部成功**（2026-08-08）
- ✅ 创建 TimelineSequence / TimelineEntry：建在 Timeline Sequences 库的序列底下——成功（2026-08-08，但**已确认这是"操纵动画"的另一套，不是关键帧本体，勿用**）
- ✅ childclip 引用动画项：`set_Item("AnimationChildClipTargetItem","@anim:动画项名")` 成功（2026-08-08）
- ✅ AnimationClip 直接引用 Animation（AnimationDataChildReferences）：**用 `ReparentProjectItem(动画完整路径, 动画组完整路径)` 实现**（2026-08-08 老隋 Studio GUI 确认 01circle_innerRadius 引用到 adas.num）；旧路 `set_Item("AnimationDataChildReferences",...)` 仍失败
- ✅ 清理测试残留：库项直接 Delete 返回 True；三个库（Data/Clips/Timeline Sequences）清理后分别回 24 / 17 / 5 项

## 待办 / 后续方向
- 组引用动画 + 关键帧配置：需插件增强（走 wrapper 底层或引擎 API），或确认需求是否可用现有动画

## 相关主题
- 绑定：kanzi-binding skill
- 触发器（属性变化触发动画）：kanzi-trigger skill
- 节点/属性：kanzi-ui skill（动画目标通常是节点属性）
