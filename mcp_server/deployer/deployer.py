#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""kanzi-deployer — KanziMCP 部署管理器（入口）

启动后在局域网提供一个管理网页，用于：
  - 首次部署：配置 → 拉源码 → 编译 → 生成配置 → 启动三组件
  - 版本升级：查看远端版本，点按钮升级（二次确认）
  - 进程管理：relay / http / feishu 单组件或全部重启
  - 配置管理：网页编辑组件配置
  - 日志查看：relay / http / feishu / deployer 分开看

用法:
    kanzi-deployer.exe                        # 启动（网页 + 后台轮询）
    kanzi-deployer.exe --no-web               # 只跑轮询（不启网页）
    kanzi-deployer.exe --check-update         # 只查一次版本，打印后退出
    kanzi-deployer.exe --config <路径>        # 指定配置文件
"""
import argparse
import logging
import os
import sys
import threading
import time
from logging.handlers import RotatingFileHandler
from pathlib import Path

# 让 core/ 和 web/ 可被导入（源码运行和 PyInstaller 都需要）
_BASE = Path(__file__).resolve().parent
if str(_BASE) not in sys.path:
    sys.path.insert(0, str(_BASE))

from core import config as cfgmod          # noqa: E402
from core import gitops, notify as notifymod  # noqa: E402
from core.paths import Paths               # noqa: E402

log = logging.getLogger("deployer")

VERSION = "1.0.0"


# ══════════════ 运行期上下文 ══════════════

class Context:
    """共享给 Web 层的上下文：配置 / 路径 / 状态。"""

    def __init__(self, cfg_path: Path, base_paths=None):
        self.cfg_path = cfg_path
        self.cfg = cfgmod.load(cfg_path)
        base = base_paths or Paths()
        # config_path=cfg_path：写盘也落回同一个文件，避免「读 A 写 B」
        self.paths = Paths(root=base.root, overrides=self.cfg.get("paths"),
                           config_path=cfg_path)
        self.paths.ensure_all()
        self._state_path = self.paths.data / "deployer_state.json"
        self.state = self._load_state()
        self._lock = threading.Lock()

    def _load_state(self) -> dict:
        import json
        if self._state_path.exists():
            try:
                return json.loads(self._state_path.read_text(encoding="utf-8"))
            except Exception:                                # noqa: BLE001
                pass
        return {"current_tag": "", "latest_tag": "", "updated_at": ""}

    def save_state(self):
        import json
        try:
            self._state_path.parent.mkdir(parents=True, exist_ok=True)
            self._state_path.write_text(
                json.dumps(self.state, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception as e:                               # noqa: BLE001
            log.warning(f"保存状态失败: {e}")

    def reload_cfg(self):
        """配置被网页改动后重新加载（并同步路径）。"""
        with self._lock:
            self.cfg = cfgmod.load(self.cfg_path)
            self.paths = Paths(root=self.paths.root,
                               overrides=self.cfg.get("paths"),
                               config_path=self.cfg_path)
            self.paths.ensure_all()


# ══════════════ 日志 ══════════════

def setup_logging(paths) -> None:
    fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    # --noconsole 打包时 sys.stdout 可能是 None，StreamHandler(None) 会报错
    try:
        if sys.stdout is not None:
            sh = logging.StreamHandler(sys.stdout)
            sh.setFormatter(fmt)
            root.addHandler(sh)
    except Exception:                                        # noqa: BLE001
        pass
    try:
        paths.logs.mkdir(parents=True, exist_ok=True)
        fh = RotatingFileHandler(paths.logs / "deployer.log", maxBytes=10 * 1024 * 1024,
                                 backupCount=5, encoding="utf-8")
        fh.setFormatter(fmt)
        root.addHandler(fh)
    except Exception as e:                                   # noqa: BLE001
        log.warning(f"文件日志启用失败: {e}")


def _write_crash_log(paths, text: str) -> None:
    """启动阶段就崩时，日志系统可能还没建好 —— 直接写文件，保证有线索。"""
    for p in (getattr(paths, "logs", None), getattr(paths, "root", None)):
        if not p:
            continue
        try:
            Path(p).mkdir(parents=True, exist_ok=True)
            (Path(p) / "deployer_crash.log").write_text(text, encoding="utf-8")
            return
        except Exception:                                    # noqa: BLE001
            continue


# ══════════════ 后台轮询（只提示，不自动升级） ══════════════

def poll_loop(ctx: "Context", stop: threading.Event) -> None:
    """定期查远端最新版本。发现新版只记状态 + 通知，绝不自动升级。

    自动升级开关（cfg.repo.auto_upgrade）默认关闭，保留字段供以后启用。
    """
    cfg = ctx.cfg.get("repo", {})
    interval = int(cfg.get("poll_interval_s", 60))

    if cfg.get("poll_check_on_start", True):
        _poll_once(ctx)

    while not stop.wait(interval):
        _poll_once(ctx)



def _hostname() -> str:
    """机器名（通知里带上，多机部署时能分清是谁）。"""
    try:
        import platform
        return os.environ.get("COMPUTERNAME") or platform.node() or "未知主机"
    except Exception:                                        # noqa: BLE001
        return "未知主机"


def _poll_once(ctx: "Context") -> None:
    try:
        repo = ctx.cfg.get("repo", {})
        if not repo.get("url"):
            return
        latest = gitops.latest_tag(repo["url"])
        if not latest:
            log.debug("未取到远端版本，跳过本轮")
            return
        ctx.state["latest_tag"] = latest
        ctx.save_state()
        current = ctx.state.get("current_tag", "")
        if latest != current:
            log.info(f"发现新版本: {current or '(无)'} → {latest}（等你在网页点升级）")
            # 通知一次即可：同一个版本只发一次，否则 60s 轮询会刷屏
            if ctx.state.get("notified_tag") != latest:
                ctx.state["notified_tag"] = latest
                ctx.save_state()
                notify_cfg = ctx.cfg.get("feishu_notify", {}) or {}
                notifymod.send(
                    notify_cfg,
                    f"🔔 kanzi-deployer 发现新版本\n"
                    f"当前：{current or '(未部署)'}\n"
                    f"最新：{latest}\n"
                    f"机器：{_hostname()}\n"
                    f"请到管理页面点「升级」。")
        else:
            log.debug(f"已是最新 {latest}")
            # 版本一致时重置标记，下次真有新版还能通知
            if ctx.state.get("notified_tag") and ctx.state["notified_tag"] != latest:
                ctx.state["notified_tag"] = ""
                ctx.save_state()
    except Exception as e:                                   # noqa: BLE001
        log.warning(f"轮询异常: {e}")


# ══════════════ 入口 ══════════════

def main():
    ap = argparse.ArgumentParser(description="KanziMCP 部署管理器")
    ap.add_argument("--config", default=None, help="配置文件路径")
    ap.add_argument("--no-web", action="store_true", help="不启动网页，只跑后台轮询")
    ap.add_argument("--check-update", action="store_true", help="只查一次版本后退出")
    ap.add_argument("--test-notify", action="store_true", help="只发一条测试通知后退出")
    ap.add_argument("--version", action="version", version=f"kanzi-deployer {VERSION}")
    args = ap.parse_args()

    # 配置文件定位：默认在安装目录下。
    # 指定 --config 时，读写都用该文件（读 A 写 B 会让人以为保存失效）。
    base = Paths()
    if args.config:
        cfg_path = Path(args.config).resolve()
        # 自定义配置一般放在安装目录之外，把路径根切到它的上级目录，
        # 这样 conf/ logs/ bin/ 等仍集中在同一处，不散落到 cwd。
        base = Paths(root=cfg_path.parent)
    else:
        cfg_path = base.deployer_config
    if not cfg_path.exists():
        cfgmod.save(cfg_path, cfgmod.DEFAULT_CONFIG)

    ctx = Context(cfg_path, base)
    setup_logging(ctx.paths)

    log.info("=" * 62)
    log.info(f"kanzi-deployer {VERSION} 启动")
    log.info(f"   安装目录: {ctx.paths.root}")
    log.info(f"   配置文件: {cfg_path}")

    if args.check_update:
        repo = ctx.cfg.get("repo", {})
        latest = gitops.latest_tag(repo.get("url", ""))
        log.info(f"本地: {ctx.state.get('current_tag') or '(无)'}  远端: {latest or '(取不到)'}")
        return

    if args.test_notify:
        ok, msg = notifymod.send(ctx.cfg.get("feishu_notify", {}),
                                 "🔔 kanzi-deployer 通知测试：收到即链路正常。")
        log.info(("✅ " if ok else "❌ ") + msg)
        return

    stop = threading.Event()

    # ── 后台轮询线程 ──
    threading.Thread(target=poll_loop, args=(ctx, stop), daemon=True,
                     name="poll").start()

    # ── 组件健康监控（挂了 / 恢复了 → 飞书通知；只通知不重启）──
    mon = None
    try:
        from core import monitor
        mon = monitor.start_monitor(ctx, log=log)
    except Exception as e:                                   # noqa: BLE001
        log.warning(f"健康监控启动失败: {e}")

    # ── Web 服务 ──
    if not args.no_web:
        try:
            from web.server import Server, local_ips
            srv = Server(ctx)
            ok, info = srv.start()
            if not ok:
                log.error(f"❌ 网页启动失败: {info}")
            else:
                log.info(f"🌐 管理页面: {info}")
                for ip in local_ips():
                    log.info(f"   局域网访问: http://{ip}:{ctx.cfg.get('web', {}).get('port', 9100)}")
                auth_cfg = (ctx.cfg.get("web") or {}).get("auth") or {}
                if auth_cfg.get("enabled") and not auth_cfg.get("password_sha256"):
                    log.warning("⚠️ 尚未设置访问密码！请在网页「设置」里设置，否则任何人可改配置")
        except Exception as e:                               # noqa: BLE001
            log.error(f"❌ 网页启动异常: {e}")
    else:
        log.info("（--no-web：未启动网页）")

    log.info("运行中，Ctrl+C 退出")
    try:
        while True:
            time.sleep(3600)
    except KeyboardInterrupt:
        log.info("已停止")


if __name__ == "__main__":
    import traceback
    try:
        main()
    except KeyboardInterrupt:
        pass
    except Exception as e:                                   # noqa: BLE001
        logging.getLogger("deployer").error(f"启动失败: {e}", exc_info=True)
        # 兜底：日志系统可能还没建好，直接写崩溃文件，保证有线索
        try:
            from core.paths import Paths as _P
            _write_crash_log(_P(),
                             f"kanzi-deployer 启动失败\n{'=' * 50}\n"
                             f"{traceback.format_exc()}\n")
        except Exception:                                    # noqa: BLE001
            pass
        sys.exit(1)
