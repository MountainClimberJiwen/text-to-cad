#!/usr/bin/env python3
"""自动上料装配单元 — 引用详细零件 STEP，所有设备通过安装载体与机架刚性连接"""
from __future__ import annotations

import math


def _t(tx: float = 0.0, ty: float = 0.0, tz: float = 0.0,
       rx: float = 0.0, ry: float = 0.0, rz: float = 0.0) -> list[float]:
    """构造 4x4 row-major 变换矩阵。角度为度数。"""
    cx, cy, cz = math.cos(math.radians(rx)), math.cos(math.radians(ry)), math.cos(math.radians(rz))
    sx, sy, sz = math.sin(math.radians(rx)), math.sin(math.radians(ry)), math.sin(math.radians(rz))
    return [
        cy * cz,  sx * sy * cz - cx * sz,  cx * sy * cz + sx * sz,  tx,
        cy * sz,  sx * sy * sz + cx * cz,  cx * sy * sz - sx * cz,  ty,
        -sy,      sx * cy,                 cx * cy,                 tz,
        0.0,      0.0,                     0.0,                     1.0,
    ]


def gen_step() -> dict[str, object]:
    return {
        "step_output": "auto_feed_assembly.step",
        "instances": [
            # 1. 机架（含所有安装载体：PLC安装板、气泵平台、电机支架、气缸安装板、阀安装板、线槽支架）
            {
                "name": "Frame",
                "path": "../automation_parts/frame_base.step",
                "transform": _t(0, 0, 0),
            },
            # 2. PLC — 底面贴合 PLC 安装板顶面（Z=830，安装板厚 10mm 在 Z=820~830）
            {
                "name": "PLC",
                "path": "../automation_parts/plc_module.step",
                "transform": _t(500, 0, 830),
            },
            # 3. 伺服电机 — 法兰面贴合电机安装支架（支架贴合面在 X=-310），轴朝+X穿过滚筒
            {
                "name": "ServoMotor",
                "path": "../automation_parts/servo_motor.step",
                "transform": _t(-310, 0, 600, ry=-90),
            },
            # 4. 滚筒 — 轴头穿入左右支架轴承孔（轴承孔中心在 Z=600）
            {
                "name": "Roller",
                "path": "../automation_parts/roller.step",
                "transform": _t(0, 0, 600),
            },
            # 5. 滚筒支架 — 底面贴合机架横梁/立柱，轴承孔中心 Z=600
            {
                "name": "RollerBrackets",
                "path": "../automation_parts/roller_bracket.step",
                "transform": _t(0, 0, 600),
            },
            # 6. 气泵 — 安装支架底面贴合气泵平台顶面（平台顶面 Z=770）
            {
                "name": "AirPump",
                "path": "../automation_parts/air_pump.step",
                "transform": _t(-400, 0, 770),
            },
            # 7. 气缸 — 安装耳座底面贴合气缸安装板顶面（安装板顶面 Z=815）
            {
                "name": "PneumaticCylinder",
                "path": "../automation_parts/pneumatic_cylinder.step",
                "transform": _t(300, -365, 815, rx=-90),
            },
            # 8. 电磁阀 — 底面贴合阀安装板顶面（安装板顶面 Z=815）
            {
                "name": "SolenoidValve",
                "path": "../automation_parts/solenoid_valve.step",
                "transform": _t(-300, 200, 815),
            },
            # 9. 线槽 — 底面贴合线槽支架顶面（支架顶面 Z=775）
            {
                "name": "CableTray",
                "path": "../automation_parts/cable_tray_channel.step",
                "transform": _t(0, 390, 775),
            },
        ],
    }
