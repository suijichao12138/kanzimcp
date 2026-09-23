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

from core import config as cfgmod, gitops


def local_ips():
    """惰性导入，避免与 web.server 循环依赖。"""
    from web.server import local_ips as _li
    return _li()
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


def _err(msg: str, code: int = 400, extra: dict | None = None):
    body = {"ok": False, "error": msg}
    if extra:
        body.update(extra)
    return code, body


# ══════════════════════ 状态 ══════════════════════


def _missing_configs(paths) -> list:
    """缺失的组件配置文件（页面提示用）。"""
    want = [
        ("config.json", paths.comp_config("http")),
        ("users.json", paths.users_json()),
        ("feishu_config.json", paths.comp_config("feishu")),
    ]
    return [name for name, p in want if not p.exists()]


_HEALTH_CACHE: dict = {}          # name -> (ts, ok, detail)
_HEALTH_TTL = 2.0                 # 秒


def _health_cached(name: str, hc: dict) -> tuple:
    """带短缓存的健康检查（3 秒轮询不重复探活）。"""
    if not hc:
        return False, "未配置检查"
    import time
    now = time.time()
    hit = _HEALTH_CACHE.get(name)
    if hit and now - hit[0] < _HEALTH_TTL:
        return hit[1], hit[2]
    ok, detail = health.check_one(hc)
    _HEALTH_CACHE[name] = (now, ok, detail)
    return ok, detail

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
        # 探活有超时（port 探测 1.5s/个），而总览 3 秒刷一次 → 加 2 秒缓存，
        # 避免每轮都重新探活导致页面发卡。
        h_ok, h_detail = _health_cached(name, hc)
        comps.append({
            "name": name,
            "running": running,
            "pid": process.pid_of(name),
            "health_ok": h_ok,
            "health_detail": h_detail,
            "exe": exe_name,
        })

    # 版本信息：以源码目录的真实 tag 为准（一键部署不再依赖 state 里有没有值）。
    # state.current_tag 作为兜底（源码目录被清掉时仍能显示上次部署的版本）。
    local_tag = gitops.local_tag(paths.src) or str(ctx.state.get("current_tag", ""))
    if local_tag and local_tag != ctx.state.get("current_tag"):
        ctx.state["current_tag"] = local_tag
        ctx.save_state()
    latest_tag = ctx.state.get("latest_tag", "")
    # 是否已部署过：源码目录就绪 或 有本地版本号
    deployed = gitops.source_ready(paths.src) or bool(local_tag)
    return _ok({
        "local_ips": local_ips(),
        "components": comps,
        "local_tag": local_tag,
        "latest_tag": latest_tag,
        "deployed": deployed,
        # 未部署过 → 不允许「升级」；已是同一版本 → 也没得升
        "upgrade_available": bool(deployed and latest_tag and latest_tag != local_tag),
        "up_to_date": bool(deployed and latest_tag and latest_tag == local_tag),
        "update_available": bool(latest_tag and latest_tag != local_tag),
        "config_ready": paths.comp_config("http").exists(),
        "config_missing": _missing_configs(paths),
        "whitelist_empty": not list((_cfg_read_json(paths.users_json()) or {}).get("users") or []),
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
    paths_ = ctx.paths

    # 首次使用（还没部署过任何东西）→ 不该走「升级」，应该先「一键部署」
    local_now = gitops.local_tag(paths_.src) or str(ctx.state.get("current_tag", ""))
    if not gitops.source_ready(paths_.src) and not local_now:
        return _err("尚未部署过，请先点「一键部署」完成首次部署，之后才能用「升级」。",
                    409, extra={"need_deploy": True})

    tag = (body or {}).get("tag") or ctx.state.get("latest_tag") or ""
    if not tag:
        tag = gitops.latest_tag(repo.get("url", ""))
    if not tag:
        return _err("未取到目标版本", 502)

    # 已是最新 → 没必要重跑一遍（编译 + 重启是有代价的）
    if local_now and tag == local_now:
        return _err(f"当前已是最新版本 {tag}，无需升级。", 409,
                    extra={"already_latest": True, "tag": tag})

    cfg, paths = ctx.cfg, ctx.paths
    notify_cfg = cfg.get("feishu_notify", {})
    host = os.environ.get("COMPUTERNAME") or os.uname().nodename

    def job(task):
        task.update("start", f"目标版本 {tag}，开始升级", 1)
        result = {}
        ok, msg = deploy.do_deploy(
            cfg, paths, tag=tag, result=result,
            progress=lambda k, m, p=0: task.update(k, m, p),
        )
        if ok:
            ctx.state["current_tag"] = result.get("tag") or tag
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



def _need_config(reason: str, hint: str) -> tuple:
    """前置检查未通过：返回 409 + need_config 标记，前端据此弹窗跳转配置页。"""
    return _err(f"{reason}。{hint}", 409, extra={"need_config": True,
                                                  "goto": "config",
                                                  "reason": reason})

def deploy_now(ctx, body: dict) -> tuple:
    """一键部署（不比对版本，直接用当前/指定版本走完整流程）。"""
    if tasks.any_running():
        return _err("已有任务在执行中，请等它结束", 409)
    cfg, paths = ctx.cfg, ctx.paths
    tag = (body or {}).get("tag") or ctx.state.get("current_tag") or ""

    # 部署前置检查：不合格就别启动任务，交给前端弹窗引导去「配置」页
    miss = _missing_configs(paths)
    if miss:
        return _need_config(
            f"缺少配置文件：{'、'.join(miss)}",
            "请到「配置」页填写并保存后再执行部署。")
    if not list((_cfg_read_json(paths.users_json()) or {}).get("users") or []):
        return _need_config(
            "http 组件白名单为空",
            "http 组件在白名单为空时会拒绝启动，请到「配置」页的 users.json 添加白名单用户。")

    notify_cfg = cfg.get("feishu_notify", {})
    host = os.environ.get("COMPUTERNAME") or os.uname().nodename

    def job(task):
        task.update("start", f"开始一键部署{'（' + tag + '）' if tag else ''}", 1)
        result = {}
        ok, msg = deploy.do_deploy(
            cfg, paths, tag=tag, result=result,
            progress=lambda k, m, p=0: task.update(k, m, p),
        )
        if ok:
            # 记录实际部署的版本：一键部署时 tag 可能为空，以源码真实 tag 为准
            ctx.state["current_tag"] = result.get("tag") or tag
            ctx.state["updated_at"] = _now()
            ctx.state["latest_tag"] = ctx.state.get("latest_tag") or ""
            ctx.save_state()
        # 通知（成功/失败都发，含环境不满足等失败原因）
        ver = result.get("tag") or tag or "(未标注版本)"
        notifymod.send(notify_cfg,
                       (f"✅ kanzi-deployer 部署成功（{ver}）\n" if ok
                        else f"❌ kanzi-deployer 部署失败（{ver}）\n")
                       + f"机器：{host}\n{msg}")
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

def _cfg_read_json(path) -> dict:
    """读已有配置文件（不存在/损坏返回 {}）。"""
    try:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    except Exception:                                        # noqa: BLE001
        pass
    return {}


def _feishu_from_real_file(ctx) -> dict:
    """从真实的 conf/feishu_config.json 回填 bots/cleanup/http。

    页面以真实文件为准，这样手工改过的配置不会被页面覆盖丢失。
    """
    raw = _cfg_read_json(ctx.paths.comp_config("feishu"))
    if not raw:
        return {}
    # 兼容旧版单 bot（顶层 app_id/relay_url）
    bots = raw.get("bots")
    if not bots and (raw.get("relay_url") or raw.get("app_id")):
        bots = [{"name": raw.get("name", "bot"),
                 "app_id": raw.get("app_id"),
                 "app_secret": raw.get("app_secret"),
                 "relay_url": raw.get("relay_url"),
                 "http_bind_ip": raw.get("http_bind_ip"),
                 "http_port": raw.get("http_port"),
                 "inbox_dir": raw.get("inbox_dir")}]
    out_bots = []
    for b in (bots or []):
        if not isinstance(b, dict):
            continue
        b = dict(b)
        b["app_secret"] = cfgmod.mask_secret((b.get("app_secret") or "").strip())
        out_bots.append(b)
    http_cfg = raw.get("http") or {}
    return {
        "http_host": http_cfg.get("host"),
        "http_port": http_cfg.get("port"),
        "cleanup": ((raw.get("cleanup") or {}).get("inbox") or {}),
        "bots": out_bots,
    }


def _http_from_real_file(ctx) -> dict:
    """从真实的 conf/config.json 回填 http 参数（含 listen 拆分）。"""
    raw = _cfg_read_json(ctx.paths.comp_config("http"))
    if not raw:
        return {}
    listen = str(raw.get("listen") or "")
    host, port = "0.0.0.0", 9001
    if ":" in listen:
        h, _, p = listen.rpartition(":")
        host = h or host
        try:
            port = int(p)
        except ValueError:
            pass
    return {
        "listen_host": host,
        "listen_port": port,
        "relay_base": raw.get("relay_base"),
        "mcp_timeout": raw.get("mcp_timeout"),
        "heartbeat_interval": raw.get("heartbeat_interval"),
        "heartbeat_max_fails": raw.get("heartbeat_max_fails"),
        "req_check_interval": raw.get("req_check_interval"),
        "result_ttl": raw.get("result_ttl"),
        "result_public_host": raw.get("result_public_host") or "",
        "result_threshold_entries": raw.get("result_threshold_entries"),
        "result_threshold_bytes": raw.get("result_threshold_bytes"),
    }


def _users_from_real_file(ctx) -> list:
    """白名单以 conf/users.json 为准。"""
    raw = _cfg_read_json(ctx.paths.users_json())
    return list(raw.get("users") or [])



def _drop_unmanaged(cfg: dict) -> None:
    """移除页面不再管理、由后端自动拼接的字段。"""
    http_cp = (cfg.get("comp_params") or {}).get("http") or {}
    for k in ("relay_base", "result_public_host"):
        http_cp.pop(k, None)
    for b in ((cfg.get("comp_params") or {}).get("feishu") or {}).get("bots") or []:
        if isinstance(b, dict):
            for k in ("http_bind_ip", "inbox_dir"):
                b.pop(k, None)

def wizard_get(ctx) -> tuple:
    """返回当前配置（脱敏）+ 可编辑的组件参数，供首次配置页回填。

    组件参数优先取真实配置文件（conf/ 下），这样手工改过的值不会丢；
    配置文件不存在时才回落到 deployer_config.json 的 comp_params。
    """
    cfg = ctx.cfg
    cp = json.loads(json.dumps(cfg.get("comp_params", {}) or {}))

    http_cp = dict(cp.get("http") or {})
    http_cp.update({k: v for k, v in _http_from_real_file(ctx).items() if v is not None})
    cp["http"] = http_cp

    fs_cp = dict(cp.get("feishu") or {})
    real_fs = _feishu_from_real_file(ctx)
    for k, v in real_fs.items():
        if v is not None and v != {} and v != []:
            fs_cp[k] = v
    cp["feishu"] = fs_cp

    users = _users_from_real_file(ctx)
    if not users:
        users = list(cfg.get("users") or [])

    return _ok({
        "repo": cfg.get("repo", {}),
        "web": {**cfg.get("web", {}),
                "auth": {**cfg.get("web", {}).get("auth", {}), "password_sha256": ""}},
        "feishu_notify": cfgmod.deep_merge(
            cfg.get("feishu_notify", {}),
            {"app_secret": cfgmod.mask_secret(
                (cfg.get("feishu_notify") or {}).get("app_secret", ""))}),
        "comp_params": cp,
        "users": users,
        "web_port": cfg.get("web", {}).get("port", 9100),
        "local_ips": local_ips(),
    })


def _restore_bot_secrets(bots_in: list, ctx) -> list:
    """bot 的 app_secret：提交的是掩码则保留真实文件里的原值。

    新增 bot（name 在旧文件里不存在）必须真填 secret，否则保持空串。
    """
    old = _cfg_read_json(ctx.paths.comp_config("feishu"))
    old_map = {}
    for b in (old.get("bots") or []):
        if isinstance(b, dict) and b.get("name"):
            old_map[b["name"]] = b.get("app_secret", "")
    out = []
    for b in (bots_in or []):
        if not isinstance(b, dict):
            continue
        b = dict(b)
        sec = (b.get("app_secret") or "").strip()
        if cfgmod.is_masked(sec) or not sec:
            b["app_secret"] = old_map.get((b.get("name") or "").strip(), "")
        out.append(b)
    return out


def _validate_comp_params(cp: dict) -> str | None:
    """校验组件参数，返回错误说明（None 表示通过）。"""
    fs = cp.get("feishu") or {}
    bots = [b for b in (fs.get("bots") or []) if isinstance(b, dict)]
    # name 唯一（组件 load_config 也会校验，这里提前拦）
    names = [(b.get("name") or "").strip() for b in bots]
    names = [n for n in names if n]
    dup = {n for n in names if names.count(n) > 1}
    if dup:
        return f"飞书 bot 名称重复: {', '.join(sorted(dup))}（名称同时是通道名，必须唯一）"
    # 注: 不校验 http_port 唯一性 —— 桥只用顶层 http.port 起一个共享文件服务，
    #     按 URL 首段 /<bot名>/ 路由，所有 bot 共用同一端口是正确的。
    # 必填项（页面只开放 3 项：名称 / App ID / App Secret）
    # 通道地址由后端按「名称 + 中继机IP + 中继端口」自动拼，页面不填也不校验。
    for b in bots:
        n = (b.get("name") or "").strip() or "(未命名)"
        if not (b.get("app_id") or "").strip():
            return f"飞书 bot「{n}」缺 App ID"
        # 掩码也允许（保存后会还原成真实值）
        sec = (b.get("app_secret") or "").strip()
        if not sec:
            return f"飞书 bot「{n}」缺 App Secret"
    return None


def wizard_put(ctx, body: dict) -> tuple:
    """保存首次配置：合并进 deployer 配置 + 生成三组件配置 + 可选启动。"""
    body = body or {}
    cfg = ctx.cfg

    for key in ("repo", "comp_params"):
        if key in body:
            cfg[key] = cfgmod.deep_merge(cfg.get(key, {}) or {}, body[key] or {})

    # 页面已不开放的字段：每次保存时从存量配置里剔除，
    # 否则旧值会一直残留并架空后端的自动拼接（relay_base 曾因此写死 127.0.0.1）。
    _drop_unmanaged(cfg)
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

    # bot 密钥：掩码 → 保留真实文件原值
    cp = cfg.get("comp_params") or {}
    if (cp.get("feishu") or {}).get("bots"):
        cp["feishu"]["bots"] = _restore_bot_secrets(cp["feishu"]["bots"], ctx)

    err = _validate_comp_params(cp)
    if err:
        return _err(err, 400)

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
