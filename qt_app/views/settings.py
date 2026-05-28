"""
Settings Page — Phase 9.

Layout
------
SettingsPage
├── Header: "Settings" title + subtitle
├── HSeparator
└── QScrollArea (full width)
    └── Content (two-column feel via cards)
        ├── Section: App Info
        │   ├── Version, data folder path, Open Data Folder
        │   └── GitHub repo link
        ├── Section: Preferences
        │   ├── Theme (placeholder — future)
        │   ├── Autosave interval
        │   └── Session recovery
        ├── Section: Dependencies
        │   ├── reportlab status
        │   └── python-docx status
        ├── Section: Session
        │   └── Reset active run session
        └── Section: Backup & Restore
            ├── Backup all data → .zip
            └── Restore from backup .zip
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QFileDialog, QFrame, QHBoxLayout, QLabel,
    QMessageBox, QPushButton, QScrollArea,
    QSizePolicy, QSpinBox, QVBoxLayout, QWidget,
)

from qt_app.theme import Colors, Fonts, Radii
from qt_app.components.widgets import (
    HSeparator, PageTitle, PrimaryButton, SubLabel,
)
from qt_app.components.toast import ToastManager
from qt_app.services.data import APP_DIR, _APP_VERSION
from qt_app.views.base_page import BasePage


# ── Helpers ───────────────────────────────────────────────────────────────────

def _lbl(text: str, color: str = Colors.TEXT_PRIMARY,
         size: int = Fonts.SIZE_SM, bold: bool = False,
         wrap: bool = False) -> QLabel:
    lbl = QLabel(text)
    weight = "700" if bold else "400"
    lbl.setStyleSheet(
        f"color: {color}; font-size: {size}px; font-weight: {weight};"
    )
    if wrap:
        lbl.setWordWrap(True)
    return lbl


def _section_header(title: str) -> QLabel:
    lbl = QLabel(title.upper())
    lbl.setStyleSheet(
        f"color: {Colors.TEXT_MUTED}; font-size: {Fonts.SIZE_XS}px;"
        f"font-weight: 700; letter-spacing: 1px;"
    )
    return lbl


def _card() -> QFrame:
    """Styled card container for a settings section."""
    card = QFrame()
    card.setStyleSheet(
        f"QFrame {{ background: {Colors.BG_CARD}; border-radius: {Radii.LG}px;"
        f"  border: 1px solid {Colors.BORDER}; }}"
    )
    return card


def _row_style() -> str:
    return (
        f"QFrame {{ background: transparent; border: none; }}"
        f"QFrame + QFrame {{ border-top: 1px solid {Colors.BORDER}; }}"
    )


def _dep_badge(ok: bool) -> QLabel:
    if ok:
        lbl = QLabel("✓  Installed")
        lbl.setStyleSheet(
            f"color: {Colors.SUCCESS}; background: {Colors.SUCCESS_BG};"
            f"border-radius: 6px; padding: 2px 10px;"
            f"font-size: {Fonts.SIZE_XS}px; font-weight: 600;"
        )
    else:
        lbl = QLabel("✗  Missing")
        lbl.setStyleSheet(
            f"color: {Colors.DANGER}; background: {Colors.DANGER_BG};"
            f"border-radius: 6px; padding: 2px 10px;"
            f"font-size: {Fonts.SIZE_XS}px; font-weight: 600;"
        )
    return lbl


def _action_btn(label: str, color: str = Colors.TEXT_SECOND,
                danger: bool = False) -> QPushButton:
    btn = QPushButton(label)
    btn.setFixedHeight(32)
    btn.setCursor(Qt.CursorShape.PointingHandCursor)
    if danger:
        btn.setStyleSheet(
            f"QPushButton {{ background: transparent; color: {Colors.DANGER};"
            f"  border: 1px solid {Colors.DANGER}; border-radius: {Radii.SM}px;"
            f"  font-size: {Fonts.SIZE_SM}px; padding: 0 12px; }}"
            f"QPushButton:hover {{ background: {Colors.DANGER_BG}; }}"
        )
    else:
        btn.setStyleSheet(
            f"QPushButton {{ background: transparent; color: {color};"
            f"  border: 1px solid {Colors.BORDER}; border-radius: {Radii.SM}px;"
            f"  font-size: {Fonts.SIZE_SM}px; padding: 0 12px; }}"
            f"QPushButton:hover {{ background: {Colors.BG_CARD_HOV}; }}"
        )
    return btn


def _check_dep(module: str) -> bool:
    """Return True if *module* can be imported."""
    import importlib.util
    return importlib.util.find_spec(module) is not None


# ── Card builders ─────────────────────────────────────────────────────────────

def _build_row(key: str, value_widget: QWidget,
               note: str = "") -> QWidget:
    """Single key–value row inside a card."""
    row = QWidget()
    row.setStyleSheet("background: transparent;")
    lay = QHBoxLayout(row)
    lay.setContentsMargins(16, 10, 16, 10)
    lay.setSpacing(12)

    k_lbl = _lbl(key, Colors.TEXT_SECOND, Fonts.SIZE_SM)
    k_lbl.setMinimumWidth(160)
    lay.addWidget(k_lbl)
    lay.addWidget(value_widget, stretch=1)
    if note:
        n_lbl = _lbl(note, Colors.TEXT_MUTED, Fonts.SIZE_XS)
        lay.addWidget(n_lbl)
    return row


def _build_action_row(description: str, btn: QPushButton,
                      note: str = "") -> QWidget:
    """Row with descriptive text on left and action button on right."""
    row = QWidget()
    row.setStyleSheet("background: transparent;")
    lay = QHBoxLayout(row)
    lay.setContentsMargins(16, 10, 16, 10)
    lay.setSpacing(12)

    desc_lbl = _lbl(description, Colors.TEXT_SECOND, Fonts.SIZE_SM, wrap=True)
    desc_lbl.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
    lay.addWidget(desc_lbl, stretch=1)
    if note:
        n_lbl = _lbl(note, Colors.TEXT_MUTED, Fonts.SIZE_XS)
        lay.addWidget(n_lbl)
    lay.addWidget(btn)
    return row


def _card_with_rows(rows: list[QWidget]) -> QFrame:
    card = _card()
    lay = QVBoxLayout(card)
    lay.setContentsMargins(0, 0, 0, 0)
    lay.setSpacing(0)
    for i, row in enumerate(rows):
        if i > 0:
            lay.addWidget(HSeparator())
        lay.addWidget(row)
    return card


# ── Main page ─────────────────────────────────────────────────────────────────

class SettingsPage(BasePage):
    """Settings page — Phase 9."""

    def __init__(self, app: "BenchFlowApp", parent: "QWidget | None" = None) -> None:  # type: ignore[name-defined]
        super().__init__(app, parent)
        self._autosave_spin: QSpinBox | None = None
        self._build()

    def _build(self) -> None:
        outer = QVBoxLayout()
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # ── Header ────────────────────────────────────────────────────────────
        hdr = QWidget()
        hdr.setStyleSheet(f"background: {Colors.BG_PAGE};")
        hdr_lay = QHBoxLayout(hdr)
        hdr_lay.setContentsMargins(28, 20, 28, 16)
        hdr_lay.setSpacing(8)
        col = QVBoxLayout()
        col.setSpacing(2)
        col.addWidget(PageTitle("Settings"))
        col.addWidget(SubLabel("App preferences, dependencies, backup & restore."))
        hdr_lay.addLayout(col)
        hdr_lay.addStretch()
        outer.addWidget(hdr)
        outer.addWidget(HSeparator())

        # ── Scroll area ───────────────────────────────────────────────────────
        scroll = QScrollArea()
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet(f"background: {Colors.BG_PAGE};")
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        content = QWidget()
        content.setStyleSheet(f"background: {Colors.BG_PAGE};")
        content_lay = QVBoxLayout(content)
        content_lay.setContentsMargins(28, 20, 28, 40)
        content_lay.setSpacing(24)

        # ── Section: App Info ─────────────────────────────────────────────────
        content_lay.addWidget(_section_header("App Info"))

        data_path_lbl = QLabel(str(APP_DIR))
        data_path_lbl.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
        data_path_lbl.setStyleSheet(
            f"color: {Colors.TEXT_PRIMARY}; font-size: {Fonts.SIZE_SM}px;"
            f"font-family: monospace;"
        )

        open_folder_btn = _action_btn("Open Folder")
        open_folder_btn.clicked.connect(self._open_data_folder)

        version_lbl = _lbl(f"v{_APP_VERSION}", Colors.TEXT_PRIMARY,
                           Fonts.SIZE_SM, bold=True)

        repo_btn = _action_btn("⎆  GitHub")
        repo_btn.clicked.connect(
            lambda: QDesktopServices.openUrl(
                QUrl("https://github.com/DaCapo111/benchflow")
            )
        )

        info_card = _card_with_rows([
            _build_row("Version", version_lbl),
            _build_row("Data folder", data_path_lbl),
            _build_action_row("Open the folder where BenchFlow stores all your data.",
                              open_folder_btn),
            _build_action_row("Source code, issues, and releases on GitHub.",
                              repo_btn),
        ])
        content_lay.addWidget(info_card)

        # ── Section: Preferences ──────────────────────────────────────────────
        content_lay.addWidget(_section_header("Preferences"))

        theme_lbl = _lbl("Dark (default)", Colors.TEXT_MUTED, Fonts.SIZE_SM)
        theme_note = "Light theme coming in a future update"

        self._autosave_spin = QSpinBox()
        self._autosave_spin.setRange(5, 300)
        self._autosave_spin.setValue(
            getattr(self.app.state, "autosave_interval_s", 30)
        )
        self._autosave_spin.setSuffix("  seconds")
        self._autosave_spin.setFixedHeight(32)
        self._autosave_spin.setFixedWidth(140)
        self._autosave_spin.setStyleSheet(
            f"QSpinBox {{ background: {Colors.BG_INPUT}; color: {Colors.TEXT_PRIMARY};"
            f"  border: 1px solid {Colors.BORDER}; border-radius: {Radii.SM}px;"
            f"  padding: 0 8px; font-size: {Fonts.SIZE_SM}px; }}"
        )
        self._autosave_spin.valueChanged.connect(self._on_autosave_changed)

        recovery_lbl = _lbl("Enabled", Colors.SUCCESS, Fonts.SIZE_SM)

        pref_card = _card_with_rows([
            _build_row("Theme", theme_lbl, note=theme_note),
            _build_row("Autosave interval", self._autosave_spin,
                       note="Active run session saved every N seconds"),
            _build_row("Session recovery", recovery_lbl,
                       note="Resumable on next launch if app closes mid-run"),
        ])
        content_lay.addWidget(pref_card)

        # ── Section: Dependencies ─────────────────────────────────────────────
        content_lay.addWidget(_section_header("Export Dependencies"))

        rl_ok   = _check_dep("reportlab")
        docx_ok = _check_dep("docx")

        dep_rows = [
            _build_row("reportlab", _dep_badge(rl_ok),
                       note="Required for PDF export"),
            _build_row("python-docx", _dep_badge(docx_ok),
                       note="Required for Word export"),
        ]
        if not rl_ok or not docx_ok:
            missing = []
            if not rl_ok:
                missing.append("reportlab")
            if not docx_ok:
                missing.append("python-docx")
            install_note = _lbl(
                f"Install missing:  pip install {' '.join(missing)}",
                Colors.WARNING, Fonts.SIZE_XS, wrap=True
            )
            install_row = QWidget()
            install_row.setStyleSheet("background: transparent;")
            install_lay = QHBoxLayout(install_row)
            install_lay.setContentsMargins(16, 8, 16, 8)
            install_lay.addWidget(install_note)
            dep_rows.append(install_row)

        content_lay.addWidget(_card_with_rows(dep_rows))

        # ── Section: Session ──────────────────────────────────────────────────
        content_lay.addWidget(_section_header("Active Session"))

        reset_btn = _action_btn("⊗  Reset Active Session", danger=True)
        reset_btn.clicked.connect(self._on_reset_session)

        session_card = _card_with_rows([
            _build_action_row(
                "Clear the saved run session so BenchFlow won't offer to resume "
                "it on next launch. Use this if a session is stuck.",
                reset_btn,
            ),
        ])
        content_lay.addWidget(session_card)

        # ── Section: Backup & Restore ─────────────────────────────────────────
        content_lay.addWidget(_section_header("Backup & Restore"))

        backup_btn = PrimaryButton("📦  Backup All Data")
        backup_btn.setFixedHeight(34)
        backup_btn.clicked.connect(self._on_backup)

        restore_btn = _action_btn("📂  Restore from Backup")
        restore_btn.setFixedHeight(34)
        restore_btn.clicked.connect(self._on_restore)

        br_card = _card_with_rows([
            _build_action_row(
                "Export all data (protocols, runs, schedule) as a ZIP archive.",
                backup_btn,
            ),
            _build_action_row(
                "Restore data from a previously created BenchFlow backup ZIP. "
                "Existing data will be backed up before overwriting.",
                restore_btn,
            ),
        ])
        content_lay.addWidget(br_card)

        content_lay.addStretch()

        scroll.setWidget(content)
        outer.addWidget(scroll, stretch=1)
        self._root_layout.addLayout(outer)

    # ── Handlers ─────────────────────────────────────────────────────────────

    def _open_data_folder(self) -> None:
        path = str(APP_DIR)
        if sys.platform == "darwin":
            subprocess.Popen(["open", path])
        elif sys.platform == "win32":
            os.startfile(path)  # type: ignore[attr-defined]
        else:
            subprocess.Popen(["xdg-open", path])

    def _on_autosave_changed(self, value: int) -> None:
        try:
            self.app.state.autosave_interval_s = value
        except Exception:
            pass

    def _on_reset_session(self) -> None:
        dlg = QMessageBox(self)
        dlg.setWindowTitle("Reset Active Session")
        dlg.setText(
            "This will clear the saved run session. "
            "BenchFlow won't offer to resume it on next launch.\n\n"
            "Proceed?"
        )
        dlg.setStandardButtons(
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel
        )
        dlg.setDefaultButton(QMessageBox.StandardButton.Cancel)
        if dlg.exec() != QMessageBox.StandardButton.Yes:
            return
        try:
            self.app.data.clear_active_session()
            ToastManager.show_success("Active session cleared.")
        except Exception as exc:
            ToastManager.show_error(f"Failed: {exc}")

    def _on_backup(self) -> None:
        from datetime import datetime as _dt
        default_name = f"BenchFlow_backup_{_dt.now().strftime('%Y-%m-%d_%H%M%S')}.zip"
        path, _ = QFileDialog.getSaveFileName(
            self, "Save Backup", default_name,
            "ZIP Archives (*.zip);;All Files (*)"
        )
        if not path:
            return
        try:
            manifest = self.app.data.export_all_data(path)
            n = len(manifest)
            fname = Path(path).name
            ToastManager.show_success(
                f"Backed up {n} file{'s' if n != 1 else ''} → {fname}"
            )
        except Exception as exc:
            ToastManager.show_error(f"Backup failed: {exc}")

    def _on_restore(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Open Backup", "",
            "ZIP Archives (*.zip);;All Files (*)"
        )
        if not path:
            return

        dlg = QMessageBox(self)
        dlg.setWindowTitle("Restore from Backup")
        dlg.setText(
            "Restoring will overwrite your current data with the backup contents.\n"
            "Your existing data will be saved as .pre_restore_*.json files "
            "in the data folder before overwriting.\n\n"
            "Continue?"
        )
        dlg.setStandardButtons(
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel
        )
        dlg.setDefaultButton(QMessageBox.StandardButton.Cancel)
        if dlg.exec() != QMessageBox.StandardButton.Yes:
            return

        try:
            restored = self.app.data.restore_all_data(path)
            n = len(restored)
            ToastManager.show_success(
                f"Restored {n} file{'s' if n != 1 else ''}. Restart BenchFlow to apply."
            )
        except ValueError as e:
            ToastManager.show_error(f"Invalid backup: {e}")
        except Exception as exc:
            ToastManager.show_error(f"Restore failed: {exc}")

    def on_show(self) -> None:
        # Refresh autosave spin to current state value
        if self._autosave_spin is not None:
            val = getattr(self.app.state, "autosave_interval_s", 30)
            self._autosave_spin.blockSignals(True)
            self._autosave_spin.setValue(val)
            self._autosave_spin.blockSignals(False)
