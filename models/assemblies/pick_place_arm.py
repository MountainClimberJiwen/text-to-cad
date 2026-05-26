"""Pick & Place Arm assembly generator.

A two-axis pneumatic cartesian transfer module:
- Horizontal beam (rodless cylinder) provides X-axis travel
- Vertical slide (guided cylinder) provides Z-axis travel
- Pneumatic gripper at bottom performs pick/place
- Cable chain on top protects air tubes and signal wires
"""
from __future__ import annotations

import math
from pathlib import Path

from build123d import (
    Axis,
    Box,
    Compound,
    Cylinder,
    Location,
    Part,
    Rotation,
    Vector,
    export_step,
    Color,
)

# ---------------------------------------------------------------------------
# Colors
# ---------------------------------------------------------------------------
COLOR_ALUMINUM = Color(0.75, 0.75, 0.78, 1.0)   # silver/gray
COLOR_GREEN = Color(0.20, 0.55, 0.30, 1.0)       # guide rail plate
COLOR_BLACK = Color(0.15, 0.15, 0.15, 1.0)       # adapter / connector
COLOR_DARK_GRAY = Color(0.35, 0.35, 0.38, 1.0)   # gripper body / cylinder
COLOR_ORANGE = Color(0.90, 0.45, 0.10, 1.0)      # jaw pads
COLOR_CHAIN = Color(0.25, 0.25, 0.28, 1.0)       # cable chain
COLOR_BUFFER = Color(0.85, 0.20, 0.20, 1.0)      # buffer knob
COLOR_SWITCH = Color(0.10, 0.10, 0.80, 1.0)      # magnetic switch

# ---------------------------------------------------------------------------
# Part generators
# ---------------------------------------------------------------------------

def _make_horizontal_beam() -> Part:
    """Rodless pneumatic cylinder beam with sliding carriage."""
    beam_length = 260.0
    beam_dia = 20.0
    carriage_w = 50.0
    carriage_h = 30.0
    carriage_d = 24.0

    # Main barrel (silver)
    barrel = Cylinder(beam_dia / 2.0, beam_length)
    barrel.color = COLOR_ALUMINUM

    # End caps
    cap = Cylinder(beam_dia / 2.0 + 2.0, 6.0)
    cap_l = cap.located(Location((0, 0, -beam_length / 2.0 + 3.0)))
    cap_r = cap.located(Location((0, 0, beam_length / 2.0 - 3.0)))
    cap_l.color = COLOR_ALUMINUM
    cap_r.color = COLOR_ALUMINUM

    # Sliding carriage (centered)
    carriage = Box(carriage_w, carriage_d, carriage_h).located(
        Location((0, 0, 0))
    )
    carriage.color = COLOR_ALUMINUM

    # Mounting slots on carriage (visual only — subtract thin boxes)
    slot = Box(carriage_w + 2, 4.0, 6.0).located(Location((0, 0, 0)))

    body = barrel + cap_l + cap_r + carriage - slot
    return body


def _make_vertical_slide() -> Part:
    """Guided slide cylinder (green rail plate + gray cylinder body)."""
    rail_w = 40.0
    rail_d = 12.0
    rail_h = 140.0
    cyl_dia = 16.0
    cyl_len = 120.0

    # Green rail plate
    rail = Box(rail_w, rail_d, rail_h)
    rail.color = COLOR_GREEN

    # Two linear guide rails (slightly raised strips)
    guide = Box(6.0, 2.0, rail_h - 10.0).located(Location((-12, rail_d / 2.0 + 1.0, 0)))
    guide2 = Box(6.0, 2.0, rail_h - 10.0).located(Location((12, rail_d / 2.0 + 1.0, 0)))
    guide.color = COLOR_ALUMINUM
    guide2.color = COLOR_ALUMINUM

    # Cylinder body (gray) — mounted on back
    cyl = Cylinder(cyl_dia / 2.0, cyl_len).located(
        Location((0, -rail_d / 2.0 - cyl_dia / 2.0 + 2.0, 0))
    )
    cyl.color = COLOR_DARK_GRAY

    # Sliding block on rail
    block = Box(30.0, 14.0, 20.0).located(Location((0, rail_d / 2.0 + 3.0, 30.0)))
    block.color = COLOR_ALUMINUM

    body = rail + guide + guide2 + cyl + block
    return body


def _make_adapter_plate() -> Part:
    """Black adapter between vertical slide and gripper."""
    plate = Box(30.0, 16.0, 10.0)
    plate.color = COLOR_BLACK
    return plate


def _make_gripper_body() -> Part:
    """Pneumatic gripper body (MHZ2-style compact)."""
    body = Box(36.0, 20.0, 22.0)
    body.color = COLOR_DARK_GRAY

    # Central bore where piston moves
    bore = Cylinder(8.0, 24.0).located(Location((0, 0, 0), (1, 0, 0), 90))

    # Slot for jaws
    slot = Box(28.0, 4.0, 24.0).located(Location((0, 0, -8.0)))

    result = body - bore - slot
    result.color = COLOR_DARK_GRAY
    return result


