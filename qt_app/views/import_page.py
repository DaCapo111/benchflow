"""
Import Page — Phase 8B.

Layout
------
ImportPage
├── Header: title + subtitle + ← Library
├── HSeparator
└── QSplitter (horizontal)
    ├── Left: method selector cards
    │   ├── 📁 JSON File   (active)
    │   ├── 📋 Paste Text  (active)
    │   ├── 📄 PDF         (coming soon)
    │   └── 📝 Word Doc    (coming soon)
    └── Right: QSplitter (vertical)
        ├── method input panel (stacked)
        └── _PreviewPanel  — name (editable) + steps + [Save to My Protocols]

Imported protocols land in My Protocols via DataService.
"""
from __future__ import annotations

import copy
import json
import re
import time
import uuid

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFileDialog, QFrame, QHBoxLayout, QLabel,
    QPlainTextEdit, QPushButton, QScrollArea,
    QSizePolicy, QSplitter, QStackedWidget,
    QVBoxLayout, QWidget, QLineEdit,
)

from qt_app.theme import Colors, Fonts, Radii
from qt_app.components.widgets import (
    HSeparator, PageTitle, PrimaryButton, SubLabel,
)
from qt_app.components.toast import ToastManager
from qt_app.services.event_bus import bus
from qt_app.views.base_page import BasePage


# ── Helpers ───────────────────────────────────────────────────────────────────

def _lbl(text: str, color: str = Colors.TEXT_PRIMARY,
         size: int = Fonts.SIZE_SM, bold: bool = False,
         wrap: bool = False) -> QLabel:
    lbl = QLabel(text)
    weight = "700" if bold else "400"
    lbl.setStyleSheet(
        f"color: {color}; font-size: {size}px; font-weight: {weight};"
    )
    if wrap:
        lbl.setWordWrap(True)
    return lbl


def _parse_json_protocol(text: str) -> "dict | None":
    """Try to extract a protocol dict from JSON text."""
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return None
    if isinstance(data, dict):
        # Accept {"protocol": {...}} wrapper from export_service
        if "protocol" in data and isinstance(data["protocol"], dict):
            return data["protocol"]
        # Bare protocol
        if "name" in data or "steps" in data:
            return data
    return None


def _parse_text_protocol(text: str) -> dict:
    """
    Simple line-by-line parser.
    First non-empty line → protocol name.
    Numbered/bulleted lines → step titles.
    """
    lines = [ln.strip() for ln in text.strip().splitlines() if ln.strip()]
    title = lines[0] if lines else "Imported Protocol"

    steps: list[dict] = []
    step_pat = re.compile(r"^(?:\d+[\.\):\s]|[-•*]\s)")
    for line in lines[1:]:
        if step_pat.match(line):
            clean = step_pat.sub("", line).strip()
            if clean:
                steps.append(_blank_step(clean))

    if not steps and len(lines) > 1:
        for line in lines[1:]:
            steps.append(_blank_step(line))

    now = int(time.time() * 1000)
    return {
        "id":          str(uuid.uuid4()),
        "name":        title,
        "category":    "Imported",
        "description": "",
        "tags":        [],
        "steps":       steps,
        "createdAt":   now,
        "updatedAt":   now,
    }


def _blank_step(title: str) -> dict:
    return {
        "id":             str(uuid.uuid4()),
        "title":          title,
        "type":           "preparation",
        "order":          0,
        "handsOnMinutes": 0,
        "waitMinutes":    0,
        "bufferMinutes":  0,
        "description":    "",
        "notes":          "",
        "warnings":       "",
        "reagents":       [],
        "equipment":      [],
        "checklist":      [],
        "substeps":       [],
    }


def _fix_step_orders(proto: dict) -> None:
    for i, s in enumerate(proto.get("steps", [])):
        s["order"] = i


# ── Method card ───────────────────────────────────────────────────────────────

