"""
ACG-EF: Assembly Constraint-Guided Engineering Framework
Ontology: defines part types, relations, and engineering rules.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any
from enum import Enum

class PartType(Enum):
    BASE_PLATE = "base_plate"
    COLUMN = "column"
    BEAM = "beam"
    GANTRY = "gantry"           # composite: beam + 2 columns
    VIBRATION_BOWL = "vibration_bowl"
    HOPPER = "hopper"
    HOPPER_SUPPORT = "hopper_support"
    LINEAR_TRACK = "linear_track"
    CYLINDER = "cylinder"
    GUIDE_RAIL = "guide_rail"
    GRIPPER = "gripper"
    GRIPPER_JAW = "gripper_jaw"
    FIXTURE = "fixture"
    FIXTURE_PLATE = "fixture_plate"
    SENSOR = "sensor"
    MOTOR = "motor"
    SLIDER = "slider"
    PISTON = "piston"

class RelationType(Enum):
    SUPPORTED_BY = "supported_by"       # A is supported by B (A above B, faces touch)
    MOUNTED_ON = "mounted_on"           # A is mounted on top of B
    ALIGNED_CENTER = "aligned_center"   # A.center == B.center along axis
    GUIDES = "guides"                   # A guides B (parallel, close)
    DRIVES = "drives"                   # A drives B (piston drives slider etc)
    REACHES = "reaches"                 # A can reach B (workspace overlap)
    CLEARANCE = "clearance"             # A and B must have min distance
    CONNECTED_TO = "connected_to"       # A output connects to B input

@dataclass
class PartSpec:
    """Specification for a part instance."""
    name: str
    part_type: PartType
    parent: Optional[str] = None  # parent part name (for composites)
    params: Dict[str, Any] = field(default_factory=dict)
    # params filled by LLM or template defaults
    # e.g. {"width": 800, "depth": 500, "thickness": 15}

@dataclass
class Relation:
    """A relation between two parts."""
    rel_type: RelationType
    source: str      # part name
    target: str      # part name
    axis: Optional[str] = None  # "x", "y", "z" for alignment
    min_dist: Optional[float] = None  # for CLEARANCE

@dataclass
class AssemblyIntent:
    """Top-level intent parsed from LLM output."""
    parts: List[PartSpec] = field(default_factory=list)
    relations: List[Relation] = field(default_factory=list)
    global_params: Dict[str, Any] = field(default_factory=dict)


# ── Engineering Rules (hard constraints) ────────────────────────────

ENGINEERING_RULES = {
    "RULE_GANTRY_001": {
        "description": "Gantry beam must be supported by two columns at both ends",
        "applies_to": [PartType.GANTRY],
        "check": "beam_has_two_supporting_columns",
    },
    "RULE_COLUMN_001": {
        "description": "Column height must be >= 8 * beam thickness it supports",
        "applies_to": [PartType.COLUMN],
        "check": "column_height_vs_beam",
    },
    "RULE_CYLINDER_001": {
        "description": "Vertical cylinder stroke > 50mm must have guide rails",
        "applies_to": [PartType.CYLINDER],
        "check": "cylinder_has_guide_if_long_stroke",
    },
    "RULE_GRIPPER_001": {
        "description": "Gripper jaw volume must be >= 0.1% of base plate volume",
        "applies_to": [PartType.GRIPPER_JAW],
        "check": "gripper_jaw_visible",
    },
    "RULE_HOPPER_001": {
        "description": "Hopper must be independently supported, not on vibrating base",
        "applies_to": [PartType.HOPPER],
        "check": "hopper_independent_support",
    },
    "RULE_CONTACT_001": {
        "description": "SUPPORTED_BY relation implies face contact (gap < 0.1mm)",
        "applies_to": "all",
        "check": "contact_gap_check",
    },
    "RULE_BEAM_001": {
        "description": "Beam width must cover column span + 20mm minimum",
        "applies_to": [PartType.BEAM],
        "check": "beam_covers_columns",
    },
    "RULE_GUIDE_001": {
        "description": "Guide rail must be parallel to cylinder axis within 1 degree",
        "applies_to": [PartType.GUIDE_RAIL],
        "check": "guide_parallel_to_cylinder",
    },
    "RULE_VIB_BOWL_001": {
        "description": "Vibration bowl diameter <= 40% of base plate width",
        "applies_to": [PartType.VIBRATION_BOWL],
        "check": "vib_bowl_proportional",
    },
}


# ── Default parameter templates ─────────────────────────────────────

PART_DEFAULTS = {
    PartType.BASE_PLATE: {"width": 800, "depth": 500, "thickness": 15, "material": "aluminum"},
    PartType.COLUMN: {"width": 30, "depth": 30, "height": 250, "material": "steel"},
    PartType.BEAM: {"width": 300, "depth": 30, "height": 30, "material": "steel"},
    PartType.GANTRY: {"span": 300, "beam_height": 30, "column_size": 30, "height": 250},
    PartType.VIBRATION_BOWL: {"diameter": 200, "height": 30, "spiral_rise": 2},
    PartType.HOPPER: {"top_width": 120, "top_depth": 120, "bottom_width": 80, "bottom_depth": 80, "height": 100},
    PartType.HOPPER_SUPPORT: {"width": 20, "depth": 20, "height": 100},
    PartType.CYLINDER: {"bore": 20, "stroke": 100, "body_length": 120, "body_dia": 25},
    PartType.GUIDE_RAIL: {"width": 10, "depth": 15, "height": 120},
    PartType.GRIPPER: {"body_width": 40, "body_depth": 25, "body_height": 20, "stroke": 10},
    PartType.GRIPPER_JAW: {"width": 8, "depth": 15, "height": 20, "gap": 12},
    PartType.FIXTURE: {"width": 80, "depth": 80, "height": 40},
    PartType.FIXTURE_PLATE: {"width": 60, "depth": 60, "thickness": 10},
    PartType.LINEAR_TRACK: {"width": 20, "depth": 10, "length": 200},
    PartType.SLIDER: {"width": 30, "depth": 30, "height": 20},
    PartType.PISTON: {"diameter": 12, "length": 80},
    PartType.SENSOR: {"width": 20, "depth": 10, "height": 15},
    PartType.MOTOR: {"width": 60, "depth": 60, "height": 80},
}


def get_defaults(part_type: PartType) -> Dict[str, Any]:
    return dict(PART_DEFAULTS.get(part_type, {}))
