#!/usr/bin/env python3
"""气缸安装支架 — L形支架，安装底面为 Z=0 基准"""
from __future__ import annotations

from build123d import Box, Cylinder, Pos, Shape, Color, Compound

DISPLAY_NAME = "Cylinder L-Bracket"

BASE_W = 50.0
BASE_D = 40.0
BASE_H = 8.0
VERT_W = 40.0
VERT_H = 50.0
VERT_T = 8.0
HOLE_DIA = 5.0


def build_bracket() -> Shape:
    # 底板
    base = Pos(0, 0, BASE_H / 2) * Box(BASE_W, BASE_D, BASE_H)
    base.color = Color(0.65, 0.65, 0.67, 1.0)

    # 竖直板
    vert = Pos(0, BASE_D / 2 + VERT_T / 2, BASE_H + VERT_H / 2) * Box(VERT_W, VERT_T, VERT_H)
    vert.color = Color(0.65, 0.65, 0.67, 1.0)

    # 加强筋
    gusset = Pos(0, BASE_D / 2 - 5, BASE_H + 15) * Box(VERT_W - 10, 8, 30)
    gusset.color = Color(0.60, 0.60, 0.62, 1.0)

    # 安装孔
    hole1 = Pos(-15, 0, BASE_H / 2) * Cylinder(HOLE_DIA / 2, BASE_H + 2)
    hole2 = Pos(15, 0, BASE_H / 2) * Cylinder(HOLE_DIA / 2, BASE_H + 2)
    # 竖直板安装孔
    hole3 = Pos(0, BASE_D / 2 + VERT_T / 2, BASE_H + VERT_H - 15) * Cylinder(HOLE_DIA / 2, VERT_T + 2)

    bracket = base + vert + gusset
    bracket -= hole1
    bracket -= hole2
    bracket -= hole3

    bracket = Compound(obj=bracket) if not isinstance(bracket, Shape) else bracket
    bracket.label = "Cylinder_Bracket"
    return bracket


def gen_step() -> dict[str, object]:
    return {
        "shape": build_bracket(),
        "step_output": "cylinder_bracket.step",
    }
