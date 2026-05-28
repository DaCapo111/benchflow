"""
Sidebar navigation component.

Emits `nav_requested(page_id: str)` when the user clicks a nav button.
The main window connects this signal to its navigate() slot.
"""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QPushButton,
    QSizePolicy, QVBoxLayout, QWidget,
)

from qt_app.theme import Colors, Fonts
from qt_app.components.widgets import HSeparator
from qt_app.services.event_bus import bus


# Nav items: (page_id, emoji, label)
NAV_ITEMS: list[tuple[str, str, str]] = [
    ("dashboard",  "⬛",  "Dashboard"),
    ("library",    "📋",  "Library"),
    ("schedule",   "🗓",  "Schedule"),
    ("flowchart",  "⎇",   "Flowchart"),
    ("run",        "▶",   "Run Mode"),
    ("history",    "📓",  "Lab Notebook"),
    ("settings",   "⚙",   "Settings"),
]


class Sidebar(QWidget):
    """Left-hand navigation sidebar."""

    nav_requested = Signal(str)  # emitted with page_id

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("Sidebar")
        self.setFixedWidth(204)
        self._nav_buttons: dict[str, QPushButton] = {}
        self._active_page: str = ""
        self._logo_title: QLabel | None = None
        self._logo_sub: QLabel | None = None
        self._footer: QLabel | None = None
        self._build()
        bus.subscribe("theme_changed", self._on_theme_changed)

    # ── Build ─────────────────────────────────────────────────────────────────

    def _build(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 20, 12, 16)
        root.setSpacing(0)

        # Logo
        root.addWidget(self._make_logo())
        root.addSpacing(16)
        root.addWidget(HSeparator())
        root.addSpacing(12)

        # Nav buttons
        for page_id, emoji, label in NAV_ITEMS:
            btn = self._make_nav_button(page_id, emoji, label)
            self._nav_buttons[page_id] = btn
            root.addWidget(btn)
            root.addSpacing(5)

        # Spacer pushes footer to bottom
        root.addStretch(1)
        root.addWidget(HSeparator())
        root.addSpacing(8)

        # Footer
        footer = QLabel("Local workspace")
        footer.setObjectName("SidebarFooter")
        footer.setAlignment(Qt.AlignmentFlag.AlignCenter)
        footer.setStyleSheet(
            f"color: {Colors.TEXT_MUTED}; font-size: {Fonts.SIZE_XS}px;"
        )
        self._footer = footer
        root.addWidget(footer)

    def _make_logo(self) -> QWidget:
        w = QWidget()
        w.setObjectName("SidebarLogo")
        lay = QVBoxLayout(w)
        lay.setContentsMargins(10, 0, 0, 0)
        lay.setSpacing(2)

        title = QLabel("BenchFlow")
        title.setObjectName("SidebarTitle")
        title.setStyleSheet(
            f"color: {Colors.TEXT_PRIMARY};"
            f"font-size: {Fonts.SIZE_XL}px;"
            f"font-weight: 700;"
        )
        self._logo_title = title

        subtitle = QLabel("Wet Lab Manager")
        subtitle.setObjectName("SidebarSubtitle")
        subtitle.setStyleSheet(
            f"color: {Colors.SB_TEXT}; font-size: {Fonts.SIZE_SM}px;"
        )
        self._logo_sub = subtitle

        lay.addWidget(title)
        lay.addWidget(subtitle)
        return w

    def _make_nav_button(self, page_id: str, emoji: str, label: str) -> QPushButton:
        btn = QPushButton(f"{emoji}   {label}")
        btn.setObjectName("NavButton")
        btn.setProperty("active", False)
        btn.setMinimumHeight(40)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setStyleSheet(self._nav_style(False))
        btn.clicked.connect(lambda checked=False, pid=page_id: self.nav_requested.emit(pid))
        return btn

    # ── Public API ────────────────────────────────────────────────────────────

    def set_active(self, page_id: str) -> None:
        """Highlight *page_id* and un-highlight the previously active button."""
        if page_id == self._active_page:
            return
        # "library" highlights for editor & import pages too — caller should
        # normalise page_id before calling here.
        for pid, btn in self._nav_buttons.items():
            active = pid == page_id
            btn.setProperty("active", active)
            btn.setStyleSheet(self._nav_style(active))
        self._active_page = page_id

    # ── Theme refresh ─────────────────────────────────────────────────────────

    def _on_theme_changed(self, theme: str = "dark", **_kw) -> None:
        """Re-apply all inline styles when the theme changes."""
        # Logo
        if self._logo_title:
            self._logo_title.setStyleSheet(
                f"color: {Colors.TEXT_PRIMARY};"
                f"font-size: {Fonts.SIZE_XL}px; font-weight: 700;"
            )
        if self._logo_sub:
            self._logo_sub.setStyleSheet(
                f"color: {Colors.SB_TEXT}; font-size: {Fonts.SIZE_SM}px;"
            )
        # Nav buttons
        for pid, btn in self._nav_buttons.items():
            active = pid == self._active_page
            btn.setStyleSheet(self._nav_style(active))
        # Footer
        if self._footer:
            self._footer.setStyleSheet(
                f"color: {Colors.TEXT_MUTED}; font-size: {Fonts.SIZE_XS}px;"
            )

    # ── Helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def _nav_style(active: bool) -> str:
        if active:
            return (
                "QPushButton {"
                f"  background-color: {Colors.SB_ACTIVE};"
                f"  color: {Colors.SB_TEXT_ACT};"
                f"  text-align: left;"
                f"  padding: 0px 14px;"
                f"  border-radius: 14px;"
                f"  border-left: 3px solid {Colors.ACCENT};"
                f"  font-size: {Fonts.SIZE_MD}px;"
                f"  font-weight: 700;"
                "}"
            )
        return (
            "QPushButton {"
            f"  background-color: transparent;"
            f"  color: {Colors.SB_TEXT};"
            f"  text-align: left;"
            f"  padding: 0px 14px;"
            f"  border-radius: 14px;"
            f"  border: none;"
            f"  font-size: {Fonts.SIZE_MD}px;"
            "}"
            "QPushButton:hover {"
            f"  background-color: {Colors.SB_HOVER};"
            f"  color: {Colors.TEXT_PRIMARY};"
            "}"
        )
