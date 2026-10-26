---
name: kanzi-state-manager
description: Kanzi Studio 状态机创建/配置。StateManager、StateGroup、State、StateObject 的完整生命周期。控制属性（ControllerProperty）的设置。状态过渡见 StateTransition 章节。
---

## 🚫 命名铁律（创建前必读）

> 创建任何东西（节点/资源/动画/别名/条目）时，**名字禁止特殊字符**：`\` `/` `|` `.` `:` `*` `?` `"` `'` `<` `>` 空格。
> **允许中文，推荐英文**（中文名可用，但英文更稳妥，避免跨工具编码问题）。
> 不要以数字开头（部分 API 限制）。
> 错误：`text/header` `bg.1` `a|b` `C:\temp` `new node`；正确：`text_header` `bg_1` `标题文本` `header-text`。

## MCP 协议基础

**MCP (Model Context Protocol)** 通过 WebSocket JSON-RPC 调用 Kanzi Studio 插件。

### 接入（HTTP MCP）

> ⚠️ **地址规则**：若环境已配置好相关 MCP（如 nlp_worker config.yaml 的 `mcp_servers` 或部署机已建网关），**必须使用已配置的 MCP 地址**；`<kz_mcp_http机IP>` 仅为通用占位符（未配置时的示例写法）。
通过 HTTP 端点 `POST http://<kz_mcp_http机IP>:9001/mcp`（Header `X-Kanzi-User: suijichao`，JSON-RPC `tools/call`）连接 Kanzi Studio 插件。返回 `ref_id = @objN` 自动进缓存，Studio 重启后（**仅人工操作**）编号失效须重新枚举。

### 基本请求格式

```python
{
  "jsonrpc": "2.0",
  "id": "请求编号",
  "method": "tools/call",
  "params": {
    "name": "kz_invoke",
    "arguments": {
      "target": "目标",     # @project / @objXXX / 节点路径
      "method": "方法名",
      "args": ["参数列表"]
    }
  }
}
```

### 特殊标识符（v4）

| 标识符 | 说明 |
|--------|------|
| `@project` | 自动注入的当前 Kanzi 工程对象（target 与 args 均可用） |
| `@obj123` / `@obj:123` | 对象缓存引用（`@obj:` 新格式等价，每次连接 Studio 后动态分配，Studio 重启（**仅人工**）后失效） |
| `@type:名字` | 用干净类型短名创建（如 `@type:StateManager` / `@type:StateGroup` / `@type:State`） |
| `@obj:parent` | 创建时的 parent 参数（引用父对象） |
| `@string:` / `@enum:` / `@null` / `@node:` 等 | v4 参数标识符（见文末总表） |

### 对象缓存机制

`@objXXX` 必须先进入缓存才能使用。发一次 `kz_invoke` 调用即可触发缓存：
```python
mcp({"..","name":"kz_invoke","arguments":{"target":"@obj47","method":"get_Name","args":[]}})
```
调用成功后 `@obj47` 就在缓存中了。

下面的调用统一走 `kz_invoke`（工具名，参数遵循 v4 标识符 @type/@int/@string/@enum/@obj/@color 等）。

### 🔍 创建前查重（幂等，2026-10-26 加，协议铁律第17条）

> 子会话可能被重派重试，**不假设本次任务全新**。创建状态机前先查 StateGroup/State 是否已存在，**已存在则跳过创建**，回报注明「N 个已存在跳过」。

```python
# 1) 枚举 StateManagerLibrary 下所有 StateGroup：
mcp({"jsonrpc":"2.0","id":"1","method":"tools/call","params":{"name":"kz_invoke","arguments":{"target":"@project","method":"get_StateManagerLibrary","args":[]}}})
mcp({"jsonrpc":"2.0","id":"2","method":"tools/call","params":{"name":"kz_invoke","arguments":{"target":"<StateManagerLibrary ref>","method":"get_Children","args":[]}}})
# → 比对 StateGroup 名，已存在则跳过该组创建

# 2) StateGroup 内查 State：
mcp({"jsonrpc":"2.0","id":"3","method":"tools/call","params":{"name":"kz_invoke","arguments":{"target":"<StateGroup ref>","method":"get_Children","args":[]}}})
# → 比对 State 名（注意 get_Children 的 type 字段不可靠，用 get_TargetObjectPath 判别），
#   已存在则跳过该 State 创建
```

