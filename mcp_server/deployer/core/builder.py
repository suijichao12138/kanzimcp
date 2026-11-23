#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""builder.py — 用 PyInstaller 编译三个组件

编译输出实时收集，供网页进度显示。
"""
import os
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


def _find_msbuild() -> str:
    """定位 msbuild.exe：优先环境变量 MSBUILD，否则 PATH 里找，再找 VS 常见安装位。

    - MSBUILD 环境变量（用户显式指定）
    - PATH 里的 msbuild（VS 开发者命令行环境下）
    - vswhere 定位 VS2019/2022 的 MSBuild.exe
    """
    import shutil as _sh
    env_msbuild = os.environ.get("MSBUILD", "")
    if env_msbuild and Path(env_msbuild).exists():
        return env_msbuild
    in_path = _sh.which("msbuild")
    if in_path:
        return in_path
    # vswhere 定位（VS2017+ 自带），覆盖 2019/2022
    vswhere = os.environ.get(
        "ProgramFiles(x86)", r"C:\Program Files (x86)") + r"\Microsoft Visual Studio\Installer\vswhere.exe"
    if Path(vswhere).exists():
        ok, out = gitops.run([
            vswhere, "-latest", "-requires", "Microsoft.Component.MSBuild",
            "-find", r"MSBuild\**\Bin\MSBuild.exe"], timeout=30)
        if ok and out.strip():
            return out.strip().splitlines()[0].strip()
    return ""


def build_artifact(name: str, spec: dict, src_root: Path, on_progress=None):
    """编译单个按需产物（不进组件启停）。返回 (ok, detail, 产物绝对路径或None)。

    spec 字段：
      build_type   script | msbuild
      cwd          相对仓库根的编译目录
      script       (script 类型) 要跑的 .cmd/.bat（Windows）
      project      (msbuild 类型) .sln/.csproj
      configuration/ platform
      output       产物相对 cwd 的路径
    """
    def report(msg: str):
        if on_progress:
            try:
                on_progress(name, msg)
            except Exception:                                # noqa: BLE001
                pass

    build_type = spec.get("build_type", "script")
    workdir = (src_root / spec["cwd"]).resolve()
    if not workdir.exists():
        return False, f"编译目录不存在: {workdir}", None
    output_rel = spec.get("output", "")
    output = (workdir / output_rel).resolve() if output_rel else None

    if build_type == "msbuild":
        return _build_msbuild(name, spec, workdir, output, report)
    return _build_script(name, spec, workdir, output, report)


def _build_msbuild(name, spec, workdir: Path, output, report) -> tuple[bool, str, "Path | None"]:
    msbuild = _find_msbuild()
    if not msbuild:
        return False, "未找到 msbuild.exe（请安装 VS2019/2022 或设 MSBUILD 环境变量）", None
    project = spec.get("project", "")
    if not project or not (workdir / project).exists():
        return False, f"MSBuild 工程不存在: {workdir / project}", None
    cfg = spec.get("configuration", "Release")
    platform = spec.get("platform", "Any CPU")
    cmd = [msbuild, project, f"/p:Configuration={cfg}",
           f"/p:Platform={platform}", "/m", "/nologo", "/v:minimal"]
    report(f"开始编译 {name} ({cfg}) …")
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
            if len(tail) > 30:
                tail.pop(0)
            if "error " in line.lower() or "warning " in line.lower():
                report(f"{name}: {line[:120]}")
        proc.wait(timeout=int(spec.get("timeout_s", 1800)))
    except subprocess.TimeoutExpired:
        proc.kill()
        return False, f"{name} 编译超时", None
    except Exception as e:                                   # noqa: BLE001
        return False, f"{name} 编译异常: {e}", None
    if proc.returncode != 0:
        return False, f"{name} MSBuild 编译失败: " + " | ".join(tail[-5:]), None
    if not output or not output.exists():
        return False, f"{name} 编译完成但找不到产物: {output}", None
    return True, f"{name} 编译成功", output


def _build_script(name, spec, workdir: Path, output, report) -> tuple[bool, str, "Path | None"]:
    script = spec.get("script", "")
    if not script:
        return False, f"{name} 未配置编译脚本", None
    script_path = workdir / script
    if not script_path.exists():
        return False, f"编译脚本不存在: {script_path}", None
    report(f"开始编译 {name}（{script}）…")
    try:
        proc = subprocess.Popen(
            ["cmd", "/c", script], cwd=str(workdir),
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, encoding="utf-8", errors="replace",
            env=gitops.git_env(),
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
            if any(k in line for k in ("[1/7]", "[2/7]", "[3/7]", "[4/7]", "[5/7]", "[6/7]", "[7/7]", "Zip package", "Portable package")):
                report(f"{name}: {line}")
        proc.wait(timeout=int(spec.get("timeout_s", 3600)))
    except subprocess.TimeoutExpired:
        proc.kill()
        return False, f"{name} 编译超时", None
    except Exception as e:                                   # noqa: BLE001
        return False, f"{name} 编译异常: {e}", None
    if proc.returncode != 0:
        return False, f"{name} 编译脚本失败: " + " | ".join(tail[-5:]), None
    if not output or not output.exists():
        return False, f"{name} 编译完成但找不到产物: {output}", None
    return True, f"{name} 编译成功", output
