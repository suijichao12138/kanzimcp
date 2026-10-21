#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""panel_qt.py — nlp_worker 可视化配置面板（PySide6 版）

给不熟悉 YAML 的人用：填表单 → 校验 → 保存 → 启动。

★ 设计约束：本文件不认识任何配置项，全部由 schema.py 驱动。
★ 密钥流：config.yaml 写 ${KEY}，真实值在 .env —— 见 dotenv_io.py。

用法：
    python panel_qt.py [--config config.yaml]
"""
from __future__ import annotations

import argparse
import os
import sys
import traceback
from pathlib import Path

# 让脚本目录可导入（打包后同样有效）
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDialog,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QSizePolicy,
    QSplitter,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

import dotenv_io
import form as form_mod
import runner
import schema as schema_mod
import validate as validate_mod
import yaml_io
from widgets import (
    C_ACCENT,
    C_BG,
    C_BORDER,
    C_CARD,
    C_ERR,
    C_MUTED,
    C_OK,
    C_TEXT,
    C_WARN,
    GLOBAL_QSS,
    insert_card,
    make_card_scroll,
)


# ════════════════════════════════════════════════════════════
#  .env 编辑页签
# ════════════════════════════════════════════════════════════

class EnvTab(QWidget):
    """编辑 config.yaml 同级的 .env —— nlp_worker 启动时自动加载它。"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.path: Path | None = None
        self._rows: list[tuple[QLineEdit, QLineEdit, QWidget]] = []

        v = QVBoxLayout(self)
        v.setContentsMargins(4, 8, 4, 4)
        v.setSpacing(10)

        # ── 说明条 ──
        bar = QFrame()
        bar.setObjectName("Card")
        bv = QVBoxLayout(bar)
        bv.setContentsMargins(14, 12, 14, 12)
        bv.setSpacing(6)
        t = QLabel("密钥文件 .env")
        t.setObjectName("CardTitle")
        bv.addWidget(t)
        d = QLabel(
            "config.yaml 里写 <code>${OPENAI_API_KEY}</code>，真实值写在这里。"
            "本文件必须和 config.yaml <b>放在同一目录</b> —— nlp_worker 启动时自动读取，"
            "并且<b>不会覆盖</b>系统里已有的同名环境变量。"
        )
        d.setTextFormat(Qt.RichText)
        d.setObjectName("CardDesc")
        d.setWordWrap(True)
        bv.addWidget(d)

        self.path_label = QLabel("—")
        self.path_label.setStyleSheet(f"color:{C_MUTED};font-size:12px;")
        bv.addWidget(self.path_label)
        v.addWidget(bar)

        # ── 引用检查结果 ──
        self.ref_box = QFrame()
        self.ref_box.setObjectName("Card")
        rv = QVBoxLayout(self.ref_box)
        rv.setContentsMargins(14, 12, 14, 12)
        rv.setSpacing(6)
        rt = QLabel("config.yaml 里引用的变量")
        rt.setObjectName("CardTitle")
        rv.addWidget(rt)
        self.ref_list = QLabel("（未加载配置）")
        self.ref_list.setTextFormat(Qt.RichText)
        self.ref_list.setWordWrap(True)
        self.ref_list.setObjectName("CardDesc")
        rv.addWidget(self.ref_list)
        v.addWidget(self.ref_box)

        # ── 键值编辑区 ──
        self.scroll, self.slay = make_card_scroll()
        card = QFrame()
        card.setObjectName("Card")
        cv = QVBoxLayout(card)
        cv.setContentsMargins(14, 12, 14, 12)
        cv.setSpacing(8)
        ct = QLabel("键值")
        ct.setObjectName("CardTitle")
        cv.addWidget(ct)

        self.rows_lay = QVBoxLayout()
        self.rows_lay.setSpacing(8)
        cv.addLayout(self.rows_lay)

        btns = QHBoxLayout()
        add = QPushButton("+ 添加一项")
        add.clicked.connect(lambda: self._add_row("", "", refresh=False))
        btns.addWidget(add)
        self.from_ref = QPushButton("从 config.yaml 补全缺失项")
        self.from_ref.setToolTip("把 config.yaml 引用了、但这里还没有的变量补成空行")
        self.from_ref.clicked.connect(self._fill_missing)
        btns.addWidget(self.from_ref)
        btns.addStretch(1)
        cv.addLayout(btns)

        insert_card(self.slay, card)
        v.addWidget(self.scroll, 1)

        self.hint = QLabel("")
        self.hint.setStyleSheet(f"color:{C_MUTED};font-size:12px;")
        v.addWidget(self.hint)

    # ──────────── 行管理 ────────────

    def _add_row(self, k: str = "", val: str = "", refresh: bool = True):
        holder = QFrame()
        holder.setStyleSheet(
            f"QFrame{{background:#fafbfc;border:1px solid {C_BORDER};border-radius:6px;}}"
        )
        h = QHBoxLayout(holder)
        h.setContentsMargins(10, 8, 10, 8)
        h.setSpacing(8)

        ke = QLineEdit(k)
        ke.setPlaceholderText("KEY_NAME")
        ke.setMinimumWidth(210)
        ke.setMaximumWidth(280)
        h.addWidget(ke)

        ve = QLineEdit(val)
        ve.setPlaceholderText("值（可留空）")
        ve.setEchoMode(QLineEdit.Password)
        h.addWidget(ve, 1)

        eye = QPushButton("👁")
        eye.setFixedWidth(34)
        eye.setCursor(Qt.PointingHandCursor)

        def _toggle():
            if ve.echoMode() == QLineEdit.Password:
                ve.setEchoMode(QLineEdit.Normal)
                eye.setText("🙈")
            else:
                ve.setEchoMode(QLineEdit.Password)
                eye.setText("👁")

        eye.clicked.connect(_toggle)
        h.addWidget(eye)

        rm = QPushButton("✕")
        rm.setObjectName("Danger")
        rm.setFixedWidth(34)
        rm.setCursor(Qt.PointingHandCursor)
        rm.setToolTip("删除这一项（保存后生效）")

        row = (ke, ve, holder)

        def _remove():
            if row in self._rows:
                self._rows.remove(row)
            holder.setParent(None)

        rm.clicked.connect(_remove)
        h.addWidget(rm)

        self.rows_lay.addWidget(holder)
        self._rows.append(row)

    def _clear_rows(self):
        for _k, _v, holder in self._rows:
            holder.setParent(None)
        self._rows.clear()

    def _fill_missing(self):
        """把 config.yaml 引用了但 .env 没有的变量补成空行。"""
        data = self.parent_window.yaml_data if hasattr(self, "parent_window") else None
        if data is None:
            return
        pairs = self.collect()
        added = 0
        for name in dotenv_io.refs_in_config(data):
            if name not in pairs:
                self._add_row(name, "")
                added += 1
        self.hint.setText(
            f"补全了 {added} 项" if added else "没有缺失的变量 ✅"
        )

    # ──────────── 读写 ────────────

    def load(self, config_path):
        """加载 config.yaml 同级的 .env。"""
        self.path = dotenv_io.env_path_for(config_path)
        created = dotenv_io.ensure(self.path) if self.path else False
        pairs, _text = dotenv_io.load(self.path) if self.path else ({}, "")

        self._clear_rows()
        if pairs:
            for k, v in pairs.items():
                self._add_row(k, v)
        else:
            for k in ("OPENAI_API_KEY", "AZURE_OPENAI_API_KEY",
                      "ANTHROPIC_API_KEY", "LOCAL_MCP_TOKEN"):
                self._add_row(k, "")

        exists = "（已新建）" if created else ""
        self.path_label.setText(f"路径：{self.path}  {exists}")
        self.hint.setText("")

    def collect(self) -> dict:
        out: dict = {}
        for ke, ve, _h in self._rows:
            k = ke.text().strip()
            if k:
                out[k] = ve.text()
        return out

    def save(self) -> bool:
        if not self.path:
            return False
        try:
            dotenv_io.dump(self.collect(), self.path)
            return True
        except Exception as exc:                             # noqa: BLE001
            QMessageBox.critical(self, "保存 .env 失败", str(exc))
            return False

    def refresh_refs(self, data):
        """根据当前 config.yaml 更新「引用检查」。"""
        if not self.path:
            return
        pairs = dotenv_io.load(self.path)[0]
        status = dotenv_io.resolve_status(data, pairs)
        if not status:
            self.ref_list.setText("（config.yaml 里没有 ${...} 引用）")
            return
        lines = []
        for s in status:
            if s["from"] == "dotenv":
                lines.append(f"✅ <b>{s['name']}</b> —— 来自 .env")
            elif s["from"] == "system":
                lines.append(
                    f"✅ <b>{s['name']}</b> "
                    f"<span style='color:{C_MUTED}'>—— 来自系统环境变量</span>"
                )
            else:
                lines.append(
                    f"<span style='color:{C_ERR}'>❌ <b>{s['name']}</b> "
                    f"—— .env 和系统环境变量里都没有，启动会失败</span>"
                )
        self.ref_list.setText("<br>".join(lines))


