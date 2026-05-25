"""Structural standard parts: plates, brackets, etc."""
from __future__ import annotations

from build123d import (
    Box,
    Cylinder,
    Location,
    Part,
    export_step,
)


def base_plate(
    width: float = 100.0,
    depth: float = 60.0,
    thickness: float = 5.0,
    mounting_hole_diameter: float = 0.0,
    hole_spacing: float = 0.0,
) -> Part:
    """Generate a base plate with optional mounting holes."""
    plate = Box(width, depth, thickness)

    if mounting_hole_diameter > 0.0 and hole_spacing > 0.0:
        hole = Cylinder(mounting_hole_diameter / 2.0, thickness + 2.0)
        nx = int(width / hole_spacing)
        ny = int(depth / hole_spacing)
        for i in range(nx + 1):
            for j in range(ny + 1):
                x = -width / 2.0 + i * hole_spacing
                y = -depth / 2.0 + j * hole_spacing
                plate = plate - hole.located(Location((x, y, 0)))

    return Part(plate)


def bracket_l(
    leg_length: float = 40.0,
    leg_width: float = 20.0,
    thickness: float = 3.0,
) -> Part:
    """Generate an L-shaped bracket."""
    leg1 = Box(leg_length, leg_width, thickness)
    leg2 = Box(leg_width, leg_width, leg_length)
    # Position leg2 perpendicular to leg1
    leg2 = leg2.located(Location((-leg_length / 2.0 + leg_width / 2.0, 0, leg_length / 2.0)))
    return Part(leg1 + leg2)


if __name__ == "__main__":
    bp = base_plate(100, 60, 5, mounting_hole_diameter=4, hole_spacing=20)
    export_step(bp, "/tmp/base_plate_test.step")
    br = bracket_l(40, 20, 3)
    export_step(br, "/tmp/bracket_l_test.step")
    print("Test STEPs saved")
