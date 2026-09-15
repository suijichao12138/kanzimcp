# 中继机 OTA 自动更新 —— 部署说明

## 一、它做什么

```
轮询远端 git tag（每 60 秒）
   ├─ 无新 tag → 睡觉
   └─ 有新 tag → ↓
① git fetch + checkout 新 tag 源码到本地
② 本地 PyInstaller 编译三个 exe       ── 编译失败 → 飞书通知"编译失败" → 中止（不动现有进程）
③ 停进程（feishu → http → relay）
④ 替换 exe（旧版自动备份到 _backup\）
⑤ 依次执行快捷方式启动（relay → http → feishu）
⑥ 健康检查（58080 端口 / 9001 端口 / feishu 进程）── 失败 → 回滚旧 exe + 重启 + 飞书通知
⑦ 成功 → 记录版本 + 飞书通知"✅ OTA 成功"
```

**关键约束已实现**：relay / http / feishu **作为一个更新单元**，任何一次更新都三个一起重启（relay 重启时另两个同步重启）。

---

## 二、目录结构（部署完成后）

```
D:\kanziOTA\                      ← OTA 程序目录
   ├─ ota_agent.py                ← 主程序
   ├─ ota_config.json             ← 配置（路径/参数都在这里改）
   ├─ ota_state.json              ← 自动生成，记录当前版本
   ├─ ota_agent.log               ← 运行日志
   └─ build_exe.bat               ← 打包脚本（被 agent 调用）

D:\kanziMCP_src\                  ← 源码目录（首次运行自动 git clone）
   └─ mcp_server\relay_nlp_http\...

D:\kanziMCP_relay\                ← exe 运行目录（你的固定位置）
   ├─ relay_multi.exe
   ├─ kz_mcp_http.exe
   ├─ feishu_bridge.exe
   ├─ relay.lnk                   ← 快捷方式（含启动参数）
   ├─ http.lnk
   ├─ feishu.lnk
   └─ _backup\                    ← 自动生成的旧版备份
```

---

## 三、一次性准备（只做一次）

### 1. 装 Python 依赖
```bat
python -m pip install pyinstaller websockets lark-oapi
```

### 2. 确认 git 能访问 GitHub
```bat
git ls-remote --tags git@github.com:suijichao12138/kanzimcp.git
```
> 内网不通 GitHub 的话，把 `ota_config.json` 里 `repo.url` 换成内网 Git 地址（Gitea/GitLab）。

### 3. 建三个快捷方式（**关键：参数写在快捷方式里**）

在 `D:\kanziMCP_relay\` 下新建三个 `.lnk`，指向同目录的 exe：

| 快捷方式 | 目标 | 起始位置 |
|---|---|---|
| `relay.lnk` | `D:\kanziMCP_relay\relay_multi.exe` | `D:\kanziMCP_relay` |
| `http.lnk` | `D:\kanziMCP_relay\kz_mcp_http.exe --config config.json` | `D:\kanziMCP_relay` |
| `feishu.lnk` | `D:\kanziMCP_relay\feishu_bridge.exe --config feishu_config.json` | `D:\kanziMCP_relay` |

> **在 exe 同目录新建 .lnk**，这样替换 exe 不用重建快捷方式。
> 如果 exe 需要额外参数，就加在快捷方式的"目标"里（exe 路径后面）。

### 4. 把配置文件（`config.json` / `users.json` / `feishu_config.json`）放进 `D:\kanziMCP_relay\`
> 这些是**数据文件不是 exe**，OTA **不会覆盖它们**（只替换 exe），所以你的配置不会被冲掉。

### 5. 改 `ota_config.json` 里的路径和飞书密钥

```json
"repo": { "local_dir": "D:\\kanziMCP_src" },
"build": { "components": [ { "target_dir": "D:\\kanziMCP_relay" } ] },
"launch": { "shortcuts": [ { "lnk": "D:\\kanziMCP_relay\\relay.lnk" } ] },
"feishu_notify": { "app_secret": "你的真实 secret" }
```

**⚠️ `feishu_notify.app_secret` 必须填真实的**（否则通知发不出来，只打日志）。
> 建议用一个专门发通知的 bot，别用三个业务 bot 的 secret。

---

## 四、启动 agent

**测试跑一轮（推荐先这样验证）：**
```bat
cd /d D:\kanziOTA
python ota_agent.py --once
```

**常驻运行（两种方式选一）：**

**方式 A：开机自启（推荐，简单）**
1. `Win+R` → 输入 `shell:startup` → 回车
2. 在打开的文件夹里新建快捷方式 → 指向：
   ```
   pythonw.exe D:\kanziOTA\ota_agent.py
   ```
   （用 `pythonw` 无窗口运行）

**方式 B：注册成 Windows 服务（更稳，关机也跑）**
```bat
nssm install kanziOTA "C:\Python\pythonw.exe" "D:\kanziOTA\ota_agent.py"
nssm set kanziOTA AppDirectory D:\kanziOTA
nssm start kanziOTA
```
> ⚠️ **服务方式下 `os.startfile(.lnk)` 可能无效**（服务在 Session 0，没有桌面会话）。
> 如果健康检查发现进程起不来，改用方式 A（用户登录态），或把 `start_shortcuts` 改成直接 `subprocess.Popen(exe, args)`。

---

## 五、发布新版本（我这边操作）

```bash
# 1. 改代码
# 2. 提交
git add -A && git commit -m "fix: xxx"
git push origin main

# 3. 打 tag 发布（★这一步才触发 OTA）
git tag v8
git push origin v8
```

**只有打 tag 才会触发更新** —— 你平时随便 commit 都不影响线上。

**回滚：** 打一个指向旧 commit 的 tag 即可（或 agent 自动回滚）。

---

## 六、常见问题

| 现象 | 原因 / 处理 |
|---|---|
| 日志显示"未取到远端 tag" | git 访问不了 GitHub；检查 SSH key 或换内网 git 地址 |
| 编译失败 | 看 `ota_agent.log` 里 build 输出尾部；多为缺依赖（`pip install websockets lark-oapi`） |
| 替换 exe 失败（文件占用） | 进程没杀干净；agent 会重试 3 次，仍失败则飞书通知 |
| 启动了但健康检查不过 | 看 .lnk 目标/参数对不对；`config.json` 是否在运行目录；端口是否被占 |
| 飞书没收到通知 | `feishu_notify.app_secret` 没填或填错；看日志里"飞书取 token 失败" |
| 想强制更新到最新 tag | `python ota_agent.py --force` |

---

## 七、安全提醒

- **`ota_config.json` 里有飞书 app_secret** → 该文件**不要提交到 git**（已在 `.gitignore` 排除）
- agent 只会 `git fetch/checkout` 到 tag，**不会 `git reset`/`clean` 你的工作区**（但 `checkout -f` 会覆盖被跟踪文件的本地修改，所以源码目录别放手工改动）
