"""
RunService — Run Mode session state machine.

Pure Python, no UI dependency.  The RunModePage owns one RunModeSession
and updates it on every user action and timer tick.

Wall-clock timer model
----------------------
Each step tracks:
  started_at_ts           wall-clock float (time.time()) when last started/resumed
  accumulated_elapsed_secs  elapsed before the last start/resume

While running:
  elapsed = (now - started_at_ts) + accumulated_elapsed_secs
  remaining = planned_secs - elapsed

While paused/idle:
  elapsed = accumulated_elapsed_secs
  remaining = planned_secs - elapsed

This model stays accurate across app sleep, window switches, and
system-level clock adjustments.  It matches the Phase-3 spec requirement.
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any

# ── Timer-type classification ──────────────────────────────────────────────────
# Steps whose primary timer is a COUNTDOWN (waitMinutes drives the timer)
COUNTDOWN_TYPES: frozenset[str] = frozenset({
    "incubation", "waiting", "centrifuge", "electrophoresis",
    "gel_running", "membrane_transfer", "imaging", "heating",
    "cooling", "blocking", "storage",
})

# Steps that are purely hands-on (elapsed stopwatch only)
HANDS_ON_TYPES: frozenset[str] = frozenset({
    "preparation", "reagent_addition", "mixing", "pipetting",
    "resuspension", "transfer", "wash", "staining", "lysis",
    "harvest", "sample_collection",
})

# Types with no meaningful timer (annotation steps)
NOTE_TYPES: frozenset[str] = frozenset({"note", "checklist_block", "decision"})


def step_planned_secs(step: dict[str, Any]) -> float:
    """Return total planned seconds for a step (wait + buffer).

    For countdown steps we use waitMinutes + bufferMinutes.
    For hands-on steps we use handsOnMinutes as the stopwatch duration target.
    """
    ho  = float(step.get("handsOnMinutes",  0))
    wt  = float(step.get("waitMinutes",     0))
    buf = float(step.get("bufferMinutes",   0))
    stype = step.get("type", "other")
    if stype in COUNTDOWN_TYPES:
        return (wt + buf) * 60.0
    if stype in HANDS_ON_TYPES or ho > 0:
        return ho * 60.0
    return (ho + wt + buf) * 60.0


def step_has_timer(step: dict[str, Any]) -> bool:
    """True when the step should show an active timer."""
    return step.get("type", "other") not in NOTE_TYPES and step_planned_secs(step) > 0


def is_countdown_step(step: dict[str, Any]) -> bool:
    return step.get("type", "other") in COUNTDOWN_TYPES


# ── StepRunState ───────────────────────────────────────────────────────────────

@dataclass
class StepRunState:
    """Runtime state for one step (or temp block) during a run."""

    step_idx: int
    step_id: str
    status: str = "idle"           # idle | running | paused | completed | skipped

    # Wall-clock timer
    original_planned_secs: float = 0.0  # original plan, never changed
    planned_secs: float = 0.0           # original + adjustments
    started_at_ts: float = 0.0          # wall-clock when last started/resumed
    accumulated_elapsed_secs: float = 0.0  # elapsed before last start/resume
    completed_at_ts: float = 0.0

    # Content
    notes: str = ""

    # Temp block flag
    is_temp: bool = False
    temp_step_data: dict[str, Any] = field(default_factory=dict)

    # ── Timer calculations ────────────────────────────────────────────────────

    def elapsed_secs(self, now: float | None = None) -> float:
        if now is None:
            now = time.time()
        if self.status == "running" and self.started_at_ts > 0:
            return (now - self.started_at_ts) + self.accumulated_elapsed_secs
        return self.accumulated_elapsed_secs

    def remaining_secs(self, now: float | None = None) -> float:
        if now is None:
            now = time.time()
        return self.planned_secs - self.elapsed_secs(now)

    def is_expired(self, now: float | None = None) -> bool:
        return self.status == "running" and self.remaining_secs(now) <= 0

    # ── State transitions ─────────────────────────────────────────────────────

    def start(self, now: float | None = None) -> None:
        if now is None:
            now = time.time()
        if self.status in ("idle", "paused"):
            self.status = "running"
            self.started_at_ts = now

    def pause(self, now: float | None = None) -> None:
        if now is None:
            now = time.time()
        if self.status == "running":
            self.accumulated_elapsed_secs += now - self.started_at_ts
            self.started_at_ts = 0.0
            self.status = "paused"

    def resume(self, now: float | None = None) -> None:
        if now is None:
            now = time.time()
        if self.status == "paused":
            self.status = "running"
            self.started_at_ts = now

    def complete(self, now: float | None = None) -> None:
        if now is None:
            now = time.time()
        if self.status == "running":
            self.accumulated_elapsed_secs += now - self.started_at_ts
            self.started_at_ts = 0.0
        self.status = "completed"
        self.completed_at_ts = now

    def undo_complete(self) -> None:
        self.completed_at_ts = 0.0
        # Revert to paused if any time was logged, else idle
        self.status = "paused" if self.accumulated_elapsed_secs > 0 else "idle"

    def skip(self, now: float | None = None) -> None:
        if now is None:
            now = time.time()
        if self.status == "running":
            self.pause(now)
        self.status = "skipped"

    def undo_skip(self) -> None:
        self.status = "paused" if self.accumulated_elapsed_secs > 0 else "idle"

    def reset(self) -> None:
        self.status = "idle"
        self.accumulated_elapsed_secs = 0.0
        self.started_at_ts = 0.0
        self.completed_at_ts = 0.0
        self.planned_secs = self.original_planned_secs

    def adjust(self, delta_secs: float) -> None:
        """Add/subtract seconds from the planned duration."""
        self.planned_secs = max(0.0, self.planned_secs + delta_secs)

    # ── Serialisation ─────────────────────────────────────────────────────────

    def to_dict(self) -> dict[str, Any]:
        return {
            "step_idx": self.step_idx,
            "step_id": self.step_id,
            "status": self.status,
            "original_planned_secs": self.original_planned_secs,
            "planned_secs": self.planned_secs,
            "started_at_ts": self.started_at_ts,
            "accumulated_elapsed_secs": self.accumulated_elapsed_secs,
            "completed_at_ts": self.completed_at_ts,
            "notes": self.notes,
            "is_temp": self.is_temp,
            "temp_step_data": self.temp_step_data,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "StepRunState":
        s = cls(
            step_idx=d.get("step_idx", 0),
            step_id=d.get("step_id", ""),
        )
        s.status = d.get("status", "idle")
        s.original_planned_secs = float(d.get("original_planned_secs", 0))
        s.planned_secs = float(d.get("planned_secs", 0))
        s.started_at_ts = float(d.get("started_at_ts", 0))
        s.accumulated_elapsed_secs = float(d.get("accumulated_elapsed_secs", 0))
        s.completed_at_ts = float(d.get("completed_at_ts", 0))
        s.notes = d.get("notes", "")
        s.is_temp = bool(d.get("is_temp", False))
        s.temp_step_data = d.get("temp_step_data", {})
        return s


# ── RunModeSession ─────────────────────────────────────────────────────────────

@dataclass
class RunModeSession:
    """
    Active Run Mode session.

    Owns:
    - the protocol data (snapshot frozen at session start)
    - step_states list (one per step/block)
    - session start timestamp
    """

    session_id: str
    protocol_id: str
    protocol_snapshot: dict[str, Any]    # frozen at session start
    step_states: list[StepRunState]
    session_start_ts: float
    version: int = 3                      # v3 = Qt wall-clock format

    @classmethod
    def new(cls, protocol: dict[str, Any]) -> "RunModeSession":
        """Create a brand-new session for *protocol*."""
        steps = protocol.get("steps", [])
        step_states = []
        for idx, step in enumerate(steps):
            planned = step_planned_secs(step)
            ss = StepRunState(
                step_idx=idx,
                step_id=step.get("id", str(uuid.uuid4())),
                planned_secs=planned,
                original_planned_secs=planned,
            )
            step_states.append(ss)

        return cls(
            session_id=str(uuid.uuid4()),
            protocol_id=protocol.get("id", ""),
            protocol_snapshot=protocol,
            step_states=step_states,
            session_start_ts=time.time(),
        )

    def steps(self) -> list[dict[str, Any]]:
        """Return steps from the protocol snapshot."""
        return self.protocol_snapshot.get("steps", [])

    def add_temp_block(self, title: str, block_type: str,
                       duration_mins: float, notes: str = "") -> StepRunState:
        """Append a temporary block to the session."""
        idx = len(self.step_states)
        planned = duration_mins * 60.0
        step_data = {
            "id": str(uuid.uuid4()),
            "title": title,
            "type": block_type,
            "handsOnMinutes": 0,
            "waitMinutes": duration_mins if block_type in COUNTDOWN_TYPES else 0,
            "bufferMinutes": 0,
            "description": notes,
            "reagents": [],
            "equipment": [],
            "notes": notes,
            "warnings": "",
            "checklist": [],
            "substeps": [],
            "temperature": "",
            "centrifugeCondition": "",
            "shakingRotation": "",
            "order": idx,
        }
        ss = StepRunState(
            step_idx=idx,
            step_id=step_data["id"],
            planned_secs=planned,
            original_planned_secs=planned,
            is_temp=True,
            temp_step_data=step_data,
            notes=notes,
        )
        self.step_states.append(ss)
        return ss

    def remove_temp_block(self, step_idx: int) -> None:
        """Remove a temporary block and re-index."""
        if 0 <= step_idx < len(self.step_states):
            ss = self.step_states[step_idx]
            if ss.is_temp:
                self.step_states.pop(step_idx)
                # Re-index remaining
                for i, s in enumerate(self.step_states):
                    s.step_idx = i

    def step_data(self, state: StepRunState) -> dict[str, Any]:
        """Return the step dict for a given state (protocol or temp)."""
        if state.is_temp:
            return state.temp_step_data
        proto_steps = self.steps()
        # Find by id, fallback to order
        for s in proto_steps:
            if s.get("id") == state.step_id:
                return s
        idx = state.step_idx
        if idx < len(proto_steps):
            return proto_steps[idx]
        return {}

    def running_states(self) -> list[StepRunState]:
        return [s for s in self.step_states if s.status == "running"]

    # ── Persistence ───────────────────────────────────────────────────────────

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "session_id": self.session_id,
            "saved_at_ts": int(time.time() * 1000),
            "protocol_id": self.protocol_id,
            "protocol_snapshot": self.protocol_snapshot,
            "session_start_ts": self.session_start_ts,
            "step_states": [s.to_dict() for s in self.step_states],
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "RunModeSession":
        states = [StepRunState.from_dict(s) for s in d.get("step_states", [])]
        return cls(
            session_id=d.get("session_id", str(uuid.uuid4())),
            protocol_id=d.get("protocol_id", ""),
            protocol_snapshot=d.get("protocol_snapshot", {}),
            step_states=states,
            session_start_ts=float(d.get("session_start_ts", time.time())),
            version=int(d.get("version", 3)),
        )


# ── Timer formatting ───────────────────────────────────────────────────────────

def format_timer(secs: float, countdown: bool = True) -> str:
    """Format seconds as MM:SS (or -MM:SS for expired countdowns)."""
    negative = secs < 0
    secs = abs(secs)
    m = int(secs) // 60
    s = int(secs) % 60
    text = f"{m:02d}:{s:02d}"
    if negative:
        text = "-" + text
    return text