class _MethodCard(QFrame):
    """Clickable card for the left method selector."""
    clicked = Signal()

    def __init__(self, emoji: str, label: str, subtitle: str,
                 active: bool = True,
                 parent: "QWidget | None" = None) -> None:
        super().__init__(parent)
        self._active = active
        self._selected = False
        self.setCursor(
            Qt.CursorShape.PointingHandCursor if active
            else Qt.CursorShape.ForbiddenCursor
        )
        self.setFixedHeight(72)

        lay = QHBoxLayout(self)
        lay.setContentsMargins(14, 10, 14, 10)
        lay.setSpacing(12)

        icon_lbl = QLabel(emoji)
        icon_lbl.setFixedWidth(32)
        icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_lbl.setStyleSheet("font-size: 22px; background: transparent;")
        lay.addWidget(icon_lbl)

        col = QVBoxLayout()
        col.setSpacing(2)
        self._name_lbl = QLabel(label)
        col.addWidget(self._name_lbl)
        sub_lbl = QLabel(subtitle)
        sub_lbl.setStyleSheet(
            f"color: {Colors.TEXT_MUTED}; font-size: {Fonts.SIZE_XS}px;"
            f"background: transparent;"
        )
        col.addWidget(sub_lbl)
        lay.addLayout(col, stretch=1)

        if not active:
            badge = QLabel("Soon")
            badge.setStyleSheet(
                f"color: {Colors.WARNING}; background: rgba(249,115,22,0.15);"
                f"border-radius: 4px; padding: 2px 6px;"
                f"font-size: {Fonts.SIZE_XS}px; font-weight: 600;"
            )
            lay.addWidget(badge)

        self._update_style()

    def set_selected(self, sel: bool) -> None:
        self._selected = sel
        self._update_style()

    def _update_style(self) -> None:
        if self._selected:
            self.setStyleSheet(
                f"QFrame {{ background: {Colors.SELECTED_BG}; border-radius: {Radii.LG}px;"
                f"  border: 1px solid {Colors.BORDER_LIGHT}; border-left: 3px solid {Colors.ACCENT}; }}"
            )
            self._name_lbl.setStyleSheet(
                f"color: {Colors.TEXT_PRIMARY}; font-size: {Fonts.SIZE_SM}px; font-weight: 600;"
                f"background: transparent;"
            )
        else:
            hover = (f"QFrame:hover {{ background: {Colors.HOVER_BG}; }}"
                     if self._active else "")
            self.setStyleSheet(
                f"QFrame {{ background: {Colors.BG_CARD}; border-radius: {Radii.LG}px;"
                f"  border: 1px solid {Colors.BORDER_LIGHT}; }}" + hover
            )
            self._name_lbl.setStyleSheet(
                f"color: {Colors.TEXT_PRIMARY}; font-size: {Fonts.SIZE_SM}px;"
                f"font-weight: 600; background: transparent;"
            )

    def mousePressEvent(self, _ev) -> None:
        if self._active:
            self.clicked.emit()


# ── Preview panel ─────────────────────────────────────────────────────────────

