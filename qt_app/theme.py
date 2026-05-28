"""
BenchFlow Qt Theme
==================
Central source of truth for colors, fonts, radii, and the global QSS stylesheet.

Usage
-----
    from qt_app.theme import apply_theme, Colors, Fonts

    app = QApplication(sys.argv)
    apply_theme(app)
"""

from __future__ import annotations
from PySide6.QtGui import QColor, QPalette, QFont, QFontDatabase
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt


# ── Colors ────────────────────────────────────────────────────────────────────

class Colors:
    # Backgrounds
    BG_DARK      = "#0f172a"   # app window bg
    BG_SIDEBAR   = "#1e293b"   # sidebar bg
    BG_CARD      = "#1e293b"   # card / panel bg
    BG_CARD_HOV  = "#263548"   # card hover
    BG_INPUT     = "#0f172a"   # input field bg
    BG_PAGE      = "#0f172a"   # page body bg

    # Sidebar
    SB_ACTIVE    = "#3b82f6"   # selected nav item bg
    SB_HOVER     = "#334155"   # hover nav item bg
    SB_TEXT      = "#94a3b8"   # inactive nav text
    SB_TEXT_ACT  = "#ffffff"   # active nav text
    SB_BORDER    = "#1e293b"   # sidebar border

    # Text
    TEXT_PRIMARY = "#f1f5f9"
    TEXT_SECOND  = "#94a3b8"
    TEXT_MUTED   = "#475569"

    # Accent
    ACCENT       = "#3b82f6"
    ACCENT_HOVER = "#2563eb"
    ACCENT_LIGHT = "#60a5fa"

    # Semantic
    SUCCESS      = "#22c55e"
    SUCCESS_BG   = "#14532d"
    WARNING      = "#f97316"
    WARNING_BG   = "#431407"
    DANGER       = "#ef4444"
    DANGER_BG    = "#450a0a"

    # Borders / separators
    BORDER       = "#334155"
    BORDER_LIGHT = "#1e293b"

    # Scrollbar
    SCROLL_HANDLE = "#334155"
    SCROLL_HOV    = "#475569"

    # Step type colors (bg, border)
    STEP_COLORS: dict[str, tuple[str, str]] = {
        "preparation":       ("#1e3a5f", "#3b82f6"),
        "reagent_addition":  ("#042f2e", "#14b8a6"),
        "mixing":            ("#2e1065", "#a855f7"),
        "incubation":        ("#431407", "#f97316"),
        "waiting":           ("#1e293b", "#475569"),
        "centrifuge":        ("#1e1b4b", "#6366f1"),
        "wash":              ("#164e63", "#06b6d4"),
        "transfer":          ("#1e1b4b", "#818cf8"),
        "pipetting":         ("#0c4a6e", "#38bdf8"),
        "resuspension":      ("#052e16", "#22c55e"),
        "staining":          ("#500724", "#f472b6"),
        "blocking":          ("#4c0519", "#fb7185"),
        "electrophoresis":   ("#3b0764", "#c084fc"),
        "gel_running":       ("#2e1065", "#a78bfa"),
        "membrane_transfer": ("#1e3a5f", "#60a5fa"),
        "imaging":           ("#064e3b", "#34d399"),
        "measurement":       ("#422006", "#fb923c"),
        "other":             ("#1e293b", "#64748b"),
    }


class Fonts:
    # On macOS, Qt uses SF Pro as the platform default — do not specify a family
    # name here; Qt's system font alias is not accessible by name in Qt6.
    # Just set size + weight; the app's default font (set in apply_theme) carries
    # the family selection.
    FAMILY    = "Helvetica Neue"   # used only in QSS; Qt resolves to system font

    SIZE_XS   = 10
    SIZE_SM   = 11
    SIZE_MD   = 13
    SIZE_LG   = 15
    SIZE_XL   = 18
    SIZE_2XL  = 22
    SIZE_3XL  = 28

    @staticmethod
    def _make(size: int, weight: QFont.Weight) -> QFont:
        # No family specified — inherits the app default font set in apply_theme()
        f = QFont()
        f.setPointSize(size)
        f.setWeight(weight)
        return f

    @staticmethod
    def regular(size: int = 13) -> QFont:
        return Fonts._make(size, QFont.Weight.Normal)

    @staticmethod
    def medium(size: int = 13) -> QFont:
        return Fonts._make(size, QFont.Weight.Medium)

    @staticmethod
    def bold(size: int = 13) -> QFont:
        return Fonts._make(size, QFont.Weight.Bold)


# ── Radii ─────────────────────────────────────────────────────────────────────