> ⚠️ 查重顺序与创建顺序一致：先组后 State；StateObject 也按名称查重。

## 创建状态机

### 核心概念

Kanzi 状态机层次结构：
```
StateManager (warning State Manager)
  └── StateGroup (warningGroup)
       └── State (warning_0)
            ├── 直接属性: StateGroupControllerPropertyTypeReference 控制属性
            │              warning.value 对应的条件值
            ├── 或者子 State (TextPrefab) — 通过 TargetObjectPath="." 指向目标节点
            │    └── TextConcept.Text = "KzResourceID:0"
```

### ✅ v4 简洁创建方式（已实测通过，推荐）

用 `@type:` 类型短名直接创建，无需预取 RuntimeType，然后逐层 `CreateProjectItem`。

> 🔁 **批量操作铁律**：创建状态机的脚本**必须用 `BeginBatchModification` / `CommitBatchModification` 成对包裹**，把 state/stateobject 的**创建 + 设置**（含但不限于：State 控制属性值、StateObject 的 TargetObjectPath/文本内容）**全部包进同一个 batch**。不成对会卡死 Studio。
> 🔌 **单连接铁律**：批量脚本**只建一次连接**，Begin→所有创建/设置→Commit 全部在**同一连接**内完成。**禁止每次调用重新连接/新开进程**（跨连接会让 @obj ref 失效、batch 事务错乱、Studio 崩溃）。
> ⚠️ **禁止硬编码 @obj 引用**（如 `@obj2191`）：每次连接/重启编号都会变，必须先从库重新枚举定位目标 parent（如 `get_StateManagerLibrary` → `get_Children` → 找到目标 SG 的当前 ref）。

```python
# 1. 获取 StateManagerLibrary 的 ref
r = mcp({"jsonrpc":"2.0","id":"1","method":"tools/call","params":{"name":"kz_invoke","arguments":{"target":"@project","method":"get_StateManagerLibrary","args":[]}}})
smlib = "@obj" + re.search(r'@obj(\d+)', r["result"]["content"][0]["text"]).group(1)

# 2. 创建 StateManager（type=@type:StateManager, parent=StateManagerLibrary, 新格式 @obj:）
r = mcp({"jsonrpc":"2.0","id":"2","method":"tools/call","params":{"name":"kz_invoke","arguments":{"target":"@project","method":"CreateProjectItem","args":["@type:StateManager","V4TestSM","@obj:"+smlib[4:]]}}})
sm_ref = "@obj" + re.search(r'@obj(\d+)', r["result"]["content"][0]["text"]).group(1)

# 3. 创建 StateGroup（parent=SM）
r = mcp({"jsonrpc":"2.0","id":"3","method":"tools/call","params":{"name":"kz_invoke","arguments":{"target":"@project","method":"CreateProjectItem","args":["@type:StateGroup","V4TestGroup","@obj:"+sm_ref[4:]]}}})
sg_ref = "@obj" + re.search(r'@obj(\d+)', r["result"]["content"][0]["text"]).group(1)

# 4. 创建 State（parent=SG）
mcp({"jsonrpc":"2.0","id":"4","method":"tools/call","params":{"name":"kz_invoke","arguments":{"target":"@project","method":"CreateProjectItem","args":["@type:State","V4TestState","@obj:"+sg_ref[4:]]}}})

# 5. 【同一 batch 内】批量设置 state / stateobject（含但不限于：
#    State 控制属性值、StateObject 的 TargetObjectPath/文本内容）
mcp kz_invoke target=<State ref> method=set_Item args=["StateControllerPropertyValue", "@int:0"]
mcp kz_invoke target=<State ref> method=CreateProjectItem args=["@type:StateObject","V4TestSO","@obj:<State ref>"]
mcp kz_invoke target=<StateObject ref> method=set_Item args=["StateObject.TargetObjectPath", "@string:."]
# 全部创建+设置都在 Begin...Commit 之间

# 6. 提交批量（必须成对！）
mcp kz_invoke target=@project method=CommitBatchModification
```

