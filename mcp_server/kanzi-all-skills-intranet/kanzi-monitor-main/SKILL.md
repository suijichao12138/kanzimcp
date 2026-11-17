---
name: kanzi-monitor-main
description: 主会话调度 skill（设备测试类）。负责测试前的环境准备——探测串口（不假定 COM3）、询问并确认测试程序位置、停掉默认程序、启动测试程序、起串口中继桥、探测环境验收——再拆解测试任务、派发给 kanzi-monitor 子会话、汇总子会话回报并收尾还原。主会话不执行 props/getprop/setprop/trace 等具体测试命令。配套 skill：kanzi-monitor-task（子会话执行）。
---

# kanzi-monitor 主会话调度

> 结构参考 `kanzi-main-protocol`：理解 → 拆解 → 派发 → 汇总。**区别**：本 skill 负责**环境就绪**，具体测试命令交给子会话。
> 配套文件：`kanzi-monitor-task`（子会话执行手册），派发时必须让子会话先通读它。

---

## 0. 职责边界

| 主会话**要做** | 主会话**不做** |
|---|---|
| 探测/确认串口，起中继桥 | `props` / `getprop` / `setprop` / `trace` 等测试命令 |
| 停默认程序、启动测试程序 | 解析 trace json、算帧耗时 |
| 探测环境并验收（5 项） | 判断业务属性语义、猜节点路径 |
| 需求理解 → 执行步骤 → 任务拆解 | 传文件、装程序 |
| 派发子会话、汇总回报、收尾还原 | 重启设备、reset 会话 |

**铁律**：环境没验收通过，**不许派子会话**。子会话拿不到可用环境只会空转烧调用次数。

### 0.1 脚本位置（所有命令的前提）

本 skill 用到的全部脚本放在**程序根目录下的 `monitor_tools` 目录**：

```
<程序根目录>                      ← nlp-worker 可执行文件 / config.yaml 所在目录
├─ monitor_tools\                 ← 脚本都在这
│  ├─ serial_probe.py            枚举 + 探测串口
│  ├─ serial_bridge.py           串口 <-> TCP 中继桥（长驻）
│  ├─ kzsh.py                    经桥发命令收回显（主力）
│  ├─ kzdump.py                  单条命令 + 大输出落盘
│  ├─ start_app.py               停默认程序 + 起测试程序 + 验收
│  ├─ dev_writecfg.py            把本地 cfg 写进设备
│  ├─ run_remote_script.py       编译机上执行脚本
│  ├─ get_remote.py              从编译机下载文件
│  ├─ requirements.txt           pyserial / paramiko
│  └─ README.md                  脚本用法速查
└─ workspace\workfile\           数据、计划、文档（不是脚本目录）
```

**四条规则**：

1. 命令一律写**相对路径** `monitor_tools\xxx.py`，并假定 **当前工作目录 = 程序根目录**；第一条命令前先 `cd <程序根目录>`。
2. 不要把脚本路径写成 `workspace\workfile\...` —— 那是数据目录。
3. 首次使用装依赖：`pip install -r monitor_tools\requirements.txt`。
4. 脚本不存在 → **停下来告诉用户**，不要自己重写替代脚本。

---

## 1. 五个必问项（缺一个不许开工）

环境**因人和机器而异，全部必须确认，禁止沿用上次的值**：

| # | 项 | 为什么必问 | 示例 |
|---|---|---|---|
| 1 | **串口** | 不一定是 COM3，插哪个口/是否有 USB 转串口都不同 | `COM5` |
| 2 | **测试程序位置** | 不同人打包位置不同 | `/var/log/test` |
| 3 | **测试程序名** | 不一定叫 clusterHmiMin | `clusterHmiMin` |
| 4 | **应用配置路径** | `-config=` 参数 | `/mnt/usr/share/theme/application_cluster_hmi.cfg` |
| 5 | **默认（量产）程序名** | 要先停掉它，否则抢屏/抢 GPU | `clusterHmi` |

一次性问完，不要挤牙膏：

