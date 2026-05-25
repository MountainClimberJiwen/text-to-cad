#!/usr/bin/env python3
"""振动盘上料搬运装配单元 — 引用详细零件 STEP，所有设备通过安装载体与底座刚性连接"""
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
        "step_output": "vibratory_feeder_assembly.step",
        "instances": [
            # 1. 底座平台（所有设备安装载体）
            {
                "name": "BasePlate",
                "path": "../automation_parts/feeder_base.step",
                "transform": _t(0, 0, 0),
            },

            # 2. 振动盘 — 底面贴合底座顶面（Z=30），位于右侧
            # 旋转 180° 使出料轨道朝向左侧（工作平台方向），料仓在右侧
            {
                "name": "VibratingBowl",
                "path": "../automation_parts/vibrating_bowl.step",
                "transform": _t(380, 50, 30, rz=180),
            },

            # 3. 搬运门架 — 底面贴合底座顶面（Z=30），位于中间偏后
            {
                "name": "TransferGantry",
                "path": "../automation_parts/transfer_column.step",
                "transform": _t(0, -120, 30),
            },

            # 4. 水平搬运气缸 — 安装在门架顶部横梁上，沿 X 方向
            # 活塞杆朝右（X正方向，朝向振动盘）
            {
                "name": "HorizontalTransferCylinder",
                "path": "../automation_parts/large_cylinder.step",
                "transform": _t(0, -120, 610, ry=-90),
            },

            # 5. 竖直搬运气缸 — 安装在门架绿色竖直滑板上，朝下
            # 绿色滑板位于两立柱之间正中，门架坐标 (0, 0, 425)，全局坐标 (0, -120, 455)
            # 气缸安装在绿色板正面滑块上，Y 向外偏移使其在两柱间清晰可见
            {
                "name": "VerticalTransferCylinder",
                "path": "../automation_parts/large_cylinder.step",
                "transform": _t(0, -80, 520, rx=180),
            },

            # 6. 产品夹爪 — 安装在竖直气缸活塞杆末端
            {
                "name": "ProductGripper",
                "path": "../automation_parts/gripper.step",
                "transform": _t(0, -80, 280),
            },

            # 7. 工作平台/料道 — 底面贴合底座顶面（Z=30）
            # 位于振动盘出料口前方（Y=300），与出料轨道对接
            {
                "name": "WorkPlatform",
                "path": "../automation_parts/work_platform.step",
                "transform": _t(240, 300, 30),
            },

            # 8. 推料机构（直线滑台）— 底面贴合底座顶面（Z=30），位于左侧
            # 沿 X 方向，推料块朝向工作平台取料位
            {
                "name": "PushSlide",
                "path": "../automation_parts/push_slide.step",
                "transform": _t(-60, 50, 30),
            },

            # 9. 水平推料气缸 — 位于推料机构左侧，沿 X 方向推动滑块
            {
                "name": "HorizontalPushCylinder",
                "path": "../automation_parts/pneumatic_cylinder.step",
                "transform": _t(-200, 50, 42),
            },

            # 9a. 推料气缸安装支架
            {
                "name": "PushCylinderBracket",
                "path": "../automation_parts/cylinder_bracket.step",
                "transform": _t(-200, 50, 30, rz=-90),
            },

            # 10. 导向气缸 — 位于工作平台取料位上方，竖直安装用于挡料/定位
            {
                "name": "GuideCylinder",
                "path": "../automation_parts/pneumatic_cylinder.step",
                "transform": _t(200, 50, 55, rx=-90),
            },

            # 10a. 导向气缸安装支架
            {
                "name": "GuideCylinderBracket",
                "path": "../automation_parts/cylinder_bracket.step",
                "transform": _t(200, 50, 30),
            },

            # 11. 直线导向滑台（辅助导向）— 位于推料机构下方，沿 X 方向
            {
                "name": "GuideSlide",
                "path": "../automation_parts/linear_guide.step",
                "transform": _t(-80, 50, 30),
            },

            # 12. 气源：小型气泵（左后方）
            # 底面贴合底座顶面（Z=30），bottom面在局部Z=-58.75，所以全局Z=88.75
            {
                "name": "AirPump",
                "path": "../automation_parts/air_pump.step",
                "transform": _t(-450, -250, 88.75),
            },

            # 13. 接近传感器1 — 检测水平滑台原位（门架横梁左侧）
            {
                "name": "SensorHome",
                "path": "../automation_parts/proximity_sensor.step",
                "transform": _t(-80, -140, 570, rx=180),
            },

            # 14. 接近传感器2 — 检测取料位有料（工作平台上方）
            {
                "name": "SensorPick",
                "path": "../automation_parts/proximity_sensor.step",
                "transform": _t(220, 30, 80, rx=180),
            },
        ],
    }
