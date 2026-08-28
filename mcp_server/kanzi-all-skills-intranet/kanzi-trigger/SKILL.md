---
name: kanzi-trigger
description: Kanzi Studio Triggers（触发器）创建与配置。TriggerNodeComponent 的创建（CreateTrigger）、Trigger 类型枚举、以及 **Action（TriggerActionItem / SetPropertyAction / DispatchMessageAction）和 Condition（TriggerConditionItem）的完整配置**——含判断条件（Operation=EQUALS/DIFFERENT、固定值 FixedPropertyValue、TermBSource=FIXED）、设置属性动作（TargetItem/PropertyType/PropertyValue）、发消息控制动画启停（DispatchMessageAction + AnimationPlayer.Play/Stop）、动画播放参数（RepeatCount=0无限循环、DurationScale倍速）、**StateManager.GoToState 直接跳转状态**（State/StateGroup用裸名字符串）。是配置 OnPropertyChanged/Message 触发器的完整流程。
---

# Kanzi Trigger 创建

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



## 连接模板（内网 HTTP MCP）

通过内网 HTTP MCP server（`relay_nlp_http/kz_mcp_http.py`）连接 Kanzi Studio 插件，直接调用 MCP 工具，无需本地客户端脚本。

- **HTTP MCP**：`http://10.10.118.152:9001/mcp`（请求头 `X-Kanzi-User: <用户名>`，白名单见 users.json，如 `suijichao`）
- **中继通道**：`ws://10.10.118.152:58080/<用户名>`（relay_multi 监听 58080，路径决定连哪台 Kanzi，须与 kz_mcp_http.py 一致）
- **调用**：直接调用 MCP 工具 `kz_invoke` 等，参数 `{"name":"kz_invoke","arguments":{"target":"X","method":"Y","args":[...]}}`
- 示例中的 `mcp kz_invoke target=X method=Y args=[...]` 即上一条的简写。

## 核心：创建 Trigger（✅ 已实测全面打通）

### 1. 枚举可用的 Trigger 类型（NodeComponentType）
Trigger 类型不是字符串，是 **NodeComponentType 对象引用**。枚举来源 = **NodeComponentTypeLibrary**：

```python
# 先定位库: 取任意已有 trigger 的 get_NodeComponentType() → get_Parent() 就是类型库
# 或在 @project.children 找 Node Component Types 文件夹(注意: 那个文件夹children为空, 只是外壳)
# 真正枚举用 GetTreeItemsAsList()
mcp kz_invoke target=@库 method=GetTreeItemsAsList
```

实测当前工程（cluster_hmi）NodeComponentTypes 库 18 个类型，其中 **Trigger 类型**：

| Trigger 类型 | NodeComponentType 引用 | 说明 |
|---|---|---|
| `Kanzi.DataTrigger` | @obj359 | 数据触发 |
| `Kanzi.MessageTrigger` | @obj347 | 消息触发（现有页面激活用这个） |
| `Kanzi.OnAttachedTrigger` | @obj366 | 挂载时触发 |
| `Kanzi.OnPropertyChangedTrigger` | @obj367 | 属性变化触发 |
| `Kanzi.TimerTrigger` | @obj372 | 定时触发 |

> ⚠️ 引用号每次连接会变，必须现场枚举获取，不能硬编码。

### 2. 在目标节点上创建 Trigger
```python
# node = 目标 UI 节点引用（如 RootPage @obj344）
mcp kz_invoke target=@obj344 method=CreateTrigger args=["@obj359"]   # ✅ 传 NodeComponentType 对象引用
```
✅ 创建成功返回 `TriggerNodeComponentPluginWrapper`，自动命名为 `Kanzi.XXXTrigger`。
前提：目标节点必须能放 NodeComponent（UI 节点都行）。

> ⚠️ 必须传 **NodeComponentType 对象引用**（如 `@obj359`），传裸字符串（`"DataTrigger"`）会报错。

### 3. 配置 Trigger 消息类型（MessageTrigger 专属）
```python
# 消息类型从 MessageTypes 库枚举 (get_Children)
# 设置 TriggerMessageType = 消息对象引用 (如 sys.startAniFinished)
mcp kz_invoke target=@新trigger method=set_Item args=["TriggerMessageType","@obj349"]
```
✅ 读回 `get_TriggerMessageType` 确认指向 `sys.startAniFinished`。
MessageTypes 库（@obj129）实测含：`sys.startAniFinished` / `theme.ani_start` / `theme.ani_end` / `sys.chargeAniFinished`。

