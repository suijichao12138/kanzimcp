#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ota_agent.py — 中继机 OTA 自动更新代理

闭环（全自动）：
  1. 轮询远端最新 git tag（只认 tag，不认 commit → 提交≠发布）
  2. 发现新 tag → git fetch + checkout 源码到本地源码目录
  3. 本地 PyInstaller 编译三个 exe                    ── 编译失败 → 飞书通知 + 中止
  4. 停三个进程（feishu → http → relay，等文件解锁）
  5. 替换 exe（先备份旧版，失败可回滚）
  6. 依次执行三个快捷方式启动（relay → http → feishu）
  7. 健康检查（端口 58080 / 9001 + feishu 进程）      ── 启动失败 → 回滚 + 飞书通知
  8. 成功 → 记录版本 + 飞书通知

约束：relay 重启时 http + feishu 必须同步重启 → 三者作为同一个更新单元，不拆开。

用法：
  python ota_agent.py --once      # 只跑一轮（测试用）
  python ota_agent.py             # 常驻，按 poll.interval_s 轮询
  python ota_agent.py --force     # 忽略版本比对，强制走一轮更新
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
import urllib.request
from datetime import datetime
from pathlib import Path

BASE_DIR = (
    Path(sys.executable).resolve().parent
    if getattr(sys, "frozen", False)      # PyInstaller/onefile 打包后
    else Path(__file__).resolve().parent  # 直接跑 .py
)
CONFIG_PATH = BASE_DIR / "ota_config.json"
STATE_PATH = BASE_DIR / "ota_state.json"


# ────────────────────────── 日志 ──────────────────────────

def log(msg: str, level: str = "INFO"):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"{ts} [{level}] {msg}"
    print(line, flush=True)
    try:
        with open(BASE_DIR / "ota_agent.log", "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass


# ────────────────────────── 飞书通知 ──────────────────────────

def feishu_notify(cfg: dict, text: str) -> bool:
    """给老隋发飞书文本消息（三步：取 token → 发消息）。失败只记日志，不抛异常。"""
    if not cfg.get("enabled"):
        return False
    app_id = cfg.get("app_id", "")
    app_secret = cfg.get("app_secret", "")
    if not app_id or not app_secret or "PUT_YOUR_SECRET" in app_secret:
        log("飞书通知未配置（app_secret 为空或占位符），跳过", "WARN")
        return False
    try:
        req = urllib.request.Request(
            "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal",
            data=json.dumps({"app_id": app_id, "app_secret": app_secret}).encode(),
            headers={"Content-Type": "application/json; charset=utf-8"},
            method="POST",
        )
        try:
            resp = json.loads(urllib.request.urlopen(req, timeout=15).read().decode())
        except urllib.error.HTTPError as e:
            log(f"飞书取 token 失败 HTTP {e.code}: {e.read().decode('utf-8', 'replace')[:500]}", "WARN")
            return False
        if resp.get("code") != 0:
            log(f"飞书取 token 失败: {resp}", "WARN")
            return False
        token = resp["tenant_access_token"]

        body = {
            "receive_id": cfg["receive_id"],
            "msg_type": "text",
            "content": json.dumps({"text": text}, ensure_ascii=False),
        }
        url2 = (f"https://open.feishu.cn/open-apis/im/v1/messages"
                f"?receive_id_type={cfg.get('receive_id_type','open_id')}")
        req2 = urllib.request.Request(
            url2,
            data=json.dumps(body, ensure_ascii=False).encode(),
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json; charset=utf-8",
            },
            method="POST",
        )
        try:
            resp2 = json.loads(urllib.request.urlopen(req2, timeout=15).read().decode())
        except urllib.error.HTTPError as e:
            raw = e.read().decode("utf-8", "replace")
            log(f"飞书发消息失败 HTTP {e.code}: {raw[:800]}", "WARN")
            return False
        if resp2.get("code") != 0:
            log(f"飞书发消息失败: {resp2}", "WARN")
            return False
        log("飞书通知已发送")
        return True
    except Exception as e:
        log(f"飞书通知异常: {type(e).__name__}: {e}", "WARN")
        return False


