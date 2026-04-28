#!/usr/bin/env python3
"""自动化控制单元装配 — 标准工业控制柜内部布置"""
from __future__ import annotations

import math
from pathlib import Path


def _t(tx: float = 0.0, ty: float = 0.0, tz: float = 0.0,
       rx: float = 0.0, ry: float = 0.0, rz: float = 0.0) -> list[float]:
    """构造 4x4 row-major 变换矩阵。角度为度数。"""
    cx, cy, cz = math.cos(math.radians(rx)), math.cos(math.radians(ry)), math.cos(math.radians(rz))
    sx, sy, sz = math.sin(math.radians(rx)), math.sin(math.radians(ry)), math.sin(math.radians(rz))

    # 组合旋转 R = Rz * Ry * Rx (Tait-Bryan ZYX)
    # Row-major 矩阵
    return [
        cy * cz,  sx * sy * cz - cx * sz,  cx * sy * cz + sx * sz,  tx,
        cy * sz,  sx * sy * sz + cx * cz,  cx * sy * sz - sx * cz,  ty,
        -sy,      sx * cy,                 cx * cy,                 tz,
        0.0,      0.0,                     0.0,                     1.0,
    ]


def gen_step() -> dict[str, object]:
    parts_dir = Path(__file__).parent.parent / "automation_parts"

    return {
        "step_output": "automation_control_unit.step",
        "instances": [
            # 0. 安装背板 — 底座
            {
                "name": "MountingPlate",
                "path": "../automation_parts/mounting_plate.step",
                "transform": _t(0, 0, 0),
            },
            # 1. DIN 导轨 — 顶帽型，沿背板上沿安装
            {
                "name": "DINRail",
                "path": "../automation_parts/din_rail.step",
                "transform": _t(0, 0, 2.0),
            },
            # 2. PLC 控制器 — 挂在 DIN 导轨中央偏左
            {
                "name": "PLC",
                "path": "../automation_parts/plc_module.step",
                "transform": _t(-60, 0, 9.5),
            },
            # 3. 接线端子排 — DIN 导轨右侧
            {
                "name": "TerminalBlock",
                "path": "../automation_parts/terminal_block.step",
                "transform": _t(80, 0, 9.5),
            },
            # 4. 伺服电机 — 背板左下，轴朝前（-Y 方向）
            {
                "name": "ServoMotor",
                "path": "../automation_parts/servo_motor.step",
                "transform": _t(-120, -80, 2.0, rx=90),
            },
            # 5. 气泵 — 背板右上
            {
                "name": "AirPump",
                "path": "../automation_parts/air_pump.step",
                "transform": _t(140, 60, 2.0),
            },
            # 6. 电磁阀 — DIN 导轨左侧
            {
                "name": "SolenoidValve",
                "path": "../automation_parts/solenoid_valve.step",
                "transform": _t(-150, 0, 9.5, rz=90),
            },
            # 7. 气动气缸 — 背板右下，水平朝前
            {
                "name": "PneumaticCylinder",
                "path": "../automation_parts/pneumatic_cylinder.step",
                "transform": _t(100, -90, 12.0, rx=90),
            },
            # 8. 光电传感器 — 气缸上方，检测位
            {
                "name": "PhotoSensor",
                "path": "../automation_parts/photo_sensor.step",
                "transform": _t(60, -70, 20.0, rx=-90),
            },
        ],
    }
