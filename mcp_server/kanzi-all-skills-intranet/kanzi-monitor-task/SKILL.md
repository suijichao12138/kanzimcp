---
name: kanzi-monitor-task
description: kanzi-monitor 子会话执行 skill。用主会话已建好的串口中继桥连上仪表，进入 monitor 插件命令控制台，按配方执行具体测试（启动/资源数据采集、属性写入时延、任意属性读写、帧耗时统计、卡顿现场抓取、性能巡检），解析输出并回报。含完整命令参考、各数据类型取值格式、输出字段含义、已知 quirks。配套 skill：kanzi-monitor-main（主会话调度）。
---

# kanzi-monitor 子会话执行

> **前置**：主会话已完成环境准备（起桥、停默认程序、启动测试程序、验收）。你**只需要跑测试命令**。
> 环境变量**全部从任务描述单读取**，描述单里没有的**停下来问，不许猜**。

---

## 0. 铁律

1. **不传文件**。不研究 `scp`/`rz`/`sz`/`hex`/`awk`/`base64`/`nc`/`tftp`，不传 `.so`/程序/trace。文件由人手工拷走。
2. **不勘察网络**。不 `ping` / `netstat -rn` / `route`，链路已由主会话验证过。
3. **不动环境**。不重启设备、不杀测试进程、不重启桥、不删设备文件、不 reset 会话。
4. **不猜变量**。串口、端口、部署目录、程序名、节点路径、属性名，全部来自描述单。缺一个就停下问。
5. **改了就还原**。测试写的任何属性，结束前必须写回描述单给的初值。
6. **有预算**。工具调用上限按描述单执行（默认 18 次）。到上限或卡住 → 立刻停，汇报已完成到哪一步 + 原始输出。
7. **改了设备配置项必须回报重启**。凡改 `kanzimonitor.cfg`（阈值/定时器/appending 等）或 `perfinfolevel`，都不能自己重启应用，必须汇报主会话重启后再继续；采集结束把改过的项全部还原。

---

## 1. 参数表（从描述单填）

| 变量 | 含义 | 示例 | 缺失时 |
|---|---|---|---|
| `<BRIDGE_PORT>` | 本机中继桥 TCP 端口 | `47001` | 问 |
| `<CONSOLE_PORT>` | 设备内 monitor 控制台端口 | `56000` | 问（或读 `kanzimonitor.cfg`） |
| `<DEPLOY_DIR>` | 测试程序部署目录 | `/var/log/test` | 问 |
| `<APP_NAME>` | 测试程序名 | `clusterHmiMin` | 问 |
| `<NODE_PATH>` | 目标节点路径 | `RootPage/Info` | 问或先 `nodetreeinfo` |
| `<PROPERTY>` | 目标属性名 | `sys.systemState` | 问 |
| `<CURRENT_VALUE>` | 属性当前值（测试后写回它） | `0` | 先 `getprop` 得到 |

---

## 1.5 脚本位置（所有命令的前提）

脚本在**程序根目录下的 `monitor_tools` 目录**，命令一律写相对路径 `monitor_tools\xxx.py`，
并假定 **当前工作目录 = 程序根目录**（`nlp-worker` 可执行文件 / `config.yaml` 所在目录）。

| 脚本 | 用途 |
|---|---|
| `monitor_tools\kzsh.py` | 经桥发命令收回显（**本 skill 主力，几乎每条命令都用它**） |
| `monitor_tools\kzdump.py` | 单条命令 + 大输出落盘（`props` / `nodetreeinfo` / `cat` 长输出） |
| `monitor_tools\serial_bridge.py` | 串口中继桥（**由主会话启动，你不要动**） |
| `monitor_tools\dev_writecfg.py` | 经桥把本地 `kanzimonitor.cfg` 写到设备（配方 F/G 用）：`python monitor_tools\dev_writecfg.py <本地cfg> <设备路径> [桥端口]` |

规则：

1. 开始前先 `cd <程序根目录>`，否则相对路径找不到脚本。
2. 缺依赖 → 汇报，不要自己乱装（依赖清单在 `monitor_tools\requirements.txt`）。
3. 脚本不存在 → **停下来汇报**，绝不用自己写的替代脚本。

---

## 2. 连接（3 步，别多做）

### 2.1 确认桥通

```powershell
python -c "import socket; s=socket.create_connection(('127.0.0.1',<BRIDGE_PORT>),3); print('bridge OK'); s.close()"
```

不通 → 汇报「桥不通」，**不要自己起桥**（主会话负责）。

### 2.2 唤醒串口 shell

```powershell
cd <程序根目录>
python monitor_tools\kzsh.py --port <BRIDGE_PORT> "@cr"
python monitor_tools\kzsh.py --port <BRIDGE_PORT> --wait 2 "echo alive"
```

