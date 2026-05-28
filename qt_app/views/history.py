"""
Lab Notebook — Phase 7: full record viewer and editor.

Layout
------
HistoryPage
├── Header row: title, subtitle, [📤 Export (disabled)]
├── Toolbar:  🔍 search  |  Protocol filter  |  date range (future)
├── HSeparator
└── QSplitter (horizontal)
    ├── Left: _RecordCard list (date-grouped, scrollable)
    └── Right: _DetailPanel
        ├── placeholder   ← nothing selected
        └── record detail
            ├── editable title  +  date/time stamp
            ├── protocol badge + category + tags
            ├── stats: steps · completed · skipped · duration
            ├── progress bar
            ├── 📋 Step Records table (planned vs actual)
            ├── 📜 Timeline log
            ├── editable Observations / Notes
            └── actions: [Duplicate] [Delete] [📤 Export (coming soon)]

Data compatibility
------------------
- Reads runs.json  (CTk-compatible format)
- Adds `summary` field when saving edits (ignored by CTk)
- Never modifies fields CTk writes (title, stepRecords, timeline, etc.)
"""
from __future__ import annotations

import copy
import time
import uuid
from datetime import datetime, date
from typing import Any

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QComboBox, QFileDialog, QFrame, QHBoxLayout, QLabel,
    QGraphicsDropShadowEffect, QMenu, QMessageBox, QPlainTextEdit, QPushButton,
    QScrollArea, QSizePolicy, QSplitter,
    QVBoxLayout, QWidget, QLineEdit,
)

from qt_app.theme import Colors, Fonts, Radii
from qt_app.components.widgets import (
    HSeparator, PageTitle, SubLabel, PrimaryButton,
)
from qt_app.components.toast import ToastManager
from qt_app.services.event_bus import bus
from qt_app.services.perf import perf
from qt_app.views.base_page import BasePage


# ── Helpers ───────────────────────────────────────────────────────────────────

_STATUS_COLOR = {
    "completed":    Colors.SUCCESS,
    "skipped":      Colors.WARNING,
    "pending":      Colors.TEXT_MUTED,
    "idle":         Colors.TEXT_MUTED,
    "in_progress":  Colors.ACCENT,
    "incomplete":   Colors.DANGER,
}

_STATUS_ICON = {
    "completed":   "✓",
    "skipped":     "→",
    "pending":     "○",
    "idle":        "○",
    "in_progress": "◷",
    "incomplete":  "✗",
}


def _lbl(text: str, color: str = Colors.TEXT_PRIMARY,
         size: int = Fonts.SIZE_SM, bold: bool = False,
         wrap: bool = False) -> QLabel:
    lbl = QLabel(text)
    style = f"color: {color}; font-size: {size}px;"
    if bold:
        style += " font-weight: 700;"
    lbl.setStyleSheet(style)
    if wrap:
        lbl.setWordWrap(True)
    return lbl


def _badge(text: str, fg: str, bg: str) -> QLabel:
    lbl = QLabel(text)
    lbl.setStyleSheet(
        f"color: {fg}; background: {bg}; border-radius: 6px;"
        f"padding: 2px 8px; font-size: {Fonts.SIZE_XS}px; font-weight: 600;"
    )
    return lbl


def _sec_duration(secs: float) -> str:
    """Format seconds → 'Xh Ym' or 'Ym Xs'."""
    s = int(secs)
    if s <= 0:
        return "—"
    h, rem = divmod(s, 3600)
    m, sec = divmod(rem, 60)
    if h:
        return f"{h}h {m}m" if m else f"{h}h"
    if m:
        return f"{m}m {sec}s" if sec else f"{m}m"
    return f"{sec}s"


def _record_date_key(record: dict) -> str:
    ts = record.get("startedAt", 0)
    if not ts:
        return "unknown"
    try:
        return datetime.fromtimestamp(ts / 1000).strftime("%Y-%m-%d")
    except Exception:
        return "unknown"


def _fmt_ts(ts_ms: int | float | None, fmt: str = "%H:%M") -> str:
    if not ts_ms:
        return "—"
    try:
        return datetime.fromtimestamp(float(ts_ms) / 1000).strftime(fmt)
    except Exception:
        return "—"


def _fmt_date_header(date_str: str) -> str:
    """'2026-05-20' → 'Tuesday · May 20, 2026'."""
    if date_str == "unknown":
        return "Unknown Date"
    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        today = date.today()
        d = dt.date()
        if d == today:
            return f"Today · {dt.strftime('%B %d, %Y')}"
        delta = (today - d).days
        if delta == 1:
            return f"Yesterday · {dt.strftime('%B %d, %Y')}"
        return dt.strftime("%A · %B %d, %Y")
    except Exception:
        return date_str


def _step_stats(records: list[dict]) -> tuple[int, int, int]:
    """Return (total, completed, skipped)."""
    total     = len(records)
    completed = sum(1 for s in records if s.get("status") == "completed")
    skipped   = sum(1 for s in records if s.get("status") == "skipped")
    return total, completed, skipped


def _actual_duration(record: dict) -> float:
    """Actual duration in seconds (best effort)."""
    d = float(record.get("actualDuration", 0))
    if d > 0:
        return d
    s = record.get("startedAt", 0)
    e = record.get("endedAt", 0)
    if s and e:
        return max(0, (e - s) / 1000)
    return 0.0


def _clear_layout(layout) -> None:
    while layout.count():
        item = layout.takeAt(0)
        w = item.widget()
        if w:
            w.deleteLater()
        elif item.layout():
            _clear_layout(item.layout())


# ── _RecordCard ───────────────────────────────────────────────────────────────

