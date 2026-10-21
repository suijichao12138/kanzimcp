#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""form.py — schema 驱动的表单构建器（PySide6）

★ 本文件不认识任何具体配置项。
   全部行为由 schema.py 的 field spec 决定 —— 加配置项只改 schema.py。

对外接口：
    FormBuilder.build(specs, values, on_change) -> (QWidget, dict)
        返回 (容器控件, {key: FieldHandle})
    FieldHandle.get() / .set(v) / .mark_error(msg, ok)
"""
from __future__ import annotations

import os
from pathlib import Path

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
    QSpinBox,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from widgets import C_ACCENT, C_BORDER, C_ERR, C_MUTED, C_REQUIRED, Card, HelpButton


# ════════════════ 字段句柄 ════════════════

class FieldHandle:
    """一个字段的读写 + 错误标记。"""

    def __init__(self, spec: dict, widget, kind: str, extra=None):
        self.spec = spec
        self.key = spec["key"]
        self.widget = widget
        self.kind = kind
        self.extra = extra or {}          # dict_list 的子控件等
        self.err_label: QLabel | None = None

    # ── 读 ──
    def get(self):
        k = self.kind
        if k in ("str", "path", "secret"):
            return self.widget.text()
        if k == "int":
            return self.widget.value()
        if k == "float":
            return round(self.widget.value(), 6)
        if k == "bool":
            return self.widget.isChecked()
        if k == "enum":
            return self.widget.currentData()
        if k == "list":
            raw = self.widget.toPlainText()
            return [ln.strip() for ln in raw.splitlines() if ln.strip()]
        if k == "dict":
            return _parse_dict(self.widget.text())
        if k == "dict_list":
            return _collect_dict_list(self)
        return None

    # ── 写 ──
    def set(self, v):
        k = self.kind
        if k in ("str", "path"):
            self.widget.setText("" if v is None else str(v))
        elif k == "secret":
            # ★ 密钥特殊：显示掩码，不动真值
            if v:
                self.widget.setPlaceholderText("已设置（留空=不改）")
                self.widget.setText("")
            else:
                self.widget.setText("")
        elif k == "int":
            self.widget.setValue(int(v) if v is not None else self.spec.get("default", 0) or 0)
        elif k == "float":
            self.widget.setValue(float(v) if v is not None else 0.0)
        elif k == "bool":
            self.widget.setChecked(bool(v))
        elif k == "enum":
            idx = self.widget.findData(v)
            if idx < 0:
                idx = 0
            self.widget.setCurrentIndex(idx)
        elif k == "list":
            self.widget.setPlainText("\n".join(str(x) for x in (v or [])))
        elif k == "dict":
            self.widget.setText(_format_dict(v))
        elif k == "dict_list":
            _populate_dict_list(self, v or [])

    # ── 错误标记 ──
    def mark_error(self, msg: str | None):
        if self.err_label is not None:
            if msg:
                self.err_label.setText("⚠️ " + msg)
                self.err_label.setVisible(True)
            else:
                self.err_label.setVisible(False)
        # 输入框描红
        if isinstance(self.widget, (QLineEdit, QPlainTextEdit)):
            self.widget.setProperty("invalid", "true" if msg else "false")
            self.widget.style().unpolish(self.widget)
            self.widget.style().polish(self.widget)


# ════════════════ 解析/格式化小工具 ════════════════

def _parse_dict(text: str) -> dict:
    """'k: v; k2: v2' → dict（也兼容换行分隔）。"""
    out: dict = {}
    if not text:
        return out
    for chunk in text.replace("\n", ";").split(";"):
        c = chunk.strip()
        if not c or ":" not in c:
            continue
        k, _, v = c.partition(":")
        k, v = k.strip(), v.strip()
        if k:
            out[k] = v
    return out


def _format_dict(d) -> str:
    if not isinstance(d, dict):
        return ""
    return "; ".join(f"{k}: {v}" for k, v in d.items())


def _collect_dict_list(handle: FieldHandle) -> list:
    """把条目卡片收集回 list[dict]。"""
    rows = handle.extra.get("rows", [])
    template = handle.spec.get("fields", [])
    out = []
    for row_widgets in rows:
        item = {}
        for sub in template:
            w = row_widgets.get(sub["key"])
            if w is None:
                continue
            v = w.text() if isinstance(w, QLineEdit) else w.currentText()
            if v.strip() == "" and sub.get("skip_empty"):
                continue
            item[sub["key"]] = v
        if item:
            out.append(item)
    return out


def _populate_dict_list(handle: FieldHandle, items: list) -> None:
    rows = handle.extra.get("rows", [])
    for w in rows:
        w["__frame"].setParent(None)
    rows.clear()
    container = handle.extra["container"]
    template = handle.spec.get("fields", [])
    for item in items:
        _add_dict_list_row(handle, template, item)


def _add_dict_list_row(handle: FieldHandle, template: list, item: dict | None = None):
    item = item or {}
    outer = handle.extra["container"]
    rows = handle.extra["rows"]
    lay = handle.extra["layout"]

    frame = QFrame()
    frame.setStyleSheet(
        f"QFrame{{background:#fafbfc;border:1px solid {C_BORDER};border-radius:6px;}}"
    )
    h = QHBoxLayout(frame)
    h.setContentsMargins(10, 8, 10, 8)
    h.setSpacing(8)

    fields: dict = {"__frame": frame}
    for sub in template:
        col = QVBoxLayout()
        col.setSpacing(2)
        lab = QLabel(sub.get("label", sub["key"]))
        lab.setStyleSheet(f"color:{C_MUTED};font-size:11px;")
        col.addWidget(lab)
        le = QLineEdit(str(item.get(sub["key"], "") or ""))
        le.setPlaceholderText(sub.get("placeholder", sub.get("example", "")))
        le.setMinimumWidth(80)
        if sub.get("flex"):
            le.setMinimumWidth(200)
        col.addWidget(le)
        fields[sub["key"]] = le
        h.addLayout(col, 1 if sub.get("flex") else 0)

    rm = QToolButton()
    rm.setText("✕")
    rm.setToolTip("删除这一条")
    rm.setCursor(Qt.PointingHandCursor)
    rm.setStyleSheet(
        f"QToolButton{{border:none;background:transparent;color:{C_MUTED};"
        f"font-size:14px;padding:0 6px;}}"
        f"QToolButton:hover{{color:{C_ERR};}}"
    )

    def _remove():
        rows.remove(fields)
        frame.setParent(None)

    rm.clicked.connect(_remove)
    h.addWidget(rm, 0, Qt.AlignBottom)

    lay.insertWidget(lay.count() - 1, frame)
    rows.append(fields)


# ════════════════ 表单构建 ════════════════

def build_group(specs: list, values: dict, getter) -> tuple[Card, dict]:
    """把同一分组的字段 spec 构造成一张卡片。

    specs  : schema 里同一 group 的字段列表
    values : 当前配置（用 getter 按 key 取值）
    getter : (key) -> value
    返回   : (Card, {key: FieldHandle})
    """
    group = specs[0].get("group", "")
    card = Card(group, specs[0].get("group_help", ""))
    handles: dict = {}

    for spec in specs:
        ctrl = _make_control(spec)
        if ctrl is None:
            continue

        rows = _make_label_row(spec)
        card.add_row(rows, ctrl)

        handle = ctrl.property("__handle__")
        handles[spec["key"]] = handle

        # 错误提示行（默认隐藏）
        err = QLabel()
        err.setStyleSheet(f"color:{C_ERR};font-size:11px;")
        err.setVisible(False)
        err.setWordWrap(True)
        handle.err_label = err
        card.add_widget(err)

        # 赋初值
        try:
            handle.set(getter(spec["key"]))
        except Exception:                                    # noqa: BLE001
            pass

    return card, handles


def _make_label_row(spec: dict) -> list:
    """字段左侧：名称(+必填星) + ? 按钮。"""
    out = []
    txt = spec.get("label", spec["key"])
    if spec.get("required"):
        txt = f"{txt} <span style='color:{C_REQUIRED}'>*</span>"
    lab = QLabel(txt)
    lab.setTextFormat(Qt.RichText)
    lab.setMinimumWidth(150)
    lab.setMaximumWidth(210)
    lab.setWordWrap(True)
    lab.setStyleSheet("font-size:13px;")
    out.append(lab)

    hb = HelpButton(spec)
    out.append(hb)
    return out


def _make_control(spec: dict) -> QWidget | None:
    """按 spec.type 造控件，并存 FieldHandle 到控件的 __handle__ 属性。"""
    t = spec.get("type", "str")
    key = spec["key"]

    if t in ("str", "path", "secret"):
        row = QWidget()
        h = QHBoxLayout(row)
        h.setContentsMargins(0, 0, 0, 0)
        h.setSpacing(6)

        le = QLineEdit()
        le.setPlaceholderText(str(spec.get("placeholder", spec.get("example", "")) or ""))
        if t == "secret":
            le.setEchoMode(QLineEdit.Password)
        h.addWidget(le, 1)

        if t == "secret":
            eye = QToolButton()
            eye.setObjectName("Eye")
            eye.setText("👁")
            eye.setToolTip("显示 / 隐藏")
            eye.setCursor(Qt.PointingHandCursor)

            def _toggle():
                if le.echoMode() == QLineEdit.Password:
                    le.setEchoMode(QLineEdit.Normal)
                    eye.setText("🙈")
                else:
                    le.setEchoMode(QLineEdit.Password)
                    eye.setText("👁")

            eye.clicked.connect(_toggle)
            h.addWidget(eye)

        if t == "path":
            btn = QPushButton("浏览…")
            btn.setCursor(Qt.PointingHandCursor)

            def _pick():
                cur = le.text().strip()
                start = cur if cur and Path(cur).is_dir() else str(Path.home())
                d = QFileDialog.getExistingDirectory(row, "选择目录", start)
                if d:
                    le.setText(d)

            btn.clicked.connect(_pick)
            h.addWidget(btn)

        handle = FieldHandle(spec, le, t)
        row.setProperty("__handle__", handle)

        # dict_list 之外的控件外再包一层是为了拿 handle
        row.__dict__["_le"] = le
        # add_row 拿到的应是 row（含按钮），handle 需要在 row 上
        return row

    if t == "int":
        w = QSpinBox()
        w.setRange(int(spec.get("min", -2147483647)), int(spec.get("max", 2147483647)))
        if spec.get("suffix"):
            w.setSuffix(" " + spec["suffix"])
        w.setProperty("__handle__", FieldHandle(spec, w, "int"))
        return w

    if t == "float":
        w = QDoubleSpinBox()
        w.setDecimals(int(spec.get("decimals", 2)))
        w.setRange(float(spec.get("min", -1e12)), float(spec.get("max", 1e12)))
        w.setProperty("__handle__", FieldHandle(spec, w, "float"))
        return w

    if t == "bool":
        w = QCheckBox(spec.get("checkbox_label", "启用"))
        w.setProperty("__handle__", FieldHandle(spec, w, "bool"))
        return w

    if t == "enum":
        w = QComboBox()
        for opt in spec.get("options", []):
            if isinstance(opt, dict):
                w.addItem(opt.get("label", opt.get("value", "")), opt.get("value"))
            else:
                w.addItem(str(opt), opt)
        w.setProperty("__handle__", FieldHandle(spec, w, "enum"))
        return w

    if t == "list":
        w = QPlainTextEdit()
        w.setPlaceholderText(
            spec.get("placeholder") or "一行一个，例如：\nsuijichao\nlaosui"
        )
        w.setFixedHeight(int(spec.get("height", 76)))
        w.setProperty("__handle__", FieldHandle(spec, w, "list"))
        return w

    if t == "dict":
        w = QLineEdit()
        w.setPlaceholderText(
            spec.get("placeholder") or "k: v; k2: v2   （分号分隔）"
        )
        w.setProperty("__handle__", FieldHandle(spec, w, "dict"))
        return w

    if t == "dict_list":
        holder = QWidget()
        v = QVBoxLayout(holder)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(6)

        rows_lay = QVBoxLayout()
        rows_lay.setSpacing(6)
        v.addLayout(rows_lay)

        add = QPushButton("+ 添加一条")
        add.setCursor(Qt.PointingHandCursor)
        add.setStyleSheet("text-align:left;")
        v.addWidget(add, 0, Qt.AlignLeft)

        handle = FieldHandle(spec, holder, "dict_list")
        handle.extra = {"layout": rows_lay, "rows": [], "container": holder}
        add.clicked.connect(
            lambda: _add_dict_list_row(handle, spec.get("fields", []), None)
        )
        holder.setProperty("__handle__", handle)
        return holder

    # 未知类型 → 退化成长文本框，别让界面崩
    w = QLineEdit()
    w.setPlaceholderText(f"（未支持的类型 {t}）")
    w.setProperty("__handle__", FieldHandle(spec, w, "str"))
    return w
