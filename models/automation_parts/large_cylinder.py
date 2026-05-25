#!/usr/bin/env python3
"""大型气动气缸 — 缸径40×行程100，安装耳座底面为 Z=0 基准"""
from __future__ import annotations

from build123d import Box, Cylinder, Pos, Rot, Shape, Color, Compound

DISPLAY_NAME = "Pneumatic Cylinder 40×100"

BARREL_DIA = 40.0
BARREL_LEN = 100.0
ROD_DIA = 16.0
ROD_LEN = 110.0
FRONT_CAP_D = 20.0
REAR_CAP_D = 15.0
MOUNT_W = 48.0
MOUNT_H = 10.0
MOUNT_D = 35.0
MOUNT_HOLE_DIA = 5.5
PORT_DIA = 5.0
PORT_LEN = 10.0


def build_cylinder() -> Shape:
    # 安装耳座底面作为 Z=0 基准
    Z_OFFSET = 35.0  # 使耳座底面在 Z=0

    # 缸筒
    barrel = Pos(0, 0, BARREL_LEN / 2 - Z_OFFSET) * Cylinder(BARREL_DIA / 2, BARREL_LEN)
    barrel.color = Color(0.85, 0.85, 0.87, 1.0)

    # 前盖
    front_cap = Pos(0, 0, BARREL_LEN + FRONT_CAP_D / 2 - Z_OFFSET) * Cylinder(BARREL_DIA / 2 + 2, FRONT_CAP_D)
    front_cap.color = Color(0.75, 0.75, 0.78, 1.0)

    # 后盖
    rear_cap = Pos(0, 0, -REAR_CAP_D / 2 - Z_OFFSET) * Cylinder(BARREL_DIA / 2 + 2, REAR_CAP_D)
    rear_cap.color = Color(0.75, 0.75, 0.78, 1.0)

    # 活塞杆
    rod = Pos(0, 0, BARREL_LEN + FRONT_CAP_D + ROD_LEN / 2 - Z_OFFSET) * Cylinder(ROD_DIA / 2, ROD_LEN)
    rod.color = Color(0.9, 0.9, 0.92, 1.0)

    # 前端安装耳座（底面在 Z=0）
    mount = Pos(0, 0, MOUNT_H / 2) * Box(MOUNT_W, MOUNT_H, MOUNT_D)
    mount.color = Color(0.6, 0.6, 0.62, 1.0)

    # 耳座安装孔
    hole_left = Pos(-MOUNT_W / 2 + 8, 0, MOUNT_H / 2) * Cylinder(MOUNT_HOLE_DIA / 2, MOUNT_H + 2)
    hole_right = Pos(MOUNT_W / 2 - 8, 0, MOUNT_H / 2) * Cylinder(MOUNT_HOLE_DIA / 2, MOUNT_H + 2)

    # 气口
    port_front = Pos(0, BARREL_DIA / 2 + PORT_LEN / 2, BARREL_LEN - 15 - Z_OFFSET) * Rot(90, 0, 0) * Cylinder(
        PORT_DIA / 2, PORT_LEN
    )
    port_front.color = Color(0.5, 0.5, 0.5, 1.0)
    port_rear = Pos(0, BARREL_DIA / 2 + PORT_LEN / 2, 15 - Z_OFFSET) * Rot(90, 0, 0) * Cylinder(
        PORT_DIA / 2, PORT_LEN
    )
    port_rear.color = Color(0.5, 0.5, 0.5, 1.0)

    cyl = barrel + front_cap + rear_cap + rod + mount + port_front + port_rear
    cyl -= hole_left
    cyl -= hole_right

    cyl = Compound(obj=cyl) if not isinstance(cyl, Shape) else cyl
    cyl.label = "Large_Pneumatic_Cylinder"
    return cyl


def gen_step() -> dict[str, object]:
    return {
        "shape": build_cylinder(),
        "step_output": "large_cylinder.step",
    }