class _RecordCard(QFrame):
    """Compact left-panel card for one run record."""

    clicked = Signal(dict)

    @staticmethod
    def _style(selected: bool) -> str:
        if selected:
            return (
                f"QFrame {{ background: {Colors.SELECTED_BG};"
                f"  border-radius: {Radii.LG}px;"
                f"  border: 1px solid {Colors.BORDER};"
                f"  border-left: 3px solid {Colors.ACCENT}; }}"
            )
        return (
            f"QFrame {{ background: {Colors.BG_ELEVATED}; border-radius: {Radii.LG}px;"
            f"  border: 1px solid {Colors.BORDER}; }}"
            f"QFrame:hover {{ background: {Colors.HOVER_BG}; border-color: {Colors.BORDER}; }}"
        )

    def __init__(self, record: dict, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._record = record
        self._sel    = False
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(12)
        shadow.setOffset(0, 3)
        shadow.setColor(QColor(17, 24, 39, 12))
        self.setGraphicsEffect(shadow)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setStyleSheet(self._style(False))
        self._build()

    def _build(self) -> None:
        r   = self._record
        lay = QVBoxLayout(self)
        lay.setContentsMargins(14, 10, 14, 10)
        lay.setSpacing(4)

        # Row 1: title + duration
        r1 = QHBoxLayout()
        r1.setSpacing(6)
        title = r.get("title", r.get("protocolName", "Run"))
        tl = QLabel(title)
        tl.setStyleSheet(
            f"color: {Colors.TEXT_PRIMARY}; font-size: {Fonts.SIZE_SM}px;"
            f"font-weight: 700;"
        )
        tl.setWordWrap(False)
        tl.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        r1.addWidget(tl, stretch=1)

        dur = _actual_duration(r)
        if dur > 0:
            dl = QLabel(_sec_duration(dur))
            dl.setStyleSheet(f"color: {Colors.TEXT_MUTED}; font-size: {Fonts.SIZE_XS}px;")
            r1.addWidget(dl)
        lay.addLayout(r1)

        # Row 2: protocol name + time range
        r2 = QHBoxLayout()
        r2.setSpacing(6)
        proto = r.get("protocolName", "")
        if proto:
            r2.addWidget(_badge(proto, Colors.ACCENT, Colors.ACCENT_BG))
        t_start = _fmt_ts(r.get("startedAt"))
        t_end   = _fmt_ts(r.get("endedAt"))
        if t_start != "—":
            tl2 = QLabel(f"{t_start}–{t_end}")
            tl2.setStyleSheet(f"color: {Colors.TEXT_MUTED}; font-size: {Fonts.SIZE_XS}px;")
            r2.addWidget(tl2)
        r2.addStretch()
        lay.addLayout(r2)

        # Row 3: step dots
        step_records = r.get("stepRecords", [])
        if step_records:
            total, done, skip = _step_stats(step_records)
            pct = int(done / total * 100) if total else 0

            r3 = QHBoxLayout()
            r3.setSpacing(3)
            # Up to 24 dots
            for s in step_records[:24]:
                status = s.get("status", "idle")
                color  = _STATUS_COLOR.get(status, Colors.TEXT_MUTED)
                dot = QLabel("●")
                dot.setStyleSheet(f"color: {color}; font-size: 7px;")
                r3.addWidget(dot)
            if len(step_records) > 24:
                more = QLabel(f"+{len(step_records)-24}")
                more.setStyleSheet(f"color: {Colors.TEXT_MUTED}; font-size: 8px;")
                r3.addWidget(more)
            r3.addStretch()

            pct_lbl = QLabel(f"{pct}%")
            pct_lbl.setStyleSheet(
                f"color: {'#22c55e' if pct == 100 else Colors.TEXT_SECOND};"
                f"font-size: {Fonts.SIZE_XS}px; font-weight: 600;"
            )
            r3.addWidget(pct_lbl)
            lay.addLayout(r3)

        # Observations snippet
        obs = (r.get("observations") or r.get("notes") or "").strip()
        if obs:
            ol = QLabel(f"💬  {obs[:90]}{'…' if len(obs) > 90 else ''}")
            ol.setStyleSheet(f"color: {Colors.TEXT_MUTED}; font-size: {Fonts.SIZE_XS}px;")
            ol.setWordWrap(True)
            lay.addWidget(ol)

    def set_selected(self, sel: bool) -> None:
        self._sel = sel
        self.setStyleSheet(self._style(sel))

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self._record)
        super().mousePressEvent(event)


# ── _DetailPanel ──────────────────────────────────────────────────────────────

