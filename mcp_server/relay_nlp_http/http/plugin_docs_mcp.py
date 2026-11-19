#!/usr/bin/env python3
"""
plugin_docs_mcp.py —— 本地 Kanzi 插件文档 MCP 处理器。

让 nlp_worker 的 Copilot 能查询本地 kanzi_plugins 目录里各插件的自带帮助文档
（Sphinx 生成的 doc 目录，.md 源文件或 .html）。挂在 kz_mcp_http.py 的
/kanzi_plugin_doc_mcp 端点上，与 /kanzi_skill_mcp 同模式。

特性：
- 目录即插件：<plugins_root>/<插件名>/doc[/html] 自动发现，无需登记
- 自动识别文档形态：.md 源文件优先；纯 HTML 用 html2text 转纯文本（质量高）
- 增量索引：扫描 mtime 变化自动重建，新插件/更新无需重启
- 三个工具：list_plugins / search_plugin_docs / get_plugin_page
"""
import logging
import os
import re
import time

log = logging.getLogger("plugin-docs-mcp")

try:
    import html2text
    _HAS_HTML2TEXT = True
except ImportError:
    _HAS_HTML2TEXT = False


def _extract_text_from_html(path: str, max_chars: int = 200_000) -> str:
    """HTML → 纯文本（三方库 html2text 优先，fallback 到正则剥离）。"""
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            html = f.read()
    except OSError:
        return ""
    if _HAS_HTML2TEXT:
        try:
            h = html2text.HTML2Text()
            h.ignore_links = True
            h.ignore_images = True
            h.body_width = 0
            text = h.handle(html)
        except Exception:  # noqa: BLE001
            text = ""
    else:
        # 简易 fallback：剥 script/style/标签，保留标题与段落
        text = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", "", html)
        text = re.sub(r"(?s)<h([1-6])[^>]*>", r"\n\n### ", text)
        text = re.sub(r"(?s)<p[^>]*>", "\n\n", text)
        text = re.sub(r"(?s)<pre[^>]*>", "\n\n```\n", text)
        text = re.sub(r"(?s)</pre>", "\n```\n", text)
        text = re.sub(r"(?s)<li[^>]*>", "\n- ", text)
        text = re.sub(r"<[^>]+>", "", text)
        text = re.sub(r"&nbsp;?", " ", text)
        text = re.sub(r"&lt;", "<", text)
        text = re.sub(r"&gt;", ">", text)
        text = re.sub(r"&amp;", "&", text)
        text = re.sub(r"&quot;", '"', text)
        text = re.sub(r"&#39;", "'", text)
        text = re.sub(r"&[a-z]+;", " ", text)
        text = re.sub(r"[ \t]+", " ", text)
        text = re.sub(r"\n{3,}", "\n\n", text)
    text = text.strip()
    if len(text) > max_chars:
        text = text[:max_chars] + "\n...[截断]"
    return text


