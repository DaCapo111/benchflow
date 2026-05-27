"""Lab Notebook / History page — Phase 7 implementation."""
from __future__ import annotations
from PySide6.QtWidgets import QWidget
from qt_app.views._placeholder import _PlaceholderPage


class HistoryPage(_PlaceholderPage):
    def __init__(self, app: "BenchFlowApp", parent: QWidget | None = None) -> None:  # type: ignore[name-defined]
        super().__init__(
            title="Lab Notebook",
            emoji="📓",
            description="Browse completed run records with timestamps, notes, and export.\n"
                        "Rich text editing via QTextEdit.",
            phase="Phase 7",
            app=app,
            parent=parent,
        )