class _DetailPanel(QWidget):
    """Right-side detail panel."""

    save_requested      = Signal(dict)   # updated record dict
    delete_requested    = Signal(dict)
    duplicate_requested = Signal(dict)
    export_requested    = Signal(dict, str)  # (record, fmt) — "pdf" | "docx" | "json"

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setMinimumWidth(320)
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
        self._lay.setContentsMargins(20, 20, 20, 32)
        self._lay.setSpacing(0)
        self._scroll.setWidget(self._inner)

        self._record: dict | None = None
        self._dirty: bool = False
        self._title_edit: QLineEdit | None = None
        self._obs_edit: QPlainTextEdit | None = None
        self._notes_edit: QPlainTextEdit | None = None
        self._summary_edit: QPlainTextEdit | None = None
        self._dirty_lbl: QLabel | None = None
        self._save_btn: QPushButton | None = None

        self._show_placeholder()

    # ── Public API ────────────────────────────────────────────────────────────

    def show_record(self, record: dict) -> None:
        self._record = record
        self._dirty  = False
        self._clear()
        lay = self._lay

        # ── Title (editable) ──────────────────────────────────────────────────
        title_lbl = _lbl("Session Title", Colors.TEXT_MUTED, Fonts.SIZE_XS)
        lay.addWidget(title_lbl)
        lay.addSpacing(3)

        self._title_edit = QLineEdit(record.get("title", ""))
        self._title_edit.setFixedHeight(38)
        self._title_edit.setStyleSheet(
            f"QLineEdit {{ background: {Colors.BG_INPUT}; color: {Colors.TEXT_PRIMARY};"
            f"  border: 1px solid {Colors.BORDER_LIGHT}; border-radius: {Radii.LG}px;"
            f"  padding: 0 10px; font-size: {Fonts.SIZE_MD}px; font-weight: 700; }}"
            f"QLineEdit:focus {{ border-color: {Colors.ACCENT}; }}"
        )
        self._title_edit.textChanged.connect(self._on_changed)
        lay.addWidget(self._title_edit)
        lay.addSpacing(10)

        # ── Date/time + duration ──────────────────────────────────────────────
        started_at = record.get("startedAt", 0)
        ended_at   = record.get("endedAt", 0)
        dur        = _actual_duration(record)

        if started_at:
            date_str  = _fmt_ts(started_at, "%B %d, %Y")
            t_start   = _fmt_ts(started_at, "%H:%M")
            t_end     = _fmt_ts(ended_at,   "%H:%M")
            info_parts = [f"📅  {date_str}", f"⏰  {t_start} – {t_end}"]
            if dur > 0:
                info_parts.append(f"⏱  {_sec_duration(dur)}")
            info_lbl = _lbl("  ·  ".join(info_parts), Colors.TEXT_SECOND,
                             Fonts.SIZE_SM, wrap=True)
            lay.addWidget(info_lbl)
            lay.addSpacing(8)

        # ── Protocol badge ────────────────────────────────────────────────────
        proto_name = record.get("protocolName", "")
        if proto_name:
            p_row = QHBoxLayout()
            p_row.setSpacing(6)
            p_row.addWidget(_lbl("Protocol:", Colors.TEXT_MUTED, Fonts.SIZE_XS))
            p_row.addWidget(_badge(proto_name, Colors.ACCENT, Colors.ACCENT_BG))
            snap = record.get("protocolSnapshot", {})
            cat  = snap.get("category", "")
            if cat:
                p_row.addWidget(_badge(cat, Colors.TEXT_SECOND, Colors.BG_SURFACE_ALT))
            p_row.addStretch()
            lay.addLayout(p_row)
            lay.addSpacing(8)

        # Tags
        tags = record.get("tags", [])
        if tags:
            t_row = QHBoxLayout()
            t_row.setSpacing(4)
            for tag in tags:
                t_row.addWidget(_badge(f"#{tag}", Colors.TEXT_SECOND, Colors.BG_SURFACE_ALT))
            t_row.addStretch()
            lay.addLayout(t_row)
            lay.addSpacing(8)

        lay.addWidget(HSeparator())
        lay.addSpacing(10)

        # ── Stats row ─────────────────────────────────────────────────────────
        step_records = record.get("stepRecords", [])
        total, done, skipped = _step_stats(step_records)
        incomplete = total - done - skipped
        pct = int(done / total * 100) if total else 0

        stats_row = QHBoxLayout()
        stats_row.setSpacing(0)
        for label, val, color in [
            ("Steps",      str(total),    Colors.TEXT_PRIMARY),
            ("Completed",  str(done),     Colors.SUCCESS),
            ("Skipped",    str(skipped),  Colors.WARNING),
            ("Incomplete", str(incomplete), Colors.DANGER),
        ]:
            col = QVBoxLayout()
            col.setSpacing(1)
            col.setAlignment(Qt.AlignmentFlag.AlignHCenter)
            v = QLabel(val)
            v.setAlignment(Qt.AlignmentFlag.AlignHCenter)
            v.setStyleSheet(f"color: {color}; font-size: {Fonts.SIZE_LG}px; font-weight: 700;")
            k = QLabel(label)
            k.setAlignment(Qt.AlignmentFlag.AlignHCenter)
            k.setStyleSheet(f"color: {Colors.TEXT_MUTED}; font-size: {Fonts.SIZE_XS}px;")
            col.addWidget(v)
            col.addWidget(k)
            stats_row.addLayout(col)
            stats_row.addStretch()
        lay.addLayout(stats_row)
        lay.addSpacing(8)

        # Progress bar (CSS-only)
        prog_bg = QFrame()
        prog_bg.setFixedHeight(8)
        prog_bg.setStyleSheet(
            f"QFrame {{ background: {Colors.BORDER_LIGHT}; border-radius: 4px; }}"
        )
        prog_fg = QFrame(prog_bg)
        prog_fg.setFixedHeight(8)
        bar_color = Colors.SUCCESS if pct == 100 else Colors.ACCENT
        w = max(4, int(pct / 100 * 400))   # will be overridden by resizing
        prog_fg.setStyleSheet(
            f"QFrame {{ background: {bar_color}; border-radius: 4px; }}"
        )
        # Use a QHBoxLayout with a stretch so the bar fills proportionally
        prog_lay = QHBoxLayout(prog_bg)
        prog_lay.setContentsMargins(0, 0, 0, 0)
        prog_lay.setSpacing(0)
        pct_fill = QFrame()
        pct_fill.setFixedHeight(8)
        pct_fill.setStyleSheet(f"QFrame {{ background: {bar_color}; border-radius: 4px; }}")
        prog_lay.addWidget(pct_fill, stretch=max(1, pct))
        if pct < 100:
            prog_lay.addStretch(100 - pct)

        lay.addWidget(prog_bg)
        pct_lbl = _lbl(f"{pct}% complete", Colors.TEXT_MUTED, Fonts.SIZE_XS)
        pct_lbl.setAlignment(Qt.AlignmentFlag.AlignRight)
        lay.addWidget(pct_lbl)
        lay.addSpacing(12)

        lay.addWidget(HSeparator())
        lay.addSpacing(10)

        # ── Summary (editable) ────────────────────────────────────────────────
        lay.addWidget(_lbl("📝  Summary / Observations", Colors.TEXT_SECOND,
                           Fonts.SIZE_XS, bold=True))
        lay.addSpacing(4)

        self._obs_edit = QPlainTextEdit()
        self._obs_edit.setPlainText(
            record.get("observations") or record.get("notes") or ""
        )
        self._obs_edit.setPlaceholderText("What happened? Key observations, anomalies…")
        self._obs_edit.setMinimumHeight(80)
        self._obs_edit.setMaximumHeight(180)
        self._obs_edit.setStyleSheet(
            f"QPlainTextEdit {{ background: {Colors.BG_INPUT}; color: {Colors.TEXT_PRIMARY};"
            f"  border: 1px solid {Colors.BORDER_LIGHT}; border-radius: {Radii.MD}px;"
            f"  padding: 8px 10px; font-size: {Fonts.SIZE_SM}px; }}"
            f"QPlainTextEdit:focus {{ border-color: {Colors.ACCENT}; }}"
        )
        self._obs_edit.textChanged.connect(self._on_changed)
        lay.addWidget(self._obs_edit)
        lay.addSpacing(10)

        # ── Additional notes ──────────────────────────────────────────────────
        lay.addWidget(_lbl("💬  Additional Notes", Colors.TEXT_SECOND,
                           Fonts.SIZE_XS, bold=True))
        lay.addSpacing(4)
        self._notes_edit = QPlainTextEdit()
        self._notes_edit.setPlainText(record.get("summary", ""))
        self._notes_edit.setPlaceholderText("Free-form notes, next steps, follow-up…")
        self._notes_edit.setMinimumHeight(60)
        self._notes_edit.setMaximumHeight(120)
        self._notes_edit.setStyleSheet(
            f"QPlainTextEdit {{ background: {Colors.BG_INPUT}; color: {Colors.TEXT_PRIMARY};"
            f"  border: 1px solid {Colors.BORDER_LIGHT}; border-radius: {Radii.MD}px;"
            f"  padding: 8px 10px; font-size: {Fonts.SIZE_SM}px; }}"
            f"QPlainTextEdit:focus {{ border-color: {Colors.ACCENT}; }}"
        )
        self._notes_edit.textChanged.connect(self._on_changed)
        lay.addWidget(self._notes_edit)
        lay.addSpacing(8)

        # Dirty indicator + save
        save_row = QHBoxLayout()
        save_row.setSpacing(8)
        self._dirty_lbl = _lbl("", Colors.WARNING, Fonts.SIZE_XS)
        save_row.addWidget(self._dirty_lbl)
        save_row.addStretch()
        self._save_btn = QPushButton("Save Notes")
        self._save_btn.setFixedHeight(32)
        self._save_btn.setFixedWidth(110)
        self._save_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._save_btn.setEnabled(False)
        self._save_btn.setStyleSheet(
            f"QPushButton {{ background: {Colors.BORDER_LIGHT}; color: {Colors.TEXT_MUTED};"
            f"  border: none; border-radius: {Radii.LG}px; font-size: {Fonts.SIZE_SM}px; }}"
        )
        self._save_btn.clicked.connect(self._on_save_notes)
        save_row.addWidget(self._save_btn)
        lay.addLayout(save_row)

        lay.addSpacing(12)
        lay.addWidget(HSeparator())
        lay.addSpacing(10)

        # ── Step records table ────────────────────────────────────────────────
        if step_records:
            lay.addWidget(self._make_step_table(step_records))
            lay.addSpacing(12)
            lay.addWidget(HSeparator())
            lay.addSpacing(10)

        # ── Timeline log ──────────────────────────────────────────────────────
        timeline = record.get("timeline", [])
        if timeline:
            lay.addWidget(self._make_timeline(timeline))
            lay.addSpacing(12)
            lay.addWidget(HSeparator())
            lay.addSpacing(10)

        # ── Action buttons ────────────────────────────────────────────────────
        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)

        dup_btn = QPushButton("⧉  Duplicate")
        dup_btn.setFixedHeight(34)
        dup_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        dup_btn.setStyleSheet(
            f"QPushButton {{ background: {Colors.BG_CARD}; color: {Colors.TEXT_SECOND};"
            f"  border: 1px solid {Colors.BORDER_LIGHT}; border-radius: {Radii.LG}px;"
            f"  font-size: {Fonts.SIZE_SM}px; padding: 0 12px; }}"
            f"QPushButton:hover {{ background: {Colors.BG_CARD_HOV}; }}"
        )
        dup_btn.clicked.connect(lambda: self.duplicate_requested.emit(self._record))
        btn_row.addWidget(dup_btn)

        del_btn = QPushButton("✕  Delete")
        del_btn.setFixedHeight(34)
        del_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        del_btn.setStyleSheet(
            f"QPushButton {{ background: transparent; color: {Colors.DANGER};"
            f"  border: 1px solid {Colors.DANGER}; border-radius: {Radii.SM}px;"
            f"  font-size: {Fonts.SIZE_SM}px; padding: 0 12px; }}"
            f"QPushButton:hover {{ background: {Colors.DANGER_BG}; }}"
        )
        del_btn.clicked.connect(lambda: self.delete_requested.emit(self._record))
        btn_row.addWidget(del_btn)

        export_btn = QPushButton("📤  Export ▾")
        export_btn.setFixedHeight(34)
        export_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        export_btn.setToolTip("Export this session as PDF, Word, or JSON")
        export_btn.setStyleSheet(
            f"QPushButton {{ background: {Colors.BG_CARD}; color: {Colors.TEXT_SECOND};"
            f"  border: 1px solid {Colors.BORDER_LIGHT}; border-radius: {Radii.LG}px;"
            f"  font-size: {Fonts.SIZE_SM}px; padding: 0 12px; }}"
            f"QPushButton:hover {{ background: {Colors.BG_CARD_HOV}; }}"
        )
        _rec_ref = [None]  # mutable closure for current record

        def _show_export_menu():
            _rec = self._record
            if not _rec:
                return
            menu = QMenu(export_btn)
            menu.setStyleSheet(
                f"QMenu {{ background: {Colors.BG_CARD}; color: {Colors.TEXT_PRIMARY};"
                f"  border: 1px solid {Colors.BORDER_LIGHT}; border-radius: {Radii.MD}px;"
                f"  padding: 4px 0; }}"
                f"QMenu::item {{ padding: 6px 20px; font-size: {Fonts.SIZE_SM}px; }}"
                f"QMenu::item:selected {{ background: {Colors.SELECTED_BG}; color: {Colors.TEXT_PRIMARY}; }}"
            )
            menu.addAction("📄  PDF Report").triggered.connect(
                lambda: self.export_requested.emit(_rec, "pdf")
            )
            menu.addAction("📝  Word Document").triggered.connect(
                lambda: self.export_requested.emit(_rec, "docx")
            )
            menu.addAction("{ }  JSON Data").triggered.connect(
                lambda: self.export_requested.emit(_rec, "json")
            )
            menu.exec(export_btn.mapToGlobal(export_btn.rect().bottomLeft()))

        export_btn.clicked.connect(_show_export_menu)
        btn_row.addWidget(export_btn)
        btn_row.addStretch()
        lay.addLayout(btn_row)

        lay.addStretch()

    def show_placeholder(self) -> None:
        self._record = None
        self._clear()
        self._show_placeholder()

    # ── Section builders ──────────────────────────────────────────────────────

    def _make_step_table(self, step_records: list[dict]) -> QWidget:
        w = QWidget()
        w.setStyleSheet("background: transparent;")
        lay = QVBoxLayout(w)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(4)

        hdr_lbl = _lbl(f"📋  Step Records ({len(step_records)})",
                       Colors.TEXT_SECOND, Fonts.SIZE_XS, bold=True)
        lay.addWidget(hdr_lbl)
        lay.addSpacing(6)

        # Column headers
        col_hdr = QHBoxLayout()
        col_hdr.setSpacing(0)
        for text, stretch in [("#", 0), ("Step", 1), ("Planned", 0),
                               ("Actual", 0), ("Status", 0)]:
            lbl = QLabel(text)
            lbl.setStyleSheet(
                f"color: {Colors.TEXT_MUTED}; font-size: {Fonts.SIZE_XS}px;"
                f"font-weight: 600; padding: 2px 4px;"
            )
            if not stretch:
                lbl.setFixedWidth(56 if text in ("Planned", "Actual", "Status") else 22)
            else:
                lbl.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
            col_hdr.addWidget(lbl)
        lay.addLayout(col_hdr)
        lay.addWidget(HSeparator())

        for i, sr in enumerate(step_records):
            row = QHBoxLayout()
            row.setSpacing(0)

            # Number
            n_lbl = QLabel(f"{i+1}")
            n_lbl.setFixedWidth(22)
            n_lbl.setStyleSheet(f"color: {Colors.TEXT_MUTED}; font-size: {Fonts.SIZE_XS}px;"
                                f"padding: 3px 4px;")
            row.addWidget(n_lbl)

            # Title
            title_text = sr.get("stepTitle", f"Step {i+1}")
            t_lbl = QLabel(title_text)
            t_lbl.setStyleSheet(f"color: {Colors.TEXT_PRIMARY}; font-size: {Fonts.SIZE_XS}px;"
                                f"padding: 3px 4px;")
            t_lbl.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
            t_lbl.setWordWrap(False)
            row.addWidget(t_lbl, stretch=1)

            # Planned
            planned_s = float(sr.get("plannedSecs", 0))
            p_lbl = QLabel(_sec_duration(planned_s))
            p_lbl.setFixedWidth(56)
            p_lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            p_lbl.setStyleSheet(f"color: {Colors.TEXT_MUTED}; font-size: {Fonts.SIZE_XS}px;"
                                f"padding: 3px 4px;")
            row.addWidget(p_lbl)

            # Actual (usedSecs; 0 = no timer ran)
            used_s  = float(sr.get("usedSecs", 0))
            a_color = Colors.TEXT_MUTED
            if used_s > 0 and planned_s > 0:
                ratio = used_s / planned_s
                a_color = Colors.SUCCESS if ratio <= 1.1 else Colors.WARNING
            a_lbl = QLabel(_sec_duration(used_s) if used_s > 0 else "—")
            a_lbl.setFixedWidth(56)
            a_lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            a_lbl.setStyleSheet(f"color: {a_color}; font-size: {Fonts.SIZE_XS}px;"
                                f"padding: 3px 4px;")
            row.addWidget(a_lbl)

            # Status badge
            status = sr.get("status", "idle")
            s_icon  = _STATUS_ICON.get(status, "○")
            s_color = _STATUS_COLOR.get(status, Colors.TEXT_MUTED)
            s_lbl = QLabel(f"{s_icon} {status}")
            s_lbl.setFixedWidth(72)
            s_lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            s_lbl.setStyleSheet(
                f"color: {s_color}; font-size: {Fonts.SIZE_XS}px;"
                f"font-weight: 600; padding: 3px 4px;"
            )
            row.addWidget(s_lbl)

            # Step notes sub-row
            step_notes = sr.get("notes", "").strip()

            lay.addLayout(row)

            if step_notes:
                note_lbl = QLabel(f"   ↳ {step_notes[:100]}")
                note_lbl.setStyleSheet(
                    f"color: {Colors.TEXT_MUTED}; font-size: {Fonts.SIZE_XS}px;"
                    f"font-style: italic; padding: 0 4px 4px 26px;"
                )
                note_lbl.setWordWrap(True)
                lay.addWidget(note_lbl)

        return w

    def _make_timeline(self, timeline: list[dict]) -> QWidget:
        w = QWidget()
        w.setStyleSheet("background: transparent;")
        lay = QVBoxLayout(w)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(2)

        hdr = _lbl(f"📜  Timeline ({len(timeline)} events)",
                   Colors.TEXT_SECOND, Fonts.SIZE_XS, bold=True)
        lay.addWidget(hdr)
        lay.addSpacing(4)

        # Show all events
        for entry in timeline:
            t_str = entry.get("time", "")
            text  = entry.get("text", "")
            if not text:
                continue
            is_finish = "finish" in text.lower() or "saved" in text.lower()
            color = Colors.SUCCESS if is_finish else Colors.TEXT_SECOND

            e_row = QHBoxLayout()
            e_row.setSpacing(8)
            if t_str:
                tl = QLabel(t_str)
                tl.setFixedWidth(48)
                tl.setStyleSheet(
                    f"color: {Colors.TEXT_MUTED}; font-size: {Fonts.SIZE_XS}px;"
                )
                e_row.addWidget(tl)
            tl2 = QLabel(text)
            tl2.setStyleSheet(f"color: {color}; font-size: {Fonts.SIZE_XS}px;")
            tl2.setWordWrap(True)
            e_row.addWidget(tl2, stretch=1)
            lay.addLayout(e_row)

        return w

    # ── Dirty / save ─────────────────────────────────────────────────────────

    def _on_changed(self) -> None:
        if not self._dirty:
            self._dirty = True
            if self._dirty_lbl:
                self._dirty_lbl.setText("● Unsaved changes")
            if self._save_btn:
                self._save_btn.setEnabled(True)
                self._save_btn.setStyleSheet(
                    f"QPushButton {{ background: {Colors.ACCENT}; color: white;"
                    f"  border: none; border-radius: {Radii.SM}px;"
                    f"  font-size: {Fonts.SIZE_SM}px; }}"
                    f"QPushButton:hover {{ background: {Colors.ACCENT_HOVER}; }}"
                )

    def _on_save_notes(self) -> None:
        if self._record is None:
            return
        updated = dict(self._record)
        if self._title_edit:
            updated["title"] = self._title_edit.text().strip() or updated.get("title", "")
        if self._obs_edit:
            updated["observations"] = self._obs_edit.toPlainText().strip()
            updated["notes"]        = updated["observations"]  # keep both for CTk compat
        if self._notes_edit:
            updated["summary"] = self._notes_edit.toPlainText().strip()

        self._record = updated
        self._dirty  = False
        if self._dirty_lbl:
            self._dirty_lbl.setText("")
        if self._save_btn:
            self._save_btn.setEnabled(False)
            self._save_btn.setStyleSheet(
                f"QPushButton {{ background: {Colors.BORDER}; color: {Colors.TEXT_MUTED};"
                f"  border: none; border-radius: {Radii.SM}px; font-size: {Fonts.SIZE_SM}px; }}"
            )
        self.save_requested.emit(updated)

    # ── Internals ─────────────────────────────────────────────────────────────

    def _show_placeholder(self) -> None:
        self._lay.addStretch()
        icon = QLabel("📓")
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon.setStyleSheet("font-size: 40px;")
        self._lay.addWidget(icon)
        lbl = QLabel("Select a session record\nto view details and edit notes.")
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl.setWordWrap(True)
        lbl.setStyleSheet(
            f"color: {Colors.TEXT_MUTED}; font-size: {Fonts.SIZE_SM}px;"
            f"font-style: italic;"
        )
        self._lay.addWidget(lbl)
        self._lay.addStretch()

    def _clear(self) -> None:
        while self._lay.count():
            item = self._lay.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()
            elif item.layout():
                _clear_layout(item.layout())
        self._title_edit  = None
        self._obs_edit    = None
        self._notes_edit  = None
        self._dirty_lbl   = None
        self._save_btn    = None
        self._dirty       = False


