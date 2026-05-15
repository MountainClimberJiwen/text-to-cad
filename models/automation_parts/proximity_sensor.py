#!/usr/bin/env python3
"""接近传感器 — 小型圆柱形传感器，安装底面为 Z=0 基准"""
from __future__ import annotations

from build123d import Box, Cylinder, Pos, Shape, Color, Compound

DISPLAY_NAME = "Proximity Sensor M12"

BODY_DIA = 12.0
BODY_LEN = 40.0
THREAD_DIA = 12.0
THREAD_LEN = 15.0
NUT_DIA = 16.0
NUT_THICK = 3.0
CABLE_DIA = 4.0
CABLE_LEN = 30.0


def build_sensor() -> Shape:
    # 传感器主体
    body = Pos(0, 0, BODY_LEN / 2) * Cylinder(BODY_DIA / 2, BODY_LEN)
    body.color = Color(0.20, 0.20, 0.22, 1.0)  # 黑色主体

    # 螺纹安装部
    thread = Pos(0, 0, THREAD_LEN / 2) * Cylinder(THREAD_DIA / 2, THREAD_LEN)
    thread.color = Color(0.70, 0.70, 0.72, 1.0)  # 银色螺纹

    # 六角螺母
    nut = Pos(0, 0, THREAD_LEN + NUT_THICK / 2) * Cylinder(NUT_DIA / 2, NUT_THICK)
    nut.color = Color(0.60, 0.60, 0.62, 1.0)  # 灰色螺母

    # 电缆
    cable = Pos(0, 0, BODY_LEN + CABLE_LEN / 2) * Cylinder(CABLE_DIA / 2, CABLE_LEN)
    cable.color = Color(0.15, 0.15, 0.50, 1.0)  # 深蓝色电缆

    sensor = body + thread + nut + cable
    sensor = Compound(obj=sensor) if not isinstance(sensor, Shape) else sensor
    sensor.label = "Proximity_Sensor"
    return sensor


def gen_step() -> dict[str, object]:
    return {
        "shape": build_sensor(),
        "step_output": "proximity_sensor.step",
    }