回显 `alive` → 通路正常。

### 2.3 进 monitor 控制台

```powershell
python monitor_tools\kzsh.py --port <BRIDGE_PORT> --wait 3 "telnet 127.0.0.1 <CONSOLE_PORT>"
```

成功特征：
```
Trying 127.0.0.1...
Connected to localhost.localdomain.
Escape character is '^]'.
```

**从这里开始，`kzsh.py` 发的每一行都是 monitor 命令，不是 shell 命令。**

`Connection refused` → 应用没在跑/已崩。**不要反复重试 telnet**，直接看 `<DEPLOY_DIR>/<APP_NAME>.run.log` 尾部 30 行，汇报崩溃原因后停。

### 2.4 退出（收尾时）

```powershell
python monitor_tools\kzsh.py --port <BRIDGE_PORT> "exit"
```
不行就发 `@raw:\x1d`（Ctrl-]），再不行说明桥卡了，汇报即可。

**退出控制台后必须清理自己起的东西：**

1. 回报前先查有没有自己起来的常驻进程（本会话里你 `Start-Process`/`Start-Job`/后台起的任何中继、轮询、采集脚本）：
   ```powershell
   Get-CimInstance Win32_Process -Filter "Name='python.exe'" | Select-Object ProcessId,CommandLine
   Get-Job
   ```
2. 有就按 **PID 精确停**（禁止按名字杀）：
   ```powershell
   Stop-Process -Id <自己的_pid> -Force
   netstat -ano | Select-String ':<自己的端口>'    # 必须为空
   ```
3. **串口中继桥 `serial_bridge.py` 是主会话起的，不要动**（动了后面的人就连不上设备）。但若你发现它已死/端口不通，要在回报里写明。
4. 回报里加一行「已停止的脚本」：脚本名 + PID + 端口验证结果。**没有自己起过就写「无」**，不能省这一行。

---

## 3. 命令参考（控制台内）

| 命令 | 用法 | 说明 |
|---|---|---|
| `nodetreeinfo` | `nodetreeinfo [index]` | 打印节点树。不带参数列全部 root；多个 root 时用索引指定 |
| `props` | `props <nodePath> [nameFilter]` | 列节点属性，可带名字过滤（大小写不敏感子串匹配） |
| `getprop` | `getprop <nodePath> <PropertyTypeName>` | 读单个属性 |
| `setprop` | `setprop <nodePath> <PropertyTypeName> <value>` | 写属性并立即回读；**额外打印 `setprop-probe` 耗时行** |
| `trace` | `trace` | 立即采集一次样本并写 trace 文件到**进程当前工作目录** |
| `appfpsinfo` | `appfpsinfo` | 打印应用帧率/帧耗时信息 |
| `perfinfolevel` | `perfinfolevel [0\|1\|2]` | 读/写 PerformanceInfo 级别（不带参数 = 读） |
| `watch` | `watch [add\|list\|remove\|clear\|reset\|metrics]` | **阈值监视器**：每帧评估指标，越阈值自动执行一条控制台命令（详见 4.8） |
| `overwatch.perf` | `overwatch.perf` | 一次性返回性能快照 JSON（FPS / frameTime / 资源数 / CPU·GPU 内存 / 队列长度） |
| `overwatch.trace` | `overwatch.trace` | 采集+写盘，返回 `{"success":true,"file":"..."}` |
| `overwatch.fetchtrace` | `overwatch.fetchtrace` | 把**最近一次**写好的 trace 文件压成单行 JSON 打出来 |
| `appquit` | `appquit` | 优雅退出应用 |

> 不确定命令名时不要瞎猜，先看 `props` / `nodetreeinfo` 的报错提示；插件实际注册 **58 条**命令（28 基础 + 30 条 `overwatch.*`），本表只列常用 12 条。

---

## 4. 逐条命令详解与输出样例

### 4.1 `props`

```
props RootPage/Info
```
输出：
```
node RootPage/Info (EmptyNode2D)
Node2D.Width [Float] = 100
...
properties: 62
```
- 首行是 `node <你传的路径> (<元类名>)`，用来确认**路径解析成功**。
- 末行 `properties: N` 是命中条数。
- 带 filter：`props RootPage/Info text` → 只列名字含 `text` 的。
- **路径错** → `props: node not found: xxx`。
- **N=0 但你知道属性存在** → 见 §8.3（单继承链缺陷），直接改用 `getprop` 试。

### 4.2 `getprop`

```
getprop RootPage/Info sys.systemState
```
输出：`sys.systemState = 0`
错误：
- `getprop: node not found: xxx` → 路径错
- `getprop: property type not found: xxx (node type Yyy)` → 属性名错

