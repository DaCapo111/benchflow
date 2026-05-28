"""BenchFlow service layer — data persistence and business logic."""
from .data import DataService
from .run_service import RunModeSession, StepRunState, format_timer
from .schedule_service import (
    make_scheduled_experiment, format_time_ms, format_duration_min, week_start,
)
from .app_state import AppState
from .event_bus import bus, _EventBus
from .background import BackgroundTaskManager, init_bg, bg
from .error_handler import eh, _ErrorHandler
from .perf import perf, _Perf

__all__ = [
    # Data
    "DataService",
    # Run
    "RunModeSession", "StepRunState", "format_timer",
    # Schedule
    "make_scheduled_experiment", "format_time_ms", "format_duration_min", "week_start",
    # Phase 4.75 — app architecture
    "AppState",
    "bus", "_EventBus",
    "BackgroundTaskManager", "init_bg", "bg",
    "eh", "_ErrorHandler",
    "perf", "_Perf",
]
