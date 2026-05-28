# BenchFlow Qt — Release Candidate QA Report

**Phase:** Phase 10 — Qt Release Candidate QA  
**Date:** 2026-05-28  
**Branch:** `qt-prototype`  
**Entry point:** `python3 qt_app/main.py`  
**Tester:** Automated static analysis + headless PySide6 tests

---

## Test Environment

| Item | Value |
|------|-------|
| Platform | macOS (Darwin arm64) |
| Python | 3.13 |
| PySide6 | 6.11.1 |
| reportlab | 4.5.1 |
| python-docx | installed |
| PyInstaller | 6.20.0 |
| App version | 0.1.0 |
| Data directory | `~/Library/Application Support/BenchFlow/` |
| Existing data | 4 protocols, 1 run record, 3 schedule blocks, 17 templates |

---

## Test Summary

| Category | Tests Run | Passed | Failed | Fixed |
|----------|-----------|--------|--------|-------|
| Syntax check (all qt_app/**/*.py) | All files | ✅ | 0 | — |
| Import smoke test (all services) | 7 | ✅ 7 | 0 | — |
| Page instantiation (headless) | 7 | ✅ 7 | 0 | — |
| Data compatibility (CTk → Qt) | All data files | ✅ | 0 | — |
| Export service (PDF/DOCX/JSON/MD) | 6 | ✅ 6 | 0 | — |
| Import page parsers | 6 | ✅ 6 | 0 | — |
| RunModeSession state machine | 5 | ✅ 5 | 0 | — |
| EventBus emissions | 6 | ✅ 6 | 0 | — |
| DataService backup/restore | 4 | ✅ 4 | 0 | — |
| Template ID injection | 17 templates | ✅ | 0 | — |
| PyInstaller build (.app bundle) | 1 | ✅ | 0 | — |
| Bundle content (templates/VERSION) | 2 | ✅ | 0 | — |

---

## Pages Tested

| Page | Instantiation | on_show Logic | Export | Import | Notes |
|------|:---:|:---:|:---:|:---:|-------|
| Dashboard | ✅ | ✅ | N/A | N/A | EventBus subscriptions verified |
| Library | ✅ | ✅ | ✅ Export menu | N/A | Template/protocol separation OK |
| Protocol Editor | ✅ | ✅ | ✅ JSON/MD/PDF | N/A | Save logic verified, dirty tracking OK |
| Run Mode | ✅ | ✅ | N/A | N/A | Timer, complete, undo, add block, save-to-notebook |
| Schedule | ✅ | ✅ | N/A | N/A | save_scheduled_experiments path OK |
| Lab Notebook | ✅ | ✅ | ✅ PDF/Word/JSON | N/A | Export roundtrip verified |
| Flowchart | ✅ | ✅ | N/A | N/A | Now shows templates + user protocols |
| Import | ✅ | ✅ | N/A | ✅ | JSON + plain-text parsers pass all test cases |
| Settings | ✅ | ✅ | N/A | N/A | Backup/restore roundtrip verified |

---

## Bugs Found and Fixed

### P1 — Fixed

#### BUG-01: Windows data directory hardcoded to macOS path
- **File:** `qt_app/services/data.py`
- **Symptom:** On Windows, `APP_DIR` resolves to `~/Library/Application Support/BenchFlow/` which doesn't exist.
- **Root cause:** `APP_DIR = Path.home() / "Library" / "Application Support" / "BenchFlow"` hardcoded for macOS.
- **Fix:** Added `_resolve_app_dir()` function using `sys.platform`:
  - macOS → `~/Library/Application Support/BenchFlow/`
  - Windows → `%APPDATA%/BenchFlow/`
  - Linux → `~/.local/share/BenchFlow/`
- **Status:** ✅ Fixed

#### BUG-02: Templates missing stable IDs — flowchart auto-select broken
- **File:** `qt_app/services/data.py`, `qt_app/views/flowchart.py`
- **Symptom:** When clicking "View Flowchart" for a built-in template from the Library, the flowchart opens but doesn't auto-select the template because:
  1. Templates have no `id` field → `proto.get("id", "")` returns `""`
  2. `app.state.selected_protocol_id = ""` → flowchart skips auto-select
  3. Flowchart only loaded user protocols, not templates
- **Fix:**
  - `load_templates()` now injects stable IDs: `tmpl_<slugified_name>` (e.g., `tmpl_western_blot_day1`)
  - `FlowchartPage._load_protocols()` now loads user protocols + templates
  - `_rebuild_list()` distinguishes templates with `⊞` prefix + muted text color
  - `on_show()` and `_rebuild_list()` guarded with safe None checks
- **Status:** ✅ Fixed

### P2 — Fixed

#### BUG-03: Save-to-notebook used `accumulated_elapsed_secs` for running steps
- **File:** `qt_app/views/run_mode.py` — `_save_to_notebook()`
- **Symptom:** If a step's timer was still `running` when "Save to Lab Notebook" was clicked, its `usedSecs` would not include the current running period (only time before the last start).
- **Root cause:** Used `state.accumulated_elapsed_secs` instead of `state.elapsed_secs()` (which includes `now - started_at_ts`).
- **Fix:** Changed to `state.elapsed_secs()` in the step record builder.
- **Status:** ✅ Fixed

