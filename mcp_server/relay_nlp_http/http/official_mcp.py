#!/usr/bin/env python3
"""
官方 Kanzi MCP HTTP 客户端（api / doc）—— 轻量 streamable-HTTP MCP 客户端。

供 kz_mcp_http.py（三端点聚合网关）与 nlp_worker_acp.py（worker 内置查询）共用。
- initialize 拿 session id
- tools/call 拿工具结果（单次请求拉全 SSE）
- sid 失效（404/报错）自动重连后重试一次

Kanzi 官方 api-MCP 工具: list_apis / set_kanzi_version / search_kanzi_api /
    get_method_signature / get_include / get_class_reference /
    get_deprecation_warnings / compare_versions / get_api_history
Kanzi 官方 doc-MCP 工具: list_versions / set_version / search_docs /
    ask_question / get_page / search_across_versions / compare_versions /
    ask_kanzi_question / search_kanzi_sources
"""
import asyncio
import json
import logging

log = logging.getLogger("official-mcp")

# api-MCP 官方端点（根路径 /）
KANZI_API_MCP_URL = "https://api.mcp.kanzi.com/"
# doc-MCP 官方端点（/mcp）
KANZI_DOC_MCP_URL = "https://docs.mcp.kanzi.com/mcp"


class OfficialMcpHttpClient:
    def __init__(self, name, url, timeout=20, fresh_each_call=False):
        self.name = name           # 如 kanzi-api-mcp / kanzi-doc-mcp
        self.url = url
        self.timeout = timeout
        # ★ 严格短 session 端点(doc-mcp)设为 True: 每次调用前都重新 initialize 拿新 sid,
        #   彻底避免复用可能已失效的旧 sid 导致 404。api 稳定可复用 sid 省往返。
        self.fresh_each_call = fresh_each_call
        self.sid = None
        self._lock = asyncio.Lock()

    async def _post(self, payload, with_sid=False, retry_sid=True, _max_retry=3):
        """POST 一条 JSON-RPC 到 MCP 端点, 返回完整 SSE 响应文本。
        session 失效(404)时强制重连换新 sid, 最多 _max_retry 次(不像旧版只重试一次
        导致 doc 这类严格端点重连后仍 404 直接失败)。"""
        from urllib.request import Request, urlopen
        import urllib.error
        data = json.dumps(payload).encode()
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
        }
        if with_sid and self.sid:
            headers["Mcp-Session-Id"] = self.sid
        req = Request(self.url, data=data, method="POST")
        for k, v in headers.items():
            req.add_header(k, v)
        try:
            body = await asyncio.get_event_loop().run_in_executor(
                None, self._urllib_open, req)
            return body
        except urllib.error.HTTPError as e:
            if e.code == 404 and with_sid:
                # session 失效: 强制重连换新 sid 多次重试(doc 严格端点重连后仍可能失效)
                log.info(f"🌐 {self.name} session 失效(404), 自动重连...")
                for attempt in range(_max_retry):
                    try:
                        await self._init()
                    except Exception as ie:
                        log.warning(f"   {self.name} 重连 initialize 失败({attempt+1}): {ie}")
                        continue
                    if not self.sid:
                        log.warning(f"   {self.name} 重连未拿到新 sid({attempt+1})")
                        continue
                    try:
                        return await self._post(
                            payload, with_sid=True, retry_sid=False, _max_retry=0)
                    except urllib.error.HTTPError as e2:
                        if e2.code == 404:
                            log.info(f"   {self.name} 重连后仍 404({attempt+1}), 再换新 sid")
                            continue
                        raise
                raise
            if e.code == 404 and not with_sid:
                raise
            raise

    @staticmethod
    def _urllib_open(req):
        from urllib.request import urlopen
        with urlopen(req, timeout=25) as resp:
            return resp.read().decode("utf-8", "replace")

    async def _init(self):
        """initialize 并保存 session id。"""
        payload = {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {
            "protocolVersion": "2025-03-26",
            "capabilities": {},
            "clientInfo": {"name": "nlp-worker", "version": "1.0"},
        }}
        from urllib.request import Request, urlopen
        data = json.dumps(payload).encode()
        req = Request(self.url, data=data, method="POST")
        req.add_header("Content-Type", "application/json")
        req.add_header("Accept", "application/json, text/event-stream")
        sid = None
        body = ""
        def _open():
            nonlocal sid, body
            with urlopen(req, timeout=25) as resp:
                sid = resp.headers.get("Mcp-Session-Id") or resp.headers.get("mcp-session-id")
                body = resp.read().decode("utf-8", "replace")
        await asyncio.get_event_loop().run_in_executor(None, _open)
        self.sid = sid
        if not self.sid:
            # ★ 严格端点必须拿到新 sid, 否则后续重试仍会 404
            raise RuntimeError(f"{self.name} initialize 未返回 Mcp-Session-Id")
        try:
            self._parse_result(body, 1)  # 解析确认无错
        except Exception:
            pass
        return sid

    @staticmethod
    def _parse_result(body, rid):
        """从 SSE 文本里取 id==rid 的 message 的 result(或抛 error)。"""
        text = body
        msgs = []
        for line in text.splitlines():
            line = line.strip()
            if line.startswith("data:"):
                line = line[5:].strip()
            if line.startswith("{") and line.rstrip().endswith("}"):
                try:
                    msgs.append(json.loads(line))
                except Exception:
                    pass
            else:
                try:
                    if line.startswith("{"):
                        msgs.append(json.loads(line))
                except Exception:
                    pass
        if not msgs:
            try:
                msgs.append(json.loads(text))
            except Exception:
                raise RuntimeError(f"无法解析 MCP 响应: {text[:200]}")
        for m in msgs:
            if m.get("id") == rid or m.get("id") == str(rid):
                if "error" in m:
                    raise RuntimeError(f"MCP 错误 {self_err(m)}")
                return m.get("result", {})
        for m in reversed(msgs):
            if "result" in m:
                return m["result"]
        raise RuntimeError(f"未找到 result (id={rid}): {text[:300]}")

    async def call_raw(self, tool, args=None):
        """调用工具返回原始 result dict; 失效自动重连重试。
        fresh_each_call=True(严格端点/dock)时每次调用前强制重新 initialize 拿新 sid,
        从源头避免复用过期 sid 导致 404。"""
        args = args or {}
        async with self._lock:
            if self.fresh_each_call or not self.sid:
                await self._init()
            payload = {"jsonrpc": "2.0", "id": 2, "method": "tools/call",
                       "params": {"name": tool, "arguments": args}}
            try:
                body = await self._post(payload, with_sid=True)
                return self._parse_result(body, 2)
            except Exception as e:
                if self.sid:
                    log.info(f"🌐 {self.name} 调用失败, 重连后重试: {e}")
                    self.sid = None
                    await self._init()
                    return await self.call_raw(tool, args)
                raise

    async def tools(self, refresh=False):
        """拉取工具清单(缓存)。返回 [(name, description, inputSchema), ...]。"""
        if refresh or not getattr(self, "_tools_cache", None):
            try:
                r = await self.list_tools()
            except Exception as e:
                log.info(f"ℹ {self.name} 工具清单拉取失败: {e}")
                r = None
            tooldict = (r or {}).get("tools", []) if isinstance(r, dict) else []
            self._tools_cache = [
                {"name": t.get("name", ""),
                 "description": t.get("description", ""),
                 "inputSchema": t.get("inputSchema", {"type": "object", "properties": {}})}
                for t in tooldict if isinstance(t, dict)
            ]
        return self._tools_cache

    async def list_tools(self, refresh_sid_ok=True):
        """用 tools/list 方法拉取官方工具清单(非 tools/call)。"""
        async with self._lock:
            if self.fresh_each_call or not self.sid:
                await self._init()
            payload = {"jsonrpc": "2.0", "id": 9, "method": "tools/list", "params": {}}
            try:
                body = await self._post(payload, with_sid=True)
                return self._parse_result(body, 9)
            except Exception as e:
                if self.sid:
                    log.info(f"🌐 {self.name} tools/list 失败, 重连后重试: {e}")
                    self.sid = None
                    await self._init()
                    return await self.list_tools(refresh_sid_ok=False)
                raise

    async def keepalive(self):
        """连通性探活(供启动时后台调用)。"""
        try:
            await self._init()
            return True
        except Exception:
            return False


def self_err(m):
    err = m.get("error", {})
    if isinstance(err, dict):
        return err.get("message", str(err))
    return str(err)
