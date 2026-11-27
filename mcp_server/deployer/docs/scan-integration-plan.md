# 静态检查接入 deployer —— 实施方案（已确认）

**功能**：新建工程（填名）→ 上传代码 → 部署（编译 exe）→ 检查（可重新检查）→ 打开报告（网页内直看）→ 删除
**工具位置**：`mcp_server/cppCheck/`
**运行环境**：`D:\suijichao\kanzi\Kanzi_Mcp_deployer`（已部署，http://10.10.118.152:9100）
**状态**：方案已确认，**未修改任何代码**

---

## 一、已确认的决策

| 项 | 决定 |
| --- | --- |
| exe 打包 | **`--onefile` 单文件** |
| 检查前提 | **必须先部署**。未部署时「检查」按钮置灰，因为不保证部署环境能直接跑源码 |
| 工具实例 | **全局共享一个**，所有工程共用同一个 `cppCheck.exe` |
| 检查引擎 | **默认全跑**（cppcheck + flawfinder + lizard + clang-tidy + clang-format + 自定义规则） |
| 磁盘配额 | 不做限制 |
| 页面改动 | **新增独立页面**；除「部署」页可加一个部署按钮外，**其他页面一律不动** |

---

## 二、线上环境核对结果

我已抓取线上三个静态资源，与本地源码逐字节比对：

| 文件 | 线上 MD5 | 本地 MD5 | 结果 |
| --- | --- | --- | --- |
| `index.html` | 11fc579387 | 11fc579387 | **完全一致** |
| `app.js` | 1dd3b71743 | 1dd3b71743 | **完全一致** |
| `style.css` | cb55538486 | cb55538486 | **完全一致** |

**结论**：线上就是本地这版，可以安全地以本地源码为改动基准。

### 现有页面结构（改动边界）

```
导航栏：状态总览 │ 部署/升级 │ 配置 │ Skills │ 日志 │ 设置
                    ↑                    ↑
              只在这里加               完全不动
              一个按钮

新增：代码检查（新 tab，独立 page）
```

现有「部署/升级」页已有三张卡片：
1. 版本升级
2. 一键部署
3. 产物下载 ← **部署按钮加在这张卡片下面，新增第 4 张卡片**

现有「产物下载」卡片的按钮写法：
```html
<button class="btn" onclick="buildArtifact('nlp_worker')">📦 编译下载 NLP Worker</button>
```
新的部署按钮完全照这个写，走同一套 `buildArtifact` 机制。

---

## 三、功能模型

```
代码检查（新页面）
├─ [新建工程]  输入工程名
└─ 工程列表
    ├─ 工程 A   状态：未部署
    │   ├─ [上传代码]  zip → data/projects/<id>/src/
    │   ├─ [部署]      需先到"部署"页点部署，或本页直接触发
    │   └─ [删除]
    │
    ├─ 工程 B   状态：已部署，待检查
    │   ├─ [检查]      → 生成 report.html
    │   └─ [删除]
    │
    └─ 工程 C   状态：已完成
        ├─ [重新检查]  → 覆盖旧报告
        ├─ [打开报告]  → 新标签页直接看
        └─ [删除]
```

### 状态与按钮可用性

| 状态 | 上传 | 部署 | 检查 | 重新检查 | 打开报告 | 删除 |
| --- | --- | --- | --- | --- | --- | --- |
| 无代码 | ✓ | ✗ | ✗ | ✗ | ✗ | ✓ |
| 有代码·未部署 | ✓ | ✓ | **✗（置灰）** | ✗ | ✗ | ✓ |
| 已部署·未检查 | ✓ | ✓ | ✓ | ✗ | ✗ | ✓ |
| 检查中 | ✗ | ✗ | ✗ | ✗ | ✗ | ✓ |
| 已完成 | ✓ | ✓ | ✗ | ✓ | ✓ | ✓ |

**为什么未部署不能检查**：你明确要求"不能保证部署环境能直接跑工具"。所以检查一律走 `cppCheck.exe`，不提供源码模式兜底。界面上把「检查」置灰并提示"请先部署工具"。

