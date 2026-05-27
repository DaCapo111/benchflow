"""BenchFlow Qt page views."""
from .base_page import BasePage
from .dashboard import DashboardPage
from .library import LibraryPage
from .editor import EditorPage
from .flowchart import FlowchartPage
from .run_mode import RunModePage
from .history import HistoryPage
from .settings import SettingsPage
from .import_page import ImportPage
from .schedule import SchedulePage

__all__ = [
    "BasePage",
    "DashboardPage",
    "LibraryPage",
    "EditorPage",
    "FlowchartPage",
    "RunModePage",
    "HistoryPage",
    "SettingsPage",
    "ImportPage",
    "SchedulePage",
]
