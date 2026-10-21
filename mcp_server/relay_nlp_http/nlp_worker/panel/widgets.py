#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""widgets.py — PySide6 动态表单控件

★ 核心约束：面板不认识任何配置项。
   所有控件都由 schema.py 的描述（field spec）现场生成。
   加一个配置项 → 只改 schema.py，本文件不用动。

支持的 field type → 控件：
    str/path → QLineEdit (+ 目录选择按钮)
    int/float → QSpinBox / QDoubleSpinBox
    bool      → QCheckBox
    enum      → QComboBox
    secret    → QLineEdit(EchoMode.Password) + 显示/隐藏
    list      → QPlainTextEdit（一行一个）
    dict      → QLineEdit（k: v; k: v）
    dict_list → 可增删的条目卡片
"""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

# ════════════════ 配色（现代扁平风）════════════════
C_BG = "#f5f6f8"
C_CARD = "#ffffff"
C_BORDER = "#e3e5e9"
C_TEXT = "#1f2328"
C_MUTED = "#6b7280"
C_ACCENT = "#2563eb"
C_ACCENT_HOVER = "#1d4ed8"
C_ERR = "#dc2626"
C_WARN = "#b45309"
C_OK = "#15803d"
C_REQUIRED = "#dc2626"

FONT = "Microsoft YaHei UI"

GLOBAL_QSS = f"""
QWidget {{
    font-family: "{FONT}", "Segoe UI", sans-serif;
    font-size: 13px;
    color: {C_TEXT};
}}
QMainWindow, QDialog {{ background: {C_BG}; }}

/* ── 卡片 ── */
QFrame#Card {{
    background: {C_CARD};
    border: 1px solid {C_BORDER};
    border-radius: 8px;
}}
QLabel#CardTitle {{
    font-size: 13px;
    font-weight: 600;
    color: {C_TEXT};
    padding: 0px;
}}
QLabel#CardDesc {{
    font-size: 12px;
    color: {C_MUTED};
}}

/* ── 页签 ── */
QTabWidget::pane {{
    border: none;
    background: transparent;
}}
QTabBar::tab {{
    background: transparent;
    border: none;
    border-bottom: 2px solid transparent;
    padding: 8px 18px;
    margin-right: 4px;
    color: {C_MUTED};
    font-size: 13px;
}}
QTabBar::tab:hover {{ color: {C_TEXT}; }}
QTabBar::tab:selected {{
    color: {C_ACCENT};
    border-bottom: 2px solid {C_ACCENT};
    font-weight: 600;
}}

/* ── 输入控件 ── */
QLineEdit, QPlainTextEdit, QSpinBox, QDoubleSpinBox, QComboBox {{
    background: {C_CARD};
    border: 1px solid {C_BORDER};
    border-radius: 6px;
    padding: 6px 9px;
    selection-background-color: {C_ACCENT};
    selection-color: #ffffff;
}}
QLineEdit:focus, QPlainTextEdit:focus, QSpinBox:focus,
QDoubleSpinBox:focus, QComboBox:focus {{
    border: 1px solid {C_ACCENT};
}}
QLineEdit:disabled, QSpinBox:disabled, QComboBox:disabled {{
    background: #f0f1f3;
    color: {C_MUTED};
}}
QLineEdit[invalid="true"] {{
    border: 1px solid {C_ERR};
    background: #fef2f2;
}}
QPlainTextEdit {{
    font-family: Consolas, "Courier New", monospace;
    font-size: 12px;
}}
QComboBox::drop-down {{ border: none; width: 22px; }}
QComboBox QAbstractItemView {{
    background: {C_CARD};
    border: 1px solid {C_BORDER};
    border-radius: 6px;
    selection-background-color: {C_ACCENT};
    selection-color: #ffffff;
    outline: none;
}}

/* ── 按钮 ── */
QPushButton {{
    background: {C_CARD};
    border: 1px solid {C_BORDER};
    border-radius: 6px;
    padding: 7px 16px;
    color: {C_TEXT};
}}
QPushButton:hover {{ background: #f0f1f4; border-color: #d3d6db; }}
QPushButton:pressed {{ background: #e6e8ec; }}
QPushButton:disabled {{ color: #b0b4ba; background: #f5f6f8; }}

QPushButton#Primary {{
    background: {C_ACCENT};
    border: 1px solid {C_ACCENT};
    color: #ffffff;
    font-weight: 600;
}}
QPushButton#Primary:hover {{ background: {C_ACCENT_HOVER}; border-color: {C_ACCENT_HOVER}; }}
QPushButton#Primary:disabled {{ background: #a9c0f0; border-color: #a9c0f0; color: #ffffff; }}

QPushButton#Danger {{ color: {C_ERR}; }}
QPushButton#Danger:hover {{ background: #fef2f2; border-color: #fca5a5; }}

QToolButton#Help {{
    background: transparent;
    border: 1px solid {C_BORDER};
    border-radius: 9px;
    color: {C_MUTED};
    font-size: 11px;
    font-weight: 600;
    min-width: 18px; max-width: 18px;
    min-height: 18px; max-height: 18px;
}}
QToolButton#Help:hover {{ background: {C_ACCENT}; color: #ffffff; border-color: {C_ACCENT}; }}

QToolButton#Eye {{
    background: transparent; border: none;
    color: {C_MUTED}; padding: 0 4px;
}}
QToolButton#Eye:hover {{ color: {C_ACCENT}; }}

