"""Protocol Library page — Phase 5 implementation."""
from __future__ import annotations
from PySide6.QtWidgets import QWidget
from qt_app.views._placeholder import _PlaceholderPage


class LibraryPage(_PlaceholderPage):
    def __init__(self, app: "BenchFlowApp", parent: QWidget | None = None) -> None:  # type: ignore[name-defined]
        super().__init__(
            title="Protocol Library",
            emoji="📋",
            description="Browse, create, and manage your wet-lab protocols.\n"
                        "Search by category, tag, or step type.",
            phase="Phase 5",
            app=app,
            parent=parent,
        )