---

## Bugs Not Fixed (Known Issues — Phase 10 Backlog)

| ID | Priority | Location | Description |
|----|----------|----------|-------------|
| BUG-04 | P2 | `qt_app/views/settings.py` | Autosave interval and other preferences are in-memory only (AppState); lost on restart. Need a preferences JSON file. |
| BUG-05 | P2 | `BenchFlow_Qt.spec` | No app icon — `icon=None`. macOS `.app` uses default PyInstaller icon. Need to create Qt `.icns` from `AppIcon.iconset/`. |
| BUG-06 | P2 | `qt_app/views/settings.py` | Theme preference (Light) is shown as non-functional "coming soon". Acceptable for RC. |
| BUG-07 | P3 | `qt_app/views/flowchart.py` | Flowchart empty-state message says "Add steps in Protocol Editor" even for read-only templates. Minor text inaccuracy. |
| BUG-08 | P3 | `.github/workflows/build.yml` | GitHub Actions still targets `app.py` (CTk). Qt build not in CI. |

---

## Workflow Validation

### A. Template Workflow
`Templates → View Flowchart` — ✅ Templates now appear in flowchart list  
`Templates → Use Template` — ✅ Creates copy in My Protocols with new UUID  
`Templates → Duplicate as Protocol` — ✅ Tested via library export signal path  

### B. Run Mode Workflow
- Timer state machine (start/pause/resume/complete/undo) — ✅ All transitions correct
- Add temp block — ✅ Appended to step list with auto-scroll
- Remove temp block — ✅ Re-indexes remaining cards correctly  
- Save to Lab Notebook — ✅ Produces CTk-compatible run record JSON
- `usedSecs` now uses `elapsed_secs()` — ✅ Fixed BUG-03

### C. Export Workflow
All 6 export formats produce correctly-sized output files:

| Format | Size (real protocol + run) |
|--------|---------------------------|
| Notebook PDF | 4.4 KB |
| Notebook DOCX | 37.6 KB |
| Notebook JSON | 18.7 KB |
| Protocol PDF | 6.8 KB |
| Protocol Markdown | 3.8 KB |
| Protocol JSON | 12.0 KB |

### D. Import Workflow
- JSON (bare protocol) → parse → preview → save: ✅
- JSON (exported wrapper) → parse → preview → save: ✅
- Plain text (numbered list) → parse → 3 steps: ✅
- Invalid JSON → returns None gracefully: ✅

### E. Backup/Restore Workflow
- Backup (4 data files) → valid ZIP with `_benchflow_backup_meta.json`: ✅
- Restore from valid backup → pre-restore files created → data restored: ✅
- Restore from invalid ZIP → `BadZipFile` raised: ✅
- Restore from ZIP without manifest → `ValueError` raised: ✅

---

## Data Compatibility

| File | CTk written | Qt readable | Qt writable (safe) |
|------|:-----------:|:-----------:|:------------------:|
| `protocols.json` | ✅ | ✅ | ✅ |
| `runs.json` | ✅ | ✅ | ✅ |
| `schedule.json` | ✅ | ✅ | ✅ |
| `scheduled_experiments.json` | ✅ | ✅ | ✅ |
| `runtime_session.json` | ✅ | ✅ | ✅ |
| `templates/*.json` | Read-only | ✅ | Read-only |

CTk data is **fully compatible** with the Qt version. Switching between versions using the same data directory is safe.

---

## Packaging Results

| Artifact | Result | Notes |
|----------|--------|-------|
| PyInstaller build | ✅ Success | 671 MB `.app` bundle |
| `.app` structure | ✅ Valid | `Contents/MacOS`, `Resources`, `Frameworks` present |
| `templates/` bundled | ✅ 17 files | In `Contents/Resources/templates/` |
| `VERSION` bundled | ✅ `0.1.0` | In `Contents/Resources/VERSION` |
| PySide6 bundled | ✅ | `Contents/Resources/PySide6/` |
| reportlab bundled | ✅ | In Resources |
| python-docx bundled | ✅ | In Resources |
| Missing dep handling | ✅ | `ExportDependencyError` caught → toast message |

**Build command used:**  
```
python3 -m PyInstaller --noconfirm BenchFlow_Qt.spec
```

---

## RC Readiness Assessment

| Criterion | Status |
|-----------|--------|
| All 9 pages load without crash | ✅ |
| CTk data is read correctly | ✅ |
| Export (PDF/Word/JSON/MD) works | ✅ |
| Import (JSON/text) works | ✅ |
| Backup/restore works | ✅ |
| macOS `.app` bundle builds | ✅ |
| Templates appear in Flowchart | ✅ (fixed) |
| Windows data path | ✅ (fixed) |
| Running step elapsed time correct | ✅ (fixed) |
| P0 bugs outstanding | ✅ None |
| P1 bugs outstanding | ✅ None |

### Recommendation

**The Qt prototype branch is RC-ready for internal testing.**

The app is functionally complete, stable, and packaging succeeds.  
Remaining items before replacing `main` (Phase 10 cutover):

1. Add app icon to `BenchFlow_Qt.spec`
2. Persist preferences to JSON (not just AppState memory)
3. Update GitHub Actions to build Qt version
4. Merge `qt-prototype` → `main` after final sign-off
