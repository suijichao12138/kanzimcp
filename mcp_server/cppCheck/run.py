#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""cppCheck 单文件入口。

PyInstaller 打包时必须用绝对导入（相对导入在单文件模式下没有父包，
会报 "attempted relative import with no known parent package"）。
"""
import sys
import os

# 源码运行时把上级目录加入 sys.path，使 codescan 作为包被导入；
# PyInstaller 打包后模块已在包里，这段无副作用。
_here = os.path.dirname(os.path.abspath(__file__))
if _here not in sys.path:
    sys.path.insert(0, _here)

from codescan.cli import main

if __name__ == "__main__":
    sys.exit(main())