### 4.3 `setprop`

```
setprop RootPage/Info sys.systemState 1
```
成功输出**固定两行**：
```
setprop: sys.systemState = 1
setprop-probe: seq=1 baseFrame=2986 resolve=12us apply=967us readback=5us total=984us frameMarkers=9
```
错误：
| 报错 | 原因 |
|---|---|
| `setprop: node not found: xxx` | 路径错（§8.1） |
| `setprop: property type not found: xxx (node type Yyy)` | 属性名错 / 不在该节点元类链上 |
| `setprop: X [Int] expects one integer value, e.g. 42` | 值格式错（§5） |
| `setprop: X [Color] expects #RRGGBB, ...` | 颜色格式错 |
| `setprop: X [Resource] has unsupported data type 'Resource'` | 该类型不支持写 |

### 4.4 `trace`

```
trace
```
立即采集 + 写盘。产出文件 `<DEPLOY_DIR>/<SessionLabel>_<时间戳>_<序号>.json`（Perfetto 格式）。
确认：`python monitor_tools\kzsh.py "ls -l <DEPLOY_DIR>/*.json"`。
**不要拉取文件内容**（铁律 1），只回报文件名 + 大小 + 时间。

### 4.5 `nodetreeinfo`

```
nodetreeinfo
```
输出节点树（含节点名与类型）。用来**先确认节点路径**再 `props`/`setprop`，比反复试路径省调用次数。

### 4.6 `appfpsinfo`

```
appfpsinfo
```
打印帧率/帧耗时统计。用于回答「现在跑多少帧、有没有掉帧」。

### 4.7 `perfinfolevel`

```
perfinfolevel        # 读当前级别
perfinfolevel 2      # 设为 2（更详细）
```
改完记得问用户要不要还原（不还原会影响后续帧耗时）。

### 4.8 `watch` — 阈值监视器（抓卡顿现场的入口）

```
watch metrics                          # 列全部指标 + 当前值
watch add <metric> <below|above> <阈值> <命令> [命令参数]
watch list                             # 看 id / active / triggered
watch reset <id>                       # 重新武装（触发后 active=false，一次性）
watch remove <id>
watch clear
```

**机制（源码核对，别记错）**：
- 每帧在 UserStage 评估一次（Recurring 任务），**不是**每秒轮询，也不是中断。
- 比较是**严格不等号**：`below` 用 `<`、`above` 用 `>`，**等于阈值不触发**。
- 触发后 `active=false` → **一次性**，再抓必须 `watch reset <id>`。
- 触发命令在**当帧 UI 线程同步执行**（所以「抓现场」和「判定」在同一帧）。

**14 个可用指标**：`fps` `appfps` `frametime` `animtime` `batches` `triangles` `texswitches` `fbswitches` `shaderswitches` `uniforms` `resources` `cpumem` `gpumem` `animations`

| 指标 | 取值来源 | 能不能抓"卡的那一帧" |
|---|---|---|
| `frametime` | `getLastFrameDuration()` **上一帧实测耗时 ms** | ✅ 逐帧比较，1 帧精度 |
| `fps` | `FrameTimeQueue::getFPS()` = **最近 min(64 帧, 1000 ms) 平均** | ❌ 平滑值，滞后最多约 1 秒 |
| 其余计数/内存类 | 每帧采样值 | 看趋势可以，抓单帧不行 |

### 4.9 `overwatch.perf` / `overwatch.trace` / `overwatch.fetchtrace`

```
overwatch.perf          # 快照：FPS / frameTime / 资源数 / CPU·GPU 内存 / 各队列长度
overwatch.trace         # collect+write，返回 {"success":true,"file":"tracing_output_..._0.json"}
overwatch.fetchtrace    # 把最近一次写好的 trace 文件整包压成单行 JSON 打出来
```

⚠️ **`trace` 抓的是"过去"**：内部只有 `collectSamples()`（把 profiler 环形缓冲里**已经录下**的样本搬进 storage）+ `writeSamples()`（写盘）。
所以「先看到卡了再敲 trace」往往已经晚了，必须让 `watch` 在触发帧内替你敲（见配方 E）。

回溯上限（源码常量，不是时间窗）：

| 类别 | 缓冲 | 影响 |
|---|---|---|
| `MainLoop`（帧标记 / task scope） | **10000 条 scope 样本** | 按**埋点条数**算，不是帧；每帧埋点几百条时只够约 1 秒 |
| `PerformanceInfo`（fps / frametime / 计数 / 内存） | **1024 样本/指标** | ≈ 17 秒 @60 FPS |
| `CollectWithAppendingEnabled` 默认 `0` | 每次 collect 前 `resetStorage()` | **不累积多段历史** |


---

## 5. 值格式表（按数据类型，**写错必报错**）