```
开始前需要确认 5 个环境项：
1) 串口是哪个口？波特率多少？（我会先枚举再让你确认）
2) 测试程序在设备上哪个目录？
3) 测试程序叫什么名字？
4) 启动时 -config= 指向哪个文件？
5) 默认（量产）程序叫什么？要不要我先停掉？
```

**🚫 停等铁律（必须遵守）**：上述 **5 项任意一项不明确**（用户没回答 / 回答含糊 / 你无法确定），**立即停止**，等用户明确回答后再继续，**禁止自己探索**（不自行 ls/pidin/探测目录/猜路径/推断程序名）。

- 停止时**明确说出缺哪一项**，把问题原样抛给用户，不要带猜测结论。
- 用户回答后**逐项复述确认**，全部明确才进入阶段 A。
- **禁止**用「上次的值」「惯例」「常见路径」补齐缺失项——每项都必须来自用户本次确认。
- 串口可以先用 `serial_probe.py` **枚举**（枚举不算探索，是提供选项），但**选定哪个口必须由用户确认**。

**附带可选项**（有默认值，但要确认）：
- 插件运行配置 `kanzimonitor.cfg` 里的 `RemoteConsoleEnabled` / 端口（默认 `56000`）
- 引擎剖析库目录（`LD_LIBRARY_PATH` 用，常见 `<部署目录>/kzprof`）
- 是否需要 `HMI_RES_PROFILING=1`（需要资源加载数据时必须）

---

## 2. 阶段 A：探测串口

### A.1 一条命令搞定：枚举 + 逐口逐波特率探测

```powershell
cd <程序根目录>
python monitor_tools\serial_probe.py
# 只试指定口            ：python monitor_tools\serial_probe.py --ports COM5,COM7
# 指定波特率尝试顺序    ：python monitor_tools\serial_probe.py --baud 921600,115200
# 命中后再验证一条命令  ：python monitor_tools\serial_probe.py --send "echo alive"
```

命中会直接打印结论行 `>>> 目标串口 = COMx  波特率 = yyyyy`，照抄进 env.json。

报错对照：

| 脚本输出 | 处理 |
|---|---|
| `没有枚举到任何串口` | 驱动未装 / 线是充电线 → 让用户查设备管理器 |
| `缺少 pyserial` | `pip install -r monitor_tools\requirements.txt` |
| `被占用` | 该口被 Tera Term / PuTTY 占着 → 让用户关掉，**不要绕** |
| `该口不支持波特率 X` | 正常，脚本会继续试下一个波特率 |

**判据**（脚本已内置，这里是人工复核口径）：

| 回显特征 | 结论 |
|---|---|
| 出现 `# ` / `sh ` / 登录提示 / `QNX` | ✅ 命中目标板 |
| 只有少量乱码或无回显 | 波特率可能不对，换 `921600` / `460800` / `115200` 再试 |
| `PermissionError(13)` / `Access is denied` | 该口被 **Tera Term / PuTTY / 其他工具** 占用 → 让用户关掉，**不要自己找办法** |
| 有回显但像是别的设备（蓝牙/虚拟串口） | 跳过，试下一个 |

### A.2 结果落盘

写入 `workspace\workfile\plan\env.json`（见 §9），**后续所有命令都从这份文件取变量，不再硬编码**。

---

## 3. 阶段 B：起串口中继桥

### B.1 起桥

```powershell
cd <程序根目录>
python monitor_tools\serial_bridge.py <COM> <BAUD> <BRIDGE_PORT> <RAW_LOG>
# 例：python monitor_tools\serial_bridge.py COM5 115200 47001 serial_raw.log
```

- 用 `mode="async"` 启动（长驻进程，sync 会卡住）。
- **起桥后立刻记下 PID**（`Get-CimInstance Win32_Process -Filter "Name='python.exe'"` 里 `serial_bridge.py` 那条），写进 `env.json` 的 `bridge_pid`。**收尾时按 §9 第 4 条停掉它**——自己起的必须自己停。
- `BRIDGE_PORT` 默认 `47001`；若被占（`OSError: [WinError 10048]`）换 `47002`/`47003`，**并记进 env.json**。
- `RAW_LOG` 保留原始字节流，用于事后取证（子会话回报可疑时回查）。

