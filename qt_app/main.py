#!/usr/bin/env python3
"""
BenchFlow — PySide6 entry point.

Usage
-----
    python3 qt_app/main.py

Or from the repo root:
    python3 -m qt_app.main
"""
import sys
import os

# Ensure the repo root is on sys.path so `qt_app.*` imports resolve
# whether we run as `python3 qt_app/main.py` or `python3 -m qt_app.main`
_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt

from qt_app.theme import apply_theme
from qt_app.app import BenchFlowApp
from qt_app.services.data import DataService


def main() -> None:
    app = QApplication(sys.argv)
    app.setApplicationName("BenchFlow")
    app.setOrganizationName("BenchFlow")
    app.setApplicationVersion("0.1.1")

    # Load persisted theme preference before creating the window
    _ds = DataService()
    _prefs = _ds.load_settings()
    _theme = _prefs.get("theme", "dark")
    if _theme == "system":
        _theme = "dark"   # system theme not yet implemented → fall back

    apply_theme(app, _theme)

    window = BenchFlowApp()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