# ────────────────────────── git ──────────────────────────

def run(cmd, cwd=None, timeout=600, env=None):
    """执行命令，返回 (returncode, stdout+stderr)"""
    try:
        p = subprocess.run(
            cmd, cwd=cwd, shell=isinstance(cmd, str),
            capture_output=True, text=True, timeout=timeout,
            encoding="utf-8", errors="replace", env=env,
        )
        return p.returncode, (p.stdout or "") + (p.stderr or "")
    except subprocess.TimeoutExpired:
        return -1, f"命令超时({timeout}s): {cmd}"
    except Exception as e:
        return -1, f"命令异常: {e}"


def git_env() -> dict:
    """git 用的环境：自动接受新主机指纹（避免 Host key verification failed）。"""
    env = dict(os.environ)
    env["GIT_SSH_COMMAND"] = (
        "ssh -o StrictHostKeyChecking=accept-new -o UserKnownHostsFile=NUL "
        "-o BatchMode=yes"
    )
    return env


def git_latest_tag(repo_url: str) -> str:
    """取远端最新 tag（按版本号排序）。失败返回空串。"""
    rc, out = run(
        f"git ls-remote --tags --sort=-v:refname {repo_url}",
        timeout=60, env=git_env(),
    )
    if rc != 0:
        log(f"取远端 tag 失败: {out.strip()[:200]}", "WARN")
        return ""
    for line in out.splitlines():
        ref = line.split("\t")[-1].strip()
        if ref.endswith("^{}"):        # 跳过 peeled 引用
            continue
        if ref.startswith("refs/tags/"):
            return ref[len("refs/tags/"):]
    return ""


def git_prepare(repo_cfg: dict) -> bool:
    """确保本地源码目录是仓库、并 checkout 到目标版本（tag 或 branch）。"""
    url = repo_cfg["url"]
    local = Path(repo_cfg["local_dir"])
    target = repo_cfg.get("target_ref") or repo_cfg.get("branch", "main")

    if not (local / ".git").exists():
        log(f"本地源码目录不存在或非 git 仓库，开始 clone → {local}")
        local.parent.mkdir(parents=True, exist_ok=True)
        rc, out = run(f'git clone {url} "{local}"', timeout=900, env=git_env())
        if rc != 0:
            log(f"clone 失败: {out.strip()[:300]}", "ERROR")
            return False
        log("clone 完成")

    rc, out = run("git fetch --all --tags --force", cwd=str(local), timeout=300, env=git_env())
    if rc != 0:
        log(f"git fetch 失败: {out.strip()[:300]}", "ERROR")
        return False

    rc, out = run(f"git checkout -f {target}", cwd=str(local), timeout=120, env=git_env())
    if rc != 0:
        log(f"checkout {target} 失败: {out.strip()[:300]}", "ERROR")
        return False

    rc, out = run("git rev-parse HEAD", cwd=str(local), env=git_env())
    head = out.strip().splitlines()[0] if rc == 0 else "?"
    log(f"源码已就绪: {target} @ {head[:10]}")
    return True


# ────────────────────────── 编译 ──────────────────────────

