#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""templates.py — 从页面配置生成三个组件的配置文件

生成的产物:
  conf/config.json          http 组件（含外置结果参数）
  conf/users.json           白名单
  conf/feishu_config.json   飞书桥（多 bot）
"""
import json
from pathlib import Path


def build_http_config(params: dict, paths) -> dict:
    """http 组件配置。

    字段说明（对应 kz_mcp_http.py 的 config.json）:
      listen                  监听地址:端口（0.0.0.0 让远程可连）
      relay_base              中继地址基座，每个用户连 <base>/<用户名>
      users                   白名单文件路径
      mcp_timeout             MCP 单请求超时秒数
      result_public_host      ★ 外置结果 URL 里用的 IP（必须 AI 可达，不能填 0.0.0.0）
      result_threshold_*      外置阈值
      result_tmp_dir          外置文件落盘目录
    """
    return {
        "relay_base": params.get("relay_base", "ws://127.0.0.1:58080"),
        "users": str(paths.users_json()),
        "listen": params.get("listen", "0.0.0.0:9001"),
        "mcp_timeout": int(params.get("mcp_timeout", 1800)),
        "heartbeat_interval": int(params.get("heartbeat_interval", 30)),
        "heartbeat_max_fails": int(params.get("heartbeat_max_fails", 3)),
        "req_check_interval": int(params.get("req_check_interval", 2)),
        "result_tmp_dir": str(paths.tmp),
        "result_ttl": int(params.get("result_ttl", 1800)),
        "result_public_host": params.get("result_public_host") or None,
        "result_threshold_entries": int(params.get("result_threshold_entries", 50)),
        "result_threshold_bytes": int(params.get("result_threshold_bytes", 4096)),
        "debug": False,
    }


def build_users_json(users: list) -> dict:
    """白名单文件。"""
    return {"users": list(users or [])}


def build_feishu_config(params: dict, paths) -> dict:
    """飞书桥配置（多 bot + 热更新 + 日志文件）。

    bots[] 每项:
      name            bot 名（同时是 relay 通道名）
      app_id/app_secret
      relay_url       该 bot 独占的 relay 通道
      http_bind_ip    桥自身 IP（不是 nlp 的 IP）
      http_port       该 bot 的文件服务端口
      inbox_dir       inbox 目录
    """
    bots = []
    for b in params.get("bots", []) or []:
        name = (b.get("name") or "").strip()
        if not name:
            continue
        bots.append({
            "name": name,
            "app_id": b.get("app_id", ""),
            "app_secret": b.get("app_secret", ""),
            "relay_url": b.get("relay_url") or f"ws://127.0.0.1:58080/{name}",
            "http_bind_ip": b.get("http_bind_ip") or params.get("http_host", "0.0.0.0"),
            "http_port": int(b.get("http_port", params.get("http_port", 8081))),
            "inbox_dir": b.get("inbox_dir") or f"inbox_{name}",
        })
    return {
        # 文件日志由 --log-path 参数控制；这里保留 logging 节以兼容组件读取
        "logging": {"file": str(paths.comp_log("feishu")),
                    "max_bytes": 10485760, "backup_count": 5},
        "reload": {"enabled": True, "watch_interval_s": 3},
        "http": {"host": params.get("http_host", "0.0.0.0")},
        "cleanup": {"inbox": {"enabled": True, "keep_days": 7, "keep_count": 500}},
        "bots": bots,
    }


def render_all(cfg: dict, paths) -> dict:
    """按部署管理器配置，生成全部组件配置文件。

    返回 {文件名: 内容 dict}，由调用方写盘。
    """
    cp = cfg.get("comp_params", {})
    http_cfg = build_http_config(cp.get("http", {}), paths)
    users_cfg = build_users_json(cfg.get("users", []))
    feishu_cfg = build_feishu_config(cp.get("feishu", {}), paths)
    return {
        str(paths.comp_config("http")): http_cfg,
        str(paths.users_json()): users_cfg,
        str(paths.comp_config("feishu")): feishu_cfg,
    }


def write_all(cfg: dict, paths, backup: bool = True) -> list:
    """把生成的配置写盘（可选先备份原文件）。返回写入结果列表。"""
    import time
    out = []
    for path_str, content in render_all(cfg, paths).items():
        p = Path(path_str)
        p.parent.mkdir(parents=True, exist_ok=True)
        if backup and p.exists():
            bak = p.with_name(p.name + f".bak.{time.strftime('%Y%m%d_%H%M%S')}")
            try:
                bak.write_text(p.read_text(encoding="utf-8"), encoding="utf-8")
            except Exception:                                # noqa: BLE001
                pass
        try:
            p.write_text(json.dumps(content, ensure_ascii=False, indent=2),
                         encoding="utf-8")
            out.append({"file": p.name, "ok": True})
        except Exception as e:                               # noqa: BLE001
            out.append({"file": p.name, "ok": False, "detail": str(e)})
    # http 组件的 cwd 下也需要一份？不需要 —— 用 --config 指定绝对路径
    return out
