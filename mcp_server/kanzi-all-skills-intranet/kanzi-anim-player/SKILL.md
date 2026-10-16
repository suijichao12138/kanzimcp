---
name: kanzi-anim-player
description: Kanzi 动画播放器：AnimationPlayer 创建+关联动画、DispatchMessageAction 控制启停。
---

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
