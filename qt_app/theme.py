"""
BenchFlow Qt Theme
==================
Two themes: "dark" (default) and "light".

``Colors`` is a mutable class-level namespace.  ``apply_theme()`` mutates its
attributes and re-applies the QPalette + QSS to the running QApplication.
All f-strings referencing ``Colors.*`` pick up the new values whenever they
are re-evaluated (e.g. after a page rebuild or a re-call to setStyleSheet()).

Usage
-----
    from qt_app.theme import apply_theme, Colors, Fonts, current_theme

    # Startup
    apply_theme(qapp, "dark")

    # Runtime switch (emits EventBus "theme_changed" separately)
    apply_theme(qapp, "light")
    bus.emit("theme_changed", theme="light")
"""

from __future__ import annotations
from PySide6.QtGui import QColor, QPalette, QFont
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QEvent, Qt


# ── Color palettes ────────────────────────────────────────────────────────────

_DARK: dict[str, object] = {
    "BG_DARK":      "#0f172a",
    "BG_SIDEBAR":   "#1e293b",
    "BG_CARD":      "#1e293b",
    "BG_CARD_HOV":  "#263548",
    "BG_INPUT":     "#0f172a",
    "BG_PAGE":      "#0f172a",
    "BG_SURFACE_ALT": "#111827",
    "BG_ELEVATED":  "#1e293b",
    "SELECTED_BG":  "rgba(59,130,246,0.18)",
    "HOVER_BG":     "#263548",

    "SB_ACTIVE":    "#3b82f6",
    "SB_HOVER":     "#334155",
    "SB_TEXT":      "#94a3b8",
    "SB_TEXT_ACT":  "#ffffff",
    "SB_BORDER":    "#1e293b",

    "TEXT_PRIMARY": "#f1f5f9",
    "TEXT_SECOND":  "#94a3b8",
    "TEXT_MUTED":   "#475569",

    "ACCENT":       "#3b82f6",
    "ACCENT_HOVER": "#2563eb",
    "ACCENT_LIGHT": "#60a5fa",
    "ACCENT_BG":    "rgba(59,130,246,0.15)",

    "SUCCESS":      "#22c55e",
    "SUCCESS_BG":   "#14532d",
    "WARNING":      "#f97316",
    "WARNING_BG":   "#431407",
    "DANGER":       "#ef4444",
    "DANGER_BG":    "#450a0a",

    "BORDER":       "#334155",
    "BORDER_LIGHT": "#1e293b",

    "SCROLL_HANDLE": "#334155",
    "SCROLL_HOV":    "#475569",

    "STEP_COLORS": {
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
    },
}

