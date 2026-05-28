"""
AddExperimentDialog — schedule a new experiment on a specific date/time.

Fields
------
title       : str  (pre-filled from selected protocol name)
protocol    : QComboBox  (list of user protocols + templates)
date        : QDateEdit  (default today)
start_time  : QTimeEdit  (default 09:00)
notes       : QPlainTextEdit

Result
------
Call result_data() after exec() == Accepted to get the filled values.
"""
from __future__ import annotations

from datetime import datetime, date

from PySide6.QtCore import QDate, QTime, Qt
from PySide6.QtWidgets import (
    QComboBox, QDateEdit, QDialog, QDialogButtonBox,
    QFormLayout, QHBoxLayout, QLabel, QLineEdit,
    QPlainTextEdit, QTimeEdit, QVBoxLayout, QWidget,
)

from qt_app.theme import Colors, Fonts, Radii


class AddExperimentDialog(QDialog):
    """Modal dialog for scheduling a new experiment."""

    def __init__(
        self,
        protocols: list[dict],
        templates: list[dict],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._protocols  = protocols
        self._templates  = templates
        self._all_protos = protocols + templates

        self.setWindowTitle("Schedule Experiment")
        self.setMinimumWidth(460)
        self.setStyleSheet(
            f"QDialog {{ background: {Colors.BG_CARD}; }}"
            f"QLabel {{ color: {Colors.TEXT_PRIMARY}; font-size: {Fonts.SIZE_SM}px; }}"
            f"QLineEdit, QPlainTextEdit, QComboBox, QDateEdit, QTimeEdit {{"
            f"  background: {Colors.BG_INPUT}; color: {Colors.TEXT_PRIMARY};"
            f"  border: 1px solid {Colors.BORDER_LIGHT}; border-radius: {Radii.MD}px;"
            f"  padding: 6px 10px; font-size: {Fonts.SIZE_MD}px; }}"
            f"QDateEdit::up-button, QDateEdit::down-button,"
            f"QTimeEdit::up-button, QTimeEdit::down-button {{"
            f"  width: 20px; }}"
        )
        self._build()

    # ── Build ─────────────────────────────────────────────────────────────────

    def _build(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 20)
        root.setSpacing(16)

        # Title header
        hdr = QLabel("Schedule Experiment")
        hdr.setStyleSheet(
            f"color: {Colors.TEXT_PRIMARY}; font-size: {Fonts.SIZE_LG}px; font-weight: 700;"
        )
        root.addWidget(hdr)

        # Form
        form = QFormLayout()
        form.setSpacing(10)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        # Protocol selector
        self._proto_cb = QComboBox()
        for p in self._protocols:
            name = p.get("name", "Untitled")
            steps = len(p.get("steps", []))
            self._proto_cb.addItem(f"{name}  ({steps} steps)", userData=p)
        if self._templates:
            self._proto_cb.insertSeparator(len(self._protocols))
            for t in self._templates:
                name = t.get("name", "Untitled")
                steps = len(t.get("steps", []))
                self._proto_cb.addItem(f"[template] {name}  ({steps})", userData=t)
        self._proto_cb.currentIndexChanged.connect(self._on_proto_changed)
        form.addRow("Protocol:", self._proto_cb)

        # Title
        self._title_edit = QLineEdit()
        self._title_edit.setPlaceholderText("Experiment title")
        form.addRow("Title:", self._title_edit)

        # Date
        self._date_edit = QDateEdit()
        self._date_edit.setDate(QDate.currentDate())
        self._date_edit.setCalendarPopup(True)
        self._date_edit.setDisplayFormat("yyyy-MM-dd")
        form.addRow("Date:", self._date_edit)

        # Start time
        self._time_edit = QTimeEdit()
        self._time_edit.setTime(QTime(9, 0))
        self._time_edit.setDisplayFormat("hh:mm AP")
        form.addRow("Start time:", self._time_edit)

        # Notes
        self._notes = QPlainTextEdit()
        self._notes.setPlaceholderText("Optional notes…")
        self._notes.setFixedHeight(72)
        form.addRow("Notes:", self._notes)

        root.addLayout(form)

        # Pre-fill title from first protocol
        self._on_proto_changed(0)

        # Buttons
        btns = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        btns.button(QDialogButtonBox.StandardButton.Ok).setText("Schedule Experiment")
        btns.button(QDialogButtonBox.StandardButton.Ok).setStyleSheet(
            f"QPushButton {{ background: {Colors.ACCENT}; color: white; border: none;"
            f"  border-radius: {Radii.LG}px; padding: 6px 16px;"
            f"  font-size: {Fonts.SIZE_SM}px; font-weight: 600; }}"
            f"QPushButton:hover {{ background: {Colors.ACCENT_HOVER}; }}"
        )
        btns.button(QDialogButtonBox.StandardButton.Cancel).setStyleSheet(
            f"QPushButton {{ background: transparent; color: {Colors.TEXT_SECOND};"
            f"  border: 1px solid {Colors.BORDER_LIGHT}; border-radius: {Radii.LG}px;"
            f"  padding: 6px 16px; font-size: {Fonts.SIZE_SM}px; }}"
        )
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        root.addWidget(btns)

    # ── Slots ─────────────────────────────────────────────────────────────────

    def _on_proto_changed(self, idx: int) -> None:
        proto = self._proto_cb.itemData(idx)
        if proto and isinstance(proto, dict):
            suggested = proto.get("name", "")
            if not self._title_edit.text():
                self._title_edit.setText(suggested)
            else:
                # Replace only if it was a previously auto-filled name
                self._title_edit.setText(suggested)

    # ── Result accessors ──────────────────────────────────────────────────────

    def selected_protocol(self) -> dict | None:
        return self._proto_cb.currentData()

    def title(self) -> str:
        t = self._title_edit.text().strip()
        if not t:
            proto = self.selected_protocol()
            t = (proto or {}).get("name", "Untitled") if proto else "Untitled"
        return t

    def date_str(self) -> str:
        """Return date as 'YYYY-MM-DD'."""
        return self._date_edit.date().toString("yyyy-MM-dd")

    def start_ts_ms(self) -> int:
        """Return start datetime as epoch milliseconds."""
        qdate = self._date_edit.date()
        qtime = self._time_edit.time()
        dt = datetime(qdate.year(), qdate.month(), qdate.day(),
                      qtime.hour(), qtime.minute())
        return int(dt.timestamp() * 1000)

    def notes(self) -> str:
        return self._notes.toPlainText().strip()
