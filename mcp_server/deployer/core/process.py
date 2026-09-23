#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""process.py — 三组件进程管理（启动 / 停止 / 重启 / 状态）

用 Popen 直接管进程（不再用 .lnk）：
- 能拿 PID
- 能优雅停（先 terminate 再 kill）
- 能按组件重启
"""
import os
import subprocess
import sys
import time
from pathlib import Path

# 已启动进程句柄: {name: Popen}
_PROCS: dict = {}

CREATE_NO_WINDOW = 0x08000000 if sys.platform == "win32" else 0
CREATE_NEW_PROCESS_GROUP = 0x00000200 if sys.platform == "win32" else 0


def build_args(args_template: list, paths, comp_name: str, component: dict) -> list:
    """把参数模板里的 {logs}/{conf}/{bin}/{data} 占位符展开成绝对路径。"""
    ctx = {
        "logs": str(paths.logs),
        "conf": str(paths.conf),
        "bin": str(paths.bin),
        "data": str(paths.data),
        "name": comp_name,
    }
    # 允许组件配置里直接写 args（覆盖模板）
    args = component.get("args") or args_template or []
    out = []
    for a in args:
        try:
            out.append(a.format(**ctx))
        except (KeyError, IndexError):
            out.append(a)
    return out


def start(name: str, exe: Path, args: list, cwd: Path) -> tuple[bool, str]:
    """启动一个组件。返回 (成功, 说明)。已在跑则不重复启动。"""
    if is_running(name):
        return True, f"{name} 已在运行 (pid={pid_of(name)})"
    exe = Path(exe)
    if not exe.exists():
        return False, f"可执行文件不存在: {exe}"
    cwd = Path(cwd) if cwd and Path(cwd).exists() else exe.parent
    try:
        proc = subprocess.Popen(
            [str(exe)] + [str(a) for a in args],
            cwd=str(cwd),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=CREATE_NO_WINDOW | CREATE_NEW_PROCESS_GROUP,
        )
        _PROCS[name] = proc
        return True, f"{name} 已启动 (pid={proc.pid})"
    except Exception as e:                                   # noqa: BLE001
        return False, f"{name} 启动失败: {e}"


def is_running(name: str, exe_name: str = "") -> bool:
    """进程是否在跑。优先用句柄判断，句柄丢失则按进程名查（用于跨重启检测）。"""
    proc = _PROCS.get(name)
    if proc is not None:
        if proc.poll() is None:
            return True
        _PROCS.pop(name, None)
    if exe_name:
        return process_exists(exe_name)
    return False


def pid_of(name: str) -> int | None:
    proc = _PROCS.get(name)
    if proc is None:
        return None
    return proc.pid if proc.poll() is None else None


def process_exists(exe_name: str) -> bool:
    """按 exe 名查系统进程（Windows tasklist / Linux pgrep）。"""
    try:
        if sys.platform == "win32":
            p = subprocess.run(["tasklist", "/FI", f"IMAGENAME eq {exe_name}", "/NH"],
                               capture_output=True, text=True, timeout=10,
                               encoding="utf-8", errors="replace")
            return exe_name.lower() in (p.stdout or "").lower()
        p = subprocess.run(["pgrep", "-f", exe_name], capture_output=True,
                           text=True, timeout=10)
        return p.returncode == 0 and bool((p.stdout or "").strip())
    except Exception:                                        # noqa: BLE001
        return False


def stop(name: str, exe_name: str = "", wait_ms: int = 2000) -> tuple[bool, str]:
    """停止组件：先 terminate（进程有机会清理），超时再 kill。"""
    proc = _PROCS.get(name)
    if proc is not None and proc.poll() is None:
        try:
            proc.terminate()
            try:
                proc.wait(timeout=wait_ms / 1000)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait(timeout=3)
        except Exception as e:                               # noqa: BLE001
            return False, f"{name} 停止失败: {e}"
        _PROCS.pop(name, None)
        return True, f"{name} 已停止"

    # 句柄丢失（例如 deployer 自己重启过），按进程名杀
    if exe_name and process_exists(exe_name):
        ok = _taskkill(exe_name)
        return ok, f"{name} 已按进程名停止" if ok else f"{name} 停止失败(taskkill)"
    return True, f"{name} 未在运行"


def _taskkill(exe_name: str) -> bool:
    try:
        if sys.platform == "win32":
            p = subprocess.run(["taskkill", "/F", "/IM", exe_name],
                               capture_output=True, text=True, timeout=15,
                               encoding="utf-8", errors="replace")
            return p.returncode == 0
        subprocess.run(["pkill", "-f", exe_name], timeout=15)
        return True
    except Exception:                                        # noqa: BLE001
        return False


def stop_all(order: list, components: dict, wait_ms: int = 2000) -> list:
    """按给定顺序停止全部组件（通常传 START_ORDER 的反序）。"""
    results = []
    for name in order:
        exe_name = components.get(name, {}).get("exe_name", "")
        ok, msg = stop(name, exe_name, wait_ms)
        results.append((name, ok, msg))
        time.sleep(wait_ms / 1000)
    return results


def start_all(order: list, components: dict, paths) -> list:
    """按给定顺序启动全部组件。"""
    results = []
    for name in order:
        comp = components.get(name, {})
        exe = paths.bin / comp.get("exe_name", f"{name}.exe")
        args = build_args(comp.get("args_template"), paths, name, comp)
        ok, msg = start(name, exe, args, paths.bin)
        results.append((name, ok, msg))
    return results
