#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""api.py — 网页控制台所有 /api/* 的处理逻辑

每个 handle_* 返回 (HTTP状态码, 响应体 dict)。路由分发在 server.py。

能力：
- 会话管理：列表（主/子会话）、重置、清空
- 配置管理：按分组读写 config.yaml（yaml 简单重写，不保留注释）
- 环境变量：读/写 .env、config 里 ${KEY} 展开显示、反向索引、掩码
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

import yaml

from . import config_groups
from .config_groups import ENV_PATTERN

log = logging.getLogger("nlp-worker.web")

# 运行期上下文（由 nlp_worker 注入）：config / store / copilot / relay
CTX = None


# ─────────────────────────── 工具 ───────────────────────────

def _main_loop():
    """返回 nlp_worker 主事件循环（web 线程跨线程提交协程用）。

    由 nlp_worker 注入 CTX.main_loop。"""
    if CTX is not None:
        return getattr(CTX, "main_loop", None)
    return None


def _ok(data=None, **kw):
    body = {"ok": True}
    if data is not None:
        body["data"] = data
    body.update(kw)
    return body


def _err(code, message):
    return code, {"ok": False, "error": message}


def _config_path() -> Path:
    """当前运行的 config.yaml 路径。"""
    cfg = CTX.config
    # config_dir 是 pydantic exclude 字段（config 文件所在目录）
    config_dir = getattr(cfg, "config_dir", None) or Path(".")
    if isinstance(config_dir, str):
        config_dir = Path(config_dir)
    # 实际文件名：优先 env/config 里记录；默认 config.yaml
    return config_dir / "config.yaml"


def _env_path() -> Path:
    return _config_path().parent / ".env"


def _read_raw_config() -> dict:
    """读 config.yaml 原始内容（含 ${KEY} 占位，不展开）。"""
    path = _config_path()
    if not path.exists():
        return {}
    with path.open(encoding="utf-8") as fh:
        raw = yaml.safe_load(fh) or {}
    return raw if isinstance(raw, dict) else {}


def _write_raw_config(raw: dict) -> None:
    """yaml 简单重写（不保留注释）。"""
    path = _config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        yaml.safe_dump(raw, fh, allow_unicode=True, sort_keys=False, default_flow_style=False)
    log.info("config.yaml 已由网页控制台保存")


def _get_path(obj: dict, dotted: str, default=None):
    """按点号路径取 dict 值。"""
    cur = obj
    for part in dotted.split("."):
        if not isinstance(cur, dict) or part not in cur:
            return default
        cur = cur[part]
    return cur


def _set_path(obj: dict, dotted: str, value) -> None:
    """按点号路径设置 dict 值（自动建中间 dict）。"""
    parts = dotted.split(".")
    cur = obj
    for part in parts[:-1]:
        nxt = cur.get(part)
        if not isinstance(nxt, dict):
            nxt = {}
            cur[part] = nxt
        cur = nxt
    cur[parts[-1]] = value


def _del_path(obj: dict, dotted: str) -> None:
    parts = dotted.split(".")
    cur = obj
    for part in parts[:-1]:
        if not isinstance(cur, dict):
            return
        cur = cur.get(part)
        if not isinstance(cur, dict):
            return
    if isinstance(cur, dict):
        cur.pop(parts[-1], None)


def _env_map() -> dict[str, str]:
    """读 .env 全部变量（不区分启用，纯 KV）。"""
    path = _env_path()
    result: dict[str, str] = {}
    if not path.exists():
        return result
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        if key:
            result[key] = value.strip()
    return result


