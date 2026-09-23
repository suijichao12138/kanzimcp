#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""config.py — 部署管理器配置的加载 / 保存 / 默认值

配置文件: <install>/deployer_config.json
"""
import json
import os
import tempfile
from pathlib import Path

# ── 三个组件的默认定义（可被配置覆盖）──────────────────────────────
DEFAULT_COMPONENTS = {
    "relay": {
        "exe_name": "relay_multi.exe",
        "src": "mcp_server/relay_nlp_http/relay/relay_multi.py",
        "cwd": "mcp_server/relay_nlp_http/relay",
        "pyinstaller_args": "--clean --onefile --noconsole --name relay_multi "
                            "--hidden-import websockets",
        "args_template": ["--log-path", "{logs}/relay.log"],
        "health": {"type": "port", "host": "127.0.0.1", "port": 58080},
    },
    "http": {
        "exe_name": "kz_mcp_http.exe",
        "src": "mcp_server/relay_nlp_http/http/kz_mcp_http.py",
        "cwd": "mcp_server/relay_nlp_http/http",
        "pyinstaller_args": "--onefile --noconsole --name kz_mcp_http "
                            "--hidden-import websockets",
        "args_template": ["--config", "{conf}/config.json",
                          "--log-path", "{logs}/http.log"],
        "health": {"type": "port", "host": "127.0.0.1", "port": 9001},
    },
    "feishu": {
        "exe_name": "feishu_bridge.exe",
        "src": "mcp_server/relay_nlp_http/feishu/feishu_bridge.py",
        "cwd": "mcp_server/relay_nlp_http/feishu",
        "pyinstaller_args": "--clean --onefile --noconsole --name feishu_bridge "
                            "--hidden-import websockets --hidden-import lark_oapi",
        "args_template": ["--config", "{conf}/feishu_config.json",
                          "--log-path", "{logs}/feishu.log"],
        "health": {"type": "process", "process": "feishu_bridge.exe"},
    },
}

# 组件的启动顺序（启动按此顺序，停止按反序）
START_ORDER = ["relay", "http", "feishu"]

# 配置模板初始内容
DEFAULT_CONFIG = {
    "paths": {
        "bin": "bin", "conf": "conf", "logs": "logs",
        "src": "src", "tmp": "tmp_results", "data": "data", "backup": "_backup",
    },
    "web": {
        "bind": "0.0.0.0",
        "port": 9100,
        "auth": {"enabled": True, "user": "admin", "password_sha256": ""},
    },
    # 组件健康监控：relay / http / feishu 挂了或端口不通 → 飞书通知（只通知不重启）
    # 状态变化才通知（挂了发一条、恢复了发一条），持续挂着不重复发。
    "monitor": {
        "enabled": True,      # 是否开启健康监控
        "interval_s": 30,     # 检测间隔（秒）
        "grace_s": 90,        # 启动后冷静期（秒）：这期间发现问题也不通知，避免组件还在起就误报
    },
    "repo": {
        "url": "https://gitee.com/suijichao/kanzimcp.git",
        "branch": "main",
        "use_tag": True,
        "poll_interval_s": 60,
        "auto_upgrade": False,          # 保留开关，默认关（只提示，不自动升）
    },
    "build": {
        "python_exe": "python",
        "pyinstaller": "pyinstaller",
        "timeout_s": 1800,
    },
    "kill_wait_ms": 2000,
    "health": {"timeout_s": 30, "interval_s": 2},
    "log": {"max_bytes": 10485760, "backup_count": 5},
    "feishu_notify": {
        "enabled": True,
        "app_id": "",
        "app_secret": "",
        "receive_id": "",
        "receive_id_type": "open_id",
    },
    # 组件的连接参数（用于生成 conf/ 下的配置文件）
    # 注意: 字段名必须与组件源码读取的键严格一致，否则组件会静默走默认值
    "comp_params": {
        "http": {
            "listen_host": "0.0.0.0",          # → listen: "<host>:<port>"
            "listen_port": 9001,
            "relay_base": "ws://127.0.0.1:58080",
            "mcp_timeout": 1800,
            "heartbeat_interval": 30,
            "heartbeat_max_fails": 3,
            "req_check_interval": 2,
            "result_ttl": 1800,
            "result_public_host": "",
            "result_threshold_entries": 50,
            "result_threshold_bytes": 4096,
        },
        # relay 无配置文件，仅端口（用于健康检查与生成组件参数）
        "relay": {"port": 58080},
        "feishu": {
            "http_host": "0.0.0.0",
            "http_port": 8081,
            # 顶层 cleanup.inbox —— 各 bot 未填时继承这里
            "cleanup": {
                "enabled": True,
                "max_age_days": 7,      # 组件字段名: max_age_days
                "max_files": 500,       # 组件字段名: max_files
                "interval_s": 3600,     # 组件字段名: interval_s
            },
            "bots": [],
        },
    },
    # http 白名单（写 conf/users.json；改它不需要重启）
    "users": [],
}

SECRET_MASK = "********"


def deep_merge(base: dict, override: dict) -> dict:
    """把 override 合并进 base（dict 递归，其余覆盖）。返回新 dict。"""
    out = dict(base)
    for k, v in (override or {}).items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = deep_merge(out[k], v)
        else:
            out[k] = v
    return out


def load(path: Path) -> dict:
    """读配置；不存在则用默认值。缺失的键用默认值补齐。"""
    if not path.exists():
        return json.loads(json.dumps(DEFAULT_CONFIG))
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        raw = {}
    merged = deep_merge(DEFAULT_CONFIG, raw)
    # components 若配置里没写，用内置默认
    if not merged.get("components"):
        merged["components"] = json.loads(json.dumps(DEFAULT_COMPONENTS))
    return merged


def save(path: Path, cfg: dict) -> None:
    """原子写入（先写临时文件再 rename），避免中途损坏配置。"""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=".cfg-", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(cfg, f, ensure_ascii=False, indent=2)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            try:
                os.remove(tmp)
            except OSError:
                pass


def mask_secret(value: str) -> str:
    """密钥脱敏：接口返回时用掩码，不回显明文。"""
    return SECRET_MASK if value else ""


def is_masked(value: str) -> bool:
    """提交上来的值是不是掩码（是则保留原值不覆盖）。"""
    return value == SECRET_MASK
