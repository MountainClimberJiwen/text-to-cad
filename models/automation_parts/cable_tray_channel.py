#!/usr/bin/env python3
"""线槽 — 工业走线槽"""
from __future__ import annotations

from build123d import Box, Pos, Shape, Color

DISPLAY_NAME = "Cable Tray Channel"


def build_tray() -> Shape:
    # 槽体
    tray = Pos(0, 0, 0) * Box(1000, 40, 20)
    tray.color = Color(0.45, 0.45, 0.48, 1.0)
    tray.label = "CableTray"
    return tray


def gen_step() -> dict[str, object]:
    return {
        "shape": build_tray(),
        "step_output": "cable_tray_channel.step",
    }
