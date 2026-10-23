# nlp_worker 网页控制台（Web 控制台）方案

> 2026-10-23 定稿。随 nlp_worker 同进程内嵌启动，提供会话管理 + 配置修改。
> 架构与 deployer 相同（stdlib ThreadingHTTPServer，零第三方依赖）。

## 一、背景与目标

nlp_worker 是飞书 → relay → Kanzi 链路中的 Copilot 工作进程。此前：
- **会话管理**：只能通过飞书 `/status` `/new` 命令，无法看到主/子会话全景、无法网页操作
- **配置修改**：只能手改 `config.yaml` + `.env`，没有可视化界面，环境变量联动（`${KEY}` 展开/缺失检查/反向索引）全靠人工

本次新增**网页控制台**，提供：
1. **会话管理**：主会话 + 子会话列表、状态查看、重置、清空
2. **配置修改**：config.yaml 按分组独立页面表单编辑
3. **环境变量**：.env 增删、掩码显示、与 config 的双向联动

## 二、总体架构

```
nlp_worker/
  web/                        # 新增：网页控制台（照 deployer 模式）
    __init__.py
    server.py                 # stdlib ThreadingHTTPServer + 路由分发 + start()/stop()
    api.py                    # 所有 /api/* 处理（会话 / 配置 / 环境变量）
    config_groups.py          # config.yaml 分组定义（唯一分组真相来源）
    static/
      index.html              # 单页前端（Tab：会话管理 / 配置修改 / 环境变量）
      app.js
      style.css
  nlp_worker.py               # 集成：run() 里 web.start()，stop() 里 web.stop()
  copilot_runtime.py          # 新增 WebConfig（enabled / listen_host / listen_port）
  session_store.py            # 新增 SessionStore.list_all()
  nlp_worker.spec             # PyInstaller 打包：web 包 + static 数据文件
  config.example.yaml         # 新增 web: 段
```

### 技术选型（与 deployer 相同）

| 项 | 选择 | 理由 |
|---|---|---|
| Web 框架 | 标准库 `http.server.ThreadingHTTPServer` | 零第三方依赖，Windows 打包最稳 |
| 启动方式 | 随 nlp_worker 同进程，`threading.Thread` + `serve_forever` | 部署简单，一个进程 |
| 前端 | 原生 HTML + JS + CSS（单页，无框架） | 无构建步骤，Windows 无 node 也能跑 |
| 配置读写 | PyYAML（nlp_worker 已有依赖） | 直接复用 |
| 会话数据 | SQLite `session_mappings`（只读）+ 内存 sessions | 复用现有 SessionStore |
| 鉴权 | 无 token | 监听 IP 可配（默认 127.0.0.1 仅本机） |

### 配置段（config.yaml 新增）

```yaml
web:
  enabled: true
  listen_host: 127.0.0.1   # 可配 0.0.0.0 或局域网 IP（无鉴权，注意安全）
  listen_port: 8400
```

## 三、功能设计

### 3.1 会话管理（/sessions 或首页 Tab）

数据来源：`SessionStore.list_all()`（SQLite）+ `CopilotRuntime.sessions`（内存）。

| 功能 | 实现 |
|---|---|
| 会话列表 | 主/子会话区分（`task:` 前缀 = 子会话）、SDK session_id、model、status、创建/更新时间、last_error、连接态 |
| 重置会话 | POST /api/sessions/reset → `copilot.new_session(key)`（跨线程用 `asyncio.run_coroutine_threadsafe` 提交主事件循环） |
| 清空全部 | POST /api/sessions/clear → 逐个重置 |
| 实时刷新 | 前端轮询 3 秒 + 状态栏 15 秒 |

### 3.2 配置修改（/config/{group} 每组分一页）

11 个分组，每个独立页面：

| 组 | 页面标题 | 类型 |
|---|---|---|
| web | 网页控制台 | fields |
| relay | 连接 Relay | fields |
| copilot | Copilot 模型 | fields |
| skills | Skills 加载 | skill_entries（含 max_file_bytes / max_total_bytes） |
| mcp_servers | MCP 服务 | dict_of_servers（每个服务含 enabled/type/url/headers/tools/timeout_seconds + 添加/删除） |
| artifacts | 文件落盘 Artifacts | fields |
| compatibility | 兼容与进度反馈 | fields |
| messages | 消息处理 | fields |
| storage | 存储 | fields |
| logging | 日志 | fields |
| task_dispatch | 任务派发(主/子会话) | fields（含 main_skills/common_skills/session_types dict 行编辑 + 描述） |

