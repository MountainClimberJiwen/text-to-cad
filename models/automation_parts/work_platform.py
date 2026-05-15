#!/usr/bin/env python3
"""工作平台/料道 — 连接振动盘出料口与取料位，安装底面为 Z=0 基准"""
from __future__ import annotations

from build123d import Box, Cylinder, Pos, Shape, Color, Compound

DISPLAY_NAME = "Work Platform & Feed Chute"

PLATE_L = 250.0
PLATE_W = 80.0
PLATE_H = 12.0
CHUTE_L = 180.0
CHUTE_W = 30.0
CHUTE_H = 25.0
GUIDE_H = 18.0
GUIDE_T = 3.0
STOP_BLOCK_W = 20.0
STOP_BLOCK_H = 18.0


def build_platform() -> Shape:
    # ---- 主平台板（底面 Z=0） ----
    plate = Pos(0, 0, PLATE_H / 2) * Box(PLATE_L, PLATE_W, PLATE_H)
    plate.color = Color(0.75, 0.75, 0.77, 1.0)

    # 安装孔（4×φ6）
    holes = []
    for dx in (-PLATE_L / 2 + 20, PLATE_L / 2 - 20):
        for dy in (-PLATE_W / 2 + 15, PLATE_W / 2 - 15):
            hole = Pos(dx, dy, PLATE_H / 2) * Cylinder(3, PLATE_H + 2)
            holes.append(hole)

    # ---- 料道（凹槽形式，用于引导零件） ----
    # 料道底板
    chute_floor = Pos(0, 0, PLATE_H + 2) * Box(CHUTE_L, CHUTE_W, 3)
    chute_floor.color = Color(0.80, 0.80, 0.82, 1.0)

    # 料道左侧挡板
    guide_left = Pos(0, -CHUTE_W / 2 - GUIDE_T / 2, PLATE_H + GUIDE_H / 2 + 2) * Box(
        CHUTE_L, GUIDE_T, GUIDE_H
    )
    guide_left.color = Color(0.65, 0.65, 0.67, 1.0)

    # 料道右侧挡板
    guide_right = Pos(0, CHUTE_W / 2 + GUIDE_T / 2, PLATE_H + GUIDE_H / 2 + 2) * Box(
        CHUTE_L, GUIDE_T, GUIDE_H
    )
    guide_right.color = Color(0.65, 0.65, 0.67, 1.0)

    # ---- 末端定位挡块（取料位） ----
    stop_block = Pos(CHUTE_L / 2 - STOP_BLOCK_W / 2, 0, PLATE_H + STOP_BLOCK_H / 2 + 2) * Box(
        STOP_BLOCK_W, CHUTE_W + 6, STOP_BLOCK_H
    )
    stop_block.color = Color(0.55, 0.55, 0.57, 1.0)

    # 定位销（取料位中心）
    locator = Pos(CHUTE_L / 2 - STOP_BLOCK_W - 5, 0, PLATE_H + 3) * Cylinder(2.5, 6)
    locator.color = Color(0.50, 0.50, 0.52, 1.0)

    result = plate + chute_floor + guide_left + guide_right + stop_block + locator
    for hole in holes:
        result -= hole

    result = Compound(obj=result) if not isinstance(result, Shape) else result
    result.label = "Work_Platform"
    return result


def gen_step() -> dict[str, object]:
    return {
        "shape": build_platform(),
        "step_output": "work_platform.step",
    }
