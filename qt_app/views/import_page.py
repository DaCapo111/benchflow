"""Import page — Phase 5 implementation."""
from __future__ import annotations
from PySide6.QtWidgets import QWidget
from qt_app.views._placeholder import _PlaceholderPage


class ImportPage(_PlaceholderPage):
    def __init__(self, app: "BenchFlowApp", parent: QWidget | None = None) -> None:  # type: ignore[name-defined]
        super().__init__(
            title="Import Protocol",
            emoji="📥",
            description="Import protocols from PDF, DOCX, or JSON.\n"
                        "Accessible from the Library page.",
            phase="Phase 5",
            app=app,
            parent=parent,
        )
