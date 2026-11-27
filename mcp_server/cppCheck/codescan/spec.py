# -*- coding: utf-8 -*-
"""规范文件解析：从 Markdown 手册里提取条款，并与自带的覆盖判定合并。

支持两种用法：
  1. 直接使用 data/spec_coverage.json（内置 224 条判定，开箱即用）
  2. 用户提供自定义 Markdown 手册，自动提取编号/分类/级别/正文，
     未在内置判定表里的条款默认标为"仅人工"
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from .common import dirs

RE_HEAD = re.compile(r"^#{2,5}\s+((?:YB-No\.\d+)|(?:BT-[\d.\-]+))\s*(.*)$", re.M)
RE_LEVEL = re.compile(r"\*\*级别\*\*\s*[：:]\s*(\S+)")
RE_BODY = re.compile(r"\*\*判定依据[^*]*\*\*\s*\n+(.*?)(?:\n\*\*|\n> 来源|\Z)", re.S)


def _builtin() -> dict:
    p = dirs()["data"] / "spec_coverage.json"
    if not p.exists():
        return {}
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        return {x["no"]: x for x in data}
    except Exception:
        return {}


def parse_spec(path: Path, log=None) -> list:
    """解析规范 Markdown，返回条款列表。"""
    builtin = _builtin()
    try:
        txt = Path(path).read_text(encoding="utf-8")
    except UnicodeDecodeError:
        txt = Path(path).read_text(encoding="gbk", errors="replace")

    heads = list(RE_HEAD.finditer(txt))
    if not heads:
        if log:
            log.warn("未从 %s 中识别到规范编号，跳过" % Path(path).name)
        return []

    rules = []
    for i, m in enumerate(heads):
        no = m.group(1).strip()
        cat = m.group(2).strip()
        end = heads[i + 1].start() if i + 1 < len(heads) else len(txt)
        block = txt[m.start():end]

        lv_m = RE_LEVEL.search(block)
        level = "必须"
        if lv_m:
            raw = lv_m.group(1)
            level = "建议" if "建议" in raw else "必须"

        bd = RE_BODY.search(block)
        text = re.sub(r"\s+", " ", bd.group(1)).strip() if bd else ""
        text = text[:300]

        base = builtin.get(no, {})
        rules.append({
            "no": no,
            "cat": cat or base.get("cat", ""),
            "level": level,
            "text": text or base.get("text", ""),
            "grade": base.get("grade", "C"),
            "tool": base.get("tool", ""),
            "note": base.get("note", "未在判定表中，按仅人工处理"),
            "hit": 0,
        })

    if log:
        auto = sum(1 for r in rules if r["grade"] in ("A", "B"))
        log.info("解析规范 %d 条，其中 %d 条可自动判定" % (len(rules), auto))
    return rules


def attach_hits(rules: list, items: list) -> None:
    """把扫描结果按规范编号统计到条款上。"""
    import collections
    cnt = collections.Counter()
    for x in items:
        sp = x.get("spec") or ""
        if sp:
            cnt[sp] += 1
    for r in rules:
        r["hit"] = cnt.get(r["no"], 0)
