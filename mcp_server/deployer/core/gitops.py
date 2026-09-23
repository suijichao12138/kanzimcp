#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""gitops.py — git 操作（查最新 tag / clone / checkout）

沿用旧版 OTA 的经验：清掉代理环境变量，否则内网 git 会走不通。
"""
import os
import subprocess
from pathlib import Path


def git_env() -> dict:
    """构造干净的 git 环境：清掉可能残留的代理变量。"""
    env = dict(os.environ)
    for k in ("http_proxy", "https_proxy", "HTTP_PROXY", "HTTPS_PROXY",
              "all_proxy", "ALL_PROXY"):
        env.pop(k, None)
    # 非交互，避免卡在账号输入
    env["GIT_TERMINAL_PROMPT"] = "0"
    env["GIT_ASKPASS"] = "echo"
    return env


def run(cmd, cwd=None, timeout=600, env=None) -> tuple[bool, str]:
    """执行外部命令，返回 (成功, 输出)。"""
    try:
        p = subprocess.run(
            cmd, cwd=cwd, timeout=timeout, env=env or git_env(),
            capture_output=True, text=True, encoding="utf-8", errors="replace",
        )
        out = ((p.stdout or "") + (p.stderr or "")).strip()
        return p.returncode == 0, out
    except subprocess.TimeoutExpired:
        return False, f"命令超时({timeout}s): {' '.join(map(str, cmd))}"
    except FileNotFoundError as e:
        return False, f"命令不存在: {e}"
    except Exception as e:                                   # noqa: BLE001
        return False, str(e)


def latest_tag(repo_url: str, timeout: int = 60) -> str:
    """查远端最新 tag（按版本号排序）。

    用 ls-remote 而非 fetch，速度快、不动本地仓库。
    排序规则：v1 < v2 < ... < v8.1，用 tuple 数字比较。
    """
    ok, out = run(["git", "ls-remote", "--tags", repo_url], timeout=timeout)
    if not ok:
        return ""
    tags = []
    for line in out.splitlines():
        if "refs/tags/" not in line:
            continue
        name = line.split("refs/tags/")[-1].strip()
        if name.endswith("^{}"):           # 去掉 peeled 引用
            name = name[:-3]
        tags.append(name)
    if not tags:
        return ""
    return max(set(tags), key=_version_key)


def _version_key(tag: str):
    """把 v8.1 这类 tag 转成可比较的元组。非版本号排最后。"""
    s = tag.lstrip("vV")
    parts = []
    for chunk in s.replace("-", ".").replace("_", ".").split("."):
        parts.append(int(chunk) if chunk.isdigit() else -1)
    return tuple(parts) if parts else (-1,)


def prepare(repo_url: str, branch: str, src_dir: Path,
            use_tag: bool = True, tag: str = "", timeout: int = 600) -> tuple[bool, str]:
    """把源码准备到 src_dir。

    - 目录不存在 → clone
    - 已存在 → fetch + checkout（强制覆盖本地改动，源码目录不做人工修改）
    """
    src_dir = Path(src_dir)
    src_dir.parent.mkdir(parents=True, exist_ok=True)

    if not (src_dir / ".git").exists():
        ok, out = run(["git", "clone", repo_url, str(src_dir)], timeout=timeout)
        if not ok:
            return False, f"clone 失败: {out[-500:]}"
    else:
        ok, out = run(["git", "fetch", "--all", "--tags", "--prune"],
                      cwd=src_dir, timeout=timeout)
        if not ok:
            return False, f"fetch 失败: {out[-500:]}"

    target = f"refs/tags/{tag}" if (use_tag and tag) else branch
    ok, out = run(["git", "checkout", "-f", target], cwd=src_dir, timeout=timeout)
    if not ok:
        return False, f"checkout {target} 失败: {out[-500:]}"

    ok, out = run(["git", "rev-parse", "--short", "HEAD"], cwd=src_dir)
    commit = out.strip() if ok else "?"
    return True, f"已检出 {target} ({commit})"
