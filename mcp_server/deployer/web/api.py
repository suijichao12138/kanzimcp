#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""api.py — 所有 /api/* 的处理逻辑

每个 handle_* 返回 (HTTP状态码, 响应体 dict)。路由分发在 server.py。
"""
import json
import os
import subprocess
import sys
from pathlib import Path

from core import config as cfgmod
from core import deploy, envcheck, gitops, health, logs, notify as notifymod, process, templates

from . import auth, tasks

# 长任务互斥：升级/部署/重启期间拒绝其他改机器操作
_EXCLUSIVE_KINDS = ("upgrade", "deploy")


def _ok(data=None, **kw):
    body = {"ok": True}
    if data is not None:
        body["data"] = data
    body.update(kw)
    return 200, body


def _err(msg: str, code: int = 400):
    return code, {"ok": False, "error": msg}


# ══════════════════════ 状态 ══════════════════════

def status(ctx) -> tuple:
    """总览：版本、三组件状态、健康检查、环境。"""
    cfg, paths = ctx.cfg, ctx.paths
    components = cfg.get("components") or cfgmod.DEFAULT_COMPONENTS
    order = cfgmod.START_ORDER

    comps = []
    for name in order:
        comp = components.get(name, {})
        exe_name = comp.get("exe_name", f"{name}.exe")
        running = process.is_running(name, exe_name)
        hc = comp.get("health") or {}
        h_ok, h_detail = (health.check_one(hc) if hc else (False, "未配置检查"))
        comps.append({
            "name": name,
            "running": running,
            "pid": process.pid_of(name),
            "health_ok": h_ok,
            "health_detail": h_detail,
            "exe": exe_name,
        })

    # 版本信息（本地 = git describe 源码目录；远端 = ls-remote）
    local_tag = ctx.state.get("current_tag", "")
    return _ok({
        "components": comps,
        "local_tag": local_tag,
        "latest_tag": ctx.state.get("latest_tag", ""),
        "update_available": bool(ctx.state.get("latest_tag")
                                 and ctx.state["latest_tag"] != local_tag),
        "config_ready": paths.comp_config("http").exists(),
        "web_port": cfg.get("web", {}).get("port", 9100),
        "task_running": tasks.any_running(),
        "logs": logs.stats(paths),
    })


def check_update(ctx) -> tuple:
    """只查远端最新版本，不改任何东西。"""
    cfg = ctx.cfg
    repo = cfg.get("repo", {})
    latest = gitops.latest_tag(repo.get("url", ""))
    local = ctx.state.get("current_tag", "")
    ctx.state["latest_tag"] = latest
    ctx.save_state()
    if not latest:
        return _err("未能取到远端版本（检查网络或仓库地址）", 502)
    return _ok({"local": local, "latest": latest, "update_available": latest != local})


# ══════════════════════ 升级 / 部署 ══════════════════════

def upgrade(ctx, body: dict) -> tuple:
    """触发升级（长任务）。body: {"tag": "v8.1"} 可选，默认最新。"""
    if tasks.any_running():
        return _err("已有任务在执行中，请等它结束", 409)
    repo = ctx.cfg.get("repo", {})
    tag = (body or {}).get("tag") or ctx.state.get("latest_tag") or ""
    if not tag:
        tag = gitops.latest_tag(repo.get("url", ""))
    if not tag:
        return _err("未取到目标版本", 502)

    cfg, paths = ctx.cfg, ctx.paths
    notify_cfg = cfg.get("feishu_notify", {})
    host = os.environ.get("COMPUTERNAME") or os.uname().nodename

    def job(task):
        task.update("start", f"目标版本 {tag}，开始升级", 1)
        ok, msg = deploy.do_deploy(
            cfg, paths, tag=tag,
            progress=lambda k, m, p=0: task.update(k, m, p),
        )
        if ok:
            ctx.state["current_tag"] = tag
            ctx.state["updated_at"] = _now()
            ctx.save_state()
            notifymod.send(notify_cfg,
                           f"✅ kanzi-deployer 升级成功（{tag}）\n机器：{host}\n{msg}")
        else:
            notifymod.send(notify_cfg,
                           f"❌ kanzi-deployer 升级失败（{tag}）\n机器：{host}\n{msg}")
        task.done(ok, msg)

    t = tasks.start("upgrade", f"升级到 {tag}", job)
    return _ok(t.to_dict())


def deploy_now(ctx, body: dict) -> tuple:
    """一键部署（不比对版本，直接用当前/指定版本走完整流程）。"""
    if tasks.any_running():
        return _err("已有任务在执行中，请等它结束", 409)
    cfg, paths = ctx.cfg, ctx.paths
    tag = (body or {}).get("tag") or ctx.state.get("current_tag") or ""

    def job(task):
        task.update("start", f"开始一键部署{'（' + tag + '）' if tag else ''}", 1)
        ok, msg = deploy.do_deploy(
            cfg, paths, tag=tag,
            progress=lambda k, m, p=0: task.update(k, m, p),
        )
        if ok:
            ctx.state["current_tag"] = tag
            ctx.state["updated_at"] = _now()
            ctx.save_state()
        task.done(ok, msg)

    t = tasks.start("deploy", "一键部署", job)
    return _ok(t.to_dict())


def task_get(ctx, task_id: str) -> tuple:
    d = tasks.get(task_id)
    if not d:
        return _err("任务不存在", 404)
    return _ok(d)


def task_list(ctx) -> tuple:
    return _ok(tasks.latest())


# ══════════════════════ 组件重启 ══════════════════════

def restart(ctx, body: dict) -> tuple:
    """重启组件。body: {"name": "relay"|"http"|"feishu"|"all"}"""
    if tasks.any_running():
        return _err("已有任务在执行中，请等它结束", 409)
    name = (body or {}).get("name", "")
    if name == "all":
        name = "relay"                     # relay 连带重启全部
    if name not in ("relay", "http", "feishu"):
        return _err(f"未知组件: {name}")
    cfg, paths = ctx.cfg, ctx.paths
    ok, msg = deploy.restart_component(name, cfg, paths)
    return (_ok({"name": name, "detail": msg}) if ok else _err(msg, 500))


# ══════════════════════ 配置读写 ══════════════════════

# 允许通过网页编辑的文件白名单（相对安装目录）
_EDITABLE = {
    "deployer": "deployer_config.json",
    "http": "conf/config.json",
    "users": "conf/users.json",
    "feishu": "conf/feishu_config.json",
}

# 保存后需要重启哪个组件
_RESTART_MAP = {
    "deployer": ["self"],
    "http": ["http"],
    "users": [],            # 白名单热更新，不用重启
    "feishu": [],           # 桥每 3s 重读配置，不用重启
}


def config_get(ctx, name: str) -> tuple:
    if name not in _EDITABLE:
        return _err(f"不允许访问的配置: {name}", 403)
    p = ctx.paths.root / _EDITABLE[name]
    if not p.exists():
        return _ok({"name": name, "exists": False, "content": ""})
    try:
        raw = p.read_text(encoding="utf-8")
    except Exception as e:                                   # noqa: BLE001
        return _err(f"读取失败: {e}", 500)
    # deployer 自己的配置里含密钥 → 脱敏后返回
    if name == "deployer":
        raw = _mask_config_text(raw)
    return _ok({"name": name, "exists": True, "content": raw,
                "restart": _RESTART_MAP.get(name, [])})


def config_put(ctx, name: str, body: dict) -> tuple:
    """保存配置。body: {"content": "<原始文本>"}，先校验 JSON 合法。"""
    if name not in _EDITABLE:
        return _err(f"不允许访问的配置: {name}", 403)
    content = (body or {}).get("content", "")
    try:
        parsed = json.loads(content)
    except json.JSONDecodeError as e:
        return _err(f"JSON 格式错误（第 {e.lineno} 行）: {e.msg}")

    p = ctx.paths.root / _EDITABLE[name]
    p.parent.mkdir(parents=True, exist_ok=True)

    # 备份
    if p.exists():
        import time
        bak = p.with_name(p.name + f".bak.{time.strftime('%Y%m%d_%H%M%S')}")
        try:
            bak.write_text(p.read_text(encoding="utf-8"), encoding="utf-8")
        except Exception:                                    # noqa: BLE001
            pass

    # deployer 配置：掩码字段保留原值
    if name == "deployer":
        parsed = _restore_masked(parsed, ctx.cfg)

    try:
        p.write_text(json.dumps(parsed, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception as e:                                   # noqa: BLE001
        return _err(f"写入失败: {e}", 500)

    # 重载内存配置
    if name == "deployer":
        ctx.reload_cfg()

    return _ok({"name": name, "saved": True,
                "restart": _RESTART_MAP.get(name, [])})


def _mask_config_text(raw: str) -> str:
    """把 deployer 配置里的 app_secret 打码，避免明文回显到浏览器。"""
    try:
        d = json.loads(raw)
    except Exception:                                        # noqa: BLE001
        return raw
    fn = d.get("feishu_notify")
    if isinstance(fn, dict) and fn.get("app_secret"):
        fn["app_secret"] = cfgmod.SECRET_MASK
    return json.dumps(d, ensure_ascii=False, indent=2)


def _restore_masked(parsed: dict, old_cfg: dict) -> dict:
    """提交的掩码值不动原值。"""
    fn = parsed.get("feishu_notify")
    if isinstance(fn, dict) and cfgmod.is_masked(fn.get("app_secret", "")):
        fn["app_secret"] = (old_cfg.get("feishu_notify") or {}).get("app_secret", "")
    return parsed


# ══════════════════════ 引导配置（首次部署） ══════════════════════

def wizard_get(ctx) -> tuple:
    """返回当前配置（脱敏）+ 可编辑的组件参数，供首次配置页回填。"""
    cfg = ctx.cfg
    return _ok({
        "repo": cfg.get("repo", {}),
        "web": {**cfg.get("web", {}),
                "auth": {**cfg.get("web", {}).get("auth", {}), "password_sha256": ""}},
        "feishu_notify": cfgmod.deep_merge(
            cfg.get("feishu_notify", {}),
            {"app_secret": cfgmod.mask_secret(
                (cfg.get("feishu_notify") or {}).get("app_secret", ""))}),
        "comp_params": cfg.get("comp_params", {}),
        "users": cfg.get("users", []),
        "web_port": cfg.get("web", {}).get("port", 9100),
    })


def wizard_put(ctx, body: dict) -> tuple:
    """保存首次配置：合并进 deployer 配置 + 生成三组件配置 + 可选启动。"""
    body = body or {}
    cfg = ctx.cfg

    for key in ("repo", "comp_params"):
        if key in body:
            cfg[key] = cfgmod.deep_merge(cfg.get(key, {}) or {}, body[key] or {})
    if "users" in body:
        cfg["users"] = body["users"] or []
    if "feishu_notify" in body:
        fn_in = dict(body["feishu_notify"] or {})
        if cfgmod.is_masked(fn_in.get("app_secret", "")):
            fn_in["app_secret"] = (cfg.get("feishu_notify") or {}).get("app_secret", "")
        cfg["feishu_notify"] = cfgmod.deep_merge(cfg.get("feishu_notify", {}) or {}, fn_in)
    if "web" in body:
        w_in = dict(body["web"] or {})
        pw = w_in.pop("password", "")
        cfg["web"] = cfgmod.deep_merge(cfg.get("web", {}) or {}, w_in)
        if pw:
            cfg["web"].setdefault("auth", {})["password_sha256"] = auth.hash_password(pw)

    try:
        cfgmod.save(ctx.paths.deployer_config, cfg)
    except Exception as e:                                   # noqa: BLE001
        return _err(f"保存配置失败: {e}", 500)

    results = templates.write_all(cfg, ctx.paths)
    ctx.reload_cfg()
    return _ok({"saved": True, "files": results})


# ══════════════════════ 环境 / 日志 ══════════════════════

def env_status(ctx) -> tuple:
    cfg = ctx.cfg.get("build", {})
    r = envcheck.check_all(cfg.get("python_exe", "python"),
                           cfg.get("pyinstaller", "pyinstaller"))
    return _ok(r)


def logs_get(ctx, name: str, lines: int = 200) -> tuple:
    if name not in logs.COMPONENTS:
        return _err(f"未知日志: {name}")
    return _ok(logs.read_tail(name, ctx.paths, lines=lines))


def logs_clear(ctx, name: str) -> tuple:
    if name not in logs.COMPONENTS:
        return _err(f"未知日志: {name}")
    ok, msg = logs.clear(name, ctx.paths)
    return _ok({"detail": msg}) if ok else _err(msg, 500)


def test_notify(ctx) -> tuple:
    if tasks.any_running():
        return _err("已有任务在执行中", 409)
    ok, msg = notifymod.send(ctx.cfg.get("feishu_notify", {}),
                             "🔔 kanzi-deployer 通知测试：收到即链路正常。")
    return _ok({"detail": msg}) if ok else _err(msg, 500)


def _now() -> str:
    import time
    return time.strftime("%Y-%m-%d %H:%M:%S")
