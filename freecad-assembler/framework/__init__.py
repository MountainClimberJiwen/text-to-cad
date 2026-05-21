"""ACG-EF: Assembly Constraint-Guided Engineering Framework"""

from .ontology import PartType, RelationType, PartSpec, Relation, AssemblyIntent
from .solver import AssemblySolver, BoundingBox
from .generator import build_intent_from_llm_output
from .verifier import AssemblyVerifier
from .templates import (
    FullStationTemplate,
    VibrationFeederTemplate,
    GantryPickPlaceTemplate,
    FixtureStationTemplate,
)

__all__ = [
    "PartType", "RelationType", "PartSpec", "Relation", "AssemblyIntent",
    "AssemblySolver", "BoundingBox",
    "build_intent_from_llm_output",
    "AssemblyVerifier",
    "FullStationTemplate",
    "VibrationFeederTemplate",
    "GantryPickPlaceTemplate",
    "FixtureStationTemplate",
]
