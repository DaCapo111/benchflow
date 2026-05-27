"""
ScheduledExperiment + TimelineBlock — PySide6 Schedule page data models.

These are separate from the CTk-compatible ScheduleBlock (schedule.py).
Stored in scheduled_experiments.json — does not touch schedule.json.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any

# ── Type constants ─────────────────────────────────────────────────────────────
TIMELINE_BLOCK_TYPES = (
    "protocol_step", "break", "task", "note", "decision", "custom",
)
TIMELINE_BLOCK_STATUSES = ("planned", "done", "skipped", "canceled")
EXPERIMENT_STATUSES    = ("planned", "running", "completed", "canceled")


# ── TimelineBlock ──────────────────────────────────────────────────────────────
@dataclass
class TimelineBlock:
    """One time-boxed item within a scheduled experiment."""

    id: str
    type: str
    title: str
    start_time: int          # epoch ms
    end_time: int            # epoch ms
    duration_minutes: float  # nominal (ignoring status)
    hands_on_minutes: float = 0.0
    wait_minutes: float = 0.0
    status: str = "planned"  # planned | done | skipped | canceled
    notes: str = ""
    source_protocol_step_id: str = ""
    is_temporary: bool = False
    is_parallel_task: bool = False
    parallel_with_block_id: str = ""

    @classmethod
    def new(cls, title: str, block_type: str, start_time_ms: int,
            duration_minutes: float, **kwargs: Any) -> "TimelineBlock":
        end_ms = start_time_ms + int(duration_minutes * 60 * 1000)
        return cls(
            id=str(uuid.uuid4()),
            type=block_type,
            title=title,
            start_time=start_time_ms,
            end_time=end_ms,
            duration_minutes=duration_minutes,
            **kwargs,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "id":                    self.id,
            "type":                  self.type,
            "title":                 self.title,
            "startTime":             self.start_time,
            "endTime":               self.end_time,
            "durationMinutes":       self.duration_minutes,
            "handsOnMinutes":        self.hands_on_minutes,
            "waitMinutes":           self.wait_minutes,
            "status":                self.status,
            "notes":                 self.notes,
            "sourceProtocolStepId":  self.source_protocol_step_id,
            "isTemporary":           self.is_temporary,
            "isParallelTask":        self.is_parallel_task,
            "parallelWithBlockId":   self.parallel_with_block_id,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "TimelineBlock":
        return cls(
            id=d.get("id", str(uuid.uuid4())),
            type=d.get("type", "task"),
            title=d.get("title", ""),
            start_time=int(d.get("startTime", 0)),
            end_time=int(d.get("endTime", 0)),
            duration_minutes=float(d.get("durationMinutes", 0)),
            hands_on_minutes=float(d.get("handsOnMinutes", 0)),
            wait_minutes=float(d.get("waitMinutes", 0)),
            status=d.get("status", "planned"),
            notes=d.get("notes", ""),
            source_protocol_step_id=d.get("sourceProtocolStepId", ""),
            is_temporary=bool(d.get("isTemporary", False)),
            is_parallel_task=bool(d.get("isParallelTask", False)),
            parallel_with_block_id=d.get("parallelWithBlockId", ""),
        )


# ── ScheduledExperiment ────────────────────────────────────────────────────────
@dataclass
class ScheduledExperiment:
    """A complete experiment session on the schedule calendar."""

    id: str
    title: str
    protocol_id: str
    protocol_name: str
    date: str            # YYYY-MM-DD
    planned_start: int   # epoch ms
    planned_end: int     # epoch ms
    total_duration: float   # minutes
    timeline_blocks: list[TimelineBlock] = field(default_factory=list)
    notes: str = ""
    status: str = "planned"  # planned | running | completed | canceled

    def recalculate_times(self) -> None:
        """Recalculate all block start/end times from planned_start.
        Skipped/canceled blocks consume zero time in the timeline.
        """
        cursor = self.planned_start
        for block in self.timeline_blocks:
            if block.status in ("skipped", "canceled"):
                block.start_time = cursor
                block.end_time = cursor
            else:
                block.start_time = cursor
                block.end_time = cursor + int(block.duration_minutes * 60 * 1000)
                cursor = block.end_time
        self.planned_end = cursor
        self.total_duration = max(0.0, (self.planned_end - self.planned_start) / 60_000)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id":              self.id,
            "title":           self.title,
            "protocolId":      self.protocol_id,
            "protocolName":    self.protocol_name,
            "date":            self.date,
            "plannedStart":    self.planned_start,
            "plannedEnd":      self.planned_end,
            "totalDuration":   self.total_duration,
            "timelineBlocks":  [b.to_dict() for b in self.timeline_blocks],
            "notes":           self.notes,
            "status":          self.status,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "ScheduledExperiment":
        blocks = [TimelineBlock.from_dict(b) for b in d.get("timelineBlocks", [])]
        return cls(
            id=d.get("id", str(uuid.uuid4())),
            title=d.get("title", ""),
            protocol_id=d.get("protocolId", ""),
            protocol_name=d.get("protocolName", ""),
            date=d.get("date", ""),
            planned_start=int(d.get("plannedStart", 0)),
            planned_end=int(d.get("plannedEnd", 0)),
            total_duration=float(d.get("totalDuration", 0)),
            timeline_blocks=blocks,
            notes=d.get("notes", ""),
            status=d.get("status", "planned"),
        )