def build_all(cfg: dict, src_dir: Path) -> tuple:
    """
    在源码目录跑 build_exe.bat（PyInstaller 打包三个 exe）。
    返回 (成功?, 输出, {组件名: exe路径})
    """
    build_cfg = cfg["build"]
    bat = src_dir / build_cfg["build_bat"]
    if not bat.exists():
        return False, f"找不到打包脚本: {bat}", {}

    log(f"开始本地编译（{bat.name}）…")
    rc, out = run(f'"{bat}"', cwd=str(src_dir), timeout=1800)
    tail = "\n".join(out.strip().splitlines()[-25:])

    if rc != 0:
        log(f"编译失败（退出码 {rc}）", "ERROR")
        return False, tail, {}

    # 收集产物
    produced = {}
    dist_root = src_dir / build_cfg.get("output_dir", "dist")
    for comp in build_cfg["components"]:
        exe_src = dist_root / comp["exe_name"]
        if exe_src.exists():
            produced[comp["name"]] = exe_src
        else:
            # 兜底：PyInstaller 产物可能在 dist/<name>/ 下
            alt = dist_root / comp["name"] / comp["exe_name"]
            if alt.exists():
                produced[comp["name"]] = alt
            else:
                log(f"编译产物缺失: {comp['exe_name']}", "ERROR")
                return False, f"缺少产物 {comp['exe_name']}\n{tail}", {}

    log(f"编译成功，产物: {[p.name for p in produced.values()]}")
    return True, tail, produced


# ────────────────────────── 进程管理 ──────────────────────────

def kill_processes(cfg: dict):
    """按顺序杀掉三个进程（先 feishu → http → relay）。"""
    wait_ms = cfg["processes"].get("kill_wait_ms", 2000)
    for exe in cfg["processes"]["kill_order"]:
        rc, out = run(f'taskkill /F /IM {exe} /T', timeout=30)
        if rc == 0:
            log(f"已停止进程: {exe}")
        else:
            log(f"进程未运行或已在退出: {exe}")
    time.sleep(wait_ms / 1000.0)


def ensure_shortcut(item: dict, comp: dict = None) -> bool:
    """
    确保快捷方式存在：不存在则自动创建（指向 exe + 参数）。
    用 PowerShell 的 WScript.Shell 创建 .lnk（无需 pywin32 依赖）。
    """
    lnk = Path(item["lnk"])
    if lnk.exists():
        return True

    exe = item.get("exe")
    if not exe:
        log(f"快捷方式不存在且未配置 exe 路径，无法自动创建: {lnk}", "ERROR")
        return False

    lnk.parent.mkdir(parents=True, exist_ok=True)
    workdir = item.get("workdir") or str(Path(exe).parent)
    arguments = item.get("args", "") or ""
    icon = item.get("icon", "") or exe

    ps = (
        "$W = New-Object -ComObject WScript.Shell; "
        f"$S = $W.CreateShortcut('{lnk}'); "
        f"$S.TargetPath = '{exe}'; "
        f"$S.WorkingDirectory = '{workdir}'; "
        f"$S.Arguments = '{arguments}'; "
        f"$S.IconLocation = '{icon}'; "
        "$S.Save()"
    )
    rc, out = run(["powershell", "-NoProfile", "-NonInteractive", "-Command", ps], timeout=60)
    if rc != 0 or not lnk.exists():
        log(f"自动创建快捷方式失败 {lnk}: {out.strip()[:200]}", "ERROR")
        return False
    log(f"已自动创建快捷方式: {lnk}")
    return True


def start_shortcuts(cfg: dict) -> bool:
    """依次执行快捷方式启动（os.startfile 等价于双击 .lnk）；缺失则自动创建。"""
    ok = True
    for item in cfg["launch"]["shortcuts"]:
        if not ensure_shortcut(item):
            ok = False
            continue
        lnk = item["lnk"]
        try:
            os.startfile(lnk)          # noqa: 仅 Windows 可用
            log(f"已启动: {item['name']} ({lnk})")
        except Exception as e:
            log(f"启动失败 {item['name']}: {e}", "ERROR")
            ok = False
        w = item.get("wait_before_next", 0)
        if w:
            time.sleep(w)
    return ok


# ────────────────────────── 健康检查 ──────────────────────────

def port_open(host: str, port: int, timeout: float = 1.5) -> bool:
    import socket
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except Exception:
        return False


