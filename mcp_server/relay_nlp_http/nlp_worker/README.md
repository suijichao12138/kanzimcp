# 飞书 Copilot NLP Worker

替换旧 `nlp_worker_acp.py`，其余三个服务不变：

```text
feishu_bridge.py → relay_multi.py → nlp_worker.py
                                      ↓
                               GitHub Copilot SDK
                                      ↓
                    kz_mcp_http.py → relay → Kanzi
```

## Windows x64 便携版

构建机安装 Windows x64 Python 3.11+ 后，在项目目录执行一条命令：

```bat
build_portable.cmd
```

脚本安装 `requirements-build.txt`、通过 SDK 官方
机制定位当前构建解释器的缓存，缓存不存在时才调用
`python -m copilot download-runtime`（300 秒超时），再执行 PyInstaller onedir 构建。企业网络
无法下载时可先显式设置 `COPILOT_RUNTIME_SOURCE` 或 SDK 支持的 `COPILOT_CLI_PATH`，指向已
验证兼容的 Windows x64 `copilot.exe`。脚本会执行 `copilot.exe --version` 并把结果写入发布
包。输出：

```text
dist\nlp-worker-portable\
  nlp_worker.exe
  _internal\runtime\copilot.exe
  config.example.yaml
  .env.example
  COPILOT_RUNTIME_VERSION.txt
  login_copilot.cmd
  run.cmd
  skills\example\SKILL.md
dist\nlp-worker-portable-win-x64.zip
```

`config.yaml`、`.env`、`.copilot-data`、SQLite、日志和任何密钥都不会进入发布包。

目标机只需解压整个文件夹，运行 `run.cmd`。首次运行仅在文件不存在时复制
`config.example.yaml → config.yaml`、`.env.example → .env`，不会覆盖已有配置。编辑这两个
文件后再次运行即可；**不需要安装 Python、Python 依赖或 Copilot CLI**。可先离线检查：

```bat
run.cmd --validate-config
```

默认 GitHub provider 配置首次使用只需双击一次 `login_copilot.cmd`，按浏览器提示完成
GitHub 授权。脚本调用包内 Runtime，并把凭据仅保存到
便携目录下的 `.copilot-data`，与 `base_directory: ./.copilot-data` 一致；它不会显示或复制
凭据。授权成功后运行 `run.cmd`。也可把配置改为 `${GITHUB_TOKEN}` 方式；使用
OpenAI/Azure/Anthropic BYOK 时不需要此登录步骤。

授权后可从当前账号实时查询可用模型：

```bat
nlp_worker.exe --config config.yaml --list-models
```

`copilot.model.name` 必须填写输出表格中的模型 **ID**，不能填写显示名。例如显示名可能是
`GPT-5.6 Sol`，对应 ID 可能是 `gpt-5.6-sol`；请以命令的实时输出为准，不要猜测或硬编码。

便携包只承诺与构建机同架构的 **Windows x64**。目标机仍需网络连接模型服务、relay 和
配置的 MCP；GitHub token 或 BYOK token 仍必须放在外部 `.env`/`config.yaml`。PyInstaller
携带 Python 运行时，但 Windows 仍需系统可加载应用所需的 Microsoft Visual C++ Runtime；
建议 Windows 10/11 x64。

冻结程序通过 SDK 1.0.11 公开的
`RuntimeConnection.for_stdio(path=...)` 显式启动包内 Runtime，不访问目标机的 SDK 缓存，也
不在首次启动时下载 Copilot CLI。配置文件默认从 `nlp_worker.exe` 旁查找；配置中的
SQLite、日志、skills、MCP cwd、Copilot `working_directory`/`base_directory` 等相对路径均
相对配置文件目录解析。示例用 `working_directory: .` 以便解压即校验；实际使用应改成目标机
**已经存在**的 Kanzi/项目根目录。程序不会擅自创建工作目录，路径不存在或不是目录会在
`--validate-config` 和正式启动前明确报出完整路径。启用的 stdio MCP `cwd` 也采用同样检查。

## 源码运行

要求 Python 3.11+。Windows PowerShell：

```powershell
python -m pip install -r requirements.txt
Copy-Item .env.example .env
Copy-Item config.example.yaml config.yaml
python -m copilot download-runtime
```

编辑 `.env` 与 `config.yaml`，然后启动：

```powershell
python nlp_worker.py --config config.yaml
```

不需要安装本项目，不需要 editable package。开发测试依赖可单独安装：

```powershell
python -m pip install -r requirements-dev.txt
python -m pytest -q
```

## 配置重点

- `relay`：旧 relay URL、`nlp_worker` 槽位名、心跳、重连和允许通道。
- `copilot.model`：模型与 GitHub/OpenAI/Azure/Anthropic BYOK。
- `copilot.permissions`：工具 allow/deny/ask；无审批 UI 时 `ask` 自动拒绝。
- `copilot.large_output`：SDK 大输出落盘。`output_directory` 必须保留
  `session-state/{session_id}/files` 模板，Worker 在 create/resume 时替换为真实 SDK 会话 ID，
  因此不同会话不会共用文件。示例的 50 KiB 阈值只控制 SDK 何时落盘，不是下载大小上限。
- `skills`：启用的 `SKILL.md` 或 skills 父目录，内容注入 system prompt。父目录自身没有
  `SKILL.md` 时自动递归发现所有子目录；例如只需配置
  `path: D:\your-project\.github\skills`。目录自身已有 `SKILL.md` 时默认保持旧行为、只加载
  自身；配置 `recursive: true` 才同时加载子目录。文件按规范化路径排序并去重，空目录会报错。
