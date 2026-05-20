#!/usr/bin/env python3
"""M8×25 六角头螺栓 — 含螺杆、螺纹示意、六角头"""
from __future__ import annotations

from build123d import Cylinder, Pos, Shape, Color, Compound

DISPLAY_NAME = "Bolt M8×25"

HEAD_DIA = 13.0
HEAD_H = 5.0
SHANK_DIA = 8.0
SHANK_LEN = 25.0


def build_bolt() -> Shape:
    head = Pos(0, 0, HEAD_H / 2) * Cylinder(HEAD_DIA / 2, HEAD_H)
    head.color = Color(0.70, 0.70, 0.72, 1.0)
    shank = Pos(0, 0, HEAD_H + SHANK_LEN / 2) * Cylinder(SHANK_DIA / 2, SHANK_LEN)
    shank.color = Color(0.76, 0.76, 0.78, 1.0)
    threads = []
    for i in range(4):
        z = HEAD_H + SHANK_LEN * 0.25 + i * SHANK_LEN * 0.18
        ring = Pos(0, 0, z) * Cylinder(SHANK_DIA / 2 + 0.3, 0.8)
        ring.color = Color(0.63, 0.63, 0.65, 1.0)
        threads.append(ring)
    bolt = head + shank
    for t in threads:
        bolt += t
    bolt = Compound(obj=bolt) if not isinstance(bolt, Shape) else bolt
    bolt.label = "Bolt_M8x25"
    return bolt


def gen_step() -> dict[str, object]:
    return {
        "shape": build_bolt(),
        "step_output": "bolt_m8x25.step",
    }
