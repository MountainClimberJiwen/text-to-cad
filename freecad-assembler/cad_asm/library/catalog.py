"""Library catalog with searchable metadata.

Agent (or user) can query the catalog by keywords / description
to find the best matching standard part before falling back to primitives.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ParamInfo:
    type: str
    description: str
    default: Any = None


@dataclass
class PartCatalogEntry:
    ref: str
    description: str
    keywords: list[str] = field(default_factory=list)
    params: dict[str, ParamInfo] = field(default_factory=dict)

    def match_score(self, query: str) -> float:
        """Simple keyword match score. 0.0 = no match, 1.0 = strong match."""
        query_lower = query.lower()
        tokens = set(query_lower.split())

        # Direct substring match in description
        if query_lower in self.description.lower():
            return 1.0

        # Keyword hits
        hits = 0
        for kw in self.keywords:
            if kw.lower() in query_lower:
                hits += 1
            elif any(kw.lower() in t for t in tokens):
                hits += 0.5

        if not self.keywords:
            return 0.0
        return min(1.0, hits / max(1, len(self.keywords) * 0.3))


# ---------------------------------------------------------------------------
# Catalog registry
# ---------------------------------------------------------------------------

CATALOG: dict[str, PartCatalogEntry] = {
    "pneumatic_cylinder": PartCatalogEntry(
        ref="pneumatic_cylinder",
        description=(
            "Realistic pneumatic cylinder with barrel, end caps, piston rod "
            "and optional mounting feet / flange."
        ),
        keywords=[
            "cylinder", "pneumatic", "air", "actuator", "气缸", "气压缸",
            "活塞", "cylinder", "缸体", "气动",
        ],
        params={
            "bore": ParamInfo("float", "Barrel inner diameter (mm)", 20.0),
            "stroke": ParamInfo("float", "Piston rod stroke length (mm)", 40.0),
            "rod_diameter": ParamInfo("float", "Piston rod diameter (mm), defaults to bore/3", None),
            "mounting": ParamInfo("str", 'Mounting style: "foot" | "flange" | "none"', "foot"),
        },
    ),
    "gripper_jaw": PartCatalogEntry(
        ref="gripper_jaw",
        description=(
            "Gripper jaw with angled grip face and central mounting hole."
        ),
        keywords=[
            "gripper", "jaw", "clamp", "夹爪", "夹头", "抓手", "夹具",
            "grip", "jaw",
        ],
        params={
            "width": ParamInfo("float", "Overall width (X direction, mm)", 30.0),
            "height": ParamInfo("float", "Overall height (Z direction, mm)", 20.0),
            "depth": ParamInfo("float", "Thickness (Y direction, mm)", 10.0),
            "grip_angle": ParamInfo("float", "Angle of grip face relative to vertical (deg)", 15.0),
            "mounting_hole_diameter": ParamInfo("float", "Central mounting hole diameter (mm)", 6.0),
        },
    ),
    "base_plate": PartCatalogEntry(
        ref="base_plate",
        description=(
            "Rectangular mounting plate with optional grid of mounting holes."
        ),
        keywords=[
            "plate", "base", "mounting", "底板", "底座", "板", "安装板",
            "base plate", "mount",
        ],
        params={
            "width": ParamInfo("float", "Plate width (mm)", 100.0),
            "depth": ParamInfo("float", "Plate depth (mm)", 60.0),
            "thickness": ParamInfo("float", "Plate thickness (mm)", 5.0),
            "mounting_hole_diameter": ParamInfo("float", "Mounting hole diameter, 0 = no holes", 0.0),
            "hole_spacing": ParamInfo("float", "Grid spacing for mounting holes, 0 = no grid", 0.0),
        },
    ),
    "bracket_l": PartCatalogEntry(
        ref="bracket_l",
        description="L-shaped bracket for perpendicular joining.",
        keywords=[
            "bracket", "l-bracket", "l bracket", "角铁", "支架", "l型",
            "bracket", "corner",
        ],
        params={
            "leg_length": ParamInfo("float", "Long leg length (mm)", 40.0),
            "leg_width": ParamInfo("float", "Leg width (mm)", 20.0),
            "thickness": ParamInfo("float", "Material thickness (mm)", 3.0),
        },
    ),
}


# ---------------------------------------------------------------------------
# Search API
# ---------------------------------------------------------------------------

def search_library(query: str, threshold: float = 0.2, top_k: int = 3) -> list[dict[str, Any]]:
    """Search the parts catalog by natural-language query.

    Returns a list of matches sorted by score descending.
    Each match is a dict with keys: ref, description, score, params.
    """
    scored = []
    for entry in CATALOG.values():
        score = entry.match_score(query)
        if score >= threshold:
            scored.append((score, entry))

    scored.sort(key=lambda x: x[0], reverse=True)

    results = []
    for score, entry in scored[:top_k]:
        results.append({
            "ref": entry.ref,
            "description": entry.description,
            "score": round(score, 3),
            "params": {k: {"type": v.type, "description": v.description, "default": v.default}
                       for k, v in entry.params.items()},
        })
    return results


def suggest_part_for_primitive(
    shape_type: str,
    params: dict[str, Any],
    query_hint: str = "",
) -> dict[str, Any] | None:
    """Given a primitive shape definition, suggest a library part if applicable.

    Returns the best library match or None if no good substitute exists.
    """
    # Build a synthetic query from shape type + params + hint
    tokens = [query_hint, shape_type]
    for k, v in params.items():
        tokens.append(f"{k}={v}")
    synthetic_query = " ".join(str(t) for t in tokens if t)

    matches = search_library(synthetic_query, threshold=0.3, top_k=1)
    if matches and matches[0]["score"] >= 0.5:
        return matches[0]
    return None


def list_library_parts() -> list[dict[str, Any]]:
    """Return a flat list of all available library parts."""
    return [
        {
            "ref": e.ref,
            "description": e.description,
            "keywords": e.keywords,
            "params": list(e.params.keys()),
        }
        for e in CATALOG.values()
    ]