- `mcp_servers`：stdio/local 或 HTTP/SSE。示例中的三个 URL 保持现有
  `kz_mcp_http.py` → relay → Kanzi 路径。
- `artifacts`：远程 MCP 产物策略。`allowed_origins` 必须逐项写完整
  `http(s)://host:port`；只允许精确匹配的 scheme/host/port，拒绝用户信息、URL fragment 和
  所有重定向。下载同时受超时、字节上限、Content-Type 与文件魔数检查，使用同目录临时文件和
  原子改名，失败会清理临时文件。
- `storage.database_path`：SQLite 会话映射和消息去重。

所有 `${ENV_VAR}` 在启动时展开；缺失变量或未知配置字段会直接报错。SDK 固定验证
`github-copilot-sdk >=1.0.11,<1.1`，MCP 超时会转换为 SDK 所需毫秒值。

SQLite 保存 conversation key、SDK session ID、模型、配置指纹、状态和时间。重启后调用
SDK `resume_session()`。恢复失败默认明确报错；只有配置 `resume_failure: new` 才新建。
模型/MCP/skills/agent 配置指纹变化也默认拒绝恢复，可用 `/new` 明确重置。

命令：`/new`、`/status`、`/cancel`、`/help`。

## 从旧 worker 迁移

1. 保持 `feishu_bridge.py`、`relay_multi.py`、`kz_mcp_http.py` 运行，不修改原目录。
2. 先停止旧 `nlp_worker_acp.py/.exe`，避免两个 worker 争抢同一槽位。
3. 把旧参数迁入 `config.yaml`：
   - `--relay` → `relay.url`；URL path 同时填 `relay.channel`。
   - `--cwd` → `copilot.working_directory`。
   - `--model` → `copilot.model.name`。
   - MCP 主机/端口 → 三个 `mcp_servers.*.url`。
   - `X-Kanzi-User` → 三个 MCP 的 headers。
   - `--bridge-http` → `compatibility.bridge_http`。
4. 执行 `python nlp_worker.py --config config.yaml`。

槽位注册首帧严格保持：

```json
{"role":"nlp_worker","name":"<relay.channel>"}
```

WebSocket 断线后按配置重连并重新注册同一槽位。旧 relay 同槽替换存在竞态，因此不能让新旧
worker 并行滚动切换。

## 用户隔离限制

现有 `feishu_bridge.py` 虽收到 `open_id/chat_id/message_id`，但发给 relay 时只保留：

```json
{"type":"user_message","text":"..."}
```

因此只改 NLP 层无法识别同一 bot/channel 内的多个飞书用户。默认
`identity.mode: dedicated_channel`，会话键为 `channel + dedicated_principal_id`，要求每个
用户或群使用独立 bot、relay channel 和 worker；多人共用一个旧 bot 不受支持。

若未来上游透传 `user_id/chat_id/thread_id/root_id/session_id/message_id`，只需把配置改为
`identity.mode: message_fields`。届时按 `channel + chat + user + thread` 隔离，并将身份与
`request_id` 原样带回响应。

`[FILE_DOWNLOAD]` 和 `[FILE] path=...` 与旧 worker 兼容。飞书桥下发的
`[FILE_DOWNLOAD]` 仍保存到 `copilot.working_directory`，不会进入 Copilot 的 session files；
下载 URL 必须与 `compatibility.bridge_http` 的 scheme、host 和 port 完全一致，拒绝重定向，
并受 `download_timeout_seconds` 与 `max_upload_bytes` 限制。同名文件使用 `-1`、`-2` 后缀，
临时文件在失败时清理，完成后原子改名。上传自动允许
`copilot.working_directory`，以及严格位于
`copilot.base_directory\session-state\<当前 session-id>\files` 下的 Runtime 会话附件；不会允许整个
`.copilot-data`，避免暴露授权数据。额外可信目录可配
`compatibility.upload_allowed_roots`，相对路径按配置目录解析。所有文件先解析真实路径、验证为
普通文件并应用大小限制；外部路径及符号链接越界会拒绝。当前配置若
`base_directory: ./.copilot-data`，Runtime 生成的截图附件无需增加额外配置即可上传。

旧 `feishu_bridge.send_file_sync` 对 SVG 使用通用文件消息，因此 `kanzi-screenshot.svg` 会按原
文件名发送，但通常不提供图片预览；PNG/JPG 等受支持图片仍按原样走图片消息。

远程 Kanzi MCP 返回 JSON 下载 URL 时走另一条独立路径，只允许
`artifacts.allowed_origins` 中明确列出的来源。Copilot 使用以下内置安全工具，不把下载正文
直接塞进模型上下文：

| 工具 | 用途 |
|---|---|
| `artifact_download` | 下载到当前 `session-state\<session-id>\files`，仅返回路径、MIME 和大小 |
| `artifact_read` | 从字节偏移开始读取受限 UTF-8 片段 |
| `artifact_search` | 流式关键词搜索并返回少量上下文 |
| `artifact_json_query` | 支持 `$.items[0].name` 形式的简单 JSON 路径 |
| `artifact_materialize_image` | 将白名单 URL 或 JSON 字段内 base64/data URL 物化为 PNG/JPEG/SVG |

所有工具结果受 `artifacts.max_tool_output_chars` 硬限制。工具只能访问当前 SDK 会话的
`files` 目录，不能读取其他会话；JSON 解析也受 `max_download_bytes` 限制。图片物化工具返回
现有 `[FILE] path=...` 标记，由 Worker 继续交给旧飞书桥上传。权限策略仍是
`default: deny`，示例仅额外允许 Runtime 实际产生的只读 kind `read`。