class _PreviewPanel(QWidget):
    """Shared protocol preview + save section shown below the input panel."""
    save_clicked = Signal(dict)

    def __init__(self, parent: "QWidget | None" = None) -> None:
        super().__init__(parent)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 16, 0, 0)
        lay.setSpacing(10)

        lay.addWidget(_lbl("Preview", Colors.TEXT_SECOND, Fonts.SIZE_XS, bold=True))

        # Editable name
        name_row = QHBoxLayout()
        name_row.setSpacing(8)
        name_row.addWidget(_lbl("Name:", Colors.TEXT_MUTED, Fonts.SIZE_SM))
        self._name_edit = QLineEdit()
        self._name_edit.setFixedHeight(32)
        self._name_edit.setPlaceholderText("Protocol name…")
        self._name_edit.setStyleSheet(
            f"QLineEdit {{ background: {Colors.BG_INPUT}; color: {Colors.TEXT_PRIMARY};"
            f"  border: 1px solid {Colors.BORDER_LIGHT}; border-radius: {Radii.LG}px;"
            f"  padding: 0 10px; font-size: {Fonts.SIZE_SM}px; }}"
            f"QLineEdit:focus {{ border-color: {Colors.ACCENT}; }}"
        )
        name_row.addWidget(self._name_edit, stretch=1)
        lay.addLayout(name_row)

        self._stats_lbl = _lbl("", Colors.TEXT_MUTED, Fonts.SIZE_XS)
        lay.addWidget(self._stats_lbl)

        lay.addWidget(_lbl("Steps", Colors.TEXT_SECOND, Fonts.SIZE_XS, bold=True))

        self._steps_scroll = QScrollArea()
        self._steps_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._steps_scroll.setWidgetResizable(True)
        self._steps_scroll.setMaximumHeight(220)
        self._steps_scroll.setStyleSheet(
            f"background: {Colors.BG_CARD}; border: 1px solid {Colors.BORDER_LIGHT};"
            f"border-radius: {Radii.LG}px;"
        )
        self._steps_w = QWidget()
        self._steps_w.setStyleSheet(f"background: {Colors.BG_CARD};")
        self._steps_lay = QVBoxLayout(self._steps_w)
        self._steps_lay.setContentsMargins(10, 8, 10, 8)
        self._steps_lay.setSpacing(4)
        self._steps_scroll.setWidget(self._steps_w)
        lay.addWidget(self._steps_scroll)

        self._save_btn = PrimaryButton("⊕  Save to My Protocols")
        self._save_btn.setFixedHeight(36)
        self._save_btn.setEnabled(False)
        self._save_btn.clicked.connect(self._emit_save)
        lay.addWidget(self._save_btn)

        self._proto: "dict | None" = None

    def load_protocol(self, proto: dict) -> None:
        self._proto = proto
        self._name_edit.setText(proto.get("name", "Imported Protocol"))
        n = len(proto.get("steps", []))
        cat = proto.get("category", "—")
        self._stats_lbl.setText(f"{n} step{'s' if n != 1 else ''}  ·  category: {cat}")

        while self._steps_lay.count():
            item = self._steps_lay.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not n:
            self._steps_lay.addWidget(
                _lbl("(No steps found)", Colors.TEXT_MUTED, Fonts.SIZE_SM)
            )
        else:
            for i, step in enumerate(proto.get("steps", [])[:50]):
                container = QWidget()
                container.setStyleSheet("background: transparent;")
                row = QHBoxLayout(container)
                row.setContentsMargins(0, 0, 0, 0)
                row.setSpacing(8)
                num = _lbl(f"{i+1}.", Colors.TEXT_MUTED, Fonts.SIZE_XS)
                num.setFixedWidth(22)
                row.addWidget(num)
                row.addWidget(
                    _lbl(step.get("title", f"Step {i+1}"),
                         Colors.TEXT_PRIMARY, Fonts.SIZE_SM),
                    stretch=1
                )
                self._steps_lay.addWidget(container)
            if n > 50:
                self._steps_lay.addWidget(
                    _lbl(f"… and {n - 50} more steps",
                         Colors.TEXT_MUTED, Fonts.SIZE_XS)
                )
        self._steps_lay.addStretch()
        self._save_btn.setEnabled(True)

    def clear(self) -> None:
        self._proto = None
        self._name_edit.setText("")
        self._stats_lbl.setText("")
        while self._steps_lay.count():
            item = self._steps_lay.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._save_btn.setEnabled(False)

    def _emit_save(self) -> None:
        if not self._proto:
            return
        proto = copy.deepcopy(self._proto)
        name = self._name_edit.text().strip()
        if name:
            proto["name"] = name
        self.save_clicked.emit(proto)


# ── JSON File panel ───────────────────────────────────────────────────────────

