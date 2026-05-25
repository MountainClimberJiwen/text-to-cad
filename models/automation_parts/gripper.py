#!/usr/bin/env python3
"""气动夹爪 — 平行开闭型，安装顶面为 Z=0 基准（夹爪朝下）"""
from __future__ import annotations

from build123d import Box, Cylinder, Pos, Rot, Shape, Color, Compound

DISPLAY_NAME = "Pneumatic Gripper 30×50"

BODY_W = 50.0
BODY_D = 30.0
BODY_H = 45.0
FINGER_W = 10.0
FINGER_L = 40.0
FINGER_H = 25.0
JAW_OPEN = 25.0
MOUNT_HOLE_DIA = 5.0
MOUNT_HOLE_SPAN = 35.0


def build_gripper() -> Shape:
    # 本体（安装顶面在 Z=0，夹爪朝下）
    body = Pos(0, 0, -BODY_H / 2) * Box(BODY_W, BODY_D, BODY_H)
    body.color = Color(0.20, 0.55, 0.25, 1.0)  # 绿色主体

    # 安装孔（顶面 2×φ5）
    mount_hole1 = Pos(-MOUNT_HOLE_SPAN / 2, 0, 0) * Cylinder(MOUNT_HOLE_DIA / 2, BODY_H + 2)
    mount_hole2 = Pos(MOUNT_HOLE_SPAN / 2, 0, 0) * Cylinder(MOUNT_HOLE_DIA / 2, BODY_H + 2)

    # 夹爪滑轨槽（本体底面）
    rail = Pos(0, 0, -BODY_H - 2) * Box(BODY_W - 6, BODY_D - 6, 4)
    rail.color = Color(0.15, 0.45, 0.20, 1.0)

    # 左夹指
    left_finger = Pos(-JAW_OPEN / 2 - FINGER_W / 2, 0, -BODY_H - FINGER_H / 2 - 2) * Box(
        FINGER_W, FINGER_L, FINGER_H
    )
    left_finger.color = Color(0.75, 0.75, 0.77, 1.0)
    # 左夹指垫
    left_pad = Pos(-JAW_OPEN / 2 - FINGER_W / 2, 0, -BODY_H - FINGER_H - 4) * Box(
        FINGER_W + 2, FINGER_L - 6, 4
    )
    left_pad.color = Color(0.50, 0.50, 0.52, 1.0)

    # 右夹指
    right_finger = Pos(JAW_OPEN / 2 + FINGER_W / 2, 0, -BODY_H - FINGER_H / 2 - 2) * Box(
        FINGER_W, FINGER_L, FINGER_H
    )
    right_finger.color = Color(0.75, 0.75, 0.77, 1.0)
    # 右夹指垫
    right_pad = Pos(JAW_OPEN / 2 + FINGER_W / 2, 0, -BODY_H - FINGER_H - 4) * Box(
        FINGER_W + 2, FINGER_L - 6, 4
    )
    right_pad.color = Color(0.50, 0.50, 0.52, 1.0)

    # 气管接口（侧面）
    port1 = Pos(BODY_W / 2 + 4, -BODY_D / 4, -BODY_H / 2) * Rot(0, 90, 0) * Cylinder(3, 8)
    port1.color = Color(0.50, 0.50, 0.50, 1.0)
    port2 = Pos(BODY_W / 2 + 4, BODY_D / 4, -BODY_H / 2) * Rot(0, 90, 0) * Cylinder(3, 8)
    port2.color = Color(0.50, 0.50, 0.50, 1.0)

    gripper = body + rail + left_finger + left_pad + right_finger + right_pad + port1 + port2
    gripper -= mount_hole1
    gripper -= mount_hole2

    gripper = Compound(obj=gripper) if not isinstance(gripper, Shape) else gripper
    gripper.label = "Pneumatic_Gripper"
    return gripper


def gen_step() -> dict[str, object]:
    return {
        "shape": build_gripper(),
        "step_output": "gripper.step",
    }
