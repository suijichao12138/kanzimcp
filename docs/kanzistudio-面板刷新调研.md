# Kanzi Studio 面板刷新调研报告（反编译 + 探测）

> 日期：2026-11-23 ~ 2026-11-24
> 起因：Preview 刷新（`RestartPreview`）正常，但 **Kanzi Studio 其他区域（节点树 / 属性库等）刷新不对**，需要找到「像 Studio 里右键→刷新」那样的分区域刷新方法。

---

## 一、问题背景

- 现有刷新机制只有两个（见 `skills/kanzi-refresh/SKILL.md`）：
  - `SelectProjectItems(item)` → 工程树选中定位刷新
  - `RestartPreview()` → 重启 Preview 进程（✅ 用户确认正常）
- 插件创建对象走的是 `Project.CreateProjectItem<T>()` **直接 API 调用**，绕过了 Studio 的**命令系统（CommandManager）**，不广播变更事件，所以面板不自动刷新。
- 目标：找到 Studio 内部各面板（节点树 / 属性库 / Library / 数据源）的刷新方法。

---

## 二、调研路径（三条线，全部查过）

### 线 1：官方命令参考（command-reference.html，190+ 命令）
- 结论：**没有任何 `Refresh`/`Reload` 命令**。
- 与「更新」相关的只有：`UpdateDataSourceContents` / `UpdateProjectDataSources` / `UpdateSolutionDataSources`（数据源）、`UpdateProjectEnginePlugins` / `UpdateSolutionEnginePlugins`（引擎插件）。
- 来源：`https://docs.kanzi.com/4.1.2/en/reference/command-reference.html`（doc-MCP 也返回同样结论）。

### 线 2：GeneratedCommandInvoker 完整方法列表（实机 type_probe，190+ 个）
- `@studio.get_Commands()` 返回的执行器，**没有通用刷新方法**。
- 能叫「刷新」的只有：
  | 方法 | 刷新区 | 状态 |
  |---|---|---|
  | `SelectProjectItems(item)` | 工程树选中定位 | 用户反馈「不对」 |
  | `RestartPreview()` | Preview | ✅ 正常 |
  | `UpdateProjectDataSources(project)` | 数据源 | 仅数据源 |
  | `UpdateProjectEnginePlugins(project)` | 引擎插件 | 仅插件 |
  | `CleanCachedFiles(project)` | 清理缓存 | 轻量 |
  | `RestartKanziStudio()` | 整个 Studio | 会断连+丢未保存（危险） |

### 线 3：反编译 Studio 内部 DLL（关键突破）
- Studio 安装目录（NAS）：`/mnt/nas/kanzi/kanzi_mcp_black/makzi_3.9.9/extracted/Bin/`
- 版本：**Kanzi Studio 3.9.9**
- 反编译工具：`monodis`（Mono IL 反汇编器，本机可用）
- 关键 DLL：
  - `ApplicationCommon.dll` — UI 面板 / 属性编辑器 / 工程视图
  - `LogicProject.dll` — 工程逻辑 / `KanziCommands` 命令定义 / `Project`
  - `LogicProperties.dll` — 属性系统
  - `LogicBase.dll` — CommandHandle / 命令基础设施

---

## 三、反编译结果（核心结论）

### 找到的「分区域刷新」方法（各面板对应）

| 面板区域 | Class（程序集） | 方法 | 说明 |
|---|---|---|---|
| **属性库/属性面板** | `Rightware.Kanzi.Tool.ApplicationCommon.PropertyEditing.PropertyGridUpdater`（ApplicationCommon） | `RequestUpdate()` 无参 | 属性面板刷新真正入口 |
| 属性面板（命令形式） | `KanziCommands`（static，LogicProject） | `get_RefreshPropertyEditor()` → CommandHandle | 命令 getter |
| **节点树/工程树** | `Rightware.Kanzi.Tool.Logic.Project.Project`（LogicProject） | `RefreshChildren()` 无参 | 节点树刷新 |
| 节点树（接口） | `Rightware.Kanzi.Tool.Logic.Project.ProjectInterface`（LogicProject） | `RefreshChildren()` 无参 | 接口形式 |
| 节点树（命令形式） | `KanziCommands`（static） | `get_UpdateProjectExplorer()` → CommandHandle | 命令 getter |
| 属性刷新器宿主 | `Rightware.Kanzi.Tool.ApplicationCommon.SolutionContainer`（ApplicationCommon） | `get_PropertyGridUpdater()` | 拿 PropertyGridUpdater 实例 |
| 数据源 | `GeneratedCommandInvoker` | `UpdateProjectDataSources` / `UpdateDataSourceContents` | ✅ 已有 |
| 引擎插件 | `GeneratedCommandInvoker` | `UpdateProjectEnginePlugins` | ✅ 已有 |
| Preview | `GeneratedCommandInvoker` | `RestartPreview` | ✅ 已在用 |

### 关键机制发现

1. **`KanziCommands` 是 static 类**（flags=0x181=abstract+sealed），含 451 个 `get_XXX()` 命令 getter，每个返回 `CommandHandle`。
2. **`CommandHandle.Execute()`**（LogicBase.dll）触发命令执行：
   - `Execute(object parameter)` / `Execute(object parameter, object context)`
   - `CanExecute(object parameter)`
3. **`PropertyGridUpdater.RequestUpdate()`** 是属性面板刷新的真正入口（通过 `SolutionContainer.get_PropertyGridUpdater` 拿到实例再调）。

### ⚠️ 反编译限制：方法体被混淆器清空