### 4. Trigger 的其他关键字段（get_ 可读）
- `get_NodeComponentType()` — 触发器类型
- `get_IsMessageTrigger()` — 是否消息触发
- `get_TriggerMessageType()` — 消息类型对象
- `get_Actions()` / `get_Conditions()` — 动作/条件（当前工程空）
- `RoutingMode` / `MessageSource` / `RelativeMessageSource`

### 5. 清理
```python
mcp kz_invoke target=@新建trigger method=Delete   # ✅ 返回 True
```

## 核心：创建并配置 Trigger + Action + Condition（全部已实测打通）

### 6. 创建 Action（TriggerActionItem）—— 打通的配置

**枚举内置 Action 类型**：用 `TriggerActionTypeLibrary.get_Items()`（不是 `GetTreeItemsAsList`，那个只返回库自身）。

```python
mcp kz_invoke target=@TriggerActionTypeLibrary method=get_Items
# 实测得到: @obj3810 Kanzi.DispatchMessageAction
#           @obj3813 Kanzi.SetPropertyAction   ← 设置属性用这个
#           @obj3816 Kanzi.ApplyActivationAction / @obj3817 Kanzi.ApplyPropertyAction
#           @obj3811 ExecuteLuaAction / @obj3814 TrySetFocusAction / @obj3815 WriteLogAction / @obj3812 MoveFocusAction
```

**给 Trigger 创建 Action**：
```python
# trigger = 已创建的 Trigger 引用,@SetPropertyAction = 上面枚举到的类型对象
mcp kz_invoke target=@trigger method=CreateAction args=["@obj3813"]   # ✅ 成功
# 返回 TriggerActionItemPluginWrapper, 自动命名 Kanzi.SetPropertyAction
```

**配置 SetPropertyAction**（设置目标节点属性）：
```python
# 目标节点 = 相对引用(默认) 或绝对路径
mcp kz_invoke target=@action method=set_Item args=["MessageArgument.SetProperty.TargetItem","@obj295"]
# 要设置的属性类型对象(如 text 的 TextConcept.Text) —— 从目标节点 get_Properties 枚举得到
mcp kz_invoke target=@action method=set_Item args=["MessageArgument.SetProperty.PropertyType","@obj3829"]
# 设置的值: 固定值模式, 用 @string: 编码 (裸整数 0 / @int:0 都会失败)
mcp kz_invoke target=@action method=set_Item args=["MessageArgument.SetProperty.PropertyValue","@string:0"]
# 读回确认
mcp kz_invoke target=@action method=get_Item args=["MessageArgument.SetProperty.PropertyValue"]
# 其它字段: PropertyAttribute=WHOLE_PROPERTY(默认), SourceType=FIXED(默认=固定值)
```

⚠️ SetPropertyAction 槽位名（从 get_Properties 枚举得到）：`TargetItem` / `PropertyType` / `PropertyAttribute` / `SourceType` / `SourceItem` / `SourcePropertyType` / `SourcePropertyAttribute` / `PropertyValue` / `MessageArgument` / `MessageArgumentAttribute`。来源固定值时：`SourceType=FIXED`，值放 `PropertyValue`。

> 💡 **CustomEnum 属性（如 warning.value）设值坑（2026-08-07）**：若 PropertyType 是 CustomEnumPropertyType（自定义枚举），PropertyValue **不能用 `@string:`**，会报 `The given value cannot`（且默认值会致误读成功）。**正确：裸整数 `2` 或 `@int:2`**。但 Condition 的 FixedPropertyValue 用字符串 `"0"` 又能成功——不同接口对同枚举编码要求不同，先探测再设。

### 7. 创建 DispatchMessageAction（发消息控制动画启停，2026-08-07 实测打通）

**用途**：在 Trigger 里追加一个「发消息」的动作。最典型场景 = 控制 AnimationPlayer 动画播放：`warning.value==0` 停止动画、`!=0` 开始动画。

> 💡 **动画启停不能靠 SetProperty**（AnimationPlayer 没有 Play/Stop 属性可设），要**派发消息**：开始=`Message.AnimationPlayer.Play`、停止=`Message.AnimationPlayer.Stop`。