_LIGHT: dict[str, object] = {
    "BG_DARK":      "#F6F3EE",   # app window / outer frame
    "BG_SIDEBAR":   "#F1EEE8",   # sidebar background
    "BG_CARD":      "#FFFFFF",   # card / panel surface
    "BG_CARD_HOV":  "#FFFDF9",   # card hover
    "BG_INPUT":     "#FFFFFF",   # input field
    "BG_PAGE":      "#F8F6F2",   # page body
    "BG_SURFACE_ALT": "#F4EFE7",
    "BG_ELEVATED":  "#FFFDF9",
    "SELECTED_BG":  "#EAF2FF",
    "HOVER_BG":     "#F4EFE7",

    "SB_ACTIVE":    "#EAF2FF",   # selected nav pill
    "SB_HOVER":     "#E9E3DA",   # nav hover
    "SB_TEXT":      "#6B6258",   # inactive nav text
    "SB_TEXT_ACT":  "#171717",   # active nav text
    "SB_BORDER":    "#DDD3C7",   # sidebar/border

    "TEXT_PRIMARY": "#171717",   # main text
    "TEXT_SECOND":  "#6B6258",   # secondary text
    "TEXT_MUTED":   "#9A9187",   # muted / placeholder

    "ACCENT":       "#2F6FED",
    "ACCENT_HOVER": "#255DD1",
    "ACCENT_LIGHT": "#3B73E6",
    "ACCENT_BG":    "#EAF1FF",

    "SUCCESS":      "#16A34A",   # darker green
    "SUCCESS_BG":   "#DCFCE7",   # light green background
    "WARNING":      "#D97706",   # darker amber
    "WARNING_BG":   "#FEF3C7",   # light amber background
    "DANGER":       "#DC2626",   # darker red
    "DANGER_BG":    "#FEE2E2",   # light red background

    "BORDER":       "#DDD3C7",
    "BORDER_LIGHT": "#E6DED2",

    "SCROLL_HANDLE": "#D8CEC1",
    "SCROLL_HOV":    "#B8AB9C",

    "STEP_COLORS": {
        "preparation":       ("#EBF3FF", "#3b82f6"),
        "reagent_addition":  ("#E8FAF9", "#14b8a6"),
        "mixing":            ("#F3ECFF", "#a855f7"),
        "incubation":        ("#FFF3E8", "#f97316"),
        "waiting":           ("#F1F4F8", "#475569"),
        "centrifuge":        ("#EDEDFF", "#6366f1"),
        "wash":              ("#E5F8FD", "#06b6d4"),
        "transfer":          ("#EDEDFF", "#818cf8"),
        "pipetting":         ("#E5F5FF", "#38bdf8"),
        "resuspension":      ("#EDFDF4", "#22c55e"),
        "staining":          ("#FFE9F5", "#f472b6"),
        "blocking":          ("#FFE9EC", "#fb7185"),
        "electrophoresis":   ("#F6EEFF", "#c084fc"),
        "gel_running":       ("#F1ECFF", "#a78bfa"),
        "membrane_transfer": ("#EBF3FF", "#60a5fa"),
        "imaging":           ("#E9FAF4", "#34d399"),
        "measurement":       ("#FFF4EB", "#fb923c"),
        "other":             ("#F1F4F8", "#64748b"),
    },
}


# ── Mutable Colors namespace ──────────────────────────────────────────────────

class Colors:
    """Live color namespace — class attributes mutated by apply_theme().

    All f-strings using ``Colors.*`` re-evaluate lazily; widget stylesheets
    that were already applied keep the old values until explicitly refreshed.
    """
    # Populated by _apply_palette() on first import
    BG_DARK:      str = _DARK["BG_DARK"]       # type: ignore[assignment]
    BG_SIDEBAR:   str = _DARK["BG_SIDEBAR"]    # type: ignore[assignment]
    BG_CARD:      str = _DARK["BG_CARD"]       # type: ignore[assignment]
    BG_CARD_HOV:  str = _DARK["BG_CARD_HOV"]  # type: ignore[assignment]
    BG_INPUT:     str = _DARK["BG_INPUT"]      # type: ignore[assignment]
    BG_PAGE:      str = _DARK["BG_PAGE"]       # type: ignore[assignment]
    BG_SURFACE_ALT: str = _DARK.get("BG_SURFACE_ALT", _DARK["BG_CARD_HOV"])  # type: ignore[assignment]
    BG_ELEVATED:  str = _DARK.get("BG_ELEVATED", _DARK["BG_CARD"])  # type: ignore[assignment]
    SELECTED_BG:  str = _DARK.get("SELECTED_BG", _DARK["ACCENT_BG"])  # type: ignore[assignment]
    HOVER_BG:     str = _DARK.get("HOVER_BG", _DARK["BG_CARD_HOV"])  # type: ignore[assignment]

    SB_ACTIVE:    str = _DARK["SB_ACTIVE"]     # type: ignore[assignment]
    SB_HOVER:     str = _DARK["SB_HOVER"]      # type: ignore[assignment]
    SB_TEXT:      str = _DARK["SB_TEXT"]       # type: ignore[assignment]
    SB_TEXT_ACT:  str = _DARK["SB_TEXT_ACT"]  # type: ignore[assignment]
    SB_BORDER:    str = _DARK["SB_BORDER"]     # type: ignore[assignment]

    TEXT_PRIMARY: str = _DARK["TEXT_PRIMARY"]  # type: ignore[assignment]
    TEXT_SECOND:  str = _DARK["TEXT_SECOND"]   # type: ignore[assignment]
    TEXT_MUTED:   str = _DARK["TEXT_MUTED"]    # type: ignore[assignment]

    ACCENT:       str = _DARK["ACCENT"]        # type: ignore[assignment]
    ACCENT_HOVER: str = _DARK["ACCENT_HOVER"]  # type: ignore[assignment]
    ACCENT_LIGHT: str = _DARK["ACCENT_LIGHT"]  # type: ignore[assignment]
    ACCENT_BG:    str = _DARK["ACCENT_BG"]     # type: ignore[assignment]

    SUCCESS:      str = _DARK["SUCCESS"]       # type: ignore[assignment]
    SUCCESS_BG:   str = _DARK["SUCCESS_BG"]    # type: ignore[assignment]
    WARNING:      str = _DARK["WARNING"]       # type: ignore[assignment]
    WARNING_BG:   str = _DARK["WARNING_BG"]    # type: ignore[assignment]
    DANGER:       str = _DARK["DANGER"]        # type: ignore[assignment]
    DANGER_BG:    str = _DARK["DANGER_BG"]     # type: ignore[assignment]

    BORDER:       str = _DARK["BORDER"]        # type: ignore[assignment]
    BORDER_LIGHT: str = _DARK["BORDER_LIGHT"]  # type: ignore[assignment]

    SCROLL_HANDLE: str = _DARK["SCROLL_HANDLE"]  # type: ignore[assignment]
    SCROLL_HOV:    str = _DARK["SCROLL_HOV"]     # type: ignore[assignment]

    STEP_COLORS: dict[str, tuple[str, str]] = _DARK["STEP_COLORS"]  # type: ignore[assignment]