# ── HistoryPage ───────────────────────────────────────────────────────────────

class HistoryPage(BasePage):
    """Lab Notebook — Phase 7 full implementation."""

    def __init__(self, app: "BenchFlowApp", parent: QWidget | None = None) -> None:  # type: ignore[name-defined]
        super().__init__(app, parent)
        self._records:        list[dict] = []
        self._filtered:       list[dict] = []
        self._cards:          list[_RecordCard] = []
        self._selected:       dict | None = None
        self._search:         str = ""
        self._proto_filter:   str = ""   # protocol name

        self._build()
        self._subscribe_events()
        self._load_data()

    # ── EventBus ──────────────────────────────────────────────────────────────

    def _subscribe_events(self) -> None:
        bus.subscribe("run_session_saved",        self._on_data_changed)
        bus.subscribe("notebook_record_created",  self._on_data_changed)

    def _on_data_changed(self, **_kw) -> None:
        if self.isVisible():
            sel_id = self._selected.get("id") if self._selected else None
            self._load_data()
            if sel_id:
                rec = next((r for r in self._records if r.get("id") == sel_id), None)
                if rec:
                    self._detail.show_record(rec)
        # else on_show() will reload

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

        title_col = QVBoxLayout()
        title_col.setSpacing(2)
        title_col.addWidget(PageTitle("Lab Notebook"))
        title_col.addWidget(SubLabel("Saved run sessions · click to view, edit notes, or export."))
        hdr_lay.addLayout(title_col)
        hdr_lay.addStretch()

        imp_btn = QPushButton("📥  Import")
        imp_btn.setFixedHeight(34)
        imp_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        imp_btn.setToolTip("Import a session from JSON")
        imp_btn.setStyleSheet(
            f"QPushButton {{ background: {Colors.BG_CARD}; color: {Colors.TEXT_SECOND};"
            f"  border: 1px solid {Colors.BORDER_LIGHT}; border-radius: {Radii.LG}px;"
            f"  font-size: {Fonts.SIZE_SM}px; padding: 0 14px; }}"
            f"QPushButton:hover {{ background: {Colors.BG_CARD_HOV}; }}"
        )
        imp_btn.clicked.connect(lambda: self.navigate("import"))
        hdr_lay.addWidget(imp_btn)
        outer.addWidget(hdr)

        # ── Toolbar ───────────────────────────────────────────────────────────
        tb = QWidget()
        tb.setStyleSheet(f"background: {Colors.BG_PAGE};")
        tb_lay = QHBoxLayout(tb)
        tb_lay.setContentsMargins(28, 0, 28, 12)
        tb_lay.setSpacing(8)

        self._search_box = QLineEdit()
        self._search_box.setPlaceholderText("🔍  Search sessions…")
        self._search_box.setFixedHeight(34)
        self._search_box.setStyleSheet(
            f"QLineEdit {{ background: {Colors.BG_INPUT}; color: {Colors.TEXT_PRIMARY};"
            f"  border: 1px solid {Colors.BORDER_LIGHT}; border-radius: {Radii.LG}px;"
            f"  padding: 0 12px; font-size: {Fonts.SIZE_SM}px; }}"
            f"QLineEdit:focus {{ border-color: {Colors.ACCENT}; }}"
        )
        self._search_box.textChanged.connect(self._on_search)
        tb_lay.addWidget(self._search_box, stretch=1)

        self._proto_cb = QComboBox()
        self._proto_cb.setFixedHeight(34)
        self._proto_cb.setMinimumWidth(160)
        self._proto_cb.setStyleSheet(
            f"QComboBox {{ background: {Colors.BG_INPUT}; color: {Colors.TEXT_PRIMARY};"
            f"  border: 1px solid {Colors.BORDER_LIGHT}; border-radius: {Radii.LG}px;"
            f"  padding: 0 10px; font-size: {Fonts.SIZE_SM}px; }}"
            f"QComboBox:focus {{ border-color: {Colors.ACCENT}; }}"
            f"QComboBox QAbstractItemView {{ background: {Colors.BG_CARD};"
            f"  color: {Colors.TEXT_PRIMARY}; border: 1px solid {Colors.BORDER_LIGHT};"
            f"  selection-background-color: {Colors.SELECTED_BG}; selection-color: {Colors.TEXT_PRIMARY}; }}"
        )
        self._proto_cb.addItem("All Protocols", userData="")
        self._proto_cb.currentIndexChanged.connect(self._on_proto_filter)
        tb_lay.addWidget(self._proto_cb)

        self._count_lbl = QLabel("")
        self._count_lbl.setStyleSheet(
            f"color: {Colors.TEXT_MUTED}; font-size: {Fonts.SIZE_XS}px;"
        )
        tb_lay.addWidget(self._count_lbl)

        outer.addWidget(tb)
        outer.addWidget(HSeparator())

        # ── Splitter ──────────────────────────────────────────────────────────
        self._splitter = QSplitter(Qt.Orientation.Horizontal)
        self._splitter.setStyleSheet(
            f"QSplitter::handle {{ background: {Colors.BORDER_LIGHT}; width: 1px; }}"
        )

        # ── Left list ─────────────────────────────────────────────────────────
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
        self._list_layout.setContentsMargins(20, 12, 12, 24)
        self._list_layout.setSpacing(0)
        self._list_scroll.setWidget(self._list_content)
        list_lay.addWidget(self._list_scroll)

        # ── Right detail ──────────────────────────────────────────────────────
        self._detail = _DetailPanel()
        self._detail.save_requested.connect(self._on_save_record)
        self._detail.delete_requested.connect(self._on_delete)
        self._detail.duplicate_requested.connect(self._on_duplicate)
        self._detail.export_requested.connect(self._on_export_record)

        self._splitter.addWidget(list_w)
        self._splitter.addWidget(self._detail)
        self._splitter.setSizes([480, 380])
        self._splitter.setChildrenCollapsible(False)

        outer.addWidget(self._splitter, stretch=1)
        self._root_layout.addLayout(outer)

    # ── Data loading ──────────────────────────────────────────────────────────

    def _load_data(self) -> None:
        with perf.measure("notebook_load"):
            self._records = self.app.data.load_runs()
            # Sort newest first
            self._records.sort(
                key=lambda r: r.get("startedAt", 0) or 0, reverse=True
            )

        # Rebuild protocol filter combo
        proto_names: set[str] = set()
        for r in self._records:
            n = r.get("protocolName", "")
            if n:
                proto_names.add(n)
        self._proto_cb.blockSignals(True)
        current = self._proto_cb.currentData() or ""
        self._proto_cb.clear()
        self._proto_cb.addItem("All Protocols", userData="")
        for n in sorted(proto_names):
            self._proto_cb.addItem(n, userData=n)
        idx = self._proto_cb.findData(current)
        self._proto_cb.setCurrentIndex(max(0, idx))
        self._proto_filter = self._proto_cb.currentData() or ""
        self._proto_cb.blockSignals(False)

        self._apply_filters()

    def _apply_filters(self) -> None:
        q    = self._search.lower()
        pf   = self._proto_filter

        def match(r: dict) -> bool:
            if q:
                haystack = " ".join([
                    r.get("title", ""),
                    r.get("protocolName", ""),
                    r.get("observations", ""),
                    r.get("notes", ""),
                    " ".join(r.get("tags", [])),
                ]).lower()
                if q not in haystack:
                    return False
            if pf and r.get("protocolName", "") != pf:
                return False
            return True

        self._filtered = [r for r in self._records if match(r)]
        n_total = len(self._records)
        n_shown = len(self._filtered)
        self._count_lbl.setText(
            f"{n_shown} session{'s' if n_shown != 1 else ''}"
            + (f" of {n_total}" if n_shown != n_total else "")
        )
        self._render_list()

    def _render_list(self) -> None:
        with perf.measure("notebook_render", threshold_ms=30):
            # Clear
            while self._list_layout.count():
                item = self._list_layout.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()
            self._cards.clear()

            if not self._filtered:
                self._list_layout.addStretch()
                lbl = QLabel("No sessions match your search." if (self._search or self._proto_filter)
                             else "No run records yet.\nComplete a protocol run to see it here.")
                lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
                lbl.setWordWrap(True)
                lbl.setStyleSheet(
                    f"color: {Colors.TEXT_MUTED}; font-size: {Fonts.SIZE_SM}px;"
                    f"font-style: italic;"
                )
                self._list_layout.addWidget(lbl)
                self._list_layout.addStretch()
                return

            # Group by date
            by_date: dict[str, list[dict]] = {}
            for r in self._filtered:
                by_date.setdefault(_record_date_key(r), []).append(r)

            for date_key in sorted(by_date.keys(), reverse=True):
                # Date header
                date_w = QWidget()
                date_w.setStyleSheet("background: transparent;")
                dh_lay = QHBoxLayout(date_w)
                dh_lay.setContentsMargins(0, 0, 0, 0)
                dh_lay.setSpacing(8)
                dh_lbl = QLabel(_fmt_date_header(date_key))
                dh_lbl.setStyleSheet(
                    f"color: {Colors.TEXT_PRIMARY}; font-size: {Fonts.SIZE_MD}px;"
                    f"font-weight: 700;"
                )
                dh_lay.addWidget(dh_lbl)
                cnt_lbl = QLabel(str(len(by_date[date_key])))
                cnt_lbl.setStyleSheet(
                    f"color: {Colors.ACCENT}; background: {Colors.ACCENT_BG};"
                    f"border-radius: 8px; padding: 1px 8px;"
                    f"font-size: {Fonts.SIZE_XS}px; font-weight: 700;"
                )
                dh_lay.addWidget(cnt_lbl)
                dh_lay.addStretch()
                self._list_layout.addSpacing(8)
                self._list_layout.addWidget(date_w)
                self._list_layout.addSpacing(6)

                for r in by_date[date_key]:
                    card = _RecordCard(r, parent=self._list_content)
                    card.clicked.connect(self._on_card_clicked)
                    self._cards.append(card)
                    self._list_layout.addWidget(card)
                    self._list_layout.addSpacing(6)

                self._list_layout.addSpacing(12)

            self._list_layout.addStretch()

            # Restore selection highlight
            if self._selected:
                sel_id = self._selected.get("id")
                for card in self._cards:
                    card.set_selected(card._record.get("id") == sel_id)

    # ── Event handlers ────────────────────────────────────────────────────────

    def _on_search(self, text: str) -> None:
        self._search = text
        self._apply_filters()

    def _on_proto_filter(self, _idx: int) -> None:
        self._proto_filter = self._proto_cb.currentData() or ""
        self._apply_filters()

    def _on_card_clicked(self, record: dict) -> None:
        # Deselect all
        for c in self._cards:
            c.set_selected(False)
        # Select clicked
        for c in self._cards:
            if c._record is record:
                c.set_selected(True)
                break
        self._selected = record
        self._detail.show_record(record)

    def _on_save_record(self, updated: dict) -> None:
        """Write the updated record back to runs.json."""
        runs = self.app.data.load_runs()
        rec_id = updated.get("id", "")
        for i, r in enumerate(runs):
            if r.get("id") == rec_id:
                runs[i] = updated
                break
        self.app.data.save_runs(runs)
        self._selected = updated
        # Update the card
        for c in self._cards:
            if c._record.get("id") == rec_id:
                c._record = updated
                break
        ToastManager.show_success("Session notes saved.")

    def _on_delete(self, record: dict) -> None:
        title = record.get("title", "this session")
        dlg = QMessageBox(self)
        dlg.setWindowTitle("Delete Session")
        dlg.setText(f"Delete  <b>{title}</b>?")
        dlg.setInformativeText("This cannot be undone.")
        dlg.setTextFormat(Qt.TextFormat.RichText)
        del_btn = dlg.addButton("Delete", QMessageBox.ButtonRole.DestructiveRole)
        dlg.addButton("Cancel", QMessageBox.ButtonRole.RejectRole)
        dlg.exec()
        if dlg.clickedButton() is not del_btn:
            return

        rec_id = record.get("id", "")
        runs = [r for r in self.app.data.load_runs() if r.get("id") != rec_id]
        self.app.data.save_runs(runs)

        if self._selected and self._selected.get("id") == rec_id:
            self._selected = None
            self._detail.show_placeholder()

        ToastManager.show_info(f"Deleted: {title}")
        self._load_data()

    def _on_duplicate(self, record: dict) -> None:
        now = int(time.time() * 1000)
        dup = copy.deepcopy(record)
        dup["id"]        = str(uuid.uuid4())
        dup["title"]     = f"Copy of {record.get('title', 'Session')}"
        dup["createdAt"] = now
        # Keep original startedAt so it stays in the same date group

        runs = self.app.data.load_runs()
        runs.insert(0, dup)
        self.app.data.save_runs(runs)

        ToastManager.show_success(f"Duplicated: {dup['title']}")
        self._load_data()
        # Select the duplicate
        self._selected = dup
        self._detail.show_record(dup)
        for c in self._cards:
            c.set_selected(c._record.get("id") == dup["id"])

    def _on_export_record(self, record: dict, fmt: str) -> None:
        from qt_app.services import export_service
        default_name = export_service.notebook_default_name(record, fmt)
        filters = {
            "pdf":  "PDF Files (*.pdf)",
            "docx": "Word Documents (*.docx)",
            "json": "JSON Files (*.json)",
        }
        path, _ = QFileDialog.getSaveFileName(
            self, "Export Session", default_name, filters.get(fmt, "All Files (*)")
        )
        if not path:
            return
        try:
            if fmt == "pdf":
                export_service.export_notebook_pdf(record, path)
            elif fmt == "docx":
                export_service.export_notebook_docx(record, path)
            else:
                export_service.export_notebook_json(record, path)
            ToastManager.show_success(f"Exported → {path.split('/')[-1]}")
        except export_service.ExportDependencyError as e:
            ToastManager.show_error(
                f"Missing dependency: {e.dep}. Run: {e.install_cmd}"
            )
        except Exception as exc:  # noqa: BLE001
            ToastManager.show_error(f"Export failed: {exc}")

    # ── on_show ───────────────────────────────────────────────────────────────

    def on_show(self) -> None:
        sel_id = self._selected.get("id") if self._selected else None
        self._load_data()
        # Restore detail panel
        if sel_id:
            rec = next((r for r in self._records if r.get("id") == sel_id), None)
            if rec:
                self._selected = rec
                self._detail.show_record(rec)
