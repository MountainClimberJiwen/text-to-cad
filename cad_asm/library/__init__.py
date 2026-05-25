"""Standard parts library for cad-asm.

Agent can reference pre-built parts instead of drawing primitives from scratch.
"""
from __future__ import annotations

from typing import Callable, Any

from build123d import Part

from cad_asm.library.pneumatic import pneumatic_cylinder
from cad_asm.library.gripper import gripper_jaw
from cad_asm.library.structural import base_plate, bracket_l
from cad_asm.library.catalog import (
    CATALOG,
    search_library,
    suggest_part_for_primitive,
    list_library_parts,
)
from cad_asm.library.step_parts import (
    step_air_pump,
    step_pneumatic_cylinder,
    step_large_cylinder,
    step_solenoid_valve,
    step_air_tube_6mm,
    step_plc_module,
    step_servo_motor,
    step_terminal_block,
    step_din_rail,
    step_photo_sensor,
    step_proximity_sensor,
    step_sensor_cable,
    step_gripper,
    step_linear_guide,
    step_push_slide,
    step_roller,
    step_vibrating_bowl,
    step_feeder_base,
    step_transfer_column,
    step_work_platform,
    step_frame_base,
    step_mounting_plate,
    step_small_base_plate,
    step_cylinder_bracket,
    step_roller_bracket,
    step_bolt_m6x20,
    step_bolt_m8x25,
    step_hex_nut_m6,
    step_flat_washer_m6,
    step_cable_tray_channel,
)

# Registry: name -> builder function
LIBRARY: dict[str, Callable[..., Part]] = {
    # Procedural parts
    "pneumatic_cylinder": pneumatic_cylinder,
    "gripper_jaw": gripper_jaw,
    "base_plate": base_plate,
    "bracket_l": bracket_l,
    # STEP-based standard parts (pneumatic)
    "step_air_pump": step_air_pump,
    "step_pneumatic_cylinder": step_pneumatic_cylinder,
    "step_large_cylinder": step_large_cylinder,
    "step_solenoid_valve": step_solenoid_valve,
    "step_air_tube_6mm": step_air_tube_6mm,
    # STEP-based standard parts (electrical)
    "step_plc_module": step_plc_module,
    "step_servo_motor": step_servo_motor,
    "step_terminal_block": step_terminal_block,
    "step_din_rail": step_din_rail,
    "step_photo_sensor": step_photo_sensor,
    "step_proximity_sensor": step_proximity_sensor,
    "step_sensor_cable": step_sensor_cable,
    # STEP-based standard parts (mechanical)
    "step_gripper": step_gripper,
    "step_linear_guide": step_linear_guide,
    "step_push_slide": step_push_slide,
    "step_roller": step_roller,
    "step_vibrating_bowl": step_vibrating_bowl,
    "step_feeder_base": step_feeder_base,
    "step_transfer_column": step_transfer_column,
    "step_work_platform": step_work_platform,
    # STEP-based standard parts (structural)
    "step_frame_base": step_frame_base,
    "step_mounting_plate": step_mounting_plate,
    "step_small_base_plate": step_small_base_plate,
    "step_cylinder_bracket": step_cylinder_bracket,
    "step_roller_bracket": step_roller_bracket,
    # STEP-based standard parts (fasteners)
    "step_bolt_m6x20": step_bolt_m6x20,
    "step_bolt_m8x25": step_bolt_m8x25,
    "step_hex_nut_m6": step_hex_nut_m6,
    "step_flat_washer_m6": step_flat_washer_m6,
    # STEP-based standard parts (conveyor)
    "step_cable_tray_channel": step_cable_tray_channel,
}


def build_library_part(name: str, params: dict[str, Any]) -> Part:
    """Build a standard part by library name and parameters."""
    if name not in LIBRARY:
        raise ValueError(f"Unknown library part: {name}. Available: {list(LIBRARY.keys())}")
    builder = LIBRARY[name]
    return builder(**params)
