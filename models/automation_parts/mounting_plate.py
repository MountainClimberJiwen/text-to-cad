#!/usr/bin/env python3
"""控制柜安装背板 — 标准 perforated 钢板"""
from __future__ import annotations

from build123d import Box, Cylinder, Pos, Shape, Color

DISPLAY_NAME = "Mounting Plate 400×300"

WIDTH = 400.0
HEIGHT = 300.0
THICKNESS = 2.0
HOLE_DIA = 5.0
HOLE_GRID_X = 25.0
HOLE_GRID_Y = 25.0


def build_mounting_plate() -> Shape:
    plate = Pos(0, 0, THICKNESS / 2) * Box(WIDTH, HEIGHT, THICKNESS)
    plate.color = Color(0.92, 0.93, 0.95, 1.0)  # 镀锌板白

    # 网格安装孔（简化，只打边沿和四角）
    holes = []
    margin = 12.5
    nx = int((WIDTH - 2 * margin) / HOLE_GRID_X)
    ny = int((HEIGHT - 2 * margin) / HOLE_GRID_Y)

    for i in range(nx + 1):
        for j in range(ny + 1):
            if i % 4 == 0 or j % 4 == 0:  # 稀疏化
                x = -WIDTH / 2 + margin + i * HOLE_GRID_X
                y = -HEIGHT / 2 + margin + j * HOLE_GRID_Y
                hole = Pos(x, y, THICKNESS / 2) * Cylinder(HOLE_DIA / 2, THICKNESS + 1)
                holes.append(hole)

    for hole in holes:
        plate -= hole

    plate.label = "Mounting_Plate"
    return plate


def gen_step() -> dict[str, object]:
    return {
        "shape": build_mounting_plate(),
        "step_output": "mounting_plate.step",
    }
