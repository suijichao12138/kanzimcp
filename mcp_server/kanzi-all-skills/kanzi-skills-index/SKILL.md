---
name: kanzi-skills-index
description: Kanzi skills 导航索引。列出全部 kanzi-* skill 的名称、用途、适用场景和文件路径。需要某 skill 的详细内容时，读取该 skill 对应的 SKILL.md 文件，而不是依赖本索引的简述。
---

# Kanzi Skills 导航索引

> **本文件是唯一需要加载进上下文的 skill**。其余 skill 的内容按需读取。
>
> **使用规则**：当任务涉及某个 skill 的领域时，**先读取该 skill 的 `SKILL.md` 文件**获取详细操作步骤，再执行操作。不要只凭本索引的一句话描述直接操作。
>
> **文件位置**：所有 skill 在 `skills/` 目录下，路径格式 `skills/<skill名>/SKILL.md`（相对 Copilot 工作目录）。

## 属性查询（最常用）

> ⚠️ **重要**：`kanzi-properties-quickref` 是单个完整文件（约 48KB），**用搜索定位内容，不要整读全文**。

| Skill | 用途 | 何时读 |
|-------|------|--------|
| `kanzi-properties-quickref/SKILL.md` | **常用属性速查**：47 组 257 个属性的「UI 面板名 \| 绑定写法 \| 说明」，单文件 | **任何属性操作先查这个**（UI 设置或绑定取值） |
| `kanzi-properties-2d` | 全部 2D 节点属性全量参考 | quickref 查不到时 |
| `kanzi-properties-3d` | 全部 3D 节点属性全量参考（含相机/灯光/网格） | quickref 查不到时 |
| `kanzi-properties-layout` | 布局节点属性参考 | 布局冷门属性 |
| `kanzi-properties-control` | 控件节点属性参考 | 控件冷门属性 |
| `kanzi-properties-resource` | 资源属性参考 | 资源冷门属性 |
| `kanzi-properties-structure` | 结构节点属性参考 | 结构冷门属性 |
| `kanzi-properties-trajectory` | 轨迹节点属性参考 | 轨迹属性 |

**属性查询流程（重要）**：

1. 需要查属性时，在 `kanzi-properties-quickref/SKILL.md` 中**搜索目标属性名或分组名**（如 `Actual Layout Width`、`## Layout.Item`、`## 字体`）。
2. **只读取搜索命中的段落/那一行**，不要读取或加载整个文件。
3. 文件按分组组织，分组名格式 `## 分组名`，属性行格式 `| 属性名 | 绑定写法 | 说明 |`。
4. 若目标属性不在 quickref 中，再按需查全量版 skill 对应章节（同样只读目标节点段落）。

## 核心操作

| Skill | 用途 | 何时读 |
|-------|------|--------|
| `kanzi-studio-mcp` | **MCP 总入口**：工具 schema、v4 参数标识符、target 取值 | **任何 Studio 操作前先读** |
| `kanzi-ui` | UI 节点创建/配置、属性添加设置删除 | 创建/配置节点时 |
| `kanzi-binding` | 绑定表达式完整语法 + CreateBinding | 创建/修改绑定时 |

## 动画/状态/触发

| Skill | 用途 | 何时读 |
|-------|------|--------|
| `kanzi-animation` | 动画创建与配置（Animation Data/Clips/Player/Timeline） | 创建动画时 |
| `kanzi-state-manager` | 状态机创建/配置 | 状态切换时 |
| `kanzi-trigger` | 触发器/动作/条件配置 | 触发逻辑时 |

## 资源/工具

| Skill | 用途 | 何时读 |
|-------|------|--------|
| `kanzi-localization` | 多国语资源表增删改查 | 多语言文本时 |
| `kanzi-resource-create` | 颜色/纹理/字体资源创建 | 建资源时 |
| `kanzi-material-brush` | 渐变材质笔刷三层关联 | 建材质时 |
| `kanzi-save-export` | 工程保存 + kzb 导出 | 保存/导出时 |
| `kanzi-screenshot` | Studio/Preview 截图 | 验证效果时 |

## 使用流程

1. 收到任务 → 判断属于哪个 skill 的领域（查上表）。
2. **读取** `skills/<skill名>/SKILL.md` 获取详细步骤。
3. 按 skill 内的 MCP 调用格式执行操作。
4. 涉及属性时：在 `kanzi-properties-quickref/SKILL.md` 中**搜索定位**目标属性/分组，只取命中段落。

## ⚠️ 上下文保护规则

- **绝不整读** `kanzi-properties-quickref`（48KB 单文件）。用搜索/定位只取需要的段落或行。
- 全量版（kanzi-properties-2d/3d/...）同样只读目标节点章节，不要整读。
- 每次查询属性，读取的内容控制在**单个属性分组**以内（≤ 几 KB）。
