#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""health.py — 健康检查（端口探测 + 进程存在）"""
import socket
import sys
import subprocess

CREATE_NO_WINDOW = 0x08000000 if sys.platform == "win32" else 0


def port_open(host: str, port: int, timeout: float = 1.5) -> bool:
    """TCP 连通性探测（只连不发，用于非 WebSocket 的普通端口）。"""
    try:
        with socket.create_connection((host, int(port)), timeout=timeout):
            return True
    except (OSError, ValueError):
        return False


def ws_handshake(host: str, port: int, path: str = "/",
                 timeout: float = 2.0) -> tuple[bool, str]:
    """真 WebSocket 握手探测。

    为什么要发真握手：只连 TCP 不发数据就断开，会让 websockets 库在服务端
    记一条 `opening handshake failed` + 完整堆栈（EOFError: stream ends
    after 0 bytes）。那是探活自己制造的噪音，刷屏会掩盖真实故障。
    发一个合法的 HTTP Upgrade 请求，服务端能正常完成握手，日志干净。

    返回 (是否成功, 说明)。
    """
    import base64
    import os

    key = base64.b64encode(os.urandom(16)).decode()
    req = (
        f"GET {path or '/'} HTTP/1.1\r\n"
        f"Host: {host}:{int(port)}\r\n"
        f"Upgrade: websocket\r\n"
        f"Connection: Upgrade\r\n"
        f"Sec-WebSocket-Key: {key}\r\n"
        f"Sec-WebSocket-Version: 13\r\n"
        f"\r\n"
    ).encode()
    try:
        with socket.create_connection((host, int(port)), timeout=timeout) as sk:
            sk.sendall(req)
            sk.settimeout(timeout)
            data = sk.recv(1024)
    except (OSError, ValueError) as e:
        return False, f"{host}:{port} 握手失败: {e}"
    if not data:
        return False, f"{host}:{port} 无响应"
    head = data.split(b"\r\n", 1)[0].decode("latin-1", "replace")
    if "101" in head:
        return True, f"{host}:{port} 握手成功"
    return False, f"{host}:{port} 拒绝握手: {head.strip()[:80]}"


def ws_port_open(host: str, port: int, path: str = "/",
                 timeout: float = 2.0) -> tuple[bool, str]:
    """端口的 WebSocket 可用性（握手成功即视为健康）。

    失败时退化为纯 TCP 探测给出更准确的说明：
    - TCP 通但握手失败 → 服务在但没正常响应（可能还在起）
    - TCP 都不通       → 端口没监听
    """
    ok, detail = ws_handshake(host, port, path=path, timeout=timeout)
    if ok:
        return True, detail
    if not port_open(host, port, timeout=min(timeout, 1.5)):
        return False, f"{host}:{port} 不通"
    return False, detail


def process_running(exe_name: str) -> bool:
    """按 exe 名查进程是否存在。"""
    try:
        if sys.platform == "win32":
            p = subprocess.run(["tasklist", "/FI", f"IMAGENAME eq {exe_name}", "/NH"],
                               capture_output=True, text=True, timeout=10,
                               encoding="utf-8", errors="replace",
                               creationflags=CREATE_NO_WINDOW)
            return exe_name.lower() in (p.stdout or "").lower()
        p = subprocess.run(["pgrep", "-f", exe_name], capture_output=True,
                           text=True, timeout=10)
        return p.returncode == 0 and bool((p.stdout or "").strip())
    except Exception:                                        # noqa: BLE001
        return False


def check_one(check: dict) -> tuple[bool, str]:
    """按一条检查定义判定，返回 (是否健康, 说明)。

    type=port 时默认发真 WebSocket 握手（ws=True），避免纯 TCP 探活给 relay
    制造 `opening handshake failed` 噪音。传 ws=False 可退回纯 TCP 探测。
    """
    t = check.get("type")
    if t == "port":
        host = check.get("host", "127.0.0.1")
        port = int(check.get("port", 0))
        # 默认发真握手：relay/http 都是 WebSocket 服务，握手成功才算真的能用
        if check.get("ws", True):
            return ws_port_open(host, port, path=check.get("path", "/"),
                                timeout=float(check.get("timeout_s", 2.0)))
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
