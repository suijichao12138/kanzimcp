# monitor_tools — 仪表 monitor 插件测试工具集

位置约定：**本目录位于程序根目录下**，相对路径 `monitor_tools/`。
所有命令都假定**当前工作目录 = 程序根目录**（即 `config.yaml`、`nlp-worker.exe` 所在目录）。

```powershell
cd <程序根目录>            # 例：D:\...\nlp-worker-portable-win-x64-noconsole
python monitor_tools\kzsh.py "echo alive"
```

## 安装依赖

```powershell
pip install -r monitor_tools\requirements.txt
```

## 脚本表

| 脚本 | 用途 | 典型用法 |
|---|---|---|
| `serial_probe.py` | 枚举本机串口并逐个探测，找出连着目标板的那个 | `python monitor_tools\serial_probe.py`<br>`python monitor_tools\serial_probe.py --baud 921600,115200 --ports COM5,COM7` |
| `serial_bridge.py` | **长驻**双向桥：串口 ↔ 本地 TCP（必须 async 方式启动） | `python monitor_tools\serial_bridge.py COM5 115200 47001 serial_raw.log` |
| `kzsh.py` | 经桥发命令并收回显（设备测试主力） | `python monitor_tools\kzsh.py --wait 3 "telnet 127.0.0.1 56000"` |
| `kzdump.py` | 单条命令 + 大输出落盘（`props`/`cat`/`grep` 长输出） | `python monitor_tools\kzdump.py props.txt 60 "props RootPage/Info"` |
| `start_app.py` | 停默认程序 + 起测试程序 + 一键验收（含 LD_LIBRARY_PATH 强制） | `python monitor_tools\start_app.py --deploy-dir /var/log/test --app clusterHmiMin --config /mnt/usr/share/theme/application_cluster_hmi.cfg --default-app clusterHmi --stop-default --env HMI_RES_PROFILING=1` |
| `dev_writecfg.py` | 把本地 cfg 逐行 `echo` 写进设备（设备无网络上传通道时用） | `python monitor_tools\dev_writecfg.py kanzimonitor.cfg /var/log/test/kanzimonitor.cfg` |
| `webui_bridge.py` | 把「串口 shell 里的 monitor telnet 会话」包成干净的 Monitor TCP 端点（去回显），给官方 web-ui 用 | `python monitor_tools\webui_bridge.py --com COM3 --baud 115200 --listen 47002` |
| `start_webui.cmd` | 一键起 web-ui：适配桥 + `monitor-web-ui-win64.exe` | `monitor_tools\start_webui.cmd COM3 115200 47002` |
| `monitor-web-ui\` | 官方 Kanzi Monitor Web UI（`monitor-web-ui-win64.exe` + `index.html`） | 见 `monitor_tools\monitor-web-ui\README.md` |
| `run_remote_script.py` | 编译机上执行本地 sh 脚本 | `python monitor_tools\run_remote_script.py my_build.sh 1800` |
| `get_remote.py` | 从编译机下载文件 | `python monitor_tools\get_remote.py /home/u/x.so .\x.so` |

`run_remote_script.py` / `get_remote.py` 的连接信息走环境变量：
`KANZI_BUILD_HOST` / `KANZI_BUILD_USER` / `KANZI_BUILD_PASSWORD`。

## 串口桥的启动要点

1. **必须用后台方式启动**（长驻进程，前台会卡住调用方）。
2. 端口被占（`OSError: [WinError 10048]`）→ 换 `47002` / `47003`，并让所有后续命令都带 `--port`。
3. `serial_raw.log` 保留原始字节流，用于事后取证。
4. 串口被 Tera Term / PuTTY 占用会报 `PermissionError(13)` —— 让用户关掉，不要绕。
5. **谁起谁停**：任务/测试结束前按 PID 停掉自己起的桥（`Stop-Process -Id <pid> -Force`），并验证进程消失 + `netstat -ano | Select-String ':47001'` 为空。不留进程占端口。

## kzsh.py 特殊参数

| 写法 | 含义 |
|---|---|
| `"命令"` | 追加 `\n` 发送（正常用法） |
| `"@cr"` | 只发一个裸 `\r`（唤醒 getty / 回车） |
| `"@raw:文本"` | 原样发送，不追加换行 |

## Web UI（官方 monitor-web-ui，仪表没网线时走串口）

```powershell
# 一条命令起全套（适配桥 + web-ui），COM 口按实际改
monitor_tools\start_webui.cmd COM3 115200 47002
# 浏览器会自动打开 http://127.0.0.1:8765
```

链路：`web-ui :8765 ── ws ──> bridge ── TCP 47002 ──> webui_bridge.py ── 串口 ──> 仪表 shell ──telnet──> 127.0.0.1:56000`

要点：

1. **`SerialConsoleEnabled` 默认是 0**，所以官方 `--serial-port COM3` 直连串口永远卡在 "Connecting to Monitor" ——
   别试了，用 `start_webui.cmd`（= 串口 shell 里 telnet 到插件 TCP 56000，再由 `webui_bridge.py` 去掉 tty 回显）。
2. 仪表**有网线**时最省事：`monitor-web-ui-win64.exe --monitor-host <仪表IP>`（直连 56000，速度最快）。
3. 115200 波特率 ≈ 11.5 KB/s：`overwatch.nodes`（本机 X）约 16 s，节点树/属性/性能/日志可用；
   纹理预览、截图、trace 这类大图默认会被 UI 降到 64~128 px，仍很慢，**别开全分辨率**。
4. 协议默认 30 s 超时，树大容易超 → 启动时带 `--command-timeout 120`（`start_webui.cmd` 已带）。
5. 界面里的 **Auto-refresh 要关掉**，否则每几秒拉一遍整棵树，串口会被占满。
6. 用完关掉两个窗口（web-ui 窗口 + `webui-adapter` 窗口）；适配桥收到 Ctrl+C 会发 `^]` + `quit` 退出设备上的 telnet，把串口还给 shell。
7. 适配桥日志：`monitor_tools\webui_bridge.log`（能看到每条命令的耗时）。

## 相关文档
- 主会话调度：`workspace\workfile\docs\SKILL-kanzi-monitor-main.md`
- 子会话执行：`workspace\workfile\docs\SKILL-kanzi-monitor-task.md`
- 背景与数据：`workspace\workfile\docs\2026-11-16-monitor插件编译与启动性能分析.md`
