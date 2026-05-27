"""RunSession and StepState dataclasses."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any


@dataclass
class StepState:
    step_id: str
    status: str = "pending"        # pending | running | paused | completed | skipped
    elapsed_secs: float = 0.0
    remaining_secs: float = 0.0
    completed_at: str = ""
    notes: str = ""
    adjusted: bool = False
    original_secs: float = 0.0
    _raw: dict[str, Any] = field(default_factory=dict, repr=False)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "StepState":
        return cls(
            step_id=d.get("stepId", d.get("step_id", "")),
            status=d.get("status", "pending"),
            elapsed_secs=float(d.get("elapsedSecs", d.get("elapsed_secs", 0))),
            remaining_secs=float(d.get("remainingSecs", d.get("remaining_secs", 0))),
            completed_at=d.get("completedAt", d.get("completed_at", "")),
            notes=d.get("notes", ""),
            adjusted=bool(d.get("adjusted", False)),
            original_secs=float(d.get("originalSecs", d.get("original_secs", 0))),
            _raw=d,
        )

    def to_dict(self) -> dict[str, Any]:
        d = dict(self._raw)
        d.update(
            stepId=self.step_id,
            status=self.status,
            elapsedSecs=self.elapsed_secs,
            remainingSecs=self.remaining_secs,
            completedAt=self.completed_at,
            notes=self.notes,
            adjusted=self.adjusted,
            originalSecs=self.original_secs,
        )
        return d


@dataclass
class RunSession:
    protocol_id: str
    step_states: list[StepState] = field(default_factory=list)
    saved_at: str = ""
    sequential_mode: bool = False
    current_step_idx: int = 0
    _raw: dict[str, Any] = field(default_factory=dict, repr=False)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "RunSession":
        states = [StepState.from_dict(s) for s in d.get("stepStates", d.get("step_states", []))]
        return cls(
            protocol_id=d.get("protocolId", d.get("protocol_id", "")),
            step_states=states,
            saved_at=d.get("savedAt", d.get("saved_at", "")),
            sequential_mode=bool(d.get("sequentialMode", d.get("sequential_mode", False))),
            current_step_idx=int(d.get("currentStepIdx", d.get("current_step_idx", 0))),
            _raw=d,
        )

    def to_dict(self) -> dict[str, Any]:
        d = dict(self._raw)
        d.update(
            protocolId=self.protocol_id,
            stepStates=[s.to_dict() for s in self.step_states],
            savedAt=self.saved_at,
            sequentialMode=self.sequential_mode,
            currentStepIdx=self.current_step_idx,
        )
        return d
