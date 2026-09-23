#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""logs.py — 日志读取 / 清空 / 轮转信息"""
from pathlib import Path

COMPONENTS = ["relay", "http", "feishu", "deployer"]


def read_tail(name: str, paths, lines: int = 200) -> dict:
    """读某个组件日志的尾部 N 行（带容错：文件不存在/编码异常都不炸）。"""
    path = paths.comp_log(name) if name != "deployer" else paths.logs / "deployer.log"
    if not path.exists():
        return {"name": name, "path": str(path), "exists": False,
                "lines": [], "size": 0, "rotated": []}
    try:
        size = path.stat().st_size
        # 从尾部读，避免大文件全量载入
        chunk = _tail_bytes(path, max(lines * 400, 8192))
        text = chunk.decode("utf-8", errors="replace")
        rows = text.splitlines()[-lines:]
    except Exception as e:                                   # noqa: BLE001
        return {"name": name, "path": str(path), "exists": True, "error": str(e),
                "lines": [], "size": 0, "rotated": []}
    return {
        "name": name, "path": str(path), "exists": True, "size": size,
        "lines": rows, "rotated": rotated_files(name, paths),
    }


def _tail_bytes(path: Path, nbytes: int) -> bytes:
    """读文件尾部 nbytes 字节。"""
    with path.open("rb") as f:
        f.seek(0, 2)
        size = f.tell()
        f.seek(max(0, size - nbytes))
        return f.read()


def rotated_files(name: str, paths) -> list:
    """列出该组件的轮转备份（xxx.log.1 / .2 ...），供页面提示。"""
    base = paths.comp_log(name) if name != "deployer" else paths.logs / "deployer.log"
    out = []
    for i in range(1, 6):
        p = base.with_name(base.name + f".{i}")
        if p.exists():
            out.append({"name": p.name, "size": p.stat().st_size})
    return out


def clear(name: str, paths) -> tuple[bool, str]:
    """清空日志文件（不删文件本身，避免组件句柄失效）。

    注意：组件持有文件句柄时清空是安全的（truncate 到 0），
    不会影响组件继续写入。
    """
    path = paths.comp_log(name) if name != "deployer" else paths.logs / "deployer.log"
    if not path.exists():
        return True, "日志文件不存在"
    try:
        with path.open("r+b") as f:
            f.truncate(0)
        return True, f"已清空 {path.name}"
    except Exception as e:                                   # noqa: BLE001
        return False, f"清空失败: {e}"


def stats(paths) -> list:
    """各组件日志的统计信息（大小、是否存在）。"""
    out = []
    for name in COMPONENTS:
        path = paths.comp_log(name) if name != "deployer" else paths.logs / "deployer.log"
        if path.exists():
            st = path.stat()
            out.append({"name": name, "exists": True,
                        "size": st.st_size, "mtime": int(st.st_mtime),
                        "rotated": len(rotated_files(name, paths))})
        else:
            out.append({"name": name, "exists": False, "size": 0,
                        "mtime": 0, "rotated": 0})
    return out