def process_running(exe_name: str) -> bool:
    rc, out = run(f'tasklist /FI "IMAGENAME eq {exe_name}" /NH', timeout=20)
    return rc == 0 and exe_name.lower() in out.lower()


def health_check(cfg: dict) -> tuple:
    """轮询健康检查，返回 (全部通过?, 失败详情)"""
    hc = cfg["health"]
    timeout_s = hc.get("timeout_s", 30)
    interval_s = hc.get("interval_s", 2)
    deadline = time.time() + timeout_s
    failed = {}

    while time.time() < deadline:
        failed = {}
        for chk in hc["checks"]:
            if chk["type"] == "port":
                if not port_open(chk["host"], chk["port"]):
                    failed[chk["name"]] = f"端口 {chk['port']} 未监听"
            elif chk["type"] == "process":
                if not process_running(chk["process"]):
                    failed[chk["name"]] = f"进程 {chk['process']} 不在"
        if not failed:
            log("健康检查通过")
            return True, {}
        time.sleep(interval_s)

    log(f"健康检查失败: {failed}", "ERROR")
    return False, failed


# ────────────────────────── 替换 exe ──────────────────────────

def deploy_exes(cfg: dict, produced: dict) -> tuple:
    """备份旧 exe → 替换新 exe。返回 (成功?, 备份信息)"""
    backup_dir = Path(cfg["rollback"]["backup_dir"])
    backup_dir.mkdir(parents=True, exist_ok=True)
    backups = {}

    for comp in cfg["build"]["components"]:
        name = comp["name"]
        if name not in produced:
            continue
        target = Path(comp["target_dir"]) / comp["exe_name"]
        target.parent.mkdir(parents=True, exist_ok=True)

        # 备份旧版
        if target.exists():
            bak = backup_dir / f"{comp['exe_name']}.bak"
            try:
                shutil.copy2(target, bak)
                backups[name] = bak
                log(f"已备份: {bak.name}")
            except Exception as e:
                log(f"备份失败 {target}: {e}", "WARN")

        # 替换（占位重试 3 次）
        for attempt in range(3):
            try:
                shutil.copy2(produced[name], target)
                log(f"已替换: {target}")
                break
            except Exception as e:
                if attempt == 2:
                    log(f"替换失败 {target}: {e}", "ERROR")
                    return False, backups
                time.sleep(1.5)
    return True, backups


def rollback(cfg: dict, backups: dict):
    """回滚：把备份的 exe 拷回原位。"""
    if not cfg["rollback"].get("enabled"):
        log("回滚未启用，跳过", "WARN")
        return
    log("开始回滚…")
    for comp in cfg["build"]["components"]:
        name = comp["name"]
        if name not in backups:
            continue
        target = Path(comp["target_dir"]) / comp["exe_name"]
        try:
            shutil.copy2(backups[name], target)
            log(f"已回滚: {target}")
        except Exception as e:
            log(f"回滚失败 {target}: {e}", "ERROR")


# ────────────────────────── 状态 ──────────────────────────