✅ **实测结果**：`@type:StateManager`/`@type:StateGroup`/`@type:State` 三个短名都能正确创建对应类型（完整层级 SM→Group→State）。

> ✅ **实测：`@type:StateObject` 和反射获取的 StateObject 类型都能正常创建 StateObject**。注意插件 `get_Children` 返回的 `type` 字段不可靠（把 StateObject 误标成 `StatePluginWrapper`），**判别 StateObject 的正确方法是 `get_TargetObjectPath`**（能返回路径如 `.` 就是 StateObject；报 "This state is a root state" 就是根 State）。

### 完整流程（旧版：预取 RuntimeType）

```python
# ===== 第1步：获取 StateManager Library =====
r = mcp({"jsonrpc":"2.0","id":"1","method":"tools/call","params":{"name":"kz_invoke","arguments":{"target":"@project","method":"get_StateManagerLibrary"}}})
# 返回中提取 ref_id，如 @obj225

# 缓存一下
mcp({"jsonrpc":"2.0","id":"2","method":"tools/call","params":{"name":"kz_invoke","arguments":{"target":"@obj225","method":"get_Name","args":[]}}})

# ===== 第2步：获取各层次 RuntimeType =====
# StateManager 类型
r = mcp({"jsonrpc":"2.0","id":"3","method":"tools/call","params":{"name":"kz_invoke","arguments":{"target":"@obj225","method":"get_ProjectItemType"}}})
sm_type = 提取 r 中的 ref_id  # 如 @obj226

# StateGroup 类型 — 找一个已有 StateGroup 获取
r = mcp({"jsonrpc":"2.0","id":"4","method":"tools/call","params":{"name":"kz_invoke","arguments":{"target":"@obj225","method":"get_Children"}}})
# 从列表中找第一个 StateGroup 的 ref_id
r = mcp({"jsonrpc":"2.0","id":"5","method":"tools/call","params":{"name":"kz_invoke","arguments":{"target":"@obj100","method":"get_ProjectItemType"}}})
sg_type = 提取 r 中的 ref_id

# State 类型 — 同样从已有 State 获取
# StateObject 类型 — 通过反射获取
r = mcp({"jsonrpc":"2.0","id":"6","method":"tools/call","params":{"name":"kz_invoke","arguments":{"target":"@project","method":"GetType","args":[]}}})
# 获取 project 类型，GetProperties 找到 Assembly
# Assembly.GetType("Rightware.Kanzi.Studio.PluginInterface.StateObject")

# ===== 第3步：批量创建 + 设置（Begin 和 Commit 必须成对！）=====
# ⚠️ 创建状态机必须把 state/stateobject 的创建 + 设置（State 控制属性值、StateObject 的 TargetObjectPath/文本）全部包进同一个 batch（Begin/Commit 成对）
mcp({"jsonrpc":"2.0","id":"begin","method":"tools/call","params":{"name":"kz_invoke","arguments":{"target":"@project","method":"BeginBatchModification","args":["创建 warning State Manager"]}}})

# 创建 StateManager（第三参 = StateManagerLibrary 的 ref）
mcp({"jsonrpc":"2.0","id":"sm","method":"tools/call","params":{"name":"kz_invoke","arguments":{"target":"@project","method":"CreateProjectItem","args":["@obj226", "warning State Manager", "@obj225"]}}})

# 创建 StateGroup（第三参 = 刚创建的 SM 的 ref）
mcp({"jsonrpc":"2.0","id":"sg","method":"tools/call","params":{"name":"kz_invoke","arguments":{"target":"@project","method":"CreateProjectItem","args":["@obj227", "warningGroup", "@obj228"]}}})

# 创建 State（第三参 = SG 的 ref）
mcp({"jsonrpc":"2.0","id":"st","method":"tools/call","params":{"name":"kz_invoke","arguments":{"target":"@project","method":"CreateProjectItem","args":["@obj229", "warning_0", "@obj230"]}}})

# Commit
mcp({"jsonrpc":"2.0","id":"commit","method":"tools/call","params":{"name":"kz_invoke","arguments":{"target":"@project","method":"CommitBatchModification"}}})
```

