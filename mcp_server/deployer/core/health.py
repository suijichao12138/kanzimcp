#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""health.py — 健康检查（端口探测 + 进程存在）"""
import socket
import sys
import subprocess


def port_open(host: str, port: int, timeout: float = 1.5) -> bool:
    """TCP 连通性探测。"""
    try:
        with socket.create_connection((host, int(port)), timeout=timeout):
            return True
    except (OSError, ValueError):
        return False


def process_running(exe_name: str) -> bool:
    """按 exe 名查进程是否存在。"""
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


def check_one(check: dict) -> tuple[bool, str]:
    """按一条检查定义判定，返回 (是否健康, 说明)。"""
    t = check.get("type")
    if t == "port":
        host = check.get("host", "127.0.0.1")
        port = int(check.get("port", 0))
        ok = port_open(host, port)
        return ok, f"{host}:{port} {'可连通' if ok else '不通'}"
    if t == "process":
        exe = check.get("process", "")
        ok = process_running(exe)
        return ok, f"{exe} {'在运行' if ok else '未运行'}"
    return False, f"未知检查类型: {t}"


def wait_healthy(checks: list, timeout_s: int = 30, interval_s: int = 2) -> dict:
    """轮询等待全部检查项通过。

    返回 {name: {"ok": bool, "detail": str}}，超时后返回最后一次结果。
    """
    import time
    deadline = time.time() + timeout_s
    last = {}
    while True:
        last = {}
        all_ok = True
        for c in checks:
            ok, detail = check_one(c)
            last[c.get("name", "?")] = {"ok": ok, "detail": detail}
            if not ok:
                all_ok = False
        if all_ok or time.time() >= deadline:
            return last
        time.sleep(interval_s)