### B.2 验证桥通

```powershell
python -c "import socket; s=socket.create_connection(('127.0.0.1',47001),3); print('bridge OK'); s.close()"
```

### B.3 之后所有设备命令走

```powershell
python monitor_tools\kzsh.py "<shell 命令>"
python monitor_tools\kzsh.py --wait 3 "@cr"          # 唤醒 getty / 等 3 秒
python monitor_tools\kzsh.py "@raw:<原样文本>"        # 不加换行的原样发送
```

---

## 4. 阶段 C：停默认程序 + 启测试程序

### C.1 停默认（量产）程序

```powershell
python monitor_tools\kzsh.py "pidin | grep -i <default_app_name>"
```

- 无输出 → 已经没跑，跳过 C.2。
- 有输出 → 优先用系统工具停（优雅，不会留下资源占用）：

```powershell
python monitor_tools\kzsh.py "sysmgrtool stop <default_app_name>"
python monitor_tools\kzsh.py "pidin | grep -i <default_app_name>"      # 必须确认已消失
```

- 没有 `sysmgrtool` 或停不掉 → 拿 PID 直接杀：

```powershell
python monitor_tools\kzsh.py "kill <PID>"
```

### C.2 清掉可能残留的测试实例

```powershell
python monitor_tools\kzsh.py "pidin | grep -i <app_name>"
```

有残留 → `kill <PID>`。**绝不**同时跑两个测试实例（抢 GPU/抢屏，数据全废）。

### C.3 启动测试程序（模板，5 个变量全部替换）

```powershell
python monitor_tools\kzsh.py --wait 8 "cd <deploy_dir> && <ENV_FLAGS> LD_LIBRARY_PATH=<lib_dir>:<deploy_dir> ./<app_name> -config=<app_config> > <deploy_dir>/<app_name>.run.log 2>&1 &"
```

**三个必须保留的要点**（缺一个就白跑）：

1. **`cd <deploy_dir>` 必须在前**——trace 文件写到进程**当前工作目录**，不 cd 就落到别处找不到。
2. **`LD_LIBRARY_PATH=<lib_dir>:<deploy_dir>` 必须带**——应用 RPATH 通常只有 `$ORIGIN`，剖析引擎库在子目录 `kzprof/`；不带会退到系统 Release 库 → **ABI 不符，首帧后 SIGSEGV**。
3. **`> ... 2>&1 &` 必须带**——不加会把串口控制台淹掉，后续命令全乱；重定向后 `&` 后台化。

`<ENV_FLAGS>` 按需：需要资源加载剖析数据时加 `<RES_PROFILING_FLAG>=1`（本工程为 `HMI_RES_PROFILING=1`）。

