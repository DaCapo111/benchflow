"""Schedule page — Phase 4 implementation."""
from __future__ import annotations
from PySide6.QtWidgets import QWidget
from qt_app.views._placeholder import _PlaceholderPage


class SchedulePage(_PlaceholderPage):
    def __init__(self, app: "BenchFlowApp", parent: QWidget | None = None) -> None:  # type: ignore[name-defined]
        super().__init__(
            title="Schedule",
            emoji="🗓",
            description="Plan experiments on a calendar timeline.\n"
                        "Drag-and-drop blocks via QGraphicsScene — GPU-accelerated.",
            phase="Phase 4",
            app=app,
            parent=parent,
        )
