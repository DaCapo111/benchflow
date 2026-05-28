"""
Run Mode page — Phase 3.5: full timer + sequential mode + progress bars.

Architecture
------------
- Single QTimer (500 ms) drives all step timer updates.
- StepCard widgets are created ONCE per protocol load; state changes
  call card.apply_state() or card.update_timer() — no rebuild.
- Session persisted to runtime_session.json on every state change
  via a debounced QTimer (100 ms) for immediate writes, 1000 ms for notes.
- Wall-clock timer math: remaining = planned - (now - started_at - paused_time).
  Accurate across sleep, window switches, and app restart.

Phase 3.5 additions
-------------------
- Sequential mode: auto-start next idle step after each complete
- QProgressBar per step card, updated only for running steps on tick
- Remove temp block button with confirmation dialog
- Notes: apply_state() no longer overwrites notes while user is typing
- Left panel step list is clickable → focus_step() scrolls to card
- "💾 Save Session" button: save to notebook + ask to clear/keep
- Info bar shows N steps / X done / Y skipped live counts
- Logging: start_sequential, auto_start_next, remove_temp_block,
  save_to_notebook, notes_autosave, focus_step
"""
from __future__ import annotations

import logging
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QListWidget, QListWidgetItem,
    QMessageBox, QPushButton, QScrollArea, QSizePolicy,
    QSplitter, QVBoxLayout, QWidget,
)

from qt_app.theme import Colors, Fonts, Radii
from qt_app.components.widgets import HSeparator, PageTitle, PrimaryButton, SubLabel
from qt_app.components.step_card import StepCard
from qt_app.components.toast import ToastManager
from qt_app.services.event_bus import bus
from qt_app.services.perf import perf
from qt_app.services.run_service import (
    RunModeSession, StepRunState,
    step_planned_secs, is_countdown_step, format_timer,
)
from qt_app.services.data import DataService
from qt_app.dialogs.add_block import AddBlockDialog
from qt_app.dialogs.restore_session import RestoreSessionDialog
from qt_app.views.base_page import BasePage, _clear_layout

# ── Logging ───────────────────────────────────────────────────────────────────
_logs_dir = Path(__file__).parent.parent.parent / "logs"
_logs_dir.mkdir(exist_ok=True)
_handler = logging.FileHandler(_logs_dir / "qt_run_mode.log", encoding="utf-8")
_handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
logger = logging.getLogger("benchflow.run_mode")
if not logger.handlers:
    logger.addHandler(_handler)
    logger.setLevel(logging.INFO)


# ── Left-panel protocol item ──────────────────────────────────────────────────

class _ProtoItem(QListWidgetItem):
    def __init__(self, protocol: dict) -> None:
        name = protocol.get("name", "Untitled")
        n = len(protocol.get("steps", []))
        super().__init__(f"  {name}  ({n})")
        self.setData(Qt.ItemDataRole.UserRole, protocol)


# ── Undo snackbar ─────────────────────────────────────────────────────────────

