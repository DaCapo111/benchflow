"""
AppState — global UI state shared across BenchFlow pages.

Owned by BenchFlowApp (``app.state``).  Pages read from and write to AppState
rather than keeping redundant local copies of cross-page state.

Usage
-----
    # In a page
    self.app.state.selected_protocol_id = proto_id
    self.app.state.protocol_selection_changed.emit(proto_id)

    # Listening for changes
    self.app.state.run_session_changed.connect(self._on_run_session_changed)

Signals are emitted manually by the writer; AppState does not auto-emit on
attribute assignment (keeps the interface explicit).
"""
from __future__ import annotations

from datetime import date
from PySide6.QtCore import QObject, Signal


class AppState(QObject):
    """Singleton-like object owned by BenchFlowApp.

    All mutable attributes are plain Python values; signals are emitted
    explicitly by the code that changes the value, so consumers can react.
    """

    # ── Signals ───────────────────────────────────────────────────────────────

    # Navigation
    page_changed                 = Signal(str)          # page_id

    # Protocol Library
    protocol_selection_changed   = Signal(str)          # protocol_id ("")=cleared

    # Schedule
    schedule_selection_changed   = Signal(str)          # experiment_id ("")=cleared
    schedule_view_changed        = Signal(str, object)  # (view_mode, base_date)

    # Run Mode
    run_session_changed          = Signal(str)          # session_id  ("")=no session
    active_session_cleared       = Signal()

    # Dirty state
    unsaved_changes_changed      = Signal(bool)

    # ── State fields ──────────────────────────────────────────────────────────

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)

        # Library / Protocol
        self.selected_protocol_id: str = ""

        # Schedule
        self.selected_schedule_experiment_id: str = ""
        self.current_schedule_date: date = date.today()
        self.current_schedule_view: str = "workweek"

        # Run Mode
        self.active_run_session_id: str = ""
        self.selected_run_session_id: str = ""

        # Navigation
        self.last_opened_page: str = "dashboard"

        # Preferences (user-configurable)
        self.autosave_interval_s: int = 30  # autosave every N seconds

        # Dirty / ready flags
        self.unsaved_changes: bool = False
        self.app_ready: bool = False

    # ── Helpers ───────────────────────────────────────────────────────────────

    def mark_dirty(self) -> None:
        """Set unsaved_changes=True and emit signal."""
        if not self.unsaved_changes:
            self.unsaved_changes = True
            self.unsaved_changes_changed.emit(True)

    def mark_clean(self) -> None:
        """Clear unsaved_changes flag and emit signal."""
        if self.unsaved_changes:
            self.unsaved_changes = False
            self.unsaved_changes_changed.emit(False)

    def set_page(self, page_id: str) -> None:
        self.last_opened_page = page_id
        self.page_changed.emit(page_id)

    def set_active_run(self, session_id: str) -> None:
        self.active_run_session_id = session_id
        self.run_session_changed.emit(session_id)

    def clear_active_run(self) -> None:
        self.active_run_session_id = ""
        self.run_session_changed.emit("")
        self.active_session_cleared.emit()
