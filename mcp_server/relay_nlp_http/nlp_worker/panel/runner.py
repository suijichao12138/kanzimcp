#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""runner.py — 启动 / 停止 / 查看 nlp_worker 进程

跨平台：Windows 用 tasklist/taskkill，POSIX 用 pgrep/kill。
关键：kill 后要轮询确认进程真的没了（taskkill 是异步的，
返回 0 不代表已退出 —— 这是 deployer 那边踩过的坑）。
"""
from __future__ import annotations

import os
import shutil
import signal
import subprocess
import sys
import time
from pathlib import Path

IS_WIN = sys.platform.startswith("win")
EXE_NAME = "nlp_worker.exe" if IS_WIN else "nlp_worker"


# ══════════════════ 找 exe ══════════════════

def find_worker_exe(base: Path) -> Path | None:
    """在面板旁边找 nlp_worker。支持几个常见摆放位置。"""
    base = Path(base)
    candidates = [
        base / EXE_NAME,
        base / "nlp_worker" / EXE_NAME,
        base / "dist" / EXE_NAME,
        base / "dist" / "nlp-worker-portable" / EXE_NAME,
        base.parent / EXE_NAME,
        base.parent / "nlp_worker" / EXE_NAME,
        base.parent / "nlp-worker-portable" / EXE_NAME,
    ]
    for c in candidates:
        if c.is_file():
            return c
    # 兜底：同名但带 .py（开发态直接跑源码）
    for d in (base, base.parent, base.parent / "nlp_worker"):
        py = d / "nlp_worker.py"
        if py.is_file():
            return py
    return None


def build_command(exe: Path, config_path: Path) -> list[str]:
    """拼启动命令。.py 用当前解释器跑。"""
    if exe.suffix.lower() == ".py":
        return [sys.executable, str(exe), "--config", str(config_path)]
    return [str(exe), "--config", str(config_path)]


# ══════════════════ 进程状态 ══════════════════

def is_running() -> bool:
    if IS_WIN:
        try:
            out = subprocess.run(
                ["tasklist", "/FI", f"IMAGENAME eq {EXE_NAME}", "/NH"],
                capture_output=True, text=True, timeout=10,
                creationflags=_no_window(),
            ).stdout
            return EXE_NAME.lower() in out.lower()
        except Exception:                                    # noqa: BLE001
            return False
    return _pgrep() is not None


def pid_list() -> list[int]:
    if IS_WIN:
        try:
            out = subprocess.run(
                ["tasklist", "/FI", f"IMAGENAME eq {EXE_NAME}", "/FO", "CSV", "/NH"],
                capture_output=True, text=True, timeout=10,
                creationflags=_no_window(),
            ).stdout
            pids = []
            for line in out.splitlines():
                parts = [x.strip('"') for x in line.split('","')]
                if len(parts) >= 2 and parts[1].isdigit():
                    pids.append(int(parts[1]))
            return pids
        except Exception:                                    # noqa: BLE001
            return []
    p = _pgrep()
    return [int(p)] if p else []


def _pgrep() -> str | None:
    try:
        out = subprocess.run(["pgrep", "-f", "nlp_worker"],
                             capture_output=True, text=True, timeout=5).stdout.strip()
        # 排除自己
        for line in out.splitlines():
            if line.strip().isdigit():
                return line.strip()
    except Exception:                                        # noqa: BLE001
        pass
    return None


def _no_window():
    if not IS_WIN:
        return 0
    return getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)


# ══════════════════ 启动 ══════════════════

def start(exe: Path, config_path: Path, log_path: Path | None = None):
    """后台启动 nlp_worker，返回 (成功, 说明)。

    输出重定向到日志文件；Windows 下用 DETACHED_PROCESS 让它独立于面板，
    这样关闭面板不会杀掉它。
    """
    exe = Path(exe)
    cmd = build_command(exe, Path(config_path))
    cwd = exe.parent if exe.suffix.lower() != ".py" else exe.parent

    stdout = open(log_path, "a", encoding="utf-8", errors="replace") if log_path else subprocess.DEVNULL
    stderr = subprocess.STDOUT if log_path else subprocess.DEVNULL

    kwargs: dict = {"cwd": str(cwd), "stdout": stdout, "stderr": stderr}
    if IS_WIN:
        kwargs["creationflags"] = (subprocess.CREATE_NEW_PROCESS_GROUP
                                   | getattr(subprocess, "DETACHED_PROCESS", 0))
        kwargs["close_fds"] = True
    else:
        kwargs["start_new_session"] = True

    try:
        proc = subprocess.Popen(cmd, **kwargs)
    except OSError as exc:
        if log_path:
            stdout.close()
        return False, f"启动失败：{exc}"

    # 给它一点时间，看是不是秒退
    time.sleep(2.0)
    if proc.poll() is not None:
        tail = ""
        if log_path and Path(log_path).exists():
            try:
                tail = Path(log_path).read_text(encoding="utf-8", errors="replace")[-1200:]
            except Exception:                                # noqa: BLE001
                pass
        return False, f"进程启动后立刻退出（退出码 {proc.returncode}）。\n日志尾部：\n{tail}"

    if not is_running():
        return False, "进程似乎没起来，请在日志里查看原因"
    return True, f"已启动（PID {proc.pid}）"


# ══════════════════ 停止 ══════════════════

def stop(wait_s: float = 15.0):
    """停止 nlp_worker。会轮询确认真的停了。返回 (成功, 说明)。"""
    pids = pid_list()
    if not pids:
        return True, "进程本来就没在运行"

    for pid in pids:
        _kill_one(pid)

    # ★ 轮询确认真的退出（taskkill 是异步的）
    deadline = time.time() + wait_s
    while time.time() < deadline:
        if not pid_list():
            return True, "已停止"
        time.sleep(0.3)

    # 还没死就强杀
    for pid in pid_list():
        _kill_one(pid, force=True)
    time.sleep(1.0)
    if pid_list():
        return False, f"未能停止（PID: {pid_list()}）—— 请用任务管理器手动结束"
    return True, "已强制停止"


def _kill_one(pid: int, force: bool = False) -> None:
    try:
        if IS_WIN:
            cmd = ["taskkill", "/PID", str(pid), "/T"]
            if force:
                cmd.append("/F")
            elif not _taskkill_graceful(pid):
                cmd.append("/F")
            subprocess.run(cmd, capture_output=True, timeout=15,
                           creationflags=_no_window())
        else:
            os.kill(pid, signal.SIGKILL if force else signal.SIGTERM)
    except Exception:                                        # noqa: BLE001
        pass


def _taskkill_graceful(pid: int) -> bool:
    """先试不带 /F（发 WM_CLOSE，让它有机会收尾）。"""
    try:
        r = subprocess.run(["taskkill", "/PID", str(pid), "/T"],
                           capture_output=True, text=True, timeout=10,
                           creationflags=_no_window())
        return r.returncode == 0
    except Exception:                                        # noqa: BLE001
        return False


# ══════════════════ 工具 ══════════════════

def tail_log(path: Path, lines: int = 200) -> str:
    p = Path(path)
    if not p.exists():
        return "（日志文件还不存在）"
    try:
        with p.open("r", encoding="utf-8", errors="replace") as f:
            data = f.readlines()
        return "".join(data[-lines:])
    except Exception as exc:                                 # noqa: BLE001
        return f"（读取日志失败：{exc}）"


def open_in_explorer(path: Path) -> None:
    """在文件管理器里打开目录。"""
    p = Path(path)
    target = p if p.is_dir() else p.parent
    try:
        if IS_WIN:
            os.startfile(str(target))                        # noqa: S606
        elif sys.platform == "darwin":
            subprocess.Popen(["open", str(target)])
        else:
            subprocess.Popen(["xdg-open", str(target)])
    except Exception:                                        # noqa: BLE001
        pass