/* ── 滚动区 ── */
QScrollArea {{ border: none; background: transparent; }}
QScrollBar:vertical {{
    background: transparent; width: 10px; margin: 0;
}}
QScrollBar::handle:vertical {{
    background: #cfd3d9; border-radius: 5px; min-height: 30px;
}}
QScrollBar::handle:vertical:hover {{ background: #b4b9c1; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ background: transparent; }}
QScrollBar:horizontal {{ height: 10px; background: transparent; }}
QScrollBar::handle:horizontal {{ background: #cfd3d9; border-radius: 5px; min-width: 30px; }}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{ width: 0; }}

/* ── 日志 ── */
QPlainTextEdit#LogView {{
    background: #1e2227;
    color: #d6dae0;
    border: 1px solid #2c3138;
    font-family: Consolas, "Courier New", monospace;
    font-size: 12px;
    border-radius: 6px;
}}

/* ── 状态徽标 ── */
QLabel#Badge {{ border-radius: 10px; padding: 3px 10px; font-size: 12px; font-weight: 600; }}
QLabel#Badge[state="on"]  {{ background: #dcfce7; color: {C_OK}; }}
QLabel#Badge[state="off"] {{ background: #f0f1f3; color: {C_MUTED}; }}

QCheckBox {{ spacing: 7px; }}
QCheckBox::indicator {{
    width: 16px; height: 16px;
    border: 1px solid #c3c7ce; border-radius: 4px;
    background: {C_CARD};
}}
QCheckBox::indicator:hover {{ border-color: {C_ACCENT}; }}
QCheckBox::indicator:checked {{
    background: {C_ACCENT}; border-color: {C_ACCENT};
    image: none;
}}

QSplitter::handle {{ background: {C_BORDER}; }}
QSplitter::handle:horizontal {{ width: 1px; }}
"""


# ════════════════ 小工具 ════════════════

class HelpButton(QToolButton):
    """字段旁的 ? 按钮 —— 点开显示完整说明。"""

    def __init__(self, spec: dict, parent=None):
        super().__init__(parent)
        self.setObjectName("Help")
        self.setText("?")
        self.setCursor(Qt.WhatsThisCursor)
        self.setToolTip("查看这个配置项的详细说明")
        self._spec = spec
        self.clicked.connect(self._show)

    def _show(self):
        from PySide6.QtWidgets import QMessageBox

        s = self._spec
        box = QMessageBox(self)
        box.setWindowTitle(s.get("label", s.get("key", "")))
        box.setTextFormat(Qt.RichText)

        parts = [f"<b style='font-size:14px'>{s.get('label','')}</b>"]
        parts.append(
            f"<p style='color:{C_MUTED};font-size:12px;margin-top:2px'>"
            f"<code>{s.get('key','')}</code></p>"
        )

        # 元信息：默认值 / 示例 / 是否需重启 / 取值范围
        meta = []
        if s.get("_default_desc"):
            meta.append(f"默认 <b>{s['_default_desc']}</b>")
        elif "default" in s and s["default"] is not None:
            meta.append(f"默认 <b>{s['default']}</b>")
        if s.get("example") not in (None, "") and s.get("type") != "secret":
            meta.append(f"示例 <code>{s['example']}</code>")
        if s.get("min") is not None or s.get("max") is not None:
            lo = s.get("min", "")
            hi = s.get("max", "")
            meta.append(f"范围 {lo} ~ {hi}")
        if s.get("restart"):
            meta.append("<span style='color:%s'>改完需重启</span>" % C_WARN)
        if meta:
            parts.append(
                "<p style='font-size:12px;color:%s'>%s</p>" % (C_MUTED, " · ".join(meta))
            )

        if s.get("help"):
            parts.append(f"<p>{s['help']}</p>")
        if s.get("hint"):
            parts.append(
                f"<p style='color:{C_WARN}'><b>⚠️ {s['hint']}</b></p>"
            )
        if s.get("type") == "secret":
            parts.append(
                "<p style='font-size:12px;color:%s'>留空 = 保持原值不变；"
                "要修改就直接输入新值。</p>" % C_MUTED
            )

        box.setText("".join(parts))
        box.setStandardButtons(QMessageBox.Ok)
        box.exec()


class Card(QFrame):
    """一个配置分组卡片：标题 + 说明 + 若干字段行。"""

    def __init__(self, title: str, desc: str = "", parent=None):
        super().__init__(parent)
        self.setObjectName("Card")
        outer = QVBoxLayout(self)
        outer.setContentsMargins(16, 14, 16, 16)
        outer.setSpacing(10)

        head = QVBoxLayout()
        head.setSpacing(2)
        t = QLabel(title)
        t.setObjectName("CardTitle")
        head.addWidget(t)
        if desc:
            d = QLabel(desc)
            d.setObjectName("CardDesc")
            d.setWordWrap(True)
            head.addWidget(d)
        outer.addLayout(head)

        self.body = QVBoxLayout()
        self.body.setSpacing(12)
        self.body.setContentsMargins(0, 4, 0, 0)
        outer.addLayout(self.body)

    def add_row(self, label_widgets, control: QWidget):
        row = QHBoxLayout()
        row.setSpacing(10)
        for w in label_widgets:
            row.addWidget(w)
        row.addWidget(control, 1)
        self.body.addLayout(row)

    def add_widget(self, w: QWidget):
        self.body.addWidget(w)


def make_card_scroll(parent=None) -> tuple[QScrollArea, QVBoxLayout]:
    """返回 (滚动区, 可往里加 Card 的布局)。"""
    area = QScrollArea(parent)
    area.setWidgetResizable(True)
    holder = QWidget()
    lay = QVBoxLayout(holder)
    lay.setContentsMargins(4, 4, 4, 4)
    lay.setSpacing(12)
    lay.addStretch(1)
    area.setWidget(holder)
    return area, lay


def insert_card(layout: QVBoxLayout, card: Card) -> None:
    """插到末尾 stretch 之前。"""
    layout.insertWidget(layout.count() - 1, card)