class _JsonPanel(QWidget):
    protocol_parsed = Signal(dict)

    def __init__(self, parent: "QWidget | None" = None) -> None:
        super().__init__(parent)
        self.setStyleSheet(f"background: {Colors.BG_PAGE};")
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(14)

        lay.addWidget(_lbl("Import from JSON File", Colors.TEXT_PRIMARY,
                           Fonts.SIZE_MD, bold=True))
        lay.addWidget(_lbl(
            "Select a BenchFlow JSON export (.json) to import a protocol "
            "or lab notebook session.",
            Colors.TEXT_SECOND, Fonts.SIZE_SM, wrap=True
        ))

        pick_btn = QPushButton("📁  Choose JSON File…")
        pick_btn.setFixedHeight(36)
        pick_btn.setMaximumWidth(220)
        pick_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        pick_btn.setStyleSheet(
            f"QPushButton {{ background: {Colors.BG_CARD}; color: {Colors.TEXT_PRIMARY};"
            f"  border: 1px solid {Colors.BORDER_LIGHT}; border-radius: {Radii.LG}px;"
            f"  font-size: {Fonts.SIZE_SM}px; padding: 0 16px; }}"
            f"QPushButton:hover {{ background: {Colors.BG_CARD_HOV}; }}"
        )
        pick_btn.clicked.connect(self._pick_file)
        lay.addWidget(pick_btn)

        self._status_lbl = _lbl("", Colors.TEXT_MUTED, Fonts.SIZE_XS)
        lay.addWidget(self._status_lbl)
        lay.addStretch()

    def _pick_file(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Open JSON Protocol", "",
            "JSON Files (*.json);;All Files (*)"
        )
        if not path:
            return
        try:
            with open(path, encoding="utf-8") as fh:
                text = fh.read()
        except OSError as e:
            self._set_status(f"❌  Cannot read file: {e}", Colors.DANGER)
            return

        proto = _parse_json_protocol(text)
        if proto is None:
            self._set_status(
                "❌  File does not contain a valid BenchFlow protocol.",
                Colors.DANGER
            )
            return

        fname = path.split("/")[-1]
        self._set_status(f"✓  Loaded: {fname}", Colors.SUCCESS)
        _fix_step_orders(proto)
        self.protocol_parsed.emit(proto)

    def _set_status(self, msg: str, color: str) -> None:
        self._status_lbl.setText(msg)
        self._status_lbl.setStyleSheet(
            f"color: {color}; font-size: {Fonts.SIZE_XS}px;"
        )


# ── Paste Text panel ──────────────────────────────────────────────────────────

class _PastePanel(QWidget):
    protocol_parsed = Signal(dict)

    def __init__(self, parent: "QWidget | None" = None) -> None:
        super().__init__(parent)
        self.setStyleSheet(f"background: {Colors.BG_PAGE};")
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(14)

        lay.addWidget(_lbl("Paste Protocol Text", Colors.TEXT_PRIMARY,
                           Fonts.SIZE_MD, bold=True))
        lay.addWidget(_lbl(
            "Paste JSON or plain text. First line → protocol name. "
            "Numbered/bulleted lines → steps.",
            Colors.TEXT_SECOND, Fonts.SIZE_SM, wrap=True
        ))

        self._text_edit = QPlainTextEdit()
        self._text_edit.setMinimumHeight(160)
        self._text_edit.setPlaceholderText(
            "Paste JSON or plain-text protocol here…\n\n"
            "Plain text example:\n"
            "Western Blot Day 1\n"
            "1. Prepare gel\n"
            "2. Load samples\n"
            "3. Run electrophoresis"
        )
        self._text_edit.setStyleSheet(
            f"QPlainTextEdit {{ background: {Colors.BG_INPUT}; color: {Colors.TEXT_PRIMARY};"
            f"  border: 1px solid {Colors.BORDER_LIGHT}; border-radius: {Radii.LG}px;"
            f"  padding: 10px; font-size: {Fonts.SIZE_SM}px; }}"
            f"QPlainTextEdit:focus {{ border-color: {Colors.ACCENT}; }}"
        )
        lay.addWidget(self._text_edit)

        parse_btn = PrimaryButton("🔍  Parse Text")
        parse_btn.setFixedHeight(36)
        parse_btn.setMaximumWidth(160)
        parse_btn.clicked.connect(self._parse)
        lay.addWidget(parse_btn)

        self._status_lbl = _lbl("", Colors.TEXT_MUTED, Fonts.SIZE_XS)
        lay.addWidget(self._status_lbl)
        lay.addStretch()

    def _parse(self) -> None:
        text = self._text_edit.toPlainText().strip()
        if not text:
            self._set_status("⚠  Nothing to parse.", Colors.WARNING)
            return

        proto = _parse_json_protocol(text)
        if proto is not None:
            self._set_status("✓  Parsed as JSON protocol.", Colors.SUCCESS)
            _fix_step_orders(proto)
            self.protocol_parsed.emit(proto)
            return

        proto = _parse_text_protocol(text)
        n = len(proto.get("steps", []))
        self._set_status(
            f"✓  Parsed as plain text: {n} step{'s' if n != 1 else ''} found.",
            Colors.SUCCESS
        )
        _fix_step_orders(proto)
        self.protocol_parsed.emit(proto)

    def _set_status(self, msg: str, color: str) -> None:
        self._status_lbl.setText(msg)
        self._status_lbl.setStyleSheet(
            f"color: {color}; font-size: {Fonts.SIZE_XS}px;"
        )


