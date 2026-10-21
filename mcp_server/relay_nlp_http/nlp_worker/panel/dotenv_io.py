#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""dotenv_io.py — .env 文件读写

nlp_worker 的密钥流：config.yaml 里写 ${OPENAI_API_KEY}，
真实的密钥放在同级的 .env 里，由 load_dotenv() 加载。

  copilot_runtime.py:496
      load_dotenv(config_path.parent / ".env", override=False)
      → _expand_env(raw)   # 替换 ${XXX}

所以：
  ★ .env 必须和 config.yaml 同目录（代码写死了 config_path.parent）
  ★ override=False → .env 不覆盖已存在的系统环境变量
  ★ .env 不入库，只有 .env.example 模板

本模块负责：读 / 写 / 生成骨架 / 找出 config.yaml 引用了但 .env 里没有的 KEY。
"""
from __future__ import annotations

import os
import re
from pathlib import Path

# ${NAME} 或 $NAME
ENV_PATTERN = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}|\$([A-Za-z_][A-Za-z0-9_]*)")

# 从 config.example.yaml 抄来的骨架
SKELETON = """# 密钥文件 —— 和 config.yaml 放同一个目录，nlp_worker 启动时自动加载。
#
# 用法：config.yaml 里写 ${KEY_NAME}，真实值写在这里。
# 特点：
#   - 本文件不要提交到仓库（含密钥）
#   - 已经存在于系统环境变量里的值不会被本文件覆盖
#   - KEY=VALUE，不要加引号；值里有空格才需要引号

# ── GitHub 官方账号（用 use_logged_in_user: false 时才需要）──
# GITHUB_TOKEN=ghp_xxxxxxxxxxxxxxxx

# ── 自带模型（BYOK）的密钥 ──
# OPENAI_API_KEY=
# AZURE_OPENAI_API_KEY=
# ANTHROPIC_API_KEY=

# ── 本地 MCP 服务的令牌（config.yaml 里 mcp_servers.*.env 引用）──
# LOCAL_MCP_TOKEN=
"""


def env_path_for(config_path) -> Path:
    """.env 必须和 config.yaml 同目录（load_dotenv 就是这么找的）。"""
    return Path(config_path).resolve().parent / ".env"


def example_path_for(config_path) -> Path:
    return Path(config_path).resolve().parent / ".env.example"


# ══════════════════ 读 ══════════════════

def load(path) -> tuple[dict, str]:
    """读 .env。返回 (键值对, 原始文本)。

    保留原始文本 —— 因为要保留注释和未修改的行，只改动的行回写。
    """
    p = Path(path)
    if not p.exists():
        return {}, ""
    try:
        text = p.read_text(encoding="utf-8")
    except Exception:                                        # noqa: BLE001
        return {}, ""

    pairs: dict = {}
    for line in text.splitlines():
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        if s.startswith("export "):
            s = s[7:].strip()
        if "=" not in s:
            continue
        k, _, v = s.partition("=")
        k = k.strip()
        v = v.strip()
        # 去引号
        if len(v) >= 2 and v[0] == v[-1] and v[0] in "\"'":
            v = v[1:-1]
        if k:
            pairs[k] = v
    return pairs, text


# ══════════════════ 写 ══════════════════

def dump(pairs: dict, path, header: str | None = None) -> None:
    """写 .env。保持稳定顺序：原有的键按原顺序，新增的追加在后面。"""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    existing, old_text = load(p)

    order: list[str] = []
    for line in old_text.splitlines():
        s = line.strip()
        if s.startswith("export "):
            s = s[7:].strip()
        if "=" in s and not s.startswith("#"):
            k = s.split("=", 1)[0].strip()
            if k and k not in order:
                order.append(k)
    for k in pairs:
        if k not in order:
            order.append(k)

    lines: list[str] = []
    if header:
        lines.append(header.rstrip())
        lines.append("")
    elif not old_text and not p.exists():
        lines.append("# nlp_worker 密钥文件")
        lines.append("")

    for k in order:
        v = pairs.get(k)
        if v is None:
            continue
        lines.append(f"{k}={_quote(v)}")

    # 保留原文件里的注释块（简单做法：原注释 + 新键值）
    p.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def _quote(v) -> str:
    s = str(v)
    if s and (re.search(r"[\s#\"']", s)):
        return '"' + s.replace('"', '\\"') + '"'
    return s


def ensure(path) -> bool:
    """确保 .env 存在。不存在就从 .env.example 拷，再不行就写骨架。返回是否新建。"""
    p = Path(path)
    if p.exists():
        return False
    ex = p.parent / ".env.example"
    if ex.exists():
        try:
            p.write_text(ex.read_text(encoding="utf-8"), encoding="utf-8")
            return True
        except Exception:                                    # noqa: BLE001
            pass
    p.write_text(SKELETON, encoding="utf-8")
    return True


# ══════════════════ 与 config.yaml 联动 ══════════════════

def refs_in_config(data) -> list[str]:
    """找出 config.yaml 里所有 ${XXX} 引用（去重、保持出现顺序）。"""
    found: list[str] = []

    def walk(node):
        if isinstance(node, str):
            for m in ENV_PATTERN.finditer(node):
                name = m.group(1) or m.group(2)
                if name and name not in found:
                    found.append(name)
        elif isinstance(node, dict):
            for v in node.values():
                walk(v)
        elif isinstance(node, list):
            for v in node:
                walk(v)

    walk(data)
    return found


def resolve_status(data, dotenv_pairs: dict) -> list[dict]:
    """每个引用给出「从哪来的」：
         dotenv   在 .env 里 ✅
         system   在系统环境变量里 ✅
         missing  都没有 ❌
    """
    out = []
    for name in refs_in_config(data):
        if name in dotenv_pairs and dotenv_pairs[name]:
            out.append({"name": name, "from": "dotenv", "ok": True})
        elif os.environ.get(name):
            out.append({"name": name, "from": "system", "ok": True})
        else:
            out.append({"name": name, "from": "missing", "ok": False})
    return out