⚠️ **注意**: 上述 `@obj227`、`@obj228` 等 ref 都是示意值。实际使用时：
1. 先获取 SM/SG/State 的 RuntimeType ref
2. 创建后从返回的 ref_id 获取新创建的对象引用
3. 用获取到的 ref_id 作为下一层级创建的 parent 参数

### 控制属性设置

#### StateGroup 控制属性引用

```python
# 先获取 StateGroup 属性列表
mcp({"jsonrpc":"2.0","id":"1","method":"tools/call","params":{"name":"kz_invoke","arguments":{"target":"@obj:230","method":"get_Properties"}}})
# 找到 "StateGroupControllerPropertyTypeReference" 的 ref_id

# 设置控制属性 — value 指向某个 PropertyType 引用（用 @obj: 新格式，v4 实测通过）
mcp({"jsonrpc":"2.0","id":"2","method":"tools/call","params":{"name":"kz_invoke","arguments":{"target":"@obj:230","method":"set_Item","args":["StateGroupControllerPropertyTypeReference", "@obj:19"]}}})
# @obj:19 = 目标属性的 PropertyType 对象（如 FloatPropertyTypePluginWrapper），
#           从目标节点 get_Properties 获取（如 FontStyleConcept.Size）
# ✅ v4 实测：set_Item 控制属性引用 + get_Item 回读均成功
```

#### State 控制属性值（用 @int: 避免数值歧义）

```python
mcp({"jsonrpc":"2.0","id":"1","method":"tools/call","params":{"name":"kz_invoke","arguments":{"target":"@obj:238","method":"set_Item","args":["warning.value", "@int:0"]}}})
```

#### StateObject 创建（mcp 可直接创建）

在 State 下创建 StateObject，`@type:StateObject` 即可（已实测）：

```python
# 创建 StateObject 到某个 State (@obj392) 下
mcp({"jsonrpc":"2.0","id":"1","method":"tools/call","params":{"name":"kz_invoke","arguments":{"target":"@project","method":"CreateProjectItem","args":["@type:StateObject", "V4TestStateObject", "@obj:392"]}}})

# 判别是不是真 StateObject — 调 get_TargetObjectPath
mcp({"jsonrpc":"2.0","id":"2","method":"tools/call","params":{"name":"kz_invoke","arguments":{"target":"@obj:新ref","method":"get_TargetObjectPath","args":[]}}})
# ✅ 返回 `.` 等路径 → 是 StateObject
# ❌ 报 "This state is a root state" → 是根 State，不是 StateObject
```

> ⚠️ `get_Children` 返回的 `type` 显示为 `StatePluginWrapper` 是**误标**，别据此判断；用 `get_TargetObjectPath` 判别最可靠。

#### StateObject 配置（TargetObjectPath 指向目标节点）

StateObject（子 State）通过 TargetObjectPath 指向目标节点：

```python
# 设置目标节点路径（"." 表示指向父 State 对应的目标节点）— 用 @string: 保证是字符串不被当节点
mcp({"jsonrpc":"2.0","id":"1","method":"tools/call","params":{"name":"kz_invoke","arguments":{"target":"@obj:1431","method":"set_TargetObjectPath","args":["@string:."]}}})

# 设置文本内容
mcp({"jsonrpc":"2.0","id":"2","method":"tools/call","params":{"name":"kz_invoke","arguments":{"target":"@obj:1431","method":"set_Item","args":["TextConcept.Text","@string:KzResourceID:1"]}}})
```

### 🚨 批量创建状态机脚本规范（2026-10-20 已根治，UI 线程）

> ⚠️ 批量创建 State + StateObject 曾让 Studio 崩，2026-10-20 已通过「状态机调用回 UI 线程」根治（插件改动：kz_invoke 一律走 UI 线程）。以下是背景 + 必须遵守的正确性规则。

#### 🎯 崩溃根因（2026-10-20 KanziStudio 日志确认）—— 非UI线程并发竞态，已修

