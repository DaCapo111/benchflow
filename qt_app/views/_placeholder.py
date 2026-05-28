"""
Internal helper: _PlaceholderPage
==================================
Creates a uniform "Coming in Phase N" stub page.
Not imported externally — used only by sibling views.
"""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget

from qt_app.theme import Colors, Fonts
from qt_app.views.base_page import BasePage


class _PlaceholderPage(BasePage):
    """Generic stub shown while a page awaits full implementation."""

    def __init__(self, title: str, emoji: str, description: str,
                 phase: str,
                 app: "BenchFlowApp",  # type: ignore[name-defined]
                 parent: QWidget | None = None) -> None:
        super().__init__(app, parent)
        self._title = title

        root = QVBoxLayout()
        root.setContentsMargins(48, 0, 48, 48)
        root.setSpacing(12)
        root.setAlignment(Qt.AlignmentFlag.AlignCenter)

        icon_lbl = QLabel(emoji)
        icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_lbl.setStyleSheet("font-size: 64px;")

        title_lbl = QLabel(title)
        title_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_lbl.setStyleSheet(
            f"color: {Colors.TEXT_PRIMARY};"
            f"font-size: {Fonts.SIZE_2XL}px;"
            f"font-weight: 700;"
        )

        desc_lbl = QLabel(description)
        desc_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        desc_lbl.setWordWrap(True)
        desc_lbl.setStyleSheet(
            f"color: {Colors.TEXT_SECOND}; font-size: {Fonts.SIZE_MD}px;"
        )

        badge = QLabel(f"Planned for {phase}")
        badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        badge.setStyleSheet(
            f"color: {Colors.ACCENT};"
            f"background: {Colors.ACCENT_BG};"
            f"border-radius: 8px;"
            f"padding: 4px 14px;"
            f"font-size: {Fonts.SIZE_SM}px;"
            f"font-weight: 600;"
        )

        root.addStretch()
        root.addWidget(icon_lbl)
        root.addSpacing(8)
        root.addWidget(title_lbl)
        root.addWidget(desc_lbl)
        root.addSpacing(12)
        root.addWidget(badge)
        root.addStretch()

        self._root_layout.addLayout(root)
