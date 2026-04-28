#!/usr/bin/env python3
"""光电传感器 — 漫反射型"""
from __future__ import annotations

from build123d import Box, Cylinder, Pos, Rot, Shape, Color

DISPLAY_NAME = "Photoelectric Sensor"

BODY_W = 20.0
BODY_H = 10.0
BODY_D = 30.0
LENS_DIA = 6.0
LENS_DEPTH = 3.0
CABLE_DIA = 4.0
CABLE_LEN = 60.0
MOUNT_BRACKET_W = 12.0
MOUNT_BRACKET_H = 18.0
MOUNT_BRACKET_D = 3.0
MOUNT_HOLE_DIA = 3.5


def build_photo_sensor() -> Shape:
    # 主体
    body = Pos(0, 0, BODY_D / 2) * Box(BODY_W, BODY_H, BODY_D)
    body.color = Color(0.1, 0.1, 0.12, 1.0)  # 黑色塑料壳

    # 透镜
    lens = Pos(0, 0, BODY_D + LENS_DEPTH / 2 - 1) * Cylinder(LENS_DIA / 2, LENS_DEPTH)
    lens.color = Color(0.3, 0.5, 0.8, 0.6)  # 半透明蓝

    # 电缆
    cable = Pos(0, 0, -CABLE_LEN / 2) * Cylinder(CABLE_DIA / 2, CABLE_LEN)
    cable.color = Color(0.05, 0.05, 0.05, 1.0)

    # L 型安装支架
    bracket_v = Pos(
        -BODY_W / 2 - MOUNT_BRACKET_D / 2,
        0,
        BODY_D - MOUNT_BRACKET_H / 2,
    ) * Box(MOUNT_BRACKET_D, BODY_H + 2, MOUNT_BRACKET_H)
    bracket_h = Pos(
        -BODY_W / 2 - MOUNT_BRACKET_W / 2,
        0,
        BODY_D - MOUNT_BRACKET_H + MOUNT_BRACKET_D / 2,
    ) * Box(MOUNT_BRACKET_W, BODY_H + 2, MOUNT_BRACKET_D)
    bracket = bracket_v + bracket_h
    bracket.color = Color(0.6, 0.6, 0.62, 1.0)

    # 支架安装孔
    hole = Pos(
        -BODY_W / 2 - MOUNT_BRACKET_W / 2,
        0,
        BODY_D - MOUNT_BRACKET_H + MOUNT_BRACKET_D / 2,
    ) * Cylinder(MOUNT_HOLE_DIA / 2, MOUNT_BRACKET_D + 2)

    sensor = body + lens + cable + bracket
    sensor -= hole

    sensor.label = "Photo_Sensor"
    return sensor


def gen_step() -> dict[str, object]:
    return {
        "shape": build_photo_sensor(),
        "step_output": "photo_sensor.step",
    }
