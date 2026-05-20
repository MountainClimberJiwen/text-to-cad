#!/usr/bin/env python3
"""M6 平垫圈"""
from __future__ import annotations

from build123d import Cylinder, Pos, Shape, Color, Compound

DISPLAY_NAME = "Flat Washer M6"

OD = 12.0
ID = 6.5
THICKNESS = 1.5


def build_washer() -> Shape:
    body = Pos(0, 0, THICKNESS / 2) * Cylinder(OD / 2, THICKNESS)
    body.color = Color(0.72, 0.72, 0.74, 1.0)
    hole = Pos(0, 0, THICKNESS / 2) * Cylinder(ID / 2, THICKNESS + 2)
    washer = body - hole
    washer = Compound(obj=washer) if not isinstance(washer, Shape) else washer
    washer.label = "Flat_Washer_M6"
    return washer


def gen_step() -> dict[str, object]:
    return {
        "shape": build_washer(),
        "step_output": "flat_washer_m6.step",
    }
