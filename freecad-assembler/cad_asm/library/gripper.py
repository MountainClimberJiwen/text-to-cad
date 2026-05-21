"""Gripper jaw standard part generator."""
from __future__ import annotations

import math

from build123d import (
    Box,
    Cylinder,
    Location,
    Part,
    export_step,
)


def gripper_jaw(
    width: float = 30.0,
    height: float = 20.0,
    depth: float = 10.0,
    grip_angle: float = 15.0,
    mounting_hole_diameter: float = 6.0,
) -> Part:
    """Generate a gripper jaw part.

    Parameters
    ----------
    width:
        Overall width (X direction).
    height:
        Overall height (Z direction).
    depth:
        Thickness (Y direction).
    grip_angle:
        Angle of the gripping face relative to vertical (degrees).
    mounting_hole_diameter:
        Diameter of the central mounting hole.
    """
    # Main body block
    body = Box(width, depth, height)

    # Grip face wedge — subtract a sloped block to create angled grip face
    if grip_angle != 0.0:
        angle_rad = math.radians(abs(grip_angle))
        wedge_depth = height * math.tan(angle_rad)
        wedge = Box(width + 2, wedge_depth + 2, height + 2).located(
            Location(
                (
                    0,
                    depth / 2.0 + wedge_depth / 2.0 + 0.5
                    if grip_angle > 0
                    else -depth / 2.0 - wedge_depth / 2.0 - 0.5,
                    0,
                )
            )
        )
        body = body - wedge

    # Mounting hole through the center (along Y axis)
    hole = Cylinder(mounting_hole_diameter / 2.0, depth + 2.0).located(
        Location((0, 0, 0))
    )
    body = body - hole

    return Part(body)


if __name__ == "__main__":
    part = gripper_jaw(width=30, height=20, depth=10, grip_angle=15)
    export_step(part, "/tmp/gripper_jaw_test.step")
    print("Test STEP saved to /tmp/gripper_jaw_test.step")
