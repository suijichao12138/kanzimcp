# -*- mode: python ; coding: utf-8 -*-
"""cppCheck.spec — PyInstaller 单文件打包配置

产物：dist/cppCheck.exe（--onefile）

打包要点：
  1. config/ data/ tools/ 全部塞进 exe（--add-data），运行时解压到 sys._MEIPASS
  2. codescan 是包，需要 collect_submodules 保证全部子模块被收集
  3. tools/ 里的第三方工具（cppcheck、flawfinder 等）是数据文件，不是 Python 模块
  4. 排除无关的大库，避免 exe 无谓变大
"""
import os
import sys
from pathlib import Path

from PyInstaller.utils.hooks import collect_submodules

BASE = Path(SPECPATH).resolve()

# ── 数据文件：把整个工具目录打进去 ──
datas = []

for sub in ("config", "data"):
    src = BASE / sub
    if src.exists():
        datas.append((str(src), sub))

# tools 目录包含 cppcheck（29MB）和 pylibs（119MB）
tools = BASE / "tools"
if tools.exists():
    datas.append((str(tools), "tools"))

hiddenimports = collect_submodules("codescan") + [
    # flawfinder 依赖 xml.sax.saxutils（标准库，需显式声明）
    "xml", "xml.sax", "xml.sax.saxutils",
    # lizard 的依赖
    "lizard", "lizard_core", "lizard_core.cli", "lizard_ext", "lizard_languages",
    "pygments", "pygments.lexers", "pygments.styles",
    "json", "zipfile", "hashlib", "subprocess", "csv", "io",
]

a = Analysis(
    [str(BASE / "run.py")],
    pathex=[str(BASE), str(BASE / "tools" / "pylibs")],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    # 排除用不到的重型库，减小体积
    excludes=[
        "tkinter", "matplotlib", "numpy", "pandas", "PIL",
        "scipy", "IPython", "pytest", "setuptools", "pip",
        "pydoc", "doctest",
    ],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="cppCheck",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,                 # 不对 tools 里的 exe 做 upx，避免损坏
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,              # 需要控制台输出，deployer 要读进度
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)
