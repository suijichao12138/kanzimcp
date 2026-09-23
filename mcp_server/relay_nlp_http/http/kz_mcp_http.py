#!/usr/bin/env python3
"""
kz_mcp_http.py — 单进程多用户 Kanzi MCP over HTTP (streamable HTTP) 服务器

一个常驻进程 + 一个 HTTP 端口, 服务所有用户。每个用户对应一个 relay 通道(一台 Kanzi)
和一个 client 槽连接。用户通过 HTTP header 指定, 且必须在内置的白名单配置里。

解决的问题: copilot --acp 只支持 http/sse 传输的 MCP(不支持 stdio), 需要一个
HTTP MCP server 把 copilot 的 MCP 请求桥接到 relay → 对应 Kanzi。

角色: 每个用户一条到 relay_multi 的 **client** 槽连接(与 server 双向直通, 裸 MCP JSON-RPC)。
      client 槽独立于 nlp_worker 槽, 可与 nlp_worker_acp.py 并存同一通道而不互踢。

安全/权限模型:
  - 通道(用户)由白名单配置决定, 只有名单内用户可以连
  - copilot 请求带 HTTP header: X-Kanzi-User: <用户名>
  - 名单外或未带 header 的请求直接拒绝(403)
  - 这样其他人无法自建用户/连别的 Kanzi

用法:
  # 1. 先写白名单配置 users.json:
  #    { "users": ["suijichao", "lisi"] }
  # 2. 启动(常驻, 不需 Kanzi server 已启动; 连某用户时才要求该 Kanzi 在线):
  #    listen 用 0.0.0.0:9001 让远程 copilot/nlp_worker 也能通过 <本机IP>:9001 连进来
  python kz_mcp_http.py --relay-base ws://127.0.0.1:58080 --users users.json --listen 0.0.0.0:9001
  # 3. copilot 里配(header 带用户名):
  copilot --additional-mcp-config '{"mcpServers":{"kanzi":{"type":"http","url":"http://127.0.0.1:9001/mcp","headers":{"X-Kanzi-User":"suijichao"}}}}'

依赖: pip install websockets
"""
import argparse
import asyncio
import json
import logging
import os
import sys
import time
import uuid

# 日志文件轮转(组件自己管, 不依赖外部程序)
from logging.handlers import RotatingFileHandler

# 官方 Kanzi MCP 客户端(api/doc) —— 供本进程聚合网关做三端点代理
from official_mcp import (
    OfficialMcpHttpClient,
    KANZI_API_MCP_URL,
    KANZI_DOC_MCP_URL,
)

try:
    import websockets
except ImportError:
    websockets = None

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger("kz-mcp-http")


def setup_file_log(path: str, max_bytes: int = 10 * 1024 * 1024, backup_count: int = 5):
    """追加 RotatingFileHandler。日志文件由本进程自己轮转, 无需外部停进程。
    max_bytes 满时自动切分为 path.1/.2..., 全程不中断服务。"""
    if not path:
        return
    try:
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        fh = RotatingFileHandler(path, maxBytes=max_bytes,
                                 backupCount=backup_count, encoding="utf-8")
        fh.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
        logging.getLogger().addHandler(fh)
        log.info(f"📄 文件日志已启用: {path} (max {max_bytes}B × {backup_count})")
    except Exception as e:
        log.warning(f"文件日志启用失败({path}): {e}")


# ═══════════════════════════════════════════════════════════════════
#  白名单配置
# ═══════════════════════════════════════════════════════════════════
def load_users(config_path: str) -> set:
    """从 JSON 配置文件读取白名单用户集合。"""
    with open(config_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    users = data.get("users", [])
    if not isinstance(users, list):
        raise ValueError("users 配置必须是数组")
    return set(str(u).strip() for u in users if str(u).strip())


# ═══════════════════════════════════════════════════════════════════
#  Relay 客户端 (单用户, client 槽位)
# ═══════════════════════════════════════════════════════════════════
class RelayClient:
    """管理到中继的 WebSocket 连接, 角色 = client (外部 MCP 客户端)

    每个用户一条连接(懒加载, 后续请求复用), URL = <relay_base>/<username>。
    Kanzi server 未启动时 relay 不再拒连(历史版本曾用 4001 拒连, 现已改为连接保持 +
    请求直接回错误), 因此下方的 4001 分支仅为兼容旧版中继保留。
    """

    def __init__(self, relay_url: str, username: str):
        self.relay_url = relay_url
        self.username = username
        self.ws = None
        self.running = False
        self.on_message = None  # 回调: func(raw_msg_str)
        self.on_link_down = None  # 回调: func() —— 连接断开/被替换时调用(用于 fail all pending)
        self.on_link_up = None    # 回调: func() —— 连接成功建立时调用

    async def start(self):
        self.running = True
        # 关键修复: _connect_loop 会一直挂在 `async for raw in ws` 等待消息,
        # 直接 await 会让调用方(如 tools/list 首次懒加载建连)永久阻塞,
        # HTTP 请求永不返回 → copilot 挂 MCP 时 CPU 0% 卡死。
        # 改为后台任务启动, 立即返回, 由事件循环调度连接与重连。
        self._task = asyncio.create_task(self._connect_loop())

    async def wait_connected(self, timeout: float = 10.0) -> bool:
        """等待 client 槽真正连上中继(与 Kanzi server 建立直连)。"""
        loop = asyncio.get_event_loop()
        deadline = loop.time() + timeout
        while loop.time() < deadline:
            if self.ws and getattr(self.ws, "state", None) and self.ws.state.name == "OPEN":
                return True
            await asyncio.sleep(0.2)
        return bool(self.ws)

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
                        "role": "client",
                        "name": self.username
                    }))
                    log.info(f"✅ [{self.username}] 已连接中继(client): {self.relay_url}")
                    if self.on_link_up:
                        try:
                            await self.on_link_up()
                        except Exception as e:
                            log.warning(f"[{self.username}] on_link_up 回调异常: {e}")

                    async for raw in ws:
                        if self.on_message:
                            await self.on_message(raw)

                # async for 循环正常退出(连接关闭) → 通知链路断开
                if self.on_link_down:
                    try:
                        await self.on_link_down()
                    except Exception as e:
                        log.warning(f"[{self.username}] on_link_down 回调异常: {e}")

            except websockets.ConnectionClosed as e:
                if e.code == 4001:
                    # 兼容旧版中继(现已改为连接保持 + 请求回错误, 不再发 4001)
                    log.warning(f"🔌 [{self.username}] server 不在线, 5秒后重试...")
                else:
                    log.warning(f"🔌 [{self.username}] 中继连接断开, 3秒后重连...")
            except Exception as e:
                log.error(f"❌ [{self.username}] 连接错误: {e}")
                if self.on_link_down:
                    try:
                        await self.on_link_down()
                    except Exception as e2:
                        log.warning(f"[{self.username}] on_link_down 回调异常: {e2}")

            if self.running:
                await asyncio.sleep(3 if self.ws else 5)

    async def send(self, msg: dict):
        if self.ws:
            try:
                await self.ws.send(json.dumps(msg, ensure_ascii=False))
            except Exception as e:
                log.warning(f"[{self.username}] 发送失败: {e}")

    async def stop(self):
        self.running = False
        if getattr(self, "_task", None):
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            except Exception:
                pass
        if self.ws:
            try:
                await self.ws.close()
            except Exception:
                pass


