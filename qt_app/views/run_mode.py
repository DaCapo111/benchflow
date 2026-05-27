"""
Run Mode page — Phase 2: protocol selector + read-only step cards.

Layout:
  ┌─────────────────┬──────────────────────────────────────┐
  │  Protocol list  │  Step cards (read-only in Phase 2)   │
  │  (left panel)   │  Full timer logic in Phase 3         │
  └─────────────────┴──────────────────────────────────────┘

Phase 2 focus: smooth scrolling validation, real data display.
Phase 3 adds: QTimer, complete/pause/undo, autosave.
"""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QListWidget, QListWidgetItem,
    QScrollArea, QSizePolicy, QSplitter, QVBoxLayout, QWidget,
)

from qt_app.theme import Colors, Fonts, Radii
from qt_app.components.widgets import (
    Card, HSeparator, PageTitle, SubLabel, Badge,
)
from qt_app.views.base_page import BasePage
from qt_app.services.data import DataService


# ── Step card (read-only Phase 2 version) ─────────────────────────────────────

STEP_TYPE_COLORS: dict[str, tuple[str, str]] = {
    "preparation":       ("#1e3a5f", "#60a5fa"),
    "reagent_addition":  ("#042f2e", "#2dd4bf"),
    "mixing":            ("#2e1065", "#c084fc"),
    "incubation":        ("#431407", "#fb923c"),
    "waiting":           ("#1e293b", "#64748b"),
    "centrifuge":        ("#1e1b4b", "#818cf8"),
    "wash":              ("#164e63", "#22d3ee"),
    "transfer":          ("#1e1b4b", "#a5b4fc"),
    "pipetting":         ("#0c4a6e", "#38bdf8"),
    "resuspension":      ("#052e16", "#4ade80"),
    "staining":          ("#500724", "#f472b6"),
    "blocking":          ("#4c0519", "#fb7185"),
    "electrophoresis":   ("#3b0764", "#d8b4fe"),
    "gel_running":       ("#2e1065", "#c4b5fd"),
    "membrane_transfer": ("#1e3a5f", "#93c5fd"),
    "imaging":           ("#064e3b", "#6ee7b7"),
    "measurement":       ("#422006", "#fdba74"),
    "lysis":             ("#450a0a", "#fca5a5"),
    "heating":           ("#431407", "#fb923c"),
    "cooling":           ("#0c4a6e", "#7dd3fc"),
    "storage":           ("#1e293b", "#94a3b8"),
    "harvest":           ("#1a2e05", "#86efac"),
    "sample_collection": ("#451a03", "#fcd34d"),
    "other":             ("#1e293b", "#94a3b8"),
}

def _step_colors(step_type: str) -> tuple[str, str]:
    return STEP_TYPE_COLORS.get(step_type, STEP_TYPE_COLORS["other"])


