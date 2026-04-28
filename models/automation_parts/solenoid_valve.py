#!/usr/bin/env python3
"""电磁阀 — 两位五通换向阀"""
from __future__ import annotations

from build123d import Box, Cylinder, Pos, Rot, Shape, Color

DISPLAY_NAME = "Solenoid Valve 5/2"

BODY_W = 40.0
BODY_H = 25.0
BODY_D = 30.0
COIL_DIA = 22.0
COIL_LEN = 35.0
PORT_DIA = 4.0
PORT_LEN = 8.0
LED_DIA = 2.5
MANUAL_OVERRIDE_DIA = 4.0


def build_solenoid_valve() -> Shape:
    # 阀体
    body = Pos(0, 0, BODY_D / 2) * Box(BODY_W, BODY_H, BODY_D)
    body.color = Color(0.85, 0.85, 0.87, 1.0)  # 铝色阀体

    # 电磁线圈
    coil = Pos(0, BODY_H / 2 + COIL_LEN / 2, BODY_D / 2) * Rot(90, 0, 0) * Cylinder(COIL_DIA / 2, COIL_LEN)
    coil.color = Color(0.15, 0.15, 0.55, 1.0)  # 深蓝色线圈护罩

    # 气口 A (前)
    port_a = Pos(0, BODY_H / 2 + PORT_LEN / 2, BODY_D / 2) * Rot(90, 0, 0) * Cylinder(PORT_DIA / 2, PORT_LEN)
    port_a.color = Color(0.6, 0.6, 0.6, 1.0)

    # 气口 B (后)
    port_b = Pos(0, -BODY_H / 2 - PORT_LEN / 2, BODY_D / 2) * Rot(90, 0, 0) * Cylinder(PORT_DIA / 2, PORT_LEN)
    port_b.color = Color(0.6, 0.6, 0.6, 1.0)

    # 进气口 P (下)
    port_p = Pos(0, 0, -PORT_LEN / 2) * Cylinder(PORT_DIA / 2, PORT_LEN)
    port_p.color = Color(0.6, 0.6, 0.6, 1.0)

    # 排气口 R/S (侧面)
    port_r = Pos(-BODY_W / 2 - PORT_LEN / 2, 0, BODY_D / 2) * Rot(0, 90, 0) * Cylinder(PORT_DIA / 2, PORT_LEN)
    port_r.color = Color(0.6, 0.6, 0.6, 1.0)
    port_s = Pos(BODY_W / 2 + PORT_LEN / 2, 0, BODY_D / 2) * Rot(0, 90, 0) * Cylinder(PORT_DIA / 2, PORT_LEN)
    port_s.color = Color(0.6, 0.6, 0.6, 1.0)

    # 状态 LED
    led = Pos(-BODY_W / 2 + 5, BODY_H / 2 + 1, BODY_D - 3) * Cylinder(LED_DIA / 2, 3)
    led.color = Color(0.0, 0.7, 0.0, 1.0)

    # 手动 override 按钮
    override = Pos(BODY_W / 2 - 5, BODY_H / 2 + 1, BODY_D - 3) * Cylinder(MANUAL_OVERRIDE_DIA / 2, 3)
    override.color = Color(0.2, 0.2, 0.2, 1.0)

    valve = body + coil + port_a + port_b + port_p + port_r + port_s + led + override
    valve.label = "Solenoid_Valve"
    return valve


def gen_step() -> dict[str, object]:
    return {
        "shape": build_solenoid_valve(),
        "step_output": "solenoid_valve.step",
    }
