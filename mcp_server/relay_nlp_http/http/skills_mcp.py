#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""skills_mcp.py — Skill MCP 本地处理器（挂载在 kz_mcp_http.py 的 9001 网关）

提供 /kanzi_skill_mcp 端点，让 Copilot（本地小模型）通过 MCP 工具查询 skill 内容。

**设计原则（2026-10-16 重构，适配小模型）**：
- 工具只有 3 个，小模型不用做复杂工具选择
- skill 拆成「完整任务单元」（读完全文能照做一件事），get_skill 一次返回完整小 skill，
  模型不用串联碎片、不用反复查 docmcp
- search_property 数据源 = 合并全量属性文件（离线本地查，秒回，不占 docmcp 上下文）

工具：
  search_property(query, limit?) — 属性查询：在合并全量属性库里搜，返回匹配行
  list_skills()                   — skill 说明：所有 skill 名 + 一句话用途 + 大小
  get_skill(name)                 — 返回某 skill 的完整内容（小 skill 3-8KB，一次拿全）

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
        self._sig = ""
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
        """扫描并构建索引。返回 {skills:[...], properties:[...]}"""
        root = self.skills_dir
        skills, properties = [], []
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
                    "file_count": len(files),
                    "path": skill_dir.as_posix(),
                })
                # 属性行：`| UI名 | 说明 |` 或 `| UI名 | 绑定写法 | 说明 |`（quickref/合并全量版）
                for m in re.finditer(
                        r"^\|\s*`([^`]+)`\s*\|\s*(.+?)\s*\|", text, re.M):
                    ui = m.group(1).strip()
                    rest = m.group(2).strip()
                    # 尝试分离绑定写法（含 `{...}` 的单元格）与说明
                    bind, desc2 = "", rest
                    bm = re.match(r"^`([^`]+)`\s*(.*)$", rest)
                    if bm and "{" in bm.group(1):
                        bind, desc2 = bm.group(1), bm.group(2).strip()
                    properties.append({
                        "ui_name": ui,
                        "binding": bind,
                        "desc": desc2,
                        "skill": skill_dir.name,
                    })
        return {"skills": skills, "properties": properties}

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
    for zh, en in _ZH_SYNONYMS.items():
        if zh in q:
            terms.add(en)
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
        if bind and t in bind:
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
    seen = set()
    for prop in index.data()["properties"]:
        s = _score_property(prop, terms)
        if s > 0:
            key = (prop["ui_name"], prop["skill"])
            if key in seen:
                continue
            seen.add(key)
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


def get_skill(index: SkillIndex, name: str, max_chars: int = 32000) -> dict:
    """返回某 skill 的完整内容。skill 已拆成小单元（3-8KB），一次拿全不用串联。"""
    max_chars = max(2000, min(int(max_chars or 32000), 60000))
    root = index.skills_dir / name
    md = root / "SKILL.md"
    if not md.exists():
        return {"found": False, "hint": f"skill 不存在: {name}。用 list_skills 查看全部。"}
    try:
        text = md.read_text(encoding="utf-8", errors="replace")
    except Exception as e:                                   # noqa: BLE001
        return {"found": False, "hint": f"读取失败: {e}"}
    truncated = len(text) > max_chars
    if truncated:
        text = text[:max_chars] + "\n…（已截断，skill 应是小单元，若仍需更多请联系维护）"
    return {
        "found": True,
        "name": name,
        "size": len(text),
        "truncated": truncated,
        "content": text,
    }


# ══════════════════════ MCP 协议层 ══════════════════════

TOOLS = [
    {
        "name": "search_property",
        "description": "搜索 Kanzi 属性库（离线全量），返回匹配的属性行（UI 面板名、绑定写法、说明）。"
                       "需要查任何 Kanzi 属性的绑定写法/面板名称时调用本工具，中英文关键词都行，"
                       "如 'actual width'、'字体'、'text color'。查不到时换更短的关键词再试。"
                       "只查属性用这个，不要读属性文件。",
        "inputSchema": {"type": "object",
                        "properties": {
                            "query": {"type": "string", "description": "属性关键词，如 width / font size / 实际宽度"},
                            "limit": {"type": "integer", "description": "返回条数上限，默认 5，最大 10"},
                        },
                        "required": ["query"]},
    },
    {
        "name": "list_skills",
        "description": "列出全部 skill（名称、一句话用途、大小）。不知道某个操作该读哪个 skill，"
                       "或想了解有哪些能力时调用。",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "get_skill",
        "description": "返回某 skill 的完整内容（已拆成小单元，一次拿全，上限 32KB）。"
                       "要执行某个操作（建节点/建材质/做绑定/本地化/动画等）时，先 list_skills 找到 skill 名，"
                       "再调本工具拿完整步骤，照着做。不要反复查其他文档。",
        "inputSchema": {"type": "object",
                        "properties": {
                            "name": {"type": "string", "description": "skill 名称，如 kanzi-node-create"},
                        },
                        "required": ["name"]},
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
                "serverInfo": {"name": "kanzi-skill-mcp", "version": "2.0.0"},
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
            elif name == "get_skill":
                result = get_skill(self.index, str(args.get("name", "")),
                                   int(args.get("max_chars", 20000) or 20000))
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
