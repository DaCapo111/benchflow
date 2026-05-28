"""
ToastManager — non-blocking floating notification system.

Shows transient feedback messages (success / warning / error / info) in the
bottom-right corner of the app window.  Multiple toasts stack vertically and
auto-dismiss after a configurable duration.

Usage
-----
    # One-time setup in BenchFlowApp.__init__:
    ToastManager.install(self.centralWidget())

    # From any page:
    from qt_app.components.toast import ToastManager
    ToastManager.show_success("Session saved to Lab Notebook.")
    ToastManager.show_error("Autosave failed — check disk space.")
    ToastManager.show_warning("Protocol has no steps.")
    ToastManager.show_info("Restored previous session.")
"""
from __future__ import annotations

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QWidget

from qt_app.theme import Colors, Fonts, Radii, current_theme


# ── Per-level style ───────────────────────────────────────────────────────────

def _level_style(level: str) -> dict[str, str]:
    light = current_theme() == "light"
    bg_by_level = {
        "success": Colors.SUCCESS_BG if light else "rgba(20, 83, 45, 0.96)",
        "error": Colors.DANGER_BG if light else "rgba(69, 10, 10, 0.96)",
        "warning": Colors.WARNING_BG if light else "rgba(67, 20, 7, 0.96)",
        "info": Colors.BG_CARD if light else "rgba(30, 41, 59, 0.96)",
    }
    base = {
        "success": {"border": Colors.SUCCESS, "icon": "✓", "color": Colors.SUCCESS},
        "error": {"border": Colors.DANGER, "icon": "✕", "color": Colors.DANGER},
        "warning": {"border": Colors.WARNING, "icon": "⚠", "color": Colors.WARNING},
        "info": {"border": Colors.ACCENT, "icon": "ℹ", "color": Colors.ACCENT},
    }
    style = base.get(level, base["info"]).copy()
    style["bg"] = bg_by_level.get(level, bg_by_level["info"])
    return style

_TOAST_W       = 320   # fixed width
_TOAST_H       = 52    # fixed height per toast
_TOAST_MARGIN  = 16    # distance from parent edge
_TOAST_SPACING = 6     # gap between stacked toasts
_TOAST_DURATION = 3800 # ms before auto-dismiss


# ── _Toast ────────────────────────────────────────────────────────────────────

class _Toast(QFrame):
    """Single floating toast message."""

    dismissed = Signal(object)  # emits self

    def __init__(self, message: str, level: str, parent: QWidget) -> None:
        super().__init__(parent)
        self._level = level
        style = _level_style(level)

        self.setFixedSize(_TOAST_W, _TOAST_H)
        self.setStyleSheet(
            f"QFrame {{"
            f"  background: {style['bg']};"
            f"  border: 1px solid {style['border']};"
            f"  border-radius: {Radii.MD}px;"
            f"}}"
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        lay = QHBoxLayout(self)
        lay.setContentsMargins(14, 0, 14, 0)
        lay.setSpacing(10)

        icon = QLabel(style["icon"])
        icon.setFixedWidth(18)
        icon.setStyleSheet(
            f"color: {style['color']}; font-size: {Fonts.SIZE_MD}px; font-weight: 700;"
        )
        lay.addWidget(icon)

        msg_lbl = QLabel(message)
        msg_lbl.setWordWrap(False)
        msg_lbl.setStyleSheet(
            f"color: {Colors.TEXT_PRIMARY}; font-size: {Fonts.SIZE_SM}px;"
        )
        # Truncate long messages
        fm = msg_lbl.fontMetrics()
        elided = fm.elidedText(message, Qt.TextElideMode.ElideRight, _TOAST_W - 80)
        msg_lbl.setText(elided)
        lay.addWidget(msg_lbl, stretch=1)

        # Auto-dismiss timer
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.setInterval(_TOAST_DURATION)
        self._timer.timeout.connect(self._dismiss)
        self._timer.start()

        self.raise_()
        self.show()

    def mousePressEvent(self, event) -> None:
        """Click to dismiss immediately."""
        self._dismiss()
        super().mousePressEvent(event)

    def _dismiss(self) -> None:
        self._timer.stop()
        self.dismissed.emit(self)
        self.deleteLater()


# ── ToastManager ─────────────────────────────────────────────────────────────

class ToastManager:
    """Class-level singleton for showing floating toasts.

    Call ``ToastManager.install(widget)`` once at startup; then call
    ``show_success`` / ``show_error`` / ``show_warning`` / ``show_info``
    from anywhere.
    """

    _parent: QWidget | None = None
    _active: list[_Toast] = []

    # ── Setup ─────────────────────────────────────────────────────────────────

    @classmethod
    def install(cls, parent: QWidget) -> None:
        """Register the host widget.  Toasts appear as children of *parent*."""
        cls._parent = parent

    # ── Public API ────────────────────────────────────────────────────────────

    @classmethod
    def show_success(cls, message: str) -> None:
        cls._show(message, "success")

    @classmethod
    def show_error(cls, message: str) -> None:
        cls._show(message, "error")

    @classmethod
    def show_warning(cls, message: str) -> None:
        cls._show(message, "warning")

    @classmethod
    def show_info(cls, message: str) -> None:
        cls._show(message, "info")

    # ── Internal ──────────────────────────────────────────────────────────────

    @classmethod
    def _show(cls, message: str, level: str) -> None:
        if cls._parent is None:
            return
        toast = _Toast(message, level, cls._parent)
        toast.dismissed.connect(cls._on_dismissed)
        cls._active.append(toast)
        cls._reposition()

    @classmethod
    def _on_dismissed(cls, toast: _Toast) -> None:
        if toast in cls._active:
            cls._active.remove(toast)
        cls._reposition()

    @classmethod
    def _reposition(cls) -> None:
        """Stack active toasts bottom-right of the parent widget."""
        if cls._parent is None:
            return
        pw = cls._parent.width()
        ph = cls._parent.height()

        # Remove references to deleted widgets
        cls._active = [t for t in cls._active if not t.isHidden() or t.isVisible()]

        y = ph - _TOAST_MARGIN
        for toast in reversed(cls._active):
            y -= _TOAST_H
            x = pw - _TOAST_W - _TOAST_MARGIN
            toast.move(x, y)
            toast.raise_()
            y -= _TOAST_SPACING
