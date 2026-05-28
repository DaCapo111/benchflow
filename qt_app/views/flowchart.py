"""
Flowchart — Phase 8A: QGraphicsScene protocol workflow visualization.

Layout
------
FlowchartPage (3-pane QSplitter)
├── Left  (200 px): protocol selector  (search + QListWidget)
├── Center (stretch): canvas
│   ├── Toolbar: [Fit] [⊙] [−] [zoom%] [+]
│   └── _FlowchartView (QGraphicsView)
│       └── QGraphicsScene
│           ├── _StepNode × N  (click → right panel)
│           └── _ArrowItem × N-1
└── Right (300 px): _StepDetailPanel

Node anatomy (264 × 90 px)
──────────────────────────
║  ①  Step Title, up to 2 lines
║     preparation   ⏱ 45m
║     🌡 4°C
(6 px type-color left strip, circular number badge)
"""
from __future__ import annotations

import math
from typing import Any

from PySide6.QtCore import Qt, Signal, QRectF, QPointF
from PySide6.QtGui import (
    QBrush, QColor, QFont, QFontMetrics,
    QPainter, QPainterPath, QPen, QTransform,
)
from PySide6.QtWidgets import (
    QFrame, QGraphicsItem, QGraphicsObject, QGraphicsPathItem,
    QGraphicsScene, QGraphicsView,
    QHBoxLayout, QLabel, QLineEdit, QListWidget, QListWidgetItem,
    QPlainTextEdit, QPushButton, QScrollArea,
    QSizePolicy, QSplitter, QVBoxLayout, QWidget,
)

from qt_app.theme import Colors, Fonts, Radii
from qt_app.components.widgets import HSeparator, PageTitle, SubLabel
from qt_app.services.event_bus import bus
from qt_app.services.data import DataService
from qt_app.views.base_page import BasePage


# ── Step-type color map (same palette as editor.py) ──────────────────────────

_TYPE_COLOR: dict[str, str] = {
    "preparation":       "#3b82f6",
    "reagent_addition":  "#14b8a6",
    "mixing":            "#a855f7",
    "incubation":        "#f97316",
    "waiting":           "#475569",
    "centrifuge":        "#6366f1",
    "wash":              "#06b6d4",
    "transfer":          "#818cf8",
    "pipetting":         "#38bdf8",
    "resuspension":      "#22c55e",
    "staining":          "#f472b6",
    "blocking":          "#fb7185",
    "electrophoresis":   "#c084fc",
    "gel_running":       "#a78bfa",
    "membrane_transfer": "#60a5fa",
    "imaging":           "#34d399",
    "measurement":       "#fb923c",
    "heating":           "#fbbf24",
    "cooling":           "#7dd3fc",
    "lysis":             "#f87171",
    "harvest":           "#4ade80",
    "sample_collection": "#a3e635",
    "storage":           "#94a3b8",
    "note":              "#e2e8f0",
    "other":             "#64748b",
}


def _type_color(step_type: str) -> QColor:
    return QColor(_TYPE_COLOR.get(step_type, "#64748b"))


def _duration_str(step: dict) -> str:
    mins = (
        float(step.get("handsOnMinutes", 0)) +
        float(step.get("waitMinutes",    0)) +
        float(step.get("bufferMinutes",  0))
    )
    m = int(round(mins))
    if m <= 0:
        return ""
    h, rem = divmod(m, 60)
    if h and rem:
        return f"{h}h {rem}m"
    return f"{h}h" if h else f"{rem}m"


def _condition_snippet(step: dict) -> str:
    """First non-empty condition field, truncated."""
    for field in ("temperature", "centrifugeCondition", "shakingRotation"):
        v = step.get(field, "").strip()
        if v:
            return v[:30] + ("…" if len(v) > 30 else "")
    return ""


# ── Node geometry ─────────────────────────────────────────────────────────────

NODE_W   = 264
NODE_H   = 90
NODE_RAD = 10
STRIP_W  = 6
BADGE_D  = 22
VGAP     = 48    # vertical gap between nodes (arrow space)
SCENE_X  = 30   # left margin in scene


# ── _StepNode ─────────────────────────────────────────────────────────────────

