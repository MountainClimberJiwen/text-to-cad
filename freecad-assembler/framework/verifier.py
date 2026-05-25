"""
Verifier: post-hoc geometric verification of solved assembly.
Checks contacts, clearances, interferences, structural stability.
"""

from typing import Dict, List, Tuple, Optional, Set
from dataclasses import dataclass, field
from .solver import BoundingBox
from .ontology import AssemblyIntent, RelationType


@dataclass
class Violation:
    severity: str   # "CRITICAL", "WARNING", "INFO"
    rule_id: str
    message: str
    parts_involved: List[str] = field(default_factory=list)


class AssemblyVerifier:
    def __init__(self, boxes: Dict[str, BoundingBox], intent: Optional[AssemblyIntent] = None):
        self.boxes = boxes
        self.violations: List[Violation] = []
        self.intent = intent
        # Build relation lookup: (a,b) -> set of RelationType
        self._rel_map: Dict[Tuple[str, str], Set[RelationType]] = {}
        if intent:
            for rel in intent.relations:
                key = tuple(sorted([rel.source, rel.target]))
                if key not in self._rel_map:
                    self._rel_map[key] = set()
                self._rel_map[key].add(rel.rel_type)

    def verify_all(self) -> List[Violation]:
        self.check_all_contacts()
        self.check_interferences()
        self.check_proportions()
        self.check_visibility()
        self.check_structural_stability()
        return self.violations

    def check_all_contacts(self):
        """Verify that parts claiming to touch actually do."""
        # Heuristic: parts with similar z-positions that should stack
        names = list(self.boxes.keys())
        for i, name_a in enumerate(names):
            for name_b in names[i+1:]:
                box_a = self.boxes[name_a]
                box_b = self.boxes[name_b]

                # Check Z contact (stacking)
                z_gap = abs(box_a.bottom - box_b.top)
                z_overlap_x = min(box_a.right, box_b.right) - max(box_a.left, box_b.left)
                z_overlap_y = min(box_a.back, box_b.back) - max(box_a.front, box_b.front)
                if z_gap < 2.0 and z_overlap_x > 1 and z_overlap_y > 1:
                    # Valid contact
                    pass
                elif z_gap < 10 and z_overlap_x > 1 and z_overlap_y > 1:
                    # Suspicious gap
                    self.violations.append(Violation(
                        severity="WARNING",
                        rule_id="CONTACT_GAP",
                        message=f"{name_a} and {name_b} have gap {z_gap:.1f}mm in Z but may intend to touch",
                        parts_involved=[name_a, name_b],
                    ))

    def check_interferences(self):
        """Detect parts that collide/overlap (not supposed to touch)."""
        names = list(self.boxes.keys())
        for i, name_a in enumerate(names):
            for name_b in names[i+1:]:
                box_a = self.boxes[name_a]
                box_b = self.boxes[name_b]

                # Skip if they are supposed to touch (parent-child or explicit contact)
                if self._likely_connected(name_a, name_b):
                    continue

                overlap_x = min(box_a.right, box_b.right) - max(box_a.left, box_b.left)
                overlap_y = min(box_a.back, box_b.back) - max(box_a.front, box_b.front)
                overlap_z = min(box_a.top, box_b.top) - max(box_a.bottom, box_b.bottom)

                if overlap_x > 1 and overlap_y > 1 and overlap_z > 1:
                    overlap_vol = overlap_x * overlap_y * overlap_z
                    self.violations.append(Violation(
                        severity="CRITICAL",
                        rule_id="INTERFERENCE",
                        message=f"{name_a} intersects {name_b}: overlap volume {overlap_vol:.0f} mm³",
                        parts_involved=[name_a, name_b],
                    ))

    def _likely_connected(self, name_a: str, name_b: str) -> bool:
        """Heuristic: parts with same prefix or parent-child naming are connected.
        Also respects explicit relations from the AssemblyIntent."""
        # 1) Explicit intent relations (strongest signal)
        key = tuple(sorted([name_a, name_b]))
        if key in self._rel_map:
            rel_types = self._rel_map[key]
            # These relation types intentionally involve physical contact/proximity
            if rel_types & {
                RelationType.SUPPORTED_BY,
                RelationType.MOUNTED_ON,
                RelationType.GUIDES,
                RelationType.DRIVES,
                RelationType.CONNECTED_TO,
            }:
                return True

        # 2) Base plate supports everything
        if any("base_plate" in n for n in [name_a, name_b]):
            return True

        # 3) Column + any part mounted above it (weak heuristic)
        na = name_a.lower()
        nb = name_b.lower()
        if ("column" in na or "support" in na) and ("cyl" in nb or "gripper" in nb or "guide" in nb):
            return True
        if ("column" in nb or "support" in nb) and ("cyl" in na or "gripper" in na or "guide" in na):
            return True

        # 4) Gantry / transfer system parts (central stacked assembly)
        central_parts = ["transfer", "gripper", "gantry"]
        if any(cp in na for cp in central_parts) and any(cp in nb for cp in central_parts):
            return True

        # 5) Same functional subsystem (left/right/center side)
        if ("left" in na and "left" in nb) or ("right" in na and "right" in nb):
            # But not if they're clearly different types that shouldn't overlap
            pass  # keep going to other heuristics

        # 6) Parent-child naming patterns
        if name_a in name_b or name_b in name_a:
            return True

        # 7) Same station prefix (first word)
        prefixes_a = name_a.split("_")
        prefixes_b = name_b.split("_")
        if len(prefixes_a) > 1 and len(prefixes_b) > 1:
            if prefixes_a[0] == prefixes_b[0] and len(prefixes_a[0]) > 2:
                return True

        return False

    def check_proportions(self):
        """Check that parts have reasonable relative sizes."""
        base_box = None
        for name, box in self.boxes.items():
            if "base_plate" in name:
                base_box = box
                break

        if base_box is None:
            return

        base_vol = base_box.volume()

        for name, box in self.boxes.items():
            vol = box.volume()
            ratio = vol / base_vol

            # Very small parts (likely invisible)
            if ratio < 0.0005 and vol > 0:
                self.violations.append(Violation(
                    severity="WARNING",
                    rule_id="TOO_SMALL",
                    message=f"{name} volume ratio {ratio:.4f} (< 0.05%) may be invisible in render",
                    parts_involved=[name],
                ))

            # Very large parts (larger than base)
            if ratio > 1.5:
                self.violations.append(Violation(
                    severity="CRITICAL",
                    rule_id="TOO_LARGE",
                    message=f"{name} volume ratio {ratio:.1f}x base plate -- likely incorrect scale",
                    parts_involved=[name],
                ))

    def check_visibility(self):
        """Check that critical parts are large enough to be seen."""
        critical_types = ["jaw", "guide", "sensor", "piston"]
        for name, box in self.boxes.items():
            if any(ct in name.lower() for ct in critical_types):
                min_dim = min(box.w, box.d, box.h)
                if min_dim < 3:
                    self.violations.append(Violation(
                        severity="WARNING",
                        rule_id="NOT_VISIBLE",
                        message=f"{name} min dimension {min_dim:.1f}mm -- likely invisible",
                        parts_involved=[name],
                    ))

    def check_structural_stability(self):
        """Check that gantry beams are actually supported."""
        # Find gantry beams
        gantry_beams = [n for n in self.boxes if "gantry" in n and "beam" in n]
        for beam_name in gantry_beams:
            beam = self.boxes[beam_name]
            # Find columns that support it
            cols = [n for n in self.boxes if "gantry" in n and "col" in n]
            supported = False
            for col_name in cols:
                col = self.boxes[col_name]
                if abs(beam.bottom - col.top) < 2:
                    # Check X overlap
                    overlap_x = min(beam.right, col.right) - max(beam.left, col.left)
                    if overlap_x > 5:
                        supported = True
                        break
            if not supported:
                self.violations.append(Violation(
                    severity="CRITICAL",
                    rule_id="NO_SUPPORT",
                    message=f"{beam_name} is not supported by any column (gap > 2mm)",
                    parts_involved=[beam_name] + cols,
                ))

    def print_report(self):
        """Print human-readable verification report."""
        critical = [v for v in self.violations if v.severity == "CRITICAL"]
        warnings = [v for v in self.violations if v.severity == "WARNING"]
        infos = [v for v in self.violations if v.severity == "INFO"]

        print("=" * 60)
        print(f"VERIFICATION REPORT: {len(critical)} CRITICAL, {len(warnings)} WARNING, {len(infos)} INFO")
        print("=" * 60)

        if critical:
            print("\n🔴 CRITICAL (must fix):")
            for v in critical:
                print(f"  [{v.rule_id}] {v.message}")

        if warnings:
            print("\n🟡 WARNING (should fix):")
            for v in warnings:
                print(f"  [{v.rule_id}] {v.message}")

        if infos:
            print("\n🟢 INFO:")
            for v in infos:
                print(f"  [{v.rule_id}] {v.message}")

        print("=" * 60)
        return len(critical) == 0
