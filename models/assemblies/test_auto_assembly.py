#!/usr/bin/env python3
"""Auto-generated assembly from AssemblyIntent."""
from __future__ import annotations
# Generated from AssemblyIntent: 6 parts, 5 relations
# Auto-generated fasteners: {'bolt': 16}


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
        "step_output": "test_auto_assembly.step",
        "instances": [
            {
                "name": "base_plate",
                "path": "../automation_parts/small_base_plate.step",
                "transform": [1.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, -0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 1.0],
            },
            {
                "name": "transfer_column",
                "path": "../automation_parts/transfer_column.step",
                "transform": [1.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, -50.0, -0.0, 0.0, 1.0, 15.0, 0.0, 0.0, 0.0, 1.0],
            },
            {
                "name": "gripper",
                "path": "../automation_parts/gripper.step",
                "transform": [1.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, -38.0, -0.0, 0.0, 1.0, 395.0, 0.0, 0.0, 0.0, 1.0],
            },
            {
                "name": "vib_bowl",
                "path": "../automation_parts/vibrating_bowl.step",
                "transform": [1.0, 0.0, 0.0, 260.0, 0.0, 1.0, 0.0, -120.0, -0.0, 0.0, 1.0, 15.0, 0.0, 0.0, 0.0, 1.0],
            },
            {
                "name": "guide_cyl",
                "path": "../automation_parts/pneumatic_cylinder.step",
                "transform": [1.0, 0.0, 0.0, -350.0, 0.0, 1.0, 0.0, 80.0, -0.0, 0.0, 1.0, 15.0, 0.0, 0.0, 0.0, 1.0],
            },
            {
                "name": "bolt_transfer_column_0",
                "path": "../automation_parts/bolt_m8x25.step",
                "transform": [1.0, 0.0, 0.0, -24.0, 0.0, 1.0, 0.0, -68.0, 0.0, 0.0, 1.0, 15.0, 0.0, 0.0, 0.0, 1.0],
            },
            {
                "name": "bolt_transfer_column_1",
                "path": "../automation_parts/bolt_m8x25.step",
                "transform": [1.0, 0.0, 0.0, 24.0, 0.0, 1.0, 0.0, -68.0, 0.0, 0.0, 1.0, 15.0, 0.0, 0.0, 0.0, 1.0],
            },
            {
                "name": "bolt_transfer_column_2",
                "path": "../automation_parts/bolt_m8x25.step",
                "transform": [1.0, 0.0, 0.0, -24.0, 0.0, 1.0, 0.0, -32.0, 0.0, 0.0, 1.0, 15.0, 0.0, 0.0, 0.0, 1.0],
            },
            {
                "name": "bolt_transfer_column_3",
                "path": "../automation_parts/bolt_m8x25.step",
                "transform": [1.0, 0.0, 0.0, 24.0, 0.0, 1.0, 0.0, -32.0, 0.0, 0.0, 1.0, 15.0, 0.0, 0.0, 0.0, 1.0],
            },
            {
                "name": "bolt_gripper_0",
                "path": "../automation_parts/bolt_m6x20.step",
                "transform": [1.0, 0.0, 0.0, -12.5, 0.0, 1.0, 0.0, -38.0, 0.0, 0.0, 1.0, 395.0, 0.0, 0.0, 0.0, 1.0],
            },
            {
                "name": "bolt_gripper_1",
                "path": "../automation_parts/bolt_m6x20.step",
                "transform": [1.0, 0.0, 0.0, 12.5, 0.0, 1.0, 0.0, -38.0, 0.0, 0.0, 1.0, 395.0, 0.0, 0.0, 0.0, 1.0],
            },
            {
                "name": "bolt_push_slide_0",
                "path": "../automation_parts/bolt_m6x20.step",
                "transform": [1.0, 0.0, 0.0, -334.0, 0.0, 1.0, 0.0, 62.0, 0.0, 0.0, 1.0, 15.0, 0.0, 0.0, 0.0, 1.0],
            },
            {
                "name": "bolt_push_slide_1",
                "path": "../automation_parts/bolt_m6x20.step",
                "transform": [1.0, 0.0, 0.0, -226.0, 0.0, 1.0, 0.0, 62.0, 0.0, 0.0, 1.0, 15.0, 0.0, 0.0, 0.0, 1.0],
            },
            {
                "name": "bolt_push_slide_2",
                "path": "../automation_parts/bolt_m6x20.step",
                "transform": [1.0, 0.0, 0.0, -334.0, 0.0, 1.0, 0.0, 98.0, 0.0, 0.0, 1.0, 15.0, 0.0, 0.0, 0.0, 1.0],
            },
            {
                "name": "bolt_push_slide_3",
                "path": "../automation_parts/bolt_m6x20.step",
                "transform": [1.0, 0.0, 0.0, -226.0, 0.0, 1.0, 0.0, 98.0, 0.0, 0.0, 1.0, 15.0, 0.0, 0.0, 0.0, 1.0],
            },
            {
                "name": "bolt_vib_bowl_0",
                "path": "../automation_parts/bolt_m8x25.step",
                "transform": [1.0, 0.0, 0.0, 245.0, 0.0, 1.0, 0.0, -135.0, 0.0, 0.0, 1.0, 15.0, 0.0, 0.0, 0.0, 1.0],
            },
            {
                "name": "bolt_vib_bowl_1",
                "path": "../automation_parts/bolt_m8x25.step",
                "transform": [1.0, 0.0, 0.0, 275.0, 0.0, 1.0, 0.0, -135.0, 0.0, 0.0, 1.0, 15.0, 0.0, 0.0, 0.0, 1.0],
            },
            {
                "name": "bolt_vib_bowl_2",
                "path": "../automation_parts/bolt_m8x25.step",
                "transform": [1.0, 0.0, 0.0, 245.0, 0.0, 1.0, 0.0, -105.0, 0.0, 0.0, 1.0, 15.0, 0.0, 0.0, 0.0, 1.0],
            },
            {
                "name": "bolt_vib_bowl_3",
                "path": "../automation_parts/bolt_m8x25.step",
                "transform": [1.0, 0.0, 0.0, 275.0, 0.0, 1.0, 0.0, -105.0, 0.0, 0.0, 1.0, 15.0, 0.0, 0.0, 0.0, 1.0],
            },
            {
                "name": "bolt_guide_cyl_0",
                "path": "../automation_parts/bolt_m6x20.step",
                "transform": [1.0, 0.0, 0.0, -355.0, 0.0, 1.0, 0.0, 80.0, 0.0, 0.0, 1.0, 15.0, 0.0, 0.0, 0.0, 1.0],
            },
            {
                "name": "bolt_guide_cyl_1",
                "path": "../automation_parts/bolt_m6x20.step",
                "transform": [1.0, 0.0, 0.0, -345.0, 0.0, 1.0, 0.0, 80.0, 0.0, 0.0, 1.0, 15.0, 0.0, 0.0, 0.0, 1.0],
            }
        ],
    }
