#!/usr/bin/env python3
"""M6 六角螺母 — 含倒角示意"""
from __future__ import annotations

from build123d import Cylinder, Pos, Shape, Color, Compound

DISPLAY_NAME = "Hex Nut M6"

NUT_DIA = 10.0
NUT_H = 5.0
HOLE_DIA = 6.5


def build_nut() -> Shape:
    body = Pos(0, 0, NUT_H / 2) * Cylinder(NUT_DIA / 2, NUT_H)
    body.color = Color(0.68, 0.68, 0.70, 1.0)
    hole = Pos(0, 0, NUT_H / 2) * Cylinder(HOLE_DIA / 2, NUT_H + 2)
    nut = body - hole
    # 顶部倒角环
    chamfer = Pos(0, 0, NUT_H + 0.5) * Cylinder(NUT_DIA / 2 - 0.5, 1)
    chamfer.color = Color(0.60, 0.60, 0.62, 1.0)
    nut = nut + chamfer
    nut = Compound(obj=nut) if not isinstance(nut, Shape) else nut
    nut.label = "Hex_Nut_M6"
    return nut


def gen_step() -> dict[str, object]:
    return {
        "shape": build_nut(),
        "step_output": "hex_nut_m6.step",
    }
