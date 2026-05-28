"""
Schedule service — business logic for the PySide6 Schedule page.

No UI imports.  Pure Python: protocol → timeline conversion, time helpers.
"""
from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta
from typing import Any

from qt_app.models.schedule_experiment import ScheduledExperiment, TimelineBlock
from qt_app.services.run_service import step_planned_secs


# ── Protocol → Timeline ────────────────────────────────────────────────────────

def protocol_to_timeline(protocol: dict[str, Any], start_ts_ms: int) -> list[TimelineBlock]:
    """Convert a protocol's steps into a sequential list of TimelineBlocks."""
    steps = protocol.get("steps", [])
    cursor = start_ts_ms
    blocks: list[TimelineBlock] = []
    for step in steps:
        secs = step_planned_secs(step)
        if secs > 0:
            dur_min = secs / 60.0
        else:
            # Fallback: use whichever time field is non-zero
            dur_min = max(
                float(step.get("handsOnMinutes", 0)),
                float(step.get("waitMinutes", 0)),
                1.0,
            )
        block = TimelineBlock(
            id=str(uuid.uuid4()),
            type=step.get("type", "task"),
            title=step.get("title", "Untitled"),
            start_time=cursor,
            end_time=cursor + int(dur_min * 60 * 1000),
            duration_minutes=dur_min,
            hands_on_minutes=float(step.get("handsOnMinutes", 0)),
            wait_minutes=float(step.get("waitMinutes", 0)),
            status="planned",
            notes=step.get("notes", ""),
            source_protocol_step_id=step.get("id", ""),
        )
        blocks.append(block)
        cursor = block.end_time
    return blocks


def make_scheduled_experiment(
    title: str,
    protocol: dict[str, Any],
    date_str: str,          # YYYY-MM-DD
    start_ts_ms: int,
    notes: str = "",
) -> ScheduledExperiment:
    """Factory: create a new ScheduledExperiment from a protocol."""
    blocks = protocol_to_timeline(protocol, start_ts_ms)
    end_ts = blocks[-1].end_time if blocks else start_ts_ms
    total_dur = max(0.0, (end_ts - start_ts_ms) / 60_000)
    return ScheduledExperiment(
        id=str(uuid.uuid4()),
        title=title,
        protocol_id=protocol.get("id", ""),
        protocol_name=protocol.get("name", ""),
        date=date_str,
        planned_start=start_ts_ms,
        planned_end=end_ts,
        total_duration=total_dur,
        timeline_blocks=blocks,
        notes=notes,
    )


# ── Time formatting helpers ────────────────────────────────────────────────────

def format_time_ms(ts_ms: int) -> str:
    """Format epoch ms as '9:30 AM'."""
    try:
        dt = datetime.fromtimestamp(ts_ms / 1000)
        h, m = dt.hour, dt.minute
        suffix = "AM" if h < 12 else "PM"
        h12 = h % 12 or 12
        return f"{h12}:{m:02d} {suffix}"
    except Exception:
        return "—"


def format_duration_min(minutes: float) -> str:
    """Format float minutes as '2h 30m' or '45m'."""
    m = int(round(minutes))
    if m <= 0:
        return "—"
    h, rem = divmod(m, 60)
    if h and rem:
        return f"{h}h {rem}m"
    if h:
        return f"{h}h"
    return f"{rem}m"


def week_start(anchor: date) -> date:
    """Monday of the ISO week containing *anchor*."""
    return anchor - timedelta(days=anchor.weekday())
