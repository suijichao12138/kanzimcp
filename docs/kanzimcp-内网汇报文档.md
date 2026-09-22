# Kanzi MCP 内网系统 · 汇报文档

> **文档版本**：v1.0
> **编写日期**：2026-09-20
> **适用范围**：**仅限内网（Intranet）部署与使用**
> **代码基线**：仓库 `kanzimcp`，当前发布版本 **v6**（2026-09-16）
> **编写原则**：本文所有配置字段、启动参数、常量值均取自仓库源码与配置文件实际内容，未做推测。

---

## 目录

1. [系统概述](#一系统概述)
2. [整体架构](#二整体架构)
3. [组件详解](#三组件详解)
4. [配置文件与启动参数全表](#四配置文件与启动参数全表)
5. [从零搭建指导](#五从零搭建指导)
6. [部署与运维](#六部署与运维)
7. [OTA 自动更新](#七ota-自动更新)
8. [优缺点分析](#八优缺点分析)
9. [常见问题与排查](#九常见问题与排查)
10. [附录](#十附录)

---

## 一、系统概述

### 1.1 系统定位

一套部署在**内网**的桥接系统，把 **Kanzi Studio 的 MCP 能力**开放给 **GitHub Copilot** 与 **飞书**。

用户在飞书里用自然语言下指令 → Copilot 理解并规划 → 通过 MCP 直接操作 Kanzi Studio → 结果（含截图、文件、JSON 数据）回传到飞书。

**典型使用场景：**

- 「把 Title_Layout 的位置改到 X:0 Y:115」
- 「截个图看看现在 Preview 长什么样」
- 「在本地化表里加一条 en/zh-CHS 的翻译」
- 「新建一个红到黄的渐变材质刷」
- 「保存工程并导出 kzb」

### 1.2 核心调用链

```
[飞书用户]
    │ 自然语言消息
    ▼
feishu_bridge（飞书桥，nlp_client 角色）
    │ WebSocket
    ▼
relay_multi（中继，:58080）
    │
    ▼
nlp_worker（Copilot 执行器，nlp_worker 角色）
    │ HTTP MCP（带 X-Kanzi-User 头）
    ▼
kz_mcp_http（HTTP MCP 服务器，:9001，client 角色）
    │ WebSocket
    ▼
relay_multi（同一中继）
    │
    ▼
Kanzi Studio MCP 插件（server 角色）
    │
    ▼
[Kanzi Studio 实际操作]
```

### 1.3 六项关键设计

| # | 设计点 | 说明 |
|---|---|---|
| 1 | **中继为中心** | 所有组件只连 relay，组件间互不直连 → 完全解耦，任一组件可独立重启 |
| 2 | **通道即用户** | relay 的 URL 路径段 = 用户名 = 通道名 → 天然多用户隔离 |
| 3 | **四角色分槽** | 每通道 4 个槽：`server` / `client` / `nlp` / `nlp_worker` |
| 4 | **多 bot 单进程** | 一个 feishu_bridge 进程管 N 个飞书机器人，各自独立通道 |
| 5 | **热更新** | 飞书 bot 列表、HTTP 白名单改配置文件即生效，**不重启** |
| 6 | **Kanzi 离线即报错** | 代码已实现（对应 v7 变更），Kanzi 不在线时立即回错误，不再积攒请求 |

---

## 二、整体架构

### 2.1 部署拓扑

```
┌───────────────────────────────────────────────────────────────────┐
│  中继机（内网服务器，示例 10.10.118.152）                            │
│                                                                   │
│  ┌────────────────┐  ┌────────────────┐  ┌────────────────────┐  │
│  │ relay_multi    │  │ kz_mcp_http    │  │ feishu_bridge      │  │
│  │ :58080 (WS)    │  │ :9001 (HTTP)   │  │ :8081 (文件服务)    │  │
│  └────────────────┘  └────────────────┘  └────────────────────┘  │
│                                                                   │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │ ota_agent（可选：从内网 Git 镜像拉取 → 本地编译 → 替换 →   │ │
│  │            健康检查 → 失败回滚 → 飞书通知）                  │ │
│  └─────────────────────────────────────────────────────────────┘ │
└───────────────────────────────────────────────────────────────────┘
        ▲                      ▲                       ▲
        │ WebSocket            │ WebSocket             │ 飞书长连接
        │                      │                       │
┌───────┴────────┐   ┌─────────┴────────┐   ┌─────────┴────────┐
│  Kanzi 机       │   │  Copilot 机       │   │  飞书服务端      │
│  (Windows)      │   │  (Windows)        │   │  (企业内部租户)  │
│                │   │                   │   │                 │
│ Kanzi Studio   │   │ nlp_worker.exe    │   │                 │
│ + MCP 插件      │   │ Copilot SDK       │   │                 │
│ (server 角色)   │   │ (nlp_worker 角色) │   │                 │
└────────────────┘   └───────────────────┘   └─────────────────┘
```

> **部署灵活**：三台机器可以合一（全部跑在中继机上），也可以分散。组件之间只依赖内网 IP + 端口。

### 2.2 relay 通道内部结构

每条通道（每个用户名）维护 4 个角色槽：

| 槽位 | 连接方 | 允许多连接 | 空闲回收 | 说明 |
|---|---|---|---|---|
| `server` | Kanzi Studio MCP 插件 | ❌ 新顶旧 | **永不回收** | 提供 Kanzi 能力 |
| `client` | kz_mcp_http | ✅ **并存** | 120s 空闲回收 | 与 server 双向直通，按 id 定向回传（未命中时兜底回主 client） |
| `nlp` | feishu_bridge | ❌ 新顶旧 | **永不回收** | 用户输入入口 |
| `nlp_worker` | nlp_worker（Copilot） | ❌ 新顶旧 | **永不回收** | 指令执行器 |

**通道内部数据流：**

```
nlp ──user_message / user_choice──→ nlp_worker
nlp_worker ──claude_output / thinking / progress──→ nlp
client ──mcp_request──→ server
server ──mcp_response──→ client（按 JSON-RPC id 定向回传）
server ──mcp_response（包装）──→ nlp_worker（额外副本）
```

**定向回传机制**：通道维护 `route: {请求id → client连接}` 映射。server 返回响应时按 id 找到发起该请求的 client 连接。

具体规则（照 `_handle_server` 实际逻辑）：

1. 取出 `route[req_id]` —— **取用即 `pop`，映射是一次性的**
2. 命中 → 只发给发起该请求的那条 client 连接（`continue`，不再走下面）
3. **未命中（无 id 或未知 id，即连接级消息）→ 兜底回给 `ch["client"]`（主连接 = 该槽最后加入的那条）**
4. **无论命中与否，Kanzi 的响应都会额外包装一份 `{"type":"mcp_response","text":<原文>}` 发给 `nlp_worker` 槽**（供 Copilot 感知 Kanzi 返回）

> **补充**：relay 的 `client` 槽允许多连接并存（`MULTI_OK_SLOTS = ("client",)`），
> 但 **kz_mcp_http 每个用户只开一条**（懒加载复用）。所以「多 client 并存」主要发生在
> 同一通道内有多个 HTTP 客户端/脚本直连的场景。
>
> **兜底的影响**：多 client 并存时，若某条响应丢了 id（连接级消息），会统一发给**主连接**，
> 而非发起者。正常 MCP 请求都带 id，实际很少走到这条分支。

### 2.3 连接生命周期（三层回收）

`relay_multi.py` 的清理策略（常量定义在第 39~41 行）：

| 层级 | 触发条件 | 常量 | 值 |
|---|---|---|---|
| ① 断开即收 | WebSocket 连接关闭 | — | 立即 |
| ② 单连接空闲 | 无收发消息 | `CONN_IDLE_TIMEOUT` | 120s |
| ③ 整通道闲置 | 全部槽位为空 | `CHANNEL_IDLE_TIMEOUT` | 600s |
| 扫描周期 | 后台 `_sweep_loop` | `SWEEP_INTERVAL` | 30s |

**两条关键例外（防止误杀长期空闲但有效的连接）：**

1. **核心槽永不空闲回收** —— 只有 `client` 槽参与空闲回收
   （早期版本的核心槽也回收，导致 Kanzi 挂机 2 分钟就被踢、Copilot 长时间思考被断开）

2. **主通道永不整通道清理** —— 曾有过 `server` 连接的通道标记 `is_primary = True`，
   不再参与整通道闲置回收

---

## 三、组件详解

### 3.1 relay_multi —— WebSocket 中继

| 项 | 值 |
|---|---|
| 源文件 | `mcp_server/relay_nlp_http/relay/relay_multi.py` |
| 产物 | `relay_multi.exe` |
| 监听 | `0.0.0.0:58080`（**硬编码**） |
| Python 依赖 | `websockets` |
| 启动 | `relay_multi.exe`（无参数） |

**职责**：全系统连接中心。按 URL 路径分通道，按首帧 `role` 字段分槽，做消息转发、定向回传、连接回收、离线判定。

**启动方式（`main()`，第 549 行）：**

```python
async def main():
    relay = MultiRelay()
    port = 58080                       # ← 端口硬编码在此
    asyncio.get_event_loop().create_task(relay._sweep_loop())
    process_request = make_process_request(relay)
    async with websockets.serve(relay.handle, "0.0.0.0", port,
                                process_request=process_request):
        log.info(f"🔄 MCP 中继 ws://0.0.0.0:{port}")
        await asyncio.Future()
```

**⚠️ 端口不可通过参数修改。** 如需改端口，必须改源码第 551 行 `port = 58080` 后重新打包。

**角色识别规则：**

| 首帧内容 | 分到槽位 |
|---|---|
| `{"role":"server", ...}` | `server` |
| `{"role":"client", ...}` | `client` |
| `{"role":"nlp_client", ...}` | `nlp` |
| `{"role":"nlp_worker", ...}` | `nlp_worker` |
| 无 `role` 字段 | 默认按 `client` 处理 |

> **注意**：连接建立后**第一帧必须带 `role`**。裸 JSON-RPC（不带 role）会被当 client 处理，
> 容易出现「已连接但收不到响应」的困惑。

**Kanzi 离线即报错（v7 变更，已合入代码）：**

Kanzi（server 槽）不在线时，client 的请求**立即返回错误**，不再无限等待或积攒：

```json
{"jsonrpc":"2.0","id":"<原样透传的id>","error":{"code":-32000,
 "message":"Kanzi Studio 未连接（Server 不在线），请求未执行"},
 "channel":"<通道名>"}
```

由 `build_kanzi_offline_error(msg, name)`（第 68 行）构造。实测 5/5 请求均秒回错误、id 全部对齐。

**server 断开广播：**

Kanzi 断开时向 nlp 槽推送：

```json
{"type":"server_disconnected","text":"Kanzi MCP 连接已断开"}
```

**worker 上下线事件（由 relay 推送给 nlp 槽）：**

| 事件 | 位置 | 内容 |
|---|---|---|
| `worker_online` | 第 438 行 | nlp_worker 槽新连上时推送 |
| `worker_disconnected` | 第 471 行 | nlp_worker 槽断开时推送 |

`sweep` 回收 nlp_worker 时同样触发 `worker_disconnected`。

**启动日志（正常输出）：**

```
🔄 MCP 中继 ws://0.0.0.0:58080
   路径区分通道: ws://ip:58080/用户名
   Server:      ws://ip:58080/用户名
   Client:      ws://ip:58080/用户名（多连接并存, 定向回传）
   NLP Client:  ws://ip:58080/用户名  (聊天插件)
   NLP Worker:  ws://ip:58080/用户名  (Claude 执行器)
   ♻️ 回收: 断开即收 + 空闲120s + 整通道闲置600s
```

---

### 3.2 kz_mcp_http —— HTTP MCP 服务器

| 项 | 值 |
|---|---|
| 源文件 | `mcp_server/relay_nlp_http/http/kz_mcp_http.py` |
| 产物 | `kz_mcp_http.exe` |
| 默认监听 | `0.0.0.0:9001` |
| Python 依赖 | `websockets` |
| 启动 | `kz_mcp_http.exe --config config.json` |

**职责**：把 relay 的 MCP 通道开放为 **streamable HTTP 端点**。
（Copilot 只支持 http/sse 传输，不支持 stdio，所以必须有这一层。）

**单进程多用户**：每个用户名对应一个独立 relay 通道，由 `X-Kanzi-User` 请求头决定连哪条通道。

**连接模型（重要，容易误解）**：

| 层 | 行为 |
|---|---|
| **http 侧** | **每个用户一条 relay 连接**（懒加载：首次请求建立，之后请求复用） |
| **relay 侧** | `client` 槽**允许多连接并存**，靠 `route[req_id]` 定向回传 |

> **为何 http 侧只用一条**：喂狗（`kz_health`）探活需要回填 `_active_req`。
> 若每请求新建连接，新 handler 的喂狗还没回填就把请求判死
> （历史实测：会导致所有请求误杀）。所以喂狗与业务**共用同一条连接**。
>
> **「脚本独立」靠什么实现**：靠 **relay 通道隔离** —— 脚本用**不同的 `X-Kanzi-User`**
> 即进入**不同通道**，天然不与 Copilot 抢连接。若脚本与 Copilot 用**同一个**
> `X-Kanzi-User`，它们实际上共用同一条 http 连接。
>
> **防误杀脚本请求**：`IDLE_GRACE_ROUNDS = 3`（连续 3 轮观察 `active_req` 为空才判链路坏），
> 给插件回填留出宽容窗口。
>
> **Kanzi 离线时**：relay **不拒连**（连接保持），客户端每条请求直接收到离线错误。
> 历史版本曾用 WebSocket `4001` 拒连，现已废弃（代码中 4001 分支仅作旧版兼容保留）。

#### 3.2.1 安全模型

| 机制 | 说明 |
|---|---|
| 白名单制 | 请求必须带 HTTP 头 `X-Kanzi-User: <用户名>` |
| 名单外/无头 | 直接返回 **403** |
| 白名单热更新 | 改 `users.json` 保存即生效，**不用重启**。实现：每次请求校验前比对文件的 **mtime**，变了才重读（不是定时轮询；3s 那个是飞书桥的配置热更新） |
| 白名单为空 | **拒绝启动**（防误配成裸奔） |

#### 3.2.2 HTTP 端点

| 端点 | 类型 | 说明 |
|---|---|---|
| `/mcp` | 本地 studio（主） | 经 relay 到 Kanzi Studio 插件 |
| `/kanzistudio_mcp` | 本地 studio（别名） | 与 `/mcp` **完全等价** |
| `/kanzi_api_mcp` | 官方代理 | Kanzi 官方 API 文档 MCP |
| `/kanzi_doc_mcp` | 官方代理 | Kanzi 官方 Doc MCP |
| `/data/<file>` | 结果下载 | 大批量结果外置文件下载 |

官方端点映射（源码第 612~614 行）：

```python
self.OFFICIAL_ENDPOINTS = {
    "/kanzi_api_mcp": (self.kanzi_api, "kanzi-api"),
    "/kanzi_doc_mcp": (self.kanzi_doc, "kanzi-doc"),
}
```

#### 3.2.3 大批量结果外置机制

MCP 返回内容过大时（如本地化表导出 991 行），若直接塞进 Copilot 上下文会撑爆 token。
因此超过阈值的内容会**落盘为 JSON 文件**，只回摘要 + 下载 URL，Copilot 再用
`artifact_download` / `artifact_read` / `artifact_json_query` 按需读取。

| 配置项 | 默认 | 说明 |
|---|---|---|
| `result_threshold_entries` | 50 | 数组记录数超此值触发外置 |
| `result_threshold_bytes` | 4096 | 文本字节数超此值触发外置 |
| `result_ttl` | 1800 | 外置文件存活秒数（30 分钟） |
| `result_tmp_dir` | `tmp_results` | 落盘目录 |
| `result_public_host` | `null` | 结果 URL 中使用的对 AI 可达 IP（**跨机部署必配**） |
| `RESULT_SWEEP_SECONDS` | 1800 | 后台清理扫描周期 |

**自动清理**：后台定时任务扫描 `result_tmp_dir`，删除超过 `result_ttl` 的 `.json` 文件。

#### 3.2.4 链路健康检测

| 配置项 | 默认 | 说明 |
|---|---|---|
| `heartbeat_interval` | 5 | 向 Kanzi 发 `kz_health` 喂狗间隔（秒） |
| `heartbeat_max_fails` | 3 | 连续 N 次无响应即判链路坏 |
| `mcp_timeout` | 300 | 单次 MCP 请求转发超时（秒） |
| `req_check_interval` | 2 | 单个请求周期检查间隔（秒） |

---

### 3.3 nlp_worker —— Copilot 执行器

| 项 | 值 |
|---|---|
| 源文件 | `mcp_server/relay_nlp_http/nlp_worker/nlp_worker.py` |
| 产物 | `nlp_worker.exe`（portable 打包） |
| 配置文件 | `config.yaml`（YAML） |
| Python 依赖 | `github-copilot-sdk>=1.0.11,<1.1`、`httpx>=0.28,<1`、`pydantic>=2.11,<3`、`python-dotenv>=1.1,<2`、`PyYAML>=6.0.2,<7`、`websockets>=15,<16` |
| 启动 | `nlp_worker.exe --config config.yaml` |

> **⚠️ 重要：`nlp_copilot` 已废弃，现役执行器是 `nlp_worker`。**
> 仓库中 `nlp_copilot/` 目录**仍存在**（仅作历史保留），新部署一律使用 `nlp_worker/`，
> 不要启动、不要配置 `nlp_copilot`。

**职责**：通过 GitHub Copilot SDK 驱动常驻会话，接收 relay 转发的 `user_message`，交给 Copilot 规划执行（可调用 MCP 工具操作 Kanzi），把 `claude_output` / `thinking` / `progress` 回传 relay。

#### 3.3.1 启动参数（仅 3 个）

| 参数 | 默认 | 说明 |
|---|---|---|
| `--config PATH` | exe 旁的 `config.yaml` | YAML 配置路径 |
| `--validate-config` | — | 只校验配置（含路径存在性检查），不连接 |
| `--list-models` | — | 列出当前 Git 账号可用模型后退出 |

#### 3.3.2 顶层配置结构

```yaml
relay:         # 中继连接与身份
copilot:       # Copilot SDK / 模型 / 权限
skills:        # SKILL.md 技能包加载
mcp_servers:   # MCP 服务端点（指向 kz_mcp_http）
artifacts:     # 远程产物下载策略
compatibility: # 与飞书桥的兼容层
messages:      # 消息队列
storage:       # SQLite 会话存储
logging:       # 日志与轮转
```

#### 3.3.3 能力要点

| 能力 | 实现 |
|---|---|
| **会话持久化** | SQLite 记录 conversation key → SDK session ID；重启后 `resume_session()` 恢复上下文 |
| **会话恢复失败策略** | `resume_failure: error / new` |
| **配置指纹校验** | `configuration_change: error / new` —— 配置变了就新建会话，避免脏上下文 |
| **活动刷新式超时** | `max_idle_seconds` 内只要还有事件就续期，长任务不误报超时 |
| **大输出落盘** | `large_output`，路径模板必须含 `{session_id}` |
| **权限模型** | `allow` / `deny` / `ask`；**无审批 UI 时 `ask` 按 `deny` 处理** |
| **技能加载** | 从 `skills.entries[].path` 加载 SKILL.md，总字节数受 `max_total_bytes` 限制 |
| **飞书命令** | `/new`、`/status`、`/cancel`、`/help` |

#### 3.3.4 便携版目录与脚本

| 文件 | 作用 |
|---|---|
| `run.cmd` | 启动：自动从 `.example` 复制出 `config.yaml` / `.env`，再跑 `nlp_worker.exe --config config.yaml` |
| `login_copilot.cmd` | 首次登录：设置 `COPILOT_HOME=%~dp0.copilot-data`，调 `_internal\runtime\copilot.exe login` |
| `build_portable.cmd` | 打包便携版 |
| `nlp_worker.spec` | PyInstaller 规格文件 |
| `.copilot-data/` | Copilot 登录凭据 + 会话状态（`base_directory`） |

**`run.cmd` 实际内容：**

```bat
@echo off
setlocal
cd /d "%~dp0"

if not exist "config.yaml" (
  copy "config.example.yaml" "config.yaml" >nul
  echo Created config.yaml. Edit it before production use.
)
if not exist ".env" (
  copy ".env.example" ".env" >nul
  echo Created .env. Replace placeholder credentials before production use.
)

"%~dp0nlp_worker.exe" --config "%~dp0config.yaml" %*
if errorlevel 1 pause
endlocal
```

**`login_copilot.cmd` 实际内容：**

```bat
@echo off
setlocal
cd /d "%~dp0"
set "COPILOT_HOME=%~dp0.copilot-data"
set "COPILOT_RUNTIME=%~dp0_internal\runtime\copilot.exe"

if not exist "%COPILOT_RUNTIME%" (
  echo ERROR: Bundled Copilot Runtime not found:
  echo   %COPILOT_RUNTIME%
  echo Re-extract the complete portable folder and try again.
  pause
  exit /b 2
)

"%COPILOT_RUNTIME%" login
set "LOGIN_EXIT_CODE=%ERRORLEVEL%"
...
```

---

### 3.4 feishu_bridge —— 飞书 ↔ Kanzi 桥

| 项 | 值 |
|---|---|
| 源文件 | `mcp_server/relay_nlp_http/feishu/feishu_bridge.py` |
| 产物 | `feishu_bridge.exe` |
| 配置文件 | `feishu_config.json` |
| Python 依赖 | `lark-oapi`、`websockets` |
| 启动 | `feishu_bridge.exe --config feishu_config.json` |

**职责**：一个进程管 N 个飞书机器人（bot），每个 bot 独立连各自的 relay 通道，
并共同承担一个 HTTP 文件服务（供 Copilot 回传截图/文件）。

#### 3.4.1 多 bot 架构

```
BotManager
   ├── BotNode "suijichao"    → 独立 relay 通道 + 独立飞书长连接 + 独立 inbox
   ├── BotNode "test"         → 同上
   └── BotNode "zhenghaitao"  → 同上
              │
              ▼
   FileRouter（单端口 8081，按 /<bot 名>/ 路径路由）
```

**三条必须遵守的规则：**

1. **每个 bot 必须连各自的独立 relay 通道** —— 同通道会互相踢连接
   （只有 `client` 槽允许多连接，`nlp` / `server` / `nlp_worker` 都是单连接新顶旧）
2. **`http_port` 默认所有 bot 共用顶层 `http.port`** —— 靠 URL 路径 `/<bot名>/` 路由；
   仅旧版单 bot 场景才在 bot 项里单独覆盖 `http_port`
3. **`http_bind_ip` 填桥自身（中继机）的 IP**，不是 nlp 机器 IP

> **⚠️ 实际配置核对**：仓库现有 `feishu_config.json` 中 `zhenghaitao` 的 `relay_url`
> 指向 `ws://10.10.118.152:58080/test`（与 `test` bot **同一通道**），按规则 1 两个 bot 会互相踢连接。
> 若要两人同时使用，需把 `zhenghaitao` 改到独立通道（如 `/zhenghaitao`）。

#### 3.4.2 配置热更新

每 `watch_interval_s`（默认 3s）重读配置文件，diff 后自动增/删/重启对应 bot：

- 改 `app_secret` → 只重启该 bot 的飞书线程
- 新增 bot → 自动起新线程 + 新 relay 连接 + 新 inbox
- 删除 bot → 自动停线程并清理
- **运行中的其他 bot 不受影响，桥进程不重启**

#### 3.4.3 单会话互斥

一轮任务处理中收到新消息 → 回：

```
⏳ Copilot 正在处理上一条指令, 请稍候...
```

内部用 `_busy` 标志 + `_done_event` 事件实现。

#### 3.4.4 worker 上下线通知（v5 新增）

| 收到事件 | 动作 |
|---|---|
| `worker_online` | 解锁 `_busy` + 飞书回 `✅ Copilot 已连接，可以继续发送指令` |
| `worker_disconnected` | 解锁 `_busy` + 飞书回 `❌ Copilot 已断开，本轮已取消。请稍后重试（或等待自动重连）。` |

**设计目的**：修复「Copilot 中途挂了 → `_busy` 卡死 → 用户后续消息全部被拒」的锁死问题。

> **⚠️ 已知行为（非缺陷）**：这两条通知的发送目标是 `last_sender`（用户最后跟哪个 bot 说过话）。
> 如果桥刚重启、用户还没发过任何消息，`last_sender` 为空 → 通知**被丢弃**，日志会打印：
> ```
> ⚠️ 无 last_sender, 回复无法路由(丢弃)
> ```
> **这不影响功能**（桥刚启动时本来就是干净状态，不需要解锁），只是看不到那条提示。

#### 3.4.5 inbox 自动清理（v6 新增）

| 机制 | 说明 |
|---|---|
| 任务数 | **多 bot 共用一个扫描任务**（不是每 bot 一个独立线程） |
| 取数方式 | `BotManager.cleaners` 是动态 property，返回所有运行中 bot 的 `InboxCleaner` |
| 热更新跟进 | 新增/删除 bot 时，清理任务自动跟进，无需重启 |
| 首次扫描 | 启动 60 秒后先扫一次，之后每 `interval_s` 扫一遍 |
| 清理策略① | 文件年龄超 `max_age_days` 天 → 删除 |
| 清理策略② | 剩余文件数超 `max_files` → 按 mtime 从旧到新删 |
| **安全边界** | **只删直接子文件，不递归，不碰任何目录** |
| 兜底下限 | `interval_s` 代码里 `max(60.0, interval_s)`，防手滑配成 1 秒 |
| 关闭方式 | `max_age_days: 0` 或 `max_files: 0` = 该维度不删 |

#### 3.4.6 HTTP 文件服务（FileRouter）

单端口（默认 8081）多 bot 复用，按路径首段区分 bot：

| 方法 | 路径 | 说明 |
|---|---|---|
| `GET` | `/<bot>/inbox/<file>` | 从该 bot 的 `inbox_dir` 返回文件（供 Copilot/飞书下载） |
| `POST` | `/<bot>/upload` | 上传字节入该 bot 队列，由 bot 发到飞书 |

**飞书 App 权限要求：** `im:resource`（下载用户发的文件）+ 发送 file 类型消息权限。

---

### 3.5 Kanzi Studio MCP 插件（C# 侧）

| 项 | 值 |
|---|---|
| 源文件 | 仓库根目录 `Kz*.cs` / `Kz*.xaml` |
| 工程文件 | `KzMCPChatPlugin.csproj` / `.sln` |
| 语言 | C# / WPF |
| 编译环境 | Windows + Kanzi SDK + Visual Studio（**AI 侧只能改代码，不能编译**） |

**关键文件：**

| 文件 | 作用 |
|---|---|
| `KzMainWindow.xaml(.cs)` | 主聊天窗口 |
| `KzMCPServerWindow.xaml(.cs)` | MCP Server 状态窗口 |
| `KzMCPChatPlugin.csproj` | 工程定义 |
| `KzMCPChatPluginFactory.cs` | 插件工厂（Kanzi 加载入口） |
| `KzMCPServerClient.cs` | 与 relay 的 WebSocket 客户端（server 角色） |
| `KzMCPReflectionBridge.cs` | **反射桥**：所有 Kanzi API 调用的统一入口 |
| `KzWSClient.cs` | WebSocket 底层封装 |
| `JsonUtils.cs` | JSON 序列化工具 |

**核心设计原则（全反射）：**

> **`KzMCPReflectionBridge` 的所有方法调用必须通过纯反射实现。**
> - 不缓存 `MethodInfo` / `PropertyInfo`
> - 不直接引用任何 `Rightware.Kanzi.*` 具体类型
> - 方法查找通过运行时 `FindMethod()`、`GetMethods()`、`InterfaceMapping` 动态完成
> - 便捷方法只是参数预处理，最终都走统一的 `Invoke` 入口

**为何必须全反射：** 插件要在多个 Kanzi 版本上工作，直接引用具体类型会导致版本不兼容编译失败。
反射让插件能在运行时适配不同版本的 Kanzi API。

---

### 3.6 技能包（kanzi-all-skills-intranet）

| 项 | 值 |
|---|---|
| 路径 | `mcp_server/kanzi-all-skills-intranet/` |
| 技能数 | **11 个** |
| 总行数 | 4269 行 |
| 加载方 | nlp_worker 的 `skills.entries[].path` |

> **⚠️ 内网部署使用 `kanzi-all-skills-intranet`，不要用 `kanzi-all-skills`。**
> 前者已去除所有外网/线上地址，只保留内网端点。后者为外网版本。

**技能清单：**

| 技能 | 行数 | 内容 |
|---|---|---|
| `kanzi-studio-mcp` | 324 | **总入口**。接入方式、31 个工具的参数 schema、v4 参数标识符（`@type/@int/@string/@enum/@obj/@node/@null/@vector/@vector3d/@quaternion/@transformation2d/@color/@dict` 等）、target 取值、返回格式、多工程切换 |
| `kanzi-ui` | 1100 | UI 节点创建/配置。EmptyNode2D、TextBlock2D、插件节点类型、属性增删改、字体字号、节点定位 |
| `kanzi-animation` | 475 | 动画创建。Animation Data（单关键帧动画）/ Animation Clips（动画组）两层结构、动画库定位、Timeline Sequences、AnimationChildClip 子片段引用、AnimationPlayer 创建与关联、DispatchMessageAction 控动画启停 |
| `kanzi-localization` | 457 | 多国语资源表完整增删改查。v13 工具 `kz_loc_entry_*`、语言列增删、文本与字体引用条目 |
| `kanzi-resource-create` | 441 | 资源创建。颜色笔刷、纹理（Texture/SingleTexture）、字体（FontFamily）、资源定位 |
| `kanzi-state-manager` | 407 | 状态机。StateManager / StateGroup / State / StateObject 生命周期、ControllerProperty 设置 |
| `kanzi-trigger` | 297 | 触发器。TriggerNodeComponent 创建、Action 与 Condition 完整配置、SetPropertyAction、DispatchMessageAction、StateManager.GoToState |
| `kanzi-binding` | 238 | 动态数据绑定。CreateBinding 参数、绑定表达式格式、查询/删除、属性 ref 获取 |
| `kanzi-material-brush` | 236 | 参数化渐变材质笔刷。Material + MaterialType + MaterialBrush 三层关联、双着色器、uniform 属性、binding |
| `kanzi-save-export` | 229 | 保存与导出。通过 `GeneratedCommandInvoker`（`@studio.get_Commands`）执行 SaveProject / ExportBinary |
| `kanzi-screenshot` | 65 | 截图。`kz_enum_all_windows` 定位 Studio 主窗 PID → `kz_screenshot_preview` 截图 |

**重要：技能加载策略**

`skills.entries` 支持两种写法：

```yaml
entries:
  # 父目录没有自己的 SKILL.md → 自动发现子技能目录（推荐）
  - path: ./skills
    enabled: true
  # 目录自带 SKILL.md 时，要加载其子技能需 recursive: true
  - path: D:\your-project\.github\skills
    enabled: true
    recursive: true
```

**关键约束：** `max_file_bytes: 131072`（单文件上限）、`max_total_bytes: 524288`（总量上限）。
11 个技能实际合计 **4269 行 / 246,702 字节（约 241KB）**，
已占 `max_total_bytes`（524288 字节 / 512KB）的 **47%**，全部启用不会超限。

---

## 五、从零搭建指导

> 本章目标：从干净的机器开始，搭出可用的完整系统。
> 以**三机分离**为例（中继机 / Kanzi 机 / Copilot 机）；单机部署时把 IP 换成 `127.0.0.1` 即可。

### 5.0 环境要求

| 项 | 要求 | 备注 |
|---|---|---|
| Python | **3.11+** | nlp_worker 明确要求；relay/http/feishu 3.10+ 实测可用 |
| 操作系统 | Windows | Kanzi Studio 插件为 C#/WPF，必须 Windows |
| 网络 | 内网互通 | 中继机 `58080` / `9001` / `8081` 对相关机器开放 |
| 飞书 | 企业内部应用 | 需 `im:resource` 权限 + 发文件权限 |
| Kanzi | Kanzi Studio | 插件需自行编译（见 3.5） |
| Visual Studio | VS2019+ | 编译 C# 插件用 |

**端口规划表：**

| 端口 | 组件 | 协议 | 开放方向 |
|---|---|---|---|
| 58080 | relay_multi | WebSocket | 中继机 ← Kanzi 机 / Copilot 机 |
| 9001 | kz_mcp_http | HTTP | 中继机 ← Copilot 机 |
| 8081 | feishu_bridge | HTTP | 中继机 ← Copilot 机（回传文件） |

---

### 5.1 步骤一：准备中继机

#### 1) 安装 Python 依赖

```bat
python -m pip install websockets lark-oapi
```

如需 OTA 自动更新（本地编译），额外装：

```bat
python -m pip install pyinstaller
```

#### 2) 建立部署目录

```
D:\kanziMCP_relay\
   ├─ relay_multi.exe          ← 放入
   ├─ kz_mcp_http.exe          ← 放入
   ├─ feishu_bridge.exe        ← 放入
   ├─ config.json              ← 新建（http 配置）
   ├─ users.json               ← 新建（白名单）
   ├─ feishu_config.json       ← 新建（桥配置）
   ├─ tmp_results\             ← 运行时自动创建
   ├─ inbox_<bot名>\           ← 运行时自动创建
   └─ logs\                    ← 运行时自动创建
```

> **关键：配置文件必须与对应 exe 同目录。** 因为启动用的是相对路径
> （`--config config.json` / `--config feishu_config.json`），
> workdir 也要设成这个目录（OTA 里 `launch.shortcuts[].workdir` 即为此）。

#### 3) 获取 exe（三选一）

| 方式 | 操作 |
|---|---|
| **A. PyInstaller 自行打包** | 按 4.6 参数在各自源码目录打包 |
| **B. OTA 构建产物** | 跑 `ota_agent.py --force`，自动编译并落到 `target_dir` |
| **C. 直接跑源码** | `python relay_multi.py`（需先装依赖，便于调试） |

---

### 5.2 步骤二：启动 relay

**relay 无参数、无配置文件，直接启动。**

```bat
cd /d D:\kanziMCP_relay
relay_multi.exe
```

**成功日志：**

```
🔄 MCP 中继 ws://0.0.0.0:58080
   路径区分通道: ws://ip:58080/用户名
   Server:      ws://ip:58080/用户名
   Client:      ws://ip:58080/用户名（多连接并存, 定向回传）
   NLP Client:  ws://ip:58080/用户名  (聊天插件)
   NLP Worker:  ws://ip:58080/用户名  (Claude 执行器)
   ♻️ 回收: 断开即收 + 空闲120s + 整通道闲置600s
```

**验证监听：**

```bat
netstat -ano | findstr 58080
```

> **注意**：relay 是**按需建通道**的，刚启动时看不到任何通道属正常现象。

---

### 5.3 步骤三：配置并启动 kz_mcp_http

#### 1) 写 `config.json`

```json
{
  "relay_base": "ws://127.0.0.1:58080",
  "users": "users.json",
  "listen": "0.0.0.0:9001",
  "mcp_timeout": 300,
  "heartbeat_interval": 5,
  "heartbeat_max_fails": 3,
  "req_check_interval": 2,
  "result_tmp_dir": "tmp_results",
  "result_ttl": 1800,
  "result_public_host": "10.10.118.152",
  "result_threshold_entries": 50,
  "result_threshold_bytes": 4096,
  "debug": false
}
```

**两个必看要点：**

| 配置 | 值 | 原因 |
|---|---|---|
| `relay_base` | `ws://127.0.0.1:58080` | http 与 relay 同机，走回环最快最稳 |
| `result_public_host` | **真实内网 IP** | Copilot 在另一台机器上要下载外置结果文件。写 `127.0.0.1` → Copilot 会去下自己机器的文件，必然 404 |

#### 2) 写 `users.json`

```json
{
  "users": ["suijichao", "wangtianyu", "wangdong", "zhenghaitao", "lvhuiyuan", "test"]
}
```

> ⚠️ **白名单不能为空** —— 代码有校验，空则**拒绝启动**（防误配成裸奔）。
> 新增用户：加名字保存即生效，**不用重启**。

#### 3) 启动

```bat
cd /d D:\kanziMCP_relay
kz_mcp_http.exe --config config.json
```

**成功日志：**

```
🌐 HTTP MCP Server 已启动: http://0.0.0.0:9001/mcp
   三端点聚合: 本地 studio(/mcp/) + 官方 api(/kanzi_api_mcp) + doc(/kanzi_doc_mcp)
```

#### 4) 验证

```bat
curl -H "X-Kanzi-User: suijichao" http://10.10.118.152:9001/kanzistudio_mcp
```

| 返回 | 含义 |
|---|---|
| `403` | 用户名不在白名单 / 没带 `X-Kanzi-User` 头 |
| 正常 MCP 响应 | 端点通（此时 Kanzi 未连可能返回 Kanzi 离线错误，属正常） |

> **⚠️ 必须监听 `0.0.0.0:9001`**，不要绑 `127.0.0.1`。
> 否则 Copilot 机（可能跨机）根本连不上。

---

### 5.4 步骤四：配置并启动 nlp_worker

#### 1) 准备便携版目录

把 nlp_worker 便携版整包解压到 Copilot 机，例如 `D:\kanziMCP_nlp\`，
里面应有：`nlp_worker.exe`、`run.cmd`、`login_copilot.cmd`、`config.example.yaml`、`.env.example`、`_internal\`。

#### 2) 首次登录 Copilot

```bat
cd /d D:\kanziMCP_nlp
login_copilot.cmd
```

该脚本会自动设 `COPILOT_HOME=%~dp0.copilot-data` 并调用 `_internal\runtime\copilot.exe login`。
登录凭据与会话状态都落在包内的 `.copilot-data\`，**不污染系统目录，整包可搬移**。

#### 3) 写 `config.yaml`（关键片段）

```yaml
relay:
  url: "ws://10.10.118.152:58080/suijichao"
  channel: "suijichao"
  role: nlp_worker                # 固定值，不要改
  reconnect_delay_seconds: 3
  identity:
    mode: dedicated_channel
    dedicated_principal_id: "suijichao"

copilot:
  use_logged_in_user: true
  working_directory: "D:/kanziMCP_work"
  base_directory: "./.copilot-data"
  response_timeout_seconds: 600
  max_idle_seconds: 300
  model:
    name: "<模型ID>"              # 必须是模型 ID，不是显示名
  permissions:
    default: deny
    allow:
      - "kanzi-*"                 # 按需放开，支持通配

skills:
  entries:
    - path: ./skills              # 11 个 SKILL 的父目录
      enabled: true

mcp_servers:
  kanzi:
    type: http
    url: "http://10.10.118.152:9001/mcp"
    headers:
      X-Kanzi-User: "suijichao"   # 必须带，否则 403
    timeout_seconds: 60

compatibility:
  bridge_http: "http://10.10.118.152:8081/suijichao"   # 不配则截图/文件回不到飞书
```

**四个最容易踩的点：**

| 项 | 说明 |
|---|---|
| `role` | 必须 `nlp_worker`；写成别的会被分到错误槽位 |
| `url` 路径段 | 必须与 `channel` 一致，且**必须独立**（不能与其他 bot 共用） |
| `X-Kanzi-User` | 必须与白名单里的用户名一致；也要与 relay URL 路径段一致 |
| `bridge_http` | **不配 → 截图和文件永远传不回飞书**（只有文字能回） |

#### 4) 校验配置（不连接）

```bat
nlp_worker.exe --validate-config --config config.yaml
```

#### 5) 查看可用模型

```bat
nlp_worker.exe --list-models
```

#### 6) 启动

```bat
run.cmd
```

> `run.cmd` 会在缺文件时自动从 `.example` 复制出 `config.yaml` / `.env` 再启动，
> 失败时 `pause` 停住便于看报错。

**成功标志**：relay 日志出现该通道的 `nlp_worker` 槽上线事件。

---

### 5.5 步骤五：配置并启动 feishu_bridge

#### 1) 飞书开放平台创建应用

| 步骤 | 操作 |
|---|---|
| ① | 创建**企业内部应用**，取 `app_id` / `app_secret` |
| ② | 开通权限：`im:resource`（下载用户文件）+ 发送 file 类型消息权限 |
| ③ | 订阅事件：接收消息（长连接模式，**无需公网回调地址**） |
| ④ | 发布应用并等待管理员审批通过 |

> **为什么不用公网回调**：桥用 `lark-oapi` 的**长连接模式**接收事件，
> 因此内网环境无需任何公网入口 —— 这是本方案能在纯内网跑起来的关键。

#### 2) 写 `feishu_config.json`

```json
{
  "reload": { "watch_interval_s": 3, "enabled": true },
  "http": { "host": "0.0.0.0", "port": 8081 },
  "cleanup": {
    "inbox": { "enabled": true, "max_age_days": 7, "max_files": 500, "interval_s": 3600 }
  },
  "bots": [
    {
      "name": "suijichao",
      "app_id": "cli_aaa263872939dce2",
      "app_secret": "***",
      "relay_url": "ws://10.10.118.152:58080/suijichao",
      "http_bind_ip": "10.10.118.152",
      "inbox_dir": "inbox_suijichao"
    }
  ]
}
```

**三条硬约束（违反必出问题）：**

| 约束 | 后果 |
|---|---|
| 每个 bot 的 `relay_url` 通道**独立** | 同通道 → 两个 bot 互相踢连接 |
| `http_port` 默认**共用**顶层 `http.port` | 靠 URL 路径 `/<bot名>/` 路由区分，**不需要**每 bot 一个端口；仅旧版单 bot 才单独覆盖 |
| `http_bind_ip` 填**桥自身（中继机）IP** | 填错 → Copilot 拿不到文件 URL |

#### 3) 启动

```bat
cd /d D:\kanziMCP_relay
feishu_bridge.exe --config feishu_config.json
```

#### 4) 验证

在飞书里给该 bot 发一条消息，观察日志是否出现该 bot 上线 + 消息转发记录。

> **热更新**：此后改 `feishu_config.json`（增 bot / 改 secret）保存即生效，
> **桥进程不重启**，其他 bot 不受影响。

---

### 5.6 步骤六：安装 Kanzi 插件并连接

1. 用 Visual Studio 以 **Windows + Kanzi SDK** 编译 `KzMCPChatPlugin.sln`
2. 把编译产物放到 Kanzi Studio 的插件目录
3. 启动 Kanzi Studio，打开**目标工程**
4. 在插件面板里填写 relay 地址：`ws://10.10.118.152:58080/<用户名>`
5. 连接（以 **server 角色**）

**成功标志：** relay 日志显示该通道 `server` 槽上线；
插件状态窗口显示已连接。

> **⚠️ 编译只能在 Windows 上做**（需 Kanzi SDK）。
> AI 侧只能改 C# 源码，编译由使用方执行。

---

### 5.7 步骤七：端到端验证

按顺序确认，任一步失败按第九章排查：

| # | 检查 | 期望 |
|---|---|---|
| 1 | `netstat \| findstr 58080` | relay 在听 |
| 2 | `netstat \| findstr 9001` | http 在听 |
| 3 | 带头的 curl | 不是 403 |
| 4 | relay 日志 | 该通道 `server` / `nlp` / `nlp_worker` 三槽均有连接 |
| 5 | nlp_worker 日志 | 已连 relay，会话已建立 |
| 6 | **飞书发一条消息** | 收到「🤖 Copilot 思考中...」→ 最终回复 |
| 7 | **飞书说「截个图」** | 收到图片（验证 `bridge_http` 通了） |

> **冷启动注意**：若 nlp_worker 比桥先连上，用户还没发过消息，
> 则「✅ Copilot 已连接」这条提示可能看不到（`last_sender` 为空被丢弃）。
> **属正常现象，直接发指令即可。**

---

## 六、部署与运维

### 6.1 进程托管（必须）

**🔴 铁律：所有常驻进程必须用 systemd / NSSM 托管，禁止裸 `nohup` / 直接双击。**

原因：裸 `nohup` 启动的进程会被 SIGTERM 掐死（会话结束、远程断开、任务清理都会触发），
表现为「刚跑起来过一会儿就没了」，极难排查。

#### Windows 用 NSSM

```bat
nssm install KanziMCP-relay  D:\kanziMCP_relay\relay_multi.exe
nssm set     KanziMCP-relay  AppDirectory D:\kanziMCP_relay

nssm install KanziMCP-http   D:\kanziMCP_relay\kz_mcp_http.exe
nssm set     KanziMCP-http   AppParameters --config config.json
nssm set     KanziMCP-http   AppDirectory  D:\kanziMCP_relay

nssm install KanziMCP-feishu D:\kanziMCP_relay\feishu_bridge.exe
nssm set     KanziMCP-feishu AppParameters --config feishu_config.json
nssm set     KanziMCP-feishu AppDirectory  D:\kanziMCP_relay
```

启动顺序：**relay → http → feishu**（http 要连 relay）。

#### Linux 用 systemd

```ini
# /etc/systemd/system/kanzimcp-relay.service
[Unit]
Description=Kanzi MCP Relay
After=network.target

[Service]
Type=simple
WorkingDirectory=/opt/kanzimcp/relay
ExecStart=/opt/kanzimcp/relay/relay_multi
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
```

> http / feishu 同理，`ExecStart` 分别加 `--config config.json`
> 和 `--config feishu_config.json`，并设对应的 `WorkingDirectory`。

---

### 6.2 更新单元规则（强制）

**🔴 relay 重启时，http 和 feishu 必须同步重启。**

三者是**同一个更新单元**，不可单独重启 relay。

**原因**：http 和 feishu 都持有到 relay 的 WebSocket 长连接。
relay 重启后旧连接全部失效，http/feishu 若不同步重启，
会出现「进程在、但连不上中继」的假活状态，表现为飞书发消息无响应。

**正确操作顺序：**

```
停止：feishu → http → relay
启动：relay → http → feishu
```

OTA 的 `processes.kill_order` 和 `launch.shortcuts` 顺序即按此设计。

---

### 6.3 日志位置与查看

| 组件 | 日志位置 | 说明 |
|---|---|---|
| relay | **控制台 stdout** | 无文件日志，靠 NSSM/systemd 重定向 |
| http | **控制台 stdout** | 同上 |
| feishu | **控制台 stdout** | 同上 |
| nlp_worker | `logging.file`，默认 `./logs/bridge.log` | 有轮转 |

**nlp_worker 日志轮转参数：**

| 字段 | 默认 | 说明 |
|---|---|---|
| `logging.level` | `INFO` | 调 `DEBUG` 看详细过程 |
| `logging.max_bytes` | 10485760（10MB） | 单文件上限 |
| `logging.backup_count` | 5 | 保留 5 个备份 |

**NSSM 重定向日志：**

```bat
nssm set KanziMCP-relay AppStdout D:\kanziMCP_relay\logs\relay.log
nssm set KanziMCP-relay AppStderr D:\kanziMCP_relay\logs\relay.err.log
```

---

### 6.4 多用户接入流程

新增一个用户（例如 `zhangsan`）需要三处同步：

| # | 位置 | 操作 |
|---|---|---|
| 1 | `users.json`（http） | 数组加 `"zhangsan"` → **保存即生效，不重启** |
| 2 | `feishu_config.json`（桥） | `bots` 加一项：`name` / `app_id` / `app_secret` / `relay_url`（通道 `zhangsan`）/ `http_bind_ip` / `inbox_dir` → **保存即生效，不重启** |
| 3 | Copilot 机 | 部署一套 nlp_worker：`url` 用 `ws://<中继机>:58080/zhangsan`、`X-Kanzi-User: zhangsan`、`bridge_http` 指向 `http://<中继机>:8081/zhangsan` |
| 4 | Kanzi（可选） | 用户自己的 Kanzi Studio 插件连 `ws://<中继机>:58080/zhangsan` |

> **要点**：一个用户 = 一条独立 relay 通道 = 一套独立 nlp_worker。
> 通道互不干扰，一个用户的 Copilot 崩了不影响其他人。

**删用户**：从 `bots` 里删掉该项 → 桥自动停掉对应线程和连接；
`users.json` 里删掉名字 → 该用户马上 403。

---

### 6.5 备份与恢复

| 对象 | 位置 | 备份建议 |
|---|---|---|
| 配置文件 | `D:\kanziMCP_relay\*.json` | 改动前后各存一份（含真实密钥的版本**只放内网**） |
| nlp_worker 会话库 | `storage.database_path`（默认 `./data/bridge.db`） | 内含飞书 conversation key → Copilot session ID 映射 |
| Copilot 登录态 | `.copilot-data\` | 丢失需重新 `login_copilot.cmd` |
| OTA 回滚备份 | `rollback.backup_dir` | 自动维护，替换前自动备份旧 exe |
| 技能包 | `skills.entries[].path` | 与仓库同源，重拉即可 |

**恢复顺序**：配置 → relay → http → feishu → nlp_worker → 插件。

---

## 七、OTA 自动更新

### 7.1 工作原理

```
① 轮询内网 Git 镜像的 tag（poll.interval_s，默认 60s；check_on_start 为 true 时启动先查一次）
        │
        ▼
② 发现新 tag（比当前 VERSION.txt 新）→ 或 --force
        │
        ▼
③ git 拉取该 tag 到 repo.local_dir
        │
        ▼
④ 本地编译：按 build.components[] 逐个跑 pyinstaller
   （用 build.python_exe / build.pyinstaller / build.build_bat）
        │
        ▼
⑤ 编译产物落 build.output_dir（dist）
        │
        ▼
⑥ 按 processes.kill_order 停止旧进程（feishu → http → relay）
   （每杀一个等 processes.kill_wait_ms）
        │
        ▼
⑦ 备份旧 exe 到 rollback.backup_dir，替换为新 exe
        │
        ▼
⑧ 按 launch.shortcuts 顺序启动（relay → http → feishu，
   每个之间等 wait_before_next 秒；.lnk 不存在会自动创建）
        │
        ▼
⑨ 健康检查：按 health.checks[] 轮询
   （port 类型查端口，process 类型查进程；总超时 health.timeout_s）
        │
   ┌────┴────┐
 通过        失败
   │          │
   ▼          ▼
⑩ 飞书通知   ⑩ 回滚（rollback.enabled）：从 backup_dir 恢复旧 exe 并重启
  「✅ OTA 成功」  ⑪ 飞书通知「❌ 启动失败，已回滚」
```

### 7.2 发布流程

**打 tag 即发布。**

```bash
git tag v<N>
git push origin v<N>      # 推到内网 Git 镜像
```

OTA 下一轮轮询（默认 60s 内）即发现并自动更新。

> `repo.use_tag: true` 表示按 tag 发布。版本号记录在 `VERSION.txt`。

### 7.3 通知机制

**🔴 三种情况都必须通知飞书，不能只通知成功。**

| 情况 | 通知内容 |
|---|---|
| 编译失败 | ❌ OTA 编译失败（附错误摘要） |
| 启动失败 | ❌ OTA 启动失败，已回滚（附失败的健康检查项） |
| 成功 | ✅ OTA 成功（v<N>) |

通知配置：`feishu_notify`。

| 字段 | 说明 |
|---|---|
| `enabled` | 开关 |
| `app_id` / `app_secret` | 通知用飞书应用凭据 |
| `receive_id` | 收件人 ID |
| `receive_id_type` | 如 `open_id` |

**自测通知：**

```bat
ota_agent.exe --test-notify
```

### 7.4 内网 Git 镜像要求

| 要求 | 原因 |
|---|---|
| 必须是**内网可达**的镜像 | 中继机 **GitHub 443 不通** |
| 支持 git clone / fetch / tag | OTA 用 git 拉源码 |
| 仓库内包含完整源码 | OTA 是**本地编译**，不是下二进制 |
| 中继机需装 Python + PyInstaller | 编译在本机做 |

> 本方案使用 Gitee 作为镜像源（`https://gitee.com/suijichao/kanzimcp.git`），
> 因为中继机到 Gitee 通、到 GitHub 不通。

### 7.5 故障处理与手动干预

| 参数 | 用途 |
|---|---|
| `--once` | 只跑一轮就退出（不常驻轮询） |
| `--force` | 忽略版本比对，强制更新到最新 tag（**回滚后手工修复用**） |
| `--test-notify` | 只测飞书通知通不通 |
| `--config` | 指定配置文件 |

**常见故障：**

| 现象 | 排查 |
|---|---|
| 一直没更新 | ①tag 是否推到镜像 ②`VERSION.txt` 当前版本 ③轮询是否在跑 |
| 编译失败 | ①中继机 Python/PyInstaller 是否装 ②`build_exe.bat` 是否 ASCII+CRLF ③依赖是否缺 |
| 更新后服务起不来 | 看 `health.checks` 哪项没过；已回滚则用 `--force` 重试或手工替换 |
| 回滚后仍是旧的 | 检查 `rollback.backup_dir` 里的备份是否完整 |

> **`build_exe.bat` 编码约束（踩过坑）**：纯 ASCII、CRLF 换行、
> 不用 `for` 循环、不用 `^` 续行 —— 否则 cmd 下乱码或解析失败。

---

## 八、优缺点分析

### 8.1 优势

| # | 优势 | 具体体现 |
|---|---|---|
| 1 | **彻底解耦** | 所有组件只连 relay，彼此不直连。任一组件（除 relay）可独立停/启/升级/换机 |
| 2 | **天然多用户隔离** | 通道 = 用户名，每个用户独立通道 + 独立 Copilot + 独立会话与会话数据 |
| 3 | **无需公网** | 飞书走长连接模式，Kanzi 在内网，全程不需要任何公网入口或端口映射 |
| 4 | **热更新友好** | 飞书 bot 列表、HTTP 白名单改文件即生效，不重启、不影响其他用户 |
| 5 | **离线快速失败** | Kanzi 不在线时立即返回明确错误（含原 id 与通道名），不空等、不积攒（`client_pending` 旧积攒队列已停用，仅启动时清理历史残留） |
| 6 | **防误杀** | 三层回收 + 「核心槽永不回收」+「主通道不清理」，避免长任务/挂机被踢 |
| 7 | **可回滚发布** | OTA 替换前自动备份，健康检查不过自动回滚，三种结果都通知飞书 |
| 8 | **上下文可控** | 大批量结果自动落盘外置，只回摘要 + 下载 URL，避免撑爆 Copilot 上下文 |
| 9 | **能力可沉淀** | 11 个 SKILL.md 技能包把「怎么操作 Kanzi」固化为可复用流程，新人照做即可 |
| 10 | **客户端轻量** | 飞书侧零安装，用自然语言即可操作 Kanzi Studio |

### 8.2 不足与风险

| # | 问题 | 影响 | 现状 |
|---|---|---|---|
| 1 | **relay 端口硬编码** | 改端口必须改源码重新打包 | 源码第 551 行 `port = 58080` |
| 2 | **relay 无配置文件** | 超时/扫描周期等调优都要改代码 | 常量在源码 39~41 行 |
| 3 | **relay 是单点** | relay 挂了全系统不可用 | 无主备、无集群 |
| 4 | **鉴权较弱** | 仅靠 `X-Kanzi-User` 请求头 + 白名单 | 内网环境可接受；头可伪造 |
| 5 | **依赖外部账号** | Copilot 需 GitHub 账号登录，模型由账号侧决定 | 账号不可用则执行器不可用 |
| 6 | **无指标监控** | 只有日志，没有 QPS/延迟/错误率面板 | 靠人工看日志 |
| 7 | **日志分散** | 三组件日志在各自 stdout，未集中 | 需 NSSM/systemd 重定向汇总 |
| 8 | **`ask` 权限失效** | 飞书链路无审批 UI，`ask` 等同 `deny` | 必须显式写 `allow` |
| 9 | **通知可能丢** | 桥刚重启时 `last_sender` 为空，worker 上下线提示被丢弃 | 属正常，不影响功能 |
| 10 | **单会话互斥** | 一轮任务处理中，新消息被拒（提示稍候） | 设计如此，防上下文串扰 |
| 11 | **证书/密钥管理** | `app_secret` 明文在配置文件里 | 需严格控制配置文件访问权限 |
| 12 | **上下文压力** | Copilot 会话过长会退化 | 靠 `/new`、结果外置、`max_output_chars` 缓解 |

### 8.3 改进建议（内网范围内）

| 优先级 | 建议 | 说明 |
|---|---|---|
| 高 | relay 参数化 | 端口/超时/扫描周期改为命令行参数或配置文件 |
| 高 | 日志集中 | 三组件日志统一写文件目录，便于一次性拉取排查 |
| 中 | 轻量鉴权增强 | 白名单 + 共享 token 头（仅内网，仍是明文头，不做过度设计） |
| 中 | 健康探针 | 加一个内网 HTTP 探活端点，便于接入现有监控 |
| 中 | 通知兜底收件人 | 为 `worker_online/disconnected` 配 fallback open_id |
| 低 | 配置友好报错 | 配置项写错时给出「哪一行、期望什么」的提示 |
| 低 | 死代码清理 | `kz_mcp_http.py` 中已失效的 `if e.code == 4001` 分支 |

> 说明：以上均**不在公网/线上环境部署**，只在内网范围内演进。

---

## 九、常见问题与排查

### 9.1 连接类

| 现象 | 原因 | 处理 |
|---|---|---|
| `未知角色` / `Server not connected` | 首帧没带 `role` 字段 | 连接建立后**第一帧必须带 `role`**（`client`/`server`/`nlp_client`/`nlp_worker`） |
| Kanzi 收不到请求 | 通道名不匹配 | relay URL 路径段、`config.yaml` 的 `channel`、Kanzi 插件地址三者必须一致 |
| HTTP 返回 **403** | 白名单 | 确认带了 `X-Kanzi-User` 头且用户名在 `users.json` 里 |
| 两个飞书 bot 互相掉线 | 两个 bot 的 `relay_url` 指向了**同一通道** | 改成各自独立通道（只有 `client` 槽允许多连接） |
| 两个 bot 抢同一个通道 | `relay_url` 路径段重复 | 改成各自独立通道；只有 `client` 槽允许多连接 |
| 进程在但连不上中继（假活） | 单独重启了 relay | 必须按 6.2 同步重启三者 |
| Kanzi 挂机 2 分钟被踢 | （旧版本问题） | v6+ 已修：核心槽永不空洞回收 |

### 9.2 消息类

| 现象 | 原因 | 处理 |
|---|---|---|
| 发消息提示「Copilot 正在处理上一条指令, 请稍候...」 | 单会话互斥 | 等当前任务结束；卡死则看 `worker_disconnected` 是否恢复 `_busy` |
| 日志 `⚠️ 无 last_sender, 回复无法路由(丢弃)` | 桥刚重启，用户还没说过话 | **正常**，不影响功能；用户发一条消息后即正常 |
| 发消息完全没反应 | nlp_worker 未连上 | 检查 Copilot 机上 nlp_worker 进程与日志 |
| 回复内容被截断 | `max_output_chars` 限制 | 默认 3500，可调（上限 100000） |
| 「✅ Copilot 已连接」看不到 | worker 比桥先连上 | **正常**，直接发指令即可 |

### 9.3 结果与文件类

| 现象 | 原因 | 处理 |
|---|---|---|
| **截图/文件永远收不到**（只有文字） | `compatibility.bridge_http` 未配 | 必须配成 `http://<中继机>:8081/<bot名>` |
| 结果文件下载 **404** | `result_public_host` 未配或写成 `127.0.0.1` | 配成 Copilot **可达**的真实 IP |
| 文件上传失败 | 超 `max_upload_bytes`（默认 20MB） | 调大或减小文件 |
| 上传路径被拒 | 不在 `upload_allowed_roots` | 加白名单；`working_directory` 与 session-state 目录自动允许 |
| 结果文件找不到 | 超 `result_ttl`（默认 30 分钟） | 已自动清理，重新执行请求 |

### 9.4 权限与工具类

| 现象 | 原因 | 处理 |
|---|---|---|
| 工具调用被拒 | 权限 `default: deny` | 加到 `copilot.permissions.allow`（支持通配 `kanzi-*`） |
| 配了 `ask` 还是被拒 | 无审批 UI，`ask` 按 `deny` 处理 | 改为写进 `allow` |
| 工具不在列表里 | `available_tools` 白名单限制 | 检查 `copilot.agent.available_tools` |
| MCP 端点连不上 | `mcp_servers.*.headers` 少了 `X-Kanzi-User` | 补上头，且用户名与通道一致 |

### 9.5 更新与运维类

| 现象 | 原因 | 处理 |
|---|---|---|
| OTA 一直不动 | tag 没推 / 当前版本判断 | 看 `VERSION.txt`；`--once` 手工跑一轮 |
| OTA 编译失败 | Python / PyInstaller 缺失，或 bat 编码问题 | 装依赖；bat 必须 ASCII + CRLF、不用 `for`、不用 `^` |
| 更新后服务起不来 | 健康检查未过 | 看 `health.checks` 哪项失败；已自动回滚；`--force` 重试 |
| 通知收不到 | `feishu_notify` 配置错 | 用 `--test-notify` 自测 |
| 更新后飞书无响应 | http/feishu 未同步重启 | 按 6.2 三件套同步重启 |

---

## 十、附录

### 10.1 端口 / 路径 / 命名速查

| 项 | 值 |
|---|---|
| relay 监听 | `0.0.0.0:58080`（硬编码） |
| http 监听 | `0.0.0.0:9001` |
| 桥文件服务 | `0.0.0.0:8081`（每 bot 需唯一端口） |
| HTTP 端点 | `/mcp`、`/kanzistudio_mcp`、`/kanzi_api_mcp`、`/kanzi_doc_mcp`、`/data/<file>`、`/<bot>/inbox/<file>`、`/<bot>/upload` |
| relay URL 格式 | `ws://<中继机IP>:58080/<用户名>` |
| 结果外置目录 | `result_tmp_dir`，默认 `tmp_results` |
| 会话库 | `storage.database_path`，默认 `./data/bridge.db` |
| 日志 | `logging.file`，默认 `./logs/bridge.log` |
| 技能包 | `mcp_server/kanzi-all-skills-intranet/`（11 个） |
| exe 名 | `relay_multi.exe` / `kz_mcp_http.exe` / `feishu_bridge.exe` / `nlp_worker.exe` |

### 10.2 启动命令速查

| 组件 | 命令 | 工作目录 |
|---|---|---|
| relay | `relay_multi.exe` | exe 所在目录 |
| http | `kz_mcp_http.exe --config config.json` | exe 所在目录 |
| feishu | `feishu_bridge.exe --config feishu_config.json` | exe 所在目录 |
| nlp_worker | `nlp_worker.exe --config config.yaml`（或 `run.cmd`） | 便携版目录 |
| ota | `ota_agent.exe`（常驻）/ `--once` / `--force` / `--test-notify` | exe 所在目录 |

### 10.3 术语表

| 术语 | 含义 |
|---|---|
| **通道（channel）** | relay 中按用户名划分的独立隔离空间，对应 URL 路径段 |
| **槽位（slot）** | 通道内的角色位置：`server` / `client` / `nlp` / `nlp_worker` |
| **角色（role）** | 连接建立后第一帧声明的身份，决定进哪个槽 |
| **主通道（is_primary）** | 曾有 `server` 连接的通道，不参与整通道闲置回收 |
| **核心槽** | 除 `client` 外的槽位，不参与空闲回收 |
| **定向回传** | 多 client 并存时，按 JSON-RPC id 把响应回给发起请求的那个连接 |
| **外置结果** | 超过阈值的返回内容落盘为 JSON，只回摘要 + 下载 URL |
| **更新单元** | relay + http + feishu，必须同步重启 |
| **桥（bridge）** | feishu_bridge，飞书与 relay 之间的桥 |
| **执行器（worker）** | nlp_worker，驱动 Copilot 执行指令的组件 |

### 10.4 版本记录

| 版本 | 关键内容 |
|---|---|
| v1 | 初始版本 |
| v2 | 基础打通 |
| v3 | 功能完善 |
| v4 | 参数标识符体系（v4 标识符） |
| v5 | **worker 上下线通知**（修 `_busy` 卡死） |
| v6 | **feishu_bridge inbox 自动清理**（多 bot 共用扫描任务，只删直接子文件） |
| v7 | **relay：Kanzi 离线直接报错不积攒**（代码已合入；`VERSION.txt` 标记的**最新发布仍为 v6**，v7 待发布） |

> 更细的逐版本变更见仓库提交历史与 `使用手册.md`。

---

## 结语

本文档描述了内网环境下 Kanzi MCP 系统的完整形态：**六个组件、一套中继、按用户隔离的通道**，
把飞书自然语言指令一路送到 Kanzi Studio 并回传结果（含截图与文件）。

**核心运维口诀：**

1. **先看 skill，再动手** —— 操作 Kanzi 前先读对应 SKILL.md
2. **relay 重启，三件套同步** —— feishu → http → relay 停，relay → http → feishu 起
3. **必须进程托管** —— NSSM / systemd，禁止裸 nohup
4. **每个用户独立通道** —— 不复用、不共用
5. **改配置文件不重启** —— 白名单和 bot 列表都热更新

**全文完**