# ── Fonts ─────────────────────────────────────────────────────────────────────

class Fonts:
    FAMILY  = "Helvetica Neue"
    SIZE_XS = 10
    SIZE_SM = 11
    SIZE_MD = 13
    SIZE_LG = 15
    SIZE_XL = 18
    SIZE_2XL = 22
    SIZE_3XL = 28

    @staticmethod
    def _make(size: int, weight: QFont.Weight) -> QFont:
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


# ── Radii / Spacing ───────────────────────────────────────────────────────────

class Radii:
    XS = 4; SM = 8; MD = 12; LG = 16; XL = 20

class Spacing:
    XS = 4; SM = 8; MD = 12; LG = 16; XL = 24; XXL = 32


# ── Private helpers ───────────────────────────────────────────────────────────

_CURRENT_THEME: str = "dark"


def _apply_palette(name: str) -> None:
    """Mutate ``Colors`` class attributes from the chosen palette dict."""
    src = _LIGHT if name == "light" else _DARK
    for key, val in src.items():
        setattr(Colors, key, val)


def _build_stylesheet() -> str:
    """Generate the global QSS string using current Colors values."""
    c = Colors
    r = Radii
    f = Fonts
    return f"""
/* ── Window / global ─────────────────────────── */
QMainWindow, QWidget#CentralWidget {{
    background-color: {c.BG_DARK};
}}

/* ── Sidebar ─────────────────────────────────── */
QWidget#Sidebar {{
    background-color: {c.BG_SIDEBAR};
    border-right: 1px solid {c.SB_BORDER};
    border-radius: {r.XL}px;
}}
QLabel#SidebarTitle {{
    color: {c.TEXT_PRIMARY};
    font-size: {f.SIZE_XL}px;
    font-weight: 700;
}}
QLabel#SidebarSubtitle {{
    color: {c.SB_TEXT};
    font-size: {f.SIZE_SM}px;
}}
QPushButton#NavButton {{
    background-color: transparent;
    color: {c.SB_TEXT};
    text-align: left;
    padding: 0px 14px;
    border-radius: {r.MD}px;
    border: none;
    font-size: {f.SIZE_MD}px;
    height: 40px;
}}
QPushButton#NavButton:hover {{
    background-color: {c.SB_HOVER};
    color: {c.TEXT_PRIMARY};
}}
QPushButton#NavButton[active="true"] {{
    background-color: {c.SB_ACTIVE};
    color: {c.SB_TEXT_ACT};
    font-weight: 700;
    border-left: 3px solid {c.ACCENT};
}}
QLabel#SidebarFooter {{
    color: {c.TEXT_MUTED};
    font-size: {f.SIZE_XS}px;
}}

/* ── Page container ───────────────────────────── */
QWidget#PageContainer {{
    background-color: {c.BG_PAGE};
    border-radius: {r.LG}px;
    border: 1px solid {c.BORDER_LIGHT};
}}

/* ── Cards ───────────────────────────────────── */
QFrame#Card {{
    background-color: {c.BG_ELEVATED};
    border-radius: {r.MD}px;
    border: 1px solid {c.BORDER_LIGHT};
}}
QFrame#Card:hover {{
    background-color: {c.BG_CARD_HOV};
    border: 1px solid {c.BORDER_LIGHT};
}}

/* ── Labels ──────────────────────────────────── */
QLabel#SectionTitle {{
    color: {c.TEXT_PRIMARY};
    font-size: {f.SIZE_XL}px;
    font-weight: 700;
}}
QLabel#PageTitle {{
    color: {c.TEXT_PRIMARY};
    font-size: {f.SIZE_3XL}px;
    font-weight: 750;
}}
QLabel#SubLabel {{
    color: {c.TEXT_SECOND};
    font-size: {f.SIZE_MD}px;
}}
QLabel#MutedLabel {{
    color: {c.TEXT_MUTED};
    font-size: {f.SIZE_XS}px;
}}

/* ── Buttons ─────────────────────────────────── */
QPushButton#PrimaryButton {{
    background-color: {c.ACCENT};
    color: #ffffff;
    border: none;
    border-radius: {r.LG}px;
    padding: 8px 20px;
    font-size: {f.SIZE_MD}px;
    font-weight: 600;
}}
QPushButton#PrimaryButton:hover {{ background-color: {c.ACCENT_HOVER}; }}
QPushButton#PrimaryButton:pressed {{ background-color: {c.ACCENT_HOVER}; }}

QPushButton#SecondaryButton {{
    background-color: {c.BG_CARD};
    color: {c.TEXT_PRIMARY};
    border: 1px solid {c.BORDER_LIGHT};
    border-radius: {r.LG}px;
    padding: 8px 20px;
    font-size: {f.SIZE_MD}px;
}}
QPushButton#SecondaryButton:hover {{
    background-color: {c.BG_CARD_HOV};
    color: {c.TEXT_PRIMARY};
    border-color: {c.BORDER};
}}

QPushButton#DangerButton {{
    background-color: {c.DANGER};
    color: #ffffff;
    border: none;
    border-radius: {r.MD}px;
    padding: 8px 20px;
    font-size: {f.SIZE_MD}px;
    font-weight: 600;
}}
QPushButton#DangerButton:hover {{ background-color: {c.DANGER}; opacity: 0.9; }}

QPushButton#SuccessButton {{
    background-color: {c.SUCCESS};
    color: #ffffff;
    border: none;
    border-radius: {r.MD}px;
    padding: 8px 20px;
    font-size: {f.SIZE_MD}px;
    font-weight: 600;
}}

QPushButton#IconButton {{
    background-color: transparent;
    border: none;
    border-radius: {r.SM}px;
    color: {c.TEXT_SECOND};
    padding: 4px;
}}
QPushButton#IconButton:hover {{
    background-color: {c.BG_CARD_HOV};
    color: {c.TEXT_PRIMARY};
}}

/* ── Inputs ──────────────────────────────────── */
QLineEdit, QTextEdit, QPlainTextEdit {{
    background-color: {c.BG_INPUT};
    color: {c.TEXT_PRIMARY};
    border: 1px solid {c.BORDER_LIGHT};
    border-radius: {r.MD}px;
    padding: 8px 12px;
    font-size: {f.SIZE_MD}px;
    selection-background-color: {c.ACCENT};
}}
QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {{
    border-color: {c.ACCENT};
}}
QLineEdit:hover, QTextEdit:hover, QPlainTextEdit:hover {{
    border-color: {c.BORDER};
}}

QComboBox {{
    background-color: {c.BG_INPUT};
    color: {c.TEXT_PRIMARY};
    border: 1px solid {c.BORDER_LIGHT};
    border-radius: {r.MD}px;
    padding: 7px 12px;
    font-size: {f.SIZE_MD}px;
}}
QComboBox:focus {{ border-color: {c.ACCENT}; }}
QComboBox::drop-down {{ border: none; width: 24px; }}
QComboBox QAbstractItemView {{
    background-color: {c.BG_CARD};
    color: {c.TEXT_PRIMARY};
    border: 1px solid {c.BORDER};
    border-radius: {r.SM}px;
    selection-background-color: {c.SELECTED_BG};
    selection-color: {c.TEXT_PRIMARY};
    outline: none;
}}

QSpinBox, QDoubleSpinBox {{
    background-color: {c.BG_INPUT};
    color: {c.TEXT_PRIMARY};
    border: 1px solid {c.BORDER};
    border-radius: {r.SM}px;
    padding: 6px 10px;
    font-size: {f.SIZE_MD}px;
}}
QSpinBox:focus, QDoubleSpinBox:focus {{ border-color: {c.ACCENT}; }}

/* ── Scrollbar ───────────────────────────────── */
QScrollBar:vertical {{
    background: transparent;
    width: 6px;
    margin: 4px 2px;
}}
QScrollBar::handle:vertical {{
    background: {c.SCROLL_HANDLE};
    border-radius: 3px;
    min-height: 32px;
}}
QScrollBar::handle:vertical:hover {{ background: {c.SCROLL_HOV}; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
QScrollBar:horizontal {{
    background: transparent;
    height: 6px;
    margin: 2px 4px;
}}
QScrollBar::handle:horizontal {{
    background: {c.SCROLL_HANDLE};
    border-radius: 3px;
    min-width: 32px;
}}
QScrollBar::handle:horizontal:hover {{ background: {c.SCROLL_HOV}; }}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{ width: 0; }}

/* ── Separator ───────────────────────────────── */
QFrame#Separator {{
    background-color: {c.BORDER_LIGHT};
    max-height: 1px;
    min-height: 1px;
}}

/* ── Table / List ────────────────────────────── */
QListWidget, QListView, QTableWidget, QTreeWidget {{
    background-color: {c.BG_PAGE};
    color: {c.TEXT_PRIMARY};
    border: none;
    outline: none;
    font-size: {f.SIZE_MD}px;
}}
QListWidget::item, QListView::item, QTableWidget::item {{
    padding: 8px;
    border-radius: {r.SM}px;
}}
QListWidget::item:hover, QListView::item:hover {{ background-color: {c.BG_CARD_HOV}; }}
QListWidget::item:selected, QListView::item:selected {{
    background-color: {c.SELECTED_BG};
    color: {c.TEXT_PRIMARY};
}}
QHeaderView::section {{
    background-color: {c.BG_SIDEBAR};
    color: {c.TEXT_SECOND};
    border: none;
    padding: 8px 12px;
    font-size: {f.SIZE_SM}px;
    font-weight: 600;
}}

/* ── Tooltip ─────────────────────────────────── */
QToolTip {{
    background-color: {c.BG_SIDEBAR};
    color: {c.TEXT_PRIMARY};
    border: 1px solid {c.BORDER};
    border-radius: {r.SM}px;
    padding: 6px 10px;
    font-size: {f.SIZE_SM}px;
}}

/* ── Dialogs ─────────────────────────────────── */
QDialog {{
    background-color: {c.BG_CARD};
    border-radius: {r.XL}px;
}}

/* ── Progress bar ────────────────────────────── */
QProgressBar {{
    background-color: {c.BORDER_LIGHT};
    border-radius: 4px;
    text-align: center;
    color: transparent;
    max-height: 6px;
    min-height: 6px;
}}
QProgressBar::chunk {{
    background-color: {c.ACCENT};
    border-radius: 4px;
}}

/* ── Checkbox ────────────────────────────────── */
QCheckBox {{
    color: {c.TEXT_PRIMARY};
    font-size: {f.SIZE_MD}px;
    spacing: 8px;
}}
QCheckBox::indicator {{
    width: 18px;
    height: 18px;
    border: 2px solid {c.BORDER};
    border-radius: 5px;
    background-color: {c.BG_INPUT};
}}
QCheckBox::indicator:checked {{
    background-color: {c.ACCENT};
    border-color: {c.ACCENT};
}}

/* ── Tabs ────────────────────────────────────── */
QTabWidget::pane {{
    background-color: {c.BG_PAGE};
    border: 1px solid {c.BORDER};
    border-radius: {r.MD}px;
}}
QTabBar::tab {{
    background-color: transparent;
    color: {c.TEXT_SECOND};
    border: none;
    padding: 8px 16px;
    font-size: {f.SIZE_SM}px;
}}
QTabBar::tab:selected {{
    color: {c.TEXT_PRIMARY};
    border-bottom: 2px solid {c.ACCENT};
    font-weight: 600;
}}
QTabBar::tab:hover {{ color: {c.TEXT_PRIMARY}; }}

/* ── Message boxes ───────────────────────────── */
QMessageBox {{
    background-color: {c.BG_SIDEBAR};
}}
QMessageBox QLabel {{
    color: {c.TEXT_PRIMARY};
}}
QMessageBox QPushButton {{
    background-color: {c.BG_CARD};
    color: {c.TEXT_PRIMARY};
    border: 1px solid {c.BORDER};
    border-radius: {r.SM}px;
    padding: 6px 16px;
    min-width: 64px;
}}
QMessageBox QPushButton:hover {{
    background-color: {c.BG_CARD_HOV};
    border-color: {c.ACCENT};
}}
"""


