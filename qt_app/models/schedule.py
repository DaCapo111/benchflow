"""ScheduleBlock dataclass."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ScheduleBlock:
    id: str
    experiment_id: str = ""
    start_ts: float = 0.0
    end_ts: float = 0.0
    color: str = "#3b82f6"
    label: str = ""
    _raw: dict[str, Any] = field(default_factory=dict, repr=False)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "ScheduleBlock":
        return cls(
            id=d.get("id", ""),
            experiment_id=d.get("experimentId", d.get("experiment_id", "")),
            start_ts=float(d.get("startTs", d.get("start_ts", 0))),
            end_ts=float(d.get("endTs", d.get("end_ts", 0))),
            color=d.get("color", "#3b82f6"),
            label=d.get("label", ""),
            _raw=d,
        )

    def to_dict(self) -> dict[str, Any]:
        d = dict(self._raw)
        d.update(
            id=self.id,
            experimentId=self.experiment_id,
            startTs=self.start_ts,
            endTs=self.end_ts,
            color=self.color,
            label=self.label,
        )
        return d
