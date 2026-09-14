# V12：多工程支持（方案 A）

> 基于 **V11_transformation2d** 派生，V11 一行未动（存档于 `../v11_transformation2d` + `v11 打包 tar.gz`）。
> V12 新增多工程支持（方案 A：不切换 ActiveProject），用户通过 `kz_list_projects` / `kz_select_project`
> 指定「当前操作上下文」，之后所有基于 `@project` 的调用自动作用于所选工程。

## 解决的问题

之前 bridge 全程只绑定单一 `_project`（= Kanzi Studio 的 ActiveProject）。只能操作"当前激活"的
那一个工程。若老隋同时打开了多个工程，无法在不切换 Studio ActiveProject 的前提下操作非激活工程。

## 反编译确认（非脑补）的关键事实

从 `PluginInterface.dll` 反编译确认（dnfile，2026-08-17）：

- **`KanziStudio`** 只暴露：`get_Project` / `get_Solution` / `get_PrimaryProject` / `get_ActiveProject`。
  **没有 `get_Projects`**（一开始我误以为有，反编译纠正了）。
- **`Solution`** 暴露：`get_PrimaryProject` / `get_ActiveProject` / `set_ActiveProject` /
  `get_PreviewStartupProject` / **`get_Projects`**。
- `Solution.get_Projects` 签名 `20 00 15 12 49 01 12 85 78` = CALLCONV_DEFAULT，0 参，
  RET = ELEMENT_TYPE_GENERICINST(0x15) 泛型集合，元素 = `Project` 类型。
  → **`get_Projects()` 返回 `IEnumerable<Project>`**（直接可 foreach 枚举所有已打开工程）。

因此枚举路径是：`@studio.get_Solution()` → `Solution` → `get_Projects()`。

## 方案 A 设计（为何不改 V11 的核心逻辑）

**核心洞察：** bridge 里所有路径/节点解析方法（`GetNodeByPath` / `GetProjectItem` / `CreateProjectItem` /
`@project` / `@projectItem` 别名）读的都是 `_project` / `_projectItem` / `_projectType` / `_projectItemType`
这四个字段。**只要 `SelectProject` 把这四个字段切换到指定工程的缓存槽，V11 已有的解析逻辑就自动作用于
所选工程，一行都不用改。**

- ✅ **不切换 Kanzi Studio 的 ActiveProject**（不打扰老隋正在编辑的工程，方案 A 的核心）。
- ✅ **最小侵入**：只新增工程池 + 两个工具 + `@proj:` 前缀解析，V11 逻辑完全保留。
- 切换后 `@project` 别名指向所选工程（RegisterObject 的 `obj==_project` 规则天然成立）。

## 新增 / 改动清单

### KzMCPReflectionBridge.cs（220KB → 新增约 120 行）
- 新增字段：`ProjectSlot` 内部类 + `_projectPool`（名字→工程槽）+ `_solutionCached` + `_selectedProjectName`
- `Refresh()`：刷新后若曾 SelectProject 则维持选中工程
- 新增方法：
  - `GetSolution()`：反射拿 `Solution`（`@studio.get_Solution`）
  - `RefreshProjects()`：`Solution.get_Projects()` 枚举所有工程，填 `_projectPool`，注册 `@proj:<name>` 别名（跳过 ActiveProject 避免覆盖 @project）
  - `ListProjects()`：返回 `[{name,isActive,isPrimary,ref}]`
  - `SelectProject(name)`：把 `_project` 四字段切到目标工程槽；空串/省略切回 ActiveProject
  - `GetSelectedProjectName()`
  - `ResolveProjPath(body)`：解析 `@proj:<name>` 与 `@proj:<name>/<path>`（带路径则临时切上下文解析后切回）
- `ResolveObject`：`@proj:` 前缀分支

### KzMCPServerClient.cs
- 新工具 schema + 分发：
  - `kz_list_projects`：列出所有已打开工程（含 Active/ Primary 标记）
  - `kz_select_project {name}`：切换当前操作上下文（空=切回 ActiveProject）
- `kz_invoke` 的 target 说明补 `@proj:<工程名>[/路径]` 语法

## 新增 MCP 工具用法

```
kz_list_projects
  → 列出所有已打开工程，例如:
    已打开的工程:
      · hmi-alarm  → @proj:hmi-alarm  [Primary]
      · hmi-second → @proj:hmi-second
    当前 ActiveProject: hmi-alarm

kz_select_project { "name": "hmi-second" }
  → ✅ 已切换到工程: hmi-second（之后 @project 相关操作作用于该工程；ActiveProject 不变）

kz_select_project { "name": "" }
  → ✅ 已切回 ActiveProject: hmi-alarm

# 或不用 select，直接定位到指定工程（不改变后续 @project 语义）:
kz_invoke { "target": "@proj:hmi-second", "method": "..." }            # 工程对象
kz_invoke { "target": "@proj:hmi-second/SomeNode", "method": "..." }   # 指定工程内节点
```

## 待实测验证点（连上真实 Kanzi Studio 后确认）

1. `Solution.get_Projects()` 是否真能 foreach 出所有工程对象（反编译已确认签名，运行行为待验证）。
2. 非 ActiveProject 工程上的写操作（新建节点/项目项、保存）是否被 Studio 允许（老隋提过"非激活工程只读"疑虑——这是方案 A 的下一验证点）。
3. `get_WrappedItem` 在非激活工程上是否同样可拿到 ProjectItem。
4. 切回 ActiveProject 后再次 `kz_list_projects` 是否稳定。

## 版本继承

V8 → V9 → V10_modify_animation → V11_transformation2d → **V12_multiproject**