class _StepNode(QGraphicsObject):
    """Clickable rounded-rect node representing one protocol step."""

    node_clicked = Signal(int)   # step index

    def __init__(self, step: dict, index: int,
                 parent: QGraphicsItem | None = None) -> None:
        super().__init__(parent)
        self._step    = step
        self._index   = index
        self._sel     = False

        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, True)
        self.setAcceptHoverEvents(True)
        self.setToolTip(step.get("title", f"Step {index + 1}"))

        # Pre-compute paint values ─────────────────────────────────────────
        stype = step.get("type", "other")
        self._type_qcolor = _type_color(stype)
        self._type_str    = stype.replace("_", " ").title()
        self._dur_str     = _duration_str(step)
        self._cond_str    = _condition_snippet(step)

        # Pre-wrap title into ≤2 lines
        title = step.get("title", "") or f"Step {index + 1}"
        badge_x   = STRIP_W + 5
        content_x = badge_x + BADGE_D + 7
        max_w     = NODE_W - content_x - 8

        title_font = QFont()
        title_font.setPointSize(Fonts.SIZE_SM)
        title_font.setWeight(QFont.Weight.Bold)
        fm = QFontMetrics(title_font)
        self._title_lines = _wrap_text(title, fm, max_w, max_lines=2)

    # ── QGraphicsObject interface ─────────────────────────────────────────────

    def boundingRect(self) -> QRectF:
        return QRectF(0, 0, NODE_W, NODE_H)

    def paint(self, painter: QPainter, option, widget=None) -> None:  # type: ignore[override]
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)

        w, h = NODE_W, NODE_H

        # ── Background ───────────────────────────────────────────────────────
        bg_path = QPainterPath()
        bg_path.addRoundedRect(QRectF(0, 0, w, h), NODE_RAD, NODE_RAD)

        if self._sel:
            bg_color = QColor(28, 52, 90)
            border_pen = QPen(QColor(Colors.ACCENT), 2)
        else:
            bg_color = QColor(Colors.BG_CARD)
            border_pen = QPen(QColor(Colors.BORDER), 1)

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(bg_color)
        painter.drawPath(bg_path)

        # ── Left accent strip (clipped to bg rounded shape) ──────────────────
        painter.save()
        painter.setClipPath(bg_path)
        painter.setBrush(self._type_qcolor)
        painter.drawRect(QRectF(0, 0, STRIP_W, h))
        painter.restore()

        # ── Border ───────────────────────────────────────────────────────────
        painter.setPen(border_pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawPath(bg_path)

        # ── Badge circle ─────────────────────────────────────────────────────
        bx = float(STRIP_W + 5)
        by = (h - BADGE_D) / 2.0
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(self._type_qcolor)
        painter.drawEllipse(QRectF(bx, by, BADGE_D, BADGE_D))

        num_f = QFont()
        num_f.setPointSize(9)
        num_f.setWeight(QFont.Weight.Bold)
        painter.setFont(num_f)
        painter.setPen(QColor("#ffffff"))
        painter.drawText(QRectF(bx, by, BADGE_D, BADGE_D),
                         Qt.AlignmentFlag.AlignCenter,
                         str(self._index + 1))

        # ── Content area ─────────────────────────────────────────────────────
        cx = bx + BADGE_D + 7
        cw = w - cx - 8

        title_f = QFont()
        title_f.setPointSize(Fonts.SIZE_SM)
        title_f.setWeight(QFont.Weight.Bold)
        painter.setFont(title_f)
        painter.setPen(QColor(Colors.TEXT_PRIMARY))

        n_lines  = len(self._title_lines)
        line_h   = 16.0
        gap      = 4.0

        # Calculate vertical layout
        sub_h = n_lines * line_h + gap + 14.0
        if self._cond_str:
            sub_h += gap + 12.0
        title_top = (h - sub_h) / 2.0

        # Title lines
        for i, line in enumerate(self._title_lines):
            ty = title_top + i * line_h
            painter.drawText(QRectF(cx, ty, cw, line_h),
                             Qt.AlignmentFlag.AlignLeft |
                             Qt.AlignmentFlag.AlignVCenter, line)

        # Type + duration row
        meta_y = title_top + n_lines * line_h + gap
        meta_f = QFont()
        meta_f.setPointSize(Fonts.SIZE_XS)
        painter.setFont(meta_f)

        painter.setPen(self._type_qcolor)
        meta_fm    = QFontMetrics(meta_f)
        type_text  = self._type_str
        painter.drawText(QRectF(cx, meta_y, cw, 14.0),
                         Qt.AlignmentFlag.AlignLeft |
                         Qt.AlignmentFlag.AlignVCenter, type_text)

        if self._dur_str:
            tx = cx + meta_fm.horizontalAdvance(type_text) + 8
            rem_w = cw - (tx - cx)
            if rem_w > 20:
                painter.setPen(QColor(Colors.TEXT_MUTED))
                painter.drawText(QRectF(tx, meta_y, rem_w, 14.0),
                                 Qt.AlignmentFlag.AlignLeft |
                                 Qt.AlignmentFlag.AlignVCenter,
                                 f"⏱ {self._dur_str}")

        # Condition snippet
        if self._cond_str:
            cond_y = meta_y + 14.0 + gap
            if cond_y + 12.0 <= h - 4:
                cond_f = QFont()
                cond_f.setPointSize(Fonts.SIZE_XS)
                painter.setFont(cond_f)
                painter.setPen(QColor(Colors.TEXT_MUTED))
                painter.drawText(QRectF(cx, cond_y, cw, 12.0),
                                 Qt.AlignmentFlag.AlignLeft |
                                 Qt.AlignmentFlag.AlignVCenter,
                                 f"● {self._cond_str}")

    # ── Interaction ───────────────────────────────────────────────────────────

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.node_clicked.emit(self._index)
        super().mousePressEvent(event)

    def set_selected(self, sel: bool) -> None:
        self._sel = sel
        self.update()   # trigger repaint


def _wrap_text(text: str, fm: QFontMetrics, max_w: int,
               max_lines: int = 2) -> list[str]:
    """Wrap *text* word-by-word into ≤max_lines lines of ≤max_w pixels each."""
    if fm.horizontalAdvance(text) <= max_w:
        return [text]

    words = text.split()
    lines: list[str] = []
    current = ""

    for word in words:
        if len(lines) == max_lines - 1:
            # Last allowed line — append remaining and elide
            rest = (current + " " + word).strip()
            lines.append(fm.elidedText(
                rest + " " + " ".join(words[words.index(word) + 1:]),
                Qt.TextElideMode.ElideRight, max_w
            ).strip())
            return lines

        test = (current + " " + word).strip()
        if fm.horizontalAdvance(test) <= max_w:
            current = test
        else:
            if current:
                lines.append(current)
            current = word

    if current:
        lines.append(current)
    return lines or [text]


# ── _ArrowItem ────────────────────────────────────────────────────────────────

_ARROW_HEAD = 8   # half-width of arrowhead
_ARROW_TIP  = 10  # height of arrowhead


class _ArrowItem(QGraphicsPathItem):
    """Downward arrow connecting two consecutive nodes."""

    def __init__(self, x_center: float, y_start: float, y_end: float,
                 parent: QGraphicsItem | None = None) -> None:
        super().__init__(parent)
        length = y_end - y_start
        shaft  = max(0, length - _ARROW_TIP)

        path = QPainterPath()
        path.moveTo(0, 0)
        path.lineTo(0, shaft)
        # Arrowhead
        path.moveTo(-_ARROW_HEAD, shaft)
        path.lineTo(0, length)
        path.lineTo(_ARROW_HEAD, shaft)

        self.setPath(path)
        self.setPos(x_center, y_start)

        pen = QPen(QColor(Colors.BORDER), 1.5)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        self.setPen(pen)
        self.setZValue(-1)


# ── _FlowchartView ────────────────────────────────────────────────────────────

class _FlowchartView(QGraphicsView):
    """QGraphicsView with Ctrl+wheel zoom and drag-to-pan."""

    def __init__(self, scene: QGraphicsScene,
                 parent: QWidget | None = None) -> None:
        super().__init__(scene, parent)
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorViewCenter)
        self.setStyleSheet(f"background: {Colors.BG_PAGE}; border: none;")
        self._zoom_level = 1.0

    def wheelEvent(self, event) -> None:
        factor = 1.20 if event.angleDelta().y() > 0 else (1 / 1.20)
        self._do_zoom(factor)

    def zoom_in(self) -> None:
        self._do_zoom(1.25)

    def zoom_out(self) -> None:
        self._do_zoom(0.80)

    def fit_view(self) -> None:
        rect = self.scene().itemsBoundingRect()
        if rect.isEmpty():
            return
        padded = rect.adjusted(-24, -24, 24, 24)
        self.fitInView(padded, Qt.AspectRatioMode.KeepAspectRatio)
        self._zoom_level = self.transform().m11()

    def center_view(self) -> None:
        rect = self.scene().itemsBoundingRect()
        if not rect.isEmpty():
            self.centerOn(rect.center())

    def reset_zoom(self) -> None:
        self.setTransform(QTransform())
        self._zoom_level = 1.0

    def zoom_level_pct(self) -> int:
        return int(self.transform().m11() * 100)

    def _do_zoom(self, factor: float) -> None:
        new_z = self._zoom_level * factor
        if new_z < 0.10 or new_z > 5.0:
            return
        self.scale(factor, factor)
        self._zoom_level = new_z


