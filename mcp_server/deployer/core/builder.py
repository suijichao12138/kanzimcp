#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""builder.py — 用 PyInstaller 编译三个组件

编译输出实时收集，供网页进度显示。
"""
import subprocess
from pathlib import Path

from . import gitops


def build_component(name: str, comp: dict, src_root: Path, paths,
                    python_exe: str = "python", pyinstaller: str = "pyinstaller",
                    timeout: int = 1800, on_progress=None) -> tuple[bool, str, Path | None]:
    """编译单个组件。

    - comp["cwd"]: 相对仓库根的编译工作目录（PyInstaller 在那里跑）
    - comp["src"]: 相对仓库根的源文件路径
    - 产物: <仓库根>/<comp.cwd>/dist/<exe_name>

    返回 (成功, 说明, 产物路径或None)
    """
    def report(msg: str):
        if on_progress:
            try:
                on_progress(name, msg)
            except Exception:                                # noqa: BLE001
                pass

    workdir = src_root / comp["cwd"]
    src_file = Path(comp["src"]).name
    if not workdir.exists():
        return False, f"编译目录不存在: {workdir}", None
    if not (workdir / src_file).exists():
        return False, f"源文件不存在: {workdir / src_file}", None

    args = (comp.get("pyinstaller_args") or f"--onefile --noconsole --name {name}").split()
    # 优先 python -m PyInstaller（避免 PATH 里 pyinstaller 与 python 不匹配）
    cmd = [python_exe, "-m", "PyInstaller"] + args + [src_file]

    report(f"开始编译 {name} …")
    try:
        proc = subprocess.Popen(
            cmd, cwd=str(workdir), stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT, text=True, encoding="utf-8",
            errors="replace", env=gitops.git_env(),
            creationflags=gitops.no_window_flags(),
        )
        tail: list[str] = []
        for line in proc.stdout:                             # type: ignore[union-attr]
            line = line.rstrip()
            if not line:
                continue
            tail.append(line)
            if len(tail) > 40:
                tail.pop(0)
            if "Building EXE" in line or "Building COLLECT" in line:
                report(f"{name}: {line}")
        proc.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        proc.kill()
        return False, f"{name} 编译超时({timeout}s)", None
    except Exception as e:                                   # noqa: BLE001
        return False, f"{name} 编译异常: {e}", None

    if proc.returncode != 0:
        return False, f"{name} 编译失败: " + " | ".join(tail[-5:]), None

    produced = workdir / "dist" / comp["exe_name"]
    if not produced.exists():
        return False, f"{name} 编译完成但找不到产物: {produced}", None
    size_mb = produced.stat().st_size / 1024 / 1024
    return True, f"{name} 编译成功 ({size_mb:.1f}MB)", produced


def build_all(components: dict, order: list, src_root: Path, paths,
              python_exe: str = "python", pyinstaller: str = "pyinstaller",
              timeout: int = 1800, on_progress=None) -> dict:
    """按顺序编译全部组件。返回 {name: {"ok":bool, "detail":str, "path":Path|None}}"""
    results = {}
    for name in order:
        comp = components.get(name)
        if not comp:
            results[name] = {"ok": False, "detail": f"配置里没有组件 {name}", "path": None}
            continue
        ok, detail, path = build_component(
            name, comp, src_root, paths,
            python_exe=python_exe, pyinstaller=pyinstaller,
            timeout=timeout, on_progress=on_progress,
        )
        results[name] = {"ok": ok, "detail": detail, "path": path}
    return results
