"""
Lab Notebook / History page — Phase 2: read-only run record list.

Shows saved run sessions grouped by date.
Full rich-text editing and export in Phase 7.
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


# Step record status colors
STEP_STATUS_COLORS: dict[str, str] = {
    "completed": Colors.SUCCESS,
    "skipped":   Colors.WARNING,
    "pending":   Colors.TEXT_MUTED,
    "idle":      Colors.TEXT_MUTED,
}


class RunRecordCard(QFrame):
    """Card showing one completed run record."""

    def __init__(self, record: dict, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("Card")
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._build(record)

    def _build(self, r: dict) -> None:
        lay = QVBoxLayout(self)
        lay.setContentsMargins(18, 14, 18, 14)
        lay.setSpacing(8)

        # Row 1: title + duration
        row1 = QHBoxLayout()
        row1.setSpacing(12)

        title = r.get("title", r.get("protocolName", "Run"))
        title_lbl = QLabel(f"📓  {title}")
        title_lbl.setStyleSheet(
            f"color: {Colors.TEXT_PRIMARY};"
            f"font-size: {Fonts.SIZE_MD}px; font-weight: 700;"
        )
        row1.addWidget(title_lbl, stretch=1)

        # Duration
        actual_dur = float(r.get("actualDuration", 0))
        started_at = r.get("startedAt", 0)
        ended_at   = r.get("endedAt", 0)
        if actual_dur <= 0 and started_at and ended_at:
            actual_dur = max(0, (ended_at - started_at) / 1000)
        if actual_dur > 0:
            h, rem = divmod(int(actual_dur), 3600)
            m, _s = divmod(rem, 60)
            dur_str = f"{h}h {m}m" if h else f"{m}m"
            dur_lbl = QLabel(f"⏱ {dur_str}")
            dur_lbl.setStyleSheet(
                f"color: {Colors.TEXT_SECOND}; font-size: {Fonts.SIZE_SM}px;"
            )
            row1.addWidget(dur_lbl)
        lay.addLayout(row1)

        # Row 2: protocol name + timestamp
        proto_name = r.get("protocolName", "")
        if proto_name and proto_name not in title:
            p_lbl = QLabel(f"📋  {proto_name}")
            p_lbl.setStyleSheet(
                f"color: {Colors.TEXT_SECOND}; font-size: {Fonts.SIZE_SM}px;"
            )
            lay.addWidget(p_lbl)

        # Time range
        if started_at:
            try:
                s_dt = datetime.fromtimestamp(started_at / 1000).strftime("%H:%M")
                e_dt = datetime.fromtimestamp(ended_at   / 1000).strftime("%H:%M") if ended_at else "—"
                time_lbl = QLabel(f"🕐  {s_dt} – {e_dt}")
                time_lbl.setStyleSheet(
                    f"color: {Colors.TEXT_MUTED}; font-size: {Fonts.SIZE_SM}px;"
                )
                lay.addWidget(time_lbl)
            except Exception:
                pass

        # Step records summary
        step_records = r.get("stepRecords", [])
        if step_records:
            completed = sum(1 for s in step_records if s.get("status") == "completed")
            total = len(step_records)
            pct = int(completed / total * 100) if total else 0

            sr_row = QHBoxLayout()
            sr_row.setSpacing(8)

            prog_lbl = QLabel(f"Steps: {completed}/{total} ({pct}%)")
            prog_lbl.setStyleSheet(
                f"color: {Colors.TEXT_SECOND}; font-size: {Fonts.SIZE_SM}px;"
            )
            sr_row.addWidget(prog_lbl)

            # Mini step dots (up to 20)
            dot_widget = QWidget()
            dot_layout = QHBoxLayout(dot_widget)
            dot_layout.setContentsMargins(0, 0, 0, 0)
            dot_layout.setSpacing(3)
            for s in step_records[:20]:
                status = s.get("status", "idle")
                color = STEP_STATUS_COLORS.get(status, Colors.TEXT_MUTED)
                dot = QLabel("●")
                dot.setStyleSheet(f"color: {color}; font-size: 8px;")
                dot_layout.addWidget(dot)
            if len(step_records) > 20:
                more = QLabel(f"+{len(step_records)-20}")
                more.setStyleSheet(f"color: {Colors.TEXT_MUTED}; font-size: 9px;")
                dot_layout.addWidget(more)
            dot_layout.addStretch()
            sr_row.addWidget(dot_widget)
            sr_row.addStretch()
            lay.addLayout(sr_row)

        # Observations / notes
        obs = r.get("observations", "").strip() or r.get("notes", "").strip()
        if obs:
            obs_lbl = QLabel(f"💬  {obs[:120]}{'…' if len(obs) > 120 else ''}")
            obs_lbl.setStyleSheet(
                f"color: {Colors.TEXT_MUTED}; font-size: {Fonts.SIZE_SM}px;"
            )
            obs_lbl.setWordWrap(True)
            lay.addWidget(obs_lbl)

        # Tags
        tags = r.get("tags", [])
        if tags:
            tags_row = QHBoxLayout()
            tags_row.setSpacing(6)
            for tag in tags[:5]:
                t_lbl = QLabel(f"#{tag}")
                t_lbl.setStyleSheet(
                    f"color: {Colors.TEXT_MUTED}; background: {Colors.BG_CARD_HOV};"
                    f"border-radius: 5px; padding: 1px 6px;"
                    f"font-size: {Fonts.SIZE_XS}px;"
                )
                tags_row.addWidget(t_lbl)
            tags_row.addStretch()
            lay.addLayout(tags_row)


def _date_group_header(date_display: str) -> QWidget:
    w = QWidget()
    lay = QHBoxLayout(w)
    lay.setContentsMargins(0, 0, 0, 0)
    lay.setSpacing(12)

    lbl = QLabel(date_display)
    lbl.setStyleSheet(
        f"color: {Colors.TEXT_PRIMARY}; font-size: {Fonts.SIZE_MD}px; font-weight: 700;"
    )
    lay.addWidget(lbl)
    lay.addStretch()
    return w


def _empty_state() -> QWidget:
    w = QWidget()
    lay = QVBoxLayout(w)
    lay.setAlignment(Qt.AlignmentFlag.AlignCenter)
    lay.setSpacing(12)

    icon = QLabel("📓")
    icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
    icon.setStyleSheet("font-size: 48px;")
    lay.addWidget(icon)

    lbl = QLabel("No run records yet.\nComplete a protocol run to see it here.")
    lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
    lbl.setWordWrap(True)
    lbl.setStyleSheet(
        f"color: {Colors.TEXT_SECOND}; font-size: {Fonts.SIZE_MD}px;"
    )
    lay.addWidget(lbl)

    badge = QLabel("Full export & rich-text editing: Phase 7")
    badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
    badge.setStyleSheet(
        f"color: {Colors.ACCENT_LIGHT}; background: rgba(59,130,246,0.15);"
        f"border-radius: 8px; padding: 4px 14px;"
        f"font-size: {Fonts.SIZE_SM}px; font-weight: 600;"
    )
    lay.addWidget(badge)
    return w


class HistoryPage(BasePage):
    """Lab Notebook — shows completed run records grouped by date."""

    def __init__(self, app: "BenchFlowApp", parent: QWidget | None = None) -> None:  # type: ignore[name-defined]
        super().__init__(app, parent)
        self._build_shell()
        self._load_data()

    def _build_shell(self) -> None:
        outer = QVBoxLayout()
        outer.setContentsMargins(32, 32, 32, 0)
        outer.setSpacing(0)

        hdr = QHBoxLayout()
        hdr.addWidget(PageTitle("Lab Notebook"))
        hdr.addStretch()
        outer.addLayout(hdr)
        outer.addSpacing(4)
        outer.addWidget(SubLabel("Completed run records. Export and rich text in Phase 7."))
        outer.addSpacing(16)
        outer.addWidget(HSeparator())
        outer.addSpacing(16)

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

        records = self.app.data.load_runs()

        if not records:
            self._cl.addStretch()
            self._cl.addWidget(_empty_state())
            self._cl.addStretch()
            return

        # Sort by startedAt descending (newest first)
        records_sorted = sorted(
            records,
            key=lambda r: r.get("startedAt", 0) or 0,
            reverse=True,
        )

        # Group by date
        by_date: dict[str, list[dict]] = {}
        for r in records_sorted:
            started_at = r.get("startedAt", 0)
            if started_at:
                try:
                    date_key = datetime.fromtimestamp(started_at / 1000).strftime("%Y-%m-%d")
                except Exception:
                    date_key = "Unknown"
            else:
                date_key = "Unknown"
            by_date.setdefault(date_key, []).append(r)

        for date_key, items in by_date.items():
            # Date header
            if date_key != "Unknown":
                try:
                    date_display = datetime.strptime(date_key, "%Y-%m-%d").strftime("%B %d, %Y")
                except ValueError:
                    date_display = date_key
            else:
                date_display = "Unknown Date"

            self._cl.addWidget(_date_group_header(date_display))
            self._cl.addSpacing(8)

            for r in items:
                card = RunRecordCard(r, parent=self._content)
                self._cl.addWidget(card)
                self._cl.addSpacing(8)
            self._cl.addSpacing(20)

        self._cl.addStretch()

    def on_show(self) -> None:
        self._load_data()
