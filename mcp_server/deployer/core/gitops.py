#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""gitops.py — git 操作（查最新 tag / clone / checkout）

沿用旧版 OTA 的经验：清掉代理环境变量，否则内网 git 会走不通。
"""
import os
import shutil
import subprocess
import sys
from pathlib import Path

CREATE_NO_WINDOW = 0x08000000 if sys.platform == "win32" else 0


def no_window_flags() -> int:
    """Windows 下隐藏控制台黑窗（否则每次调外部命令都闪一下）。"""
    return CREATE_NO_WINDOW


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
            creationflags=CREATE_NO_WINDOW,
        )
        out = ((p.stdout or "") + (p.stderr or "")).strip()
        return p.returncode == 0, out
    except subprocess.TimeoutExpired:
        return False, f"命令超时({timeout}s): {' '.join(map(str, cmd))}"
    except FileNotFoundError as e:
        return False, f"命令不存在: {e}"
    except Exception as e:                                   # noqa: BLE001
        return False, str(e)


def latest_tag(repo_url: str, timeout: int = 60, vcs: str = "git") -> str:
    """查远端最新版本。git 返回最新 tag；svn 返回最新 revision 号（字符串）。"""
    vcs = (vcs or "git").lower()
    if vcs == "svn":
        return _svn_latest_rev(repo_url, timeout)
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


def _svn_exe() -> str:
    """定位 svn.exe：环境变量 SVN/SVN_EXE → PATH → 常见安装路径（TortoiseSVN/SlikSVN）。

    Windows 上 svn 命令行客户端不随系统自带：TortoiseSVN 需在安装时勾选
    "command line client tools"，装完在 <ProgramFiles>/TortoiseSVN/bin/svn.exe
    且默认不进 PATH。这里做全量兜底定位，找不到时调用方给明确安装提示。
    """
    global _SVN_EXE_CACHE
    if _SVN_EXE_CACHE:
        return _SVN_EXE_CACHE
    for var in ("SVN", "SVN_EXE"):
        v = os.environ.get(var, "")
        if v and Path(v).exists():
            _SVN_EXE_CACHE = v
            return v
    in_path = shutil.which("svn")
    if in_path:
        _SVN_EXE_CACHE = in_path
        return in_path
    pf = os.environ.get("ProgramFiles", r"C:\Program Files")
    pfx = os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")
    # Windows 才查常见安装路径（Linux 上这些路径无意义且 Path() 会抛 OSError）
    if sys.platform == "win32":
        for c in (rf"{pf}\TortoiseSVN\bin\svn.exe",
                  rf"{pfx}\TortoiseSVN\bin\svn.exe",
                  rf"{pf}\SlikSvn\bin\svn.exe",
                  rf"{pfx}\SlikSvn\bin\svn.exe",
                  rf"{pf}\VisualSVN\bin\svn.exe",
                  rf"{pfx}\VisualSVN\bin\svn.exe"):
            if Path(c).exists():
                _SVN_EXE_CACHE = c
                return c
    return ""


_SVN_EXE_CACHE = ""


def _svn_run(args: list, timeout: int = 60) -> tuple[bool, str]:
    """执行 svn 命令（自动定位 svn.exe）。找不到时给明确安装提示。"""
    exe = _svn_exe()
    if not exe:
        return False, ("未找到 svn 命令行客户端（svn.exe）。请安装 TortoiseSVN 并在安装时勾选 "
                       "\"command line client tools\"，或设置环境变量 SVN=<svn.exe 绝对路径>")
    return run([exe] + args, timeout=timeout)


def _svn_latest_rev(repo_url: str, timeout: int = 60) -> str:
    """svn 远端最新 revision（svn info --show-item revision <url>）。"""
    ok, out = _svn_run(["info", "--show-item", "revision",
                        "--non-interactive", repo_url], timeout=timeout)
    if not ok:
        return ""
    rev = (out or "").strip().splitlines()[-1].strip()
    return rev if rev.isdigit() else ""


def _svn_local_rev(src_dir: Path, timeout: int = 30) -> str:
    """svn 本地 working copy 的 revision。"""
    ok, out = _svn_run(["info", "--show-item", "revision",
                        "--non-interactive", str(src_dir)], timeout=timeout)
    if not ok:
        return ""
    rev = (out or "").strip().splitlines()[-1].strip()
    return rev if rev.isdigit() else ""



def local_tag(src_dir: Path, vcs: str = "git") -> str:
    """取本地源码目录当前版本号。svn 返回 revision；git 取 tag/分支/短 commit。"""
    src_dir = Path(src_dir)
    vcs = (vcs or "git").lower()
    if vcs == "svn":
        return _svn_local_rev(src_dir)
    if not (src_dir / ".git").exists():
        return ""
    ok, out = run(["git", "describe", "--tags", "--exact-match", "HEAD"],
                  cwd=src_dir, timeout=30)
    tag = (out or "").strip().splitlines()[-1].strip() if ok else ""
    if tag:
        return tag
    ok, out = run(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=src_dir, timeout=30)
    br = (out or "").strip().splitlines()[-1].strip() if ok else ""
    if br and br != "HEAD":
        return br
    ok, out = run(["git", "rev-parse", "--short", "HEAD"], cwd=src_dir, timeout=30)
    return (out or "").strip().splitlines()[-1].strip() if ok else ""


def source_ready(src_dir: Path, vcs: str = "git") -> bool:
    """源码目录是否已就绪（存在版本库目录：git → .git，svn → .svn）。"""
    marker = ".svn" if (vcs or "git").lower() == "svn" else ".git"
    return (Path(src_dir) / marker).exists()


def _version_key(tag: str):
    """把 v8.1 这类 tag 转成可比较的元组。非版本号排最后。"""
    s = tag.lstrip("vV")
    parts = []
    for chunk in s.replace("-", ".").replace("_", ".").split("."):
        parts.append(int(chunk) if chunk.isdigit() else -1)
    return tuple(parts) if parts else (-1,)


def prepare(repo_url: str, branch: str, src_dir: Path,
            use_tag: bool = True, tag: str = "", timeout: int = 600,
            vcs: str = "git") -> tuple[bool, str]:
    """把源码准备到 src_dir。

    - git：目录不存在 → clone；已存在 → fetch + checkout
    - svn：目录无 .svn → checkout；有 .svn → update（版本 = revision，忽略 branch/tag）
    """
    vcs = (vcs or "git").lower()
    if vcs == "svn":
        return _svn_prepare(repo_url, src_dir, timeout)

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


def _svn_prepare(repo_url: str, src_dir: Path, timeout: int = 600) -> tuple[bool, str]:
    """svn：无 .svn → checkout；有 → update。版本用 revision（trunk 直接拉最新）。"""
    src_dir = Path(src_dir)
    src_dir.parent.mkdir(parents=True, exist_ok=True)
    if not (src_dir / ".svn").exists():
        ok, out = _svn_run(["checkout", "--non-interactive",
                            repo_url, str(src_dir)], timeout=timeout)
        if not ok:
            return False, f"svn checkout 失败: {out[-500:]}"
    else:
        ok, out = _svn_run(["update", "--non-interactive", str(src_dir)],
                           timeout=timeout)
        if not ok:
            return False, f"svn update 失败: {out[-500:]}"
    rev = _svn_local_rev(src_dir)
    return True, (f"已检出 svn r{rev}" if rev else "已检出 svn（无法读 revision）")