# ════════════════════════════════════════════════════════════
#  日志页签
# ════════════════════════════════════════════════════════════

class LogTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        v = QVBoxLayout(self)
        v.setContentsMargins(4, 8, 4, 4)
        v.setSpacing(8)

        bar = QHBoxLayout()
        self.src = QComboBox()
        self.src.setMinimumWidth(240)
        self.src.currentIndexChanged.connect(self._reload)
        bar.addWidget(QLabel("日志文件："))
        bar.addWidget(self.src, 1)
        rl = QPushButton("刷新")
        rl.clicked.connect(self._reload)
        bar.addWidget(rl)
        auto = QPushButton("打开日志目录")
        auto.clicked.connect(self._open_dir)
        bar.addWidget(auto)
        v.addLayout(bar)

        self.view = QPlainTextEdit()
        self.view.setObjectName("LogView")
        self.view.setReadOnly(True)
        self.view.setLineWrapMode(QPlainTextEdit.NoWrap)
        v.addWidget(self.view, 1)

        self.candidates: list[str] = []

    def set_candidates(self, names: list[str]):
        self.src.clear()
        self.candidates = names
        for n in names:
            self.src.addItem(n)

    def _current_path(self):
        base = getattr(self, "base_dir", None)
        if not base or not self.candidates:
            return None
        return Path(base) / self.candidates[self.src.currentIndex()]

    def _reload(self):
        p = self._current_path()
        if not p:
            self.view.setPlainText("（未找到日志文件）")
            return
        txt = runner.tail_log(p, 500)
        self.view.setPlainText(txt or f"（日志为空或不存在：{p}）")
        sb = self.view.verticalScrollBar()
        sb.setValue(sb.maximum())

    def _open_dir(self):
        p = self._current_path()
        if p:
            runner.open_in_explorer(p.parent)


