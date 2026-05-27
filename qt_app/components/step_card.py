"""
StepCard — the per-step widget in Run Mode.

Design principles
-----------------
- Created ONCE when a protocol is selected (render_step_cards_once).
- State changes call apply_state(state) which only toggles visibility and
  updates labels — no widget is destroyed or recreated.
- Timer ticks call update_timer(remaining) which updates ONE QLabel only.
- All user actions emit signals; RunModePage wires them to the session.

Signals emitted (all carry step_idx: int)
------------------------------------------
action_start(int)
action_pause(int)
action_resume(int)
action_complete(int)
action_undo_complete(int)
action_skip(int)
action_undo_skip(int)
action_reset(int)
action_adjust(int, float)   # (step_idx, delta_secs)
notes_changed(int, str)     # debounced by RunModePage
"""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QPlainTextEdit,
    QPushButton, QSizePolicy, QVBoxLayout, QWidget,
)

from qt_app.theme import Colors, Fonts, Radii
from qt_app.services.run_service import (
    StepRunState, format_timer,
    is_countdown_step, step_has_timer, COUNTDOWN_TYPES,
)

# ── Step type accent colors ────────────────────────────────────────────────────
_ACCENTS: dict[str, str] = {
    "preparation":       "#60a5fa",
    "reagent_addition":  "#2dd4bf",
    "mixing":            "#c084fc",
    "incubation":        "#fb923c",
    "waiting":           "#94a3b8",
    "centrifuge":        "#818cf8",
    "wash":              "#22d3ee",
    "transfer":          "#a5b4fc",
    "pipetting":         "#38bdf8",
    "resuspension":      "#4ade80",
    "staining":          "#f472b6",
    "blocking":          "#fb7185",
    "electrophoresis":   "#d8b4fe",
    "gel_running":       "#c4b5fd",
    "membrane_transfer": "#93c5fd",
    "imaging":           "#6ee7b7",
    "measurement":       "#fdba74",
    "lysis":             "#fca5a5",
    "heating":           "#fb923c",
    "cooling":           "#7dd3fc",
    "storage":           "#94a3b8",
    "harvest":           "#86efac",
    "sample_collection": "#fcd34d",
    "note":              "#64748b",
    "checklist_block":   "#4ade80",
    "decision":          "#fcd34d",
    "break":             "#f9a8d4",
    "task":              "#67e8f9",
    "other":             "#94a3b8",
}

_BG: dict[str, str] = {
    "preparation":       "#1e3a5f",
    "reagent_addition":  "#042f2e",
    "mixing":            "#2e1065",
    "incubation":        "#431407",
    "waiting":           "#1e293b",
    "centrifuge":        "#1e1b4b",
    "wash":              "#164e63",
    "transfer":          "#1e1b4b",
    "pipetting":         "#0c4a6e",
    "resuspension":      "#052e16",
    "staining":          "#500724",
    "blocking":          "#4c0519",
    "electrophoresis":   "#3b0764",
    "gel_running":       "#2e1065",
    "membrane_transfer": "#1e3a5f",
    "imaging":           "#064e3b",
    "measurement":       "#422006",
    "lysis":             "#450a0a",
    "heating":           "#431407",
    "cooling":           "#0c4a6e",
    "storage":           "#1e293b",
    "harvest":           "#1a2e05",
    "sample_collection": "#451a03",
    "note":              "#1e293b",
    "checklist_block":   "#052e16",
    "decision":          "#451a03",
    "break":             "#500724",
    "task":              "#042f2e",
    "other":             "#1e293b",
}


def _accent(stype: str) -> str:
    return _ACCENTS.get(stype, "#94a3b8")


def _bg(stype: str) -> str:
    return _BG.get(stype, "#1e293b")


# ── Button factory helpers ─────────────────────────────────────────────────────

