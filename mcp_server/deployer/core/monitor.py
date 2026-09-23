#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""monitor.py — 组件健康监控（挂了 / 恢复了 → 发飞书通知）

设计要点（避免刷屏）：
- 只在**状态翻转**时通知：正常→挂 发一条，挂→正常 发一条，持续挂不重复发。
- 启动后先跳过若干轮（组件可能还在起），等稳定了才开始判定。
- 只通知，不自动重启。
"""
import threading
import time

from . import config as cfgmod
from . import health, notify as notifymod, process

# 默认检测间隔（秒）
DEFAULT_INTERVAL_S = 30
# 启动后的「冷静期」：这段时间内发现问题也不通知（组件可能正在起）
DEFAULT_GRACE_S = 90


def check_components(cfg: dict) -> list[dict]:
    """跑一遍三组件健康检查，返回 [{name, running, ok, detail}]。"""
    components = cfg.get("components") or cfgmod.DEFAULT_COMPONENTS
    order = cfgmod.START_ORDER
    out = []
    for name in order:
        comp = components.get(name, {}) or {}
        exe_name = comp.get("exe_name", f"{name}.exe")
        running = process.is_running(name, exe_name)
        hc = comp.get("health") or {}
        if hc:
            h_ok, h_detail = health.check_one(hc)
        else:
            h_ok, h_detail = running, f"{exe_name} {'在运行' if running else '未运行'}"
        out.append({"name": name, "running": running, "ok": bool(h_ok), "detail": h_detail})
    return out


def format_state(items: list[dict]) -> str:
    """把一份检查结果拼成一行摘要（用于日志）。"""
    return "  ".join(
        f"{i['name']}={'OK' if i['ok'] else 'DOWN'}" for i in items
    )


class HealthMonitor:
    """后台健康监控线程。

    状态翻转才通知：
      - 正常 → 挂      发「❌ 组件异常」
      - 挂   → 恢复正常 发「✅ 组件恢复」
      - 状态不变        不发
    """

    def __init__(self, ctx, interval_s: int = DEFAULT_INTERVAL_S,
                 grace_s: int = DEFAULT_GRACE_S, log=None):
        self.ctx = ctx
        self.interval_s = max(5, int(interval_s))
        self.grace_s = max(0, int(grace_s))
        self.log = log
        self._last: dict[str, bool] = {}       # name -> 上次是否健康
        self._stop = threading.Event()

    # ── 通知 ──
    def _notify(self, text: str) -> None:
        cfg = (self.ctx.cfg or {}).get("feishu_notify", {})
        try:
            ok, msg = notifymod.send(cfg, text)
            if self.log and not ok:
                self.log.warning(f"健康告警通知未发出: {msg}")
        except Exception as e:                               # noqa: BLE001
            if self.log:
                self.log.warning(f"健康告警通知异常: {e}")

    def _machine(self) -> str:
        import os
        import platform
        try:
            return os.environ.get("COMPUTERNAME") or platform.node() or "未知主机"
        except Exception:                                    # noqa: BLE001
            return "未知主机"

    # ── 单轮 ──
    def poll_once(self, allow_notify: bool = True) -> list[dict]:
        items = check_components(self.ctx.cfg or {})
        if self.log:
            self.log.debug("组件健康: " + format_state(items))

        for it in items:
            name, ok = it["name"], it["ok"]
            prev = self._last.get(name)
            self._last[name] = ok
            if prev is None or prev == ok:
                continue                                  # 首次/无变化 → 不通知
            if not allow_notify:
                continue
            host = self._machine()
            if prev and not ok:
                self._notify(
                    f"❌ kanzi-deployer 组件异常：{name}\n"
                    f"机器：{host}\n原因：{it['detail']}")
                if self.log:
                    self.log.warning(f"组件 {name} 异常: {it['detail']}")
            elif not prev and ok:
                self._notify(
                    f"✅ kanzi-deployer 组件恢复：{name}\n"
                    f"机器：{host}\n状态：{it['detail']}")
                if self.log:
                    self.log.info(f"组件 {name} 已恢复: {it['detail']}")
        return items

    # ── 线程体 ──
    def run(self) -> None:
        # 冷静期：组件可能还在起，这期间只记录状态不通知
        grace_end = time.time() + self.grace_s
        try:
            while not self._stop.is_set():
                allow = time.time() >= grace_end
                try:
                    self.poll_once(allow_notify=allow)
                except Exception as e:                       # noqa: BLE001
                    if self.log:
                        self.log.warning(f"健康监控异常: {e}")
                if self._stop.wait(self.interval_s):
                    break
        except Exception:                                    # noqa: BLE001
            pass

    def start(self) -> threading.Thread:
        t = threading.Thread(target=self.run, daemon=True, name="health-monitor")
        t.start()
        return t

    def stop(self) -> None:
        self._stop.set()


def start_monitor(ctx, log=None) -> HealthMonitor:
    """按配置启动健康监控，返回实例（可用于 stop）。"""
    mon_cfg = (ctx.cfg or {}).get("monitor") or {}
    if mon_cfg.get("enabled") is False:
        if log:
            log.info("健康监控已关闭（monitor.enabled = false）")
        return None
    interval = int(mon_cfg.get("interval_s", DEFAULT_INTERVAL_S))
    grace = int(mon_cfg.get("grace_s", DEFAULT_GRACE_S))
    mon = HealthMonitor(ctx, interval_s=interval, grace_s=grace, log=log)
    mon.start()
    if log:
        log.info(f"健康监控已启动（每 {mon.interval_s}s，冷静期 {mon.grace_s}s，仅通知不重启）")
    return mon
