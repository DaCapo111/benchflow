"""
Dashboard page — Phase 2: real data from DataService.

Shows:
- Protocol / template / schedule / notebook counts
- Active session indicator (if crash-recovery session exists)
- Quick-access cards

Phase 4.75
----------
- Subscribes to EventBus events (run_session_saved, schedule_updated,
  notebook_record_created, protocol_updated) to refresh counts.
- Counts are refreshed lazily via on_show() or immediately if visible.
"""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame, QGridLayout, QHBoxLayout, QLabel,
    QScrollArea, QSizePolicy, QVBoxLayout, QWidget,
)

from qt_app.theme import Colors, Fonts, Radii
from qt_app.components.widgets import (
    Card, PageTitle, PrimaryButton, SubLabel,
)
from qt_app.services.event_bus import bus
from qt_app.views.base_page import BasePage


# ── Stat card ─────────────────────────────────────────────────────────────────

class _StatCard(Card):
    def __init__(self, icon: str, value: str, label: str, accent: str,
                 parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setMinimumHeight(138)
        self.setStyleSheet(
            f"QFrame#Card {{ background: {Colors.BG_ELEVATED};"
            f"  border: 1px solid {Colors.BORDER}; border-radius: {Radii.LG}px; }}"
            f"QFrame#Card:hover {{ background: {Colors.BG_CARD_HOV};"
            f"  border-color: {Colors.BORDER}; }}"
        )
        lay = QVBoxLayout(self)
        lay.setContentsMargins(20, 18, 20, 18)
        lay.setSpacing(8)

        icon_lbl = QLabel(icon)
        icon_lbl.setFixedSize(36, 36)
        icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_lbl.setStyleSheet(
            f"font-size: 20px; color: {accent};"
            f"background: {Colors.BG_SURFACE_ALT};"
            f"border-radius: 12px;"
        )
        lay.addWidget(icon_lbl)

        val_lbl = QLabel(value)
        val_lbl.setStyleSheet(
            f"color: {Colors.TEXT_PRIMARY};"
            f"font-size: {Fonts.SIZE_3XL}px; font-weight: 750;"
        )
        lay.addWidget(val_lbl)

        lab_lbl = QLabel(label)
        lab_lbl.setStyleSheet(
            f"color: {Colors.TEXT_SECOND}; font-size: {Fonts.SIZE_MD}px;"
        )
        lay.addWidget(lab_lbl)
        lay.addStretch()


# ── Active session banner ─────────────────────────────────────────────────────

class _ActiveSessionBanner(QFrame):
    """Shown when a crash-recovery runtime_session.json exists."""

    def __init__(self, session: dict, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setStyleSheet(
            f"QFrame {{"
            f"  background: {Colors.WARNING_BG};"
            f"  border: 1px solid {Colors.BORDER};"
            f"  border-left: 3px solid {Colors.WARNING};"
            f"  border-radius: {Radii.LG}px;"
            f"}}"
        )
        lay = QHBoxLayout(self)
        lay.setContentsMargins(18, 12, 18, 12)
        lay.setSpacing(14)

        icon = QLabel("⚠")
        icon.setStyleSheet(f"color: {Colors.WARNING}; font-size: 20px;")
        lay.addWidget(icon)

        proto_name = (
            session.get("protocol_snapshot", {}).get("name", "")
            or session.get("protocol_id", "Unknown protocol")
        )
        msg = QLabel(f"Interrupted run: <b>{proto_name}</b>  — open Run Mode to resume")
        msg.setStyleSheet(
            f"color: {Colors.TEXT_PRIMARY}; font-size: {Fonts.SIZE_SM}px;"
        )
        msg.setTextFormat(Qt.TextFormat.RichText)
        lay.addWidget(msg, stretch=1)


# ── Quick-access card ─────────────────────────────────────────────────────────

def _quick_card(emoji: str, label: str, page: str, app) -> QFrame:
    card = Card()
    card.setCursor(Qt.CursorShape.PointingHandCursor)
    card.setMinimumHeight(94)
    card.setStyleSheet(
        f"QFrame#Card {{ background: {Colors.BG_ELEVATED};"
        f"  border: 1px solid {Colors.BORDER}; border-radius: {Radii.LG}px; }}"
        f"QFrame#Card:hover {{ background: {Colors.BG_CARD_HOV};"
        f"  border-color: {Colors.BORDER}; }}"
    )
    card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

    lay = QHBoxLayout(card)
    lay.setContentsMargins(18, 16, 18, 16)
    lay.setSpacing(14)

    e_lbl = QLabel(emoji)
    e_lbl.setFixedSize(36, 36)
    e_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
    e_lbl.setStyleSheet(
        f"font-size: 20px; background: {Colors.BG_SURFACE_ALT};"
        f"border-radius: 12px;"
    )
    lay.addWidget(e_lbl)

    t_lbl = QLabel(label)
    t_lbl.setStyleSheet(
        f"color: {Colors.TEXT_PRIMARY}; font-size: {Fonts.SIZE_MD}px; font-weight: 700;"
    )
    lay.addWidget(t_lbl)
    lay.addStretch()

    arr = QLabel("›")
    arr.setStyleSheet(f"color: {Colors.TEXT_MUTED}; font-size: 22px;")
    lay.addWidget(arr)

    card.mousePressEvent = lambda e, p=page: app.navigate(p)
    return card


# ── DashboardPage ─────────────────────────────────────────────────────────────

class DashboardPage(BasePage):
    """Landing page — shows real counts from DataService.

    Phase 4.75: subscribes to EventBus so counts refresh when other pages
    modify data.  If the Dashboard is currently visible the rebuild happens
    immediately; otherwise it refreshes on the next on_show().
    """

    def __init__(self, app: "BenchFlowApp", parent: QWidget | None = None) -> None:  # type: ignore[name-defined]
        super().__init__(app, parent)
        self._needs_refresh = False
        self._build()
        self._subscribe_events()

    def _subscribe_events(self) -> None:
        """Register callbacks for EventBus events that affect dashboard counts."""
        for event in (
            "run_session_saved",
            "schedule_updated",
            "notebook_record_created",
            "protocol_created",
            "protocol_updated",
            "protocol_deleted",
        ):
            bus.subscribe(event, self._on_data_changed)

    def _on_data_changed(self, **_kwargs) -> None:
        """Called by EventBus when any relevant data changes."""
        if self.isVisible():
            # Immediately refresh if the dashboard tab is showing
            self._rebuild()
        else:
            # Defer: rebuild on next on_show()
            self._needs_refresh = True

    def _rebuild(self) -> None:
        """Clear and rebuild the entire dashboard with fresh counts."""
        while self._root_layout.count():
            item = self._root_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._build()
        self._needs_refresh = False

    def _build(self) -> None:
        scroll = QScrollArea()
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet(f"background: {Colors.BG_PAGE};")

        inner = QWidget()
        inner.setStyleSheet(f"background: {Colors.BG_PAGE};")
        scroll.setWidget(inner)

        root = QVBoxLayout(inner)
        root.setContentsMargins(36, 34, 36, 36)
        root.setSpacing(0)

        # ── Active session banner (optional) ──────────────────────────────────
        session = self.app.data.load_active_session()
        if session:
            banner = _ActiveSessionBanner(session)
            root.addWidget(banner)
            root.addSpacing(16)

        # ── Header ────────────────────────────────────────────────────────────
        header = QHBoxLayout()
        header.setSpacing(16)

        col = QVBoxLayout()
        col.setSpacing(6)
        col.addWidget(PageTitle("Dashboard"))
        col.addWidget(SubLabel("Protocols, scheduled work, and recent runs in one place."))
        header.addLayout(col)
        header.addStretch()

        run_btn = PrimaryButton("▶  Start Run")
        run_btn.setMinimumWidth(140)
        run_btn.clicked.connect(lambda: self.app.navigate("run"))
        header.addWidget(run_btn)
        root.addLayout(header)
        root.addSpacing(24)

        # ── Stats ─────────────────────────────────────────────────────────────
        n_protocols = len(self.app.data.load_protocols())
        n_templates = len(self.app.data.load_templates())
        n_schedule  = len(self.app.data.load_scheduled_experiments())
        n_runs      = len(self.app.data.load_runs())

        ovr_lbl = QLabel("Overview")
        ovr_lbl.setStyleSheet(
            f"color: {Colors.TEXT_PRIMARY}; font-size: {Fonts.SIZE_XL}px;"
            f"font-weight: 700;"
        )
        root.addWidget(ovr_lbl)
        root.addSpacing(10)

        grid = QGridLayout()
        grid.setSpacing(14)
        grid.setContentsMargins(0, 0, 0, 0)

        stats = [
            ("📋", str(n_protocols), "Protocols",    Colors.ACCENT),
            ("🗂", str(n_templates), "Templates",    Colors.ACCENT_LIGHT),
            ("🗓", str(n_schedule),  "Scheduled",    Colors.WARNING),
            ("📓", str(n_runs),      "Run records",  Colors.SUCCESS),
        ]
        for col_idx, (icon, val, lbl, color) in enumerate(stats):
            card = _StatCard(icon, val, lbl, color)
            grid.addWidget(card, 0, col_idx)
        root.addLayout(grid)
        root.addSpacing(30)

        # ── Quick access ──────────────────────────────────────────────────────
        qa_lbl = QLabel("Quick access")
        qa_lbl.setStyleSheet(
            f"color: {Colors.TEXT_PRIMARY}; font-size: {Fonts.SIZE_XL}px;"
            f"font-weight: 700;"
        )
        root.addWidget(qa_lbl)
        root.addSpacing(10)

        qa_row = QHBoxLayout()
        qa_row.setSpacing(14)
        for label, page, emoji in [
            ("Protocol Library", "library",  "📋"),
            ("Run Mode",         "run",      "▶"),
            ("Schedule",         "schedule", "🗓"),
            ("Lab Notebook",     "history",  "📓"),
        ]:
            qa_row.addWidget(_quick_card(emoji, label, page, self.app))
        root.addLayout(qa_row)
        root.addStretch()

        self._root_layout.addWidget(scroll)

    def on_show(self) -> None:
        if self._needs_refresh:
            self._rebuild()
        else:
            # Always rebuild on show to pick up any changes since last visit
            self._rebuild()
