"""Pick & Place Arm assembly generator — v3 using real STEP standard parts.

Components:
- horizontal beam: push_slide (as-is, along X axis) — real slide table
- vertical cylinder: pneumatic_cylinder (vertical, along Z axis)
- gripper: gripper (vertical)
- solenoid valve: solenoid_valve
- air tubes: air_tube_6mm (bent routing)
- end buffer: procedural cylinder
- magnetic switch: procedural cylinder
"""
from __future__ import annotations

from pathlib import Path

from build123d import Compound, Cylinder, Location, import_step, export_step


def _lib_step(name: str) -> str:
    return str(Path(__file__).resolve().parent.parent.parent / "cad_asm/lib" / name)


def gen_step() -> dict:
    script_dir = Path(__file__).resolve().parent

    # Load real STEP parts
    push_slide = import_step(_lib_step("mechanical/push_slide.step"))
    pneumatic_cyl = import_step(_lib_step("pneumatic/pneumatic_cylinder.step"))
    gripper = import_step(_lib_step("mechanical/gripper.step"))
    solenoid_valve = import_step(_lib_step("pneumatic/solenoid_valve.step"))
    air_tube = import_step(_lib_step("pneumatic/air_tube_6mm.step"))

    # 1. Horizontal beam = push_slide (real slide table, along X)
    # Original bbox: [-90,-30,0] -> [90,30,42], center (0,0,21)
    # Place center at Z=0
    beam = push_slide.located(Location((0.0, 0.0, -21.0)))

    # 2. Vertical cylinder = pneumatic_cylinder (vertical, along Z)
    # Original bbox: [-12,-11,-31.2] -> [12,16,95.8], top at Z=95.8
    # Align top with beam bottom at Z=-21
    # Z shift: -21 - 95.8 = -116.8
    v_cyl = pneumatic_cyl.located(Location((0.0, 0.0, -116.8)))

    # 3. Gripper — mounting face at Z=0, jaw tips at Z=-76
    # Align mounting face (Z=0) with cylinder bottom (Z=-148)
    # Z shift: -148
    gripper_inst = gripper.located(Location((0.0, 0.0, -148.0)))

    # 4. Solenoid valve — mounted on Y+ side of VERTICAL cylinder (no floating)
    # Original bbox: [-28,-20.5,-8] -> [28,47.5,30]
    # Vertical cylinder after placement: Y range [-11, 16]
    # Place valve so its Y- face touches cylinder Y+ face (Y=16)
    valve = solenoid_valve.located(Location((0.0, 36.5, -84.5)))

    # 5. Short rigid air tubes — connecting valve to cylinder body (no floating)
    # Two short cylinders running from valve Y- face down to cylinder ports
    tube_p = Cylinder(2.5, 22.0).located(Location((12.0, 26.0, -55.0), (1, 0, 0), 90))
    tube_q = Cylinder(2.5, 22.0).located(Location((-12.0, 26.0, -55.0), (1, 0, 0), 90))

    # 6. End buffer — procedural hydraulic shock absorber at beam end
    buffer_body = Cylinder(5.0, 15.0).located(Location((95.0, 0.0, 0.0), (0, 1, 0), 90))
    buffer_knob = Cylinder(3.5, 8.0).located(Location((102.5, 0.0, 0.0), (0, 1, 0), 90))
    buffer = buffer_body + buffer_knob

    # 7. Magnetic switch — small cylinder on beam side
    switch = Cylinder(2.5, 10.0).located(Location((40.0, 33.0, 0.0), (1, 0, 0), -90))

    # Combine assembly
    assembly = Compound(children=[
        beam, v_cyl, gripper_inst, valve,
        tube_p, tube_q, buffer, switch,
    ])

    step_path = script_dir / "pick_place_arm_v3.step"
    export_step(assembly, str(step_path))

    # Build children envelope
    parts_dir = script_dir / "pick_place_arm_v3_parts"
    parts_dir.mkdir(exist_ok=True)

    # Export origin parts and record transforms
    origin_items = [
        ("push_slide", push_slide, Location((0.0, 0.0, -21.0))),
        ("pneumatic_cylinder", pneumatic_cyl, Location((0.0, 0.0, -116.8))),
        ("gripper", gripper, Location((0.0, 0.0, -148.0))),
        ("solenoid_valve", solenoid_valve, Location((0.0, 36.5, -84.5))),
        ("air_tube_p", air_tube, Location((12.0, 26.0, -55.0), (1, 0, 0), 90)),
        ("air_tube_q", air_tube, Location((-12.0, 26.0, -55.0), (1, 0, 0), 90)),
    ]

    # Procedural parts don't have separate origin files; include inline
    for name, shape, loc in origin_items:
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
        {"name": name, "path": f"pick_place_arm_v3_parts/{name}_origin.step", "transform": _loc_to_transform(loc)}
        for name, _, loc in origin_items
    ]
    # Add procedural parts as flat shapes (no path, but we need path for assembly contract)
    # Export procedural parts too
    export_step(buffer, str(parts_dir / "end_buffer_origin.step"))
    export_step(switch, str(parts_dir / "magnetic_switch_origin.step"))
    children.append({"name": "end_buffer", "path": "pick_place_arm_v3_parts/end_buffer_origin.step", "transform": _loc_to_transform(Location((0, 0, 0)))})
    children.append({"name": "magnetic_switch", "path": "pick_place_arm_v3_parts/magnetic_switch_origin.step", "transform": _loc_to_transform(Location((0, 0, 0)))})

    return {
        "children": children,
        "step_output": "pick_place_arm_v3.step",
    }


if __name__ == "__main__":
    env = gen_step()
    print(f"Assembly exported to: {env['step_output']}")
