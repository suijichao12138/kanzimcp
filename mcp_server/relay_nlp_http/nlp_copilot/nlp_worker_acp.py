#!/usr/bin/env python3
"""
NLP Worker ACP — GitHub Copilot CLI 执行器 + Kanzi MCP 代理 (交互式常驻版)

把旧的 nlp_worker.py (claude --print, 每次起子进程) 升级为真正的交互式:
通过 ACP 协议 (Agent Client Protocol) 驱动 copilot --acp 常驻会话,
支持多轮上下文连续 + 会话持久化恢复 + copilot 直接调 Kanzi MCP。

角色: 占 relay_multi 通道的 **nlp_worker** 槽位, 只做聊天插件执行器。
copilot 调 Kanzi 的 MCP 强制走 **kz_mcp_http.py**(client 槽), 不内置。
安全: 通道(用户)由 kz_mcp_http.py 的 --relay 决定, 其他人无法通过
本进程随意切换用户/通道。

会话持久化:
  ACP 会话的 sessionId 会保存到当前目录的 会话配置文件 (如 .nlp_session.suijichao.json),
  下次启动自动恢复上下文。

用法 (先起 kz_mcp_http.py 占同一通道的 client 槽):
    # 终端1: kz_mcp_http.py 控制通道, 默认 http://127.0.0.1:9001/mcp
    python kz_mcp_http.py --relay ws://127.0.0.1:58080/suijichao --listen 127.0.0.1:9001
    # 终端2: nlp_worker_acp.py 聊天执行器, --relay 必须与 kz_mcp_http.py 同通道
    python nlp_worker_acp.py --relay ws://10.10.118.152:58080/suijichao

依赖:
    pip install websockets
"""
import argparse
import asyncio
import json
import logging
import os
import re
import subprocess
import sys
import time
import urllib.request
import urllib.parse
import mimetypes

try:
    import websockets
except ImportError:
    websockets = None

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger("nlp-worker-acp")

# 协议版本: copilot CLI 的 ACP 实现期望整数且 <=65535, 实测为 1
ACP_PROTOCOL_VERSION = 1



# ═══════════════════════════════════════════════════════════════════
#  Relay 客户端 (复用 nlp_worker.py 逻辑)
# ═══════════════════════════════════════════════════════════════════
class RelayClient:
    """管理到中继的 WebSocket 连接, 角色 = nlp_worker"""

    def __init__(self, relay_url: str):
        self.relay_url = relay_url
        self.ws = None
        self.running = False
        self.on_message = None  # 回调: func(raw_msg_str)

    async def start(self):
        self.running = True
        await self._connect_loop()

    async def _connect_loop(self):
        while self.running:
            try:
                async with websockets.connect(
                    self.relay_url,
                    ping_interval=30,
                    ping_timeout=10,
                    close_timeout=5,
                ) as ws:
                    self.ws = ws
                    await ws.send(json.dumps({
                        "role": "nlp_worker",
                        "name": self.relay_url.rsplit("/", 1)[-1]
                    }))
                    log.info(f"✅ 已连接中继(nlp_worker): {self.relay_url}")

                    async for raw in ws:
                        if self.on_message:
                            await self.on_message(raw)

                    # ★ async for 正常结束后到这里(relay 关闭/连接结束): 打日志便于定位
                    log.warning("🔌 中继连接被关闭(async for 结束), 3秒后重连...")

            except websockets.ConnectionClosed as e:
                log.warning(
                    f"🔌 中继连接断开({type(e).__name__}, "
                    f"code={getattr(e, 'code', '?')}, reason={getattr(e, 'reason', '?')!r}), 3秒后重连...")
            except Exception as e:
                log.error(f"❌ 连接错误: {e}")

            if self.running:
                await asyncio.sleep(3)

    async def send(self, msg: dict):
        if self.ws:
            try:
                await self.ws.send(json.dumps(msg, ensure_ascii=False))
            except Exception as e:
                log.warning(f"发送失败: {e}")

    async def stop(self):
        self.running = False
        if self.ws:
            try:
                await self.ws.close()
            except Exception:
                pass


class McpProxyHandler:
    """
    MCP 请求代理: 把本地收到的 MCP JSON-RPC 通过 relay 转发到 Kanzi server。
    relay_multi 中 nlp_worker 角色位收到 {"type":"mcp_request","text":...} 会转发到 server;
    server 的 MCP 响应由 relay 包装成 {"type":"mcp_response","text":...} 回给 nlp_worker。
    """

    def __init__(self, relay: RelayClient, channel: str):
        self.relay = relay
        self.channel = channel
        self.pending = {}  # jsonrpc id(str) -> (asyncio.Future, timeout)
        self._lock = asyncio.Lock()

    async def relay_request(self, req: dict, timeout=60.0) -> dict:
        """向 Kanzi server 发送 MCP JSON-RPC 请求并等待响应"""
        req_id = str(req.get("id"))
        fut = asyncio.get_event_loop().create_future()
        async with self._lock:
            self.pending[req_id] = fut

        try:
            await self.relay.send({
                "type": "mcp_request",
                "text": json.dumps(req, ensure_ascii=False)
            })
            try:
                return await asyncio.wait_for(fut, timeout=timeout)
            except asyncio.TimeoutError:
                return {"jsonrpc": "2.0", "id": req_id,
                        "error": {"code": -32000, "message": "MCP 请求超时"}}
        finally:
            async with self._lock:
                self.pending.pop(req_id, None)

    async def handle_mcp_response(self, raw: str):
        """处理从中继收到的 MCP 响应 (relay 会包装成 {"type":"mcp_response","text":...})"""
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            return

        if data.get("type") != "mcp_response":
            return

        try:
            response = json.loads(data.get("text", "{}"))
        except json.JSONDecodeError:
            return

        req_id = str(response.get("id"))
        async with self._lock:
            fut = self.pending.get(req_id)
            if fut and not fut.done():
                fut.set_result(response)


