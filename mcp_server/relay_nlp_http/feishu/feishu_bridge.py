#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
feishu_bridge.py — 飞书 ↔ Kanzi nlp_worker(copilot) 桥（v3: 多 bot + 热更新）

一个桥进程管理多个飞书机器人，每个机器人独立连各自的 relay 通道，
进而连通各自的 nlp_worker/copilot/Kanzi。

架构:
    [用户A] → 机器人A(App_A) ─┐
    [用户B] → 机器人B(App_B) ─┤→ 同一个 feishu_bridge 进程(本程序)
    [用户C] → 机器人C(App_C) ─┘
            │ 每个机器人 = 独立线程跑 lark-oapi 长连接(各自 App)
            │          + 各自 relay 通道(nlp_client 角色)
            │          + 各自 HTTP 文件服务端口 + inbox
            ▼
    [relay_multi(58080)] 通道A ←→ nlp_worker_A ←→ copilot_A ←→ kz_mcp_http_A ←→ Kanzi_A
                         通道B ←→ nlp_worker_B ←→ ...            ←→ Kanzi_B
                         ...

热更新: 定期(默认 3s)重读 feishu_config.json 的 bots 列表, diff 后:
    - 新增 bot → 自动启动该机器人链路
    - 删除 bot → 停掉对应 relay 任务(移除)
    - 改动 bot → 重启该机器人
  运行中的其它 bot 不受影响, 全程不用重启桥进程。

依赖:
    pip install lark-oapi websockets

用法:
    python feishu_bridge.py --config feishu_config_v3.json [--debug]

配置(feishu_config.example.v3.json 可参考):
    {
      "reload": { "enabled": true, "watch_interval_s": 3 },
      "http": { "host": "0.0.0.0" },
      "bots": [
        { "name": "hmi-alarm", "app_id": "...", "app_secret": "...",
          "relay_url": "ws://10.10.118.152:58080/hmi-alarm",
          "http_bind_ip": "10.10.118.152", "http_port": 8081,
          "inbox_dir": "inbox_hmi-alarm" },
        ...
      ]
    }

注意:
    - 每个 bot 连各自独立通道(relay_url 路径段), 不能共用同一通道
      (relay 每条通道只允许 1 个 nlp_client, 共用会把别人踢掉)。
    - 每个 bot 的 http_port 必须全局唯一(文件服务用端口路由回对应机器人)。
    - 与对应 nlp_worker_acp 必须同通道; nlp_worker 的 --bridge-http 指向该 bot 的 http_port。
