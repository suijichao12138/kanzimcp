# Kanzi Skill MCP 方案（skill 按需查询，治本方案）

> 状态：**已实现**（2026-10-15 完成 deployer skill 管理 + skill MCP 服务，端到端测试通过）
> 作者：kanzimcp agent | 日期：2026-10-14
> 背景：nlp_worker 全量注入 skill 导致 Copilot 上下文超限，现用「index 搜索定位」缓解，本方案是根治。

---

## 一、问题根源

nlp_worker 建会话时把 `skills.entries` 里 **enabled 的所有 SKILL.md 全量注入 system prompt**
（`load_skills()` → `<configured_skills>...</configured_skills>`，见 copilot_runtime.py:1406）。

- skill 库现状 ≈758KB（7 个全量属性版 ~460KB + 原有常用 ~180KB + 其他）
- 默认上限 `max_total_bytes: 512KB` → 全开必爆，症状 `Copilot returned no assistant message`
- 已采取的缓解措施（非根治）：
  1. **config 只加载 kanzi-skills-index（3KB 导航）**，其余靠 Copilot 读文件
  2. **index 写搜索定位指引**：查属性时搜索 quickref 只取命中段落，不整读
  - 局限：依赖 Copilot 自觉遵守「只读段落」；冷门属性难搜到；skill 增加时 index 要手动维护

**本质**：skill 是「内容」，被当「提示词」全量加载。skill 库会持续增大，这条路必然再爆。

## 二、方案核心思路

**把 skill 变成 Copilot 能精确调用的「工具」** —— 查什么返回什么，几十字节到几 KB。

实现位置：**9001 聚合网关 `kz_mcp_http.py` 增加一个本地 MCP 端点 `/kanzi_skill_mcp`**
（不是新起服务，是网关内新增一个处理器，与官方 api/doc 端点并列）。

## 三、架构现状（已确认）

```
9001 网关 kz_mcp_http.py（三端点聚合，自建，python，mcp_server/relay_nlp_http/http/）
  ├─ /mcp              → 本地 studio（ws relay 到 Kanzi Studio）
  ├─ /kanzi_api_mcp    → 官方 api.mcp.kanzi.com（OfficialMcpHttpClient 封装）
  └─ /kanzi_doc_mcp    → 官方 docs.mcp.kanzi.com（OfficialMcpHttpClient 封装）
```

> ⚠️ 关键事实：`kanzi-doc-mcp` / `kanzi-api-mcp` 都是 **Kanzi 官方云服务**，不是自建。
> 所以 skill 查询逻辑必须自己写（参考 `http/official_mcp.py` 的 MCP 协议封装模式）。

## 四、工具设计（详细版，2026-10-15 补全）

### 工具总览

| 工具 | 作用 | 返回大小 |
|------|------|---------|
| `search_property(query, limit?)` | 搜索属性表（quickref 257 + 全量版），返回**匹配行**（UI名\|绑定写法\|说明） | 几十字节~几KB |
| `list_skills()` | 所有 skill 的名字 + 一句话用途（自动扫描生成） | ~3KB |
| `get_skill_summary(name)` | 某 skill 的 description + 章节标题列表 | ~1KB |
| `read_skill_section(name, heading)` | 按章节标题读某 skill 的一段，控制大小 | 按段返回 |

**核心是 `search_property`**：精确到行，绝不整读大文件。Copilot 不用「自觉」，工具强制返回精确结果。

### 4.1 search_property —— 参数设计（核心）

**只一个参数 `query`（string）+ 可选 `limit`（默认 5，最大 10）**。
不搞结构化（不传 group/type），Copilot 不可能传错。

**宽容匹配（多路评分）—— 关键：Copilot 传什么词都能命中**：

| 匹配方式 | 例子（query=width） | 分 |
|---------|------|-----|
| 属性名包含关键词 | `width` ∈ `Actual Layout Width` | +10 |
| 绑定名包含关键词 | `width` ∈ `Node.ActualWidth` | +8 |
| 描述包含关键词 | `width` ∈ "The calculated width..." | +3 |
| 词边界精确命中 | `\bwidth\b` | +5 |
| 中文同义词映射 | 「宽度」→ width、「字号」→ font size | +10 |
| 拼写容错（可选） | `wodth` → width（编辑距离 ≤1） | +6 |

**返回 top-N 按分排序**，最相关的排最前。已用真实 quickref 数据实测：
`search_property("width")` → 13 条，`Actual Layout Width` 和 `Layout Width` 并列高分排 top-2 ✅

**返回 JSON 格式**：
```json
{
  "query": "actual width",
  "matches": [
    {
      "ui_name": "Actual Layout Width",
      "binding": "{@../Node.ActualWidth}",
      "desc": "布局算完后的实际宽度（只读）",
      "group": "Layout.Item",
      "score": 26
    }
  ],
  "total": 2
}
```

**未命中兑底**：返回 `{"matches": [], "hint": "未找到，试试这些关键词：layout/font/color/opacity/..."}`，引导 Copilot 换词再试。

### 4.2 工具 description（Copilot 的教学，藏在描述里）

```
search_property(query, limit?): 搜索 Kanzi 属性表。
  用法：传入你想查的属性关键词，如 "actual width"、"font size"、"text color"。
  返回匹配的属性行，每行含 UI 面板名、绑定表达式写法、说明。
  需要查任何 Kanzi 属性的绑定写法/面板名称时调用本工具，不要直接读取 skill 文件。
  查不到时换更短的关键词再试（如 "width" 而非 "actual layout width"）。
```