class McpProxyHandler:
    """单用户的 MCP 请求代理: 裸 JSON-RPC 经 client 槽转发到 Kanzi server。
    ★ 喂狗机制(http 侧发起): 后台定期并行探测 kz_health, 插件返回执行状态
      {ok, busy, active_request_id}; 据此动态判定每个 pending 该等还是秒级 fail。
      * 插件 active_request_id==我 → 在执行 → 继续等(不误杀长动作)
      * 插件 active_request_id==别的 → 我在排队 → 继续等
      * 插件空闲(null) 且我没收到响应 → 请求丢了 → fail(秒级, copilot 重试)
      * 喂狗连续 N 次无响应(链路坏) → fail 所有 pending + 自动重连
    """

    # 喂狗/动态判定配置
    HB_INTERVAL = 5       # 喂狗(kz_health)间隔 秒
    HB_MAX_FAILS = 3      # 连续 N 次无响应 ⇒ 判链路坏
    REQ_CHECK_INTERVAL = 2  # 单个 pending 周期检查间隔 秒
    IDLE_GRACE_ROUNDS = 3   # active_req 为空时的宽容观察轮数(给插件回填留时间, 防误杀脚本请求)

    def __init__(self, relay: RelayClient, username: str, request_timeout=300.0,
                 hb_interval=None, hb_max_fails=None, req_check=None):
        self.relay = relay
        self.username = username
        self.request_timeout = request_timeout
        # 喂狗参数: 实例级优先, 缺省用类常量
        self.HB_INTERVAL = hb_interval if hb_interval else self.HB_INTERVAL
        self.HB_MAX_FAILS = hb_max_fails if hb_max_fails else self.HB_MAX_FAILS
        self.REQ_CHECK_INTERVAL = req_check if req_check else self.REQ_CHECK_INTERVAL
        self.pending = {}
        self._lock = asyncio.Lock()
        # 喂狗状态(每用户独立)
        self._hb_task = None
        self._hb_fail_count = 0      # 连续无响应计数(0=最近一次探活成功)
        self._active_req = None      # 插件当前执行中的请求 id(kz_health 回填)
        self._idle_empty_rounds = {}  # 各请求在 active_req 为空状态下的连续观察轮数
        self._hb_locked = False      # 喂狗自身占信道的锁(避免和业务请求抢)
        # 链路断开回调 → fail 所有 pending(自愈关键)
        self.relay.on_link_down = self._on_link_down
        self.relay.on_link_up = self._on_link_up

    # ── 喂狗任务启停 ──
    def start_heartbeat(self):
        if self._hb_task is None or self._hb_task.done():
            self._hb_task = asyncio.get_event_loop().create_task(self._heartbeat_loop())

    def stop_heartbeat(self):
        if self._hb_task:
            self._hb_task.cancel()
            self._hb_task = None

    async def _heartbeat_loop(self):
        """后台喂狗: 定期发 kz_health 探活, 更新 active_req/链路状态。
        注意: kz_health 必须并行独立响应、不排业务请求队列(插件侧保证),
        否则长动作会卡住探活、误判链路坏。"""
        while True:
            try:
                await asyncio.sleep(self.HB_INTERVAL)
                # 探活请求(短超时)
                hb_id = f"hb-{uuid.uuid4().hex}"
                resp = await self.relay_request(
                    {"jsonrpc": "2.0", "id": hb_id, "method": "tools/call",
                     "params": {"name": "kz_health", "arguments": {}}},
                    timeout=min(self.HB_INTERVAL, 4.0))
                # 解析插件返回的执行状态
                self._parse_health(resp)
                # 探活成功 → 清零连续失败
                self._hb_fail_count = 0
            except Exception as e:
                # 探活自身失败(超时/无响应) → 连续失败计数+1
                self._hb_fail_count += 1
                log.warning(f"💗 [{self.username}] 喂狗无响应 ({self._hb_fail_count}/{self.HB_MAX_FAILS}): {e}")
                if self._hb_fail_count >= self.HB_MAX_FAILS:
                    # 链路坏 → fail 所有 pending(不干等), 触发 relay 重连
                    log.error(f"🚨 [{self.username}] 喂狗连续 {self.HB_MAX_FAILS} 次无响应 → 判链路坏, fail 所有 pending")
                    await self.fail_all_pending("链路断(喂狗连续无响应)")

    def _parse_health(self, resp):
        """从 kz_health 返回里提取 busy / active_request_id。"""
        try:
            if not isinstance(resp, dict):
                return
            # 可能直接 result.busy / result.active_request_id, 或 result.content[].text 里
            r = resp.get("result")
            if isinstance(r, dict):
                if "activeRequestId" in r:
                    self._active_req = r.get("activeRequestId")
                elif "active_request_id" in r:
                    self._active_req = r.get("active_request_id")
                # busy 若存在而 no active id → 插件在跑未知请求, 保守不 fail
            elif isinstance(r, dict) and isinstance(r.get("content"), list):
                txt = " ".join(c.get("text", "") for c in r["content"] if isinstance(c, dict))
                # 简单解析文本里的 active_request_id:  xxx
                import re as _re
                m = _re.search(r"active[_\-]?request[_\-]?id[\s:=\s]*([A-Za-z0-9\-_]+)", txt)
                if m:
                    self._active_req = m.group(1)
        except Exception:
            pass

    # ── 链路状态回调 ──
    async def _on_link_down(self):
        """连接断开/被替换 → fail 所有 pending(立刻报错, 不干等 300s)。
        copilot 收到错误后重试, 此时连接已重建、重试必成。"""
        log.warning(f"🔌 [{self.username}] 链路断开 → fail 所有 pending")
        await self.fail_all_pending("链路断开(连接被替换/掉落)")

    async def _on_link_up(self):
        """连接重新建立 → 喂狗计数清零, 等待新链路接管。"""
        log.info(f"🔗 [{self.username}] 链路已重建")
        self._hb_fail_count = 0

    async def fail_all_pending(self, reason: str):
        """fail 该用户所有 pending(立刻返回错误)。"""
        async with self._lock:
            items = list(self.pending.items())
            for req_id, fut in items:
                if not fut.done():
                    fut.set_result({
                        "jsonrpc": "2.0", "id": req_id,
                        "error": {"code": -32000, "message": f"MCP 请求失败: {reason}"}
                    })

    async def relay_request(self, req: dict, timeout=None) -> dict:
        if timeout is None:
            timeout = self.request_timeout
        req_id = str(req.get("id"))
        req_id = str(req.get("id"))
        fut = asyncio.get_event_loop().create_future()
        async with self._lock:
            self.pending[req_id] = fut
        # 是否探活请求(短超时, 不进动态判定的业务判定)
        is_health = req.get("params", {}).get("name") == "kz_health"
        try:
            if not self.relay.ws:
                return {"jsonrpc": "2.0", "id": req_id,
                        "error": {"code": -32000,
                                  "message": f"用户 {self.username} 的 Kanzi 未连接(server 可能未启动)"}}
            await self.relay.send(req)

            if is_health:
                # 探活: 固定短超时, 不参与动态判定
                try:
                    return await asyncio.wait_for(fut, timeout=timeout)
                except asyncio.TimeoutError:
                    return None
            # 业务请求: 固定兜底超时 + 周期动态判定
            try:
                done, _ = await asyncio.wait(
                    [fut, asyncio.get_event_loop().create_task(self._watch_req(req_id))],
                    timeout=timeout, return_when=asyncio.FIRST_COMPLETED)
            except asyncio.TimeoutError:
                done = None
            if not done:
                return {"jsonrpc": "2.0", "id": req_id,
                        "error": {"code": -32000, "message": "MCP 请求超时(兜底)"}}
            # fut 完成
            for t in done:
                if t is fut and not fut.done():
                    fut.set_result({"jsonrpc":"2.0","id":req_id,
                                    "error":{"code":-32000,"message":"MCP 请求超时"}})
                if getattr(t, "cancel", None):
                    t.cancel()
            if fut.done():
                return fut.result()
            return {"jsonrpc": "2.0", "id": req_id,
                    "error": {"code": -32000, "message": "MCP 请求超时"}}
        finally:
            async with self._lock:
                self.pending.pop(req_id, None)

    async def _watch_req(self, req_id: str):
        """单个 pending 的周期检查: 判定它该等还是秒级 fail。
        规则(插件串行, 全局 active_req 即可判):
          - active_req == 我        → 插件在执行 → 等(不误杀)
          - active_req == 别的      → 我在排队   → 等
          - active_req == None 且未收到响应 → 请求丢了/插件空闲 → 秒级 fail(让 copilot 重试)
        """
        while True:
            await asyncio.sleep(self.REQ_CHECK_INTERVAL)
            async with self._lock:
                fut = self.pending.get(req_id)
                if fut is None or fut.done():
                    return  # 已收响应/已 fail, 结束
            # 链路断(喂狗判定) → 该请求已被 fail_all, 这里只需等 fut 完成
            ar = self._active_req
            if ar is None:
                # 插件空闲: 不再第一次就 sec级 fail。脚本/Kanzi 收到请求后 active_request_id
                # 由 kz_health 周期回填(有间隔延迟), 可能暂时还是 None。
                # 采用“连续多轮观察仍为空才 fail”的宽容窗口, 给插件回填留时间, 避免误杀脚本请求。
                self._idle_empty_rounds[req_id] = self._idle_empty_rounds.get(req_id, 0) + 1
                if (self._idle_empty_rounds[req_id] >= self.IDLE_GRACE_ROUNDS
                        and self._hb_fail_count < self.HB_MAX_FAILS):
                    async with self._lock:
                        fut2 = self.pending.get(req_id)
                        if fut2 and not fut2.done():
                            log.warning(f"⚠️ [{self.username}] 请求 {req_id} 插件空闲连续{self._idle_empty_rounds[req_id]}轮未响应 → fail(重试)")
                            fut2.set_result({
                                "jsonrpc": "2.0", "id": req_id,
                                "error": {"code": -32000,
                                           "message": "MCP 请求丢失(插件空闲未收到), 请重试"}
                            })
                            return
            else:
                # active_req 有值(我在执行或排队) → 插件忙, 清掉空观察计数, 继续等
                self._idle_empty_rounds.pop(req_id, None)
            # 继续等; 下一轮再看

        # 注: 链路坏由喂狗(fail_all_pending)处理, 与这里的宽容窗口无关, 不受影响。

    async def handle_mcp_response(self, raw: str):
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            return
        if isinstance(data, dict) and data.get("type") == "mcp_response":
            try:
                response = json.loads(data.get("text", "{}"))
            except json.JSONDecodeError:
                return
        elif isinstance(data, dict) and "id" in data:
            response = data
        else:
            return
        req_id = str(response.get("id"))
        async with self._lock:
            fut = self.pending.get(req_id)
            # ★ 方案B 兜底(兼容旧插件): 插件回包 id 可能恒为 -1/-1.0/None(字符串 id 被按整数解析),
            #   此时按 id 配不上 → 退回 FIFO(最早未完成的 pending), 保证结果不丢。
            #   代价: 多请求并发时可能按到达顺序配对(顺序不保证精确)。
            #   根治办法是插件端原样透传 id(方案A); 两者同时生效时不会走到这里。
            if not (fut and not fut.done()):
                if req_id in ("-1", "-1.0", "None", "none", "null"):
                    for _rid, _f in list(self.pending.items()):
                        if not _f.done():
                            log.info(f"↩ [{self.username}] 回包 id={req_id} 配不上 → FIFO 兜底配给请求 {_rid}")
                            _f.set_result(response)
                            return
                    log.warning(f"⚠️ [{self.username}] 回包 id={req_id} 配不上且无 pending 可配 → 丢弃")
                return
            fut.set_result(response)


