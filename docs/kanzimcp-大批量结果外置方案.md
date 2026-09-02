# KanziMCP 大批量结果外置方案（会话 token 优化）

> 版本：v1（方案讨论稿，未动代码）
> 日期：2026-09-02
> 作者：kanzimcp agent（与老隋讨论定稿）

## 一、问题

KanziMCP 的**所有列举/查询类操作**（`get_Properties`/`get_Children`/查图片目录/`kz_loc_entry_list` 整表/`get_Translations` 等）都会把**全量数据**灌进 AI 上下文：

- 会话累计 token 消耗惊人；
- AI 为判断"属性/资源/条目是否存在"做**防御性查询**，进一步放大；
- 真实场景如"文件夹全部图片→批量建 texture"确实需要全量，但用反复单条查询拼出来，每步都是高 token 往返。

## 二、核心思路（老隋定调）

把**大批量结果从对话上下文移出，落盘成文件**，AI 只拿**文件映射**，需要时才去取。

- **数据流**：`Kanzi → relay(WS 大JSON) → kz_mcp_http → 落盘中继机临时文件(TTL自删) → 返回 file:URL+计数+摘要 → AI GET 取全量`
- **Kanzi 插件不动、feishu_bridge 不参与**（AI 调 Kanzi 走链A：`kz_mcp_http → relay → Kanzi`，不经 feishu_bridge）。
- **中继机落一份临时文件** + 过期自动清理（Windows 中继机）。
- **kz_mcp_http 服务多个 AI 连接**，方案需保证多 AI 并发安全。

## 三、定稿参数

| 项 | 定稿值 |
|----|--------|
| 落点 | `kz_mcp_http.py`（单点） |
| 文件格式 | **UTF-8 JSON**（Kanzi 结果本就是 JSON 结构，天然格式） |
| 触发阈值 | 结果 >50 条 **或** **>4KB** 才外置；小的照旧直返 |
| 临时目录 | 中继机 kz_mcp_http 工作目录下 `tmp_results/` |
| 文件 ID | guid，每次请求唯一（多 AI 不冲突） |
| TTL | 30 分钟 |
| 清理 | kz_mcp_http 内嵌定时任务（每 10-30 分钟扫一次，删过期文件） |
| 返回格式 | `URL · 文件大小 · 记录数 · 简短摘要` |
| 新端点 | kz_mcp_http 9001 上新增 `GET /data/<id>`（AI 本就能访问 9001） |

## 四、架构（目标数据流）

```
[Kanzi 机]  --大JSON-->  [relay(58080)]  --WS-->  [kz_mcp_http(9001)]
                                                       │
                                          ┌────────────┴─────────────┐
                                          │ 超过阈值?                │
                                          │  否→照旧直接返回给 AI     │
                                          │  是→落盘 tmp_results/<id>.json
                                          │      + 返回file:URL+摘要  │
                                          └────────────┬─────────────┘
                                                       ▼
                                            [中继机 tmp_results/]
                                                       │ (TTL 30min, 定时删)
                                                       ▼
                                          [AI 机] GET /data/<id> 取全量
```

多 AI 并发安全：
- 每个 AI 请求被 kz_mcp_http 按 `X-Kanzi-User` 隔离到各自 relay client 槽；
- 落盘文件 ID 每次请求 guid 唯一，互不覆盖；
- `file:` URL 只在**那次响应的**返回里出现，其它 AI 拿不到。

## 五、改动点（kz_mcp_http.py，Kanzi 插件/feishu_bridge 不动）

1. **`HttpMcpServer._handle_jsonrpc`（tools/call 分支）**：拿到 Kanzi 返回的 `result` 后，判断是否超过阈值；
   - 未超 → 原样返回（现状不变）；
   - 超 → 序列化成 UTF-8 JSON 写入 `tmp_results/<guid>.json`，返回里替换成 `外置文件结构`（见下节）。