---

## 四、目录布局

### 4.1 源码（SVN 新增目录）

```
kanzi_mcp/mcp_server/
└── cppCheck/                     ← 新增
    ├── codescan/                 检查工具源码（13 个模块）
    ├── config/
    │   ├── scan_config.json
    │   └── .clang-format
    ├── data/spec_coverage.json   224 条规范覆盖判定
    ├── build.cmd                 ★ 编译脚本（环境检查→下载工具→打包 onefile）
    ├── cppCheck.spec             PyInstaller 配置
    ├── scan.cmd                  本地命令行扫描（调试用）
    ├── setup_env.cmd             单独准备环境（build.cmd 会调用）
    └── README.md
```

### 4.2 运行期（deployer 安装目录）

```
Kanzi_Mcp_deployer/
├── data/
│   ├── projects/                ← 新增：各工程的代码和报告
│   │   └── <工程id>/
│   │       ├── meta.json        工程名/状态/时间/统计
│   │       ├── upload.zip
│   │       ├── src/             解压的源码
│   │       └── out/             report.html / coverage.html / summary.md
│   └── tools/
│       └── cppCheck.exe         ← 全局共享的检查工具（部署产物）
└── bin/                         现有组件 exe（不动）
```

**全局共享**：`cppCheck.exe` 只有一份，放在 `data/tools/`。所有工程检查时都用它，`--src` 指向各自目录。

---

## 五、部署按钮的接入方式

### 5.1 复用现有 artifacts 机制（0 行核心改动）

`core/builder.py:195` 的 `_build_script()` 已经能跑 `.cmd` 并实时回报进度，`web/api.py:652` 的 `artifact_build()` 会把它挂到任务系统。所以只在配置里加一项：

```json
// deployer_config.json → artifacts 里加
"cppcheck_tool": {
  "label": "静态检查工具",
  "build_type": "script",
  "cwd": "mcp_server/cppCheck",
  "script": "build.cmd",
  "output": "dist/cppCheck.exe",
  "timeout_s": 1800
}
```

### 5.2 build.cmd 的流程

```
[1/6] 检查 Python（3.8+ / 64 位 / pip）
[2/6] 下载/校验第三方工具（多镜像回退 + 缓存复用）
      · cppcheck 绿色版
      · flawfinder / lizard / clang-tidy / clang-format（pip）
[3/6] 逐个验证工具可运行（--version）
[4/6] PyInstaller --onefile 打包
      · 把 codescan/ + config/ + data/ + tools/ 全部打进去
[5/6] 验证产物（跑一次 --version）
[6/6] 复制到 data/tools/cppCheck.exe
```

**onefile 的关键处理**：
exe 运行时会把自身解压到 `%TEMP%\_MEIxxxx`。工具内部用 `sys._MEIPASS` 定位打包进去的 `tools/` 目录，需要改 `codescan/common.py` 的 `dirs()` 函数——加一段 frozen 判断。这是唯一需要为打包改的工具代码（约 8 行）。

---

## 六、改动清单（严格遵守"其他页面不动"）

### 6.1 deployer 侧

| 文件 | 改什么 | 行数 | 是否碰其他页面 |
| --- | --- | --- | --- |
| `core/paths.py` | 加 `self.projects`、`self.tools` | +3 | 否 |
| `web/server.py` | ① `_read_body` 上限可配 ② 新增 `_send_file_inline()` ③ 挂 9 条路由 | +30 | 否 |
| `web/scan_api.py` | **新增**：工程 CRUD / 上传 / 部署 / 检查 / 报告 / 删除 | ~340 | 否 |
| `static/index.html` | ① 导航加 1 个 tab ② 新增 1 个 `<section>` ③ **部署页加 1 张卡片** | +45 | 仅部署页 +1 卡片 |
| `static/app.js` | ① `goTab` 加 1 行 ② 新增 8 个函数 | +190 | 否 |
| `static/style.css` | **不改**（全部复用现有类名） | 0 | 否 |
| `deployer_config.json` | artifacts 加 1 项 | +7 | 否 |
| **老代码合计** | | **约 33 行** | |

