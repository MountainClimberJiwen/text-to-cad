#!/usr/bin/env python3
"""M6×20 六角头螺栓 — 含螺杆、螺纹示意、六角头，安装轴线为 Z"""
from __future__ import annotations

from build123d import Box, Cylinder, Pos, Shape, Color, Compound

DISPLAY_NAME = "Bolt M6×20"

HEAD_DIA = 10.0
HEAD_H = 4.0
SHANK_DIA = 6.0
SHANK_LEN = 20.0
THREAD_PITCH = 1.0


def build_bolt() -> Shape:
    # 六角头（外接圆近似）
    head = Pos(0, 0, HEAD_H / 2) * Cylinder(HEAD_DIA / 2, HEAD_H)
    head.color = Color(0.72, 0.72, 0.74, 1.0)

    # 螺杆（光杆段）
    shank = Pos(0, 0, HEAD_H + SHANK_LEN / 2) * Cylinder(SHANK_DIA / 2, SHANK_LEN)
    shank.color = Color(0.78, 0.78, 0.80, 1.0)

    # 螺纹示意（3 道细环）
    threads = []
    for i in range(3):
        z = HEAD_H + SHANK_LEN * 0.3 + i * SHANK_LEN * 0.25
        ring = Pos(0, 0, z) * Cylinder(SHANK_DIA / 2 + 0.3, 0.8)
        ring.color = Color(0.65, 0.65, 0.67, 1.0)
        threads.append(ring)

    bolt = head + shank
    for t in threads:
        bolt += t

    bolt = Compound(obj=bolt) if not isinstance(bolt, Shape) else bolt
    bolt.label = "Bolt_M6x20"
    return bolt


def gen_step() -> dict[str, object]:
    return {
        "shape": build_bolt(),
        "step_output": "bolt_m6x20.step",
    }
