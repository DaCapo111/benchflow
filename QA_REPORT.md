# BenchFlow UI/UX QA Report
**Date:** 2026-05-22  
**Audited file:** `app.py` (7 141 lines)  
**Status:** All Priority-1 and Priority-2 issues fixed.

---

## Pages Audited

| Page | Status |
|---|---|
| Dashboard | ✅ No issues |
| Library — My Protocols | ✅ Fixed (description ellipsis) |
| Library — Templates | ✅ No issues |
| Protocol Editor | ✅ No issues |
| Step Editor Dialog | ✅ No issues |
| Flowchart | ✅ Fixed (title wrap + wheel) |
| Run Mode | ✅ Fixed (temp block state + sidebar truncation) |
| Add Temporary Block Dialog | ✅ No issues |
| Finish / Save Session Dialogs | ✅ No issues |
| Lab Notebook (History) | ✅ Fixed (observation wraplength) |
| Settings | ✅ No issues |
| Schedule / Calendar | ✅ No issues |
| Schedule — Detail Panel | ✅ No issues |
| Import (Phase 1 + Phase 2) | ✅ No issues |
| Create Protocol Dialog | ✅ No issues |
| MiniCalendarPicker | ✅ No issues |
| BlockEditDialog | ✅ No issues |
| ScheduleBlockDialog | ✅ No issues |
| SkipBlockDialog | ✅ No issues |

---

## Fixes Applied

### P1-01 — FlowchartPage: Node title hard-truncated at 26 chars
**File:** `app.py` — `FlowchartPage._draw_graph()`  
**Root cause:** `if len(title) > 26: title = title[:26] + "…"` was too aggressive for a 220 px node. A 12 pt bold character is ~7 px wide; 26 chars ≈ 182 px, but NODE_W − padding = 196 px, giving ~28 chars. Longer titles from templates (e.g. "Add Streptavidin-HRP (if using biotinylated detection antibody)" = 62 chars) were truncated to the point of being unreadable.  
**Fix:**
- Raised `NODE_H` from 90 → 96 px to accommodate a potential 2-line title.
- Removed the hard 26-char cutoff; replaced with a safety cap at 64 chars.
- Added `width=NODE_W-24` to `canvas.create_text()` so Tk wraps text within the node instead of overflowing or clipping.
- Moved the time/conditions row from `y+68` → `y+80` to clear a 2-line title block.
- Adjusted title y from `y+45` → `y+46` (centred between badge at y+26 and info at y+80).

### P1-02 — FlowchartPage: Mouse wheel scrolls only ±1 unit
**File:** `app.py` — `FlowchartPage._build()`  
**Root cause:** The old binding used `1 if e.delta>0 else -1` which produces exactly 1 unit per event, making the flowchart feel very stiff on trackpads.  
**Fix:**
- Added `_fc_wheel()` method with the same proportional delta logic used by `ScrollFrame` and `SchedulePage`:  physical mouse wheel → ±3 units/notch; trackpad → `delta/3` units (proportional, minimum ±1).
- Added `<Button-4>` / `<Button-5>` bindings for Linux.

### P1-03 — RunPage: Temporary block `new_state` dict missing ~15 required keys
**File:** `app.py` — `RunPage._add_temp_block()`  
**Root cause:** When a user adds a block mid-run via "Add Block During Run", the state dict created for it was missing: `start_mono`, `start_remaining`, all `ho_*` (hands-on stopwatch) fields, `_pre_complete_status`, `_undo_job`, `_ctrl_norm`, `_ctrl_done`, `_undo_lbl`, `_ctrl_container`. All downstream timer, undo, and control-swap logic calls `.get()` on these keys — so there were no crashes, but the undo countdown, hands-on tracking, and "done controls" swap would silently fail to work for temp blocks.  
Also, `timer_secs` was stored as `int` instead of `float`, which could cause precision issues in wall-clock calculations.  
**Fix:** Added all missing keys to the `new_state` dict with safe defaults, and changed `timer_secs` / `start_remaining` to `float`.

### P2-01 — LibraryPage: Protocol description cut at 80 chars without "…"
**File:** `app.py` — `LibraryPage._proto_card()`  
**Root cause:** `p["description"][:80]` silently drops everything past character 80 with no visual indicator to the user.  
**Fix:** Added conditional ellipsis: `(_desc[:80] + "…") if len(_desc) > 80 else _desc`.

### P2-02 — HistoryPage: Observation text not wrapped
**File:** `app.py` — `HistoryPage._session_card()`  
**Root cause:** `CTkLabel` defaults to `wraplength=0` (no wrapping). Long single-line observations would overflow horizontally beyond the card boundary.  
**Fix:** Added `wraplength=640` to the observation label.

### P2-03 — RunPage sidebar: Step title truncated to 18 chars with no ellipsis
**File:** `app.py` — `RunPage._proto_step_row()`  
**Root cause:** `step.get('title')[:18]` silently cuts the title. The sidebar left panel is ~200 px wide; at 10 pt font (~6.5 px/char) that allows ~28 chars. 18 is too short for many protocol titles.  
**Fix:** Raised limit to 22 chars and appended "…" when truncated.

---

## No-action Items (reviewed, no change needed)

| Area | Observation |
|---|---|
| ScrollFrame double-scroll | Fixed in a previous session. Single handler replaces CTk canvas binding; pre-marked to prevent recursive rebind. ✅ |
| ScrollFrame `_refresh_scroll_bindings` every 5 s | Harmless; ensures newly added child widgets get bindings. Performance cost is negligible. |
| StepEditorDialog layout | Fixed-header + ScrollFrame body pattern is correct. |
| SchedulePage canvas wheel | Already uses proper delta math (`_canvas_wheel`). |
| Detail panel wraplength=210 | Panel is 300 px wide; wraplength=210 leaves 45 px margin each side — correct. |
| RunPage `_scroll_to_step` | Uses `card.winfo_y() / frame.winfo_height()` — consistent with how CTkScrollableFrame exposes its content height. |
| DashboardPage | Clean grid layout, no overflow or scroll issues. |
| SettingsPage | ScrollFrame-wrapped, no issues. |
| ImportPage split-pane | Phase 1 / Phase 2 stack via `tkraise()`; source text widget has its own scrollbar. Both correct. |
| LibraryPage Templates | Disclaimer banner, category groups, tag pills, "Use Template" deep-copy all verified correct. |

---

## Summary

| Priority | Total found | Fixed | Deferred |
|---|---|---|---|
| P1 (bugs / data errors) | 3 | 3 | 0 |
| P2 (UI layout / truncation) | 3 | 3 | 0 |
| P3 (polish / no-action) | 8 | 0 | 8 (no change needed) |