# ════════════════════════════════════════════════════════════
#  主窗口
# ════════════════════════════════════════════════════════════

class Panel(QMainWindow):
    def __init__(self, config_path: Path | None = None):
        super().__init__()
        self.setWindowTitle("nlp_worker 配置面板")
        self.resize(1080, 780)
        self.setMinimumSize(900, 620)

        self.config_path: Path = config_path or self._guess_config()
        self.yaml_data: dict = {}
        self.handles: dict = {}

        root = QWidget()
        self.setCentralWidget(root)
        v = QVBoxLayout(root)
        v.setContentsMargins(16, 14, 16, 14)
        v.setSpacing(12)

        v.addWidget(self._build_header())

        self.tabs = QTabWidget()
        self.tabs.addTab(self._build_form_tabs(), "配置")
        self.env_tab = EnvTab()
        self.env_tab.parent_window = self
        self.tabs.addTab(self.env_tab, "密钥 (.env)")
        self.log_tab = LogTab()
        self.log_tab.base_dir = self.config_path.parent
        self.tabs.addTab(self.log_tab, "日志")
        self.tabs.currentChanged.connect(self._on_tab_changed)
        v.addWidget(self.tabs, 1)

        v.addWidget(self._build_footer())

        # 状态栏
        self.status = QLabel("就绪")
        self.status.setStyleSheet(f"color:{C_MUTED};font-size:12px;")
        v.addWidget(self.status)

        self._load_config()
        self._refresh_status()

        self.timer = QTimer(self)
        self.timer.timeout.connect(self._refresh_status)
        self.timer.start(5000)

    # ──────────── 顶部 ────────────

    def _build_header(self) -> QWidget:
        card = QFrame()
        card.setObjectName("Card")
        h = QHBoxLayout(card)
        h.setContentsMargins(14, 12, 14, 12)
        h.setSpacing(10)

        lab = QLabel("配置文件")
        lab.setStyleSheet(f"color:{C_MUTED};font-size:12px;")
        h.addWidget(lab)

        self.cfg_edit = QLineEdit(str(self.config_path))
        self.cfg_edit.setMinimumHeight(32)
        h.addWidget(self.cfg_edit, 1)

        br = QPushButton("浏览…")
        br.clicked.connect(self._browse_config)
        h.addWidget(br)

        rl = QPushButton("重新加载")
        rl.setToolTip("丢弃未保存的修改，从磁盘重新读")
        rl.clicked.connect(self._load_config)
        h.addWidget(rl)

        h.addSpacing(8)

        self.badge = QLabel("● 已停止")
        self.badge.setObjectName("Badge")
        self.badge.setProperty("state", "off")
        h.addWidget(self.badge)

        self.pid_label = QLabel("")
        self.pid_label.setStyleSheet(f"color:{C_MUTED};font-size:12px;")
        h.addWidget(self.pid_label)

        rf = QPushButton("刷新状态")
        rf.clicked.connect(self._refresh_status)
        h.addWidget(rf)

        return card

    def _guess_config(self) -> Path:
        here = Path(__file__).resolve().parent
        for base in (here, here.parent):
            for name in ("config.yaml", "config.yml"):
                p = base / name
                if p.exists():
                    return p
        return here / "config.yaml"

    def _browse_config(self):
        start = str(self.config_path.parent)
        f, _ = QFileDialog.getOpenFileName(
            self, "选择 config.yaml", start, "YAML 配置 (*.yaml *.yml);;所有文件 (*)"
        )
        if f:
            self.cfg_edit.setText(f)
            self._load_config()

    # ──────────── 配置页签（三档分层）────────────

    def _build_form_tabs(self) -> QWidget:
        self.tier_host = QTabWidget()
        self.tier_host.setDocumentMode(True)

        self.tier_views: dict[str, tuple] = {}
        labels = {"basic": "基础", "advanced": "进阶", "expert": "高级"}

        for tier in ("basic", "advanced", "expert"):
            area, lay = make_card_scroll()
            self.tier_views[tier] = (area, lay)
            tip = {
                "basic": "不填就跑不起来，或必须按你的环境改。",
                "advanced": "默认值通常够用，有特殊需求再调。",
                "expert": "绝大多数情况不用碰。",
            }[tier]
            host = QWidget()
            hv = QVBoxLayout(host)
            hv.setContentsMargins(0, 6, 0, 0)
            hv.setSpacing(8)
            l = QLabel(tip)
            l.setStyleSheet(f"color:{C_MUTED};font-size:12px;")
            hv.addWidget(l)
            hv.addWidget(area, 1)
            self.tier_host.addTab(host, labels[tier])

        return self.tier_host

    def _rebuild_forms(self):
        """按 tier 把字段铺进三个页签。★ 完全由 schema 决定。"""
        for _tier, (area, lay) in self.tier_views.items():
            # 清空旧内容（保留末尾 stretch）
            while lay.count() > 1:
                it = lay.takeAt(0)
                w = it.widget()
                if w:
                    w.setParent(None)
            area.setWidget(area.widget())

        self.handles = {}
        getter = lambda k: yaml_io.get_path(self.yaml_data, k)

        for g in schema_mod.GROUPS:
            for tier in ("basic", "advanced", "expert"):
                specs = [
                    f for f in g.get("fields", [])
                    if f.get("tier", g.get("tier", "expert")) == tier
                ]
                if not specs:
                    continue
                group_specs = [dict(s) for s in specs]
                group_specs[0] = dict(group_specs[0])
                group_specs[0]["group"] = g["title"]
                group_specs[0]["group_help"] = g.get("desc", "")
                card, hs = form_mod.build_group(group_specs, self.yaml_data, getter)
                self.handles.update(hs)
                _area, lay = self.tier_views[tier]
                insert_card(lay, card)

    # ──────────── 底部工具栏 ────────────

    def _build_footer(self) -> QWidget:
        card = QFrame()
        card.setObjectName("Card")
        h = QHBoxLayout(card)
        h.setContentsMargins(14, 10, 14, 10)
        h.setSpacing(8)

        v1 = QPushButton("校验")
        v1.setToolTip("检查配置有没有错（本地规则）")
        v1.clicked.connect(lambda: self.do_validate(False))
        h.addWidget(v1)

        v2 = QPushButton("校验 + 连通性")
        v2.setObjectName("Primary")
        v2.setToolTip("额外试着连一下中继和 MCP 服务（推荐）")
        v2.clicked.connect(lambda: self.do_validate(True))
        h.addWidget(v2)

        h.addStretch(1)

        self.save_btn = QPushButton("保存配置")
        self.save_btn.clicked.connect(self.do_save)
        h.addWidget(self.save_btn)

        self.stop_btn = QPushButton("停止")
        self.stop_btn.setObjectName("Danger")
        self.stop_btn.clicked.connect(self.do_stop)
        h.addWidget(self.stop_btn)

        self.start_btn = QPushButton("启动")
        self.start_btn.setObjectName("Primary")
        self.start_btn.clicked.connect(self.do_start)
        h.addWidget(self.start_btn)

        return card

    # ──────────── 配置读写 ────────────

    def _load_config(self):
        self.config_path = Path(self.cfg_edit.text()).expanduser() if hasattr(self, "cfg_edit") \
            else self.config_path
        try:
            if self.config_path.exists():
                self.yaml_data = yaml_io.load(self.config_path)
            else:
                self.yaml_data = {}
        except Exception as exc:                             # noqa: BLE001
            QMessageBox.warning(self, "读取失败", f"{self.config_path}\n{exc}")
            self.yaml_data = {}

        # 没有就尝试从 config.example.yaml 起步
        if not self.yaml_data:
            ex = self.config_path.parent / "config.example.yaml"
            if ex.exists():
                try:
                    self.yaml_data = yaml_io.load(ex)
                    self.status.setText(f"已从 {ex.name} 载入默认值，请按需修改后保存")
                except Exception:                            # noqa: BLE001
                    pass

        self._rebuild_forms()
        self.env_tab.load(self.config_path)
        self.env_tab.refresh_refs(self.yaml_data)

        # 日志文件候选
        logs = []
        for name in ("logs/bridge.log", "bridge.log", "logs/worker.log",
                     "nlp_worker.log", "logs/nlp_worker.log"):
            if (self.config_path.parent / name).exists():
                logs.append(name)
        if not logs:
            logs = ["logs/bridge.log"]
        self.log_tab.base_dir = self.config_path.parent
        self.log_tab.set_candidates(logs)

        if self.config_path.exists() and self.yaml_data:
            self.status.setText(f"已加载 {self.config_path.name}")

    def collect(self, skip_secrets: bool = True) -> dict:
        """把表单值写回副本（密钥留空则不覆盖）。"""
        data = yaml_io.deep_copy(self.yaml_data)
        for key, h in self.handles.items():
            try:
                if h.kind == "secret" and not h.get().strip():
                    continue                                  # 留空 = 不改
                val = h.get()
                yaml_io.set_path(data, key, val)
            except Exception as exc:                          # noqa: BLE001
                self.status.setText(f"读取 {key} 失败：{exc}")
        return data

    # ──────────── 校验 ────────────

    def do_validate(self, net: bool):
        for h in self.handles.values():
            h.mark_error(None)
        data = self.collect()
        result = validate_mod.check(data, self.config_path.parent, do_net=net)

        shown = 0
        for key, msg in result.errors:
            h = self.handles.get(key)
            if h:
                h.mark_error(msg)
                shown += 1
        for key, msg in result.warns:
            h = self.handles.get(key)
            if h and not h.err_label.isVisible():
                # 警告只在没有错误时显示，颜色区分不大，统一用橙色文案
                h.err_label.setText("⚠️ " + msg)
                h.err_label.setStyleSheet(f"color:{C_WARN};font-size:11px;")
                h.err_label.setVisible(True)

        # 弹窗汇总
        box = QMessageBox(self)
        box.setWindowTitle("校验结果")
        if result.errors:
            box.setIcon(QMessageBox.Critical)
            box.setText(f"发现 {len(result.errors)} 个错误")
        elif result.warns:
            box.setIcon(QMessageBox.Warning)
            box.setText(f"通过，但有 {len(result.warns)} 条提醒")
        else:
            box.setIcon(QMessageBox.Information)
            box.setText("校验通过 ✅")

        lines = []
        for k, m in result.errors[:12]:
            lines.append(f"❌ [{k}] {m}")
        for k, m in result.warns[:12]:
            lines.append(f"⚠️ [{k}] {m}")
        if len(result.errors) > 12:
            lines.append(f"… 还有 {len(result.errors)-12} 个错误")
        box.setInformativeText("\n".join(lines) or result.summary())
        box.exec()

        self.status.setText(result.summary())
        if not result.errors:
            self.env_tab.refresh_refs(data)

    # ──────────── 保存 ────────────

    def do_save(self):
        data = self.collect()

        # 先校验（本地）
        result = validate_mod.check(data, self.config_path.parent, do_net=False)
        if result.errors:
            if QMessageBox.question(
                self, "配置有错",
                f"发现 {len(result.errors)} 个错误，仍然保存吗？\n\n"
                + "\n".join(f"· [{k}] {m}" for k, m in result.errors[:6]),
            ) != QMessageBox.Yes:
                return

        self.config_path.parent.mkdir(parents=True, exist_ok=True)

        # 备份
        if self.config_path.exists():
            try:
                bak = self.config_path.with_suffix(".yaml.bak")
                bak.write_bytes(self.config_path.read_bytes())
            except Exception:                                 # noqa: BLE001
                pass

        try:
            yaml_io.dump(data, self.config_path)
        except Exception as exc:                             # noqa: BLE001
            QMessageBox.critical(self, "保存失败", str(exc))
            return

        env_ok = self.env_tab.save()
        self.yaml_data = data
        self.status.setText(
            f"已保存 {self.config_path.name}" + ("  和 .env" if env_ok else "")
        )

        box = QMessageBox(self)
        box.setIcon(QMessageBox.Information)
        box.setText("保存成功")
        box.setInformativeText(
            f"配置：{self.config_path}\n"
            f"密钥：{self.env_tab.path}\n\n"
            "多数改动需要重启 nlp_worker 才生效。"
        )
        box.exec()

    # ──────────── 启停 ────────────

    def _worker_exe(self):
        return runner.find_worker_exe(self.config_path.parent)

    def do_start(self):
        exe = self._worker_exe()
        if not exe:
            QMessageBox.warning(
                self, "找不到 nlp_worker",
                "没在本目录或上级目录找到 nlp_worker 可执行文件。\n\n"
                "请把本面板和 nlp_worker.exe 放在同一个目录。",
            )
            return
        if runner.is_running():
            QMessageBox.information(self, "已在运行", "nlp_worker 已经启动了。")
            return

        if not self.config_path.exists():
            QMessageBox.warning(
                self, "没有配置文件",
                f"配置文件不存在：\n{self.config_path}\n\n请先点「保存配置」。",
            )
            return

        log = self.config_path.parent / "logs" / "panel_supervisor.log"
        try:
            pid = runner.start(exe, self.config_path, log)
        except Exception as exc:                             # noqa: BLE001
            QMessageBox.critical(self, "启动失败", str(exc))
            return

        self.status.setText(f"已启动，PID {pid}")
        QTimer.singleShot(700, self._refresh_status)

    def do_stop(self):
        if not runner.is_running():
            QMessageBox.information(self, "未运行", "nlp_worker 当前没有运行。")
            return
        runner.stop()
        self.status.setText("已发送停止信号")
        QTimer.singleShot(900, self._refresh_status)

    def _refresh_status(self):
        pids = runner.pid_list()
        running = bool(pids)
        self.badge.setText("● 运行中" if running else "● 已停止")
        self.badge.setProperty("state", "on" if running else "off")
        self.badge.style().unpolish(self.badge)
        self.badge.style().polish(self.badge)

        self.pid_label.setText(
            "PID " + ", ".join(str(p) for p in pids) if pids else ""
        )
        self.start_btn.setEnabled(not running)
        self.stop_btn.setEnabled(running)

    def _on_tab_changed(self, idx: int):
        w = self.tabs.widget(idx)
        if isinstance(w, LogTab):
            w._reload()
        elif isinstance(w, EnvTab):
            w.refresh_refs(self.collect())


# ════════════════════════════════════════════════════════════
#  入口
# ════════════════════════════════════════════════════════════

def main():
    ap = argparse.ArgumentParser(description="nlp_worker 可视化配置面板")
    ap.add_argument("--config", type=Path, default=None,
                    help="config.yaml 路径（默认自动查找）")
    args = ap.parse_args()

    app = QApplication(sys.argv)
    app.setApplicationName("nlp-worker-panel")
    app.setStyleSheet(GLOBAL_QSS)
    try:
        app.setFont(QFont("Microsoft YaHei UI", 9))
    except Exception:                                        # noqa: BLE001
        pass

    win = Panel(args.config)
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    try:
        main()
    except Exception:
        traceback.print_exc()
        input("\n出错了，按回车退出…")
