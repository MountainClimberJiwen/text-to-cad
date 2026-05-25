"""STEP-based standard parts library.

Loads pre-built STEP files from cad_asm/lib/ as library parts.
Each function returns a build123d Part loaded from the corresponding STEP file.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from build123d import import_step, Part, Compound, Solid


def _lib_dir() -> Path:
    """Return the path to the cad_asm/lib directory."""
    return Path(__file__).resolve().parent.parent / "lib"


def _load_step_part(rel_path: str) -> Part:
    """Load a STEP file from cad_asm/lib and return it as a Part."""
    step_path = _lib_dir() / rel_path
    if not step_path.exists():
        raise FileNotFoundError(f"STEP library part not found: {step_path}")

    shape = import_step(str(step_path))
    # import_step may return Solid or Compound; wrap uniformly as Part
    if isinstance(shape, Part):
        return shape
    if isinstance(shape, (Solid, Compound)):
        return Part([shape])
    # Fallback: try direct Part construction
    return Part(shape)


# ---------------------------------------------------------------------------
# Pneumatic parts
# ---------------------------------------------------------------------------
def step_air_pump(**_kwargs: Any) -> Part:
    return _load_step_part("pneumatic/air_pump.step")


def step_pneumatic_cylinder(**_kwargs: Any) -> Part:
    return _load_step_part("pneumatic/pneumatic_cylinder.step")


def step_large_cylinder(**_kwargs: Any) -> Part:
    return _load_step_part("pneumatic/large_cylinder.step")


def step_solenoid_valve(**_kwargs: Any) -> Part:
    return _load_step_part("pneumatic/solenoid_valve.step")


def step_air_tube_6mm(**_kwargs: Any) -> Part:
    return _load_step_part("pneumatic/air_tube_6mm.step")


# ---------------------------------------------------------------------------
# Electrical parts
# ---------------------------------------------------------------------------
def step_plc_module(**_kwargs: Any) -> Part:
    return _load_step_part("electrical/plc_module.step")


def step_servo_motor(**_kwargs: Any) -> Part:
    return _load_step_part("electrical/servo_motor.step")


def step_terminal_block(**_kwargs: Any) -> Part:
    return _load_step_part("electrical/terminal_block.step")


def step_din_rail(**_kwargs: Any) -> Part:
    return _load_step_part("electrical/din_rail.step")


def step_photo_sensor(**_kwargs: Any) -> Part:
    return _load_step_part("electrical/photo_sensor.step")


def step_proximity_sensor(**_kwargs: Any) -> Part:
    return _load_step_part("electrical/proximity_sensor.step")


def step_sensor_cable(**_kwargs: Any) -> Part:
    return _load_step_part("electrical/sensor_cable.step")


# ---------------------------------------------------------------------------
# Mechanical parts
# ---------------------------------------------------------------------------
def step_gripper(**_kwargs: Any) -> Part:
    return _load_step_part("mechanical/gripper.step")


def step_linear_guide(**_kwargs: Any) -> Part:
    return _load_step_part("mechanical/linear_guide.step")


def step_push_slide(**_kwargs: Any) -> Part:
    return _load_step_part("mechanical/push_slide.step")


def step_roller(**_kwargs: Any) -> Part:
    return _load_step_part("mechanical/roller.step")


def step_vibrating_bowl(**_kwargs: Any) -> Part:
    return _load_step_part("mechanical/vibrating_bowl.step")


def step_feeder_base(**_kwargs: Any) -> Part:
    return _load_step_part("mechanical/feeder_base.step")


def step_transfer_column(**_kwargs: Any) -> Part:
    return _load_step_part("mechanical/transfer_column.step")


def step_work_platform(**_kwargs: Any) -> Part:
    return _load_step_part("mechanical/work_platform.step")


# ---------------------------------------------------------------------------
# Structural parts
# ---------------------------------------------------------------------------
def step_frame_base(**_kwargs: Any) -> Part:
    return _load_step_part("structural/frame_base.step")


def step_mounting_plate(**_kwargs: Any) -> Part:
    return _load_step_part("structural/mounting_plate.step")


def step_small_base_plate(**_kwargs: Any) -> Part:
    return _load_step_part("structural/small_base_plate.step")


def step_cylinder_bracket(**_kwargs: Any) -> Part:
    return _load_step_part("structural/cylinder_bracket.step")


def step_roller_bracket(**_kwargs: Any) -> Part:
    return _load_step_part("structural/roller_bracket.step")


# ---------------------------------------------------------------------------
# Fasteners
# ---------------------------------------------------------------------------
def step_bolt_m6x20(**_kwargs: Any) -> Part:
    return _load_step_part("fasteners/bolt_m6x20.step")


def step_bolt_m8x25(**_kwargs: Any) -> Part:
    return _load_step_part("fasteners/bolt_m8x25.step")


def step_hex_nut_m6(**_kwargs: Any) -> Part:
    return _load_step_part("fasteners/hex_nut_m6.step")


def step_flat_washer_m6(**_kwargs: Any) -> Part:
    return _load_step_part("fasteners/flat_washer_m6.step")


# ---------------------------------------------------------------------------
# Conveyor parts
# ---------------------------------------------------------------------------
def step_cable_tray_channel(**_kwargs: Any) -> Part:
    return _load_step_part("conveyor/cable_tray_channel.step")
