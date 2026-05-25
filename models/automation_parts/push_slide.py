#!/usr/bin/env python3
"""推料机构 — 含L形推料叉、微型导轨、安装底板，安装底面为 Z=0 基准"""
from __future__ import annotations

from build123d import Box, Cylinder, Pos, Shape, Color, Compound

DISPLAY_NAME = "Push Slide Mechanism"

BASE_L = 180.0
BASE_W = 60.0
BASE_H = 12.0
RAIL_L = 150.0
RAIL_W = 12.0
RAIL_H = 8.0
BLOCK_W = 35.0
BLOCK_D = 28.0
BLOCK_H = 22.0
FORK_W = 4.0
FORK_L = 25.0
FORK_H = 18.0
FORK_GAP = 12.0


def build_push_slide() -> Shape:
    # ---- 安装底板（底面 Z=0） ----
    base = Pos(0, 0, BASE_H / 2) * Box(BASE_L, BASE_W, BASE_H)
    base.color = Color(0.72, 0.72, 0.74, 1.0)

    # 底板安装孔（4×φ5）
    holes = []
    for dx in (-BASE_L / 2 + 15, BASE_L / 2 - 15):
        for dy in (-BASE_W / 2 + 10, BASE_W / 2 - 10):
            hole = Pos(dx, dy, BASE_H / 2) * Cylinder(2.5, BASE_H + 2)
            holes.append(hole)

    # ---- 微型导轨（两条平行轨） ----
    rail1 = Pos(0, -10, BASE_H + RAIL_H / 2) * Box(RAIL_L, RAIL_W, RAIL_H)
    rail1.color = Color(0.60, 0.60, 0.62, 1.0)
    rail2 = Pos(0, 10, BASE_H + RAIL_H / 2) * Box(RAIL_L, RAIL_W, RAIL_H)
    rail2.color = Color(0.60, 0.60, 0.62, 1.0)

    # ---- 推料滑块主体 ----
    block = Pos(25, 0, BASE_H + RAIL_H + BLOCK_H / 2) * Box(BLOCK_W, BLOCK_D, BLOCK_H)
    block.color = Color(0.15, 0.15, 0.17, 1.0)  # 深黑色推料块

    # ---- L形推料叉（双叉） ----
    # 上横臂
    fork_arm = Pos(25 + BLOCK_W / 2 + FORK_L / 2, 0, BASE_H + RAIL_H + BLOCK_H - FORK_H / 2) * Box(
        FORK_L, BLOCK_D, FORK_H
    )
    fork_arm.color = Color(0.20, 0.20, 0.22, 1.0)

    # 左叉齿
    fork_left = Pos(25 + BLOCK_W / 2 + FORK_L, -FORK_GAP / 2 - FORK_W / 2,
                    BASE_H + RAIL_H + BLOCK_H / 2) * Box(
        FORK_W, FORK_W, BLOCK_H
    )
    fork_left.color = Color(0.20, 0.20, 0.22, 1.0)

    # 右叉齿
    fork_right = Pos(25 + BLOCK_W / 2 + FORK_L, FORK_GAP / 2 + FORK_W / 2,
                     BASE_H + RAIL_H + BLOCK_H / 2) * Box(
        FORK_W, FORK_W, BLOCK_H
    )
    fork_right.color = Color(0.20, 0.20, 0.22, 1.0)

    # 气缸连接头（滑块背面）
    conn = Pos(25 - BLOCK_W / 2 - 5, 0, BASE_H + RAIL_H + BLOCK_H / 2) * Cylinder(5, 10)
    conn.color = Color(0.70, 0.70, 0.72, 1.0)

    result = base + rail1 + rail2 + block + fork_arm + fork_left + fork_right + conn
    for hole in holes:
        result -= hole

    result = Compound(obj=result) if not isinstance(result, Shape) else result
    result.label = "Push_Slide"
    return result


def gen_step() -> dict[str, object]:
    return {
        "shape": build_push_slide(),
        "step_output": "push_slide.step",
    }
