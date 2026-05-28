"""
Protocol Library page — Phase 5: full management hub.

Layout
------
Page
├── Header (title, subtitle, + New Protocol)
├── Toolbar (search, category filter, sort)
├── HSeparator
└── QSplitter
    ├── Left: scrollable list
    │   ├── My Protocols section
    │   │   └── _ProtocolCard × N
    │   └── Built-in Templates section
    │       └── _ProtocolCard × N  (read-only, template badges)
    └── Right: detail panel (_DetailPanel)
        ├── Placeholder (nothing selected)
        └── Protocol / Template detail with action buttons

Actions
-------
Protocol:  Duplicate  Delete  Open in Run Mode  Schedule
Template:  Use Template (copy → My Protocols)   Duplicate as Protocol
Phase 6:   Edit (opens Protocol Editor — stub for now)
"""
from __future__ import annotations

import copy
import time
import uuid
from datetime import datetime
from typing import Any

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QComboBox, QFrame, QHBoxLayout, QLabel, QLineEdit,
    QMenu, QMessageBox, QPushButton, QScrollArea,
    QSizePolicy, QSplitter, QVBoxLayout, QWidget,
)

from qt_app.theme import Colors, Fonts, Radii
from qt_app.components.widgets import (
    HSeparator, PageTitle, PrimaryButton, SubLabel,
)
from qt_app.components.toast import ToastManager
from qt_app.services.event_bus import bus
from qt_app.services.data import DataService
from qt_app.services.perf import perf
from qt_app.dialogs.new_protocol import NewProtocolDialog
from qt_app.views.base_page import BasePage


# ── Helpers ───────────────────────────────────────────────────────────────────

def _badge(text: str, fg: str, bg: str, parent: QWidget | None = None) -> QLabel:
    lbl = QLabel(text, parent)
    lbl.setStyleSheet(
        f"color: {fg}; background: {bg}; border-radius: 9px;"
        f"padding: 2px 8px; font-size: {Fonts.SIZE_XS}px; font-weight: 600;"
    )
    return lbl


def _label_style(color: str, size: int, bold: bool = False) -> str:
    return (
        f"color: {color}; font-size: {size}px;"
        + ("font-weight: 700;" if bold else "")
    )


def _total_hands_on(proto: dict) -> float:
    return sum(
        float(s.get("handsOnMinutes", s.get("hands_on_minutes", 0)))
        for s in proto.get("steps", [])
    )


def _total_wait(proto: dict) -> float:
    return sum(
        float(s.get("waitMinutes", s.get("wait_minutes", 0)))
        for s in proto.get("steps", [])
    )


def _format_dur(minutes: float) -> str:
    return DataService.format_duration(minutes)


# ── _ProtocolCard ─────────────────────────────────────────────────────────────

class _ProtocolCard(QFrame):
    """Compact card for one protocol or template."""

    clicked = Signal(dict, bool)   # (protocol_dict, is_template)

    def __init__(self, proto: dict, is_template: bool = False,
                 parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._proto       = proto
        self._is_template = is_template
        self._sel         = False
        self.setObjectName("ProtocolCard")
        self.setStyleSheet(self._style(False))
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._build()

    @staticmethod
    def _style(selected: bool) -> str:
        if selected:
            return (
                f"QFrame#ProtocolCard {{ background: {Colors.SELECTED_BG};"
                f"  border-radius: {Radii.LG}px;"
                f"  border: 1px solid {Colors.BORDER_LIGHT};"
                f"  border-left: 3px solid {Colors.ACCENT}; }}"
                f"QFrame#ProtocolCard:hover {{ background: {Colors.SELECTED_BG}; }}"
            )
        return (
            f"QFrame#ProtocolCard {{ background: {Colors.BG_CARD};"
            f"  border-radius: {Radii.LG}px;"
            f"  border: 1px solid {Colors.BORDER_LIGHT}; }}"
            f"QFrame#ProtocolCard:hover {{ background: {Colors.HOVER_BG};"
            f"  border-color: {Colors.BORDER}; }}"
        )

    def _build(self) -> None:
        p   = self._proto
        lay = QVBoxLayout(self)
        lay.setContentsMargins(16, 13, 16, 13)
        lay.setSpacing(6)

        # Row 1: name + duration
        r1 = QHBoxLayout()
        r1.setSpacing(6)
        name_lbl = QLabel(p.get("name", "Untitled"))
        name_lbl.setStyleSheet(_label_style(Colors.TEXT_PRIMARY, Fonts.SIZE_MD, bold=True))
        name_lbl.setWordWrap(False)
        r1.addWidget(name_lbl, stretch=1)

        total = DataService.protocol_total_minutes(p)
        dur_lbl = QLabel(_format_dur(total))
        dur_lbl.setStyleSheet(_label_style(Colors.TEXT_MUTED, Fonts.SIZE_SM))
        r1.addWidget(dur_lbl)
        lay.addLayout(r1)

        # Row 2: category + steps + template badge
        r2 = QHBoxLayout()
        r2.setSpacing(6)
        cat = p.get("category", "")
        if cat:
            r2.addWidget(_badge(cat, Colors.ACCENT, Colors.ACCENT_BG))
        n = len(p.get("steps", []))
        r2.addWidget(_badge(f"{n} step{'s' if n!=1 else ''}", Colors.TEXT_SECOND, Colors.BG_SURFACE_ALT))
        if self._is_template:
            r2.addWidget(_badge("Template", Colors.WARNING, Colors.WARNING_BG))
        r2.addStretch()
        lay.addLayout(r2)

        # Row 3: tags (up to 3)
        tags = p.get("tags", [])
        if tags:
            r3 = QHBoxLayout()
            r3.setSpacing(4)
            for tag in tags[:3]:
                r3.addWidget(_badge(f"#{tag}", Colors.TEXT_SECOND, Colors.BG_SURFACE_ALT))
            if len(tags) > 3:
                r3.addWidget(_badge(f"+{len(tags)-3}", Colors.TEXT_SECOND, Colors.BG_SURFACE_ALT))
            r3.addStretch()
            lay.addLayout(r3)

    def set_selected(self, sel: bool) -> None:
        self._sel = sel
        self.setStyleSheet(self._style(sel))

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self._proto, self._is_template)
        super().mousePressEvent(event)


