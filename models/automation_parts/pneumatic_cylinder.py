#!/usr/bin/env python3
"""气动气缸 — 标准紧凑型气缸，安装耳座底面为 Z=0 基准"""
from __future__ import annotations

from build123d import Box, Cylinder, Pos, Rot, Shape, Color, Compound

DISPLAY_NAME = "Pneumatic Cylinder 20×50"

BARREL_DIA = 20.0
BARREL_LEN = 50.0
ROD_DIA = 8.0
ROD_LEN = 55.0
FRONT_CAP_D = 12.0
REAR_CAP_D = 10.0
MOUNT_W = 24.0
MOUNT_H = 6.0
MOUNT_D = 20.0
MOUNT_HOLE_DIA = 4.0
PORT_DIA = 3.0
PORT_LEN = 6.0


def build_cylinder() -> Shape:
    # 安装耳座底面作为 Z=0 基准
    # 原 mount 中心在 Y=-30, Z=21.25；下移 21.25 使底面在 Z=0
    Z_OFFSET = 21.25

    # 缸筒
    barrel = Pos(0, 0, BARREL_LEN / 2 - Z_OFFSET) * Cylinder(BARREL_DIA / 2, BARREL_LEN)
    barrel.color = Color(0.85, 0.85, 0.87, 1.0)

    # 前盖
    front_cap = Pos(0, 0, BARREL_LEN + FRONT_CAP_D / 2 - Z_OFFSET) * Cylinder(BARREL_DIA / 2 + 1, FRONT_CAP_D)
    front_cap.color = Color(0.75, 0.75, 0.78, 1.0)

    # 后盖
    rear_cap = Pos(0, 0, -REAR_CAP_D / 2 - Z_OFFSET) * Cylinder(BARREL_DIA / 2 + 1, REAR_CAP_D)
    rear_cap.color = Color(0.75, 0.75, 0.78, 1.0)

    # 活塞杆
    rod = Pos(0, 0, BARREL_LEN + FRONT_CAP_D + ROD_LEN / 2 - Z_OFFSET) * Cylinder(ROD_DIA / 2, ROD_LEN)
    rod.color = Color(0.9, 0.9, 0.92, 1.0)

    # 前端安装耳座（底面在 Z=0）
    mount = Pos(0, 0, MOUNT_H / 2) * Box(MOUNT_W, MOUNT_H, MOUNT_D)
    mount.color = Color(0.6, 0.6, 0.62, 1.0)

    # 耳座安装孔
    hole_left = Pos(-MOUNT_W / 2 + 4, 0, MOUNT_H / 2) * Cylinder(MOUNT_HOLE_DIA / 2, MOUNT_H + 2)
    hole_right = Pos(MOUNT_W / 2 - 4, 0, MOUNT_H / 2) * Cylinder(MOUNT_HOLE_DIA / 2, MOUNT_H + 2)

    # 气口
    port_front = Pos(0, BARREL_DIA / 2 + PORT_LEN / 2, BARREL_LEN - 8 - Z_OFFSET) * Rot(90, 0, 0) * Cylinder(
        PORT_DIA / 2, PORT_LEN
    )
    port_front.color = Color(0.5, 0.5, 0.5, 1.0)
    port_rear = Pos(0, BARREL_DIA / 2 + PORT_LEN / 2, 8 - Z_OFFSET) * Rot(90, 0, 0) * Cylinder(
        PORT_DIA / 2, PORT_LEN
    )
    port_rear.color = Color(0.5, 0.5, 0.5, 1.0)

    cyl = barrel + front_cap + rear_cap + rod + mount + port_front + port_rear
    cyl -= hole_left
    cyl -= hole_right

    cyl = Compound(obj=cyl) if not isinstance(cyl, Shape) else cyl
    cyl.label = "Pneumatic_Cylinder"
    return cyl


def gen_step() -> dict[str, object]:
    return {
        "shape": build_cylinder(),
        "step_output": "pneumatic_cylinder.step",
    }
