#!/usr/bin/env python3
"""Φ6 PU 气管 — 蓝色半透明，两端带快插接头示意"""
from __future__ import annotations

from build123d import Cylinder, Pos, Shape, Color, Compound

DISPLAY_NAME = "Air Tube Φ6×100"

TUBE_DIA = 6.0
TUBE_LEN = 100.0
FITTING_DIA = 8.0
FITTING_LEN = 8.0


def build_tube() -> Shape:
    # 主气管
    tube = Pos(0, 0, TUBE_LEN / 2) * Cylinder(TUBE_DIA / 2, TUBE_LEN)
    tube.color = Color(0.15, 0.35, 0.75, 0.6)  # 蓝色半透明

    # 两端快插接头（金属色）
    fitting1 = Pos(0, 0, FITTING_LEN / 2) * Cylinder(FITTING_DIA / 2, FITTING_LEN)
    fitting1.color = Color(0.55, 0.55, 0.58, 1.0)
    fitting2 = Pos(0, 0, TUBE_LEN - FITTING_LEN / 2) * Cylinder(FITTING_DIA / 2, FITTING_LEN)
    fitting2.color = Color(0.55, 0.55, 0.58, 1.0)

    result = tube + fitting1 + fitting2
    result = Compound(obj=result) if not isinstance(result, Shape) else result
    result.label = "Air_Tube_6mm"
    return result


def gen_step() -> dict[str, object]:
    return {
        "shape": build_tube(),
        "step_output": "air_tube_6mm.step",
    }