| 数据类型 | 格式 | 示例 |
|---|---|---|
| **Float** | 1 个数值 | `setprop RootPage/Text Opacity 0.5` |
| **Int** | 1 个整数 | `setprop RootPage/Text Width 300` |
| **Bool** | `true`/`false`/`1`/`0`/`on`/`off`/`yes`/`no` | `setprop RootPage/Info Visible false` |
| **String** | 其余全部内容整体作文本（**含空格**）；外层成对引号自动剥掉 | `setprop RootPage/Text Text hello world` 或 `Text "启动完成"` |
| **Color** | `#RRGGBB` / `#AARRGGBB`（按 sRGB→线性，与 Studio 一致）或 `r,g,b[,a]` 线性浮点 | `setprop RootPage/Bg ForegroundBrush.Color #FF9BA014` |
| **Vector2** | 2 个数值，逗号/分号/空格/括号任意分隔 | `setprop X LayoutWidth 100,200` |
| **Vector3** | 3 个数值 | `setprop X LayoutOffset 0,10,0` |
| **Vector4** | 4 个数值 | |
| **SRT2D** | 5 值：`scaleX,scaleY,rotationDeg,transX,transY` | `setprop X RenderTransformation 1,1,0,0,115` |
| **SRT3D** | 9 值：`scaleXYZ,rotXDeg,rotYDeg,rotZDeg,transXYZ` | `setprop X RenderTransformation 1,1,1,0,0,0,0,0,0` |
| **Matrix / Pointer / Resource / Range** | **不支持写** | 报 `has unsupported data type` |

---

## 6. 输出解析

### 6.1 `setprop-probe:` 行（同步段耗时）

```
setprop-probe: seq=1 baseFrame=2986 resolve=12us apply=967us readback=5us total=984us frameMarkers=9
```

| 字段 | 含义 | 典型值 |
|---|---|---|
| `seq` | 本次写入序号（从 1 递增，进程生命周期内） | 1,2,3… |
| `baseFrame` | 写入时的主循环帧号 | — |
| `resolve` | 找节点 + 找属性类型的耗时 | 5–15 us |
| `apply` | **类型转换 + 真正写入**的耗时（**同步段绝对大头，~98%**） | 800–1000 us |
| `readback` | 读回并格式化的耗时 | 2–8 us |
| `total` | 三段合计 | ≈ resolve+apply+readback |
| `frameMarkers` | 排进后续帧的标记数，正常 **9**（3 帧 × 3 阶段）；**0** = 上一个探针链还没跑完（连续两次 setprop 会这样） | 9 |

### 6.2 帧标记行（异步段，在 `run.log` 里）

```
info:generic> setprop probe: seq 1 frameBegin frame+1/3 (frame 2987) 15030 us after setprop
info:generic> setprop probe: seq 1 userStage  frame+1/3 (frame 2987) 16120 us after setprop
info:generic> setprop probe: seq 1 renderStage frame+1/3 (frame 2987) 18090 us after setprop
```

- 第 2 个字段就是**阶段名**：`frameBegin`（InputStage 末）/ `userStage`（UserStage 末）/ `renderStage`（RenderStage 末），可按名字直接筛选。
- `frame+X/3` = 第 X 个被观测帧；`(frame N)` = 实际帧号；末尾 `us after setprop` = **相对 setprop 写完的时刻**。
- 每帧 **3 条**，同一帧内顺序恒为 `frameBegin → userStage → renderStage`。
- ⚠️ **版本注意**：`libpluginmonitor.so` 早于 2026-11-17 12:02 的构建里，阶段名被日志格式化成指针地址（`4a707d85a8` 这类），只能靠顺序区分。原因为 `const char*` 变量在 Kanzi 日志里按指针格式化，现已改为 `kanzi::string_view`。看到 12 位十六进制就说明插件是旧版，**换插件**而不是猜阶段。
- **关键判读**：
  - 某帧第 3 条 = 该帧渲染提交完成 ≈ **上屏时刻** → 第一条帧标记帧的第 3 条就是「设置后多久能看到」。本工程实测 ≈ **18 ms**。
  - `frame+3/3` 第 3 条 = 三帧后完全稳定 ≈ **51–52 ms**。
  - 相邻两帧第 1 条之差 = 帧间隔（实测 ≈ 17 ms ≈ 59 FPS）。

取日志：
```powershell
python monitor_tools\kzsh.py --port <BRIDGE_PORT> --wait 3 "grep 'setprop probe' <DEPLOY_DIR>/<APP_NAME>.run.log | tail -20"
```

---

## 7. 测试配方（照抄，别自由发挥）

### 配方 A：启动 / 资源加载数据采集