- 崩溃堆栈：`StateGroup.GetInvalidityReason()` ← UI 线程枚举 StateGroup 集合；`ProjectItemViewModel.SetValidity()` ← 工程树刷新有效性标记；崩在 `System.Windows.Threading`（UI 线程）。
- **机制**：状态机创建调用跑**非 UI 线程**（v5 提速策略）时，Kanzi 的 UI 线程同时枚举同一个 StateGroup 集合做有效性校验 → 集合被并发修改 → 「集合已修改」未处理异常 → 整个 Studio 崩。
- **修复**：插件 `KzMCPServerClient` 的 kz_invoke 线程策略改为**一律 `Dispatcher.Invoke` 回 UI 线程**（修改和校验同线程串行，不再并发）。代价：批量创建约慢 2.7 倍（v5b 非UI 11 分钟 → UI 线程 30 分钟），换取稳定。
- 不需要再 sleep / 分批小跑 / 限次数（那是非UI线程时代的缓解措施，已随修复移除）。

#### ✅ 正确性规则（必须遵守，与线程无关）

1. **State 名必须符合命名铁律 —— 禁止空格/特殊字符（含逗号、句号）！**
   - ❌ `'21_高压绝缘故障 n请联系经销商'`（空格）、`'22_...，请安全停车 n...，熄火后...'`（空格+逗号）
   - ✅ `'21_高压绝缘故障请联系经销商'`（无空格无逗号）
   - 名字来自文本数据时**先清洗**：去掉空格、逗号、句号、`/`、`.`、`:`、`(`、`)`、`&`、`，` 等（只保留中文/数字/下划线/字母）。**写个清洗函数，循环里统一处理，别手写每个名字。**

2. **设置 StateObject 的 TargetObjectPath 用 `set_TargetObjectPath` 方法，且参数必须是合法节点路径！**
   - ✅ `mcp kz_invoke target=@so_ref method=set_TargetObjectPath args=["@string:."]`（`.` = 指向父 State 对应的目标节点，**skill 实测值**）
   - ⚠️ **参数不能是裸节点名**（如 `'popup'`）—— 必须是路径格式：`.` 或 `/Screens/Screen/RootPage/popup`。裸名解析不了 → 报错。
   - ❌ `mcp kz_invoke target=@so_ref method=set_Item args=["StateObject.TargetObjectPath", ...]`（set_Item 属性名不存在 → 报错）

3. **自定义属性（warning.value / warning.level 等）先 `AddProperty` 再 `set_Item`**：
   ```python
   mcp kz_invoke target=@st_ref method=AddProperty args=["warning.value"]
   mcp kz_invoke target=@st_ref method=set_Item args=["warning.value", "@int:21"]
   mcp kz_invoke target=@so_ref method=AddProperty args=["warning.level"]
   mcp kz_invoke target=@so_ref method=set_Item args=["warning.level", "@int:2"]
   ```

4. **Begin/Commit 必须成对 + 单连接**：见 index 第 6/7 条铁律。整批（Begin→创建→设置→Commit）在同一连接内完成。

5. **每次 kz() 调用后必须检查返回，error/❌ 立即停！**（插件崩了返回 error，不检查继续发 = 白打）
   ```python
   def kz(target, method, args=None):
       ... # 原逻辑
       if "error" in str(text) or "❌" in str(text) or text.strip() == "":
           print(f"  ❌ {method}@{target} 失败: {str(text)[:80]}")
           return None   # 或抛异常中断
       return text
   # 循环里：
   r = kz(...)
   if r is None: break
   ```

6. **Begin 也要检查返回**：Begin 失败（插件没连上/已崩）就不要再发循环，直接退出。

> 批量脚本正确结构（伪代码）：
> ```python
> # 1. 定位 SM/SG（动态枚举，不硬编码 @obj）
> # 2. 写清洗函数 sanitize(name)，循环统一处理所有 State 名（去空格/逗号/句号等）
> # 3. Begin（检查返回，失败即退出）
> # 4. 循环（单连接，无需 sleep）：
> #      r = CreateProjectItem(State)  →  r None 即 break
> #      AddProperty + set_Item(控制值)
> #      r = CreateProjectItem(StateObject)  →  r None 即 break
> #      set_TargetObjectPath(".")          ← 参数用 . 或完整路径，不是裸名
> #      AddProperty + set_Item(level)
> # 5. Commit（finally 里也要尝试 Commit）
> ```

## 🧩 StateTransition（状态过渡）创建/删除/属性设置（2026-08-19 实测打通）

