"""
Template library for common automation station configurations.
Each template is a pre-validated assembly intent that LLM can instantiate.
"""

from typing import Dict, List, Any, Tuple
from .ontology import PartSpec, PartType, Relation, RelationType, get_defaults


def merge_defaults(user_params: Dict[str, Any], part_type: PartType) -> Dict[str, Any]:
    """Merge user params over defaults."""
    defaults = get_defaults(part_type)
    defaults.update(user_params)
    return defaults


class VibrationFeederTemplate:
    """
    Template: Vibration bowl feeder with hopper.
    Includes: bowl, spiral track, hopper, hopper support.
    All parts reference a shared base plate by name.
    """
    @staticmethod
    def create(name_prefix: str = "vib", params: Dict[str, Any] = None,
               base_name: str = "base_plate") -> Tuple[List[PartSpec], List[Relation]]:
        p = params or {}
        bowl_dia = p.get("bowl_diameter", 200)
        bowl_h = p.get("bowl_height", 30)
        hopper_h = p.get("hopper_height", 100)
        support_h = p.get("support_height", 80)
        pos_x = p.get("x", 650)
        pos_y = p.get("y", 100)

        bowl = PartSpec(name=f"{name_prefix}_bowl", part_type=PartType.VIBRATION_BOWL)
        bowl.params = merge_defaults({"diameter": bowl_dia, "height": bowl_h, "x": pos_x, "y": pos_y}, PartType.VIBRATION_BOWL)

        track = PartSpec(name=f"{name_prefix}_track", part_type=PartType.LINEAR_TRACK)
        track.params = {"width": 20, "depth": 10, "length": 150, "x": pos_x - 120, "y": pos_y}

        hopper = PartSpec(name=f"{name_prefix}_hopper", part_type=PartType.HOPPER)
        # No x,y — will inherit from support via SUPPORTED_BY
        hopper.params = merge_defaults({"height": hopper_h}, PartType.HOPPER)

        support = PartSpec(name=f"{name_prefix}_support", part_type=PartType.HOPPER_SUPPORT)
        support.params = merge_defaults({"height": support_h, "x": pos_x + 30, "y": pos_y - 50}, PartType.HOPPER_SUPPORT)

        parts = [bowl, track, hopper, support]
        relations = [
            Relation(RelationType.SUPPORTED_BY, bowl.name, base_name),
            Relation(RelationType.SUPPORTED_BY, track.name, base_name),
            Relation(RelationType.CONNECTED_TO, bowl.name, track.name),
            Relation(RelationType.SUPPORTED_BY, support.name, base_name),
            Relation(RelationType.SUPPORTED_BY, hopper.name, support.name),
            Relation(RelationType.ALIGNED_CENTER, support.name, bowl.name, "x"),
            Relation(RelationType.ALIGNED_CENTER, support.name, bowl.name, "y"),
        ]
        return parts, relations