> 前提：主会话已用带资源剖析标志的环境变量启动程序，且 `kanzimonitor.cfg` 配了 `WritingTimerOnceInterval`。

1. 确认程序在跑：
   ```powershell
   python monitor_tools\kzsh.py --port <BRIDGE_PORT> "pidin | grep -i <APP_NAME>"
   ```
2. 看启动日志是否健康：
   ```powershell
   python monitor_tools\kzsh.py --port <BRIDGE_PORT> --wait 3 "tail -40 <DEPLOY_DIR>/<APP_NAME>.run.log"
   ```
   要看到 `TraceService: set Profiling Category`，**不能**有 `SIGSEGV`/`core dumped`。
3. 等自动写盘（按 `WritingTimerOnceInterval` 时长等），或手动触发：
   ```powershell
   # 进控制台后
   trace
   ```
4. 确认产出：
   ```powershell
   python monitor_tools\kzsh.py --port <BRIDGE_PORT> "ls -l <DEPLOY_DIR>/*.json"
   ```
5. 回报：文件名 + 大小 + 时间 + 日志关键行。**不拉文件内容**。

### 配方 B：属性写入时延（setprop 埋点）

固定 8 步，顺序不能变：

```powershell
$P = <BRIDGE_PORT>
# 1 进控制台
python monitor_tools\kzsh.py --port $P --wait 3 "telnet 127.0.0.1 <CONSOLE_PORT>"
# 2 记初值
python monitor_tools\kzsh.py --port $P --wait 2 "getprop <NODE_PATH> <PROPERTY>"
# 3 写入目标值
python monitor_tools\kzsh.py --port $P --wait 2 "setprop <NODE_PATH> <PROPERTY> <TARGET_VALUE>"
# 4 等 3 秒（看帧标记落地）
python monitor_tools\kzsh.py --port $P --wait 3 "@cr"
# 5 读回确认 = 目标值
python monitor_tools\kzsh.py --port $P --wait 2 "getprop <NODE_PATH> <PROPERTY>"
# 6 写回初值
python monitor_tools\kzsh.py --port $P --wait 2 "setprop <NODE_PATH> <PROPERTY> <CURRENT_VALUE>"
# 7 读回确认 = 初值
python monitor_tools\kzsh.py --port $P --wait 2 "getprop <NODE_PATH> <PROPERTY>"
# 8 取帧标记日志
python monitor_tools\kzsh.py --port $P --wait 3 "grep 'setprop probe' <DEPLOY_DIR>/<APP_NAME>.run.log | tail -20"
```

输出必须包含：
- 两次 `setprop-probe:` 行（`frameMarkers` 应为 9）
- 两组共 18 条帧标记（每组 9 条）
- 读回值 2 次正确

⚠️ 第 4 步发裸 `@cr` 后，第 5 步可能报 `Command getprop not found` —— **重发一次**即可，这是控制台已知怪癖。

### 配方 C：任意属性读写验证

```powershell
python monitor_tools\kzsh.py --port <BRIDGE_PORT> --wait 3 "telnet 127.0.0.1 <CONSOLE_PORT>"
python monitor_tools\kzsh.py --port <BRIDGE_PORT> --wait 2 "props <NODE_PATH>"
python monitor_tools\kzsh.py --port <BRIDGE_PORT> --wait 2 "props <NODE_PATH> <关键词>"     # 找属性全名
python monitor_tools\kzsh.py --port <BRIDGE_PORT> --wait 2 "getprop <NODE_PATH> <PROPERTY>"  # 记初值
python monitor_tools\kzsh.py --port <BRIDGE_PORT> --wait 2 "setprop <NODE_PATH> <PROPERTY> <新值>"
python monitor_tools\kzsh.py --port <BRIDGE_PORT> --wait 2 "getprop <NODE_PATH> <PROPERTY>"  # 确认新值
python monitor_tools\kzsh.py --port <BRIDGE_PORT> --wait 2 "setprop <NODE_PATH> <PROPERTY> <初值>"  # 必须还原
python monitor_tools\kzsh.py --port <BRIDGE_PORT> --wait 2 "getprop <NODE_PATH> <PROPERTY>"  # 确认还原
```

### 配方 D：帧耗时 / 渲染统计

```powershell
python monitor_tools\kzsh.py --port <P> --wait 3 "telnet 127.0.0.1 <CONSOLE_PORT>"
python monitor_tools\kzsh.py --port <P> --wait 2 "perfinfolevel"      # 先看当前级别
python monitor_tools\kzsh.py --port <P> --wait 2 "appfpsinfo"         # 帧率/帧耗时
```
需要更详细信息时 `perfinfolevel 2`，采完**问用户是否还原**。

### 配方 E：抓「卡顿那一帧」的现场（已知某个操作会卡）★最常用

