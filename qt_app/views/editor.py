"""Protocol Editor page — Phase 6 implementation."""
from __future__ import annotations
from PySide6.QtWidgets import QWidget
from qt_app.views._placeholder import _PlaceholderPage


class EditorPage(_PlaceholderPage):
    def __init__(self, app: "BenchFlowApp", parent: QWidget | None = None) -> None:  # type: ignore[name-defined]
        super().__init__(
            title="Protocol Editor",
            emoji="✏️",
            description="Add, reorder, and edit steps in a protocol.\n"
                        "Set timers, reagents, and notes per step.",
            phase="Phase 6",
            app=app,
            parent=parent,
        )
