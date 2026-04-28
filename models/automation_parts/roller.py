#!/usr/bin/env python3
"""输送滚筒 — φ100×500mm，带轴头"""
from __future__ import annotations

from build123d import Cylinder, Pos, Rot, Shape, Color

DISPLAY_NAME = "Conveyor Roller φ100×500"


def build_roller() -> Shape:
    # 滚筒主体
    body = Pos(0, 0, 0) * Rot(0, 90, 0) * Cylinder(50, 500)
    body.color = Color(0.25, 0.35, 0.55, 1.0)

    # 左轴头
    shaft_left = Pos(-265, 0, 0) * Rot(0, 90, 0) * Cylinder(12, 30)
    shaft_left.color = Color(0.85, 0.85, 0.87, 1.0)

    # 右轴头
    shaft_right = Pos(235, 0, 0) * Rot(0, 90, 0) * Cylinder(12, 30)
    shaft_right.color = Color(0.85, 0.85, 0.87, 1.0)

    roller = body + shaft_left + shaft_right
    roller = Compound(obj=roller) if not isinstance(roller, Shape) else roller
    roller.label = "Roller"
    return roller


def gen_step() -> dict[str, object]:
    return {
        "shape": build_roller(),
        "step_output": "roller.step",
    }