class GantryPickPlaceTemplate:
    """
    Template: Gantry-based pick-and-place mechanism.
    Includes: gantry (composite), horizontal cylinder, slider,
              vertical cylinder, gripper, gripper jaws.
    """
    @staticmethod
    def create(name_prefix: str = "gantry", params: Dict[str, Any] = None,
               base_name: str = "base_plate") -> Tuple[List[PartSpec], List[Relation]]:
        p = params or {}
        span = p.get("span", 300)
        col_height = p.get("column_height", 250)
        beam_h = p.get("beam_height", 30)
        h_stroke = p.get("horizontal_stroke", 200)
        v_stroke = p.get("vertical_stroke", 100)
        gripper_span = p.get("gripper_span", 20)
        pos_x = p.get("x", 400)
        pos_y = p.get("y", 250)

        # Gantry composite
        gantry = PartSpec(name=f"{name_prefix}", part_type=PartType.GANTRY)
        gantry.params = {
            "span": span,
            "height": col_height,
            "beam_height": beam_h,
            "column_size": 30,
            "beam_width": span + 50,
            "x": pos_x,
            "y": pos_y,
        }

        # Horizontal drive
        horiz_cyl = PartSpec(name=f"{name_prefix}_horiz_cyl", part_type=PartType.CYLINDER)
        horiz_cyl.params = merge_defaults({
            "body_length": h_stroke + 40,
            "stroke": h_stroke,
            "body_dia": 25,
            "x": pos_x,
            "y": pos_y,
        }, PartType.CYLINDER)

        horiz_slider = PartSpec(name=f"{name_prefix}_horiz_slider", part_type=PartType.SLIDER)
        horiz_slider.params = {"width": 40, "depth": 40, "height": 30, "x": pos_x, "y": pos_y}

        # Vertical cylinder
        vert_cyl = PartSpec(name=f"{name_prefix}_vert_cyl", part_type=PartType.CYLINDER)
        vert_cyl.params = merge_defaults({
            "body_length": v_stroke + 40,
            "stroke": v_stroke,
            "body_dia": 20,
            "x": pos_x,
            "y": pos_y,
        }, PartType.CYLINDER)

        # Gripper
        gripper = PartSpec(name=f"{name_prefix}_gripper", part_type=PartType.GRIPPER)
        gripper.params = merge_defaults({"body_width": 40, "body_depth": 25, "body_height": 20, "x": pos_x, "y": pos_y}, PartType.GRIPPER)

        jaw_l = PartSpec(name=f"{name_prefix}_jaw_l", part_type=PartType.GRIPPER_JAW)
        jaw_l.params = merge_defaults({"width": 8, "depth": 15, "height": 20, "gap": gripper_span, "x": pos_x - gripper_span/2 - 4, "y": pos_y}, PartType.GRIPPER_JAW)

        jaw_r = PartSpec(name=f"{name_prefix}_jaw_r", part_type=PartType.GRIPPER_JAW)
        jaw_r.params = merge_defaults({"width": 8, "depth": 15, "height": 20, "gap": gripper_span, "x": pos_x + gripper_span/2 + 4, "y": pos_y}, PartType.GRIPPER_JAW)

        parts = [gantry, horiz_cyl, horiz_slider, vert_cyl, gripper, jaw_l, jaw_r]
        relations = [
            # Gantry on base (handled by composite expansion)
            Relation(RelationType.SUPPORTED_BY, f"{gantry.name}_left_col", base_name),
            Relation(RelationType.SUPPORTED_BY, f"{gantry.name}_right_col", base_name),
            # Horizontal cylinder on beam
            Relation(RelationType.MOUNTED_ON, horiz_cyl.name, f"{gantry.name}_beam"),
            Relation(RelationType.ALIGNED_CENTER, horiz_cyl.name, f"{gantry.name}_beam", "y"),
            # Slider driven by horizontal cylinder
            Relation(RelationType.DRIVES, horiz_cyl.name, horiz_slider.name),
            Relation(RelationType.MOUNTED_ON, horiz_slider.name, f"{gantry.name}_beam"),
            # Vertical cylinder on slider
            Relation(RelationType.MOUNTED_ON, vert_cyl.name, horiz_slider.name),
            # Gripper on vertical cylinder
            Relation(RelationType.MOUNTED_ON, gripper.name, vert_cyl.name),
            Relation(RelationType.ALIGNED_CENTER, gripper.name, vert_cyl.name, "x"),
            Relation(RelationType.ALIGNED_CENTER, gripper.name, vert_cyl.name, "y"),
            # Jaws on gripper
            Relation(RelationType.MOUNTED_ON, jaw_l.name, gripper.name),
            Relation(RelationType.MOUNTED_ON, jaw_r.name, gripper.name),
            Relation(RelationType.CLEARANCE, jaw_l.name, jaw_r.name, 5),
        ]
        return parts, relations