"""

import argparse
import asyncio
import json
import logging
import multiprocessing
import os
import queue
import re
import threading
import time
import urllib.request

import websockets

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("feishu-bridge-v3")


# ═══════════════════════════════════════════════════════════════════
#  Relay 侧: 以 nlp_client 角色连中继, 收发消息
# ═══════════════════════════════════════════════════════════════════
class RelayNlpClient:
    """管理到中继的 WebSocket 连接, 角色 = nlp_client。每个 bot 一条。"""

    def __init__(self, relay_url: str, channel: str, bot_name: str, on_message):
        self.relay_url = relay_url      # 如 ws://10.10.118.152:58080/hmi-alarm
        self.channel = channel          # 用户名/通道
        self.bot_name = bot_name
        self.on_message = on_message    # 回调: async func(msg: dict)
        self.ws = None
        self._running = False
        self._task = None
        self._send_lock = asyncio.Lock()

    async def start(self):
        self._running = True
        self._task = asyncio.create_task(self._connect_loop())

    async def _connect_loop(self):
        while self._running:
            try:
                async with websockets.connect(
                    self.relay_url,
                    ping_interval=30,
                    max_size=16 * 1024 * 1024,
                ) as ws:
                    self.ws = ws
                    # 握手: 声明角色 + 通道名(用户名)
                    await ws.send(json.dumps(
                        {"role": "nlp_client", "name": self.channel},
                        ensure_ascii=False))
                    log.info(f"✅ [{self.bot_name}] 已连接中继(nlp_client): {self.relay_url}")
                    async for raw in ws:
                        try:
                            msg = json.loads(raw)
                        except json.JSONDecodeError:
                            continue
                        await self.on_message(msg)
            except Exception as e:
                log.warning(f"🔌 [{self.bot_name}] 中继断开({e}), 3s 后重连...")
            finally:
                self.ws = None
            await asyncio.sleep(3)

    async def send_user_message(self, text: str):
        """把飞书消息作为 user_message 发给 nlp_worker(copilot)。"""
        ws = self.ws
        if not ws:
            log.warning(f"⚠️ [{self.bot_name}] 中继未连接, 消息未发送")
            return False
        try:
            async with self._send_lock:
                await ws.send(json.dumps(
                    {"type": "user_message", "text": text}, ensure_ascii=False))
            return True
        except Exception as e:
            log.error(f"⚠️ [{self.bot_name}] user_message 发送失败: {e}")
            return False

    async def stop(self):
        self._running = False
        if self.ws:
            try:
                await self.ws.close()
            except Exception:
                pass
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except (asyncio.CancelledError, Exception):
                pass


# ═══════════════════════════════════════════════════════════════════
#  单个机器人节点: 桥主控(飞书事件 <-> relay 消息 配对路由)
# ═══════════════════════════════════════════════════════════════════
class Bridge:
    """一个机器人的桥逻辑。串起飞书长连接事件线程 与 relay 客户端。

    每个 bot 独立维护: last_sender(回给谁)、单会话互斥、inbox、HTTP 文件服务。
    飞书侧(lark-oapi 事件回调)运行在 SDK 的线程里, 用线程安全队列和主事件循环协作。
    """

    def __init__(self, bot_name: str, feishu_client, relay: RelayNlpClient,
                 http_host="0.0.0.0", http_port=8081, inbox_dir=None, http_bind_ip=None):
        self.bot_name = bot_name
        self.feishu = feishu_client
        self.relay = relay
        self.http_host = http_host
        self.http_port = http_port
        self.http_bind_ip = http_bind_ip or http_host  # 生成下载 URL 用的可访问 IP
        self.inbox_dir = inbox_dir or os.path.join(os.getcwd(), f"inbox_{bot_name}")
        os.makedirs(self.inbox_dir, exist_ok=True)
        self._feishu_to_main = queue.Queue()   # 飞书事件线程 → 主循环
        self._upload_queue = queue.Queue()     # HTTP /upload 线程 → 主循环
        self.last_sender = None                # 最近一条指令的 open_id
        self._busy = False
        self._done_event = asyncio.Event()     # 单会话互斥
        self._thinking_sent = False
        # ---- 单条进度消息 · 五行滚动编辑 ----
        # nlp 发来的每条 progress 都编辑进同一条飞书消息, 内容保留最近 5 行, 不刷屏。
        self._progress_msg_id = None      # 当前进度消息的 message_id(为空则需新发)
        self._progress_open_id = None     # 进度消息所属用户 open_id
        self._progress_lines: list[str] = []  # 五行环形(最多 5 行)
        self._PROGRESS_MAX_LINES = 5
        self._stopping = False

    def register_file_service(self, upload_queue: queue.Queue):
        """把本 bot 的 upload_queue 交给共享 FileRouter(多 bot 共用单端口时)。
        下载 URL 仍用本 bot 的 http_bind_ip/http_port(共享同一端口, 路径带 bot 名路由)。
        """
        self._upload_queue = upload_queue

    def _tag(self, s: str) -> str:
        return f"[{self.bot_name}] {s}"

    # ---- 飞书侧回调(lark-oapi SDK 线程里, 只入队) ----
    def on_feishu_message(self, open_id: str, text: str):
        self._feishu_to_main.put(("cmd", open_id, text))

    def on_feishu_file(self, open_id: str, message_id: str, file_key: str, file_name: str):
        log.info(self._tag(f"📎 收到飞书文件: {file_name} key={file_key}"))
        self._feishu_to_main.put(("file", open_id, (message_id, file_key, file_name)))

    # ---- relay 侧回调(asyncio 主循环里) ----
    async def on_relay_message(self, msg: dict):
        msg_type = msg.get("type", "")
        if msg_type == "claude_output":
            text = msg.get("text", "") or "(无输出)"
            # 完成标志: claude_output 是"一轮结束"的唯一判定, 让用户知道何时完成。
            # 分块输出格式 "(1/N)...(N/N)": 只在末帧(第N==总数)或未分块的单条加"✅完成";
            # 中间帧不加, 避免用户误以为已结束。
            m = re.match(r"^\((\d+)/(\d+)\)", text)
            if m and m.group(1) == m.group(2):
                await self._reply_feishu(f"✅ 完成\n\n{text}")
            elif not m:
                await self._reply_feishu(f"✅ 完成\n\n{text}")
            else:
                await self._reply_feishu(text)
            self._thinking_sent = False
            # 一轮结束: 清空进度消息(下条任务重新新发一条)
            self._progress_msg_id = None
            self._progress_open_id = None
            self._progress_lines = []
            self._done_event.set()
        elif msg_type == "thinking":
            t = str(msg.get("text", ""))
            log.info(f"[{self.bot_name}] copilot thinking: {t[:120]}")
            if not self._thinking_sent and t.strip():
                self._thinking_sent = True
                await self._reply_feishu("🤖 思考中...")
        elif msg_type == "connected":
            log.info(f"[{self.bot_name}] {msg.get('text','')}")
        elif msg_type == "worker_online":
            # worker 上线：解掉可能的残留锁 + 提示用户已可用
            log.info(f"[{self.bot_name}] copilot worker 在线")
            self._reset_round_state()
            await self._reply_feishu("✅ Copilot 已连接，可以继续发送指令")
        elif msg_type == "worker_disconnected":
            # worker 断开：必须解锁，否则 _busy 永远 True → 后续消息全被"请稍候"挡死
            log.warning(f"[{self.bot_name}] copilot worker 断开，解锁并提示用户")
            self._reset_round_state()
            await self._reply_feishu("❌ Copilot 已断开，本轮已取消。请稍后重试（或等待自动重连）。")
        elif msg_type == "progress":
            # 多阶段活动反馈：绝不触发 _done_event(不作为一轮结束、不提前放行第二条)。
            # 单条 ·五行滚动编辑: 维持一条进度消息, 内容保留最近五行, 不刷屏。
            t = str(msg.get("text", ""))
            if t.strip():
                log.info(f"[{self.bot_name}] copilot progress: {t[:120]}")
                await self._reply_progress(t)

    async def _reply_feishu(self, text: str):
        open_id = self.last_sender
        if not open_id:
            log.warning(self._tag("⚠️ 无 last_sender, 回复无法路由(丢弃)"))
            return
        await self.feishu.send_text(open_id, text)

    def _reset_round_state(self):
        """解锁单会话互斥并清掉本轮状态。

        worker 上线/断开时必须调用：否则 _busy 永远为 True，
        后续消息全被"⏳ Copilot 正在处理上一条指令"挡死。
        """
        self._busy = False
        self._done_event.set()          # 唤醒可能正在 wait 的协程
        self._thinking_sent = False
        self._progress_msg_id = None
        self._progress_open_id = None
        self._progress_lines = []
        self._busy_round_seq = getattr(self, "_busy_round_seq", 0) + 1

    async def _reply_progress(self, line: str):
        """单条进度消息 · 五行滚动编辑。

        把 nlp 发来的每条进度编辑进同一条飞书消息, 消息内容保留最近五行:
        - 无当前进度消息 → 新发一条并记录 message_id;
        - 已有 → 用飞书 update 编辑该条(内容=最近五行)。
        条数始终 1 条, 内容滚动更新; nlp 已做事件节流, 这里不再加频率限制。
        """
        open_id = self._progress_open_id or self.last_sender
        if not open_id:
            log.warning(self._tag("⚠️ 无 open_id, progress 无法路由(丢弃)"))
            return
        # 五行环形: 追加, 超 5 行顶掉最旧
        self._progress_lines.append(line)
        if len(self._progress_lines) > self._PROGRESS_MAX_LINES:
            self._progress_lines = self._progress_lines[-self._PROGRESS_MAX_LINES:]
        body = "\n".join(self._progress_lines)
        if not self._progress_msg_id:
            # 新发一条
            ok, mid = await self.feishu.send_text_with_id(open_id, body)
            if ok and mid:
                self._progress_msg_id = mid
                self._progress_open_id = open_id
        else:
            # 编辑同一条
            ok = await self.feishu.edit_text(open_id, self._progress_msg_id, body)
            if not ok:
                # 编辑失败(可能已失效) → 重新新发一条
                log.warning(self._tag("进度编辑失败, 重新新发一条"))
                ok, mid = await self.feishu.send_text_with_id(open_id, body)
                if ok and mid:
                    self._progress_msg_id = mid
                    self._progress_open_id = open_id

    # ---- 主循环: 排空飞书指令队列, 转发给 copilot ----
    async def run(self):
        await self.relay.start()
        while not self._stopping:
            # 优先排空 /upload 队列(回传截图等)
            # 该 upload_queue 是本 bot 私有的, /upload 路径段已按机器人路由;
            # 截图必在用户发指令后回调, 所以回发给本 bot 的 last_sender 即可(无需 open_id 参数)。
            while True:
                try:
                    u = self._upload_queue.get_nowait()
                except queue.Empty:
                    break
                open_id = u.get("open_id") or self.last_sender
                if not open_id:
                    log.warning(self._tag("⚠️ 无 last_sender, 截图/文件无法回发"))
                    continue
                try:
                    await asyncio.get_event_loop().run_in_executor(
                        None, self.feishu.send_file_sync, open_id, u["data"], u["name"])
                except Exception as e:
                    log.error(self._tag(f"回发 /upload 文件失败: {e}"))

            try:
                item = self._feishu_to_main.get_nowait()
            except queue.Empty:
                await asyncio.sleep(0.1)
                continue

            if item[0] == "file":
                _, open_id, (msg_id, file_key, file_name) = item
                await self._handle_file_upload(open_id, msg_id, file_key, file_name)
                continue

            _, open_id, text = item

            if self._busy:
                await self._reply_feishu("⏳ Copilot 正在处理上一条指令, 请稍候...")
                continue

            self.last_sender = open_id
            self._busy = True
            self._done_event.clear()
            self._thinking_sent = False
            log.info(f"📝 [{self.bot_name}] 飞书指令: {text[:100]}")

            async def _fallback_feedback():
                try:
                    await asyncio.sleep(1.8)
                    if not self._thinking_sent and not self._done_event.is_set():
                        self._thinking_sent = True
                        await self._reply_feishu("🤖 思考中...")
                except asyncio.CancelledError:
                    pass

            _fb = asyncio.ensure_future(_fallback_feedback())

            ok = await self.relay.send_user_message(text)
            if not ok:
                _fb.cancel()
                await self._reply_feishu(self._tag("❌ 中继未连接, 请确认 nlp_worker 是否已启动"))
                self._busy = False
                continue
            try:
                await asyncio.wait_for(self._done_event.wait(), timeout=36000)
            except asyncio.TimeoutError:
                log.warning(f"⏱ [{self.bot_name}] copilot 回复超时(36000), 放行下一条")
                await self._reply_feishu("⏳ Copilot 处理超时(10h), 请重试")
            finally:
                _fb.cancel()
                self._busy = False

    # ---- v2: 用户上传文件 → 下载到 inbox/ → 发 FILE_DOWNLOAD 指令 ----
    async def _handle_file_upload(self, open_id, message_id, file_key, file_name):
        safe_name = re.sub(r"[^\w.\-]", "_", file_name) or "file"
        local_path = os.path.join(self.inbox_dir, f"{int(time.time()*1000)}_{safe_name}")
        try:
            data = await asyncio.get_event_loop().run_in_executor(
                None, self.feishu.download_resource, message_id, file_key)
            with open(local_path, "wb") as f:
                f.write(data)
        except Exception as e:
            log.error(self._tag(f"❌ 下载飞书文件失败: {e}"))
            await self._reply_feishu("❌ 下载文件失败, 请重试")
            return
        fname = os.path.basename(local_path)
        # URL 带 bot 前缀, 供共享 FileRouter 路由到本 bot:{bind_ip}:{http_port}/{bot_name}/inbox/<file>
        url = f"http://{self.http_bind_ip}:{self.http_port}/{self.bot_name}/inbox/{fname}"
        instruction = (
            f"[FILE_DOWNLOAD]\n"
            f"url={url}\n"
            f"name={file_name}\n"
            f"note=用户上传的文件已生成下载链接, 请下载到工作目录后直接回复保存路径, 无需通知 copilot"
        )
        self.last_sender = open_id
        self._busy = True
        self._done_event.clear()
        self._thinking_sent = False
        ok = await self.relay.send_user_message(instruction)
        if not ok:
            self._busy = False
            await self._reply_feishu(self._tag("❌ 中继未连接, 无法处理文件"))
            return
        try:
            await asyncio.wait_for(self._done_event.wait(), timeout=600)
        except asyncio.TimeoutError:
            log.warning(f"⏱ [{self.bot_name}] 文件下载任务超时")
            await self._reply_feishu("⏳ 文件下载处理超时")
        finally:
            self._busy = False
        log.info(self._tag(f"✅ 文件 {file_name} 已落盘 inbox/: {fname}"))

    async def stop(self):
        self._stopping = True
        await self.relay.stop()


# ═══════════════════════════════════════════════════════════════════
#  (全局 DEBUG 标志)
# ═══════════════════════════════════════════════════════════════════
_DEBUG = False


# ═══════════════════════════════════════════════════════════════════
#  飞书侧: lark-oapi 长连接 + 发消息(每 bot 一个实例)
# ═══════════════════════════════════════════════════════════════════
def _is_image_bytes(data: bytes) -> bool:
    """按文件头判断是否为图片(PNG/JPG/BMP/GIF/WEBP)。"""
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return True
    if data[:3] == b"\xff\xd8\xff":
        return True
    if data[:2] == b"BM":
        return True
    if data[:6] in (b"GIF87a", b"GIF89a"):
        return True
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return True
    return False


class FeishuClient:
    def __init__(self, app_id: str, app_secret: str, bot_name: str, bridge: Bridge):
        self.app_id = app_id
        self.app_secret = app_secret
        self.bot_name = bot_name
        self.bridge = bridge
        self.client = None
        self._lark = None
        self._handler = None
        self._tenant_token = None
        self._tenant_token_exp = 0
        self._ws_proc = None
        self._ws_mp_q = None
        self._ws_drain_thread = None

    def _build(self):
        lark = self._lark

        def on_im_message(data) -> None:
            try:
                event = data.event
                sender = getattr(event, "sender", None)
                sender_id = getattr(sender, "sender_id", None) if sender else None
                open_id = getattr(sender_id, "open_id", None) if sender_id else None
                message = getattr(event, "message", None)
                msg_type = getattr(message, "message_type", "") or ""
                raw_content = getattr(message, "content", "") or ""
                message_id = getattr(message, "message_id", "") or ""
                chat_id = getattr(message, "chat_id", "") or ""
                log.info(f"📨 [{self.bot_name}] 收到飞书消息: type={msg_type} open_id={open_id} chat={chat_id}")
                if msg_type == "file":
                    try:
                        cobj = json.loads(raw_content) if raw_content else {}
                    except json.JSONDecodeError:
                        cobj = {}
                    file_key = cobj.get("file_key", "") or ""
                    file_name = cobj.get("file_name", "") or "file"
                    if open_id and file_key:
                        self.bridge.on_feishu_file(open_id, message_id, file_key, file_name)
                    else:
                        log.warning(f"[{self.bot_name}] 文件消息缺 open_id/file_key")
                    return
                text = self._extract_text(msg_type, raw_content)
                if text:
                    self.bridge.on_feishu_message(open_id, text)
                    log.info(f"📝 [{self.bot_name}] 飞书文本指令: {text[:100]}")
                else:
                    log.warning(f"[{self.bot_name}] 非文本/空消息忽略: type={msg_type}")
            except Exception as e:
                log.error(f"[{self.bot_name}] 事件处理异常: {e}")

        handler = (
            lark.EventDispatcherHandler.builder("", "")
            .register_p2_im_message_receive_v1(on_im_message)
            .register_p2_im_chat_access_event_bot_p2p_chat_entered_v1(lambda data: None)
            .register_p2_im_chat_member_bot_added_v1(lambda data: None)
            .register_p2_im_chat_member_bot_deleted_v1(lambda data: None)
            .register_p2_im_message_message_read_v1(lambda data: None)
            .register_p2_im_message_recalled_v1(lambda data: None)
            .register_p2_application_bot_menu_v6(lambda data: None)
            .build()
        )
        self._handler = handler

    @staticmethod
    def _extract_text(msg_type: str, raw_content: str) -> str:
        try:
            obj = json.loads(raw_content) if raw_content else {}
        except json.JSONDecodeError:
            obj = {}
        if msg_type == "text":
            return str(obj.get("text", "") or "").strip()
        return ""

    def send_text(self, open_id: str, text: str):
        return asyncio.get_running_loop().run_in_executor(None, self._send_text_sync, open_id, text)

    # 新发一条文本消息, 返回 (ok, message_id)
    def send_text_with_id(self, open_id: str, text: str):
        return asyncio.get_running_loop().run_in_executor(None, self._send_text_with_id_sync, open_id, text)

    # 编辑已发消息内容(飞书 update), 返回 ok
    def edit_text(self, open_id: str, message_id: str, text: str):
        return asyncio.get_running_loop().run_in_executor(None, self._edit_text_sync, open_id, message_id, text)

    def _send_text_sync(self, open_id: str, text: str):
        ok, _mid = self._send_text_with_id_sync(open_id, text)
        return ok

    def _send_text_with_id_sync(self, open_id: str, text: str) -> tuple:
        if not self.client:
            log.error(f"[{self.bot_name}] 飞书客户端未初始化")
            return (False, None)
        try:
            _ReqCls = getattr(self, "_CreateMessageRequest", None)
            _BodyCls = getattr(self, "_CreateMessageRequestBody", None)
            if _ReqCls is None or _BodyCls is None:
                _ReqCls = self._lark.api.im.v1.CreateMessageRequest
                _BodyCls = self._lark.api.im.v1.CreateMessageRequestBody
            body = _BodyCls.builder() \
                .receive_id(open_id) \
                .msg_type("text") \
                .content(json.dumps({"text": text}, ensure_ascii=False)) \
                .build()
            request = _ReqCls.builder() \
                .receive_id_type("open_id") \
                .request_body(body) \
                .build()
            resp = self.client.im.v1.message.create(request)
            if not resp.success():
                log.error(f"[{self.bot_name}] 飞书发送失败: code={resp.code} msg={resp.msg}")
                return (False, None)
            mid = ""
            try:
                data = resp.data
                if data is not None:
                    mid = str(getattr(data, "message_id", "") or "")
            except Exception:
                pass
            log.info(f"[{self.bot_name}] 已回复飞书({mid}): {text[:40]}")
            return (True, mid)
        except Exception as e:
            log.error(f"[{self.bot_name}] 飞书发送异常: {e}")
            return (False, None)

    def _edit_text_sync(self, open_id: str, message_id: str, text: str) -> bool:
        if not self.client or not message_id:
            log.error(f"[{self.bot_name}] 飞书客户端未初始化或缺 message_id")
            return False
        try:
            _ReqCls = getattr(self, "_UpdateMessageRequest", None)
            _BodyCls = getattr(self, "_UpdateMessageRequestBody", None)
            if _ReqCls is None or _BodyCls is None:
                _ReqCls = self._lark.api.im.v1.UpdateMessageRequest
                _BodyCls = self._lark.api.im.v1.UpdateMessageRequestBody
            body = _BodyCls.builder() \
                .msg_type("text") \
                .content(json.dumps({"text": text}, ensure_ascii=False)) \
                .build()
            request = _ReqCls.builder() \
                .message_id(message_id) \
                .request_body(body) \
                .build()
            resp = self.client.im.v1.message.update(request)
            if not resp.success():
                log.error(f"[{self.bot_name}] 飞书编辑失败: code={resp.code} msg={resp.msg}")
                return False
            log.info(f"[{self.bot_name}] 已编辑飞书进度({message_id}): {text[:40]}")
            return True
        except Exception as e:
            log.error(f"[{self.bot_name}] 飞书编辑异常: {e}")
            return False

    # ---- v2: 飞书文件 API ----
    def _get_tenant_token(self):
        now = time.time()
        if self._tenant_token and now < self._tenant_token_exp - 60:
            return self._tenant_token
        req = urllib.request.Request(
            "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal",
            data=json.dumps({"app_id": self.app_id, "app_secret": self.app_secret}).encode(),
            headers={"Content-Type": "application/json; charset=utf-8"},
        )
        with urllib.request.urlopen(req, timeout=15) as r:
            obj = json.loads(r.read().decode())
        if obj.get("code", -1) != 0:
            raise RuntimeError(f"飞书 token 获取失败: {obj}")
        self._tenant_token = obj.get("tenant_access_token", "")
        self._tenant_token_exp = now + obj.get("expire", 7200)
        return self._tenant_token

    def download_resource(self, message_id: str, file_key: str) -> bytes:
        token = self._get_tenant_token()
        url = (f"https://open.feishu.cn/open-apis/im/v1/messages/{message_id}/resources/{file_key}"
               f"?type=file")
        req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
        with urllib.request.urlopen(req, timeout=60) as r:
            return r.read()

    def send_file_sync(self, open_id: str, file_bytes: bytes, file_name: str):
        if not self._lark:
            log.error(f"[{self.bot_name}] 飞书客户端未初始化")
            return False
        try:
            token = self._get_tenant_token()
            import requests
            import io as _io
            # 用文件头判断是否图片: 是图则走图片消息(image, 飞书直接预览并保留名), 否则走文件消息(file)
            if _is_image_bytes(file_bytes):
                try:
                    up = requests.post(
                        "https://open.feishu.cn/open-apis/im/v1/images",
                        headers={"Authorization": f"Bearer {token}"},
                        files={"image_type": (None, "message"),
                               "image": (file_name, file_bytes, "application/octet-stream")},
                        timeout=60,
                    ).json()
                except Exception as _e:
                    log.error(f"[{self.bot_name}] 飞书图片上传异常: {_e}")
                    up = {}
                if up.get("code", -1) != 0:
                    log.error(f"[{self.bot_name}] 飞书图片上传失败: {up}")
                    return False
                image_key = up.get("data", {}).get("image_key", "")
                if not image_key:
                    log.error(f"[{self.bot_name}] 飞书图片上传无 image_key")
                    return False
                _ReqCls = getattr(self, "_CreateMessageRequest", None)
                _BodyCls = getattr(self, "_CreateMessageRequestBody", None)
                if _ReqCls is None or _BodyCls is None:
                    _ReqCls = self._lark.api.im.v1.CreateMessageRequest
                    _BodyCls = self._lark.api.im.v1.CreateMessageRequestBody
                body2 = _BodyCls.builder() \
                    .receive_id(open_id) \
                    .msg_type("image") \
                    .content(json.dumps({"image_key": image_key}, ensure_ascii=False)) \
                    .build()
                request2 = _ReqCls.builder() \
                    .receive_id_type("open_id") \
                    .request_body(body2) \
                    .build()
                resp = self.client.im.v1.message.create(request2)
                if not resp.success():
                    log.error(f"[{self.bot_name}] 飞书发图片失败: code={resp.code} msg={resp.msg}")
                    return False
                log.info(f"[{self.bot_name}] 已回发飞书图片: {file_name}")
                return True
            # 非图片: 走文件消息
            up = requests.post(
                "https://open.feishu.cn/open-apis/im/v1/files",
                headers={"Authorization": f"Bearer {token}"},
                files={"file": (file_name, file_bytes, "application/octet-stream"),
                       "file_type": (None, "stream")},
                timeout=60,
            ).json()
            if up.get("code", -1) != 0:
                log.error(f"[{self.bot_name}] 飞书文件上传失败: {up}")
                return False
            file_key = up.get("data", {}).get("file_key", "")
            if not file_key:
                log.error(f"[{self.bot_name}] 飞书上传无 file_key")
                return False
            _ReqCls = getattr(self, "_CreateMessageRequest", None)
            _BodyCls = getattr(self, "_CreateMessageRequestBody", None)
            if _ReqCls is None or _BodyCls is None:
                _ReqCls = self._lark.api.im.v1.CreateMessageRequest
                _BodyCls = self._lark.api.im.v1.CreateMessageRequestBody
            body2 = _BodyCls.builder() \
                .receive_id(open_id) \
                .msg_type("file") \
                .content(json.dumps({"file_key": file_key}, ensure_ascii=False)) \
                .build()
            request2 = _ReqCls.builder() \
                .receive_id_type("open_id") \
                .request_body(body2) \
                .build()
            resp = self.client.im.v1.message.create(request2)
            if not resp.success():
                log.error(f"[{self.bot_name}] 飞书发文件失败: code={resp.code} msg={resp.msg}")
                return False
            log.info(f"[{self.bot_name}] 已回发飞书文件: {file_name}")
            return True
        except Exception as e:
            log.error(f"[{self.bot_name}] 飞书发文件异常: {e}")
            return False

    def start_long_conn(self):
        """启动飞书长连接。

        lark-oapi 的 ws/client.py 在【模块顶层】用 asyncio.get_event_loop() 定死一个
        全局 loop, 且全类复用。多 bot 场景下第二个 bot 复用缓存模块/同一 loop,
        而该 loop 已被第一个 bot 的 start() run_until_complete 占用 →
        RuntimeError: This event loop is already running。

        修复: 长连接收事件的 ws 部分放进独立 multiprocessing.Process(spawn),
        子进程全新解释器, import lark_oapi 时拿到干净 loop, 天然隔离多 bot。
        发消息/下载文件是纯 HTTP, 留在主进程(不依赖 ws loop)。
        """
        # ---- 主进程: 构建 HTTP client(发消息/下载) - 不依赖 ws loop ----
        try:
            import lark_oapi as lark
        except ImportError as e:
            raise RuntimeError("未安装 lark-oapi, 请先: pip install lark-oapi") from e
        self._lark = lark
        try:
            import importlib as _ilib
            _imv1 = _ilib.import_module("lark_oapi.api.im.v1")
            self._CreateMessageRequest = _imv1.CreateMessageRequest
            self._CreateMessageRequestBody = _imv1.CreateMessageRequestBody
        except Exception as _e:
            log.warning(f"[{self.bot_name}] 预加载 lark CreateMessage 类失败: {_e}")
            self._CreateMessageRequest = None
            self._CreateMessageRequestBody = None
        self.client = (
            lark.Client.builder()
            .app_id(self.app_id)
            .app_secret(self.app_secret)
            .log_level(lark.LogLevel.INFO)
            .build()
        )

        # ---- 子进程: 长连接收事件 - 每 bot 独立解释器, loop 干净 ----
        # 事件只回传纯数据(("cmd",open_id,text)/("file",open_id,(msg_id,file_key,name)))
        mp_q = multiprocessing.Queue()
        proc = multiprocessing.Process(
            target=_feishu_ws_worker,
            args=(self.app_id, self.app_secret, self.bot_name, mp_q, _DEBUG),
            daemon=True,
        )
        self._ws_proc = proc
        self._ws_mp_q = mp_q
        log.info(f"▶ [{self.bot_name}] 启动飞书长连接(子进程)")
        proc.start()

        # 主进程 drain 线程: 子进程队列 → Bridge._feishu_to_main(纯数据)
        bridge = self.bridge

        def _drain():
            while True:
                try:
                    item = mp_q.get()
                except (EOFError, OSError):
                    break
                except Exception as e:
                    log.error(f"[{self.bot_name}] drain ws 队列异常: {e}")
                    continue
                try:
                    if item[0] == "cmd":
                        bridge.on_feishu_message(item[1], item[2])
                    elif item[0] == "file":
                        # item = ("file", open_id, (message_id, file_key, file_name))
                        _, open_id, (message_id, file_key, file_name) = item
                        bridge.on_feishu_file(open_id, message_id, file_key, file_name)
                except Exception as e:
                    log.error(f"[{self.bot_name}] 事件入 Bridge 队列失败: {e}")

        t = threading.Thread(target=_drain, daemon=True)
        self._ws_drain_thread = t
        t.start()

    def stop_long_conn(self):
        """停止长连接子进程(热更新 stop 时调用)。"""
        proc = getattr(self, "_ws_proc", None)
        if proc and proc.is_alive():
            try:
                proc.terminate()
                proc.join(timeout=3)
            except Exception as e:
                log.warning(f"[{self.bot_name}] 终止长连接子进程异常: {e}")



def _parse_im_event(bot_name: str, data):
    """解析一条 lark im.message.receive_v1 事件, 返回 (
        ("cmd", open_id, text) | ("file", open_id, (message_id, file_key, file_name)) | None)。
    纯数据导出(无 lark 对象), 供子进程 worker 用。"""
    try:
        event = data.event
        sender = getattr(event, "sender", None)
        sender_id = getattr(sender, "sender_id", None) if sender else None
        open_id = getattr(sender_id, "open_id", None) if sender_id else None
        message = getattr(event, "message", None)
        msg_type = getattr(message, "message_type", "") or ""
        raw_content = getattr(message, "content", "") or ""
        message_id = getattr(message, "message_id", "") or ""
        log.info(f"📨 [{bot_name}] 收到飞书消息: type={msg_type} open_id={open_id}")
        if msg_type == "file":
            try:
                cobj = json.loads(raw_content) if raw_content else {}
            except json.JSONDecodeError:
                cobj = {}
            file_key = cobj.get("file_key", "") or ""
            file_name = cobj.get("file_name", "") or "file"
            if open_id and file_key:
                return ("file", open_id, (message_id, file_key, file_name))
            log.warning(f"[{bot_name}] 文件消息缺 open_id/file_key")
            return None
        text = _extract_text_static(msg_type, raw_content)
        if text:
            log.info(f"📝 [{bot_name}] 飞书文本指令: {text[:100]}")
            return ("cmd", open_id, text)
        log.warning(f"[{bot_name}] 非文本/空消息忽略: type={msg_type}")
        return None
    except Exception as e:
        log.error(f"[{bot_name}] 事件解析异常: {e}")
        return None


def _extract_text_static(msg_type: str, raw_content: str) -> str:
    try:
        obj = json.loads(raw_content) if raw_content else {}
    except json.JSONDecodeError:
        obj = {}
    if msg_type == "text":
        return str(obj.get("text", "") or "").strip()
    return ""


def _feishu_ws_worker(app_id: str, app_secret: str, bot_name: str, out_q, debug: bool):
    """子进程: lark-oapi 长连接收事件, 解析后把纯数据 put 进 multiprocessing.Queue。

    spawn 子进程是全新解释器, import lark_oapi 时 asyncio.get_event_loop() 拿到
    该子进程的干净 loop —— 彻底解决多 bot 共享模块级 loop 的冲突。
    """
    try:
        import lark_oapi as lark
    except ImportError as e:
        raise RuntimeError("未安装 lark-oapi, 请先: pip install lark-oapi") from e

    if debug:
        lk = logging.getLogger("Lark")
        lk.setLevel(logging.DEBUG)
        lk.handlers = []
        _h = logging.StreamHandler()
        _h.setFormatter(logging.Formatter("[Lark] [%(asctime)s] [%(levelname)s] %(message)s"))
        lk.addHandler(_h)

    def on_im_message(data):
        parsed = _parse_im_event(bot_name, data)
        if parsed:
            try:
                out_q.put(parsed)
            except Exception as e:
                log.error(f"[{bot_name}] ws worker 入队失败: {e}")

    handler = (
        lark.EventDispatcherHandler.builder("", "")
        .register_p2_im_message_receive_v1(on_im_message)
        .register_p2_im_chat_access_event_bot_p2p_chat_entered_v1(lambda data: None)
        .register_p2_im_chat_member_bot_added_v1(lambda data: None)
        .register_p2_im_chat_member_bot_deleted_v1(lambda data: None)
        .register_p2_im_message_message_read_v1(lambda data: None)
        .register_p2_im_message_recalled_v1(lambda data: None)
        .register_p2_application_bot_menu_v6(lambda data: None)
        .build()
    )

    level = lark.LogLevel.DEBUG if debug else lark.LogLevel.INFO
    log.info(f"▶ [{bot_name}] ws worker 启动长连接 ...")
    lark.ws.Client(
        app_id, app_secret,
        event_handler=handler,
        log_level=level,
    ).start()


# ═══════════════════════════════════════════════════════════════════
#  BotManager: 多 bot 编排 + 热更新
# ═══════════════════════════════════════════════════════════════════
def _extract_channel(relay_url: str) -> str:
    return relay_url.rstrip("/").rsplit("/", 1)[-1] or "default"


# ═══════════════════════════════════════════════════════════════
#  v3: inbox 自动清理(多 bot 共享单扫描任务, 每个 bot 独立目录)
# ═══════════════════════════════════════════════════════════════
class InboxCleaner:
    """定期清理各 bot 的 inbox_dir。

    多 bot 要点:
    - 每 bot 目录独立, 但**只起一个扫描任务**(在 BotManager 里), 遍历所有 bot 的
      inbox_dir; 热更新增/删 bot 时轮询名单自动跟进, 不重复起任务。
    - 清理策略: ① 超过 max_age_days 的文件删除; ② 若剩余仍超过 max_files,
      按 mtime 从旧到新删到只剩 max_files 个。
    - 只处理普通文件, 不递归(避免误删子目录); 只删本 bot 目录内的直接子文件。
    """

    def __init__(self, inbox_dir: str, enabled=True, max_age_days=7,
                 max_files=500, interval_s=3600, bot_name=""):
        self.inbox_dir = inbox_dir
        self.enabled = bool(enabled)
        self.max_age_days = float(max_age_days) if max_age_days else 0
        self.max_files = int(max_files) if max_files else 0
        self.interval_s = max(60.0, float(interval_s or 3600))
        self.bot_name = bot_name or "bot"

    def sweep_once(self) -> tuple:
        """扫一次, 返回 (删除数, 释放字节数)。异常内部吞掉, 不影响主流程。"""
        removed, freed = 0, 0
        d = self.inbox_dir
        if not d or not os.path.isdir(d):
            return 0, 0
        now = time.time()
        entries = []
        try:
            for fn in os.listdir(d):
                fp = os.path.join(d, fn)
                # 只处理直接子文件; 不递归、不碰目录(防误删)
                if not os.path.isfile(fp):
                    continue
                try:
                    st = os.stat(fp)
                except OSError:
                    continue
                entries.append((fp, st.st_mtime, st.st_size))
        except OSError as e:
            log.warning(f"[{self.bot_name}] 🧹 清理失败(目录不可读): {e}")
            return 0, 0

        # ① 按年龄删
        if self.max_age_days > 0:
            cutoff = now - self.max_age_days * 86400
            for fp, mtime, size in entries:
                if mtime < cutoff:
                    try:
                        os.remove(fp)
                        removed += 1
                        freed += size
                    except OSError:
                        continue
            entries = [(fp, mt, sz) for fp, mt, sz in entries if os.path.exists(fp)]

        # ② 按数量删(保留最新 max_files 个)
        if self.max_files > 0 and len(entries) > self.max_files:
            entries.sort(key=lambda x: x[1])          # 旧 → 新
            for fp, _, size in entries[: len(entries) - self.max_files]:
                try:
                    os.remove(fp)
                    removed += 1
                    freed += size
                except OSError:
                    continue

        if removed:
            log.info(f"[{self.bot_name}] 🧹 inbox 清理 {removed} 个文件, 释放 "
                     f"{freed / 1024:.0f} KB ({self.inbox_dir})")
        return removed, freed


async def inbox_clean_loop(cleaners: list, interval_s: float):
    """统一的 inbox 清理循环(多 bot 共用一个任务)。

    启动 60s 后先扫一次, 之后每 interval_s 扫一遍所有 bot。
    轮询时动态传入 cleaners(热更新增/删 bot 后, BotManager 会更新该列表内容)。
    """
    await asyncio.sleep(60)
    while True:
        try:
            for c in list(cleaners):
                if c.enabled:
                    c.sweep_once()
        except Exception as e:
            log.warning(f"🧹 inbox 清理循环异常: {e}")
        await asyncio.sleep(interval_s)


def _normalize_bot(cfg_bot: dict, http_default_host: str, http_default_port: int, cwd: str,
                   default_cleanup: dict = None) -> dict:
    """把 config 里一个 bot 项补全默认值, 返回规范化字典。

    http_port 默认用共享端口 http_default_port(顶层 http.port);
    若某 bot 单独指定了 http_port 则覆盖之(旧版多端口兼容)。
    default_cleanup: 顶层 cleanup.inbox 默认值, 供本 bot 继承。
    """
    app_id = (cfg_bot.get("app_id") or "").strip()
    app_secret = (cfg_bot.get("app_secret") or "").strip()
    relay_url = (cfg_bot.get("relay_url") or "").strip()
    if not app_id or not app_secret or not relay_url:
        raise ValueError(f"bot 配置缺 app_id/app_secret/relay_url: name={cfg_bot.get('name')}")
    name = (cfg_bot.get("name") or _extract_channel(relay_url)).strip() or "bot"
    channel = _extract_channel(relay_url)
    relay_host = relay_url.split("://", 1)[-1].rsplit(":", 1)[0]
    return {
        "name": name,
        "app_id": app_id,
        "app_secret": app_secret,
        "relay_url": relay_url,
        "channel": channel,
        "http_host": cfg_bot.get("http_host") or http_default_host,
        "http_port": int(cfg_bot.get("http_port") or http_default_port),
        "http_bind_ip": cfg_bot.get("http_bind_ip") or relay_host,
        "inbox_dir": cfg_bot.get("inbox_dir") or os.path.join(cwd, f"inbox_{name}"),
        # v3: inbox 自动清理配置(每 bot 可单独覆盖, 默认继承顶层 cleanup.inbox)
        "cleanup": _normalize_cleanup(cfg_bot.get("cleanup") or {}, default_cleanup),
    }


def _normalize_cleanup(bot_cleanup: dict, default_cleanup: dict) -> dict:
    """归一化单个 bot 的 inbox 清理配置。
    bot.cleanup 里的字段覆盖顶层 cleanup.inbox 默认值; 未给则用默认。
    """
    d = dict(default_cleanup or {})
    if isinstance(bot_cleanup, dict):
        for k, v in bot_cleanup.items():
            if v is not None:
                d[k] = v
    return {
        "enabled": bool(d.get("enabled", True)),
        "max_age_days": float(d.get("max_age_days", 7) or 0),
        "max_files": int(d.get("max_files", 500) or 0),
        "interval_s": float(d.get("interval_s", 3600) or 3600),
    }


def load_config(path: str, http_default_host: str, cwd: str) -> dict:
    """读取 config, 规范化并校验。返回 {reload:{...}, http:{host:...}, bots:[{...}]}。

    兼容旧版单 bot 配置(顶层 app_id/app_secret/relay_url 而非 bots 数组):
    检测到无 bots 但有顶层 relay_url 时, 自动包装成单个 bot。
    """
    with open(path, "r", encoding="utf-8") as f:
        cfg = json.load(f)
    reload_cfg = cfg.get("reload") or {}
    http_cfg = cfg.get("http") or {}
    http_host = http_cfg.get("host") or http_default_host
    http_port = int(http_cfg.get("port") or 8081)
    # v3: inbox 自动清理默认值(顶层 cleanup.inbox); 各 bot 可用自己的 cleanup 覆盖
    _cleanup_cfg = (cfg.get("cleanup") or {}).get("inbox") or {}
    default_cleanup = {
        "enabled": bool(_cleanup_cfg.get("enabled", True)),
        "max_age_days": float(_cleanup_cfg.get("max_age_days", 7) or 0),
        "max_files": int(_cleanup_cfg.get("max_files", 500) or 0),
        "interval_s": float(_cleanup_cfg.get("interval_s", 3600) or 3600),
    }
    raw_bots = cfg.get("bots")
    # 兼容旧版单 bot: 无 bots 数组但有顶层单 bot 字段
    if not raw_bots and (cfg.get("relay_url") or cfg.get("app_id")):
        raw_bots = [{
            "name": cfg.get("name") or "bot",
            "app_id": cfg.get("app_id"),
            "app_secret": cfg.get("app_secret"),
            "relay_url": cfg.get("relay_url"),
            "http_bind_ip": cfg.get("http_bind_ip"),
            "http_port": cfg.get("http_port"),
            "inbox_dir": cfg.get("inbox_dir"),
        }]
    if not isinstance(raw_bots, list):
        raise ValueError("config 缺 bots 数组(或顶层单 bot 的 relay_url/app_id)")
    bots = [_normalize_bot(b, http_host, http_port, cwd, default_cleanup) for b in raw_bots]
    # 校验 name 唯一(URL/通道路由依赖 name)
    names = [b["name"] for b in bots]
    if len(names) != len(set(names)):
        raise ValueError(f"bot name 重复: {names}")
    # http.host/http.port 记入返回(共享文件服务配置)
    http_cfg["host"] = http_host
    http_cfg["port"] = http_port
    return {
        "reload": reload_cfg,
        "http": http_cfg,
        "cleanup": {"inbox": default_cleanup},
        "bots": bots,
    }


# 共享文件服务: 多个 bot 共用单端口(http.host:http.port), 靠 URL 首段 bot 名路由
class FileRouter:
    """单端口 HTTP 文件服务。路由规则:
      GET  /<bot>/inbox/<file>   → 从该 bot 的 inbox_dir 返回文件
      POST /<bot>/upload        → 字节入该 bot 的 upload_queue(回传到对应机器人)
    每个运行的 bot 通过 register() 提供 (inbox_dir, upload_queue)。
    """

    def __init__(self, http_host="0.0.0.0", http_port=8081):
        self.http_host = http_host
        self.http_port = http_port
        self._targets = {}   # bot_name -> (inbox_dir, upload_queue)
        self._lock = threading.Lock()
        self._http_srv = None

    def register(self, bot_name: str, inbox_dir: str, upload_queue):
        with self._lock:
            self._targets[bot_name] = (inbox_dir, upload_queue)

    def unregister(self, bot_name: str):
        with self._lock:
            self._targets.pop(bot_name, None)

    def start(self):
        import http.server
        import urllib.parse as _up
        router = self

        class Handler(http.server.BaseHTTPRequestHandler):
            def log_message(self, *a):
                pass

            def _send(self, code, body=b"", ctype="application/octet-stream"):
                self.send_response(code)
                self.send_header("Content-Type", ctype)
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                if body:
                    self.wfile.write(body)

            def _resolve(self):
                """解析 /<bot>/<rest...> → (bot, rest_path)。"""
                path = _up.urlparse(self.path).path.strip("/")
                if not path:
                    return None, ""
                segs = path.split("/", 1)
                return segs[0], (segs[1] if len(segs) > 1 else "")

            def do_GET(self):
                bot, rest = self._resolve()
                if not bot:
                    self._send(404, b"not found")
                    return
                if not rest.startswith("inbox/"):
                    self._send(404, b"not found")
                    return
                with router._lock:
                    tgt = router._targets.get(bot)
                if not tgt:
                    self._send(404, b"no bot")
                    return
                inbox_dir, _q = tgt
                fname = _up.unquote(os.path.basename(rest))
                full = os.path.join(inbox_dir, fname)
                if not os.path.isfile(full):
                    self._send(404, b"no file")
                    return
                with open(full, "rb") as f:
                    self._send(200, f.read())

            def do_POST(self):
                bot, rest = self._resolve()
                parsed = _up.urlparse(self.path)
                qs = _up.parse_qs(parsed.query)
                if not bot or rest != "upload":
                    self._send(404, b"not found")
                    return
                with router._lock:
                    tgt = router._targets.get(bot)
                if not tgt:
                    self._send(404, b"no bot")
                    return
                _inbox, upload_queue = tgt
                try:
                    length = int(self.headers.get("Content-Length", 0))
                    data = self.rfile.read(length) if length > 0 else b""
                except Exception as e:
                    log.error(f"[{bot}] 读 /upload 请求体失败: {e}")
                    self._send(400, b"read fail")
                    return
                open_id = (qs.get("open_id", [""]))[0]
                name = (qs.get("name", ["file.bin"]))[0]
                upload_queue.put({"open_id": open_id, "data": data, "name": name})
                self._send(200, b"ok")

        self._http_srv = http.server.HTTPServer((self.http_host, self.http_port), Handler)
        t = threading.Thread(target=self._http_srv.serve_forever, daemon=True)
        t.start()
        log.info(f"🌐 共享文件 HTTP 服务已启动: http://{self.http_host}:{self.http_port} (按 /<bot>/ 路由)")

    def stop(self):
        if self._http_srv:
            try:
                self._http_srv.shutdown()
            except Exception:
                pass


# 运行中的单个机器人节点
class BotNode:
    def __init__(self, bot: dict, router: FileRouter):
        self.bot = bot
        self.name = bot["name"]
        self.router = router
        self.bridge = None
        self.feishu = None
        self._relay = None
        self._feishu_thread = None
        self.inbox_cleaner = None

    async def start(self):
        bot = self.bot
        bridge_holder = {}

        async def _relay_cb(msg):
            b = bridge_holder.get("bridge")
            if b:
                await b.on_relay_message(msg)

        relay = RelayNlpClient(bot["relay_url"], bot["channel"], bot["name"], _relay_cb)
        bridge = Bridge(bot["name"], None, relay,
                        http_host=bot["http_host"], http_port=bot["http_port"],
                        inbox_dir=bot["inbox_dir"], http_bind_ip=bot["http_bind_ip"])
        bridge_holder["bridge"] = bridge

        feishu = FeishuClient(bot["app_id"], bot["app_secret"], bot["name"], bridge)
        bridge.feishu = feishu

        self.bridge = bridge
        self.feishu = feishu
        self._relay = relay

        # v3: 本 bot 的 inbox 清理器(由 BotManager 统一轮询, 不单独起任务)
        c = bot.get("cleanup") or {}
        self.inbox_cleaner = InboxCleaner(
            bot["inbox_dir"],
            enabled=c.get("enabled", True),
            max_age_days=c.get("max_age_days", 7),
            max_files=c.get("max_files", 500),
            interval_s=c.get("interval_s", 3600),
            bot_name=bot["name"],
        )

        # 注册到共享文件服务(多 bot 共用单端口, 靠 /<bot>/ 路由)
        bridge.register_file_service(queue.Queue())
        self.router.register(bot["name"], bot["inbox_dir"], bridge._upload_queue)
        # 飞书长连接在独立 multiprocessing 子进程跑(每 bot 独立解释器, loop 干净)
        feishu.start_long_conn()
        # 主循环作为 asyncio task
        self.run_task = asyncio.create_task(bridge.run())
        log.info(f"🚀 [{self.name}] 机器人已启动: relay={bot['relay_url']}" +
                 (f" | inbox清理: {'开' if self.inbox_cleaner.enabled else '关'}"
                  f"(>{self.inbox_cleaner.max_age_days:g}天/{self.inbox_cleaner.max_files}个)"
                  if self.inbox_cleaner.enabled else " | inbox清理: 关"))

    async def stop(self):
        """停掉该机器人: 停 relay 任务、取消 run_task、终止长连接子进程、注销路由。"""
        if self.bridge:
            await self.bridge.stop()
        if self.feishu:
            self.feishu.stop_long_conn()
        if self.run_task:
            self.run_task.cancel()
            try:
                await self.run_task
            except (asyncio.CancelledError, Exception):
                pass
        self.router.unregister(self.name)
        log.info(f"🛑 [{self.name}] 机器人已停止")


# 多 bot 编排 + 热更新
class BotManager:
    def __init__(self, bots: list, router: FileRouter, loop: asyncio.AbstractEventLoop):
        self.loop = loop
        self.router = router
        self.bots: dict[str, BotNode] = {}   # key = bot name
        for b in bots:
            self.bots[b["name"]] = BotNode(b, router)

    async def start_all(self):
        for name, node in self.bots.items():
            await node.start()

    async def apply_diff(self, wanted: list):
        """对比期望 bots 列表, 对运行中的做增/删/改。返回是否发生变化。"""
        changed = False
        wanted_map = {b["name"]: b for b in wanted}
        cur_names = set(self.bots.keys())
        new_names = set(wanted_map.keys())

        # ① 删除
        for name in list(cur_names - new_names):
            log.info(f"🔄 [{name}] config 已移除, 停止该机器人")
            await self.bots[name].stop()
            del self.bots[name]
            changed = True

        # ② 改动
        for name in (cur_names & new_names):
            old = self.bots[name].bot
            new = wanted_map[name]
            if old != new:
                log.info(f"🔄 [{name}] 配置变化, 重启该机器人")
                await self.bots[name].stop()
                node = BotNode(new, self.router)
                self.bots[name] = node
                await node.start()
                changed = True

        # ③ 新增
        for name in (new_names - cur_names):
            log.info(f"🟢 [{name}] config 新增, 启动该机器人")
            node = BotNode(wanted_map[name], self.router)
            self.bots[name] = node
            await node.start()
            changed = True

        return changed

    async def hot_reload_loop(self, config_path: str, interval: float, http_host: str, http_port: int, cwd: str):
        """定期重读 config, diff 并增删改机器人。"""
        while True:
            try:
                cfg = load_config(config_path, http_host, cwd)
                await self.apply_diff(cfg["bots"])
            except Exception as e:
                log.error(f"⚠️ 热更新读取/应用失败(下次重试): {e}")
            await asyncio.sleep(interval)

    @property
    def cleaners(self) -> list:
        """当前运行中的各 bot 的 inbox 清理器(随热更新增删自动跟进)。"""
        return [n.inbox_cleaner for n in self.bots.values() if n.inbox_cleaner]

    async def stop_all(self):
        for name, node in list(self.bots.items()):
            await node.stop()


async def main():
    parser = argparse.ArgumentParser(description="飞书 ↔ nlp_worker(copilot) 桥 v3(多 bot + 热更新)")
    parser.add_argument("--config", default="feishu_config.json", help="配置文件路径")
    parser.add_argument("--debug", action="store_true")
    args = parser.parse_args()
    if args.debug:
        global _DEBUG
        _DEBUG = True
        logging.getLogger().setLevel(logging.DEBUG)

    loop = asyncio.get_running_loop()
    http_default_host = "0.0.0.0"
    cwd = os.getcwd()

    # 首次加载 config (load_config 已兼容旧版单 bot 配置)
    cfg = load_config(args.config, http_default_host, cwd)

    reload_cfg = cfg.get("reload") or {}
    reload_enabled = reload_cfg.get("enabled", True)
    watch_interval = float(reload_cfg.get("watch_interval_s") or 3)

    # 共享文件服务: 多 bot 共用单端口, 靠 /<bot>/ 路由
    http_cfg = cfg.get("http") or {}
    router = FileRouter(http_host=http_cfg.get("host", http_default_host),
                        http_port=int(http_cfg.get("port") or 8081))
    router.start()

    mgr = BotManager(cfg["bots"], router, loop)
    await mgr.start_all()
    log.info(f"🚀 桥启动: {len(mgr.bots)} 个机器人")

    # v3: inbox 自动清理(多 bot 只起一个扫描任务, 遍历所有 bot 的 inbox_dir)
    _ck_interval = float((cfg.get("cleanup") or {}).get("inbox", {}).get("interval_s", 3600) or 3600)
    mgr.clean_loop_interval = _ck_interval
    cleaner_task = asyncio.create_task(inbox_clean_loop(mgr.cleaners, _ck_interval))
    _any = any(c.enabled for c in mgr.cleaners)
    log.info(f"🧹 inbox 自动清理{'已开启' if _any else '已关闭'}: 每 {_ck_interval / 60:.0f} 分钟扫一遍 "
             f"({len(mgr.cleaners)} 个 bot 的 inbox)")

    # 热更新 watcher
    if reload_enabled:
        watcher = asyncio.create_task(
            mgr.hot_reload_loop(args.config, watch_interval, http_cfg.get("host", http_default_host),
                                http_cfg.get("port") or 8081, cwd))
        log.info(f"🔄 热更新已开启: 每 {watch_interval}s 重读 {args.config}")

    try:
        while True:
            await asyncio.sleep(3600)
    except KeyboardInterrupt:
        pass
    finally:
        await mgr.stop_all()
        router.stop()


if __name__ == "__main__":
    # ── PyInstaller + multiprocessing 兼容 ──
    # exe 子进程会以 `--multiprocessing-fork parent_pid=.. pipe_handle=..` 重新启动自身,
    # 这些参数必须交给 multiprocessing 内部处理, 不能进 main() 的 argparse。
    import multiprocessing as _mp
    _mp.freeze_support()
    # 双保险: 显式移除整段 `--multiprocessing-fork <v> <v>` (freeze_support 在某些打包环境不裁剪 argv)
    import sys as _sys
    _argv = _sys.argv
    _cleaned = []
    _skip = 0
    for _i, _a in enumerate(_argv):
        if _skip:
            _skip -= 1
            continue
        if _a == "--multiprocessing-fork":
            _skip = 2  # 跳过紧随的两个值: parent_pid=.. pipe_handle=..
            continue
        _cleaned.append(_a)
    _sys.argv = _cleaned
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
