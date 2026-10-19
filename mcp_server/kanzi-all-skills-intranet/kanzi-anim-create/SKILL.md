---
name: kanzi-anim-create
description: Kanzi 创建动画：创建动画对象（裸类型名+完整路径）、子片段引用 @anim:、完整流程+命名规则。读取动画数据见 kanzi-anim-read；播放器见 kanzi-anim-player。
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

> 读取动画数据库/动画项属性 → `kanzi-anim-read` skill。
> 动画播放器（AnimationPlayer 创建+关联动画）→ `kanzi-anim-player` skill。