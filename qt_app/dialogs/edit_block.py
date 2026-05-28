"""
EditBlockDialog — add or edit a timeline block in a scheduled experiment.

Used for both:
- Adding a new break/task/note/custom block
- Editing an existing block's title, type, duration, notes

Pass block=None for "Add" mode; pass an existing TimelineBlock for "Edit" mode.
"""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox, QDialog, QDialogButtonBox, QDoubleSpinBox,
    QFormLayout, QLabel, QLineEdit, QPlainTextEdit, QVBoxLayout, QWidget,
)

from qt_app.theme import Colors, Fonts, Radii
from qt_app.models.schedule_experiment import TimelineBlock, TIMELINE_BLOCK_TYPES


class EditBlockDialog(QDialog):
    """Modal dialog for adding or editing a timeline block."""

    def __init__(
        self,
        block: TimelineBlock | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._block = block
        self._is_edit = block is not None

        title = "Edit Block" if self._is_edit else "Add Block"
        self.setWindowTitle(title)
        self.setMinimumWidth(400)
        self.setStyleSheet(
            f"QDialog {{ background: {Colors.BG_SIDEBAR}; }}"
            f"QLabel {{ color: {Colors.TEXT_PRIMARY}; font-size: {Fonts.SIZE_SM}px; }}"
            f"QLineEdit, QPlainTextEdit, QComboBox, QDoubleSpinBox {{"
            f"  background: {Colors.BG_INPUT}; color: {Colors.TEXT_PRIMARY};"
            f"  border: 1px solid {Colors.BORDER}; border-radius: {Radii.SM}px;"
            f"  padding: 6px 10px; font-size: {Fonts.SIZE_MD}px; }}"
        )
        self._build()

    # ── Build ─────────────────────────────────────────────────────────────────

    def _build(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 20)
        root.setSpacing(14)

        hdr = QLabel("Edit Block" if self._is_edit else "Add Block")
        hdr.setStyleSheet(
            f"color: {Colors.TEXT_PRIMARY}; font-size: {Fonts.SIZE_LG}px; font-weight: 700;"
        )
        root.addWidget(hdr)

        form = QFormLayout()
        form.setSpacing(10)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        # Title
        self._title = QLineEdit()
        self._title.setPlaceholderText("Block title")
        if self._block:
            self._title.setText(self._block.title)
        form.addRow("Title:", self._title)

        # Type
        self._type_cb = QComboBox()
        # For new blocks, show only non-protocol-step types
        if self._is_edit and self._block:
            current_type = self._block.type
            for t in TIMELINE_BLOCK_TYPES:
                self._type_cb.addItem(t.replace("_", " ").title(), userData=t)
            idx = self._type_cb.findData(current_type)
            if idx >= 0:
                self._type_cb.setCurrentIndex(idx)
        else:
            for t in ("break", "task", "note", "decision", "custom"):
                self._type_cb.addItem(t.replace("_", " ").title(), userData=t)
        form.addRow("Type:", self._type_cb)

        # Duration
        self._duration = QDoubleSpinBox()
        self._duration.setRange(1.0, 600.0)
        self._duration.setDecimals(1)
        self._duration.setSuffix(" min")
        self._duration.setValue(
            self._block.duration_minutes if self._block else 15.0
        )
        form.addRow("Duration:", self._duration)

        # Notes
        self._notes = QPlainTextEdit()
        self._notes.setPlaceholderText("Notes…")
        self._notes.setFixedHeight(64)
        if self._block:
            self._notes.setPlainText(self._block.notes)
        form.addRow("Notes:", self._notes)

        root.addLayout(form)

        # Buttons
        btn_label = "Save" if self._is_edit else "Add Block"
        btns = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        btns.button(QDialogButtonBox.StandardButton.Ok).setText(btn_label)
        btns.button(QDialogButtonBox.StandardButton.Ok).setStyleSheet(
            f"QPushButton {{ background: {Colors.ACCENT}; color: white; border: none;"
            f"  border-radius: {Radii.SM}px; padding: 6px 16px;"
            f"  font-size: {Fonts.SIZE_SM}px; font-weight: 600; }}"
            f"QPushButton:hover {{ background: {Colors.ACCENT_HOVER}; }}"
        )
        btns.button(QDialogButtonBox.StandardButton.Cancel).setStyleSheet(
            f"QPushButton {{ background: transparent; color: {Colors.TEXT_SECOND};"
            f"  border: 1px solid {Colors.BORDER}; border-radius: {Radii.SM}px;"
            f"  padding: 6px 16px; font-size: {Fonts.SIZE_SM}px; }}"
        )
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        root.addWidget(btns)

    # ── Result accessors ──────────────────────────────────────────────────────

    def result_title(self) -> str:
        return self._title.text().strip() or "Untitled"

    def result_type(self) -> str:
        return self._type_cb.currentData() or "task"

    def result_duration(self) -> float:
        return self._duration.value()

    def result_notes(self) -> str:
        return self._notes.toPlainText().strip()
