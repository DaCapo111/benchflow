"""
NewProtocolDialog — creates a new protocol via one of three methods:

  • Blank Protocol    — just a name + category
  • From Template     — copy a built-in template (template stays untouched)
  • Duplicate Existing — copy one of the user's existing protocols
"""
from __future__ import annotations

import copy
import time
import uuid
from typing import Any

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox, QDialog, QFrame, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QVBoxLayout, QWidget,
)

from qt_app.theme import Colors, Fonts, Radii


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_blank(name: str, category: str) -> dict[str, Any]:
    now = int(time.time() * 1000)
    return {
        "id":          str(uuid.uuid4()),
        "name":        name.strip() or "New Protocol",
        "category":    category.strip(),
        "description": "",
        "tags":        [],
        "createdAt":   now,
        "updatedAt":   now,
        "steps":       [],
    }


def _copy_protocol(source: dict[str, Any], new_name: str) -> dict[str, Any]:
    now = int(time.time() * 1000)
    dup = copy.deepcopy(source)
    dup["id"]        = str(uuid.uuid4())
    dup["name"]      = new_name.strip() or f"Copy of {source.get('name','Protocol')}"
    dup["createdAt"] = now
    dup["updatedAt"] = now
    # Re-generate step IDs so they are unique
    for step in dup.get("steps", []):
        step["id"] = str(uuid.uuid4())
    return dup


# ── NewProtocolDialog ─────────────────────────────────────────────────────────

