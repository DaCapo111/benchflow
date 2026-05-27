"""
RestoreSessionDialog — shown when a crash-recovery runtime_session.json is found.

Result: "resume" | "discard" | "save_notebook"
"""
from __future__ import annotations

from datetime import datetime
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget,
)

from qt_app.theme import Colors, Fonts, Radii


class RestoreSessionDialog(QDialog):
    """Three-choice modal dialog for session recovery."""

    def __init__(self, session: dict, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Interrupted Session Found")
        self.setMinimumWidth(480)
        self.setModal(True)
        self._result_action = "discard"
        self._apply_style()
        self._build(session)

    def _apply_style(self) -> None:
        self.setStyleSheet(
            f"QDialog {{ background: {Colors.BG_SIDEBAR}; border-radius: {Radii.XL}px; }}"
            f"QLabel {{ color: {Colors.TEXT_PRIMARY}; font-size: {Fonts.SIZE_MD}px; }}"
        )

    def _build(self, session: dict) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(28, 28, 28, 24)
        root.setSpacing(14)

        # Icon + title
        title = QLabel("⚠  Interrupted Session Found")
        title.setStyleSheet(
            f"color: {Colors.WARNING}; font-size: {Fonts.SIZE_LG}px; font-weight: 700;"
        )
        root.addWidget(title)

        # Session info
        proto_name = (
            session.get("protocol_snapshot", {}).get("name", "")
            or session.get("protocol_id", "Unknown")
        )
        saved_ts = session.get("saved_at_ts", 0)
        try:
            saved_str = datetime.fromtimestamp(saved_ts / 1000).strftime("%b %d, %Y  %H:%M")
        except Exception:
            saved_str = "unknown time"

        info = QLabel(
            f"Protocol: <b>{proto_name}</b><br>"
            f"Last saved: {saved_str}"
        )
        info.setTextFormat(Qt.TextFormat.RichText)
        info.setStyleSheet(
            f"color: {Colors.TEXT_SECOND}; font-size: {Fonts.SIZE_MD}px;"
            f"background: {Colors.BG_CARD}; border-radius: {Radii.MD}px; padding: 12px 14px;"
            f"border: 1px solid {Colors.BORDER};"
        )
        info.setWordWrap(True)
        root.addWidget(info)

        msg = QLabel(
            "Would you like to resume where you left off, save it to Lab Notebook, "
            "or discard the session?"
        )
        msg.setWordWrap(True)
        msg.setStyleSheet(f"color: {Colors.TEXT_SECOND}; font-size: {Fonts.SIZE_SM}px;")
        root.addWidget(msg)

        # Buttons
        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)

        resume_btn = self._make_btn("▶  Resume", Colors.SUCCESS, "#16a34a")
        resume_btn.clicked.connect(lambda: self._choose("resume"))

        notebook_btn = self._make_btn("📓  Save to Notebook", Colors.ACCENT, Colors.ACCENT_HOVER)
        notebook_btn.clicked.connect(lambda: self._choose("save_notebook"))

        discard_btn = self._make_btn("🗑  Discard", Colors.DANGER, "#dc2626")
        discard_btn.clicked.connect(lambda: self._choose("discard"))

        btn_row.addWidget(resume_btn)
        btn_row.addWidget(notebook_btn)
        btn_row.addWidget(discard_btn)
        root.addLayout(btn_row)

    @staticmethod
    def _make_btn(text: str, color: str, hover: str) -> QPushButton:
        btn = QPushButton(text)
        btn.setMinimumHeight(38)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setStyleSheet(
            f"QPushButton {{ background: {color}; color: white; border: none;"
            f"  border-radius: {Radii.MD}px; padding: 8px 14px;"
            f"  font-size: {Fonts.SIZE_SM}px; font-weight: 600; }}"
            f"QPushButton:hover {{ background: {hover}; }}"
        )
        return btn

    def _choose(self, action: str) -> None:
        self._result_action = action
        self.accept()

    def action(self) -> str:
        """Return "resume" | "discard" | "save_notebook"."""
        return self._result_action
