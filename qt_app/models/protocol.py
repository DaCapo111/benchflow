"""
Protocol and Step dataclasses.

Field mapping (CTk JSON → Qt model)
-------------------------------------
CTk JSON key         Qt field
────────────────     ─────────────────
type                 step_type
handsOnMinutes       hands_on_minutes
waitMinutes          wait_minutes
bufferMinutes        buffer_minutes
centrifugeCondition  centrifuge_condition
shakingRotation      shaking_rotation
createdAt            created_at   (ms timestamp int)
updatedAt            updated_at   (ms timestamp int)

to_dict() / from_dict() write/read the original CTk JSON key names so
data files stay 100% compatible with the CTk app.py.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any


@dataclass
class Step:
    # ── Identity ───────────────────────────────────────────────────────────────
    id: str
    order: int = 0
    title: str = ""

    # ── Type ──────────────────────────────────────────────────────────────────
    step_type: str = "other"          # JSON key: "type"

    # ── Description / instructions ────────────────────────────────────────────
    description: str = ""
    notes: str = ""
    warnings: str = ""

    # ── Timing ────────────────────────────────────────────────────────────────
    hands_on_minutes: float = 0.0     # JSON key: "handsOnMinutes"
    wait_minutes: float = 0.0         # JSON key: "waitMinutes"
    buffer_minutes: float = 0.0       # JSON key: "bufferMinutes"

    # ── Conditions ────────────────────────────────────────────────────────────
    temperature: str = ""
    centrifuge_condition: str = ""    # JSON key: "centrifugeCondition"
    shaking_rotation: str = ""        # JSON key: "shakingRotation"

    # ── Content lists ─────────────────────────────────────────────────────────
    reagents: list[dict[str, Any]] = field(default_factory=list)
    equipment: list[str] = field(default_factory=list)
    checklist: list[Any] = field(default_factory=list)
    substeps: list[Any] = field(default_factory=list)

    # ── Raw dict (preserves any unknown future fields) ────────────────────────
    _raw: dict[str, Any] = field(default_factory=dict, repr=False)

    # ── Derived ───────────────────────────────────────────────────────────────
    @property
    def total_minutes(self) -> float:
        return self.hands_on_minutes + self.wait_minutes + self.buffer_minutes

    # ── Serialisation ─────────────────────────────────────────────────────────
    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "Step":
        return cls(
            id=d.get("id", ""),
            order=int(d.get("order", 0)),
            title=d.get("title", ""),
            step_type=d.get("type", d.get("step_type", "other")),
            description=d.get("description", ""),
            notes=d.get("notes", ""),
            warnings=d.get("warnings", ""),
            hands_on_minutes=float(d.get("handsOnMinutes", d.get("hands_on_minutes", 0))),
            wait_minutes=float(d.get("waitMinutes", d.get("wait_minutes", 0))),
            buffer_minutes=float(d.get("bufferMinutes", d.get("buffer_minutes", 0))),
            temperature=d.get("temperature", ""),
            centrifuge_condition=d.get("centrifugeCondition", d.get("centrifuge_condition", "")),
            shaking_rotation=d.get("shakingRotation", d.get("shaking_rotation", "")),
            reagents=d.get("reagents", []),
            equipment=d.get("equipment", []),
            checklist=d.get("checklist", []),
            substeps=d.get("substeps", []),
            _raw=d,
        )

    def to_dict(self) -> dict[str, Any]:
        # Start with raw (preserves any unknown fields)
        d = dict(self._raw)
        d.update(
            id=self.id,
            order=self.order,
            title=self.title,
            type=self.step_type,
            description=self.description,
            notes=self.notes,
            warnings=self.warnings,
            handsOnMinutes=self.hands_on_minutes,
            waitMinutes=self.wait_minutes,
            bufferMinutes=self.buffer_minutes,
            temperature=self.temperature,
            centrifugeCondition=self.centrifuge_condition,
            shakingRotation=self.shaking_rotation,
            reagents=self.reagents,
            equipment=self.equipment,
            checklist=self.checklist,
            substeps=self.substeps,
        )
        return d


@dataclass
class Protocol:
    # ── Identity ───────────────────────────────────────────────────────────────
    id: str
    name: str

    # ── Metadata ──────────────────────────────────────────────────────────────
    category: str = ""
    description: str = ""
    tags: list[str] = field(default_factory=list)
    created_at: int = 0     # ms epoch  (JSON key: "createdAt")
    updated_at: int = 0     # ms epoch  (JSON key: "updatedAt")

    # ── Steps ─────────────────────────────────────────────────────────────────
    steps: list[Step] = field(default_factory=list)

    # ── Raw dict ──────────────────────────────────────────────────────────────
    _raw: dict[str, Any] = field(default_factory=dict, repr=False)

    # ── Derived ───────────────────────────────────────────────────────────────
    @property
    def total_minutes(self) -> float:
        return sum(s.total_minutes for s in self.steps)

    # ── Serialisation ─────────────────────────────────────────────────────────
    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "Protocol":
        steps = [Step.from_dict(s) for s in d.get("steps", [])]
        return cls(
            id=d.get("id", ""),
            name=d.get("name", ""),
            category=d.get("category", ""),
            description=d.get("description", ""),
            tags=d.get("tags", []),
            created_at=int(d.get("createdAt", d.get("created_at", 0))),
            updated_at=int(d.get("updatedAt", d.get("updated_at", 0))),
            steps=steps,
            _raw=d,
        )

    def to_dict(self) -> dict[str, Any]:
        d = dict(self._raw)
        d.update(
            id=self.id,
            name=self.name,
            category=self.category,
            description=self.description,
            tags=self.tags,
            createdAt=self.created_at,
            updatedAt=self.updated_at,
            steps=[s.to_dict() for s in self.steps],
        )
        return d
