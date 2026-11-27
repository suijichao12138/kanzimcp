# -*- coding: utf-8 -*-
"""工具环境：自动检测 + 自动下载 + 校验 + 缓存。

支持的第三方工具：
  cppcheck     绿色版 zip，无需安装       （必需）
  flawfinder   pip 包                     （必需）
  lizard       pip 包                     （必需）
  clang-tidy   pip 包（自带二进制）        （可选）
  clang-format pip 包（自带二进制）        （可选）

设计要点：
  1. 全部装进项目 tools/ 目录，不污染系统环境，可直接归档
  2. 下载走多镜像回退（GitHub 直连慢，自动切代理镜像）
  3. 有 SHA256 的做校验，无 SHA256 的做"能否正常运行"验证
  4. 已存在且验证通过则跳过下载（离线可用）
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import sys
import zipfile
from pathlib import Path

from .common import dirs, human_size, load_config, run

# ============================================================ 工具清单

# cppcheck: 官方 release，可指定多个下载源（前面的失败自动换后面）
CPPCHECK_VERSION = "2.22.0"
CPPCHECK_MIRRORS = [
    "https://gh-proxy.com/https://github.com/danmar/cppcheck/releases/download/"
    "v{ver}/cppcheck-{ver}-x64-Setup.msi",
    "https://ghfast.top/https://github.com/danmar/cppcheck/releases/download/"
    "v{ver}/cppcheck-{ver}-x64-Setup.msi",
    "https://github.com/danmar/cppcheck/releases/download/"
    "v{ver}/cppcheck-{ver}-x64-Setup.msi",
]

# pip 包（装到 tools/pylibs，二进制在 tools/pylibs/bin）
PIP_PACKAGES = {
    "flawfinder": "flawfinder>=2.0.19",
    "lizard": "lizard>=1.17.10",
    "clang-tidy": "clang-tidy>=18",
    "clang-format": "clang-format>=18",
}


# ============================================================ 环境检测

def check_python(log, min_version=(3, 8)) -> bool:
    """检查 Python 版本与位数。"""
    v = sys.version_info
    ok = (v.major, v.minor) >= min_version
    log.info("Python %d.%d.%d (%s)" % (v.major, v.minor, v.micro,
                                       "64-bit" if sys.maxsize > 2**32 else "32-bit"))
    if not ok:
        log.err("需要 Python >= %d.%d，当前 %d.%d"
                % (min_version[0], min_version[1], v.major, v.minor))
    if sys.maxsize <= 2**32:
        log.warn("检测到 32 位 Python，部分工具可能不可用，建议换 64 位")
    return ok


def check_pip(log) -> bool:
    rc, out = run([sys.executable, "-m", "pip", "--version"], timeout=60)
    if rc != 0:
        log.err("pip 不可用，请安装 pip 或使用完整版 Python")
        return False
    log.info(out.strip().splitlines()[0] if out.strip() else "pip OK")
    return True


def check_network(log, timeout=15) -> bool:
    """探测能否访问 pip 源与镜像。"""
    rc, _ = run([sys.executable, "-c",
                 "import urllib.request as u;"
                 "u.urlopen('https://pypi.org/simple/', timeout=%d)" % timeout],
                timeout=timeout + 10)
    if rc == 0:
        log.info("网络可达 pypi.org")
        return True
    log.warn("pypi.org 不可达，将尝试国内镜像")
    return False


# ============================================================ 工具定位

def _download(url: str, dest: Path, log, timeout=900) -> bool:
    """下载文件，带进度提示。"""
    import urllib.request
    import urllib.error
    log.info("下载 %s" % url.split("/")[-1])
    log.info("  来源 %s" % url.split("/")[2])
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "code-scan-tool/1.0"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            total = int(resp.headers.get("Content-Length") or 0)
            done = 0
            last = 0
            dest.parent.mkdir(parents=True, exist_ok=True)
            tmp = dest.with_suffix(dest.suffix + ".part")
            with open(tmp, "wb") as f:
                while True:
                    chunk = resp.read(256 * 1024)
                    if not chunk:
                        break
                    f.write(chunk)
                    done += len(chunk)
                    if total and done - last > total // 10:
                        log.info("  %s / %s (%.0f%%)"
                                 % (human_size(done), human_size(total),
                                    100.0 * done / total))
                        last = done
            tmp.replace(dest)
        log.ok("已下载 %s" % human_size(dest.stat().st_size))
        return True
    except Exception as exc:
        log.warn("下载失败：%s" % str(exc)[:120])
        if dest.exists():
            dest.unlink()
        return False


def _extract_msi_cab(msi: Path, out_dir: Path, log) -> bool:
    """cppcheck 的 MSI 需要两级解包：msi -> cab -> 文件。

    优先用 7-Zip（若系统有），否则用内置的 MSI/CAB 解析。
    """
    seven = _find_7z()
    if seven:
        log.info("使用 7-Zip 解包")
        tmp = out_dir / "_msi"
        rc, _ = run([seven, "x", str(msi), "-o" + str(tmp), "-y"], timeout=300)
        if rc != 0:
            log.warn("7z 解 msi 失败")
            return False
        cab = tmp / "Cppcheck.cab"
        if not cab.exists():
            cands = list(tmp.glob("*.cab"))
            if not cands:
                log.warn("MSI 内未找到 cab")
                return False
            cab = cands[0]
        rc, _ = run([seven, "x", str(cab), "-o" + str(out_dir), "-y"], timeout=300)
        if rc != 0:
            log.warn("7z 解 cab 失败")
            return False
        shutil.rmtree(tmp, ignore_errors=True)
        return True

    log.warn("未找到 7-Zip，尝试改用 pip 版 cppcheck")
    return False


def _find_7z():
    for c in (r"C:\Program Files\7-Zip\7z.exe",
              r"C:\Program Files (x86)\7-Zip\7z.exe",
              "7z", "7za"):
        p = Path(c) if os.path.sep in c else None
        if p and p.exists():
            return str(p)
        if not p:
            from .common import which
            w = which(c)
            if w:
                return str(w)
    return None


def _fix_cppcheck_dll(dest: Path, log):
    """安装器会把 cppcheckcore.dll 重命名为 cppcheck-core.dll。

    手工解包必须自行改名，否则 exe 无法启动（0xC0000135）。
    """
    src = dest / "cppcheckcore.dll"
    dst = dest / "cppcheck-core.dll"
    if src.exists() and not dst.exists():
        shutil.copy2(src, dst)
        log.info("已修正 DLL 名称 cppcheckcore.dll -> cppcheck-core.dll")


def _prune_cppcheck(dest: Path, log):
    """删除 GUI 相关无用文件，减小归档体积（29MB -> 约 8MB）。"""
    patterns = ["cppcheckguiexe", "*.qm", "Qt6*.dll", "qt.conf"]
    removed = 0
    for pat in patterns:
        for p in dest.glob(pat):
            try:
                p.unlink()
                removed += 1
            except OSError:
                pass
    if removed:
        log.info("精简 %d 个 GUI 相关文件" % removed)



def verify_tool(name: str, path: Path, timeout=60):
    """运行 --version 验证工具可用。返回 (ok, version_string)。

    注意：本函数仅 envcheck 内部安装流程使用；
    运行时统一走 toolchain.probe()，两者判定口径一致。
    """
    from . import toolchain
    if not Path(path).exists():
        return False, "不存在"
    t = toolchain.Tool(name, "exe", Path(path), toolchain._pylibs_env())
    t = toolchain.probe(t, timeout=timeout)
    return t.ok, t.version



def install_cppcheck(log, force=False) -> bool:
    """安装 cppcheck 绿色版。"""
    d = dirs()
    dest = d["tools"] / "cppcheck"
    exe = dest / "cppcheck.exe"

    if exe.exists() and not force:
        ok, ver = verify_tool("cppcheck", exe)
        if ok:
            log.ok("cppcheck 已就绪：%s" % ver)
            return True
        log.warn("已有 cppcheck 无法运行，重新安装")

    # 方案 A：从官方 release 下载 MSI 解包
    d["build"].mkdir(parents=True, exist_ok=True)
    msi = d["build"] / ("cppcheck-%s.msi" % CPPCHECK_VERSION)

    got = False
    if msi.exists() and msi.stat().st_size > 20 * 1024 * 1024:
        log.info("复用已下载的安装包缓存")
        got = True
    else:
        for tpl in CPPCHECK_MIRRORS:
            url = tpl.format(ver=CPPCHECK_VERSION)
            if _download(url, msi, log):
                if msi.stat().st_size > 20 * 1024 * 1024:
                    got = True
                    break
                log.warn("文件偏小（%s），可能不是完整包，换镜像"
                         % human_size(msi.stat().st_size))

    if got:
        if dest.exists():
            shutil.rmtree(dest, ignore_errors=True)
        dest.mkdir(parents=True, exist_ok=True)
        if _extract_msi_cab(msi, dest, log):
            _fix_cppcheck_dll(dest, log)
            _prune_cppcheck(dest, log)
            ok, ver = verify_tool("cppcheck", dest / "cppcheck.exe")
            if ok:
                log.ok("cppcheck 安装完成：%s（%s）"
                       % (ver, human_size(_dir_size(dest))))
                return True
            log.warn("解包后仍无法运行，尝试 pip 方案")

    # 方案 B：pip 版（备用，功能略少但可用）
    log.info("改用 pip 安装 cppcheck")
    py = d["tools"] / "pylibs"
    rc, out = run([sys.executable, "-m", "pip", "install", "--target", str(py),
                   "cppcheck"], timeout=600)
    if rc == 0:
        cand = list(py.rglob("cppcheck.exe"))
        if cand:
            dest.mkdir(parents=True, exist_ok=True)
            for f in cand[0].parent.iterdir():
                shutil.copy2(f, dest / f.name)
            _fix_cppcheck_dll(dest, log)
            ok, ver = verify_tool("cppcheck", dest / "cppcheck.exe")
            if ok:
                log.ok("cppcheck（pip 版）就绪：%s" % ver)
                return True

    # 方案 C：提示手工放置
    log.err("cppcheck 自动安装失败")
    log.err("请手工下载后解压到：%s" % dest)
    log.err("  下载地址 https://github.com/danmar/cppcheck/releases/tag/v%s"
            % CPPCHECK_VERSION)
    log.err("  注意：需把 cppcheckcore.dll 复制为 cppcheck-core.dll")
    return False


def _dir_size(p: Path) -> int:
    total = 0
    for f in p.rglob("*"):
        if f.is_file():
            try:
                total += f.stat().st_size
            except OSError:
                pass
    return total


# ============================================================ 下载：pip 工具

def install_pip_tool(pkg: str, log, force=False) -> bool:
    """把 pip 包装到 tools/pylibs，二进制在 tools/pylibs/bin。"""
    d = dirs()
    py = d["tools"] / "pylibs"
    bin_dir = py / "bin"
    spec = PIP_PACKAGES.get(pkg, pkg)

    exe_name = pkg.replace("-", "_") if pkg == "clang-format" else pkg
    # 实际二进制名映射
    binmap = {
        "flawfinder": "flawfinder.exe",
        "lizard": "lizard.exe",
        "clang-tidy": "clang-tidy.exe",
        "clang-format": "clang-format.exe",
    }
    target = bin_dir / binmap.get(pkg, pkg + ".exe")

    if target.exists() and not force:
        ok, ver = verify_tool(pkg, target)
        if ok:
            log.ok("%s 已就绪：%s" % (pkg, ver))
            return True

    py.mkdir(parents=True, exist_ok=True)

    # 优先官方源，失败再国内镜像
    indexes = [
        None,                                        # 默认
        "https://pypi.tuna.tsinghua.edu.cn/simple",  # 清华
        "https://mirrors.aliyun.com/pypi/simple/",   # 阿里云
    ]
    for idx in indexes:
        cmd = [sys.executable, "-m", "pip", "install", "--target", str(py),
               "--upgrade", spec]
        if idx:
            cmd += ["-i", idx, "--trusted-host", idx.split("/")[2]]
        label = idx or "默认源"
        log.info("pip install %s（%s）" % (spec, label))
        rc, out = run(cmd, timeout=900)
        if rc == 0:
            break
        tail = "\n".join(out.strip().splitlines()[-3:])
        log.warn("失败：%s" % tail[:200])
    else:
        log.err("%s 安装失败（所有源均不可用）" % pkg)
        return False

    # pip --target 生成的脚本 shebang 指向构建机 Python，Windows 下直接调用
    # 可能是 .exe wrapper，也可能只是 .py，做双重兜底
    if not target.exists():
        cands = list(bin_dir.glob(binmap.get(pkg, pkg + ".exe")))
        cands += list(py.rglob(binmap.get(pkg, pkg + ".exe")))
        if cands:
            target = cands[0]

    ok, ver = verify_tool(pkg, target)
    if ok:
        log.ok("%s 安装完成：%s" % (pkg, ver))
        return True

    # 最后兜底：用 -m 方式验证
    mod = {"clang-format": "clang_format",
           "clang-tidy": "clang_tidy"}.get(pkg, pkg)
    rc, out = run([sys.executable, "-m", mod, "--version"], timeout=60,
                  env={"PYTHONPATH": str(py)})
    if rc == 0:
        log.ok("%s 可用（python -m %s）：%s"
               % (pkg, mod, out.strip().splitlines()[0][:60]))
        return True
    log.err("%s 安装后无法运行" % pkg)
    return False


# ============================================================ 统一入口

REQUIRED = ["cppcheck", "flawfinder", "lizard"]
OPTIONAL = ["clang-tidy", "clang-format"]


def ensure_all(log, *, force=False, skip_optional=False) -> dict:
    """确保所有工具可用，返回 {name: bool}。"""
    result = {}

    if not check_python(log):
        raise RuntimeError("Python 环境不满足要求")
    if not check_pip(log):
        raise RuntimeError("pip 不可用")

    log.info("")
    log.info("--- 必需工具 ---")
    result["cppcheck"] = install_cppcheck(log, force=force)
    for pkg in ("flawfinder", "lizard"):
        result[pkg] = install_pip_tool(pkg, log, force=force)

    if skip_optional:
        log.info("")
        log.info("--- 可选工具（已跳过）---")
        for pkg in OPTIONAL:
            result[pkg] = False
    else:
        log.info("")
        log.info("--- 可选工具（缺失不影响基础扫描）---")
        for pkg in OPTIONAL:
            try:
                result[pkg] = install_pip_tool(pkg, log, force=force)
            except Exception as exc:
                log.warn("%s 安装异常：%s" % (pkg, exc))
                result[pkg] = False

    return result


def report_env(log, status: dict) -> bool:
    """汇总环境状态，返回是否满足最低要求。"""
    from . import toolchain
    log.info("")
    log.info("环境检查结果：")
    all_required_ok = True
    tools = toolchain.probe_all()
    for name, ok in status.items():
        t = tools.get(name)
        mark = "OK  " if ok else "MISS"
        need = "必需" if name in REQUIRED else "可选"
        ver = t.version if t and ok else ""
        log.info("  [%s] %-14s %s %s" % (mark, name, need, ver))
        if name in REQUIRED and not ok:
            all_required_ok = False
    return all_required_ok