class StepCard(QFrame):
    """Read-only step card for Phase 2."""

    def __init__(self, step: dict, idx: int, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        bg, accent = _step_colors(step.get("type", "other"))
        self.setStyleSheet(
            f"QFrame {{"
            f"  background: {bg};"
            f"  border-radius: {Radii.LG}px;"
            f"  border: 1px solid {accent}40;"
            f"}}"
        )
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._build(step, idx, accent)

    def _build(self, step: dict, idx: int, accent: str) -> None:
        lay = QVBoxLayout(self)
        lay.setContentsMargins(18, 14, 18, 14)
        lay.setSpacing(6)

        # ── Header: index + title + type badge ────────────────────────────
        row1 = QHBoxLayout()
        row1.setSpacing(10)

        idx_lbl = QLabel(f"{idx + 1:02d}")
        idx_lbl.setStyleSheet(
            f"color: {accent}; font-size: {Fonts.SIZE_SM}px; font-weight: 700;"
            f"background: {accent}25; border-radius: 6px; padding: 2px 8px;"
        )
        row1.addWidget(idx_lbl)

        title = step.get("title", "Untitled step")
        title_lbl = QLabel(title)
        title_lbl.setStyleSheet(
            f"color: {Colors.TEXT_PRIMARY}; font-size: {Fonts.SIZE_MD}px; font-weight: 600;"
        )
        title_lbl.setWordWrap(True)
        row1.addWidget(title_lbl, stretch=1)

        stype = step.get("type", "other").replace("_", " ").title()
        type_badge = QLabel(stype)
        type_badge.setStyleSheet(
            f"color: {accent}; background: {accent}20;"
            f"border-radius: 6px; padding: 2px 8px;"
            f"font-size: {Fonts.SIZE_XS}px; font-weight: 600;"
        )
        row1.addWidget(type_badge)
        lay.addLayout(row1)

        # ── Timing row ─────────────────────────────────────────────────────
        timing_parts = []
        ho = float(step.get("handsOnMinutes", 0))
        wt = float(step.get("waitMinutes", 0))
        buf = float(step.get("bufferMinutes", 0))
        if ho:
            timing_parts.append(f"⏱ {ho:.0f}m hands-on")
        if wt:
            timing_parts.append(f"⏳ {wt:.0f}m wait")
        if buf:
            timing_parts.append(f"+ {buf:.0f}m buffer")

        if timing_parts:
            timing_lbl = QLabel("  ·  ".join(timing_parts))
            timing_lbl.setStyleSheet(
                f"color: {Colors.TEXT_SECOND}; font-size: {Fonts.SIZE_SM}px;"
            )
            lay.addWidget(timing_lbl)

        # ── Description preview ────────────────────────────────────────────
        desc = step.get("description", "").strip()
        if desc:
            # Show first 120 chars
            preview = desc[:120] + ("…" if len(desc) > 120 else "")
            desc_lbl = QLabel(preview)
            desc_lbl.setStyleSheet(
                f"color: {Colors.TEXT_MUTED}; font-size: {Fonts.SIZE_SM}px;"
            )
            desc_lbl.setWordWrap(True)
            lay.addWidget(desc_lbl)

        # ── Reagents ───────────────────────────────────────────────────────
        reagents = step.get("reagents", [])
        if reagents:
            r_names = [r.get("name", "") for r in reagents[:3] if r.get("name")]
            if r_names:
                suffix = f" +{len(reagents)-3}" if len(reagents) > 3 else ""
                r_lbl = QLabel("🧪 " + ", ".join(r_names) + suffix)
                r_lbl.setStyleSheet(
                    f"color: {Colors.TEXT_SECOND}; font-size: {Fonts.SIZE_XS}px;"
                )
                lay.addWidget(r_lbl)

        # ── Temperature / condition ────────────────────────────────────────
        temp = step.get("temperature", "").strip()
        centrifuge = step.get("centrifugeCondition", "").strip()
        cond_parts = []
        if temp:
            cond_parts.append(f"🌡 {temp}")
        if centrifuge:
            cond_parts.append(f"⚙ {centrifuge}")
        if cond_parts:
            cond_lbl = QLabel("  ·  ".join(cond_parts))
            cond_lbl.setStyleSheet(
                f"color: {Colors.TEXT_SECOND}; font-size: {Fonts.SIZE_XS}px;"
            )
            lay.addWidget(cond_lbl)

        # ── Notes preview ─────────────────────────────────────────────────
        notes = step.get("notes", "").strip()
        if notes:
            n_lbl = QLabel(f"📝 {notes[:80]}{'…' if len(notes) > 80 else ''}")
            n_lbl.setStyleSheet(
                f"color: {Colors.TEXT_MUTED}; font-size: {Fonts.SIZE_XS}px;"
            )
            n_lbl.setWordWrap(True)
            lay.addWidget(n_lbl)


# ── Protocol list item ────────────────────────────────────────────────────────

class ProtocolListItem(QListWidgetItem):
    def __init__(self, protocol: dict) -> None:
        name = protocol.get("name", "Untitled")
        n_steps = len(protocol.get("steps", []))
        super().__init__(f"  {name}  ({n_steps} steps)")
        self.setData(Qt.ItemDataRole.UserRole, protocol)


# ── RunModePage ───────────────────────────────────────────────────────────────

class RunModePage(BasePage):
    """Run Mode page — Phase 2: protocol browser + read-only step cards."""

    def __init__(self, app: "BenchFlowApp", parent: QWidget | None = None) -> None:  # type: ignore[name-defined]
        super().__init__(app, parent)
        self._build()

    def _build(self) -> None:
        root = QVBoxLayout()
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Top header ────────────────────────────────────────────────────────
        header_widget = QWidget()
        header_widget.setStyleSheet(f"background: {Colors.BG_PAGE};")
        header_layout = QHBoxLayout(header_widget)
        header_layout.setContentsMargins(32, 28, 32, 16)
        header_layout.setSpacing(12)

        title_col = QVBoxLayout()
        title_col.setSpacing(2)
        title_col.addWidget(PageTitle("Run Mode"))
        sub = SubLabel("Select a protocol to view its steps. Timers coming in Phase 3.")
        title_col.addWidget(sub)
        header_layout.addLayout(title_col)
        header_layout.addStretch()
        root.addWidget(header_widget)

        sep = HSeparator()
        root.addWidget(sep)

        # ── Main split: protocol list | step cards ────────────────────────────
        self._splitter = QSplitter(Qt.Orientation.Horizontal)
        self._splitter.setStyleSheet(
            f"QSplitter::handle {{ background: {Colors.BORDER}; width: 1px; }}"
        )

        # Left panel — protocol list
        left = self._build_left_panel()
        self._splitter.addWidget(left)

        # Right panel — step cards
        right = self._build_right_panel()
        self._splitter.addWidget(right)

        self._splitter.setSizes([220, 900])
        self._splitter.setChildrenCollapsible(False)
        root.addWidget(self._splitter, stretch=1)

        self._root_layout.addLayout(root)
        self._populate_protocols()

    # ── Left panel ────────────────────────────────────────────────────────────

    def _build_left_panel(self) -> QWidget:
        w = QWidget()
        w.setStyleSheet(f"background: {Colors.BG_SIDEBAR};")
        w.setMinimumWidth(200)
        w.setMaximumWidth(300)
        lay = QVBoxLayout(w)
        lay.setContentsMargins(12, 16, 12, 16)
        lay.setSpacing(8)

        hdr = QLabel("Protocols")
        hdr.setStyleSheet(
            f"color: {Colors.TEXT_SECOND}; font-size: {Fonts.SIZE_SM}px;"
            f"font-weight: 600; padding-left: 4px;"
        )
        lay.addWidget(hdr)

        self._proto_list = QListWidget()
        self._proto_list.setStyleSheet(
            f"QListWidget {{"
            f"  background: transparent; border: none; outline: none;"
            f"  font-size: {Fonts.SIZE_MD}px; color: {Colors.TEXT_PRIMARY};"
            f"}}"
            f"QListWidget::item {{"
            f"  padding: 10px 8px; border-radius: 10px; margin: 2px 0;"
            f"}}"
            f"QListWidget::item:hover {{"
            f"  background: {Colors.BG_CARD_HOV};"
            f"}}"
            f"QListWidget::item:selected {{"
            f"  background: {Colors.ACCENT}; color: white; border-radius: 10px;"
            f"}}"
        )
        self._proto_list.currentItemChanged.connect(self._on_protocol_selected)
        lay.addWidget(self._proto_list, stretch=1)
        return w

    # ── Right panel ───────────────────────────────────────────────────────────

    def _build_right_panel(self) -> QWidget:
        w = QWidget()
        w.setStyleSheet(f"background: {Colors.BG_PAGE};")
        lay = QVBoxLayout(w)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        # Protocol info bar
        self._info_bar = QWidget()
        self._info_bar.setStyleSheet(
            f"background: {Colors.BG_SIDEBAR}; border-bottom: 1px solid {Colors.BORDER};"
        )
        info_lay = QHBoxLayout(self._info_bar)
        info_lay.setContentsMargins(20, 12, 20, 12)
        info_lay.setSpacing(16)

        self._info_name = QLabel("—")
        self._info_name.setStyleSheet(
            f"color: {Colors.TEXT_PRIMARY}; font-size: {Fonts.SIZE_LG}px; font-weight: 700;"
        )
        info_lay.addWidget(self._info_name)

        self._info_steps = QLabel("")
        self._info_steps.setStyleSheet(f"color: {Colors.TEXT_SECOND}; font-size: {Fonts.SIZE_SM}px;")
        info_lay.addWidget(self._info_steps)

        self._info_dur = QLabel("")
        self._info_dur.setStyleSheet(f"color: {Colors.TEXT_MUTED}; font-size: {Fonts.SIZE_SM}px;")
        info_lay.addWidget(self._info_dur)
        info_lay.addStretch()

        phase_badge = QLabel("Read-only · Phase 2")
        phase_badge.setStyleSheet(
            f"color: {Colors.ACCENT_LIGHT}; background: rgba(59,130,246,0.15);"
            f"border-radius: 8px; padding: 3px 10px;"
            f"font-size: {Fonts.SIZE_XS}px; font-weight: 600;"
        )
        info_lay.addWidget(phase_badge)
        lay.addWidget(self._info_bar)

        # Step scroll area
        self._step_scroll = QScrollArea()
        self._step_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._step_scroll.setWidgetResizable(True)
        self._step_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._step_scroll.setStyleSheet(f"background: {Colors.BG_PAGE};")

        self._step_content = QWidget()
        self._step_content.setStyleSheet(f"background: {Colors.BG_PAGE};")
        self._step_layout = QVBoxLayout(self._step_content)
        self._step_layout.setContentsMargins(20, 20, 20, 20)
        self._step_layout.setSpacing(10)
        self._step_scroll.setWidget(self._step_content)
        lay.addWidget(self._step_scroll, stretch=1)

        # Initial empty state
        self._show_empty_state("Select a protocol from the left panel.")
        return w

    # ── Data ──────────────────────────────────────────────────────────────────

    def _populate_protocols(self) -> None:
        self._proto_list.clear()
        protocols = self.app.data.load_protocols()
        for p in protocols:
            self._proto_list.addItem(ProtocolListItem(p))
        if not protocols:
            placeholder = QListWidgetItem("  No protocols yet")
            placeholder.setFlags(Qt.ItemFlag.NoItemFlags)
            placeholder.setForeground(Colors.TEXT_MUTED)
            self._proto_list.addItem(placeholder)

    def _on_protocol_selected(self, current: QListWidgetItem | None, _prev) -> None:
        if current is None:
            return
        protocol = current.data(Qt.ItemDataRole.UserRole)
        if protocol is None:
            return
        self._render_steps(protocol)

    def _render_steps(self, protocol: dict) -> None:
        # Update info bar
        name = protocol.get("name", "Untitled")
        steps = protocol.get("steps", [])
        total_min = DataService.protocol_total_minutes(protocol)

        self._info_name.setText(name)
        self._info_steps.setText(f"{len(steps)} steps")
        self._info_dur.setText(f"~{DataService.format_duration(total_min)}")

        # Clear step layout
        while self._step_layout.count():
            item = self._step_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not steps:
            self._show_empty_state("This protocol has no steps.")
            return

        for i, step in enumerate(steps):
            card = StepCard(step, i, parent=self._step_content)
            self._step_layout.addWidget(card)

        self._step_layout.addStretch()

    def _show_empty_state(self, msg: str) -> None:
        # Clear existing content first
        while self._step_layout.count():
            item = self._step_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        self._info_name.setText("—")
        self._info_steps.setText("")
        self._info_dur.setText("")

        lbl = QLabel(msg)
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl.setStyleSheet(
            f"color: {Colors.TEXT_MUTED}; font-size: {Fonts.SIZE_MD}px;"
            f"font-style: italic;"
        )
        self._step_layout.addStretch()
        self._step_layout.addWidget(lbl)
        self._step_layout.addStretch()

    def on_show(self) -> None:
        self._populate_protocols()