def _make_gripper_jaw(side: str = "left") -> Part:
    """Single gripper jaw finger with grip face."""
    w = 8.0
    d = 12.0
    h = 25.0

    # Main finger block
    jaw = Box(w, d, h)

    # Angled grip face (15 deg)
    angle_rad = math.radians(15.0)
    wedge_d = h * math.tan(angle_rad)
    wedge = Box(w + 2, wedge_d + 2, h + 2).located(
        Location((0, -d / 2.0 - wedge_d / 2.0 - 0.5, 0))
    )
    jaw = jaw - wedge

    # Grip pad (orange insert)
    pad = Box(w - 2, 2.0, h - 8.0).located(Location((0, -d / 2.0 + 1.0, -4.0)))
    pad.color = COLOR_ORANGE

    jaw = jaw + pad
    jaw.color = COLOR_ALUMINUM

    return jaw


def _make_cable_chain() -> Part:
    """Flexible cable chain / hose carrier above the beam."""
    # Build a chain as a series of small links along an arc
    links = []
    n_links = 12
    radius = 60.0
    start_angle = math.radians(0.0)
    end_angle = math.radians(90.0)

    for i in range(n_links):
        t = i / (n_links - 1)
        angle = start_angle + t * (end_angle - start_angle)
        x = -radius * math.cos(angle) + radius
        z = radius * math.sin(angle)
        link = Box(14.0, 10.0, 4.0).located(Location((x, 0, z)))
        link.color = COLOR_CHAIN
        links.append(link)

    chain_compound = sum(links[1:], links[0])
    return Part(chain_compound)


def _make_end_buffer() -> Part:
    """Hydraulic shock absorber at beam end."""
    body = Cylinder(6.0, 18.0)
    body.color = COLOR_DARK_GRAY
    knob = Cylinder(4.0, 8.0).located(Location((0, 0, 13.0)))
    knob.color = COLOR_BUFFER
    return body + knob


def _make_magnetic_switch() -> Part:
    """Small cylinder magnetic reed switch."""
    sw = Cylinder(3.0, 12.0)
    sw.color = COLOR_SWITCH
    return sw


# ---------------------------------------------------------------------------
# Assembly
# ---------------------------------------------------------------------------