# ── _DetailPanel ──────────────────────────────────────────────────────────────

class _DetailPanel(QWidget):
    """Right-side panel: shows protocol detail + actions."""

    # Signals back to LibraryPage
    run_requested           = Signal(dict)   # protocol dict
    schedule_requested      = Signal(dict)
    duplicate_requested     = Signal(dict)
    delete_requested        = Signal(dict)
    use_template_requested  = Signal(dict)
    edit_requested          = Signal(dict)   # opens Protocol Editor (Phase 6)
    flowchart_requested     = Signal(dict)   # opens Flowchart (Phase 8A)
    export_requested        = Signal(dict, str)  # (protocol, fmt) — "json"|"md"|"pdf"

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setMinimumWidth(280)
        self.setStyleSheet(
            f"background: {Colors.BG_CARD};"
            f"border-left: 1px solid {Colors.BORDER_LIGHT};"
        )

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        self._scroll = QScrollArea()
        self._scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._scroll.setWidgetResizable(True)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._scroll.setStyleSheet(f"background: {Colors.BG_CARD};")
        outer.addWidget(self._scroll)

        self._inner = QWidget()
        self._inner.setStyleSheet(f"background: {Colors.BG_CARD};")
        self._lay = QVBoxLayout(self._inner)
        self._lay.setContentsMargins(20, 20, 20, 24)
        self._lay.setSpacing(10)
        self._scroll.setWidget(self._inner)

        self._show_placeholder()

    # ── Public API ────────────────────────────────────────────────────────────

    def show_protocol(self, proto: dict, is_template: bool) -> None:
        self._clear()
        lay = self._lay

        # ── Title row ─────────────────────────────────────────────────────────
        title_lbl = QLabel(proto.get("name", "Untitled"))
        title_lbl.setWordWrap(True)
        title_lbl.setStyleSheet(_label_style(Colors.TEXT_PRIMARY, Fonts.SIZE_LG, bold=True))
        lay.addWidget(title_lbl)

        # Type badge
        if is_template:
            lay.addWidget(_badge("Built-in Template", Colors.WARNING, Colors.WARNING_BG))
        else:
            cat = proto.get("category", "")
            if cat:
                lay.addWidget(_badge(cat, Colors.ACCENT, Colors.ACCENT_BG))

        # Tags
        tags = proto.get("tags", [])
        if tags:
            trow = QHBoxLayout()
            trow.setSpacing(4)
            for t in tags:
                trow.addWidget(_badge(f"#{t}", Colors.TEXT_SECOND, Colors.BG_SURFACE_ALT))
            trow.addStretch()
            lay.addLayout(trow)

        # Description
        desc = proto.get("description", "")
        if desc:
            desc_lbl = QLabel(desc)
            desc_lbl.setWordWrap(True)
            desc_lbl.setStyleSheet(
                f"color: {Colors.TEXT_SECOND}; font-size: {Fonts.SIZE_SM}px;"
                f"font-style: italic;"
            )
            lay.addWidget(desc_lbl)

        lay.addWidget(HSeparator())

        # ── Stats ─────────────────────────────────────────────────────────────
        total  = DataService.protocol_total_minutes(proto)
        hands  = _total_hands_on(proto)
        wait   = _total_wait(proto)
        n_steps = len(proto.get("steps", []))

        stats = [
            ("Steps",     str(n_steps)),
            ("Total",     _format_dur(total)),
            ("Hands-on",  _format_dur(hands)),
            ("Wait",      _format_dur(wait)),
        ]
        for label, val in stats:
            row = QHBoxLayout()
            row.setContentsMargins(0, 0, 0, 0)
            k = QLabel(label)
            k.setStyleSheet(_label_style(Colors.TEXT_MUTED, Fonts.SIZE_XS))
            k.setFixedWidth(70)
            v = QLabel(val)
            v.setStyleSheet(_label_style(Colors.TEXT_PRIMARY, Fonts.SIZE_SM, bold=True))
            row.addWidget(k)
            row.addWidget(v)
            row.addStretch()
            lay.addLayout(row)

        lay.addWidget(HSeparator())

        # ── Steps list ────────────────────────────────────────────────────────
        steps_hdr = QLabel(f"Steps ({n_steps})")
        steps_hdr.setStyleSheet(
            f"color: {Colors.TEXT_SECOND}; font-size: {Fonts.SIZE_XS}px; font-weight: 700;"
        )
        lay.addWidget(steps_hdr)

        for i, step in enumerate(proto.get("steps", [])[:30]):
            s_row = QHBoxLayout()
            s_row.setSpacing(8)
            s_row.setContentsMargins(0, 0, 0, 0)

            num = QLabel(f"{i+1}.")
            num.setFixedWidth(22)
            num.setStyleSheet(_label_style(Colors.TEXT_MUTED, Fonts.SIZE_XS))
            s_row.addWidget(num)

            s_name = QLabel(step.get("title", f"Step {i+1}"))
            s_name.setStyleSheet(_label_style(Colors.TEXT_PRIMARY, Fonts.SIZE_SM))
            s_name.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
            s_row.addWidget(s_name, stretch=1)

            step_total = (
                float(step.get("handsOnMinutes", 0)) +
                float(step.get("waitMinutes", 0)) +
                float(step.get("bufferMinutes", 0))
            )
            if step_total > 0:
                dur_lbl = QLabel(_format_dur(step_total))
                dur_lbl.setStyleSheet(_label_style(Colors.TEXT_MUTED, Fonts.SIZE_XS))
                s_row.addWidget(dur_lbl)

            lay.addLayout(s_row)

        if n_steps > 30:
            more_lbl = QLabel(f"… and {n_steps - 30} more steps")
            more_lbl.setStyleSheet(_label_style(Colors.TEXT_MUTED, Fonts.SIZE_XS))
            lay.addWidget(more_lbl)

        if n_steps == 0:
            empty_lbl = QLabel("No steps yet.")
            empty_lbl.setStyleSheet(
                f"color: {Colors.TEXT_MUTED}; font-size: {Fonts.SIZE_SM}px; font-style: italic;"
            )
            lay.addWidget(empty_lbl)

        lay.addWidget(HSeparator())

        # ── Action buttons ────────────────────────────────────────────────────
        if is_template:
            self._add_action_btn(
                "⊕  Use Template",
                Colors.ACCENT, True,
                lambda p=proto: self.use_template_requested.emit(p),
            )
            self._add_action_btn(
                "⎇  View Flowchart",
                Colors.TEXT_SECOND, False,
                lambda p=proto: self.flowchart_requested.emit(p),
            )
            self._add_action_btn(
                "⧉  Duplicate as Protocol",
                Colors.TEXT_SECOND, False,
                lambda p=proto: self.duplicate_requested.emit(p),
            )
            self._add_export_menu_btn(proto)
        else:
            self._add_action_btn(
                "✎  Edit Protocol",
                Colors.ACCENT, True,
                lambda p=proto: self.edit_requested.emit(p),
            )
            self._add_action_btn(
                "▶  Open in Run Mode",
                Colors.SUCCESS, False,
                lambda p=proto: self.run_requested.emit(p),
            )
            self._add_action_btn(
                "⎇  View Flowchart",
                Colors.TEXT_SECOND, False,
                lambda p=proto: self.flowchart_requested.emit(p),
            )
            self._add_action_btn(
                "🗓  Schedule Experiment",
                Colors.TEXT_SECOND, False,
                lambda p=proto: self.schedule_requested.emit(p),
            )
            self._add_action_btn(
                "⧉  Duplicate",
                Colors.TEXT_SECOND, False,
                lambda p=proto: self.duplicate_requested.emit(p),
            )
            self._add_action_btn(
                "✕  Delete",
                Colors.DANGER, False,
                lambda p=proto: self.delete_requested.emit(p),
            )
            self._add_export_menu_btn(proto)

        lay.addStretch()

    def show_placeholder(self) -> None:
        self._clear()
        self._show_placeholder()

    # ── Internals ─────────────────────────────────────────────────────────────

    def _show_placeholder(self) -> None:
        self._lay.addStretch()
        lbl = QLabel("Select a protocol or template\nto view details and actions.")
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl.setWordWrap(True)
        lbl.setStyleSheet(
            f"color: {Colors.TEXT_MUTED}; font-size: {Fonts.SIZE_SM}px;"
            f"font-style: italic;"
        )
        self._lay.addWidget(lbl)
        self._lay.addStretch()

    def _add_action_btn(self, label: str, color: str, primary: bool,
                        callback) -> None:
        btn = QPushButton(label)
        btn.setFixedHeight(36)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        if primary:
            btn.setStyleSheet(
                f"QPushButton {{ background: {color}; color: white;"
                f"  border: none; border-radius: {Radii.LG}px;"
                f"  font-size: {Fonts.SIZE_SM}px; font-weight: 600; padding: 0 14px; }}"
                f"QPushButton:hover {{ opacity: 0.9; }}"
            )
        else:
            btn.setStyleSheet(
                f"QPushButton {{ background: {Colors.BG_CARD}; color: {color};"
                f"  border: 1px solid {Colors.BORDER_LIGHT}; border-radius: {Radii.LG}px;"
                f"  font-size: {Fonts.SIZE_SM}px; padding: 0 14px; }}"
                f"QPushButton:hover {{ background: {Colors.BG_CARD_HOV}; }}"
            )
        btn.clicked.connect(callback)
        self._lay.addWidget(btn)

    def _add_export_menu_btn(self, proto: dict) -> None:
        btn = QPushButton("📤  Export ▾")
        btn.setFixedHeight(36)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setToolTip("Export this protocol as JSON, Markdown, or PDF")
        btn.setStyleSheet(
            f"QPushButton {{ background: {Colors.BG_CARD}; color: {Colors.TEXT_SECOND};"
            f"  border: 1px solid {Colors.BORDER_LIGHT}; border-radius: {Radii.LG}px;"
            f"  font-size: {Fonts.SIZE_SM}px; padding: 0 14px; }}"
            f"QPushButton:hover {{ background: {Colors.BG_CARD_HOV}; }}"
        )

        def _show_menu():
            menu = QMenu(btn)
            menu.setStyleSheet(
                f"QMenu {{ background: {Colors.BG_CARD}; color: {Colors.TEXT_PRIMARY};"
                f"  border: 1px solid {Colors.BORDER_LIGHT}; border-radius: {Radii.MD}px;"
                f"  padding: 4px 0; }}"
                f"QMenu::item {{ padding: 6px 20px; font-size: {Fonts.SIZE_SM}px; }}"
                f"QMenu::item:selected {{ background: {Colors.SELECTED_BG}; color: {Colors.TEXT_PRIMARY}; }}"
            )
            menu.addAction("{ }  JSON").triggered.connect(
                lambda: self.export_requested.emit(proto, "json")
            )
            menu.addAction("📄  Markdown").triggered.connect(
                lambda: self.export_requested.emit(proto, "md")
            )
            menu.addAction("📋  PDF").triggered.connect(
                lambda: self.export_requested.emit(proto, "pdf")
            )
            menu.exec(btn.mapToGlobal(btn.rect().bottomLeft()))

        btn.clicked.connect(_show_menu)
        self._lay.addWidget(btn)

    def _clear(self) -> None:
        while self._lay.count():
            item = self._lay.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()
            elif item.layout():
                _clear_layout(item.layout())


