"""
DataService
===========
Singleton that owns all BenchFlow persistence.

Data directory:  ~/Library/Application Support/BenchFlow/
Templates:       <repo>/templates/*.json  (read-only, shipped with app)

Design
------
- All writes are atomic: write temp → os.replace()
- Corrupt JSON is backed-up and treated as empty (app never crashes on bad data)
- All public methods return plain Python objects (list / dict / None)
  so views don't need to import models to call the service

Data file catalogue
-------------------
protocols.json        List[ProtocolDict]
runs.json             List[RunRecordDict]
categories.json       List[str]
tags.json             List[str]
schedule.json         List[ScheduleBlockDict]
runtime_session.json  RuntimeSessionDict | {}
"""
from __future__ import annotations

import json
import os
import shutil
import sys
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Any

# ── Data directory ─────────────────────────────────────────────────────────────
APP_DIR = Path.home() / "Library" / "Application Support" / "BenchFlow"
APP_DIR.mkdir(parents=True, exist_ok=True)

PROTOCOLS_FILE        = APP_DIR / "protocols.json"
RUNS_FILE             = APP_DIR / "runs.json"
CATEGORIES_FILE       = APP_DIR / "categories.json"
TAGS_FILE             = APP_DIR / "tags.json"
SCHEDULE_FILE         = APP_DIR / "schedule.json"
SCHEDULED_EXP_FILE    = APP_DIR / "scheduled_experiments.json"
RUNTIME_FILE          = APP_DIR / "runtime_session.json"

# Templates: repo root / templates/*.json  (read-only)
_APP_BASE = (Path(sys._MEIPASS)          # type: ignore[attr-defined]
             if getattr(sys, "frozen", False)
             else Path(__file__).parent.parent.parent)
TEMPLATES_DIR = _APP_BASE / "templates"

# App version — read from VERSION file at repo root, fallback "0.1.0"
def _read_version() -> str:
    vf = _APP_BASE / "VERSION"
    try:
        return vf.read_text(encoding="utf-8").strip()
    except Exception:
        return "0.1.0"

_APP_VERSION: str = _read_version()


# ── Low-level helpers ──────────────────────────────────────────────────────────

def _load_json(path: Path, default: Any = None) -> Any:
    """Load JSON from *path*.

    If the file is missing → return *default*.
    If the file is corrupt → back it up, return *default*.
    """
    fallback = default if default is not None else []
    if not path.exists():
        return fallback
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        # Backup the corrupt file so the user's data isn't silently lost
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup = path.with_suffix(f".corrupt_{ts}.json")
        try:
            shutil.copy2(path, backup)
        except Exception:
            pass
        return fallback


def _save_json(path: Path, data: Any) -> None:
    """Atomically write *data* as JSON to *path*.

    Writes to a temp file first, then os.replace() for crash-safety.
    """
    tmp = path.with_suffix(".tmp")
    try:
        tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        os.replace(tmp, path)
    except Exception:
        try:
            tmp.unlink(missing_ok=True)
        except Exception:
            pass
        raise


def _load_terms(path: Path) -> list[str]:
    data = _load_json(path, [])
    if isinstance(data, list):
        return sorted({str(x).strip() for x in data if str(x).strip()})
    return []


def _save_terms(path: Path, terms: list[str]) -> None:
    _save_json(path, sorted({str(x).strip() for x in terms if str(x).strip()}))


# ── DataService ────────────────────────────────────────────────────────────────