class FixtureStationTemplate:
    """
    Template: Part fixture/locating station.
    Includes: fixture base, fixture plate, optional push cylinder.
    """
    @staticmethod
    def create(name_prefix: str = "fix", params: Dict[str, Any] = None,
               base_name: str = "base_plate") -> Tuple[List[PartSpec], List[Relation]]:
        p = params or {}
        fx = p.get("x", 150)
        fy = p.get("y", 350)

        base = PartSpec(name=f"{name_prefix}_base", part_type=PartType.FIXTURE)
        base.params = merge_defaults({"width": 100, "depth": 100, "height": 50, "x": fx, "y": fy}, PartType.FIXTURE)

        plate = PartSpec(name=f"{name_prefix}_plate", part_type=PartType.FIXTURE_PLATE)
        plate.params = merge_defaults({"width": 80, "depth": 80, "thickness": 10, "x": fx, "y": fy}, PartType.FIXTURE_PLATE)

        parts = [base, plate]
        relations = [
            Relation(RelationType.SUPPORTED_BY, base.name, base_name),
            Relation(RelationType.SUPPORTED_BY, plate.name, base.name),
            Relation(RelationType.ALIGNED_CENTER, plate.name, base.name, "x"),
            Relation(RelationType.ALIGNED_CENTER, plate.name, base.name, "y"),
        ]

        if p.get("has_push_cylinder", False):
            push_cyl = PartSpec(name=f"{name_prefix}_push_cyl", part_type=PartType.CYLINDER)
            push_cyl.params = merge_defaults({"body_length": 80, "stroke": 50, "body_dia": 16, "x": fx - 60, "y": fy}, PartType.CYLINDER)
            parts.append(push_cyl)
            relations.append(Relation(RelationType.MOUNTED_ON, push_cyl.name, base_name))

        return parts, relations


class FullStationTemplate:
    """
    Template: Complete pick-and-place station.
    Combines vibration feeder + gantry pick-place + fixture station on shared base.
    """
    @staticmethod
    def create(params: Dict[str, Any] = None) -> Tuple[List[PartSpec], List[Relation]]:
        p = params or {}
        station_w = p.get("station_width", 800)
        station_d = p.get("station_depth", 500)

        parts = []
        relations = []

        # Shared base plate
        base = PartSpec(name="base_plate", part_type=PartType.BASE_PLATE)
        base.params = {"width": station_w, "depth": station_d, "thickness": 15}
        parts.append(base)

        # Vibration feeder at right-rear
        vib_x = p.get("vib_x", station_w - 150)
        vib_y = p.get("vib_y", 100)
        vib_parts, vib_rels = VibrationFeederTemplate.create("vib", {
            "x": vib_x, "y": vib_y,
            "bowl_diameter": p.get("bowl_diameter", 200),
        }, base_name="base_plate")
        parts.extend(vib_parts)
        relations.extend(vib_rels)

        # Gantry at center
        gantry_x = p.get("gantry_x", station_w / 2)
        gantry_y = p.get("gantry_y", station_d / 2)
        gantry_parts, gantry_rels = GantryPickPlaceTemplate.create("gantry", {
            "x": gantry_x, "y": gantry_y,
            "span": p.get("gantry_span", 300),
            "column_height": p.get("gantry_height", 250),
            "vertical_stroke": p.get("vertical_stroke", 120),
            "horizontal_stroke": p.get("horizontal_stroke", 250),
            "gripper_span": p.get("gripper_span", 20),
        }, base_name="base_plate")
        parts.extend(gantry_parts)
        relations.extend(gantry_rels)

        # Fixture station at left-front
        fix_x = p.get("fix_x", 150)
        fix_y = p.get("fix_y", station_d - 100)
        fix_parts, fix_rels = FixtureStationTemplate.create("fix", {
            "x": fix_x, "y": fix_y,
            "has_push_cylinder": p.get("fix_has_push", True),
        }, base_name="base_plate")
        parts.extend(fix_parts)
        relations.extend(fix_rels)

        # Global reachability relations
        relations.append(Relation(RelationType.REACHES, "gantry_gripper", "vib_bowl"))
        relations.append(Relation(RelationType.REACHES, "gantry_gripper", "fix_plate"))
        relations.append(Relation(RelationType.CLEARANCE, "gantry", "vib_bowl", 30))

        return parts, relations
