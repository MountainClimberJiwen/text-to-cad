#!/usr/bin/env python3
"""自动上料搬运站装配体 — 精简连接件，保留关键装配关系"""
from __future__ import annotations

import math


def _t(tx: float = 0.0, ty: float = 0.0, tz: float = 0.0,
       rx: float = 0.0, ry: float = 0.0, rz: float = 0.0) -> list[float]:
    cx, cy, cz = math.cos(math.radians(rx)), math.cos(math.radians(ry)), math.cos(math.radians(rz))
    sx, sy, sz = math.sin(math.radians(rx)), math.sin(math.radians(ry)), math.sin(math.radians(rz))
    return [
        cy * cz,  sx * sy * cz - cx * sz,  cx * sy * cz + sx * sz,  tx,
        cy * sz,  sx * sy * sz + cx * cz,  cx * sy * sz - sx * cz,  ty,
        -sy,      sx * cy,                 cx * cy,                 tz,
        0.0,      0.0,                     0.0,                     1.0,
    ]


def gen_step() -> dict[str, object]:
    instances = []

    # ═══════════════════════════════════════════════════
    #  A. 主体结构零件
    # ═══════════════════════════════════════════════════

    # 1. 底座板
    instances.append({"name": "BasePlate", "path": "../automation_parts/small_base_plate.step", "transform": _t(0, 0, 0)})

    # 2. 中心搬运门架
    instances.append({"name": "TransferColumn", "path": "../automation_parts/transfer_column.step", "transform": _t(0, -50, 15)})

    # 3. 夹爪
    instances.append({"name": "Gripper", "path": "../automation_parts/gripper.step", "transform": _t(0, -38, 415)})

    # 4-5. 顶部水平搬运气缸 ×2
    instances.append({"name": "HorizTransferCyl_L", "path": "../automation_parts/pneumatic_cylinder.step", "transform": _t(-30, -50, 595)})
    instances.append({"name": "HorizTransferCyl_R", "path": "../automation_parts/pneumatic_cylinder.step", "transform": _t(30, -50, 595)})

    # 6. 竖直搬运气缸
    instances.append({"name": "VertTransferCyl", "path": "../automation_parts/large_cylinder.step", "transform": _t(0, -60, 440)})

    # 7. 左侧推料滑台
    instances.append({"name": "PushSlide", "path": "../automation_parts/push_slide.step", "transform": _t(-280, 80, 15)})

    # 8. 左侧导向气缸
    instances.append({"name": "GuideCyl", "path": "../automation_parts/pneumatic_cylinder.step", "transform": _t(-350, 80, 15)})

    # 9. 直线导向滑台
    instances.append({"name": "LinearGuide", "path": "../automation_parts/linear_guide.step", "transform": _t(-200, 80, 15)})

    # 10. 振动盘送料器
    instances.append({"name": "VibBowl", "path": "../automation_parts/vibrating_bowl.step", "transform": _t(260, -120, 15)})

    # 11. 气泵
    instances.append({"name": "AirPump", "path": "../automation_parts/air_pump.step", "transform": _t(-300, -180, 15)})

    # 12. 电磁阀
    instances.append({"name": "SolenoidValve", "path": "../automation_parts/solenoid_valve.step", "transform": _t(-200, -180, 15)})

    # 13. DIN 导轨
    instances.append({"name": "DINRail", "path": "../automation_parts/din_rail.step", "transform": _t(-300, 180, 15, rz=90)})

    # 14. PLC
    instances.append({"name": "PLC", "path": "../automation_parts/plc_module.step", "transform": _t(-300, 180, 22)})

    # 15. 接线端子
    instances.append({"name": "TerminalBlock", "path": "../automation_parts/terminal_block.step", "transform": _t(-250, 180, 22)})

    # 16. 电缆槽
    instances.append({"name": "CableTray", "path": "../automation_parts/cable_tray_channel.step", "transform": _t(0, 230, 15)})

    # 17-18. 接近传感器
    instances.append({"name": "ProximitySensor1", "path": "../automation_parts/proximity_sensor.step", "transform": _t(-220, 110, 50)})
    instances.append({"name": "ProximitySensor2", "path": "../automation_parts/proximity_sensor.step", "transform": _t(-180, 110, 50, rz=180)})

    # 19-20. 光电传感器
    instances.append({"name": "PhotoSensor1", "path": "../automation_parts/photo_sensor.step", "transform": _t(-120, 110, 50)})
    instances.append({"name": "PhotoSensor2", "path": "../automation_parts/photo_sensor.step", "transform": _t(180, -120, 200, rx=-90)})

    # ═══════════════════════════════════════════════════
    #  B. 连接件 — 仅保留关键位置的少量螺栓
    # ═══════════════════════════════════════════════════

    # B1. TransferColumn 底板四角 — 4×M8（最关键的承重连接）
    instances.append({"name": "Bolt_M8_1", "path": "../automation_parts/bolt_m8x25.step", "transform": _t(-125, -105, 35)})
    instances.append({"name": "Bolt_M8_2", "path": "../automation_parts/bolt_m8x25.step", "transform": _t(125, -105, 35)})
    instances.append({"name": "Bolt_M8_3", "path": "../automation_parts/bolt_m8x25.step", "transform": _t(-125, 5, 35)})
    instances.append({"name": "Bolt_M8_4", "path": "../automation_parts/bolt_m8x25.step", "transform": _t(125, 5, 35)})

    # B2. Gripper 顶面 — 2×M6（夹爪与滑块的连接）
    instances.append({"name": "Bolt_M6_1", "path": "../automation_parts/bolt_m6x20.step", "transform": _t(-17.5, -38, 415)})
    instances.append({"name": "Bolt_M6_2", "path": "../automation_parts/bolt_m6x20.step", "transform": _t(17.5, -38, 415)})

    # B3. VibBowl 底座 — 2×M8（只放 2 个对角，示意即可）
    instances.append({"name": "Bolt_M8_V1", "path": "../automation_parts/bolt_m8x25.step", "transform": _t(348, -32, 95)})
    instances.append({"name": "Bolt_M8_V2", "path": "../automation_parts/bolt_m8x25.step", "transform": _t(172, -208, 95)})

    # ═══════════════════════════════════════════════════
    #  C. 气管 — 只保留 2 段最关键的气路
    # ═══════════════════════════════════════════════════

    # 气泵 → 电磁阀（最短的一段，水平）
    instances.append({"name": "Tube_Pump_Valve", "path": "../automation_parts/air_tube_6mm.step", "transform": _t(-250, -180, 35, ry=90)})

    return {
        "step_output": "auto_station_assembly.step",
        "instances": instances,
    }