# ── Coming Soon panel ─────────────────────────────────────────────────────────

class _ComingSoonPanel(QWidget):
    def __init__(self, emoji: str, label: str,
                 parent: "QWidget | None" = None) -> None:
        super().__init__(parent)
        self.setStyleSheet(f"background: {Colors.BG_PAGE};")
        lay = QVBoxLayout(self)
        lay.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.setSpacing(16)

        icon = QLabel(emoji)
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon.setStyleSheet("font-size: 48px;")
        lay.addWidget(icon)

        title = QLabel(f"{label} Import")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet(
            f"color: {Colors.TEXT_PRIMARY}; font-size: {Fonts.SIZE_LG}px;"
            f"font-weight: 700;"
        )
        lay.addWidget(title)

        sub = QLabel(
            "This import method is coming in a future update.\n"
            "For now, use JSON File or Paste Text."
        )
        sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sub.setWordWrap(True)
        sub.setStyleSheet(
            f"color: {Colors.TEXT_MUTED}; font-size: {Fonts.SIZE_SM}px;"
        )
        lay.addWidget(sub)


# ── Main page ─────────────────────────────────────────────────────────────────

_METHODS = [
    ("📁", "JSON File",  "Import from .json export",  True,  0),
    ("📋", "Paste Text", "Paste JSON or plain text",   True,  1),
    ("📄", "PDF",        "Coming in a future update",  False, 2),
    ("📝", "Word Doc",   "Coming in a future update",  False, 3),
]