这批 DLL 被商业混淆器处理过（随机类名 `SGvXVjeIZTmVIT4SxR`、`Unknown heap type`）。反汇编结果是：
- **方法签名是明文**（类型名/方法名/参数都能看到）
- **方法体是空桩**：
  ```
  get_RefreshPropertyEditor() { nop; nop; ldnull; ret }   ← 返回 null
  RefreshChildren()         { nop; nop; nop; ret }        ← 空
  ```

**含义**：反编译只能拿到「签名」（哪个类型有哪个刷新方法名），看不到真实实现逻辑。这些签名在**运行时**对应的方法是真实存在的（混淆器清理的是离线副本，实机进程里方法是能跑的）。所以必须实机探测/验证。

---

## 四、所有方案汇总

| 方案 | 内容 | 优点 | 缺点 | 状态 |
|---|---|---|---|---|
| **A. 离线反编译定位** | monodis 反编译 Studio DLL 找刷新类型/方法名 | 零改动、纯调研 | 拿不到实现逻辑，需实机验证 | ✅ 已完成 |
| **B. 进程内枚举已加载程序集** | 给反射桥加诊断工具，枚举 AppDomain 所有程序集找 Refresh 类型 | 直接在 Studio 进程内定位 | 要改插件重编 DLL | 未做 |
| **C. 补变更通知（治本）** | 创建后补命令系统广播（走 GeneratedCommandInvoker 命令 / `CommandManager.InvalidateRequerySuggested()`） | 可能从根上解决自动刷新 | 要改插件 | 未做 |
| **D. 用反射桥 @static 静态调用** | 对 `KanziCommands` 等 static 类反射调命令 | 不改插件 | 命令 getter 是桩，需实机确认 | 已探测（见下） |
| **E. instance 方法直调** | `Project.RefreshChildren()` / `PropertyGridUpdater.RequestUpdate()` | ✅ 实机确认存在 | 需实调验证面板真刷 | **推荐下一步** |

---

## 五、探测结果结论（2026-11-23 实机只读验证）

用现有 relay 通道（ws://123.57.85.81:58080/suijichao）+ `kz_type_probe` / `@static:` + `ListStaticMethods`，**只读探测**（未触发任何刷新，未污染工程）。

### 探测结果表

| 类型（程序集） | 关键方法 | loaded | 结论 |
|---|---|---|---|
| `PropertyGridUpdater`（ApplicationCommon） | `RequestUpdate()` / `OnUpdateRequested(EventArgs)` | ✅ True | **存在，可反射** |
| `Project`（LogicProject） | `RefreshChildren()` | ✅ True | **存在，可反射** |
| `ProjectInterface`（LogicProject） | `RefreshChildren()` | ✅ True | **存在，可反射** |
| `SolutionContainer`（ApplicationCommon） | `get_PropertyGridUpdater()` / `set_PropertyGridUpdater(...)` | ✅ True | **存在，可反射** |
| `KanziCommands`（LogicProject） | loaded=True | ✅ True | 静态方法清单未展开（返回序列化小 bug） |

### 结论

1. **核心刷新方法全部在实机 Studio 进程里存在且可反射**，方法签名与反编译 3.9.9 完全对齐。
2. 用户反馈的「节点树 + 属性库」两个区域，正好对应：
   - 节点树 → `Project.RefreshChildren()`（`@project` 即 Project 对象，一步到位）
   - 属性库 → `PropertyGridUpdater.RequestUpdate()`（需先经 `SolutionContainer.get_PropertyGridUpdater()` 拿实例）
3. **可行性成立** —— 实机验证只需 `kz_invoke` 实调，不需要改插件代码。

### 附带发现（小 bug，不影响结论）

`KanziCommands` 的 `ListStaticMethods` 反射桥返回时数组没展开，只显示 `System.String[]`。但 `get_RefreshPropertyEditor` / `get_UpdateProjectExplorer` 只是 CommandHandle getter（反编译里是 `ldnull` 桩），真正刷新实现就是 `RefreshChildren()` / `RequestUpdate()` 这两个 instance 方法，已确认存在，故此 bug 不阻塞。

---

## 六、下一步（待办）

- [ ] **实调验证**（有副作用，需用户先点头再执行）：
  1. 先试最安全的 `kz_invoke target=@project method=RefreshChildren args=[]`，看节点树是否刷新
  2. 再试属性面板：探 `SolutionContainer` 实例获取路径 → `get_PropertyGridUpdater()` → `RequestUpdate()`
- [ ] 验证通过后，把 `RefreshChildren` / `RequestUpdate` 加入 `skills/kanzi-refresh/SKILL.md`（三处同步，内网脱敏）
- [ ] 若 `RefreshChildren` 无效，再评估方案 C（补命令系统广播）或方案 B（进程内枚举）

---

## 七、附：关键类型全限定名速查

```
Rightware.Kanzi.Tool.ApplicationCommon.PropertyEditing.PropertyGridUpdater
Rightware.Kanzi.Tool.ApplicationCommon.SolutionContainer
Rightware.Kanzi.Tool.Logic.Project.KanziCommands          (static)
Rightware.Kanzi.Tool.Logic.Project.Project
Rightware.Kanzi.Tool.Logic.Project.ProjectInterface
Rightware.Kanzi.Tool.Logic.Base.Commands.CommandHandle
Rightware.Kanzi.Tool.ApplicationCommon.Plugin.GeneratedCommandInvoker
```

## 八、附：反编译命令备忘

```bash
D=/mnt/nas/kanzi/kanzi_mcp_black/makzi_3.9.9/extracted/Bin
monodis --typedef $D/ApplicationCommon.dll      # 列类型
monodis --method  $D/ApplicationCommon.dll      # 列方法（签名明文，方法体被混淆清空）
monodis $D/LogicProject.dll                     # 完整 IL（看 getter 是 ldnull 桩）
```