> 原理：`trace` 抓的是缓冲里的**过去**，人手敲一定晚。必须用 `watch` 在**触发那一帧内**替你敲。
> 必须用 `frametime`（上一帧实测耗时，1 帧精度），**不能用 `fps`**（最近 1 秒平均，滞后约 1 秒）。

```powershell
$P = <BRIDGE_PORT>
# 1 进控制台
python monitor_tools\kzsh.py --port $P --wait 3 "telnet 127.0.0.1 <CONSOLE_PORT>"
# 2 看指标当前值（记下 frametime 基线，用来定阈值：基线 × 2~3）
python monitor_tools\kzsh.py --port $P --wait 2 "watch metrics"
# 3 武装（阈值单位 ms，例：基线 17ms → 用 30 或 40）
python monitor_tools\kzsh.py --port $P --wait 2 "watch add frametime above <阈值> overwatch.trace"
# 4 确认装上且 active
python monitor_tools\kzsh.py --port $P --wait 2 "watch list"
# 5 ★回报主会话/用户：「监视器已武装，请现在执行会卡的操作」——子会话不要自己点 UI
# 6 操作完成后看是否触发
python monitor_tools\kzsh.py --port $P --wait 2 "watch list"
python monitor_tools\kzsh.py --port $P --wait 3 "grep 'Performance watcher' <DEPLOY_DIR>/<APP_NAME>.run.log | tail -5"
# 7 看产出的 trace 文件（只回报文件名+大小+时间，不拉内容）
python monitor_tools\kzsh.py --port $P --wait 3 "ls -l <DEPLOY_DIR>/*.json | tail -5"
# 8 若要再抓一次，重新武装（触发后 active=false）
python monitor_tools\kzsh.py --port $P --wait 2 "watch reset <id>"
```

**通过判据**：
- 日志出现 `Performance watcher #<id>: frametime above <阈值> (current: <实际ms>), executing: overwatch.trace`
- 同时刻多出一个 `<SessionLabel>_<时间戳>_<n>.json`，大小明显大于 0
- `watch list` 里该条 `active=false / triggered`

**必须回报的数据**：阈值、触发时的 `current` 值、trace 文件名 + 字节数、以及「武装→触发」之间用户做了什么操作。

### 配方 F：一分钟偶发一次、不知道何时（cfg 自动抓，不用守着）

> 依赖 `kanzimonitor.cfg`（插件 init **只读一次**，改完**必须重启应用**才生效）。
> **子会话只负责写 cfg + 验证读数，不自己重启应用** —— 重启由主会话用 `start_app.py` 做。

```powershell
# 1 主会话/用户先在本地准备好 cfg 文件（含下面三行），再用工具写入设备
python monitor_tools\dev_writecfg.py <本地cfg路径> <DEPLOY_DIR>/kanzimonitor.cfg <BRIDGE_PORT>
# 2 回读确认
python monitor_tools\kzsh.py --port <BRIDGE_PORT> "cat <DEPLOY_DIR>/kanzimonitor.cfg"
# 3 ★回报主会话「cfg 已就绪，需要重启应用生效」，等重启完成后再继续
# 4 重启后确认插件读到了配置
python monitor_tools\kzsh.py --port <BRIDGE_PORT> --wait 3 "grep 'Configuration loaded' <DEPLOY_DIR>/<APP_NAME>.run.log | tail -3"
# 5 让场景自然跑一段时间，然后看自动抓到的文件
python monitor_tools\kzsh.py --port <BRIDGE_PORT> --wait 3 "grep 'onFrameTask' <DEPLOY_DIR>/<APP_NAME>.run.log | tail -10"
python monitor_tools\kzsh.py --port <BRIDGE_PORT> --wait 3 "ls -l <DEPLOY_DIR>/*.json | tail -10"
```

cfg 三行：

```ini
WritingOnFrameDurationThreshold=50      ; 单帧 ≥50 ms 自动抓；0=关（默认）
CollectWithAppendingEnabled=1           ; 老样本搬进 storage，不 resetStorage
CollectingOnFullSampleBufferEnabled=1   ; 缓冲满先搬走再覆盖（需上一行=1 才注册）
```

**语义（源码确认）**：`onFrameTask` 每帧检查，超阈值就挂一个 **100 ms 延迟定时器**再 collect+write
→ 抓到的窗口 = **触发帧 + 之后约 100 ms**（能看到卡顿后遗症）。连续卡顿会连续触发、一次多出几个文件。
`CollectWithAppendingEnabled=1` 后才可能一个文件覆盖远超环形缓冲（`MainLoop` 10000 条 scope 样本）的历史。

### 配方 G：想让一段时间全程可回放（已知要做一分钟操作）

