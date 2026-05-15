#!/usr/bin/env python3
"""搬运门架 — 双立柱+横梁+水平滑台+竖直滑轨，支撑 XY 搬运模组，安装底面为 Z=0 基准"""
from __future__ import annotations

import math
from build123d import Box, Cylinder, Pos, Rot, Shape, Color, Compound

DISPLAY_NAME = "Transfer Gantry Frame"

COLUMN_W = 80.0
COLUMN_D = 60.0
COLUMN_H = 500.0
COLUMN_SPAN = 200.0
BEAM_L = 280.0
BEAM_W = 80.0
BEAM_H = 60.0
BASE_PLATE_W = 300.0
BASE_PLATE_D = 160.0
BASE_PLATE_H = 20.0

# 水平滑台参数
H_RAIL_W = 18.0
H_RAIL_H = 10.0
H_SLIDE_W = 50.0
H_SLIDE_D = 55.0
H_SLIDE_H = 25.0

# 竖直滑轨参数
V_PLATE_W = 60.0
V_PLATE_D = 12.0
V_PLATE_H = 120.0
V_RAIL_W = 12.0
V_RAIL_H = 30.0


def build_column() -> Shape:
    # ---- 安装底板（底面 Z=0） ----
    base_plate = Pos(0, 0, BASE_PLATE_H / 2) * Box(BASE_PLATE_W, BASE_PLATE_D, BASE_PLATE_H)
    base_plate.color = Color(0.75, 0.72, 0.68, 1.0)  # 米色

    # 底板安装孔（4×φ8）
    holes = []
    for dx in (-BASE_PLATE_W / 2 + 25, BASE_PLATE_W / 2 - 25):
        for dy in (-BASE_PLATE_D / 2 + 25, BASE_PLATE_D / 2 - 25):
            hole = Pos(dx, dy, BASE_PLATE_H / 2) * Cylinder(4, BASE_PLATE_H + 2)
            holes.append(hole)

    # ---- 双立柱 ----
    left_col = Pos(-COLUMN_SPAN / 2, 0, BASE_PLATE_H + COLUMN_H / 2) * Box(COLUMN_W, COLUMN_D, COLUMN_H)
    left_col.color = Color(0.78, 0.75, 0.70, 1.0)
    right_col = Pos(COLUMN_SPAN / 2, 0, BASE_PLATE_H + COLUMN_H / 2) * Box(COLUMN_W, COLUMN_D, COLUMN_H)
    right_col.color = Color(0.78, 0.75, 0.70, 1.0)

    # 立柱底部加强筋
    gussets = []
    for dx in (-COLUMN_SPAN / 2 - COLUMN_W / 2 - 15, -COLUMN_SPAN / 2 + COLUMN_W / 2 + 15,
               COLUMN_SPAN / 2 - COLUMN_W / 2 - 15, COLUMN_SPAN / 2 + COLUMN_W / 2 + 15):
        g = Pos(dx, 0, BASE_PLATE_H + 50) * Box(20, 8, 100)
        g.color = Color(0.70, 0.67, 0.62, 1.0)
        gussets.append(g)

    # ---- 顶部横梁 ----
    beam = Pos(0, 0, BASE_PLATE_H + COLUMN_H + BEAM_H / 2) * Box(BEAM_L, BEAM_W, BEAM_H)
    beam.color = Color(0.78, 0.75, 0.70, 1.0)

    # 横梁端板
    end_plate_left = Pos(-BEAM_L / 2 - 5, 0, BASE_PLATE_H + COLUMN_H + BEAM_H / 2) * Box(10, BEAM_W + 10, BEAM_H + 10)
    end_plate_left.color = Color(0.70, 0.67, 0.62, 1.0)
    end_plate_right = Pos(BEAM_L / 2 + 5, 0, BASE_PLATE_H + COLUMN_H + BEAM_H / 2) * Box(10, BEAM_W + 10, BEAM_H + 10)
    end_plate_right.color = Color(0.70, 0.67, 0.62, 1.0)

    # ---- 横梁底部水平导轨（位于两立柱之间，Y≈0 区域） ----
    h_rail1 = Pos(0, -15, BASE_PLATE_H + COLUMN_H - H_RAIL_H / 2) * Box(BEAM_L - 30, H_RAIL_W, H_RAIL_H)
    h_rail1.color = Color(0.60, 0.60, 0.62, 1.0)
    h_rail2 = Pos(0, 15, BASE_PLATE_H + COLUMN_H - H_RAIL_H / 2) * Box(BEAM_L - 30, H_RAIL_W, H_RAIL_H)
    h_rail2.color = Color(0.60, 0.60, 0.62, 1.0)

    # ---- 水平滑块（可在导轨上左右滑动，初始位置居中） ----
    h_slide = Pos(0, 0, BASE_PLATE_H + COLUMN_H - H_RAIL_H - H_SLIDE_H / 2) * Box(H_SLIDE_W, H_SLIDE_D, H_SLIDE_H)
    h_slide.color = Color(0.55, 0.55, 0.57, 1.0)

    # ---- 绿色竖直安装板（固定在水平滑块下方，位于两立柱之间） ----
    # 绿色板在 Y=0 附近，与立柱平行
    v_plate = Pos(0, 0, BASE_PLATE_H + COLUMN_H - H_RAIL_H - H_SLIDE_H - V_PLATE_H / 2) * Box(
        V_PLATE_W, V_PLATE_D, V_PLATE_H
    )
    v_plate.color = Color(0.20, 0.55, 0.25, 1.0)  # 绿色，与原图一致

    # 竖直导轨（固定在绿色板正面）
    v_rail_left = Pos(-15, V_PLATE_D / 2 + 3,
                      BASE_PLATE_H + COLUMN_H - H_RAIL_H - H_SLIDE_H - V_PLATE_H / 2) * Box(
        V_RAIL_W, 6, V_PLATE_H
    )
    v_rail_left.color = Color(0.50, 0.50, 0.52, 1.0)
    v_rail_right = Pos(15, V_PLATE_D / 2 + 3,
                       BASE_PLATE_H + COLUMN_H - H_RAIL_H - H_SLIDE_H - V_PLATE_H / 2) * Box(
        V_RAIL_W, 6, V_PLATE_H
    )
    v_rail_right.color = Color(0.50, 0.50, 0.52, 1.0)

    # 竖直滑块（可在竖直导轨上滑动）
    v_slide = Pos(0, V_PLATE_D / 2 + 6,
                  BASE_PLATE_H + COLUMN_H - H_RAIL_H - H_SLIDE_H - V_PLATE_H / 2) * Box(
        36, 8, 50
    )
    v_slide.color = Color(0.30, 0.30, 0.32, 1.0)

    # ---- 顶部气管/电缆保护管（两根，竖直向上） ----
    tube1 = Pos(-30, 0, BASE_PLATE_H + COLUMN_H + BEAM_H + 100) * Cylinder(12, 200)
    tube1.color = Color(0.45, 0.45, 0.47, 1.0)
    tube2 = Pos(30, 0, BASE_PLATE_H + COLUMN_H + BEAM_H + 100) * Cylinder(12, 200)
    tube2.color = Color(0.45, 0.45, 0.47, 1.0)
    # 管座
    tube_base1 = Pos(-30, 0, BASE_PLATE_H + COLUMN_H + BEAM_H + 5) * Cylinder(18, 10)
    tube_base1.color = Color(0.50, 0.50, 0.52, 1.0)
    tube_base2 = Pos(30, 0, BASE_PLATE_H + COLUMN_H + BEAM_H + 5) * Cylinder(18, 10)
    tube_base2.color = Color(0.50, 0.50, 0.52, 1.0)

    # ---- 简化气管（从顶部管座连接到下方气口） ----
    # 气管1：从左侧管座弯向水平气缸 rear port
    hose1_v = Pos(-30, 0, BASE_PLATE_H + COLUMN_H + BEAM_H - 10) * Cylinder(4, 40)
    hose1_v.color = Color(0.30, 0.30, 0.32, 1.0)
    hose1_h = Pos(-30, 0, BASE_PLATE_H + COLUMN_H + BEAM_H - 30) * Rot(90, 0, 0) * Cylinder(4, 60)
    hose1_h.color = Color(0.30, 0.30, 0.32, 1.0)

    # 气管2：从右侧管座弯向竖直气缸 top port
    hose2_v = Pos(30, 0, BASE_PLATE_H + COLUMN_H + BEAM_H - 10) * Cylinder(4, 50)
    hose2_v.color = Color(0.30, 0.30, 0.32, 1.0)
    hose2_h = Pos(30, 15, BASE_PLATE_H + COLUMN_H + BEAM_H - 40) * Rot(90, 0, 0) * Cylinder(4, 30)
    hose2_h.color = Color(0.30, 0.30, 0.32, 1.0)

    result = base_plate + left_col + right_col + beam + end_plate_left + end_plate_right
    result += h_rail1 + h_rail2 + h_slide + v_plate + v_rail_left + v_rail_right + v_slide
    result += tube1 + tube2 + tube_base1 + tube_base2
    result += hose1_v + hose1_h + hose2_v + hose2_h
    for g in gussets:
        result += g
    for hole in holes:
        result -= hole

    result = Compound(obj=result) if not isinstance(result, Shape) else result
    result.label = "Transfer_Gantry"
    return result


def gen_step() -> dict[str, object]:
    return {
        "shape": build_column(),
        "step_output": "transfer_column.step",
    }
