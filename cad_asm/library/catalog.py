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
    # -----------------------------------------------------------------------
    # Procedural parts
    # -----------------------------------------------------------------------
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
    # -----------------------------------------------------------------------
    # STEP-based standard parts  (pneumatic)
    # -----------------------------------------------------------------------
    "step_air_pump": PartCatalogEntry(
        ref="step_air_pump",
        description="Standard air pump / vacuum generator unit.",
        keywords=["air pump", "vacuum", "气泵", "真空泵", "pneumatic pump"],
        params={},
    ),
    "step_pneumatic_cylinder": PartCatalogEntry(
        ref="step_pneumatic_cylinder",
        description="Standard pneumatic cylinder (STEP model).",
        keywords=["cylinder", "pneumatic", "air", "actuator", "气缸", "气压缸", "气动"],
        params={},
    ),
    "step_large_cylinder": PartCatalogEntry(
        ref="step_large_cylinder",
        description="Large-bore pneumatic cylinder (STEP model).",
        keywords=["cylinder", "large", "pneumatic", "大气缸", "big cylinder"],
        params={},
    ),
    "step_solenoid_valve": PartCatalogEntry(
        ref="step_solenoid_valve",
        description="Pneumatic solenoid directional control valve.",
        keywords=["solenoid", "valve", "电磁阀", "换向阀", "pneumatic valve"],
        params={},
    ),
    "step_air_tube_6mm": PartCatalogEntry(
        ref="step_air_tube_6mm",
        description="6 mm pneumatic air tube / hose segment.",
        keywords=["air tube", "hose", "气管", "6mm", "pneumatic tube"],
        params={},
    ),
    # -----------------------------------------------------------------------
    # STEP-based standard parts  (electrical)
    # -----------------------------------------------------------------------
    "step_plc_module": PartCatalogEntry(
        ref="step_plc_module",
        description="PLC control module / programmable logic controller.",
        keywords=["plc", "controller", "PLC", "控制器", "programmable"],
        params={},
    ),
    "step_servo_motor": PartCatalogEntry(
        ref="step_servo_motor",
        description="AC servo motor with encoder feedback.",
        keywords=["servo", "motor", "伺服电机", "马达", "servo motor"],
        params={},
    ),
    "step_terminal_block": PartCatalogEntry(
        ref="step_terminal_block",
        description="DIN-rail terminal block for wire termination.",
        keywords=["terminal", "block", "接线端子", "端子排", "terminal block"],
        params={},
    ),
    "step_din_rail": PartCatalogEntry(
        ref="step_din_rail",
        description="Standard DIN rail mounting rail (35 mm top-hat).",
        keywords=["din rail", "rail", "导轨", "DIN导轨", "mounting rail"],
        params={},
    ),
    "step_photo_sensor": PartCatalogEntry(
        ref="step_photo_sensor",
        description="Photoelectric proximity / through-beam sensor.",
        keywords=["photo sensor", "photoelectric", "光电传感器", "sensor", "光电开关"],
        params={},
    ),
    "step_proximity_sensor": PartCatalogEntry(
        ref="step_proximity_sensor",
        description="Inductive proximity sensor (M8 / M12 cylinder type).",
        keywords=["proximity", "sensor", "接近开关", "感应器", "inductive"],
        params={},
    ),
    "step_sensor_cable": PartCatalogEntry(
        ref="step_sensor_cable",
        description="Pre-wired sensor cable with M8/M12 connector.",
        keywords=["sensor cable", "cable", "传感器线缆", "连接线", "wire"],
        params={},
    ),
    # -----------------------------------------------------------------------
    # STEP-based standard parts  (mechanical)
    # -----------------------------------------------------------------------
    "step_gripper": PartCatalogEntry(
        ref="step_gripper",
        description="Pneumatic / electric gripper assembly (full body).",
        keywords=["gripper", "夹爪", "抓手", "夹具", "grip", "clamp"],
        params={},
    ),
    "step_linear_guide": PartCatalogEntry(
        ref="step_linear_guide",
        description="Linear motion guide rail with block (LM guide).",
        keywords=["linear guide", "guide", "直线导轨", "滑轨", "LM guide"],
        params={},
    ),
    "step_push_slide": PartCatalogEntry(
        ref="step_push_slide",
        description="Pneumatic push slide / slide table actuator.",
        keywords=["push slide", "slide", "滑台", "滑台气缸", "slide table"],
        params={},
    ),
    "step_roller": PartCatalogEntry(
        ref="step_roller",
        description="Conveyor idle roller / pulley wheel.",
        keywords=["roller", "滚筒", "滚轮", "pulley", "conveyor roller"],
        params={},
    ),
    "step_vibrating_bowl": PartCatalogEntry(
        ref="step_vibrating_bowl",
        description="Vibratory bowl feeder base unit.",
        keywords=["vibrating bowl", "feeder", "振动盘", "bowl feeder", "振动送料"],
        params={},
    ),
    "step_feeder_base": PartCatalogEntry(
        ref="step_feeder_base",
        description="Linear vibratory feeder base / drive unit.",
        keywords=["feeder base", "feeder", "送料器底座", "linear feeder", "vibratory"],
        params={},
    ),
    "step_transfer_column": PartCatalogEntry(
        ref="step_transfer_column",
        description="Vertical transfer column / lifting mast.",
        keywords=["transfer column", "column", "立柱", "升降柱", "mast"],
        params={},
    ),
    "step_work_platform": PartCatalogEntry(
        ref="step_work_platform",
        description="Adjustable work platform / table top.",
        keywords=["work platform", "platform", "工作台", "平台", "table"],
        params={},
    ),
    # -----------------------------------------------------------------------
    # STEP-based standard parts  (structural)
    # -----------------------------------------------------------------------
    "step_frame_base": PartCatalogEntry(
        ref="step_frame_base",
        description="Machine frame base / chassis foundation.",
        keywords=["frame base", "frame", "机架底座", "底座", "chassis"],
        params={},
    ),
    "step_mounting_plate": PartCatalogEntry(
        ref="step_mounting_plate",
        description="Large mounting plate with hole pattern.",
        keywords=["mounting plate", "plate", "安装板", "底板", "mount"],
        params={},
    ),
    "step_small_base_plate": PartCatalogEntry(
        ref="step_small_base_plate",
        description="Compact base plate for small fixtures.",
        keywords=["small base plate", "plate", "小底板", "底板", "base"],
        params={},
    ),
    "step_cylinder_bracket": PartCatalogEntry(
        ref="step_cylinder_bracket",
        description="Bracket for mounting pneumatic cylinders.",
        keywords=["cylinder bracket", "bracket", "气缸支架", "支架", "mount"],
        params={},
    ),
    "step_roller_bracket": PartCatalogEntry(
        ref="step_roller_bracket",
        description="Bracket for mounting conveyor rollers.",
        keywords=["roller bracket", "bracket", "滚筒支架", "支架", "roller"],
        params={},
    ),
    # -----------------------------------------------------------------------
    # STEP-based standard parts  (fasteners)
    # -----------------------------------------------------------------------
    "step_bolt_m6x20": PartCatalogEntry(
        ref="step_bolt_m6x20",
        description="Hex socket head bolt M6 x 20 mm.",
        keywords=["bolt", "m6", "螺栓", "螺丝", "hex bolt"],
        params={},
    ),
    "step_bolt_m8x25": PartCatalogEntry(
        ref="step_bolt_m8x25",
        description="Hex socket head bolt M8 x 25 mm.",
        keywords=["bolt", "m8", "螺栓", "螺丝", "hex bolt"],
        params={},
    ),
    "step_hex_nut_m6": PartCatalogEntry(
        ref="step_hex_nut_m6",
        description="Hex nut M6 (DIN 934).",
        keywords=["nut", "m6", "螺母", "六角螺母", "hex nut"],
        params={},
    ),
    "step_flat_washer_m6": PartCatalogEntry(
        ref="step_flat_washer_m6",
        description="Flat washer M6 (DIN 125).",
        keywords=["washer", "m6", "垫圈", "平垫", "flat washer"],
        params={},
    ),
    # -----------------------------------------------------------------------
    # STEP-based standard parts  (conveyor)
    # -----------------------------------------------------------------------
    "step_cable_tray_channel": PartCatalogEntry(
        ref="step_cable_tray_channel",
        description="Cable tray / wire duct channel section.",
        keywords=["cable tray", "channel", "线槽", "电缆桥架", "wire duct"],
        params={},
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
