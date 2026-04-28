#!/usr/bin/env python3
"""接线端子排 — 导轨式弹簧端子"""
from __future__ import annotations

from build123d import Box, Cylinder, Pos, Shape, Color, Compound

DISPLAY_NAME = "Terminal Block 6P"

UNIT_W = 10.0
TOTAL_W = 60.0
HEIGHT = 45.0
DEPTH = 8.0
SCREW_DIA = 3.0
SCREW_DEPTH = 4.0
LED_DIA = 1.8
DIN_CLIP_H = 4.0


def build_terminal_block() -> Shape:
    # 主体
    body = Pos(0, 0, HEIGHT / 2) * Box(TOTAL_W, DEPTH, HEIGHT)
    body.color = Color(0.9, 0.9, 0.92, 1.0)  # 浅灰塑料

    # DIN 卡扣
    clip = Pos(0, 0, -DIN_CLIP_H / 2) * Box(TOTAL_W - 4, DEPTH - 2, DIN_CLIP_H)
    clip.color = Color(0.1, 0.1, 0.1, 1.0)

    # 螺钉/操作孔（6 个）
    screws = []
    for i in range(6):
        x = -TOTAL_W / 2 + UNIT_W / 2 + i * UNIT_W
        screw = Pos(x, DEPTH / 2 + SCREW_DEPTH / 2 - 1, HEIGHT - 10) * Box(3, SCREW_DEPTH, 3)
        screw.color = Color(0.2, 0.2, 0.2, 1.0)
        screws.append(screw)

    # 指示灯
    led = Pos(0, DEPTH / 2 + 1, HEIGHT - 22) * Cylinder(LED_DIA / 2, 2)
    led.color = Color(0.0, 0.6, 0.0, 1.0)

    tb = body + clip + led
    for screw in screws:
        tb += screw

    tb = Compound(obj=tb) if not isinstance(tb, Shape) else tb
    tb.label = "Terminal_Block"
    return tb


def gen_step() -> dict[str, object]:
    return {
        "shape": build_terminal_block(),
        "step_output": "terminal_block.step",
    }
