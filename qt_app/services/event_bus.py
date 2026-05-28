"""
EventBus — lightweight pub/sub dispatcher for inter-page communication.

Pages emit events to signal changes; other pages subscribe to react without
holding direct references to each other.

Usage
-----
    from qt_app.services.event_bus import bus

    # Emit after saving
    bus.emit("run_session_saved", session_id="abc123", protocol="Western Blot")

    # Subscribe in a page __init__
    bus.subscribe("schedule_updated", self._on_schedule_updated)

    # Unsubscribe when tearing down
    bus.unsubscribe("schedule_updated", self._on_schedule_updated)

Supported events
----------------
    protocol_created           payload: {"protocol_id", "name"}
    protocol_updated           payload: {"protocol_id"}
    protocol_deleted           payload: {"protocol_id"}
    run_session_started        payload: {"session_id", "protocol_id", "protocol_name"}
    run_session_saved          payload: {"protocol_name"}
    schedule_updated           payload: {}
    notebook_record_created    payload: {"protocol_name"}
    active_session_restored    payload: {"protocol_name"}
    data_saved                 payload: {"filename"}
    data_error                 payload: {"context", "message"}
"""
from __future__ import annotations

import logging
from typing import Any, Callable

logger = logging.getLogger("benchflow.event_bus")


# ── Known events (for documentation / typo prevention) ────────────────────────

KNOWN_EVENTS = frozenset({
    "protocol_created",
    "protocol_updated",
    "protocol_deleted",
    "run_session_started",
    "run_session_saved",
    "schedule_updated",
    "notebook_record_created",
    "active_session_restored",
    "data_saved",
    "data_error",
})


# ── EventBus ──────────────────────────────────────────────────────────────────

class _EventBus:
    """Process-wide singleton event dispatcher.

    Thread safety: designed for single-threaded Qt main-loop use only.
    """

    def __init__(self) -> None:
        self._listeners: dict[str, list[Callable[..., None]]] = {}

    def subscribe(self, event: str, callback: Callable[..., None]) -> None:
        """Register *callback* to be called whenever *event* is emitted.

        Safe to call multiple times — duplicate registrations are ignored.
        """
        lst = self._listeners.setdefault(event, [])
        if callback not in lst:
            lst.append(callback)

    def unsubscribe(self, event: str, callback: Callable[..., None]) -> None:
        """Remove *callback* from *event*.  No-op if not registered."""
        lst = self._listeners.get(event, [])
        try:
            lst.remove(callback)
        except ValueError:
            pass

    def emit(self, event: str, **payload: Any) -> None:
        """Fire all callbacks registered for *event*.

        Callbacks are called with keyword arguments from *payload*.
        Exceptions inside callbacks are caught and logged so one bad
        subscriber cannot silence the others.
        """
        for cb in list(self._listeners.get(event, [])):
            try:
                cb(**payload)
            except Exception as exc:
                logger.exception(f"EventBus handler error [{event}] cb={cb}: {exc}")

    def clear(self) -> None:
        """Remove all listeners.  Useful for testing."""
        self._listeners.clear()


# ── Module-level singleton ────────────────────────────────────────────────────

bus = _EventBus()
