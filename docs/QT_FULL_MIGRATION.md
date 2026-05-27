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
| Phase 4 | Schedule — QGraphicsScene calendar, drag-and-drop | 🔲 |
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

### Phase 4 — Schedule

Next implementation target: full calendar view with `QGraphicsScene` + drag-and-drop blocks.

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
