"""BasePage — common superclass for all BenchFlow pages."""
from __future__ import annotations

from PySide6.QtWidgets import QWidget, QVBoxLayout
from qt_app.theme import Colors, current_theme
from qt_app.services.event_bus import bus


def _clear_layout(layout) -> None:
    """Recursively delete all items from *layout*."""
    while layout.count():
        item = layout.takeAt(0)
        w = item.widget()
        if w:
            w.deleteLater()
        elif item.layout():
            _clear_layout(item.layout())


class BasePage(QWidget):
    """Every page inherits from this.

    Provides:
    - transparent background so the container's dark bg shows through
    - ``app`` reference for cross-page navigation / data access
    - ``on_show()`` hook called by BenchFlowApp before the page is raised
    - ``_rebuild_theme()`` — clears root layout and re-calls ``_build()``
      so pages automatically re-render with the new theme colors
    """

    def __init__(self, app: "BenchFlowApp", parent: QWidget | None = None) -> None:  # type: ignore[name-defined]
        super().__init__(parent)
        self.app = app
        self._last_theme: str = ""   # set after first build; "" = needs build

        self.setStyleSheet(f"background: {Colors.BG_PAGE};")

        self._root_layout = QVBoxLayout(self)
        self._root_layout.setContentsMargins(0, 0, 0, 0)
        self._root_layout.setSpacing(0)

        # Subscribe to theme changes — fires whenever switch_theme() is called
        bus.subscribe("theme_changed", self._on_theme_changed)

    # ── Theme lifecycle ───────────────────────────────────────────────────────

    def _on_theme_changed(self, theme: str = "dark", **_kw) -> None:
        """Called via EventBus when the user switches themes.

        If this page is currently visible, rebuild immediately so the user
        sees the change straight away.  Otherwise, mark as stale and rebuild
        lazily in ``_ensure_fresh_theme()`` (called by BenchFlowApp.navigate
        before on_show).
        """
        if self.isVisible():
            self._rebuild_theme()
        else:
            self._last_theme = ""   # mark stale

    def _ensure_fresh_theme(self) -> None:
        """Called by BenchFlowApp.navigate() just before on_show().

        Rebuilds the page if the theme changed since the last visit.
        Subclasses that need special handling (e.g. RunMode) should override.
        """
        t = current_theme()
        if self._last_theme != t:
            self._rebuild_theme()

    def _rebuild_theme(self) -> None:
        """Clear root layout and re-call _build().

        Subclasses with significant runtime state (RunMode) override this to
        preserve in-progress sessions.
        """
        from qt_app.theme import current_theme as _ct
        self._last_theme = _ct()
        self.setStyleSheet(f"background: {Colors.BG_PAGE};")
        _clear_layout(self._root_layout)
        if hasattr(self, "_build"):
            self._build()  # type: ignore[attr-defined]

    # ── Show hook ─────────────────────────────────────────────────────────────

    def on_show(self) -> None:
        """Called every time this page is raised (switched to).

        Override in subclasses to refresh data.
        """
        pass
