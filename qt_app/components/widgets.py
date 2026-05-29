"""
Reusable themed widgets for BenchFlow Qt UI.

All widgets set their Qt objectName so QSS selectors like
QPushButton#PrimaryButton work without extra style calls.
"""
from __future__ import annotations

from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QFont, QColor
from PySide6.QtWidgets import (
    QFrame, QLabel, QPushButton, QScrollArea, QSizePolicy,
    QGraphicsDropShadowEffect,
    QWidget, QVBoxLayout,
)

from qt_app.theme import Colors, Fonts, Radii


# ── Separator ─────────────────────────────────────────────────────────────────

class HSeparator(QFrame):
    """1 px horizontal separator line."""
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("Separator")
        self.setFrameShape(QFrame.Shape.HLine)
        self.setFrameShadow(QFrame.Shadow.Plain)
        self.setFixedHeight(1)
        self.setStyleSheet(f"background-color: {Colors.BORDER_LIGHT};")


# ── Labels ────────────────────────────────────────────────────────────────────

class _ThemedLabel(QLabel):
    def __init__(self, text: str = "", object_name: str = "",
                 color: str = Colors.TEXT_PRIMARY,
                 font: QFont | None = None,
                 parent: QWidget | None = None) -> None:
        super().__init__(text, parent)
        if object_name:
            self.setObjectName(object_name)
        if font:
            self.setFont(font)
        self.setStyleSheet(f"color: {color};")


class PageTitle(_ThemedLabel):
    def __init__(self, text: str = "", parent: QWidget | None = None) -> None:
        super().__init__(text, "PageTitle", Colors.TEXT_PRIMARY,
                         Fonts.bold(Fonts.SIZE_2XL), parent)


class SectionTitle(_ThemedLabel):
    def __init__(self, text: str = "", parent: QWidget | None = None) -> None:
        super().__init__(text, "SectionTitle", Colors.TEXT_PRIMARY,
                         Fonts.bold(Fonts.SIZE_LG), parent)


class SubLabel(_ThemedLabel):
    def __init__(self, text: str = "", parent: QWidget | None = None) -> None:
        super().__init__(text, "SubLabel", Colors.TEXT_SECOND,
                         Fonts.regular(Fonts.SIZE_SM), parent)


class MutedLabel(_ThemedLabel):
    def __init__(self, text: str = "", parent: QWidget | None = None) -> None:
        super().__init__(text, "MutedLabel", Colors.TEXT_MUTED,
                         Fonts.regular(Fonts.SIZE_XS), parent)


# ── Buttons ───────────────────────────────────────────────────────────────────

class _ThemedButton(QPushButton):
    _OBJECT_NAME = ""
    _MIN_HEIGHT = 36

    def __init__(self, text: str = "", icon_text: str = "",
                 parent: QWidget | None = None) -> None:
        label = f"{icon_text}  {text}" if icon_text else text
        super().__init__(label, parent)
        if self._OBJECT_NAME:
            self.setObjectName(self._OBJECT_NAME)
        self.setMinimumHeight(self._MIN_HEIGHT)
        self.setCursor(Qt.CursorShape.PointingHandCursor)


class PrimaryButton(_ThemedButton):
    _OBJECT_NAME = "PrimaryButton"


class SecondaryButton(_ThemedButton):
    _OBJECT_NAME = "SecondaryButton"


class DangerButton(_ThemedButton):
    _OBJECT_NAME = "DangerButton"


class SuccessButton(_ThemedButton):
    _OBJECT_NAME = "SuccessButton"


class IconButton(QPushButton):
    """Compact square button for toolbar icons / inline actions."""
    def __init__(self, text: str = "", size: int = 32,
                 parent: QWidget | None = None) -> None:
        super().__init__(text, parent)
        self.setObjectName("IconButton")
        self.setFixedSize(QSize(size, size))
        self.setCursor(Qt.CursorShape.PointingHandCursor)


# ── Card ─────────────────────────────────────────────────────────────────────

def apply_card_shadow(frame: QFrame, *, blur: int = 26,
                      y_offset: int = 8, alpha: int = 31) -> None:
    """Apply BenchFlow's warm light-theme card elevation."""
    frame.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
    frame.setAutoFillBackground(False)
    shadow = QGraphicsDropShadowEffect(frame)
    shadow.setBlurRadius(blur)
    shadow.setOffset(0, y_offset)
    shadow.setColor(QColor(80, 60, 40, alpha))
    frame.setGraphicsEffect(shadow)


class Card(QFrame):
    """Rounded themed card container."""
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("Card")
        apply_card_shadow(self)


# ── ScrollArea ────────────────────────────────────────────────────────────────

class ScrollArea(QScrollArea):
    """Frameless scroll area with inner QWidget for adding child widgets."""
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        self._inner = QWidget()
        self._inner.setObjectName("ScrollInner")
        self._inner.setStyleSheet(f"background: transparent;")
        self._layout = QVBoxLayout(self._inner)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(0)
        self.setWidget(self._inner)

    @property
    def inner(self) -> QWidget:
        return self._inner

    @property
    def inner_layout(self) -> QVBoxLayout:
        return self._layout


# ── Badge ─────────────────────────────────────────────────────────────────────

class Badge(QLabel):
    """Small colored pill label (for step types, status, etc.)."""
    def __init__(self, text: str = "", bg: str = Colors.BG_CARD,
                 fg: str = Colors.TEXT_SECOND,
                 parent: QWidget | None = None) -> None:
        super().__init__(text, parent)
        self.setObjectName("Badge")
        self._bg = bg
        self._fg = fg
        self._apply_style()

    def set_colors(self, bg: str, fg: str = Colors.TEXT_PRIMARY) -> None:
        self._bg = bg
        self._fg = fg
        self._apply_style()

    def _apply_style(self) -> None:
        self.setStyleSheet(
            f"background-color: {self._bg};"
            f"color: {self._fg};"
            f"border-radius: {Radii.SM}px;"
            f"padding: 2px 8px;"
            f"font-size: {Fonts.SIZE_XS}px;"
            f"font-weight: 600;"
        )
