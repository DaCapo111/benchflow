"""Protocol and Step dataclasses."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any


@dataclass
class Step:
    id: str
    title: str
    step_type: str = "other"
    wait_minutes: float = 0.0
    hands_on_minutes: float = 0.0
    notes: str = ""
    reagents: list[dict[str, Any]] = field(default_factory=list)
    # extra fields stored as raw dict to avoid losing unknown keys
    _raw: dict[str, Any] = field(default_factory=dict, repr=False)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "Step":
        return cls(
            id=d.get("id", ""),
            title=d.get("title", ""),
            step_type=d.get("type", d.get("step_type", "other")),
            wait_minutes=float(d.get("waitMinutes", d.get("wait_minutes", 0))),
            hands_on_minutes=float(d.get("handsOnMinutes", d.get("hands_on_minutes", 0))),
            notes=d.get("notes", ""),
            reagents=d.get("reagents", []),
            _raw=d,
        )

    def to_dict(self) -> dict[str, Any]:
        d = dict(self._raw)
        d.update(
            id=self.id,
            title=self.title,
            type=self.step_type,
            waitMinutes=self.wait_minutes,
            handsOnMinutes=self.hands_on_minutes,
            notes=self.notes,
            reagents=self.reagents,
        )
        return d


@dataclass
class Protocol:
    id: str
    name: str
    steps: list[Step] = field(default_factory=list)
    created_at: str = ""
    updated_at: str = ""
    description: str = ""
    category: str = ""
    tags: list[str] = field(default_factory=list)
    _raw: dict[str, Any] = field(default_factory=dict, repr=False)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "Protocol":
        steps = [Step.from_dict(s) for s in d.get("steps", [])]
        return cls(
            id=d.get("id", ""),
            name=d.get("name", ""),
            steps=steps,
            created_at=d.get("createdAt", d.get("created_at", "")),
            updated_at=d.get("updatedAt", d.get("updated_at", "")),
            description=d.get("description", ""),
            category=d.get("category", ""),
            tags=d.get("tags", []),
            _raw=d,
        )

    def to_dict(self) -> dict[str, Any]:
        d = dict(self._raw)
        d.update(
            id=self.id,
            name=self.name,
            steps=[s.to_dict() for s in self.steps],
            createdAt=self.created_at,
            updatedAt=self.updated_at,
            description=self.description,
            category=self.category,
            tags=self.tags,
        )
        return d