# ═══════════════════════════════════════════════════════════════════
#  HTTP MCP Server (streamable HTTP) — 暴露给 copilot 连接
# ═══════════════════════════════════════════════════════════════════
class HttpMcpServer:
    """
    用 asyncio 起一个 HTTP server (仅一个并发 copilot 连接, 语义上够用)。
    处理: initialize / notifications/initialized / tools/list / tools/call / session 校验。
    MCP 请求经 McpProxyHandler 转发到 relay → Kanzi server。
    """

    def __init__(self, mcp_handler: McpProxyHandler, host="127.0.0.1", port=9001):
        self.handler = mcp_handler
        self.host = host
        self.port = port
        self.server = None

    async def start(self):
        self.server = await asyncio.start_server(self._handle_conn, self.host, self.port)
        log.info(f"🌐 HTTP MCP Server 已启动: http://{self.host}:{self.port}/mcp")
        return self.server

    async def _handle_conn(self, reader, writer):
        try:
            # 读 HTTP 请求头
            request_line = await reader.readline()
            log.debug("[http] request_line=%r", request_line)
            if not request_line:
                writer.close()
                return
            method_path = request_line.decode("utf-8", "replace").strip().split(" ")
            if len(method_path) < 2:
                writer.close()
                return
            method = method_path[0]
            path = method_path[1]

            headers = {}
            while True:
                line = await reader.readline()
                if line in (b"\r\n", b"\n", b""):
                    break
                text = line.decode("utf-8", "replace").strip()
                if ":" in text:
                    k, v = text.split(":", 1)
                    headers[k.strip().lower()] = v.strip()

            # 只处理 /mcp 路径
            if path.rstrip("/") != "/mcp" and path.rstrip("/") != "/":
                await self._send_http(writer, 404, "text/plain", "Not Found")
                return

            content_length = int(headers.get("content-length", "0"))
            body = b""
            if content_length > 0:
                body = await reader.readexactly(content_length)

            # 判定内容类型 & 处理
            content_type = headers.get("content-type", "")

            # GET + Accept: text/event-stream → SSE 初始化 (streamable HTTP)
            if method == "GET":
                await self._send_http(writer, 200, "application/json",
                                      self._init_sse_payload(), is_sse=False)
                return

            # POST 请求体是 JSON-RPC
            try:
                req = json.loads(body.decode("utf-8"))
            except Exception:
                await self._send_http(writer, 400, "application/json",
                                      json.dumps({"jsonrpc": "2.0", "error": {"code": -32700,
                                                                              "message": "Parse error"}, "id": None}))
                return

            resp = await self._handle_jsonrpc(req)

            # 若要 SSE 响应 (streaming), 走 text/event-stream; 否则普通 json
            accept_sse = "text/event-stream" in headers.get("accept", "")
            if accept_sse and resp:
                await self._send_http(writer, 200, "text/event-stream",
                                      f"data: {json.dumps(resp, ensure_ascii=False)}\n\n",
                                      is_sse=True)
            else:
                await self._send_http(writer, 200, "application/json",
                                      json.dumps(resp, ensure_ascii=False) if resp else "")

        except Exception as e:
            log.error(f"HTTP 处理异常: {e}")
            try:
                await self._send_http(writer, 500, "application/json",
                                      json.dumps({"jsonrpc": "2.0", "error": {"code": -32603,
                                                                              "message": str(e)}, "id": None}))
            except Exception:
                pass
        finally:
            try:
                writer.close()
            except Exception:
                pass

    async def _handle_jsonrpc(self, req: dict) -> dict:
        if not isinstance(req, dict):
            return {"jsonrpc": "2.0", "error": {"code": -32600, "message": "Invalid Request"}, "id": None}
        method = req.get("method", "")
        req_id = req.get("id")

        if method == "initialize":
            return {
                "jsonrpc": "2.0", "id": req_id,
                "result": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {"tools": {"listChanged": False}},
                    "serverInfo": {"name": "kanzi-studio-mcp-http", "version": "1.0.0"}
                }
            }
        if method == "notifications/initialized":
            return None
        if method == "ping":
            return {"jsonrpc": "2.0", "id": req_id, "result": {}}
        if method == "tools/list":
            return {
                "jsonrpc": "2.0", "id": req_id,
                "result": {"tools": [
                    {
                        "name": "kz_invoke",
                        "description": "在 Kanzi Studio API 对象上通过反射调用任意方法。target: @studio/@project/@projectItem/@obj1/@objN(引用)/节点路径",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "target": {"type": "string"},
                                "method": {"type": "string"},
                                "args": {"type": "array", "items": {}}
                            },
                            "required": ["target", "method"]
                        }
                    },
                    {
                        "name": "kz_ref_properties",
                        "description": "获取指定引用的可用属性(含类型和当前值)",
                        "inputSchema": {
                            "type": "object",
                            "properties": {"ref_id": {"type": "string"}},
                            "required": ["ref_id"]
                        }
                    },
                    {
                        "name": "kz_create_node",
                        "description": "在 Kanzi 工程创建 UI 节点",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "parent": {"type": "string"},
                                "type": {"type": "string"},
                                "name": {"type": "string"}
                            },
                            "required": ["parent", "type", "name"]
                        }
                    },
                    {
                        "name": "kz_set_property",
                        "description": "设置节点属性值",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "node_path": {"type": "string"},
                                "property": {"type": "string"},
                                "value": {"type": "string"}
                            },
                            "required": ["node_path", "property", "value"]
                        }
                    },
                    {
                        "name": "kz_get_node_tree",
                        "description": "获取工程节点树",
                        "inputSchema": {"type": "object",
                                        "properties": {"root": {"type": "string"}}}
                    },
                    {
                        "name": "kz_save_project",
                        "description": "保存当前 Kanzi 工程",
                        "inputSchema": {"type": "object", "properties": {}}
                    },
                ]}
            }
        if method == "tools/call":
            params = req.get("params", {})
            tool_name = params.get("name", "")
            arguments = params.get("arguments", {})
            # 构造 MCP JSON-RPC 转发到 Kanzi server
            forward_req = {
                "jsonrpc": "2.0",
                "id": req_id,
                "method": "tools/call",
                "params": {"name": tool_name, "arguments": arguments}
            }
            resp = await self.handler.relay_request(forward_req)
            # 兼容 Kanzi server 的返回 (可能 result 已经带 content, 或者直接是原始响应)
            return resp

        return {"jsonrpc": "2.0", "id": req_id, "result": {}}

    async def _send_http(self, writer, status, ctype, body: str, is_sse=False):
        reason = {200: "OK", 400: "Bad Request", 404: "Not Found", 500: "Internal Server Error"}.get(status, "")
        header = (f"HTTP/1.1 {status} {reason}\r\n"
                  f"Content-Type: {ctype}\r\n"
                  f"Content-Length: {len(body.encode('utf-8'))}\r\n"
                  f"Connection: close\r\n"
                  f"Access-Control-Allow-Origin: *\r\n"
                  f"Access-Control-Allow-Headers: Content-Type, Accept\r\n"
                  f"Access-Control-Allow-Methods: GET, POST, OPTIONS\r\n"
                  f"\r\n")
        try:
            writer.write(header.encode("utf-8"))
            if body:
                writer.write(body.encode("utf-8"))
            await writer.drain()
            # 不等待 wait_closed (可能因 peer 未关闭而阻塞), 响应已写出
            writer.close()
        except Exception:
            pass

    def _init_sse_payload(self):
        # streamable HTTP 的 GET 初始化返回, 这里是占位 json
        payload = {
            "jsonrpc": "2.0",
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}},
                "serverInfo": {
                    "name": "kanzi-studio-mcp-http",
                    "version": "1.0.0"
                }
            }
        }
        return json.dumps(payload)


