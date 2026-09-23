#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""templates.py — 从页面配置生成三个组件的配置文件

生成的产物:
  conf/config.json          http 组件（含外置结果参数）
  conf/users.json           白名单
  conf/feishu_config.json   飞书桥（多 bot）
"""
import json
import re
from pathlib import Path


def build_http_config(params: dict, paths) -> dict:
    """http 组件配置（字段名严格对应 kz_mcp_http.py 读取的键）。

    字段说明:
      listen                  监听地址:端口（0.0.0.0 让远程可连）
      relay_base              中继地址基座，每个用户连 <base>/<用户名>
      users                   白名单文件路径
      mcp_timeout             MCP 单请求超时秒数
      result_public_host      ★ 外置结果 URL 里用的 IP（必须 AI 可达，不能填 0.0.0.0）
      result_threshold_*      外置阈值
      result_tmp_dir          外置文件落盘目录
    """
    host = str(params.get("listen_host") or "0.0.0.0").strip()
    port = int(params.get("listen_port") or 9001)
    # relay 地址与对外 IP 页面不开放（手填极易写错），统一由后端按中继参数拼：
    #   relay_base         ← ws://<中继机IP>:<relay端口>
    #   result_public_host ← 同一台中继机 IP（AI 要能访问到）
    relay_ip = (params.get("relay_host") or "").strip()
    if not relay_ip:
        # 没给中继机 IP 就退回到本机探测
        try:
            from web.server import local_ips
            ips = local_ips()
            relay_ip = ips[0] if ips else "127.0.0.1"
        except Exception:                                    # noqa: BLE001
            relay_ip = "127.0.0.1"
    relay_port = int(params.get("relay_port") or 58080)
    # 强制按中继参数重算，不吃历史残留值（页面已不开放此项，旧配置里的值必须忽略）
    auto_relay_base = f"ws://{relay_ip}:{relay_port}"
    return {
        "relay_base": auto_relay_base,
        "users": str(paths.users_json()),
        "listen": f"{host}:{port}",
        "mcp_timeout": int(params.get("mcp_timeout", 1800)),
        "heartbeat_interval": int(params.get("heartbeat_interval", 30)),
        "heartbeat_max_fails": int(params.get("heartbeat_max_fails", 3)),
        "req_check_interval": int(params.get("req_check_interval", 2)),
        "result_tmp_dir": str(paths.tmp),
        "result_ttl": int(params.get("result_ttl", 1800)),
        "result_public_host": relay_ip,
        "result_threshold_entries": int(params.get("result_threshold_entries", 50)),
        "result_threshold_bytes": int(params.get("result_threshold_bytes", 4096)),
        "debug": False,
    }


def build_users_json(users: list) -> dict:
    """白名单文件（http 组件用，改它热更新不重启）。"""
    return {"users": list(users or [])}


def _cleanup_payload(src: dict) -> dict:
    """收拢 cleanup 字段。字段名严格对应 feishu_bridge._normalize_cleanup:
    enabled / max_age_days / max_files / interval_s。
    值为空（None/""）的键不写入 —— 组件靠这个区分「继承」与「显式设置」。
    """
    out: dict = {}
    src = src or {}
    if src.get("enabled") is not None:
        out["enabled"] = bool(src["enabled"])
    for k in ("max_age_days", "max_files", "interval_s"):
        v = src.get(k)
        if v is None or v == "":
            continue
        try:
            out[k] = float(v) if k != "max_files" else int(v)
        except (TypeError, ValueError):
            continue
    return out


def build_feishu_config(params: dict, paths) -> dict:
    """飞书桥配置（多 bot + 热更新 + 日志文件）。

    结构严格对应 feishu_bridge.load_config 读取的键:
      reload / http{host,port} / cleanup{inbox{...}} / bots[]
    bots[] 每项:
      name            bot 名（同时是 relay 通道名，必须唯一）
      app_id/app_secret
      relay_url       该 bot 独占的 relay 通道
      http_bind_ip    桥自身 IP（不是 nlp 的 IP）
      inbox_dir       inbox 目录

    不提供过多设项：每个 bot 只写上述 6 个字段（页面只填 3 个，其余自动拼）。
    不写 http_port（桥只用顶层 http.port 起共享文件服务，按 /<bot名>/ 路由）；
    不写每 bot 的 cleanup（统一用顶层 cleanup.inbox）。
    字段顺序与老隋给定模板一致：name → app_id → app_secret → relay_url
                                    → http_bind_ip → inbox_dir
    """
    params = params or {}
    cleanup_inbox = _cleanup_payload(params.get("cleanup") or {})
    if not cleanup_inbox:
        # 顶层未配置时给一套内置默认（与组件默认值一致）
        cleanup_inbox = {"enabled": True, "max_age_days": 7,
                         "max_files": 500, "interval_s": 3600}

    # 页面只让用户填 3 项（name / app_id / app_secret），其余全部自动拼接：
    #   relay_url   → ws://<中继机IP>:<中继端口>/<name>
    #                 （通道名 = 名称，中继按名字分槽；曾因两者不一致导致
    #                  飞书报「没有可用的 Chat Worker」）
    #   http_bind_ip→ 中继机 IP（桥自己就在中继机上）
    #   inbox_dir   → inbox_<name>
    relay_host = (params.get("relay_host") or "").strip()
    relay_port = int(params.get("relay_port") or 58080)
    bots = []
    for b in params.get("bots", []) or []:
        if not isinstance(b, dict):
            continue
        name = (b.get("name") or "").strip()
        if not name:
            continue
        # 通道地址按名称强制重算，不吃历史残留值
        relay_url = f"ws://{relay_host}:{relay_port}/{name}"
        bind_ip = relay_host or params.get("http_host", "0.0.0.0")
        bots.append({
            "name": name,
            "app_id": (b.get("app_id") or "").strip(),
            "app_secret": (b.get("app_secret") or "").strip(),
            "relay_url": relay_url,
            "http_bind_ip": bind_ip,
            "inbox_dir": (b.get("inbox_dir") or f"inbox_{name}"),
        })

    return {
        "reload": {"watch_interval_s": 3, "enabled": True},
        "bots": bots,
        "http": {"host": params.get("http_host", "0.0.0.0"),
                 "port": int(params.get("http_port", 8081))},
        "cleanup": {"inbox": cleanup_inbox},
    }


def render_all(cfg: dict, paths) -> dict:
    """按部署管理器配置，生成全部组件配置文件。

    返回 {文件名: 内容 dict}，由调用方写盘。
    """
    cp = cfg.get("comp_params", {})
    # 中继机 IP/端口注入各组件参数：relay 地址与对外 IP 由后端统一拼接，
    # 页面不开放这两项（手填极易写错）。
    relay_host = (cp.get("relay_host") or "").strip()
    if not relay_host:
        try:
            from web.server import local_ips
            ips = local_ips()
            relay_host = ips[0] if ips else "127.0.0.1"
        except Exception:                                    # noqa: BLE001
            relay_host = "127.0.0.1"

    http_params = dict(cp.get("http", {}) or {})
    http_params.setdefault("relay_host", relay_host)
    http_params.setdefault("relay_port", (cp.get("relay", {}) or {}).get("port", 58080))

    feishu_params = dict(cp.get("feishu", {}) or {})
    feishu_params.setdefault("relay_host", relay_host)

    http_cfg = build_http_config(http_params, paths)
    users_cfg = build_users_json(cfg.get("users", []))
    feishu_cfg = build_feishu_config(feishu_params, paths)
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