**工具发现靠 SDK 自动注入**（像现有 kanzi-studio-mcp 的 31 个工具一样），不需要专门 skill 教 Copilot 怎么用。

### 4.3 Copilot 调用完整链路（示例）

```
用户：把 A 节点宽度绑成 B 节点实际宽度
   ↓
Copilot 看到工具 search_property（描述写"查属性调用"）
   ↓
调 search_property({"query": "actual width"})   ← 传什么词都行，工具宽容
   ↓
返回 [Actual Layout Width → {@../Node.ActualWidth}]
   ↓
Copilot 直接写绑定：clamp(50, 120, {@../Node.ActualWidth} / 5)
```

### 4.4 数据源与索引

- **属性索引**：启动时解析 quickref（257 条） + 全量版 7 个（~2.1 万条） → 内存列表（毫秒级）
- **skill 索引**：扫描 `skills/` 目录，读每个 SKILL.md 的 frontmatter（name/description）+ 章节标题
- 缓存到 `skills/.skill-index.json`（可选，加速启动）
- **数据目录可配置**：config 里指定 skills 根路径

## 五、改动量评估

| 部分 | 工作量 | 说明 |
|------|--------|------|
| `skill_mcp.py`（新写） | ~200 行 python | 扫描 skills/ 目录建索引 + 搜索实现，复用 official_mcp.py 的 MCP 响应格式 |
| `kz_mcp_http.py` 挂载 | ~20 行 | 照 OFFICIAL_ENDPOINTS 模式加 `/kanzi_skill_mcp` 路由 |
| 数据索引（启动扫描） | ~50 行 | 快，500 属性量级 |
| `config.yaml` 加 mcp_servers | 5 行 | 照 doc-mcp 抄一条 |
| 测试/部署 | 半天 | 与 Kanzi Studio 联动验证 |

**总计 ≈300 行新代码 + 半天**，不动现有逻辑。

## 六、skill 增加时的表现（关键优势）

1. **新 skill 零配置接入**：处理器启动时扫描 `skills/` 目录自动发现新 SKILL.md，自动建索引。
   加 skill 不用改代码、不用改 config —— 根治「skill 库一直长大」。
2. **搜索兜底**：新加的 skill 即使没写进 index，`search_property` / `read_skill_section` 也能搜到内容。
3. **上下文可控**：工具返回精确行/段落，**永远不整读大文件**。skill 涨到 10MB 也不怕
   —— 因为加载的是「工具」不是「内容」。
4. **和 index 方案互补**：index（3KB）仍是轻量入口，告诉 Copilot 有这些工具；实际查内容走工具。

## 七、与现状方案对比

| 维度 | 现状（index 搜索定位） | Skill MCP 方案 |
|------|----------------------|----------------|
| 上下文占用 | 靠 Copilot 自觉只读段落 | 工具强制返回精确结果 |
| skill 增加 | 每次手动更新 index | 自动扫描，零维护 |
| 冷门属性 | 难搜到 | search_property 全量搜 |
| 改动量 | 已完成（配置改动） | ~300 行 + 半天 |

## 八、实施步骤（已完成，2026-10-15）

1. 写 `skill_mcp.py`：扫描 skills/ → 建属性索引（quickref + 全量版）→ 实现 4 个工具
2. `kz_mcp_http.py` 挂 `/kanzi_skill_mcp` 端点（复用鉴权/大结果外置逻辑）
3. 本地测试：curl 直接调 4 个工具验证
4. `config.yaml` 加 mcp_servers 条目（照 doc-mcp 抄）
5. nlp_worker 会话里让 Copilot 调 `search_property` 验证
6. 验证 OK 后按 git 流程提交（等老隋明确指令才推 GitHub）

## 九、风险与注意

- **动 9001 网关 = nlp_worker 链路核心组件**，必须先老隋明确点头再动工
- 索引文件放哪：建议 skill 目录旁一个隐藏索引文件（如 `skills/.skill-index.json`），
  避免每次启动全扫（虽然 500 属性量级扫一次也就毫秒级）
- 若 Copilot 会话工具太多，search_property 可与现有 kanzi-doc-mcp 的 search_docs 区分职责：
  doc 查官方文档，skill-mcp 查本地 skill
- 部署位置默认与 kz_mcp_http.py 同机（9001），用户无感

## 十、配套指引（双保险，可选但推荐）

MCP 工具靠 SDK 自动注入，**不需要专门的「怎么用工具」skill**。但为了钉死 Copilot 行为、
防止它偷懒去读大文件，在现有 `kanzi-skills-index`（4KB）里加 5 行：

```
## 工具使用规则（MCP 可用时）
- 查属性 → 调 search_property，禁止直接读 kanzi-properties-* 大文件
- 查操作步骤 → 调 read_skill_section，禁止整读 SKILL.md
- 工具结果够用就用工具，只有工具查不到才读文件（且只读命中段落）
```

这样 system prompt 仍很小（4KB + 5 行），Copilot 既知道工具有哪些，又被指引钉住「用工具不读文件」。

---

*关联：nlp-worker-skill-loading skill（加载机制/排查）、kanzi-skills-index（现用导航）、
copilot_runtime.py（load_skills 全量注入实现）*