# ═══════════════════════════════════════════════════════════════════
#  用户连接管理器 (懒加载: 来请求才建连)
# ═══════════════════════════════════════════════════════════════════
class UserManager:
    """按用户名管理(懒加载)各用户的 RelayClient + McpProxyHandler。
    白名单外的用户名一律拒绝。

    ★ 白名单热更新: 每次校验前检查 users.json 的 mtime, 变了就重新读。
      改/增用户无需重启 kz_mcp_http.py 和 nlp_worker, 保存文件后下个请求即生效。
    """

    def __init__(self, relay_base: str, allowed_users: set, request_timeout=300.0,
                 config_path: str = None, hb_interval=5, hb_max_fails=3, req_check=2):
        self.relay_base = relay_base.rstrip("/")
        self.request_timeout = request_timeout
        self.hb_interval = hb_interval       # 喂狗(kz_health)间隔
        self.hb_max_fails = hb_max_fails     # 连续无响应判坏阈值
        self.req_check = req_check           # 单请求周期检查间隔
        self._config_path = config_path
        self._last_mtime = None
        self.allowed = allowed_users
        # 记录初始 mtime, 保证首次 _reload 不重复读
        if config_path:
            try:
                self._last_mtime = os.path.getmtime(config_path)
            except OSError:
                pass
        self.connections = {}   # user -> [ (RelayClient, McpProxyHandler) ]
                                # 每用户一条稳定连接(喂狗+业务共用), 懒加载、后续请求复用。
                                # '脚本独立'靠 relay 通道隔离实现: 脚本用不同 X-Kanzi-User
                                # = 不同通道, 不依赖这里开多连接。

    def _reload(self) -> bool:
        """重读白名单文件, 返回是否真的有变化。文件缺失/损坏时保留旧名单不崩溃。"""
        if not self._config_path:
            return False
        try:
            new_allowed = load_users(self._config_path)
        except Exception as e:
            log.warning(f"⚠ 重读白名单失败, 保留现名单: {e}")
            return False
        if new_allowed == self.allowed:
            return False
        old = sorted(self.allowed)
        self.allowed = new_allowed
        add = new_allowed - set(old)
        rm = set(old) - new_allowed
        if add:
            log.info(f"➕ 白名单新增用户(热更新, 无需重启): {sorted(add)}")
        if rm:
            log.info(f"➖ 白名单移除用户(热更新): {sorted(rm)}")
        # 新用户没启动过连接则维持懒加载; 被移除用户的全部连接停止释放
        for u in rm:
            conns = self.connections.pop(u, None)
            if conns:
                for relay, _ in conns:
                    asyncio.get_event_loop().create_task(self._safe_stop(relay))
        return True

    async def _safe_stop(self, relay):
        try:
            await relay.stop()
        except Exception:
            pass

    def refresh_if_changed(self):
        """检查 users.json mtime, 变了就热更新白名单。每次请求校验前调用。"""
        if not self._config_path:
            return
        try:
            mtime = os.path.getmtime(self._config_path)
        except OSError:
            return
        if self._last_mtime is None or mtime != self._last_mtime:
            self._last_mtime = mtime
            self._reload()

    def is_allowed(self, username: str) -> bool:
        self.refresh_if_changed()
        return username in self.allowed

    def _ensure(self, username: str) -> list:
        """返回该用户的连接列表。
        每用户保持**一条稳定连接**(喂狗+业务共用), 这样才能让喂狗探活回填 _active_req;
        若每请求新建连接, 新 handler 的喂狗还未回填就把请求判死(实测: 所有请求误杀)。
        'copilot 站住 + 脚本独立' 靠 relay 通道隔离实现(不同 X-Kanzi-User = 不同通道)。
        返回列表形式仅为了兼容调用方, 实际只有一条。"""
        conns = self.connections.get(username)
        if not conns:
            url = f"{self.relay_base}/{username}"
            relay = RelayClient(url, username)
            handler = McpProxyHandler(relay, username, self.request_timeout,
                                      hb_interval=self.hb_interval,
                                      hb_max_fails=self.hb_max_fails,
                                      req_check=self.req_check)
            relay.on_message = handler.handle_mcp_response
            self.connections[username] = [(relay, handler)]
        return self.connections[username]

    async def start_user(self, username: str):
        """启动该用户的稳定连接(未启动则启动), 返回 (relay, handler)。"""
        conns = self._ensure(username)
        relay, _ = conns[-1]
        if not relay.running:
            await relay.start()
            # 连接启动后才需要喂狗回填; _ensure 时未启动则不启(避免无谓任务)
            conns[-1][1].start_heartbeat()
        return conns[-1]

    def get_handler(self, username: str):
        """返回该用户的 handler(单条稳定连接)。"""
        return self._ensure(username)[-1][1]

    async def stop_all(self):
        for relay, handler in self.connections.values():
            try:
                handler.stop_heartbeat()
            except Exception:
                pass
            await relay.stop()