# ═══════════════════════════════════════════════════════════════════
#  ACP 客户端 — 驱动 copilot --acp 常驻交互会话
# ═══════════════════════════════════════════════════════════════════
class AcpClient:
    """通过 stdio 连接 copilot --acp (ACP server), 提供常驻多轮交互 + 会话持久化"""

    def __init__(self, copilot_cmd="copilot", cwd=None, session_file=None, model=None,
                 mcp_config=None):
        self.copilot_cmd = copilot_cmd
        self.cwd = cwd or os.getcwd()
        self.session_file = session_file
        self.model = model
        self.mcp_config = mcp_config or []   # [{name,type,url,headers}] 经 --additional-mcp-config 挂载
        self.proc = None
        self._id = 0
        self.pending = {}
        self.session_id = None
        self._pump_task = None
        self.sess_update_queue = []   # 累积的 agent_message_chunk 文本 (当前轮)
        self._turn_done = asyncio.Event()
        self._died = asyncio.Event()  # copilot 进程死亡信号(EOF)
        self.stderr_error = None      # (时间戳, 文本) 最近的错误 stderr
        self._stderr_error_evt = asyncio.Event()  # stderr 出现错误时置位(唤醒 prompt)
        self._last_activity = time.time()  # 最近一次 copilot 消息时间(供活动刷新超时)

    # ---- 进程 & 消息 ----
    def start_process(self):
        # MCP 不在命令行挂载: 已验证 copilot 1.0.77 的 --acp ACP 模式会**忽略**
        # --additional-mcp-config(即使传了, copilot 仍报『没有配置任何 MCP 服务』)。
        # 正确做法: 在 session/new、session/resume 请求的 mcpServers 字段显式传 MCP 配置
        # (见 create_or_resume_session -> _mcp_servers_param)。
        cmd = [self.copilot_cmd, "--acp", "--allow-all", "--no-color", "-C", self.cwd]
        log.info(f"▶ 启动 copilot: {' '.join(cmd)}")
        self.proc = subprocess.Popen(
            cmd,
            cwd=self.cwd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1,
            shell=(sys.platform == "win32"),
        )

    def _next_id(self):
        self._id += 1
        return str(self._id)

    def _write(self, obj):
        """向 copilot stdin 写一行 JSON-RPC。
        ★ 同步阻塞隐患: copilot 若忙于初始化 MCP/不读 stdin, 这里 write+flush 可能
        阻塞整个 asyncio 事件循环(进而无法响应 relay 的 ping→被踢)。
        因此改为在**专用线程**里执行写, 绝不让事件循环卡在 flush 上。"""
        def _do():
            try:
                self.proc.stdin.write(json.dumps(obj, ensure_ascii=False) + "\n")
                self.proc.stdin.flush()
            except Exception as e:
                log.error(f"写入 copilot 失败: {e}")
        try:
            import threading
            threading.Thread(target=_do, daemon=True).start()
        except Exception as e:
            log.error(f"写入 copilot 异常: {e}")

    async def _read_line(self):
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.proc.stdout.readline)

    async def _read_stderr(self):
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.proc.stderr.readline)

    async def request(self, method, params, timeout=60, idle_extend=False, max_idle=300):
        rid = self._next_id()
        fut = asyncio.get_event_loop().create_future()
        self.pending[rid] = fut
        self._write({"jsonrpc": "2.0", "id": rid, "method": method, "params": params})
        if not idle_extend:
            try:
                return await asyncio.wait_for(fut, timeout=timeout)
            except asyncio.TimeoutError:
                self.pending.pop(rid, None)
                return {"error": {"code": -32000, "message": f"ACP {method} 超时"}}
        # ★ 活动刷新式超时: 只要 copilot 还在持续输出/调 MCP(_last_activity 在更新)
        #   就不断续期, 只有真正"死寂"(超过 max_idle 秒无任何活动)才报超时。
        #   解决长任务(如创建状态机)因固定 timeout 被误判超时、以及 copilot 还在
        #   后台干活但 worker 已放弃等待导致的重复操作隐患。
        while True:
            try:
                return await asyncio.wait_for(asyncio.shield(fut), timeout=max_idle)
            except asyncio.TimeoutError:
                # 这期间是否有活动? 有则继续等; 无则真死寂
                if time.time() - self._last_activity >= max_idle:
                    self.pending.pop(rid, None)
                    return {"error": {"code": -32000,
                                      "message": f"ACP {method} 超时(长时间无活动)"}}

    def notify(self, method, params):
        self._write({"jsonrpc": "2.0", "method": method, "params": params})

    # ---- ACP 会话生命周期 ----
    async def initialize(self, timeout=180):
        # timeout 默认 180s: copilot 冷启动可能很慢, 不能超时即退
        res = await self.request("initialize", {
            "protocolVersion": ACP_PROTOCOL_VERSION,
            "clientCapabilities": {
                "fs": {"readTextFile": True, "writeTextFile": True},
                "terminal": True,
                "positionEncodings": ["utf-32"],
            },
            "clientInfo": {"name": "nlp-worker-acp", "version": "1.0.0"},
        }, timeout=timeout)
        if "error" in res:
            raise RuntimeError(f"initialize 失败: {json.dumps(res['error'], ensure_ascii=False)}")
        self.notify("notifications/initialized", {})
        info = res.get("agentInfo", {})
        log.info(f"✔ Copilot 已握手: {info.get('name')} {info.get('version')}")
        return res

    def _mcp_servers_param(self):
        """生成 ACP 会话请求(session/new、session/resume)的 mcpServers 参数。
        已验证: copilot 1.0.77 在 --acp 模式下**忽略** --additional-mcp-config 命令行参数,
        只认会话请求里的 mcpServers 字段(否则报『没有配置任何 MCP 服务』)。

        字段格式据 copilot 1.0.77 的 session/new 校验错误确认(zod schema):
          - type: 必须 "http" | "sse"
          - headers: 必须是**数组**(每项 {name, value}), 不能是对象
          - command/args/env: 标准字段需存在(stdio 用), HTTP 型留空
        之前 headers 传对象导致 "expected array, received object"。"""
        servers = []
        for m in self.mcp_config:
            headers = m.get("headers", {})
            headers_arr = []
            if isinstance(headers, dict):
                # 对象 {k: v} → [{name: k, value: v}, ...]
                for k, v in headers.items():
                    headers_arr.append({"name": k, "value": v})
            elif isinstance(headers, list):
                headers_arr = headers
            servers.append({
                "type": "http",
                "name": m.get("name", m.get("url", "mcp")),
                "url": m.get("url", ""),
                "headers": headers_arr,
                "command": "",
                "args": [],
                "env": [],
            })
        return servers

    async def create_or_resume_session(self, mcp_servers=None, force_new=True):
        # ★ 已禁用会话持久化恢复: 老隋确认 copilot 恢复旧会话总失败/失效,
        #   且恢复时 MCP 挂载不完整(缺 api)。因此永远直接新建会话(session/new),
        #   保证每次启动 copilot 都全新加载全部 MCP, 最干净可靠。
        # 旧的恢复分支已移除; force_new 参数仅保留签名兼容(始终为 True 行为)。
        res = await self.request("session/new", {
            "cwd": self.cwd,
            "mcpServers": self._mcp_servers_param(),
        }, timeout=60)
        if "error" in res:
            raise RuntimeError(f"session/new 失败: {json.dumps(res['error'], ensure_ascii=False)}")
        self.session_id = res.get("sessionId")
        log.info(f"✔ 新会话已创建: {self.session_id}")
        return self.session_id

    def _save_session(self):
        # ★ 已禁用会话持久化恢复: 不再写会话文件, 保证每次全新启动
        #   (若保留会触发 _load 恢复, 干扰 MCP 完整挂载/旧会话失效)。
        return

    # ---- 交互 ----
    async def prompt(self, text, timeout=300, _retry=True) -> str:
        """发送用户消息到 copilot 会话, 返回最终文本结果 (交互式, 上下文连续)。
        若 copilot 立即返回错误(如预算不足/参数错)会实时反馈; 超时则给明确提示。
        会话失效(not found)时自动新建会话重试一次(跨进程恢复的会话常已失效)。"""
        self.sess_update_queue = []
        self._turn_done = asyncio.Event()
        self._stderr_error_evt.clear()  # 清空旧错误标记, 只关注本轮新错误

        # 发送指令, 检查请求级错误(如预算不足会在此返回)
        # ★ idle_extend=True: 活动刷新式超时。只要 copilot 还在持续输出/调 MCP 就
        #   不超时(刷新 _last_activity), 只有长时间无活动才报超时。
        #   timeout 参数保留为"若从未有过任何活动"的兜底上限(不强制)。
        resp = await self.request("session/prompt", {
            "sessionId": self.session_id,
            "prompt": [{"type": "text", "text": text}],
        }, timeout=timeout, idle_extend=True)
        if isinstance(resp, dict) and resp.get("error"):
            msg = resp["error"]
            err_txt = msg.get("message", str(msg))
            err_low = err_txt.lower()
            # 会话失效: 自动新建会话重试一次, 避免用户看到无意义错误
            if _retry and ("not found" in err_low or "session" in err_low and "unknown" in err_low):
                log.warning(f"⚠ 会话 {self.session_id} 失效, 自动新建会话重试")
                try:
                    # force_new=True: 跳过文件里可能同样失效的旧 sessionId
                    await self.create_or_resume_session(force_new=True)
                except Exception as e:
                    log.error(f"自动新建会话失败: {e}")
                return await self.prompt(text, timeout=timeout, _retry=False)
            log.error(f"❌ session/prompt 返回错误: {err_txt}")
            return f"[copilot 错误] {err_txt}"

        # ★ 修复结束信号: copilot 1.0.77 不用 params.isResult 标记回合结束,
        # 而是用 session/prompt 请求的响应 result.stopReason 表示 (如 "end_turn").
        # 因为 await request 会阻塞到该响应到达才返回, 此时回合已真正结束,
        # chunk 也已收完, 直接收敛结果即可, 无需再等 _turn_done。
        stop_reason = None
        timed_out = False
        stderr_fired = False
        if isinstance(resp, dict):
            _r = resp.get("result") if "result" in resp else resp
            if isinstance(_r, dict):
                stop_reason = _r.get("stopReason")
        if stop_reason:
            log.info(f"✔ copilot 回合结束 (stopReason={stop_reason})")
        else:
            # 没有 stopReason (兼容旧版/其他 agent): 才进入等 _turn_done 的回退逻辑
            # 等待 copilot 结果(isResult)或 stderr 报错(如预算不足), 任一先到
            # 用 create_task (ensure_future 传入协程时结合 asyncio.wait 有调度问题, 事件 set 后不被唤醒)
            t_turn = asyncio.create_task(self._turn_done.wait())
            t_err = asyncio.create_task(self._stderr_error_evt.wait())
            done, pending = await asyncio.wait({t_turn, t_err}, timeout=timeout)
            for t in pending:
                t.cancel()
            if not done:
                timed_out = True
                log.warning("⚠ 等待 copilot 结果超时")
            else:
                # stderr 错误事件触发时视为报错(预算不足等), 及时反馈而不是等超时
                if self._stderr_error_evt.is_set():
                    stderr_fired = True

        # 收敛所有 chunk
        # ★ 修复: copilot 的 agent_message_chunk 是逐字/逐词流式吐出, 必须直接连续拼接,
        # 不能逐 chunk .strip() 或用换行 join(否则每个字之间都会被插换行)。
        parts = []
        for chunk in self.sess_update_queue:
            if chunk.get("type") == "text" and chunk.get("text"):
                parts.append(chunk["text"])  # 保留原文(含 chunk 内的换行符)
        result = "".join(parts)  # 直接拼接, 不插入分隔
        # 去掉多余换行: 连续 2 个以上换行压缩成单个, 并去除每行首尾空白
        result = re.sub(r"\n{2,}", "\n", result)
        result = "\n".join(line.strip() for line in result.split("\n"))
        result = result.strip()
        if not result:
            if stderr_fired and self.stderr_error and time.time() - self.stderr_error[0] < 120:
                return f"[copilot 错误] {self.stderr_error[1]}"
            if timed_out:
                # 若近期有错误 stderr(如预算不足), 优先反馈它
                if self.stderr_error and time.time() - self.stderr_error[0] < 120:
                    return f"[copilot 错误] {self.stderr_error[1]}"
                return "[copilot 无响应] 等待结果超时(可能预算不足或 copilot 卡住)"
            return "(无输出)"
        return result

    # ---- pump (常驻读 copilot stdout) ----
    async def run_pump(self):
        stderr_task = asyncio.ensure_future(self._stderr_loop())
        while True:
            line = await self._read_line()
            if line is None or line == "":
                log.warning("⚠ copilot stdout EOF")
                self._died.set()  # 标记进程死亡, 供上层自动重启
                break
            line = line.strip()
            if not line:
                continue
            try:
                msg = json.loads(line)
            except json.JSONDecodeError:
                continue
            # ★ 任何来自 copilot 的合法消息都是"活动"信号, 刷新活动刷新超时的计时
            self._last_activity = time.time()

            method = msg.get("method")
            if method:
                params = msg.get("params", {})
                # copilot 的 update 是自定义 sessionUpdate 字段
                if method == "session/update":
                    update = params.get("update", {})
                    su = update.get("sessionUpdate")
                    if su == "agent_message_chunk":
                        content = update.get("content", {})
                        if isinstance(content, dict):
                            self.sess_update_queue.append(content)
                    if params.get("isResult"):
                        self._turn_done.set()
                    continue
                elif method == "permission/request":
                    # --allow-all 下一般不会出现, 兜底批准
                    self._write({"jsonrpc": "2.0", "id": msg.get("id"), "result": {
                        "outcome": "allowed", "sessionId": params.get("sessionId"), "totalCostUsd": 0.0}})
                    continue
                else:
                    # 其他 agent 请求, 兜底空响应
                    if "id" in msg:
                        self._write({"jsonrpc": "2.0", "id": msg.get("id"), "result": {}})
                    continue
            else:
                # 对我们请求的响应
                rid = msg.get("id")
                if rid in self.pending:
                    fut = self.pending.pop(rid)
                    if not fut.done():
                        if "error" in msg:
                            fut.set_result(msg)
                        else:
                            fut.set_result(msg.get("result", {}))
                else:
                    log.debug("未配对响应: %s", json.dumps(msg, ensure_ascii=False)[:200])
        stderr_task.cancel()  # cancel() 返回 bool, 不是 awaitable

    async def _stderr_loop(self):
        while True:
            line = await self._read_stderr()
            if line is None or line == "":
                return
            line = line.strip()
            if not line:
                continue
            log.info(f"  [copilot stderr] {line[:300]}")
            # 捕获错误类 stderr(如预算不足/失败), 供 prompt 反馈给用户
            low = line.lower()
            if any(k in low for k in ("error", "budget", "fail", "exceed", "limit")):
                self.stderr_error = (time.time(), line.strip())
                # 置位结束事件(turn) + 错误标记: 让等待中的 prompt 提前返回报错
                self._stderr_error_evt.set()
                self._turn_done.set()

    async def close_session(self):
        if self.session_id:
            try:
                await self.request("session/close", {"sessionId": self.session_id}, timeout=10)
            except Exception:
                pass

    def stop_process(self):
        try:
            self.proc.kill()
        except Exception:
            pass
        self._died.set()

    def reset(self):
        """进程重启前的状态清理。"""
        self._died.clear()
        self._id = 0
        self.pending = {}
        self.session_id = None
        self.sess_update_queue = []

    async def start_session(self, mcp_servers=None):
        """启动进程 + 握手 + 创建/恢复会话。任一步失败抛异常由上层重试。
        MCP 通过 create_or_resume_session 的 mcpServers 字段挂载
        (copilot 1.0.77 ACP 模式不认命令行 --additional-mcp-config)。"""
        self.reset()
        self.start_process()
        # 必须先启动 stdout pump, 否则 initialize/session 的响应读不到(会卡死)
        self._pump_task = asyncio.ensure_future(self.run_pump())
        await self.initialize()
        await self.create_or_resume_session()
        return self.session_id


