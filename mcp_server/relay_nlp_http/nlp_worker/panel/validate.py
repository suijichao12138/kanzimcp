#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""validate.py — 保存前校验（复刻 nlp_worker 的启动校验）

用户不熟配置，最大的价值就是「填的时候就告诉他哪不对」，
而不是等他启动完才发现报错。

校验分三级：
  ❌ 错误  必定启动失败（复刻 pydantic 校验器）
  ⚠️ 警告  可能出问题（例如通道名不一致的隐患）
  ✅ 提示  顺便查了连通性/目录存在性
"""
from __future__ import annotations

import os
import re
from pathlib import Path
from urllib.parse import urlparse

from yaml_io import get_path
import dotenv_io

# ══════════════════ 结果容器 ══════════════════

class Result:
    def __init__(self):
        self.errors: list[tuple[str, str]] = []      # (字段key, 说明)
        self.warns: list[tuple[str, str]] = []
        self.infos: list[tuple[str, str]] = []

    def err(self, key, msg):
        self.errors.append((key, msg))

    def warn(self, key, msg):
        self.warns.append((key, msg))

    def info(self, key, msg):
        self.infos.append((key, msg))

    @property
    def ok(self):
        return not self.errors

    def summary(self) -> str:
        parts = []
        if self.errors:
            parts.append(f"❌ {len(self.errors)} 个错误")
        if self.warns:
            parts.append(f"⚠️ {len(self.warns)} 个警告")
        if self.infos:
            parts.append(f"ℹ️ {len(self.infos)} 条提示")
        return "　".join(parts) if parts else "✅ 全部通过"


# ══════════════════ 主校验 ══════════════════

def check(data: dict, config_dir: Path | None = None,
          do_net: bool = False) -> Result:
    """校验整份配置。config_dir 用于解析相对路径。"""
    r = Result()
    base = Path(config_dir) if config_dir else Path(".")

    _check_relay(data, r)
    _check_copilot(data, r, base)
    _check_provider(data, r)
    _check_messages(data, r)
    _check_artifacts(data, r)
    _check_mcp(data, r)
    _check_paths(data, r, base)
    _check_env(data, r, base)

    if do_net:
        _check_network(data, r)

    return r


# ── 中继 ──────────────────────────────────────────────────────

def _check_relay(data: dict, r: Result) -> None:
    url = (get_path(data, "relay.url") or "").strip()
    channel = (get_path(data, "relay.channel") or "").strip()
    allowed = get_path(data, "relay.allowed_channels") or []

    if not url:
        r.err("relay.url", "中继地址没填")
    else:
        p = urlparse(url)
        if p.scheme not in ("ws", "wss") or not p.netloc:
            r.err("relay.url", "必须是 ws:// 或 wss:// 开头的地址")
        else:
            # ★ 最容易填错的地方：URL 末尾那段必须 = 通道名
            path_channel = p.path.strip("/").rsplit("/", 1)[-1]
            if channel and path_channel != channel:
                r.err("relay.channel",
                      f"通道名「{channel}」和中继地址末尾的「{path_channel}」不一致"
                      f"（这是启动失败最常见的原因）")

    if not channel:
        r.err("relay.channel", "通道名没填")

    if not allowed:
        r.err("relay.allowed_channels", "允许的通道不能为空")
    elif channel and channel not in allowed:
        r.err("relay.allowed_channels",
              f"这里必须包含你的通道名「{channel}」，否则启动会报错")

    # 专属用户标识
    ident = get_path(data, "relay.identity.dedicated_principal_id")
    if not ident:
        r.err("relay.identity.dedicated_principal_id", "专属用户标识没填")
    elif channel and ident != channel:
        r.warn("relay.identity.dedicated_principal_id",
               f"和通道名「{channel}」不一致 —— 通常应该相同，"
               f"除非你明确知道中继侧用的是另一个名字")


# ── Copilot 认证与目录 ─────────────────────────────────────────

def _check_copilot(data: dict, r: Result, base: Path) -> None:
    use_login = get_path(data, "copilot.use_logged_in_user")
    token = get_path(data, "copilot.github_token")
    if use_login is False and not token:
        r.err("copilot.github_token",
              "关掉了「使用已登录账号」，就必须填 GitHub Token")

    work = get_path(data, "copilot.working_directory")
    if not work:
        r.err("copilot.working_directory", "工作目录没填")

    # 模型名
    if not (get_path(data, "copilot.model.name") or "").strip():
        r.err("copilot.model.name", "模型名没填")

    # 超时关系
    total = get_path(data, "copilot.response_timeout_seconds")
    idle = get_path(data, "copilot.max_idle_seconds")
    if isinstance(total, (int, float)) and isinstance(idle, (int, float)):
        if idle > total:
            r.warn("copilot.max_idle_seconds",
                   f"最大空闲({idle}s) 大于总超时({total}s) —— "
                   f"空闲检测永远不会触发，等于总超时说了算")


# ── 模型服务商 ────────────────────────────────────────────────

def _check_provider(data: dict, r: Result) -> None:
    ptype = get_path(data, "copilot.model.provider.type") or "github"
    base_url = (get_path(data, "copilot.model.provider.base_url") or "").strip()
    api_key = get_path(data, "copilot.model.provider.api_key")

    if ptype == "github":
        if base_url:
            r.err("copilot.model.provider.base_url",
                  "服务商类型是 github 时不能填服务地址（写了会启动报错）")
    else:
        if not base_url:
            r.err("copilot.model.provider.base_url",
                  f"服务商类型是 {ptype}（自带模型），必须填服务地址")
        elif not re.match(r"^https?://", base_url):
            r.err("copilot.model.provider.base_url",
                  "服务地址必须以 http:// 或 https:// 开头")
        if not api_key:
            r.warn("copilot.model.provider.api_key",
                   "没填 API 密钥 —— 有些服务商允许匿名，但多数会拒绝")
        elif isinstance(api_key, str) and not api_key.startswith("${") \
                and len(api_key) > 20:
            r.warn("copilot.model.provider.api_key",
                   "密钥是明文写在这里的 —— 建议改成 ${环境变量名}，"
                   "避免密钥跟着配置文件一起被传出去")


# ── 消息 ──────────────────────────────────────────────────────

def _check_messages(data: dict, r: Result) -> None:
    wc = get_path(data, "messages.worker_count")
    mode = get_path(data, "relay.identity.mode") or "dedicated_channel"
    if mode == "dedicated_channel" and wc is not None and wc != 1:
        r.err("messages.worker_count",
              f"专属通道模式下 worker_count 必须是 1（当前 {wc}）")

    mi = get_path(data, "messages.max_input_chars")
    mo = get_path(data, "messages.max_output_chars")
    if isinstance(mi, (int, float)) and mi > 100000:
        r.err("messages.max_input_chars", "超出上限 100000")
    if isinstance(mo, (int, float)) and mo > 100000:
        r.err("messages.max_output_chars", "超出上限 100000")


# ── 工件下载 ──────────────────────────────────────────────────

def _check_artifacts(data: dict, r: Result) -> None:
    enabled = get_path(data, "artifacts.enabled")
    origins = get_path(data, "artifacts.allowed_origins") or []
    if enabled:
        if not origins:
            r.err("artifacts.allowed_origins",
                  "启用了工件下载，就必须填「允许的来源」")
        if not get_path(data, "copilot.base_directory"):
            r.err("copilot.base_directory",
                  "启用了工件下载，就必须填「数据目录」")
    for o in origins:
        p = urlparse(str(o))
        try:
            port = p.port
        except ValueError:
            port = None
        if p.scheme not in ("http", "https") or not p.hostname or port is None:
            r.err("artifacts.allowed_origins",
                  f"「{o}」格式不对 —— 必须写成 http(s)://主机:端口，"
                  f"不能带路径或参数")


# ── MCP ──────────────────────────────────────────────────────

def _check_mcp(data: dict, r: Result) -> None:
    servers = get_path(data, "mcp_servers") or {}
    channel = (get_path(data, "relay.channel") or "").strip()
    if not isinstance(servers, dict) or not servers:
        r.warn("mcp_servers",
               "没有配置任何 MCP 服务器 —— Copilot 将无法操作 Kanzi")
        return

    for name, cfg in servers.items():
        if not isinstance(cfg, dict):
            continue
        key = f"mcp_servers.{name}"
        stype = cfg.get("type", "http")
        if not cfg.get("enabled"):
            continue
        if stype in ("http", "sse"):
            url = (cfg.get("url") or "").strip()
            if not url:
                r.err(f"{key}.url", f"MCP「{name}」是 {stype} 类型，必须填地址")
            elif not re.match(r"^https?://", url):
                r.err(f"{key}.url", f"MCP「{name}」地址必须以 http:// 开头")
        elif stype in ("stdio", "local"):
            if not (cfg.get("command") or "").strip():
                r.err(f"{key}.command",
                      f"MCP「{name}」是本地服务，必须填启动命令")

        # ★ X-Kanzi-User 必须等于通道名
        headers = cfg.get("headers") or {}
        if isinstance(headers, dict):
            u = headers.get("X-Kanzi-User")
            if u and channel and u != channel:
                r.err(f"{key}.headers",
                      f"MCP「{name}」的 X-Kanzi-User「{u}」"
                      f"和通道名「{channel}」不一致 —— http 组件会返回 403")


# ── 路径存在性 ────────────────────────────────────────────────

def _check_paths(data: dict, r: Result, base: Path) -> None:
    def resolve(v) -> Path:
        p = Path(str(v))
        return p if p.is_absolute() else (base / p)

    work = get_path(data, "copilot.working_directory")
    if work:
        p = resolve(work)
        if not p.exists():
            r.err("copilot.working_directory",
                  f"目录不存在：{p}")
        elif not p.is_dir():
            r.err("copilot.working_directory",
                  f"不是目录：{p}")
        else:
            r.info("copilot.working_directory", f"目录存在：{p}")


# ── 连通性（可选，会阻塞）─────────────────────────────────────

def _check_network(data: dict, r: Result) -> None:
    """试着连一下中继和 MCP 服务。"""
    url = (get_path(data, "relay.url") or "").strip()
    if url:
        p = urlparse(url)
        if p.hostname and p.port:
            ok = _tcp(p.hostname, p.port, 2.0)
            if ok:
                r.info("relay.url", f"中继可连通（{p.hostname}:{p.port}）✅")
            else:
                r.warn("relay.url",
                       f"连不上中继 {p.hostname}:{p.port} —— "
                       f"服务没启动、IP/端口写错、或防火墙拦了")

    servers = get_path(data, "mcp_servers") or {}
    if isinstance(servers, dict):
        seen = set()
        for name, cfg in servers.items():
            if not isinstance(cfg, dict) or not cfg.get("enabled"):
                continue
            if cfg.get("type") not in ("http", "sse"):
                continue
            p = urlparse(str(cfg.get("url") or ""))
            if not p.hostname:
                continue
            port = p.port or (443 if p.scheme == "https" else 80)
            if (p.hostname, port) in seen:
                continue
            seen.add((p.hostname, port))
            if _tcp(p.hostname, port, 2.0):
                r.info(f"mcp_servers.{name}.url",
                       f"MCP 服务可连通（{p.hostname}:{port}）✅")
            else:
                r.warn(f"mcp_servers.{name}.url",
                       f"连不上 MCP 服务 {p.hostname}:{port}")


def _tcp(host: str, port: int, timeout: float) -> bool:
    import socket
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


# ══════════════════ 环境变量检查 ══════════════════

def check_env_refs(data: dict, config_dir: Path | None = None) -> list[str]:
    """找出配置里引用了但没设的环境变量。

    ★ 必须同时看 .env —— nlp_worker 启动时 load_dotenv(config.yaml 同级/.env)，
      所以值写在 .env 里同样算「已设置」。
      只查 os.environ 会把 .env 里的值误判成缺失。
    """
    dotenv_pairs: dict = {}
    if config_dir:
        try:
            dotenv_pairs = dotenv_io.load(dotenv_io.env_path_for(config_dir))[0]
        except Exception:                                    # noqa: BLE001
            dotenv_pairs = {}

    missing: set[str] = set()
    pattern = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}")

    def walk(node):
        if isinstance(node, str):
            for m in pattern.finditer(node):
                name = m.group(1)
                if dotenv_pairs.get(name):
                    continue
                if os.environ.get(name) is not None:
                    continue
                missing.add(name)
        elif isinstance(node, dict):
            for v in node.values():
                walk(v)
        elif isinstance(node, list):
            for v in node:
                walk(v)

    walk(data)
    return sorted(missing)


def _check_env(data: dict, r: "Result", base: Path) -> None:
    """检查 ${...} 引用是否都能解析（.env + 系统环境变量）。"""
    missing = check_env_refs(data, base / "config.yaml")
    for name in missing:
        r.err(
            "env." + name,
            f"${{{name}}} 在 .env 和系统环境变量里都没有 —— 启动会失败。"
            f"请在「密钥 (.env)」页签填上 {name}=...",
        )
