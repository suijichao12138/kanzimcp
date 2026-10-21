---
name: kanzi-task-execution-protocol
description: 子会话执行协议（注入所有 task 子会话）。读任务描述单 → 从数据源提取参数 → 生成命令序列表格 → 分组执行 → 回报成功/失败。Kanzi 操作的执行规范与正确性铁律都在这里。
---

# 子会话执行协议（Kanzi 任务执行）

> 你是 Kanzi 某类型的执行子会话。上下文与主会话隔离：主会话只给你「任务描述单」（objective + constraints + data_source），**具体参数值由你从数据源自行提取**，你不依赖主会话给参数。

## 执行流程（四步）

1. **读任务描述单**：objective（目标）、constraints（约束）、data_source（数据源路径）、project（工程）、type（你的类型）。
2. **从数据源提取参数**：按 objective/constraints 从 data_source（xlsx/文本/kanzi 资源）读取具体参数（名称、ID、值、路径）。**参数在这一步产生，只留在本会话**。
3. **生成命令序列表格**：按「步骤号/目标/MCP 工具/方法参数/预期结果/验证点」逐行列出要执行的命令。大输出标注落盘 + grep，不整读。
4. **分组执行**：按「同工程 + 同类操作 + 可验证边界」分组，每组 10–30 行；组不跨工程；用 kz_* 工具执行。

完成后**只回报**：
- ✅ 成功（新建对象数量 + 清单文件路径，正文只列关键对象）
- ❌ 失败（第几步、哪个命令、原因）

**禁止**：复述完整参数/返回值/命令序列；不向主会话要参数（从数据源自己读）。

## 执行总则（正确性铁律，必须遵守）

1. **命名铁律**：State/节点名禁止空格/特殊字符（含逗号、句号）；文本数据先清洗（去空格/逗号/句号/`/`/`.`/`:`/`(`/`)`/`&`/`，`），只保留中文/数字/下划线/字母。
2. **批量操作必须成对**：`BeginBatchModification` / `CommitBatchModification` 必须成对（不成对卡死 Studio）。创建状态机脚本把 state/stateobject 的创建+设置全部包进同一个 batch。
3. **单连接铁律**：一个脚本只建一次连接，所有调用复用同一连接；禁止每次调用重新连接/新开进程（跨连接 ref 失效、batch 事务错乱、Studio 崩溃）。
4. **@obj 按工程隔离**：`kz_select_project` 切换工程会清空上一工程引用缓存；cachedRefs/prefetchPlan 按工程分区，绝不跨工程复用引用。
5. **中文字符串直接传中文**，不传 \uXXXX。
6. **大输出一律落盘**（get_Properties/get_Options/get_Children/get_Node_Tree）：只用 grep、定向查询或脚本提取必要字段，禁止读取完整 dump。
7. **批量优先**：一次提交同类资源或属性，禁止可合并的逐项调用和逐项读回。
8. **返回检查（抽样 + 关键步骤必查，2026-10-21 老隋调整）**：
   - **批量同类调用**（如 set_Item 20 次）：不用每次检查，**抽查首项/末项 + 中间任一异常项**即可，其余靠"返回总数 = 预期数"批量核对。返回数量异常（少/多/空）再停下来查。
   - **关键步骤必查**：`BeginBatchModification`/`CommitBatchModification`、创建类（Create*/kz_create_node）、有依赖的衔接步骤 —— 这些必须看返回，error/❌/空立即停。
   - 一旦发现一个 error，**立即停**并查原因（说明前面可能系统性出错），不硬闯下一批。
9. **Begin 也要检查返回**：Begin 失败（插件没连上/已崩）就不要再发循环，直接退出。
10. **脚本优先**：有关 kanzi MCP 的操作优先脚本执行。
11. **工具输出只保留**：成功数、失败项、关键路径、必要引用；不在回复复述完整参数/返回值/文件清单。
12. **状态压缩**：每完成一步把状态压为「已完成/未完成/异常/下一步」四项，只读该摘要继续。
13. **创建后必须刷新工程树**：任何创建操作（节点/模板/属性/状态机/多国语表/纹理/动画/笔刷/资源/别名）完成后，必须 `Commands.SelectProjectItems` 刷新工程树，否则 Studio 里不可见。
14. **截图前必须先刷新 Preview**：`Commands.RestartPreview()`（若本任务需要截图）。
15. **不重启/关闭/退出 Kanzi Studio**：`CloseProject()`/`CloseSolution()`/`ExitApplication()`/杀进程 禁止；卡死时停止当前操作、重新枚举 ref 恢复连接。

## 保存/导出（若任务要求）
- 用 `@studio.get_Commands()` 动态取 GeneratedCommandInvoker（不写死编号），`SaveProject("@project")`，按需 `ExportBinary("@project")`。
