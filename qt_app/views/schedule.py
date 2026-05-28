"""
Schedule page — Phase 4: interactive calendar + timeline editor.

Layout
------
Page
├── Header (title, date nav, view toggle, + Schedule Experiment)
└── QSplitter (horizontal)
    ├── Left: Calendar panel
    │   ├── _DayHeader   (fixed 44px, drawn via paintEvent)
    │   └── QScrollArea → _CalendarGrid (QWidget)
    │       ├── paintEvent: hour grid, day separators, today column, now-line
    │       └── _SessionBlock children (QFrame, draggable)
    └── Right: Detail panel
        └── QScrollArea → experiment header + timeline block rows

Session block drag model
------------------------
_SessionBlock tracks global mouse position delta → moves within _CalendarGrid.
On release, emits drag_finished(exp_id, new_start_ms).
SchedulePage receives → update experiment, recalculate_times(), save, refresh.

Phase 4.5 (implemented)
-----------------------
- Week view (7 days Mon–Sun)
- Right-click context menu: Edit, Duplicate, Insert Before/After,
  Mark Skipped, Mark Canceled (Keep/Remove Time), Restore, Move Up/Down, Delete
- Move Up / Move Down buttons on each block row
- Date picker (click date label → QCalendarWidget popup)
- Selected experiment preserved across on_show() reloads
- retains_time support for canceled blocks
"""
from __future__ import annotations

import logging
import uuid
from datetime import date, datetime, timedelta, time as time_t
from pathlib import Path
from typing import Any

from PySide6.QtCore import Qt, QDate, QSize, QTimer, Signal
from PySide6.QtGui import QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import (
    QCalendarWidget, QDialog, QFrame, QHBoxLayout, QLabel, QMenu,
    QPushButton, QScrollArea, QSizePolicy, QSplitter, QVBoxLayout, QWidget,
)

from qt_app.theme import Colors, Fonts, Radii
from qt_app.components.widgets import (
    HSeparator, PageTitle, PrimaryButton, SubLabel,
)
from qt_app.models.schedule_experiment import (
    ScheduledExperiment, TimelineBlock, TIMELINE_BLOCK_TYPES,
)
from qt_app.services.schedule_service import (
    make_scheduled_experiment, format_time_ms, format_duration_min, week_start,
)
from qt_app.dialogs.add_experiment import AddExperimentDialog
from qt_app.dialogs.edit_block import EditBlockDialog
from qt_app.views.base_page import BasePage
from qt_app.components.toast import ToastManager
from qt_app.services.event_bus import bus
from qt_app.services.perf import perf

# ── Logging ───────────────────────────────────────────────────────────────────
_logs_dir = Path(__file__).parent.parent.parent / "logs"
_logs_dir.mkdir(exist_ok=True)
_handler = logging.FileHandler(_logs_dir / "qt_schedule.log", encoding="utf-8")
_handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
logger = logging.getLogger("benchflow.schedule")
if not logger.handlers:
    logger.addHandler(_handler)
    logger.setLevel(logging.INFO)

# ── Block type → accent color ─────────────────────────────────────────────────
_BLOCK_ACCENT: dict[str, str] = {
    "protocol_step":   "#60a5fa",
    "break":           "#f9a8d4",
    "task":            "#67e8f9",
    "note":            "#fcd34d",
    "decision":        "#c084fc",
    "custom":          "#94a3b8",
    # Protocol step sub-types
    "preparation":     "#60a5fa",
    "reagent_addition":"#2dd4bf",
    "mixing":          "#c084fc",
    "incubation":      "#fb923c",
    "waiting":         "#94a3b8",
    "centrifuge":      "#818cf8",
    "wash":            "#22d3ee",
    "transfer":        "#a5b4fc",
    "pipetting":       "#38bdf8",
    "resuspension":    "#4ade80",
    "staining":        "#f472b6",
    "blocking":        "#fb7185",
    "electrophoresis": "#d8b4fe",
    "gel_running":     "#c4b5fd",
    "membrane_transfer":"#93c5fd",
    "imaging":         "#6ee7b7",
    "measurement":     "#fdba74",
    "lysis":           "#fca5a5",
    "heating":         "#fb923c",
    "cooling":         "#7dd3fc",
    "storage":         "#94a3b8",
    "harvest":         "#86efac",
    "sample_collection":"#fcd34d",
    "other":           "#94a3b8",
}

_STATUS_ACCENT: dict[str, str] = {
    "planned":   Colors.ACCENT,
    "running":   Colors.SUCCESS,
    "completed": Colors.TEXT_MUTED,
    "canceled":  Colors.DANGER,
}


def _block_accent(btype: str) -> str:
    return _BLOCK_ACCENT.get(btype, "#94a3b8")


# ── _SessionBlock ─────────────────────────────────────────────────────────────