class _UndoSnackbar(QFrame):
    """9-second floating undo toast shown after Complete."""

    def __init__(self, step_title: str, on_undo, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._on_undo = on_undo
        self._remaining = 9
        self.setStyleSheet(
            f"QFrame {{ background: {Colors.BG_CARD};"
            f"  border-radius: {Radii.MD}px;"
            f"  border: 1px solid {Colors.BORDER_LIGHT}; }}"
        )
        lay = QHBoxLayout(self)
        lay.setContentsMargins(14, 10, 14, 10)
        lay.setSpacing(12)

        self._msg_lbl = QLabel(f"✓  '{step_title[:30]}' completed")
        self._msg_lbl.setStyleSheet(
            f"color: {Colors.TEXT_PRIMARY}; font-size: {Fonts.SIZE_SM}px;"
        )
        lay.addWidget(self._msg_lbl, stretch=1)

        self._countdown_lbl = QLabel("9s")
        self._countdown_lbl.setStyleSheet(
            f"color: {Colors.TEXT_MUTED}; font-size: {Fonts.SIZE_SM}px;"
        )
        lay.addWidget(self._countdown_lbl)

        undo_btn = QPushButton("Undo")
        undo_btn.setStyleSheet(
            f"QPushButton {{ background: {Colors.WARNING}; color: white; border: none;"
            f"  border-radius: {Radii.SM}px; padding: 4px 12px;"
            f"  font-size: {Fonts.SIZE_SM}px; font-weight: 600; }}"
            f"QPushButton:hover {{ background: #ea580c; }}"
        )
        undo_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        undo_btn.clicked.connect(self._do_undo)
        lay.addWidget(undo_btn)

        self._tick_timer = QTimer(self)
        self._tick_timer.setInterval(1000)
        self._tick_timer.timeout.connect(self._tick)
        self._tick_timer.start()

    def _tick(self) -> None:
        self._remaining -= 1
        self._countdown_lbl.setText(f"{self._remaining}s")
        if self._remaining <= 0:
            self._tick_timer.stop()
            self.hide()

    def _do_undo(self) -> None:
        self._tick_timer.stop()
        self.hide()
        self._on_undo()


# ── RunModePage ───────────────────────────────────────────────────────────────

class RunModePage(BasePage):
    """Full Run Mode — wall-clock timers, autosave, session restore, sequential mode."""

    def __init__(self, app: "BenchFlowApp", parent: QWidget | None = None) -> None:  # type: ignore[name-defined]
        super().__init__(app, parent)
        self._session: RunModeSession | None = None
        self._cards: list[StepCard] = []
        self._snackbar: _UndoSnackbar | None = None

        # Sequential mode state
        self._sequential: bool = False

        # Single global tick timer
        self._tick_timer = QTimer(self)
        self._tick_timer.setInterval(500)
        self._tick_timer.timeout.connect(self._on_tick)

        # Debounced save timers
        self._save_timer = QTimer(self)
        self._save_timer.setSingleShot(True)
        self._save_timer.setInterval(100)
        self._save_timer.timeout.connect(self._do_save)

        self._notes_save_timer = QTimer(self)
        self._notes_save_timer.setSingleShot(True)
        self._notes_save_timer.setInterval(1000)
        self._notes_save_timer.timeout.connect(self._do_save)

        self._build()

    # ── Theme override ────────────────────────────────────────────────────────

    def _on_theme_changed(self, theme: str = "dark", **_kw) -> None:
        """Refresh Run Mode without discarding an active timer session."""
        if self._session is None:
            self._rebuild_theme()
            return
        self._rebuild_active_theme()

    def _ensure_fresh_theme(self) -> None:
        """Rebuild stale theme state while preserving active sessions."""
        from qt_app.theme import current_theme as _ct
        t = _ct()
        if self._last_theme == t:
            return
        if self._session is not None:
            self._rebuild_active_theme()
            return
        self._rebuild_theme()

    def _rebuild_active_theme(self) -> None:
        """Rebuild theme-dependent widgets while keeping the run session object."""
        from qt_app.theme import current_theme as _ct

        selected_step = self._step_status_list.currentRow() if hasattr(self, "_step_status_list") else -1
        scroll_value = (
            self._step_scroll.verticalScrollBar().value()
            if hasattr(self, "_step_scroll") else 0
        )
        sequential = self._sequential

        if self._snackbar is not None:
            self._snackbar.hide()
            self._snackbar = None

        self._last_theme = _ct()
        self.setStyleSheet(f"background: {Colors.BG_PAGE};")
        _clear_layout(self._root_layout)
        self._cards.clear()

        self._build()
        self._load_protocol_list()

        if self._session is not None:
            self._select_protocol_in_list(self._session.protocol_id)
            self._sequential = sequential
            self._seq_btn.blockSignals(True)
            self._seq_btn.setChecked(sequential)
            self._seq_btn.blockSignals(False)
            self._add_block_btn.setVisible(True)
            self._save_btn.setVisible(True)
            self._end_run_btn.setVisible(True)
            self._seq_btn.setVisible(True)
            self._session_badge.setText("● Active session")
            self._session_badge.setVisible(True)
            self._render_step_cards_once()
            if selected_step >= 0:
                self._step_status_list.setCurrentRow(selected_step)
                if selected_step < len(self._cards):
                    self._focus_step(selected_step)
            QTimer.singleShot(
                0,
                lambda value=scroll_value: self._step_scroll.verticalScrollBar().setValue(value),
            )
            if not self._tick_timer.isActive():
                self._tick_timer.start()

    # ── UI construction ───────────────────────────────────────────────────────

    def _build(self) -> None:
        root = QVBoxLayout()
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Header bar
        hdr_w = QWidget()
        hdr_w.setStyleSheet(f"background: {Colors.BG_PAGE};")
        hdr_lay = QHBoxLayout(hdr_w)
        hdr_lay.setContentsMargins(28, 22, 28, 14)
        hdr_lay.setSpacing(8)

        col = QVBoxLayout()
        col.setSpacing(2)
        col.addWidget(PageTitle("Run Mode"))
        col.addWidget(SubLabel("Real-time protocol execution with wall-clock accurate timers."))
        hdr_lay.addLayout(col)
        hdr_lay.addStretch()

        # Sequential mode toggle
        self._seq_btn = QPushButton("▶ Sequential")
        self._seq_btn.setMinimumWidth(120)
        self._seq_btn.setMinimumHeight(36)
        self._seq_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._seq_btn.setCheckable(True)
        self._seq_btn.setVisible(False)
        self._seq_btn.setStyleSheet(
            f"QPushButton {{ background: {Colors.BG_CARD}; color: {Colors.TEXT_PRIMARY};"
            f"  border: 1px solid {Colors.BORDER_LIGHT}; border-radius: {Radii.LG}px;"
            f"  padding: 6px 16px; font-size: {Fonts.SIZE_SM}px; font-weight: 600; }}"
            f"QPushButton:hover {{ background: {Colors.BG_CARD_HOV}; }}"
            f"QPushButton:checked {{ background: {Colors.SELECTED_BG}; color: {Colors.TEXT_PRIMARY};"
            f"  border-color: {Colors.BORDER_LIGHT}; }}"
            f"QPushButton:checked:hover {{ background: {Colors.SELECTED_BG}; }}"
        )
        self._seq_btn.toggled.connect(self._on_sequential_toggled)
        hdr_lay.addWidget(self._seq_btn)

        # Add Block button
        self._add_block_btn = PrimaryButton("＋ Block")
        self._add_block_btn.setMinimumWidth(100)
        self._add_block_btn.setVisible(False)
        self._add_block_btn.clicked.connect(self._on_add_block)
        hdr_lay.addWidget(self._add_block_btn)

        # Save Session button
        self._save_btn = QPushButton("💾 Save")
        self._save_btn.setMinimumWidth(90)
        self._save_btn.setMinimumHeight(36)
        self._save_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._save_btn.setVisible(False)
        self._save_btn.setStyleSheet(
            f"QPushButton {{ background: {Colors.BG_CARD}; color: {Colors.TEXT_PRIMARY};"
            f"  border: 1px solid {Colors.BORDER_LIGHT}; border-radius: {Radii.LG}px;"
            f"  padding: 6px 16px; font-size: {Fonts.SIZE_SM}px; font-weight: 600; }}"
            f"QPushButton:hover {{ background: {Colors.BG_CARD_HOV}; }}"
        )
        self._save_btn.clicked.connect(self._on_save_session)
        hdr_lay.addWidget(self._save_btn)

        # End Run button
        self._end_run_btn = PrimaryButton("■ End Run")
        self._end_run_btn.setMinimumWidth(110)
        self._end_run_btn.setVisible(False)
        self._end_run_btn.setStyleSheet(
            f"QPushButton {{ background: {Colors.DANGER}; color: white; border: none;"
            f"  border-radius: {Radii.LG}px; padding: 8px 20px;"
            f"  font-size: {Fonts.SIZE_MD}px; font-weight: 600; }}"
            f"QPushButton:hover {{ background: #dc2626; }}"
        )
        self._end_run_btn.clicked.connect(self._on_end_run)
        hdr_lay.addWidget(self._end_run_btn)

        root.addWidget(hdr_w)
        root.addWidget(HSeparator())

        # Main splitter
        self._splitter = QSplitter(Qt.Orientation.Horizontal)
        self._splitter.setStyleSheet(
            f"QSplitter::handle {{ background: {Colors.BORDER_LIGHT}; width: 1px; }}"
        )

        self._splitter.addWidget(self._build_left_panel())
        self._splitter.addWidget(self._build_right_panel())
        self._splitter.setSizes([210, 900])
        self._splitter.setChildrenCollapsible(False)
        root.addWidget(self._splitter, stretch=1)

        self._root_layout.addLayout(root)

    def _build_left_panel(self) -> QWidget:
        w = QWidget()
        w.setStyleSheet(
            f"background: {Colors.BG_CARD};"
            f"border-right: 1px solid {Colors.BORDER_LIGHT};"
        )
        w.setMinimumWidth(180)
        w.setMaximumWidth(280)
        lay = QVBoxLayout(w)
        lay.setContentsMargins(10, 14, 10, 14)
        lay.setSpacing(6)

        hdr = QLabel("Protocols")
        hdr.setStyleSheet(
            f"color: {Colors.TEXT_SECOND}; font-size: {Fonts.SIZE_SM}px;"
            f"font-weight: 600; padding-left: 4px;"
        )
        lay.addWidget(hdr)

        self._proto_list = QListWidget()
        self._proto_list.setStyleSheet(
            f"QListWidget {{ background: transparent; border: none; outline: none;"
            f"  font-size: {Fonts.SIZE_MD}px; color: {Colors.TEXT_PRIMARY}; }}"
            f"QListWidget::item {{ padding: 9px 8px; border-radius: 10px; margin: 1px 0; }}"
            f"QListWidget::item:hover {{ background: {Colors.HOVER_BG}; }}"
            f"QListWidget::item:selected {{ background: {Colors.SELECTED_BG}; color: {Colors.TEXT_PRIMARY};"
            f"  border-radius: 10px; }}"
        )
        self._proto_list.currentItemChanged.connect(self._on_proto_selected)
        lay.addWidget(self._proto_list, stretch=1)

        # Step status clickable list (visible during active session)
        lay.addWidget(HSeparator())

        self._steps_hdr = QLabel("Steps")
        self._steps_hdr.setStyleSheet(
            f"color: {Colors.TEXT_SECOND}; font-size: {Fonts.SIZE_XS}px;"
            f"font-weight: 600; padding-left: 4px;"
        )
        self._steps_hdr.setVisible(False)
        lay.addWidget(self._steps_hdr)

        self._step_status_list = QListWidget()
        self._step_status_list.setStyleSheet(
            f"QListWidget {{ background: transparent; border: none; outline: none;"
            f"  font-size: {Fonts.SIZE_XS}px; }}"
            f"QListWidget::item {{ padding: 3px 4px; border-radius: 6px; margin: 1px 0; }}"
            f"QListWidget::item:hover {{ background: {Colors.HOVER_BG}; }}"
            f"QListWidget::item:selected {{ background: {Colors.SELECTED_BG}; }}"
        )
        self._step_status_list.setVisible(False)
        self._step_status_list.setMaximumHeight(220)
        self._step_status_list.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self._step_status_list.itemClicked.connect(self._on_step_list_clicked)
        lay.addWidget(self._step_status_list)

        return w

    def _build_right_panel(self) -> QWidget:
        w = QWidget()
        w.setStyleSheet(f"background: {Colors.BG_PAGE};")
        lay = QVBoxLayout(w)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        # Info bar (protocol name, step counts)
        self._info_bar = QWidget()
        self._info_bar.setStyleSheet(
            f"background: {Colors.BG_CARD}; border-bottom: 1px solid {Colors.BORDER_LIGHT};"
        )
        info_lay = QHBoxLayout(self._info_bar)
        info_lay.setContentsMargins(20, 10, 20, 10)
        info_lay.setSpacing(14)

        self._info_name = QLabel("—")
        self._info_name.setStyleSheet(
            f"color: {Colors.TEXT_PRIMARY}; font-size: {Fonts.SIZE_LG}px; font-weight: 700;"
        )
        info_lay.addWidget(self._info_name)

        self._info_meta = QLabel("")
        self._info_meta.setStyleSheet(
            f"color: {Colors.TEXT_SECOND}; font-size: {Fonts.SIZE_SM}px;"
        )
        info_lay.addWidget(self._info_meta)
        info_lay.addStretch()

        self._session_badge = QLabel("")
        self._session_badge.setStyleSheet(
            f"color: {Colors.SUCCESS}; background: {Colors.SUCCESS_BG};"
            f"border-radius: 8px; padding: 3px 10px;"
            f"font-size: {Fonts.SIZE_XS}px; font-weight: 600;"
        )
        self._session_badge.setVisible(False)
        info_lay.addWidget(self._session_badge)

        lay.addWidget(self._info_bar)

        # Scroll area for step cards
        self._step_scroll = QScrollArea()
        self._step_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._step_scroll.setWidgetResizable(True)
        self._step_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._step_scroll.setStyleSheet(f"background: {Colors.BG_PAGE};")

        self._step_content = QWidget()
        self._step_content.setStyleSheet(f"background: {Colors.BG_PAGE};")
        self._step_layout = QVBoxLayout(self._step_content)
        self._step_layout.setContentsMargins(20, 16, 20, 20)
        self._step_layout.setSpacing(10)
        self._step_scroll.setWidget(self._step_content)
        lay.addWidget(self._step_scroll, stretch=1)

        self._show_idle_state()
        return w

    # ── on_show ───────────────────────────────────────────────────────────────

    def on_show(self) -> None:
        logger.info("enter_run_mode")
        self._load_protocol_list()

        # Auto-select protocol if one was requested (e.g. from Library "Open in Run Mode")
        wanted_id = getattr(self.app.state, "selected_protocol_id", "")
        if wanted_id:
            for i in range(self._proto_list.count()):
                item = self._proto_list.item(i)
                proto = item.data(Qt.ItemDataRole.UserRole) if item else None
                if proto and proto.get("id") == wanted_id:
                    self._proto_list.setCurrentItem(item)
                    break
            # Clear so a subsequent on_show() doesn't re-select stale value
            self.app.state.selected_protocol_id = ""

        # Check for existing session
        existing = self.app.data.load_active_session()
        if existing and existing.get("version", 0) == 3:
            self._offer_restore(existing)

    # ── Protocol list ─────────────────────────────────────────────────────────

    def _load_protocol_list(self) -> None:
        self._proto_list.clear()
        for p in self.app.data.load_protocols():
            self._proto_list.addItem(_ProtoItem(p))

    def _select_protocol_in_list(self, protocol_id: str) -> None:
        """Select a protocol row without starting/replacing the active session."""
        self._proto_list.blockSignals(True)
        try:
            self._proto_list.clearSelection()
            for i in range(self._proto_list.count()):
                item = self._proto_list.item(i)
                proto = item.data(Qt.ItemDataRole.UserRole) if item else None
                if proto and proto.get("id", "") == protocol_id:
                    self._proto_list.setCurrentItem(item)
                    break
        finally:
            self._proto_list.blockSignals(False)

    def _on_proto_selected(self, current: QListWidgetItem | None, _prev) -> None:
        if current is None:
            return
        protocol = current.data(Qt.ItemDataRole.UserRole)
        if protocol is None:
            return

        # If we already have an active session for this protocol, keep it
        if (self._session is not None
                and self._session.protocol_id == protocol.get("id", "")):
            return

        logger.info(f"select_protocol: {protocol.get('name', '?')}")
        self._session = RunModeSession.new(protocol)
        self._sequential = False
        self._seq_btn.setChecked(False)
        self._render_step_cards_once()
        self._schedule_save()
        self._tick_timer.start()
        self._add_block_btn.setVisible(True)
        self._save_btn.setVisible(True)
        self._end_run_btn.setVisible(True)
        self._seq_btn.setVisible(True)
        self._session_badge.setText("● Active session")
        self._session_badge.setVisible(True)

    # ── Step card rendering (once per protocol) ───────────────────────────────

    def _render_step_cards_once(self) -> None:
        """Create all StepCard widgets. Called once per protocol selection."""
        if self._session is None:
            return

        with perf.measure("render_step_cards"):
            self._render_step_cards_impl()

    def _render_step_cards_impl(self) -> None:
        # Clear previous cards
        self._cards.clear()
        while self._step_layout.count():
            item = self._step_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        proto = self._session.protocol_snapshot
        name = proto.get("name", "Untitled")
        proto_steps = self._session.steps()

        self._info_name.setText(name)
        self._update_session_stats()

        # Build left-panel mini step status
        self._update_left_step_status()

        # Create cards
        for state in self._session.step_states:
            step_data = self._session.step_data(state)
            card = StepCard(state.step_idx, step_data, state, parent=self._step_content)
            self._wire_card(card)
            self._cards.append(card)
            self._step_layout.addWidget(card)

        self._step_layout.addStretch()

    def _wire_card(self, card: StepCard) -> None:
        card.action_start.connect(self._on_start)
        card.action_pause.connect(self._on_pause)
        card.action_resume.connect(self._on_resume)
        card.action_complete.connect(self._on_complete)
        card.action_undo_complete.connect(self._on_undo_complete)
        card.action_skip.connect(self._on_skip)
        card.action_undo_skip.connect(self._on_undo_skip)
        card.action_reset.connect(self._on_reset)
        card.action_remove.connect(self._on_remove_block)
        card.action_adjust.connect(self._on_adjust)
        card.notes_changed.connect(self._on_notes_changed)

    # ── Update individual card state (no rebuild) ─────────────────────────────

    def _update_card(self, idx: int) -> None:
        if self._session is None or idx >= len(self._cards):
            return
        state = self._session.step_states[idx]
        self._cards[idx].apply_state(state)
        self._update_left_step_status()
        self._update_session_stats()

    # ── Timer tick ────────────────────────────────────────────────────────────

    def _on_tick(self) -> None:
        if self._session is None:
            return
        now = time.time()
        for state in self._session.step_states:
            if state.status == "running" and state.step_idx < len(self._cards):
                card = self._cards[state.step_idx]
                card.update_timer(state, now)
                card.update_progress(state, now)

    # ── Step actions ──────────────────────────────────────────────────────────

    def _on_start(self, idx: int) -> None:
        if not self._validate(idx):
            return
        state = self._session.step_states[idx]
        state.start()
        logger.info(f"start_timer: step={idx} id={state.step_id}")
        self._update_card(idx)
        self._schedule_save()

    def _on_pause(self, idx: int) -> None:
        if not self._validate(idx):
            return
        state = self._session.step_states[idx]
        state.pause()
        logger.info(f"pause_timer: step={idx}")
        self._update_card(idx)
        self._schedule_save()

    def _on_resume(self, idx: int) -> None:
        if not self._validate(idx):
            return
        state = self._session.step_states[idx]
        state.resume()
        logger.info(f"resume_timer: step={idx}")
        self._update_card(idx)
        self._schedule_save()

    def _on_complete(self, idx: int) -> None:
        if not self._validate(idx):
            return
        state = self._session.step_states[idx]
        step_data = self._session.step_data(state)
        title = step_data.get("title", f"Step {idx+1}")

        state.complete()
        logger.info(f"complete_step: step={idx} title={title}")
        self._update_card(idx)
        self._schedule_save()

        # Clear focus on completed card
        self._cards[idx].set_focused(False)

        # Undo snackbar
        self._show_snackbar(title, lambda i=idx: self._on_undo_complete(i))

        # Sequential mode: auto-start next
        if self._sequential:
            self._advance_sequential(idx)

    def _on_undo_complete(self, idx: int) -> None:
        if not self._validate(idx):
            return
        state = self._session.step_states[idx]
        state.undo_complete()
        logger.info(f"undo_complete: step={idx}")
        self._update_card(idx)
        self._schedule_save()

    def _on_skip(self, idx: int) -> None:
        if not self._validate(idx):
            return
        state = self._session.step_states[idx]
        state.skip()
        logger.info(f"skip_step: step={idx}")
        self._update_card(idx)
        self._schedule_save()

    def _on_undo_skip(self, idx: int) -> None:
        if not self._validate(idx):
            return
        state = self._session.step_states[idx]
        state.undo_skip()
        logger.info(f"undo_skip: step={idx}")
        self._update_card(idx)
        self._schedule_save()

    def _on_reset(self, idx: int) -> None:
        if not self._validate(idx):
            return
        state = self._session.step_states[idx]
        state.reset()
        logger.info(f"reset_step: step={idx}")
        self._update_card(idx)
        self._schedule_save()

    def _on_adjust(self, idx: int, delta_secs: float) -> None:
        if not self._validate(idx):
            return
        state = self._session.step_states[idx]
        state.adjust(delta_secs)
        logger.info(f"adjust_timer: step={idx} delta={delta_secs}s")
        self._update_card(idx)
        self._schedule_save()

    def _on_notes_changed(self, idx: int, text: str) -> None:
        if not self._validate(idx):
            return
        self._session.step_states[idx].notes = text
        self._notes_save_timer.start()
        logger.info(f"notes_autosave: step={idx} len={len(text)}")

    # ── Sequential mode ───────────────────────────────────────────────────────

    def _on_sequential_toggled(self, checked: bool) -> None:
        self._sequential = checked
        if checked:
            self._start_sequential()
        else:
            # Clear all focus indicators
            for card in self._cards:
                card.set_focused(False)

    def _start_sequential(self) -> None:
        """Enable sequential mode and start the first idle step."""
        if self._session is None:
            return
        first_idle = next(
            (s.step_idx for s in self._session.step_states if s.status == "idle"),
            None
        )
        if first_idle is not None:
            self._on_start(first_idle)
            self._focus_step(first_idle)
            logger.info(f"start_sequential: first_step={first_idle}")
        else:
            logger.info("start_sequential: no idle steps found")

    def _advance_sequential(self, completed_idx: int) -> None:
        """After completing a step, auto-start the next idle step."""
        if self._session is None or not self._sequential:
            return
        next_idx = next(
            (s.step_idx for s in self._session.step_states
             if s.step_idx > completed_idx and s.status == "idle"),
            None
        )
        if next_idx is not None:
            self._on_start(next_idx)
            self._focus_step(next_idx)
            logger.info(f"auto_start_next: step={next_idx}")
        else:
            # No more idle steps — deactivate sequential
            self._sequential = False
            self._seq_btn.setChecked(False)
            for card in self._cards:
                card.set_focused(False)
            logger.info("auto_start_next: all steps done, sequential mode off")

    # ── Step focus (scroll to card) ───────────────────────────────────────────

    def _focus_step(self, idx: int) -> None:
        """Scroll right panel to show card at idx, highlight it."""
        if idx >= len(self._cards):
            return
        card = self._cards[idx]
        self._step_scroll.ensureWidgetVisible(card, 0, 20)

        # Update focused state on all cards
        for i, c in enumerate(self._cards):
            c.set_focused(i == idx)

        # Sync left panel selection
        if idx < self._step_status_list.count():
            self._step_status_list.setCurrentRow(idx)

        logger.info(f"focus_step: idx={idx}")

    def _on_step_list_clicked(self, item: QListWidgetItem) -> None:
        """Left panel step clicked → focus matching card."""
        idx = item.data(Qt.ItemDataRole.UserRole)
        if idx is not None:
            self._focus_step(idx)

    # ── Remove Temporary Block ────────────────────────────────────────────────

    def _on_remove_block(self, idx: int) -> None:
        if self._session is None or not self._validate(idx):
            return
        state = self._session.step_states[idx]
        if not state.is_temp:
            return
        sd = self._session.step_data(state)
        title = sd.get("title", "this block")

        ret = QMessageBox.question(
            self,
            "Remove Block",
            f"Remove temporary block '{title}'?\nThis cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if ret != QMessageBox.StandardButton.Yes:
            return

        # Remove card from layout and list
        card = self._cards[idx]
        self._step_layout.removeWidget(card)
        card.deleteLater()
        self._cards.pop(idx)

        # Remove from session (re-indexes step_states)
        self._session.remove_temp_block(idx)

        # Re-index remaining cards
        for i in range(idx, len(self._cards)):
            self._cards[i].set_idx(i)

        self._update_left_step_status()
        self._update_session_stats()
        self._schedule_save()
        logger.info(f"remove_temp_block: idx={idx} title={title}")

    # ── Add Temporary Block ───────────────────────────────────────────────────

    def _on_add_block(self) -> None:
        if self._session is None:
            return
        dlg = AddBlockDialog(self)
        if dlg.exec() != AddBlockDialog.DialogCode.Accepted:
            return
        title = dlg.block_title()
        btype = dlg.block_type()
        dur_m = dlg.duration_minutes()
        notes = dlg.notes()

        state = self._session.add_temp_block(title, btype, dur_m, notes)
        idx = state.step_idx
        step_data = state.temp_step_data

        card = StepCard(idx, step_data, state, parent=self._step_content)
        self._wire_card(card)
        self._cards.append(card)

        # Insert before the stretch spacer
        count = self._step_layout.count()
        self._step_layout.insertWidget(count - 1, card)

        self._update_left_step_status()
        self._update_session_stats()
        self._schedule_save()
        logger.info(f"add_block: title={title} type={btype} dur={dur_m}m")

    # ── Save Session to Lab Notebook ──────────────────────────────────────────

    def _on_save_session(self) -> None:
        if self._session is None:
            return
        self._save_to_notebook()
        ToastManager.show_success("Session saved to Lab Notebook.")

        msg = QMessageBox(self)
        msg.setWindowTitle("Session Saved")
        msg.setText("Session saved to Lab Notebook.")
        msg.setInformativeText("Clear the current session state and start fresh?")
        clear_btn = msg.addButton("Clear Session", QMessageBox.ButtonRole.DestructiveRole)
        keep_btn  = msg.addButton("Keep Running",  QMessageBox.ButtonRole.RejectRole)
        msg.setDefaultButton(keep_btn)
        msg.exec()

        if msg.clickedButton() is clear_btn:
            self._clear_session_state()

        logger.info("save_to_notebook: manual_save")

    # ── End Run ───────────────────────────────────────────────────────────────

    def _on_end_run(self) -> None:
        if self._session is None:
            return
        proto_name = (self._session.protocol_snapshot or {}).get("name", "")
        self._save_to_notebook()
        self._clear_session_state()
        ToastManager.show_success(
            f"Run saved: {proto_name}" if proto_name else "Run saved to Lab Notebook."
        )
        logger.info("end_run")

    def _clear_session_state(self) -> None:
        """Tear down all session state and reset the UI."""
        self.app.data.clear_active_session()
        self._session = None
        self._cards.clear()
        self._sequential = False
        self._tick_timer.stop()

        # Hide header buttons
        self._add_block_btn.setVisible(False)
        self._save_btn.setVisible(False)
        self._end_run_btn.setVisible(False)
        self._seq_btn.setChecked(False)
        self._seq_btn.setVisible(False)
        self._session_badge.setVisible(False)

        # Hide step list
        self._step_status_list.setVisible(False)
        self._steps_hdr.setVisible(False)
        self._step_status_list.clear()

        self._show_idle_state()
        self._info_name.setText("—")
        self._info_meta.setText("")

    # ── Session restore ───────────────────────────────────────────────────────

    def _offer_restore(self, raw: dict) -> None:
        if (self._session is not None
                and self._session.protocol_id == raw.get("protocol_id", "")):
            return

        dlg = RestoreSessionDialog(raw, self)
        if dlg.exec() != RestoreSessionDialog.DialogCode.Accepted:
            return

        action = dlg.action()
        logger.info(f"restore_session: action={action}")

        if action == "resume":
            try:
                restored = RunModeSession.from_dict(raw)
                self._session = restored
                self._render_step_cards_once()
                self._tick_timer.start()
                self._add_block_btn.setVisible(True)
                self._save_btn.setVisible(True)
                self._end_run_btn.setVisible(True)
                self._seq_btn.setVisible(True)
                self._session_badge.setText("● Resumed")
                self._session_badge.setVisible(True)

                # Highlight the restored protocol in the list
                proto_id = restored.protocol_id
                for i in range(self._proto_list.count()):
                    item = self._proto_list.item(i)
                    if item and (item.data(Qt.ItemDataRole.UserRole) or {}).get("id") == proto_id:
                        self._proto_list.setCurrentItem(item)
                        break
                logger.info(f"restore_session: resumed protocol_id={proto_id}")
            except Exception as e:
                logger.error(f"restore_session error: {e}")

        elif action == "save_notebook":
            try:
                restored = RunModeSession.from_dict(raw)
                self._session = restored
                self._save_to_notebook()
                self.app.data.clear_active_session()
                self._session = None
            except Exception as e:
                logger.error(f"save_notebook error: {e}")

        else:  # discard
            self.app.data.clear_active_session()

    # ── Autosave ──────────────────────────────────────────────────────────────

    def _schedule_save(self) -> None:
        self._save_timer.start()

    def _do_save(self) -> None:
        if self._session is None:
            return
        try:
            self.app.data.save_active_session(self._session.to_dict())
            logger.info("autosave: runtime_session.json written")
        except Exception as e:
            logger.error(f"autosave error: {e}")

    # ── Save to notebook ──────────────────────────────────────────────────────

    def _save_to_notebook(self) -> None:
        if self._session is None:
            return
        try:
            proto = self._session.protocol_snapshot
            now_ts = int(time.time() * 1000)
            start_ts = int(self._session.session_start_ts * 1000)
            dur_s = (time.time() - self._session.session_start_ts)

            step_records = []
            for state in self._session.step_states:
                sd = self._session.step_data(state)
                step_records.append({
                    "stepId":      state.step_id,
                    "stepTitle":   sd.get("title", ""),
                    "stepType":    sd.get("type", ""),
                    "status":      state.status,
                    "plannedSecs": state.original_planned_secs,
                    "usedSecs":    state.elapsed_secs(),  # includes running time
                    "notes":       state.notes,
                })

            dt = datetime.fromtimestamp(self._session.session_start_ts)
            record = {
                "id":               str(uuid.uuid4()),
                "title":            f"{proto.get('name', 'Untitled')} — {dt.strftime('%b %d, %Y')}",
                "protocolId":       proto.get("id", ""),
                "protocolName":     proto.get("name", "Untitled"),
                "protocolSnapshot": proto,
                "startedAt":        start_ts,
                "endedAt":          now_ts,
                "actualDuration":   dur_s,
                "timeline":         [],
                "stepRecords":      step_records,
                "observations":     "",
                "tags":             [],
                "notes":            "",
            }
            runs = self.app.data.load_runs()
            runs.insert(0, record)
            self.app.data.save_runs(runs)
            logger.info(f"save_to_notebook: saved run record id={record['id']}")
            # Notify other pages (Dashboard count, History list)
            bus.emit("run_session_saved",
                     protocol_name=proto.get("name", ""))
            bus.emit("notebook_record_created",
                     protocol_name=proto.get("name", ""))
        except Exception as e:
            logger.error(f"save_to_notebook error: {e}")

    # ── Left panel step status (clickable) ────────────────────────────────────

    def _update_left_step_status(self) -> None:
        if self._session is None:
            return

        self._step_status_list.setVisible(True)
        self._steps_hdr.setVisible(True)
        self._step_status_list.clear()

        status_icons = {
            "idle":      ("●", Colors.TEXT_MUTED),
            "running":   ("▶", Colors.SUCCESS),
            "paused":    ("⏸", Colors.WARNING),
            "completed": ("✓", Colors.ACCENT_LIGHT),
            "skipped":   ("⟩", Colors.TEXT_MUTED),
        }

        for state in self._session.step_states:
            sd = self._session.step_data(state)
            title = sd.get("title", f"Block {state.step_idx + 1}")
            icon, color = status_icons.get(state.status, ("●", Colors.TEXT_MUTED))
            short = f"{icon}  {title[:20]}{'…' if len(title) > 20 else ''}"
            item = QListWidgetItem(short)
            item.setData(Qt.ItemDataRole.UserRole, state.step_idx)
            item.setForeground(QColor(color))
            self._step_status_list.addItem(item)

    # ── Session stats in info bar ─────────────────────────────────────────────

    def _update_session_stats(self) -> None:
        if self._session is None:
            return
        states = self._session.step_states
        total   = len(states)
        done    = sum(1 for s in states if s.status == "completed")
        skipped = sum(1 for s in states if s.status == "skipped")
        proto   = self._session.protocol_snapshot
        total_min = DataService.protocol_total_minutes(proto)
        self._info_meta.setText(
            f"{total} steps  ·  {done} done  ·  {skipped} skipped"
            f"  ·  ~{DataService.format_duration(total_min)}"
        )

    # ── Idle / empty state ────────────────────────────────────────────────────

    def _show_idle_state(self) -> None:
        while self._step_layout.count():
            item = self._step_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        lbl = QLabel("Select a protocol from the left panel to begin a run.")
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl.setWordWrap(True)
        lbl.setStyleSheet(
            f"color: {Colors.TEXT_MUTED}; font-size: {Fonts.SIZE_MD}px;"
            f"font-style: italic;"
        )
        self._step_layout.addStretch()
        self._step_layout.addWidget(lbl)
        self._step_layout.addStretch()

    # ── Snackbar ──────────────────────────────────────────────────────────────

    def _show_snackbar(self, step_title: str, on_undo) -> None:
        if self._snackbar is not None:
            self._snackbar.hide()
            self._snackbar.deleteLater()

        sb = _UndoSnackbar(step_title, on_undo, parent=self._step_scroll)
        sb.setFixedHeight(48)
        self._snackbar = sb
        self._reposition_snackbar()
        sb.show()
        sb.raise_()

    def _reposition_snackbar(self) -> None:
        if self._snackbar is None:
            return
        sr = self._step_scroll
        w = sr.width() - 40
        x = 20
        y = sr.height() - 58
        self._snackbar.setGeometry(x, y, w, 48)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._reposition_snackbar()

    # ── Validation helper ─────────────────────────────────────────────────────

    def _validate(self, idx: int) -> bool:
        return (self._session is not None
                and 0 <= idx < len(self._session.step_states)
                and idx < len(self._cards))
