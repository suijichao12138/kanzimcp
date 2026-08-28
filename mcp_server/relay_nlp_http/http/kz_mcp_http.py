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

    每个用户一条连接, URL = <relay_base>/<username>。
    Kanzi server 未启动时, relay 会拒绝(4001) —— 程序重连直到 server 上线。
    """

    def __init__(self, relay_url: str, username: str):
        self.relay_url = relay_url
        self.username = username
        self.ws = None
        self.running = False
        self.on_message = None  # 回调: func(raw_msg_str)

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

                    async for raw in ws:
                        if self.on_message:
                            await self.on_message(raw)

            except websockets.ConnectionClosed as e:
                if e.code == 4001:
                    log.warning(f"🔌 [{self.username}] server 不在线, 5秒后重试...")
                else:
                    log.warning(f"🔌 [{self.username}] 中继连接断开, 3秒后重连...")
            except Exception as e:
                log.error(f"❌ [{self.username}] 连接错误: {e}")

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
    """单用户的 MCP 请求代理: 裸 JSON-RPC 经 client 槽转发到 Kanzi server。"""

    def __init__(self, relay: RelayClient, username: str, request_timeout=300.0):
        self.relay = relay
        self.username = username
        self.request_timeout = request_timeout
        self.pending = {}
        self._lock = asyncio.Lock()

    async def relay_request(self, req: dict, timeout=None) -> dict:
        if timeout is None:
            timeout = self.request_timeout
        req_id = str(req.get("id"))
        fut = asyncio.get_event_loop().create_future()
        async with self._lock:
            self.pending[req_id] = fut
        try:
            if not self.relay.ws:
                return {"jsonrpc": "2.0", "id": req_id,
                        "error": {"code": -32000,
                                  "message": f"用户 {self.username} 的 Kanzi 未连接(server 可能未启动)"}}
            await self.relay.send(req)
            try:
                return await asyncio.wait_for(fut, timeout=timeout)
            except asyncio.TimeoutError:
                return {"jsonrpc": "2.0", "id": req_id,
                        "error": {"code": -32000, "message": "MCP 请求超时"}}
        finally:
            async with self._lock:
                self.pending.pop(req_id, None)

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
            req_id = str(response.get("id"))
        elif isinstance(data, dict) and "id" in data:
            response = data
            req_id = str(data.get("id"))
        else:
            return
        async with self._lock:
            fut = self.pending.get(req_id)
            if fut and not fut.done():
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
                 config_path: str = None):
        self.relay_base = relay_base.rstrip("/")
        self.request_timeout = request_timeout
        self._config_path = config_path
        self._last_mtime = None
        self.allowed = allowed_users
        # 记录初始 mtime, 保证首次 _reload 不重复读
        if config_path:
            try:
                self._last_mtime = os.path.getmtime(config_path)
            except OSError:
                pass
        self.connections = {}   # user -> (RelayClient, McpProxyHandler)

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
        # 新用户没启动过连接则维持懒加载; 被移除用户的连接停止释放
        for u in rm:
            conn = self.connections.pop(u, None)
            if conn:
                relay, _ = conn
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

    def _ensure(self, username: str):
        if username not in self.connections:
            url = f"{self.relay_base}/{username}"
            relay = RelayClient(url, username)
            handler = McpProxyHandler(relay, username, self.request_timeout)
            relay.on_message = handler.handle_mcp_response
            self.connections[username] = (relay, handler)
        return self.connections[username]

    async def start_user(self, username: str):
        relay, _ = self._ensure(username)
        if not relay.running:
            await relay.start()
        return self.connections[username]

    def get_handler(self, username: str):
        return self._ensure(username)[1]

    async def stop_all(self):
        for relay, _ in self.connections.values():
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

    def __init__(self, user_manager: UserManager, host="127.0.0.1", port=9001, url_path="/mcp"):
        self.users = user_manager
        self.host = host
        self.port = port
        self.url_path = url_path
        self.server = None
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

            # 路径路由: 官方端点(/kanzi_api_mcp / /kanzi_doc_mcp)或其他(studio: /mcp / / /kanzistudio_mcp)
            path_norm = path.rstrip("/")
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

        # 需要 Kanzi 连接的操作 → 确保该用户 client 已连接
        handler = self.users.get_handler(username)
        # 懒加载启动(首次请求时建连; start() 已改为后台任务, 立即返回)
        relay, _ = self.users.connections.get(username, (None, None))
        if relay and not relay.running:
            await self.users.start_user(username)
        # 等 client 槽真正连上中继(与 Kanzi server 直通), 避免首请求发空
        try:
            await asyncio.wait_for(relay.wait_connected(3.0), timeout=4.0)
        except (asyncio.TimeoutError, Exception):
            # server 未上线时 relay 会 4001 拒连, 这里不抛错, 让下方 fallback
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
            return await handler.relay_request(forward_req)

        return {"jsonrpc": "2.0", "id": req_id, "result": {}}

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
#  入口
# ═══════════════════════════════════════════════════════════════════
async def main():
    parser = argparse.ArgumentParser(description="单进程多用户 Kanzi MCP over HTTP server")
    parser.add_argument("--relay-base", required=True,
                       help="中继地址基座(不含用户名), 如 ws://127.0.0.1:58080 —— 每个用户连接 <base>/<用户名>")
    parser.add_argument("--users", required=True,
                       help="白名单配置文件(JSON, 含 users 数组), 如 users.json")
    parser.add_argument("--listen", default="0.0.0.0:9001",
                       help="HTTP MCP server 监听 主机:端口 (默认 0.0.0.0:9001; 需远程 copilot 访问时用 0.0.0.0, 仅本机调试才用 127.0.0.1)")
    parser.add_argument("--mcp-timeout", type=int, default=300,
                       help="MCP 转发到 Kanzi 的单次请求超时秒数 (默认 300; Kanzi 创建慢时可调大)")
    parser.add_argument("--debug", action="store_true", help="开启调试日志")
    args = parser.parse_args()

    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)

    host, _, port_str = args.listen.partition(":")
    port = int(port_str or "9001")

    allowed = load_users(args.users)
    if not allowed:
        log.error("白名单为空, 拒绝启动")
        sys.exit(1)

    manager = UserManager(args.relay_base, allowed, request_timeout=args.mcp_timeout,
                          config_path=args.users)
    http_mcp = HttpMcpServer(manager, host, port)
    await http_mcp.start()

    log.info(f"🚀 kz_mcp_http.py 已就绪 (单进程多用户)")
    log.info(f"   relay 基座: {args.relay_base}")
    log.info(f"   白名单: {sorted(allowed)}")
    log.info(f"   ★ 白名单热更新: 编辑 {args.users} 保存后即时生效, 无需重启 kz_mcp_http.py / nlp_worker")
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
