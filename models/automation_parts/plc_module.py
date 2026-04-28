#!/usr/bin/env python3
"""PLC 控制器模块 — 参数化工业自动化零件"""
from __future__ import annotations

from build123d import (
    Box, Cylinder, Pos, Rot, Shape, Color,
    Compound,
)

DISPLAY_NAME = "PLC Controller Module"

# 标准 120mm 宽 PLC 外形参数
BODY_W = 120.0   # 宽度 (X)
BODY_H = 90.0    # 高度 (Y)
BODY_D = 75.0    # 深度 (Z)
MOUNT_CLIP_H = 8.0
MOUNT_CLIP_D = 12.0
STATUS_LED_D = 3.0
ETH_PORT_W = 18.0
ETH_PORT_H = 14.0
ETH_PORT_D = 4.0


def build_plc() -> Shape:
    # 主体
    body = Pos(0, 0, BODY_D / 2) * Box(BODY_W, BODY_H, BODY_D)
    body.color = Color(0.22, 0.24, 0.26, 1.0)  # 深灰工业色

    # 顶部 DIN 导轨卡扣
    clip = Pos(0, BODY_H / 2 + MOUNT_CLIP_H / 2, BODY_D - MOUNT_CLIP_D / 2) * Box(
        BODY_W - 10, MOUNT_CLIP_H, MOUNT_CLIP_D
    )
    clip.color = Color(0.15, 0.15, 0.15, 1.0)

    # 前面板 — 状态指示灯（3 个）
    leds = []
    for i, color in enumerate([
        Color(0.0, 0.8, 0.2, 1.0),   # RUN 绿色
        Color(0.9, 0.1, 0.1, 1.0),   # ERR 红色
        Color(0.1, 0.5, 0.9, 1.0),   # COM 蓝色
    ]):
        led = Pos(
            -BODY_W / 2 + 12 + i * 10,
            BODY_H / 2 - 8,
            BODY_D + STATUS_LED_D / 2 - 1,
        ) * Cylinder(STATUS_LED_D / 2, 2)
        led.color = color
        leds.append(led)

    # 前面板 — 以太网接口
    eth = Pos(
        BODY_W / 2 - 20,
        BODY_H / 2 - 15,
        BODY_D + ETH_PORT_D / 2 - 1,
    ) * Box(ETH_PORT_W, ETH_PORT_H, ETH_PORT_D)
    eth.color = Color(0.1, 0.1, 0.1, 1.0)

    # 底部接线端子区域（示意）
    terminals = Pos(0, -BODY_H / 2 + 6, BODY_D / 2) * Box(BODY_W - 8, 12, BODY_D - 4)
    terminals.color = Color(0.18, 0.20, 0.22, 1.0)

    plc = body + clip + eth + terminals
    for led in leds:
        plc += led

    plc = Compound(obj=plc) if not isinstance(plc, Shape) else plc
    plc.label = "PLC_Module"
    return plc


def gen_step() -> dict[str, object]:
    return {
        "shape": build_plc(),
        "step_output": "plc_module.step",
    }
