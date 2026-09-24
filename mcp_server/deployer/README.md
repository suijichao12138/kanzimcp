# kanzi-deployer

> KanziMCP 部署管理器 —— 网页版「部署 / 配置 / 升级 / 运维」控制台
>
> 零第三方依赖（Python 标准库）　|　常驻 Windows，局域网网页访问

**详细文档** → [`docs/使用手册.md`](docs/使用手册.md)（怎么用）　·　[`docs/整体架构文档.md`](docs/整体架构文档.md)（怎么转）

> ⚠️ 旧版 OTA（`mcp_server/ota/`）已废弃，见文末。

---

## 这是什么

一个常驻 Windows 程序。启动后在局域网提供一个网页，把原来手敲命令行的活收成一个界面：

| 能力 | 说明 |
|---|---|
| **首次部署** | 配置向导 → 一键拉源码 → 编译 → 生成配置 → 启动三组件 |
| **版本升级** | 后台轮询远端版本，**点按钮才升级**（二次确认，不中断在跑的任务） |
| **进程管理** | 单组件重启 / 全部重启。**relay 重启会连带重启 http + feishu**（下游依赖） |
| **配置管理** | 网页编辑四个配置文件，保存后按需重启（白名单和桥配置热更新，不用重启） |
| **日志查看** | 一个日志页切换四个日志源，可调行数、自动刷新、一键清空 |
| **健康监控** | 每 30s 检查三组件，挂了/恢复 → 飞书通知（**只通知，不自动重启**） |
| **飞书通知** | 部署/升级成功失败、发现新版本、组件异常，都推到飞书 |
| **环境自检** | Python / PyInstaller / git 是否可用，缺什么一眼看到 |
| **访问密码** | HTTP Basic Auth，密码存 SHA-256 哈希 |

### 它管理的三个组件

| 组件 | 程序 | 作用 | 默认端口 |
|---|---|---|---|
| relay | `relay_multi.exe` | WebSocket 中继（按路径分通道、多角色转发） | 58080 |
| http | `kz_mcp_http.exe` | MCP over HTTP 端点（给 Copilot 连） | 9001 |
| feishu | `feishu_bridge.exe` | 飞书 ↔ Copilot 桥（多 bot + 文件服务） | 8081 |

**启动顺序固定 `relay → http → feishu`**（停止按反序）—— http 和 feishu 都要连 relay。

---

## 快速开始

```bat
:: 双击或命令行启动
kanzi-deployer.exe
```

启动日志会打印访问地址和**首次自动生成的随机密码**：

```
🌐 管理页面: http://0.0.0.0:9100
   局域网访问: http://10.10.118.152:9100
🔑 首次启动，已生成访问密码: xxxxxxxx
```

浏览器打开 `http://<本机IP>:9100`，用户名 `admin` + 上面的密码登录。
没部署过时会自动进入**配置向导**（三步：组件参数 → 飞书通知 → 一键部署）。

### 命令行参数

| 参数 | 作用 |
|---|---|
| `--config <路径>` | 指定配置文件（默认：安装目录下 `deployer_config.json`） |
| `--no-web` | 不启动网页，只跑后台版本轮询 |
| `--check-update` | 只查一次远端版本后退出（脚本用） |
| `--test-notify` | 只发一条飞书测试通知后退出 |
| `--version` | 打印版本号 |

---

## 实施要点

**① 白名单不能为空**

`conf/users.json` 为空时 http 组件**直接 `sys.exit(1)` 退出**，部署必然失败。页面会提前拦住。

**② relay 重启连带下游**

relay 是 http 和 feishu 的依赖。单独重启 relay 时，会**先停 http + feishu，再停 relay，然后按序全部拉起**。

**③ 探活按各组件真实协议走**（不能一刀切）

| 组件 | 协议 | 探测方式 |
|---|---|---|
| relay | WebSocket | 发真握手 |
| http | **裸 HTTP**（`asyncio.start_server`） | 发 HTTP 请求，收到任何响应即健康 |
| feishu | 进程 | 查进程名 |

> ⚠️ http 组件**不是** WebSocket 服务，对它发握手会失败。

**④ 进程真停才继续**

`taskkill` 是异步的，**返回 0 不代表进程已死**。所以会轮询 `tasklist` 确认进程真没了、
再探测文件句柄真释放了，才覆盖 exe —— 这是 `[WinError 5] 拒绝访问` 的根因所在。

**⑤ 配置单向生成**

页面配置（`deployer_config.json`）→ `core/templates.py` → 生成 `conf/` 下三个文件。
**手改 `conf/` 会被下次部署覆盖**，要改就在页面改。

**⑥ 升级失败自动回滚**

任何一步失败 → 从 `_backup/` 恢复上一版 exe（回滚前同样先杀残留、等文件释放）。

