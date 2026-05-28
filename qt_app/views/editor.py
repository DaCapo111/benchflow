"""
Protocol Editor — Phase 6.

Layout
------
EditorPage
├── Top bar:  ← Back   [Protocol name]   [● Unsaved] [Save Protocol]
├── Meta card: Name · Category · Tags · Description
└── QSplitter (horizontal)
    ├── Left: step list
    │   ├── Section header + [＋ Add Step]
    │   └── _StepRow × N  (click → select, ▲▼ reorder, ⧉ dup, ✕ del)
    └── Right: _StepForm (scrollable)
        ├── Title + Type
        ├── Timing (hands-on / wait / buffer)
        ├── Conditions (temperature / centrifuge / shaking)
        ├── Description + Notes + Warnings
        ├── Reagents  (add/remove rows)
        ├── Equipment (tag chips)
        ├── Checklist (line items)
        └── Substeps  (line items)
"""
from __future__ import annotations

import copy
import time
import uuid
from typing import Any

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QComboBox, QDoubleSpinBox, QFileDialog, QFrame, QHBoxLayout,
    QLabel, QLineEdit, QMenu, QMessageBox, QPlainTextEdit,
    QPushButton, QScrollArea, QSizePolicy,
    QSplitter, QVBoxLayout, QWidget,
)

from qt_app.theme import Colors, Fonts, Radii
from qt_app.components.widgets import (
    HSeparator, PageTitle, PrimaryButton, SubLabel,
)
from qt_app.components.toast import ToastManager
from qt_app.services.event_bus import bus
from qt_app.views.base_page import BasePage


# ── Constants ─────────────────────────────────────────────────────────────────

STEP_TYPES = [
    "preparation", "reagent_addition", "pipetting", "mixing",
    "incubation", "heating", "cooling", "waiting",
    "centrifuge", "wash", "transfer", "resuspension",
    "lysis", "measurement", "staining", "blocking",
    "gel_running", "electrophoresis", "membrane_transfer",
    "imaging", "harvest", "sample_collection", "storage",
    "note", "other",
]

_TYPE_COLOR: dict[str, str] = {
    "preparation":       "#3b82f6",
    "reagent_addition":  "#14b8a6",
    "mixing":            "#a855f7",
    "incubation":        "#f97316",
    "waiting":           "#475569",
    "centrifuge":        "#6366f1",
    "wash":              "#06b6d4",
    "transfer":          "#818cf8",
    "pipetting":         "#38bdf8",
    "resuspension":      "#22c55e",
    "staining":          "#f472b6",
    "blocking":          "#fb7185",
    "electrophoresis":   "#c084fc",
    "gel_running":       "#a78bfa",
    "membrane_transfer": "#60a5fa",
    "imaging":           "#34d399",
    "measurement":       "#fb923c",
    "heating":           "#fbbf24",
    "cooling":           "#7dd3fc",
    "lysis":             "#f87171",
    "harvest":           "#4ade80",
    "sample_collection": "#a3e635",
    "storage":           "#94a3b8",
    "note":              "#e2e8f0",
    "other":             "#64748b",
}


def _dot(step_type: str) -> str:
    """Return a colored bullet string (unicode) for the type."""
    return _TYPE_COLOR.get(step_type, "#64748b")


def _mk_input(placeholder: str = "", height: int = 36) -> QLineEdit:
    e = QLineEdit()
    e.setPlaceholderText(placeholder)
    e.setFixedHeight(height)
    e.setStyleSheet(
        f"QLineEdit {{ background: {Colors.BG_INPUT}; color: {Colors.TEXT_PRIMARY};"
        f"  border: 1px solid {Colors.BORDER_LIGHT}; border-radius: {Radii.MD}px;"
        f"  padding: 0 10px; font-size: {Fonts.SIZE_SM}px; }}"
        f"QLineEdit:focus {{ border-color: {Colors.ACCENT}; }}"
    )
    return e


def _mk_textarea(placeholder: str = "", min_h: int = 64) -> QPlainTextEdit:
    t = QPlainTextEdit()
    t.setPlaceholderText(placeholder)
    t.setMinimumHeight(min_h)
    t.setMaximumHeight(min_h * 2)
    t.setStyleSheet(
        f"QPlainTextEdit {{ background: {Colors.BG_INPUT}; color: {Colors.TEXT_PRIMARY};"
        f"  border: 1px solid {Colors.BORDER_LIGHT}; border-radius: {Radii.MD}px;"
        f"  padding: 8px 10px; font-size: {Fonts.SIZE_SM}px; }}"
        f"QPlainTextEdit:focus {{ border-color: {Colors.ACCENT}; }}"
    )
    return t


def _mk_spinbox(max_val: float = 9999, decimals: int = 1) -> QDoubleSpinBox:
    sb = QDoubleSpinBox()
    sb.setRange(0, max_val)
    sb.setDecimals(decimals)
    sb.setSuffix("  min")
    sb.setFixedHeight(36)
    sb.setFixedWidth(110)
    sb.setStyleSheet(
        f"QDoubleSpinBox {{ background: {Colors.BG_INPUT}; color: {Colors.TEXT_PRIMARY};"
        f"  border: 1px solid {Colors.BORDER_LIGHT}; border-radius: {Radii.MD}px;"
        f"  padding: 0 8px; font-size: {Fonts.SIZE_SM}px; }}"
        f"QDoubleSpinBox:focus {{ border-color: {Colors.ACCENT}; }}"
        f"QDoubleSpinBox::up-button, QDoubleSpinBox::down-button {{"
        f"  border: none; width: 16px; }}"
    )
    return sb


def _field_label(text: str) -> QLabel:
    lbl = QLabel(text)
    lbl.setStyleSheet(
        f"color: {Colors.TEXT_SECOND}; font-size: {Fonts.SIZE_SM}px; font-weight: 600;"
    )
    return lbl


def _section_hdr(text: str) -> QLabel:
    lbl = QLabel(text)
    lbl.setStyleSheet(
        f"color: {Colors.TEXT_PRIMARY}; font-size: {Fonts.SIZE_SM}px;"
        f"font-weight: 700; letter-spacing: 0.5px;"
        f"padding-top: 6px;"
    )
    return lbl


def _icon_btn(text: str, tooltip: str = "", size: int = 28,
              color: str = Colors.TEXT_SECOND) -> QPushButton:
    b = QPushButton(text)
    b.setFixedSize(size, size)
    b.setCursor(Qt.CursorShape.PointingHandCursor)
    if tooltip:
        b.setToolTip(tooltip)
    b.setStyleSheet(
        f"QPushButton {{ background: transparent; color: {color};"
        f"  border: none; border-radius: {Radii.XS}px;"
        f"  font-size: {Fonts.SIZE_SM}px; }}"
        f"QPushButton:hover {{ background: {Colors.BG_CARD_HOV}; color: {Colors.TEXT_PRIMARY}; }}"
    )
    return b


# ── _StepRow ──────────────────────────────────────────────────────────────────