**状态过渡 (StateTransition) 控制状态切换的时长、曲线、延迟等。** 是 StateGroup 上的子对象，每个过渡=一条"某态→某态"（或带通配）的切换规则。API 来源：Kanzi 文档 `StateGroup` (a00032) / `StateTransition` (a00034)，实测 cluster_hmi。

### 结构 & 获取

```python
# StateGroup 的过渡集合（每条 = 一个 StateTransitionWrapper）
mcp kz_invoke target=@StateGroup method=get_StateTransitions
# → 返回一组 ref_id，如 @obj421 / @obj422 ...
```

### ✏️ 创建（任意/单向/双向 关键在参数）

```python
# 语法: StateGroup.CreateTransition(startState, endState)
# parent 必须是 StateGroup (StateGroup ref 作为 target)
mcp kz_invoke target=@StateGroup method=CreateTransition args=["@obj:<startState>", "@obj:<endState>"]
```

> ⚠️ **"任意"用真正的 `null` 字面量**（第 2 参直接传 `null`，不是 `@string:`/`@obj:` 空！）：
> - 传 `null` → 该端=任意/通配
> - 传 `@string:""` 或 `@obj:` 会报错 `String 无法转换为 State`
> - **默认自动生成的那条"任意→任意"过渡** get_StartState/get_EndState 都返回空(null)

```python
# 例：状态0 → 任意（start=@obj393, end=null）
args=["@obj:393", null]

# 例：0 ⇄ 2（双向，见下方 Direction）
args=["@obj:393", "@obj:395"]
```

### 🔀 方向 Direction

- **"谁到谁"（如 0→2）= 单向 UNIDIRECTIONAL**：只作用 StartState→EndState
- **"两个之间切换"（如 0 和 2 之间）= 双向 BIDIRECTIONAL**：Start⇄End 都生效，**一条过渡即可，勿建两条**

```python
mcp kz_invoke target=@StateTransition method=set_Direction args=["@enum:BIDIRECTIONAL"]
mcp kz_invoke target=@StateTransition method=set_Direction args=["@enum:UNIDIRECTIONAL"]
# 读回 get_Direction
```

### ⏱ 属性设置

| 方法 | 含义 | 单位 | 示例 |
|------|------|------|------|
| `set_Duration` | 切换时长 | ms | `args=["@double:20"]` → 20ms |
| `set_StartTime` | 启动延迟 | ms | `args=["@double:5"]` → 延迟5ms后启动 |
| `set_AnimationType` | 缓动曲线 | 枚举值(见下) | `args=["@int:11"]` → POWER |
| `set_Direction` | 方向 | 枚举 | `["@enum:BIDIRECTIONAL"]` |
| `get_Duration` / `get_StartTime` / `get_AnimationType` / `get_Direction` / `get_StartState` / `get_EndState` | 读回 | | |

取值统一用 `@double:`（Duration/StartTime 是 double）。

### 🎚 AnimationType 枚举值（从 LogicProject.dll 反编译确认，非脑补）

`Rightware.Kanzi.Tool.Logic.Project.StateManagers.StateTransitionAnimationType`，值按声明顺序从 0 递增（运行时 @int:0-3 验证过 LINEAR=1/SMOOTH_STEP=2/STEP=3）：

| 值 | 名称(曲线) | | 值 | 名称 |
|----|-----------|--|----|------|
| 0 | CUSTOM | | 9 | ELASTIC |
| 1 | LINEAR | | 10 | EXPONENTIAL |
| 2 | SMOOTH_STEP | | **11** | **POWER** |
| 3 | STEP | | 12 | QUADRATIC |
| 4 | SMOOTHER_STEP | | 13 | QUARTIC |
| 5 | BACK | | 14 | QUINTIC |
| 6 | BOUNCE | | 15 | SINE |
| 7 | CIRCLE | | 16 | Modified |
| 8 | CUBIC | | | |

> ⚠️ **设 AnimationType 用 `@int:<值>`，不要用 `@enum:POWER`**：bridge 的 `@enum:` 对 set_AnimationType 参数类型 `Rightware.Kanzi.Studio.PluginInterface.StateTransitionAnimationType` 会报 `EnumTag 无法转换`。用 `@int:11` 等效设置 POWER，`get_AnimationType` 返回 11。

### 🗑 删除

