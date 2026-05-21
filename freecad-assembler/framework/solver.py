"""
Lightweight constraint solver for assembly coordinates.
No external SMT solver needed -- pure Python algebraic propagation.
"""

from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from .ontology import AssemblyIntent, PartSpec, Relation, RelationType, PartType, ENGINEERING_RULES


@dataclass
class BoundingBox:
    """3D bounding box with center and dimensions."""
    cx: float = 0.0
    cy: float = 0.0
    cz: float = 0.0
    w: float = 0.0   # width (x-axis)
    d: float = 0.0   # depth (y-axis)
    h: float = 0.0   # height (z-axis)

    @property
    def left(self) -> float:
        return self.cx - self.w / 2

    @property
    def right(self) -> float:
        return self.cx + self.w / 2

    @property
    def front(self) -> float:
        return self.cy - self.d / 2

    @property
    def back(self) -> float:
        return self.cy + self.d / 2

    @property
    def bottom(self) -> float:
        return self.cz - self.h / 2

    @property
    def top(self) -> float:
        return self.cz + self.h / 2

    def volume(self) -> float:
        return self.w * self.d * self.h

    def touches(self, other: "BoundingBox", axis: str = "z", tolerance: float = 0.1) -> bool:
        """Check if two boxes touch on the given axis face."""
        if axis == "z":
            gap = abs(self.bottom - other.top)
            overlap_x = min(self.right, other.right) - max(self.left, other.left)
            overlap_y = min(self.back, other.back) - max(self.front, other.front)
            return gap < tolerance and overlap_x > 0 and overlap_y > 0
        if axis == "y":
            gap = abs(self.front - other.back)
            overlap_x = min(self.right, other.right) - max(self.left, other.left)
            overlap_z = min(self.top, other.top) - max(self.bottom, other.bottom)
            return gap < tolerance and overlap_x > 0 and overlap_z > 0
        if axis == "x":
            gap = abs(self.left - other.right)
            overlap_y = min(self.back, other.back) - max(self.front, other.front)
            overlap_z = min(self.top, other.top) - max(self.bottom, other.bottom)
            return gap < tolerance and overlap_y > 0 and overlap_z > 0
        return False