def _clear_layout(layout) -> None:
    while layout.count():
        item = layout.takeAt(0)
        w = item.widget()
        if w:
            w.deleteLater()
        elif item.layout():
            _clear_layout(item.layout())


# ── LibraryPage ───────────────────────────────────────────────────────────────

_SORT_OPTIONS = [
    ("name_asc",   "Name A→Z"),
    ("name_desc",  "Name Z→A"),
    ("recent",     "Most recent"),
    ("steps_desc", "Most steps"),
    ("steps_asc",  "Fewest steps"),
]


class LibraryPage(BasePage):
    """Protocol Library — full management hub (Phase 5)."""

    def __init__(self, app: "BenchFlowApp", parent: QWidget | None = None) -> None:  # type: ignore[name-defined]
        super().__init__(app, parent)
        self._protocols: list[dict]  = []
        self._templates: list[dict]  = []
        self._filtered_p: list[dict] = []
        self._filtered_t: list[dict] = []
        self._selected_proto: dict | None = None
        self._selected_is_template: bool  = False
        self._cards: list[_ProtocolCard]  = []
        self._search: str = ""
        self._cat:    str = ""
        self._sort:   str = "recent"

        self._build()
        self._subscribe_events()
        self._load_data()

    # ── EventBus ──────────────────────────────────────────────────────────────

    def _subscribe_events(self) -> None:
        for ev in ("protocol_created", "protocol_updated", "protocol_deleted"):
            bus.subscribe(ev, self._on_data_changed)

    def _on_data_changed(self, **_kw) -> None:
        if self.isVisible():
            self._load_data()
        # else on_show will call _load_data

    # ── UI shell ──────────────────────────────────────────────────────────────

    def _build(self) -> None:
        outer = QVBoxLayout()
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # ── Header ────────────────────────────────────────────────────────────
        hdr = QWidget()
        hdr.setStyleSheet(f"background: {Colors.BG_PAGE};")
        hdr_lay = QHBoxLayout(hdr)
        hdr_lay.setContentsMargins(28, 20, 28, 12)
        hdr_lay.setSpacing(8)

        col = QVBoxLayout()
        col.setSpacing(2)
        col.addWidget(PageTitle("Protocol Library"))
        col.addWidget(SubLabel("Manage your protocols and built-in templates."))
        hdr_lay.addLayout(col)
        hdr_lay.addStretch()

        new_btn = PrimaryButton("＋ New Protocol")
        new_btn.setMinimumWidth(130)
        new_btn.clicked.connect(self._on_new_protocol)
        hdr_lay.addWidget(new_btn)
        outer.addWidget(hdr)

        # ── Toolbar ───────────────────────────────────────────────────────────
        toolbar = QWidget()
        toolbar.setStyleSheet(f"background: {Colors.BG_PAGE};")
        tb_lay = QHBoxLayout(toolbar)
        tb_lay.setContentsMargins(28, 0, 28, 12)
        tb_lay.setSpacing(8)

        self._search_box = QLineEdit()
        self._search_box.setPlaceholderText("🔍  Search protocols…")
        self._search_box.setFixedHeight(34)
        self._search_box.setStyleSheet(
            f"QLineEdit {{ background: {Colors.BG_INPUT}; color: {Colors.TEXT_PRIMARY};"
            f"  border: 1px solid {Colors.BORDER_LIGHT}; border-radius: {Radii.LG}px;"
            f"  padding: 0 12px; font-size: {Fonts.SIZE_SM}px; }}"
            f"QLineEdit:focus {{ border-color: {Colors.ACCENT}; }}"
        )
        self._search_box.textChanged.connect(self._on_search_changed)
        tb_lay.addWidget(self._search_box, stretch=1)

        self._cat_cb = self._toolbar_combo()
        self._cat_cb.addItem("All Categories", userData="")
        self._cat_cb.currentIndexChanged.connect(self._on_cat_changed)
        tb_lay.addWidget(self._cat_cb)

        self._sort_cb = self._toolbar_combo()
        for val, label in _SORT_OPTIONS:
            self._sort_cb.addItem(label, userData=val)
        self._sort_cb.setCurrentIndex(2)  # Most recent
        self._sort_cb.currentIndexChanged.connect(self._on_sort_changed)
        tb_lay.addWidget(self._sort_cb)

        outer.addWidget(toolbar)
        outer.addWidget(HSeparator())

        # ── Splitter ──────────────────────────────────────────────────────────
        self._splitter = QSplitter(Qt.Orientation.Horizontal)
        self._splitter.setStyleSheet(
            f"QSplitter::handle {{ background: {Colors.BORDER}; width: 1px; }}"
        )

        # ── Left: list panel ──────────────────────────────────────────────────
        list_w = QWidget()
        list_w.setStyleSheet(f"background: {Colors.BG_PAGE};")
        list_lay = QVBoxLayout(list_w)
        list_lay.setContentsMargins(0, 0, 0, 0)
        list_lay.setSpacing(0)

        self._list_scroll = QScrollArea()
        self._list_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._list_scroll.setWidgetResizable(True)
        self._list_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._list_scroll.setStyleSheet(f"background: {Colors.BG_PAGE};")

        self._list_content = QWidget()
        self._list_content.setStyleSheet(f"background: {Colors.BG_PAGE};")
        self._list_layout = QVBoxLayout(self._list_content)
        self._list_layout.setContentsMargins(20, 16, 12, 24)
        self._list_layout.setSpacing(0)
        self._list_scroll.setWidget(self._list_content)
        list_lay.addWidget(self._list_scroll, stretch=1)

        # ── Right: detail panel ───────────────────────────────────────────────
        self._detail = _DetailPanel()
        self._detail.run_requested.connect(self._on_run_mode)
        self._detail.schedule_requested.connect(self._on_schedule)
        self._detail.duplicate_requested.connect(self._on_duplicate)
        self._detail.delete_requested.connect(self._on_delete)
        self._detail.use_template_requested.connect(self._on_use_template)
        self._detail.edit_requested.connect(self._on_edit)
        self._detail.flowchart_requested.connect(self._on_flowchart)
        self._detail.export_requested.connect(self._on_export_protocol)

        self._splitter.addWidget(list_w)
        self._splitter.addWidget(self._detail)
        self._splitter.setSizes([520, 340])
        self._splitter.setChildrenCollapsible(False)

        outer.addWidget(self._splitter, stretch=1)
        self._root_layout.addLayout(outer)

    @staticmethod
    def _toolbar_combo() -> QComboBox:
        cb = QComboBox()
        cb.setFixedHeight(34)
        cb.setMinimumWidth(140)
        cb.setStyleSheet(
            f"QComboBox {{ background: {Colors.BG_INPUT}; color: {Colors.TEXT_PRIMARY};"
            f"  border: 1px solid {Colors.BORDER_LIGHT}; border-radius: {Radii.LG}px;"
            f"  padding: 0 10px; font-size: {Fonts.SIZE_SM}px; }}"
            f"QComboBox:focus {{ border-color: {Colors.ACCENT}; }}"
            f"QComboBox QAbstractItemView {{ background: {Colors.BG_CARD};"
            f"  color: {Colors.TEXT_PRIMARY}; border: 1px solid {Colors.BORDER_LIGHT};"
            f"  selection-background-color: {Colors.SELECTED_BG}; selection-color: {Colors.TEXT_PRIMARY}; }}"
        )
        return cb

    # ── Data loading and filtering ────────────────────────────────────────────

    def _load_data(self) -> None:
        with perf.measure("library_load"):
            self._protocols = self.app.data.load_protocols()
            self._templates = self.app.data.load_templates()

        # Rebuild category combo
        cats: set[str] = set()
        for p in self._protocols + self._templates:
            c = p.get("category", "")
            if c:
                cats.add(c)
        self._cat_cb.blockSignals(True)
        current_cat = self._cat_cb.currentData() or ""
        self._cat_cb.clear()
        self._cat_cb.addItem("All Categories", userData="")
        for c in sorted(cats):
            self._cat_cb.addItem(c, userData=c)
        # Restore selection
        idx = self._cat_cb.findData(current_cat)
        self._cat_cb.setCurrentIndex(max(0, idx))
        self._cat = self._cat_cb.currentData() or ""
        self._cat_cb.blockSignals(False)

        self._apply_filters()

    def _apply_filters(self) -> None:
        q = self._search.lower()
        cat = self._cat

        def match(p: dict) -> bool:
            if q and q not in p.get("name", "").lower():
                if not any(q in t.lower() for t in p.get("tags", [])):
                    if q not in p.get("category", "").lower():
                        return False
            if cat and p.get("category", "") != cat:
                return False
            return True

        self._filtered_p = [p for p in self._protocols if match(p)]
        self._filtered_t = [t for t in self._templates if match(t)]

        self._sort_lists()
        self._render_list()

    def _sort_lists(self) -> None:
        key = self._sort

        def sort_key(p: dict):
            if key == "name_asc":
                return p.get("name", "").lower()
            if key == "name_desc":
                return tuple([-ord(c) for c in p.get("name", "").lower()])
            if key == "recent":
                return -(p.get("updatedAt", p.get("createdAt", 0)))
            if key == "steps_desc":
                return -len(p.get("steps", []))
            if key == "steps_asc":
                return len(p.get("steps", []))
            return p.get("name", "").lower()

        self._filtered_p.sort(key=sort_key)
        self._filtered_t.sort(key=sort_key)

    # ── List rendering ────────────────────────────────────────────────────────

    def _render_list(self) -> None:
        with perf.measure("library_render", threshold_ms=30):
            self._cards.clear()
            while self._list_layout.count():
                item = self._list_layout.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()

            # My Protocols
            self._list_layout.addWidget(
                self._section_header("My Protocols", len(self._filtered_p),
                                     total=len(self._protocols))
            )
            self._list_layout.addSpacing(8)

            if self._filtered_p:
                for p in self._filtered_p:
                    self._add_card(p, is_template=False)
            else:
                empty_msg = (
                    "No protocols match your search."
                    if self._search or self._cat
                    else "No protocols yet.  Click  ＋ New Protocol  to get started."
                )
                self._list_layout.addWidget(self._empty(empty_msg))

            self._list_layout.addSpacing(24)

            # Built-in Templates
            self._list_layout.addWidget(
                self._section_header("Built-in Templates", len(self._filtered_t),
                                     total=len(self._templates))
            )
            self._list_layout.addSpacing(8)

            if self._filtered_t:
                # Group by category
                by_cat: dict[str, list[dict]] = {}
                for t in self._filtered_t:
                    by_cat.setdefault(t.get("category", "Other"), []).append(t)
                for cat, items in sorted(by_cat.items()):
                    cat_lbl = QLabel(cat)
                    cat_lbl.setStyleSheet(
                        f"color: {Colors.TEXT_SECOND}; font-size: {Fonts.SIZE_XS}px;"
                        f"font-weight: 700; letter-spacing: 0.5px;"
                    )
                    self._list_layout.addWidget(cat_lbl)
                    self._list_layout.addSpacing(4)
                    for t in items:
                        self._add_card(t, is_template=True)
                    self._list_layout.addSpacing(12)
            else:
                self._list_layout.addWidget(self._empty("No templates match your search."))

            self._list_layout.addStretch()

        # Re-select if something was selected before
        if self._selected_proto:
            for card in self._cards:
                if (card._proto.get("id") == self._selected_proto.get("id")
                        and card._is_template == self._selected_is_template):
                    card.set_selected(True)
                    break

    def _add_card(self, proto: dict, is_template: bool) -> None:
        card = _ProtocolCard(proto, is_template=is_template, parent=self._list_content)
        card.clicked.connect(self._on_card_clicked)
        self._cards.append(card)
        self._list_layout.addWidget(card)
        self._list_layout.addSpacing(6)

    @staticmethod
    def _section_header(title: str, count: int, total: int = -1) -> QWidget:
        w = QWidget()
        lay = QHBoxLayout(w)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(8)
        lbl = QLabel(title)
        lbl.setStyleSheet(
            f"color: {Colors.TEXT_PRIMARY}; font-size: {Fonts.SIZE_LG}px; font-weight: 700;"
        )
        lay.addWidget(lbl)
        count_text = str(count) if (total < 0 or count == total) else f"{count}/{total}"
        cnt = QLabel(count_text)
        cnt.setStyleSheet(
            f"color: {Colors.ACCENT}; background: {Colors.ACCENT_BG};"
            f"border-radius: 8px; padding: 2px 10px;"
            f"font-size: {Fonts.SIZE_SM}px; font-weight: 700;"
        )
        lay.addWidget(cnt)
        lay.addStretch()
        return w

    @staticmethod
    def _empty(msg: str) -> QWidget:
        w = QWidget()
        lay = QHBoxLayout(w)
        lay.setContentsMargins(0, 4, 0, 4)
        lbl = QLabel(msg)
        lbl.setStyleSheet(
            f"color: {Colors.TEXT_MUTED}; font-size: {Fonts.SIZE_SM}px; font-style: italic;"
        )
        lay.addWidget(lbl)
        lay.addStretch()
        return w

    # ── Filter / sort handlers ────────────────────────────────────────────────

    def _on_search_changed(self, text: str) -> None:
        self._search = text
        self._apply_filters()

    def _on_cat_changed(self, _idx: int) -> None:
        self._cat = self._cat_cb.currentData() or ""
        self._apply_filters()

    def _on_sort_changed(self, _idx: int) -> None:
        self._sort = self._sort_cb.currentData() or "recent"
        self._apply_filters()

    # ── Card selection ────────────────────────────────────────────────────────

    def _on_card_clicked(self, proto: dict, is_template: bool) -> None:
        # Deselect previous
        for card in self._cards:
            card.set_selected(False)
        # Select clicked
        for card in self._cards:
            if card._proto is proto:
                card.set_selected(True)
                break

        self._selected_proto       = proto
        self._selected_is_template = is_template
        self._detail.show_protocol(proto, is_template)

        # Update AppState
        self.app.state.selected_protocol_id = proto.get("id", "")

    # ── Actions ───────────────────────────────────────────────────────────────

    def _on_new_protocol(self) -> None:
        dlg = NewProtocolDialog(self._protocols, self._templates, parent=self)
        if dlg.exec() != NewProtocolDialog.DialogCode.Accepted:
            return
        proto = dlg.result_dict()
        if not proto:
            return

        protocols = self.app.data.load_protocols()
        protocols.insert(0, proto)
        self.app.data.save_protocols(protocols)

        method = dlg.result_method()
        name   = proto.get("name", "Protocol")
        if method == "blank":
            ToastManager.show_success(f"Created: {name}")
        elif method == "template":
            ToastManager.show_success(f"Template copied: {name}")
        else:
            ToastManager.show_success(f"Duplicated: {name}")

        bus.emit("protocol_created", protocol_id=proto["id"], name=name)
        self._load_data()
        # Auto-select the new protocol
        self._selected_proto       = proto
        self._selected_is_template = False
        self._detail.show_protocol(proto, False)

        # For blank protocols, jump straight into the editor
        if method == "blank":
            self.app.state.selected_protocol_id = proto["id"]
            self.app.navigate("editor")

    def _on_use_template(self, tmpl: dict) -> None:
        """Copy template → new editable protocol in My Protocols."""
        import copy, time, uuid
        now  = int(time.time() * 1000)
        dup  = copy.deepcopy(tmpl)
        dup["id"]        = str(uuid.uuid4())
        dup["createdAt"] = now
        dup["updatedAt"] = now
        for step in dup.get("steps", []):
            step["id"] = str(uuid.uuid4())

        protocols = self.app.data.load_protocols()
        protocols.insert(0, dup)
        self.app.data.save_protocols(protocols)

        name = dup.get("name", "Protocol")
        ToastManager.show_success(f"Template copied to My Protocols: {name}")
        bus.emit("protocol_created", protocol_id=dup["id"], name=name)
        self._load_data()
        # Select the new protocol
        self._selected_proto       = dup
        self._selected_is_template = False
        self._detail.show_protocol(dup, False)

    def _on_duplicate(self, proto: dict) -> None:
        import copy, time, uuid
        now  = int(time.time() * 1000)
        dup  = copy.deepcopy(proto)
        dup["id"]        = str(uuid.uuid4())
        dup["name"]      = f"Copy of {proto.get('name', 'Protocol')}"
        dup["createdAt"] = now
        dup["updatedAt"] = now
        for step in dup.get("steps", []):
            step["id"] = str(uuid.uuid4())

        protocols = self.app.data.load_protocols()
        protocols.insert(0, dup)
        self.app.data.save_protocols(protocols)

        name = dup.get("name", "")
        ToastManager.show_success(f"Duplicated: {name}")
        bus.emit("protocol_created", protocol_id=dup["id"], name=name)
        self._load_data()

    def _on_delete(self, proto: dict) -> None:
        name = proto.get("name", "this protocol")
        dlg = QMessageBox(self)
        dlg.setWindowTitle("Delete Protocol")
        dlg.setText(f"Delete  <b>{name}</b>?")
        dlg.setInformativeText("This cannot be undone.")
        dlg.setTextFormat(Qt.TextFormat.RichText)
        del_btn = dlg.addButton("Delete", QMessageBox.ButtonRole.DestructiveRole)
        dlg.addButton("Cancel", QMessageBox.ButtonRole.RejectRole)
        dlg.exec()
        if dlg.clickedButton() is not del_btn:
            return

        proto_id = proto.get("id", "")
        protocols = [p for p in self.app.data.load_protocols() if p.get("id") != proto_id]
        self.app.data.save_protocols(protocols)

        ToastManager.show_info(f"Deleted: {name}")
        bus.emit("protocol_deleted", protocol_id=proto_id)

        self._selected_proto = None
        self._detail.show_placeholder()
        self._load_data()

    def _on_edit(self, proto: dict) -> None:
        proto_id = proto.get("id", "")
        if not proto_id:
            ToastManager.show_error("Cannot edit this protocol: missing protocol ID.")
            return
        self.app.state.selected_protocol_id = proto_id
        self.app.navigate("editor")

    def _on_flowchart(self, proto: dict) -> None:
        self.app.state.selected_protocol_id = proto.get("id", "")
        self.app.navigate("flowchart")

    def _on_run_mode(self, proto: dict) -> None:
        self.app.state.selected_protocol_id = proto.get("id", "")
        self.app.navigate("run")

    def _on_schedule(self, proto: dict) -> None:
        self.app.state.selected_protocol_id = proto.get("id", "")
        self.app.navigate("schedule")

    def _on_export_protocol(self, proto: dict, fmt: str) -> None:
        from PySide6.QtWidgets import QFileDialog
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

    # ── on_show ───────────────────────────────────────────────────────────────

    def on_show(self) -> None:
        self._load_data()
        # Restore detail panel if there was a selection
        if self._selected_proto:
            self._detail.show_protocol(
                self._selected_proto, self._selected_is_template
            )