class NewProtocolDialog(QDialog):
    """Modal dialog for creating a new protocol.

    After exec() == Accepted, call:
        dlg.result_dict()  → the ready-to-save protocol dict
    """

    _METHODS = [
        ("blank",     "Blank Protocol",      "Start from scratch — add steps in the editor."),
        ("template",  "From Template",       "Copy a built-in template as your starting point."),
        ("duplicate", "Duplicate Existing",  "Clone one of your own protocols."),
    ]

    _BTN_ACTIVE = (
        f"QPushButton {{ background: {Colors.ACCENT}; color: white;"
        f"  border: 2px solid {Colors.ACCENT}; border-radius: {Radii.MD}px;"
        f"  font-size: {Fonts.SIZE_SM}px; font-weight: 700; padding: 10px 16px; }}"
    )
    _BTN_IDLE = (
        f"QPushButton {{ background: {Colors.BG_CARD}; color: {Colors.TEXT_SECOND};"
        f"  border: 1px solid {Colors.BORDER}; border-radius: {Radii.MD}px;"
        f"  font-size: {Fonts.SIZE_SM}px; padding: 10px 16px; }}"
        f"QPushButton:hover {{ background: {Colors.BG_CARD_HOV}; color: {Colors.TEXT_PRIMARY}; }}"
    )

    def __init__(self, protocols: list[dict], templates: list[dict],
                 parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("New Protocol")
        self.setMinimumWidth(460)
        self.setStyleSheet(f"QDialog {{ background: {Colors.BG_SIDEBAR}; }}")
        self._protocols  = protocols
        self._templates  = templates
        self._method     = "blank"
        self._result: dict[str, Any] | None = None

        self._build()

    # ── UI construction ───────────────────────────────────────────────────────

    def _build(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 20)
        root.setSpacing(16)

        # Title
        title = QLabel("New Protocol")
        title.setStyleSheet(
            f"color: {Colors.TEXT_PRIMARY}; font-size: {Fonts.SIZE_LG}px; font-weight: 700;"
        )
        root.addWidget(title)

        # Method selector
        method_row = QHBoxLayout()
        method_row.setSpacing(8)
        self._method_btns: dict[str, QPushButton] = {}
        for key, label, _ in self._METHODS:
            b = QPushButton(label)
            b.setCheckable(False)
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.clicked.connect(lambda chk=False, k=key: self._set_method(k))
            self._method_btns[key] = b
            method_row.addWidget(b)
        root.addLayout(method_row)

        # Description label (changes with method)
        self._desc_lbl = QLabel("")
        self._desc_lbl.setStyleSheet(
            f"color: {Colors.TEXT_MUTED}; font-size: {Fonts.SIZE_XS}px;"
        )
        root.addWidget(self._desc_lbl)

        # Separator
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setFixedHeight(1)
        sep.setStyleSheet(f"background: {Colors.BORDER};")
        root.addWidget(sep)

        # ── Dynamic form area ─────────────────────────────────────────────────
        self._form_w = QWidget()
        self._form_l = QVBoxLayout(self._form_w)
        self._form_l.setContentsMargins(0, 0, 0, 0)
        self._form_l.setSpacing(10)
        root.addWidget(self._form_w)

        # Name field (always shown)
        self._name_field = self._input("Protocol name *")
        self._form_l.addWidget(QLabel("Name"))
        self._form_l.itemAt(self._form_l.count()-1).widget().setStyleSheet(
            f"color: {Colors.TEXT_SECOND}; font-size: {Fonts.SIZE_SM}px;"
        )
        self._form_l.addWidget(self._name_field)

        # Category (shown for blank)
        self._cat_lbl = QLabel("Category")
        self._cat_lbl.setStyleSheet(
            f"color: {Colors.TEXT_SECOND}; font-size: {Fonts.SIZE_SM}px;"
        )
        self._cat_field = self._input("e.g. Cell Biology, Biochemistry…")
        self._form_l.addWidget(self._cat_lbl)
        self._form_l.addWidget(self._cat_field)

        # Source selector (shown for template/duplicate)
        self._src_lbl = QLabel("Source")
        self._src_lbl.setStyleSheet(
            f"color: {Colors.TEXT_SECOND}; font-size: {Fonts.SIZE_SM}px;"
        )
        self._src_cb = QComboBox()
        self._src_cb.setStyleSheet(
            f"QComboBox {{ background: {Colors.BG_INPUT}; color: {Colors.TEXT_PRIMARY};"
            f"  border: 1px solid {Colors.BORDER}; border-radius: {Radii.MD}px;"
            f"  padding: 7px 12px; font-size: {Fonts.SIZE_SM}px; }}"
            f"QComboBox:focus {{ border-color: {Colors.ACCENT}; }}"
            f"QComboBox QAbstractItemView {{ background: {Colors.BG_SIDEBAR};"
            f"  color: {Colors.TEXT_PRIMARY}; border: 1px solid {Colors.BORDER};"
            f"  selection-background-color: {Colors.ACCENT}; }}"
        )
        self._src_cb.currentIndexChanged.connect(self._on_source_changed)
        self._form_l.addWidget(self._src_lbl)
        self._form_l.addWidget(self._src_cb)

        # ── Buttons ───────────────────────────────────────────────────────────
        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)
        btn_row.addStretch()

        cancel = QPushButton("Cancel")
        cancel.setFixedHeight(36)
        cancel.setMinimumWidth(80)
        cancel.setCursor(Qt.CursorShape.PointingHandCursor)
        cancel.setStyleSheet(
            f"QPushButton {{ background: transparent; color: {Colors.TEXT_SECOND};"
            f"  border: 1px solid {Colors.BORDER}; border-radius: {Radii.MD}px;"
            f"  font-size: {Fonts.SIZE_SM}px; padding: 0 16px; }}"
            f"QPushButton:hover {{ background: {Colors.BG_CARD_HOV}; }}"
        )
        cancel.clicked.connect(self.reject)
        btn_row.addWidget(cancel)

        self._ok_btn = QPushButton("Create Protocol")
        self._ok_btn.setFixedHeight(36)
        self._ok_btn.setMinimumWidth(130)
        self._ok_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._ok_btn.setStyleSheet(
            f"QPushButton {{ background: {Colors.ACCENT}; color: white;"
            f"  border: none; border-radius: {Radii.MD}px;"
            f"  font-size: {Fonts.SIZE_SM}px; font-weight: 600; padding: 0 16px; }}"
            f"QPushButton:hover {{ background: {Colors.ACCENT_HOVER}; }}"
        )
        self._ok_btn.clicked.connect(self._accept)
        btn_row.addWidget(self._ok_btn)

        root.addLayout(btn_row)

        # Initialize to blank
        self._set_method("blank")

    def _input(self, placeholder: str) -> QLineEdit:
        e = QLineEdit()
        e.setPlaceholderText(placeholder)
        e.setFixedHeight(38)
        e.setStyleSheet(
            f"QLineEdit {{ background: {Colors.BG_INPUT}; color: {Colors.TEXT_PRIMARY};"
            f"  border: 1px solid {Colors.BORDER}; border-radius: {Radii.MD}px;"
            f"  padding: 0 12px; font-size: {Fonts.SIZE_SM}px; }}"
            f"QLineEdit:focus {{ border-color: {Colors.ACCENT}; }}"
        )
        return e

    # ── Method switching ──────────────────────────────────────────────────────

    def _set_method(self, method: str) -> None:
        self._method = method

        for key, btn in self._method_btns.items():
            btn.setStyleSheet(self._BTN_ACTIVE if key == method else self._BTN_IDLE)

        desc = next((d for k, _, d in self._METHODS if k == method), "")
        self._desc_lbl.setText(desc)

        is_blank = (method == "blank")
        is_src   = (method in ("template", "duplicate"))

        self._cat_lbl.setVisible(is_blank)
        self._cat_field.setVisible(is_blank)
        self._src_lbl.setVisible(is_src)
        self._src_cb.setVisible(is_src)

        # Populate source combo
        if is_src:
            self._src_cb.blockSignals(True)
            self._src_cb.clear()
            items = self._templates if method == "template" else self._protocols
            for item in items:
                self._src_cb.addItem(item.get("name", "Untitled"), userData=item)
            self._src_cb.blockSignals(False)
            self._on_source_changed()

        # Reset name placeholder
        if method == "template" and self._templates:
            self._name_field.setPlaceholderText("Name for the new protocol…")
        elif method == "duplicate" and self._protocols:
            self._name_field.setPlaceholderText("Name for the copy…")
        else:
            self._name_field.setPlaceholderText("Protocol name *")

    def _on_source_changed(self) -> None:
        """Prefill name when source changes."""
        src = self._src_cb.currentData()
        if src:
            src_name = src.get("name", "")
            prefix = "" if self._method == "template" else "Copy of "
            self._name_field.setPlaceholderText(f"{prefix}{src_name}")

    # ── Accept ────────────────────────────────────────────────────────────────

    def _accept(self) -> None:
        name = self._name_field.text().strip()

        if self._method == "blank":
            if not name:
                self._name_field.setFocus()
                self._name_field.setStyleSheet(
                    f"QLineEdit {{ background: {Colors.BG_INPUT}; color: {Colors.TEXT_PRIMARY};"
                    f"  border: 1px solid {Colors.DANGER}; border-radius: {Radii.MD}px;"
                    f"  padding: 0 12px; font-size: {Fonts.SIZE_SM}px; }}"
                )
                return
            self._result = _make_blank(name, self._cat_field.text())

        elif self._method == "template":
            src = self._src_cb.currentData()
            if src is None:
                return
            final_name = name or f"{src.get('name','Template')}"
            self._result = _copy_protocol(src, final_name)

        elif self._method == "duplicate":
            src = self._src_cb.currentData()
            if src is None:
                return
            final_name = name or f"Copy of {src.get('name','Protocol')}"
            self._result = _copy_protocol(src, final_name)

        if self._result:
            self.accept()

    # ── Result ────────────────────────────────────────────────────────────────

    def result_dict(self) -> dict[str, Any] | None:
        return self._result

    def result_method(self) -> str:
        return self._method