```python
# ★ 步骤1: DispatchMessageAction 类型 = TriggerActionTypeLibrary.get_Items()
mcp kz_invoke target=@TriggerActionTypes库 method=get_Items
# → @obj3810 Kanzi.DispatchMessageAction

# ★ 步骤2: 给 trigger 追加动作
mcp kz_invoke target=@trigger method=CreateAction args=["@obj3810"]
# → 返回新 DispatchMessageAction

# ★ 步骤3: 定位 Play/Stop 消息引用 (⚠️ 必须用 get_Items, get_Children 只有自定义4个)
mcp kz_invoke target=@obj129 method=get_Items   # MessageTypes 库
# → @obj3881 Message.AnimationPlayer.Play  /  @obj3884 Message.AnimationPlayer.Stop

# ★ 步骤4: 设置消息类型 (⚠️ 缓存时序坑: 必须先多次 get_Name 预热缓存!)
for _ in range(3):
    mcp kz_invoke target=@obj3884 method=get_Name   # Stop 消息
mcp kz_invoke target=@DispatchAction method=set_DispatchMessageActionMessageType args=["@obj3884"]
```

⚠️ **缓存时序坑**：`set_DispatchMessageActionMessageType` 会偶发报 `类型"System.String"无法转换为...MessageType`。原因是 get_Items 新枚举出的 @obj 引用，bridge 缓存可能还没切成 MessageTypePluginWrapper 类型。**解决：set 前对该消息引用多次 `get_Name`（2-3次）预热缓存**，再 set 就成功。

**（可选）播放参数 —— 在 Play action 的消息参数里配，不是 AnimationPlayer 组件！**
```python
# Play action (@DispatchAction=Play 的那个) 的槽位:
# AnimationPlayer.PlayMessageArguments.PlaybackMode / DurationScale / RepeatCount

# 3倍速 = DurationScale
mcp kz_invoke target=@PlayAction method=set_Item args=["AnimationPlayer.PlayMessageArguments.DurationScale","@float:3"]
# 无限循环(Infinite) = RepeatCount 设 0 (Kanzi不允许<0的数,-1会报错; 0才是Infinite)
mcp kz_invoke target=@PlayAction method=set_Item args=["AnimationPlayer.PlayMessageArguments.RepeatCount","0"]
# PlaybackMode: NORMAL(正向)/REVERSE(反向)/PING_PONG(往返)
```

**RoutingTarget（消息发往目标）—— 默认即可！**
```python
# 新建 DispatchMessageAction 的默认 RoutingTarget = 挂 trigger 的节点自身(RelativePath=".")
# 例: trigger 挂在 warning 上, AnimationPlayer 组件也在 warning 上 → 消息被组件处理, 无需改!
```
⚠️ `set_RoutingTarget` 只接受 `@node:相对路径`（如 `@node:../..`），绝对路径/纯路径/对象引用全失败。但默认值已正确，通常不动。

**名字显示差异（老隋确认）**：脚本创建的 DispatchMessageAction 默认名显示为 `Message.AnimationPlayer.Play/Stop`；Studio 手动创建（Dispatch Message Action → Animation Player → Start/Stop）默认名显示 `Animation Player:Start/Stop`。**底层消息类型完全相同，功能等价，不是建错。**

### 7b. DispatchMessageAction → StateManager GoToState（直接跳转状态！2026-08-07）

> ⚠️ **要控制状态机切状态，用 GoToState 消息（直接跳转），不是设控制属性/SetPropertyAction！** 老隋确认：正确流程是 **Dispatch Message Action → State Manager → Go To State**。

**消息**：`Message.StateManager.GoToState`（MessageTypes 库 `@obj129 get_Items` 里有；还有 GoToNextDefinedState/GoToPreviousDefinedState/EnteredState/LeftState 等）。

