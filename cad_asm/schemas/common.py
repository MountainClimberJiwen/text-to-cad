"""Common geometric types shared across schemas."""
from __future__ import annotations

from pydantic import BaseModel, Field


class Vector3(BaseModel):
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0


class Rotation(BaseModel):
    axis: Vector3 = Field(default_factory=lambda: Vector3(x=0, y=0, z=1))
    angle_deg: float = 0.0


class Transform(BaseModel):
    position: Vector3 = Field(default_factory=Vector3)
    rotation: Rotation = Field(default_factory=Rotation)