class PluginDocsHandler:
    """本地插件文档 MCP JSON-RPC 处理器（同 SkillsMcpHandler 模式）。"""

    def __init__(self, plugins_root: str | os.PathLike):
        self.plugins_root = str(plugins_root)
        self._index_mtime = 0.0
        self._index: dict[str, dict] = {}   # plugin -> {"name","pages":[{"id","title","path","kind","size"}]}
        self._scan_plugins()

    # ---------- 索引 ----------
    def _find_doc_recursive(self, base: str, depth: int = 0) -> str | None:
        """递归找 doc 目录（限 depth 层）。返回第一个含 doc 的路径；没有返回 None。"""
        direct = os.path.join(base, "doc")
        if os.path.isdir(direct):
            return direct
        if depth >= 2:
            return None
        try:
            for sub in sorted(os.listdir(base)):
                sp = os.path.join(base, sub)
                if os.path.isdir(sp) and not sub.startswith("."):
                    found = self._find_doc_recursive(sp, depth + 1)
                    if found:
                        return found
        except OSError:
            pass
        return None

    def _plugin_dirs(self) -> list[str]:
        """扫描根目录下每个插件子目录（含 doc 的才算）。
        兼容 doc 嵌套在子目录的情况（如 kzmonitor-src/monitor/doc）。"""
        out = []
        try:
            names = sorted(os.listdir(self.plugins_root))
        except OSError:
            return out
        for n in names:
            p = os.path.join(self.plugins_root, n)
            if not os.path.isdir(p) or n.startswith("."):
                continue
            if self._find_doc_recursive(p):
                out.append(n)
        return out

    def _resolve_doc_root(self, plugin: str) -> str:
        """找插件 doc 根（递归，最多 2 层子目录）。"""
        p = os.path.join(self.plugins_root, plugin)
        found = self._find_doc_recursive(p)
        return found or os.path.join(p, "doc")  # 不存在则返回原路径（collect 得空）

    def _scan_plugins(self):
        """全量扫描：每个插件收集页面（.md 优先；无 .md 收 .html）。"""
        index: dict[str, dict] = {}
        for plugin in self._plugin_dirs():
            doc_root = self._resolve_doc_root(plugin)
            pages = self._collect_pages(plugin, doc_root)
            if not pages:
                continue
            index[plugin] = {
                "name": plugin,
                "root": doc_root,
                "pages": pages,
                "page_count": len(pages),
                "mtime": os.path.getmtime(doc_root),
            }
        self._index = index
        self._index_mtime = time.time()

    def _collect_pages(self, plugin: str, doc_root: str) -> list[dict]:
        """递归收集 .md（优先）或 .html 页面；跳过 _static/_images/.doctrees。"""
        pages: list[dict] = []
        skip_dirs = {"_static", "_images", ".doctrees", "_sources", "searchindex.js"}
        for root, dirs, files in os.walk(doc_root):
            dirs[:] = [d for d in dirs if d not in skip_dirs]
            for f in files:
                if f.startswith("."):
                    continue
                ext = os.path.splitext(f)[1].lower()
                if ext not in (".md", ".html", ".htm"):
                    continue
                full = os.path.join(root, f)
                rel = os.path.relpath(full, doc_root).replace("\\", "/")
                kind = "md" if ext in (".md",) else "html"
                try:
                    size = os.path.getsize(full)
                except OSError:
                    size = 0
                pages.append({
                    "id": rel,
                    "title": rel,
                    "path": full,
                    "kind": kind,
                    "size": size,
                })
        # .md 优先：若存在同名 .md 则剔除对应 .html，避免重复
        md_ids = {p["id"][:-3] for p in pages if p["kind"] == "md"}
        pages = [p for p in pages if not (p["kind"] == "html" and p["id"][:-5] in md_ids)]
        pages.sort(key=lambda p: p["id"])
        return pages

    def _ensure_fresh(self):
        """mtime 变化时重建索引（新插件/更新 doc 无需重启）。"""
        try:
            root_mtime = os.path.getmtime(self.plugins_root)
        except OSError:
            return
        if root_mtime > self._index_mtime:
            self._scan_plugins()

    def _search_all(self, query: str, limit: int = 10) -> list[dict]:
        """跨插件全文搜索：标题命中优先，正文子串命中次之。"""
        q = query.strip().lower()
        if not q:
            return []
        hits: list[dict] = []
        qlen = len(q)
        for plugin, info in self._index.items():
            for pg in info["pages"]:
                title = pg["title"].lower()
                title_score = 0
                if q in title:
                    title_score = 2 + (1 if title.startswith(q) else 0)
                # 正文抽查（只读前 60KB 加速）
                body = ""
                try:
                    if pg["kind"] == "md":
                        with open(pg["path"], "r", encoding="utf-8", errors="replace") as f:
                            body = f.read(60_000)
                    else:
                        body = _extract_text_from_html(pg["path"], 60_000)
                except OSError:
                    body = ""
                bl = body.lower()
                if q in bl:
                    # 取首次命中位置附近片段
                    idx = bl.find(q)
                    start = max(0, idx - 80)
                    snippet = body[start: idx + qlen + 120].replace("\n", " ")
                    snippet = re.sub(r"\s+", " ", snippet)
                    score = 1 + title_score
                    hits.append({
                        "plugin": plugin,
                        "page": pg["id"],
                        "title": title,
                        "kind": pg["kind"],
                        "score": score,
                        "snippet": snippet[:200],
                    })
        hits.sort(key=lambda h: (-h["score"], h["plugin"], h["page"]))
        return hits[:limit]

    # ---------- 工具 ----------
    def _tool_list_plugins(self) -> dict:
        return {
            "plugins": [
                {
                    "name": p,
                    "page_count": info["page_count"],
                    "root": info["root"],
                }
                for p, info in sorted(self._index.items())
            ],
            "total": len(self._index),
            "plugins_root": self.plugins_root,
        }

    def _tool_search(self, query: str, limit: int) -> dict:
        hits = self._search_all(query, limit)
        return {"query": query, "hits": hits, "count": len(hits)}

    def _tool_get_page(self, plugin: str, page: str, max_chars: int) -> dict:
        info = self._index.get(plugin)
        if not info:
            return {"error": f"插件不存在: {plugin}（可用 list_plugins 查看）"}
        target = None
        for pg in info["pages"]:
            if pg["id"] == page or pg["id"].endswith("/" + page):
                target = pg
                break
        if target is None:
            pages = [p["id"] for p in info["pages"]]
            return {"error": f"页面不存在: {page}。该插件页面清单（前 50）: {pages[:50]}"}
        try:
            if target["kind"] == "md":
                with open(target["path"], "r", encoding="utf-8", errors="replace") as f:
                    content = f.read(max_chars)
            else:
                content = _extract_text_from_html(target["path"], max_chars)
        except OSError as e:
            return {"error": f"读取失败: {e}"}
        return {
            "plugin": plugin,
            "page": target["id"],
            "kind": target["kind"],
            "content": content,
        }

    # ---------- MCP 入口 ----------
    def handle(self, req: dict) -> dict:
        if not isinstance(req, dict) or "method" not in req:
            return self._error(-32600, "Invalid Request", req)
        method = req.get("method", "")
        rid = req.get("id")
        if method == "initialize":
            return {"jsonrpc": "2.0", "id": rid, "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {"listChanged": False}},
                "serverInfo": {"name": "kanzi-plugin-doc-mcp", "version": "1.0.0"},
            }}
        if method == "notifications/initialized":
            return None
        if method == "ping":
            return {"jsonrpc": "2.0", "id": rid, "result": {}}
        if method == "tools/list":
            return {"jsonrpc": "2.0", "id": rid, "result": {"tools": TOOLS}}
        if method == "tools/call":
            return self._call(req)
        return self._error(-32601, f"未知方法: {method}", req)

    def _call(self, req: dict) -> dict:
        params = req.get("params") or {}
        name = params.get("name", "")
        args = params.get("arguments") or {}
        rid = req.get("id")
        try:
            self._ensure_fresh()
            if name == "list_plugins":
                result = self._tool_list_plugins()
            elif name == "search_plugin_docs":
                result = self._tool_search(str(args.get("query", "")),
                                           int(args.get("limit", 10) or 10))
            elif name == "get_plugin_page":
                result = self._tool_get_page(str(args.get("plugin", "")),
                                             str(args.get("page", "")),
                                             int(args.get("max_chars", 20000) or 20000))
            else:
                return self._error(-32602, f"未知工具: {name}", req)
        except Exception as e:  # noqa: BLE001
            return self._error(-32603, f"工具执行失败: {e}", req)
        return {"jsonrpc": "2.0", "id": rid, "result": {
            "content": [{"type": "text", "text": _json_str(result)}],
            "structuredContent": result,
        }}

    @staticmethod
    def _error(code, message, req):
        return {"jsonrpc": "2.0", "id": req.get("id") if isinstance(req, dict) else None,
                "error": {"code": code, "message": message}}


