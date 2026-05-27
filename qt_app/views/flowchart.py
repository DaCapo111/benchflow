"""Flowchart page — Phase 8 implementation."""
from __future__ import annotations
from PySide6.QtWidgets import QWidget
from qt_app.views._placeholder import _PlaceholderPage


class FlowchartPage(_PlaceholderPage):
    def __init__(self, app: "BenchFlowApp", parent: QWidget | None = None) -> None:  # type: ignore[name-defined]
        super().__init__(
            title="Flowchart",
            emoji="⎇",
            description="Visualize your protocol as an interactive flowchart.\n"
                        "Built with QGraphicsScene for GPU-accelerated rendering.",
            phase="Phase 8",
            app=app,
            parent=parent,
        )
