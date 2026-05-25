#!/usr/bin/env python3
"""振动盘上料单元底座 — 1200×800 平板式工作台，安装面 Z=0"""
from __future__ import annotations

from build123d import Box, Cylinder, Pos, Shape, Color, Compound

DISPLAY_NAME = "Feeder Base Plate 1200×800"

PLATE_L = 1200.0
PLATE_W = 800.0
PLATE_H = 30.0
LEG_H = 80.0
LEG_W = 60.0


def build_base() -> Shape:
    # 主平台
    plate = Pos(0, 0, PLATE_H / 2) * Box(PLATE_L, PLATE_W, PLATE_H)
    plate.color = Color(0.68, 0.68, 0.70, 1.0)

    # 四条支腿
    legs = []
    for dx in (-PLATE_L / 2 + 60, PLATE_L / 2 - 60):
        for dy in (-PLATE_W / 2 + 60, PLATE_W / 2 - 60):
            leg = Pos(dx, dy, -LEG_H / 2) * Box(LEG_W, LEG_W, LEG_H)
            leg.color = Color(0.60, 0.60, 0.62, 1.0)
            legs.append(leg)

    # 支脚底板
    foot_plates = []
    for dx in (-PLATE_L / 2 + 60, PLATE_L / 2 - 60):
        for dy in (-PLATE_W / 2 + 60, PLATE_W / 2 - 60):
            fp = Pos(dx, dy, -LEG_H - 5) * Box(LEG_W + 20, LEG_W + 20, 10)
            fp.color = Color(0.55, 0.55, 0.57, 1.0)
            foot_plates.append(fp)

    # 平台表面安装孔阵列（简化示意）
    holes = []
    for dx in range(-500, 501, 100):
        for dy in range(-300, 301, 100):
            hole = Pos(dx, dy, PLATE_H / 2) * Cylinder(3, PLATE_H + 2)
            holes.append(hole)

    result = plate
    for leg in legs:
        result += leg
    for fp in foot_plates:
        result += fp
    for hole in holes:
        result -= hole

    result = Compound(obj=result) if not isinstance(result, Shape) else result
    result.label = "Feeder_Base"
    return result


def gen_step() -> dict[str, object]:
    return {
        "shape": build_base(),
        "step_output": "feeder_base.step",
    }