---

## 目录结构

```
<安装目录>/
├── kanzi-deployer.exe
├── deployer_config.json       # 部署管理器自己的配置
├── bin/                       # 三组件 exe
│   ├── relay_multi.exe
│   ├── kz_mcp_http.exe
│   └── feishu_bridge.exe
├── conf/                      # 三组件配置（页面生成，勿手改）
│   ├── config.json            #   http 组件配置
│   ├── users.json             #   http 白名单（热更新，不用重启）
│   └── feishu_config.json     #   飞书桥配置（3s 热更新，不用重启）
├── logs/                      # 日志（各组件自己轮转 10MB×5）
│   ├── deployer.log
│   ├── relay.log
│   ├── http.log
│   └── feishu.log
├── src/                       # git clone 的源码
├── tmp_results/               # http 外置结果文件
├── data/                      # 运行时数据（state.json 等）
└── _backup/                   # 升级前备份（回滚用）
```

## 源码结构

```
mcp_server/deployer/
├── deployer.py                # 主入口：Web + 版本轮询 + 健康监控
├── build.bat                  # 打包成 kanzi-deployer.exe
├── docs/                      # 使用手册 + 整体架构文档
├── core/                      # 核心逻辑（不依赖 Web 层）
│   ├── config.py              #   配置加载/保存/默认值
│   ├── paths.py               #   目录结构管理
│   ├── gitops.py              #   git 操作（查 tag / clone / checkout）
│   ├── builder.py             #   PyInstaller 编译三组件
│   ├── deploy.py              #   部署/升级编排（核心流程）
│   ├── process.py             #   进程管理（启停/重启/状态）
│   ├── health.py              #   健康检查（WS 握手 / HTTP / 进程）
│   ├── monitor.py             #   组件健康监控（挂了→飞书通知）
│   ├── notify.py              #   飞书通知（urllib 直调，零依赖）
│   ├── templates.py           #   生成组件配置文件
│   ├── envcheck.py            #   环境检测
│   └── logs.py                #   日志读取/清空/轮转信息
└── web/                       # Web 层
    ├── server.py              #   HTTP server + 路由 + Basic Auth
    ├── api.py                 #   各接口实现
    ├── tasks.py               #   异步任务管理（部署/升级进度）
    ├── auth.py                #   Basic Auth 校验
    └── static/                #   index.html / app.js / style.css
```

---

## 日志

四个日志源都支持 `--log-path <路径>`，用标准库 `RotatingFileHandler`
**自己轮转（10MB × 5 个备份），轮转过程不中断服务**。

```bat
relay_multi.exe   --log-path logs/relay.log
kz_mcp_http.exe   --config conf/config.json --log-path logs/http.log
feishu_bridge.exe --config conf/feishu_config.json --log-path logs/feishu.log
```

**不传 `--log-path` 则只输出控制台**（向后兼容）。

在页面「日志」页用一个下拉框切换四个日志源，可调 100/200/500/1000 行、自动刷新、清空。

---

## 版本号说明

| 名称 | 位置 | 含义 |
|---|---|---|
| `deployer.py::VERSION` | 源码 | **管理器程序自身**的版本号 |
| git tag（如 `v12`） | 仓库 | 整个 KanziMCP 项目的发布版本 |

两者**不是一回事**：管理器读的是 git tag 来判断「有没有新版本要升级」。

---

## 常用排查

| 症状 | 原因 |
|---|---|
| 飞书报「没有可用的 Chat Worker」 | bot 名 ≠ relay 通道名（必须一致） |
| http 组件起不来 | 白名单为空 |
| Copilot 连不上 http | `listen` 不是 `0.0.0.0` |
| AI 拿不到外置文件 | `result_public_host` 是 `0.0.0.0` 或填错 |
| 升级报 `WinError 5` | 进程残留 / 文件句柄没释放 |
| 收不到飞书通知 | App ID / App Secret / 接收人 ID 没配全，或权限不足 |

**升级失败时可先手动清进程再重试：**

```bat
taskkill /F /T /IM relay_multi.exe
taskkill /F /T /IM kz_mcp_http.exe
taskkill /F /T /IM feishu_bridge.exe
```

更多问题见 [`docs/使用手册.md`](docs/使用手册.md) 的 FAQ（13 条，含各问题对应哪个版本修复）。

---

## 旧版说明

`mcp_server/ota/` 是**旧版 OTA 程序（`ota_agent.py`），已停止使用**，
仅作历史保留，见其 `DEPRECATED.md`。

新版功能全部由本目录（`mcp_server/deployer/`）提供 —— 相比旧版多了
网页界面、模块化结构、组件健康监控、飞书通知、配置向导、四日志源分离。
