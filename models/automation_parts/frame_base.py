#!/usr/bin/env python3
"""机架底座 — 1200×800×800 工业铝型材框架，含安装载体"""
from __future__ import annotations

from build123d import Box, Cylinder, Pos, Shape, Color, Compound

DISPLAY_NAME = "Machine Frame 1200×800×800"


def build_frame() -> Shape:
    # 底框
    base = Pos(0, 0, 20) * Box(1200, 800, 40)
    base.color = Color(0.70, 0.70, 0.73, 1.0)

    # 四根立柱 40×40×800
    posts = []
    for dx in (-580, 580):
        for dy in (-380, 380):
            post = Pos(dx, dy, 400) * Box(40, 40, 800)
            post.color = Color(0.65, 0.65, 0.68, 1.0)
            posts.append(post)

    # 顶框
    top = Pos(0, 0, 800) * Box(1200, 800, 40)
    top.color = Color(0.70, 0.70, 0.73, 1.0)

    # 横梁加固（前后各一根）
    beam_front = Pos(0, -380, 400) * Box(1120, 40, 40)
    beam_front.color = Color(0.65, 0.65, 0.68, 1.0)
    beam_rear = Pos(0, 380, 400) * Box(1120, 40, 40)
    beam_rear.color = Color(0.65, 0.65, 0.68, 1.0)

    # ====== 安装载体 ======

    # 1. PLC 安装板 — 顶框上方，与顶框螺栓固定
    plc_plate = Pos(500, 0, 825) * Box(200, 160, 10)
    plc_plate.color = Color(0.55, 0.55, 0.58, 1.0)
    # PLC 安装板与顶框的螺栓（示意）
    plc_bolts = []
    for dx in (440, 560):
        for dy in (-60, 60):
            bolt = Pos(dx, dy, 820) * Cylinder(3, 10)
            bolt.color = Color(0.3, 0.3, 0.3, 1.0)
            plc_bolts.append(bolt)

    # 2. 气泵安装平台 — 左侧立柱中部，与立柱焊接/螺栓固定
    # 平台底面贴合左侧横梁
    pump_platform = Pos(-400, 0, 760) * Box(320, 220, 20)
    pump_platform.color = Color(0.55, 0.55, 0.58, 1.0)
    # 平台与立柱的加强筋
    pump_gusset1 = Pos(-580, 0, 670) * Box(40, 20, 180)
    pump_gusset1.color = Color(0.60, 0.60, 0.62, 1.0)
    pump_gusset2 = Pos(-220, 0, 670) * Box(40, 20, 180)
    pump_gusset2.color = Color(0.60, 0.60, 0.62, 1.0)

    # 3. 电机安装支架 — 左侧立柱上部，与立柱螺栓固定
    # 垂直安装板，法兰贴合面在 X=-310
    motor_mount_plate = Pos(-310, 0, 600) * Box(10, 140, 120)
    motor_mount_plate.color = Color(0.55, 0.55, 0.58, 1.0)
    # 电机安装孔（4×φ6.5，圆周φ60）
    motor_holes = []
    for angle in [0, 90, 180, 270]:
        import math
        hx = -310
        hy = 30 * math.cos(math.radians(angle))
        hz = 600 + 30 * math.sin(math.radians(angle))
        hole = Pos(hx, hy, hz) * Cylinder(3.5, 12)
        motor_holes.append(hole)
    # 电机轴通孔
    motor_shaft_hole = Pos(-310, 0, 600) * Cylinder(10, 12)

    # 4. 气缸安装板 — 前端立柱，与立柱螺栓固定
    cyl_plate = Pos(300, -360, 810) * Box(60, 10, 50)
    cyl_plate.color = Color(0.55, 0.55, 0.58, 1.0)
    # 气缸安装孔（2×φ4.5）
    cyl_hole1 = Pos(300, -365, 825) * Cylinder(2.5, 12)
    cyl_hole2 = Pos(300, -365, 795) * Cylinder(2.5, 12)

    # 5. 电磁阀安装板 — 顶框上方小支架
    valve_plate = Pos(-300, 200, 810) * Box(50, 30, 10)
    valve_plate.color = Color(0.55, 0.55, 0.58, 1.0)

    # 6. 线槽支架 — 后横梁上方
    tray_bracket = Pos(0, 390, 770) * Box(1000, 20, 10)
    tray_bracket.color = Color(0.55, 0.55, 0.58, 1.0)

    frame = base + top + beam_front + beam_rear
    for p in posts:
        frame += p
    frame += plc_plate + pump_platform + pump_gusset1 + pump_gusset2
    frame += motor_mount_plate + cyl_plate + valve_plate + tray_bracket
    for bolt in plc_bolts:
        frame += bolt
    for hole in motor_holes:
        frame -= hole
    frame -= motor_shaft_hole
    frame -= cyl_hole1
    frame -= cyl_hole2

    frame = Compound(obj=frame) if not isinstance(frame, Shape) else frame
    frame.label = "Frame"
    return frame


def gen_step() -> dict[str, object]:
    return {
        "shape": build_frame(),
        "step_output": "frame_base.step",
    }
