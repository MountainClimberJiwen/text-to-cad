#!/usr/bin/env python3
"""伺服电机 — 标准 80mm 法兰工业伺服"""
from __future__ import annotations

from build123d import Box, Cylinder, Pos, Rot, Shape, Color

DISPLAY_NAME = "Servo Motor 80mm Flange"

FLANGE_W = 80.0
FLANGE_H = 80.0
FLANGE_D = 10.0
BODY_D = 95.0
BODY_DIA = 62.0
SHAFT_DIA = 14.0
SHAFT_LEN = 30.0
SHAFT_KEY_W = 5.0
SHAFT_KEY_H = 3.0
CONN_BOX_W = 50.0
CONN_BOX_H = 30.0
CONN_BOX_D = 35.0


def build_servo() -> Shape:
    # 法兰盘
    flange = Pos(0, 0, FLANGE_D / 2) * Box(FLANGE_W, FLANGE_H, FLANGE_D)
    flange.color = Color(0.75, 0.75, 0.78, 1.0)  # 银灰铝色

    # 安装孔（4 角）
    holes = []
    hole_offset = 35.0
    for dx in (-hole_offset, hole_offset):
        for dy in (-hole_offset, hole_offset):
            hole = Pos(dx, dy, FLANGE_D / 2) * Cylinder(3.5, FLANGE_D + 2)
            holes.append(hole)

    # 电机主体
    body = Pos(0, 0, FLANGE_D + BODY_D / 2) * Cylinder(BODY_DIA / 2, BODY_D)
    body.color = Color(0.15, 0.15, 0.17, 1.0)  # 黑色电机壳

    # 输出轴
    shaft = Pos(0, 0, -SHAFT_LEN / 2 + 1) * Cylinder(SHAFT_DIA / 2, SHAFT_LEN)
    shaft.color = Color(0.85, 0.85, 0.87, 1.0)  # 钢色

    # 轴键槽
    key = Pos(SHAFT_DIA / 2 - SHAFT_KEY_W / 2 + 1, 0, -SHAFT_KEY_H / 2) * Box(
        SHAFT_KEY_W, SHAFT_DIA + 2, SHAFT_KEY_H
    )
    key.color = Color(0.85, 0.85, 0.87, 1.0)

    # 编码器/接线盒
    conn = Pos(0, BODY_DIA / 2 + CONN_BOX_H / 2 - 2, FLANGE_D + BODY_D - CONN_BOX_D / 2) * Box(
        CONN_BOX_W, CONN_BOX_H, CONN_BOX_D
    )
    conn.color = Color(0.12, 0.12, 0.14, 1.0)

    servo = flange + body + shaft + key + conn
    for hole in holes:
        servo -= hole

    servo.label = "Servo_Motor"
    return servo


def gen_step() -> dict[str, object]:
    return {
        "shape": build_servo(),
        "step_output": "servo_motor.step",
    }
