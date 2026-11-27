# -*- coding: utf-8 -*-
"""工具调用适配层。

不同 pip 包的安装形态不一样，需要统一成"可执行命令"：
  cppcheck         -> 独立 exe，自带 DLL（任何情况都能直接跑）
  clang-tidy / clang-format / lizard -> pylibs/bin/xxx.exe
  flawfinder       -> 纯 Python 脚本，没有 exe

**打包成单文件 exe 后的关键问题**：
  frozen 模式下 sys.executable 指向 cppCheck.exe 自己，
  所以 `[sys.executable, "-m", "flawfinder"]` 会变成
  `cppCheck.exe -m flawfinder`，这个命令无效。

  解决办法：纯 Python 工具改为**进程内调用**（inproc），
  直接 import 它的 main() 并重定向 stdout/stderr，拿到同样的输出文本。
  这样打包后不需要外部 Python 环境，符合"部署环境不保证有 Python"的要求。
"""
from __future__ import annotations

import contextlib
import io
import os
import sys
from dataclasses import dataclass
from pathlib import Path

from .common import dirs, is_frozen, run


@dataclass
class Tool:
    name: str
    kind: str            # "exe" | "script" | "module" | "inproc"
    target: Path | str   # exe 路径 / 脚本路径 / 模块名
    env: dict            # 额外环境变量（PYTHONPATH 等）
    version: str = ""
    ok: bool = False

    def cmd(self, *args) -> list:
        """构造完整命令行（inproc 类型不走命令行）。"""
        a = [str(x) for x in args]
        if self.kind == "exe":
            return [str(self.target)] + a
        if self.kind == "script":
            return [sys.executable, str(self.target)] + a
        return [sys.executable, "-m", str(self.target)] + a

    def run(self, *args, timeout=600):
        """执行并返回 (returncode, 输出文本)。

        inproc 类型在进程内调用，无法设超时（Python 侧不好中断），
        但这几个工具都是毫秒级，实际没有超时风险。
        """
        if self.kind == "inproc":
            return _run_inproc(self.name, [str(x) for x in args])
        return run(self.cmd(*args), timeout=timeout, env=self.env)


# 进程内调用的适配函数表：name -> callable(args)->int
def _inproc_flawfinder(args):
    mod = _import_pylib("flawfinder")
    # flawfinder.py 是脚本式结构，顶层直接处理 sys.argv
    old = sys.argv
    try:
        sys.argv = ["flawfinder"] + args
        try:
            mod.main()
        except SystemExit as e:
            return int(e.code or 0)
        return 0
    finally:
        sys.argv = old


def _inproc_lizard(args):
    """lizard 的 --version 没实现（会把参数当路径扫描），这里自己拦一下。"""
    if args and args[0] in ("--version", "-V"):
        # 必须真的打印版本，否则 probe() 拿到空输出，
        # 版本号会退化成「已就绪」，诊断时看不出装的是哪版。
        try:
            from importlib.metadata import version as _pkg_version
            print("lizard %s" % _pkg_version("lizard"))
        except Exception:                        # noqa: BLE001
            print("lizard (内置)")
        return 0
    from lizard_core.cli import main as liz_main
    try:
        return int(liz_main(args) or 0)
    except SystemExit as e:
        return int(e.code or 0)


_INPROC = {
    "flawfinder": _inproc_flawfinder,
    "lizard": _inproc_lizard,
}


def _import_pylib(name: str):
    """把 tools/pylibs 加入 sys.path 后导入模块。"""
    p = str(dirs()["tools"] / "pylibs")
    if p not in sys.path:
        sys.path.insert(0, p)
    import importlib
    return importlib.import_module(name)


def _run_inproc(name: str, args: list):
    """在进程内执行工具，捕获 stdout/stderr。"""
    fn = _INPROC.get(name)
    if not fn:
        return -1, "unsupported inproc tool: %s" % name
    buf_out, buf_err = io.StringIO(), io.StringIO()
    rc = -1
    # 进程内调用必须临时替换 sys.argv：
    #   lizard 的 main() 里写的是 parse_args(argv or sys.argv)，
    #   传空列表时会退化成读 sys.argv，等于把 cppCheck.exe scan --src ...
    #   这些参数当成路径，从而扫描到当前目录（甚至编译器内置头文件）。
    #   flawfinder 顶层同样直接读 sys.argv。
    old_argv = sys.argv
    try:
        sys.argv = ["%s" % name] + list(args)
        with contextlib.redirect_stdout(buf_out), contextlib.redirect_stderr(buf_err):
            rc = fn(args)
    except BaseException as exc:                 # noqa: BLE001
        buf_err.write("\ninproc error: %s: %s" % (type(exc).__name__, exc))
        rc = -1
    finally:
        sys.argv = old_argv
    return rc, buf_out.getvalue() + buf_err.getvalue()


