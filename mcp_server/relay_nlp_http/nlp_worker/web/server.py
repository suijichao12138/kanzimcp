#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""server.py — nlp_worker 网页控制台（标准库 ThreadingHTTPServer，零第三方依赖）

架构与 deployer 相同：路由分发 + 静态文件 + 线程内嵌启动。
无鉴权（监听 IP 由 config web.listen_host 控制，默认仅本机）。

由 nlp_worker 注入运行期上下文（config / store / copilot / relay）后 start()。
"""

from __future__ import annotations

import json
import logging
import mimetypes
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from . import api

log = logging.getLogger("nlp-worker.web")

# 运行期上下文（config / store / copilot / relay），由 nlp_worker 注入
CTX = None


def _static_dir() -> Path:
    if getattr(sys, "frozen", False):
        base = Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
        for cand in (base / "web" / "static", base / "static"):
            if cand.exists():
                return cand
    return Path(__file__).resolve().parent / "static"


_STATIC = _static_dir()


class Handler(BaseHTTPRequestHandler):
    server_version = "nlp-worker-web"
    protocol_version = "HTTP/1.1"

    def _send(self, code: int, body: bytes, ctype: str = "application/json; charset=utf-8"):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        try:
            self.wfile.write(body)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def _json(self, code: int, obj: dict):
        self._send(code, json.dumps(obj, ensure_ascii=False).encode("utf-8"))

    def _read_body(self) -> dict:
        try:
            length = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            length = 0
        if length <= 0 or length > 16 * 1024 * 1024:
            return {}
        try:
            return json.loads(self.rfile.read(length).decode("utf-8"))
        except Exception:  # noqa: BLE001
            return {}

    def log_message(self, fmt, *args):
        pass  # 静音，避免刷屏

    # ── 路由 ──
    def do_GET(self):
        u = urlparse(self.path)
        path = u.path
        if path in ("/", "/index.html"):
            return self._serve_static("index.html")
        if path.startswith("/static/"):
            return self._serve_static(path[len("/static/"):])
        try:
            if path == "/api/status":
                code, body = api.status()
            elif path == "/api/logs":
                from urllib.parse import parse_qs as _parse_qs
                _qs = _parse_qs(u.query)
                _lines = _qs.get("lines", ["200"])[0]
                code, body = api.logs_list({"lines": _lines})
            elif path == "/api/sessions":
                code, body = api.sessions_list()
            elif path == "/api/config":
                code, body = api.config_groups_meta()
            elif path == "/api/config/env":
                code, body = api.env_list()
            elif path.startswith("/api/config/"):
                group = path[len("/api/config/"):]
                if group and group != "env":
                    code, body = api.config_get(group)
                else:
                    code, body = api.env_list()
            elif path == "/api/env":
                code, body = api.env_list()
            else:
                code, body = 404, {"ok": False, "error": "not found"}
        except Exception as exc:  # noqa: BLE001
            log.exception("web GET 处理失败: %s", exc)
            code, body = 500, {"ok": False, "error": f"服务内部错误: {exc}"}
        return self._json(code, body)

    def do_POST(self):
        path = urlparse(self.path).path
        body = self._read_body()
        try:
            if path == "/api/sessions/reset":
                code, out = api.session_reset(body)
            elif path == "/api/sessions/clear":
                code, out = api.sessions_clear()
            elif path == "/api/restart":
                code, out = api.restart()
            elif path == "/api/env":
                code, out = api.env_put(body)
            elif path == "/api/env/refresh":
                code, out = api.env_refresh_process()
            elif path.startswith("/api/config/"):
                group = path[len("/api/config/"):]
                if group and group != "env":
                    code, out = api.config_put(group, body)
                else:
                    code, out = 404, {"ok": False, "error": "not found"}
            else:
                code, out = 404, {"ok": False, "error": "not found"}
        except Exception as exc:  # noqa: BLE001
            log.exception("web POST 处理失败: %s", exc)
            code, out = 500, {"ok": False, "error": f"服务内部错误: {exc}"}
        return self._json(code, out)

    def do_DELETE(self):
        path = urlparse(self.path).path
        try:
            if path.startswith("/api/env/"):
                key = path[len("/api/env/"):]
                code, out = api.env_delete(key)
            else:
                code, out = 404, {"ok": False, "error": "not found"}
        except Exception as exc:  # noqa: BLE001
            log.exception("web DELETE 处理失败: %s", exc)
            code, out = 500, {"ok": False, "error": f"服务内部错误: {exc}"}
        return self._json(code, out)

    def _serve_static(self, rel: str):
        rel = rel.split("?")[0].lstrip("/")
        if ".." in rel or rel.startswith("/"):
            return self._send(400, b"bad path", "text/plain")
        p = _STATIC / rel
        if not p.exists() or not p.is_file():
            return self._send(404, b"not found", "text/plain")
        ctype = mimetypes.guess_type(str(p))[0] or "application/octet-stream"
        if ctype.startswith("text/") or ctype in ("application/javascript",):
            ctype += "; charset=utf-8"
        return self._send(200, p.read_bytes(), ctype)


class Server:
    """网页控制台服务：start() 内嵌启动，stop() 停止。"""

    def __init__(self, ctx):
        global CTX
        CTX = ctx
        api.CTX = ctx  # api 模块用自己模块级的 CTX
        web_cfg = getattr(ctx.config, "web", None)
        self.host = getattr(web_cfg, "listen_host", "127.0.0.1") if web_cfg else "127.0.0.1"
        self.port = int(getattr(web_cfg, "listen_port", 8400) if web_cfg else 8400)
        self.httpd: ThreadingHTTPServer | None = None
        self._thread: threading.Thread | None = None

    def start(self):
        if not _STATIC.exists():
            return False, f"static 目录不存在: {_STATIC}"
        try:
            self.httpd = ThreadingHTTPServer((self.host, self.port), Handler)
        except OSError as exc:
            return False, f"端口 {self.port} 绑定失败: {exc}"
        self.httpd.daemon_threads = True
        self._thread = threading.Thread(
            target=self.httpd.serve_forever,
            kwargs={"poll_interval": 0.5},
            daemon=True,
            name="nlp-worker-web",
        )
        self._thread.start()
        log.info("网页控制台已启动: http://%s:%d", self.host, self.port)
        return True, f"http://{self.host}:{self.port}"

    def stop(self):
        if self.httpd is not None:
            self.httpd.shutdown()
            self.httpd.server_close()
            self.httpd = None
        if self._thread is not None:
            self._thread.join(timeout=2)
            self._thread = None
        log.info("网页控制台已停止")