```python
# StateGroup.DeleteTransition(该transition对象)
mcp kz_invoke target=@StateGroup method=DeleteTransition args=["@obj:<StateTransition>"]
# 返回 void = 成功；删后 get_StateTransitions 不再含它
```

### 完整样例（cluster_hmi 实测）

```python
# 创建 状态0(→任意) start≠null,end=null
@obj424 = SG.CreateTransition("@obj:393", null)   # StartState=0, EndState=null(任意)
@obj424.set_Duration("@double:15")                 # 15ms

# 创建 0⇄2 双向（== "0和2之间切换"）
@obj425 = SG.CreateTransition("@obj:393", "@obj:395")
@obj425.set_Duration("@double:20")
@obj425.set_StartTime("@double:5")
@obj425.set_Direction("@enum:BIDIRECTIONAL")
@obj425.set_AnimationType("@int:11")   # POWER

# 删除 任意→任意 默认过渡
@obj421 的 get_StartState/get_EndState 都 null → SG.DeleteTransition("@obj:421")
```

## 关键类型

| 接口 | 获取方式 | 备注 |
| StateTransition | StateGroup.get_StateTransitions 或 CreateTransition | 控制状态切换时长/曲线/方向/延迟 |
|------|----------|------|
| StateManager | `@type:StateManager` 短名 | ✅ 简洁方式推荐 |
| StateGroup | `@type:StateGroup` 短名 | ✅ 简洁方式推荐 |
| State | `@type:State` 短名 | ✅ 简洁方式推荐 |
| StateObject | `@type:StateObject`（或反射 Assembly.GetType("...StateObject")） | ✅ 都能创建；get_Children 显示为 StatePluginWrapper 是误标，用 get_TargetObjectPath 判别 |

## ⚠️ 状态机删除 — 无 API

**插件反射 API 没有删除状态机的方法**（经 `PluginInterface.dll` 全量确认）：
- 只有 `CreateProjectItem`（创建）、`CanDeleteProjectItem`（仅查询权限）
- `DeleteProperty`/`DeleteBinding`/`DeleteTransition`/`DeleteCondition`/`DeleteTrigger` 等只能删**子对象**
- **没有** `DeleteProjectItem`/`DeleteStateManager`/`DeleteState`/`DeleteStateGroup`

删除状态机只能在 **Kanzi Studio GUI** 手工操作（资源管理器选中状态机 → 右键删除）。不要尝试用 `ExecutePluginCommand` 等 hack 删除——有卡死风险。

## 查询资源

```python
# 列出项目所有第一级子项
mcp({"jsonrpc":"2.0","id":"1","method":"tools/call","params":{"name":"kz_invoke","arguments":{"target":"@project","method":"get_Children"}}})
# 返回中找 "State Managers" 文件夹，获取 ref_id

# 列出 State Managers 文件夹下的所有 StateManager
mcp({"jsonrpc":"2.0","id":"2","method":"tools/call","params":{"name":"kz_invoke","arguments":{"target":"@obj47","method":"get_Children"}}})

# 列出 StateManager 下的 StateGroup
mcp({"jsonrpc":"2.0","id":"3","method":"tools/call","params":{"name":"kz_invoke","arguments":{"target":"@obj107","method":"get_Children"}}})

# 列出 StateGroup 下的所有 State
mcp({"jsonrpc":"2.0","id":"4","method":"tools/call","params":{"name":"kz_invoke","arguments":{"target":"@obj120","method":"get_Children"}}})
```

## 常见错误处理

| 错误信息 | 原因 | 解决 |
|----------|------|------|
| Kanzi Studio 卡死，所有 API 返回空 | BeginBatchModification 无对应的 CommitBatchModification | **不要重启 Studio！** 停止当前批量操作，重新枚举 ref 恢复连接；如必须人工干预，请用户处理 |
| 子项看起来像 StatePluginWrapper，怀疑不是 StateObject | 只看了 get_Children 的 type 字段 | 用 `get_TargetObjectPath` 判别：能返回 `.` 就是 StateObject，确非根 State |
| ref 不存在 | Studio 重启过（**仅人工**） | 重新获取所有 ref |

> 调试工具（kz_list_refs / kz_ref_methods / kz_ref_properties）和 v4 参数标识符总表 → `kanzi-studio-mcp` skill。