# ═══════════════════════════════════════════════════════════════════
#  HTTP MCP Server (streamable HTTP) — 多用户路由
# ═══════════════════════════════════════════════════════════════════
class HttpMcpServer:
    """一个 HTTP 端口, 从 header X-Kanzi-User 取用户, 校验白名单后路由到对应 client。"""

    # Kanzi 端插件(当前 v13) 完整工具集。tools/call 原样转发给 Kanzi server, 这里 TOOLS 是
    # tools/list 的(兜底)工具清单: 插件在线时优先返回插件自身工具(以 tools/list 实际注册为准), 插件离线/不可用时
    # 用本表, 保证 agent 始终能看到完整可调用的工具。参数 schema 由 2026-08-19 插件 tools/list 实测生成。
    TOOLS = [
        {"name": "kz_health", "description": "检查 Kanzi Studio 插件连接状态和当前工程信息", "inputSchema": {"type": "object", "properties": {}}},
        {"name": "kz_list_projects", "description": "V12多工程：列出所有已打开的工程（含 ActiveProject/Primary 标记）。不切换当前工程。", "inputSchema": {"type": "object", "properties": {}}},
        {"name": "kz_select_project", "description": "V12多工程：选择指定工程为『当前操作上下文』。之后所有基于 @project 的调用自动作用于该工程，且不切换 Kanzi Studio 的 ActiveProject。传入空字符串/省略则切回 ActiveProject。", "inputSchema": {"type": "object", "properties": {"name": {"type": "string", "description": "工程名（kz_list_projects 返回的 name）；空/省略=切回 ActiveProject"}}, "required": ["name"]}},
        {"name": "kz_invoke", "description": "通用反射调用：在任意 Kanzi Studio API 对象上调用任意方法。target 额外支持 @proj:<工程名>（指定工程对象）和 @proj:<工程名>/<路径>（指定工程内节点/项目项）", "inputSchema": {"type": "object", "properties": {"target": {"type": "string", "description": "调用目标。格式: @studio | @project | @projectItem | @obj1/@obj2 | @proj:<工程名>[/路径] | /节点路径"}, "method": {"type": "string", "description": "方法名"}, "args": {"type": "array", "description": "参数列表", "items": {}}}, "required": ["target", "method"]}},
        {"name": "kz_localized_resources", "description": "[V13] 读取本地化表里按 locale 使用的资源（字体等 NodeResource）。普通文本读 kz_invoke get_Translations 通道；这里读本地化资源通道（GetLocalizedResourceList）。target 传本地化表路径或 @obj 引用。返回每个资源（含 ref_id 可用于继续 kz_invoke）", "inputSchema": {"type": "object", "properties": {"target": {"type": "string", "description": "本地化表位置，如 /Localization/Localization Table 或 @obj 引用"}}, "required": ["target"]}},
        {"name": "kz_ref_properties", "description": "列出指定引用的所有可用属性", "inputSchema": {"type": "object", "properties": {"target": {"type": "string", "description": "对象引用ID，如 @obj1, @project, @studio"}}, "required": ["target"]}},
        {"name": "kz_ref_methods", "description": "列出指定引用的所有可用方法", "inputSchema": {"type": "object", "properties": {"target": {"type": "string", "description": "对象引用ID"}}, "required": ["target"]}},
        {"name": "kz_list_refs", "description": "列出当前对象引用缓存中的所有引用", "inputSchema": {"type": "object", "properties": {}}},
        {"name": "kz_create_node", "description": "创建 UI 节点", "inputSchema": {"type": "object", "properties": {"parent": {"type": "string", "description": "父节点路径"}, "type": {"type": "string", "description": "节点类型，如 Button2D, TextBlock2D"}, "name": {"type": "string", "description": "新节点名称"}}, "required": ["parent", "type", "name"]}},
        {"name": "kz_set_property", "description": "设置节点属性值", "inputSchema": {"type": "object", "properties": {"node_path": {"type": "string", "description": "节点路径"}, "property": {"type": "string", "description": "属性名"}, "value": {"type": "string", "description": "属性值"}}, "required": ["node_path", "property", "value"]}},
        {"name": "kz_get_property", "description": "获取节点属性值", "inputSchema": {"type": "object", "properties": {"node_path": {"type": "string", "description": "节点路径"}, "property": {"type": "string", "description": "属性名"}}, "required": ["node_path", "property"]}},
        {"name": "kz_delete_node", "description": "删除节点", "inputSchema": {"type": "object", "properties": {"node_path": {"type": "string", "description": "节点路径"}}, "required": ["node_path"]}},
        {"name": "kz_get_node_tree", "description": "获取工程节点树", "inputSchema": {"type": "object", "properties": {"root": {"type": "string", "description": "根节点路径（可选）"}}}},
        {"name": "kz_save_project", "description": "保存当前工程", "inputSchema": {"type": "object", "properties": {}}},
        {"name": "kz_loc_entry_list", "description": "列出本地化表所有条目（含 type/文本/引用）。不删表不重建，直接枚举。返回每个条目的 key、是否为文本/isText、引用信息，并注册 @obj 可继续 kz_invoke。", "inputSchema": {"type": "object", "properties": {"target": {"type": "string", "description": "LocalizationTable 对象引用或路径（如 /Localization/Localization 或 @objN）"}}, "required": ["target"]}},
        {"name": "kz_loc_entry_get", "description": "按 key(resourceName) 查本地化表单条目。返回 found/key/isText/引用。", "inputSchema": {"type": "object", "properties": {"target": {"type": "string", "description": "LocalizationTable 对象引用或路径"}, "key": {"type": "string", "description": "resourceName(Key)，只传这一个 key"}}, "required": ["target", "key"]}},
        {"name": "kz_loc_entry_add", "description": "新增本地化表单条目，支持一次多行，每行需指定 type（text|font|style|node）。纯 Add/SetOrCreate，不删表，字体/A引用天然保留。", "inputSchema": {"type": "object", "properties": {"target": {"type": "string", "description": "LocalizationTable 对象引用或路径"}, "rows": {"type": "array", "items": {"type": "object", "properties": {"resourceName": {"type": "string", "description": "键/resourceName（唯一）"}, "type": {"type": "string", "description": "条目类型：text(文本,默认) | font(字体) | style | node；非 text 需配 targetRef"}, "defaultText": {"type": "string", "description": "默认文本（text 类型）"}, "targetRef": {"type": "string", "description": "font/style/node 类型的资源引用（@objN 或路径）"}}, "required": ["resourceName"]}, "description": "多行数组"}}, "required": ["target", "rows"]}},
        {"name": "kz_loc_entry_set", "description": "修改本地化表单条目，支持一次多行。改 defaultText/type/引用。保留原条目不删改，字体/A引用保留。", "inputSchema": {"type": "object", "properties": {"target": {"type": "string", "description": "LocalizationTable 对象引用或路径"}, "rows": {"type": "array", "items": {"type": "object", "properties": {"resourceName": {"type": "string", "description": "键/resourceName"}, "type": {"type": "string", "description": "条目类型：text|font|style|node"}, "defaultText": {"type": "string", "description": "默认文本"}, "targetRef": {"type": "string", "description": "font/style/node 的资源引用"}}, "required": ["resourceName"]}, "description": "多行数组"}}, "required": ["target", "rows"]}},
        {"name": "kz_loc_entry_delete", "description": "删除本地化表单条目，支持一次多行。按 key 单个 Remove，不删整表，其余条目/字体引用保留。", "inputSchema": {"type": "object", "properties": {"target": {"type": "string", "description": "LocalizationTable 对象引用或路径"}, "keys": {"type": "array", "items": {"type": "string"}, "description": "要删除的 resourceName(Key) 数组"}}, "required": ["target", "keys"]}},
        {"name": "kz_loc_entry_delete_language", "description": "删除本地化表的一个语言（语言列）。等价 GUI 菜单删除 → Delete ProjectItem \".../Localization Table/<lang>\"，对 get_Locales 里匹配 lang 的 Locale 项目项调 Delete()。安全：只删完全匹配的那一个语言；找不到 lang 不删任何内容。target=本地化表路径或 @obj 引用，lang=语言码（缩写，如 de）。", "inputSchema": {"type": "object", "properties": {"target": {"type": "string", "description": "本地化表路径或 @obj 引用，如 /Localization/Localization Table"}, "lang": {"type": "string", "description": "要删除的语言码（缩写，如 de / fr / zh-CN）"}}, "required": ["target", "lang"]}},
        {"name": "kz_loc_entry_dump", "description": "诊断：列出拿到 entry 的内部对象的全部接口方法（含显式接口实现），用于找读翻译/文本的隐藏入口。只读元数据。", "inputSchema": {"type": "object", "properties": {"target": {"type": "string", "description": "LocalizationTable 对象引用或路径"}}, "required": ["target"]}},
        {"name": "kz_type_probe", "description": "只读诊断：按完整类型名探测一个类型是否能加载到 Studio 进程，并列出其构造函数和方法签名（不执行任何逻辑，不污染工程）。用于验证如 CreateLocaleCommandRecord 等命令记录是否可反射直调。", "inputSchema": {"type": "object", "properties": {"typeName": {"type": "string", "description": "完整类型名，如 Rightware.Kanzi.Tool.Logic.Project.ResourceLocalizationItems.CreateLocaleCommandRecord"}}, "required": ["typeName"]}},
        {"name": "kz_loc_entry_add_language", "description": "给本地化表新增一个语言（语言列）。走 CreateLocaleCommandRecord.CreateProjectItem（等价 GUI 菜单\"新建语言\"）。target=本地化表路径或 @obj 引用，lang=新语言码（缩写，如 de）。", "inputSchema": {"type": "object", "properties": {"target": {"type": "string", "description": "本地化表路径或 @obj 引用，如 /Localization/Localization Table"}, "lang": {"type": "string", "description": "新语言码（缩写，如 de / fr / zh-CN）"}}, "required": ["target", "lang"]}},
        {"name": "kz_loc_row_get", "description": "读本地化表单单行（按 key）。返回该行的 DefaultText + Translations（语言→值字典）。对文本行/字体行都适用，验证每种语言能读到什么。走 ExportTranslations。", "inputSchema": {"type": "object", "properties": {"target": {"type": "string", "description": "LocalizationTable 对象引用或路径"}, "key": {"type": "string", "description": "resourceName/key"}}, "required": ["target", "key"]}},
        {"name": "kz_loc_iface", "description": "通用诊断：在 target 的内部对象上调指定接口 getter 或 0 参接口方法（普通反射看不到的显式接口实现）。结果注册引用 + 枚举受限列表。可传 key 作为单参（如 GetEntry(key)）。", "inputSchema": {"type": "object", "properties": {"target": {"type": "string", "description": "LocalizationTable / Localization 库 / Locale 对象引用或路径"}, "method": {"type": "string", "description": "接口/类方法名，如 get_Locales / get_Entries / GetEntry / get_ResourceReference"}, "key": {"type": "string", "description": "可选；传给方法的单参数（用于 GetEntry(key) 等）"}}, "required": ["target", "method"]}},
        {"name": "kz_capture_screen", "description": "截取屏幕区域并返回 PNG 的 base64（用于 Preview/Studio 截图验证）。默认截整屏；可指定 x,y,width,height 区域。", "inputSchema": {"type": "object", "properties": {"x": {"type": "integer", "description": "左上角x（默认0）"}, "y": {"type": "integer", "description": "左上角y（默认0）"}, "width": {"type": "integer", "description": "宽（<=0则整屏）"}, "height": {"type": "integer", "description": "高（<=0则整屏）"}, "maxSide": {"type": "integer", "description": "缩放最大边（默认800，<=0保持原尺寸）"}}, "required": []}},
        {"name": "kz_enum_windows", "description": "用 user32.EnumWindows 枚举指定 PID 进程的所有顶层窗口（HWND、类名、可见性、矩形）。用于定位被 MCP 面板遮挡/不在前台的 Preview、Studio 窗口，Process.MainWindowHandle 在这种环境下常为0，EnumWindows 才可靠。", "inputSchema": {"type": "object", "properties": {"pid": {"type": "integer", "description": "目标进程 PID（如 KanziPreview 的 PID）"}}, "required": ["pid"]}},
        {"name": "kz_enum_all_windows", "description": "枚举系统中所有顶层窗口（无需 pid），每个带 pid/title/className/visible/坐标。用于直接找 Preview 或任意被拽出窗口的标题，不需要先拿进程 PID。", "inputSchema": {"type": "object", "properties": {}}},
        {"name": "kz_print_window", "description": "用 user32.PrintWindow 把指定 HWND 的窗口内容离屏渲染成 PNG(base64)。即使窗口被 MCP 面板遮挡/不在前台也能截到（不走屏幕像素）。hwnd 用 kz_enum_windows 拿到。对 OpenGL/DirectX 渲染(如 NVOpenGLPbuffer)可能抓不到 GPU 内容。", "inputSchema": {"type": "object", "properties": {"hwnd": {"type": "integer", "description": "窗口句柄（kz_enum_windows 返回的 hwnd）"}, "maxSide": {"type": "integer", "description": "缩放最大边（默认0不缩放）"}}, "required": ["hwnd"]}},
        {"name": "kz_screenshot_preview", "description": "一键截图 Preview；获取不到 Preview 窗口则截 Studio 主窗。不截主屏幕。内部自动判断：对 Studio 进程可见窗口 PrintWindow 试截，命中 Title/className 含 Preview 或内容最大的窗口优先。需传 Studio 进程 PID。", "inputSchema": {"type": "object", "properties": {"pid": {"type": "integer", "description": "KanziStudio 进程 PID"}, "maxSide": {"type": "integer", "description": "缩放最大边（默认1200）"}}, "required": ["pid"]}},
        {"name": "kz_modify_animation", "description": "给 Animation Data 加/改/删关键帧（驱动 Kanzi ModifyAnimationCommand，带撤销）。action：add(加帧) | modify(改帧，按 time 定位) | remove(删帧，按 time 定位)。keyframes 数组每项 { time(秒), value(动画属性值，数值/布尔/颜色均可), type?(LINEAR/STEP/BEZIER/HERMITE，默认LINEAR) }。animation 传目标动画路径或 @obj 引用。执行后返回中间对象 @obj 引用(parameterRef/modifiedDataRef/commandRecordRef/frames[].frameRef)，可继续用 kz_invoke 操作。", "inputSchema": {"type": "object", "properties": {"animation": {"type": "string", "description": "目标 Animation Data 路径或 @obj 引用（AnimationPluginWrapper）"}, "action": {"type": "string", "description": "操作：add(加帧) | modify(改帧) | remove(删帧)"}, "keyframes": {"type": "array", "items": {"type": "object", "properties": {"time": {"type": "number", "description": "关键帧时间（秒）"}, "value": {"type": "string", "description": "关键帧值（数值/布尔/颜色#RRGGBB）"}, "type": {"type": "string", "description": "插值类型：LINEAR/STEP/BEZIER/HERMITE（默认LINEAR）"}}, "required": ["time", "value"]}, "description": "关键帧数组（[ { time, value, type? } ]）"}}, "required": ["animation", "action", "keyframes"]}},

    ]

    # HTTP header 里用户名取值(小写)
    USER_HEADER = "x-kanzi-user"

    # 大批量结果外置配置（默认值，可被命令行参数覆盖后经 set_result_offload 注入）
    RESULT_TMP_DIR = None          # 落盘目录（绝对/相对路径）；None = 用 cwd/tmp_results
    RESULT_THRESHOLD_ENTRIES = 50  # 记录数 > 此值才外置
    RESULT_THRESHOLD_BYTES = 4096  # 文本大小 > 此值(字节)才外置
    RESULT_TTL_SECONDS = 1800      # 临时文件存活秒数(30分钟)
    RESULT_SWEEP_SECONDS = 1800    # 清理任务扫描间隔
    RESULT_SUMMARY_COUNT = 8       # 摘要(前 N 项)条数
    RESULT_SUMMARY_CHARS = 120     # 摘要单条截断字符数

    def __init__(self, user_manager: UserManager, host="127.0.0.1", port=9001, url_path="/mcp"):
        self.users = user_manager
        self.host = host
        self.port = port
        self.url_path = url_path
        self.server = None
        self._tmp_dir = None
        self._result_url_base = None
        self._sweep_task = None
        self.set_result_offload(None, None)
        # ★ 官方 Kanzi MCP 客户端(api/doc): 作为三端点聚合代理的后端, 失效自动重连
        self.kanzi_api = OfficialMcpHttpClient("kanzi-api-mcp", KANZI_API_MCP_URL)
        # ★ doc 官方端点 session 极短/校验极严(实测比 api 易失效), 每次调用前强制
        #   重新 initialize 拿新 sid, 从源头避免复用过期 sid 持续 404 导致调用被中断。
        self.kanzi_doc = OfficialMcpHttpClient("kanzi-doc-mcp", KANZI_DOC_MCP_URL, fresh_each_call=True)
        # 官方路径 → 客户端映射
        self.OFFICIAL_ENDPOINTS = {
            "/kanzi_api_mcp": (self.kanzi_api, "kanzi-api"),
            "/kanzi_doc_mcp": (self.kanzi_doc, "kanzi-doc"),
        }

    # ═══════════ 大批量结果外置（2026-09-02 老隋定稿）═══════════
    def set_result_offload(self, tmp_dir=None, ttl=None, public_host=None):
        """注入外置配置（main() 从命令行参数调用）。
        tmp_dir: 落盘目录（None=用 <cwd>/tmp_results）；ttl: 存活秒数；
        public_host: 文件 URL 里对 AI 可达的中继机 IP（None=用 self.host，
        注意若监听用 0.0.0.0 则 AI 连不回，跨机时须显式配真实 IP，参考 feishu_bridge http_bind_ip）。"""
        _tmp = tmp_dir or self.RESULT_TMP_DIR or os.path.join(os.getcwd(), "tmp_results")
        self._tmp_dir = os.path.abspath(_tmp)
        os.makedirs(self._tmp_dir, exist_ok=True)
        self._result_ttl = ttl if ttl is not None else self.RESULT_TTL_SECONDS
        _host = public_host if public_host else self.host
        self._result_url_base = f"http://{_host}:{self.port}/data"
        if _host in ("0.0.0.0", "127.0.0.1", "::", "localhost"):
            log.warning(f"⚠️ 结果外置 URL 用的 host={_host!r} 可能不能被远端 AI 访问；"
                        f"若 AI 与中继不在同一机器，请用 --result-public-host 指定真实中继机 IP")
        log.info(f"📦 大批量结果外置已启用: 目录={self._tmp_dir} TTL={self._result_ttl}s "
                 f"阈值={self.RESULT_THRESHOLD_ENTRIES}条/{self.RESULT_THRESHOLD_BYTES}B 摘要前{self.RESULT_SUMMARY_COUNT}项")

    def _resolve_tmp_path(self, res_id: str):
        """临时文件路径。文件名只用 res_id 的散列，防止超长/非法字符。"""
        import hashlib
        h = hashlib.sha256(res_id.encode("utf-8")).hexdigest()[:16]
        return os.path.join(self._tmp_dir, f"{h}.json")

    @staticmethod
    def _count_entries(text: str) -> int:
        """从 MCP 返回文本里粗估记录数（估算，用于阈值判断与摘要展示）。
        行数与 '▪'/'·' 或列出项数取近似。"""
        lines = [l for l in text.split("\n") if l.strip()]
        if not lines:
            return 0
        # 计算缩进层级为顶层的行（无前导空格/制表符的）作条目数近似
        top = sum(1 for l in lines if not l[:1].isspace())
        return max(top, 0)

    def _make_summary(self, text: str, count: int) -> str:
        """从文本摘取前 N 条供返回摘要。"""
        lines = [l for l in text.split("\n") if l.strip()]
        keep = []
        for l in lines:
            # 略过纯装饰行（▪ / · / 分隔 / 等）只保留实质内容
            s = l.strip().lstrip("▪·-• ")
            if not s or s.startswith("共") or s.startswith("..."):
                continue
            keep.append(s[:self.RESULT_SUMMARY_CHARS])
            if len(keep) >= self.RESULT_SUMMARY_COUNT:
                break
        return ", ".join(keep) if keep else "(无法摘要)"

    def _offload_result(self, res_id: str, mcp_text: str) -> dict:
        """把大结果落盘成 UTF-8 JSON 文件，返回外置信息（不含文件内容本身）。
        文件内容 = MCP 响应的 text（UTF-8 JSON 字符串）。"""
        path = self._resolve_tmp_path(res_id)
        # 落盘：UTF-8 JSON
        payload = {
            "id": res_id,
            "created": int(time.time()),
            "entries": self._count_entries(mcp_text),
            "text": mcp_text,
        }
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(payload, f, ensure_ascii=False)
        except Exception as e:
            log.error(f"📦 落盘失败: {e}")
            return None
        size = os.path.getsize(path)
        return {
            "url": f"{self._result_url_base}/{os.path.basename(path)}",
            "size": size,
            "entries": payload["entries"],
            "summary": self._make_summary(mcp_text, payload["entries"]),
        }

    def _should_offload(self, mcp_text: str) -> bool:
        """判断是否超过阈值该外置。>N条 或 >B字节。"""
        if not mcp_text:
            return False
        if len(mcp_text.encode("utf-8")) > self.RESULT_THRESHOLD_BYTES:
            return True
        return self._count_entries(mcp_text) > self.RESULT_THRESHOLD_ENTRIES

    async def _sweep_old(self):
        """定时清理过期临时文件。"""
        while True:
            try:
                now = time.time()
                if self._tmp_dir and os.path.isdir(self._tmp_dir):
                    removed = 0
                    for fn in os.listdir(self._tmp_dir):
                        if not fn.endswith(".json"):
                            continue
                        fp = os.path.join(self._tmp_dir, fn)
                        try:
                            if now - os.path.getmtime(fp) > self._result_ttl:
                                os.remove(fp)
                                removed += 1
                        except OSError:
                            continue
                    if removed:
                        log.info(f"🗑️ 清理批量结果临时文件 {removed} 个")
            except Exception as e:
                log.warning(f"🗑️ 清理任务异常: {e}")
            await asyncio.sleep(self.RESULT_SWEEP_SECONDS)

    async def start_sweep(self):
        if self._sweep_task is None:
            self._sweep_task = asyncio.ensure_future(self._sweep_old())

    async def _handle_data_get(self, path_norm: str, writer):
        """GET /data/<filename>：下发外置结果文件（UTF-8 JSON）。"""
        prefix = "/data/"
        if not path_norm.startswith(prefix):
            return False
        fn = path_norm[len(prefix):]
        # 只允许 .json 且不带路径分隔，防止目录穿越
        if not fn or not fn.endswith(".json") or "/" in fn or "\\" in fn or ".." in fn:
            await self._send_http(writer, 400, "text/plain", "Bad filename")
            return True
        fp = os.path.join(self._tmp_dir, fn) if self._tmp_dir else None
        if fp and os.path.isfile(fp):
            try:
                with open(fp, "r", encoding="utf-8") as f:
                    body = f.read()
                await self._send_http(writer, 200, "application/json; charset=utf-8", body)
            except Exception as e:
                log.error(f"📄 读取结果文件失败 {fn}: {e}")
                await self._send_http(writer, 500, "text/plain", "read fail")
        else:
            await self._send_http(writer, 404, "text/plain", "not found/expired")
        return True

    async def start(self):
        self.server = await asyncio.start_server(self._handle_conn, self.host, self.port)
        log.info(f"🌐 HTTP MCP Server 已启动: http://{self.host}:{self.port}{self.url_path}")
        log.info(f"   三端点聚合: 本地 studio({self.url_path}/) + 官方 api(/kanzi_api_mcp) + doc(/kanzi_doc_mcp)")
        log.info(f"   白名单用户: {sorted(self.users.allowed)}")
        return self.server

    async def _handle_conn(self, reader, writer):
        try:
            request_line = await reader.readline()
            if not request_line:
                writer.close()
                return
            parts = request_line.decode("utf-8", "replace").strip().split(" ")
            if len(parts) < 2:
                writer.close()
                return
            method = parts[0]
            path = parts[1]

            headers = {}
            while True:
                line = await reader.readline()
                if line in (b"\r\n", b"\n", b""):
                    break
                text = line.decode("utf-8", "replace").strip()
                if ":" in text:
                    k, v = text.split(":", 1)
                    headers[k.strip().lower()] = v.strip()

            # 路径路由: ①大批量结果文件 GET /data/<fn> → 文件下发(不校验用户，只认文件名) 
            #            ②官方端点(/kanzi_api_mcp / /kanzi_doc_mcp) ③studio(/mcp / / /kanzistudio_mcp)
            path_norm = path.rstrip("/")
            if path_norm.startswith("/data/"):
                if method != "GET":
                    await self._send_http(writer, 405, "text/plain", "Only GET")
                    return
                await self._handle_data_get(path_norm, writer)
                return
            is_official = path_norm in self.OFFICIAL_ENDPOINTS
            is_studio = (not is_official) and (
                path_norm == self.url_path.rstrip("/")
                or path_norm == "/"
                or path_norm == "/kanzistudio_mcp"
            )
            if not (is_official or is_studio):
                await self._send_http(writer, 404, "text/plain", "Not Found")
                return

            # 取用户名并校验白名单
            username = headers.get(self.USER_HEADER, "")
            if not username:
                await self._send_http(writer, 400, "application/json",
                                      json.dumps({"jsonrpc": "2.0",
                                                  "error": {"code": -32000,
                                                            "message": "缺少 X-Kanzi-User header"},
                                                  "id": None}))
                return
            if not self.users.is_allowed(username):
                log.warning(f"⛔ 拒绝未知用户: {username}")
                await self._send_http(writer, 403, "application/json",
                                      json.dumps({"jsonrpc": "2.0",
                                                  "error": {"code": -32000,
                                                            "message": f"用户 {username} 不在白名单"},
                                                  "id": None}))
                return

            content_length = int(headers.get("content-length", "0"))
            body = b""
            if content_length > 0:
                body = await reader.readexactly(content_length)

            if method == "GET":
                init = {"jsonrpc": "2.0", "result": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {"tools": {"listChanged": False}},
                    "serverInfo": {"name": "kanzi-studio-mcp-http", "version": "1.0.0"}}}
                await self._send_http(writer, 200, "application/json", json.dumps(init))
                return

            try:
                req = json.loads(body.decode("utf-8"))
            except Exception:
                await self._send_http(writer, 400, "application/json",
                                      json.dumps({"jsonrpc": "2.0",
                                                  "error": {"code": -32700, "message": "Parse error"},
                                                  "id": None}))
                return

            # 按路径路由: 官方端点 → 官方客户端处理; 否则 → 本地 studio(现有逻辑)
            if is_official:
                client, client_name = self.OFFICIAL_ENDPOINTS[path_norm]
                resp = await self._handle_jsonrpc_official(client, client_name, req)
            else:
                resp = await self._handle_jsonrpc(req, username)
            if resp is None:
                await self._send_http(writer, 202, "application/json", "")
            else:
                accept_sse = "text/event-stream" in headers.get("accept", "")
                if accept_sse:
                    await self._send_http(writer, 200, "text/event-stream",
                                          f"data: {json.dumps(resp, ensure_ascii=False)}\n\n")
                else:
                    await self._send_http(writer, 200, "application/json",
                                          json.dumps(resp, ensure_ascii=False))

        except Exception as e:
            log.error(f"HTTP 处理异常: {e}")
            try:
                await self._send_http(writer, 500, "application/json",
                                      json.dumps({"jsonrpc": "2.0",
                                                  "error": {"code": -32603, "message": str(e)},
                                                  "id": None}))
            except Exception:
                pass
        finally:
            try:
                writer.close()
            except Exception:
                pass

    async def _handle_jsonrpc_official(self, client: "OfficialMcpHttpClient", client_name: str, req: dict):
        """处理官方 api/doc 端点的 JSON-RPC: initialize / tools/list / tools/call / ping。
        tools/call 通过 client 转发到官方 MCP, session 失效自动重连。"""
        if not isinstance(req, dict) or "method" not in req:
            return {"jsonrpc": "2.0", "error": {"code": -32600, "message": "Invalid Request"},
                    "id": req.get("id") if isinstance(req, dict) else None}
        method = req.get("method", "")
        req_id = req.get("id")

        if method == "initialize":
            return {"jsonrpc": "2.0", "id": req_id, "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {"listChanged": False}},
                "serverInfo": {"name": f"{client_name}-mcp-http", "version": "1.0.0"}}}
        if method == "notifications/initialized":
            return None
        if method == "ping":
            return {"jsonrpc": "2.0", "id": req_id, "result": {}}
        if method == "tools/list":
            try:
                tools = await client.tools(refresh=False)
            except Exception as e:
                log.info(f"ℹ [{client_name}] 官方工具清单拉取失败: {e}")
                tools = []
            return {"jsonrpc": "2.0", "id": req_id, "result": {"tools": tools}}
        if method == "tools/call":
            params = req.get("params", {}) or {}
            tool = params.get("name", "")
            args = params.get("arguments", {}) or {}
            try:
                result = await client.call_raw(tool, args)
                return {"jsonrpc": "2.0", "id": req_id, "result": result}
            except Exception as e:
                return {"jsonrpc": "2.0", "id": req_id, "result": {
                    "content": [{"type": "text",
                                  "text": f"❌ 官方 {client_name} 调用失败: {e}"}]}}
        return {"jsonrpc": "2.0", "id": req_id, "result": {}}

    async def _handle_jsonrpc(self, req: dict, username: str):
        if not isinstance(req, dict) or "method" not in req:
            return {"jsonrpc": "2.0", "error": {"code": -32600, "message": "Invalid Request"},
                    "id": req.get("id") if isinstance(req, dict) else None}
        method = req.get("method", "")
        req_id = req.get("id")

        if method == "initialize":
            return {"jsonrpc": "2.0", "id": req_id, "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {"listChanged": False}},
                "serverInfo": {"name": "kanzi-studio-mcp-http", "version": "1.0.0"}}}
        if method == "notifications/initialized":
            return None
        if method == "ping":
            return {"jsonrpc": "2.0", "id": req_id, "result": {}}

        # 需要 Kanzi 连接的操作 → 取得该用户的稳定连接(无则新建, 有则复用)并确保已启动
        # (历史修复: 之前 get_handler 取首个 running、start_user 起最新 —— 两条不是同一条,
        #  导致新建连接 ws 一直为 None, 报 "Kanzi 未连接")
        relay, handler = await self.users.start_user(username)
        # 等 client 槽真正连上中继(与 Kanzi server 直通), 避免首请求发空
        try:
            await asyncio.wait_for(relay.wait_connected(3.0), timeout=4.0)
        except (asyncio.TimeoutError, Exception):
            # Kanzi server 未上线时 relay 不拒连(连接保持), 请求一律直接回错误, 这里不抛错让下方 fallback
            pass
        if not (relay.ws and getattr(relay.ws, "state", None) and relay.ws.state.name == "OPEN"):
            if method == "tools/list":
                return {"jsonrpc": "2.0", "id": req_id, "result": {"tools": self.TOOLS}}
            if method == "tools/call":
                return {"jsonrpc": "2.0", "id": req_id,
                        "error": {"code": -32000,
                                   "message": f"用户 {username} 的 Kanzi 未连接(server 可能未启动或尚未连到中继)"}}

        if method == "tools/list":
            try:
                resp = await handler.relay_request({"jsonrpc": "2.0", "id": req_id,
                                                    "method": "tools/list", "params": {}}, timeout=8.0)
                if isinstance(resp, dict) and "result" in resp and isinstance(resp["result"], dict):
                    return resp
                if isinstance(resp, dict) and "error" in resp and resp["error"].get("message", "").startswith("用户"):
                    return {"jsonrpc": "2.0", "id": req_id, "result": {"tools": self.TOOLS}}
            except Exception as e:
                log.info(f"ℹ [{username}] server 工具列表不可用, 用本地工具表 ({e})")
            return {"jsonrpc": "2.0", "id": req_id, "result": {"tools": self.TOOLS}}

        if method == "tools/call":
            params = req.get("params", {})
            forward_req = {"jsonrpc": "2.0", "id": req_id, "method": "tools/call",
                           "params": {"name": params.get("name", ""),
                                      "arguments": params.get("arguments", {})}}
            resp = await handler.relay_request(forward_req)
            return self._maybe_offload_resp(resp, req_id)

        return {"jsonrpc": "2.0", "id": req_id, "result": {}}

    def _maybe_offload_resp(self, resp: dict, req_id) -> dict:
        """检测 Kanzi 返回是否为大结果(超阈值)，若是则外置成文件并替换返回摘要。
        中小结果照旧原样返回(现状不变)。"""
        try:
            if not (isinstance(resp, dict) and "result" in resp):
                return resp
            result = resp["result"]
            if not (isinstance(result, dict) and isinstance(result.get("content"), list)):
                return resp
            texts = [
                c.get("text", "")
                for c in result["content"]
                if isinstance(c, dict) and c.get("type") == "text" and c.get("text") is not None
            ]
            if not texts:
                return resp
            full = "\n".join(texts)
            if not self._tmp_dir or not self._should_offload(full):
                return resp
            res_id = uuid.uuid4().hex
            info = self._offload_result(res_id, full)
            if info is None:
                return resp
            log.info(f"📦 tools/call id={req_id} 结果外置: {info['url']} "
                     f"entries={info['entries']} size={info['size']}B")
            summary = (
                f"✅ 结果较大，已外置到文件(共 {info['entries']} 条):\n"
                f"URL: {info['url']}\n"
                f"大小: {self._fmt_size(info['size'])}\n"
                f"记录数: {info['entries']}\n"
                f"摘要: {info['summary']}\n"
                f"需要全部数据请 GET 上述 URL（UTF-8 JSON，文件内 text 字段为完整内容，TTL {int(self._result_ttl // 60)} 分钟自动清理）；需要单条用其 ref_id 继续 kz_invoke。"
            )
            return {"jsonrpc": "2.0", "id": req_id, "result": {
                "content": [{"type": "text", "text": summary}]
            }}
        except Exception as e:
            log.warning(f"📦 结果外置处理异常(回退原样返回): {e}")
            return resp

    @staticmethod
    def _fmt_size(nbytes: int) -> str:
        if nbytes < 1024:
            return f"{nbytes} B"
        if nbytes < 1024 * 1024:
            return f"{nbytes / 1024:.1f} KB"
        return f"{nbytes / 1024 / 1024:.2f} MB"

    async def _send_http(self, writer, status, ctype, body: str):
        reason = {200: "OK", 202: "Accepted", 400: "Bad Request",
                  403: "Forbidden", 404: "Not Found", 500: "Internal Server Error"}.get(status, "")
        header = (f"HTTP/1.1 {status} {reason}\r\n"
                  f"Content-Type: {ctype}\r\n"
                  f"Content-Length: {len(body.encode('utf-8'))}\r\n"
                  f"Connection: close\r\n"
                  f"Access-Control-Allow-Origin: *\r\n"
                  f"Access-Control-Allow-Headers: Content-Type, Accept, X-Kanzi-User\r\n"
                  f"Access-Control-Allow-Methods: GET, POST, OPTIONS\r\n"
                  f"\r\n")
        try:
            writer.write(header.encode("utf-8"))
            if body:
                writer.write(body.encode("utf-8"))
            await writer.drain()
            writer.close()
        except Exception:
            pass


