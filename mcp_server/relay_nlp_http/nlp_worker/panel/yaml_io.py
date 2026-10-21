#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""yaml_io.py — 按点号路径读写 config.yaml

只做「取/设/校验」，不依赖 nlp_worker 的任何代码 —— 面板要能单独运行
（用户机器上不一定装了 PyYAML，但一定有 nlp_worker 的 venv）。

★ 关键：没有 PyYAML 时退化为「内置极简 YAML 读写」，
  覆盖 config.yaml 用到的所有形态（嵌套 map / list / 多行字符串 / 引号）。
"""
from __future__ import annotations

import re
from pathlib import Path

try:
    import yaml as _yaml
except ImportError:                                          # noqa: N816
    _yaml = None


# ══════════════════ 读 ══════════════════

def load(path) -> dict:
    """读 YAML 成 dict；文件不存在/为空返回 {}。"""
    p = Path(path)
    if not p.exists():
        return {}
    text = p.read_text(encoding="utf-8")
    if not text.strip():
        return {}
    if _yaml:
        data = _yaml.safe_load(text)
        return data if isinstance(data, dict) else {}
    return _mini_load(text)


def dump(data: dict, path) -> None:
    """写 YAML。有 PyYAML 用 PyYAML，否则用内置序列化。"""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    if _yaml:
        text = _yaml.safe_dump(
            data, allow_unicode=True, sort_keys=False,
            default_flow_style=False, width=100,
        )
    else:
        text = _mini_dump(data)
    p.write_text(text, encoding="utf-8")


# ══════════════════ 点号路径取/设 ══════════════════

def get_path(data: dict, key: str, default=None):
    """按 'a.b.c' 取值。"""
    cur = data
    for part in key.split("."):
        if not isinstance(cur, dict) or part not in cur:
            return default
        cur = cur[part]
    return cur


def set_path(data: dict, key: str, value) -> None:
    """按 'a.b.c' 设值（中间层自动建）。value 为 None 表示删除该键。"""
    parts = key.split(".")
    cur = data
    for part in parts[:-1]:
        nxt = cur.get(part)
        if not isinstance(nxt, dict):
            nxt = {}
            cur[part] = nxt
        cur = nxt
    leaf = parts[-1]
    if value is None:
        cur.pop(leaf, None)
    else:
        cur[leaf] = value


def prune_empty(data: dict) -> dict:
    """递归删掉空 dict / None 值（保持生成的 YAML 干净）。list 不动。"""
    if not isinstance(data, dict):
        return data
    out = {}
    for k, v in data.items():
        if isinstance(v, dict):
            v = prune_empty(v)
            if not v:
                continue
        elif v is None:
            continue
        out[k] = v
    return out


# ══════════════════ 内置极简 YAML（无 PyYAML 时兜底）══════════════════

def _mini_dump(data, indent: int = 0) -> str:
    """把 dict/list 序列化成 YAML。只覆盖 config.yaml 会用到的形态。"""
    pad = "  " * indent
    lines: list[str] = []
    if isinstance(data, dict):
        for k, v in data.items():
            if isinstance(v, dict) and v:
                lines.append(f"{pad}{k}:")
                lines.append(_mini_dump(v, indent + 1))
            elif isinstance(v, list):
                if not v:
                    lines.append(f"{pad}{k}: []")
                else:
                    lines.append(f"{pad}{k}:")
                    lines.append(_mini_list(v, indent + 1))
            else:
                lines.append(f"{pad}{k}: {_scalar(v)}")
    return "\n".join(x for x in lines if x != "")


def _mini_list(items, indent: int) -> str:
    pad = "  " * indent
    lines: list[str] = []
    for it in items:
        if isinstance(it, dict):
            first = True
            for k, v in it.items():
                if isinstance(v, (dict, list)):
                    lines.append(f"{pad}- {k}:" if first else f"{pad}  {k}:")
                    lines.append(_mini_dump(v, indent + 1))
                else:
                    lines.append(f"{pad}- {k}: {_scalar(v)}" if first
                                 else f"{pad}  {k}: {_scalar(v)}")
                first = False
        else:
            lines.append(f"{pad}- {_scalar(it)}")
    return "\n".join(lines)


def _scalar(v) -> str:
    if v is None:
        return "null"
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, (int, float)):
        return str(v)
    s = str(v)
    # 多行字符串 → 块标量
    if "\n" in s:
        body = "\n".join("  " + ln for ln in s.split("\n"))
        return "|\n" + body
    # 需要引号的：含特殊字符、看起来像数字/布尔、或含 ${}
    if s == "" or re.search(r"[:#{}\[\],&*?|<>=!%@`\"']", s) or \
       re.match(r"^[\d.+-]", s) or s.lower() in {"true", "false", "null", "yes", "no"}:
        return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'
    return s


def _mini_load(text: str) -> dict:
    """极简 YAML 解析：够读 config.yaml。支持嵌套 map / list / 引号 / 块标量。"""
    root: dict = {}
    # 栈：[(缩进, 容器)]
    stack: list[tuple[int, object]] = [(-1, root)]
    lines = text.split("\n")
    i = 0
    while i < len(lines):
        raw = lines[i]
        i += 1
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        indent = len(raw) - len(raw.lstrip(" "))
        line = raw.strip()

        while stack and indent <= stack[-1][0]:
            stack.pop()
        if not stack:
            stack = [(-1, root)]
        cur = stack[-1][1]

        # 块标量：key: |
        m_block = re.match(r"^([^:]+):\s*\|[-+]?\s*$", line)
        if m_block and isinstance(cur, dict):
            body: list[str] = []
            while i < len(lines):
                nxt = lines[i]
                if nxt.strip() and (len(nxt) - len(nxt.lstrip(" "))) <= indent:
                    break
                body.append(nxt[indent + 2:] if len(nxt) > indent + 2 else "")
                i += 1
            cur[m_block.group(1).strip()] = "\n".join(body).rstrip()
            continue

        if line.startswith("- "):           # 列表项
            item = line[2:].strip()
            if not isinstance(cur, list):
                continue
            # 判断是「k: v 映射项」还是「纯标量项」：
            #   只有冒号后跟空格/行尾，且冒号前是干净的键名，才算映射。
            #   这样 "- http://x"（URL）不会被误当 key/value。
            kv = None
            m = re.match(r"^([A-Za-z_][\w.\- ]*):(?:\s+(.*))?$", item)
            if m:
                kv = m
            if kv:
                d = {kv.group(1).strip(): _parse_scalar(kv.group(2).strip())}
                cur.append(d)
                stack.append((indent, d))
            else:
                cur.append(_parse_scalar(item))
            continue

        kv = re.match(r"^([^:]+):\s*(.*)$", line)
        if not kv:
            continue
        k = kv.group(1).strip()
        v = kv.group(2).strip()
        if v == "":
            # 看下一行的缩进决定是 map 还是 list
            j = i
            while j < len(lines) and (not lines[j].strip() or lines[j].lstrip().startswith("#")):
                j += 1
            nxt_indent = (len(lines[j]) - len(lines[j].lstrip(" "))) if j < len(lines) else -1
            container = [] if (j < len(lines) and lines[j].strip().startswith("- ")
                               and nxt_indent > indent) else {}
            if isinstance(cur, dict):
                cur[k] = container
            stack.append((indent, container))
        else:
            if isinstance(cur, dict):
                cur[k] = _parse_scalar(v)
    return root


def _parse_scalar(v: str):
    if v == "":
        return ""
    if len(v) >= 2 and v[0] == v[-1] and v[0] in "\"'":
        return v[1:-1]
    low = v.lower()
    if low in {"null", "~"}:
        return None
    if low in {"true", "yes"}:
        return True
    if low in {"false", "no"}:
        return False
    if v == "[]":
        return []
    if v == "{}":
        return {}
    m = re.match(r"^-?\d+$", v)
    if m:
        return int(v)
    m = re.match(r"^-?\d+\.\d+$", v)
    if m:
        return float(v)
    return v


# ══════════════════ 值类型转换 ══════════════════

def coerce(field: dict, raw):
    """把界面上的字符串按字段类型转成 YAML 值。空值返回 None（=不写）。"""
    t = field.get("type", "str")

    if t == "bool":
        return bool(raw)
    if t in ("int",):
        s = str(raw).strip()
        if s == "":
            return None
        return int(float(s))
    if t in ("float",):
        s = str(raw).strip()
        if s == "":
            return None
        return float(s)
    if t in ("list",):
        if not raw:
            return None
        return [str(x) for x in raw]
    if t in ("dict", "dict_list"):
        if not raw:
            return None
        return raw
    # str / secret / path / enum
    s = str(raw).strip()
    if s == "":
        return None
    if t == "enum" and field.get("options") and s not in field["options"]:
        return None
    if t == "path":
        return s.replace("/", "\\") if ("\\" in s or ":" in s) else s
    return s
