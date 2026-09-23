#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""deploy.py — 部署 / 升级编排（串起 git → build → stop → deploy → start → health）

失败时自动回滚（用 _backup 里升级前的 exe）。
"""
import shutil
import time
from pathlib import Path

from . import builder, config as cfgmod, gitops, health, notify as notifymod, process, templates


def _backup_exes(components: dict, paths) -> dict:
    """升级前把现有 exe 备份到 _backup/<时间戳>/。返回 {name: 备份路径}"""
    stamp = time.strftime("%Y%m%d_%H%M%S")
    dest = paths.backup / stamp
    dest.mkdir(parents=True, exist_ok=True)
    backups = {}
    for name, comp in components.items():
        exe = paths.bin / comp.get("exe_name", f"{name}.exe")
        if exe.exists():
            target = dest / exe.name
            try:
                shutil.copy2(exe, target)
                backups[name] = target
            except Exception:                                # noqa: BLE001
                pass
    return backups


def _restore(backups: dict, components: dict, paths) -> None:
    """回滚：把备份的 exe 覆盖回去。"""
    for name, bak in backups.items():
        exe = paths.bin / components.get(name, {}).get("exe_name", f"{name}.exe")
        try:
            shutil.copy2(bak, exe)
        except Exception:                                    # noqa: BLE001
            pass


def deploy_exes(produced: dict, components: dict, paths) -> tuple[bool, str]:
    """把编译产物复制到 bin/，并清理同目录下的 back 残留。"""
    msgs = []
    for name, info in produced.items():
        if not info.get("ok") or not info.get("path"):
            msgs.append(f"{name}: 无产物，跳过")
            continue
        src = Path(info["path"])
        exe_name = components.get(name, {}).get("exe_name", f"{name}.exe")
        dst = paths.bin / exe_name
        try:
            paths.bin.mkdir(parents=True, exist_ok=True)
            if dst.exists():
                try:
                    dst.unlink()
                except OSError:
                    time.sleep(1.5)                          # 文件被占用，等一下
                    dst.unlink()
            shutil.copy2(src, dst)
            msgs.append(f"{name} → {dst.name}")
        except Exception as e:                               # noqa: BLE001
            return False, f"{name} 部署失败: {e}"
    return True, "；".join(msgs) if msgs else "无组件部署"


def do_deploy(cfg: dict, paths, tag: str = "", progress=None, do_build: bool = True):
    """完整部署/升级流程。

    progress(step_key, message, percent) 回调用于页面进度显示。
    返回 (成功, 汇总信息)
    """
    def rep(key, msg, pct=0):
        if progress:
            try:
                progress(key, msg, pct)
            except Exception:                                # noqa: BLE001
                pass

    components = cfg.get("components") or cfgmod.DEFAULT_COMPONENTS
    order = cfgmod.START_ORDER
    build_cfg = cfg.get("build", {})
    repo = cfg.get("repo", {})

    paths.ensure_all()

    # ── 1. 环境检查 ──
    rep("env", "检查环境 …", 2)
    from . import envcheck
    env = envcheck.check_all(build_cfg.get("python_exe", "python"),
                             build_cfg.get("pyinstaller", "pyinstaller"))
    if do_build and not env["ok"]:
        missing = ", ".join(i["name"] for i in env["items"] if not i["ok"] and i["required"])
        return False, f"环境不满足，缺少: {missing}"

    # ── 2. 拉源码 ──
    rep("git", "拉取源码 …", 10)
    target_tag = tag or ""
    ok, msg = gitops.prepare(
        repo.get("url", ""), repo.get("branch", "main"), paths.src,
        use_tag=repo.get("use_tag", True), tag=target_tag,
    )
    if not ok:
        return False, f"拉取源码失败: {msg}"
    rep("git", msg, 20)

    # ── 3. 备份现有 exe ──
    rep("backup", "备份现有程序 …", 22)
    backups = _backup_exes(components, paths)

    # ── 4. 编译 ──
    produced = {}
    if do_build:
        rep("build", "开始编译 …", 25)
        produced = builder.build_all(
            components, order, paths.src, paths,
            python_exe=build_cfg.get("python_exe", "python"),
            pyinstaller=build_cfg.get("pyinstaller", "pyinstaller"),
            timeout=int(build_cfg.get("timeout_s", 1800)),
            on_progress=lambda n, m: rep("build", m),
        )
        failed = [n for n, i in produced.items() if not i["ok"]]
        if failed:
            return False, "编译失败: " + "；".join(
                produced[n]["detail"] for n in failed)
        rep("build", "编译完成", 70)

    # ── 5. 生成配置 ──
    rep("conf", "生成组件配置 …", 72)
    conf_results = templates.write_all(cfg, paths)

    # ── 6. 停旧进程 ──
    rep("stop", "停止旧进程 …", 76)
    process.stop_all(list(reversed(order)), components,
                     wait_ms=int(cfg.get("kill_wait_ms", 2000)))

    # ── 7. 部署 exe ──
    if do_build:
        rep("deploy", "部署新程序 …", 82)
        ok, msg = deploy_exes(produced, components, paths)
        if not ok:
            _restore(backups, components, paths)
            return False, f"部署失败已回滚: {msg}"
        rep("deploy", msg, 86)

    # ── 8. 启动 ──
    rep("start", "启动组件 …", 90)
    starts = process.start_all(order, components, paths)
    bad = [m for _, ok_, m in starts if not ok_]
    if bad:
        return False, "启动失败: " + "；".join(bad)

    # ── 9. 健康检查 ──
    rep("health", "健康检查 …", 95)
    checks = [dict(c, name=n) for n in order for c in [components[n].get("health", {})] if c]
    result = health.wait_healthy(
        checks, timeout_s=int(cfg.get("health", {}).get("timeout_s", 30)),
        interval_s=int(cfg.get("health", {}).get("interval_s", 2)),
    )
    unhealthy = [n for n, r in result.items() if not r["ok"]]
    if unhealthy:
        # 健康检查失败不回滚（进程已起，回滚反而更乱），只报告
        rep("health", f"⚠️ 未通过: {', '.join(unhealthy)}", 100)
        return False, f"部署完成但健康检查未通过: {', '.join(unhealthy)}"

    rep("health", "全部正常", 100)
    return True, f"部署成功（{target_tag or repo.get('branch')}）"


def restart_component(name: str, cfg: dict, paths) -> tuple[bool, str]:
    """重启单个组件。

    ⚠️ relay 重启会连带重启 http 和 feishu（relay 是下游依赖）。
    """
    components = cfg.get("components") or cfgmod.DEFAULT_COMPONENTS
    if name not in components:
        return False, f"未知组件: {name}"
    wait_ms = int(cfg.get("kill_wait_ms", 2000))

    # relay 连带重启下游
    targets = ["http", "feishu"] if name == "relay" else [name]
    msgs = []

    for t in reversed(targets):           # 先停下游
        comp = components.get(t, {})
        ok, msg = process.stop(t, comp.get("exe_name", ""), wait_ms)
        msgs.append(msg)
        if not ok:
            return False, "；".join(msgs)
    if name == "relay":
        comp = components["relay"]
        ok, msg = process.stop("relay", comp.get("exe_name", ""), wait_ms)
        msgs.append(msg)
        if not ok:
            return False, "；".join(msgs)

    time.sleep(wait_ms / 1000)

    start_list = ["relay", "http", "feishu"] if name == "relay" else [name]
    for t in start_list:                  # 再按顺序起
        comp = components.get(t, {})
        exe = paths.bin / comp.get("exe_name", f"{t}.exe")
        args = process.build_args(comp.get("args_template"), paths, t, comp)
        ok, msg = process.start(t, exe, args, paths.bin)
        msgs.append(msg)
        if not ok:
            return False, "；".join(msgs)
        time.sleep(1.0)

    # 只回报目标组件的健康（连带重启的等它们自己起）
    comp = components.get(name, {})
    hc = comp.get("health")
    if hc:
        result = health.wait_healthy(
            [dict(hc, name=name)], timeout_s=int(cfg.get("health", {}).get("timeout_s", 30)))
        if not result.get(name, {}).get("ok"):
            return False, f"{name} 重启后健康检查未通过；" + "；".join(msgs)
    return True, "；".join(msgs)


def restart_all(cfg: dict, paths) -> tuple[bool, str]:
    """全部重启（等价于 relay 连带）。"""
    return restart_component("relay", cfg, paths)
