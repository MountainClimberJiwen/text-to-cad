#!/usr/bin/env python3
"""小型工业气泵 / 真空泵 — 安装底面为 Z=0 基准"""
from __future__ import annotations

from build123d import Box, Cylinder, Pos, Rot, Shape, Color, Compound

DISPLAY_NAME = "Mini Air Pump"

BODY_DIA = 60.0
BODY_LEN = 85.0
MOTOR_DIA = 45.0
MOTOR_LEN = 55.0
OUTLET_DIA = 8.0
OUTLET_LEN = 15.0
MOUNT_W = 70.0
MOUNT_H = 8.0
MOUNT_D = 35.0
MOUNT_HOLE_DIA = 4.5


def build_air_pump() -> Shape:
    # 安装支架底面作为 Z=0 基准
    # 支架中心原在 Y=-30, Z=21.25；下移 3.75 使底面在 Z=0
    Z_OFFSET = 3.75

    # 泵主体
    pump_body = Pos(0, 0, 42.5 - Z_OFFSET) * Cylinder(BODY_DIA / 2, BODY_LEN)
    pump_body.color = Color(0.18, 0.40, 0.60, 1.0)

    # 电机部分
    motor = Pos(0, 0, -27.5 - Z_OFFSET) * Cylinder(MOTOR_DIA / 2, MOTOR_LEN)
    motor.color = Color(0.20, 0.20, 0.22, 1.0)

    # 出气接口
    outlet = Pos(BODY_DIA / 2 + OUTLET_LEN / 2 - 2, 0, 81.25 - Z_OFFSET) * Rot(0, 90, 0) * Cylinder(
        OUTLET_DIA / 2, OUTLET_LEN
    )
    outlet.color = Color(0.75, 0.75, 0.75, 1.0)

    # 安装支架（底面在 Z=0）
    mount = Pos(0, -30, MOUNT_H / 2) * Box(MOUNT_W, MOUNT_H, MOUNT_D)
    mount.color = Color(0.55, 0.55, 0.58, 1.0)

    # 安装孔
    hole_left = Pos(-MOUNT_W / 2 + 8, -30, MOUNT_H / 2) * Cylinder(
        MOUNT_HOLE_DIA / 2, MOUNT_H + 2
    )
    hole_right = Pos(MOUNT_W / 2 - 8, -30, MOUNT_H / 2) * Cylinder(
        MOUNT_HOLE_DIA / 2, MOUNT_H + 2
    )

    pump = pump_body + motor + outlet + mount
    pump -= hole_left
    pump -= hole_right

    pump = Compound(obj=pump) if not isinstance(pump, Shape) else pump
    pump.label = "Air_Pump"
    return pump


def gen_step() -> dict[str, object]:
    return {
        "shape": build_air_pump(),
        "step_output": "air_pump.step",
    }