> 说明：`index.html` 的改动严格限定在"新增"。唯一碰到现有内容的地方是"部署/升级"页——按你的要求在那里加一个部署按钮（新增一张卡片，不修改既有卡片）。

### 6.2 cppCheck 侧

| 文件 | 改动 |
| --- | --- |
| 整个目录 | 从 `code-scan-tool` 搬过来 |
| `codescan/common.py` | 加 `sys._MEIPASS` 判断（onefile 打包必需，+8 行） |
| `codescan/report.py` | **修问题 1**：`</script>` 截断（+1 行） |
| `codescan/report.py` | **修问题 2**：源码内嵌加阈值（+8 行） |
| `codescan/cli.py` | 加 `--embed-sources` 参数（+5 行） |
| `build.cmd` | **新增** |
| `cppCheck.spec` | **新增** |

---

## 七、接口设计

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET | `/api/projects` | 工程列表 |
| POST | `/api/project/create` | 新建 `{name}` |
| POST | `/api/project/upload` | 上传 `{id, data_b64}` |
| POST | `/api/project/deploy` | 部署工具 → task_id |
| POST | `/api/project/scan` | 检查 / 重新检查 → task_id |
| GET | `/api/project/detail` | 详情 `?id=` |
| GET | `/api/project/report` | **inline 返回 HTML** `?id=&name=` |
| POST | `/api/project/delete` | 删除 `{id}` |

进度统一走现有的 `GET /api/task?id=`，前端复用 `watchArtifactTask()` 的轮询写法。

### 报告 inline 下发（关键）

现有 `_send_file()` 固定 `Content-Disposition: attachment`，这就是会下载的原因。新增一个方法：

```python
def _send_file_inline(self, path, ctype="text/html; charset=utf-8"):
    p = Path(path)
    if not p.exists():
        return self._json(404, {"ok": False, "error": "报告不存在"})
    body = p.read_bytes()
    self.send_response(200)
    self.send_header("Content-Type", ctype)
    self.send_header("Content-Length", str(len(body)))
    self.send_header("Content-Disposition", "inline")        # 关键：浏览器直接渲染
    self.send_header("X-Content-Type-Options", "nosniff")
    self.send_header("Content-Security-Policy", "sandbox allow-scripts")
    self.send_header("Cache-Control", "no-store")
    self.end_headers()
    self.wfile.write(body)
```

`CSP: sandbox` 必须加——报告是用户上传的代码生成的 HTML，不能让它有同源权限（否则能读 `/api/config`）。

---

## 八、页面设计（新 tab）

### 8.1 布局

```
┌─ 代码规范检查 ───────────────────────── [＋新建工程] [刷新] ─┐
│ 工具状态：cppCheck.exe 已就绪 (v1.0.0) · 全局共享            │
├──────────────────────────────────────────────────────────────┤
│ 工程名        状态      问题数  代码   时间        操作        │
│ hmi-info-app  已完成     1190   12MB  11-27 11:20  [报告][重查][删除] │
│ 测试工程      未部署     -      5MB   11-27 11:10  [部署][删除]        │
│ 新工程        有代码     -      -     11-27 11:00  [部署][删除]        │
└──────────────────────────────────────────────────────────────┘
┌─ 任务进度（复用现有 task-card 结构）─────────────────────────┐
│ ████████████░░░░░░░░ 45%                                     │
│ [scan] 正在执行 clang-tidy 8/12 …                            │
│ ┌ 日志 ────────────────────────────────────┐                 │
│ └──────────────────────────────────────────┘                 │
└──────────────────────────────────────────────────────────────┘
```

### 8.2 新建工程弹窗

```
标题：新建工程
工程名  [___________________]   placeholder: 如 hmi-info-app
提示：创建后可上传代码、部署检查工具、执行检查。
[取消] [创建]
```

