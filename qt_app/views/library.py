"""
Protocol Library page — Phase 2: read-only data display.

Shows two sections:
  • My Protocols  — user-created (protocols.json)
  • Built-in Templates — shipped templates/*.json

Each card shows: name, category, step count, total duration, tags.
Clicking a card selects/highlights it.
"""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QScrollArea,
    QSizePolicy, QVBoxLayout, QWidget,
)

from qt_app.theme import Colors, Fonts, Radii
from qt_app.components.widgets import (
    Card, HSeparator, MutedLabel, PageTitle, PrimaryButton, SubLabel,
)
from qt_app.views.base_page import BasePage
from qt_app.services.data import DataService


# ── Protocol card ─────────────────────────────────────────────────────────────

class ProtocolCard(QFrame):
    """Single clickable card showing one protocol or template."""

    selected = Signal(dict)   # emits the raw protocol dict when clicked

    _STYLE_DEFAULT = (
        f"QFrame {{"
        f"  background: {Colors.BG_CARD};"
        f"  border-radius: {Radii.LG}px;"
        f"  border: 1px solid {Colors.BORDER};"
        f"}}"
        f"QFrame:hover {{"
        f"  border: 1px solid {Colors.ACCENT};"
        f"}}"
    )
    _STYLE_SELECTED = (
        f"QFrame {{"
        f"  background: rgba(59,130,246,0.12);"
        f"  border-radius: {Radii.LG}px;"
        f"  border: 2px solid {Colors.ACCENT};"
        f"}}"
    )

    def __init__(self, protocol: dict, is_template: bool = False,
                 parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._protocol = protocol
        self._selected = False
        self.setStyleSheet(self._STYLE_DEFAULT)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._build(protocol, is_template)

    def _build(self, p: dict, is_template: bool) -> None:
        lay = QVBoxLayout(self)
        lay.setContentsMargins(18, 14, 18, 14)
        lay.setSpacing(6)

        # ── Row 1: name + duration ─────────────────────────────────────────
        row1 = QHBoxLayout()
        row1.setSpacing(8)

        name = p.get("name", "Untitled")
        name_lbl = QLabel(name)
        name_lbl.setStyleSheet(
            f"color: {Colors.TEXT_PRIMARY};"
            f"font-size: {Fonts.SIZE_MD}px;"
            f"font-weight: 700;"
        )
        name_lbl.setWordWrap(False)
        row1.addWidget(name_lbl, stretch=1)

        total_min = DataService.protocol_total_minutes(p)
        dur_lbl = QLabel(DataService.format_duration(total_min))
        dur_lbl.setStyleSheet(
            f"color: {Colors.TEXT_MUTED}; font-size: {Fonts.SIZE_SM}px;"
        )
        row1.addWidget(dur_lbl)
        lay.addLayout(row1)

        # ── Row 2: category + step count ──────────────────────────────────
        row2 = QHBoxLayout()
        row2.setSpacing(10)

        cat = p.get("category", "")
        n_steps = len(p.get("steps", []))

        if cat:
            cat_lbl = self._badge(cat, Colors.ACCENT, "rgba(59,130,246,0.15)")
            row2.addWidget(cat_lbl)

        steps_lbl = self._badge(
            f"{n_steps} step{'s' if n_steps != 1 else ''}",
            Colors.TEXT_SECOND, Colors.BG_CARD_HOV,
        )
        row2.addWidget(steps_lbl)

        if is_template:
            tmpl_lbl = self._badge("Template", Colors.WARNING, "rgba(249,115,22,0.15)")
            row2.addWidget(tmpl_lbl)

        row2.addStretch()
        lay.addLayout(row2)

        # ── Row 3: tags ───────────────────────────────────────────────────
        tags = p.get("tags", [])
        if tags:
            tags_row = QHBoxLayout()
            tags_row.setSpacing(6)
            for tag in tags[:4]:
                t = self._badge(f"#{tag}", Colors.TEXT_MUTED, Colors.BG_CARD_HOV)
                tags_row.addWidget(t)
            if len(tags) > 4:
                more = self._badge(f"+{len(tags)-4}", Colors.TEXT_MUTED, Colors.BG_CARD_HOV)
                tags_row.addWidget(more)
            tags_row.addStretch()
            lay.addLayout(tags_row)

    @staticmethod
    def _badge(text: str, fg: str, bg: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setStyleSheet(
            f"color: {fg};"
            f"background: {bg};"
            f"border-radius: 6px;"
            f"padding: 2px 8px;"
            f"font-size: {Fonts.SIZE_XS}px;"
            f"font-weight: 600;"
        )
        return lbl

    # ── Selection ─────────────────────────────────────────────────────────────
    def set_selected(self, sel: bool) -> None:
        self._selected = sel
        self.setStyleSheet(self._STYLE_SELECTED if sel else self._STYLE_DEFAULT)

    def mousePressEvent(self, event) -> None:
        self.selected.emit(self._protocol)
        super().mousePressEvent(event)


# ── Section header ────────────────────────────────────────────────────────────

def _section_header(title: str, count: int) -> QWidget:
    w = QWidget()
    lay = QHBoxLayout(w)
    lay.setContentsMargins(0, 0, 0, 0)
    lay.setSpacing(10)

    lbl = QLabel(title)
    lbl.setStyleSheet(
        f"color: {Colors.TEXT_PRIMARY};"
        f"font-size: {Fonts.SIZE_LG}px;"
        f"font-weight: 700;"
    )
    lay.addWidget(lbl)

    cnt = QLabel(str(count))
    cnt.setStyleSheet(
        f"color: {Colors.ACCENT_LIGHT};"
        f"background: rgba(59,130,246,0.15);"
        f"border-radius: 8px;"
        f"padding: 2px 10px;"
        f"font-size: {Fonts.SIZE_SM}px;"
        f"font-weight: 700;"
    )
    lay.addWidget(cnt)
    lay.addStretch()
    return w


# ── Empty state ────────────────────────────────────────────────────────────────

def _empty_state(msg: str) -> QWidget:
    w = QWidget()
    lay = QHBoxLayout(w)
    lay.setContentsMargins(0, 0, 0, 0)
    lbl = QLabel(msg)
    lbl.setStyleSheet(
        f"color: {Colors.TEXT_MUTED}; font-size: {Fonts.SIZE_SM}px;"
        f"font-style: italic;"
    )
    lay.addWidget(lbl)
    lay.addStretch()
    return w


# ── LibraryPage ────────────────────────────────────────────────────────────────

class LibraryPage(BasePage):
    """Protocol Library — lists My Protocols + Built-in Templates."""

    def __init__(self, app: "BenchFlowApp", parent: QWidget | None = None) -> None:  # type: ignore[name-defined]
        super().__init__(app, parent)
        self._cards: list[ProtocolCard] = []
        self._selected_card: ProtocolCard | None = None
        self._build_shell()
        self._load_data()

    # ── Shell (fixed layout, content reloaded on show) ────────────────────────
    def _build_shell(self) -> None:
        outer = QVBoxLayout()
        outer.setContentsMargins(32, 32, 32, 0)
        outer.setSpacing(0)

        # Header
        header = QHBoxLayout()
        header.addWidget(PageTitle("Protocol Library"))
        header.addStretch()
        outer.addLayout(header)
        outer.addSpacing(4)

        sub = SubLabel(
            "Your protocols and built-in templates. "
            "Full editing available in Phase 5."
        )
        outer.addWidget(sub)
        outer.addSpacing(16)
        outer.addWidget(HSeparator())
        outer.addSpacing(16)

        # Scroll area
        self._scroll = QScrollArea()
        self._scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._scroll.setWidgetResizable(True)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._scroll.setStyleSheet(f"background: {Colors.BG_PAGE};")

        self._content = QWidget()
        self._content.setStyleSheet(f"background: {Colors.BG_PAGE};")
        self._content_layout = QVBoxLayout(self._content)
        self._content_layout.setContentsMargins(0, 0, 16, 32)
        self._content_layout.setSpacing(0)
        self._scroll.setWidget(self._content)
        outer.addWidget(self._scroll, stretch=1)

        self._root_layout.addLayout(outer)

    # ── Load & render ─────────────────────────────────────────────────────────
    def _load_data(self) -> None:
        # Clear old cards
        self._cards.clear()
        self._selected_card = None
        while self._content_layout.count():
            item = self._content_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        protocols = self.app.data.load_protocols()
        templates = self.app.data.load_templates()

        # My Protocols section
        self._content_layout.addWidget(_section_header("My Protocols", len(protocols)))
        self._content_layout.addSpacing(10)
        if protocols:
            for p in protocols:
                self._add_card(p, is_template=False)
        else:
            self._content_layout.addWidget(
                _empty_state("No protocols yet. Create one from a template or from scratch.")
            )
        self._content_layout.addSpacing(28)

        # Templates section
        self._content_layout.addWidget(_section_header("Built-in Templates", len(templates)))
        self._content_layout.addSpacing(10)
        if templates:
            # Group by category
            by_cat: dict[str, list[dict]] = {}
            for t in templates:
                cat = t.get("category", "Other")
                by_cat.setdefault(cat, []).append(t)

            for cat, items in sorted(by_cat.items()):
                # Category sub-header
                cat_lbl = QLabel(cat)
                cat_lbl.setStyleSheet(
                    f"color: {Colors.TEXT_SECOND}; font-size: {Fonts.SIZE_SM}px;"
                    f"font-weight: 600; margin-top: 4px;"
                )
                self._content_layout.addWidget(cat_lbl)
                self._content_layout.addSpacing(6)
                for t in items:
                    self._add_card(t, is_template=True)
                self._content_layout.addSpacing(12)
        else:
            self._content_layout.addWidget(
                _empty_state("No templates found.")
            )

        self._content_layout.addStretch()

    def _add_card(self, p: dict, is_template: bool) -> None:
        card = ProtocolCard(p, is_template=is_template, parent=self._content)
        card.selected.connect(self._on_card_selected)
        self._cards.append(card)
        self._content_layout.addWidget(card)
        self._content_layout.addSpacing(8)

    def _on_card_selected(self, protocol: dict) -> None:
        # Deselect old
        if self._selected_card is not None:
            self._selected_card.set_selected(False)
        # Find and select the new one
        for card in self._cards:
            if card._protocol is protocol:
                card.set_selected(True)
                self._selected_card = card
                break

    # ── Refresh on show ───────────────────────────────────────────────────────
    def on_show(self) -> None:
        self._load_data()