class DataService:
    """Manages all BenchFlow data I/O.

    Instantiate once in BenchFlowApp and pass (or use via app.data).
    All methods return plain Python dicts/lists — no model imports needed.
    """

    # ── Protocols ──────────────────────────────────────────────────────────────

    def load_protocols(self) -> list[dict[str, Any]]:
        data = _load_json(PROTOCOLS_FILE, [])
        return data if isinstance(data, list) else []

    def save_protocols(self, protocols: list[dict[str, Any]]) -> None:
        _save_json(PROTOCOLS_FILE, protocols)

    # ── Run records (Lab Notebook) ─────────────────────────────────────────────

    def load_runs(self) -> list[dict[str, Any]]:
        data = _load_json(RUNS_FILE, [])
        return data if isinstance(data, list) else []

    def save_runs(self, runs: list[dict[str, Any]]) -> None:
        _save_json(RUNS_FILE, runs)

    # Alias used by Notebook / History pages
    load_notebook_records = load_runs
    save_notebook_records = save_runs
    load_run_sessions = load_runs
    save_run_sessions = save_runs

    # ── Categories ─────────────────────────────────────────────────────────────

    def load_categories(self) -> list[str]:
        return _load_terms(CATEGORIES_FILE)

    def save_categories(self, categories: list[str]) -> None:
        _save_terms(CATEGORIES_FILE, categories)

    # ── Tags ───────────────────────────────────────────────────────────────────

    def load_tags(self) -> list[str]:
        return _load_terms(TAGS_FILE)

    def save_tags(self, tags: list[str]) -> None:
        _save_terms(TAGS_FILE, tags)

    # ── Schedule ───────────────────────────────────────────────────────────────

    def load_schedule(self) -> list[dict[str, Any]]:
        data = _load_json(SCHEDULE_FILE, [])
        return data if isinstance(data, list) else []

    def save_schedule(self, schedule: list[dict[str, Any]]) -> None:
        _save_json(SCHEDULE_FILE, schedule)

    # ── Scheduled experiments (PySide6 calendar) ───────────────────────────────

    def load_scheduled_experiments(self) -> list[dict[str, Any]]:
        """Load scheduled_experiments.json (Qt-native format)."""
        data = _load_json(SCHEDULED_EXP_FILE, [])
        return data if isinstance(data, list) else []

    def save_scheduled_experiments(self, experiments: list[dict[str, Any]]) -> None:
        _save_json(SCHEDULED_EXP_FILE, experiments)

    # ── Templates (built-in, read-only) ───────────────────────────────────────

    def load_templates(self) -> list[dict[str, Any]]:
        """Load all *.json files from the templates/ directory."""
        if not TEMPLATES_DIR.exists():
            return []
        templates: list[dict[str, Any]] = []
        for f in sorted(TEMPLATES_DIR.glob("*.json")):
            try:
                t = json.loads(f.read_text(encoding="utf-8"))
                if isinstance(t, dict) and t.get("name"):
                    templates.append(t)
            except Exception:
                pass
        templates.sort(key=lambda t: (t.get("category", ""), t.get("name", "")))
        return templates

    # ── Runtime / active session ───────────────────────────────────────────────

    def load_active_session(self) -> dict[str, Any] | None:
        """Return the crash-recovery checkpoint, or None if none exists."""
        data = _load_json(RUNTIME_FILE, None)
        if isinstance(data, dict) and data:
            return data
        return None

    def save_active_session(self, session: dict[str, Any]) -> None:
        _save_json(RUNTIME_FILE, session)

    def clear_active_session(self) -> None:
        try:
            RUNTIME_FILE.unlink(missing_ok=True)
        except Exception:
            pass

    # Aliases used by older code paths
    load_runtime_session  = load_active_session
    save_runtime_session  = save_active_session
    discard_runtime_session = clear_active_session

    # ── Backup / Restore ───────────────────────────────────────────────────────

    def export_all_data(self, zip_path: str) -> dict[str, int]:
        """Write a ZIP archive containing all user data files.

        Returns a dict of ``{filename: byte_size}`` for every file included.
        Raises ``OSError`` on write failure.
        """
        _data_files = [
            PROTOCOLS_FILE,
            RUNS_FILE,
            CATEGORIES_FILE,
            TAGS_FILE,
            SCHEDULE_FILE,
            SCHEDULED_EXP_FILE,
            RUNTIME_FILE,
        ]
        ts = datetime.now().strftime("%Y-%m-%d_%H%M%S")
        manifest: dict[str, int] = {}

        with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            # Write manifest header
            meta = {
                "benchflow_backup": True,
                "created_at": ts,
                "app_version": _APP_VERSION,
                "files": [],
            }
            for f in _data_files:
                if f.exists():
                    arc_name = f.name
                    zf.write(f, arc_name)
                    size = f.stat().st_size
                    manifest[arc_name] = size
                    meta["files"].append(arc_name)
            zf.writestr("_benchflow_backup_meta.json",
                        json.dumps(meta, indent=2))
        return manifest

    def restore_all_data(self, zip_path: str) -> list[str]:
        """Restore user data from a backup ZIP.

        - Creates per-file backups of existing data before overwriting.
        - Returns list of restored filenames.
        - Raises ``ValueError`` if ZIP is not a BenchFlow backup.
        - Raises ``OSError`` on read/write failure.
        """
        _allowed = {
            "protocols.json", "runs.json", "categories.json",
            "tags.json", "schedule.json", "scheduled_experiments.json",
            "runtime_session.json",
        }
        with zipfile.ZipFile(zip_path, "r") as zf:
            names = set(zf.namelist())
            if "_benchflow_backup_meta.json" not in names:
                raise ValueError(
                    "Not a BenchFlow backup — missing _benchflow_backup_meta.json"
                )
            meta_bytes = zf.read("_benchflow_backup_meta.json")
            meta = json.loads(meta_bytes)
            if not meta.get("benchflow_backup"):
                raise ValueError("Not a valid BenchFlow backup archive")

            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            restored: list[str] = []
            for name in names:
                if name not in _allowed:
                    continue
                dest = APP_DIR / name
                # Back up existing file before overwriting
                if dest.exists():
                    backup = dest.with_suffix(f".pre_restore_{ts}.json")
                    try:
                        shutil.copy2(dest, backup)
                    except Exception:
                        pass
                data = zf.read(name)
                dest.write_bytes(data)
                restored.append(name)
        return restored

    # ── Convenience helpers ────────────────────────────────────────────────────

    @staticmethod
    def step_total_minutes(step: dict[str, Any]) -> float:
        """Return total planned duration for a step in minutes."""
        return (float(step.get("handsOnMinutes", 0))
                + float(step.get("waitMinutes", 0))
                + float(step.get("bufferMinutes", 0)))

    @staticmethod
    def protocol_total_minutes(protocol: dict[str, Any]) -> float:
        """Return summed planned duration for all steps in a protocol (minutes)."""
        return sum(DataService.step_total_minutes(s)
                   for s in protocol.get("steps", []))

    @staticmethod
    def format_duration(minutes: float) -> str:
        """Format minutes as 'Xh Ym' or 'Ym'."""
        m = int(round(minutes))
        if m <= 0:
            return "—"
        h, rem = divmod(m, 60)
        if h and rem:
            return f"{h}h {rem}m"
        if h:
            return f"{h}h"
        return f"{rem}m"

    @staticmethod
    def format_ts(ts_ms: int | float | None) -> str:
        """Format a millisecond timestamp as 'Mon DD, YYYY HH:MM'."""
        if not ts_ms:
            return "—"
        try:
            dt = datetime.fromtimestamp(float(ts_ms) / 1000)
            return dt.strftime("%b %d, %Y  %H:%M")
        except Exception:
            return "—"

    @staticmethod
    def format_date(date_str: str) -> str:
        """Format 'YYYY-MM-DD' as 'Mon DD, YYYY'."""
        if not date_str:
            return "—"
        try:
            dt = datetime.strptime(date_str, "%Y-%m-%d")
            return dt.strftime("%b %d, %Y")
        except Exception:
            return date_str
