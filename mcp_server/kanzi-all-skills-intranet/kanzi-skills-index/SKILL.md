---
name: kanzi-skills-index
description: Kanzi skills 导航索引（小模型适配版）。唯一常驻的导航文件：告诉 Copilot 用 skill MCP 的 3 个工具（search_property 查属性 / list_skills 看有哪些 skill / get_skill 拿完整步骤），以及高频属性表位置。其余 skill 内容一律通过工具获取，不直接读文件。
---

# Kanzi Skills 导航（小模型版）

> **本文件 + 高频属性表（kanzi-properties-highfreq）是仅有的两个常驻 skill**。
> 其余内容一律通过 skill MCP 的 3 个工具获取，**不要直接读 skill 文件**。

## 🛠️ 使用规则（必须遵守）

skill MCP 提供 **3 个工具**（9001 网关 `/kanzi_skill_mcp`）：

| 工具 | 用途 | 用法 |
|------|------|------|
| `search_property(query, limit?)` | **查属性**（绑定写法/面板名） | 传关键词，中英文都行：`"width"` / `"字体"` / `"actual width"` |
| `list_skills()` | **看有哪些 skill** | 无参数，返回全部 skill 名+用途+大小 |
| `get_skill(name)` | **拿完整操作步骤** | 传 skill 名（如 `kanzi-node-create`），一次返回全文 |

**执行任务的标准流程**：

1. **查属性** → `search_property("关键词")`（高频属性也能先在常驻表里找）。
2. **要操作步骤** → `list_skills()` 找到对应 skill → `get_skill("skill名")` 拿完整步骤照着做。
3. **禁止**：直接读 `skills/*/SKILL.md` 文件、反复查 docmcp、多次调工具试错。
4. `search_property` 查不到 → 换更短关键词再试一次，还不行才考虑读全量属性文件对应段落。

## 📋 高频属性（常驻，不用查工具）

`kanzi-properties-highfreq` 已常驻 system prompt：布局尺寸（Layout Width/Height、Actual Width/Height）、对齐（Horizontal/Vertical Alignment）、边距、文本（Text/Word Wrap/Font 族）、颜色（Foreground/Background Brush、Opacity）、九宫格 NinePatch、范围值（Min/Max Value）、变换（Render Transformation）等 39 个最常用属性。

**查这些属性直接在本表找，不调 search_property。**

## 🗂️ skill 清单（按任务查）

> 全部 skill 已拆成「完整任务单元」，`get_skill` 一次返回全文。以下是任务 → skill 对照（详细描述用 `list_skills()` 看）。

### 节点与 UI
| 任务 | skill 名 |
|------|---------|
| 创建节点（EmptyNode2D/TextBlock2D/插件节点/九宫格） | `kanzi-node-create` |
| 布局节点（StackLayout2D 方向/创建） | `kanzi-layout` |
| 属性添加/设置/删除（set_Item/AddProperty） | `kanzi-prop-set` |
| 文本内容/排版（TextBlock2D 配置） | `kanzi-textblock` |
| TextBlock2D 完整配置 | `kanzi-textblock` |
| 自定义属性类型（Property Types） | `kanzi-proptype` |
| 变换定位（RenderTransformation） | `kanzi-transform` |
| Prefab 模板/占位符 | `kanzi-prefab` |
| 创建别名 Alias | `kanzi-alias` |
| 多工程切换 | `kanzi-project-switch` |

### 绑定/数据
| 任务 | skill 名 |
|------|---------|
| 创建/修改/查询/删除绑定 + 表达式语法 | `kanzi-binding` |

### 动画/状态/触发
| 任务 | skill 名 |
|------|---------|
| 动画全流程（读/创建/关键帧/播放器/启停） | `kanzi-animation` |
| 状态机（创建/过渡） | `kanzi-state-manager` |
| 触发器（条件/动作） | `kanzi-trigger` |

### 资源（创建 vs 设置 分开！）
| 任务 | skill 名 |
|------|---------|
| **创建** Resource 资源条目（ResourceDictionary+CreateResourceEntry） | `kanzi-resource-create` |
| **创建** 素材（颜色笔刷/纹理/字体） | `kanzi-asset-create` |
| **设置** 节点上的资源引用（前景/背景色/字体/状态机） | `kanzi-resource-set` |
| 图片/九宫格设置（Image2D.Image/9 块图，在属性设置里） | `kanzi-prop-set` |
| 渐变材质笔刷三层 | `kanzi-material-brush` |
| Shader 操作 | `kanzi-shader` |

### 本地化
| 任务 | skill 名 |
|------|---------|
| 本地化全流程（读/CRUD/删表建表） | `kanzi-localization` |

### 工程/工具
| 任务 | skill 名 |
|------|---------|
| MCP 总入口（参数标识符/target） | `kanzi-studio-mcp` |
| 保存/导出 kzb | `kanzi-save-export` |
| 截图 | `kanzi-screenshot` |
| **刷新工程树 / 刷新 Preview**（创建后必刷/截图前必刷） | `kanzi-refresh` |