def _btn(text: str, color: str = Colors.ACCENT, hover: str | None = None,
         min_w: int = 80, h: int = 32) -> QPushButton:
    if hover is None:
        hover = color
    b = QPushButton(text)
    b.setMinimumHeight(h)
    b.setMinimumWidth(min_w)
    b.setCursor(Qt.CursorShape.PointingHandCursor)
    b.setStyleSheet(
        f"QPushButton {{ background: {color}; color: white; border: none;"
        f"  border-radius: {Radii.SM}px; font-size: {Fonts.SIZE_SM}px; font-weight: 600; }}"
        f"QPushButton:hover {{ background: {hover}; }}"
        f"QPushButton:disabled {{ background: {Colors.BORDER}; color: {Colors.TEXT_MUTED}; }}"
    )
    return b


def _ghost_btn(text: str, fg: str = Colors.TEXT_SECOND, h: int = 32,
               min_w: int = 60) -> QPushButton:
    b = QPushButton(text)
    b.setMinimumHeight(h)
    b.setMinimumWidth(min_w)
    b.setCursor(Qt.CursorShape.PointingHandCursor)
    b.setStyleSheet(
        f"QPushButton {{ background: transparent; color: {fg}; border: 1px solid {Colors.BORDER};"
        f"  border-radius: {Radii.SM}px; font-size: {Fonts.SIZE_SM}px; }}"
        f"QPushButton:hover {{ background: {Colors.BG_CARD_HOV}; color: {Colors.TEXT_PRIMARY}; }}"
    )
    return b


# ── StepCard ──────────────────────────────────────────────────────────────────