# ═══════════════════════════════════════════════════════════════════
#  主 Worker — 三合一: relay(nlp_worker) + ACP(copilot) + HTTP MCP
# ═══════════════════════════════════════════════════════════════════
class NLPWorkerACP:
    def __init__(self, relay_url, copilot_cmd="copilot", cwd=None, session_file=None,
                 model=None, mcp_url="http://127.0.0.1:9001/mcp", mcp_user=None,
                 notes_file=None, bridge_http=None, bridge_target_open_id=None):
        """
        聊天执行器: 占 relay 的 nlp_worker 槽, 驱动 copilot --acp 常驻会话。
        copilot 的 Kanzi MCP 强制走 kz_mcp_http.py(单进程多用户版), 不内置。
        安全: 通道(用户)由 kz_mcp_http.py 白名单控制, 本进程通过 header 带用户名,
        其他人拿本进程无法自建用户/连别的 Kanzi。
        持久化: 每次对话(用户指令+copilot回复)追加到 notes_file(结构化开发笔记),
        启动时自动让 copilot 读笔记恢复开发进度。

        v2 新增: bridge_http = 桥的 HTTP 文件服务地址(如 http://10.10.118.152:8081),
        用于文件下载([FILE_DOWNLOAD])与截图回传([FILE] → POST /upload)。
        bridge_target_open_id = 回传截图时携带的飞书用户 open_id(若固定单用户可配; 否则置空由桥自动路由)。
        """
        self.relay_url = relay_url
        self.channel = relay_url.rsplit("/", 1)[-1] or "default"
        self.cwd = cwd or os.getcwd()
        self.mcp_url = mcp_url
        self.mcp_user = mcp_user or self.channel
        self.notes_file = notes_file or os.path.join(self.cwd, "开发笔记.md")
        self.bridge_http = (bridge_http or "").rstrip("/")
        self.bridge_target_open_id = bridge_target_open_id or ""
        # v2: 截图约定是否已合并注入首条指令(只注入一次)
        self._screenshot_conv_injected = False

        self.relay = RelayClient(relay_url)
        self.acp = AcpClient(copilot_cmd, self.cwd, session_file, model,
                             mcp_config=self._mcp_config())

        self._busy = False
        self._history = []
        # ★ relay 真正就绪信号: 收到 relay 的 connected 消息才置位,
        # 确保笔记提示等消息在 relay 握手完成后才发出(避免发到未就绪窗口丢失)
        self._relay_ready = asyncio.Event()

    def _mcp_config(self):
        """
        copilot 挂的 MCP 配置(写进 .mcp.json / 会话 mcpServers)——**全部指向本地
        kz_mcp_http.py 三端点, 一个都不会直接连官方/公网**:
          - kanzi-studio-mcp → {base}/kanzistudio_mcp  (本地代理 → Kanzi Studio)
          - kanzi-api-mcp    → {base}/kanzi_api_mcp   (本地代理 → 官方 api MCP)
          - kanzi-doc-mcp    → {base}/kanzi_doc_mcp   (本地代理 → 官方 doc MCP)

        ★ 三端点全部是本地 kz_mcp_http.py 的代理, 地址本地/快/稳/断不了。
          copilot **能主动用全部工具**(studio+api+doc), 官方 api/doc 的 session 失效
          由 kz_mcp_http.py(内置 OfficialMcpHttpClient)自动重连, copilot 无感、
          永不丢上下文、免重启。

        headers 用对象形式 ({key:value}), studio/官方代理都走白名单, 带用户名 header。
        """
        base = self.mcp_url.rsplit("/mcp", 1)[0] if "/mcp" in self.mcp_url else self.mcp_url.rstrip("/")
        return [
            {
                "name": "kanzi-studio-mcp",
                "type": "http",
                "url": f"{base}/kanzistudio_mcp",
                "headers": {"X-Kanzi-User": self.mcp_user},
            },
            {
                "name": "kanzi-api-mcp",
                "type": "http",
                "url": f"{base}/kanzi_api_mcp",
                "headers": {"X-Kanzi-User": self.mcp_user},
            },
            {
                "name": "kanzi-doc-mcp",
                "type": "http",
                "url": f"{base}/kanzi_doc_mcp",
                "headers": {"X-Kanzi-User": self.mcp_user},
            },
        ]

    def _ensure_mcp_config_file(self):
        """启动 copilot 前, 把 Kanzi MCP 写入 cwd 的 .mcp.json(copilot 启动时读取)。

        已验证: copilot 1.0.77 的 --acp 模式忽略 --additional-mcp-config, 且
        session/new 传来的 mcpServers 只过 zod 校验但 copilot 并不真正加载
        (仍报『No MCP servers configured』)。copilot 实际从 cwd 的 .mcp.json 读取 MCP。

        这里合并写入(不覆盖已有配置), 让 copilot 一启动就能识别 kanziMCP。"""
        path = os.path.join(self.cwd, ".mcp.json")
        cfg = {}
        try:
            if os.path.exists(path):
                with open(path, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
                    if not isinstance(cfg, dict) or "mcpServers" not in cfg:
                        cfg = {"mcpServers": cfg.get("mcpServers", {}) if isinstance(cfg, dict) else {}}
        except Exception as e:
            log.warning(f"读取 .mcp.json 失败, 将重建: {e}")
            cfg = {"mcpServers": {}}
        cfg.setdefault("mcpServers", {})
        for m in self._mcp_config():
            cfg["mcpServers"][m["name"]] = {
                "type": m["type"],
                "url": m["url"],
                "headers": m.get("headers", {}),
            }
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(cfg, f, ensure_ascii=False, indent=2)
            log.info(f"📄 已写入 MCP 配置: {path}")
            log.info(f"   {path} → kanzi-studio-mcp = {self.mcp_url} (user={self.mcp_user})")
        except Exception as e:
            log.warning(f"写入 .mcp.json 失败(可能只读): {e}")

    async def start(self):
        self.relay.on_message = self._on_relay_message

        # 先写入 MCP 配置文件, 确保 copilot 启动即能识别 Kanzi MCP
        self._ensure_mcp_config_file()

        # 先带重试地启动 copilot ACP (initialize/会话失败不退出, 自动重启)
        await self._bootstrap()

        # 再启动 relay (nlp_worker 角色) —— 常驻, 断开自动重连, 后台跑
        self._relay_task = asyncio.ensure_future(self.relay.start())

        log.info("🚀 NLP Worker ACP 已就绪")
        log.info(f"   copilot Kanzi MCP → {self.mcp_url}  (user={self.mcp_user})")
        if self.acp.session_id:
            log.info(f"   会话: {self.acp.session_id} (持久化已启用)")

        # 启动时不主动让 copilot 读开发笔记(避免触发 copilot 读文件/初始化 MCP 导致卡死
        # 而被 relay 判定超时踢掉), 只给 Kanzi 插件发一条提醒(提示有笔记可查), 快速就绪。
        await self._notify_notes_prompt()

        return None

    def _screenshot_convention(self) -> str:
        """v2: 截图回传约定文本(只在用户发来首条指令时合并注入一次)。

        约定仅在**当前 copilot 会话**(cwd=本项目)的上下文里生效, 不写任何共享/全局文件,
        因此**不影响其他项目的 copilot**。"""
        return (
            "【工作约定 - 请一直记住】\n"
            "以后你执行截图(比如用 Kanzi MCP 的截图工具)后, 请在回复末尾另起一行写:\n"
            "[FILE]\n"
            "path=<截图文件的完整路径>\n"
            "例如:\n"
            "[FILE]\n"
            "path=C:\\目录\\截图.png\n"
            "这样文件才能被正确回传给用户。若用不到截图, 忽略本条即可。"
        )

    async def _bootstrap(self):
        """启动 copilot 并建立会话, 带失败重试(最多 10 次, 每次间隔 10s)。
        不退出 —— copilot 冷启动慢或预算卡住时持续重试, 直到成功。"""
        for attempt in range(1, 11):
            try:
                await self.acp.start_session()
                return
            except Exception as e:
                log.warning(f"⚠ copilot 启动/握手失败(第{attempt}次): {e}")
                try:
                    self.acp.stop_process()
                except Exception:
                    pass
                if attempt >= 10:
                    log.error("⚠ copilot 连续 10 次启动失败, 将进入后台自动重试循环")
                    return  # 不退出, 交给主循环的 health-check 继续尝试
                await asyncio.sleep(10)

    def _copilot_alive(self):
        if self.acp.proc is None:
            return False
        return self.acp.proc.poll() is None and not self.acp._died.is_set()

    async def _health_loop(self):
        """后台守护: copilot 进程挂了就自动重启并恢复会话(解决隔夜/崩溃)。"""
        while True:
            if not self._copilot_alive():
                log.info("♻ copilot 进程不在, 自动重启...")
                try:
                    self.acp.stop_process()
                except Exception:
                    pass
                try:
                    await self.acp.start_session()
                    log.info("✅ copilot 已自动重启并恢复会话")
                except Exception as e:
                    log.warning(f"⚠ 自动重启失败: {e}, 30秒后重试")
                    await asyncio.sleep(30)
                    continue
            await asyncio.sleep(10)

    async def _on_relay_message(self, raw: str):
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            return

        msg_type = data.get("type", "")

        # relay 连接/握手完成信号
        if msg_type == "connected":
            log.info(f"中继: {data.get('text', '')}")
            self._relay_ready.set()   # ★ 标记 relay 已就绪
            return

        # 聊天指令 (copilot 调 Kanzi 的 MCP 走 kz_mcp_http.py, 本进程不处理 mcp_response)
        if msg_type in ("user_message", "user_choice"):
            instruction = data.get("selected") or data.get("text", "")
            if not instruction:
                return

            # v2: 文件下载任务 → nlp_worker 自己下载到工作目录, 不经过 copilot
            if instruction.strip().startswith("[FILE_DOWNLOAD]"):
                await self._handle_file_download(instruction)
                return

            if self._busy:
                await self.relay.send({"type": "thinking",
                                       "text": "⏳ Copilot 正在处理上一条指令, 请稍候..."})
                return

            log.info(f"📝 指令: {instruction[:100]}")
            loop = asyncio.get_event_loop()
            loop.create_task(self._handle_instruction(instruction))

        elif msg_type == "connected":
            log.info(f"中继: {data.get('text', '')}")

    async def _handle_file_download(self, instruction: str):
        """v2: 处理 [FILE_DOWNLOAD] 任务 —— nlp_worker 自己下载到工作目录, 不经过 copilot。
        下载成功后直接回飞书保存路径。"""
        url = ""
        name = "file"
        for line in instruction.splitlines():
            line = line.strip()
            if line.startswith("url="):
                url = line[4:].strip()
            elif line.startswith("name="):
                name = line[5:].strip()
        if not url:
            await self.relay.send({"type": "claude_output", "text": "❌ 文件下载任务缺少 url"})
            return
        try:
            save_name = os.path.basename(url) or name.replace("/", "_")
            save_path = os.path.join(self.cwd, save_name)
            # v2@fix: URL 里的非 ASCII 字符(如中文文件名)需 percent-encode, 否则 urlopen 以 ascii 编码失败
            enc_url = urllib.parse.quote(url, safe="/:~&#@!$&'()*+,;=%")
            req = urllib.request.Request(enc_url)
            with urllib.request.urlopen(req, timeout=120) as r:
                data = r.read()
            with open(save_path, "wb") as f:
                f.write(data)
            msg = f"✅ 文件已保存到工作目录:\n{save_path}"
            if name and name != save_name:
                msg += f"\n(原始文件名: {name})"
            await self.relay.send({"type": "claude_output", "text": msg})
            log.info(f"📥 已下载文件到: {save_path}")
        except Exception as e:
            log.error(f"下载文件失败: {e}")
            await self.relay.send({"type": "claude_output", "text": f"❌ 文件下载失败: {e}"})

    async def _handle_instruction(self, instruction: str):
        self._busy = True
        try:
            await self.relay.send({"type": "thinking", "text": "🤖 Copilot 思考中..."})
            # ★ 用户明确要求『查看笔记』时才读笔记(启动不自动读, 避免卡死);
            #   这里把笔记内容作为上下文交给 copilot 恢复进度
            if instruction and ("查看笔记" in instruction or "恢复进度" in instruction):
                notes = self._load_notes()
                if notes:
                    instruction = (
                        f"这是开发笔记内容, 请据此了解开发进度并准备继续之前的工作, 简要说明你了解了什么:\n\n"
                        f"{notes[-3000:]}")
                else:
                    instruction = "开发笔记为空, 没有历史记录。"
            # v2: 首条指令合并截图约定(只注入一次, 仅当前会话生效, 不影响其他项目)
            if not self._screenshot_conv_injected and self.bridge_http:
                instruction = self._screenshot_convention() + "\n\n" + instruction
                self._screenshot_conv_injected = True
            result = await self.acp.prompt(instruction)
            self._history.append(instruction)
            # 追加开发笔记(用户指令 + copilot 回复, 结构化)
            self._append_note(instruction, result)
            await self._process_copilot_reply(result)
        except Exception as e:
            log.error(f"处理异常: {e}")
            try:
                await self.relay.send({"type": "claude_output",
                                       "text": f"❌ 异常: {e}"})
            except Exception:
                pass
        finally:
            self._busy = False

    # ---- v2: 处理 copilot 回复, 提取 [FILE] 截图回传 ----
    async def _process_copilot_reply(self, result: str):
        """发送 copilot 回复; 若含 [FILE] 标记则先读图 POST 到桥 /upload 回飞书。
        定位图片顺序(老隋定): ① 解析回复中的 [FILE]path= ② 解析不到则扫描工作目录取最新图片。
        """
        text = result or "(无输出)"
        file_path = self._extract_file_marker(text)
        if file_path:
            # 有 path= 标记: 直接读该文件并 POST
            uploaded = await self._upload_to_bridge(file_path, text)
        else:
            # 无 [FILE]path= 标记: 说明 copilot 本次没有显式截图, 不回传(避免每次回复都误带工作目录旧图)
            uploaded = False
        # 清理 [FILE] 标记后发纯文本
        clean = re.sub(r"\[FILE[^\]]*\](\s*path\s*=\s*\S+)?", "", text)
        clean = re.sub(r"\n{2,}", "\n", clean).strip()
        await self.relay.send({"type": "claude_output", "text": clean or "(无输出)"})
        if uploaded:
            log.info("🖼️ 截图已回传飞书")

    @staticmethod
    def _extract_file_marker(text: str):
        """从回复里提取 [FILE] 标记的 path= 路径。
        支持 "[FILE]...path=C:\\dir\\x.png" 等; 兼容 Windows 反斜杠和 Linux 斜杠。"""
        if "[FILE]" not in text:
            return None
        # 优先带引号的路径, 再退化到行尾非空白串
        m = re.search(r"path\s*=\s*[\"']([^\"']+)[\"']", text)
        if m:
            return m.group(1).strip()
        # 未带引号: 取行内 path= 后到行尾/分号/中文结束的部分
        m = re.search(r"path\s*=\s*([^\s;]+)", text, re.IGNORECASE | re.MULTILINE)
        if m:
            p = m.group(1).strip().rstrip(",.:`'").strip('"').strip("'")
            return p or None
        return None
    async def _upload_to_bridge(self, file_path: str, original_text: str) -> bool:
        """读文件字节并 HTTP POST 到桥 /upload?open_id=..&name=..(同步发飞书)。"""
        if not self.bridge_http:
            log.warning("⚠️ 未配置 bridge_http, 无法回传截图")
            return False
        try:
            with open(file_path, "rb") as f:
                data = f.read()
            name = os.path.basename(file_path) or "file"
            # 文件名无后缀时按文件头识别真实图片格式补后缀(copilot 截图常存成 UUID 裸名)
            if not os.path.splitext(name)[1]:
                ext = _sniff_image_ext(data)
                name = name + ext
            qs = urllib.parse.urlencode({"name": name})
            if self.bridge_target_open_id:
                qs += "&" + urllib.parse.urlencode({"open_id": self.bridge_target_open_id})
            url = f"{self.bridge_http}/upload?{qs}"
            req = urllib.request.Request(url, data=data, method="POST",
                                         headers={"Content-Type": "application/octet-stream",
                                                  "Content-Length": str(len(data))})
            with urllib.request.urlopen(req, timeout=120) as r:
                r.read()
            return True
        except Exception as e:
            log.error(f"上传截图到桥失败: {e}")
            return False
    def _append_note(self, instruction: str, reply: str):
        """把一次交互结构化追加到笔记文件。"""
        try:
            ts = time.strftime("%Y-%m-%d %H:%M:%S")
            # 剔除明显无意义/纯问候的指令, 避免污染笔记
            t = (instruction or "").strip()
            low = t.lower()
            greet = ("在吗", "你好", "在不在", "在么", "hello", "hi", "hey")
            if not t or len(t) < 2 or low in greet or low.startswith(("hello", "hi", "hey")):
                return
            with open(self.notes_file, "a", encoding="utf-8") as f:
                f.write(f"\n### {ts}\n")
                f.write(f"**用户要求**: {t}\n")
                if reply and not reply.startswith("[") :
                    f.write(f"**copilot 执行/回复**: {(reply or '').strip()[:2000]}\n")
            log.info(f"📒 已记录到开发笔记: {self.notes_file}")
        except Exception as e:
            log.warning(f"写开发笔记失败: {e}")

    def _load_notes(self):
        """读取笔记内容(供启动时让 copilot 恢复进度)。"""
        try:
            if os.path.exists(self.notes_file):
                with open(self.notes_file, "r", encoding="utf-8") as f:
                    content = f.read().strip()
                # 只取最近 60 条(避免过长)
                entries = content.split("\n### ")
                if len(entries) > 60:
                    content = "### " + "\n### ".join(entries[-60:])
                return content
        except Exception as e:
            log.warning(f"读取开发笔记失败: {e}")
        return ""

    async def _notify_notes_prompt(self):
        """启动时**不**主动让 copilot 读开发笔记(避免触发 copilot 读文件/初始化 MCP
        导致启动卡死/被 relay 踢), 只给 Kanzi 插件发一条**提醒**(提示有笔记可查)。
        会话创建完成后调用, 快速就绪不阻塞。"""
        notes = self._load_notes()
        try:
            # 先等 relay 真正握手完成(_relay_ready), 再发提醒给 Kanzi 插件
            await self._wait_relay_ready()
            if notes:
                text = ("📒 检测到开发笔记。如需恢复之前的开发进度, 可回复『查看笔记』；"
                        "否则直接发指令即可继续工作。")
            else:
                text = "📖 无开发笔记记录, 直接开始新工作即可。"
            await self.relay.send({"type": "claude_output", "text": text})
            log.info("📒 已发送开发笔记提醒")
        except Exception as e:
            log.warning(f"发送开发笔记提醒失败: {e}")

    async def _wait_relay_ready(self, timeout=15.0):
        """等待 relay 与通道握手完成(_relay_ready 置位)。超时则记录警告但不抛错,
        避免因 relay 未就绪而永久阻塞提醒发送。"""
        try:
            await asyncio.wait_for(self._relay_ready.wait(), timeout=timeout)
        except asyncio.TimeoutError:
            log.warning("⚠ 等待 relay 就绪超时, 继续(消息可能丢失)")

    async def stop(self):
        try:
            await self.acp.close_session()
        except Exception:
            pass
        try:
            self.acp.stop_process()
        except Exception:
            pass
        await self.relay.stop()


# ═══════════════════════════════════════════════════════════════════
#  入口
# ═══════════════════════════════════════════════════════════════════


def _sniff_image_ext(data: bytes) -> str:
    """按文件头 magic bytes 识别图片格式, 返回带点后缀; 识别不出返回 .png。"""
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return ".png"
    if data[:3] == b"\xff\xd8\xff":
        return ".jpg"
    if data[:2] == b"BM":
        return ".bmp"
    if data[:6] in (b"GIF87a", b"GIF89a"):
        return ".gif"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return ".webp"
    return ".png"

async def main():
    parser = argparse.ArgumentParser(description="NLP Worker ACP (聊天插件执行器, 强制走 kz_mcp_http.py)")
    parser.add_argument("--relay", default=None,
                       help="中继地址, 如 ws://10.10.118.152:58080/suijichao (路径决定通道/哪台 Kanzi, 必须与 kz_mcp_http.py 一致)")
    parser.add_argument("--copilot", default="copilot", help="copilot 命令 (默认 copilot)")
    parser.add_argument("--cwd", default=None, help="copilot 工作目录")
    parser.add_argument("--session-file", default=None,
                       help="会话持久化文件路径 (默认读取 --relay 自动生成在 --cwd)")
    parser.add_argument("--model", default=None, help="指定 copilot 模型 (如 gpt-5.6-sol)")
    parser.add_argument("--notes", default=None,
                       help="开发笔记文件路径 (默认 <cwd>/开发笔记.md; 每次对话自动追加, 启动时自动让 copilot 读取)")
    parser.add_argument("--mcp-port", type=int, default=9001,
                       help="kz_mcp_http.py 的 HTTP MCP 端口 (默认 9001; 端口变化时改这个)")
    parser.add_argument("--mcp-host", default=None,
                       help="kz_mcp_http.py 所在机器 IP (默认用 --relay 的主机 IP, 即 relay 机)")
    parser.add_argument("--bridge-http", default=None,
                       help="桥的 HTTP 文件服务地址, 如 http://10.10.118.152:8081 (用于文件下载/截图回传)")
    parser.add_argument("--bridge-open-id", default=None,
                       help="回传截图/文件携带的飞书用户 open_id (固定单用户可配; 留空由桥路由)")
    parser.add_argument("--debug", action="store_true", help="开启调试日志")
    args = parser.parse_args()

    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)

    if not args.relay:
        parser.error("需要 --relay 参数")

    # 从 --relay ws://<ip>:<port>/<user> 推出 主机IP + relay端口 + 用户名
    # --relay 必须带路径(用户名)
    relay_no_scheme = args.relay.split("://", 1)[-1]
    if "/" not in relay_no_scheme:
        parser.error("请使用带用户名的 relay 地址, 如 ws://IP:端口/用户名")
    hostport, _, username = relay_no_scheme.rpartition("/")
    username = username or ""
    # kz_mcp_http.py 与 relay 同机(在 10.10.118.152:9001), nlp_worker_acp.py/copilot 可能跨机。
    # 因此 mcp_url 用 relay 的主机 IP(即 kz_mcp_http.py 所在机), 保证远程 copilot 也能
    # 通过 10.10.118.152:9001 访问 kz_mcp_http.py。
    # 前提: kz_mcp_http.py 必须监听 0.0.0.0:9001(而非 127.0.0.1), 否则远程连不进。
    # 同机部署时, relay IP 即本机 IP, 同样可用。
    mcp_host = args.mcp_host or hostport.rsplit(":", 1)[0]

    # 会话文件默认: <cwd>/.nlp_session.<channel>.json
    cwd = args.cwd or os.getcwd()
    channel = username
    session_file = args.session_file or os.path.join(cwd, f".nlp_session.{channel}.json")
    notes_file = args.notes or os.path.join(cwd, "开发笔记.md")

    # copilot 挂的 MCP 指向 kz_mcp_http.py
    mcp_url = f"http://{mcp_host}:{args.mcp_port}/mcp"

    worker = None
    try:
        worker = NLPWorkerACP(args.relay, args.copilot, cwd, session_file, args.model,
                              mcp_url, mcp_user=username, notes_file=notes_file,
                              bridge_http=args.bridge_http,
                              bridge_target_open_id=args.bridge_open_id)
        await worker.start()
        # 后台守护: copilot 挂了自动重启
        health = asyncio.ensure_future(worker._health_loop())
        # 保持运行
        while True:
            await asyncio.sleep(3600)
    except KeyboardInterrupt:
        logging.info("已停止")
    except Exception as e:
        logging.error(f"运行异常: {e}, 5秒后自动重启")
        if worker:
            try:
                await worker.stop()
            except Exception:
                pass
        await asyncio.sleep(5)
        return await main()  # 意外异常时整体重入(不退出)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        log.info("已停止")
    except Exception as e:
        log.error(f"启动失败: {e}")
        sys.exit(1)
