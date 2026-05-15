#!/usr/bin/env python3
"""振动盘送料器 — 碗形料斗+振动底座，安装底面为 Z=0 基准"""
from __future__ import annotations

import math
from build123d import (
    Box, Cylinder, Cone, Torus, Pos, Rot, Shape, Color, Compound,
    Vector, Vertex, Edge, Wire, Face, Solid, Shell,
    make_face, extrude, loft, add, sweep
)

DISPLAY_NAME = "Vibrating Bowl Feeder Φ300"

BOWL_DIA_TOP = 380.0
BOWL_DIA_BOTTOM = 180.0
BOWL_HEIGHT = 160.0
BASE_DIA = 300.0
BASE_HEIGHT = 80.0
TRACK_WIDTH = 30.0
TRACK_RISE = 80.0
OUTLET_LEN = 120.0
OUTLET_WIDTH = 35.0


def build_bowl() -> Shape:
    # ---- 振动底座（圆柱形，底面 Z=0） ----
    base = Pos(0, 0, BASE_HEIGHT / 2) * Cylinder(BASE_DIA / 2, BASE_HEIGHT)
    base.color = Color(0.55, 0.55, 0.58, 1.0)

    # 底座装饰环
    base_ring = Pos(0, 0, BASE_HEIGHT - 5) * Cylinder(BASE_DIA / 2 + 5, 10)
    base_ring.color = Color(0.50, 0.50, 0.53, 1.0)

    # ---- 料斗（截锥形） ----
    # 底部贴合底座顶面 Z=BASE_HEIGHT
    bowl_bottom = Pos(0, 0, BASE_HEIGHT) * Cylinder(BOWL_DIA_BOTTOM / 2, 1)
    bowl_top = Pos(0, 0, BASE_HEIGHT + BOWL_HEIGHT) * Cylinder(BOWL_DIA_TOP / 2, 1)

    # 使用圆锥近似碗形
    bowl = Pos(0, 0, BASE_HEIGHT + BOWL_HEIGHT / 2) * Cone(
        BOWL_DIA_BOTTOM / 2, BOWL_DIA_TOP / 2, BOWL_HEIGHT
    )
    bowl.color = Color(0.78, 0.78, 0.80, 1.0)

    # 碗口翻边
    rim = Pos(0, 0, BASE_HEIGHT + BOWL_HEIGHT + 3) * Cylinder(BOWL_DIA_TOP / 2 + 5, 6)
    rim.color = Color(0.70, 0.70, 0.72, 1.0)

    # ---- 螺旋轨道（简化表示为从碗壁延伸的坡道） ----
    # 出料口平台
    outlet = Pos(BOWL_DIA_TOP / 2 + OUTLET_LEN / 2 - 10, 0, BASE_HEIGHT + BOWL_HEIGHT - 10) * Box(
        OUTLET_LEN, OUTLET_WIDTH, 8
    )
    outlet.color = Color(0.75, 0.75, 0.77, 1.0)

    # 出料口挡板
    guard = Pos(BOWL_DIA_TOP / 2 + OUTLET_LEN / 2 - 10, OUTLET_WIDTH / 2 + 3, BASE_HEIGHT + BOWL_HEIGHT + 5) * Box(
        OUTLET_LEN, 3, 20
    )
    guard.color = Color(0.65, 0.65, 0.67, 1.0)

    # ---- 底座安装孔（4×φ8，均布） ----
    holes = []
    for angle in [45, 135, 225, 315]:
        r = BASE_DIA / 2 - 25
        hx = r * math.cos(math.radians(angle))
        hy = r * math.sin(math.radians(angle))
        hole = Pos(hx, hy, BASE_HEIGHT / 2) * Cylinder(4, BASE_HEIGHT + 2)
        holes.append(hole)

    # ---- 顶部料斗（方锥形料仓，用于储料） ----
    # 料仓位于与出料轨道相对的一侧（X 负方向）
    hopper = Pos(-BOWL_DIA_TOP / 2 - 80, 0, BASE_HEIGHT + BOWL_HEIGHT + 60) * Box(120, 120, 100)
    hopper.color = Color(0.80, 0.80, 0.82, 1.0)
    # 料仓底部缩口
    hopper_bottom = Pos(-BOWL_DIA_TOP / 2 - 80, 0, BASE_HEIGHT + BOWL_HEIGHT + 10) * Box(80, 80, 1)
    hopper_bottom.color = Color(0.75, 0.75, 0.77, 1.0)

    result = base + base_ring + bowl + rim + outlet + guard + hopper + hopper_bottom
    for hole in holes:
        result -= hole

    result = Compound(obj=result) if not isinstance(result, Shape) else result
    result.label = "Vibrating_Bowl_Feeder"
    return result


def gen_step() -> dict[str, object]:
    return {
        "shape": build_bowl(),
        "step_output": "vibrating_bowl.step",
    }
