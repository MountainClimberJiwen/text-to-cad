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

# Registry: name -> builder function
LIBRARY: dict[str, Callable[..., Part]] = {
    "pneumatic_cylinder": pneumatic_cylinder,
    "gripper_jaw": gripper_jaw,
    "base_plate": base_plate,
    "bracket_l": bracket_l,
}


def build_library_part(name: str, params: dict[str, Any]) -> Part:
    """Build a standard part by library name and parameters."""
    if name not in LIBRARY:
        raise ValueError(f"Unknown library part: {name}. Available: {list(LIBRARY.keys())}")
    builder = LIBRARY[name]
    return builder(**params)