```python
# 1. 创建 DispatchMessageAction
mcp kz_invoke target=@trigger method=CreateAction args=["@obj3810"]  # DispatchMessageAction类型

# 2. 设消息类型 = GoToState
mcp kz_invoke target=@新action method=set_DispatchMessageActionMessageType args=["@GoToState消息"]

# 3. 🌟设 State/StateGroup —— 用裸名字符串, ⚠️不能用 @obj 对象引用!
mcp kz_invoke target=@新action method=set_Item args=["MessageArgument.StateManager.StateGroup","warningGroup"]
mcp kz_invoke target=@新action method=set_Item args=["MessageArgument.StateManager.State","warning_0"]
# ✅ 裸名(如 "warning_0") / "@state:warning_0" / "@project:...路径" 都能成功
# ❌ "@obj:4158" / "@obj4158" 报 "given value cannot" (State/StateGroup是StateReference, 接受名称字符串)

# 读回验证
mcp kz_invoke target=@新action method=get_Item args=["MessageArgument.StateManager.State"]  # warning_0
mcp kz_invoke target=@新action method=get_Item args=["MessageArgument.StateManager.StateGroup"]  # warningGroup
```

**槽位**：`MessageArgument.StateManager.StateGroup` / `.State` / `.Immediate`(是否立即跳过过渡) / `.ShowStateManagerOnly` / `.StateDefinedInCode` / `.StateSelectorPlaceholder`。

> 💡 前提：warning 节点需已挂 StateManager 属性（`AddProperty("Node.StateManager")` + `Set(..., 状态机资源)`，见 kanzi-state-manager skill）。

### 8. 创建 Condition（TriggerConditionItem）—— 打通的配置

**创建**（无参版可用，不需要类型参数）：
```python
mcp kz_invoke target=@trigger method=CreateCondition   # ✅ 成功, 自动命名 Condition
```

**配置条件判断**（如 warning.value == 0 / != 0）：

关键方法与枚举值（实测）：

| 配置项 | 方法 | 值 | 说明 |
|---|---|---|---|
| 监控属性(左值) | `set_Item("TriggerCondition.PropertyTypeReferenceA", @属性对象)` | @obj602 | TermA 引用属性 |
| 操作符 | `set_ConditionOperation` | **`"1"`=EQUALS, `"DIFFERENT"`=不等** | 🌟见下坑 |
| B侧来源 | `set_TermBSource` | **`"FIXED"`** 或 `"FROM_PROPERTY"`/`"FROM_MESSAGE"` | 用固定值必须 FIXED |
| 固定值 | `set_FixedPropertyValue` | `"0"` | 具体判断值 |

**⚠️ 最关键的坑：set 参数必须传字符串！**
- 传 `set_ConditionOperation(1)`（JSON 裸数字）→ 插件报「System.Int64 无法转换为 TriggerConditionOperation」
- 传 `set_ConditionOperation("1")`（字符串）→ ✅ 成功解析为 EQUALS
- 操作符枚举名（字符串直接可用）：`set_ConditionOperation("DIFFERENT")` → ✅ DIFFERENT（不等）。`@enum:DIFFERENT` 也可。

**✨ 为什么裸数字会报 Int64（源码根源）**：插件 `KzMCPReflectionBridge.FindEnumMethod` 的枚举自动转换只判断 `argVal is int`(Int32) 才走 `Enum.ToObject`；JSON 反序列化后的裸数字若是 `long`/Int64 就不匹配，直接落到类型不符报错。而字符串 `"1"` 会走 `ResolveSingleArg` 的 `int.TryParse` 转成 Int32，再成功转枚举。所以**枚举/数值参数一律传字符串**（`"1"`/`"DIFFERENT"`/`"FIXED"` 或 `"@enum:X"`），不要传裸数字。

**枚举名对照**（实测反编译 PluginInterface.dll）：
- `TriggerConditionOperationEnum`: `NONE`/`EQUALS`(或`EQUAL`)/`DIFFERENT`(≠)/`SMALLER`/`BIGGER`/`SMALLER_OR_EQUALS`/`BIGGER_OR_EQUALS`
- `TriggerTermSourceTypeEnum`: `FROM_PROPERTY`/`FIXED`/`FROM_MESSAGE`。判断固定值用 **`FIXED`**（不是 FIXED_VALUE/CONSTANT，那些不存在）

**✨ 为什么看"没设具体值"**：只设了 PropertyTypeReferenceA（监控属性），但 `TermBSource` 还是默认 `FROM_PROPERTY` → B 侧在找属性而不是用固定值，`FixedPropertyValue=0` 不生效。必须同时：`TermBSource=("FIXED")` + `FixedPropertyValue=("0")`，操作符才真正作用到固定值上。