def _write_env_file(env: dict[str, str]) -> None:
    """写 .env（保留原注释头，KV 排序）。"""
    path = _env_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    header = []
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip().startswith("#") or line.strip() == "":
                header.append(line)
            else:
                break
    lines = list(header)
    for key in sorted(env):
        lines.append(f"{key}={env[key]}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    log.info(".env 已由网页控制台保存")


def _find_env_refs(raw: dict, prefix: str = "") -> dict[str, list[str]]:
    """扫描 config.yaml 里所有 ${KEY} 引用 → {KEY: [点号路径,...]} 反向索引。"""
    refs: dict[str, list[str]] = {}
    if isinstance(raw, dict):
        for k, v in raw.items():
            path = f"{prefix}.{k}" if prefix else k
            sub = _find_env_refs(v, path)
            for key, paths in sub.items():
                refs.setdefault(key, []).extend(paths)
    elif isinstance(raw, list):
        for i, v in enumerate(raw):
            sub = _find_env_refs(v, f"{prefix}[{i}]")
            for key, paths in sub.items():
                refs.setdefault(key, []).extend(paths)
    elif isinstance(raw, str):
        for m in ENV_PATTERN.finditer(raw):
            refs.setdefault(m.group(1), []).append(prefix or "<root>")
    return refs


def _display_value(value, env_map: dict[str, str], env_allowed: bool = True):
    """把 config 值转成表单显示值：${KEY} → 真实值 + 标记。

    env_allowed=False（字段不标记 env）时不做展开，原样显示 config 里的值。
    """
    if not isinstance(value, str):
        return value, None, False
    match = ENV_PATTERN.search(value)
    if not match:
        return value, None, False
    if not env_allowed:
        return value, None, False  # 不 env 联动的字段：显示占位原文
    key = match.group(1)
    if value.strip() == f"${{{key}}}":
        # 整值就是占位 → 显示真实值
        real = env_map.get(key)
        if real is None:
            return "", key, True   # 缺失
        return real, key, False
    # 部分占位（如 URL 里嵌）→ 原样显示 + 标注
    return value, key, False


# ─────────────────────────── 会话 API ───────────────────────────

def sessions_list() -> tuple[int, dict]:
    """会话列表（主/子会话）。"""
    store = CTX.store
    sessions = {}
    # 从 SQLite 读全部（需要 list_all 方法）
    try:
        sessions = store.list_all()
    except Exception as exc:  # noqa: BLE001
        log.warning("list_all 失败: %s", exc)
        sessions = {}
    # 补充内存态（当前连接的会话）
    in_memory = set()
    if getattr(CTX, "copilot", None) is not None:
        in_memory = set(getattr(CTX.copilot, "sessions", {}).keys())
    rows = []
    for key, rec in sessions.items():
        is_sub = key.startswith("task:")
        # rec 是 SessionMapping dataclass（不是 dict）
        g = rec if not isinstance(rec, dict) else type("R", (), rec)()
        rows.append({
            "key": key,
            "type": "子会话" if is_sub else "主会话",
            "session_id": getattr(g, "session_id", ""),
            "model": getattr(g, "model_name", ""),
            "status": getattr(g, "status", ""),
            "connected": key in in_memory,
            "created_at": getattr(g, "created_at", None),
            "updated_at": getattr(g, "updated_at", None),
            "last_error": getattr(g, "last_error", None),
        })
    # 内存里有但 SQLite 没写的（理论不发生，保险）
    for key in in_memory:
        if not any(r["key"] == key for r in rows):
            rows.append({
                "key": key,
                "type": "子会话" if key.startswith("task:") else "主会话",
                "session_id": "",
                "model": getattr(CTX.config.copilot.model, "name", ""),
                "status": "active",
                "connected": True,
                "created_at": None,
                "updated_at": None,
                "last_error": None,
            })
    rows.sort(key=lambda r: (r["created_at"] or 0), reverse=True)
    return 200, _ok({"sessions": rows, "count": len(rows)})


def session_reset(body: dict) -> tuple[int, dict]:
    """重置指定会话（删映射 + new_session 重建）。"""
    key = (body or {}).get("key", "")
    if not key:
        return _err(400, "缺少 key")
    copilot = getattr(CTX, "copilot", None)
    if copilot is None:
        return _err(500, "copilot runtime 不可用")
    import asyncio
    loop = _main_loop()
    if loop is None:
        return _err(500, "主事件循环不可用")
    try:
        new_id = asyncio.run_coroutine_threadsafe(
            copilot.new_session(key), loop
        ).result(timeout=120)
    except Exception as exc:  # noqa: BLE001
        log.warning("重置会话失败 %s: %s", key, exc)
        return _err(500, f"重置失败: {exc}")
    return 200, _ok({"key": key, "new_session_id": new_id})


def sessions_clear() -> tuple[int, dict]:
    """清空全部会话（重置所有）。"""
    rows = sessions_list()[1].get("data", {}).get("sessions", [])
    copilot = getattr(CTX, "copilot", None)
    import asyncio
    loop = _main_loop()
    cleared = []
    for row in rows:
        key = row["key"]
        try:
            asyncio.run_coroutine_threadsafe(
                copilot.new_session(key), loop
            ).result(timeout=120)
            cleared.append(key)
        except Exception:  # noqa: BLE001
            pass
    return 200, _ok({"cleared": cleared, "count": len(cleared)})


# ─────────────────────────── 配置 API ───────────────────────────

def config_groups_meta() -> tuple[int, dict]:
    """返回所有分组定义（供前端渲染导航 + 表单）。"""
    groups = []
    for g in config_groups.GROUPS:
        groups.append({
            "key": g.key,
            "title": g.title,
            "description": g.description,
            "kind": g.kind,
            "fields": [
                {
                    "key": f.key,
                    "label": f.label,
                    "type": f.type,
                    "default": f.default,
                    "help": f.help,
                    "env": f.env,
                    "required": f.required,
                    "enum_values": f.enum_values,
                }
                for f in g.fields
            ],
        })
    return 200, _ok({"groups": groups})


def config_get(group: str) -> tuple[int, dict]:
    """读某组配置（${KEY} 展开真实值 + 缺失标记 + env 反向索引）。"""
    g = config_groups.group_by_key(group)
    if g is None:
        return _err(404, f"未知配置组: {group}")
    raw = _read_raw_config()
    env_map = _env_map()
    refs = _find_env_refs(raw)
    group_raw = raw.get(group)

    if g.kind == "fields":
        fields = []
        for f in g.fields:
            value = _get_path(group_raw, f.key, f.default) if isinstance(group_raw, dict) else f.default
            display, env_key, missing = _display_value(value, env_map, env_allowed=(f.env is not None))
            fields.append({
                "key": f.key,
                "label": f.label,
                "type": f.type,
                "value": display,
                "default": f.default,
                "help": f.help,
                "env": env_key,
                "missing_env": missing,
                "required": f.required,
                "enum_values": f.enum_values,
                "is_env_placeholder": isinstance(value, str) and ENV_PATTERN.search(value) is not None,
            })
        return 200, _ok({
            "group": g.key,
            "key": g.key,
            "title": g.title,
            "description": g.description,
            "kind": g.kind,
            "fields": fields,
            "env_refs": refs,
        })
    if g.kind == "dict_of_servers":
        servers = {}
        if isinstance(group_raw, dict):
            for name, cfg in group_raw.items():
                if isinstance(cfg, dict):
                    servers[name] = {
                        "enabled": cfg.get("enabled", True),
                        "type": cfg.get("type", "http"),
                        "url": cfg.get("url", ""),
                        "headers": cfg.get("headers", {}),
                        "tools": cfg.get("tools", ["*"]),
                        "timeout_seconds": cfg.get("timeout_seconds", 300),
                    }
        return 200, _ok({
            "group": g.key, "key": g.key, "title": g.title, "kind": g.kind,
            "servers": servers, "env_refs": refs,
        })
    if g.kind == "skill_entries":
        entries = []
        sk = raw.get("skills") or {}
        max_file_bytes = sk.get("max_file_bytes", 131072)
        max_total_bytes = sk.get("max_total_bytes", 524288)
        for ent in sk.get("entries", []) or []:
            if isinstance(ent, dict):
                entries.append({
                    "path": ent.get("path", ""),
                    "enabled": ent.get("enabled", True),
                })
        return 200, _ok({
            "group": g.key, "key": g.key, "title": g.title, "kind": g.kind,
            "max_file_bytes": max_file_bytes,
            "max_total_bytes": max_total_bytes,
            "entries": entries, "env_refs": refs,
        })
    return _err(400, f"不支持的组类型: {g.kind}")


def config_put(group: str, body: dict) -> tuple[int, dict]:
    """保存某组配置（yaml 重写，保持 ${KEY} 占位）。"""
    g = config_groups.group_by_key(group)
    if g is None:
        return _err(404, f"未知配置组: {group}")
    raw = _read_raw_config()

    if g.kind == "fields":
        fields = (body or {}).get("fields", {})
        cur = raw.get(group)
        if cur is None or not isinstance(cur, dict):
            cur = {}
            raw[group] = cur
        for f in g.fields:
            if f.key not in fields:
                continue
            value = fields[f.key]
            # 铁律：仅当字段标记了 env（f.env 非空）时，原值 ${KEY} 占位 → 无论提交
            # 什么值都写回占位，绝不让真实密钥落盘 config.yaml（密钥只存在于 .env）。
            # 未标记 env 的字段（如 Provider API Key 直接显示）按普通字段正常保存。
            if f.env:
                original = _get_path(cur, f.key)
                if isinstance(original, str) and ENV_PATTERN.search(original):
                    continue
            if value == "" or value is None:
                _del_path(cur, f.key)
                continue
            # 类型转换
            if f.type == "int":
                try:
                    value = int(value)
                except (TypeError, ValueError):
                    value = value
            elif f.type == "float":
                try:
                    value = float(value)
                except (TypeError, ValueError):
                    value = value
            elif f.type == "bool":
                value = bool(value) if isinstance(value, bool) else str(value).lower() in ("true", "1", "yes", "on")
            elif f.type == "list":
                if isinstance(value, str):
                    value = [x.strip() for x in value.split(",") if x.strip()]
            elif f.type == "dict":
                if isinstance(value, str):
                    try:
                        value = json.loads(value)
                    except json.JSONDecodeError:
                        value = {}
            _set_path(cur, f.key, value)
    elif g.kind == "dict_of_servers":
        servers = (body or {}).get("servers", {})
        new_servers = {}
        for name, cfg in servers.items():
            new_servers[name] = {
                "enabled": bool(cfg.get("enabled", True)),
                "type": cfg.get("type", "http"),
                "url": cfg.get("url", ""),
                "headers": cfg.get("headers", {}),
                "tools": cfg.get("tools", ["*"]),
                "timeout_seconds": int(cfg.get("timeout_seconds", 300)),
            }
        raw[group] = new_servers
    elif g.kind == "skill_entries":
        entries = (body or {}).get("entries", [])
        max_file_bytes = int((body or {}).get("max_file_bytes", 131072))
        max_total_bytes = int((body or {}).get("max_total_bytes", 524288))
        raw["skills"] = {
            "max_file_bytes": max_file_bytes,
            "max_total_bytes": max_total_bytes,
            "entries": [{"path": e.get("path", ""), "enabled": bool(e.get("enabled", True))} for e in entries],
        }
    else:
        return _err(400, f"不支持的组类型: {g.kind}")

    try:
        _write_raw_config(raw)
    except Exception as exc:  # noqa: BLE001
        return _err(500, f"保存失败: {exc}")
    return 200, _ok({"group": g.key})


# ─────────────────────────── 环境变量 API ───────────────────────────

def env_list() -> tuple[int, dict]:
    """.env 列表：值掩码 + 被 config 引用位置。"""
    env_map = _env_map()
    refs = _find_env_refs(_read_raw_config())
    items = []
    for key, value in env_map.items():
        items.append({
            "key": key,
            "masked": value[:2] + "*" * 6 if value else "",
            "has_value": bool(value),
            "refs": refs.get(key, []),
        })
    # 被引用但 .env 缺失的 KEY
    missing = [key for key in refs if key not in env_map]
    items.sort(key=lambda x: x["key"])
    return 200, _ok({"env": items, "missing": sorted(missing)})


def env_put(body: dict) -> tuple[int, dict]:
    """新增/修改环境变量。"""
    key = (body or {}).get("key", "").strip()
    value = (body or {}).get("value", "")
    if not key:
        return _err(400, "缺少 key")
    if not re_match_key(key):
        return _err(400, "key 只能含字母数字下划线且不能以数字开头")
    env_map = _env_map()
    env_map[key] = value
    _write_env_file(env_map)
    return 200, _ok({"key": key})


def env_delete(key: str) -> tuple[int, dict]:
    """删除环境变量。"""
    env_map = _env_map()
    if key not in env_map:
        return _err(404, f"环境变量不存在: {key}")
    del env_map[key]
    _write_env_file(env_map)
    return 200, _ok({"key": key})


def env_refresh_process() -> tuple[int, dict]:
    """把 .env 重新 load 进进程环境（供新请求的 load_config 生效）。"""
    from dotenv import load_dotenv
    load_dotenv(_env_path(), override=True)
    return 200, _ok({})


def re_match_key(key: str) -> bool:
    import re as _re
    return bool(_re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", key))


# ─────────────────────────── 状态 API ───────────────────────────

def status() -> tuple[int, dict]:
    """服务状态：worker 通道、模型、会话数、web 配置。"""
    cfg = CTX.config
    web_cfg = getattr(cfg, "web", None)
    return 200, _ok({
        "channel": cfg.relay.channel,
        "model": cfg.copilot.model.name,
        "worker_count": cfg.messages.worker_count,
        "web": {
            "enabled": getattr(web_cfg, "enabled", True) if web_cfg else True,
            "listen_host": getattr(web_cfg, "listen_host", "127.0.0.1") if web_cfg else "127.0.0.1",
            "listen_port": getattr(web_cfg, "listen_port", 8400) if web_cfg else 8400,
        },
        "session_count": len(getattr(CTX, "copilot", None).sessions) if getattr(CTX, "copilot", None) else 0,
        "config_path": str(_config_path()),
        "env_path": str(_env_path()),
    })


# ─────────────────────────── 日志 API ───────────────────────────

def _log_path() -> Path | None:
    """返回当前日志文件路径（config.logging.file，可能为空）。"""
    cfg = getattr(CTX, "config", None)
    if cfg is None:
        return None
    logging_cfg = getattr(cfg, "logging", None)
    if logging_cfg is None:
        return None
    file_path = getattr(logging_cfg, "file", None)
    if not file_path:
        return None
    if isinstance(file_path, str):
        file_path = Path(file_path)
    # 相对路径相对 config 目录解析
    if not file_path.is_absolute():
        config_dir = getattr(cfg, "config_dir", None) or Path(".")
        if isinstance(config_dir, str):
            config_dir = Path(config_dir)
        file_path = config_dir / file_path
    return file_path


def logs_list(body: dict) -> tuple[int, dict]:
    """读取日志文件尾部。参数：lines=行数（默认 200，上限 2000）；tail=1 表示读尾部。"""
    lines = int((body or {}).get("lines", 200) or 200)
    lines = max(1, min(lines, 2000))
    path = _log_path()
    if path is None or not path.exists():
        return 200, _ok({
            "log_path": str(path) if path else None,
            "lines": [],
            "total": 0,
            "truncated": False,
            "tail": True,
        })
    try:
        # 读尾部 N 行（大文件不整读）
        size = path.stat().st_size
        chunk = 64 * 1024
        with path.open("r", encoding="utf-8", errors="replace") as fh:
            if size > chunk:
                fh.seek(max(0, size - chunk))
                # 跳过可能被截断的首行
                fh.readline()
            content = fh.read()
        all_lines = content.splitlines()
        truncated = len(all_lines) > lines
        tail_lines = all_lines[-lines:] if truncated else all_lines
        return 200, _ok({
            "log_path": str(path),
            "lines": tail_lines,
            "total": len(all_lines),
            "truncated": truncated,
            "tail": True,
        })
    except OSError as exc:
        return _err(500, f"读取日志失败: {exc}")


def restart() -> tuple[int, dict]:
    """重启 nlp_worker：Popen 拉起新进程（同命令同参数），再请求主循环退出。

    新进程用 DETACHED_PROCESS（Windows）脱离当前控制台，避免被旧进程退出带走。
    """
    import os as _os
    import subprocess as _subprocess
    import sys as _sys

    executable = _sys.executable
    if getattr(_sys, "frozen", False):
        # 打包 exe：直接重启 exe（不经过 python）
        argv = [executable, "--config", str(_config_path())]
    else:
        # 源码运行：python nlp_worker.py --config ...
        script = Path(__file__).resolve().parent.parent / "nlp_worker.py"
        argv = [executable, str(script), "--config", str(_config_path())]

    creationflags = 0
    if _sys.platform == "win32":
        creationflags = (
            _subprocess.DETACHED_PROCESS
            | _subprocess.CREATE_NEW_PROCESS_GROUP
            | _subprocess.CREATE_NO_WINDOW
        )
    try:
        proc = _subprocess.Popen(
            argv,
            cwd=str(_config_path().parent),
            creationflags=creationflags,
            close_fds=True,
            stdout=_subprocess.DEVNULL,
            stderr=_subprocess.DEVNULL,
            stdin=_subprocess.DEVNULL,
        )
    except OSError as exc:
        log.warning("重启拉起新进程失败: %s", exc)
        return _err(500, f"重启失败（拉起新进程）: {exc}")

    # 请求主循环退出（relay.stop() 置 running=False → run() 返回 → 进程自然退出）
    relay = getattr(CTX, "relay", None)
    if relay is not None:
        import asyncio
        loop = _main_loop()
        if loop is not None:
            try:
                asyncio.run_coroutine_threadsafe(
                    relay.stop(), loop
                ).result(timeout=10)
            except Exception as exc:  # noqa: BLE001
                log.warning("重启时停止 relay 失败: %s", exc)

    return 200, _ok({
        "restarted": True,
        "pid": proc.pid,
        "argv": argv,
    })