class Radii:
    XS  = 4
    SM  = 8
    MD  = 12
    LG  = 16
    XL  = 20


# ── Spacing ───────────────────────────────────────────────────────────────────

class Spacing:
    """Standard spacing/padding values (pixels)."""
    XS  = 4
    SM  = 8
    MD  = 12
    LG  = 16
    XL  = 24
    XXL = 32


# ── Global QSS ────────────────────────────────────────────────────────────────

STYLESHEET = f"""
/* ── Window / global ─────────────────────────── */
QMainWindow, QWidget#CentralWidget {{
    background-color: {Colors.BG_DARK};
}}

/* ── Sidebar ─────────────────────────────────── */
QWidget#Sidebar {{
    background-color: {Colors.BG_SIDEBAR};
    border-right: 1px solid {Colors.BORDER_LIGHT};
    border-radius: {Radii.LG}px;
}}

/* Logo area */
QLabel#SidebarTitle {{
    color: {Colors.ACCENT_LIGHT};
    font-size: {Fonts.SIZE_XL}px;
    font-weight: 700;
}}
QLabel#SidebarSubtitle {{
    color: {Colors.SB_TEXT};
    font-size: {Fonts.SIZE_SM}px;
}}

/* Nav buttons */
QPushButton#NavButton {{
    background-color: transparent;
    color: {Colors.SB_TEXT};
    text-align: left;
    padding: 0px 14px;
    border-radius: {Radii.MD}px;
    border: none;
    font-size: {Fonts.SIZE_MD}px;
    height: 42px;
}}
QPushButton#NavButton:hover {{
    background-color: {Colors.SB_HOVER};
    color: {Colors.TEXT_PRIMARY};
}}
QPushButton#NavButton[active="true"] {{
    background-color: {Colors.SB_ACTIVE};
    color: {Colors.SB_TEXT_ACT};
    font-weight: 600;
}}

/* Sidebar footer */
QLabel#SidebarFooter {{
    color: {Colors.TEXT_MUTED};
    font-size: {Fonts.SIZE_XS}px;
}}

/* ── Page container ───────────────────────────── */
QWidget#PageContainer {{
    background-color: {Colors.BG_DARK};
    border-radius: {Radii.XL}px;
    border: 1px solid {Colors.BORDER};
}}

/* ── Cards ───────────────────────────────────── */
QFrame#Card {{
    background-color: {Colors.BG_CARD};
    border-radius: {Radii.LG}px;
    border: 1px solid {Colors.BORDER};
}}
QFrame#Card:hover {{
    border: 1px solid {Colors.ACCENT};
}}

/* ── Section labels ──────────────────────────── */
QLabel#SectionTitle {{
    color: {Colors.TEXT_PRIMARY};
    font-size: {Fonts.SIZE_LG}px;
    font-weight: 700;
}}
QLabel#PageTitle {{
    color: {Colors.TEXT_PRIMARY};
    font-size: {Fonts.SIZE_2XL}px;
    font-weight: 700;
}}
QLabel#SubLabel {{
    color: {Colors.TEXT_SECOND};
    font-size: {Fonts.SIZE_SM}px;
}}
QLabel#MutedLabel {{
    color: {Colors.TEXT_MUTED};
    font-size: {Fonts.SIZE_XS}px;
}}

/* ── Buttons ─────────────────────────────────── */
QPushButton#PrimaryButton {{
    background-color: {Colors.ACCENT};
    color: #ffffff;
    border: none;
    border-radius: {Radii.MD}px;
    padding: 8px 20px;
    font-size: {Fonts.SIZE_MD}px;
    font-weight: 600;
}}
QPushButton#PrimaryButton:hover {{
    background-color: {Colors.ACCENT_HOVER};
}}
QPushButton#PrimaryButton:pressed {{
    background-color: #1d4ed8;
}}

QPushButton#SecondaryButton {{
    background-color: transparent;
    color: {Colors.TEXT_SECOND};
    border: 1px solid {Colors.BORDER};
    border-radius: {Radii.MD}px;
    padding: 8px 20px;
    font-size: {Fonts.SIZE_MD}px;
}}
QPushButton#SecondaryButton:hover {{
    background-color: {Colors.BG_CARD_HOV};
    color: {Colors.TEXT_PRIMARY};
    border-color: {Colors.ACCENT};
}}

QPushButton#DangerButton {{
    background-color: {Colors.DANGER};
    color: #ffffff;
    border: none;
    border-radius: {Radii.MD}px;
    padding: 8px 20px;
    font-size: {Fonts.SIZE_MD}px;
    font-weight: 600;
}}
QPushButton#DangerButton:hover {{
    background-color: #dc2626;
}}

QPushButton#SuccessButton {{
    background-color: {Colors.SUCCESS};
    color: #ffffff;
    border: none;
    border-radius: {Radii.MD}px;
    padding: 8px 20px;
    font-size: {Fonts.SIZE_MD}px;
    font-weight: 600;
}}
QPushButton#SuccessButton:hover {{
    background-color: #16a34a;
}}

QPushButton#IconButton {{
    background-color: transparent;
    border: none;
    border-radius: {Radii.SM}px;
    color: {Colors.TEXT_SECOND};
    padding: 4px;
}}
QPushButton#IconButton:hover {{
    background-color: {Colors.BG_CARD_HOV};
    color: {Colors.TEXT_PRIMARY};
}}

/* ── Inputs ──────────────────────────────────── */
QLineEdit, QTextEdit, QPlainTextEdit {{
    background-color: {Colors.BG_INPUT};
    color: {Colors.TEXT_PRIMARY};
    border: 1px solid {Colors.BORDER};
    border-radius: {Radii.MD}px;
    padding: 8px 12px;
    font-size: {Fonts.SIZE_MD}px;
    selection-background-color: {Colors.ACCENT};
}}
QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {{
    border-color: {Colors.ACCENT};
}}
QLineEdit:hover, QTextEdit:hover, QPlainTextEdit:hover {{
    border-color: {Colors.TEXT_MUTED};
}}

QComboBox {{
    background-color: {Colors.BG_INPUT};
    color: {Colors.TEXT_PRIMARY};
    border: 1px solid {Colors.BORDER};
    border-radius: {Radii.MD}px;
    padding: 7px 12px;
    font-size: {Fonts.SIZE_MD}px;
}}
QComboBox:focus {{ border-color: {Colors.ACCENT}; }}
QComboBox::drop-down {{
    border: none;
    width: 24px;
}}
QComboBox QAbstractItemView {{
    background-color: {Colors.BG_SIDEBAR};
    color: {Colors.TEXT_PRIMARY};
    border: 1px solid {Colors.BORDER};
    border-radius: {Radii.SM}px;
    selection-background-color: {Colors.ACCENT};
    outline: none;
}}

QSpinBox, QDoubleSpinBox {{
    background-color: {Colors.BG_INPUT};
    color: {Colors.TEXT_PRIMARY};
    border: 1px solid {Colors.BORDER};
    border-radius: {Radii.SM}px;
    padding: 6px 10px;
    font-size: {Fonts.SIZE_MD}px;
}}
QSpinBox:focus, QDoubleSpinBox:focus {{
    border-color: {Colors.ACCENT};
}}

/* ── Scrollbar ───────────────────────────────── */
QScrollBar:vertical {{
    background: transparent;
    width: 6px;
    margin: 4px 2px;
}}
QScrollBar::handle:vertical {{
    background: {Colors.SCROLL_HANDLE};
    border-radius: 3px;
    min-height: 32px;
}}
QScrollBar::handle:vertical:hover {{
    background: {Colors.SCROLL_HOV};
}}
QScrollBar::add-line:vertical,
QScrollBar::sub-line:vertical {{
    height: 0;
}}
QScrollBar:horizontal {{
    background: transparent;
    height: 6px;
    margin: 2px 4px;
}}
QScrollBar::handle:horizontal {{
    background: {Colors.SCROLL_HANDLE};
    border-radius: 3px;
    min-width: 32px;
}}
QScrollBar::handle:horizontal:hover {{
    background: {Colors.SCROLL_HOV};
}}
QScrollBar::add-line:horizontal,
QScrollBar::sub-line:horizontal {{
    width: 0;
}}

/* ── Separator ───────────────────────────────── */
QFrame#Separator {{
    background-color: {Colors.BORDER};
    max-height: 1px;
    min-height: 1px;
}}

/* ── Table / List ────────────────────────────── */
QListWidget, QListView, QTableWidget, QTreeWidget {{
    background-color: {Colors.BG_DARK};
    color: {Colors.TEXT_PRIMARY};
    border: none;
    outline: none;
    font-size: {Fonts.SIZE_MD}px;
}}
QListWidget::item, QListView::item, QTableWidget::item {{
    padding: 8px;
    border-radius: {Radii.SM}px;
}}
QListWidget::item:hover, QListView::item:hover {{
    background-color: {Colors.BG_CARD_HOV};
}}
QListWidget::item:selected, QListView::item:selected {{
    background-color: {Colors.ACCENT};
    color: #ffffff;
}}
QHeaderView::section {{
    background-color: {Colors.BG_SIDEBAR};
    color: {Colors.TEXT_SECOND};
    border: none;
    padding: 8px 12px;
    font-size: {Fonts.SIZE_SM}px;
    font-weight: 600;
}}

/* ── Tooltip ─────────────────────────────────── */
QToolTip {{
    background-color: {Colors.BG_SIDEBAR};
    color: {Colors.TEXT_PRIMARY};
    border: 1px solid {Colors.BORDER};
    border-radius: {Radii.SM}px;
    padding: 6px 10px;
    font-size: {Fonts.SIZE_SM}px;
}}

/* ── Dialogs ─────────────────────────────────── */
QDialog {{
    background-color: {Colors.BG_SIDEBAR};
    border-radius: {Radii.XL}px;
}}

/* ── Progress bar ────────────────────────────── */
QProgressBar {{
    background-color: {Colors.BORDER};
    border-radius: 4px;
    text-align: center;
    color: transparent;
    max-height: 6px;
    min-height: 6px;
}}
QProgressBar::chunk {{
    background-color: {Colors.ACCENT};
    border-radius: 4px;
}}

/* ── Checkbox ────────────────────────────────── */
QCheckBox {{
    color: {Colors.TEXT_PRIMARY};
    font-size: {Fonts.SIZE_MD}px;
    spacing: 8px;
}}
QCheckBox::indicator {{
    width: 18px;
    height: 18px;
    border: 2px solid {Colors.BORDER};
    border-radius: 5px;
    background-color: {Colors.BG_INPUT};
}}
QCheckBox::indicator:checked {{
    background-color: {Colors.ACCENT};
    border-color: {Colors.ACCENT};
}}

/* ── Tabs ────────────────────────────────────── */
QTabWidget::pane {{
    background-color: {Colors.BG_DARK};
    border: 1px solid {Colors.BORDER};
    border-radius: {Radii.MD}px;
}}
QTabBar::tab {{
    background-color: transparent;
    color: {Colors.TEXT_SECOND};
    border: none;
    padding: 8px 16px;
    font-size: {Fonts.SIZE_SM}px;
}}
QTabBar::tab:selected {{
    color: {Colors.TEXT_PRIMARY};
    border-bottom: 2px solid {Colors.ACCENT};
    font-weight: 600;
}}
QTabBar::tab:hover {{
    color: {Colors.TEXT_PRIMARY};
}}
"""