def load_state() -> dict:
    if STATE_PATH.exists():
        try:
            return json.loads(STATE_PATH.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


def save_state(state: dict):
    try:
        STATE_PATH.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception as e:
        log(f"保存状态失败: {e}", "WARN")


# ────────────────────────── 主流程 ──────────────────────────

def update_once(cfg: dict, tag: str) -> bool:
    """走一轮完整更新。返回是否成功。"""
    notify = cfg.get("feishu_notify", {})
    repo_cfg = dict(cfg["repo"])
    repo_cfg["target_ref"] = tag

    # 1. 拉源码
    if not git_prepare(repo_cfg):
        feishu_notify(notify, f"❌ OTA 失败（{tag}）\n原因：拉取源码失败\n机器：{os.environ.get('COMPUTERNAME','?')}")
        return False

    src_dir = Path(repo_cfg["local_dir"])

    # 2. 编译
    ok, out, produced = build_all(cfg, src_dir)
    if not ok:
        feishu_notify(notify, f"❌ OTA 失败（{tag}）\n原因：编译失败\n\n{out[-800:]}")
        return False
    log("编译阶段完成")

    # 3. 停进程（三个一起）
    kill_processes(cfg)

    # 4. 替换 exe
    ok, backups = deploy_exes(cfg, produced)
    if not ok:
        feishu_notify(notify, f"❌ OTA 失败（{tag}）\n原因：替换 exe 失败（文件可能被占用）")
        rollback(cfg, backups)
        kill_processes(cfg)
        start_shortcuts(cfg)
        return False

    # 5. 启动（relay → http → feishu）
    if not start_shortcuts(cfg):
        feishu_notify(notify, f"❌ OTA 失败（{tag}）\n原因：快捷方式启动失败（检查 .lnk 路径）")
        rollback(cfg, backups)
        kill_processes(cfg)
        start_shortcuts(cfg)
        return False

    # 6. 健康检查
    ok, failed = health_check(cfg)
    if not ok:
        detail = "\n".join(f"  · {k}: {v}" for k, v in failed.items())
        feishu_notify(notify, f"⚠️ OTA 启动异常（{tag}）\n健康检查未通过：\n{detail}\n已触发回滚")
        rollback(cfg, backups)
        kill_processes(cfg)
        start_shortcuts(cfg)
        return False

    # 7. 成功
    state = load_state()
    state["current_tag"] = tag
    state["updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    save_state(state)

    components = "、".join(c["name"] for c in cfg["build"]["components"])
    feishu_notify(
        notify,
        f"✅ OTA 成功（{tag}）\n"
        f"机器：{os.environ.get('COMPUTERNAME','?')}\n"
        f"组件：{components}\n"
        f"时间：{state['updated_at']}\n"
        f"请测试效果，有问题直接反馈。",
    )
    log(f"✅ 更新完成: {tag}")
    return True


def main():
    ap = argparse.ArgumentParser(description="中继机 OTA 自动更新代理")
    ap.add_argument("--once", action="store_true", help="只跑一轮后退出")
    ap.add_argument("--force", action="store_true", help="忽略版本比对，强制更新到最新 tag")
    ap.add_argument("--test-notify", action="store_true", help="只测飞书通知能否发通，然后退出")
    ap.add_argument("--config", default=str(CONFIG_PATH), help="配置文件路径")
    args = ap.parse_args()

    cfg = json.loads(Path(args.config).read_text(encoding="utf-8"))
    log("=" * 60)
    log("OTA Agent 启动")

    if args.test_notify:
        n = cfg.get("feishu_notify", {})
        log(f"测试飞书通知 → app_id={n.get('app_id')} receive_id={n.get('receive_id')} "
            f"type={n.get('receive_id_type')}")
        ok = feishu_notify(n, "🔔 OTA 通知测试：如果你收到这条消息，说明通知链路正常。")
        log("✅ 通知发送成功" if ok else "❌ 通知发送失败，请看上方 WARN 里的飞书原始返回")
        return

    while True:
        try:
            state = load_state()
            current = state.get("current_tag", "")

            if cfg["repo"].get("use_tag"):
                latest = git_latest_tag(cfg["repo"]["url"])
            else:
                latest = ""

            if not latest:
                log("未取到远端 tag，跳过本轮", "WARN")
            elif latest == current and not args.force:
                log(f"已是最新版本 {current}，等待 {cfg['poll']['interval_s']}s")
            else:
                log(f"发现新版本: {current or '(无)'} → {latest}，开始更新")
                update_once(cfg, latest)
        except Exception as e:
            log(f"本轮异常: {e}", "ERROR")

        if args.once:
            break
        time.sleep(cfg["poll"]["interval_s"])

    log("OTA Agent 退出")


if __name__ == "__main__":
    main()
