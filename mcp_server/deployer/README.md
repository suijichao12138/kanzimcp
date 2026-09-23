# kanzi-deployer

> KanziMCP 部署管理器 —— 网页版部署 / 配置 / 运维控制台
>
> **原名 OTA（`mcp_server/ota/`），已废弃，勿用。** 见文末说明。

## 这是什么

一个常驻的 Windows 程序，启动后在局域网提供一个网页，用来：

- **首次部署**：填好配置 → 一键拉源码 → 编译 → 生成配置 → 启动三个组件
- **版本升级**：查看远端最新版本，**点按钮**才升级（二次确认，不中断在跑的任务）
- **进程管理**：relay / http / feishu 单组件重启、全部重启
- **配置管理**：网页编辑三个组件的配置文件，保存后按需重启
- **日志查看**：relay / http / feishu / deployer 四个日志页分开看

## 三个组件

| 组件 | 程序 | 作用 |
|---|---|---|
| relay | `relay_multi.exe` | WebSocket 中继（通道隔离、多角色转发） |
| http | `kz_mcp_http.exe` | MCP over HTTP 服务（给 Copilot 连） |
| feishu | `feishu_bridge.exe` | 飞书 ↔ Copilot 桥（多 bot） |

## 目录结构

```
<安装目录>/
├── kanzi-deployer.exe
├── deployer_config.json       # 部署管理器自己的配置
├── bin/                       # 三组件 exe
├── conf/                      # 三组件配置
├── logs/                      # 日志（各组件自己轮转 10MB×5）
├── src/                       # git clone 的源码
├── tmp_results/               # http 外置结果文件
├── data/                      # 运行时数据
└── _backup/                   # 升级前备份（回滚用）
```

## 日志

三个组件都支持 `--log-path <路径>`，用 Python 标准库 `RotatingFileHandler`
自己轮转（10MB × 5 个备份），**轮转过程不中断服务**。

```bash
relay_multi.exe   --log-path logs/relay.log
kz_mcp_http.exe   --config conf/config.json --log-path logs/http.log
feishu_bridge.exe --config conf/feishu_config.json --log-path logs/feishu.log
```

不传 `--log-path` 则只输出控制台（向后兼容）。

## 旧版说明

`mcp_server/ota/` 是**旧版 OTA 程序，已停止使用**，仅作历史保留。
新版功能全部由本目录（`mcp_server/deployer/`）提供。