**读回验证**：
```python
mcp kz_invoke target=@condition method=get_ConditionOperation   # EQUALS/DIFFERENT
mcp kz_invoke target=@condition method=get_TermBSource          # FIXED
mcp kz_invoke target=@condition method=get_FixedPropertyValue   # 0
mcp kz_invoke target=@condition method=get_PropertyA            # 属性 ref
```

### 9. OnPropertyChangedTrigger 的触发属性配置
触发属性（谁变化时触发）：
```python
# SourcePropertyType = 要监控的属性对象
mcp kz_invoke target=@trigger method=set_Item args=["OnPropertyChangedTrigger.SourcePropertyType","@obj602"]
# 其它: SourceNode(默认当前节点), IgnoreIdenticalValue, IgnoreInitialValue
```

### 10. 完整示例：OnPropertyChanged 双分支（warning.value==0→text=0, !=0→text=1）
```python
# 分支A trigger1 + condA + actionA
CreateTrigger(OnPropertyChangedTrigger类型)
condA=CreateCondition(); actA=trigger1.CreateAction(SetPropertyAction类型)
condA.set_Item(PropertyTypeReferenceA, warning.value)
condA.set_ConditionOperation("1")            # EQUALS
condA.set_TermBSource("FIXED")
condA.set_FixedPropertyValue("0")
actA.set_Item(PropertyType, text.Text@obj)
actA.set_Item(PropertyValue, "@string:0")
# 分支B trigger2 + condB + actionB (同样配置)
condB.set_ConditionOperation("DIFFERENT")     # ≠
actB.set_Item(PropertyValue, "@string:1")
```

## 通用注意事项
- **引用号每次连接重新分配**，必须现场通过路径/枚举重新定位，不能硬编码
- **设置任何枚举值，参数传字符串**（`"1"`/`"DIFFERENT"`/`"FIXED"`/`"@enum:X"`），不要传 Python int
- **设置固定值/数值用 `@string:` 前缀**（`"@string:0"`），裸 int / `@int:` / `@float:` 都会失败
- 属性类型对象（如 text 的 TextConcept.Text）：从目标节点 `get_Properties` 枚举拿到 PropertyTypePluginWrapper 类属性对象引用
- 相对引用 TargetItem/SourceItem 默认 `@obj295`（relative ref, IsAbsoluteReference=False）

## 已知边界 / 说明
- CreateTrigger/CreateAction/CreateCondition 均已打通。前置条件：监听对象、触发属性的**对象引用必须先在当前连接通过 get_Name/get_Properties 触发缓存**。
- 判断"固定值"的枚举值名是 `FIXED`，操作符"不等"是 `DIFFERENT`（不是 NOT_EQUALS/NOT_EQUAL/FIXED_VALUE——那些名在枚举里不存在，会转换失败）。这些坑是反编译 PluginInterface.dll + 运行时探测得到的，别再猜。

## 已实测验证清单（2026-08-07）
- ✅ DataTrigger / MessageTrigger / OnAttachedTrigger / OnPropertyChangedTrigger / TimerTrigger 五种创建全部成功，Delete 清理干净
- ✅ 现有 RootPage 页面激活 trigger（Page: Activated）为 Kanzi.MessageTrigger，NodeComponentType=@obj347，IsMessageTrigger=True
- ✅ 工程无损：所有测试对象已清理
- ✅ **OnPropertyChangedTrigger 完整链路打通**：info 下 warning+text 节点、绑定、触发warning.value、双分支 Condition(action 判断EQUALS/DIFFERENT + 固定值) → SetPropertyAction 写 text.text=0/1，全部读回验证通过（2026-08-07）
- ✅ **DispatchMessageAction 控制动画启停打通**：trigger 追加动作，MessageType=Play/Stop，默认 RoutingTarget 指向节点自身；循环（RepeatCount=0）+3倍速（DurationScale=3）配在 PlayMessageArguments（2026-08-07）
- ✅ **DispatchMessageAction → StateManager.GoToState 打通（老隋纠正）**：直接跳转状态，State/StateGroup 参数用**裸名字符串**（非 @obj引用）；分支A→warning_0、分支B→warning_2（2026-08-07）


## 相关主题
- 节点/组件创建：kanzi-ui skill
- 状态机：kanzi-state-manager skill（Trigger 也常挂在状态相关的节点上）