class ImportPage(BasePage):
    """Protocol import page — Phase 8B."""

    def __init__(self, app: "BenchFlowApp", parent: "QWidget | None" = None) -> None:  # type: ignore[name-defined]
        super().__init__(app, parent)
        self._build()

    def _build(self) -> None:
        outer = QVBoxLayout()
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # ── Header ────────────────────────────────────────────────────────────
        hdr = QWidget()
        hdr.setStyleSheet(f"background: {Colors.BG_PAGE};")
        hdr_lay = QHBoxLayout(hdr)
        hdr_lay.setContentsMargins(28, 20, 28, 16)
        hdr_lay.setSpacing(8)

        title_col = QVBoxLayout()
        title_col.setSpacing(2)
        title_col.addWidget(PageTitle("Import Protocol"))
        title_col.addWidget(SubLabel(
            "Import protocols from JSON, plain text, or other sources."
        ))
        hdr_lay.addLayout(title_col)
        hdr_lay.addStretch()

        back_btn = QPushButton("← Library")
        back_btn.setFixedHeight(34)
        back_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        back_btn.setStyleSheet(
            f"QPushButton {{ background: transparent; color: {Colors.ACCENT};"
            f"  border: none; font-size: {Fonts.SIZE_SM}px; font-weight: 600; }}"
            f"QPushButton:hover {{ color: {Colors.ACCENT_HOVER}; }}"
        )
        back_btn.clicked.connect(lambda: self.navigate("library"))
        hdr_lay.addWidget(back_btn)

        outer.addWidget(hdr)
        outer.addWidget(HSeparator())

        # ── Splitter ──────────────────────────────────────────────────────────
        main_splitter = QSplitter(Qt.Orientation.Horizontal)
        main_splitter.setStyleSheet(
            f"QSplitter::handle {{ background: {Colors.BORDER_LIGHT}; width: 1px; }}"
        )

        # ── Left: method selector ─────────────────────────────────────────────
        left_w = QWidget()
        left_w.setStyleSheet(
            f"background: {Colors.BG_CARD};"
            f"border-right: 1px solid {Colors.BORDER_LIGHT};"
        )
        left_w.setMinimumWidth(180)
        left_w.setMaximumWidth(250)
        left_lay = QVBoxLayout(left_w)
        left_lay.setContentsMargins(16, 20, 16, 20)
        left_lay.setSpacing(8)
        left_lay.addWidget(
            _lbl("Method", Colors.TEXT_MUTED, Fonts.SIZE_XS, bold=True)
        )

        self._method_cards: list[_MethodCard] = []
        for emoji, label, subtitle, active, idx in _METHODS:
            card = _MethodCard(emoji, label, subtitle, active)
            card.clicked.connect(lambda i=idx: self._select_method(i))
            left_lay.addWidget(card)
            self._method_cards.append(card)
        left_lay.addStretch()

        # ── Right: input + preview ────────────────────────────────────────────
        right_w = QWidget()
        right_w.setStyleSheet(f"background: {Colors.BG_PAGE};")
        right_lay = QVBoxLayout(right_w)
        right_lay.setContentsMargins(0, 0, 0, 0)
        right_lay.setSpacing(0)

        right_splitter = QSplitter(Qt.Orientation.Vertical)
        right_splitter.setStyleSheet(
            f"QSplitter::handle {{ background: {Colors.BORDER_LIGHT}; height: 1px; }}"
        )

        # Input stack
        input_w = QWidget()
        input_w.setStyleSheet(f"background: {Colors.BG_PAGE};")
        input_lay = QVBoxLayout(input_w)
        input_lay.setContentsMargins(28, 20, 28, 20)
        input_lay.setSpacing(0)

        self._stack = QStackedWidget()
        self._json_panel  = _JsonPanel()
        self._paste_panel = _PastePanel()
        self._cs_pdf  = _ComingSoonPanel("📄", "PDF")
        self._cs_docx = _ComingSoonPanel("📝", "Word Document")
        self._stack.addWidget(self._json_panel)
        self._stack.addWidget(self._paste_panel)
        self._stack.addWidget(self._cs_pdf)
        self._stack.addWidget(self._cs_docx)
        input_lay.addWidget(self._stack, stretch=1)

        # Preview
        preview_w = QWidget()
        preview_w.setStyleSheet(
            f"background: {Colors.BG_CARD};"
            f"border-top: 1px solid {Colors.BORDER_LIGHT};"
        )
        preview_lay = QVBoxLayout(preview_w)
        preview_lay.setContentsMargins(28, 0, 28, 24)
        self._preview = _PreviewPanel()
        preview_lay.addWidget(self._preview)

        right_splitter.addWidget(input_w)
        right_splitter.addWidget(preview_w)
        right_splitter.setSizes([340, 360])
        right_splitter.setChildrenCollapsible(False)

        right_lay.addWidget(right_splitter, stretch=1)

        main_splitter.addWidget(left_w)
        main_splitter.addWidget(right_w)
        main_splitter.setSizes([220, 680])
        main_splitter.setChildrenCollapsible(False)

        outer.addWidget(main_splitter, stretch=1)
        self._root_layout.addLayout(outer)

        # ── Connections ───────────────────────────────────────────────────────
        self._json_panel.protocol_parsed.connect(self._on_protocol_parsed)
        self._paste_panel.protocol_parsed.connect(self._on_protocol_parsed)
        self._preview.save_clicked.connect(self._on_save_protocol)

        # Default selection
        self._select_method(0)

    # ── Handlers ─────────────────────────────────────────────────────────────

    def _select_method(self, idx: int) -> None:
        for i, card in enumerate(self._method_cards):
            card.set_selected(i == idx)
        self._stack.setCurrentIndex(idx)
        self._preview.clear()

    def _on_protocol_parsed(self, proto: dict) -> None:
        self._preview.load_protocol(proto)

    def _on_save_protocol(self, proto: dict) -> None:
        now = int(time.time() * 1000)
        if not proto.get("id"):
            proto["id"] = str(uuid.uuid4())
        proto["updatedAt"] = now
        if not proto.get("createdAt"):
            proto["createdAt"] = now

        protocols = self.app.data.load_protocols()

        # Deduplicate name
        existing = {p.get("name", "").lower() for p in protocols}
        base_name = proto["name"]
        if base_name.lower() in existing:
            suffix = 1
            while f"{base_name} ({suffix})".lower() in existing:
                suffix += 1
            proto["name"] = f"{base_name} ({suffix})"

        protocols.insert(0, proto)
        self.app.data.save_protocols(protocols)

        bus.emit("protocol_created", protocol=proto)
        name = proto["name"]
        ToastManager.show_success(f"Imported: “{name}”")
        self._preview.clear()
        self.navigate("library")

    def on_show(self) -> None:
        self._select_method(0)
