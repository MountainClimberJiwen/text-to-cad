#!/usr/bin/env python3
"""传感器电缆 — Φ4 黑色护套，两端带 M12 接头"""
from __future__ import annotations

from build123d import Cylinder, Pos, Shape, Color, Compound

DISPLAY_NAME = "Sensor Cable Φ4×150"

CABLE_DIA = 4.0
CABLE_LEN = 150.0
CONNECTOR_DIA = 12.0
CONNECTOR_LEN = 20.0


def build_cable() -> Shape:
    # 线缆主体
    cable = Pos(0, 0, CABLE_LEN / 2) * Cylinder(CABLE_DIA / 2, CABLE_LEN)
    cable.color = Color(0.12, 0.12, 0.12, 1.0)

    # M12 接头（金属螺纹外壳）
    conn1 = Pos(0, 0, CONNECTOR_LEN / 2) * Cylinder(CONNECTOR_DIA / 2, CONNECTOR_LEN)
    conn1.color = Color(0.55, 0.55, 0.58, 1.0)
    conn2 = Pos(0, 0, CABLE_LEN - CONNECTOR_LEN / 2) * Cylinder(CONNECTOR_DIA / 2, CONNECTOR_LEN)
    conn2.color = Color(0.55, 0.55, 0.58, 1.0)

    # 接头尾部护套
    boot1 = Pos(0, 0, CONNECTOR_LEN + 5) * Cylinder(CABLE_DIA + 2, 10)
    boot1.color = Color(0.20, 0.20, 0.20, 1.0)
    boot2 = Pos(0, 0, CABLE_LEN - CONNECTOR_LEN - 5) * Cylinder(CABLE_DIA + 2, 10)
    boot2.color = Color(0.20, 0.20, 0.20, 1.0)

    result = cable + conn1 + conn2 + boot1 + boot2
    result = Compound(obj=result) if not isinstance(result, Shape) else result
    result.label = "Sensor_Cable"
    return result


def gen_step() -> dict[str, object]:
    return {
        "shape": build_cable(),
        "step_output": "sensor_cable.step",
    }
