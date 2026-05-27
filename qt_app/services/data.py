"""
DataService
===========
Singleton that owns all persistence: load/save protocols, runs, schedule,
categories, tags, templates, and the crash-recovery session checkpoint.

This is a straight port of the top-level functions from the CTk app.py.
No UI dependency — plain Python I/O.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

# ── Data directory ─────────────────────────────────────────────────────────────
APP_DIR = Path.home() / "Library" / "Application Support" / "BenchFlow"
APP_DIR.mkdir(parents=True, exist_ok=True)

PROTOCOLS_FILE  = APP_DIR / "protocols.json"
RUNS_FILE       = APP_DIR / "runs.json"
CATEGORIES_FILE = APP_DIR / "categories.json"
TAGS_FILE       = APP_DIR / "tags.json"
SCHEDULE_FILE   = APP_DIR / "schedule.json"
RUNTIME_FILE    = APP_DIR / "runtime_session.json"

# Templates directory — works both from source and inside PyInstaller bundle
_APP_BASE = (Path(sys._MEIPASS)  # type: ignore[attr-defined]
             if getattr(sys, "frozen", False)
             else Path(__file__).parent.parent.parent)
TEMPLATES_DIR = _APP_BASE / "templates"


def _load_json(path: Path, default: Any = None) -> Any:
    """Load JSON from *path*, returning *default* on any failure."""
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            pass
    return default if default is not None else []


def _save_json(path: Path, data: Any) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _load_terms(path: Path) -> list[str]:
    data = _load_json(path, [])
    if isinstance(data, list):
        return sorted({str(x).strip() for x in data if str(x).strip()})
    return []


def _save_terms(path: Path, terms: list[str]) -> None:
    _save_json(path, sorted({str(x).strip() for x in terms if str(x).strip()}))


class DataService:
    """Manages all BenchFlow data persistence.

    Instantiate once and pass to views that need it.
    """

    # ── Protocols ──────────────────────────────────────────────────────────────
    def load_protocols(self) -> list[dict[str, Any]]:
        return _load_json(PROTOCOLS_FILE, [])

    def save_protocols(self, protocols: list[dict[str, Any]]) -> None:
        _save_json(PROTOCOLS_FILE, protocols)

    # ── Runs (lab notebook / history) ─────────────────────────────────────────
    def load_runs(self) -> list[dict[str, Any]]:
        return _load_json(RUNS_FILE, [])

    def save_runs(self, runs: list[dict[str, Any]]) -> None:
        _save_json(RUNS_FILE, runs)

    # ── Categories & Tags ──────────────────────────────────────────────────────
    def load_categories(self) -> list[str]:
        return _load_terms(CATEGORIES_FILE)

    def save_categories(self, categories: list[str]) -> None:
        _save_terms(CATEGORIES_FILE, categories)

    def load_tags(self) -> list[str]:
        return _load_terms(TAGS_FILE)

    def save_tags(self, tags: list[str]) -> None:
        _save_terms(TAGS_FILE, tags)

    # ── Schedule ───────────────────────────────────────────────────────────────
    def load_schedule(self) -> list[dict[str, Any]]:
        return _load_json(SCHEDULE_FILE, [])

    def save_schedule(self, schedule: list[dict[str, Any]]) -> None:
        _save_json(SCHEDULE_FILE, schedule)

    # ── Templates (built-in, read-only) ───────────────────────────────────────
    def load_templates(self) -> list[dict[str, Any]]:
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

    # ── Runtime session (crash recovery) ──────────────────────────────────────
    def load_runtime_session(self) -> dict[str, Any] | None:
        data = _load_json(RUNTIME_FILE, None)
        return data if isinstance(data, dict) else None

    def save_runtime_session(self, session: dict[str, Any]) -> None:
        _save_json(RUNTIME_FILE, session)

    def discard_runtime_session(self) -> None:
        try:
            RUNTIME_FILE.unlink(missing_ok=True)
        except Exception:
            pass