class StepCard(QFrame):
    """One step card — created once, updated in-place."""

    # Signals
    action_start      = Signal(int)
    action_pause      = Signal(int)
    action_resume     = Signal(int)
    action_complete   = Signal(int)
    action_undo_complete = Signal(int)
    action_skip       = Signal(int)
    action_undo_skip  = Signal(int)
    action_reset      = Signal(int)
    action_adjust     = Signal(int, float)
    notes_changed     = Signal(int, str)

    def __init__(self, idx: int, step: dict, state: StepRunState,
                 parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._idx   = idx
        self._step  = step
        self._state = state
        self._stype = step.get("type", "other")
        self._has_timer = step_has_timer(step)
        self._is_countdown = is_countdown_step(step)

        accent = _accent(self._stype)
        bg     = _bg(self._stype)
        self.setStyleSheet(
            f"QFrame {{"
            f"  background: {bg};"
            f"  border-radius: {Radii.LG}px;"
            f"  border: 1px solid {accent}40;"
            f"}}"
        )
        self._accent = accent
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._build()
        self.apply_state(state)

    # ── Build (once) ──────────────────────────────────────────────────────────

    def _build(self) -> None:
        step  = self._step
        idx   = self._idx
        accent = self._accent
        root  = QVBoxLayout(self)
        root.setContentsMargins(16, 12, 16, 12)
        root.setSpacing(6)

        # ── Row 1: index, title, type badge, status indicator ─────────────────
        row1 = QHBoxLayout()
        row1.setSpacing(8)

        idx_lbl = QLabel(f"{idx + 1:02d}")
        idx_lbl.setStyleSheet(
            f"color: {accent}; font-size: {Fonts.SIZE_XS}px; font-weight: 700;"
            f"background: {accent}25; border-radius: 5px; padding: 2px 6px;"
        )
        row1.addWidget(idx_lbl)

        title_lbl = QLabel(step.get("title", "Untitled"))
        title_lbl.setStyleSheet(
            f"color: {Colors.TEXT_PRIMARY}; font-size: {Fonts.SIZE_MD}px; font-weight: 600;"
        )
        title_lbl.setWordWrap(False)
        row1.addWidget(title_lbl, stretch=1)

        stype_lbl = QLabel(self._stype.replace("_", " ").title())
        stype_lbl.setStyleSheet(
            f"color: {accent}; background: {accent}20;"
            f"border-radius: 5px; padding: 2px 7px;"
            f"font-size: {Fonts.SIZE_XS}px; font-weight: 600;"
        )
        row1.addWidget(stype_lbl)

        # Status badge (updated by apply_state)
        self._status_badge = QLabel("●  idle")
        self._status_badge.setStyleSheet(
            f"color: {Colors.TEXT_MUTED}; font-size: {Fonts.SIZE_XS}px;"
        )
        row1.addWidget(self._status_badge)

        root.addLayout(row1)

        # ── Timer row ─────────────────────────────────────────────────────────
        if self._has_timer:
            timer_row = QHBoxLayout()
            timer_row.setSpacing(12)

            self._timer_lbl = QLabel("00:00")
            self._timer_lbl.setStyleSheet(
                f"color: {Colors.TEXT_PRIMARY}; font-size: {Fonts.SIZE_2XL}px;"
                f"font-weight: 700; font-family: monospace;"
            )
            timer_row.addWidget(self._timer_lbl)

            # Planned duration label
            ho  = float(step.get("handsOnMinutes",  0))
            wt  = float(step.get("waitMinutes",     0))
            buf = float(step.get("bufferMinutes",   0))
            parts = []
            if ho  > 0: parts.append(f"⏱ {ho:.0f}m hands-on")
            if wt  > 0: parts.append(f"⏳ {wt:.0f}m wait")
            if buf > 0: parts.append(f"+ {buf:.0f}m buffer")
            if parts:
                plan_lbl = QLabel("  ·  ".join(parts))
                plan_lbl.setStyleSheet(
                    f"color: {Colors.TEXT_MUTED}; font-size: {Fonts.SIZE_XS}px;"
                )
                timer_row.addWidget(plan_lbl)
            timer_row.addStretch()

            # Adjust buttons
            adj_row = QHBoxLayout()
            adj_row.setSpacing(4)
            for delta_m, label in [(-5, "-5m"), (-1, "-1m"), (+1, "+1m"), (+5, "+5m")]:
                b = _ghost_btn(label, min_w=44)
                b.clicked.connect(
                    lambda checked=False, d=delta_m: self.action_adjust.emit(self._idx, d * 60.0)
                )
                adj_row.addWidget(b)
            timer_row.addLayout(adj_row)

            root.addLayout(timer_row)
        else:
            self._timer_lbl = None
            # Show duration estimate for non-timed steps
            ho = float(step.get("handsOnMinutes", 0))
            if ho > 0:
                est_lbl = QLabel(f"⏱  Hands-on estimate: {ho:.0f} min")
                est_lbl.setStyleSheet(
                    f"color: {Colors.TEXT_MUTED}; font-size: {Fonts.SIZE_SM}px;"
                )
                root.addWidget(est_lbl)

        # ── Description / reagents preview ────────────────────────────────────
        desc = step.get("description", "").strip()
        if desc:
            d_lbl = QLabel(desc[:140] + ("…" if len(desc) > 140 else ""))
            d_lbl.setStyleSheet(
                f"color: {Colors.TEXT_MUTED}; font-size: {Fonts.SIZE_SM}px;"
            )
            d_lbl.setWordWrap(True)
            root.addWidget(d_lbl)

        reagents = step.get("reagents", [])
        if reagents:
            r_names = [r.get("name", "") for r in reagents[:3] if r.get("name")]
            if r_names:
                suffix = f" +{len(reagents)-3}" if len(reagents) > 3 else ""
                r_lbl = QLabel("🧪 " + ", ".join(r_names) + suffix)
                r_lbl.setStyleSheet(
                    f"color: {Colors.TEXT_SECOND}; font-size: {Fonts.SIZE_XS}px;"
                )
                root.addWidget(r_lbl)

        # ── Notes textbox ─────────────────────────────────────────────────────
        self._notes = QPlainTextEdit()
        self._notes.setPlaceholderText("Notes…")
        self._notes.setFixedHeight(56)
        self._notes.setStyleSheet(
            f"QPlainTextEdit {{"
            f"  background: rgba(0,0,0,0.2);"
            f"  color: {Colors.TEXT_PRIMARY};"
            f"  border: 1px solid {Colors.BORDER};"
            f"  border-radius: {Radii.SM}px;"
            f"  padding: 4px 8px;"
            f"  font-size: {Fonts.SIZE_SM}px;"
            f"}}"
            f"QPlainTextEdit:focus {{ border-color: {self._accent}; }}"
        )
        self._notes.textChanged.connect(
            lambda: self.notes_changed.emit(self._idx, self._notes.toPlainText())
        )
        root.addWidget(self._notes)

        # ── Action buttons row ────────────────────────────────────────────────
        btn_row = QHBoxLayout()
        btn_row.setSpacing(6)

        self._btn_start   = _btn("▶  Start",   Colors.ACCENT, Colors.ACCENT_HOVER)
        self._btn_pause   = _btn("⏸  Pause",   "#64748b",     "#475569")
        self._btn_resume  = _btn("▶  Resume",  Colors.ACCENT, Colors.ACCENT_HOVER)
        self._btn_complete = _btn("✓  Complete", Colors.SUCCESS, "#16a34a", min_w=100)
        self._btn_undo_complete = _btn("↩  Undo", "#64748b", "#475569")
        self._btn_skip    = _ghost_btn("Skip →", Colors.WARNING)
        self._btn_undo_skip = _btn("↩  Undo Skip", "#64748b", "#475569")
        self._btn_reset   = _ghost_btn("⟳ Reset", Colors.TEXT_MUTED, min_w=64)

        self._btn_start.clicked.connect(lambda: self.action_start.emit(self._idx))
        self._btn_pause.clicked.connect(lambda: self.action_pause.emit(self._idx))
        self._btn_resume.clicked.connect(lambda: self.action_resume.emit(self._idx))
        self._btn_complete.clicked.connect(lambda: self.action_complete.emit(self._idx))
        self._btn_undo_complete.clicked.connect(lambda: self.action_undo_complete.emit(self._idx))
        self._btn_skip.clicked.connect(lambda: self.action_skip.emit(self._idx))
        self._btn_undo_skip.clicked.connect(lambda: self.action_undo_skip.emit(self._idx))
        self._btn_reset.clicked.connect(lambda: self.action_reset.emit(self._idx))

        for b in (self._btn_start, self._btn_pause, self._btn_resume,
                  self._btn_complete, self._btn_undo_complete,
                  self._btn_skip, self._btn_undo_skip, self._btn_reset):
            btn_row.addWidget(b)
        btn_row.addStretch()

        root.addLayout(btn_row)

    # ── apply_state — updates all visual elements in-place ────────────────────

    def apply_state(self, state: StepRunState) -> None:
        """Update all visual elements based on current state (no widget rebuild)."""
        self._state = state
        status = state.status

        # Status badge
        badge_map = {
            "idle":      (f"color: {Colors.TEXT_MUTED};",    "●  idle"),
            "running":   (f"color: {Colors.SUCCESS};",       "▶  running"),
            "paused":    (f"color: {Colors.WARNING};",       "⏸  paused"),
            "completed": (f"color: {Colors.ACCENT_LIGHT};",  "✓  done"),
            "skipped":   (f"color: {Colors.TEXT_MUTED};",    "⟩  skipped"),
        }
        style, text = badge_map.get(status, ("", ""))
        self._status_badge.setStyleSheet(style + f" font-size: {Fonts.SIZE_XS}px;")
        self._status_badge.setText(text)

        # Button visibility
        self._btn_start.setVisible(status == "idle")
        self._btn_pause.setVisible(status == "running")
        self._btn_resume.setVisible(status == "paused")
        self._btn_complete.setVisible(status in ("running", "paused"))
        self._btn_undo_complete.setVisible(status == "completed")
        self._btn_skip.setVisible(status in ("idle", "running", "paused"))
        self._btn_undo_skip.setVisible(status == "skipped")
        self._btn_reset.setVisible(status in ("idle", "paused", "completed", "skipped"))

        # Notes
        if self._notes.toPlainText() != state.notes:
            # Block signals to avoid re-triggering notes_changed
            self._notes.blockSignals(True)
            self._notes.setPlainText(state.notes)
            self._notes.blockSignals(False)

        # Card border highlight for running state
        accent = self._accent
        if status == "running":
            self.setStyleSheet(
                f"QFrame {{ background: {_bg(self._stype)};"
                f"  border-radius: {Radii.LG}px;"
                f"  border: 2px solid {accent}; }}"
            )
        elif status == "completed":
            self.setStyleSheet(
                f"QFrame {{ background: rgba(34,197,94,0.08);"
                f"  border-radius: {Radii.LG}px;"
                f"  border: 1px solid {Colors.SUCCESS}80; }}"
            )
        elif status == "skipped":
            self.setStyleSheet(
                f"QFrame {{ background: rgba(100,116,139,0.10);"
                f"  border-radius: {Radii.LG}px;"
                f"  border: 1px solid {Colors.BORDER}; }}"
            )
        else:
            self.setStyleSheet(
                f"QFrame {{ background: {_bg(self._stype)};"
                f"  border-radius: {Radii.LG}px;"
                f"  border: 1px solid {accent}40; }}"
            )

        # Update timer label with current remaining
        if self._timer_lbl is not None:
            self.update_timer(state)

    def update_timer(self, state: StepRunState, now: float | None = None) -> None:
        """Fast path: only update the timer label. Called every 500 ms."""
        if self._timer_lbl is None:
            return

        remaining = state.remaining_secs(now)
        is_cd = self._is_countdown

        if state.status == "idle":
            # Show planned duration
            self._timer_lbl.setText(format_timer(state.planned_secs, countdown=is_cd))
            self._timer_lbl.setStyleSheet(
                f"color: {Colors.TEXT_MUTED}; font-size: {Fonts.SIZE_2XL}px;"
                f"font-weight: 700; font-family: monospace;"
            )
        elif state.status in ("running", "paused"):
            if is_cd:
                # Countdown
                color = Colors.DANGER if remaining <= 0 else (
                    Colors.WARNING if remaining < 60 else Colors.TEXT_PRIMARY
                )
                self._timer_lbl.setText(format_timer(remaining, countdown=True))
            else:
                # Elapsed stopwatch (counts up)
                elapsed = state.elapsed_secs(now)
                color = Colors.TEXT_PRIMARY
                self._timer_lbl.setText(format_timer(elapsed, countdown=False))
            self._timer_lbl.setStyleSheet(
                f"color: {color}; font-size: {Fonts.SIZE_2XL}px;"
                f"font-weight: 700; font-family: monospace;"
            )
        elif state.status == "completed":
            if is_cd:
                self._timer_lbl.setText("✓ 00:00")
            else:
                self._timer_lbl.setText(f"✓ {format_timer(state.elapsed_secs(now))}")
            self._timer_lbl.setStyleSheet(
                f"color: {Colors.SUCCESS}; font-size: {Fonts.SIZE_2XL}px;"
                f"font-weight: 700; font-family: monospace;"
            )
        elif state.status == "skipped":
            self._timer_lbl.setText("— skipped")
            self._timer_lbl.setStyleSheet(
                f"color: {Colors.TEXT_MUTED}; font-size: {Fonts.SIZE_2XL}px;"
                f"font-weight: 700;"
            )

    def set_notes_text(self, text: str) -> None:
        """Set notes without triggering notes_changed signal."""
        self._notes.blockSignals(True)
        self._notes.setPlainText(text)
        self._notes.blockSignals(False)
