"""
Kanzi Studio MCP WebSocket 中继服务 — 多用户 + NLP Worker + 多连接共存版

处理四种客户端角色：
- server: Kanzi MCP server_ws
- client: 外部 MCP 客户端
- nlp_client: Kanzi Studio 聊天插件（用户输入自然语言）
- nlp_worker: Claude Worker（执行 Claude Code）

V2026-09-14 多连接共存改造（脚本批量执行不抢占）：
- 槽位并存：同槽位不互踢，主会话 + N 个脚本连接同时存在
- 定向回传：Kanzi 返回按请求 id 只回给发请求的那条连接（不广播）
- 三层回收：断开即收 + 空闲超时兜底 + 整通道闲置移除（连接不堆积）

每个通道内，nlp_client ↔ nlp_worker 双向转发，
server ↔ client 双向转发（client 槽支持多连接定向回传）。

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
import time
import websockets

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger("kz-relay-multi")

# ── 回收配置（可按需调整）──
SWEEP_INTERVAL        = 30    # 回收扫描间隔 秒
CONN_IDLE_TIMEOUT     = 120   # 单连接空闲回收 秒（有收发消息就刷新 last_active，不误伤执行中）
CHANNEL_IDLE_TIMEOUT  = 600   # 整通道闲置回收 秒（全部槽位空后）


def parse_req_id(text: str):
    """尽力从一条消息里取出请求 id（用于定向回传）。无 id 返回 None。"""
    if not text:
        return None
    try:
        data = json.loads(text)
    except (json.JSONDecodeError, ValueError):
        return None
    if isinstance(data, dict):
        # 直接 JSON-RPC: {"id": ...}
        if "id" in data and data["id"] is not None:
            return str(data["id"])
        # 可能包装在 text 里: {"type":"mcp_request","text":"{...}"}
        t = data.get("text")
        if isinstance(t, str) and t.strip().startswith("{"):
            try:
                inner = json.loads(t)
            except (json.JSONDecodeError, ValueError):
                return None
            if isinstance(inner, dict) and "id" in inner and inner["id"] is not None:
                return str(inner["id"])
    return None


def build_kanzi_offline_error(msg: str, name: str) -> str:
    """Kanzi(Server) 不在线时，对一条 client 请求生成错误回包（原样带 id，便于定向回传）。"""
    req_id = parse_req_id(msg)
    payload = {
        "jsonrpc": "2.0",
        "id": req_id if req_id is not None else -1,
        "error": {
            "code": -32000,
            "message": "Kanzi Studio 未连接（Server 不在线），请求未执行",
        },
        "channel": name,
    }
    return json.dumps(payload, ensure_ascii=False)


def make_channel():
    return {
        "server":     None,   # 主连接（指向 conns 里最后一条，兼容现有 http/nlp 读取）
        "client":     None,
        "nlp":        None,
        "nlp_worker": None,
        "conns": {            # 并存连接列表（主会话 + N 个脚本全在这）
            "server":     [],   # 每项 = {"ws": ws, "last_active": ts}
            "client":     [],
            "nlp":        [],
            "nlp_worker": [],
        },
        "route": {},          # { 请求id(str): client_conn } —— 定向回传归属
        "nlp_pending": [],
        "is_primary": False,  # 主通道标记：曾有 server 连接即标 true → 永不整通道清理
        "last_active": time.time(),   # 通道级活跃时间（整通道闲置回收用）
    }


class MultiRelay:
    def __init__(self):
        self.channels: dict[str, dict] = {}

    # ── 工具 ──

    def _touch(self, ch):
        ch["last_active"] = time.time()

    def _touch_conn(self, conn):
        conn["last_active"] = time.time()

    async def _send_safe(self, ws, msg):
        if ws is None:
            return False
        try:
            await ws.send(msg)
            return True
        except Exception:
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

    # ── 连接注册/注销通用辅助 ──

    # 方向1（2026-09-15）: 只有 client 槽允许多连接并存（靠 route[req_id] 定向回传）；
    # server / nlp / nlp_worker 是单个角色（Kanzi插件 / 飞书聊天入口 / Copilot worker），
    # 必须单连接——新连接顶替旧连接（踢旧），避免断连重连时新旧并存导致消息发给死连接。
    MULTI_OK_SLOTS = ("client",)

    def _attach(self, ch, slot: str, ws):
        """连接加入列表。client 槽多连接并存；其他核心槽单连接（新顶旧）。
        返回 (conn, kicked_ws)：kicked_ws 为被顶替的旧连接（需关闭），无则 None。"""
        conn = {"ws": ws, "last_active": time.time()}
        kicked_ws = None
        if slot not in self.MULTI_OK_SLOTS:
            # 非多连接槽：先踢掉同槽旧连接，保证只有一个活跃连接
            old_conns = ch["conns"][slot][:]
            for old in old_conns:
                if old.get("removed"):
                    continue
                kicked_ws = old["ws"]
                old["removed"] = True
                try:
                    ch["conns"][slot].remove(old)
                except ValueError:
                    pass
                # 清理该旧连接遗留的 route 归属
                for rid, t in list(ch["route"].items()):
                    if t is old:
                        ch["route"].pop(rid, None)
            if old_conns:
                log.info(f"♻ [{ch.get('name', '?')}] {slot} 槽新连接顶替旧连接")
        ch["conns"][slot].append(conn)
        ch[slot] = ws          # 主字段 = 最后加入
        # 主通道标记：server（Kanzi）连接 = 该通道是主会话通道 → 永不整通道清理
        if slot == "server":
            ch["is_primary"] = True
        self._touch(ch)
        return conn, kicked_ws

    def _detach(self, ch, slot: str, conn):
        """连接从列表移除；若它是主连接，主字段指向剩余最后一条。
        加 removed 标记防与 _sweep_loop 并发重复移除（list.remove 竞态）。"""
        if conn.get("removed"):
            return
        conns = ch["conns"][slot]
        if conn in conns:
            conns.remove(conn)
            conn["removed"] = True
        if conns:
            ch[slot] = conns[-1]["ws"]
        else:
            ch[slot] = None
        self._touch(ch)

    # ── Server ──

    async def _handle_server(self, ws, name: str):
        ch = self._ensure(name)
        ch["name"] = name
        conn, kicked = self._attach(ch, "server", ws)
        if kicked is not None:
            await self._send_safe(kicked, json.dumps({"type": "error", "text": "replaced by new server connection"}))
            try:
                await kicked.close()
            except Exception:
                pass

        await self._send_safe(ws, json.dumps({"type": "connected", "role": "server"}))
        log.info(f"✅ [{name}] Server 已连接（并存 #{len(ch['conns']['server'])}）")

        # 方向一：Kanzi 不在线期间不再积攒 client 请求（请求已当场回错）。
        # 此处仅清空历史遗留队列，避免旧队列跨重启被误 flush。
        pending = ch.get("client_pending")
        if pending:
            log.info(f"🧹 [{name}] 丢弃 {len(pending)} 条历史遗留挂起请求（Kanzi 离线期间已改为直接回错）")
            ch["client_pending"] = []

        try:
            async for msg in ws:
                self._touch(ch)
                self._touch_conn(conn)
                req_id = parse_req_id(msg)
                # 定向回传：Kanzi 返回按请求 id 只回给发起这条请求的 client 连接
                if req_id and req_id in ch["route"]:
                    target = ch["route"].pop(req_id, None)
                    if target is not None:
                        await self._send_safe(target["ws"], msg)
                        continue
                # 无 id 或未知 id（连接级消息）→ 回给主 client（兜底）
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
            self._detach(ch, "server", conn)
            await self._push_to_nlp(name, {
                "type": "server_disconnected", "text": "Kanzi MCP 连接已断开"
            })
            self._cleanup(name)

    # ── Client ──

    async def _handle_client(self, ws, name: str, first_msg: str):
        ch = self._ensure(name)
        ch["name"] = name
        conn, kicked = self._attach(ch, "client", ws)
        if kicked is not None:
            try:
                await kicked.close()
            except Exception:
                pass

        log.info(f"✅ [{name}] Client 已连接（并存 #{len(ch['conns']['client'])}）")

        # Kanzi 不在线 → 收到请求直接回错误，不积攒不挂起（server 不在线时请求根本执行不了）。
        # 连接本身保持（不 close），客户端不会因此重连。
        server = ch.get("server")
        if server is None:
            log.info(f"⏸ [{name}] Client 已连接但 Kanzi(Server) 未上线 → 请求一律直接回错误，不积攒")
            try:
                async for msg in ws:
                    self._touch(ch)
                    self._touch_conn(conn)
                    await self._send_safe(ws, build_kanzi_offline_error(msg, name))
            except websockets.ConnectionClosed:
                pass
            finally:
                log.info(f"🔌 [{name}] Client 断开（Kanzi 离线期间）")
                self._detach(ch, "client", conn)
                self._cleanup(name)
            return

        # server 已上线：转发首条（含归属）
        first_id = parse_req_id(first_msg)
        if first_id:
            ch["route"][first_id] = conn
        await self._send_safe(server, first_msg)

        try:
            async for msg in ws:
                self._touch(ch)
                self._touch_conn(conn)
                server = ch.get("server")
                if server:
                    req_id = parse_req_id(msg)
                    if req_id:
                        ch["route"][req_id] = conn
                    await self._send_safe(server, msg)
                    continue
                else:
                    # server 中途掉线 → 同样直接回错误，不积攒
                    await self._send_safe(ws, build_kanzi_offline_error(msg, name))
        except websockets.ConnectionClosed:
            pass
        finally:
            log.info(f"🔌 [{name}] Client 断开")
            self._detach(ch, "client", conn)
            self._cleanup(name)

    # ── NLP Client（聊天插件） ──

    async def _handle_nlp_client(self, ws, name: str):
        ch = self._ensure(name)
        ch["name"] = name
        conn, kicked = self._attach(ch, "nlp", ws)
        if kicked is not None:
            try:
                await kicked.close()
            except Exception:
                pass

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
                self._touch(ch)
                self._touch_conn(conn)
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
            self._detach(ch, "nlp", conn)
            self._cleanup(name)

    # ── NLP Worker（Claude 执行器） ──

    async def _handle_nlp_worker(self, ws, name: str):
        ch = self._ensure(name)
        ch["name"] = name
        conn, kicked = self._attach(ch, "nlp_worker", ws)
        if kicked is not None:
            try:
                await kicked.close()
            except Exception:
                pass

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
                self._touch(ch)
                self._touch_conn(conn)
                try:
                    data = json.loads(raw)
                    msg_type = data.get("type", "")
                    if msg_type == "mcp_request":
                        # MCP 请求转发给 Server
                        server = ch.get("server")
                        if server:
                            # 记录归属：定向回传
                            req_id = parse_req_id(data.get("text", raw))
                            if req_id:
                                ch["route"][req_id] = conn
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
            self._detach(ch, "nlp_worker", conn)
            await self._push_to_nlp(name, {
                "type": "worker_disconnected", "text": "Chat Worker 已断开"
            })
            self._cleanup(name)

    # ── 三层回收：空闲超时兜底 + 整通道闲置移除 ──

    async def _sweep_loop(self):
        while True:
            await asyncio.sleep(SWEEP_INTERVAL)
            try:
                now = time.time()
                for name, ch in list(self.channels.items()):
                    # 第二层：空闲超时回收单连接
                    # 注意：主通道(is_primary)的 server 连接是 Kanzi 插件核心，永不空闲回收——
                    # 否则 server 无请求空闲 120s 就被回收→反复断连→脚本请求丢失(之前日志 20:23/20:25 实锤)。
                    primary = ch.get("is_primary")
                    for slot, conns in ch["conns"].items():
                        for conn in conns[:]:
                            # 已由 _detach 移除的（removed 标记）→ 跳过，防重复移除竞态
                            if conn.get("removed"):
                                continue
                            # 核心槽（server/nlp_worker/nlp）永不空闲回收——它们必须一直保持连接；
                            # 只有 client 槽（脚本/http 短连接）才做空闲回收。
                            # 主通道 server 也不能回收（历史教训：空闲 120s 被回收→脚本请求丢失）。
                            if slot != "client":
                                continue
                            if now - conn["last_active"] > CONN_IDLE_TIMEOUT:
                                log.info(f"⏱ [{name}] {slot} 连接空闲超时回收")
                                try:
                                    await self._send_safe(conn["ws"], json.dumps({
                                        "type": "error",
                                        "text": "connection idle timeout, closing"
                                    }))
                                    await conn["ws"].close()
                                except Exception:
                                    pass
                                if conn in conns:
                                    conns.remove(conn)
                                    conn["removed"] = True
                                # 若回收的是主连接，主字段重指剩余
                                if conns:
                                    ch[slot] = conns[-1]["ws"]
                                else:
                                    ch[slot] = None
                                # 清理该连接遗留的 route 归属
                                for rid, t in list(ch["route"].items()):
                                    if t is conn:
                                        ch["route"].pop(rid, None)
                    # 第三层：整通道闲置移除 —— 仅非主通道（无 server 的临时/脚本通道）才回收
                    # 主通道（is_primary，曾有 Kanzi server 连接）永不整通道清理，只收里面空闲的单连接。
                    empty = not any(ch["conns"][s] for s in ch["conns"])
                    if (not ch["is_primary"]) and empty and now - ch["last_active"] > CHANNEL_IDLE_TIMEOUT:
                        self.channels.pop(name, None)
                        log.info(f"🗑️ 整通道闲置回收(非主): {name}")
            except Exception as e:
                log.warning(f"回收扫描异常: {e}")

    # ── 清理 ──

    def _cleanup(self, name: str):
        ch = self.channels.get(name)
        # 主通道（is_primary，曾有 server 连接）永不整通道清理 → 连接全断后保留通道结构，等 server 重连
        if ch and (not ch.get("is_primary")) and not any(ch["conns"][s] for s in ch["conns"]):
            # 非主通道：整通道无任何连接 → 立即可移除
            self.channels.pop(name, None)
            log.info(f"🗑️ 清理通道(非主): {name}")


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

    # 启动三层回收的后台扫描任务
    asyncio.get_event_loop().create_task(relay._sweep_loop())

    process_request = make_process_request(relay)

    async with websockets.serve(
        relay.handle, "0.0.0.0", port,
        process_request=process_request
    ):
        log.info(f"🔄 MCP 中继 ws://0.0.0.0:{port}")
        log.info(f"   路径区分通道: ws://ip:{port}/用户名")
        log.info(f"   Server:      ws://ip:{port}/用户名")
        log.info(f"   Client:      ws://ip:{port}/用户名（多连接并存, 定向回传）")
        log.info(f"   NLP Client:  ws://ip:{port}/用户名  (聊天插件)")
        log.info(f"   NLP Worker:  ws://ip:{port}/用户名  (Claude 执行器)")
        log.info(f"   ♻️ 回收: 断开即收 + 空闲{CONN_IDLE_TIMEOUT}s + 整通道闲置{CHANNEL_IDLE_TIMEOUT}s")
        await asyncio.Future()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        log.info("已停止")
    except Exception as e:
        log.error(f"启动失败: {e}")
        sys.exit(1)