> 💡 **可一步做完 C.1–C.4**（推荐；脚本已强制上述三个要点，并自带验收判定）：
>
> ```powershell
> python monitor_tools\start_app.py --deploy-dir <deploy_dir> --app <app_name> `
>   --config <app_config> --default-app <default_app_name> --stop-default --env "<ENV_FLAGS>"
> ```
>
> 可选覆盖：`--console-port <port>`、`--lib-dir <dir>`（默认 `<deploy_dir>/kzprof`）、`--boot-wait 15`、`--log-name <名字>`。
> 脚本会依次做：停默认程序 → 清残留测试实例 → `chmod` → 启动 → `pidin`/`netstat`/`tail` → 打印`[ OK ]`/`[FAIL]` 结论。

### C.4 判定启动成功

```powershell
python monitor_tools\kzsh.py --wait 3 "tail -30 <deploy_dir>/<app_name>.run.log"
```

| 日志特征 | 结论 |
|---|---|
| `Listening for connections...` / `TraceService: set Profiling Category` | ✅ 起来了 |
| `SIGSEGV` / `core dumped` / `Killed` / 无新日志 | ❌ 起失败 → 查 §10 故障表，**不要立刻重试派子会话** |
| `error while loading shared libraries` | ❌ `LD_LIBRARY_PATH` / `lib_dir` 写错 |

---

## 5. 阶段 D：环境验收（5 项，全过才能派）

| # | 检查项 | 命令 | 通过判据 |
|---|---|---|---|
| 1 | 测试进程存活 | `pidin \| grep -i <app_name>` | 有且仅有 1 个 PID |
| 2 | monitor 控制台可连 | `python monitor_tools\kzsh.py --wait 3 "telnet 127.0.0.1 <console_port>"` | 出现 `Connected` |
| 3 | 插件配置生效 | `cat <deploy_dir>/kanzimonitor.cfg` | `RemoteConsoleEnabled = 1`、端口一致 |
| 4 | 桥 + 串口通路 | `python monitor_tools\kzsh.py "echo alive"` | 回显 `alive` |
| 5 | 目标节点可寻址 | 进控制台后 `props <root_path>` | 打印 `node ... (Metaclass)` + `properties: N`（N>0） |

**任一项不过 → 停在这里查 §10，不要派子会话。**
第 5 项如果不知道根路径，先让子会话跑 `nodetreeinfo`，或先自己进控制台看一眼。

> ⚠️ 测完第 2/5 项后要退出 telnet（`Ctrl-]` 或 `exit`），否则后续 `kzsh.py` 发的命令还在 telnet 会话里。

---

## 6. 阶段 E：任务拆解（同 kanzi-main-protocol 阶段 1–3）

1. **需求理解摘要**：编号列出工作项，标注「需要哪些命令、产出什么数据」。
2. **执行步骤文档**：每步写目标 / 约束 / 验证方式，**不写具体参数值**（节点路径、属性名、目标值都从需求或数据源取）。
3. **拆任务**：一个子任务**最多 2 个操作类型**。典型切分：
   - `启动数据采集`（trace + 资源加载）
   - `属性写入时延`（setprop 埋点 + 帧标记）
   - `任意属性读写验证`
   - `帧耗时/渲染统计`
   - `抓卡顿现场`（watch 阈值监视 + trace，对应子会话 skill 配方 E）
   - `偶发卡顿自动抓`（写 cfg + 回报重启 + 事后取文件，配方 F）
   - `性能现状巡检`（overwatch.perf / watch metrics / appfpsinfo，配方 H）
4. 每个子任务描述单的第一条约束**必须**是：
   > 子会话已通过 task_dispatch 注入 `kanzi-monitor-task` skill（SKILL.md），直接通读注入内容全文，严格按其步骤执行，禁止脑补命令/参数。

5. **性能类任务记得加上「配置生效」这一步**：`kanzimonitor.cfg` / `perfinfolevel` 改动后插件只在启动时读一次，
   子会话改完会回报请你重启；**重启应用是你的职责**（`start_app.py`），不是子会话的。重启后再派后续采集。

---

## 7. 阶段 F：派发（描述单模板）

```
type: kanzi-monitor
objective: <一句话说清要测什么、产出什么数据>
data_source: <需求文档 / 参数来源文件路径>
project: <工程名>

constraints:
  1. 子会话已注入 kanzi-monitor-task skill，直接通读注入内容全文并严格照做（不用读任何外部文件）。
  2. 环境已就绪，直接用；不要再探测、不要重启程序、不要重新起桥：
     串口=<COM> 波特率=<BAUD> 桥端口=<BRIDGE_PORT>（PID=<PID>，已在跑）
     部署目录=<deploy_dir> 程序名=<app_name> 配置=<app_config>
     monitor 控制台端口=<console_port>
  3. 程序当前已在运行（PID <app_pid>），**不要 kill、不要重启**。
  4. 目标节点路径=<node_path>，属性=<property_name>，当前值=<current_value>（测试后写回该值）。
  5. 严禁传文件：禁止 scp/rz/sz/hex/awk/base64/nc/tftp，禁止传 .so / 程序 / trace 文件。
  6. 严禁勘察网络：禁止 ping / netstat -rn / route。
  7. 严禁重启设备、关机、reset 会话、删 <deploy_dir> 下文件。
  8. 工具调用上限 <N> 次；到上限或阻塞立即汇报，不要试错。
  9. 回报必须含：每条命令原文 + 原始输出片段（不加工、不省略错误）+ 结论表。
