"""
Schedule page — Phase 2: read-only list of scheduled experiments.

Shows scheduled experiment blocks grouped by date.
Full calendar drag-and-drop in Phase 4.
"""
from __future__ import annotations

from datetime import datetime
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QScrollArea,
    QSizePolicy, QVBoxLayout, QWidget,
)

from qt_app.theme import Colors, Fonts, Radii
from qt_app.components.widgets import HSeparator, PageTitle, SubLabel
from qt_app.views.base_page import BasePage


# Status colors
STATUS_COLORS = {
    "planned":   (Colors.ACCENT,   "rgba(59,130,246,0.15)"),
    "running":   (Colors.SUCCESS,  "rgba(34,197,94,0.15)"),
    "completed": (Colors.TEXT_MUTED, Colors.BG_CARD_HOV),
    "cancelled": (Colors.DANGER,   "rgba(239,68,68,0.15)"),
}


def _status_badge(status: str) -> QLabel:
    fg, bg = STATUS_COLORS.get(status, (Colors.TEXT_SECOND, Colors.BG_CARD_HOV))
    lbl = QLabel(status.title())
    lbl.setStyleSheet(
        f"color: {fg}; background: {bg};"
        f"border-radius: 6px; padding: 2px 8px;"
        f"font-size: {Fonts.SIZE_XS}px; font-weight: 600;"
    )
    return lbl