### 8.3 全部复用现有样式类

`.card` `.card-head` `.row` `.tbl` `.btn` `.btn-primary` `.btn-sm` `.btn-warn` `.muted` `.pill` `.pill-ok` `.pill-bad` `.bar` `.bar-fill` `.log` `.modal` `.toast`

**`style.css` 一行都不用改。**

---

## 九、检查流程

```python
def start_scan(ctx, proj_id):
    d = _proj_dir(ctx, proj_id)
    exe = ctx.paths.tools / "cppCheck.exe"
    if not exe.exists():
        return _err("检查工具未部署，请先在部署页部署")

    cmd = [str(exe), "scan",
           "--src",  str(d / "src"),
           "--out",  str(d / "out"),
           "--project-name", meta["name"],
           "--no-open",
           "--embed-sources", "auto"]

    def job(task):
        task.update("scan", "启动检查…", 5)
        proc = subprocess.Popen(cmd, stdout=PIPE, stderr=STDOUT,
                                text=True, encoding="utf-8", errors="replace")
        for line in proc.stdout:
            task.update("", line.rstrip())
        proc.wait()
        ok = (d / "out" / "report.html").exists()
        task.done(ok, "检查完成" if ok else f"失败({proc.returncode})")

    tasks.start("scan", f"检查: {meta['name']}", job)
```

---

## 十、工具自身要修的 2 个问题

| # | 问题 | 影响 | 修法 |
| --- | --- | --- | --- |
| **1** | `report.py` 用 `json.dumps` 把源码直接塞进 `<script>`，源码含 `</script>` 会截断 | **报告白屏**（已实测） | `json_text.replace("</", "<\\/")` |
| **2** | 报告内嵌全部源码全文 | 代码大时报告臃肿 | `--embed-sources auto`，超 30MB 不内嵌 |

第 3 项（onefile 必需）：

| # | 问题 | 修法 |
| --- | --- | --- |
| **3** | onefile 打包后工具找不到自带的 `tools/` 目录 | `common.py` 的 `dirs()` 加 `sys._MEIPASS` 判断（+8 行） |

---

## 十一、安全清单

| 项 | 措施 |
| --- | --- |
| 路径穿越 | 解压校验 `..` / 绝对路径 / 盘符，拒绝 |
| zip 炸弹 | 解压前累加 `file_size`，超 500MB 中止 |
| 只收源码 | 白名单 `.c/.cpp/.cc/.cxx/.h/.hpp/.hxx` |
| 报告 XSS | `CSP: sandbox allow-scripts` |
| 上传大小 | `_read_body` 上限按路径区分，扫描接口 200MB |
| 命令注入 | `subprocess` list 传参；工程名过滤 `/ \ : * ? " < > \|` |
| 工程名 | 仅允许中英文数字下划线连字符，长度 ≤ 50 |
| exe 执行 | 只执行 `data/tools/cppCheck.exe` 固定路径 |

---

## 十二、实施顺序

| 阶段 | 内容 | 验证 |
| --- | --- | --- |
| 1 | 建 `cppCheck/`，搬工具，改 3 处（onefile 适配 + 2 个修复） | 命令行跑通报告 |
| 2 | 写 `build.cmd` + `cppCheck.spec` | 手工编译出 exe 并验证 |
| 3 | `paths.py` + `server.py` 三处小改 | 启动服务不报错 |
| 4 | `scan_api.py` 全部接口 | curl 逐个打通 |
| 5 | 前端新 tab + 部署页新增卡片 | 浏览器点通全流程 |
| 6 | 打包 + 完整回归 | 部署页点按钮 → 新页面走完 |

---

## 十三、下一步

方案已按你的确认要点改好。**现在没有动任何代码。**

如果这个方案没问题，我就按第十二节的顺序开始实施，每完成一个阶段会向你报告：
- 改了哪个文件的哪几行
- 用 diff 说明具体变化
- 如何验证

需要我现在开始吗？
