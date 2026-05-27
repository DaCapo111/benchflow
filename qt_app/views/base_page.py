"""BasePage — common superclass for all BenchFlow pages."""
from __future__ import annotations

from PySide6.QtWidgets import QWidget, QVBoxLayout
from qt_app.theme import Colors


class BasePage(QWidget):
    """Every page inherits from this.

    Provides:
    - transparent background so the container's dark bg shows through
    - ``app`` reference for cross-page navigation / data access
    - ``on_show()`` hook called by MainWindow before the page is raised
    - ``layout`` convenience property
    """

    def __init__(self, app: "BenchFlowApp", parent: QWidget | None = None) -> None:  # type: ignore[name-defined]
        super().__init__(parent)
        self.app = app
        self.setStyleSheet(f"background: {Colors.BG_PAGE};")

        self._root_layout = QVBoxLayout(self)
        self._root_layout.setContentsMargins(0, 0, 0, 0)
        self._root_layout.setSpacing(0)

    # ── Hook ──────────────────────────────────────────────────────────────────

    def on_show(self) -> None:
        """Called every time this page is raised (switched to).

        Override in subclasses to refresh data.
        """
        pass
