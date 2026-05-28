"""
BackgroundTaskManager — centralized debounce / deferred-task manager.

Replaces the pattern of each page holding its own ``QTimer`` for debounced
autosave.  All pending timers are named by key, making it easy to cancel or
flush them on app close.

Usage
-----
    from qt_app.services.background import bg

    # Debounce a save: cancel any pending save for this key, schedule a new one
    bg.debounce("run_autosave", 100, self._do_save)
    bg.debounce("notes_save",  1000, lambda: self._save_notes(idx))

    # Cancel explicitly (e.g. protocol unloaded)
    bg.cancel("run_autosave")

    # On app close: fire all pending callbacks immediately, then clear
    bg.flush_all()
    bg.cancel_all()
"""
from __future__ import annotations

import logging
from typing import Callable

from PySide6.QtCore import QObject, QTimer

logger = logging.getLogger("benchflow.background")


# ── BackgroundTaskManager ─────────────────────────────────────────────────────

class BackgroundTaskManager(QObject):
    """Debounce manager for autosave and other deferred UI actions.

    Owned by BenchFlowApp (``app.bg``).
    """

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._timers: dict[str, QTimer] = {}
        self._callbacks: dict[str, Callable[[], None]] = {}

    # ── Public API ────────────────────────────────────────────────────────────

    def debounce(self, key: str, delay_ms: int,
                 callback: Callable[[], None]) -> None:
        """Schedule *callback* after *delay_ms*, cancelling any pending call
        for the same *key*.

        If *delay_ms* ≤ 0 the callback is invoked immediately.
        """
        self.cancel(key)
        if delay_ms <= 0:
            try:
                callback()
            except Exception as exc:
                logger.exception(f"debounce immediate [{key}]: {exc}")
            return

        timer = QTimer(self)
        timer.setSingleShot(True)
        timer.setInterval(delay_ms)

        def _fire() -> None:
            self._timers.pop(key, None)
            self._callbacks.pop(key, None)
            try:
                callback()
            except Exception as exc:
                logger.exception(f"debounce fire [{key}]: {exc}")

        timer.timeout.connect(_fire)
        self._timers[key] = timer
        self._callbacks[key] = callback
        timer.start()

    def cancel(self, key: str) -> None:
        """Stop and remove any pending timer for *key*."""
        timer = self._timers.pop(key, None)
        self._callbacks.pop(key, None)
        if timer is not None:
            timer.stop()
            timer.deleteLater()

    def cancel_all(self) -> None:
        """Stop all pending timers without invoking their callbacks."""
        for key in list(self._timers):
            self.cancel(key)

    def flush_all(self) -> None:
        """Invoke all pending callbacks immediately, then clear timers.

        Call this during app close to ensure no autosave is lost.
        """
        keys = list(self._timers)
        for key in keys:
            timer = self._timers.pop(key, None)
            callback = self._callbacks.pop(key, None)
            if timer is not None:
                timer.stop()
                timer.deleteLater()
            if callback is not None:
                try:
                    callback()
                    logger.debug(f"flush [{key}]: fired")
                except Exception as exc:
                    logger.exception(f"flush [{key}]: error: {exc}")

    def pending_keys(self) -> list[str]:
        """Return names of all currently pending debounced tasks."""
        return [k for k, t in self._timers.items() if t.isActive()]


# ── Module-level singleton ────────────────────────────────────────────────────
# Populated with a real QObject parent by BenchFlowApp.__init__

bg: BackgroundTaskManager | None = None   # set by BenchFlowApp


def init_bg(parent: QObject) -> BackgroundTaskManager:
    """Create and register the global BackgroundTaskManager."""
    global bg
    bg = BackgroundTaskManager(parent)
    return bg
