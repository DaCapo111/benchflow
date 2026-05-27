"""Settings page — Phase 8 implementation."""
from __future__ import annotations
from PySide6.QtWidgets import QWidget
from qt_app.views._placeholder import _PlaceholderPage


class SettingsPage(_PlaceholderPage):
    def __init__(self, app: "BenchFlowApp", parent: QWidget | None = None) -> None:  # type: ignore[name-defined]
        super().__init__(
            title="Settings",
            emoji="⚙",
            description="Manage categories, tags, theme, and app preferences.\n"
                        "Implemented with QFormLayout.",
            phase="Phase 8",
            app=app,
            parent=parent,
        )
