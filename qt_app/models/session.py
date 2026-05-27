"""
RunRecord and RuntimeSession dataclasses.

RunRecord (from runs.json)
--------------------------
Real CTk JSON keys:
  id, title, protocolId, protocolName, protocolSnapshot,
  startedAt (ms), endedAt (ms), actualDuration (s),
  timeline, stepRecords, observations, tags, notes

StepRecord (inside RunRecord.stepRecords)
-----------------------------------------
  stepId, stepTitle, stepType, status,
  plannedSecs, usedSecs, notes

RuntimeSession (runtime_session.json — crash recovery)
-------------------------------------------------------
  version, saved_at_ts (ms), protocol_id, protocol_snapshot,
  session_start_ts (ms), timeline, step_states, seq_mode, seq_idx

StepRuntimeState (inside RuntimeSession.step_states)
----------------------------------------------------
  status, timer_secs, original_secs, adjusted_total_secs,
  elapsed_secs, timer_secs_at_start, adjusted, notes,
  ho_elapsed_secs, ho_status, is_temp
"""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


# ── StepRecord ─────────────────────────────────────────────────────────────────

@dataclass
class StepRecord:
    step_id: str = ""
    step_title: str = ""
    step_type: str = ""
    status: str = "pending"
    planned_secs: float = 0.0
    used_secs: float = 0.0
    notes: str = ""
    _raw: dict[str, Any] = field(default_factory=dict, repr=False)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "StepRecord":
        return cls(
            step_id=d.get("stepId", d.get("step_id", "")),
            step_title=d.get("stepTitle", d.get("step_title", "")),
            step_type=d.get("stepType", d.get("step_type", "")),
            status=d.get("status", "pending"),
            planned_secs=float(d.get("plannedSecs", d.get("planned_secs", 0))),
            used_secs=float(d.get("usedSecs", d.get("used_secs", 0))),
            notes=d.get("notes", ""),
            _raw=d,
        )

    def to_dict(self) -> dict[str, Any]:
        d = dict(self._raw)
        d.update(
            stepId=self.step_id,
            stepTitle=self.step_title,
            stepType=self.step_type,
            status=self.status,
            plannedSecs=self.planned_secs,
            usedSecs=self.used_secs,
            notes=self.notes,
        )
        return d


# ── RunRecord ──────────────────────────────────────────────────────────────────

@dataclass
class RunRecord:
    id: str
    title: str = ""
    protocol_id: str = ""
    protocol_name: str = ""
    started_at: int = 0          # ms epoch
    ended_at: int = 0            # ms epoch
    actual_duration: float = 0.0 # seconds
    step_records: list[StepRecord] = field(default_factory=list)
    observations: str = ""
    tags: list[str] = field(default_factory=list)
    notes: str = ""
    _raw: dict[str, Any] = field(default_factory=dict, repr=False)

    # ── Derived ───────────────────────────────────────────────────────────────
    @property
    def started_display(self) -> str:
        if not self.started_at:
            return "—"
        try:
            return datetime.fromtimestamp(self.started_at / 1000).strftime("%b %d, %Y  %H:%M")
        except Exception:
            return "—"

    @property
    def date_key(self) -> str:
        """'YYYY-MM-DD' for grouping."""
        if not self.started_at:
            return "Unknown"
        try:
            return datetime.fromtimestamp(self.started_at / 1000).strftime("%Y-%m-%d")
        except Exception:
            return "Unknown"

    @property
    def date_display(self) -> str:
        if not self.started_at:
            return "Unknown date"
        try:
            return datetime.fromtimestamp(self.started_at / 1000).strftime("%B %d, %Y")
        except Exception:
            return "Unknown date"

    @property
    def duration_display(self) -> str:
        s = int(self.actual_duration)
        if s <= 0 and self.started_at and self.ended_at:
            s = max(0, int((self.ended_at - self.started_at) / 1000))
        if s <= 0:
            return "—"
        h, rem = divmod(s, 3600)
        m, sec = divmod(rem, 60)
        if h:
            return f"{h}h {m}m"
        if m:
            return f"{m}m {sec}s"
        return f"{sec}s"

    # ── Serialisation ─────────────────────────────────────────────────────────
    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "RunRecord":
        step_records = [StepRecord.from_dict(s) for s in d.get("stepRecords", [])]
        return cls(
            id=d.get("id", ""),
            title=d.get("title", ""),
            protocol_id=d.get("protocolId", d.get("protocol_id", "")),
            protocol_name=d.get("protocolName", d.get("protocol_name", "")),
            started_at=int(d.get("startedAt", d.get("started_at", 0))),
            ended_at=int(d.get("endedAt", d.get("ended_at", 0))),
            actual_duration=float(d.get("actualDuration", d.get("actual_duration", 0))),
            step_records=step_records,
            observations=d.get("observations", ""),
            tags=d.get("tags", []),
            notes=d.get("notes", ""),
            _raw=d,
        )

    def to_dict(self) -> dict[str, Any]:
        d = dict(self._raw)
        d.update(
            id=self.id,
            title=self.title,
            protocolId=self.protocol_id,
            protocolName=self.protocol_name,
            startedAt=self.started_at,
            endedAt=self.ended_at,
            actualDuration=self.actual_duration,
            stepRecords=[s.to_dict() for s in self.step_records],
            observations=self.observations,
            tags=self.tags,
            notes=self.notes,
        )
        return d