class ScheduleCard(QFrame):
    """One scheduled experiment block."""

    def __init__(self, block: dict, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("Card")
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._build(block)

    def _build(self, b: dict) -> None:
        lay = QVBoxLayout(self)
        lay.setContentsMargins(18, 14, 18, 14)
        lay.setSpacing(6)

        # Row 1: title + status
        row1 = QHBoxLayout()
        row1.setSpacing(10)

        title = b.get("title", "") or b.get("protocolName", "Experiment")
        title_lbl = QLabel(title)
        title_lbl.setStyleSheet(
            f"color: {Colors.TEXT_PRIMARY};"
            f"font-size: {Fonts.SIZE_MD}px; font-weight: 700;"
        )
        row1.addWidget(title_lbl, stretch=1)
        row1.addWidget(_status_badge(b.get("status", "planned")))
        lay.addLayout(row1)

        # Row 2: protocol name
        proto_name = b.get("protocolName", "")
        if proto_name and proto_name != title:
            p_lbl = QLabel(f"📋  {proto_name}")
            p_lbl.setStyleSheet(
                f"color: {Colors.TEXT_SECOND}; font-size: {Fonts.SIZE_SM}px;"
            )
            lay.addWidget(p_lbl)

        # Row 3: date + time range
        date_str = b.get("date", "")
        planned_start = b.get("plannedStart", 0)
        planned_end   = b.get("plannedEnd", 0)

        time_parts = []
        if date_str:
            try:
                date_display = datetime.strptime(date_str, "%Y-%m-%d").strftime("%b %d, %Y")
            except ValueError:
                date_display = date_str
            time_parts.append(f"📅  {date_display}")

        if planned_start and planned_end:
            try:
                s = datetime.fromtimestamp(planned_start / 1000).strftime("%H:%M")
                e = datetime.fromtimestamp(planned_end   / 1000).strftime("%H:%M")
                dur_min = max(0, (planned_end - planned_start) // 60_000)
                h, m = divmod(dur_min, 60)
                dur_str = f"{h}h {m}m" if h else f"{m}m"
                time_parts.append(f"🕐  {s} – {e}  ({dur_str})")
            except Exception:
                pass

        if time_parts:
            t_lbl = QLabel("   ".join(time_parts))
            t_lbl.setStyleSheet(
                f"color: {Colors.TEXT_SECOND}; font-size: {Fonts.SIZE_SM}px;"
            )
            lay.addWidget(t_lbl)

        # Notes
        notes = b.get("notes", "").strip()
        if notes:
            n_lbl = QLabel(f"📝  {notes[:100]}{'…' if len(notes) > 100 else ''}")
            n_lbl.setStyleSheet(
                f"color: {Colors.TEXT_MUTED}; font-size: {Fonts.SIZE_SM}px;"
            )
            n_lbl.setWordWrap(True)
            lay.addWidget(n_lbl)


def _empty_state(msg: str) -> QWidget:
    w = QWidget()
    lay = QVBoxLayout(w)
    lay.setAlignment(Qt.AlignmentFlag.AlignCenter)
    lay.setSpacing(12)

    icon = QLabel("🗓")
    icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
    icon.setStyleSheet("font-size: 48px;")
    lay.addWidget(icon)

    lbl = QLabel(msg)
    lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
    lbl.setWordWrap(True)
    lbl.setStyleSheet(
        f"color: {Colors.TEXT_SECOND}; font-size: {Fonts.SIZE_MD}px;"
    )
    lay.addWidget(lbl)

    badge = QLabel("Full calendar view: Phase 4")
    badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
    badge.setStyleSheet(
        f"color: {Colors.ACCENT_LIGHT}; background: rgba(59,130,246,0.15);"
        f"border-radius: 8px; padding: 4px 14px;"
        f"font-size: {Fonts.SIZE_SM}px; font-weight: 600;"
    )
    lay.addWidget(badge)
    return w


class SchedulePage(BasePage):
    """Schedule page — Phase 2 read-only list."""

    def __init__(self, app: "BenchFlowApp", parent: QWidget | None = None) -> None:  # type: ignore[name-defined]
        super().__init__(app, parent)
        self._build_shell()
        self._load_data()

    def _build_shell(self) -> None:
        outer = QVBoxLayout()
        outer.setContentsMargins(32, 32, 32, 0)
        outer.setSpacing(0)

        # Header
        hdr = QHBoxLayout()
        hdr.addWidget(PageTitle("Schedule"))
        hdr.addStretch()
        outer.addLayout(hdr)
        outer.addSpacing(4)
        outer.addWidget(SubLabel("Scheduled experiments. Full calendar view in Phase 4."))
        outer.addSpacing(16)
        outer.addWidget(HSeparator())
        outer.addSpacing(16)

        # Scroll
        self._scroll = QScrollArea()
        self._scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._scroll.setWidgetResizable(True)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._scroll.setStyleSheet(f"background: {Colors.BG_PAGE};")

        self._content = QWidget()
        self._content.setStyleSheet(f"background: {Colors.BG_PAGE};")
        self._cl = QVBoxLayout(self._content)
        self._cl.setContentsMargins(0, 0, 16, 32)
        self._cl.setSpacing(0)
        self._scroll.setWidget(self._content)
        outer.addWidget(self._scroll, stretch=1)
        self._root_layout.addLayout(outer)

    def _load_data(self) -> None:
        while self._cl.count():
            item = self._cl.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        blocks = self.app.data.load_schedule()

        if not blocks:
            self._cl.addStretch()
            self._cl.addWidget(_empty_state("No experiments scheduled yet."))
            self._cl.addStretch()
            return

        # Sort by date + plannedStart
        def _sort_key(b: dict):
            date = b.get("date", "9999-12-31")
            start = b.get("plannedStart", 0) or 0
            return (date, start)

        blocks = sorted(blocks, key=_sort_key)

        # Group by date
        by_date: dict[str, list[dict]] = {}
        for b in blocks:
            date = b.get("date", "Unknown")
            by_date.setdefault(date, []).append(b)

        # Today marker
        today = datetime.now().strftime("%Y-%m-%d")

        for date, items in by_date.items():
            # Date header
            try:
                date_display = datetime.strptime(date, "%Y-%m-%d").strftime("%B %d, %Y")
            except ValueError:
                date_display = date

            hdr_row = QHBoxLayout()
            hdr_row.setSpacing(10)

            d_lbl = QLabel(date_display)
            d_lbl.setStyleSheet(
                f"color: {Colors.TEXT_PRIMARY}; font-size: {Fonts.SIZE_MD}px; font-weight: 700;"
            )
            hdr_row.addWidget(d_lbl)

            if date == today:
                today_badge = QLabel("TODAY")
                today_badge.setStyleSheet(
                    f"color: {Colors.SUCCESS}; background: rgba(34,197,94,0.15);"
                    f"border-radius: 6px; padding: 2px 8px;"
                    f"font-size: {Fonts.SIZE_XS}px; font-weight: 700;"
                )
                hdr_row.addWidget(today_badge)
            hdr_row.addStretch()

            hdr_widget = QWidget()
            hdr_widget.setLayout(hdr_row)
            self._cl.addWidget(hdr_widget)
            self._cl.addSpacing(8)

            for b in items:
                card = ScheduleCard(b, parent=self._content)
                self._cl.addWidget(card)
                self._cl.addSpacing(8)
            self._cl.addSpacing(16)

        self._cl.addStretch()

    def on_show(self) -> None:
        self._load_data()