```ini
CollectingTimerRepeatInterval=1000      ; 每 1 s collect
WritingTimerRepeatInterval=5000         ; 每 5 s 写一个文件
```

同配方 F：写 cfg → 回报主会话重启 → 事后 `ls -l <DEPLOY_DIR>/*.json` 按时间挑文件。
⚠️ 持续写盘本身影响帧率，只能看"相对位置"，不能拿这批数字当性能基线。采完把这两行改回 `0` 并再重启一次。

### 配方 H：性能现状巡检（"现在多少帧 / 有没有漏资源"）

```powershell
python monitor_tools\kzsh.py --port <P> --wait 3 "telnet 127.0.0.1 <CONSOLE_PORT>"
python monitor_tools\kzsh.py --port <P> --wait 2 "overwatch.perf"        # 快照 JSON
python monitor_tools\kzsh.py --port <P> --wait 2 "watch metrics"         # 14 个指标当前值
python monitor_tools\kzsh.py --port <P> --wait 2 "appfpsinfo"
```

**读数规则**：
- **采 3 次、取稳态**，不要用一次瞬时值（首帧/刚启动的帧间隔会是 30 ms 级别的假象）。
- `appfps` 与 `fps` 不一致时，先看是否开了 `appfps` 对应的 Application（无 Application 时该键不存在）。
- 队列长度（Acquire/Deploy/Load）**长期非 0** 才是问题；采样瞬间非 0 正常。
- 采集前后 `perfinfolevel` 必须一致，否则帧耗时不可比。
- ⚠️ 开了 `idlesuspend` / SuspendWhenIdle 后没帧 → 帧率和 watcher 全都不动，先 `idlesuspend 0` 或让界面有动画。

---

## 8. 已知 quirks（踩过，别再踩）

### 8.1 节点路径

- `findNode()` 会剥前导 `/`，再依次试：各注册 root → Application Screen → **剥掉第一段**再试一次。
- **推荐写法**：相对 root 的路径，如 `RootPage/Info`。前导 `/` 可有可无。
- 带 `Screens/Screen/...` 前缀**不一定**能命中（只剥一段），**不要依赖**。
- 不确定就先 `nodetreeinfo` 或 `props RootPage/Info` 看首行是否有 `node ... (元类名)`。

### 8.2 动态属性看不见

`sys.*` 这类**动态属性不在 `props` 的静态属性列表里**，但 `getprop`/`setprop` 能直接读写。
→ **不要因为 props 列表里没有就判定属性不存在**，直接 `getprop` 试。

### 8.3 `props` 单继承链缺陷

`props` / 属性名解析只沿 `metaclass->getBase()` **单继承链**走，拿不到 `TextBlock2D` 之类**旁支概念类**的属性（表现为「带 filter 返回 `properties: 0`」）。
→ 遇到这种情况**不要反复换关键词**，直接用 `getprop <节点> <全限定属性名>` 试。

### 8.4 控制台输入

- 命令必须以 **LF（`\n`）** 结尾才执行；`kzsh.py` 默认就发 `\n`，正常。
- 发裸 `@cr` 之后**紧跟的第一条命令可能报 `Command xxx not found`** → 重发。
- 大输出（如全树 `nodetreeinfo`）可能把控制台冲乱 → 加 `| head -50` / `| tail -30` 截断。

### 8.5 其它

- `appquit` 有时会写 core 到 `/var/log/<APP_NAME>.core`，**进程正常退出**，不影响采集；汇报时提一句即可（`rm` 由主会话/用户决定）。
- `setprop-probe ... frameMarkers=0` = 上一个探针链未完成，**等 1 秒再写**，不是故障。
- trace 文件名里的时间戳可能无意义（设备 RTC 未对时）。

### 8.6 性能采集特有坑（配方 E/F/G/H 必看）

- **`fps` 不能用来抓单帧**。`fps` = `getFramesPerSecond()`，是 `FrameTimeQueue` 的**滑动窗口平均**（窗口 = `min(64 帧, 1000 ms)`，实测 `MeasurementWindowWidth=1000`），卡顿那一帧会被后面十几帧稀释，滞后最多约 1 秒。
  抓单帧**只能用 `frametime`**（=`getLastFrameDuration()`，单帧实测）。
- **`MainLoop` trace 缓冲按「scope 样本条数」算，不是按帧**：容量 10000 条。埋点密时（每帧几百条）只装得下约 **1 秒**；埋点稀时才够几十秒。
  → 想要更长回溯，只能提前开 `CollectingTimerRepeatInterval` / `WritingTimerRepeatInterval` 滚动写盘（配方 G），不要指望一次 trace 拿到很长的历史。