def _build_palette() -> QPalette:
    """Build QPalette from current Colors values."""
    c = Colors
    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window,          QColor(c.BG_PAGE))
    palette.setColor(QPalette.ColorRole.WindowText,      QColor(c.TEXT_PRIMARY))
    palette.setColor(QPalette.ColorRole.Base,            QColor(c.BG_INPUT))
    palette.setColor(QPalette.ColorRole.AlternateBase,   QColor(c.BG_SIDEBAR))
    palette.setColor(QPalette.ColorRole.Text,            QColor(c.TEXT_PRIMARY))
    palette.setColor(QPalette.ColorRole.BrightText,      QColor(c.TEXT_PRIMARY))
    palette.setColor(QPalette.ColorRole.Button,          QColor(c.BG_CARD))
    palette.setColor(QPalette.ColorRole.ButtonText,      QColor(c.TEXT_PRIMARY))
    palette.setColor(QPalette.ColorRole.Highlight,       QColor(c.ACCENT))
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor("#ffffff"))
    palette.setColor(QPalette.ColorRole.Light,           QColor(c.BORDER))
    palette.setColor(QPalette.ColorRole.Mid,             QColor(c.BORDER))
    palette.setColor(QPalette.ColorRole.Dark,            QColor(c.BG_DARK))
    palette.setColor(QPalette.ColorRole.Shadow,          QColor("#000000"))
    palette.setColor(QPalette.ColorRole.ToolTipBase,     QColor(c.BG_SIDEBAR))
    palette.setColor(QPalette.ColorRole.ToolTipText,     QColor(c.TEXT_PRIMARY))
    palette.setColor(QPalette.ColorGroup.Disabled,
                     QPalette.ColorRole.WindowText, QColor(c.TEXT_MUTED))
    palette.setColor(QPalette.ColorGroup.Disabled,
                     QPalette.ColorRole.Text,       QColor(c.TEXT_MUTED))
    palette.setColor(QPalette.ColorGroup.Disabled,
                     QPalette.ColorRole.ButtonText, QColor(c.TEXT_MUTED))
    return palette


# ── Public API ────────────────────────────────────────────────────────────────

def current_theme() -> str:
    """Return the currently active theme name ("dark" or "light")."""
    return _CURRENT_THEME


def apply_theme(app: QApplication | None = None, name: str = "dark") -> None:
    """Apply *name* theme to *app*.

    Mutates ``Colors`` class attributes so any subsequent f-string using
    ``Colors.*`` reflects the new palette.  Then re-applies QPalette and
    global QSS to *app* (if provided).
    """
    global _CURRENT_THEME
    _CURRENT_THEME = name

    _apply_palette(name)

    if app is not None:
        app.setStyle("Fusion")
        app.setPalette(_build_palette())
        app.setStyleSheet(_build_stylesheet())

        default_font = QFont()
        default_font.setPointSize(Fonts.SIZE_MD)
        app.setFont(default_font)

        for widget in app.allWidgets():
            widget.setPalette(app.palette())
            widget.style().unpolish(widget)
            widget.style().polish(widget)
            widget.update()
            app.sendEvent(widget, QEvent(QEvent.Type.StyleChange))


# ── Backwards-compat alias (old STYLESHEET constant) ─────────────────────────
# Code that does `from qt_app.theme import STYLESHEET` still works.
STYLESHEET = _build_stylesheet()