def apply_theme(app: QApplication) -> None:
    """Apply dark palette and global stylesheet to the QApplication."""
    app.setStyle("Fusion")

    palette = QPalette()
    c = Colors

    # Window & base
    palette.setColor(QPalette.ColorRole.Window,          QColor(c.BG_DARK))
    palette.setColor(QPalette.ColorRole.WindowText,      QColor(c.TEXT_PRIMARY))
    palette.setColor(QPalette.ColorRole.Base,            QColor(c.BG_INPUT))
    palette.setColor(QPalette.ColorRole.AlternateBase,   QColor(c.BG_SIDEBAR))
    palette.setColor(QPalette.ColorRole.Text,            QColor(c.TEXT_PRIMARY))
    palette.setColor(QPalette.ColorRole.BrightText,      QColor(c.TEXT_PRIMARY))

    # Buttons
    palette.setColor(QPalette.ColorRole.Button,          QColor(c.BG_CARD))
    palette.setColor(QPalette.ColorRole.ButtonText,      QColor(c.TEXT_PRIMARY))

    # Highlight / selection
    palette.setColor(QPalette.ColorRole.Highlight,       QColor(c.ACCENT))
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor("#ffffff"))

    # Borders & tooltips
    palette.setColor(QPalette.ColorRole.Light,           QColor(c.BORDER))
    palette.setColor(QPalette.ColorRole.Mid,             QColor(c.BORDER))
    palette.setColor(QPalette.ColorRole.Dark,            QColor(c.BG_DARK))
    palette.setColor(QPalette.ColorRole.Shadow,          QColor("#000000"))
    palette.setColor(QPalette.ColorRole.ToolTipBase,     QColor(c.BG_SIDEBAR))
    palette.setColor(QPalette.ColorRole.ToolTipText,     QColor(c.TEXT_PRIMARY))

    # Disabled state
    palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.WindowText,
                     QColor(c.TEXT_MUTED))
    palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.Text,
                     QColor(c.TEXT_MUTED))
    palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.ButtonText,
                     QColor(c.TEXT_MUTED))

    app.setPalette(palette)
    app.setStyleSheet(STYLESHEET)

    # Default app font — inherit platform default family, just set size
    default_font = QFont()
    default_font.setPointSize(Fonts.SIZE_MD)
    app.setFont(default_font)