- **`PerformanceInfo` 缓冲每指标 1024 样本 ≈ 17 秒 @60FPS**（`PROFILING_PERFORMANCEINFO_DEFAULT_BUFFER_SIZE=1024`）。`perfinfolevel` 改过之后计数/内存等指标的样本序列会重置，**同一个对比实验必须全程同级别**。
- **`watch` 触发是一次性的**：触发后 `active=false`，如果当时没有命令再抓，之后就一直「没抓到」。抓完务必 `watch list` 确认状态，或直接 `watch clear` 后重新武装。
- **改了 `kanzimonitor.cfg` 不重启应用 = 没改**：插件 `init` 只读一次配置。写完 cfg 必须**回报主会话重启应用**，不要自己重启、也不要改完接着测。
- **`watch` 不评估 = 没有帧**：开了 `sys.idlesuspend` 或界面静止导致不渲染时，`EvaluatePerformanceWatchers` 不跑，阈值永远不命中。测之前先确认 `sys.idlesuspend` 状态，必要时先让界面动起来。
- **连续卡顿会连续写盘**：`onFrameTask` 每次超阈值都挂一个 100 ms 定时器，一次卡顿序列可能连写好几个 trace 文件、把设备磁盘写满。配方 F 抓够就立刻把 `WritingOnFrameDurationThreshold` 改回 `0`。
- **trace 抓的是「过去」**：`commandTrace` = `collectSamples()`（把 profiler 环形缓冲里已经录到的样本搬进 storage）+ `writeSamples()`（整包写盘）。默认 `CollectWithAppendingEnabled=0`，每次 collect 前会 `resetStorage()`，**不累积多段历史**。
- **`overwatch.fetchtrace` 只读最近一次写好的文件**（去换行拼成单行 JSON）。若同时存在多个 trace 文件，要 `cat` / `ls -l` 确认拿到的是哪一个。

---

## 9. 回报格式（必须按这个结构）

```
✅/❌ 成功/失败回报

1. 每条命令原文 + 原始输出（不要加工、不要省略错误信息）
   ----- CMD: xxx -----
   <原样输出>

2. 数据表
   | 项 | 值 |
   |---|---|
   | 属性初值 | ... |
   | setprop 后读回 | ... |
   | resolve/apply/readback/total | ... |
   | frameMarkers | ... |
   | 首帧渲染完成（上屏时延） | ... us / ms |
   | 三帧稳定 | ... |
   | 已还原 | 是/否 |

   **性能类任务（配方 E–H）额外必须回报：**
   | 项 | 值 |
   |---|---|
   | `perfinfolevel` 级别（全程是否一致） | ... |
   | `sys.idlesuspend` 状态 | ... |
   | 阈值设定（watch 表达式 / cfg 键值） | ... |
   | 触发时的 `current` 值（从 `Performance watcher #` 日志取） | ... |
   | trace 文件名 + 字节数 | ... |
   | 抓取期间用户做了什么操作（起止时刻/操作描述） | ... |
   | 是否已 `watch clear` / watcher 已失效 | 是/否 |
   | cfg 是否已还原（`WritingOnFrameDurationThreshold` 等改回 0） | 是/否 / 不涉及 |
   | 未取到数据的原因（若失败） | ... |

3. 结论（3–5 句，回答任务目标的问题）

4. 异常备注（崩溃/core/怪癖/没做到的部分）

5. 已停止的脚本（§2.4）：脚本名 + PID + 端口验证结果；没有自己起过就写「无」
```

**失败也必须按此格式回报**：说明卡在第几步、原始报错是什么、尝试过什么。不要只回一句「失败」。

---

## 10. 禁止项

1. 不传文件（scp/rz/sz/hex/awk/base64/nc/tftp）。
2. 不勘察设备网络（ping/route 到设备，或对设备做 netstat）。本机 `netstat` 仅允许用于 §2.4 验证自己端口是否释放。
3. 不重启设备、不重启测试程序、不重启桥、不杀进程。
4. 不删设备文件（含 trace json、core）。
5. 不 reset 会话。
6. 不猜环境变量；缺就问。
7. 测试写的属性必须还原。
8. **不留下自己起的脚本/后台进程** —— 任务结束前按 §2.4 全部停掉并验证（进程消失 + 端口释放）；串口桥是主会话的，别动也别留自己的。
9. **不自己重启应用** —— 改了 `kanzimonitor.cfg`（配方 F/G）后必须**回报主会话请求重启**，重启由主会话用 `start_app.py` 做；你自己 `appquit` 之后不要接着起应用。
10. **不留长期 watcher** —— 性能采集结束必须 `watch clear`（或确认所有 watcher 已失效），且把改过的 cfg 键（`WritingOnFrameDurationThreshold` / `CollectWithAppendingEnabled` / 定时器间隔）还原并回报。
