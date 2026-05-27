"""
ScheduleBlock dataclass.

Real field names from ~/.benchflow/schedule.json:
  id, title, protocolId, protocolName, protocolSnapshot,
  date (YYYY-MM-DD), plannedStart (ms), plannedEnd (ms),
  scheduledSteps, timelineBlocks, notes, status
"""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class ScheduleBlock:
    id: str
    title: str = ""
    protocol_id: str = ""           # JSON: "protocolId"
    protocol_name: str = ""         # JSON: "protocolName"
    date: str = ""                  # "YYYY-MM-DD"
    planned_start: int = 0          # JSON: "plannedStart"  (ms epoch)
    planned_end: int = 0            # JSON: "plannedEnd"    (ms epoch)
    notes: str = ""
    status: str = "planned"         # planned | running | completed | cancelled
    _raw: dict[str, Any] = field(default_factory=dict, repr=False)

    # ── Derived ───────────────────────────────────────────────────────────────
    @property
    def date_display(self) -> str:
        if self.date:
            try:
                return datetime.strptime(self.date, "%Y-%m-%d").strftime("%b %d, %Y")
            except ValueError:
                return self.date
        return "—"

    @property
    def time_range_display(self) -> str:
        if self.planned_start and self.planned_end:
            try:
                s = datetime.fromtimestamp(self.planned_start / 1000).strftime("%H:%M")
                e = datetime.fromtimestamp(self.planned_end / 1000).strftime("%H:%M")
                return f"{s} – {e}"
            except Exception:
                pass
        return ""

    @property
    def duration_minutes(self) -> float:
        if self.planned_start and self.planned_end:
            return max(0, (self.planned_end - self.planned_start) / 60_000)
        return 0.0

    # ── Serialisation ─────────────────────────────────────────────────────────
    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "ScheduleBlock":
        return cls(
            id=d.get("id", ""),
            title=d.get("title", ""),
            protocol_id=d.get("protocolId", d.get("protocol_id", "")),
            protocol_name=d.get("protocolName", d.get("protocol_name", "")),
            date=d.get("date", ""),
            planned_start=int(d.get("plannedStart", d.get("planned_start", 0))),
            planned_end=int(d.get("plannedEnd", d.get("planned_end", 0))),
            notes=d.get("notes", ""),
            status=d.get("status", "planned"),
            _raw=d,
        )

    def to_dict(self) -> dict[str, Any]:
        d = dict(self._raw)
        d.update(
            id=self.id,
            title=self.title,
            protocolId=self.protocol_id,
            protocolName=self.protocol_name,
            date=self.date,
            plannedStart=self.planned_start,
            plannedEnd=self.planned_end,
            notes=self.notes,
            status=self.status,
        )
        return d
