"""Pick & Place Arm assembly generator — using real STEP standard parts from cad_asm/lib.

Components:
- horizontal beam: large_cylinder (rotated to X axis)
- vertical slide: push_slide (rotated to Z axis)
- gripper: gripper (as-is, vertical)
- solenoid valve: solenoid_valve (mounted on beam side)
- air tubes: air_tube_6mm (multiple instances for tubing)
- bracket: cylinder_bracket (adapter between slide and gripper)
"""
from __future__ import annotations

from pathlib import Path

from build123d import Compound, Location, import_step, export_step


def _lib_step(name: str) -> str:
    return str(Path(__file__).resolve().parent.parent.parent / "cad_asm/lib" / name)


def gen_step() -> dict:
    script_dir = Path(__file__).resolve().parent

    # ------------------------------------------------------------------
    # Load real STEP parts
    # ------------------------------------------------------------------
    large_cylinder = import_step(_lib_step("pneumatic/large_cylinder.step"))
    push_slide = import_step(_lib_step("mechanical/push_slide.step"))
    gripper = import_step(_lib_step("mechanical/gripper.step"))
    solenoid_valve = import_step(_lib_step("pneumatic/solenoid_valve.step"))
    air_tube = import_step(_lib_step("pneumatic/air_tube_6mm.step"))
    bracket = import_step(_lib_step("structural/cylinder_bracket.step"))

    # ------------------------------------------------------------------
    # Apply transforms to assemble
    # ------------------------------------------------------------------

    # 1. Horizontal beam (large cylinder) — rotate to X axis, center at origin
    # Original bbox: [-24,-22,-50] -> [24,30,195]  (along Z)
    # After Y-90 rotation: X[-50,195], Y[-22,30], Z[-24,24], center (72.5,4,0)
    beam = large_cylinder.located(Location((-72.5, -4.0, 0.0), (0, 1, 0), 90))

    # 2. Vertical slide (push slide) — rotate to Z axis, hang under beam
    # Original bbox: [-90,-30,0] -> [90,30,42]  (horizontal, along X)
    # After Y-90 rotation: X[0,42], Y[-30,30], Z[-90,90], center (21,0,0)
    # Top face at Z=90 should align with beam bottom at Z=-24
    # Z shift: -24 - 90 = -114
    # X shift: center at 0 -> -21
    slide = push_slide.located(Location((-21.0, 0.0, -114.0), (0, 1, 0), 90))

    # 3. Gripper — keep vertical. Original bbox Z[-76,0]
    # Z=-76 is jaw tips (bottom), Z=0 is mounting face (top)
    # Mounting face aligns with slide bottom at Z=-204
    # Z shift: -204
    # X shift: center at X=4 -> -4
    gripper_inst = gripper.located(Location((-4.0, 0.0, -204.0)))

    # 4. Cylinder bracket — adapter between slide and gripper
    # Original bbox: [-25,-20,0] -> [25,28,58] (vertical, Z up)
    # Mount under slide bottom (Z=-204), above gripper mounting face (Z=-204)
    # Actually place it alongside or between. Let's put it on the side of the slide.
    bracket_inst = bracket.located(Location((45.0, 0.0, -120.0)))

    # 5. Solenoid valve — mounted on side of beam
    # Original bbox: [-28,-20.5,-8] -> [28,47.5,30]
    # Place on Y+ side of beam
    valve = solenoid_valve.located(Location((20.0, 45.0, 0.0)))

    # 6. Air tubes — from valve to slide
    # Tube original: [-4,-4,0] -> [4,4,100] (along Z)
    tube1 = air_tube.located(Location((20.0, 35.0, -40.0), (1, 0, 0), -90))  # vertical down
    tube2 = air_tube.located(Location((20.0, 25.0, -80.0), (1, 0, 0), -90))  # another tube
    tube3 = air_tube.located(Location((10.0, 30.0, -60.0), (0, 1, 0), 90))   # angled

    # ------------------------------------------------------------------
    # Combine into assembly
    # ------------------------------------------------------------------
    assembly = Compound(children=[
        beam, slide, gripper_inst, bracket_inst,
        valve, tube1, tube2, tube3,
    ])

    step_path = script_dir / "pick_place_arm_v2.step"
    export_step(assembly, str(step_path))

    # ------------------------------------------------------------------
    # Build children envelope for viewer assembly tree
    # ------------------------------------------------------------------
    parts_dir = script_dir / "pick_place_arm_v2_parts"
    parts_dir.mkdir(exist_ok=True)

    origin_names = [
        ("horizontal_beam", large_cylinder, Location((-72.5, -4.0, 0.0), (0, 1, 0), 90)),
        ("vertical_slide", push_slide, Location((-21.0, 0.0, -114.0), (0, 1, 0), 90)),
        ("gripper", gripper, Location((-4.0, 0.0, -204.0))),
        ("cylinder_bracket", bracket, Location((45.0, 0.0, -120.0))),
        ("solenoid_valve", solenoid_valve, Location((20.0, 45.0, 0.0))),
        ("air_tube_1", air_tube, Location((20.0, 35.0, -40.0), (1, 0, 0), -90)),
        ("air_tube_2", air_tube, Location((20.0, 25.0, -80.0), (1, 0, 0), -90)),
        ("air_tube_3", air_tube, Location((10.0, 30.0, -60.0), (0, 1, 0), 90)),
    ]

    for name, shape, loc in origin_names:
        export_step(shape, str(parts_dir / f"{name}_origin.step"))

    def _loc_to_transform(loc: Location) -> list[float]:
        m = loc.wrapped.Transformation()
        return [
            float(m.Value(1, 1)), float(m.Value(1, 2)), float(m.Value(1, 3)), float(m.Value(1, 4)),
            float(m.Value(2, 1)), float(m.Value(2, 2)), float(m.Value(2, 3)), float(m.Value(2, 4)),
            float(m.Value(3, 1)), float(m.Value(3, 2)), float(m.Value(3, 3)), float(m.Value(3, 4)),
            0.0, 0.0, 0.0, 1.0,
        ]

    children = [
        {"name": name, "path": f"pick_place_arm_v2_parts/{name}_origin.step", "transform": _loc_to_transform(loc)}
        for name, _, loc in origin_names
    ]

    return {
        "children": children,
        "step_output": "pick_place_arm_v2.step",
    }


if __name__ == "__main__":
    env = gen_step()
    print(f"Assembly exported to: {env['step_output']}")