def _pylibs_env() -> dict:
    p = dirs()["tools"] / "pylibs"
    old = os.environ.get("PYTHONPATH", "")
    # 分隔符必须跟平台走：Windows 是 ';'，POSIX 是 ':'
    sep = ";" if os.name == "nt" else ":"
    return {"PYTHONPATH": str(p) + ((sep + old) if old else "")}


def resolve(name: str) -> Tool:
    """按名字解析工具，返回可调用的 Tool 对象。"""
    d = dirs()
    py = d["tools"] / "pylibs"
    pybin = py / "bin"
    env = _pylibs_env()

    if name == "cppcheck":
        exe = d["tools"] / "cppcheck" / "cppcheck.exe"
        return Tool("cppcheck", "exe", exe, {})

    # 1) pip 标准位置：pylibs/bin/<name>.exe
    exe = pybin / (name + ".exe")
    if exe.exists():
        return Tool(name, "exe", exe, env)

    # 2) pylibs 根目录
    exe = py / (name + ".exe")
    if exe.exists():
        return Tool(name, "exe", exe, env)

    # 3) 包内自带二进制，如 clang_format/data/bin/clang-format.exe
    pkg = name.replace("-", "_")
    for cand in (py / pkg / "data" / "bin" / (name + ".exe"),
                 py / pkg / "bin" / (name + ".exe"),
                 py / pkg / (name + ".exe")):
        if cand.exists():
            return Tool(name, "exe", cand, env)

    # 4) 全目录搜索（最后兜底）
    if py.exists():
        hits = sorted(py.rglob(name + ".exe"))
        if hits:
            return Tool(name, "exe", hits[0], env)

    # 5) 纯 Python 脚本形态（如 flawfinder.py）
    mod = {"clang-format": "clang_format",
           "clang-tidy": "clang_tidy"}.get(name, name)
    script = py / (mod + ".py")

    # frozen（打成单文件 exe）时没有可用的 python 解释器，
    # sys.executable 就是 cppCheck.exe 自己，必须走进程内调用。
    if is_frozen():
        if name in _INPROC:
            return Tool(name, "inproc", name, env)
        # 其他纯 Python 工具在 frozen 下无法运行，标记为不可用
        return Tool(name, "exe", pybin / (name + ".exe"), env)

    rc, _ = run([sys.executable, "-c", "import %s" % mod],
                timeout=60, env=env)
    if rc == 0 and script.exists():
        return Tool(name, "script", script, env)
    if rc == 0:
        return Tool(name, "module", mod, env)

    return Tool(name, "exe", pybin / (name + ".exe"), env)


def probe(tool: Tool, timeout=90) -> Tool:
    """探测工具是否可用，填充 ok / version。"""
    if tool.kind == "exe" and not Path(tool.target).exists():
        tool.ok, tool.version = False, "不存在"
        return tool

    # inproc 工具的版本从包元数据取，不跑 --version
    # （lizard 不认这个参数，flawfinder 的输出也夹着别的行）
    if tool.kind == "inproc":
        try:
            from importlib.metadata import version as _pkg_version
            tool.version = "%s %s" % (tool.name, _pkg_version(tool.name))
        except Exception:                        # noqa: BLE001
            # 单文件打包后通常没有包元数据，走兜底文案
            tool.version = tool.name + " (内置)"
        tool.ok = True
        # 真正验一次：跑 --version 确认能执行且不崩
        try:
            rc, out = tool.run("--version", timeout=timeout)
            if rc != 0:
                tool.ok = False
                tool.version = "执行失败: " + (out or "").strip()[:60]
        except Exception as exc:                 # noqa: BLE001
            tool.ok = False
            tool.version = str(exc)[:60]
        return tool

    try:
        rc, out = tool.run("--version", timeout=timeout)
    except Exception as exc:
        tool.ok, tool.version = False, str(exc)[:60]
        return tool
    tool.ok = rc == 0
    # 从输出里挑最能代表版本的短行（LLVM/version 关键词优先）
    lines = [l.strip() for l in (out or "").splitlines() if l.strip()]
    ver = ""
    for line in lines:
        low = line.lower()
        if "version" in low or line[:3].isdigit():
            ver = line[:70]
            break
    if not ver:
        for line in lines:
            low = line.lower()
            if not low.startswith(("usage", "error", "llvm (", "optimized")):
                ver = line[:70]
                break
    if not ver and lines:
        # LLVM 类输出：取 "LLVM version x.y.z"
        for line in lines:
            if "llvm version" in line.lower():
                ver = line[:70]
                break
    tool.version = ver or "已就绪"
    return tool


def all_tools() -> dict:
    """返回 {name: Tool}（未探测）。"""
    return {n: resolve(n) for n in
            ("cppcheck", "flawfinder", "lizard", "clang-tidy", "clang-format")}


def probe_all() -> dict:
    return {n: probe(t) for n, t in all_tools().items()}
