"""
AddBlockDialog — QDialog for inserting a temporary block into the current run.

Uses QDialog.exec() which is blocking but safe on macOS (no grab_set race).
"""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox, QDialog, QDialogButtonBox, QDoubleSpinBox,
    QFormLayout, QLabel, QLineEdit, QPlainTextEdit,
    QVBoxLayout, QWidget,
)

from qt_app.theme import Colors, Fonts, Radii

BLOCK_TYPES = [
    ("waiting",   "⏳  Waiting / Hold"),
    ("break",     "☕  Break"),
    ("task",      "✅  Task"),
    ("note",      "📝  Note"),
    ("incubation","🌡  Incubation"),
    ("other",     "⬛  Custom"),
]


class AddBlockDialog(QDialog):
    """Modal dialog to add a temporary block to the current run session."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Add Temporary Block")
        self.setMinimumWidth(420)
        self.setModal(True)
        self._apply_style()
        self._build()

    def _apply_style(self) -> None:
        self.setStyleSheet(
            f"QDialog {{"
            f"  background: {Colors.BG_CARD};"
            f"  border-radius: {Radii.XL}px;"
            f"}}"
            f"QLabel {{"
            f"  color: {Colors.TEXT_PRIMARY};"
            f"  font-size: {Fonts.SIZE_MD}px;"
            f"}}"
            f"QLineEdit, QPlainTextEdit, QComboBox, QDoubleSpinBox {{"
            f"  background: {Colors.BG_INPUT};"
            f"  color: {Colors.TEXT_PRIMARY};"
            f"  border: 1px solid {Colors.BORDER_LIGHT};"
            f"  border-radius: {Radii.MD}px;"
            f"  padding: 7px 10px;"
            f"  font-size: {Fonts.SIZE_MD}px;"
            f"}}"
            f"QLineEdit:focus, QPlainTextEdit:focus, QComboBox:focus, QDoubleSpinBox:focus {{"
            f"  border-color: {Colors.ACCENT};"
            f"}}"
            f"QComboBox::drop-down {{ border: none; width: 24px; }}"
            f"QComboBox QAbstractItemView {{"
            f"  background: {Colors.BG_CARD}; color: {Colors.TEXT_PRIMARY};"
            f"  border: 1px solid {Colors.BORDER_LIGHT}; border-radius: {Radii.MD}px;"
            f"  selection-background-color: {Colors.SELECTED_BG};"
            f"  selection-color: {Colors.TEXT_PRIMARY};"
            f"}}"
            f"QDialogButtonBox QPushButton {{"
            f"  background: {Colors.ACCENT}; color: white;"
            f"  border: none; border-radius: {Radii.LG}px;"
            f"  padding: 8px 20px; font-size: {Fonts.SIZE_MD}px; font-weight: 600;"
            f"  min-width: 80px;"
            f"}}"
            f"QDialogButtonBox QPushButton:hover {{"
            f"  background: {Colors.ACCENT_HOVER};"
            f"}}"
            f"QDialogButtonBox QPushButton[text='Cancel'] {{"
            f"  background: transparent; color: {Colors.TEXT_SECOND};"
            f"  border: 1px solid {Colors.BORDER_LIGHT};"
            f"}}"
            f"QDialogButtonBox QPushButton[text='Cancel']:hover {{"
            f"  background: {Colors.BG_CARD_HOV}; color: {Colors.TEXT_PRIMARY};"
            f"}}"
        )

    def _build(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 24, 24, 20)
        root.setSpacing(16)

        # Title
        title = QLabel("Add Temporary Block")
        title.setStyleSheet(
            f"color: {Colors.TEXT_PRIMARY}; font-size: {Fonts.SIZE_LG}px; font-weight: 700;"
        )
        root.addWidget(title)

        sub = QLabel("Insert a one-off block into the current run session.")
        sub.setStyleSheet(f"color: {Colors.TEXT_SECOND}; font-size: {Fonts.SIZE_SM}px;")
        root.addWidget(sub)

        form = QFormLayout()
        form.setSpacing(10)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        # Block title
        self._title_edit = QLineEdit()
        self._title_edit.setPlaceholderText("e.g. Lunch break, Overnight incubation…")
        form.addRow("Title:", self._title_edit)

        # Block type
        self._type_combo = QComboBox()
        for value, label in BLOCK_TYPES:
            self._type_combo.addItem(label, value)
        form.addRow("Type:", self._type_combo)

        # Duration
        self._duration_spin = QDoubleSpinBox()
        self._duration_spin.setRange(0.0, 9999.0)
        self._duration_spin.setSingleStep(5.0)
        self._duration_spin.setValue(15.0)
        self._duration_spin.setSuffix("  minutes")
        self._duration_spin.setDecimals(0)
        form.addRow("Duration:", self._duration_spin)

        # Notes
        self._notes_edit = QPlainTextEdit()
        self._notes_edit.setPlaceholderText("Optional notes…")
        self._notes_edit.setFixedHeight(72)
        form.addRow("Notes:", self._notes_edit)

        root.addLayout(form)

        # Buttons
        btns = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        root.addWidget(btns)

    # ── Result accessors ──────────────────────────────────────────────────────

    def block_title(self) -> str:
        return self._title_edit.text().strip() or "Block"

    def block_type(self) -> str:
        return self._type_combo.currentData() or "other"

    def duration_minutes(self) -> float:
        return float(self._duration_spin.value())

    def notes(self) -> str:
        return self._notes_edit.toPlainText().strip()
