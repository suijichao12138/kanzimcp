#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""paths.py — 目录结构管理

所有路径基于「可执行文件/入口脚本所在目录」，不依赖 cwd，
保证从任何位置启动都指向同一套目录。
"""
import os
import sys
from pathlib import Path


def install_dir() -> Path:
    """程序安装目录。

    - PyInstaller 打包后: exe 所在目录
    - 源码运行: 本文件的上上级目录（deployer/）
    """
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


class Paths:
    """统一的目录结构。

        <install>/
        ├── kanzi-deployer.exe
        ├── deployer_config.json
        ├── bin/         三组件 exe
        ├── conf/        三组件配置
        ├── logs/        日志
        ├── src/         git 源码
        ├── tmp_results/ http 外置结果
        ├── data/        运行时数据
        └── _backup/     升级备份
    """

    def __init__(self, root: Path | None = None, overrides: dict | None = None):
        self.root = Path(root) if root else install_dir()
        ov = overrides or {}
        # 每个子目录都允许在配置里覆盖（相对路径 → 相对 root）
        self.bin = self._sub("bin", ov.get("bin"))
        self.conf = self._sub("conf", ov.get("conf"))
        self.logs = self._sub("logs", ov.get("logs"))
        self.src = self._sub("src", ov.get("src"))
        self.tmp = self._sub("tmp_results", ov.get("tmp"))
        self.data = self._sub("data", ov.get("data"))
        self.backup = self._sub("_backup", ov.get("backup"))

    def _sub(self, default: str, override) -> Path:
        if not override:
            return self.root / default
        p = Path(override)
        return p if p.is_absolute() else self.root / p

    def ensure_all(self):
        """创建所有运行期需要的目录（bin/src 由部署流程创建，这里一并建好）。"""
        for p in (self.bin, self.conf, self.logs, self.src,
                  self.tmp, self.data, self.backup):
            p.mkdir(parents=True, exist_ok=True)

    # ── 配置文件路径 ──
    @property
    def deployer_config(self) -> Path:
        return self.root / "deployer_config.json"

    def comp_config(self, name: str) -> Path:
        """http 组件配置文件名按惯例是 config.json，其余是 <name>_config.json"""
        if name == "http":
            return self.conf / "config.json"
        return self.conf / f"{name}_config.json"

    def users_json(self) -> Path:
        return self.conf / "users.json"

    def comp_log(self, name: str) -> Path:
        return self.logs / f"{name}.log"

    def comp_exe(self, name: str) -> Path:
        from . import config as _cfg  # 延迟导入避免循环
        return self.bin / _cfg.DEFAULT_COMPONENTS.get(name, {}).get("exe_name", f"{name}.exe")
