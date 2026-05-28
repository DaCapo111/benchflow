"""
BenchFlowApp — Main application window (QMainWindow).

Layout
------
QMainWindow
└── central widget (QWidget, objectName="CentralWidget")
    └── QHBoxLayout (no margins)
        ├── Sidebar  (fixed 196 px)
        └── QStackedWidget  (page container, expands)

Phase 4.75 additions
--------------------
- app.state   : AppState — cross-page UI state
- app.bg      : BackgroundTaskManager — centralised debounce/flush
- ToastManager installed on centralWidget()
- closeEvent  : flush pending saves, persist AppState snapshot
"""
from __future__ import annotations

import logging
from pathlib import Path

from PySide6.QtCore import Qt, QSize
from PySide6.QtWidgets import (
    QHBoxLayout, QMainWindow, QSizePolicy, QStackedWidget, QWidget,
)

from qt_app.theme import Colors
from qt_app.services.data import DataService
from qt_app.services.event_bus import bus
from qt_app.services.app_state import AppState
from qt_app.services.background import init_bg
from qt_app.components.sidebar import Sidebar
from qt_app.components.toast import ToastManager
from qt_app.views import (
    DashboardPage, LibraryPage, EditorPage, FlowchartPage,
    RunModePage, HistoryPage, SettingsPage, ImportPage, SchedulePage,
)

# ── Logging ───────────────────────────────────────────────────────────────────
_logs_dir = Path(__file__).parent.parent / "logs"
_logs_dir.mkdir(exist_ok=True)
_app_handler = logging.FileHandler(_logs_dir / "qt_app.log", encoding="utf-8")
_app_handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
_app_logger = logging.getLogger("benchflow.app")
if not _app_logger.handlers:
    _app_logger.addHandler(_app_handler)
    _app_logger.setLevel(logging.INFO)


class BenchFlowApp(QMainWindow):
    """Top-level window.  Owns the Sidebar, QStackedWidget, DataService,
    AppState, and BackgroundTaskManager."""

    # Pages that share the "library" highlight in the sidebar
    _LIBRARY_ALIASES = {"editor", "import"}

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("BenchFlow")
        self.resize(1280, 800)
        self.setMinimumSize(QSize(900, 600))

        # ── Shared services ───────────────────────────────────────────────────
        self.data  = DataService()
        self.state = AppState(self)
        self.bg    = init_bg(self)   # BackgroundTaskManager singleton

        # ── Load persisted settings → apply to AppState ───────────────────────
        _settings = self.data.load_settings()
        self.state.autosave_interval_s = int(
            _settings.get("autosave_interval_s", 30)
        )

        # ── Central widget + main layout ──────────────────────────────────────
        central = QWidget()
        central.setObjectName("CentralWidget")
        central.setStyleSheet(f"background: {Colors.BG_DARK};")
        self.setCentralWidget(central)

        # Install toast overlay on the central widget
        ToastManager.install(central)

        layout = QHBoxLayout(central)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        # ── Sidebar ───────────────────────────────────────────────────────────
        self.sidebar = Sidebar()
        self.sidebar.nav_requested.connect(self.navigate)
        layout.addWidget(self.sidebar)

        # ── Page container ────────────────────────────────────────────────────
        self._stack = QStackedWidget()
        self._stack.setObjectName("PageContainer")
        self._stack.setStyleSheet(
            f"QStackedWidget#PageContainer {{"
            f"  background: {Colors.BG_PAGE};"
            f"  border-radius: 20px;"
            f"  border: 1px solid {Colors.BORDER};"
            f"}}"
        )
        layout.addWidget(self._stack, stretch=1)

        # ── Build pages ───────────────────────────────────────────────────────
        self._pages: dict[str, "BasePage"] = {}  # type: ignore[name-defined]
        self._register_pages()

        # ── Subscribe to theme changes → refresh container border ────────────────
        bus.subscribe("theme_changed", self._on_theme_changed)

        # Mark app as ready
        self.state.app_ready = True
        _app_logger.info("BenchFlowApp started")

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

    def _on_theme_changed(self, theme: str = "dark", **_kw) -> None:
        """Re-apply theme-sensitive styles on the app window chrome."""
        central = self.centralWidget()
        if central:
            central.setStyleSheet(f"background: {Colors.BG_DARK};")
        self._stack.setStyleSheet(
            f"QStackedWidget#PageContainer {{"
            f"  background: {Colors.BG_PAGE};"
            f"  border-radius: 20px;"
            f"  border: 1px solid {Colors.BORDER};"
            f"}}"
        )

    def navigate(self, page_id: str) -> None:
        """Switch to *page_id*.  Editor and Import alias to Library in sidebar."""
        page = self._pages.get(page_id)
        if page is None:
            return

        # Ensure theme is fresh before showing (lazy rebuild if theme changed)
        page._ensure_fresh_theme()

        # Raise the page
        self._stack.setCurrentWidget(page)
        page.on_show()

        # Update sidebar highlight
        sidebar_id = "library" if page_id in self._LIBRARY_ALIASES else page_id
        self.sidebar.set_active(sidebar_id)

        # Update AppState
        self.state.set_page(page_id)
        _app_logger.info(f"navigate: {page_id}")

    # ── Close lifecycle ───────────────────────────────────────────────────────

    def closeEvent(self, event) -> None:
        """Graceful shutdown: flush pending saves, persist active session."""
        _app_logger.info("closeEvent: flushing pending tasks…")

        # 1. Fire any debounced autosave callbacks immediately
        try:
            self.bg.flush_all()
        except Exception as exc:
            _app_logger.error(f"closeEvent flush_all error: {exc}")

        # 2. Ensure active Run Mode session is persisted if running
        try:
            run_page = self._pages.get("run")
            if run_page is not None and hasattr(run_page, "_session"):
                session = getattr(run_page, "_session", None)
                if session is not None:
                    self.data.save_active_session(session.to_dict())
                    _app_logger.info("closeEvent: run session flushed to disk")
        except Exception as exc:
            _app_logger.error(f"closeEvent run session flush error: {exc}")

        # 3. Cancel all remaining background timers
        try:
            self.bg.cancel_all()
        except Exception as exc:
            _app_logger.error(f"closeEvent cancel_all error: {exc}")

        _app_logger.info("closeEvent: shutdown complete")
        super().closeEvent(event)