```

**为什么把环境变量写进约束**：子会话每次都是新上下文，让它自己探测等于把已验证的事重做一遍，还会因为路径/端口猜错而失败。

---

## 8. 阶段 G：汇总回报

### 8.1 回报可能丢，别干等

**已知系统性缺陷**：子会话「完成 → 主会话回报注入」这一段会**静默丢失**（子会话其实早就成功结束了）。判定与补救：

1. 查 `workspace\workfile\plan\<对话>.json` 的 `steps[].status`——这是**唯一真相源**。
2. `status=done` 但你没收到回报 → 去读子会话自己的
   `.copilot-data/session-state/<session_id>/events.jsonl`，取最后一条 `type=assistant.message` 的 `data.content`。
3. `task_status` 报空闲 + plan 里有 `pending/retry` → 立即续派，**不要等**。

### 8.2 完成度检查

| 任务类型 | 必查项 |
|---|---|
| 启动数据 | trace 文件真存在（`ls -l`）＋ 含资源加载段 |
| 属性写入时延 | `setprop-probe:` 行数 = 预期次数；`frameMarkers` = 9；读回值正确；已写回原值 |
| 属性读写 | 首/末值对得上，属性数量对得上 |
| 帧耗时 | `appfpsinfo` 有输出且帧率合理 |
| 抓卡顿现场 | 日志有 `Performance watcher #... (current: ...)`；trace 文件真存在（`ls -l` 大小>0）；回报含阈值 / current / 文件名 / 用户操作；已 `watch clear` |
| 偶发卡顿自动抓 | cfg 三键已写入并回读一致；重启后有 `Configuration loaded`；有 `onFrameTask` 记录；trace 文件 ≥1 个；cfg 已还原 |
| 性能巡检 | 有 3 次稳态读数；`appfps`/`fps` 一致；队列非长期非 0；`perfinfolevel` 前后一致 |
| 任意任务收尾 | 子会话回报里有「已停止的脚本」一行；主会话自己也核对一遍进程/端口 |

### 8.3 数值合理性对照（明显偏离就怀疑固件/参数不对）

在本工程实测基线（供 sanity check，**不是验收标准**）：

| 指标 | 参考值 |
|---|---|
| `setprop` 的 `resolve` | 5–15 us |
| `setprop` 的 `apply` | 800–1000 us（**占 98%**） |
| `setprop` 的 `readback` | 2–8 us |
| 写入 → 首帧渲染完成 | ≈ 18 ms（约 1 个 vsync） |
| 写入 → 3 帧后稳定 | ≈ 51–52 ms |
| 帧间隔 | ≈ 17 ms（≈59 FPS） |

---

## 9. 阶段 H：收尾

> ⚠️ **铁规：谁起的脚本谁停。** 本次会话里由你启动的每一个常驻脚本（串口中继桥 `serial_bridge.py`、任何 `Start-Process`/`Start-Job` 起的中继/轮询/采集进程），**必须在任务结束前全部停掉**，并用「端口已释放 + 进程已消失」两条证据确认。**绝不留着自己起的进程占着串口/端口**——那会让下一个人（或下一轮测试）一开串口就 `PermissionError(13)`、一起桥就 `10048`，而且没人知道是谁占的。

收尾按顺序逐条执行，一条都不能跳：

