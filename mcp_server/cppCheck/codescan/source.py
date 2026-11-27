# -*- coding: utf-8 -*-
"""源码获取：本地目录直接使用，或从远程主机拉取。

重要：部分企业环境对源码目录做了透明加密（如 E-SafeNet DLP），
此时走 SFTP 读到的会是密文，必须通过 shell 的 cat 读取才会自动解密。
本模块默认走 cat 通道，并对结果做密文特征检测。
"""
from __future__ import annotations

import os
import posixpath
import re
import shutil
from pathlib import Path

from .common import dirs, run

SRC_EXT = (".c", ".cpp", ".cc", ".cxx", ".h", ".hpp", ".hxx")
HDR_EXT = (".h", ".hpp", ".hxx")

# 密文特征（E-SafeNet / 常见 DLP 的文件头）
CIPHER_MARKS = (b"E-SafeNet", b"SafeNet", b"LOCK\x00")


def _q(s: str) -> str:
    """把任意字符串安全地包成单引号 shell 参数。

    路径里出现空格、中文、单引号时，裸拼接会让 cd/find/cat 直接断掉，
    甚至被当作额外命令执行。这里按 POSIX 规则转义：' -> '\'' 。
    """
    return "'" + str(s).replace("'", "'\\''") + "'"


def _is_cipher(data: bytes) -> bool:
    head = data[:128]
    return any(m in head for m in CIPHER_MARKS)


def collect_local(root: Path, include_ext=SRC_EXT):
    """收集本地源码文件列表。"""
    out = []
    for p in Path(root).rglob("*"):
        if p.is_file() and p.suffix.lower() in include_ext:
            out.append(p)
    return sorted(out)


# ============================================================ 远程拉取

def fetch_remote(cfg: dict, log, dest_root: Path) -> int:
    """从远程主机拉取源码到 dest_root，返回文件数。

    走 shell cat 通道，规避 DLP 透明加密导致的密文问题。
    """
    try:
        import paramiko
    except ImportError:
        raise RuntimeError(
            "需要 paramiko 才能远程拉取源码。请执行：\n"
            "  pip install paramiko\n"
            "或改用本地模式（配置 local.source_dir）")

    r = cfg["remote"]
    host, port = r["host"], int(r.get("port") or 22)
    user, pwd = r["user"], r.get("password") or ""
    base = r["source_dir"].rstrip("/")
    key = r.get("private_key") or ""

    log.info("连接 %s@%s:%d" % (user, host, port))
    cli = paramiko.SSHClient()
    cli.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    kw = dict(hostname=host, port=port, username=user, timeout=25,
              banner_timeout=30, auth_timeout=30)
    if key:
        kw["key_filename"] = key
    else:
        kw["password"] = pwd
    cli.connect(**kw)

    # 1) 列出源码文件
    cmd = ("cd %s && find . -type f \\( -name '*.c' -o -name '*.cpp' "
           "-o -name '*.cc' -o -name '*.cxx' -o -name '*.h' -o -name '*.hpp' "
           "-o -name '*.hxx' \\) -not -path './.git/*' | sort" % _q(base))
    _, so, se = cli.exec_command(cmd, timeout=180)
    listing = so.read().decode("utf-8", "replace")
    err = se.read().decode("utf-8", "replace")
    if err.strip():
        log.warn("远端 find 提示：%s" % err.strip()[:200])
    files = [x.strip() for x in listing.splitlines() if x.strip()]
    if not files:
        cli.close()
        raise RuntimeError("远端目录下未找到源码文件：%s" % base)

    log.info("远端源码 %d 个文件" % len(files))

    # 2) 逐个 cat 下载
    ok = cipher = fail = 0
    dest_root.mkdir(parents=True, exist_ok=True)
    for i, rel in enumerate(files, 1):
        rel = rel.lstrip("./")
        remote = posixpath.join(base, rel)
        _, so, _ = cli.exec_command("cat " + _q(remote), timeout=120)
        data = so.read()
        if not data:
            fail += 1
            log.warn("空文件：%s" % rel)
            continue
        if _is_cipher(data):
            cipher += 1
            log.warn("检测到密文（DLP 加密），跳过：%s" % rel)
            continue
        lp = dest_root / rel.replace("/", os.sep)
        lp.parent.mkdir(parents=True, exist_ok=True)
        lp.write_bytes(data)
        ok += 1
        if i % 10 == 0 or i == len(files):
            log.info("已拉取 %d/%d" % (i, len(files)))

    cli.close()
    log.ok("源码拉取完成：成功 %d，密文 %d，失败 %d" % (ok, cipher, fail))
    if ok == 0:
        raise RuntimeError("没有成功拉取任何文件，请检查路径与权限")
    return ok


