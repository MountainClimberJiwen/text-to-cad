"""Declarative shape schema for build123d part generation."""
from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

from cad_asm.schemas.common import Transform


class ShapeType(str, Enum):
    BOX = "box"
    CYLINDER = "cylinder"
    SPHERE = "sphere"
    CONE = "cone"
    TORUS = "torus"
    UNION = "union"
    SUBTRACT = "subtract"
    INTERSECT = "intersect"
    LIBRARY = "library"


class ShapeDef(BaseModel):
    """Recursive shape definition consumed by `build_shape()`."""

    type: ShapeType
    params: dict[str, Any] = Field(default_factory=dict)
    transform: Transform | None = None
    children: list["ShapeDef"] = Field(default_factory=list)