1. **退出测试程序**：控制台里 `appquit`（优雅）；不行再 `kill <PID>`。
2. **清理 core**：`ls -l <deploy_dir>/*.core` → 有就 `rm`（`appquit` 有时会写 core，占磁盘）。
3. **恢复默认程序**（用户要求时）：`sysmgrtool start <default_app_name>`。
4. **停掉自己起的所有脚本**（逐条核对，不留一个）：
   ```powershell
   # 先列：看还有哪些是本会话起的
   Get-CimInstance Win32_Process -Filter "Name='python.exe'" | Select-Object ProcessId,CommandLine
   # 再停：按 PID 精确停，禁止按名字杀
   Stop-Process -Id <bridge_pid> -Force
   # 验一：进程没了
   Get-CimInstance Win32_Process -Filter "Name='python.exe'" | Select-Object ProcessId,CommandLine
   # 验二：端口释放了
   netstat -ano | Select-String ':<bridge_port>'
   ```
   两条验证都要「输出为空」才算停干净。`Start-Job` 起的任务用 `Get-Job` / `Remove-Job -Force` 一并清。
5. **落盘报告**：数据表 + 结论 + 异常备注，写进 `workspace\workfile\docs\`。
6. **回报里写明已停**：把停掉的脚本 + PID + 端口验证结果写进最终回报，让用户能核。

### env.json 结构

```json
{
  "com_port": "COM5",
  "baud": 115200,
  "bridge_port": 47001,
  "bridge_pid": 6008,
  "raw_log": "serial_raw.log",
  "deploy_dir": "/var/log/test",
  "app_name": "clusterHmiMin",
  "default_app_name": "clusterHmi",
  "app_config": "/mnt/usr/share/theme/application_cluster_hmi.cfg",
  "lib_dir": "/var/log/test/kzprof",
  "env_flags": "HMI_RES_PROFILING=1",
  "console_port": 56000,
  "app_pid": 12836961,
  "verified_at": "2026-11-17T11:28:00+08:00"
}
```

---

## 10. 故障速查（主会话侧）

| 现象 | 原因 | 处理 |
|---|---|---|
| 串口打不开，`PermissionError(13)` | Tera Term / PuTTY 占用 | 让用户关掉，**别绕** |
| 探测所有口都无回显 | 波特率不对 / 板子没上电 / 线是充电线 | 换波特率 → 问用户上电状态 → 换线 |
| 桥连不上 `10048` | BRIDGE_PORT 被占 | 换端口，记进 env.json |
| 应用起不来 `error while loading shared libraries` | `LD_LIBRARY_PATH` 或 `lib_dir` 错 | 按 §4 C.3 原文重发 |
| 首帧后 SIGSEGV | 同上（退到系统 Release 引擎库） | 同上 |
| `telnet 127.0.0.1 <console_port>` refused | 应用没跑 / 已崩 | 看 `run.log`，**别反复 telnet** |
| 控制台报 `Command xxx not found` | 发裸 `\r` 之后紧跟的第一条命令会丢 | 重发一次即可；或用 `--wait` 拉开间隔 |
| getty 掉线，回显全无 | 串口登录会话掉了 | `@cr` 唤醒，不行上报用户人工处理 |
| 子会话一律被拒「上一个任务还在执行中」 | **reset 了正在跑的子会话** → 队列所有权泄漏 | 改 plan/reset 都无效，**只能重启 nlp_worker** |

---

## 11. 禁止项（红线）

1. **绝不 `/api/sessions/reset` 正在跑的子会话** —— 会造成队列所有权永久泄漏，之后每次 `task_dispatch` 都被拒，只能重启 nlp_worker。要中止只能 `task_cancel`。
2. **绝不重启 / 关机设备**。
3. **绝不传文件**（`.so`、程序、trace），一切由人手工替换/拷走。
4. **绝不假设串口是 COM3、部署目录是固定路径** —— 每次问。
5. **绝不在环境未验收（§5 五项）的情况下派子会话**。
6. **绝不硬编码上一次的环境值** —— 换人换机就全变了。
7. **绝不留着自己起的脚本** —— 串口桥、中继、采集、轮询，任务一结束就按 §9 第 4 条停干净（进程列表 + 端口两条验证），并在回报里写明停掉的 PID。