class AssemblySolver:
    """Solves assembly coordinates from intent + relations."""

    def __init__(self, intent: AssemblyIntent):
        self.intent = intent
        self.boxes: Dict[str, BoundingBox] = {}
        self.solved = False
        self.errors: List[str] = []
        self._reported_violations: set = set()  # dedup contact violations

    def _get_param(self, part: PartSpec, key: str, default: float = 0.0) -> float:
        return float(part.params.get(key, default))

    def _init_boxes(self):
        """Initialize bounding boxes from part specs."""
        for part in self.intent.parts:
            if part.part_type == PartType.BASE_PLATE:
                self.boxes[part.name] = BoundingBox(
                    cx=self._get_param(part, "width", 800) / 2,
                    cy=self._get_param(part, "depth", 500) / 2,
                    cz=self._get_param(part, "thickness", 15) / 2,
                    w=self._get_param(part, "width", 800),
                    d=self._get_param(part, "depth", 500),
                    h=self._get_param(part, "thickness", 15),
                )
            elif part.part_type == PartType.COLUMN:
                self.boxes[part.name] = BoundingBox(
                    cx=self._get_param(part, "x", 0),
                    cy=self._get_param(part, "y", 0),
                    w=self._get_param(part, "width", 30),
                    d=self._get_param(part, "depth", 30),
                    h=self._get_param(part, "height", 250),
                )
            elif part.part_type == PartType.BEAM:
                self.boxes[part.name] = BoundingBox(
                    cx=self._get_param(part, "x", 0),
                    cy=self._get_param(part, "y", 0),
                    w=self._get_param(part, "width", 300),
                    d=self._get_param(part, "depth", 30),
                    h=self._get_param(part, "height", 30),
                )
            elif part.part_type == PartType.GANTRY:
                # Composite: expand into sub-parts later
                span = self._get_param(part, "span", 300)
                col_size = self._get_param(part, "column_size", 30)
                height = self._get_param(part, "height", 250)
                beam_h = self._get_param(part, "beam_height", 30)
                self.boxes[part.name] = BoundingBox(
                    cx=self._get_param(part, "x", 0),
                    cy=self._get_param(part, "y", 0),
                    w=span + col_size,
                    d=col_size,
                    h=height + beam_h,
                )
                # Store sub-part params for expansion
                part.params["_sub_left"] = f"{part.name}_left_col"
                part.params["_sub_right"] = f"{part.name}_right_col"
                part.params["_sub_beam"] = f"{part.name}_beam"
            elif part.part_type == PartType.VIBRATION_BOWL:
                dia = self._get_param(part, "diameter", 200)
                h = self._get_param(part, "height", 30)
                self.boxes[part.name] = BoundingBox(
                    cx=self._get_param(part, "x", 0),
                    cy=self._get_param(part, "y", 0),
                    w=dia, d=dia, h=h)
            elif part.part_type == PartType.HOPPER:
                tw = self._get_param(part, "top_width", 120)
                td = self._get_param(part, "top_depth", 120)
                h = self._get_param(part, "height", 100)
                self.boxes[part.name] = BoundingBox(
                    cx=self._get_param(part, "x", 0),
                    cy=self._get_param(part, "y", 0),
                    w=tw, d=td, h=h)
            elif part.part_type == PartType.HOPPER_SUPPORT:
                w = self._get_param(part, "width", 20)
                d = self._get_param(part, "depth", 20)
                h = self._get_param(part, "height", 100)
                self.boxes[part.name] = BoundingBox(
                    cx=self._get_param(part, "x", 0),
                    cy=self._get_param(part, "y", 0),
                    w=w, d=d, h=h)
            elif part.part_type == PartType.CYLINDER:
                bl = self._get_param(part, "body_length", 120)
                bd = self._get_param(part, "body_dia", 25)
                self.boxes[part.name] = BoundingBox(
                    cx=self._get_param(part, "x", 0),
                    cy=self._get_param(part, "y", 0),
                    w=bd, d=bd, h=bl)
            elif part.part_type == PartType.GUIDE_RAIL:
                w = self._get_param(part, "width", 10)
                d = self._get_param(part, "depth", 15)
                h = self._get_param(part, "height", 120)
                self.boxes[part.name] = BoundingBox(
                    cx=self._get_param(part, "x", 0),
                    cy=self._get_param(part, "y", 0),
                    w=w, d=d, h=h)
            elif part.part_type == PartType.GRIPPER:
                w = self._get_param(part, "body_width", 40)
                d = self._get_param(part, "body_depth", 25)
                h = self._get_param(part, "body_height", 20)
                self.boxes[part.name] = BoundingBox(
                    cx=self._get_param(part, "x", 0),
                    cy=self._get_param(part, "y", 0),
                    w=w, d=d, h=h)
            elif part.part_type == PartType.GRIPPER_JAW:
                w = self._get_param(part, "width", 8)
                d = self._get_param(part, "depth", 15)
                h = self._get_param(part, "height", 20)
                self.boxes[part.name] = BoundingBox(
                    cx=self._get_param(part, "x", 0),
                    cy=self._get_param(part, "y", 0),
                    w=w, d=d, h=h)
            elif part.part_type == PartType.FIXTURE:
                w = self._get_param(part, "width", 80)
                d = self._get_param(part, "depth", 80)
                h = self._get_param(part, "height", 40)
                self.boxes[part.name] = BoundingBox(
                    cx=self._get_param(part, "x", 0),
                    cy=self._get_param(part, "y", 0),
                    w=w, d=d, h=h)
            elif part.part_type == PartType.FIXTURE_PLATE:
                w = self._get_param(part, "width", 60)
                d = self._get_param(part, "depth", 60)
                h = self._get_param(part, "thickness", 10)
                self.boxes[part.name] = BoundingBox(
                    cx=self._get_param(part, "x", 0),
                    cy=self._get_param(part, "y", 0),
                    w=w, d=d, h=h)
            elif part.part_type == PartType.SLIDER:
                w = self._get_param(part, "width", 30)
                d = self._get_param(part, "depth", 30)
                h = self._get_param(part, "height", 20)
                self.boxes[part.name] = BoundingBox(
                    cx=self._get_param(part, "x", 0),
                    cy=self._get_param(part, "y", 0),
                    w=w, d=d, h=h)
            elif part.part_type == PartType.PISTON:
                dia = self._get_param(part, "diameter", 12)
                length = self._get_param(part, "length", 80)
                self.boxes[part.name] = BoundingBox(
                    cx=self._get_param(part, "x", 0),
                    cy=self._get_param(part, "y", 0),
                    w=dia, d=dia, h=length)
            elif part.part_type == PartType.LINEAR_TRACK:
                w = self._get_param(part, "width", 20)
                d = self._get_param(part, "depth", 10)
                length = self._get_param(part, "length", 200)
                self.boxes[part.name] = BoundingBox(
                    cx=self._get_param(part, "x", 0),
                    cy=self._get_param(part, "y", 0),
                    w=w, d=d, h=length)
            elif part.part_type == PartType.SENSOR:
                w = self._get_param(part, "width", 20)
                d = self._get_param(part, "depth", 10)
                h = self._get_param(part, "height", 15)
                self.boxes[part.name] = BoundingBox(
                    cx=self._get_param(part, "x", 0),
                    cy=self._get_param(part, "y", 0),
                    w=w, d=d, h=h)
            elif part.part_type == PartType.MOTOR:
                w = self._get_param(part, "width", 60)
                d = self._get_param(part, "depth", 60)
                h = self._get_param(part, "height", 80)
                self.boxes[part.name] = BoundingBox(
                    cx=self._get_param(part, "x", 0),
                    cy=self._get_param(part, "y", 0),
                    w=w, d=d, h=h)
            else:
                self.boxes[part.name] = BoundingBox(w=50, d=50, h=50)

    def _apply_rules(self):
        """Apply engineering rules to adjust parameters before solving."""
        base_plate = None
        for part in self.intent.parts:
            if part.part_type == PartType.BASE_PLATE:
                base_plate = part
                break

        if base_plate is None:
            self.errors.append("No base plate found")
            return

        bp_vol = base_plate.params.get("width", 800) * base_plate.params.get("depth", 500) * base_plate.params.get("thickness", 15)

        for part in self.intent.parts:
            # RULE_VIB_BOWL_001: bowl diameter <= 40% of base plate width
            if part.part_type == PartType.VIBRATION_BOWL:
                max_dia = base_plate.params.get("width", 800) * 0.4
                if part.params.get("diameter", 200) > max_dia:
                    part.params["diameter"] = max_dia
                    self.errors.append(f"RULE_VIB_BOWL_001: reduced {part.name} diameter to {max_dia}")

            # RULE_GRIPPER_001: jaw volume >= 0.1% of base plate
            if part.part_type == PartType.GRIPPER_JAW:
                jaw_w = part.params.get("width", 8)
                jaw_d = part.params.get("depth", 15)
                jaw_h = part.params.get("height", 20)
                jaw_vol = jaw_w * jaw_d * jaw_h
                min_vol = bp_vol * 0.001
                if jaw_vol < min_vol:
                    scale = (min_vol / jaw_vol) ** (1/3)
                    part.params["width"] = jaw_w * scale
                    part.params["depth"] = jaw_d * scale
                    part.params["height"] = jaw_h * scale
                    self.errors.append(f"RULE_GRIPPER_001: scaled {part.name} by {scale:.2f}x for visibility")

            # RULE_CYLINDER_001: long stroke needs guide
            if part.part_type == PartType.CYLINDER:
                stroke = part.params.get("stroke", 100)
                if stroke > 50:
                    # Check if guide exists in relations
                    has_guide = any(
                        r.rel_type == RelationType.GUIDES and r.target == part.name
                        for r in self.intent.relations
                    )
                    if not has_guide:
                        # Auto-add guide rail relation
                        guide_name = f"{part.name}_guide"
                        guide_part = PartSpec(name=guide_name, part_type=PartType.GUIDE_RAIL)
                        guide_part.params = {
                            "width": 10,
                            "depth": 15,
                            "height": part.params.get("body_length", 120) * 1.2,
                        }
                        self.intent.parts.append(guide_part)
                        self.intent.relations.append(Relation(
                            rel_type=RelationType.GUIDES,
                            source=guide_name,
                            target=part.name,
                        ))
                        self.errors.append(f"RULE_CYLINDER_001: auto-added guide rail for {part.name}")

            # RULE_COLUMN_001: column height >= 8 * beam thickness
            if part.part_type == PartType.COLUMN:
                # Find supported beam
                for rel in self.intent.relations:
                    if rel.rel_type == RelationType.SUPPORTED_BY and rel.source == part.name:
                        beam = next((p for p in self.intent.parts if p.name == rel.target), None)
                        if beam and beam.part_type == PartType.BEAM:
                            beam_thick = beam.params.get("height", 30)
                            min_h = beam_thick * 8
                            if part.params.get("height", 250) < min_h:
                                part.params["height"] = min_h
                                self.errors.append(f"RULE_COLUMN_001: increased {part.name} height to {min_h}")

    def _expand_composites(self):
        """Expand composite parts (like GANTRY) into concrete sub-parts."""
        new_parts = []
        new_relations = []
        to_remove = []

        for part in self.intent.parts:
            if part.part_type == PartType.GANTRY:
                span = part.params.get("span", 300)
                col_size = part.params.get("column_size", 30)
                height = part.params.get("height", 250)
                beam_h = part.params.get("beam_height", 30)
                beam_w = part.params.get("beam_width", span + col_size + 20)

                gx = part.params.get("x", 0)
                gy = part.params.get("y", 0)

                left_col = PartSpec(
                    name=f"{part.name}_left_col",
                    part_type=PartType.COLUMN,
                    parent=part.name,
                )
                left_col.params = {"width": col_size, "depth": col_size, "height": height, "x": gx - span/2, "y": gy}

                right_col = PartSpec(
                    name=f"{part.name}_right_col",
                    part_type=PartType.COLUMN,
                    parent=part.name,
                )
                right_col.params = {"width": col_size, "depth": col_size, "height": height, "x": gx + span/2, "y": gy}

                beam = PartSpec(
                    name=f"{part.name}_beam",
                    part_type=PartType.BEAM,
                    parent=part.name,
                )
                beam.params = {"width": beam_w, "depth": col_size, "height": beam_h, "x": gx, "y": gy}

                new_parts.extend([left_col, right_col, beam])

                # Internal relations
                new_relations.append(Relation(
                    rel_type=RelationType.SUPPORTED_BY,
                    source=left_col.name,
                    target="base_plate",
                ))
                new_relations.append(Relation(
                    rel_type=RelationType.SUPPORTED_BY,
                    source=right_col.name,
                    target="base_plate",
                ))
                new_relations.append(Relation(
                    rel_type=RelationType.SUPPORTED_BY,
                    source=beam.name,
                    target=left_col.name,
                ))
                new_relations.append(Relation(
                    rel_type=RelationType.SUPPORTED_BY,
                    source=beam.name,
                    target=right_col.name,
                ))
                new_relations.append(Relation(
                    rel_type=RelationType.ALIGNED_CENTER,
                    source=beam.name,
                    target=left_col.name,
                    axis="y",
                ))
                new_relations.append(Relation(
                    rel_type=RelationType.ALIGNED_CENTER,
                    source=beam.name,
                    target=right_col.name,
                    axis="y",
                ))

                to_remove.append(part)

        for p in to_remove:
            self.intent.parts.remove(p)
        self.intent.parts.extend(new_parts)
        self.intent.relations.extend(new_relations)

    def _solve_positions(self):
        """Propagate coordinates from relations."""
        # Find base plate as anchor
        base_name = None
        for part in self.intent.parts:
            if part.part_type == PartType.BASE_PLATE:
                base_name = part.name
                box = self.boxes[part.name]
                box.cx = box.w / 2
                box.cy = box.d / 2
                box.cz = box.h / 2
                break

        if base_name is None:
            self.errors.append("No base plate to anchor coordinates")
            return

        # Iteratively solve until no more progress
        solved_names = {base_name}
        max_iter = 50

        for _ in range(max_iter):
            progress = False

            for rel in self.intent.relations:
                src = rel.source
                tgt = rel.target

                if src not in self.boxes or tgt not in self.boxes:
                    continue

                src_box = self.boxes[src]
                tgt_box = self.boxes[tgt]

                # SUPPORTED_BY: source sits on top of target
                if rel.rel_type == RelationType.SUPPORTED_BY:
                    if tgt in solved_names:
                        if src not in solved_names:
                            # Source bottom touches target top
                            src_box.cz = tgt_box.top + src_box.h / 2
                            # Only align XY if not already positioned
                            if abs(src_box.cx) < 0.1 and abs(src_box.cy) < 0.1:
                                src_box.cx = tgt_box.cx
                                src_box.cy = tgt_box.cy
                            solved_names.add(src)
                            progress = True
                        else:
                            # Already solved, verify contact
                            gap = abs(src_box.bottom - tgt_box.top)
                            if gap > 0.1:
                                key = f"CONTACT:{src}:{tgt}"
                                if key not in self._reported_violations:
                                    self._reported_violations.add(key)
                                    self.errors.append(f"CONTACT_VIOLATION: {src} bottom({src_box.bottom:.1f}) != {tgt} top({tgt_box.top:.1f}), gap={gap:.1f}")

                # MOUNTED_ON: same as SUPPORTED_BY
                elif rel.rel_type == RelationType.MOUNTED_ON:
                    if tgt in solved_names and src not in solved_names:
                        src_box.cz = tgt_box.top + src_box.h / 2
                        if abs(src_box.cx) < 0.1 and abs(src_box.cy) < 0.1:
                            src_box.cx = tgt_box.cx
                            src_box.cy = tgt_box.cy
                        solved_names.add(src)
                        progress = True

                # ALIGNED_CENTER
                elif rel.rel_type == RelationType.ALIGNED_CENTER:
                    if tgt in solved_names and src in solved_names:
                        axis = rel.axis or "y"
                        if axis == "y":
                            src_box.cy = tgt_box.cy
                        elif axis == "x":
                            src_box.cx = tgt_box.cx
                        elif axis == "z":
                            src_box.cz = tgt_box.cz
                        progress = True

                # GUIDES: source is parallel and near target
                elif rel.rel_type == RelationType.GUIDES:
                    if tgt in solved_names and src not in solved_names:
                        # Place source beside target, same bottom, parallel
                        src_box.cz = tgt_box.cz
                        src_box.cy = tgt_box.cy
                        src_box.cx = tgt_box.cx + tgt_box.w/2 + src_box.w/2 + 2
                        solved_names.add(src)
                        progress = True

                # DRIVES: source drives target (e.g. piston drives slider)
                elif rel.rel_type == RelationType.DRIVES:
                    if tgt in solved_names and src not in solved_names:
                        src_box.cx = tgt_box.cx
                        src_box.cy = tgt_box.cy
                        src_box.cz = tgt_box.cz
                        solved_names.add(src)
                        progress = True

                # CLEARANCE
                elif rel.rel_type == RelationType.CLEARANCE:
                    if src in solved_names and tgt in solved_names and rel.min_dist:
                        dist = ((src_box.cx - tgt_box.cx)**2 + (src_box.cy - tgt_box.cy)**2 + (src_box.cz - tgt_box.cz)**2) ** 0.5
                        if dist < rel.min_dist:
                            self.errors.append(f"CLEARANCE_VIOLATION: {src}-{tgt} distance={dist:.1f} < min={rel.min_dist}")

            if not progress:
                break

        # Check for unsolved parts
        for part in self.intent.parts:
            if part.name not in solved_names:
                self.errors.append(f"UNSOLVED: {part.name} has no coordinate")

    def solve(self) -> Dict[str, BoundingBox]:
        """Run full solve pipeline."""
        self._apply_rules()
        self._expand_composites()
        self._init_boxes()
        self._solve_positions()
        self.solved = len([e for e in self.errors if e.startswith("UNSOLVED")]) == 0
        return self.boxes
