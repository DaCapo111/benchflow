"""
BenchFlowApp — Main application window (QMainWindow).

Layout
------
QMainWindow
└── central widget (QWidget, objectName="CentralWidget")
    └── QHBoxLayout (no margins)
        ├── Sidebar  (fixed 196 px)
        └── QStackedWidget  (page container, expands)
"""
from __future__ import annotations

from PySide6.QtCore import Qt, QSize
from PySide6.QtWidgets import (
    QHBoxLayout, QMainWindow, QSizePolicy, QStackedWidget, QWidget,
)

from qt_app.theme import Colors
from qt_app.services.data import DataService
from qt_app.components.sidebar import Sidebar
from qt_app.views import (
    DashboardPage, LibraryPage, EditorPage, FlowchartPage,
    RunModePage, HistoryPage, SettingsPage, ImportPage, SchedulePage,
)


class BenchFlowApp(QMainWindow):
    """Top-level window.  Owns the Sidebar, QStackedWidget, and DataService."""

    # Pages that share the "library" highlight in the sidebar
    _LIBRARY_ALIASES = {"editor", "import"}

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("BenchFlow")
        self.resize(1280, 800)
        self.setMinimumSize(QSize(900, 600))

        # ── Shared data service ───────────────────────────────────────────────
        self.data = DataService()

        # ── Central widget + main layout ──────────────────────────────────────
        central = QWidget()
        central.setObjectName("CentralWidget")
        central.setStyleSheet(f"background: {Colors.BG_DARK};")
        self.setCentralWidget(central)

        layout = QHBoxLayout(central)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        # ── Sidebar ───────────────────────────────────────────────────────────
        self.sidebar = Sidebar()
        self.sidebar.nav_requested.connect(self.navigate)
        layout.addWidget(self.sidebar)

        # ── Page container ────────────────────────────────────────────────────
        self._stack = QStackedWidget()
        self._stack.setObjectName("PageContainer")
        self._stack.setStyleSheet(
            f"QStackedWidget#PageContainer {{"
            f"  background: {Colors.BG_DARK};"
            f"  border-radius: 20px;"
            f"  border: 1px solid {Colors.BORDER};"
            f"}}"
        )
        layout.addWidget(self._stack, stretch=1)

        # ── Build pages ───────────────────────────────────────────────────────
        self._pages: dict[str, "BasePage"] = {}  # type: ignore[name-defined]
        self._register_pages()

        # ── Navigate to initial page ──────────────────────────────────────────
        self.navigate("dashboard")

    # ── Page registration ─────────────────────────────────────────────────────

    def _register_pages(self) -> None:
        page_classes = [
            ("dashboard",  DashboardPage),
            ("library",    LibraryPage),
            ("editor",     EditorPage),
            ("import",     ImportPage),
            ("schedule",   SchedulePage),
            ("flowchart",  FlowchartPage),
            ("run",        RunModePage),
            ("history",    HistoryPage),
            ("settings",   SettingsPage),
        ]
        for page_id, PageClass in page_classes:
            page = PageClass(app=self)
            self._pages[page_id] = page
            self._stack.addWidget(page)

    # ── Navigation ────────────────────────────────────────────────────────────

    def navigate(self, page_id: str) -> None:
        """Switch to *page_id*.  Editor and Import alias to Library in sidebar."""
        page = self._pages.get(page_id)
        if page is None:
            return

        # Raise the page
        self._stack.setCurrentWidget(page)
        page.on_show()

        # Update sidebar highlight
        sidebar_id = "library" if page_id in self._LIBRARY_ALIASES else page_id
        self.sidebar.set_active(sidebar_id)
