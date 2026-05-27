"""
Dashboard page — Phase 1 skeleton.

Shows a welcome banner plus quick-stat cards.
Full implementation comes in a later phase.
"""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame, QGridLayout, QHBoxLayout, QLabel,
    QScrollArea, QSizePolicy, QVBoxLayout, QWidget,
)

from qt_app.theme import Colors, Fonts
from qt_app.components.widgets import (
    Card, HSeparator, MutedLabel, PageTitle, PrimaryButton, SubLabel,
)
from qt_app.views.base_page import BasePage


class _StatCard(Card):
    """Small metric card: icon + number + label."""

    def __init__(self, icon: str, value: str, label: str,
                 accent: str = Colors.ACCENT,
                 parent: QWidget | None = None) -> None:
        super().__init__(parent)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(20, 20, 20, 20)
        lay.setSpacing(6)

        icon_lbl = QLabel(icon)
        icon_lbl.setStyleSheet(f"font-size: 28px; color: {accent};")
        lay.addWidget(icon_lbl)

        val_lbl = QLabel(value)
        val_lbl.setStyleSheet(
            f"color: {Colors.TEXT_PRIMARY};"
            f"font-size: {Fonts.SIZE_2XL}px;"
            f"font-weight: 700;"
        )
        lay.addWidget(val_lbl)

        lab_lbl = QLabel(label)
        lab_lbl.setStyleSheet(
            f"color: {Colors.TEXT_SECOND}; font-size: {Fonts.SIZE_SM}px;"
        )
        lay.addWidget(lab_lbl)
        lay.addStretch()


class DashboardPage(BasePage):
    """Landing page shown on app start."""

    def __init__(self, app: "BenchFlowApp", parent: QWidget | None = None) -> None:  # type: ignore[name-defined]
        super().__init__(app, parent)
        self._build()

    def _build(self) -> None:
        # ── Outer scroll wrapper ──────────────────────────────────────────────
        scroll = QScrollArea()
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet(f"background: {Colors.BG_PAGE};")

        inner = QWidget()
        inner.setStyleSheet(f"background: {Colors.BG_PAGE};")
        scroll.setWidget(inner)

        root = QVBoxLayout(inner)
        root.setContentsMargins(32, 32, 32, 32)
        root.setSpacing(24)

        # ── Header ────────────────────────────────────────────────────────────
        header = QHBoxLayout()
        header.setSpacing(16)

        title_col = QVBoxLayout()
        title_col.setSpacing(4)
        title_col.addWidget(PageTitle("Dashboard"))
        sub = SubLabel("Welcome back — your lab at a glance.")
        title_col.addWidget(sub)
        header.addLayout(title_col)
        header.addStretch()

        run_btn = PrimaryButton("▶  Start Run")
        run_btn.setMinimumWidth(140)
        run_btn.clicked.connect(lambda: self.app.navigate("run"))
        header.addWidget(run_btn)

        root.addLayout(header)
        root.addWidget(HSeparator())

        # ── Stat cards ────────────────────────────────────────────────────────
        stats_label = QLabel("Overview")
        stats_label.setStyleSheet(
            f"color: {Colors.TEXT_SECOND}; font-size: {Fonts.SIZE_SM}px;"
            f"font-weight: 600; letter-spacing: 1px;"
        )
        root.addWidget(stats_label)

        grid = QGridLayout()
        grid.setSpacing(12)
        grid.setContentsMargins(0, 0, 0, 0)

        stats = [
            ("📋", self._count_protocols(), "Protocols",     Colors.ACCENT),
            ("▶",  self._count_runs(),      "Runs logged",   Colors.SUCCESS),
            ("🗓", self._count_schedule(),  "Scheduled",     Colors.WARNING),
            ("📓", self._count_notes(),     "Notebook entries", Colors.ACCENT_LIGHT),
        ]
        for col, (icon, val, lbl, color) in enumerate(stats):
            card = _StatCard(icon, str(val), lbl, color)
            card.setMinimumHeight(130)
            grid.addWidget(card, 0, col)

        root.addLayout(grid)

        # ── Quick access ──────────────────────────────────────────────────────
        qa_label = QLabel("Quick access")
        qa_label.setStyleSheet(
            f"color: {Colors.TEXT_SECOND}; font-size: {Fonts.SIZE_SM}px;"
            f"font-weight: 600; letter-spacing: 1px;"
        )
        root.addWidget(qa_label)

        qa_row = QHBoxLayout()
        qa_row.setSpacing(12)

        for label, page, emoji in [
            ("Protocol Library", "library",  "📋"),
            ("Schedule",         "schedule", "🗓"),
            ("Lab Notebook",     "history",  "📓"),
            ("Settings",         "settings", "⚙"),
        ]:
            btn = self._make_quick_card(emoji, label, page)
            qa_row.addWidget(btn)

        root.addLayout(qa_row)
        root.addStretch()

        self._root_layout.addWidget(scroll)

    # ── Quick card ────────────────────────────────────────────────────────────

    def _make_quick_card(self, emoji: str, label: str, page: str) -> QFrame:
        card = Card()
        card.setCursor(Qt.CursorShape.PointingHandCursor)
        card.setMinimumHeight(80)
        card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        lay = QHBoxLayout(card)
        lay.setContentsMargins(16, 16, 16, 16)
        lay.setSpacing(12)

        icon = QLabel(emoji)
        icon.setStyleSheet(f"font-size: 22px;")
        lay.addWidget(icon)

        lbl = QLabel(label)
        lbl.setStyleSheet(
            f"color: {Colors.TEXT_PRIMARY}; font-size: {Fonts.SIZE_MD}px; font-weight: 600;"
        )
        lay.addWidget(lbl)
        lay.addStretch()

        arrow = QLabel("›")
        arrow.setStyleSheet(f"color: {Colors.TEXT_MUTED}; font-size: 20px;")
        lay.addWidget(arrow)

        # Make the whole card clickable via mouse press event
        card.mousePressEvent = lambda e, p=page: self.app.navigate(p)
        return card

    # ── Data helpers ──────────────────────────────────────────────────────────

    def _count_protocols(self) -> int:
        try:
            return len(self.app.data.load_protocols())
        except Exception:
            return 0

    def _count_runs(self) -> int:
        try:
            return len(self.app.data.load_runs())
        except Exception:
            return 0

    def _count_schedule(self) -> int:
        try:
            return len(self.app.data.load_schedule())
        except Exception:
            return 0

    def _count_notes(self) -> int:
        try:
            return len(self.app.data.load_runs())  # placeholder until notebook model is separate
        except Exception:
            return 0

    # ── on_show ───────────────────────────────────────────────────────────────

    def on_show(self) -> None:
        """Rebuild stat cards with fresh data each time Dashboard is shown."""
        # For Phase 1, a full rebuild is fine.
        # Phase 2+ will use signals to update only changed counts.
        # Clear and rebuild
        for i in reversed(range(self._root_layout.count())):
            item = self._root_layout.itemAt(i)
            if item and item.widget():
                item.widget().deleteLater()
        self._build()
