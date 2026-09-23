#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""envcheck.py — 环境检测（Python / PyInstaller / git）

首次部署前必须确认这些工具可用；缺什么要明确报出来，供页面红字提示。
"""
import shutil
import subprocess
import sys

CREATE_NO_WINDOW = 0x08000000 if sys.platform == "win32" else 0


def _probe(cmd: list[str], timeout: int = 15) -> tuple[bool, str]:
    """跑一个命令看是否可用，返回 (是否成功, 版本/错误信息)。"""
    try:
        p = subprocess.run(cmd, capture_output=True, text=True,
                           timeout=timeout, encoding="utf-8", errors="replace",
                           creationflags=CREATE_NO_WINDOW)
        if p.returncode == 0:
            first = (p.stdout or p.stderr or "").strip().splitlines()
            return True, first[0] if first else "ok"
        return False, (p.stderr or p.stdout or "").strip()[:200]
    except FileNotFoundError:
        return False, "未找到命令"
    except subprocess.TimeoutExpired:
        return False, "执行超时"
    except Exception as e:                                  # noqa: BLE001
        return False, str(e)[:200]


def check_all(python_exe: str = "python", pyinstaller: str = "pyinstaller") -> dict:
    """检查全部依赖，返回逐项结果 + 汇总是否可以编译。

    {
      "ok": bool,               # 是否具备编译条件
      "items": [
        {"name": "Python", "ok": bool, "detail": "...", "required": bool},
        ...
      ]
    }
    """
    items = []

    # ── Python ──
    ok, detail = _probe([python_exe, "--version"])
    items.append({"name": "Python", "ok": ok, "detail": detail, "required": True})

    # ── PyInstaller ──
    ok2, detail2 = _probe([pyinstaller, "--version"])
    if not ok2:
        # 退一步：python -m PyInstaller
        ok2, detail2 = _probe([python_exe, "-m", "PyInstaller", "--version"])
        if ok2:
            detail2 = f"(via python -m PyInstaller) {detail2}"
    items.append({"name": "PyInstaller", "ok": ok2, "detail": detail2, "required": True})

    # ── git ──
    ok3, detail3 = _probe(["git", "--version"])
    items.append({"name": "git", "ok": ok3, "detail": detail3, "required": True})

    # 必需项全通过才算具备编译条件
    ready = all(i["ok"] for i in items if i["required"])
    return {"ok": ready, "items": items}


def which(cmd: str) -> str | None:
    return shutil.which(cmd)