class _SessionBlock(QFrame):
    """Draggable calendar block representing one ScheduledExperiment."""

    clicked       = Signal(str)       # exp_id
    drag_finished = Signal(str, int)  # exp_id, new_planned_start_ms

    def __init__(self, exp: ScheduledExperiment, grid: "_CalendarGrid",
                 parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._exp  = exp
        self._grid = grid
        self._press_global_y: int | None = None
        self._orig_y: int = 0
        self._dragging: bool = False

        accent = _STATUS_ACCENT.get(exp.status, Colors.ACCENT)
        self.setStyleSheet(
            f"QFrame {{ background: {Colors.ACCENT_BG};"
            f"  border-radius: {Radii.MD}px;"
            f"  border-left: 3px solid {accent};"
            f"  border-top: 1px solid {Colors.BORDER_LIGHT};"
            f"  border-right: 1px solid {Colors.BORDER_LIGHT};"
            f"  border-bottom: 1px solid {Colors.BORDER_LIGHT}; }}"
        )
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._build(exp)

    def _build(self, exp: ScheduledExperiment) -> None:
        lay = QVBoxLayout(self)
        lay.setContentsMargins(8, 6, 6, 6)
        lay.setSpacing(2)

        # Title
        title_lbl = QLabel(exp.title)
        title_lbl.setWordWrap(True)
        title_lbl.setStyleSheet(
            f"color: {Colors.TEXT_PRIMARY}; font-size: {Fonts.SIZE_SM}px;"
            f"font-weight: 600; background: transparent; border: none;"
        )
        lay.addWidget(title_lbl)

        # Time range
        t_start = format_time_ms(exp.planned_start)
        t_end   = format_time_ms(exp.planned_end)
        dur     = format_duration_min(exp.total_duration)
        time_lbl = QLabel(f"{t_start} – {t_end}  ·  {dur}")
        time_lbl.setStyleSheet(
            f"color: {Colors.TEXT_SECOND}; font-size: {Fonts.SIZE_XS}px;"
            f"background: transparent; border: none;"
        )
        lay.addWidget(time_lbl)
        lay.addStretch()

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._press_global_y = int(event.globalPosition().y())
            self._orig_y = self.y()
            self._dragging = False
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:
        if self._press_global_y is None:
            return
        if not (event.buttons() & Qt.MouseButton.LeftButton):
            self._press_global_y = None
            return
        dy = int(event.globalPosition().y()) - self._press_global_y
        if not self._dragging and abs(dy) > 6:
            self._dragging = True
        if self._dragging:
            snap_px = max(1, self._grid.HOUR_H // 4)   # 15-min snap
            new_y = round((self._orig_y + dy) / snap_px) * snap_px
            new_y = max(0, min(new_y, self._grid.height() - self.height()))
            self.move(self.x(), new_y)
            self.setCursor(Qt.CursorShape.ClosedHandCursor)

    def mouseReleaseEvent(self, event) -> None:
        if self._press_global_y is not None:
            if self._dragging:
                # Convert y → new start timestamp
                new_hour = self._grid.MIN_HOUR + self.y() / self._grid.HOUR_H
                try:
                    exp_date = datetime.strptime(self._exp.date, "%Y-%m-%d").date()
                    new_dt = datetime.combine(
                        exp_date,
                        time_t(int(new_hour) % 24, int((new_hour % 1) * 60)),
                    )
                    new_start_ms = int(new_dt.timestamp() * 1000)
                    self.drag_finished.emit(self._exp.id, new_start_ms)
                except Exception as e:
                    logger.error(f"drag release error: {e}")
            else:
                self.clicked.emit(self._exp.id)
            self._press_global_y = None
            self._dragging = False
            self.setCursor(Qt.CursorShape.PointingHandCursor)
        super().mouseReleaseEvent(event)

    def update_exp(self, exp: ScheduledExperiment) -> None:
        """Update internal experiment reference (after time change)."""
        self._exp = exp


# ── _DayHeader ────────────────────────────────────────────────────────────────

class _DayHeader(QWidget):
    """Non-scrolling day-name / date-number header above the calendar grid."""

    GUTTER_W = 56   # must match _CalendarGrid.GUTTER_W
    H = 44

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFixedHeight(self.H)
        self.setStyleSheet(
            f"background: {Colors.BG_CARD};"
            f"border-bottom: 1px solid {Colors.BORDER_LIGHT};"
        )
        self._dates: list[date] = []

    def set_dates(self, dates: list[date]) -> None:
        self._dates = dates
        self.update()

    def paintEvent(self, event) -> None:
        if not self._dates:
            return
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        n = len(self._dates)
        gw = self.GUTTER_W
        col_w = max(60, (self.width() - gw) // n)
        today = date.today()

        font_xs = QFont()
        font_xs.setPointSize(Fonts.SIZE_XS)
        font_xs.setWeight(QFont.Weight.Bold)
        font_md = QFont()
        font_md.setPointSize(Fonts.SIZE_MD)

        for i, d in enumerate(self._dates):
            cx = gw + i * col_w + col_w // 2
            is_today = (d == today)

            # Day name
            p.setFont(font_xs)
            p.setPen(QColor(Colors.ACCENT if is_today else Colors.TEXT_MUTED))
            day_str = d.strftime("%a").upper()
            fm = p.fontMetrics()
            tw = fm.horizontalAdvance(day_str)
            p.drawText(cx - tw // 2, 15, day_str)

            # Date number
            num_str = str(d.day)
            p.setFont(font_md)
            fm2 = p.fontMetrics()
            tw2 = fm2.horizontalAdvance(num_str)

            if is_today:
                r = 13
                p.setBrush(QColor(Colors.ACCENT))
                p.setPen(Qt.PenStyle.NoPen)
                p.drawEllipse(cx - r, 22, r * 2, r * 2)
                p.setPen(QColor("white"))
                p.drawText(cx - tw2 // 2, 22 + r + fm2.ascent() // 2 - 1, num_str)
            else:
                p.setPen(QColor(Colors.TEXT_PRIMARY))
                p.drawText(cx - tw2 // 2, 40, num_str)

        # Gutter border
        p.setPen(QPen(QColor(Colors.BORDER), 1))
        p.drawLine(gw, 0, gw, self.H)
        p.end()


# ── _CalendarGrid ─────────────────────────────────────────────────────────────

class _CalendarGrid(QWidget):
    """
    Custom QWidget that draws the hour grid and hosts _SessionBlock children.

    Designed to be placed inside a QScrollArea (widgetResizable=True).
    The widget fills viewport width; minimum height forces vertical scrollbar.
    """

    HOUR_H  = 80   # pixels per hour
    GUTTER_W = 56  # left gutter (time labels)
    MIN_HOUR = 6   # 6 AM
    MAX_HOUR = 24  # midnight

    block_clicked      = Signal(str)       # exp_id
    block_time_changed = Signal(str, int)  # exp_id, new_start_ms

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._experiments: list[ScheduledExperiment] = []
        self._block_widgets: dict[str, _SessionBlock] = {}
        self._view_mode  = "workweek"   # day | workweek | week (week = Phase 4.5)
        self._base_date  = date.today()
        self.setMinimumHeight(self._total_h)

    # ── Properties ────────────────────────────────────────────────────────────

    @property
    def _total_h(self) -> int:
        return (self.MAX_HOUR - self.MIN_HOUR) * self.HOUR_H

    @property
    def _n_cols(self) -> int:
        if self._view_mode == "day":
            return 1
        if self._view_mode == "week":
            return 7
        return 5   # workweek

    def _col_width(self) -> int:
        return max(60, (self.width() - self.GUTTER_W) // max(1, self._n_cols))

    def _dates(self) -> list[date]:
        if self._view_mode == "day":
            return [self._base_date]
        mon = week_start(self._base_date)
        n = 7 if self._view_mode == "week" else 5
        return [mon + timedelta(days=i) for i in range(n)]

    def _date_to_col(self, date_str: str) -> int | None:
        try:
            d = datetime.strptime(date_str, "%Y-%m-%d").date()
            dates = self._dates()
            if d in dates:
                return dates.index(d)
        except Exception:
            pass
        return None

    def _time_to_y(self, hour: float) -> int:
        return int((hour - self.MIN_HOUR) * self.HOUR_H)

    # ── Public API ────────────────────────────────────────────────────────────

    def set_view(self, mode: str) -> None:
        self._view_mode = mode
        self._reposition_blocks()
        self.update()

    def set_base_date(self, d: date) -> None:
        self._base_date = d
        self._reposition_blocks()
        self.update()

    def set_experiments(self, experiments: list[ScheduledExperiment]) -> None:
        # Destroy old block widgets
        for w in self._block_widgets.values():
            w.deleteLater()
        self._block_widgets.clear()

        self._experiments = experiments
        for exp in experiments:
            self._create_block_widget(exp)
        self._reposition_blocks()

    def update_experiment(self, exp: ScheduledExperiment) -> None:
        """Update a single session block after time/data change."""
        if exp.id in self._block_widgets:
            self._block_widgets[exp.id].update_exp(exp)
        else:
            self._create_block_widget(exp)
        self._reposition_blocks()

    def highlight_block(self, exp_id: str) -> None:
        """Visually select a block (accent border)."""
        for eid, w in self._block_widgets.items():
            selected = (eid == exp_id)
            w.setStyleSheet(
                f"QFrame {{ background: {Colors.SELECTED_BG if selected else Colors.ACCENT_BG};"
                f"  border-radius: {Radii.MD}px;"
                f"  border-left: 3px solid {Colors.ACCENT};"
                f"  border-top: 1px solid {Colors.BORDER_LIGHT};"
                f"  border-right: 1px solid {Colors.BORDER_LIGHT};"
                f"  border-bottom: 1px solid {Colors.BORDER_LIGHT}; }}"
            )

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _create_block_widget(self, exp: ScheduledExperiment) -> None:
        w = _SessionBlock(exp, self, parent=self)
        w.clicked.connect(self.block_clicked)
        w.drag_finished.connect(self._on_block_drag)
        self._block_widgets[exp.id] = w
        w.show()

    def _reposition_blocks(self) -> None:
        if self.width() == 0:
            return
        col_w = self._col_width()
        visible_dates = set(str(d) for d in self._dates())

        for exp in self._experiments:
            w = self._block_widgets.get(exp.id)
            if w is None:
                continue
            if exp.date not in visible_dates:
                w.setVisible(False)
                continue
            col = self._date_to_col(exp.date)
            if col is None:
                w.setVisible(False)
                continue
            w.setVisible(True)

            try:
                start_dt = datetime.fromtimestamp(exp.planned_start / 1000)
                end_dt   = datetime.fromtimestamp(exp.planned_end   / 1000)
            except Exception:
                w.setVisible(False)
                continue

            sh = start_dt.hour + start_dt.minute / 60
            eh = end_dt.hour   + end_dt.minute   / 60
            y  = self._time_to_y(sh)
            h  = max(28, self._time_to_y(eh) - y)
            x  = self.GUTTER_W + col * col_w + 4
            w.setGeometry(x, y, col_w - 8, h)

    def _on_block_drag(self, exp_id: str, new_start_ms: int) -> None:
        self.block_time_changed.emit(exp_id, new_start_ms)

    # ── Qt overrides ──────────────────────────────────────────────────────────

    def paintEvent(self, event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, False)

        w   = self.width()
        col_w = self._col_width()
        n   = self._n_cols
        gh  = self._total_h
        gw  = self.GUTTER_W
        dates = self._dates()
        today = date.today()

        # Today column highlight
        if today in dates:
            ci = dates.index(today)
            p.fillRect(gw + ci * col_w, 0, col_w, gh, QColor(37, 99, 235, 12))

        font_xs = QFont()
        font_xs.setPointSize(Fonts.SIZE_XS)
        p.setFont(font_xs)

        # Hour lines + labels
        for h in range(self.MIN_HOUR, self.MAX_HOUR + 1):
            y = (h - self.MIN_HOUR) * self.HOUR_H

            # Hour line (main)
            if h > self.MIN_HOUR:
                p.setPen(QPen(QColor(Colors.BORDER_LIGHT), 1))
                p.drawLine(gw, y, w, y)

            # Half-hour line (dashed, lighter)
            if h < self.MAX_HOUR:
                hy = y + self.HOUR_H // 2
                pen = QPen(QColor(Colors.BORDER_LIGHT), 1)
                pen.setStyle(Qt.PenStyle.DashLine)
                p.setPen(pen)
                p.drawLine(gw + 4, hy, w, hy)

            # Time label
            if h < self.MAX_HOUR:
                if h == 0:    lbl = "12 AM"
                elif h < 12:  lbl = f"{h} AM"
                elif h == 12: lbl = "12 PM"
                else:         lbl = f"{h - 12} PM"
                p.setPen(QColor(Colors.TEXT_MUTED))
                p.drawText(4, y + 14, lbl)

        # Day separator lines
        p.setPen(QPen(QColor(Colors.BORDER_LIGHT), 1))
        for ci in range(n + 1):
            x = gw + ci * col_w
            p.drawLine(x, 0, x, gh)

        # Current time indicator (only in "today" column)
        if today in dates:
            now = datetime.now()
            ch  = now.hour + now.minute / 60
            if self.MIN_HOUR <= ch < self.MAX_HOUR:
                ty = int((ch - self.MIN_HOUR) * self.HOUR_H)
                ci = dates.index(today)
                tx1 = gw + ci * col_w
                tx2 = tx1 + col_w
                p.setPen(QPen(QColor(Colors.DANGER), 2))
                p.drawLine(tx1, ty, tx2, ty)
                p.setBrush(QColor(Colors.DANGER))
                p.setPen(Qt.PenStyle.NoPen)
                p.drawEllipse(tx1 - 4, ty - 4, 8, 8)

        p.end()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._reposition_blocks()

    def sizeHint(self) -> QSize:
        return QSize(self.GUTTER_W + self._n_cols * 120, self._total_h)

    def minimumSizeHint(self) -> QSize:
        return QSize(self.GUTTER_W + self._n_cols * 80, self._total_h)


# ── _TimelineBlockRow ─────────────────────────────────────────────────────────

def _context_menu_qss() -> str:
    return f"""
QMenu {{
    background: {Colors.BG_CARD}; color: {Colors.TEXT_PRIMARY};
    border: 1px solid {Colors.BORDER_LIGHT}; border-radius: 10px;
    padding: 4px 0;
}}
QMenu::item {{ padding: 6px 18px 6px 14px; font-size: 13px; }}
QMenu::item:selected {{ background: {Colors.BG_CARD_HOV}; color: {Colors.TEXT_PRIMARY}; }}
QMenu::item:disabled {{ color: {Colors.TEXT_MUTED}; }}
QMenu::separator {{ height: 1px; background: {Colors.BORDER_LIGHT}; margin: 3px 0; }}
QMenu::indicator {{ width: 0; }}
"""


class _TimelineBlockRow(QFrame):
    """One row in the right-panel timeline — shows one TimelineBlock."""

    # ── Signals ───────────────────────────────────────────────────────────────
    edit_requested          = Signal(str)        # block_id
    skip_requested          = Signal(str)        # block_id
    delete_requested        = Signal(str)        # block_id
    duplicate_requested     = Signal(str)        # block_id
    cancel_requested        = Signal(str, bool)  # block_id, retains_time
    restore_requested       = Signal(str)        # block_id
    move_up_requested       = Signal(str)        # block_id
    move_down_requested     = Signal(str)        # block_id
    insert_before_requested = Signal(str, str)   # block_id, block_type
    insert_after_requested  = Signal(str, str)   # block_id, block_type

    def __init__(self, block: TimelineBlock, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._block = block
        self._build()

    def _build(self) -> None:
        block     = self._block
        accent    = _block_accent(block.type)
        is_done      = block.status == "done"
        is_inactive  = block.status in ("skipped", "canceled")

        self.setStyleSheet(
            f"_TimelineBlockRow {{ background: {Colors.BG_CARD};"
            f"  border-radius: {Radii.LG}px;"
            f"  border-left: 3px solid {accent};"
            f"  border-top: 1px solid {Colors.BORDER_LIGHT};"
            f"  border-right: 1px solid {Colors.BORDER_LIGHT};"
            f"  border-bottom: 1px solid {Colors.BORDER_LIGHT}; }}"
            f"_TimelineBlockRow:hover {{ background: {Colors.HOVER_BG}; }}"
        )
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_context_menu)

        row = QHBoxLayout(self)
        row.setContentsMargins(4, 8, 10, 8)
        row.setSpacing(6)

        # Drag handle (visual only)
        handle = QLabel("⠿")
        handle.setFixedWidth(16)
        handle.setStyleSheet(
            f"color: {Colors.TEXT_MUTED}; font-size: 14px; padding: 0;"
        )
        handle.setToolTip("Drag to reorder (use ▲▼ buttons)")
        row.addWidget(handle)

        # Time column
        t_col = QVBoxLayout()
        t_col.setSpacing(1)
        t_col.setContentsMargins(0, 0, 0, 0)
        t_start_lbl = QLabel(format_time_ms(block.start_time))
        t_start_lbl.setStyleSheet(
            f"color: {Colors.TEXT_SECOND}; font-size: {Fonts.SIZE_XS}px;"
        )
        t_end_lbl = QLabel(format_time_ms(block.end_time))
        t_end_lbl.setStyleSheet(
            f"color: {Colors.TEXT_MUTED}; font-size: {Fonts.SIZE_XS}px;"
        )
        t_col.addWidget(t_start_lbl)
        t_col.addWidget(t_end_lbl)
        time_w = QWidget()
        time_w.setFixedWidth(68)
        time_w.setLayout(t_col)
        row.addWidget(time_w)

        # Content column
        content = QVBoxLayout()
        content.setSpacing(2)
        content.setContentsMargins(0, 0, 0, 0)

        title_lbl = QLabel(block.title)
        title_lbl.setStyleSheet(
            f"color: {Colors.TEXT_MUTED if is_inactive else Colors.TEXT_PRIMARY};"
            f"font-size: {Fonts.SIZE_SM}px; font-weight: 600;"
            + ("text-decoration: line-through;" if is_inactive else "")
        )
        title_lbl.setWordWrap(False)
        content.addWidget(title_lbl)

        meta_parts = [block.type.replace("_", " ")]
        if block.duration_minutes > 0:
            meta_parts.append(format_duration_min(block.duration_minutes))
        if block.hands_on_minutes > 0:
            meta_parts.append(f"⏱ {block.hands_on_minutes:.0f}m hands-on")
        if block.wait_minutes > 0:
            meta_parts.append(f"⏳ {block.wait_minutes:.0f}m wait")
        meta_lbl = QLabel("  ·  ".join(meta_parts))
        meta_lbl.setStyleSheet(
            f"color: {Colors.TEXT_MUTED}; font-size: {Fonts.SIZE_XS}px;"
        )
        content.addWidget(meta_lbl)

        if block.notes:
            notes_lbl = QLabel(block.notes[:80] + ("…" if len(block.notes) > 80 else ""))
            notes_lbl.setStyleSheet(
                f"color: {Colors.TEXT_MUTED}; font-size: {Fonts.SIZE_XS}px;"
                f"font-style: italic;"
            )
            content.addWidget(notes_lbl)

        row.addLayout(content, stretch=1)

        # Status badge
        _STATUS_BADGE = {
            "planned":  (Colors.ACCENT,   Colors.ACCENT_BG),
            "done":     (Colors.SUCCESS,  Colors.SUCCESS_BG),
            "skipped":  (Colors.WARNING,  Colors.WARNING_BG),
            "canceled": (Colors.DANGER,   Colors.DANGER_BG),
        }
        sc, sbg = _STATUS_BADGE.get(block.status, (Colors.TEXT_MUTED, Colors.BG_CARD))
        s_lbl = QLabel(block.status)
        s_lbl.setStyleSheet(
            f"color: {sc}; background: {sbg};"
            f"border-radius: 6px; padding: 2px 8px;"
            f"font-size: {Fonts.SIZE_XS}px; font-weight: 600;"
        )
        row.addWidget(s_lbl)

        # Move Up / Move Down
        up_btn = self._action_btn("▲", Colors.TEXT_MUTED)
        up_btn.setToolTip("Move up")
        up_btn.clicked.connect(lambda: self.move_up_requested.emit(self._block.id))
        row.addWidget(up_btn)

        down_btn = self._action_btn("▼", Colors.TEXT_MUTED)
        down_btn.setToolTip("Move down")
        down_btn.clicked.connect(lambda: self.move_down_requested.emit(self._block.id))
        row.addWidget(down_btn)

        # Edit / Restore / Skip / Delete
        if not is_done:
            edit_btn = self._action_btn("✎", Colors.TEXT_SECOND)
            edit_btn.setToolTip("Edit block")
            edit_btn.clicked.connect(lambda: self.edit_requested.emit(self._block.id))
            row.addWidget(edit_btn)

        if is_inactive:
            restore_btn = self._action_btn("↩", Colors.SUCCESS)
            restore_btn.setToolTip("Restore block")
            restore_btn.clicked.connect(lambda: self.restore_requested.emit(self._block.id))
            row.addWidget(restore_btn)
        elif not is_done and block.status == "planned":
            skip_btn = self._action_btn("⟩", Colors.WARNING)
            skip_btn.setToolTip("Skip block")
            skip_btn.clicked.connect(lambda: self.skip_requested.emit(self._block.id))
            row.addWidget(skip_btn)

        del_btn = self._action_btn("✕", Colors.DANGER)
        del_btn.setToolTip("Delete block")
        del_btn.clicked.connect(lambda: self.delete_requested.emit(self._block.id))
        row.addWidget(del_btn)

    # ── Context menu ──────────────────────────────────────────────────────────

    def _show_context_menu(self, local_pos) -> None:
        block = self._block
        is_inactive = block.status in ("skipped", "canceled")
        menu = QMenu(self)
        menu.setStyleSheet(_context_menu_qss())

        # Edit
        a_edit = menu.addAction("✎  Edit…")
        a_edit.triggered.connect(lambda: self.edit_requested.emit(block.id))

        # Duplicate
        a_dup = menu.addAction("⧉  Duplicate")
        a_dup.triggered.connect(lambda: self.duplicate_requested.emit(block.id))

        menu.addSeparator()

        # Insert Before submenu
        ins_before = menu.addMenu("↑  Insert Before")
        ins_before.setStyleSheet(_context_menu_qss())
        for btype, label in [("break", "Break"), ("task", "Task"),
                              ("note", "Note"), ("custom", "Custom")]:
            a = ins_before.addAction(label)
            a.triggered.connect(
                lambda chk=False, bt=btype: self.insert_before_requested.emit(block.id, bt)
            )

        # Insert After submenu
        ins_after = menu.addMenu("↓  Insert After")
        ins_after.setStyleSheet(_context_menu_qss())
        for btype, label in [("break", "Break"), ("task", "Task"),
                              ("note", "Note"), ("custom", "Custom")]:
            a = ins_after.addAction(label)
            a.triggered.connect(
                lambda chk=False, bt=btype: self.insert_after_requested.emit(block.id, bt)
            )

        menu.addSeparator()

        # Status changes
        if block.status == "planned":
            a_skip = menu.addAction("⟩  Mark Skipped")
            a_skip.triggered.connect(lambda: self.skip_requested.emit(block.id))
            a_cancel = menu.addAction("✕  Mark Canceled…")
            a_cancel.triggered.connect(lambda: self._ask_cancel())
        elif block.status == "done":
            a_restore = menu.addAction("↩  Restore to Planned")
            a_restore.triggered.connect(lambda: self.restore_requested.emit(block.id))
        else:
            a_restore = menu.addAction("↩  Restore to Planned")
            a_restore.triggered.connect(lambda: self.restore_requested.emit(block.id))

        menu.addSeparator()

        # Reorder
        a_up = menu.addAction("▲  Move Up")
        a_up.triggered.connect(lambda: self.move_up_requested.emit(block.id))
        a_down = menu.addAction("▼  Move Down")
        a_down.triggered.connect(lambda: self.move_down_requested.emit(block.id))

        menu.addSeparator()

        a_del = menu.addAction("🗑  Delete")
        a_del.triggered.connect(lambda: self.delete_requested.emit(block.id))

        menu.exec(self.mapToGlobal(local_pos))

    def _ask_cancel(self) -> None:
        """Show 'Keep Time / Remove Time / Don't Cancel' dialog."""
        dlg = QDialog(self)
        dlg.setWindowTitle("Cancel block")
        dlg.setStyleSheet(
            f"QDialog {{ background: {Colors.BG_CARD}; }}"
            f"QLabel {{ color: {Colors.TEXT_PRIMARY}; font-size: {Fonts.SIZE_SM}px; }}"
        )
        lay = QVBoxLayout(dlg)
        lay.setContentsMargins(20, 16, 20, 16)
        lay.setSpacing(12)

        lbl = QLabel(
            f"Cancel  <b>{self._block.title}</b>?<br>"
            "Choose how the block's time slot is handled:"
        )
        lbl.setWordWrap(True)
        lay.addWidget(lbl)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)

        def _mk_btn(text: str, color: str) -> QPushButton:
            b = QPushButton(text)
            b.setFixedHeight(34)
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.setStyleSheet(
                f"QPushButton {{ background: {Colors.BG_CARD}; color: {color};"
                f"  border: 1px solid {Colors.BORDER_LIGHT}; border-radius: {Radii.LG}px;"
                f"  font-size: {Fonts.SIZE_SM}px; padding: 0 12px; }}"
                f"QPushButton:hover {{ background: {Colors.HOVER_BG}; }}"
            )
            return b

        b_keep   = _mk_btn("Keep Time",   Colors.WARNING)
        b_remove = _mk_btn("Remove Time", Colors.DANGER)
        b_dont   = _mk_btn("Don't Cancel", Colors.TEXT_SECOND)

        b_keep.clicked.connect(lambda: (
            self.cancel_requested.emit(self._block.id, True),  # retains_time=True
            dlg.accept(),
        ))
        b_remove.clicked.connect(lambda: (
            self.cancel_requested.emit(self._block.id, False),  # retains_time=False
            dlg.accept(),
        ))
        b_dont.clicked.connect(dlg.reject)

        btn_row.addWidget(b_keep)
        btn_row.addWidget(b_remove)
        btn_row.addWidget(b_dont)
        lay.addLayout(btn_row)
        dlg.exec()

    @staticmethod
    def _action_btn(text: str, color: str) -> QPushButton:
        b = QPushButton(text)
        b.setFixedSize(26, 26)
        b.setCursor(Qt.CursorShape.PointingHandCursor)
        b.setStyleSheet(
            f"QPushButton {{ background: {Colors.BG_CARD}; color: {color};"
            f"  border: 1px solid {Colors.BORDER_LIGHT}; border-radius: {Radii.LG}px;"
            f"  font-size: {Fonts.SIZE_SM}px; }}"
            f"QPushButton:hover {{ background: {Colors.BG_CARD_HOV}; }}"
        )
        return b


# ── SchedulePage ──────────────────────────────────────────────────────────────

class SchedulePage(BasePage):
    """PySide6 Schedule page — calendar grid + timeline detail editor."""

    def __init__(self, app: "BenchFlowApp", parent: QWidget | None = None) -> None:  # type: ignore[name-defined]
        super().__init__(app, parent)
        self._experiments: list[ScheduledExperiment] = []
        self._selected_exp: ScheduledExperiment | None = None
        self._view_mode = "workweek"
        self._base_date = date.today()

        # Autosave debounce
        self._save_timer = QTimer(self)
        self._save_timer.setSingleShot(True)
        self._save_timer.setInterval(150)
        self._save_timer.timeout.connect(self._do_save)

        # 1-minute repaint timer (refreshes current-time line) — wired in _build()
        self._repaint_timer = QTimer(self)
        self._repaint_timer.setInterval(60_000)

        self._build()

    # ── UI construction ───────────────────────────────────────────────────────

    def _build(self) -> None:
        root = QVBoxLayout()
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Header ────────────────────────────────────────────────────────────
        hdr_w = QWidget()
        hdr_w.setStyleSheet(f"background: {Colors.BG_PAGE};")
        hdr_lay = QHBoxLayout(hdr_w)
        hdr_lay.setContentsMargins(28, 20, 28, 12)
        hdr_lay.setSpacing(8)

        title_col = QVBoxLayout()
        title_col.setSpacing(2)
        title_col.addWidget(PageTitle("Schedule"))
        title_col.addWidget(SubLabel("Plan and visualise experiments on a time grid."))
        hdr_lay.addLayout(title_col)
        hdr_lay.addStretch()

        # Date navigation
        def _nav_btn(text: str) -> QPushButton:
            b = QPushButton(text)
            b.setFixedSize(32, 32)
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.setStyleSheet(
                f"QPushButton {{ background: {Colors.BG_CARD}; color: {Colors.TEXT_PRIMARY};"
                f"  border: 1px solid {Colors.BORDER_LIGHT}; border-radius: {Radii.LG}px;"
                f"  font-size: {Fonts.SIZE_MD}px; }}"
                f"QPushButton:hover {{ background: {Colors.BG_CARD_HOV}; }}"
            )
            return b

        self._prev_btn = _nav_btn("‹")
        self._prev_btn.setToolTip("Previous period")
        self._prev_btn.clicked.connect(self._go_prev)
        hdr_lay.addWidget(self._prev_btn)

        self._today_btn = QPushButton("Today")
        self._today_btn.setFixedHeight(32)
        self._today_btn.setMinimumWidth(60)
        self._today_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._today_btn.setStyleSheet(
            f"QPushButton {{ background: {Colors.BG_CARD}; color: {Colors.TEXT_PRIMARY};"
            f"  border: 1px solid {Colors.BORDER_LIGHT}; border-radius: {Radii.LG}px;"
            f"  padding: 0 10px; font-size: {Fonts.SIZE_SM}px; }}"
            f"QPushButton:hover {{ background: {Colors.BG_CARD_HOV}; }}"
        )
        self._today_btn.clicked.connect(self._go_today)
        hdr_lay.addWidget(self._today_btn)

        self._next_btn = _nav_btn("›")
        self._next_btn.setToolTip("Next period")
        self._next_btn.clicked.connect(self._go_next)
        hdr_lay.addWidget(self._next_btn)

        # Clickable date label (opens date picker)
        self._date_btn = QPushButton("")
        self._date_btn.setFixedHeight(32)
        self._date_btn.setMinimumWidth(140)
        self._date_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._date_btn.setStyleSheet(
            f"QPushButton {{ background: transparent; color: {Colors.TEXT_SECOND};"
            f"  border: none; font-size: {Fonts.SIZE_SM}px; font-weight: 600;"
            f"  text-align: left; padding: 0 4px; }}"
            f"QPushButton:hover {{ color: {Colors.TEXT_PRIMARY}; }}"
        )
        self._date_btn.clicked.connect(self._on_date_picker)
        hdr_lay.addWidget(self._date_btn)

        # View toggle (Day | Work Week | Week)
        self._view_btns: list[QPushButton] = []
        for mode, label in [("day", "Day"), ("workweek", "Work Week"), ("week", "Week")]:
            b = QPushButton(label)
            b.setCheckable(True)
            b.setChecked(mode == self._view_mode)
            b.setFixedHeight(32)
            b.setMinimumWidth(70)
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.setObjectName(f"view_{mode}")
            b.setStyleSheet(
                f"QPushButton {{ background: {Colors.BG_CARD}; color: {Colors.TEXT_SECOND};"
                f"  border: 1px solid {Colors.BORDER_LIGHT}; border-radius: {Radii.LG}px;"
                f"  padding: 0 10px; font-size: {Fonts.SIZE_SM}px; }}"
                f"QPushButton:checked {{ background: {Colors.SELECTED_BG}; color: {Colors.TEXT_PRIMARY};"
                f"  border-color: {Colors.BORDER_LIGHT}; font-weight: 600; }}"
                f"QPushButton:hover:!checked {{ background: {Colors.HOVER_BG}; }}"
            )
            b.toggled.connect(lambda checked, m=mode, btn=b: self._on_view_toggled(m, checked, btn))
            hdr_lay.addWidget(b)
            self._view_btns.append(b)

        # + Schedule Experiment
        self._add_exp_btn = PrimaryButton("＋ Experiment")
        self._add_exp_btn.setMinimumWidth(130)
        self._add_exp_btn.clicked.connect(self._on_add_experiment)
        hdr_lay.addWidget(self._add_exp_btn)

        root.addWidget(hdr_w)
        root.addWidget(HSeparator())

        # ── Splitter ──────────────────────────────────────────────────────────
        self._splitter = QSplitter(Qt.Orientation.Horizontal)
        self._splitter.setStyleSheet(
            f"QSplitter::handle {{ background: {Colors.BORDER_LIGHT}; width: 1px; }}"
        )
        self._splitter.addWidget(self._build_calendar_panel())
        self._splitter.addWidget(self._build_detail_panel())
        self._splitter.setSizes([700, 380])
        self._splitter.setChildrenCollapsible(False)
        root.addWidget(self._splitter, stretch=1)

        self._root_layout.addLayout(root)

        # Wire repaint timer now that _grid exists
        self._repaint_timer.timeout.connect(self._grid.update)
        self._repaint_timer.start()

    def _build_calendar_panel(self) -> QWidget:
        container = QWidget()
        container.setStyleSheet(f"background: {Colors.BG_PAGE};")
        lay = QVBoxLayout(container)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        # Day header (non-scrollable)
        self._day_header = _DayHeader()
        lay.addWidget(self._day_header)

        # Scrollable grid
        self._cal_scroll = QScrollArea()
        self._cal_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._cal_scroll.setWidgetResizable(True)
        self._cal_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._cal_scroll.setStyleSheet(f"background: {Colors.BG_PAGE};")

        self._grid = _CalendarGrid()
        self._grid.setStyleSheet(f"background: {Colors.BG_PAGE};")
        self._grid.block_clicked.connect(self._on_session_clicked)
        self._grid.block_time_changed.connect(self._on_session_time_changed)
        self._cal_scroll.setWidget(self._grid)

        lay.addWidget(self._cal_scroll, stretch=1)
        return container

    def _build_detail_panel(self) -> QWidget:
        w = QWidget()
        w.setStyleSheet(
            f"background: {Colors.BG_CARD}; "
            f"border-left: 1px solid {Colors.BORDER_LIGHT};"
        )
        w.setMinimumWidth(280)
        w.setMaximumWidth(500)
        lay = QVBoxLayout(w)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        # Detail content scroll area
        self._detail_scroll = QScrollArea()
        self._detail_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._detail_scroll.setWidgetResizable(True)
        self._detail_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._detail_scroll.setStyleSheet(f"background: {Colors.BG_CARD};")

        self._detail_content = QWidget()
        self._detail_content.setStyleSheet(f"background: {Colors.BG_CARD};")
        self._detail_layout = QVBoxLayout(self._detail_content)
        self._detail_layout.setContentsMargins(16, 16, 16, 20)
        self._detail_layout.setSpacing(8)
        self._detail_scroll.setWidget(self._detail_content)
        lay.addWidget(self._detail_scroll, stretch=1)

        self._show_detail_placeholder()
        return w

    # ── on_show ───────────────────────────────────────────────────────────────

    def on_show(self) -> None:
        logger.info("enter_schedule")
        # Remember selected experiment ID before reloading
        prev_id = self._selected_exp.id if self._selected_exp else None

        self._load_experiments()
        self._refresh_calendar()

        # Restore selection after reload (new objects, same ID)
        if prev_id:
            restored = self._find_exp(prev_id)
            if restored:
                self._selected_exp = restored
                self._grid.highlight_block(prev_id)
                self._show_experiment_detail(restored)
            else:
                self._selected_exp = None
                self._show_detail_placeholder()

        # Scroll to ~1 hour before now
        now = datetime.now()
        target_h = max(self._grid.MIN_HOUR, now.hour - 1)
        scroll_y = (target_h - self._grid.MIN_HOUR) * self._grid.HOUR_H
        QTimer.singleShot(0, lambda: self._cal_scroll.verticalScrollBar().setValue(scroll_y))

    # ── Data loading ──────────────────────────────────────────────────────────

    def _load_experiments(self) -> None:
        raw = self.app.data.load_scheduled_experiments()
        self._experiments = [ScheduledExperiment.from_dict(d) for d in raw]

    def _do_save(self) -> None:
        try:
            with perf.measure("schedule_autosave", threshold_ms=100):
                self.app.data.save_scheduled_experiments(
                    [e.to_dict() for e in self._experiments]
                )
            logger.info("autosave: scheduled_experiments.json written")
            bus.emit("schedule_updated")
        except Exception as e:
            logger.error(f"autosave error: {e}")

    def _schedule_save(self) -> None:
        self._save_timer.start()

    # ── Calendar refresh ──────────────────────────────────────────────────────

    def _refresh_calendar(self) -> None:
        self._grid.set_view(self._view_mode)
        self._grid.set_base_date(self._base_date)
        self._grid.set_experiments(self._experiments)
        self._day_header.set_dates(self._grid._dates())
        self._update_date_label()

        # Re-highlight selected experiment
        if self._selected_exp is not None:
            self._grid.highlight_block(self._selected_exp.id)

    def _update_date_label(self) -> None:
        dates = self._grid._dates()
        if not dates:
            self._date_btn.setText("")
            return
        if len(dates) == 1:
            d = dates[0]
            self._date_btn.setText(f"{d.strftime('%B')} {d.day}, {d.year}")
        else:
            d0, d1 = dates[0], dates[-1]
            if d0.month == d1.month:
                self._date_btn.setText(
                    f"{d0.strftime('%b')} {d0.day}–{d1.day}, {d0.year}"
                )
            else:
                self._date_btn.setText(
                    f"{d0.strftime('%b')} {d0.day} – {d1.strftime('%b')} {d1.day}, {d0.year}"
                )

    # ── Navigation ────────────────────────────────────────────────────────────

    def _go_today(self) -> None:
        self._base_date = date.today()
        self._refresh_calendar()

    def _go_prev(self) -> None:
        delta = timedelta(days=1 if self._view_mode == "day" else 7)
        self._base_date -= delta
        self._refresh_calendar()

    def _go_next(self) -> None:
        delta = timedelta(days=1 if self._view_mode == "day" else 7)
        self._base_date += delta
        self._refresh_calendar()

    def _on_date_picker(self) -> None:
        """Open a QCalendarWidget popup so the user can jump to any date."""
        dlg = QDialog(self)
        dlg.setWindowTitle("Go to date")
        dlg.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.FramelessWindowHint)
        dlg.setStyleSheet(
            f"QDialog {{ background: {Colors.BG_CARD};"
            f"  border: 1px solid {Colors.BORDER_LIGHT}; border-radius: {Radii.MD}px; }}"
            f"QCalendarWidget QAbstractItemView:enabled {{"
            f"  color: {Colors.TEXT_PRIMARY}; background: {Colors.BG_CARD};"
            f"  selection-background-color: {Colors.SELECTED_BG}; selection-color: {Colors.TEXT_PRIMARY}; }}"
            f"QCalendarWidget QWidget {{ color: {Colors.TEXT_PRIMARY};"
            f"  background: {Colors.BG_CARD}; }}"
            f"QCalendarWidget QToolButton {{ color: {Colors.TEXT_PRIMARY};"
            f"  background: {Colors.BG_CARD}; }}"
        )
        lay = QVBoxLayout(dlg)
        lay.setContentsMargins(8, 8, 8, 8)
        cal = QCalendarWidget(dlg)
        cal.setFirstDayOfWeek(Qt.DayOfWeek.Monday)
        cal.setGridVisible(False)
        cal.setNavigationBarVisible(True)
        # Set current selection
        cal.setSelectedDate(QDate(self._base_date.year, self._base_date.month, self._base_date.day))

        def _accept(qdate: QDate) -> None:
            self._base_date = date(qdate.year(), qdate.month(), qdate.day())
            self._refresh_calendar()
            dlg.accept()

        cal.activated.connect(_accept)
        lay.addWidget(cal)

        # Position below the date button
        btn_pos = self._date_btn.mapToGlobal(self._date_btn.rect().bottomLeft())
        dlg.move(btn_pos)
        dlg.exec()

    def _on_view_toggled(self, mode: str, checked: bool, btn: QPushButton) -> None:
        if not checked:
            return
        # Uncheck sibling buttons
        for b in self._view_btns:
            if b is not btn:
                b.blockSignals(True)
                b.setChecked(False)
                b.blockSignals(False)
        self._view_mode = mode
        self._refresh_calendar()

    # ── Session selection & drag ──────────────────────────────────────────────

    def _on_session_clicked(self, exp_id: str) -> None:
        exp = self._find_exp(exp_id)
        if exp is None:
            return
        self._selected_exp = exp
        self._grid.highlight_block(exp_id)
        self._show_experiment_detail(exp)
        logger.info(f"select_experiment: id={exp_id} title={exp.title}")

    def _on_session_time_changed(self, exp_id: str, new_start_ms: int) -> None:
        exp = self._find_exp(exp_id)
        if exp is None:
            return
        duration_ms = exp.planned_end - exp.planned_start
        exp.planned_start = new_start_ms
        exp.planned_end   = new_start_ms + duration_ms

        # Update date field from new start
        try:
            new_dt = datetime.fromtimestamp(new_start_ms / 1000)
            exp.date = new_dt.strftime("%Y-%m-%d")
        except Exception:
            pass

        # Recalculate internal timeline from new start
        exp.recalculate_times()

        self._grid.update_experiment(exp)
        if self._selected_exp and self._selected_exp.id == exp_id:
            self._show_experiment_detail(exp)

        self._schedule_save()
        logger.info(f"drag_session: id={exp_id} new_start={new_start_ms}")

    # ── Add Experiment ────────────────────────────────────────────────────────

    def _on_add_experiment(self) -> None:
        protocols = self.app.data.load_protocols()
        templates = self.app.data.load_templates()
        dlg = AddExperimentDialog(protocols, templates, parent=self)
        if dlg.exec() != AddExperimentDialog.DialogCode.Accepted:
            return

        proto = dlg.selected_protocol()
        if proto is None:
            return

        exp = make_scheduled_experiment(
            title=dlg.title(),
            protocol=proto,
            date_str=dlg.date_str(),
            start_ts_ms=dlg.start_ts_ms(),
            notes=dlg.notes(),
        )
        self._experiments.append(exp)
        self._grid.update_experiment(exp)
        self._schedule_save()

        # Select the new experiment
        self._on_session_clicked(exp.id)
        # Navigate to the date of the new experiment
        try:
            self._base_date = datetime.strptime(exp.date, "%Y-%m-%d").date()
            self._refresh_calendar()
            self._grid.highlight_block(exp.id)
        except Exception:
            pass

        ToastManager.show_success(f"Scheduled: {exp.title}")
        logger.info(f"add_experiment: id={exp.id} title={exp.title}")

    # ── Right panel detail ────────────────────────────────────────────────────

    def _show_experiment_detail(self, exp: ScheduledExperiment) -> None:
        """Rebuild the right panel for the given experiment."""
        self._selected_exp = exp
        self._clear_detail()

        # ── Experiment header ──────────────────────────────────────────────
        title_lbl = QLabel(exp.title)
        title_lbl.setStyleSheet(
            f"color: {Colors.TEXT_PRIMARY}; font-size: {Fonts.SIZE_LG}px; font-weight: 700;"
        )
        title_lbl.setWordWrap(True)
        self._detail_layout.addWidget(title_lbl)

        proto_lbl = QLabel(exp.protocol_name or "Custom")
        proto_lbl.setStyleSheet(
            f"color: {Colors.TEXT_SECOND}; font-size: {Fonts.SIZE_SM}px;"
        )
        self._detail_layout.addWidget(proto_lbl)

        meta_lbl = QLabel(
            f"{exp.date}  ·  "
            f"{format_time_ms(exp.planned_start)} – {format_time_ms(exp.planned_end)}"
            f"  ·  {format_duration_min(exp.total_duration)}"
        )
        meta_lbl.setStyleSheet(
            f"color: {Colors.TEXT_MUTED}; font-size: {Fonts.SIZE_XS}px;"
        )
        self._detail_layout.addWidget(meta_lbl)

        if exp.notes:
            notes_lbl = QLabel(exp.notes)
            notes_lbl.setStyleSheet(
                f"color: {Colors.TEXT_MUTED}; font-size: {Fonts.SIZE_XS}px;"
                f"font-style: italic;"
            )
            notes_lbl.setWordWrap(True)
            self._detail_layout.addWidget(notes_lbl)

        self._detail_layout.addWidget(HSeparator())

        # ── Timeline blocks ────────────────────────────────────────────────
        steps_hdr = QLabel(f"Timeline  ({len(exp.timeline_blocks)} blocks)")
        steps_hdr.setStyleSheet(
            f"color: {Colors.TEXT_SECOND}; font-size: {Fonts.SIZE_XS}px; font-weight: 600;"
        )
        self._detail_layout.addWidget(steps_hdr)

        for block in exp.timeline_blocks:
            row_w = _TimelineBlockRow(block, parent=self._detail_content)
            row_w.edit_requested.connect(
                lambda bid, e=exp: self._on_edit_block(e, bid))
            row_w.skip_requested.connect(
                lambda bid, e=exp: self._on_skip_block(e, bid))
            row_w.delete_requested.connect(
                lambda bid, e=exp: self._on_delete_block(e, bid))
            row_w.duplicate_requested.connect(
                lambda bid, e=exp: self._on_duplicate_block(e, bid))
            row_w.cancel_requested.connect(
                lambda bid, rt, e=exp: self._on_cancel_block(e, bid, rt))
            row_w.restore_requested.connect(
                lambda bid, e=exp: self._on_restore_block(e, bid))
            row_w.move_up_requested.connect(
                lambda bid, e=exp: self._on_move_up(e, bid))
            row_w.move_down_requested.connect(
                lambda bid, e=exp: self._on_move_down(e, bid))
            row_w.insert_before_requested.connect(
                lambda bid, bt, e=exp: self._on_insert_before(e, bid, bt))
            row_w.insert_after_requested.connect(
                lambda bid, bt, e=exp: self._on_insert_after(e, bid, bt))
            self._detail_layout.addWidget(row_w)

        self._detail_layout.addWidget(HSeparator())

        # ── Add block buttons ──────────────────────────────────────────────
        add_row = QHBoxLayout()
        add_row.setSpacing(6)
        for btype, label in [("break", "＋ Break"), ("task", "＋ Task"), ("note", "＋ Note")]:
            btn = QPushButton(label)
            btn.setFixedHeight(30)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setStyleSheet(
                f"QPushButton {{ background: {Colors.BG_CARD}; color: {Colors.TEXT_SECOND};"
                f"  border: 1px solid {Colors.BORDER_LIGHT}; border-radius: {Radii.LG}px;"
                f"  font-size: {Fonts.SIZE_SM}px; padding: 0 10px; }}"
                f"QPushButton:hover {{ background: {Colors.BG_CARD_HOV};"
                f"  color: {Colors.TEXT_PRIMARY}; }}"
            )
            btn.clicked.connect(lambda checked=False, bt=btype, e=exp: self._on_add_block(e, bt))
            add_row.addWidget(btn)
        add_row.addStretch()
        self._detail_layout.addLayout(add_row)

        self._detail_layout.addStretch()

    def _show_detail_placeholder(self) -> None:
        self._clear_detail()
        lbl = QLabel("Click an experiment on the calendar\nto view its timeline.")
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl.setWordWrap(True)
        lbl.setStyleSheet(
            f"color: {Colors.TEXT_MUTED}; font-size: {Fonts.SIZE_SM}px;"
            f"font-style: italic;"
        )
        self._detail_layout.addStretch()
        self._detail_layout.addWidget(lbl)
        self._detail_layout.addStretch()

    @staticmethod
    def _clear_layout(layout) -> None:
        """Recursively clear all items from a layout."""
        while layout.count():
            item = layout.takeAt(0)
            w = item.widget()
            if w is not None:
                w.deleteLater()
            else:
                sub = item.layout()
                if sub is not None:
                    SchedulePage._clear_layout(sub)

    def _clear_detail(self) -> None:
        self._clear_layout(self._detail_layout)

    # ── Timeline block actions ────────────────────────────────────────────────

    def _on_edit_block(self, exp: ScheduledExperiment, block_id: str) -> None:
        block = self._find_block(exp, block_id)
        if block is None:
            return
        dlg = EditBlockDialog(block=block, parent=self)
        if dlg.exec() != EditBlockDialog.DialogCode.Accepted:
            return
        block.title            = dlg.result_title()
        block.type             = dlg.result_type()
        block.duration_minutes = dlg.result_duration()
        block.notes            = dlg.result_notes()
        exp.recalculate_times()
        self._grid.update_experiment(exp)
        self._show_experiment_detail(exp)
        self._schedule_save()
        logger.info(f"edit_block: exp={exp.id} block={block_id}")

    def _on_skip_block(self, exp: ScheduledExperiment, block_id: str) -> None:
        block = self._find_block(exp, block_id)
        if block is None:
            return
        block.status = "skipped"
        exp.recalculate_times()
        self._grid.update_experiment(exp)
        self._show_experiment_detail(exp)
        self._schedule_save()
        logger.info(f"skip_block: exp={exp.id} block={block_id}")

    def _on_delete_block(self, exp: ScheduledExperiment, block_id: str) -> None:
        exp.timeline_blocks = [b for b in exp.timeline_blocks if b.id != block_id]
        exp.recalculate_times()
        self._grid.update_experiment(exp)
        self._show_experiment_detail(exp)
        self._schedule_save()
        logger.info(f"delete_block: exp={exp.id} block={block_id}")

    def _on_add_block(self, exp: ScheduledExperiment, block_type: str) -> None:
        dlg = EditBlockDialog(parent=self)
        # Pre-select the type
        idx = dlg._type_cb.findData(block_type)
        if idx >= 0:
            dlg._type_cb.setCurrentIndex(idx)
        if dlg.exec() != EditBlockDialog.DialogCode.Accepted:
            return

        last_end = exp.planned_end if not exp.timeline_blocks else exp.timeline_blocks[-1].end_time
        dur = dlg.result_duration()
        new_block = TimelineBlock.new(
            title=dlg.result_title(),
            block_type=dlg.result_type(),
            start_time_ms=last_end,
            duration_minutes=dur,
            notes=dlg.result_notes(),
            is_temporary=True,
        )
        exp.timeline_blocks.append(new_block)
        exp.recalculate_times()
        self._grid.update_experiment(exp)
        self._show_experiment_detail(exp)
        self._schedule_save()
        logger.info(f"add_block: exp={exp.id} type={block_type} dur={dur}m")

    def _on_duplicate_block(self, exp: ScheduledExperiment, block_id: str) -> None:
        import copy
        block = self._find_block(exp, block_id)
        if block is None:
            return
        dup = copy.deepcopy(block)
        dup.id = str(uuid.uuid4())
        dup.status = "planned"
        dup.retains_time = False
        idx = next((i for i, b in enumerate(exp.timeline_blocks) if b.id == block_id), -1)
        if idx >= 0:
            exp.timeline_blocks.insert(idx + 1, dup)
        else:
            exp.timeline_blocks.append(dup)
        exp.recalculate_times()
        self._grid.update_experiment(exp)
        self._show_experiment_detail(exp)
        self._schedule_save()
        logger.info(f"duplicate_block: exp={exp.id} orig={block_id} new={dup.id}")

    def _on_insert_before(self, exp: ScheduledExperiment,
                          ref_id: str, block_type: str) -> None:
        self._do_insert(exp, ref_id, block_type, after=False)

    def _on_insert_after(self, exp: ScheduledExperiment,
                         ref_id: str, block_type: str) -> None:
        self._do_insert(exp, ref_id, block_type, after=True)

    def _do_insert(self, exp: ScheduledExperiment, ref_id: str,
                   block_type: str, after: bool) -> None:
        dlg = EditBlockDialog(parent=self)
        idx_cb = dlg._type_cb.findData(block_type)
        if idx_cb >= 0:
            dlg._type_cb.setCurrentIndex(idx_cb)
        if dlg.exec() != EditBlockDialog.DialogCode.Accepted:
            return
        ref_idx = next((i for i, b in enumerate(exp.timeline_blocks) if b.id == ref_id), -1)
        insert_at = (ref_idx + 1) if after else max(0, ref_idx)
        new_block = TimelineBlock.new(
            title=dlg.result_title(),
            block_type=dlg.result_type(),
            start_time_ms=exp.planned_start,  # recalculate_times will fix it
            duration_minutes=dlg.result_duration(),
            notes=dlg.result_notes(),
        )
        if ref_idx < 0:
            exp.timeline_blocks.append(new_block)
        else:
            exp.timeline_blocks.insert(insert_at, new_block)
        exp.recalculate_times()
        self._grid.update_experiment(exp)
        self._show_experiment_detail(exp)
        self._schedule_save()
        where = "after" if after else "before"
        logger.info(f"insert_{where}: exp={exp.id} ref={ref_id} new={new_block.id}")

    def _on_cancel_block(self, exp: ScheduledExperiment,
                         block_id: str, retains_time: bool) -> None:
        block = self._find_block(exp, block_id)
        if block is None:
            return
        block.status = "canceled"
        block.retains_time = retains_time
        exp.recalculate_times()
        self._grid.update_experiment(exp)
        self._show_experiment_detail(exp)
        self._schedule_save()
        label = "retains_time" if retains_time else "removes_time"
        logger.info(f"cancel_block: exp={exp.id} block={block_id} {label}")

    def _on_restore_block(self, exp: ScheduledExperiment, block_id: str) -> None:
        block = self._find_block(exp, block_id)
        if block is None:
            return
        block.status = "planned"
        block.retains_time = False
        exp.recalculate_times()
        self._grid.update_experiment(exp)
        self._show_experiment_detail(exp)
        self._schedule_save()
        logger.info(f"restore_block: exp={exp.id} block={block_id}")

    def _on_move_up(self, exp: ScheduledExperiment, block_id: str) -> None:
        blocks = exp.timeline_blocks
        idx = next((i for i, b in enumerate(blocks) if b.id == block_id), -1)
        if idx <= 0:
            return
        blocks[idx - 1], blocks[idx] = blocks[idx], blocks[idx - 1]
        exp.recalculate_times()
        self._grid.update_experiment(exp)
        self._show_experiment_detail(exp)
        self._schedule_save()
        logger.info(f"move_up: exp={exp.id} block={block_id}")

    def _on_move_down(self, exp: ScheduledExperiment, block_id: str) -> None:
        blocks = exp.timeline_blocks
        idx = next((i for i, b in enumerate(blocks) if b.id == block_id), -1)
        if idx < 0 or idx >= len(blocks) - 1:
            return
        blocks[idx], blocks[idx + 1] = blocks[idx + 1], blocks[idx]
        exp.recalculate_times()
        self._grid.update_experiment(exp)
        self._show_experiment_detail(exp)
        self._schedule_save()
        logger.info(f"move_down: exp={exp.id} block={block_id}")

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _find_exp(self, exp_id: str) -> ScheduledExperiment | None:
        return next((e for e in self._experiments if e.id == exp_id), None)

    def _find_block(self, exp: ScheduledExperiment, block_id: str) -> TimelineBlock | None:
        return next((b for b in exp.timeline_blocks if b.id == block_id), None)

    def _apply_block_change(self, exp: ScheduledExperiment,
                            log_action: str = "block_changed") -> None:
        """Recalculate times, refresh grid + detail panel, and schedule save.

        Wraps the common post-mutation pattern used by all block edit handlers.
        Includes perf instrumentation.
        """
        with perf.measure("schedule_recalc"):
            exp.recalculate_times()
        self._grid.update_experiment(exp)
        self._show_experiment_detail(exp)
        self._schedule_save()
        logger.info(log_action)
