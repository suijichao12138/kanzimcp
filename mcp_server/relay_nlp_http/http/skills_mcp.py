#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""skills_mcp.py — Skill MCP 本地处理器（挂载在 kz_mcp_http.py 的 9001 网关）

提供 /kanzi_skill_mcp 端点，让 Copilot 通过 MCP 工具按需查询 skill 内容，
避免把全部 skill 注入 system prompt（全量 758KB 必超限）。

数据源：deployer 网页维护的独立 skill 仓库（--skills-dir 指定，
默认 <部署根>/data/skills）。与 nlp_worker 的 skill 完全隔离。

工具：
  list_skills()              — 所有 skill 名 + description + 文件数（~3KB）
  search_property(query,limit?) — 在 quickref/全量属性里搜属性，返回匹配行（宽容匹配）
  get_skill_summary(name)    — 某 skill 的 description + 章节标题（~1KB）
  read_skill_section(name, heading) — 读某 skill 指定章节（按段返回，控制大小）

协议：遵循 MCP JSON-RPC（initialize / tools/list / tools/call / ping），
由 kz_mcp_http.py 的 _handle_jsonrpc_skills 调用。
"""
import os
import re
import threading
from pathlib import Path

log = logging = None  # 由宿主注入


def set_logger(logger):
    global log
    log = logger


# ══════════════════════ 数据加载 ══════════════════════

class SkillIndex:
    """扫描 skill 目录，构建属性/章节索引。进程内缓存，目录变更自动重扫。"""

    def __init__(self, skills_dir: str | Path):
        self.skills_dir = Path(skills_dir)
        self._lock = threading.Lock()
        self._cache = None          # (mtime_sig, data)
        self._data = None

    def _mtime_sig(self) -> str:
        """目录结构签名：所有 SKILL.md 路径 + 大小 + mtime，变了就重扫。"""
        try:
            parts = []
            for md in sorted(self.skills_dir.rglob("SKILL.md")):
                st = md.stat()
                parts.append(f"{md}|{st.st_size}|{int(st.st_mtime)}")
            return ";".join(parts)
        except Exception:                                    # noqa: BLE001
            return ""

    def _load(self) -> dict:
        """扫描并构建索引。返回 {skills:[...], properties:[...], chapters:[...]}"""
        root = self.skills_dir
        skills, properties, chapters = [], [], []
        if root.exists():
            for skill_dir in sorted(root.iterdir()):
                if not skill_dir.is_dir():
                    continue
                md = skill_dir / "SKILL.md"
                if not md.exists():
                    continue
                try:
                    text = md.read_text(encoding="utf-8", errors="replace")
                except Exception:                            # noqa: BLE001
                    continue
                desc = self._frontmatter(text, "description")
                files = [p.relative_to(skill_dir).as_posix()
                         for p in sorted(skill_dir.rglob("*")) if p.is_file()]
                skills.append({
                    "name": skill_dir.name,
                    "description": desc,
                    "size": md.stat().st_size,
                    "files": files,
                    "file_count": len(files),
                    "path": skill_dir.as_posix(),
                })
                # 章节（## 标题）
                for m in re.finditer(r"^##\s+(.+)$", text, re.M):
                    chapters.append({
                        "skill": skill_dir.name,
                        "heading": m.group(1).strip(),
                    })
                # 属性行：quickref 的 `| UI名 | 绑定写法 | 说明 |`（绑定写法可能带 ✅）
                for m in re.finditer(
                        r"^\|\s*`([^`]+)`\s*\|\s*(`[^`]*`\s*[^|]*?)\s*\|\s*([^|]*?)\s*\|\s*$",
                        text, re.M):
                    properties.append({
                        "ui_name": m.group(1).strip(),
                        "binding": m.group(2).strip(),
                        "desc": m.group(3).strip(),
                        "skill": skill_dir.name,
                    })
        return {"skills": skills, "properties": properties, "chapters": chapters}

    def data(self) -> dict:
        """带缓存的索引数据。"""
        sig = self._mtime_sig()
        with self._lock:
            if self._data is None or self._sig != sig:
                self._data = self._load()
                self._sig = sig
            return self._data

    @staticmethod
    def _frontmatter(text: str, key: str) -> str:
        if text.startswith("---"):
            end = text.find("\n---", 3)
            if end != -1:
                for line in text[3:end].splitlines():
                    if line.startswith(f"{key}:"):
                        return line[len(key) + 1:].strip().strip('"\'')
        return ""


# 中文同义词映射（宽容匹配用）
_ZH_SYNONYMS = {
    "宽度": "width", "高度": "height", "宽": "width", "高": "height",
    "文本": "text", "字体": "font", "颜色": "color", "颜色色": "color",
    "透明度": "opacity", "尺寸": "size", "位置": "position", "对齐": "align",
    "边距": "margin", "背景": "background", "前景": "foreground",
    "居中": "center", "旋转": "rotation", "缩放": "scale", "可见": "visible",
    "隐藏": "hidden", "焦点": "focus", "图片": "image", "画刷": "brush",
    "阴影": "shadow", "模糊": "blur", "蒙版": "mask", "描边": "outline",
    "材质": "material", "布局": "layout", "网格": "grid", "按钮": "button",
    "滑块": "slider", "列表": "list", "范围": "range", "值": "value",
    "默认": "default", "当前": "current", "实际": "actual", "启用": "enabled",
    "禁用": "disabled", "圆角": "radius", "行": "row", "列": "column",
    "间距": "spacing", "字体大小": "font size", "字号": "font size",
    "对齐方式": "alignment", "内容": "content",
}


def _normalize_query(q: str) -> list[str]:
    """把 query 拆成多个检索词：原词 + 小写 + 中文同义词。"""
    q = q.strip()
    if not q:
        return []
    terms = {q.lower()}
    # 中文 → 英文同义词
    for zh, en in _ZH_SYNONYMS.items():
        if zh in q:
            terms.add(en)
    # 拆空格分多个词
    for w in re.split(r"[\s,，/]+", q.lower()):
        if w:
            terms.add(w)
    return list(terms)


def _score_property(prop: dict, terms: list[str]) -> int:
    ui, bind, desc = prop["ui_name"].lower(), prop["binding"].lower(), prop["desc"].lower()
    score = 0
    for t in terms:
        if t in ui:
            score += 10
        if t in bind:
            score += 8
        if t in desc:
            score += 3
        if re.search(rf"\b{re.escape(t)}\b", ui):
            score += 5
    return score


# ══════════════════════ 工具实现 ══════════════════════

def list_skills(index: SkillIndex) -> dict:
    data = index.data()
    skills = []
    for s in data["skills"]:
        skills.append({
            "name": s["name"],
            "description": s["description"],
            "file_count": s["file_count"],
            "size": s["size"],
        })
    return {"skills": skills, "count": len(skills)}


def search_property(index: SkillIndex, query: str, limit: int = 5) -> dict:
    limit = max(1, min(int(limit or 5), 10))
    terms = _normalize_query(query)
    if not terms:
        return {"query": query, "matches": [], "total": 0,
                "hint": "请输入要查的属性关键词，如 width / font size / text color"}
    scored = []
    for prop in index.data()["properties"]:
        s = _score_property(prop, terms)
        if s > 0:
            scored.append((s, prop))
    scored.sort(key=lambda x: -x[0])
    matches = [{
        "ui_name": p["ui_name"],
        "binding": p["binding"],
        "desc": p["desc"][:80],
        "skill": p["skill"],
        "score": s,
    } for s, p in scored[:limit]]
    if not matches:
        return {"query": query, "matches": [], "total": 0,
                "hint": "未找到匹配属性。试试更短的关键词：width / font / color / opacity / text / layout"}
    return {"query": query, "matches": matches, "total": len(scored)}


def get_skill_summary(index: SkillIndex, name: str) -> dict:
    data = index.data()
    skill = next((s for s in data["skills"] if s["name"] == name), None)
    if not skill:
        return {"found": False, "hint": f"skill 不存在: {name}。可用 list_skills 查看全部。"}
    headings = [c["heading"] for c in data["chapters"] if c["skill"] == name]
    return {
        "found": True,
        "name": skill["name"],
        "description": skill["description"],
        "file_count": skill["file_count"],
        "size": skill["size"],
        "chapters": headings,
    }


def read_skill_section(index: SkillIndex, name: str, heading: str, max_chars: int = 4000) -> dict:
    """读某 skill 指定章节（模糊匹配标题，返回该章节正文，控制大小）。"""
    max_chars = max(500, min(int(max_chars or 4000), 12000))
    root = index.skills_dir / name
    md = root / "SKILL.md"
    if not md.exists():
        return {"found": False, "hint": f"skill 不存在: {name}"}
    try:
        text = md.read_text(encoding="utf-8", errors="replace")
    except Exception as e:                                   # noqa: BLE001
        return {"found": False, "hint": f"读取失败: {e}"}

    # 匹配章节（支持子串）
    target = heading.strip().lower()
    sections = []
    starts = [m.start() for m in re.finditer(r"^##\s+.+$", text, re.M)]
    bounds = starts[1:] + [len(text)]
    for i, st in enumerate(starts):
        sec = re.search(r"^##\s+(.+)$", text[st:bounds[i]], re.M)
        if not sec:
            continue
        sec_heading = sec.group(1).strip()
        if target in sec_heading.lower() or sec_heading.lower() in target:
            sections.append((st, bounds[i], sec_heading))

    if not sections:
        return {"found": False, "hint": f"未找到章节「{heading}」。可用 get_skill_summary 查看全部章节。"}

    best = max(sections, key=lambda x: x[1] - x[0])
    body = text[best[0]:best[1]].strip()
    if len(body) > max_chars:
        body = body[:max_chars] + "\n…（已截断，如需更多可缩小范围）"
    return {"found": True, "skill": name, "heading": best[2], "content": body}


# ══════════════════════ MCP 协议层 ══════════════════════

TOOLS = [
    {
        "name": "list_skills",
        "description": "列出独立 skill 仓库里的所有 skill（名称、用途、文件数）。需要知道有哪些 skill 可用时调用。",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "search_property",
        "description": "搜索 Kanzi 属性表（quickref + 全量属性版），返回匹配的属性行（UI 面板名、绑定表达式写法、说明）。"
                       "需要查任何 Kanzi 属性的绑定写法/面板名称时调用本工具，不要直接读取 skill 文件。"
                       "用法：传你想查的属性关键词，如 'actual width'、'font size'、'text color'，中英文都行。"
                       "查不到时换更短的关键词再试（如 'width' 而非 'actual layout width'）。",
        "inputSchema": {"type": "object",
                        "properties": {
                            "query": {"type": "string", "description": "属性关键词，如 width / font size / 实际宽度"},
                            "limit": {"type": "integer", "description": "返回条数上限，默认 5，最大 10"},
                        },
                        "required": ["query"]},
    },
    {
        "name": "get_skill_summary",
        "description": "获取某 skill 的描述和章节标题列表。需要了解某个 skill 覆盖什么内容时调用，比读整个文件省上下文。",
        "inputSchema": {"type": "object",
                        "properties": {"name": {"type": "string", "description": "skill 名称，如 kanzi-ui"}},
                        "required": ["name"]},
    },
    {
        "name": "read_skill_section",
        "description": "读取某 skill 的指定章节内容（按标题匹配，返回该段正文，控制大小）。"
                       "需要某 skill 的操作步骤细节时调用，不要整读整个 SKILL.md。",
        "inputSchema": {"type": "object",
                        "properties": {
                            "name": {"type": "string", "description": "skill 名称"},
                            "heading": {"type": "string", "description": "章节标题（支持模糊匹配），如 '创建节点'"},
                            "max_chars": {"type": "integer", "description": "返回内容上限，默认 4000"},
                        },
                        "required": ["name", "heading"]},
    },
]


class SkillsMcpHandler:
    """MCP JSON-RPC 处理：initialize / tools/list / tools/call / ping。"""

    def __init__(self, skills_dir: str | Path):
        self.index = SkillIndex(skills_dir)

    def handle(self, req: dict) -> dict:
        if not isinstance(req, dict) or "method" not in req:
            return self._error(-32600, "Invalid Request", req)
        method = req.get("method", "")
        rid = req.get("id")
        if method == "initialize":
            return {"jsonrpc": "2.0", "id": rid, "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {"listChanged": False}},
                "serverInfo": {"name": "kanzi-skill-mcp", "version": "1.0.0"},
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
            if name == "list_skills":
                result = list_skills(self.index)
            elif name == "search_property":
                result = search_property(self.index, str(args.get("query", "")),
                                         int(args.get("limit", 5) or 5))
            elif name == "get_skill_summary":
                result = get_skill_summary(self.index, str(args.get("name", "")))
            elif name == "read_skill_section":
                result = read_skill_section(self.index, str(args.get("name", "")),
                                            str(args.get("heading", "")),
                                            int(args.get("max_chars", 4000) or 4000))
            else:
                return self._error(-32602, f"未知工具: {name}", req)
        except Exception as e:                               # noqa: BLE001
            return self._error(-32603, f"工具执行失败: {e}", req)
        return {"jsonrpc": "2.0", "id": rid, "result": {
            "content": [{"type": "text", "text": _json_str(result)}],
            "structuredContent": result,
        }}

    @staticmethod
    def _error(code, message, req):
        return {"jsonrpc": "2.0", "id": req.get("id") if isinstance(req, dict) else None,
                "error": {"code": code, "message": message}}


def _json_str(obj) -> str:
    import json
    return json.dumps(obj, ensure_ascii=False, indent=1)