def gen_step() -> dict:
    """Generate the Pick & Place Arm assembly envelope."""
    script_dir = Path(__file__).resolve().parent

    # --- Build parts at origin ---
    horizontal = _make_horizontal_beam()
    vertical = _make_vertical_slide()
    adapter = _make_adapter_plate()
    gripper = _make_gripper_body()
    jaw_l = _make_gripper_jaw("left")
    jaw_r = _make_gripper_jaw("right")
    chain = _make_cable_chain()
    buffer = _make_end_buffer()
    switch = _make_magnetic_switch()

    # --- Apply transforms to assemble ---
    # 1. Horizontal beam is the base, lying along X axis at top
    horizontal_t = horizontal.located(Location((0, 0, 0), (0, 1, 0), 90))

    # 2. Vertical slide hangs from carriage center, pointing down (-Z)
    # Carriage bottom is at Z = -15; slide rail top aligns there.
    # Rail height 140, center offset = -15 - 70 = -85
    vertical_t = vertical.located(Location((0, 0, -85.0)))

    # 3. Adapter plate between vertical slide and gripper
    # Slide bottom at Z = -85 - 70 = -155; adapter top aligns there.
    # Adapter height 10, center at -155 - 5 = -160
    adapter_t = adapter.located(Location((0, 0, -160.0)))

    # 4. Gripper body below adapter
    # Adapter bottom at Z = -160 - 5 = -165; gripper top aligns there.
    # Gripper height 22, center at -165 - 11 = -176
    gripper_t = gripper.located(Location((0, 0, -176.0)))

    # 5. Jaw fingers inside gripper slot
    # Gripper bottom at Z = -176 - 11 = -187; jaw top aligns there.
    # Jaw height 25, center at -187 - 12.5 = -199.5
    jaw_l_t = jaw_l.located(Location((-7.0, 0, -199.5)))
    jaw_r_t = jaw_r.located(Location((7.0, 0, -199.5)))

    # 6. Cable chain above beam, starting from carriage area
    chain_t = chain.located(Location((-20.0, 0, 25.0)))

    # 7. End buffer at right end of beam
    buffer_t = buffer.located(Location((130.0, 0, 0), (0, 1, 0), 90))

    # 8. Magnetic switch on side of horizontal beam (Y+ side)
    # Switch cylinder along Y axis, mounted on carriage side Y=12
    switch_t = switch.located(Location((60.0, 18.0, 0), (1, 0, 0), -90))

    # Combine all into one Compound for export
    assembly = Compound(children=[
        horizontal_t, vertical_t, adapter_t, gripper_t,
        jaw_l_t, jaw_r_t, chain_t, buffer_t, switch_t,
    ])

    # Export
    step_path = script_dir / "pick_place_arm.step"
    export_step(assembly, str(step_path))

    # Also write individual component STEP files for assembly envelope
    parts_dir = script_dir / "pick_place_arm_parts"
    parts_dir.mkdir(exist_ok=True)

    part_paths = {
        "horizontal_beam": (horizontal_t, parts_dir / "horizontal_beam.step"),
        "vertical_slide": (vertical_t, parts_dir / "vertical_slide.step"),
        "adapter_plate": (adapter_t, parts_dir / "adapter_plate.step"),
        "gripper_body": (gripper_t, parts_dir / "gripper_body.step"),
        "gripper_jaw_left": (jaw_l_t, parts_dir / "gripper_jaw_left.step"),
        "gripper_jaw_right": (jaw_r_t, parts_dir / "gripper_jaw_right.step"),
        "cable_chain": (chain_t, parts_dir / "cable_chain.step"),
        "end_buffer": (buffer_t, parts_dir / "end_buffer.step"),
        "magnetic_switch": (switch_t, parts_dir / "magnetic_switch.step"),
    }

    for name, (shape, path) in part_paths.items():
        export_step(shape, str(path))

    # Build children tree with transforms (identity since we pre-transformed)
    # Actually for children tree we should export at-origin parts and provide transforms.
    # Re-export at-origin parts:
    origin_paths = {
        "horizontal_beam": (horizontal, parts_dir / "horizontal_beam_origin.step"),
        "vertical_slide": (vertical, parts_dir / "vertical_slide_origin.step"),
        "adapter_plate": (adapter, parts_dir / "adapter_plate_origin.step"),
        "gripper_body": (gripper, parts_dir / "gripper_body_origin.step"),
        "gripper_jaw_left": (jaw_l, parts_dir / "gripper_jaw_left_origin.step"),
        "gripper_jaw_right": (jaw_r, parts_dir / "gripper_jaw_right_origin.step"),
        "cable_chain": (chain, parts_dir / "cable_chain_origin.step"),
        "end_buffer": (buffer, parts_dir / "end_buffer_origin.step"),
        "magnetic_switch": (switch, parts_dir / "magnetic_switch_origin.step"),
    }
    for name, (shape, path) in origin_paths.items():
        export_step(shape, str(path))

    def _loc_to_transform(loc: Location) -> list[float]:
        """Convert build123d Location to 16-number row-major transform."""
        m = loc.wrapped.Transformation()
        # Row-major: OCP gp_Trsf matrix is 3x4, row-major in Value(i,j) where i=1..3, j=1..4
        return [
            float(m.Value(1, 1)), float(m.Value(1, 2)), float(m.Value(1, 3)), float(m.Value(1, 4)),
            float(m.Value(2, 1)), float(m.Value(2, 2)), float(m.Value(2, 3)), float(m.Value(2, 4)),
            float(m.Value(3, 1)), float(m.Value(3, 2)), float(m.Value(3, 3)), float(m.Value(3, 4)),
            0.0, 0.0, 0.0, 1.0,
        ]

    children = [
        {"name": "horizontal_beam", "path": "pick_place_arm_parts/horizontal_beam_origin.step", "transform": _loc_to_transform(Location((0, 0, 0), (0, 1, 0), 90))},
        {"name": "vertical_slide", "path": "pick_place_arm_parts/vertical_slide_origin.step", "transform": _loc_to_transform(Location((0, 0, -85.0)))},
        {"name": "adapter_plate", "path": "pick_place_arm_parts/adapter_plate_origin.step", "transform": _loc_to_transform(Location((0, 0, -160.0)))},
        {"name": "gripper_body", "path": "pick_place_arm_parts/gripper_body_origin.step", "transform": _loc_to_transform(Location((0, 0, -176.0)))},
        {"name": "gripper_jaw_left", "path": "pick_place_arm_parts/gripper_jaw_left_origin.step", "transform": _loc_to_transform(Location((-7.0, 0, -199.5)))},
        {"name": "gripper_jaw_right", "path": "pick_place_arm_parts/gripper_jaw_right_origin.step", "transform": _loc_to_transform(Location((7.0, 0, -199.5)))},
        {"name": "cable_chain", "path": "pick_place_arm_parts/cable_chain_origin.step", "transform": _loc_to_transform(Location((-20.0, 0, 25.0)))},
        {"name": "end_buffer", "path": "pick_place_arm_parts/end_buffer_origin.step", "transform": _loc_to_transform(Location((130.0, 0, 0), (0, 1, 0), 90))},
        {"name": "magnetic_switch", "path": "pick_place_arm_parts/magnetic_switch_origin.step", "transform": _loc_to_transform(Location((60.0, 18.0, 0), (1, 0, 0), -90))},
    ]

    return {
        "children": children,
        "step_output": "pick_place_arm.step",
    }


if __name__ == "__main__":
    env = gen_step()
    print(f"Assembly exported to: {env['step_output']}")
