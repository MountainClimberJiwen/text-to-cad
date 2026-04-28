#!/usr/bin/env python3
"""DIN 导轨 — 标准 35mm 顶帽型铝导轨"""
from __future__ import annotations

from build123d import Box, Pos, Shape, Color

DISPLAY_NAME = "DIN Rail 35×7.5"

LENGTH = 300.0
WIDTH = 35.0
HEIGHT = 7.5
TOP_WIDTH = 25.0
TOP_HEIGHT = 4.0
SLOT_W = 4.5
SLOT_H = 2.5


def build_din_rail() -> Shape:
    # 主体底座
    base = Pos(0, 0, HEIGHT / 2) * Box(WIDTH, LENGTH, HEIGHT)
    base.color = Color(0.75, 0.78, 0.82, 1.0)  # 铝原色

    # 顶部凸起
    top = Pos(0, 0, HEIGHT + TOP_HEIGHT / 2) * Box(TOP_WIDTH, LENGTH, TOP_HEIGHT)
    top.color = Color(0.75, 0.78, 0.82, 1.0)

    rail = base + top

    # 中心长槽（简化）
    slot = Pos(0, 0, HEIGHT / 2) * Box(SLOT_W, LENGTH + 2, SLOT_H)
    rail -= slot

    rail.label = "DIN_Rail"
    return rail


def gen_step() -> dict[str, object]:
    return {
        "shape": build_din_rail(),
        "step_output": "din_rail.step",
    }