TOOLS = [
    {
        "name": "list_plugins",
        "description": "列出本地已收录的 Kanzi 插件文档（插件名、页面数）。查询插件能力/文档前先看有哪些插件可用。",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "search_plugin_docs",
        "description": "跨所有本地插件文档全文搜索，返回命中页面与片段。关键词支持中文/英文（如 '地图' / 'navigation' / 'monitor'）。查插件用法/配置/API 用这个。",
        "inputSchema": {"type": "object",
                        "properties": {
                            "query": {"type": "string", "description": "搜索关键词，如 'mapbox' / '加载' / 'profiling'"},
                            "limit": {"type": "integer", "description": "返回条数上限，默认 10，最大 20"},
                        },
                        "required": ["query"]},
    },
    {
        "name": "get_plugin_page",
        "description": "返回某插件某页文档全文（.md 源或 HTML 转文本）。先 search_plugin_docs 找到 page 再取全文，不要反复猜页名。",
        "inputSchema": {"type": "object",
                        "properties": {
                            "plugin": {"type": "string", "description": "插件名（list_plugins 返回的 name）"},
                            "page": {"type": "string", "description": "页面 id（search_plugin_docs 返回的 page，如 'index.md' 或 'working-with/xxx.html'）"},
                            "max_chars": {"type": "integer", "description": "最大返回字符数，默认 20000"},
                        },
                        "required": ["plugin", "page"]},
    },
]


def _json_str(obj: dict) -> str:
    import json
    return json.dumps(obj, ensure_ascii=False, indent=1)


if __name__ == "__main__":
    # 自检：python plugin_docs_mcp.py <plugins_root> <query>
    import sys
    root = sys.argv[1] if len(sys.argv) > 1 else "."
    h = PluginDocsHandler(root)
    print("插件:", _json_str(h._tool_list_plugins()))
    if len(sys.argv) > 2:
        q = sys.argv[2]
        print(f"\n搜索 '{q}':", _json_str(h._tool_search(q, 10)))