- 字段类型：str / int / float / bool / enum / list / textarea / secret / dict
- dict 类型（session_types）：每行 `类型 → skill1, skill2`，可增删行
- 保存：yaml 简单重写（不保留原注释）

### 3.3 环境变量（/config/env 独立页）

| 功能 | 实现 |
|---|---|
| 列表 | 所有 KEY + 值掩码（`xx******`）+ 被 config 引用位置（反向索引） |
| 增删 | POST /api/env 新增/修改、DELETE /api/env/{key} 删除，纯 KV 无结构限制 |
| 缺失警告 | config 引用但 .env 缺失的 KEY 列表高亮提示 |
| 表单联动 | config 表单里 `${KEY}` 整值占位 → 显示真实值 + 标注"环境变量 KEY"；缺失 → 红框警告 |

### 3.4 密钥安全（铁律）

- **`${KEY}` 占位保护**：config 里 `xxx: ${KEY}` 的字段，保存时无论前端提交什么值，后端强制写回 `${KEY}` 占位，**真实密钥绝不落盘 config.yaml**（只存在于 .env）
- 例外：字段标记 `env=None`（如 Provider API Key 按老隋要求直接显示 config 值）时不做联动、不做保护，直接保存 config 里的值

## 四、API 一览

```
GET  /                       → index.html
GET  /static/*               → 静态资源
GET  /api/status             → 服务状态（通道/模型/会话数/web 配置/路径）
GET  /api/sessions           → 会话列表（主/子区分）
POST /api/sessions/reset     → 重置指定会话 {key}
POST /api/sessions/clear     → 清空全部会话
GET  /api/config             → 全部分组定义（config_groups 元数据）
GET  /api/config/{group}     → 某组配置（env 展开 + 缺失标记）
POST /api/config/{group}     → 保存某组配置
GET  /api/env                → 环境变量列表（掩码 + 反向索引 + 缺失）
POST /api/env                → 新增/修改环境变量 {key, value}
DELETE /api/env/{key}        → 删除环境变量
```

## 五、会话重置的跨线程处理

web 请求在独立 HTTP 线程处理，`new_session()` 是协程：
```python
# api.py
loop = _main_loop()  # nlp_worker 在 run() 里设置 self.main_loop
new_id = asyncio.run_coroutine_threadsafe(copilot.new_session(key), loop).result(timeout=120)
```

## 六、PyInstaller 打包（nlp_worker.spec）

```python
# datas 加前端静态资源
(str(project_root / "web" / "static"), "web/static"),
# hiddenimports 加 web 包
"web.server", "web.api", "web.config_groups",
```

打包后 `_static_dir()` 通过 `sys._MEIPASS`（onedir = `_internal`）找到 `web/static`。

## 七、部署步骤

1. 更新 nlp_worker 源码目录：`web/` 包 + `nlp_worker.py` + `copilot_runtime.py` + `session_store.py` + `nlp_worker.spec` + `config.example.yaml`
2. config.yaml 加 `web:` 段（默认 127.0.0.1:8400）
3. 源码运行：直接启动；打包运行：Windows 重跑 `build_portable.cmd`
4. 浏览器打开 `http://<listen_host>:<listen_port>`
5. 改配置后需重启 nlp_worker 完全生效（网页有提示）

## 八、版本记录

| 版本 | 内容 |
|---|---|
| v3.0 | 首版：会话管理 + 11 组配置 + env 联动 + 密钥保护 |
| v3.1 | 修复三页同时显示 bug（CSS display 覆盖 hidden）；主/子会话区分 |
| v3.2 | MCP 服务标题改"MCP 服务" + headers 输入框；skills 加 max 字段；session_types dict 行编辑 + 描述 |
| v3.3 | skills 按钮对齐；MCP 启用 select 改小 + 字段标题 + grid 对齐；api_key 不再 env 联动 |
| v3.4 | MCP 启用 select 加大 + 添加/删除按钮；dict-row 对齐；env 值列宽加大 + 删除按钮不换行 |
| v3.5 | dict-row 删除按钮水平对齐（!important 覆盖全局 margin）；MCP 删除按钮移到底部右侧；select/input 统一 32px 高 |
| v3.6 | 修复保存"未知配置组"（config_get 补 key 字段 + 前端 g.key||g.group） |

## 九、废弃 panel/ 目录说明

旧 `panel/`（PySide6 桌面面板：schema/form/panel_qt/runner/validate/widgets/yaml_io/dotenv_io/build_panel.bat）**未测试通过，已废弃删除**。网页控制台（web/）取代它，schema 驱动的思想由 `config_groups.py` 继承（加配置项只改 config_groups.py，前端/API 不用动）。
