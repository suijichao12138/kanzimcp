# -*- coding: utf-8 -*-
"""便于 `python -m codescan` 调用。"""
import sys

from .cli import main

if __name__ == "__main__":
    sys.exit(main())
