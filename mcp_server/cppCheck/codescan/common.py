# -*- coding: utf-8 -*-
"""公共工具：路径、日志、配置加载、子进程执行。

设计原则：
  - 所有路径基于项目根目录推算，不依赖当前工作目录
  - 日志统一带步骤前缀，便于 CI 里定位失败阶段
  - 子进程执行统一超时与编码处理（Windows 中文环境易乱码）
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path

# ---------------------------------------------------------------- 路径

def is_frozen() -> bool:
    """是否运行在 PyInstaller 打包的单文件 exe 中。"""
    return getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS")


def project_root() -> Path:
    """项目根目录。

    - 源码运行：本文件的祖父目录（cppCheck/）
    - PyInstaller --onefile：sys._MEIPASS（exe 运行时解压出的临时目录）。
      打包时用 --add-data 把 config/ data/ tools/ 放到了 _MEIPASS 根下，
      所以这里返回 _MEIPASS 就能按同样的相对路径找到它们。
    - PyInstaller --onedir：exe 所在目录
    """
    if is_frozen():
        return Path(sys._MEIPASS)          # noqa: SLF001
    return Path(__file__).resolve().parent.parent


def writable_root() -> Path:
    """可写目录。

    onefile 的 _MEIPASS 是临时目录，重启即失效，不能往里写产物。
    产物统一写到 exe 同级的 output/ 或调用方用 --out 指定。
    """
    if is_frozen():
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


def dirs() -> dict:
    """项目标准目录。

    config/data/tools 是"只读资源"，打包后在 _MEIPASS 里；
    output/build 是"可写产物"，始终相对可执行文件所在目录。
    """
    res = project_root()          # 只读资源根
    wr = writable_root()          # 可写根
    d = {
        "root": res,
        "codescan": res / "codescan",
        "tools": res / "tools",
        "config": res / "config",
        "data": res / "data",
        "docs": res / "docs",
        "output": wr / "output",
        "build": wr / "build",
    }
    return d


def ensure_dirs(*keys: str) -> None:
    """确保目录存在。"""
    d = dirs()
    for k in keys:
        d[k].mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------- 日志

class Log:
    """带步骤计数的日志器。"""

    def __init__(self, total_steps: int = 0, quiet: bool = False):
        self.total = total_steps
        self.step = 0
        self.quiet = quiet
        self.t0 = time.time()

    def phase(self, msg: str) -> None:
        self.step += 1
        if self.total:
            head = "[%d/%d]" % (self.step, self.total)
        else:
            head = "[*]"
        print("\n%s %s" % (head, msg), flush=True)

    def info(self, msg: str) -> None:
        if not self.quiet:
            print("      %s" % msg, flush=True)

    def ok(self, msg: str) -> None:
        print("      [OK] %s" % msg, flush=True)

    def warn(self, msg: str) -> None:
        print("      [WARN] %s" % msg, flush=True)

    def err(self, msg: str) -> None:
        print("      [ERROR] %s" % msg, file=sys.stderr, flush=True)

    def done(self, msg: str = "") -> None:
        cost = time.time() - self.t0
        print("\n%s%s" % (msg or "完成", "（耗时 %.1fs）" % cost), flush=True)


# ---------------------------------------------------------------- 子进程

def run(cmd, *, cwd=None, timeout=600, env=None, check=False):
    """执行子进程，返回 (returncode, stdout+stderr)。

    Windows 下统一用 utf-8 解码并忽略错误，避免 GBK 输出导致异常。
    """
    if isinstance(cmd, (list, tuple)):
        cmd = [str(x) for x in cmd]
    e = os.environ.copy()
    if env:
        e.update(env)
    # 去掉可能干扰的代理变量（部分构建机设置了失效代理，会让下载/拉取直接失败）
    for k in ("https_proxy", "http_proxy", "HTTPS_PROXY", "HTTP_PROXY",
              "all_proxy", "ALL_PROXY"):
        e.pop(k, None)
    try:
        r = subprocess.run(cmd, cwd=str(cwd) if cwd else None,
                           capture_output=True, timeout=timeout, env=e)
        out = (r.stdout or b"").decode("utf-8", "replace")
        err = (r.stderr or b"").decode("utf-8", "replace")
        blob = out + ("\n" + err if err.strip() else "")
        if check and r.returncode != 0:
            raise RuntimeError("命令失败(%d): %s\n%s"
                               % (r.returncode, " ".join(cmd[:3]), blob[:800]))
        return r.returncode, blob
    except subprocess.TimeoutExpired:
        return -9, "TIMEOUT after %ss: %s" % (timeout, " ".join(cmd[:3]))
    except FileNotFoundError as exc:
        return -2, "NOT FOUND: %s (%s)" % (cmd[0] if cmd else "?", exc)


def which(name: str):
    """查找可执行文件，返回 Path 或 None。"""
    from shutil import which as _w
    p = _w(name)
    return Path(p) if p else None


# ---------------------------------------------------------------- 配置

def load_config(path=None) -> dict:
    """加载 JSON 配置；缺失时返回内置默认值。"""
    d = dirs()
    p = Path(path) if path else (d["config"] / "scan_config.json")
    if p.exists():
        with open(p, encoding="utf-8") as f:
            return json.load(f)
    return default_config()


def default_config() -> dict:
    """内置默认配置（首次运行或无配置文件时使用）。"""
    return {
        "project_name": "未命名工程",
        "remote": {
            "enabled": False,
            "host": "",
            "port": 22,
            "user": "",
            "password": "",
            "source_dir": "",
            "private_key": "",
        },
        "local": {
            "source_dir": "",
            "include_dirs": [],
        },
        "rules": {
            "spec_file": "",
        },
        "scan": {
            "engines": ["cppcheck", "flawfinder", "lizard",
                        "clang-tidy", "custom"],
            "clang_format_check": True,
            "std": "c++14",
            "cppcheck_build_dir": "",
            "suppress": [],
            "extra_defines": [],
        },
        "report": {
            "title": "",
            "open_browser": True,
            "top_n_files": 20,
        },
    }


def save_config(cfg: dict, path=None) -> Path:
    d = dirs()
    p = Path(path) if path else (d["config"] / "scan_config.json")
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "w", encoding="utf-8", newline="\n") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)
    return p


# ---------------------------------------------------------------- 小工具

def read_text(p) -> str:
    try:
        return Path(p).read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return Path(p).read_text(encoding="gbk", errors="replace")


def rel_posix(p, base) -> str:
    try:
        return Path(p).resolve().relative_to(Path(base).resolve()).as_posix()
    except ValueError:
        return Path(p).as_posix()


def human_size(n: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024:
            return "%.1f %s" % (n, unit)
        n /= 1024.0
    return "%.1f TB" % n
