"""
Run Mode page — Phase 3 implementation.

Phase 1: Skeleton with protocol selector and placeholder step list.
Phase 3: Full StepCard + QTimer implementation.
"""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox, QFrame, QHBoxLayout, QLabel,
    QScrollArea, QSizePolicy, QVBoxLayout, QWidget,
)

from qt_app.theme import Colors, Fonts
from qt_app.components.widgets import (
    Card, HSeparator, MutedLabel, PageTitle, PrimaryButton,
    SecondaryButton, SubLabel,
)
from qt_app.views.base_page import BasePage


class RunModePage(BasePage):
    """Run Mode — execute a protocol with live timers."""

    def __init__(self, app: "BenchFlowApp", parent: QWidget | None = None) -> None:  # type: ignore[name-defined]
        super().__init__(app, parent)
        self._build()

    def _build(self) -> None:
        root = QVBoxLayout()
        root.setContentsMargins(32, 32, 32, 0)
        root.setSpacing(0)

        # ── Header ────────────────────────────────────────────────────────────
        header = QHBoxLayout()
        header.setSpacing(12)
        header.addWidget(PageTitle("Run Mode"))
        header.addStretch()

        self._proto_selector = QComboBox()
        self._proto_selector.setObjectName("ProtoSelector")
        self._proto_selector.setMinimumWidth(260)
        self._proto_selector.setMinimumHeight(36)
        self._proto_selector.setStyleSheet(
            f"QComboBox {{ background: {Colors.BG_CARD}; color: {Colors.TEXT_PRIMARY};"
            f"border: 1px solid {Colors.BORDER}; border-radius: 10px;"
            f"padding: 6px 12px; font-size: {Fonts.SIZE_MD}px; }}"
        )
        header.addWidget(self._proto_selector)

        start_btn = PrimaryButton("▶  Start")
        start_btn.setMinimumWidth(100)
        header.addWidget(start_btn)

        root.addLayout(header)
        root.addSpacing(16)
        root.addWidget(HSeparator())
        root.addSpacing(16)

        # ── Placeholder content ───────────────────────────────────────────────
        placeholder = QWidget()
        placeholder.setStyleSheet(f"background: transparent;")
        ph_lay = QVBoxLayout(placeholder)
        ph_lay.setAlignment(Qt.AlignmentFlag.AlignCenter)
        ph_lay.setSpacing(12)

        icon = QLabel("▶")
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon.setStyleSheet(f"font-size: 56px; color: {Colors.ACCENT};")

        msg = QLabel("Select a protocol above and press Start to begin a run.")
        msg.setAlignment(Qt.AlignmentFlag.AlignCenter)
        msg.setWordWrap(True)
        msg.setStyleSheet(
            f"color: {Colors.TEXT_SECOND}; font-size: {Fonts.SIZE_MD}px;"
        )

        phase_badge = QLabel("Full implementation: Phase 3")
        phase_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        phase_badge.setStyleSheet(
            f"color: {Colors.ACCENT_LIGHT};"
            f"background: rgba(59,130,246,0.15);"
            f"border-radius: 8px; padding: 4px 14px;"
            f"font-size: {Fonts.SIZE_SM}px; font-weight: 600;"
        )

        ph_lay.addWidget(icon)
        ph_lay.addWidget(msg)
        ph_lay.addSpacing(8)
        ph_lay.addWidget(phase_badge)

        root.addStretch()
        root.addWidget(placeholder)
        root.addStretch()

        self._root_layout.addLayout(root)
        self._populate_protocols()
        self._proto_selector.currentIndexChanged.connect(self._on_proto_changed)

    def _populate_protocols(self) -> None:
        self._proto_selector.clear()
        self._proto_selector.addItem("— Select protocol —", None)
        try:
            for p in self.app.data.load_protocols():
                name = p.get("name", "Untitled")
                pid  = p.get("id", "")
                self._proto_selector.addItem(name, pid)
        except Exception:
            pass

    def _on_proto_changed(self, idx: int) -> None:
        # Will drive step card rendering in Phase 3
        pass

    def on_show(self) -> None:
        self._populate_protocols()
