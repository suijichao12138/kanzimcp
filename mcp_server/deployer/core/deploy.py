#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""deploy.py — 部署 / 升级编排（串起 git → build → stop → deploy → start → health）

失败时自动回滚（用 _backup 里升级前的 exe）。
"""
import json
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
            # 文件可能正被运行中的进程占用（共享读通常没问题，但保险起见重试）
            for attempt in range(3):
                try:
                    shutil.copy2(exe, target)
                    backups[name] = target
                    break
                except Exception:                            # noqa: BLE001
                    if attempt < 2:
                        time.sleep(1.0)
    return backups


def _missing_configs(paths) -> list:
    """列出缺失的组件配置文件（http / users / feishu）。"""
    want = [
        ("config.json", paths.comp_config("http")),
        ("users.json", paths.users_json()),
        ("feishu_config.json", paths.comp_config("feishu")),
    ]
    return [name for name, p in want if not p.exists()]


def _read_users(paths) -> list:
    """读 conf/users.json 里的白名单（部署后以此为准）。"""
    try:
        data = json.loads(paths.users_json().read_text(encoding="utf-8"))
        return list(data.get("users") or [])
    except Exception:                                        # noqa: BLE001
        return []


def _restore(backups: dict, components: dict, paths) -> None:
    """回滚：把备份的 exe 覆盖回去。

    覆盖前先清残留进程并等文件释放，否则回滚本身也会 [WinError 5] 拒绝访问，
    留下一个半新半旧的 bin/（二次部署会更难收拾）。
    """
    for name, bak in backups.items():
        exe_name = components.get(name, {}).get("exe_name", f"{name}.exe")
        exe = paths.bin / exe_name
        try:
            if process.process_exists(exe_name):
                process.kill_by_name(exe_name)
            if exe.exists():
                process.wait_file_free(exe, timeout_s=20)
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
            # 覆盖前：残留进程先杀掉，再等文件真释放。
            # Windows 上进程没退干净时删/覆盖都会 [WinError 5] 拒绝访问。
            if process.process_exists(exe_name):
                process.kill_by_name(exe_name)
            if dst.exists() and not process.wait_file_free(dst, timeout_s=20):
                return False, (f"{name} 部署失败：{exe_name} 仍被占用"
                               f"（可能仍有残留进程，请手动结束该进程后重试）")
            shutil.copy2(src, dst)
            msgs.append(f"{name} → {dst.name}")
        except Exception as e:                               # noqa: BLE001
            return False, f"{name} 部署失败: {e}"
    return True, "；".join(msgs) if msgs else "无组件部署"


def do_deploy(cfg: dict, paths, tag: str = "", progress=None, do_build: bool = True,
              result: dict | None = None):
    """完整部署/升级流程。

    progress(step_key, message, percent) 回调用于页面进度显示。
    result: 可选 dict，成功后写入 {"tag": 实际部署的版本号}，
            供调用方记录版本（一键部署时 tag 可能为空，以源码真实 tag 为准）。
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
    conf_warnings: list = []          # 非致命提醒，随成功信息一起返回
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
    target_tag = tag or ""
    actual_tag = ""          # 源码实际落在哪个版本（一键部署 tag 为空时靠这个）
    rep("git", "拉取源码 …", 10)
    ok, msg = gitops.prepare(
        repo.get("url", ""), repo.get("branch", "main"), paths.src,
        use_tag=repo.get("use_tag", True), tag=target_tag,
    )
    if not ok:
        return False, f"拉取源码失败: {msg}"
    rep("git", msg, 20)
    # 一键部署（tag 为空）时，版本号以源码真实 tag 为准
    actual_tag = gitops.local_tag(paths.src) or target_tag

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

    # ── 5. 检查配置 ──
    # 三个配置文件必须已存在（由「配置」页保存生成）。
    # 不做自动生成：缺配置时后端 /api/deploy 已提前拦下并弹窗引导去配置页，
    # 这里只兜底（比如直接调 core 内部接口时）。
    rep("conf", "检查组件配置 …", 71)
    missing = _missing_configs(paths)
    if missing:
        return False, ("缺少配置文件: " + "、".join(missing)
                       + "。请先到「配置」页填写并保存，再执行部署。")
    conf_results = templates.write_all(cfg, paths)
    bad_confs = [r["file"] for r in conf_results if not r.get("ok")]
    if bad_confs:
        return False, f"生成配置文件失败: {', '.join(bad_confs)}"
    rep("conf", "配置就绪", 73)

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
        msg = f"部署完成但健康检查未通过: {', '.join(unhealthy)}"
        if conf_warnings:
            msg += "\n⚠️ " + "\n⚠️ ".join(conf_warnings)
        return False, msg

    rep("health", "全部正常", 100)
    if result is not None:
        result["tag"] = actual_tag or target_tag
    summary = f"部署成功（{actual_tag or target_tag or repo.get('branch')}）"
    if conf_warnings:
        rep("warn", "；".join(conf_warnings), 100)
        summary += "\n⚠️ " + "\n⚠️ ".join(conf_warnings)
    return True, summary


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
