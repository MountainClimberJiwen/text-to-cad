#!/usr/bin/env python3
"""直线导向滑台 — 含导轨底座与滑块，安装底面为 Z=0 基准"""
from __future__ import annotations

from build123d import Box, Cylinder, Pos, Shape, Color, Compound

DISPLAY_NAME = "Linear Guide Slide 200×40"

RAIL_L = 200.0
RAIL_W = 40.0
RAIL_H = 15.0
BLOCK_W = 60.0
BLOCK_D = 45.0
BLOCK_H = 20.0
MOUNT_HOLE_DIA = 5.0
MOUNT_HOLE_SPAN_X = 160.0
MOUNT_HOLE_SPAN_Y = 24.0


def build_guide() -> Shape:
    # ---- 导轨底座（底面 Z=0） ----
    rail = Pos(0, 0, RAIL_H / 2) * Box(RAIL_L, RAIL_W, RAIL_H)
    rail.color = Color(0.72, 0.72, 0.74, 1.0)

    # 导轨凸起条
    rail_rib = Pos(0, 0, RAIL_H + 3) * Box(RAIL_L, 12, 6)
    rail_rib.color = Color(0.65, 0.65, 0.67, 1.0)

    # 底座安装孔（4×φ5，四角）
    holes = []
    for dx in (-MOUNT_HOLE_SPAN_X / 2, MOUNT_HOLE_SPAN_X / 2):
        for dy in (-MOUNT_HOLE_SPAN_Y / 2, MOUNT_HOLE_SPAN_Y / 2):
            hole = Pos(dx, dy, RAIL_H / 2) * Cylinder(MOUNT_HOLE_DIA / 2, RAIL_H + 2)
            holes.append(hole)

    # ---- 滑块（可在导轨上滑动，初始位置居中） ----
    block = Pos(0, 0, RAIL_H + BLOCK_H / 2 + 3) * Box(BLOCK_W, BLOCK_D, BLOCK_H)
    block.color = Color(0.30, 0.30, 0.32, 1.0)  # 深灰色滑块

    # 滑块顶部安装平台
    block_top = Pos(0, 0, RAIL_H + BLOCK_H + 5) * Box(BLOCK_W + 10, BLOCK_D + 10, 4)
    block_top.color = Color(0.55, 0.55, 0.57, 1.0)

    # 滑块顶部安装孔（4×φ4）
    block_holes = []
    for dx in (-BLOCK_W / 2 + 8, BLOCK_W / 2 - 8):
        for dy in (-BLOCK_D / 2 + 8, BLOCK_D / 2 - 8):
            bh = Pos(dx, dy, RAIL_H + BLOCK_H + 5) * Cylinder(2.5, 6)
            block_holes.append(bh)

    # 滑块侧面防尘盖
    cover_front = Pos(0, BLOCK_D / 2 + 2, RAIL_H + BLOCK_H / 2 + 3) * Box(BLOCK_W, 2, BLOCK_H)
    cover_front.color = Color(0.20, 0.20, 0.22, 1.0)
    cover_rear = Pos(0, -BLOCK_D / 2 - 2, RAIL_H + BLOCK_H / 2 + 3) * Box(BLOCK_W, 2, BLOCK_H)
    cover_rear.color = Color(0.20, 0.20, 0.22, 1.0)

    guide = rail + rail_rib + block + block_top + cover_front + cover_rear
    for hole in holes:
        guide -= hole
    for bh in block_holes:
        guide -= bh

    guide = Compound(obj=guide) if not isinstance(guide, Shape) else guide
    guide.label = "Linear_Guide_Slide"
    return guide


def gen_step() -> dict[str, object]:
    return {
        "shape": build_guide(),
        "step_output": "linear_guide.step",
    }