### 属性全量（离线，不加载）
| 文件 | 用途 |
|------|------|
| `kanzi-properties-all` | 全部节点属性合并版（254KB）。**search_property 的数据源**；人工查证时按 `## 节点名` 分组定位，绝不整读 |

## ⚠️ 上下文铁律

1. **只常驻**：index + highfreq（共 ~10KB）。
2. **一切操作内容走工具**（get_skill 一次拿全小 skill）。
3. **绝不**整读 `kanzi-properties-all`（254KB）。
4. **绝不**反复调 docmcp / 工具试错 —— 拿不到就换关键词再试一次，或直接问。
5. **🚫 绝不重启 / 关闭 / 退出 Kanzi Studio！** 这些操作会造成未保存内容丢失、且断连后可能再也连不上。**禁止**：重启 Studio、`CloseProject()`、`CloseSolution()`、`ExitApplication()`、杀 Studio 进程。遇到 Studio 卡死/异常 → 停止当前操作、重新枚举 ref 恢复连接；需要真重启/关闭时交给老隋人工处理，不自己操作。
6. **🔁 批量操作必须成对**：`BeginBatchModification` 和 `CommitBatchModification` **必须成对出现**（不成对会卡死 Studio）。创建状态机的脚本必须把 state/stateobject 的**创建 + 设置**（含但不限于：State 控制属性值、StateObject 的 TargetObjectPath/文本内容）全部包进同一个 batch。
7. **🔌 脚本必须单连接执行所有调用**：一个脚本**只建一次连接**（一个 WS client 连接/一个进程），**所有调用复用同一连接**提交。**禁止每次调用都重新连接/新开进程/新开连接**（会造成 @obj ref 缓存失效、batch 事务跨连接错乱、触发 Studio 崩溃）。批量脚本的正确结构：`建连接 → BeginBatchModification → 循环内复用同一连接发 N 次调用 → CommitBatchModification → 关闭连接`。
8. **🔁 创建后必须刷新工程树 + 截图前必须刷新 Preview！**（2026-10-21 老隋要求）**任何创建操作完成后，必须刷新工程树**，否则新建内容在 Kanzi Studio 里不可见。**适用于所有创建**：新建节点、模板（Prefab）、属性、状态机（StateManager/StateGroup/State/StateObject）、多国语表、纹理、动画、笔刷、资源条目、别名等，**创建之后必须 SelectProjectItems**。截图前必须先 RestartPreview。**完整步骤见 `kanzi-refresh` skill**（拿 Commands → SelectProjectItems / RestartPreview）。

## 🚫 命名铁律（所有创建/命名操作通用）

> 所有需要命名的操作 —— **创建节点 / 资源 / 动画 / 别名 / 属性类型 / 本地化条目 / 变量 / 参数** 等 —— 名字必须满足：

1. **禁止**特殊字符：`\` `/` `|` `.` `:` `*` `?` `"` `'` `<` `>` 空格 等。
2. **允许中文，推荐英文**（中文名可用，但英文更稳妥，避免跨工具编码问题）。
3. **不能以数字开头**（部分 API 限制）。

**错误示例**（一律不能用）：
- `text/header`（含 `/`）❌
- `bg.1`（含 `.`）❌
- `a|b`（含 `|`）❌
- `C:\\temp`（含 `\\`）❌
- `new node`（空格）❌

**正确示例**：
- `text_header` / `bg_1` / `header-text` / `kzGradientType_yy` / `标题文本` ✅

> 用 kz_create_node / CreateProjectItem / CreateBrush / CreateNodeAliasEntry 等创建时，`name` / `@string:` 参数都遵守此规则。

## 🚫 资源引用写法（两种，别混！）

| 你要引用的是… | 写法 | 示例 |
|---|---|---|
| **素材/资源对象**（brush/纹理/字体/状态机，先用 get_Children 拿到它的引用） | `@obj<引用>` | `args=["Node2D.ForegroundBrush", "@obj5736"]` |
| **Resource 条目**（ResourceDictionary 里用 resourceID 注册的条目） | `KzResourceID:资源名` | `args=["Node2D.ForegroundBrush", "KzResourceID:FFFFFF"]` |

> ⚠️ 前缀拼写：是 `KzResourceID:`，不是 `resourceID:` / `resource:`（少 `Kz` 会失败）。

### 对应的 skill
- 创建 Resource 条目（ResourceDictionary+CreateResourceEntry）→ `kanzi-resource-create`
- 设置 Resource 引用（用 KzResourceID）→ `kanzi-resource-set`
- 创建素材（brush/纹理/字体）→ `kanzi-asset-create`
- 图片/九宫格设置（直接设图，不涉及引用）→ `kanzi-prop-set`