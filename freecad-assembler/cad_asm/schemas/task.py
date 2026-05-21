"""Task schema for cad-asm assembly jobs."""
from __future__ import annotations

from enum import Enum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from cad_asm.schemas.common import Transform, Vector3
from cad_asm.schemas.shape import ShapeDef


class ConstraintType(str, Enum):
    PLACE_AT = "place_at"           # absolute placement
    ALIGN_FACE = "align_face"       # align two faces
    COAXIAL = "coaxial"             # cylindrical axes aligned
    DISTANCE = "distance"           # fixed distance between features


class Constraint(BaseModel):
    type: ConstraintType
    part1: str
    part2: str
    # type-specific parameters
    params: dict[str, Any] = Field(default_factory=dict)


class PartSource(BaseModel):
    """How to obtain the part geometry."""
    type: str  # "python", "step", "stl", "build123d"
    # For 'python': path to a .py file that exports a Part / Solid when run
    # For 'step'/'stl': path to existing mesh file
    # For 'build123d': inline Python expression (advanced)
    path: str | None = None
    expression: str | None = None


class PartDef(BaseModel):
    id: str = Field(..., description="Unique part identifier")
    name: str | None = None
    source: PartSource | None = None
    shape: ShapeDef | None = None
    # Initial transform if no constraint applies yet
    initial_transform: Transform | None = None


class OutputConfig(BaseModel):
    step: str | None = None
    stl: str | None = None
    urdf: str | None = None
    report: str | None = None


class AssemblyTask(BaseModel):
    """Root task descriptor consumed by `cad-asm init`."""
    task_id: str
    name: str | None = None
    parts: list[PartDef]
    constraints: list[Constraint] = Field(default_factory=list)
    outputs: OutputConfig = Field(default_factory=OutputConfig)
    # Whether to pause for review before each part placement
    review_each_step: bool = True
    # Whether to auto-solve constraint order (True) or follow explicit order (False)
    auto_order: bool = True

    @classmethod
    def from_file(cls, path: Path) -> AssemblyTask:
        import json
        return cls.model_validate(json.loads(path.read_text()))

    def to_file(self, path: Path) -> None:
        import json
        path.write_text(self.model_dump_json(indent=2))