# ── StepRuntimeState ───────────────────────────────────────────────────────────

@dataclass
class StepRuntimeState:
    """Live state of one step during a run (from runtime_session.json)."""
    status: str = "idle"            # idle | running | paused | completed | skipped
    timer_secs: float = 0.0
    original_secs: float = 0.0
    adjusted_total_secs: float = 0.0
    elapsed_secs: float = 0.0
    timer_secs_at_start: float = 0.0
    adjusted: bool = False
    notes: str = ""
    ho_elapsed_secs: float = 0.0
    ho_status: str = "idle"
    is_temp: bool = False
    _raw: dict[str, Any] = field(default_factory=dict, repr=False)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "StepRuntimeState":
        return cls(
            status=d.get("status", "idle"),
            timer_secs=float(d.get("timer_secs", 0)),
            original_secs=float(d.get("original_secs", 0)),
            adjusted_total_secs=float(d.get("adjusted_total_secs", 0)),
            elapsed_secs=float(d.get("elapsed_secs", 0)),
            timer_secs_at_start=float(d.get("timer_secs_at_start", 0)),
            adjusted=bool(d.get("adjusted", False)),
            notes=d.get("notes", ""),
            ho_elapsed_secs=float(d.get("ho_elapsed_secs", 0)),
            ho_status=d.get("ho_status", "idle"),
            is_temp=bool(d.get("is_temp", False)),
            _raw=d,
        )

    def to_dict(self) -> dict[str, Any]:
        d = dict(self._raw)
        d.update(
            status=self.status,
            timer_secs=self.timer_secs,
            original_secs=self.original_secs,
            adjusted_total_secs=self.adjusted_total_secs,
            elapsed_secs=self.elapsed_secs,
            timer_secs_at_start=self.timer_secs_at_start,
            adjusted=self.adjusted,
            notes=self.notes,
            ho_elapsed_secs=self.ho_elapsed_secs,
            ho_status=self.ho_status,
            is_temp=self.is_temp,
        )
        return d


# ── RuntimeSession ─────────────────────────────────────────────────────────────

@dataclass
class RuntimeSession:
    """Crash-recovery checkpoint written every tick during a run."""
    version: int = 1
    saved_at_ts: int = 0            # ms epoch
    protocol_id: str = ""
    session_start_ts: int = 0       # ms epoch
    step_states: list[StepRuntimeState] = field(default_factory=list)
    seq_mode: bool = False
    seq_idx: int = 0
    _raw: dict[str, Any] = field(default_factory=dict, repr=False)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "RuntimeSession":
        states = [StepRuntimeState.from_dict(s) for s in d.get("step_states", [])]
        return cls(
            version=int(d.get("version", 1)),
            saved_at_ts=int(d.get("saved_at_ts", 0)),
            protocol_id=d.get("protocol_id", ""),
            session_start_ts=int(d.get("session_start_ts", 0)),
            step_states=states,
            seq_mode=bool(d.get("seq_mode", False)),
            seq_idx=int(d.get("seq_idx", 0)),
            _raw=d,
        )

    def to_dict(self) -> dict[str, Any]:
        d = dict(self._raw)
        d.update(
            version=self.version,
            saved_at_ts=self.saved_at_ts,
            protocol_id=self.protocol_id,
            session_start_ts=self.session_start_ts,
            step_states=[s.to_dict() for s in self.step_states],
            seq_mode=self.seq_mode,
            seq_idx=self.seq_idx,
        )
        return d
