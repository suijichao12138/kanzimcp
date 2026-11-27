# -*- coding: utf-8 -*-
"""归档打包：生成可分发的 zip。

用法：
    python -m codescan.pack               生成 zip 到 dist/
    python -m codescan.pack --with-tools  连第三方工具一起打包（离线可用）
    python -m codescan.pack --no-tools    只打源码（体积小）
"""
from __future__ import annotations

import argparse
import sys
import time
import zipfile
from pathlib import Path

from . import __version__
from .common import dirs, human_size

# 始终排除的目录/文件
EXCLUDE_DIRS = {"build", "output", "__pycache__", ".git", ".venv", "dist"}
EXCLUDE_EXT = {".pyc", ".pyo", ".part"}
EXCLUDE_FILES = {"manifest.json", ".stub-version"}


def _iter_files(root: Path, with_tools: bool):
    for p in sorted(root.rglob("*")):
        if not p.is_file():
            continue
        rel = p.relative_to(root)
        parts = set(rel.parts)
        if parts & EXCLUDE_DIRS:
            continue
        if p.suffix.lower() in EXCLUDE_EXT:
            continue
        if p.name in EXCLUDE_FILES:
            continue
        if not with_tools and rel.parts[0] == "tools":
            continue
        yield p, rel


def pack(with_tools=True, out_dir=None) -> Path:
    d = dirs()
    root = d["root"]
    out = Path(out_dir) if out_dir else (root / "dist")
    out.mkdir(parents=True, exist_ok=True)

    stamp = time.strftime("%Y%m%d")
    tag = "full" if with_tools else "src"
    name = "code-scan-tool-%s-%s-v%s.zip" % (tag, stamp, __version__)
    target = out / name

    count = 0
    total = 0
    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        for p, rel in _iter_files(root, with_tools):
            arc = Path("code-scan-tool") / rel
            z.write(p, arc.as_posix())
            count += 1
            total += p.stat().st_size

    print("已生成归档：%s" % target)
    print("  文件数 %d，原始大小 %s，压缩后 %s"
          % (count, human_size(total), human_size(target.stat().st_size)))
    if with_tools:
        print("  已包含第三方工具，目标机可直接离线使用")
    else:
        print("  未包含第三方工具，目标机需首次运行 setup_env.cmd 下载")
    return target


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        prog="codescan.pack", description="生成可归档的 zip 包")
    ap.add_argument("--with-tools", action="store_true", default=True,
                    help="包含第三方工具（默认）")
    ap.add_argument("--no-tools", dest="with_tools", action="store_false",
                    help="不含第三方工具，体积更小")
    ap.add_argument("--out", help="输出目录（默认 dist/）")
    args = ap.parse_args(argv)
    pack(with_tools=args.with_tools, out_dir=args.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
