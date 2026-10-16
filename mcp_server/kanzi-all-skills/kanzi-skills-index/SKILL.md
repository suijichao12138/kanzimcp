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
| 属性添加/设置/删除（set_Item/AddProperty） | `kanzi-prop-set` |
| 文本/图片/前景/背景色 + KzResourceID | `kanzi-text-image` |
| TextBlock2D 完整配置 | `kanzi-textblock` |
| 自定义属性类型（Property Types） | `kanzi-proptype` |
| 变换定位（RenderTransformation） | `kanzi-transform` |
| Prefab 模板/占位符 | `kanzi-prefab` |
| 创建别名 Alias | `kanzi-alias` |
| 多工程切换 | `kanzi-project-switch` |

### 绑定/数据
| 任务 | skill 名 |
|------|---------|
| 创建/修改绑定（CreateBinding + 表达式语法） | `kanzi-binding` |

### 动画/状态/触发
| 任务 | skill 名 |
|------|---------|
| 创建动画对象 + 完整流程 | `kanzi-anim-create` |
| 动画播放器 + 启停 | `kanzi-anim-player` |
| 关键帧 + 动画组 | `kanzi-anim-clips` |
| 状态机（创建/过渡） | `kanzi-state-manager` |
| 触发器（条件/动作） | `kanzi-trigger` |

### 资源/材质/着色器
| 任务 | skill 名 |
|------|---------|
| 本地化 CRUD（增删改查） | `kanzi-loc-crud` |
| 本地化读取（ExportTranslations） | `kanzi-loc-read` |
| 本地化删表+建表 | `kanzi-loc-delete` |
| 颜色笔刷创建 | `kanzi-resource-brush` |
| 纹理创建 | `kanzi-resource-texture` |
| 字体创建 + 资源定位 | `kanzi-resource-font` |
| 渐变材质笔刷三层 | `kanzi-material-brush` |
| Shader 操作 | `kanzi-shader` |

### 工程/工具
| 任务 | skill 名 |
|------|---------|
| MCP 总入口（参数标识符/target） | `kanzi-studio-mcp` |
| 保存/导出 kzb | `kanzi-save-export` |
| 截图 | `kanzi-screenshot` |

### 属性全量（离线，不加载）
| 文件 | 用途 |
|------|------|
| `kanzi-properties-all` | 全部节点属性合并版（207KB）。**search_property 的数据源**；人工查证时按 `## 节点名` 分组定位，绝不整读 |

## ⚠️ 上下文铁律

1. **只常驻**：index + highfreq（共 ~10KB）。
2. **一切操作内容走工具**（get_skill 一次拿全小 skill）。
3. **绝不**整读 `kanzi-properties-all`（254KB）。
4. **绝不**反复调 docmcp / 工具试错 —— 拿不到就换关键词再试一次，或直接问。

## 🚫 命名铁律（所有创建/命名操作通用）

> 所有需要命名的操作 —— **创建节点 / 资源 / 动画 / 别名 / 属性类型 / 本地化条目 / 变量 / 参数** 等 —— 名字必须满足：

1. **只允许**：字母、数字、下划线 `_`、连字符 `-`。
2. **禁止**特殊字符：`\` `/` `|` `.` `:` `*` `?` `"` `'` `<` `>` 空格 中文 等。
3. **不能以数字开头**（部分 API 限制）。
4. **不要用中文命名**（Kanzi 资源名/变量名不支持）。

**错误示例**（一律不能用）：
- `text/header`（含 `/`）❌
- `bg.1`（含 `.`）❌
- `a|b`（含 `|`）❌
- `C:\\temp`（含 `\\`）❌
- `标题文本`（中文）❌
- `new node`（空格）❌

**正确示例**：
- `text_header` / `bg_1` / `header-text` / `kzGradientType_yy` ✅

> 用 kz_create_node / CreateProjectItem / CreateBrush / CreateNodeAliasEntry 等创建时，`name` / `@string:` 参数都遵守此规则。
