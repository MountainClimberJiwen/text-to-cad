"""Pneumatic cylinder standard part generator.

Produces a realistic-ish cylinder with barrel, end caps, piston rod and
mounting feet.  Not a full manufacturer model, but enough to look like a
cylinder and expose useful mating faces for assembly constraints.
"""
from __future__ import annotations

from build123d import (
    Box,
    Cylinder,
    Location,
    Part,
    export_step,
)


def pneumatic_cylinder(
    bore: float = 20.0,
    stroke: float = 40.0,
    rod_diameter: float | None = None,
    mounting: str = "foot",
) -> Part:
    """Generate a pneumatic cylinder part.

    Parameters
    ----------
    bore:
        Cylinder barrel inner diameter.
    stroke:
        Piston rod stroke length.
    rod_diameter:
        Piston rod diameter (defaults to bore/3).
    mounting:
        "foot" | "flange" | "none".
    """
    if rod_diameter is None:
        rod_diameter = bore / 3.0

    end_cap_thickness = max(4.0, bore / 8.0)
    barrel_length = stroke + end_cap_thickness * 2.0

    # Barrel (main tube)
    barrel = Cylinder(bore / 2.0, barrel_length)

    # Front cap (slightly larger OD, has rod bore)
    front_cap = Cylinder(bore / 2.0 + 3.0, end_cap_thickness).located(
        Location((0, 0, barrel_length / 2.0 - end_cap_thickness / 2.0))
    )

    # Rear cap
    rear_cap = Cylinder(bore / 2.0 + 3.0, end_cap_thickness).located(
        Location((0, 0, -barrel_length / 2.0 + end_cap_thickness / 2.0))
    )

    # Piston rod (protrudes from front cap by stroke length)
    rod_length = stroke + end_cap_thickness
    rod = Cylinder(rod_diameter / 2.0, rod_length).located(
        Location((0, 0, barrel_length / 2.0 + rod_length / 2.0 - end_cap_thickness))
    )

    shapes = [barrel, front_cap, rear_cap, rod]

    # Mounting feet — two symmetric tabs on the side
    if mounting == "foot":
        foot_thickness = max(4.0, bore / 6.0)
        foot_width = bore / 2.0 + 10.0
        foot_depth = 12.0
        y_offset = bore / 2.0 + foot_thickness / 2.0 + 1.0

        foot1 = Box(foot_width, foot_thickness, foot_depth).located(
            Location((0, -y_offset, 0))
        )
        foot2 = Box(foot_width, foot_thickness, foot_depth).located(
            Location((0, y_offset, 0))
        )
        shapes.extend([foot1, foot2])

    return Part(sum(shapes[1:], shapes[0]))


if __name__ == "__main__":
    part = pneumatic_cylinder(bore=20, stroke=40, mounting="foot")
    export_step(part, "/tmp/pneumatic_cylinder_test.step")
    print("Test STEP saved to /tmp/pneumatic_cylinder_test.step")