def fetch_remote_headers(cfg: dict, log, dest_root: Path,
                         local_src: Path, extra_bases=None) -> int:
    """拉取源码引用的工程头文件（供 clang-tidy 解析）。

    在远端按文件名搜索，命中即下载。只抓工程内头，不抓标准库。
    """
    try:
        import paramiko
    except ImportError:
        log.warn("无 paramiko，跳过头文件拉取")
        return 0

    r = cfg["remote"]
    cli = paramiko.SSHClient()
    cli.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    kw = dict(hostname=r["host"], port=int(r.get("port") or 22),
              username=r["user"], timeout=25)
    if r.get("private_key"):
        kw["key_filename"] = r["private_key"]
    else:
        kw["password"] = r.get("password") or ""
    cli.connect(**kw)

    # 收集本地源码引用过的头
    incs = set()
    pat = re.compile(r'#\s*include\s*[<"]([^>"]+)[>"]')
    for p in local_src.rglob("*"):
        if p.is_file() and p.suffix.lower() in SRC_EXT:
            try:
                txt = p.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            for m in pat.finditer(txt):
                incs.add(m.group(1))

    STD = {
        "cstdio", "cstring", "cstdint", "cstdlib", "cmath", "ctime", "iostream",
        "fstream", "sstream", "string", "vector", "map", "set", "list", "deque",
        "queue", "stack", "mutex", "thread", "atomic", "chrono", "functional",
        "algorithm", "iterator", "memory", "unordered_map", "unordered_set",
        "limits", "utility", "array", "tuple", "numeric", "regex", "optional",
        "variant", "any", "type_traits", "stdexcept", "new", "exception",
        "stdint.h", "stdio.h", "string.h", "stdlib.h", "math.h", "time.h",
        "unistd.h", "pthread.h", "sys/types.h", "memory.h", "errno.h",
    }
    targets = sorted(x for x in incs
                     if x not in STD
                     and not x.startswith(("kanzi/", "screen/", "sys/",
                                           "linux/", "asm/")))

    bases = extra_bases or []
    # 默认在两个常见位置找
    src_top = posixpath.dirname(r["source_dir"].rstrip("/"))
    bases = bases + [
        posixpath.join(src_top, "..", "release-qnx/usr/include"),
        posixpath.join(src_top, ".."),
    ]
    bases = [posixpath.normpath(b) for b in bases]

    log.info("需拉取工程头 %d 个" % len(targets))
    ok = 0
    for inc in targets:
        found = None
        for b in bases:
            cmd = ("find %s -name %s -not -path '*/.git/*' "
                   "2>/dev/null | head -1"
                   % (_q(b), _q(posixpath.basename(inc))))
            _, so, _ = cli.exec_command(cmd, timeout=90)
            p = so.read().decode().strip()
            if p:
                found = p
                break
        if not found:
            continue
        _, so, _ = cli.exec_command("cat " + _q(found), timeout=90)
        data = so.read()
        if not data or _is_cipher(data):
            continue
        lp = dest_root / inc.replace("/", os.sep)
        lp.parent.mkdir(parents=True, exist_ok=True)
        lp.write_bytes(data)
        ok += 1

    cli.close()
    log.ok("工程头拉取完成：%d 个" % ok)
    return ok


# ============================================================ 统一入口

def prepare_sources(cfg: dict, log) -> Path:
    """准备源码目录，返回可供扫描的本地路径。"""
    d = dirs()
    out_src = d["build"] / "src"

    if cfg["remote"].get("enabled"):
        if out_src.exists():
            shutil.rmtree(out_src, ignore_errors=True)
        out_src.mkdir(parents=True, exist_ok=True)
        fetch_remote(cfg, log, out_src)
    else:
        local = cfg["local"].get("source_dir") or ""
        if not local:
            raise RuntimeError(
                "未配置源码路径。请在 config/scan_config.json 中设置\n"
                "  remote.enabled=true 并提供 remote.* 参数，或\n"
                "  local.source_dir 指向本地源码目录")
        src = Path(local)
        if not src.is_absolute():
            src = d["root"] / src
        if not src.exists():
            raise RuntimeError("本地源码目录不存在：%s" % src)
        if out_src.exists():
            shutil.rmtree(out_src, ignore_errors=True)
        shutil.copytree(src, out_src)
        n = len(collect_local(out_src))
        log.info("已复制本地源码：%s（%d 个文件）" % (src, n))

    files = collect_local(out_src)
    if not files:
        raise RuntimeError("源码目录中没有 C/C++ 文件：%s" % out_src)
    total_lines = 0
    for p in files:
        try:
            total_lines += len(p.read_text(encoding="utf-8",
                                           errors="replace").splitlines())
        except OSError:
            pass
    log.ok("源码就绪：%d 个文件，约 %d 行" % (len(files), total_lines))
    return out_src
