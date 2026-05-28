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
| Phase 5 | Library + Protocol Editor + Import | 🔲 |
| Phase 6 | Flowchart (QGraphicsScene + arrow connectors) | 🔲 |
| Phase 7 | Lab Notebook — rich text (QTextEdit), PDF/DOCX export | 🔲 |
| Phase 8 | Settings, Categories/Tags manager | 🔲 |
| Phase 9 | Cutover — remove CTk from distribution, update BenchFlow.spec | 🔲 |

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
│   └── data.py              # DataService — all JSON I/O
│
├── components/
│   ├── __init__.py
│   ├── sidebar.py           # Sidebar(QWidget) with nav_requested signal
│   └── widgets.py           # PrimaryButton, Card, Badge, HSeparator, etc.
│
└── views/
    ├── __init__.py
    ├── base_page.py         # BasePage(QWidget) — app ref + on_show() hook
    ├── _placeholder.py      # Generic placeholder for unimplemented pages
    ├── dashboard.py         # ✅ Real data
    ├── library.py           # ✅ Protocols + Templates
    ├── run_mode.py          # ✅ Protocol list + read-only step cards
    ├── schedule.py          # ✅ Schedule list
    ├── history.py           # ✅ Lab Notebook (run records)
    ├── editor.py            # Placeholder → Phase 5
    ├── flowchart.py         # Placeholder → Phase 6
    ├── import_page.py       # Placeholder → Phase 5
    └── settings.py          # Placeholder → Phase 8
```
