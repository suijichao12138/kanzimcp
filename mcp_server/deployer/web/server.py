#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""server.py — Web 服务（标准库 ThreadingHTTPServer，零第三方依赖）

路由分发 + Basic Auth + 静态文件。
"""
import json
import mimetypes
import socket
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse, parse_qs

from . import api, auth
from . import skills_api
from . import scan_api

# 运行期上下文（配置 / 路径 / 状态），由 deployer.py 注入
CTX = None


def _static_dir() -> Path:
    """静态资源目录。

    - PyInstaller onefile 解包目录: sys._MEIPASS/web/static
    - PyInstaller onedir / 源码运行: 本文件同级 static
    """
    if getattr(sys, "frozen", False):
        base = Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
        for cand in (base / "web" / "static", base / "static"):
            if cand.exists():
                return cand
    return Path(__file__).resolve().parent / "static"


_STATIC = _static_dir()


class _BodyTooLarge(Exception):
    """请求体超过配置上限。"""

    def __init__(self, max_mb: int):
        self.max_mb = max_mb
        super().__init__("请求体超过上限 %dMB" % max_mb)


class Handler(BaseHTTPRequestHandler):
    server_version = "kanzi-deployer"
    protocol_version = "HTTP/1.1"

    # ── 工具 ──
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

    def _send_file(self, path: str, filename: str):
        """流式下发文件（大文件下载用，避免整体读入内存）。"""
        p = Path(path)
        if not p.exists() or not p.is_file():
            return self._json(404, {"ok": False, "error": "文件不存在"})
        import urllib.parse
        disp = filename.replace('"', '').replace("\\", "_")
        disp_ascii = urllib.parse.quote(disp)
        ctype = mimetypes.guess_type(str(p))[0] or "application/octet-stream"
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(p.stat().st_size))
        self.send_header("Content-Disposition",
                         f"attachment; filename=\"{disp_ascii}\"; filename*=UTF-8''{disp_ascii}")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        try:
            with open(p, "rb") as f:
                while True:
                    chunk = f.read(1024 * 1024)      # 1MB 块
                    if not chunk:
                        break
                    self.wfile.write(chunk)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def _send_file_inline(self, path: str, ctype: str = "text/html; charset=utf-8"):
        """内联下发文件：浏览器直接渲染，而不是弹出下载框。

        与 _send_file 的唯一区别是 Content-Disposition 用 inline。
        用于静态检查报告——用户要求「直接打开 html 网页不需要下载」。

        CSP sandbox 是必需的：报告由用户上传的代码生成，
        不能让它拥有同源权限（否则报告里的脚本能读 /api/config 等接口）。
        加 allow-scripts 是因为报告本身依赖 JS 渲染表格。
        """
        p = Path(path)
        if not p.exists() or not p.is_file():
            return self._json(404, {"ok": False, "error": "报告不存在"})
        # 报告内嵌源码时可能几十 MB，不能整体 read_bytes 进内存
        # （并发几个人打开就会把 deployer 内存吃满）。分块流式下发。
        try:
            size = p.stat().st_size
        except OSError as e:
            return self._json(500, {"ok": False, "error": "读取报告失败: %s" % e})
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(size))
        self.send_header("Content-Disposition", "inline")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Content-Security-Policy",
                         "sandbox allow-scripts allow-popups")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        try:
            with open(p, "rb") as f:
                while True:
                    chunk = f.read(256 * 1024)
                    if not chunk:
                        break
                    self.wfile.write(chunk)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def _read_body(self, max_mb: int = 0) -> dict:
        """读取 JSON 请求体。

        max_mb=0 时用配置里的 web.max_body_mb（默认 8MB）。
        静态检查的代码上传走大值（base64 会膨胀约 33%，需要更大空间）。
        """
        try:
            n = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            n = 0
        if n <= 0:
            return {}
        if not max_mb:
            w = (CTX.cfg.get("web") or {})
            max_mb = int(w.get("max_body_mb") or 8)
        if n > max_mb * 1024 * 1024:
            # 超限不能静默返回 {}：前端会拿到「缺少文件内容」这类
            # 完全对不上原因的报错。这里明确回 413 并说明上限。
            self.rfile.read(n)                      # 读掉请求体，避免连接错乱
            raise _BodyTooLarge(max_mb)
        try:
            return json.loads(self.rfile.read(n).decode("utf-8") or "{}")
        except Exception:                           # noqa: BLE001
            return {}

    def _authed(self) -> bool:
        """是否通过认证。

        未启用认证 或 尚未设置密码 → 放行（靠启动横幅强力提醒去设密码）。
        否则校验 Basic Auth。
        """
        w = (CTX.cfg.get("web") or {}).get("auth") or {}
        if not w.get("enabled"):
            return True
        expected = w.get("password_sha256") or ""
        if not expected:               # 还没设密码 → 别把自己锁在外面
            return True
        return auth.verify(self.headers.get("Authorization", ""),
                           w.get("user", "admin"), expected)

    def _deny(self):
        self.send_response(401)
        self.send_header("WWW-Authenticate", 'Basic realm="kanzi-deployer"')
        self.send_header("Content-Length", "0")
        self.end_headers()

    def log_message(self, fmt, *args):
        pass        # 静音，避免刷屏（自己的日志走 logging）

    # ── 路由 ──
    def do_GET(self):
        u = urlparse(self.path)
        path, qs = u.path, parse_qs(u.query)

        if path in ("/", "/index.html"):
            return self._serve_static("index.html")

        # 静态资源（css/js）在登录页就要用，且不含敏感数据 → 放在认证之前
        if path.startswith("/static/"):
            return self._serve_static(path[len("/static/"):])

        if not self._authed():
            return self._deny()

        try:
            if path == "/api/status":
                code, body = api.status(CTX)
            elif path == "/api/check_update":
                code, body = api.check_update(CTX)
            elif path == "/api/task":
                code, body = api.task_get(CTX, (qs.get("id") or [""])[0])
            elif path == "/api/tasks":
                code, body = api.task_list(CTX)
            elif path == "/api/wizard":
                code, body = api.wizard_get(CTX)
            elif path == "/api/env":
                code, body = api.env_status(CTX)
            elif path == "/api/logs":
                name = (qs.get("name") or ["deployer"])[0]
                lines = int((qs.get("lines") or ["200"])[0] or 200)
                code, body = api.logs_get(CTX, name, lines)
            elif path == "/api/config":
                code, body = api.config_get(CTX, (qs.get("name") or [""])[0])
            elif path == "/api/skills":
                code, body = skills_api.skills_list(CTX)
            elif path == "/api/skills/download":
                name = (qs.get("name") or [""])[0]
                as_zip = (qs.get("zip") or [""])[0] in ("1", "true", "yes")
                code, body = skills_api.skills_download(CTX, name, as_zip)
            elif path == "/api/skills/download_all":
                code, body = skills_api.skills_download_all(CTX)
            elif path == "/api/skills/get":
                code, body = skills_api.skills_get(CTX, (qs.get("name") or [""])[0])
            elif path == "/api/artifacts":
                code, body = api.artifacts_list(CTX)
            elif path == "/api/artifact/download":
                # 文件流直下（不走 base64，避免大文件吃内存）
                code, body = api.artifact_download(CTX, (qs.get("name") or [""])[0])
                if code == 200 and body.get("ok") and body.get("data"):
                    return self._send_file(body["data"]["path"], body["data"]["filename"])
                return self._json(code, body)
            # ── 静态检查（代码检查页）──
            elif path == "/api/projects":
                code, body = scan_api.list_all(CTX)
            elif path == "/api/project/detail":
                code, body = scan_api.detail(CTX, (qs.get("id") or [""])[0])
            elif path == "/api/project/report":
                # 内联下发，浏览器直接渲染 HTML，不触发下载
                code, body = scan_api.report_path(
                    CTX, (qs.get("id") or [""])[0],
                    (qs.get("name") or ["report.html"])[0])
                if code == 200 and body.get("ok") and body.get("data"):
                    return self._send_file_inline(body["data"]["path"],
                                                  body["data"]["ctype"])
                return self._json(code, body)
            else:
                code, body = 404, {"ok": False, "error": "not found"}
        except Exception as e:                       # noqa: BLE001
            code, body = 500, {"ok": False, "error": f"服务内部错误: {e}"}
        return self._json(code, body)

    def do_POST(self):
        if not self._authed():
            return self._deny()
        path = urlparse(self.path).path
        # 代码上传走大 body（base64 膨胀约 33%），其余接口保持默认 8MB
        big = 200 if path == "/api/project/upload" else 0
        try:
            body = self._read_body(big)
        except _BodyTooLarge as e:
            return self._json(413, {"ok": False,
                                    "error": "%s，请压缩后重试" % str(e)})
        try:
            if path == "/api/upgrade":
                code, out = api.upgrade(CTX, body)
            elif path == "/api/deploy":
                code, out = api.deploy_now(CTX, body)
            elif path == "/api/restart":
                code, out = api.restart(CTX, body)
            elif path == "/api/config":
                code, out = api.config_put(CTX, urlparse(self.path).query
                                           and parse_qs(urlparse(self.path).query).get("name", [""])[0]
                                           or body.get("name", ""), body)
            elif path == "/api/skills/upload":
                code, out = skills_api.skills_upload(CTX, body)
            elif path == "/api/skills/delete":
                code, out = skills_api.skills_delete(CTX, (body or {}).get("name", ""))
            elif path == "/api/skills/edit":
                code, out = skills_api.skills_edit(CTX, (body or {}).get("name", ""), body)
            elif path == "/api/wizard":
                code, out = api.wizard_put(CTX, body)
            elif path == "/api/logs/clear":
                code, out = api.logs_clear(CTX, body.get("name", ""))
            elif path == "/api/artifact/build":
                code, out = api.artifact_build(CTX, body)
            elif path == "/api/test_notify":
                code, out = api.test_notify(CTX)
            elif path == "/api/restart_self":
                code, out = 200, {"ok": True, "data": {"detail": "正在重启，3 秒后刷新页面"}}
                threading.Timer(1.0, _restart_self).start()
            # ── 静态检查（代码检查页）──
            elif path == "/api/project/create":
                code, out = scan_api.create(CTX, body)
            elif path == "/api/project/upload":
                code, out = scan_api.upload(CTX, body)
            elif path == "/api/project/scan":
                code, out = scan_api.start_scan(CTX, body)
            elif path == "/api/project/deploy":
                code, out = scan_api.start_deploy(CTX, body)
            elif path == "/api/project/delete":
                code, out = scan_api.delete(CTX, (body or {}).get("id", ""))
            else:
                code, out = 404, {"ok": False, "error": "not found"}
        except Exception as e:                       # noqa: BLE001
            code, out = 500, {"ok": False, "error": f"服务内部错误: {e}"}
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


def _restart_self():
    """重启自身：起一个 detached 子进程延迟拉起，然后本进程退出。"""
    import os
    import subprocess
    import time
    exe = Path(sys.executable)
    if getattr(sys, "frozen", False):
        cmd = f'timeout /t 3 /nobreak >nul & start "" "{exe}"'
        subprocess.Popen(cmd, shell=True,
                         creationflags=subprocess.DETACHED_PROCESS
                         | subprocess.CREATE_NEW_PROCESS_GROUP)
    else:
        cmd = [sys.executable] + sys.argv
        subprocess.Popen(cmd, cwd=str(Path(__file__).resolve().parent.parent.parent))
    time.sleep(0.3)
    os._exit(0)


class Server:
    def __init__(self, ctx):
        global CTX
        CTX = ctx
        w = ctx.cfg.get("web") or {}
        self.host = w.get("bind", "0.0.0.0")
        self.port = int(w.get("port", 9100))
        self.httpd: ThreadingHTTPServer | None = None
        self._thread: threading.Thread | None = None

    def start(self):
        try:
            self.httpd = ThreadingHTTPServer((self.host, self.port), Handler)
        except OSError as e:
            return False, f"端口 {self.port} 绑定失败: {e}"
        self.httpd.daemon_threads = True
        self._thread = threading.Thread(target=self.httpd.serve_forever,
                                        kwargs={"poll_interval": 0.5},
                                        daemon=True, name="web")
        self._thread.start()
        return True, f"http://{self.host}:{self.port}"

    def stop(self):
        if self.httpd:
            self.httpd.shutdown()


def local_ips() -> list:
    """列出本机可用的局域网 IP（按可用性排序，第一个最可能是对的）。"""
    ips = []

    def _add(ip):
        if not ip or ip.startswith("127.") or ip.startswith("169.254."):
            return
        if ip not in ips:
            ips.append(ip)

    # ① 首选：UDP socket 探测默认出口网卡（不发包，只是让系统选出路由源地址）
    for probe in ("10.255.255.255", "8.8.8.8"):
        try:
            sk = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            try:
                sk.connect((probe, 53))
                _add(sk.getsockname()[0])
            finally:
                sk.close()
        except Exception:                            # noqa: BLE001
            pass

    # ② 补充：主机名解析出的地址
    try:
        hostname = socket.gethostname()
        for info in socket.getaddrinfo(hostname, None, socket.AF_INET):
            _add(info[4][0])
    except Exception:                                # noqa: BLE001
        pass

    # ③ 兜底：真实网卡枚举（不依赖 DNS/hosts）
    try:
        import socket as _s
        if hasattr(_s, "if_nameindex"):
            for _, name in _s.if_nameindex():
                try:
                    import fcntl
                    import struct
                    sk = _s.socket(_s.AF_INET, _s.SOCK_DGRAM)
                    try:
                        packed = fcntl.ioctl(sk.fileno(), 0x8915,   # SIOCGIFADDR
                                             struct.pack("256s", name[:15].encode()))
                        _add(_s.inet_ntoa(packed[20:24]))
                    finally:
                        sk.close()
                except Exception:                    # noqa: BLE001
                    continue
    except Exception:                                # noqa: BLE001
        pass

    return ips
