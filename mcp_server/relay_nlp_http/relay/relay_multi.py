"""
Kanzi Studio MCP WebSocket 中继服务 — 多用户 + NLP Worker 版

处理三种客户端角色：
- server: Kanzi MCP server_ws
- client: 外部 MCP 客户端
- nlp_client: Kanzi Studio 聊天插件（用户输入自然语言）
- nlp_worker: Claude Worker（执行 Claude Code）

每个通道内，nlp_client ↔ nlp_worker 双向转发，
server ↔ client 双向转发（原有功能不变）。

用法：
    python relay_multi.py
    默认监听 58080

依赖：
    pip install websockets
"""
import asyncio
import json
import logging
import sys
import websockets

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger("kz-relay-multi")


def make_channel():
    return {
        "server": None,
        "client": None,
        "nlp": None,       # nlp_client（聊天插件）
        "nlp_worker": None, # nlp_worker（Claude 执行器）
        "nlp_pending": [],
    }


class MultiRelay:
    def __init__(self):
        self.channels: dict[str, dict] = {}

    async def _send_safe(self, ws, msg):
        if ws is None:
            return False
        try:
            await ws.send(msg)
            return True
        except:
            return False

    def _ensure(self, name: str) -> dict:
        if name not in self.channels:
            self.channels[name] = make_channel()
            log.info(f"📂 创建通道: {name}")
        return self.channels[name]

    async def _push_to_nlp(self, name: str, msg: dict):
        ch = self.channels.get(name)
        if not ch:
            return
        ws = ch.get("nlp")
        if ws:
            await self._send_safe(ws, json.dumps(msg, ensure_ascii=False))
        else:
            ch.setdefault("nlp_pending", []).append(msg)

    async def _flush_nlp_pending(self, name: str):
        ch = self.channels.get(name)
        if not ch:
            return
        pending = ch.get("nlp_pending", [])
        ws = ch.get("nlp")
        if ws and pending:
            for msg in pending:
                await self._send_safe(ws, json.dumps(msg, ensure_ascii=False))
            ch["nlp_pending"] = []

    # ── 主入口 ──

    async def handle(self, websocket):
        name = getattr(websocket, "_relay_channel", "default")
        if not name or name == "/":
            name = "default"

        try:
            first_raw = await asyncio.wait_for(websocket.recv(), timeout=15)
        except asyncio.TimeoutError:
            log.warning(f"⏱ [{name}] 超时")
            await websocket.close()
            return
        except websockets.ConnectionClosed:
            return

        try:
            data = json.loads(first_raw)
        except json.JSONDecodeError:
            log.warning(f"❌ [{name}] JSON 解析失败")
            await websocket.close()
            return

        role = data.get("role", "")

        if role == "server":
            msg_name = data.get("name", "")
            if msg_name:
                name = msg_name
            await self._handle_server(websocket, name)
        elif role == "nlp_client":
            msg_name = data.get("name", "")
            if msg_name:
                name = msg_name
            await self._handle_nlp_client(websocket, name)
        elif role == "nlp_worker":
            msg_name = data.get("name", "")
            if msg_name:
                name = msg_name
            await self._handle_nlp_worker(websocket, name)
        else:
            await self._handle_client(websocket, name, first_raw)

    # ── Server ──

    async def _handle_server(self, ws, name: str):
        ch = self._ensure(name)
        old = ch["server"]
        ch["server"] = ws
        if old:
            try: await old.close()
            except: pass

        await self._send_safe(ws, json.dumps({"type": "connected", "role": "server"}))
        log.info(f"✅ [{name}] Server 已连接")

        try:
            async for msg in ws:
                client = ch.get("client")
                if client:
                    await self._send_safe(client, msg)
                # 也转发给 nlp_worker（包装为 MCP 响应类型）
                nlp_worker = ch.get("nlp_worker")
                if nlp_worker:
                    await self._send_safe(nlp_worker, json.dumps({
                        "type": "mcp_response",
                        "text": msg
                    }))
        except websockets.ConnectionClosed:
            pass
        finally:
            log.warning(f"🔌 [{name}] Server 断开")
            ch["server"] = None
            await self._push_to_nlp(name, {
                "type": "server_disconnected", "text": "Kanzi MCP 连接已断开"
            })
            self._cleanup(name)

    # ── Client ──

    async def _handle_client(self, ws, name: str, first_msg: str):
        ch = self._ensure(name)
        if ch["server"] is None:
            log.warning(f"[{name}] Server 不在线，拒绝 Client")
            await ws.close(4001, f"Server [{name}] not connected")
            return

        old = ch["client"]
        ch["client"] = ws
        if old:
            try: await old.close()
            except: pass

        log.info(f"✅ [{name}] Client 已连接")
        await self._send_safe(ch["server"], first_msg)

        try:
            async for msg in ws:
                server = ch.get("server")
                if server:
                    await self._send_safe(server, msg)
                else:
                    await ws.close()
                    return
        except websockets.ConnectionClosed:
            pass
        finally:
            log.warning(f"🔌 [{name}] Client 断开")
            ch["client"] = None
            self._cleanup(name)

    # ── NLP Client（聊天插件） ──

    async def _handle_nlp_client(self, ws, name: str):
        ch = self._ensure(name)
        old = ch["nlp"]
        ch["nlp"] = ws
        if old:
            try: await old.close()
            except: pass

        await self._send_safe(ws, json.dumps({
            "type": "connected",
            "role": "nlp_client",
            "text": f"已连接到通道 [{name}]",
            "server_online": ch["server"] is not None,
            "worker_online": ch["nlp_worker"] is not None
        }))
        log.info(f"✅ [{name}] NLP Client 已连接")

        await self._flush_nlp_pending(name)

        try:
            async for raw in ws:
                try:
                    data = json.loads(raw)
                except json.JSONDecodeError:
                    await self._send_safe(ws, json.dumps({
                        "type": "error", "text": "消息格式错误"
                    }))
                    continue

                msg_type = data.get("type", "")

                if msg_type in ("user_message", "user_choice"):
                    # 转发给 nlp_worker
                    nlp_worker = ch.get("nlp_worker")
                    if nlp_worker:
                        await self._send_safe(nlp_worker, raw)
                    else:
                        await self._send_safe(ws, json.dumps({
                            "type": "error",
                            "text": "没有可用的 Chat Worker，请先启动 nlp_worker.py"
                        }))
                else:
                    await self._send_safe(ws, json.dumps({
                        "type": "error", "text": f"未知消息类型: {msg_type}"
                    }))

        except websockets.ConnectionClosed:
            pass
        finally:
            log.warning(f"🔌 [{name}] NLP Client 断开")
            ch["nlp"] = None
            self._cleanup(name)

    # ── NLP Worker（Claude 执行器） ──

    async def _handle_nlp_worker(self, ws, name: str):
        ch = self._ensure(name)
        old = ch["nlp_worker"]
        ch["nlp_worker"] = ws
        if old:
            try: await old.close()
            except: pass

        await self._send_safe(ws, json.dumps({
            "type": "connected", "role": "nlp_worker",
            "text": f"已连接到通道 [{name}]"
        }))
        log.info(f"✅ [{name}] NLP Worker 已连接")

        # 通知 nlp_client worker 在线
        await self._push_to_nlp(name, {
            "type": "worker_online", "text": "Chat Worker 已连接"
        })

        try:
            async for raw in ws:
                try:
                    data = json.loads(raw)
                    msg_type = data.get("type", "")
                    if msg_type == "mcp_request":
                        # MCP 请求转发给 Server
                        server = ch.get("server")
                        if server:
                            await self._send_safe(server, data.get("text", raw))
                        continue
                except json.JSONDecodeError:
                    pass

                # worker 的普通消息转发给 nlp_client
                nlp = ch.get("nlp")
                if nlp:
                    await self._send_safe(nlp, raw)
        except websockets.ConnectionClosed:
            pass
        finally:
            log.warning(f"🔌 [{name}] NLP Worker 断开")
            ch["nlp_worker"] = None
            await self._push_to_nlp(name, {
                "type": "worker_disconnected", "text": "Chat Worker 已断开"
            })
            self._cleanup(name)

    # ── 清理 ──

    def _cleanup(self, name: str):
        ch = self.channels.get(name)
        if ch and all(v is None for v in (ch["server"], ch["client"], ch["nlp"], ch["nlp_worker"])):
            self.channels.pop(name, None)
            log.info(f"🗑️ 清理通道: {name}")


def make_process_request(relay):
    async def process_request(connection, request):
        path = request.path if request else "/"
        name = path.strip("/")
        if not name or name == "/":
            name = "default"
        connection._relay_channel = name
    return process_request


async def main():
    relay = MultiRelay()
    port = 58080
    process_request = make_process_request(relay)

    async with websockets.serve(
        relay.handle, "0.0.0.0", port,
        process_request=process_request
    ):
        log.info(f"🔄 MCP 中继 ws://0.0.0.0:{port}")
        log.info(f"   路径区分通道: ws://ip:{port}/用户名")
        log.info(f"   Server:      ws://ip:{port}/用户名")
        log.info(f"   Client:      ws://ip:{port}/用户名")
        log.info(f"   NLP Client:  ws://ip:{port}/用户名  (聊天插件)")
        log.info(f"   NLP Worker:  ws://ip:{port}/用户名  (Claude 执行器)")
        await asyncio.Future()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        log.info("已停止")
    except Exception as e:
        log.error(f"启动失败: {e}")
        sys.exit(1)