class _StepRow(QFrame):
    """One row in the step list panel."""

    row_clicked  = Signal(int)   # index
    move_up      = Signal(int)
    move_down    = Signal(int)
    duplicate    = Signal(int)
    deleted      = Signal(int)

    def __init__(self, index: int, step: dict,
                 parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._index = index
        self._step  = step
        self._sel   = False
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setStyleSheet(self._style(False))
        self._build()

    @staticmethod
    def _style(selected: bool) -> str:
        if selected:
            return (
                f"QFrame {{ background: {Colors.SELECTED_BG};"
                f"  border-radius: {Radii.LG}px;"
                f"  border: 1px solid {Colors.BORDER_LIGHT};"
                f"  border-left: 3px solid {Colors.ACCENT}; }}"
            )
        return (
            f"QFrame {{ background: {Colors.BG_CARD}; border-radius: {Radii.LG}px;"
            f"  border: 1px solid {Colors.BORDER_LIGHT}; }}"
            f"QFrame:hover {{ background: {Colors.HOVER_BG}; }}"
        )

    def _build(self) -> None:
        lay = QHBoxLayout(self)
        lay.setContentsMargins(10, 8, 8, 8)
        lay.setSpacing(6)

        # Type color dot
        dot = QLabel("●")
        color = _dot(self._step.get("type", "other"))
        dot.setStyleSheet(f"color: {color}; font-size: 10px;")
        dot.setFixedWidth(14)
        lay.addWidget(dot)

        # Number
        num = QLabel(f"{self._index + 1}.")
        num.setFixedWidth(24)
        num.setStyleSheet(
            f"color: {Colors.TEXT_MUTED}; font-size: {Fonts.SIZE_SM}px;"
        )
        lay.addWidget(num)

        # Title
        title = self._step.get("title", "") or f"Step {self._index + 1}"
        lbl = QLabel(title)
        lbl.setStyleSheet(
            f"color: {Colors.TEXT_PRIMARY}; font-size: {Fonts.SIZE_SM}px;"
        )
        lbl.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        lbl.setWordWrap(False)
        lay.addWidget(lbl, stretch=1)

        # Duration
        total = (
            float(self._step.get("handsOnMinutes", 0)) +
            float(self._step.get("waitMinutes", 0)) +
            float(self._step.get("bufferMinutes", 0))
        )
        if total > 0:
            dur = QLabel(f"{int(total)}m")
            dur.setStyleSheet(
                f"color: {Colors.TEXT_MUTED}; font-size: {Fonts.SIZE_XS}px;"
            )
            lay.addWidget(dur)

        # Action buttons
        up_btn  = _icon_btn("▲", "Move up")
        dn_btn  = _icon_btn("▼", "Move down")
        dup_btn = _icon_btn("⧉", "Duplicate")
        del_btn = _icon_btn("✕", "Delete", color=Colors.DANGER)

        idx = self._index
        up_btn.clicked.connect(lambda: self.move_up.emit(idx))
        dn_btn.clicked.connect(lambda: self.move_down.emit(idx))
        dup_btn.clicked.connect(lambda: self.duplicate.emit(idx))
        del_btn.clicked.connect(lambda: self.deleted.emit(idx))

        lay.addWidget(up_btn)
        lay.addWidget(dn_btn)
        lay.addWidget(dup_btn)
        lay.addWidget(del_btn)

    def set_selected(self, sel: bool) -> None:
        self._sel = sel
        self.setStyleSheet(self._style(sel))

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.row_clicked.emit(self._index)
        super().mousePressEvent(event)


# ── _ReagentRow ───────────────────────────────────────────────────────────────

class _ReagentRow(QWidget):
    """One reagent row: name | amount | unit | × ."""

    removed = Signal(object)  # self

    def __init__(self, reagent: dict | None = None,
                 parent: QWidget | None = None) -> None:
        super().__init__(parent)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(4)

        self._name   = _mk_input("Reagent name")
        self._amount = _mk_input("Amount", height=36)
        self._amount.setFixedWidth(80)
        self._unit   = _mk_input("Unit", height=36)
        self._unit.setFixedWidth(80)

        if reagent:
            self._name.setText(str(reagent.get("name", "")))
            self._amount.setText(str(reagent.get("amount", "")))
            self._unit.setText(str(reagent.get("unit", "")))

        rm = _icon_btn("✕", "Remove reagent", color=Colors.DANGER)
        rm.clicked.connect(lambda: self.removed.emit(self))

        lay.addWidget(self._name, stretch=1)
        lay.addWidget(self._amount)
        lay.addWidget(self._unit)
        lay.addWidget(rm)

    def to_dict(self) -> dict:
        return {
            "name":   self._name.text().strip(),
            "amount": self._amount.text().strip(),
            "unit":   self._unit.text().strip(),
        }


# ── _ListItemRow ──────────────────────────────────────────────────────────────

class _ListItemRow(QWidget):
    """Generic single-text list item (equipment / checklist / substep)."""

    removed = Signal(object)

    def __init__(self, text: str = "", placeholder: str = "",
                 parent: QWidget | None = None) -> None:
        super().__init__(parent)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(4)
        self._edit = _mk_input(placeholder)
        self._edit.setText(text)
        rm = _icon_btn("✕", "Remove", color=Colors.DANGER)
        rm.clicked.connect(lambda: self.removed.emit(self))
        lay.addWidget(self._edit, stretch=1)
        lay.addWidget(rm)

    def text(self) -> str:
        return self._edit.text().strip()


# ── _TagChip ──────────────────────────────────────────────────────────────────

class _TagChip(QFrame):
    removed = Signal(object)

    def __init__(self, tag: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._tag = tag
        lay = QHBoxLayout(self)
        lay.setContentsMargins(8, 3, 4, 3)
        lay.setSpacing(4)
        self.setStyleSheet(
            f"QFrame {{ background: {Colors.ACCENT_BG};"
            f"  border-radius: {Radii.LG}px;"
            f"  border: 1px solid {Colors.BORDER_LIGHT}; }}"
        )
        lbl = QLabel(f"#{tag}")
        lbl.setStyleSheet(f"color: {Colors.ACCENT}; font-size: {Fonts.SIZE_XS}px;")
        rm = QPushButton("×")
        rm.setFixedSize(16, 16)
        rm.setCursor(Qt.CursorShape.PointingHandCursor)
        rm.setStyleSheet(
            f"QPushButton {{ background: transparent; color: {Colors.TEXT_MUTED};"
            f"  border: none; font-size: 12px; }}"
            f"QPushButton:hover {{ color: {Colors.DANGER}; }}"
        )
        rm.clicked.connect(lambda: self.removed.emit(self))
        lay.addWidget(lbl)
        lay.addWidget(rm)

    def tag(self) -> str:
        return self._tag


# ── _StepForm ─────────────────────────────────────────────────────────────────

class _StepForm(QScrollArea):
    """Right-side detail editor for one step."""

    changed = Signal()   # any field edited

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setStyleSheet(f"background: {Colors.BG_PAGE};")

        self._inner = QWidget()
        self._inner.setStyleSheet(f"background: {Colors.BG_PAGE};")
        self._lay = QVBoxLayout(self._inner)
        self._lay.setContentsMargins(20, 16, 20, 32)
        self._lay.setSpacing(8)
        self.setWidget(self._inner)

        self._step: dict | None = None
        self._reagent_rows: list[_ReagentRow] = []
        self._equip_rows:   list[_ListItemRow] = []
        self._check_rows:   list[_ListItemRow] = []
        self._sub_rows:     list[_ListItemRow] = []

        self._reagent_cont: QWidget | None = None
        self._equip_cont:   QWidget | None = None
        self._check_cont:   QWidget | None = None
        self._sub_cont:     QWidget | None = None

        self._show_placeholder()

    # ── Public API ────────────────────────────────────────────────────────────

    def load_step(self, step: dict) -> None:
        """Populate form from step dict."""
        self.blockSignals(True)
        try:
            self._load_step(step)
        finally:
            self.blockSignals(False)

    def _load_step(self, step: dict) -> None:
        self._step = step
        self._clear()
        lay = self._lay

        # ── Title ─────────────────────────────────────────────────────────────
        lay.addWidget(_field_label("Step Title *"))
        self._title_edit = _mk_input("Enter step title…", height=38)
        self._title_edit.setText(step.get("title", ""))
        self._title_edit.textChanged.connect(self._on_changed)
        lay.addWidget(self._title_edit)

        # ── Type ──────────────────────────────────────────────────────────────
        lay.addWidget(_field_label("Step Type"))
        self._type_cb = QComboBox()
        for t in STEP_TYPES:
            self._type_cb.addItem(t.replace("_", " ").title(), userData=t)
        self._type_cb.setStyleSheet(
            f"QComboBox {{ background: {Colors.BG_INPUT}; color: {Colors.TEXT_PRIMARY};"
            f"  border: 1px solid {Colors.BORDER_LIGHT}; border-radius: {Radii.MD}px;"
            f"  padding: 6px 10px; font-size: {Fonts.SIZE_SM}px; }}"
            f"QComboBox:focus {{ border-color: {Colors.ACCENT}; }}"
            f"QComboBox QAbstractItemView {{ background: {Colors.BG_CARD};"
            f"  color: {Colors.TEXT_PRIMARY}; border: 1px solid {Colors.BORDER_LIGHT};"
            f"  selection-background-color: {Colors.SELECTED_BG}; selection-color: {Colors.TEXT_PRIMARY}; }}"
        )
        idx = self._type_cb.findData(step.get("type", "other"))
        self._type_cb.setCurrentIndex(max(0, idx))
        self._type_cb.currentIndexChanged.connect(self._on_changed)
        lay.addWidget(self._type_cb)

        lay.addWidget(HSeparator())

        # ── Timing ────────────────────────────────────────────────────────────
        lay.addWidget(_section_hdr("⏱  Timing"))
        timing_row = QHBoxLayout()
        timing_row.setSpacing(12)

        for attr, label in [
            ("handsOnMinutes", "Hands-on"),
            ("waitMinutes", "Wait"),
            ("bufferMinutes", "Buffer"),
        ]:
            col = QVBoxLayout()
            col.setSpacing(3)
            col.addWidget(_field_label(label))
            sb = _mk_spinbox()
            sb.setValue(float(step.get(attr, 0)))
            sb.valueChanged.connect(self._on_changed)
            setattr(self, f"_sb_{attr}", sb)
            col.addWidget(sb)
            timing_row.addLayout(col)

        timing_row.addStretch()
        lay.addLayout(timing_row)
        lay.addWidget(HSeparator())

        # ── Conditions ────────────────────────────────────────────────────────
        lay.addWidget(_section_hdr("🌡  Conditions"))
        for attr, label, ph in [
            ("temperature",        "Temperature",  "e.g. 4°C, 37°C, RT"),
            ("centrifugeCondition","Centrifuge",   "e.g. 14 000 × g, 15 min, 4°C"),
            ("shakingRotation",    "Shaking/RPM",  "e.g. 300 rpm, 15 min"),
        ]:
            lay.addWidget(_field_label(label))
            inp = _mk_input(ph)
            inp.setText(step.get(attr, ""))
            inp.textChanged.connect(self._on_changed)
            setattr(self, f"_inp_{attr}", inp)
            lay.addWidget(inp)

        lay.addWidget(HSeparator())

        # ── Description ───────────────────────────────────────────────────────
        lay.addWidget(_section_hdr("📝  Description"))
        self._desc_edit = _mk_textarea("Detailed procedure for this step…", min_h=80)
        self._desc_edit.setPlainText(step.get("description", ""))
        self._desc_edit.textChanged.connect(self._on_changed)
        lay.addWidget(self._desc_edit)

        # ── Notes ─────────────────────────────────────────────────────────────
        lay.addWidget(_field_label("Notes"))
        self._notes_edit = _mk_textarea("Helpful tips and observations…", min_h=56)
        self._notes_edit.setPlainText(step.get("notes", ""))
        self._notes_edit.textChanged.connect(self._on_changed)
        lay.addWidget(self._notes_edit)

        # ── Warnings ─────────────────────────────────────────────────────────
        lay.addWidget(_field_label("⚠ Warnings"))
        self._warn_edit = _mk_textarea("Safety notes, critical pitfalls…", min_h=56)
        self._warn_edit.setStyleSheet(
            f"QPlainTextEdit {{ background: {Colors.BG_INPUT}; color: {Colors.WARNING};"
            f"  border: 1px solid {Colors.BORDER_LIGHT}; border-radius: {Radii.MD}px;"
            f"  padding: 8px 10px; font-size: {Fonts.SIZE_SM}px; }}"
            f"QPlainTextEdit:focus {{ border-color: {Colors.WARNING}; }}"
        )
        self._warn_edit.setPlainText(step.get("warnings", ""))
        self._warn_edit.textChanged.connect(self._on_changed)
        lay.addWidget(self._warn_edit)

        lay.addWidget(HSeparator())

        # ── Reagents ──────────────────────────────────────────────────────────
        lay.addWidget(self._make_reagents_section(step.get("reagents", [])))

        lay.addWidget(HSeparator())

        # ── Equipment ─────────────────────────────────────────────────────────
        lay.addWidget(self._make_list_section(
            "🔬  Equipment",
            step.get("equipment", []),
            "equip", "e.g. Microcentrifuge, Ice bucket",
        ))

        lay.addWidget(HSeparator())

        # ── Checklist ─────────────────────────────────────────────────────────
        lay.addWidget(self._make_list_section(
            "☑  Checklist Items",
            [i if isinstance(i, str) else str(i.get("text", i)) for i in step.get("checklist", [])],
            "check", "e.g. Wear gloves, Pre-cool centrifuge",
        ))

        lay.addWidget(HSeparator())

        # ── Substeps ─────────────────────────────────────────────────────────
        lay.addWidget(self._make_list_section(
            "◈  Substeps",
            [s if isinstance(s, str) else str(s.get("text", s)) for s in step.get("substeps", [])],
            "sub", "e.g. Add 10 µL sample to tube",
        ))

        lay.addStretch()

    def collect(self) -> dict:
        """Read all form widgets → updated step dict."""
        if self._step is None:
            return {}
        d = dict(self._step)
        d["title"]              = self._title_edit.text().strip()
        d["type"]               = self._type_cb.currentData() or "other"
        d["handsOnMinutes"]     = self._sb_handsOnMinutes.value()
        d["waitMinutes"]        = self._sb_waitMinutes.value()
        d["bufferMinutes"]      = self._sb_bufferMinutes.value()
        d["temperature"]        = self._inp_temperature.text().strip()
        d["centrifugeCondition"]= self._inp_centrifugeCondition.text().strip()
        d["shakingRotation"]    = self._inp_shakingRotation.text().strip()
        d["description"]        = self._desc_edit.toPlainText().strip()
        d["notes"]              = self._notes_edit.toPlainText().strip()
        d["warnings"]           = self._warn_edit.toPlainText().strip()

        d["reagents"]  = [r.to_dict() for r in self._reagent_rows
                          if r.to_dict().get("name")]
        d["equipment"] = [r.text() for r in self._equip_rows if r.text()]
        d["checklist"] = [r.text() for r in self._check_rows if r.text()]
        d["substeps"]  = [r.text() for r in self._sub_rows  if r.text()]
        return d

    # ── Section builders ──────────────────────────────────────────────────────

    def _make_reagents_section(self, reagents: list) -> QWidget:
        w = QWidget()
        w.setStyleSheet("background: transparent;")
        lay = QVBoxLayout(w)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(4)

        hdr = QHBoxLayout()
        hdr.addWidget(_section_hdr("🧪  Reagents / Materials"))
        hdr.addStretch()
        add_btn = QPushButton("＋ Add")
        add_btn.setFixedHeight(26)
        add_btn.setFixedWidth(70)
        add_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        add_btn.setStyleSheet(
            f"QPushButton {{ background: {Colors.ACCENT_BG}; color: {Colors.ACCENT};"
            f"  border: 1px solid {Colors.BORDER_LIGHT}; border-radius: {Radii.LG}px;"
            f"  font-size: {Fonts.SIZE_XS}px; font-weight: 600; }}"
            f"QPushButton:hover {{ background: {Colors.ACCENT_BG}; }}"
        )
        hdr.addWidget(add_btn)
        lay.addLayout(hdr)

        # Column headers
        hdr2 = QHBoxLayout()
        hdr2.setSpacing(4)
        for lbl_text, w_val in [("Name", None), ("Amount", 80), ("Unit", 80), ("", 28)]:
            lbl = QLabel(lbl_text)
            lbl.setStyleSheet(f"color: {Colors.TEXT_MUTED}; font-size: {Fonts.SIZE_XS}px;")
            if w_val:
                lbl.setFixedWidth(w_val)
            else:
                lbl.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
            hdr2.addWidget(lbl)
        lay.addLayout(hdr2)

        # Container for rows
        self._reagent_cont = QWidget()
        self._reagent_cont.setStyleSheet("background: transparent;")
        cont_lay = QVBoxLayout(self._reagent_cont)
        cont_lay.setContentsMargins(0, 0, 0, 0)
        cont_lay.setSpacing(3)
        lay.addWidget(self._reagent_cont)

        self._reagent_rows = []
        for r in reagents:
            self._add_reagent_row(r)

        add_btn.clicked.connect(lambda: self._add_reagent_row({}))
        return w

    def _add_reagent_row(self, reagent: dict) -> None:
        row = _ReagentRow(reagent, parent=self._reagent_cont)
        row.removed.connect(self._remove_reagent_row)
        row._name.textChanged.connect(self._on_changed)
        row._amount.textChanged.connect(self._on_changed)
        row._unit.textChanged.connect(self._on_changed)
        self._reagent_rows.append(row)
        self._reagent_cont.layout().addWidget(row)
        self._on_changed()

    def _remove_reagent_row(self, row: _ReagentRow) -> None:
        if row in self._reagent_rows:
            self._reagent_rows.remove(row)
        row.deleteLater()
        self._on_changed()

    def _make_list_section(self, title: str, items: list[str],
                           key: str, placeholder: str) -> QWidget:
        w = QWidget()
        w.setStyleSheet("background: transparent;")
        lay = QVBoxLayout(w)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(4)

        hdr = QHBoxLayout()
        hdr.addWidget(_section_hdr(title))
        hdr.addStretch()
        add_btn = QPushButton("＋ Add")
        add_btn.setFixedHeight(26)
        add_btn.setFixedWidth(70)
        add_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        add_btn.setStyleSheet(
            f"QPushButton {{ background: {Colors.ACCENT_BG}; color: {Colors.ACCENT};"
            f"  border: 1px solid {Colors.BORDER_LIGHT}; border-radius: {Radii.LG}px;"
            f"  font-size: {Fonts.SIZE_XS}px; font-weight: 600; }}"
            f"QPushButton:hover {{ background: {Colors.ACCENT_BG}; }}"
        )
        hdr.addWidget(add_btn)
        lay.addLayout(hdr)

        # Container
        cont = QWidget()
        cont.setStyleSheet("background: transparent;")
        cont_lay = QVBoxLayout(cont)
        cont_lay.setContentsMargins(0, 0, 0, 0)
        cont_lay.setSpacing(3)
        lay.addWidget(cont)

        rows: list[_ListItemRow] = []
        setattr(self, f"_{key}_rows", rows)
        setattr(self, f"_{key}_cont", cont)

        for item in items:
            self._add_list_row(rows, cont, str(item), placeholder)

        add_btn.clicked.connect(lambda: self._add_list_row(rows, cont, "", placeholder))
        return w

    def _add_list_row(self, rows: list, cont: QWidget,
                      text: str, placeholder: str) -> None:
        row = _ListItemRow(text, placeholder, parent=cont)
        row.removed.connect(lambda r, ro=rows: self._remove_list_row(r, ro))
        row._edit.textChanged.connect(self._on_changed)
        rows.append(row)
        cont.layout().addWidget(row)
        self._on_changed()

    def _remove_list_row(self, row: _ListItemRow, rows: list) -> None:
        if row in rows:
            rows.remove(row)
        row.deleteLater()
        self._on_changed()

    # ── Internal ──────────────────────────────────────────────────────────────

    def _on_changed(self, *_) -> None:
        self.changed.emit()

    def _show_placeholder(self) -> None:
        self._lay.addStretch()
        lbl = QLabel("Select a step from the list\nto edit its details.")
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl.setWordWrap(True)
        lbl.setStyleSheet(
            f"color: {Colors.TEXT_MUTED}; font-size: {Fonts.SIZE_SM}px; font-style: italic;"
        )
        self._lay.addWidget(lbl)
        self._lay.addStretch()

    def _clear(self) -> None:
        while self._lay.count():
            item = self._lay.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()
            elif item.layout():
                _clear_layout(item.layout())
        self._reagent_rows = []
        self._equip_rows   = []
        self._check_rows   = []
        self._sub_rows     = []


def _clear_layout(layout) -> None:
    while layout.count():
        item = layout.takeAt(0)
        w = item.widget()
        if w:
            w.deleteLater()
        elif item.layout():
            _clear_layout(item.layout())


# ── _MetaCard ─────────────────────────────────────────────────────────────────

class _MetaCard(QFrame):
    """Collapsible metadata section: name, category, tags, description."""

    changed = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setStyleSheet(
            f"QFrame {{ background: {Colors.BG_CARD}; border-radius: {Radii.LG}px;"
            f"  border: 1px solid {Colors.BORDER_LIGHT}; }}"
        )
        self._tag_chips: list[_TagChip] = []
        self._build()

    def _build(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(16, 12, 16, 12)
        outer.setSpacing(8)

        # Row 1: name + category
        r1 = QHBoxLayout()
        r1.setSpacing(12)

        name_col = QVBoxLayout()
        name_col.setSpacing(3)
        name_col.addWidget(_field_label("Protocol Name *"))
        self._name_edit = QLineEdit()
        self._name_edit.setPlaceholderText("Protocol name")
        self._name_edit.setFixedHeight(36)
        self._name_edit.setStyleSheet(
            f"QLineEdit {{ background: {Colors.BG_INPUT}; color: {Colors.TEXT_PRIMARY};"
            f"  border: 1px solid {Colors.BORDER_LIGHT}; border-radius: {Radii.MD}px;"
            f"  padding: 0 10px; font-size: {Fonts.SIZE_MD}px; font-weight: 700; }}"
            f"QLineEdit:focus {{ border-color: {Colors.ACCENT}; }}"
        )
        self._name_edit.textChanged.connect(lambda *_: self.changed.emit())
        name_col.addWidget(self._name_edit)
        r1.addLayout(name_col, stretch=2)

        cat_col = QVBoxLayout()
        cat_col.setSpacing(3)
        cat_col.addWidget(_field_label("Category"))
        self._cat_edit = _mk_input("e.g. Cell Biology, Biochemistry")
        self._cat_edit.textChanged.connect(lambda *_: self.changed.emit())
        cat_col.addWidget(self._cat_edit)
        r1.addLayout(cat_col, stretch=1)

        outer.addLayout(r1)

        # Row 2: description
        desc_col = QVBoxLayout()
        desc_col.setSpacing(3)
        desc_col.addWidget(_field_label("Description"))
        self._desc_edit = _mk_textarea("Short description of this protocol…", min_h=52)
        self._desc_edit.textChanged.connect(lambda *_: self.changed.emit())
        desc_col.addWidget(self._desc_edit)
        outer.addLayout(desc_col)

        # Row 3: tags
        tag_col = QVBoxLayout()
        tag_col.setSpacing(4)
        tag_col.addWidget(_field_label("Tags"))

        tag_input_row = QHBoxLayout()
        tag_input_row.setSpacing(6)
        self._tag_input = _mk_input("Add tag…", height=32)
        self._tag_input.setFixedWidth(160)
        self._tag_input.returnPressed.connect(self._on_add_tag)
        add_tag_btn = QPushButton("＋")
        add_tag_btn.setFixedSize(32, 32)
        add_tag_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        add_tag_btn.setStyleSheet(
            f"QPushButton {{ background: {Colors.ACCENT}; color: white;"
            f"  border: none; border-radius: {Radii.LG}px; font-size: 14px; }}"
            f"QPushButton:hover {{ background: {Colors.ACCENT_HOVER}; }}"
        )
        add_tag_btn.clicked.connect(self._on_add_tag)
        tag_input_row.addWidget(self._tag_input)
        tag_input_row.addWidget(add_tag_btn)
        tag_input_row.addStretch()
        tag_col.addLayout(tag_input_row)

        self._tag_row_w = QWidget()
        self._tag_row_w.setStyleSheet("background: transparent;")
        self._tag_flow = QHBoxLayout(self._tag_row_w)
        self._tag_flow.setContentsMargins(0, 0, 0, 0)
        self._tag_flow.setSpacing(4)
        self._tag_flow.addStretch()
        tag_col.addWidget(self._tag_row_w)
        outer.addLayout(tag_col)

    def load(self, proto: dict) -> None:
        self.blockSignals(True)
        try:
            self._name_edit.setText(proto.get("name", ""))
            self._cat_edit.setText(proto.get("category", ""))
            self._desc_edit.setPlainText(proto.get("description", ""))
            # Clear chips
            for chip in list(self._tag_chips):
                chip.deleteLater()
            self._tag_chips.clear()
            for tag in proto.get("tags", []):
                self._add_chip(tag, emit=False)
        finally:
            self.blockSignals(False)

    def collect(self) -> tuple[str, str, str, list[str]]:
        """Return (name, category, description, tags)."""
        name  = self._name_edit.text().strip()
        cat   = self._cat_edit.text().strip()
        desc  = self._desc_edit.toPlainText().strip()
        tags  = [c.tag() for c in self._tag_chips]
        return name, cat, desc, tags

    def _on_add_tag(self) -> None:
        tag = self._tag_input.text().strip().lstrip("#")
        if not tag:
            return
        # Avoid duplicates
        if any(c.tag() == tag for c in self._tag_chips):
            self._tag_input.clear()
            return
        self._add_chip(tag, emit=True)
        self._tag_input.clear()

    def _add_chip(self, tag: str, emit: bool = True) -> None:
        chip = _TagChip(tag, parent=self._tag_row_w)
        chip.removed.connect(self._on_remove_tag)
        self._tag_chips.append(chip)
        # Insert before the stretch
        idx = self._tag_flow.count() - 1
        self._tag_flow.insertWidget(idx, chip)
        if emit:
            self.changed.emit()

    def _on_remove_tag(self, chip: _TagChip) -> None:
        if chip in self._tag_chips:
            self._tag_chips.remove(chip)
        self._tag_flow.removeWidget(chip)
        chip.deleteLater()
        self.changed.emit()


# ── EditorPage ────────────────────────────────────────────────────────────────

class EditorPage(BasePage):
    """Full Protocol Editor — Phase 6."""

    def __init__(self, app: "BenchFlowApp", parent: QWidget | None = None) -> None:  # type: ignore[name-defined]
        super().__init__(app, parent)
        self._proto: dict | None    = None   # working copy
        self._selected_idx: int     = -1
        self._step_rows: list[_StepRow] = []
        self._dirty: bool           = False

        self._build()
        self._subscribe_events()

    # ── EventBus ──────────────────────────────────────────────────────────────

    def _subscribe_events(self) -> None:
        bus.subscribe("protocol_updated", self._on_external_update)

    def _on_external_update(self, protocol_id: str = "", **_kw) -> None:
        """If the currently open protocol was updated externally, reload."""
        if (self._proto and protocol_id == self._proto.get("id")
                and not self._dirty):
            self._reload_proto()

    # ── UI construction ───────────────────────────────────────────────────────

    def _build(self) -> None:
        outer = QVBoxLayout()
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # ── Top bar ───────────────────────────────────────────────────────────
        bar = QWidget()
        bar.setStyleSheet(f"background: {Colors.BG_PAGE};")
        bar.setFixedHeight(60)
        bar_lay = QHBoxLayout(bar)
        bar_lay.setContentsMargins(24, 0, 24, 0)
        bar_lay.setSpacing(12)

        self._back_btn = QPushButton("← Library")
        self._back_btn.setFixedHeight(34)
        self._back_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._back_btn.setStyleSheet(
            f"QPushButton {{ background: transparent; color: {Colors.ACCENT};"
            f"  border: none; font-size: {Fonts.SIZE_SM}px; font-weight: 600; }}"
            f"QPushButton:hover {{ color: {Colors.ACCENT_HOVER}; }}"
        )
        self._back_btn.clicked.connect(self._on_back)
        bar_lay.addWidget(self._back_btn)

        self._proto_title_lbl = QLabel("Protocol Editor")
        self._proto_title_lbl.setStyleSheet(
            f"color: {Colors.TEXT_PRIMARY}; font-size: {Fonts.SIZE_LG}px; font-weight: 700;"
        )
        bar_lay.addWidget(self._proto_title_lbl, stretch=1)

        self._dirty_lbl = QLabel("")
        self._dirty_lbl.setStyleSheet(
            f"color: {Colors.WARNING}; font-size: {Fonts.SIZE_SM}px;"
        )
        bar_lay.addWidget(self._dirty_lbl)

        self._export_btn = QPushButton("📤  Export ▾")
        self._export_btn.setFixedHeight(36)
        self._export_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._export_btn.setToolTip("Export this protocol as JSON, Markdown, or PDF")
        self._export_btn.setStyleSheet(
            f"QPushButton {{ background: {Colors.BG_CARD}; color: {Colors.TEXT_SECOND};"
            f"  border: 1px solid {Colors.BORDER_LIGHT}; border-radius: {Radii.LG}px;"
            f"  font-size: {Fonts.SIZE_SM}px; padding: 0 14px; }}"
            f"QPushButton:hover {{ background: {Colors.BG_CARD_HOV}; }}"
        )
        self._export_btn.clicked.connect(self._on_export)
        bar_lay.addWidget(self._export_btn)

        self._save_btn = PrimaryButton("💾  Save Protocol")
        self._save_btn.setFixedHeight(36)
        self._save_btn.setMinimumWidth(150)
        self._save_btn.clicked.connect(self._on_save)
        bar_lay.addWidget(self._save_btn)

        outer.addWidget(bar)
        outer.addWidget(HSeparator())

        # ── Placeholder (shown when no protocol loaded) ───────────────────────
        self._placeholder_w = QWidget()
        ph_lay = QVBoxLayout(self._placeholder_w)
        ph_lay.setAlignment(Qt.AlignmentFlag.AlignCenter)
        ph_lbl = QLabel("Open a protocol from the Library to edit it.")
        ph_lbl.setStyleSheet(
            f"color: {Colors.TEXT_MUTED}; font-size: {Fonts.SIZE_MD}px; font-style: italic;"
        )
        ph_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        ph_lay.addWidget(ph_lbl)
        ph_open = QPushButton("← Go to Library")
        ph_open.setFixedSize(160, 36)
        ph_open.setCursor(Qt.CursorShape.PointingHandCursor)
        ph_open.setStyleSheet(
            f"QPushButton {{ background: {Colors.ACCENT}; color: white;"
            f"  border: none; border-radius: {Radii.LG}px; font-size: {Fonts.SIZE_SM}px; }}"
            f"QPushButton:hover {{ background: {Colors.ACCENT_HOVER}; }}"
        )
        ph_open.clicked.connect(lambda: self.app.navigate("library"))
        ph_lay.addWidget(ph_open, alignment=Qt.AlignmentFlag.AlignHCenter)
        outer.addWidget(self._placeholder_w)

        # ── Editor body ───────────────────────────────────────────────────────
        self._editor_w = QWidget()
        self._editor_w.setStyleSheet(f"background: {Colors.BG_PAGE};")
        editor_lay = QVBoxLayout(self._editor_w)
        editor_lay.setContentsMargins(20, 12, 20, 0)
        editor_lay.setSpacing(10)

        # Meta card
        self._meta_card = _MetaCard()
        self._meta_card.changed.connect(self._on_meta_changed)
        editor_lay.addWidget(self._meta_card)

        # Splitter: step list | step form
        self._splitter = QSplitter(Qt.Orientation.Horizontal)
        self._splitter.setStyleSheet(
            f"QSplitter::handle {{ background: {Colors.BORDER_LIGHT}; width: 1px; }}"
        )

        # ── Left: step list ───────────────────────────────────────────────────
        left_w = QWidget()
        left_w.setStyleSheet(f"background: {Colors.BG_PAGE};")
        left_lay = QVBoxLayout(left_w)
        left_lay.setContentsMargins(0, 0, 0, 0)
        left_lay.setSpacing(6)

        step_hdr = QHBoxLayout()
        step_hdr.setSpacing(8)
        self._step_count_lbl = QLabel("Steps (0)")
        self._step_count_lbl.setStyleSheet(
            f"color: {Colors.TEXT_PRIMARY}; font-size: {Fonts.SIZE_MD}px; font-weight: 700;"
        )
        step_hdr.addWidget(self._step_count_lbl, stretch=1)
        add_step_btn = QPushButton("＋ Add Step")
        add_step_btn.setFixedHeight(32)
        add_step_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        add_step_btn.setStyleSheet(
            f"QPushButton {{ background: {Colors.ACCENT}; color: white;"
            f"  border: none; border-radius: {Radii.LG}px;"
            f"  font-size: {Fonts.SIZE_SM}px; font-weight: 600; padding: 0 12px; }}"
            f"QPushButton:hover {{ background: {Colors.ACCENT_HOVER}; }}"
        )
        add_step_btn.clicked.connect(self._on_add_step)
        step_hdr.addWidget(add_step_btn)
        left_lay.addLayout(step_hdr)

        self._step_scroll = QScrollArea()
        self._step_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._step_scroll.setWidgetResizable(True)
        self._step_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._step_scroll.setStyleSheet(f"background: {Colors.BG_PAGE};")

        self._step_list_w = QWidget()
        self._step_list_w.setStyleSheet(f"background: {Colors.BG_PAGE};")
        self._step_list_lay = QVBoxLayout(self._step_list_w)
        self._step_list_lay.setContentsMargins(0, 0, 4, 0)
        self._step_list_lay.setSpacing(4)
        self._step_list_lay.addStretch()
        self._step_scroll.setWidget(self._step_list_w)
        left_lay.addWidget(self._step_scroll, stretch=1)

        # ── Right: step form ──────────────────────────────────────────────────
        self._step_form = _StepForm()
        self._step_form.changed.connect(self._on_step_form_changed)

        self._splitter.addWidget(left_w)
        self._splitter.addWidget(self._step_form)
        self._splitter.setSizes([320, 540])
        self._splitter.setChildrenCollapsible(False)

        editor_lay.addWidget(self._splitter, stretch=1)
        outer.addWidget(self._editor_w)

        self._root_layout.addLayout(outer)

        # Initial state
        self._editor_w.hide()
        self._placeholder_w.show()

    # ── on_show ───────────────────────────────────────────────────────────────

    def on_show(self) -> None:
        wanted_id = getattr(self.app.state, "selected_protocol_id", "")
        if wanted_id:
            current_id = self._proto.get("id", "") if self._proto else ""
            if wanted_id != current_id and not self._confirm_replace_current_protocol():
                self.app.state.selected_protocol_id = ""
                if self._proto is None:
                    self._editor_w.hide()
                    self._placeholder_w.show()
                return
            self._load_protocol_by_id(wanted_id)
            self.app.state.selected_protocol_id = ""
        elif self._proto is None:
            # Nothing open — show placeholder
            self._editor_w.hide()
            self._placeholder_w.show()

    # ── Protocol loading ──────────────────────────────────────────────────────

    def _load_protocol_by_id(self, proto_id: str) -> bool:
        all_protos = self.app.data.load_protocols()
        proto = next((p for p in all_protos if p.get("id") == proto_id), None)
        if proto is None:
            ToastManager.show_error(f"Protocol not found: {proto_id}")
            return False
        self._open_proto(proto)
        return True

    def _confirm_replace_current_protocol(self) -> bool:
        """Ask before replacing an editor buffer with unsaved changes."""
        if not self._dirty:
            return True

        dlg = QMessageBox(self)
        dlg.setWindowTitle("Unsaved Changes")
        dlg.setText("You have unsaved changes. Save before opening another protocol?")
        save_btn = dlg.addButton("Save & Open", QMessageBox.ButtonRole.AcceptRole)
        discard_btn = dlg.addButton("Discard", QMessageBox.ButtonRole.DestructiveRole)
        dlg.addButton("Cancel", QMessageBox.ButtonRole.RejectRole)
        dlg.exec()

        clicked = dlg.clickedButton()
        if clicked is save_btn:
            self._on_save()
            return not self._dirty
        if clicked is discard_btn:
            return True
        return False

    def _open_proto(self, proto: dict) -> None:
        self._proto       = copy.deepcopy(proto)
        self._selected_idx = -1
        self._dirty       = False
        self._update_dirty_ui()

        self._meta_card.load(self._proto)
        self._proto_title_lbl.setText(
            self._proto.get("name", "Protocol Editor")
        )
        self._render_steps()
        self._placeholder_w.hide()
        self._editor_w.show()

        # Auto-select first step
        if self._proto.get("steps"):
            self._select_step(0)

    def _reload_proto(self) -> None:
        if self._proto:
            self._load_protocol_by_id(self._proto["id"])

    # ── Step list rendering ───────────────────────────────────────────────────

    def _render_steps(self) -> None:
        """Rebuild the step list widget from self._proto["steps"]."""
        # Remove all rows (keep the stretch)
        while self._step_list_lay.count() > 1:
            item = self._step_list_lay.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        steps = self._proto.get("steps", []) if self._proto else []
        self._step_rows = []

        for i, step in enumerate(steps):
            row = _StepRow(i, step, parent=self._step_list_w)
            row.row_clicked.connect(self._select_step)
            row.move_up.connect(self._on_move_up)
            row.move_down.connect(self._on_move_down)
            row.duplicate.connect(self._on_duplicate_step)
            row.deleted.connect(self._on_delete_step)
            self._step_rows.append(row)
            self._step_list_lay.insertWidget(i, row)

        n = len(steps)
        self._step_count_lbl.setText(f"Steps ({n})")

        if n == 0:
            lbl = QLabel("No steps yet. Click ＋ Add Step.")
            lbl.setStyleSheet(
                f"color: {Colors.TEXT_MUTED}; font-size: {Fonts.SIZE_SM}px;"
                f"font-style: italic; padding: 8px;"
            )
            self._step_list_lay.insertWidget(0, lbl)

    # ── Step selection ────────────────────────────────────────────────────────

    def _select_step(self, idx: int) -> None:
        """Commit any pending form changes, then show form for step at idx."""
        if self._proto is None:
            return

        # Commit previous edits
        if self._selected_idx >= 0:
            self._flush_form_to_step(self._selected_idx)

        steps = self._proto.get("steps", [])
        if not (0 <= idx < len(steps)):
            return

        # Update selection highlight
        for i, row in enumerate(self._step_rows):
            row.set_selected(i == idx)

        self._selected_idx = idx
        self._step_form.load_step(steps[idx])

    def _flush_form_to_step(self, idx: int) -> None:
        """Write form widget values back into the step dict."""
        if self._proto is None:
            return
        steps = self._proto.get("steps", [])
        if 0 <= idx < len(steps):
            updated = self._step_form.collect()
            if updated:
                steps[idx] = updated

    # ── Dirty state ───────────────────────────────────────────────────────────

    def _mark_dirty(self) -> None:
        self._dirty = True
        self._update_dirty_ui()

    def _mark_clean(self) -> None:
        self._dirty = False
        self._update_dirty_ui()

    def _update_dirty_ui(self) -> None:
        if self._dirty:
            self._dirty_lbl.setText("● Unsaved changes")
            self._save_btn.setStyleSheet(
                f"QPushButton {{ background: {Colors.ACCENT}; color: white;"
                f"  border: none; border-radius: {Radii.LG}px;"
                f"  font-size: {Fonts.SIZE_MD}px; font-weight: 600; padding: 8px 20px; }}"
                f"QPushButton:hover {{ background: {Colors.ACCENT_HOVER}; }}"
            )
        else:
            self._dirty_lbl.setText("")
            self._save_btn.setStyleSheet(
                f"QPushButton {{ background: {Colors.BG_CARD}; color: {Colors.TEXT_SECOND};"
                f"  border: 1px solid {Colors.BORDER_LIGHT}; border-radius: {Radii.LG}px;"
                f"  font-size: {Fonts.SIZE_MD}px; padding: 8px 20px; }}"
                f"QPushButton:hover {{ background: {Colors.BG_CARD_HOV};"
                f"  color: {Colors.TEXT_PRIMARY}; }}"
            )

    # ── Event handlers ────────────────────────────────────────────────────────

    def _on_meta_changed(self) -> None:
        if self._proto is None:
            return
        name, cat, desc, tags = self._meta_card.collect()
        self._proto["name"]        = name
        self._proto["category"]    = cat
        self._proto["description"] = desc
        self._proto["tags"]        = tags
        self._proto_title_lbl.setText(name or "Protocol Editor")
        self._mark_dirty()

    def _on_step_form_changed(self) -> None:
        self._mark_dirty()
        # Live-update the step row label
        if self._selected_idx >= 0 and self._proto:
            steps = self._proto.get("steps", [])
            if 0 <= self._selected_idx < len(steps):
                updated = self._step_form.collect()
                if updated:
                    steps[self._selected_idx] = updated
                    # Rebuild just this row (cheaper than full re-render)
                    self._refresh_step_row(self._selected_idx)

    def _refresh_step_row(self, idx: int) -> None:
        """Replace the visual row at idx without rebuilding all rows."""
        if not (0 <= idx < len(self._step_rows)):
            return
        old_row = self._step_rows[idx]
        steps   = self._proto.get("steps", [])
        if not (0 <= idx < len(steps)):
            return

        new_row = _StepRow(idx, steps[idx], parent=self._step_list_w)
        new_row.row_clicked.connect(self._select_step)
        new_row.move_up.connect(self._on_move_up)
        new_row.move_down.connect(self._on_move_down)
        new_row.duplicate.connect(self._on_duplicate_step)
        new_row.deleted.connect(self._on_delete_step)
        new_row.set_selected(True)

        self._step_list_lay.replaceWidget(old_row, new_row)
        old_row.deleteLater()
        self._step_rows[idx] = new_row

    def _on_add_step(self) -> None:
        if self._proto is None:
            return
        # Flush current step
        if self._selected_idx >= 0:
            self._flush_form_to_step(self._selected_idx)

        new_step: dict[str, Any] = {
            "id":                 str(uuid.uuid4()),
            "order":              len(self._proto.get("steps", [])),
            "title":              "",
            "type":               "preparation",
            "description":        "",
            "notes":              "",
            "warnings":           "",
            "handsOnMinutes":     0.0,
            "waitMinutes":        0.0,
            "bufferMinutes":      0.0,
            "temperature":        "",
            "centrifugeCondition": "",
            "shakingRotation":    "",
            "reagents":           [],
            "equipment":          [],
            "checklist":          [],
            "substeps":           [],
        }
        self._proto.setdefault("steps", []).append(new_step)
        self._render_steps()
        self._select_step(len(self._proto["steps"]) - 1)
        # Scroll to bottom
        self._step_scroll.verticalScrollBar().setValue(
            self._step_scroll.verticalScrollBar().maximum()
        )
        self._mark_dirty()

    def _on_move_up(self, idx: int) -> None:
        if self._proto is None or idx <= 0:
            return
        self._flush_form_to_step(self._selected_idx)
        steps = self._proto["steps"]
        steps[idx - 1], steps[idx] = steps[idx], steps[idx - 1]
        self._reorder_steps()
        new_idx = idx - 1
        self._render_steps()
        self._select_step(new_idx)
        self._mark_dirty()

    def _on_move_down(self, idx: int) -> None:
        if self._proto is None:
            return
        steps = self._proto.get("steps", [])
        if idx >= len(steps) - 1:
            return
        self._flush_form_to_step(self._selected_idx)
        steps[idx], steps[idx + 1] = steps[idx + 1], steps[idx]
        self._reorder_steps()
        new_idx = idx + 1
        self._render_steps()
        self._select_step(new_idx)
        self._mark_dirty()

    def _on_duplicate_step(self, idx: int) -> None:
        if self._proto is None:
            return
        self._flush_form_to_step(self._selected_idx)
        steps = self._proto.get("steps", [])
        if not (0 <= idx < len(steps)):
            return
        dup = copy.deepcopy(steps[idx])
        dup["id"] = str(uuid.uuid4())
        dup["title"] = f"{dup.get('title', 'Step')} (copy)"
        steps.insert(idx + 1, dup)
        self._reorder_steps()
        self._render_steps()
        self._select_step(idx + 1)
        self._mark_dirty()

    def _on_delete_step(self, idx: int) -> None:
        if self._proto is None:
            return
        steps = self._proto.get("steps", [])
        if not (0 <= idx < len(steps)):
            return
        title = steps[idx].get("title", f"Step {idx+1}")

        dlg = QMessageBox(self)
        dlg.setWindowTitle("Delete Step")
        dlg.setText(f"Delete  <b>{title}</b>?")
        dlg.setTextFormat(Qt.TextFormat.RichText)
        del_btn = dlg.addButton("Delete", QMessageBox.ButtonRole.DestructiveRole)
        dlg.addButton("Cancel", QMessageBox.ButtonRole.RejectRole)
        dlg.exec()
        if dlg.clickedButton() is not del_btn:
            return

        steps.pop(idx)
        self._reorder_steps()

        # Pick new selection
        new_idx = min(idx, len(steps) - 1)
        self._selected_idx = -1
        self._render_steps()
        if new_idx >= 0:
            self._select_step(new_idx)
        else:
            # No steps left — show placeholder in form
            self._step_form._clear()
            self._step_form._show_placeholder()
        self._mark_dirty()

    def _reorder_steps(self) -> None:
        """Update the `order` field on each step after a reorder/delete."""
        for i, step in enumerate(self._proto.get("steps", [])):
            step["order"] = i

    # ── Save ──────────────────────────────────────────────────────────────────

    def _on_save(self) -> None:
        if self._proto is None:
            return

        # Validate name
        name, cat, desc, tags = self._meta_card.collect()
        if not name:
            ToastManager.show_error("Protocol name is required.")
            return

        # Flush current step form
        if self._selected_idx >= 0:
            self._flush_form_to_step(self._selected_idx)

        # Apply meta
        self._proto["name"]        = name
        self._proto["category"]    = cat
        self._proto["description"] = desc
        self._proto["tags"]        = tags
        self._proto["updatedAt"]   = int(time.time() * 1000)

        # Write to disk
        all_protos = self.app.data.load_protocols()
        proto_id   = self._proto.get("id", "")
        replaced   = False
        for i, p in enumerate(all_protos):
            if p.get("id") == proto_id:
                all_protos[i] = self._proto
                replaced = True
                break
        if not replaced:
            # New protocol (opened without pre-existing save)
            all_protos.insert(0, self._proto)

        self.app.data.save_protocols(all_protos)
        self._mark_clean()

        ToastManager.show_success(f"Saved: {name}")
        bus.emit("protocol_updated", protocol_id=proto_id, name=name)

    # ── Back ──────────────────────────────────────────────────────────────────

    def _on_export(self) -> None:
        if not self._proto:
            ToastManager.show_error("No protocol loaded — nothing to export.")
            return
        from qt_app.services import export_service
        proto = self._proto
        menu = QMenu(self._export_btn)
        menu.setStyleSheet(
            f"QMenu {{ background: {Colors.BG_CARD}; color: {Colors.TEXT_PRIMARY};"
            f"  border: 1px solid {Colors.BORDER_LIGHT}; border-radius: {Radii.MD}px;"
            f"  padding: 4px 0; }}"
            f"QMenu::item {{ padding: 6px 20px; font-size: {Fonts.SIZE_SM}px; }}"
            f"QMenu::item:selected {{ background: {Colors.SELECTED_BG}; color: {Colors.TEXT_PRIMARY}; }}"
        )
        menu.addAction("{ }  JSON").triggered.connect(
            lambda: self._do_export(proto, "json")
        )
        menu.addAction("📄  Markdown").triggered.connect(
            lambda: self._do_export(proto, "md")
        )
        menu.addAction("📋  PDF").triggered.connect(
            lambda: self._do_export(proto, "pdf")
        )
        menu.exec(self._export_btn.mapToGlobal(
            self._export_btn.rect().bottomLeft()
        ))

    def _do_export(self, proto: dict, fmt: str) -> None:
        from qt_app.services import export_service
        default_name = export_service.protocol_default_name(proto, fmt)
        filters = {
            "json": "JSON Files (*.json)",
            "md":   "Markdown Files (*.md)",
            "pdf":  "PDF Files (*.pdf)",
        }
        path, _ = QFileDialog.getSaveFileName(
            self, "Export Protocol", default_name, filters.get(fmt, "All Files (*)")
        )
        if not path:
            return
        try:
            if fmt == "pdf":
                export_service.export_protocol_pdf(proto, path)
            elif fmt == "md":
                export_service.export_protocol_markdown(proto, path)
            else:
                export_service.export_protocol_json(proto, path)
            ToastManager.show_success(f"Exported → {path.split('/')[-1]}")
        except export_service.ExportDependencyError as e:
            ToastManager.show_error(
                f"Missing dependency: {e.dep}. Run: {e.install_cmd}"
            )
        except Exception as exc:  # noqa: BLE001
            ToastManager.show_error(f"Export failed: {exc}")

    def _on_back(self) -> None:
        if self._dirty:
            dlg = QMessageBox(self)
            dlg.setWindowTitle("Unsaved Changes")
            dlg.setText("You have unsaved changes. Save before leaving?")
            save_btn   = dlg.addButton("Save & Leave",
                                       QMessageBox.ButtonRole.AcceptRole)
            discard_btn = dlg.addButton("Discard",
                                        QMessageBox.ButtonRole.DestructiveRole)
            dlg.addButton("Cancel", QMessageBox.ButtonRole.RejectRole)
            dlg.exec()
            clicked = dlg.clickedButton()
            if clicked is save_btn:
                self._on_save()
            elif clicked is discard_btn:
                pass   # fall through to navigate
            else:
                return  # Cancel — stay on editor
        self.app.navigate("library")