# ═══════════════════════════════════════════════════════════════════
#  配置文件加载（把全部启动参数收敛到一个 config.json，白名单单独 users.json 保持热更新）
# ═══════════════════════════════════════════════════════════════════
DEFAULT_CONFIG_PATH = "config.json"

def _cfg(path, key, defv):
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        v = data.get(key, defv)
        return v
    except Exception:
        return defv

def _cfg_int(cfg, key, defv):
    v = cfg.get(key)
    if v is None:
        return defv
    try:
        return int(v)
    except Exception:
        return defv

def _cfg_str(cfg, key, defv):
    v = cfg.get(key)
    return v if v is not None and str(v) != "" else defv

def _cfg_bool(cfg, key, defv):
    v = cfg.get(key)
    if v is None:
        return defv
    if isinstance(v, bool):
        return v
    return str(v).lower() in ("1", "true", "yes", "on")

def load_config(path):
    """读取 config.json（若存在）。不存在/损坏返回空 dict，全部走命令行默认值，不崩。
    白名单不在这个文件里 —— users 永远走独立 users.json 并热更新（改了不重启）。"""
    cfg = {}
    if not path:
        return cfg
    try:
        with open(path, "r", encoding="utf-8") as f:
            cfg = json.load(f)
    except FileNotFoundError:
        log.info("info: config not found, use commandline defaults " + str(path))
    except Exception as e:
        log.warning("warn: config read fail, use commandline defaults: %s" % e)
    return cfg if isinstance(cfg, dict) else {}

