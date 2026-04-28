#!/usr/bin/env python3
"""滚筒支架 — 成对 L 型轴承支架，轴承孔中心为原点，底面 Z=0"""
from __future__ import annotations

from build123d import Box, Cylinder, Pos, Shape, Color, Compound

DISPLAY_NAME = "Roller Bracket Pair"


def build_bracket() -> Shape:
    # 轴承孔中心在原点 (0,0,0)，底面在 Z=-40
    # 左支架
    base_l = Pos(-280, 0, -20) * Box(60, 120, 40)
    base_l.color = Color(0.65, 0.65, 0.68, 1.0)
    upright_l = Pos(-280, 0, 30) * Box(40, 80, 60)
    upright_l.color = Color(0.65, 0.65, 0.68, 1.0)
    # 轴承孔（φ26，通孔）
    hole_l = Pos(-280, 0, 0) * Cylinder(13, 60)

    # 右支架
    base_r = Pos(280, 0, -20) * Box(60, 120, 40)
    base_r.color = Color(0.65, 0.65, 0.68, 1.0)
    upright_r = Pos(280, 0, 30) * Box(40, 80, 60)
    upright_r.color = Color(0.65, 0.65, 0.68, 1.0)
    # 轴承孔
    hole_r = Pos(280, 0, 0) * Cylinder(13, 60)

    brackets = base_l + upright_l + base_r + upright_r
    brackets -= hole_l
    brackets -= hole_r

    brackets = Compound(obj=brackets) if not isinstance(brackets, Shape) else brackets
    brackets.label = "RollerBrackets"
    return brackets


def gen_step() -> dict[str, object]:
    return {
        "shape": build_bracket(),
        "step_output": "roller_bracket.step",
    }
