# BenchFlow — PySide6 Full Migration Plan

> **Branch**: `qt-prototype`  
> **Legacy CTk app**: `app.py` on `main` (unchanged, still ships)  
> **Qt entry point**: `python3 qt_app/main.py`

---

## Migration Status

| Phase | Description | Status |
|---|---|---|
| Phase 1 | App skeleton (window, sidebar, routing, theme) | ✅ **Done** |
| Phase 2 | Data layer integration (DataService, models, read-only pages) | ✅ **Done** |
| Phase 3 | Run Mode — QTimer, step cards, complete/pause/undo, autosave | ✅ **Done** |
| Phase 3.5 | Run Mode polish — sequential, progress bars, remove block, focus scroll | ✅ **Done** |
| Phase 4 | Schedule — calendar grid, drag session blocks, timeline editor | ✅ **Done** |
| Phase 4.5 | Schedule polish — week view, right-panel drag-reorder, context menu | ✅ **Done** |
| Phase 4.75 | App-wide stabilization — AppState, EventBus, Toast, BackgroundMgr, Perf | ✅ **Done** |
| Phase 5 | Library + Templates — cards, search/filter/sort, New Protocol dialog, detail panel | ✅ **Done** |
| Phase 6 | Protocol Editor — metadata, step CRUD, reagents, conditions, reorder, save | ✅ **Done** |
| Phase 8A | Flowchart — QGraphicsScene nodes, arrows, zoom/pan, step detail panel | ✅ **Done** |
| Phase 7 | Lab Notebook — date-grouped list, detail panel, step table, edit notes, search | ✅ **Done** |
| Phase 8B | Export (PDF/DOCX/JSON/MD) + Import page (JSON file, paste text) | ✅ **Done** |
| Phase 9 | Settings page, backup/restore, packaging (BenchFlow_Qt.spec, build scripts) | ✅ **Done** |
| Phase 10 | Cutover — replace CTk on main, update GitHub Actions, signed builds | 🔲 |

---

## Phase 1 — App Skeleton ✅

**Commit**: `feat(phase-1): PySide6 app skeleton — window, sidebar, routing, theme`

### What was built

```
qt_app/
  main.py          entry point: python3 qt_app/main.py
  app.py           BenchFlowApp(QMainWindow): sidebar + QStackedWidget routing
  theme.py         Colors, Fonts, Radii, QSS stylesheet, apply_theme()
  models/          Protocol, Step, ScheduleBlock, RunRecord, RuntimeSession dataclasses
  services/        DataService (JSON persistence)
  components/      Sidebar (nav_requested signal), shared widgets
  views/           BasePage base class + 9 page stubs
```

### Architecture decisions