# ── _StepDetailPanel ──────────────────────────────────────────────────────────

class _StepDetailPanel(QWidget):
    """Right panel — shows full detail for selected node."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setMinimumWidth(280)
        self.setStyleSheet(f"background: {Colors.BG_SIDEBAR};")

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        self._scroll = QScrollArea()
        self._scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._scroll.setWidgetResizable(True)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._scroll.setStyleSheet(f"background: {Colors.BG_SIDEBAR};")
        outer.addWidget(self._scroll)

        self._inner = QWidget()
        self._inner.setStyleSheet(f"background: {Colors.BG_SIDEBAR};")
        self._lay = QVBoxLayout(self._inner)
        self._lay.setContentsMargins(16, 16, 16, 24)
        self._lay.setSpacing(6)
        self._scroll.setWidget(self._inner)

        self._show_placeholder()

    # ── Public API ────────────────────────────────────────────────────────────

    def show_step(self, step: dict, index: int, total: int) -> None:
        self._clear()
        lay = self._lay
        stype   = step.get("type", "other")
        tcolor  = _TYPE_COLOR.get(stype, "#64748b")

        # ── Step header ───────────────────────────────────────────────────────
        hdr_row = QHBoxLayout()
        hdr_row.setSpacing(8)
        num_lbl = QLabel(f"{index + 1}")
        num_lbl.setFixedSize(28, 28)
        num_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        num_lbl.setStyleSheet(
            f"background: {tcolor}; color: white; border-radius: 14px;"
            f"font-size: {Fonts.SIZE_SM}px; font-weight: 700;"
        )
        hdr_row.addWidget(num_lbl)
        of_lbl = QLabel(f"of {total}")
        of_lbl.setStyleSheet(f"color: {Colors.TEXT_MUTED}; font-size: {Fonts.SIZE_XS}px;")
        hdr_row.addWidget(of_lbl)
        hdr_row.addStretch()
        lay.addLayout(hdr_row)

        # Title
        title_lbl = QLabel(step.get("title", f"Step {index + 1}"))
        title_lbl.setWordWrap(True)
        title_lbl.setStyleSheet(
            f"color: {Colors.TEXT_PRIMARY}; font-size: {Fonts.SIZE_MD}px; font-weight: 700;"
        )
        lay.addWidget(title_lbl)

        # Type badge
        type_lbl = QLabel(stype.replace("_", " ").title())
        type_lbl.setStyleSheet(
            f"color: {tcolor}; background: rgba(0,0,0,0.25);"
            f"border-radius: 6px; padding: 2px 8px;"
            f"font-size: {Fonts.SIZE_XS}px; font-weight: 600;"
        )
        type_lbl.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        lay.addWidget(type_lbl)
        lay.addWidget(HSeparator())

        # ── Timing ────────────────────────────────────────────────────────────
        def timing_row(label: str, mins: float, color: str) -> None:
            if mins <= 0:
                return
            r = QHBoxLayout()
            r.setSpacing(8)
            k = QLabel(label)
            k.setFixedWidth(72)
            k.setStyleSheet(f"color: {Colors.TEXT_MUTED}; font-size: {Fonts.SIZE_XS}px;")
            v = QLabel(DataService.format_duration(mins))
            v.setStyleSheet(f"color: {color}; font-size: {Fonts.SIZE_SM}px; font-weight: 600;")
            r.addWidget(k)
            r.addWidget(v)
            r.addStretch()
            lay.addLayout(r)

        timing_row("Hands-on", float(step.get("handsOnMinutes", 0)), Colors.SUCCESS)
        timing_row("Wait",     float(step.get("waitMinutes",    0)), Colors.WARNING)
        timing_row("Buffer",   float(step.get("bufferMinutes",  0)), Colors.TEXT_SECOND)

        total_m = (float(step.get("handsOnMinutes", 0)) +
                   float(step.get("waitMinutes",    0)) +
                   float(step.get("bufferMinutes",  0)))
        if total_m > 0:
            r = QHBoxLayout()
            k = QLabel("Total")
            k.setFixedWidth(72)
            k.setStyleSheet(f"color: {Colors.TEXT_SECOND}; font-size: {Fonts.SIZE_XS}px; font-weight: 600;")
            v = QLabel(DataService.format_duration(total_m))
            v.setStyleSheet(f"color: {Colors.TEXT_PRIMARY}; font-size: {Fonts.SIZE_SM}px; font-weight: 700;")
            r.addWidget(k); r.addWidget(v); r.addStretch()
            lay.addLayout(r)
            lay.addWidget(HSeparator())

        # ── Conditions ────────────────────────────────────────────────────────
        conds = [
            ("Temperature",  step.get("temperature",         "")),
            ("Centrifuge",   step.get("centrifugeCondition",  "")),
            ("Shaking/RPM",  step.get("shakingRotation",      "")),
        ]
        for label, val in conds:
            if not val.strip():
                continue
            r = QHBoxLayout()
            k = QLabel(label)
            k.setFixedWidth(72)
            k.setStyleSheet(f"color: {Colors.TEXT_MUTED}; font-size: {Fonts.SIZE_XS}px;")
            v = QLabel(val)
            v.setWordWrap(True)
            v.setStyleSheet(f"color: {Colors.TEXT_PRIMARY}; font-size: {Fonts.SIZE_SM}px;")
            r.addWidget(k); r.addWidget(v, stretch=1)
            lay.addLayout(r)
        if any(v.strip() for _, v in conds):
            lay.addWidget(HSeparator())

        # ── Description / Notes / Warnings ────────────────────────────────────
        for label, field, color in [
            ("Description", "description", Colors.TEXT_PRIMARY),
            ("Notes",       "notes",       Colors.TEXT_SECOND),
            ("⚠ Warnings", "warnings",    Colors.WARNING),
        ]:
            text = step.get(field, "").strip()
            if not text:
                continue
            lay.addWidget(self._txt_lbl(label, Colors.TEXT_MUTED))
            body = QLabel(text)
            body.setWordWrap(True)
            body.setStyleSheet(
                f"color: {color}; font-size: {Fonts.SIZE_SM}px;"
                f"padding: 4px 0;"
            )
            lay.addWidget(body)

        # ── Reagents ──────────────────────────────────────────────────────────
        reagents = step.get("reagents", [])
        if reagents:
            lay.addWidget(HSeparator())
            lay.addWidget(self._txt_lbl("🧪 Reagents", Colors.TEXT_MUTED))
            for r in reagents:
                name   = r.get("name", "")
                amount = r.get("amount", "")
                unit   = r.get("unit", r.get("amountUnit", ""))
                parts  = [x for x in [amount, unit] if x]
                suffix = f"  —  {' '.join(parts)}" if parts else ""
                rl = QLabel(f"• {name}{suffix}")
                rl.setWordWrap(True)
                rl.setStyleSheet(
                    f"color: {Colors.TEXT_SECOND}; font-size: {Fonts.SIZE_SM}px;"
                )
                lay.addWidget(rl)

        # ── Equipment ─────────────────────────────────────────────────────────
        equipment = step.get("equipment", [])
        if equipment:
            lay.addWidget(HSeparator())
            lay.addWidget(self._txt_lbl("🔬 Equipment", Colors.TEXT_MUTED))
            for e in equipment:
                el = QLabel(f"• {str(e).strip()}")
                el.setWordWrap(True)
                el.setStyleSheet(
                    f"color: {Colors.TEXT_SECOND}; font-size: {Fonts.SIZE_SM}px;"
                )
                lay.addWidget(el)

        # ── Checklist ─────────────────────────────────────────────────────────
        checklist = step.get("checklist", [])
        if checklist:
            lay.addWidget(HSeparator())
            lay.addWidget(self._txt_lbl("☑ Checklist", Colors.TEXT_MUTED))
            for item in checklist:
                txt = str(item.get("text", item) if isinstance(item, dict) else item).strip()
                if txt:
                    cl = QLabel(f"☐  {txt}")
                    cl.setWordWrap(True)
                    cl.setStyleSheet(
                        f"color: {Colors.TEXT_SECOND}; font-size: {Fonts.SIZE_SM}px;"
                    )
                    lay.addWidget(cl)

        # ── Substeps ─────────────────────────────────────────────────────────
        substeps = step.get("substeps", [])
        if substeps:
            lay.addWidget(HSeparator())
            lay.addWidget(self._txt_lbl("◈ Substeps", Colors.TEXT_MUTED))
            for i, s in enumerate(substeps):
                txt = str(s.get("text", s) if isinstance(s, dict) else s).strip()
                if txt:
                    sl = QLabel(f"  {i+1}. {txt}")
                    sl.setWordWrap(True)
                    sl.setStyleSheet(
                        f"color: {Colors.TEXT_SECOND}; font-size: {Fonts.SIZE_SM}px;"
                    )
                    lay.addWidget(sl)

        lay.addStretch()

    def show_placeholder(self) -> None:
        self._clear()
        self._show_placeholder()

    # ── Helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def _txt_lbl(text: str, color: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setStyleSheet(
            f"color: {color}; font-size: {Fonts.SIZE_XS}px; font-weight: 700;"
        )
        return lbl

    def _show_placeholder(self) -> None:
        self._lay.addStretch()
        icon = QLabel("⎇")
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon.setStyleSheet("font-size: 36px;")
        self._lay.addWidget(icon)
        lbl = QLabel("Click a step node\nto see its details here.")
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


def _clear_layout(layout) -> None:
    while layout.count():
        item = layout.takeAt(0)
        w = item.widget()
        if w:
            w.deleteLater()
        elif item.layout():
            _clear_layout(item.layout())


# ── FlowchartPage ─────────────────────────────────────────────────────────────

class FlowchartPage(BasePage):
    """Protocol Flowchart — Phase 8A."""

    def __init__(self, app: "BenchFlowApp", parent: QWidget | None = None) -> None:  # type: ignore[name-defined]
        super().__init__(app, parent)
        self._protocols:   list[dict] = []
        self._current_proto: dict | None = None
        self._nodes:       list[_StepNode] = []
        self._selected_idx: int = -1
        self._search_str:  str = ""

        self._scene  = QGraphicsScene()
        self._scene.setBackgroundBrush(QBrush(QColor(Colors.BG_PAGE)))

        self._build()
        self._subscribe_events()
        self._load_protocols()

    # ── EventBus ──────────────────────────────────────────────────────────────

    def _subscribe_events(self) -> None:
        bus.subscribe("protocol_created", self._on_proto_changed)
        bus.subscribe("protocol_updated", self._on_proto_changed)
        bus.subscribe("protocol_deleted", self._on_proto_changed)

    def _on_proto_changed(self, **_kw) -> None:
        cur_id = self._current_proto.get("id", "") if self._current_proto else ""
        self._load_protocols()
        if cur_id:
            for p in self._protocols:
                if p.get("id") == cur_id:
                    self._open_protocol(p)
                    break

    # ── UI construction ───────────────────────────────────────────────────────

    def _build(self) -> None:
        outer = QVBoxLayout()
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # ── Top bar ───────────────────────────────────────────────────────────
        bar = QWidget()
        bar.setFixedHeight(56)
        bar.setStyleSheet(f"background: {Colors.BG_PAGE};")
        bar_lay = QHBoxLayout(bar)
        bar_lay.setContentsMargins(24, 0, 24, 0)
        bar_lay.setSpacing(12)

        title_lbl = PageTitle("Flowchart")
        bar_lay.addWidget(title_lbl)

        self._proto_name_lbl = QLabel("— Select a protocol —")
        self._proto_name_lbl.setStyleSheet(
            f"color: {Colors.TEXT_SECOND}; font-size: {Fonts.SIZE_SM}px;"
        )
        bar_lay.addWidget(self._proto_name_lbl, stretch=1)

        # Canvas toolbar (zoom controls)
        self._zoom_lbl = QLabel("100%")
        self._zoom_lbl.setFixedWidth(44)
        self._zoom_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._zoom_lbl.setStyleSheet(
            f"color: {Colors.TEXT_MUTED}; font-size: {Fonts.SIZE_XS}px;"
        )

        fit_btn  = self._toolbar_btn("⊞ Fit",    self._on_fit)
        cent_btn = self._toolbar_btn("⊙",         self._on_center)
        zoom_out = self._toolbar_btn("−",          self._on_zoom_out)
        zoom_in  = self._toolbar_btn("＋",          self._on_zoom_in)
        reset_btn = self._toolbar_btn("1:1",       self._on_reset_zoom)

        for w in (fit_btn, cent_btn, zoom_out, self._zoom_lbl, zoom_in, reset_btn):
            bar_lay.addWidget(w)

        outer.addWidget(bar)
        outer.addWidget(HSeparator())

        # ── 3-pane splitter ───────────────────────────────────────────────────
        self._splitter = QSplitter(Qt.Orientation.Horizontal)
        self._splitter.setStyleSheet(
            f"QSplitter::handle {{ background: {Colors.BORDER}; width: 1px; }}"
        )

        # ── Left: protocol list ───────────────────────────────────────────────
        left_w = QWidget()
        left_w.setStyleSheet(f"background: {Colors.BG_PAGE};")
        left_lay = QVBoxLayout(left_w)
        left_lay.setContentsMargins(12, 12, 8, 12)
        left_lay.setSpacing(8)

        lhdr = QLabel("Protocols")
        lhdr.setStyleSheet(
            f"color: {Colors.TEXT_PRIMARY}; font-size: {Fonts.SIZE_SM}px;"
            f"font-weight: 700;"
        )
        left_lay.addWidget(lhdr)

        self._search_box = QLineEdit()
        self._search_box.setPlaceholderText("🔍 Search…")
        self._search_box.setFixedHeight(32)
        self._search_box.setStyleSheet(
            f"QLineEdit {{ background: {Colors.BG_INPUT}; color: {Colors.TEXT_PRIMARY};"
            f"  border: 1px solid {Colors.BORDER}; border-radius: {Radii.SM}px;"
            f"  padding: 0 10px; font-size: {Fonts.SIZE_SM}px; }}"
            f"QLineEdit:focus {{ border-color: {Colors.ACCENT}; }}"
        )
        self._search_box.textChanged.connect(self._on_search)
        left_lay.addWidget(self._search_box)

        self._proto_list = QListWidget()
        self._proto_list.setStyleSheet(
            f"QListWidget {{ background: transparent; color: {Colors.TEXT_PRIMARY};"
            f"  border: none; outline: none; font-size: {Fonts.SIZE_SM}px; }}"
            f"QListWidget::item {{ padding: 7px 8px; border-radius: {Radii.SM}px; }}"
            f"QListWidget::item:hover {{ background: {Colors.BG_CARD_HOV}; }}"
            f"QListWidget::item:selected {{ background: {Colors.ACCENT}; color: white; }}"
        )
        self._proto_list.currentItemChanged.connect(self._on_list_selection)
        left_lay.addWidget(self._proto_list, stretch=1)

        self._step_count_lbl = QLabel("")
        self._step_count_lbl.setStyleSheet(
            f"color: {Colors.TEXT_MUTED}; font-size: {Fonts.SIZE_XS}px;"
            f"text-align: center;"
        )
        self._step_count_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        left_lay.addWidget(self._step_count_lbl)

        # ── Center: canvas ────────────────────────────────────────────────────
        center_w = QWidget()
        center_w.setStyleSheet(f"background: {Colors.BG_PAGE};")
        center_lay = QVBoxLayout(center_w)
        center_lay.setContentsMargins(0, 0, 0, 0)
        center_lay.setSpacing(0)

        self._view = _FlowchartView(self._scene)
        center_lay.addWidget(self._view, stretch=1)

        # Empty state overlay
        self._empty_lbl = QLabel(
            "Select a protocol or template to view its workflow."
        )
        self._empty_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._empty_lbl.setWordWrap(True)
        self._empty_lbl.setStyleSheet(
            f"color: {Colors.TEXT_MUTED}; font-size: {Fonts.SIZE_MD}px;"
            f"font-style: italic;"
        )
        center_lay.addWidget(self._empty_lbl)
        self._view.hide()  # hidden until a protocol is loaded

        # ── Right: step detail ────────────────────────────────────────────────
        self._detail = _StepDetailPanel()

        self._splitter.addWidget(left_w)
        self._splitter.addWidget(center_w)
        self._splitter.addWidget(self._detail)
        self._splitter.setSizes([200, 620, 300])
        self._splitter.setChildrenCollapsible(False)

        outer.addWidget(self._splitter, stretch=1)
        self._root_layout.addLayout(outer)

    @staticmethod
    def _toolbar_btn(label: str, slot) -> QPushButton:
        btn = QPushButton(label)
        btn.setFixedHeight(30)
        btn.setMinimumWidth(32 if len(label) <= 2 else 54)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setStyleSheet(
            f"QPushButton {{ background: {Colors.BG_CARD}; color: {Colors.TEXT_SECOND};"
            f"  border: 1px solid {Colors.BORDER}; border-radius: {Radii.SM}px;"
            f"  font-size: {Fonts.SIZE_SM}px; padding: 0 8px; }}"
            f"QPushButton:hover {{ background: {Colors.BG_CARD_HOV};"
            f"  color: {Colors.TEXT_PRIMARY}; }}"
        )
        btn.clicked.connect(slot)
        return btn

    # ── Data loading ──────────────────────────────────────────────────────────

    def _load_protocols(self) -> None:
        # User protocols first, then built-in templates (visually separated)
        user_protos = self.app.data.load_protocols()
        templates   = self.app.data.load_templates()
        self._protocols = user_protos + templates
        self._rebuild_list()

    def _rebuild_list(self) -> None:
        from PySide6.QtGui import QColor as _QColor
        q = self._search_str.lower()
        items = [
            p for p in self._protocols
            if not q or q in p.get("name", "").lower()
        ]

        current_id = (self._current_proto.get("id", "")
                      if self._current_proto else "")

        self._proto_list.blockSignals(True)
        self._proto_list.clear()
        for p in items:
            n_steps = len(p.get("steps", []))
            is_tmpl = p.get("id", "").startswith("tmpl_")
            prefix  = "⊞ " if is_tmpl else "  "
            label   = f"{prefix}{p.get('name','Untitled')}  ({n_steps})"
            item = QListWidgetItem(label)
            item.setData(Qt.ItemDataRole.UserRole, p)
            if is_tmpl:
                item.setForeground(_QColor(Colors.TEXT_MUTED))
            self._proto_list.addItem(item)

        # Restore selection
        if current_id:
            for i in range(self._proto_list.count()):
                it = self._proto_list.item(i)
                if it and (it.data(Qt.ItemDataRole.UserRole) or {}).get("id") == current_id:
                    self._proto_list.setCurrentItem(it)
                    break
        self._proto_list.blockSignals(False)

    # ── Canvas rendering ──────────────────────────────────────────────────────

    def _open_protocol(self, proto: dict) -> None:
        self._current_proto = proto
        self._selected_idx  = -1
        self._nodes.clear()
        self._scene.clear()

        steps = proto.get("steps", [])
        self._proto_name_lbl.setText(
            f"{proto.get('name', 'Protocol')}  ·  {len(steps)} step{'s' if len(steps)!=1 else ''}"
        )
        self._step_count_lbl.setText(f"{len(steps)} steps")
        self._detail.show_placeholder()

        if not steps:
            is_tmpl = proto.get("id", "").startswith("tmpl_")
            if is_tmpl:
                self._empty_lbl.setText(
                    "Viewing template workflow.\n"
                    "Use Template to create an editable protocol."
                )
            else:
                self._empty_lbl.setText("This protocol has no steps yet.")
            self._view.hide()
            self._empty_lbl.show()
            return

        # Build nodes
        node_x = float(SCENE_X)
        for i, step in enumerate(steps):
            node_y = float(i * (NODE_H + VGAP))
            node   = _StepNode(step, i)
            node.setPos(node_x, node_y)
            node.node_clicked.connect(self._on_node_clicked)
            self._scene.addItem(node)
            self._nodes.append(node)

            # Arrow to next node
            if i < len(steps) - 1:
                arrow = _ArrowItem(
                    x_center = node_x + NODE_W / 2,
                    y_start  = node_y + NODE_H,
                    y_end    = node_y + NODE_H + VGAP,
                )
                self._scene.addItem(arrow)

        self._view.show()
        self._empty_lbl.hide()
        # Fit view after a brief moment (let scene settle)
        from PySide6.QtCore import QTimer
        QTimer.singleShot(50, self._view.fit_view)
        self._update_zoom_label()

    def _on_node_clicked(self, idx: int) -> None:
        steps = self._current_proto.get("steps", []) if self._current_proto else []
        if not (0 <= idx < len(steps)):
            return

        # Update selection visuals
        for i, node in enumerate(self._nodes):
            node.set_selected(i == idx)

        self._selected_idx = idx
        self._detail.show_step(steps[idx], idx, len(steps))
        self._update_zoom_label()

    # ── Toolbar handlers ──────────────────────────────────────────────────────

    def _on_fit(self) -> None:
        self._view.fit_view()
        self._update_zoom_label()

    def _on_center(self) -> None:
        self._view.center_view()

    def _on_zoom_in(self) -> None:
        self._view.zoom_in()
        self._update_zoom_label()

    def _on_zoom_out(self) -> None:
        self._view.zoom_out()
        self._update_zoom_label()

    def _on_reset_zoom(self) -> None:
        self._view.reset_zoom()
        self._update_zoom_label()

    def _update_zoom_label(self) -> None:
        self._zoom_lbl.setText(f"{self._view.zoom_level_pct()}%")

    # ── List event handlers ───────────────────────────────────────────────────

    def _on_list_selection(self, current: QListWidgetItem | None, _prev) -> None:
        if current is None:
            return
        proto = current.data(Qt.ItemDataRole.UserRole)
        if proto and proto.get("id") != (
            self._current_proto.get("id", "") if self._current_proto else ""
        ):
            self._open_protocol(proto)

    def _on_search(self, text: str) -> None:
        self._search_str = text
        self._rebuild_list()

    # ── on_show ───────────────────────────────────────────────────────────────

    def on_show(self) -> None:
        wanted_id = getattr(self.app.state, "selected_protocol_id", "")
        self._load_protocols()

        if wanted_id:
            self.app.state.selected_protocol_id = ""
            for p in self._protocols:
                if p.get("id") == wanted_id:
                    # Highlight in list
                    for i in range(self._proto_list.count()):
                        it = self._proto_list.item(i)
                        pd = it.data(Qt.ItemDataRole.UserRole) if it else None
                        if pd and pd.get("id") == wanted_id:
                            self._proto_list.setCurrentItem(it)
                            break
                    self._open_protocol(p)
                    break
        elif self._current_proto:
            # Re-render in case protocol was edited
            for p in self._protocols:
                if p.get("id") == self._current_proto.get("id"):
                    self._open_protocol(p)
                    break