2. **新增落盘模块**：`write_result_file(data) -> {id, path, url, entries, summary}`：
   - guid 生成；写入 `tmp_results/<id>.json`（UTF-8）；
   - 计算 `entries`（集合元素数）与 `summary`（前几条 + ref_id）。

3. **新增 GET 端点 `/data/<id>`**：读取临时文件返回（Content-Type: application/json; charset=utf-8）；
   - 不存在 → 404。

4. **新增定时清理任务**：`sweep_tmp()`，每 10-30 分钟扫 `tmp_results/`，删 mtime 超过 TTL(30min) 的文件；
   - 在 `main()` 的事件循环里 `create_task` 常驻。

5. **可配置项**（命令行参数，带默认值）：
   - `--result-tmp-dir`（默认 `./tmp_results`）
   - `--result-threshold-entries`（默认 50）
   - `--result-threshold-bytes`（默认 4096）
   - `--result-ttl-seconds`（默认 1800）
   - `--result-sweep-seconds`（默认 1800）
   - **`--result-public-host`（默认无，用 `--listen` 的 host）**：文件 URL 里对 **AI 可达** 的中继机真实 IP。**当监听用 `0.0.0.0` 而 AI 与中继不在同一台机器时，必须配此真实 IP**（否则返回的 `http://0.0.0.0:9001/data/...` AI 连不回去，参考 feishu_bridge 的 http_bind_ip 做法）。示例：`--result-public-host 10.10.118.152`

   > ⚠️ 2026-09-02 实测踩坑：URL 直接用了监听地址 `0.0.0.0`，导致跨机 AI 拿不到文件、copilot 误判"未启用外置"。已在代码加此参数并告警（检测到 0.0.0.0/127.0.0.1/localhost 时提示应配真实 IP）。

## 六、返回格式示例

未超阈值（小结果，现状不变）：
```json
{ "result": { "content": [ { "type": "text", "text": "✅ 结果: xxx" } ] } }
```

超阈值（外置）：
```
✅ 结果较大，已外置到文件：
URL: http://<中继机IP>:9001/data/8f3c...a1.json
大小: 45.2 KB
记录数: 991
摘要: adas, green_sig_num, day, night, ... 等
需要全部数据请 GET 上述 URL；需要单条用其 ref_id 直接 kz_invoke。
```

## 七、AI 侧约定（skill/提示词辅助，非强依赖）

- AI 收到 `file:` 字段时，知道是**外置的大结果**，可用 HTTP GET（copilot/nlp 有抓取能力）取全量；
- 判断"是否存在"靠 `entries: N`（总数 >0 即可），**无需取全量文件**；
- 需要全部（如所有图片建 texture）才 GET 文件，取后自行消费、用完不长期保留。

## 八、优点

- **单点改动**（kz_mcp_http.py），Kanzi 插件（红线，Kanzi 专属）与 feishu_bridge 都不动；
- 所有列举/查询类大结果**一次覆盖**，不靠 AI 自觉、不需加一堆工具；
- 判断存在性靠总数，不受影响；真要全量有文件可取；
- 只在中继机落**一份临时**文件（TTL 自动清），源头 Kanzi 不落盘、AI 拿走自用，规避三份冗余；
- 多 AI 并发安全（guid 唯一 + 按用户隔离）。

## 九、待确认 / 后续

- ⚠️ 默认阈值已由老隋定为 **>50 条 或 >4KB**；返回格式定为 **URL · 文件大小 · 记录数 · 简短摘要**（2026-09-02 确认）。
- 落盘目录建议放 kz_mcp_http 工作目录下、与程序同生命周期，便于管理；
- 记录数/文件大小由落盘时计算，摘要取前几条（条数可配置，默认 5-10）；
- 方案认可后，再进入实施（仍只改 kz_mcp_http.py，Kanzi 插件红线不动）。

## 十、相关文件（只读参考，不改）

- `kz_mcp_http.py`：`HttpMcpServer._handle_jsonrpc` / `main` / 新增端点
- relay_multi / feishu_bridge：不参与本次改动
- skill：kanzi-ui / kanzi-resource-create（高频列举场景对应）