def write_config_example(path):
    """生成一份带全部字段的示例配置（不覆盖已有文件）。"""
    if os.path.exists(path):
        return
    example = {
        "relay_base": "ws://127.0.0.1:58080",
        "users": "users.json",
        "listen": "0.0.0.0:9001",
        "mcp_timeout": 300,
        "heartbeat_interval": 5,
        "heartbeat_max_fails": 3,
        "req_check_interval": 2,
        "result_tmp_dir": "tmp_results",
        "result_ttl": 1800,
        "result_public_host": None,
        "result_threshold_entries": 50,
        "result_threshold_bytes": 4096,
        "debug": False,
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(example, f, ensure_ascii=False, indent=2)
    log.info("sample config written: " + str(path))

# ═══════════════════════════════════════════════════════════════════
#  入口
# ═══════════════════════════════════════════════════════════════════
async def main():
    parser = argparse.ArgumentParser(description="单进程多用户 Kanzi MCP over HTTP server")
    parser.add_argument("--log-path", default=None,
                       help="日志文件路径(组件自己轮转, 10MB×5); 不传则只输出控制台")
    parser.add_argument("--config", default=None,
                       help="配置文件路径 (默认 config.json; 所有启动参数都在这改)。命令行参数仍可覆盖对应项。白名单永远在 users 字段指定的 users.json, 改它不重启热更新)")
    parser.add_argument("--relay-base", default=None,
                       help="中继地址基座(不含用户名), 如 ws://127.0.0.1:58080 —— 每个用户连接 <base>/<用户名>")
    parser.add_argument("--users", default=None,
                       help="白名单配置文件(JSON, 含 users 数组), 如 users.json (改它不重启, 热更新)")
    parser.add_argument("--listen", default=None,
                       help="HTTP MCP server 监听 主机:端口 (默认 0.0.0.0:9001)")
    parser.add_argument("--mcp-timeout", type=int, default=None,
                       help="MCP 转发到 Kanzi 的单次请求超时秒数 (默认 300)")
    parser.add_argument("--heartbeat-interval", type=int, default=None,
                       help="喂狗(kz_health)间隔秒数 (默认 5)")
    parser.add_argument("--heartbeat-max-fails", type=int, default=None,
                       help="喂狗连续 N 次无响应即判链路坏 (默认 3)")
    parser.add_argument("--req-check-interval", type=int, default=None,
                       help="单个请求周期检查间隔秒数 (默认 2)")
    parser.add_argument("--result-tmp-dir", default=None,
                       help="大批量结果落盘目录 (默认 tmp_results)")
    parser.add_argument("--result-ttl", type=int, default=None,
                       help="临时结果文件存活秒数 (默认 1800)")
    parser.add_argument("--result-public-host", default=None,
                       help="结果文件 URL 里对 AI 可达的中继机 IP (跨机必配)")
    parser.add_argument("--result-threshold-entries", type=int, default=None,
                       help="记录数超过此值才外置 (默认 50)")
    parser.add_argument("--result-threshold-bytes", type=int, default=None,
                       help="文本超过此字节才外置 (默认 4096)")
    parser.add_argument("--debug", const=True, nargs="?", default=None,
                       help="开启调试日志")
    args = parser.parse_args()
    setup_file_log(args.log_path)

    # 加载配置文件（不存在则生成示例）
    cfg_path = args.config or DEFAULT_CONFIG_PATH
    write_config_example(cfg_path)
    cfg = load_config(cfg_path)

    # 参数解析: 命令行优先, 缺省走配置, 再缺省走内置默认
    relay_base   = args.relay_base or _cfg_str(cfg, "relay_base", None)
    users_file   = args.users or _cfg_str(cfg, "users", None)
    listen       = args.listen or _cfg_str(cfg, "listen", "0.0.0.0:9001")
    mcp_timeout  = args.mcp_timeout if args.mcp_timeout is not None else _cfg_int(cfg, "mcp_timeout", 300)
    hb_interval  = args.heartbeat_interval if args.heartbeat_interval is not None else _cfg_int(cfg, "heartbeat_interval", 5)
    hb_max_fails = args.heartbeat_max_fails if args.heartbeat_max_fails is not None else _cfg_int(cfg, "heartbeat_max_fails", 3)
    req_check    = args.req_check_interval if args.req_check_interval is not None else _cfg_int(cfg, "req_check_interval", 2)
    debg         = args.debug if args.debug is not None else _cfg_bool(cfg, "debug", False)

    if debg:
        logging.getLogger().setLevel(logging.DEBUG)

    if not relay_base or not users_file:
        log.error("缺少 relay_base 或 users 配置（请写入 %s 或命令行传入）" % cfg_path)
        sys.exit(1)

    host, _, port_str = listen.partition(":")
    port = int(port_str or "9001")

    allowed = load_users(users_file)
    if not allowed:
        log.error("白名单为空, 拒绝启动")
        sys.exit(1)

    manager = UserManager(relay_base, allowed, request_timeout=mcp_timeout,
                          config_path=users_file,
                          hb_interval=hb_interval, hb_max_fails=hb_max_fails,
                          req_check=req_check)
    http_mcp = HttpMcpServer(manager, host, port)
    # 大批量结果外置配置 (阈值/TTL/TMP 目录)
    _e = args.result_threshold_entries
    http_mcp.RESULT_THRESHOLD_ENTRIES = _e if _e is not None else _cfg_int(cfg, "result_threshold_entries", 50)
    _b = args.result_threshold_bytes
    http_mcp.RESULT_THRESHOLD_BYTES = _b if _b is not None else _cfg_int(cfg, "result_threshold_bytes", 4096)
    _rt = args.result_tmp_dir or _cfg_str(cfg, "result_tmp_dir", None)
    _ttl = args.result_ttl if args.result_ttl is not None else _cfg_int(cfg, "result_ttl", 1800)
    _ph = args.result_public_host or _cfg_str(cfg, "result_public_host", None)
    http_mcp.set_result_offload(_rt, _ttl, public_host=_ph)
    await http_mcp.start()
    await http_mcp.start_sweep()

    log.info(f"🚀 kz_mcp_http.py 已就绪 (单进程多用户)")
    log.info(f"   relay 基座: {relay_base}")
    log.info(f"   白名单: {sorted(allowed)}")
    log.info(f"   配置文件: {cfg_path}")
    log.info(f"   喂狗: interval={hb_interval}s max_fails={hb_max_fails} req_check={req_check}s")
    log.info(f"   ★ 白名单热更新: 编辑 {users_file} 保存后即时生效, 无需重启 kz_mcp_http.py / nlp_worker")
    log.info(f"   HTTP 端点: http://{host}:{port}/mcp")
    log.info(f"   copilot 配置示例:")
    log.info(f"     --additional-mcp-config '{{\"kanzi\":{{\"type\":\"http\",\"url\":\"http://{host}:{port}/mcp\",\"headers\":{{\"X-Kanzi-User\":\"suijichao\"}}}}}}'")

    try:
        while True:
            await asyncio.sleep(3600)
    except KeyboardInterrupt:
        pass
    finally:
        await manager.stop_all()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        log.info("已停止")
    except Exception as e:
        log.error(f"启动失败: {e}")
        sys.exit(1)
