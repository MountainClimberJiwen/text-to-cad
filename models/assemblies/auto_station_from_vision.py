#!/usr/bin/env python3
"""Auto-generated assembly from AssemblyIntent."""
from __future__ import annotations
# Generated from AssemblyIntent: 16 parts, 15 relations
# Auto-generated fasteners: {'bolt': 28, 'tube': 1}


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
    return {
        "step_output": "auto_station_from_vision.step",
        "instances": [
            {
                "name": "horizontal_transfer_cylinder",
                "path": "../automation_parts/pneumatic_cylinder.step",
                "transform": [1.0, 0.0, 0.0, 360.0, 0.0, 1.0, 0.0, 225.0, -0.0, 0.0, 1.0, 615.0, 0.0, 0.0, 0.0, 1.0],
            },
            {
                "name": "vertical_transfer_cylinder",
                "path": "../automation_parts/pneumatic_cylinder.step",
                "transform": [1.0, 0.0, 0.0, 360.0, 0.0, 1.0, 0.0, 225.0, -0.0, 0.0, 1.0, 735.0, 0.0, 0.0, 0.0, 1.0],
            },
            {
                "name": "product_gripper",
                "path": "../automation_parts/gripper.step",
                "transform": [1.0, 0.0, 0.0, 360.0, 0.0, 1.0, 0.0, 225.0, -0.0, 0.0, 1.0, 855.0, 0.0, 0.0, 0.0, 1.0],
            },
            {
                "name": "horizontal_positioning_cylinder",
                "path": "../automation_parts/pneumatic_cylinder.step",
                "transform": [1.0, 0.0, 0.0, 120.0, 0.0, 1.0, 0.0, 400.0, -0.0, 0.0, 1.0, 195.0, 0.0, 0.0, 0.0, 1.0],
            },
            {
                "name": "guide_cylinder",
                "path": "../automation_parts/pneumatic_cylinder.step",
                "transform": [1.0, 0.0, 0.0, 120.0, 0.0, 1.0, 0.0, 275.0, -0.0, 0.0, 1.0, 195.0, 0.0, 0.0, 0.0, 1.0],
            },
            {
                "name": "guide_mechanism",
                "path": "../automation_parts/linear_guide.step",
                "transform": [1.0, 0.0, 0.0, 64.0, 0.0, 1.0, 0.0, 275.0, -0.0, 0.0, 1.0, 15.0, 0.0, 0.0, 0.0, 1.0],
            },
            {
                "name": "vibration_bowl",
                "path": "../automation_parts/vibrating_bowl.step",
                "transform": [1.0, 0.0, 0.0, 624.0, 0.0, 1.0, 0.0, 110.0, -0.0, 0.0, 1.0, 15.0, 0.0, 0.0, 0.0, 1.0],
            },
            {
                "name": "part_storage_hopper",
                "path": "../automation_parts/vibrating_bowl.step",
                "transform": [1.0, 0.0, 0.0, 624.0, 0.0, 1.0, 0.0, 360.0, -0.0, 0.0, 1.0, 65.0, 0.0, 0.0, 0.0, 1.0],
            },
            {
                "name": "linear_feeding_track",
                "path": "../automation_parts/work_platform.step",
                "transform": [1.0, 0.0, 0.0, 480.0, 0.0, 1.0, 0.0, 110.0, -0.0, 0.0, 1.0, 15.0, 0.0, 0.0, 0.0, 1.0],
            },
            {
                "name": "vertical_support_column",
                "path": "../automation_parts/transfer_column.step",
                "transform": [1.0, 0.0, 0.0, 360.0, 0.0, 1.0, 0.0, 225.0, -0.0, 0.0, 1.0, 15.0, 0.0, 0.0, 0.0, 1.0],
            },
            {
                "name": "station_base_plate",
                "path": "../automation_parts/small_base_plate.step",
                "transform": [1.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, -0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 1.0],
            },
            {
                "name": "horizontal_transfer_cylinder_guide",
                "path": "../automation_parts/linear_guide.step",
                "transform": [1.0, 0.0, 0.0, 360.0, 0.0, 1.0, 0.0, 225.0, -0.0, 0.0, 1.0, 15.0, 0.0, 0.0, 0.0, 1.0],
            },
            {
                "name": "vertical_transfer_cylinder_guide",
                "path": "../automation_parts/linear_guide.step",
                "transform": [1.0, 0.0, 0.0, 360.0, 0.0, 1.0, 0.0, 225.0, -0.0, 0.0, 1.0, 15.0, 0.0, 0.0, 0.0, 1.0],
            },
            {
                "name": "horizontal_positioning_cylinder_guide",
                "path": "../automation_parts/linear_guide.step",
                "transform": [1.0, 0.0, 0.0, 64.0, 0.0, 1.0, 0.0, 375.0, -0.0, 0.0, 1.0, 15.0, 0.0, 0.0, 0.0, 1.0],
            },
            {
                "name": "guide_cylinder_guide",
                "path": "../automation_parts/linear_guide.step",
                "transform": [1.0, 0.0, 0.0, 64.0, 0.0, 1.0, 0.0, 275.0, -0.0, 0.0, 1.0, 15.0, 0.0, 0.0, 0.0, 1.0],
            },
            {
                "name": "bolt_horizontal_transfer_cylinder_0",
                "path": "../automation_parts/bolt_m6x20.step",
                "transform": [1.0, 0.0, 0.0, 353.8, 0.0, 1.0, 0.0, 225.0, 0.0, 0.0, 1.0, 615.0, 0.0, 0.0, 0.0, 1.0],
            },
            {
                "name": "bolt_horizontal_transfer_cylinder_1",
                "path": "../automation_parts/bolt_m6x20.step",
                "transform": [1.0, 0.0, 0.0, 366.2, 0.0, 1.0, 0.0, 225.0, 0.0, 0.0, 1.0, 615.0, 0.0, 0.0, 0.0, 1.0],
            },
            {
                "name": "bolt_vertical_transfer_cylinder_0",
                "path": "../automation_parts/bolt_m6x20.step",
                "transform": [1.0, 0.0, 0.0, 353.8, 0.0, 1.0, 0.0, 225.0, 0.0, 0.0, 1.0, 735.0, 0.0, 0.0, 0.0, 1.0],
            },
            {
                "name": "bolt_vertical_transfer_cylinder_1",
                "path": "../automation_parts/bolt_m6x20.step",
                "transform": [1.0, 0.0, 0.0, 366.2, 0.0, 1.0, 0.0, 225.0, 0.0, 0.0, 1.0, 735.0, 0.0, 0.0, 0.0, 1.0],
            },
            {
                "name": "bolt_product_gripper_0",
                "path": "../automation_parts/bolt_m6x20.step",
                "transform": [1.0, 0.0, 0.0, 350.0, 0.0, 1.0, 0.0, 225.0, 0.0, 0.0, 1.0, 855.0, 0.0, 0.0, 0.0, 1.0],
            },
            {
                "name": "bolt_product_gripper_1",
                "path": "../automation_parts/bolt_m6x20.step",
                "transform": [1.0, 0.0, 0.0, 370.0, 0.0, 1.0, 0.0, 225.0, 0.0, 0.0, 1.0, 855.0, 0.0, 0.0, 0.0, 1.0],
            },
            {
                "name": "bolt_horizontal_positioning_cylinder_0",
                "path": "../automation_parts/bolt_m6x20.step",
                "transform": [1.0, 0.0, 0.0, 113.8, 0.0, 1.0, 0.0, 400.0, 0.0, 0.0, 1.0, 195.0, 0.0, 0.0, 0.0, 1.0],
            },
            {
                "name": "bolt_horizontal_positioning_cylinder_1",
                "path": "../automation_parts/bolt_m6x20.step",
                "transform": [1.0, 0.0, 0.0, 126.2, 0.0, 1.0, 0.0, 400.0, 0.0, 0.0, 1.0, 195.0, 0.0, 0.0, 0.0, 1.0],
            },
            {
                "name": "bolt_guide_cylinder_0",
                "path": "../automation_parts/bolt_m6x20.step",
                "transform": [1.0, 0.0, 0.0, 113.8, 0.0, 1.0, 0.0, 275.0, 0.0, 0.0, 1.0, 195.0, 0.0, 0.0, 0.0, 1.0],
            },
            {
                "name": "bolt_guide_cylinder_1",
                "path": "../automation_parts/bolt_m6x20.step",
                "transform": [1.0, 0.0, 0.0, 126.2, 0.0, 1.0, 0.0, 275.0, 0.0, 0.0, 1.0, 195.0, 0.0, 0.0, 0.0, 1.0],
            },
            {
                "name": "bolt_guide_mechanism_0",
                "path": "../automation_parts/bolt_m6x20.step",
                "transform": [1.0, 0.0, 0.0, 4.0, 0.0, 1.0, 0.0, 270.5, 0.0, 0.0, 1.0, 15.0, 0.0, 0.0, 0.0, 1.0],
            },
            {
                "name": "bolt_guide_mechanism_1",
                "path": "../automation_parts/bolt_m6x20.step",
                "transform": [1.0, 0.0, 0.0, 124.0, 0.0, 1.0, 0.0, 270.5, 0.0, 0.0, 1.0, 15.0, 0.0, 0.0, 0.0, 1.0],
            },
            {
                "name": "bolt_guide_mechanism_2",
                "path": "../automation_parts/bolt_m6x20.step",
                "transform": [1.0, 0.0, 0.0, 4.0, 0.0, 1.0, 0.0, 279.5, 0.0, 0.0, 1.0, 15.0, 0.0, 0.0, 0.0, 1.0],
            },
            {
                "name": "bolt_guide_mechanism_3",
                "path": "../automation_parts/bolt_m6x20.step",
                "transform": [1.0, 0.0, 0.0, 124.0, 0.0, 1.0, 0.0, 279.5, 0.0, 0.0, 1.0, 15.0, 0.0, 0.0, 0.0, 1.0],
            },
            {
                "name": "bolt_vertical_support_column_0",
                "path": "../automation_parts/bolt_m8x25.step",
                "transform": [1.0, 0.0, 0.0, 315.0, 0.0, 1.0, 0.0, 216.0, 0.0, 0.0, 1.0, 15.0, 0.0, 0.0, 0.0, 1.0],
            },
            {
                "name": "bolt_vertical_support_column_1",
                "path": "../automation_parts/bolt_m8x25.step",
                "transform": [1.0, 0.0, 0.0, 405.0, 0.0, 1.0, 0.0, 216.0, 0.0, 0.0, 1.0, 15.0, 0.0, 0.0, 0.0, 1.0],
            },
            {
                "name": "bolt_vertical_support_column_2",
                "path": "../automation_parts/bolt_m8x25.step",
                "transform": [1.0, 0.0, 0.0, 315.0, 0.0, 1.0, 0.0, 234.0, 0.0, 0.0, 1.0, 15.0, 0.0, 0.0, 0.0, 1.0],
            },
            {
                "name": "bolt_vertical_support_column_3",
                "path": "../automation_parts/bolt_m8x25.step",
                "transform": [1.0, 0.0, 0.0, 405.0, 0.0, 1.0, 0.0, 234.0, 0.0, 0.0, 1.0, 15.0, 0.0, 0.0, 0.0, 1.0],
            },
            {
                "name": "bolt_vibration_bowl_0",
                "path": "../automation_parts/bolt_m8x25.step",
                "transform": [1.0, 0.0, 0.0, 534.0, 0.0, 1.0, 0.0, 95.0, 0.0, 0.0, 1.0, 15.0, 0.0, 0.0, 0.0, 1.0],
            },
            {
                "name": "bolt_vibration_bowl_1",
                "path": "../automation_parts/bolt_m8x25.step",
                "transform": [1.0, 0.0, 0.0, 714.0, 0.0, 1.0, 0.0, 95.0, 0.0, 0.0, 1.0, 15.0, 0.0, 0.0, 0.0, 1.0],
            },
            {
                "name": "bolt_vibration_bowl_2",
                "path": "../automation_parts/bolt_m8x25.step",
                "transform": [1.0, 0.0, 0.0, 534.0, 0.0, 1.0, 0.0, 125.0, 0.0, 0.0, 1.0, 15.0, 0.0, 0.0, 0.0, 1.0],
            },
            {
                "name": "bolt_vibration_bowl_3",
                "path": "../automation_parts/bolt_m8x25.step",
                "transform": [1.0, 0.0, 0.0, 714.0, 0.0, 1.0, 0.0, 125.0, 0.0, 0.0, 1.0, 15.0, 0.0, 0.0, 0.0, 1.0],
            },
            {
                "name": "bolt_hopper_support_0",
                "path": "../automation_parts/bolt_m6x20.step",
                "transform": [1.0, 0.0, 0.0, 536.5, 0.0, 1.0, 0.0, 240.0, 0.0, 0.0, 1.0, 15.0, 0.0, 0.0, 0.0, 1.0],
            },
            {
                "name": "bolt_hopper_support_1",
                "path": "../automation_parts/bolt_m6x20.step",
                "transform": [1.0, 0.0, 0.0, 711.5, 0.0, 1.0, 0.0, 240.0, 0.0, 0.0, 1.0, 15.0, 0.0, 0.0, 0.0, 1.0],
            },
            {
                "name": "bolt_part_storage_hopper_0",
                "path": "../automation_parts/bolt_m8x25.step",
                "transform": [1.0, 0.0, 0.0, 504.0, 0.0, 1.0, 0.0, 345.0, 0.0, 0.0, 1.0, 65.0, 0.0, 0.0, 0.0, 1.0],
            },
            {
                "name": "bolt_part_storage_hopper_1",
                "path": "../automation_parts/bolt_m8x25.step",
                "transform": [1.0, 0.0, 0.0, 744.0, 0.0, 1.0, 0.0, 345.0, 0.0, 0.0, 1.0, 65.0, 0.0, 0.0, 0.0, 1.0],
            },
            {
                "name": "bolt_part_storage_hopper_2",
                "path": "../automation_parts/bolt_m8x25.step",
                "transform": [1.0, 0.0, 0.0, 504.0, 0.0, 1.0, 0.0, 375.0, 0.0, 0.0, 1.0, 65.0, 0.0, 0.0, 0.0, 1.0],
            },
            {
                "name": "bolt_part_storage_hopper_3",
                "path": "../automation_parts/bolt_m8x25.step",
                "transform": [1.0, 0.0, 0.0, 744.0, 0.0, 1.0, 0.0, 375.0, 0.0, 0.0, 1.0, 65.0, 0.0, 0.0, 0.0, 1.0],
            },
            {
                "name": "tube_linear_feeding_track_vibration_bowl",
                "path": "../automation_parts/air_tube_6mm.step",
                "transform": [1.0, -0.0, 0.0, 552.0, 0.0, 1.0, 0.0, 110.0, 0.0, 0.0, 1.0, 15.0, 0.0, 0.0, 0.0, 1.0],
            }
        ],
    }
