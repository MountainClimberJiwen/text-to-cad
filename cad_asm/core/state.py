"""Workspace state management."""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any


class StepStatus(str, Enum):
    PENDING = "pending"
    IN_REVIEW = "in_review"
    APPROVED = "approved"
    DONE = "done"
    ERROR = "error"


@dataclass
class PartState:
    part_id: str
    status: StepStatus = StepStatus.PENDING
    # Path to the generated individual part file (under workspace/parts/)
    part_file: str | None = None
    # Resolved transform after placement (dict for JSON serialisation)
    resolved_transform: dict[str, Any] | None = None
    error_message: str | None = None


@dataclass
class ReviewRequest:
    iteration: int
    part_id: str
    proposed_transform: dict[str, Any]
    warnings: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)


@dataclass
class WorkspaceState:
    task_id: str
    iteration: int = 0
    parts: list[PartState] = field(default_factory=list)
    completed_constraints: list[dict[str, Any]] = field(default_factory=list)
    pending_constraints: list[dict[str, Any]] = field(default_factory=list)
    # Assembly checkpoint path relative to workspace root
    checkpoint_file: str | None = None
    status: Literal["running", "in_review", "done", "error"] = "running"
    last_error: str | None = None

    @classmethod
    def from_file(cls, path: Path) -> WorkspaceState:
        data = json.loads(path.read_text())
        parts = [PartState(**p) for p in data.pop("parts", [])]
        return cls(parts=parts, **data)

    def to_file(self, path: Path) -> None:
        path.write_text(json.dumps(self._to_dict(), indent=2))

    def _to_dict(self) -> dict[str, Any]:
        return {
            "task_id": self.task_id,
            "iteration": self.iteration,
            "parts": [asdict(p) for p in self.parts],
            "completed_constraints": self.completed_constraints,
            "pending_constraints": self.pending_constraints,
            "checkpoint_file": self.checkpoint_file,
            "status": self.status,
            "last_error": self.last_error,
        }

    def get_part(self, part_id: str) -> PartState | None:
        for p in self.parts:
            if p.part_id == part_id:
                return p
        return None


# Helper for type checker
from typing import Literal
