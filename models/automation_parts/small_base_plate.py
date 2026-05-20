#!/usr/bin/env python3
"""小型工作站底座板 — 800×500×15 铝型材面板，安装面 Z=0 基准"""
from __future__ import annotations

from build123d import Box, Cylinder, Pos, Shape, Color, Compound

DISPLAY_NAME = "Small Base Plate 800×500"

PLATE_L = 800.0
PLATE_W = 500.0
PLATE_H = 15.0
LEG_H = 60.0
LEG_W = 50.0


def build_plate() -> Shape:
    # ---- 主面板（顶面 Z=PLATE_H） ----
    plate = Pos(0, 0, PLATE_H / 2) * Box(PLATE_L, PLATE_W, PLATE_H)
    plate.color = Color(0.82, 0.84, 0.86, 1.0)  # 浅灰铝面板

    # 面板边缘倒角示意（薄边条）
    edge_front = Pos(0, -PLATE_W / 2 + 1, PLATE_H / 2) * Box(PLATE_L, 2, PLATE_H + 1)
    edge_front.color = Color(0.70, 0.72, 0.74, 1.0)
    edge_rear = Pos(0, PLATE_W / 2 - 1, PLATE_H / 2) * Box(PLATE_L, 2, PLATE_H + 1)
    edge_rear.color = Color(0.70, 0.72, 0.74, 1.0)
    edge_left = Pos(-PLATE_L / 2 + 1, 0, PLATE_H / 2) * Box(2, PLATE_W - 4, PLATE_H + 1)
    edge_left.color = Color(0.70, 0.72, 0.74, 1.0)
    edge_right = Pos(PLATE_L / 2 - 1, 0, PLATE_H / 2) * Box(2, PLATE_W - 4, PLATE_H + 1)
    edge_right.color = Color(0.70, 0.72, 0.74, 1.0)

    # ---- 4 条支腿（铝型材 50×50） ----
    legs = []
    for dx in (-PLATE_L / 2 + 40, PLATE_L / 2 - 40):
        for dy in (-PLATE_W / 2 + 40, PLATE_W / 2 - 40):
            leg = Pos(dx, dy, -LEG_H / 2) * Box(LEG_W, LEG_W, LEG_H)
            leg.color = Color(0.68, 0.70, 0.72, 1.0)
            legs.append(leg)

    # ---- 支脚底板 + 调平脚 ----
    feet = []
    for dx in (-PLATE_L / 2 + 40, PLATE_L / 2 - 40):
        for dy in (-PLATE_W / 2 + 40, PLATE_W / 2 - 40):
            # 金属底板
            fp = Pos(dx, dy, -LEG_H - 3) * Box(LEG_W + 16, LEG_W + 16, 6)
            fp.color = Color(0.55, 0.57, 0.60, 1.0)
            feet.append(fp)
            # 橡胶垫
            pad = Pos(dx, dy, -LEG_H - 6) * Cylinder(28, 3)
            pad.color = Color(0.15, 0.15, 0.15, 1.0)
            feet.append(pad)

    # ---- 面板安装孔阵列（M6 螺纹孔，100×100 间距） ----
    holes = []
    for dx in range(-350, 351, 100):
        for dy in range(-200, 201, 100):
            hole = Pos(dx, dy, PLATE_H / 2) * Cylinder(3, PLATE_H + 2)
            holes.append(hole)

    # ---- 中心定位销孔（2×φ8，用于立柱定位） ----
    pin_hole1 = Pos(-100, 0, PLATE_H / 2) * Cylinder(4, PLATE_H + 2)
    pin_hole2 = Pos(100, 0, PLATE_H / 2) * Cylinder(4, PLATE_H + 2)

    result = plate + edge_front + edge_rear + edge_left + edge_right
    for leg in legs:
        result += leg
    for f in feet:
        result += f
    for hole in holes:
        result -= hole
    result -= pin_hole1
    result -= pin_hole2

    result = Compound(obj=result) if not isinstance(result, Shape) else result
    result.label = "Small_Base_Plate"
    return result


def gen_step() -> dict[str, object]:
    return {
        "shape": build_plate(),
        "step_output": "small_base_plate.step",
    }