- `QStackedWidget` for page routing (same as CTk's `grid()` / `grid_remove()`)
- `Sidebar` emits `nav_requested(str)` signal → `BenchFlowApp.navigate()`
- `BasePage.on_show()` hook called on every navigation (for data refresh)
- `apply_theme()` sets Fusion style + dark QPalette + global QSS

---

## Phase 2 — Data Layer Integration ✅

**Commit**: `feat(phase-2): data layer integration — DataService, models, real pages`

### Data files (unchanged from CTk app)

| File | Location | Format |
|---|---|---|
| protocols.json | `~/Library/Application Support/BenchFlow/` | `List[Protocol]` |
| runs.json | same | `List[RunRecord]` (lab notebook) |
| categories.json | same | `List[str]` |
| tags.json | same | `List[str]` |
| schedule.json | same | `List[ScheduleBlock]` |
| runtime_session.json | same | `RuntimeSession` (crash recovery) |
| templates/*.json | `<repo>/templates/` | read-only built-in templates |

All data files are **100% compatible** between CTk and Qt versions.
Both apps read/write the same JSON format. No migration needed.

### CTk → Qt field name mapping

| CTk JSON key | Qt model field | Notes |
|---|---|---|
| `type` | `step_type` | `from_dict()` reads both |
| `handsOnMinutes` | `hands_on_minutes` | |
| `waitMinutes` | `wait_minutes` | |
| `bufferMinutes` | `buffer_minutes` | |
| `centrifugeCondition` | `centrifuge_condition` | |
| `shakingRotation` | `shaking_rotation` | |
| `createdAt` | `created_at` | ms epoch int |
| `updatedAt` | `updated_at` | ms epoch int |
| `protocolId` | `protocol_id` | |
| `plannedStart` | `planned_start` | ms epoch |
| `plannedEnd` | `planned_end` | ms epoch |
| `startedAt` | `started_at` | ms epoch |
| `endedAt` | `ended_at` | ms epoch |
| `stepRecords` | `step_records` | list of StepRecord |

`to_dict()` always writes the original CTk key names, preserving 100% compatibility.

### DataService improvements (Phase 2)

- **Atomic writes**: `write temp → os.replace()` — no half-written files on crash
- **Corrupt file recovery**: bad JSON backed up as `*.corrupt_TIMESTAMP.json`, app returns empty and keeps running
- **Utility helpers**: `format_duration()`, `format_ts()`, `format_date()`, `step_total_minutes()`, `protocol_total_minutes()`

### Pages implemented in Phase 2

| Page | Phase 2 state |
|---|---|
| Dashboard | ✅ Real counts (protocols, templates, schedule, runs), active session banner |
| Library | ✅ Protocols + Templates grouped by category, clickable cards with stats |
| Run Mode | ✅ Protocol list (left panel), read-only step cards (right panel), QSplitter |
| Schedule | ✅ Experiments grouped by date, time range, status badge |
| Lab Notebook | ✅ Run records grouped by date, step completion dots, observations |
| Editor | Placeholder → Phase 5 |
| Flowchart | Placeholder → Phase 6 |
| Import | Placeholder → Phase 5 |
| Settings | Placeholder → Phase 8 |

### Known limitations (by design, not bugs)

- Run Mode step cards are **read-only** — no timers, no Complete button
- Library cards are **selection-only** — no create/edit/delete
- Schedule is **list-only** — no calendar, no drag-and-drop
- Lab Notebook is **view-only** — no rich text editing, no export

---

## Phase 3 — Run Mode ✅

**Commit**: `feat(phase-3): full Run Mode — wall-clock timers, autosave, session restore`

### What was built

**`qt_app/services/run_service.py`** — Pure Python session engine
- `StepRunState`: per-step runtime state with wall-clock timer math
  - `start()` / `pause()` / `resume()` / `complete()` / `undo_complete()` / `skip()` / `reset()` / `adjust()`
  - `remaining_secs(now)` = `planned_secs - ((now - started_at) + accumulated_elapsed_secs)`
  - Accurate across app sleep, system suspend, window switches
- `RunModeSession`: owns protocol snapshot + step states + temp blocks
  - `add_temp_block()` inserts extra blocks at runtime
  - `to_dict()` / `from_dict()`: version-3 format (safe coexistence with CTk v1)

**`qt_app/components/step_card.py`** — `StepCard(QFrame)`
- Created ONCE per protocol load, updated in-place via `apply_state()` / `update_timer()`
- All buttons: Start / Pause / Resume / Complete / Undo Complete / Skip / Undo Skip / Reset
- Adjust buttons: -5m / -1m / +1m / +5m
- Notes textbox with `notes_changed` signal
- Countdown (wait steps) vs. elapsed stopwatch (hands-on steps) automatically selected

**`qt_app/dialogs/add_block.py`** — `AddBlockDialog(QDialog)`
- `QDialog.exec()` — safe on macOS, no `grab_set()` race
- Fields: title, type, duration, notes

**`qt_app/dialogs/restore_session.py`** — `RestoreSessionDialog(QDialog)`
- Three choices: Resume / Save to Notebook / Discard
- Shows protocol name + last-saved timestamp

**`qt_app/views/run_mode.py`** — full rewrite
- Single 500ms `QTimer` for all steps (not one per step)
- Protocol selection → `render_step_cards_once()` (creates cards once)
- State changes → `update_card(idx)` → `card.apply_state()` (no rebuild)
- Timer ticks → `card.update_timer()` on running steps only
- 9-second `_UndoSnackbar` after Complete; persistent Undo button on completed cards
- `_on_end_run()` saves to Lab Notebook + clears active session
- `_offer_restore()` checks `runtime_session.json` version=3 on `on_show()`
- Autosave: debounced 100ms for state changes, 1000ms for notes

**`logs/qt_run_mode.log`** — structured log of all run actions

### Differences from CTk version

| Issue | CTk | Qt Phase 3 |
|---|---|---|
| Scroll performance | O(N) NSView reframes; 320 widgets scroll at ~60fps limit | `QScrollArea` compositing; 50+ cards smooth |
| Complete freeze | `grab_set()` on `CTkToplevel` intercepts all events on macOS | `QDialog.exec()` — no grab_set, native modal |
| Timer accuracy | `remaining -= 1` per `after(1000)` — drifts on sleep | Wall-clock: `planned - (now - started_at - paused)` |
| Session restore | Checked at app startup (freezes launch) | Checked lazily on `on_show()` — no launch penalty |
| Undo | 9s countdown via `after()` chain | `_UndoSnackbar` with dedicated `QTimer`, persistent button |
| Add Block | Modal via `CTkToplevel` + `grab_set` | `QDialog.exec()` |

### Known limitations (Phase 3)

- Sequential mode not implemented (free-run only; Phase 3.5)
- Step card "remove temp block" button not wired (temp blocks can be ended/skipped)
- No progress bar on step cards (Phase 3.5)
- Notes scroll position not restored after session reload

---

## Phase 4 — Schedule ✅

**Commit**: `feat(phase-4): Schedule calendar, timeline editor, drag sessions`

### New files

```
qt_app/models/schedule_experiment.py   ScheduledExperiment + TimelineBlock dataclasses
qt_app/services/schedule_service.py    protocol_to_timeline(), make_scheduled_experiment(), helpers
qt_app/dialogs/add_experiment.py       AddExperimentDialog (title/protocol/date/time/notes)
qt_app/dialogs/edit_block.py           EditBlockDialog (add or edit a timeline block)
qt_app/views/schedule.py              Full rewrite — calendar grid + timeline detail panel
logs/qt_schedule.log                   Structured action log
```

### Data

New file `~/Library/Application Support/BenchFlow/scheduled_experiments.json`  
Format: `List[ScheduledExperiment]` (Qt-native, independent of CTk `schedule.json`)

CTk `schedule.json` is **not touched** — full compatibility preserved.

### Architecture

| Component | Implementation |
|---|---|
| Calendar grid | `_CalendarGrid(QWidget)` — custom paintEvent + `_SessionBlock(QFrame)` children |
| Session blocks | Absolutely positioned `QFrame` children; geometry set by `_reposition_blocks()` |
| Day header | `_DayHeader(QWidget)` — custom paintEvent (today circle in blue) |
| Timeline rows | `_TimelineBlockRow(QFrame)` — per-block widget with time, title, actions |
| Drag | Global-y delta in `mouseMoveEvent`; 15-min snap; `drag_finished` signal on release |
| Autosave | 150ms debounced `QTimer` → atomic write via `DataService` |

### What was built

- **Day / Work Week calendar view** with Day / Work Week toggle
- Date navigation: `< Prev`, `Today`, `Next >`; date range label
- **Today column highlight** + **current-time indicator** (red line + dot)
- **Session blocks** positioned on grid by `planned_start` / `planned_end`
- **Vertical drag** to change session start time (15-minute snap)
- **+ Schedule Experiment** dialog: title, protocol selector (protocols + templates), date, start time, notes
- Protocol → timeline auto-generation using `step_planned_secs()`
- **Right panel** shows selected experiment's full timeline blocks
- Per-block actions: **Edit** (dialog), **Skip** (status=skipped, zero-duration), **Delete**
- **Add Break / Task / Note** buttons append blocks to timeline
- `recalculate_times()` updates all block start/end after any change
- Session block position and height update after drag or timeline edit
- Experiment persisted to `scheduled_experiments.json` on every change

### Known limitations (Phase 4.5)

- Week view (7-day) not implemented — only Day and Work Week
- Right-panel timeline block drag-reorder deferred to Phase 4.5
- Right-click context menu not implemented
- Parallel task support not implemented
- "Mark done" per block not yet in the UI (status can be set to `done` via Edit dialog)

### Differences from CTk Schedule page

| CTk | Phase 4 Qt |
|---|---|
| List-only (grouped by date) | Interactive calendar grid with time axis |
| No drag | Drag session block to change start time |
| No timeline detail | Right panel shows all internal steps |
| No add/edit | Full add/edit/skip/delete per block |
| Reads `schedule.json` | New `scheduled_experiments.json` — no conflict |

---

## Phase 4.5 — Schedule Polish ✅

**Commit**: `feat(phase-4.5): Schedule polish — week view, context menu, reorder, date picker`

### What was built

**`TimelineBlock` model changes** (`qt_app/models/schedule_experiment.py`):
- New field: `retains_time: bool = False`
  - `retains_time=False` (default): canceled/skipped block occupies zero time in timeline
  - `retains_time=True`: block keeps its time slot (used by "Keep Time" cancel option)
- `recalculate_times()` updated to respect `retains_time`
- `to_dict` / `from_dict` round-trip the new field as `"retainsTime"`

**`_TimelineBlockRow`** — full rebuild:
- New signals: `duplicate_requested`, `cancel_requested(str, bool)`, `restore_requested`,
  `move_up_requested`, `move_down_requested`, `insert_before_requested(str, str)`,
  `insert_after_requested(str, str)`
- Drag handle label (⠿) visual — indicates future drag-reorder
- ▲ / ▼ Move Up / Move Down buttons — swap block with adjacent block
- Restore button (↩) shown when block is skipped/canceled
- Right-click context menu with dark QSS theme:
  - Edit… / Duplicate
  - Insert Before ▶ (Break/Task/Note/Custom submenu)
  - Insert After ▶ (Break/Task/Note/Custom submenu)
  - Mark Skipped / Mark Canceled… / Restore to Planned
  - Move Up / Move Down
  - Delete
- **Mark Canceled dialog**: "Keep Time" vs "Remove Time" vs "Don't Cancel"

**`_CalendarGrid`** week mode:
- `_n_cols` returns 7 for "week" mode
- `_dates()` returns Mon–Sun for "week" mode
- Column min-width adjusted to 60px to accommodate 7 columns

**`SchedulePage` header**:
- Added "Week" toggle button (Day | Work Week | **Week**)
- `_date_lbl` replaced by `_date_btn` (clickable QPushButton)
- `_on_date_picker()`: frameless `QDialog` + `QCalendarWidget` anchored below the button
- `_update_date_label()` uses `d.day` (integer) — no more `%-d` (macOS-only strftime)

**`on_show()` — selection persistence**:
- Saves `_selected_exp.id` before reloading
- After `_load_experiments()`, re-finds experiment by ID
- If found: re-highlights in grid + re-renders detail panel
- If not found (deleted externally): shows placeholder

**`_clear_detail()`** — bug fix:
- Replaced buggy nested-layout teardown with recursive `_clear_layout(layout)` static method

**New handlers**:
| Method | Action |
|---|---|
| `_on_duplicate_block` | Deep-copy block, new UUID, insert after, recalculate |
| `_on_insert_before` / `_on_insert_after` | Open EditBlockDialog, insert at position |
| `_on_cancel_block(exp, bid, retains_time)` | Set status=canceled, set retains_time |
| `_on_restore_block` | Set status=planned, retains_time=False |
| `_on_move_up` / `_on_move_down` | Swap adjacent blocks, recalculate |

### Known limitations (deferred to Phase 5+)

- Full drag-reorder of timeline rows (handle is visual only; use ▲▼ for now)
- Parallel task columns (separate track for overlapping blocks)
- "Mark done" per individual block (status can be set via Edit dialog)

### Next: Phase 5 — Library + Protocol Editor + Import

---

## Phase 3 (old planning section — now done)

### What to implement

1. `QTimer` per step (countdown + elapsed)
2. Step card states: idle → running → paused → completed → skipped
3. Complete step button + undo (9-second countdown)
4. Adjust time (±1m buttons)
5. "Ask save adjusted time" dialog (QDialog — no grab_set needed in Qt)
6. Autosave to `runtime_session.json` every tick
7. Sequential mode (one step at a time)
8. Crash recovery: on `RunMode.on_show()`, check `DataService.load_active_session()`

### Key architectural advantage over CTk

- `QTimer` fires on main thread — same model as `after()`, zero threading complexity
- `QScrollArea` + `QWidget` per card: 16 cards scroll at 60fps (no O(N) NSView reframes)
- `QDialog.exec()` for modal dialogs — no `grab_set()` race condition on macOS

### Files to create

```
qt_app/views/run_mode.py    (extend existing skeleton)
qt_app/services/run_service.py   (step state machine, timer logic)
```

---

## How to Run

```bash
cd /Users/zihengxu/Documents/GitHub/benchflow
git checkout qt-prototype
pip install PySide6
python3 qt_app/main.py
```

Reads data from `~/Library/Application Support/BenchFlow/` —
the same data directory used by the CTk app on `main`.

---

## Phase 4.75 — App-wide Stabilization ✅

**Commit**: `stabilize: AppState, EventBus, ToastManager, BackgroundTaskManager, perf logging`

### New files

| File | Purpose |
|---|---|
| `qt_app/services/app_state.py` | `AppState(QObject)` — cross-page UI state with signals |
| `qt_app/services/event_bus.py` | `_EventBus` singleton (`bus`) — lightweight pub/sub dispatcher |
| `qt_app/services/background.py` | `BackgroundTaskManager` (`bg`) — centralized debounce / flush-on-close |
| `qt_app/services/error_handler.py` | `_ErrorHandler` (`eh`) — `safe_call`, `log_exception`, `show_error_toast` |
| `qt_app/services/perf.py` | `_Perf` (`perf`) — context-manager performance logging (>50ms threshold) |
| `qt_app/components/toast.py` | `ToastManager` — bottom-right floating toasts (success/warning/error/info) |

### AppState (`app.state`)

Owned by `BenchFlowApp`. Replaces per-page duplicate state:
- `selected_protocol_id`, `selected_schedule_experiment_id`, `active_run_session_id`
- `current_schedule_date`, `current_schedule_view`, `last_opened_page`
- `unsaved_changes`, `app_ready`
- Signals: `protocol_selection_changed`, `schedule_selection_changed`, `run_session_changed`, `page_changed`, `unsaved_changes_changed`

### EventBus (`bus`)

Module-level singleton. Supported events:
- `protocol_created/updated/deleted`
- `run_session_started`, `run_session_saved`
- `schedule_updated`
- `notebook_record_created`
- `active_session_restored`
- `data_saved`, `data_error`

### BackgroundTaskManager (`app.bg`)

- `debounce(key, delay_ms, callback)` — cancel + reschedule by named key
- `cancel(key)`, `cancel_all()` — explicit cancel
- `flush_all()` — fire all pending callbacks immediately (called in `closeEvent`)

### ToastManager

- Installed on `centralWidget()` in `BenchFlowApp.__init__()`
- `show_success/error/warning/info(message)`
- Auto-dismiss after 3.8s; click to dismiss early
- Stacks vertically bottom-right

### Theme additions

- `Radii.XS = 4`
- `Spacing` class: `XS=4, SM=8, MD=12, LG=16, XL=24, XXL=32`

### Page integrations

| Page | Change |
|---|---|
| `app.py` | `closeEvent` — flushes `bg`, saves active run session, cancels timers |
| `dashboard.py` | Subscribes to EventBus; refreshes counts on `run_session_saved`, `schedule_updated`, etc. |
| `schedule.py` | `_do_save` emits `schedule_updated`; `_on_add_experiment` shows success toast; `_apply_block_change` helper wraps recalculate + perf |
| `run_mode.py` | `_save_to_notebook` emits `run_session_saved` + `notebook_record_created`; `_on_save_session` / `_on_end_run` show success toast; `_render_step_cards_once` wrapped with `perf.measure` |

### Log files produced

| File | Content |
|---|---|
| `logs/qt_app.log` | Navigation events, startup/shutdown |
| `logs/qt_errors.log` | Exceptions via `eh.log_exception` |
| `logs/qt_perf.log` | Operations exceeding 50ms threshold |
| `logs/qt_run_mode.log` | Run Mode actions (existing) |
| `logs/qt_schedule.log` | Schedule actions (existing) |

### Known limitations

- `BackgroundTaskManager` does not yet replace the per-page `QTimer` instances in `run_mode.py` and `schedule.py` — those pages still create their own timers. Full migration deferred.
- `AppState` fields are not yet read back by all pages — pages still use local state. Incremental adoption as pages are refactored.
- Toast reposition on window resize deferred (toasts reposition correctly when the next toast appears).

### Next: Phase 5 — Library + Protocol Editor + Import

---

## Phase 5 — Library and Templates ✅

**Commit**: `feat(phase-5): Library page — protocol cards, templates, New Protocol dialog`

### New files

| File | Purpose |
|---|---|
| `qt_app/dialogs/new_protocol.py` | `NewProtocolDialog` — Blank / From Template / Duplicate Existing |
| `qt_app/views/library.py` | Full `LibraryPage` rewrite with `_ProtocolCard` and `_DetailPanel` |

### Architecture

```
LibraryPage (QSplitter)
├── Left panel (QScrollArea)
│   ├── Header row: "Protocol Library" title + "＋ New Protocol" button
│   ├── Toolbar: search QLineEdit + category QComboBox + sort QComboBox
│   ├── "My Protocols" section header
│   ├── _ProtocolCard × N  (click → _DetailPanel.show_protocol)
│   ├── "Templates" section header
│   └── _ProtocolCard × M  (click → _DetailPanel.show_protocol, is_template=True)
└── Right panel (_DetailPanel)
    ├── show_placeholder(): "Select a protocol to see details"
    └── show_protocol(proto, is_template):
        ├── Name, category badge, tags
        ├── Stats: steps / total time / hands-on / wait
        ├── Step list (up to 30)
        └── Action buttons:
            Protocol: Open in Run Mode (primary), Schedule Experiment, Duplicate, Delete
            Template:  Use Template (primary), Duplicate as Protocol
```

### NewProtocolDialog

Three creation methods — toggled by method buttons:

| Method | UI shown | Output |
|---|---|---|
| Blank Protocol | Name + Category fields | Fresh dict with empty steps |
| From Template | Name + Source combo (templates list) | Deep copy, new UUID + step UUIDs |
| Duplicate Existing | Name + Source combo (protocols list) | Deep copy, new UUID + step UUIDs |

### Search / Filter / Sort

- **Search**: live filtering on name, tags, category (case-insensitive)
- **Category filter**: combo auto-populated from all loaded protocols+templates
- **Sort options**: Name A→Z, Name Z→A, Most Recent (updatedAt), Most Steps, Fewest Steps

### EventBus events emitted

| Event | Trigger |
|---|---|
| `protocol_created` | New blank, use template, or duplicate |
| `protocol_deleted` | Confirmed delete |

### Run Mode integration

`run_mode.py` `on_show()` now checks `app.state.selected_protocol_id`. If set (e.g. navigated from Library "Open in Run Mode"), the matching protocol is auto-selected in the left-panel list and `selected_protocol_id` is cleared.

### Known limitations

- Protocol Editor (`editor.py`) is still a placeholder — editing steps deferred to Phase 6.
- "Edit" action in detail panel shows a "Coming in Phase 6" info dialog.
- Import page (`import_page.py`) deferred to a later phase.
- Flowchart view deferred to Phase 6.

### Next: Phase 6 — Protocol Editor (QFormLayout step builder)

---

## Phase 6 — Protocol Editor ✅

**Commit**: `feat(phase-6): Protocol Editor — full step CRUD, reagents, reorder, save`

### New file

| File | Purpose |
|---|---|
| `qt_app/views/editor.py` | Full `EditorPage` — metadata card, step list, step form |

### Architecture

```
EditorPage (BasePage)
├── Top bar: ← Library  [protocol name]  [● Unsaved]  [Save Protocol]
├── _MetaCard
│   ├── Protocol Name (QLineEdit, bold)
│   ├── Category (QLineEdit)
│   ├── Description (QPlainTextEdit)
│   └── Tags  (_TagChip chips + add-tag input)
└── QSplitter (horizontal)
    ├── Left: step list (QScrollArea)
    │   ├── Header row + [＋ Add Step]
    │   └── _StepRow × N
    │       ├── Type-color dot, number, title, duration
    │       └── ▲ ▼ ⧉ ✕ action buttons
    └── Right: _StepForm (QScrollArea)
        ├── Title + Type (QComboBox, 25 types)
        ├── Timing  — Hands-on / Wait / Buffer (QDoubleSpinBox)
        ├── Conditions — Temperature / Centrifuge / Shaking (QLineEdit)
        ├── Description, Notes, Warnings (QPlainTextEdit)
        ├── Reagents  — _ReagentRow (name / amount / unit / ×)
        ├── Equipment — _ListItemRow items
        ├── Checklist — _ListItemRow items
        └── Substeps  — _ListItemRow items
```

### Step types supported (25)

`preparation`, `reagent_addition`, `pipetting`, `mixing`, `incubation`, `heating`,
`cooling`, `waiting`, `centrifuge`, `wash`, `transfer`, `resuspension`, `lysis`,
`measurement`, `staining`, `blocking`, `gel_running`, `electrophoresis`,
`membrane_transfer`, `imaging`, `harvest`, `sample_collection`, `storage`, `note`, `other`

### Save behavior

1. "Save Protocol" collects all form values (meta + current step) into the working copy
2. Finds the protocol by ID in `protocols.json`, replaces it, writes atomically
3. Emits `protocol_updated` on EventBus → Library refreshes
4. "Unsaved changes" indicator (orange ●) shown when any field is modified

### Unsaved-changes guard

Clicking "← Library" when dirty shows a dialog: **Save & Leave / Discard / Cancel**

### Library integration

- `_DetailPanel` "Edit Protocol" button (primary, blue) → `edit_requested` signal
- `LibraryPage._on_edit()` sets `app.state.selected_protocol_id` and navigates to "editor"
- New blank protocols created from Library jump directly into the editor
- "✎ Edit Protocol" is now the primary action for user protocols (was placeholder)

### CTk JSON compatibility

All saved fields use original CTk key names:
`handsOnMinutes`, `waitMinutes`, `bufferMinutes`, `centrifugeCondition`, `shakingRotation`,
`createdAt`, `updatedAt` — fully compatible with CTk `app.py` on `main`.

### Known limitations

- No drag-and-drop reorder (use ▲▼ buttons)
- No inline substep nesting (substeps stored as plain strings)
- No image/file attachment support
- Flowchart view deferred to Phase 6b

### Next: Phase 7 — Lab Notebook

---

## Phase 7 — Lab Notebook ✅

**Commit**: `Implement PySide6 Lab Notebook`

### Rewritten file

| File | Change |
|---|---|
| `qt_app/views/history.py` | Full rewrite — `_RecordCard`, `_DetailPanel`, `HistoryPage` |

### Architecture

```
HistoryPage (BasePage)
├── Header: "Lab Notebook" title + subtitle + [Export All (disabled)]
├── Toolbar: 🔍 search QLineEdit  |  Protocol filter QComboBox  |  count label
├── HSeparator
└── QSplitter (horizontal)
    ├── Left: record list (QScrollArea)
    │   ├── Date group headers (Today / Yesterday / Weekday · Month DD, YYYY)
    │   ├── session count badge per group
    │   └── _RecordCard × N
    │       ├── Title (bold) + actual duration
    │       ├── Protocol badge + HH:MM–HH:MM time range
    │       ├── Step dots (up to 24, color-coded) + completion %
    │       └── Observations snippet (first 90 chars)
    └── Right: _DetailPanel
        ├── Editable session title (QLineEdit)
        ├── Date/time range · duration
        ├── Protocol badge + category + tags
        ├── Stats row: Steps · Completed · Skipped · Incomplete (4 columns)
        ├── Progress bar (proportional, green at 100%)
        ├── Editable Observations/Summary (QPlainTextEdit)
        ├── Editable Additional Notes (QPlainTextEdit)
        ├── [Save Notes] button with ● Unsaved indicator
        ├── Step Records table: # | Title | Planned | Actual | Status
        ├── Timeline log (all events with timestamps)
        └── [Duplicate] [Delete] [Export (disabled)]
```

### Step Records table

| Column | Source | Notes |
|---|---|---|
| # | row index | |
| Step | `stepTitle` | |
| Planned | `plannedSecs` | formatted as Xh Ym |
| Actual | `usedSecs` | green if ≤ 110% planned; orange if over |
| Status | `status` | colored icon + label |

Step notes (from `stepRecord.notes`) shown as indented sub-row when non-empty.

### Search / Filter

- **Search**: live substring match across title, protocolName, observations, notes, tags
- **Protocol filter**: combo auto-populated from all loaded records

### Editing (backwards-compatible)

Fields written on "Save Notes":
- `title` — editable session title
- `observations` — primary notes (CTk reads this)
- `notes` — mirror of observations (CTk compat)
- `summary` — additional notes field (new, ignored by CTk)

No other CTk fields (`stepRecords`, `timeline`, `protocolSnapshot`, etc.) are modified.

### EventBus subscriptions

| Event | Action |
|---|---|
| `run_session_saved` | Reload if visible; restore selection |
| `notebook_record_created` | Reload if visible |

### Known limitations

- Export (PDF/DOCX) button is present but disabled — Phase 8
- No inline rich-text (bold/italic) in notes fields — Phase 8
- No tag editing in the detail panel — Phase 8

### Next: Phase 8 — Settings, PDF export, Tags manager

---

## Phase 8A — Flowchart ✅

**Commit**: `Implement PySide6 Flowchart view`

### Rewritten file

| File | Change |
|---|---|
| `qt_app/views/flowchart.py` | Full implementation — `_StepNode`, `_ArrowItem`, `_FlowchartView`, `_StepDetailPanel`, `FlowchartPage` |

### Architecture

```
FlowchartPage (BasePage)  —  3-pane QSplitter
│
├── Left (200 px): Protocol Selector
│   ├── "Protocols" header
│   ├── 🔍 search QLineEdit (live filter)
│   ├── QListWidget (protocol name + step count)
│   └── step count footer label
│
├── Center (stretch): Canvas
│   ├── Top bar: [⊞ Fit] [⊙ Center] [−] [zoom%] [＋] [1:1]
│   └── _FlowchartView (QGraphicsView + QGraphicsScene)
│       ├── _StepNode × N  (clickable)
│       └── _ArrowItem × N-1  (downward arrows)
│
└── Right (300 px): _StepDetailPanel
    ├── Placeholder (no step selected)
    └── Full step detail (title, type, timing, conditions,
        description/notes/warnings, reagents, equipment,
        checklist, substeps)
```

### _StepNode (264 × 90 px)

```
┌──────────────────────────────────────────────┐
║  ①  Step Title Here, wrapped to 2 lines max  ║
║     Preparation   ⏱ 45m                      ║
║     ● 37°C                                    ║
└──────────────────────────────────────────────┘
 ↑ 6 px type-color left accent strip
 ↑ Circular number badge (type-color background, white number)
```

- Accent strip and badge color comes from step type (25 types, same palette as editor)
- Title pre-wrapped to ≤2 lines using QFontMetrics; long lines elided with `…`
- Blue border highlight when selected (`_sel = True`)
- Tooltip shows full step title

### _ArrowItem

Simple downward `QPainterPath` line with an arrowhead (8px wide, 10px tip) pointing toward the next node. Rendered at Z = −1 (behind nodes).

### _FlowchartView

| Feature | How |
|---|---|
| Pan | `ScrollHandDrag` mode (drag canvas) |
| Zoom with wheel | `wheelEvent` → `scale()` |
| Fit View | `fitInView(bounding_rect + 24px margin, KeepAspectRatio)` |
| Center | `centerOn(scene.itemsBoundingRect().center())` |
| 1:1 reset | `setTransform(QTransform())` |
| Zoom range | 10%–500% |

### Library integration

`_DetailPanel` now has a **"⎇ View Flowchart"** secondary button for both user protocols and templates:
- `flowchart_requested = Signal(dict)` → `LibraryPage._on_flowchart()`
- Sets `app.state.selected_protocol_id` and navigates to `"flowchart"`

`FlowchartPage.on_show()` reads `selected_protocol_id`, auto-selects the matching item in the left list and renders its workflow.

### EventBus subscriptions

| Event | Action |
|---|---|
| `protocol_created/updated/deleted` | Reload protocol list; re-render if current protocol changed |

### Known limitations

- Linear layout only (no branch / decision nodes)
- No drag-to-edit or rearrange nodes
- No horizontal / swimlane layouts yet
- Export (PNG/PDF) of flowchart nodes deferred to a future phase

### Next: Phase 8B — Export and Import foundation

---

## Phase 8B — Export and Import ✅

**Commit**: `Add PySide6 export and import foundation`

### What was built

#### `qt_app/services/export_service.py` (new)

Full export back-end for both Lab Notebook sessions and Protocols:

| Function | Output | Dependency |
|---|---|---|
| `export_notebook_json(record, path)` | JSON wrapper | stdlib |
| `export_notebook_pdf(record, path)` | PDF report | reportlab |
| `export_notebook_docx(record, path)` | Word document | python-docx |
| `export_protocol_json(protocol, path)` | JSON wrapper | stdlib |
| `export_protocol_markdown(protocol, path)` | Markdown file | stdlib |
| `export_protocol_pdf(protocol, path)` | PDF report | reportlab |

Helper functions:
- `notebook_default_name(record, fmt)` → `"BenchFlow_<Title>_<YYYY-MM-DD>.pdf"`
- `protocol_default_name(protocol, fmt)` → `"BenchFlow_Protocol_<Name>.json"`
- `ExportDependencyError` raised when optional dep (reportlab / python-docx) is missing; callers catch and show toast with `pip install` instructions

#### Export buttons (UI)

- **Lab Notebook** (`history.py`): `_DetailPanel` — disabled export button replaced with active `📤 Export ▾` QMenu (PDF Report / Word Document / JSON Data); `HistoryPage` handles `export_requested(dict, str)` signal via `_on_export_record()`
- **Library** (`library.py`): `_DetailPanel` — `📤 Export ▾` QMenu (JSON / Markdown / PDF) added after action buttons for both protocols and templates; `LibraryPage` handles via `_on_export_protocol()`
- **Protocol Editor** (`editor.py`): top bar — `📤 Export ▾` button added between dirty indicator and Save; `_on_export()` shows QMenu; `_do_export()` calls export_service with file dialog

All export handlers:
1. Call `export_service.<fn>_default_name()` to suggest a filename
2. Open `QFileDialog.getSaveFileName()` at that default
3. Call the appropriate export function
4. Show `ToastManager.show_success()` on success or `show_error()` on failure

#### Import page (`import_page.py`, full rewrite)

4-method selector on the left (card UI):

| Method | Status | Description |
|---|---|---|
| 📁 JSON File | ✅ Active | `QFileDialog` → parse → preview |
| 📋 Paste Text | ✅ Active | textarea → JSON or plain-text parser → preview |
| 📄 PDF | Coming Soon | stub |
| 📝 Word Doc | Coming Soon | stub |

JSON parser: accepts bare protocol dict or `{protocol: {...}}` wrapper from export_service  
Plain-text parser: first line → name, numbered/bulleted lines → step titles

Preview panel (shared):
- Editable protocol name
- Step count + category stats
- Scrollable step list (capped at 50 shown)
- `⊕ Save to My Protocols` button — deduplicates name, saves to `protocols.json`, emits `protocol_created`, navigates to Library

### Limitations / deferred
- Notebook JSON import (parse runs.json entries) — future phase
- Flowchart PNG export — future phase
- Bulk export of all sessions — future phase

---

## Phase 9 — Settings and Packaging Readiness ✅

**Commit**: `Add PySide6 settings and packaging readiness`

### What was built

#### `qt_app/views/settings.py` (full rewrite)

Five card sections:

| Section | Contents |
|---------|---------|
| **App Info** | Version badge · data folder path (monospace, selectable) · Open Folder button · GitHub link |
| **Preferences** | Theme (dark, placeholder) · Autosave interval QSpinBox (5–300 s) · Session recovery status |
| **Export Dependencies** | reportlab status badge (✓ Installed / ✗ Missing) · python-docx status badge · `pip install` hint if missing |
| **Active Session** | ⊗ Reset Active Session (danger button, confirmation dialog) |
| **Backup & Restore** | 📦 Backup All Data → `QFileDialog.getSaveFileName` → ZIP · 📂 Restore from Backup → `QFileDialog.getOpenFileName` → validates + restores |

Design: card-style rows (key–value + note columns), `HSeparator` between rows, matching dark theme. Each card is a `QFrame` with `BG_CARD` + rounded border.

#### `qt_app/services/data.py` additions

Two new public methods on `DataService`:

```python
def export_all_data(self, zip_path: str) -> dict[str, int]:
    # Writes protocols.json, runs.json, categories.json, tags.json,
    # schedule.json, scheduled_experiments.json, runtime_session.json
    # + _benchflow_backup_meta.json manifest inside the ZIP
    # Returns {filename: byte_size} for each included file

def restore_all_data(self, zip_path: str) -> list[str]:
    # Validates _benchflow_backup_meta.json presence
    # Creates .pre_restore_<timestamp>.json backups of existing files
    # Writes restored files to APP_DIR
    # Raises ValueError if not a BenchFlow backup ZIP
    # Returns list of restored filenames
```

Also added `_APP_VERSION` constant (read from `VERSION` file at startup) used in the backup manifest.

#### `qt_app/services/app_state.py` addition

```python
self.autosave_interval_s: int = 30   # user-configurable via Settings page
```

#### Packaging files (new)

| File | Purpose |
|------|---------|
| `BenchFlow_Qt.spec` | PyInstaller spec for the Qt app (`qt_app/main.py` entry point; bundles PySide6, reportlab, python-docx, templates/, VERSION) |
| `build_qt_mac.sh` | macOS build script — checks Python/PyInstaller/PySide6, builds `.app`, creates `.dmg`, copies to `releases/` |
| `build_qt_windows.bat` | Windows build script — same flow, produces `.exe` + `.zip` |
| `requirements_qt.txt` | `PySide6>=6.6`, `reportlab>=4.0`, `python-docx>=1.1`, `pyinstaller>=6.0` |

### Running the Qt app

```bash
git checkout qt-prototype
pip install -r requirements_qt.txt
python3 qt_app/main.py
```

### Building a distributable

```bash
# macOS
chmod +x build_qt_mac.sh
./build_qt_mac.sh
# → dist/mac_qt/BenchFlow.app  +  releases/BenchFlow-Qt-v0.1.0-macOS.dmg

# Windows
build_qt_windows.bat
# → dist\win_qt\BenchFlow_Qt\BenchFlow_Qt.exe  +  releases\BenchFlow-Qt-v0.1.0-Windows.zip
```

### Known issues / remaining before Phase 10 cutover

| Issue | Notes |
|-------|-------|
| No app icon for Qt build | `AppIcon.icns` from CTk build needs adapting; add to `BenchFlow_Qt.spec` `icon=` |
| GitHub Actions not updated for Qt | `.github/workflows/build.yml` still targets `app.py` / CTk spec |
| Windows `APP_DIR` hardcoded to macOS path | `data.py` uses `~/Library/Application Support/BenchFlow/` — needs `%APPDATA%/BenchFlow/` on Windows |
| Settings preferences not persisted across restarts | `autosave_interval_s` lives in AppState (in-memory); add JSON preferences file in Phase 10 |
| Categories/Tags manager not implemented | Placeholder section in Settings; full manager deferred to Phase 10 |
| No light theme | Theme preference UI is present but non-functional; Phase 10 |

---

## File Structure

```
qt_app/
├── __init__.py
├── main.py                  # Entry point
├── app.py                   # BenchFlowApp(QMainWindow)
├── theme.py                 # Colors, Fonts, QSS, apply_theme()
│
├── models/
│   ├── __init__.py
│   ├── protocol.py          # Protocol, Step dataclasses
│   ├── schedule.py          # ScheduleBlock dataclass
│   └── session.py           # RunRecord, StepRecord, RuntimeSession, StepRuntimeState
│
├── services/
│   ├── __init__.py
│   ├── data.py              # DataService — all JSON I/O
│   ├── app_state.py         # AppState(QObject) — cross-page state + signals  [4.75]
│   ├── event_bus.py         # _EventBus singleton (bus) — pub/sub dispatcher  [4.75]
│   ├── background.py        # BackgroundTaskManager (bg) — debounce + flush   [4.75]
│   ├── error_handler.py     # _ErrorHandler (eh) — safe_call, log_exception   [4.75]
│   ├── perf.py              # _Perf (perf) — context-manager perf logging      [4.75]
│   ├── run_service.py       # RunModeSession, StepRunState helpers
│   └── export_service.py    # ✅ PDF/DOCX/JSON/MD export (Phase 8B)
│
├── components/
│   ├── __init__.py
│   ├── sidebar.py           # Sidebar(QWidget) with nav_requested signal
│   ├── widgets.py           # PrimaryButton, Card, Badge, HSeparator, etc.
│   ├── step_card.py         # StepCard — run-mode step widget
│   └── toast.py             # ToastManager — floating bottom-right toasts      [4.75]
│
├── dialogs/
│   ├── new_protocol.py      # NewProtocolDialog (Blank/Template/Duplicate)     [5]
│   ├── add_block.py         # AddBlockDialog — add temp block in Run Mode
│   └── restore_session.py   # RestoreSessionDialog — resume active session
│
└── views/
    ├── __init__.py
    ├── base_page.py         # BasePage(QWidget) — app ref + on_show() hook
    ├── _placeholder.py      # Generic placeholder for unimplemented pages
    ├── dashboard.py         # ✅ Real data, EventBus reactive refresh
    ├── library.py           # ✅ Protocols + Templates (full Phase 5)          [5]
    ├── run_mode.py          # ✅ Full run mode — timers, sequential, autosave
    ├── schedule.py          # ✅ Calendar + timeline editor
    ├── history.py           # ✅ Lab Notebook — full Phase 7 (date list, detail, edit)
    ├── editor.py            # ✅ Full Protocol Editor (Phase 6)
    ├── flowchart.py         # ✅ Flowchart — QGraphicsScene (Phase 8A)
    ├── import_page.py       # ✅ Import — JSON file + paste text (Phase 8B)
    └── settings.py          # ✅ Settings — data folder, prefs, deps, backup (Phase 9)
```

**Repo-level packaging files (Phase 9):**
```
BenchFlow_Qt.spec       PyInstaller spec for Qt build (qt_app/main.py)
build_qt_mac.sh         macOS build script (PySide6 version)
build_qt_windows.bat    Windows build script (PySide6 version)
requirements_qt.txt     PySide6 + optional export dependencies
```
