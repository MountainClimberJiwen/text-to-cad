#!/usr/bin/env python3
"""
verify_assembly.py — Industrial automation assembly verification script.

Checks an assembly source file for:
  1. Geometry validity of each component
  2. Interference (collision) between component pairs
  3. Minimum clearance/gap between component pairs

Inspired by FreeCAD harness "measure" + "verify" pipeline.

Usage:
    ./.venv/bin/python skills/industrial_cad/scripts/verify_assembly.py \
        models/assemblies/vibratory_feeder_assembly.py \
        --min-gap 5.0
"""

from __future__ import annotations

import argparse
import json
import math
import sys
import time
from pathlib import Path
from typing import Any

# Allow importing cad skill common modules when run from repo root.
_our_dir = Path(__file__).resolve().parent
sys.path.insert(0, str(_our_dir.parent.parent / "cad" / "scripts"))

from OCP.Bnd import Bnd_Box
from OCP.BRepBndLib import BRepBndLib
from OCP.BRepCheck import BRepCheck_Analyzer
from OCP.BRepExtrema import BRepExtrema_DistShapeShape
from OCP.BRepAlgoAPI import BRepAlgoAPI_Common
from OCP.gp import gp_Trsf

from common.assembly_spec import (
    AssemblySpec,
    AssemblyNodeSpec,
    IDENTITY_TRANSFORM,
    assembly_spec_children,
    multiply_transforms,
    read_assembly_spec,
)
from common.assembly_flatten import filesystem_entry
from common.assembly_export import (
    _load_step_shape,
    _load_step_assembly_shape,
    _step_has_assembly_artifact,
)


# ---------------------------------------------------------------------------
# OCP helpers
# ---------------------------------------------------------------------------


def _location_from_transform(transform: tuple[float, ...]):
    import build123d

    trsf = gp_Trsf()
    trsf.SetValues(
        transform[0],
        transform[1],
        transform[2],
        transform[3],
        transform[4],
        transform[5],
        transform[6],
        transform[7],
        transform[8],
        transform[9],
        transform[10],
        transform[11],
    )
    return build123d.Location(trsf)


def _get_bbox(shape) -> Bnd_Box:
    box = Bnd_Box()
    BRepBndLib.AddOptimal_s(shape.wrapped, box, False, False)
    return box


def _bbox_might_intersect(box_a: Bnd_Box, box_b: Bnd_Box, margin: float = 0.0) -> bool:
    ax1, ay1, az1, ax2, ay2, az2 = box_a.Get()
    bx1, by1, bz1, bx2, by2, bz2 = box_b.Get()
    return not (
        ax2 + margin < bx1
        or bx2 + margin < ax1
        or ay2 + margin < by1
        or by2 + margin < ay1
        or az2 + margin < bz1
        or bz2 + margin < az1
    )


def _bbox_min_gap(box_a: Bnd_Box, box_b: Bnd_Box) -> float:
    """Conservative lower-bound on distance between two shapes using their bboxes."""
    ax1, ay1, az1, ax2, ay2, az2 = box_a.Get()
    bx1, by1, bz1, bx2, by2, bz2 = box_b.Get()

    gaps = []
    # x
    if ax2 < bx1:
        gaps.append(bx1 - ax2)
    elif bx2 < ax1:
        gaps.append(ax1 - bx2)
    else:
        gaps.append(0.0)
    # y
    if ay2 < by1:
        gaps.append(by1 - ay2)
    elif by2 < ay1:
        gaps.append(ay1 - by2)
    else:
        gaps.append(0.0)
    # z
    if az2 < bz1:
        gaps.append(bz1 - az2)
    elif bz2 < az1:
        gaps.append(az1 - bz2)
    else:
        gaps.append(0.0)

    if all(g == 0.0 for g in gaps):
        return 0.0  # bboxes intersect
    return max(gaps)


def _check_geometry_validity(shape, name: str) -> tuple[bool, list[str]]:
    analyzer = BRepCheck_Analyzer(shape.wrapped)
    is_valid = analyzer.IsValid()
    issues: list[str] = []
    if not is_valid:
        # Collect specific failure reasons
        from OCP.BRepCheck import BRepCheck_ListIteratorOfListOfStatus
        from OCP.TopExp import TopExp_Explorer
        from OCP.TopAbs import TopAbs_FACE, TopAbs_EDGE, TopAbs_VERTEX

        shape_types = [(TopAbs_FACE, "face"), (TopAbs_EDGE, "edge"), (TopAbs_VERTEX, "vertex")]
        for top_abs, label in shape_types:
            explorer = TopExp_Explorer(shape.wrapped, top_abs)
            while explorer.More():
                sub_shape = explorer.Current()
                result = analyzer.Result(sub_shape)
                if result:
                    it = BRepCheck_ListIteratorOfListOfStatus(result)
                    while it.More():
                        status = it.Value()
                        issues.append(f"{label}: {status}")
                        it.Next()
                explorer.Next()
    return is_valid, issues


def _compute_exact_distance(shape_a, shape_b) -> float:
    dist = BRepExtrema_DistShapeShape(shape_a.wrapped, shape_b.wrapped)
    dist.Perform()
    if dist.IsDone():
        return float(dist.Value())
    return float("inf")


def _intersection_volume(shape_a, shape_b) -> float:
    """Compute volume of intersection between two shapes."""
    common = BRepAlgoAPI_Common(shape_a.wrapped, shape_b.wrapped)
    common.Build()
    if common.Shape().IsNull():
        return 0.0
    from OCP.BRepGProp import BRepGProp
    from OCP.GProp import GProp_GProps

    props = GProp_GProps()
    BRepGProp.VolumeProperties_s(common.Shape(), props)
    return float(props.Mass())


def _check_interference(shape_a, shape_b, volume_threshold: float = 0.1) -> tuple[bool, float]:
    """Return (has_interference, intersection_volume_mm3).

    Face-contact (volume ≈ 0) is NOT considered interference.
    Only solid penetration (volume > threshold) counts.
    """
    vol = _intersection_volume(shape_a, shape_b)
    return vol > volume_threshold, vol


# ---------------------------------------------------------------------------
# Shape collection: from assembly spec OR direct STEP
# ---------------------------------------------------------------------------


def _load_step_shapes(step_path: Path) -> list[tuple[str, Any, Bnd_Box]]:
    """Load all top-level shapes from a STEP file (for direct STEP input).

    Returns list of (name, build123d_shape, bbox).
    """
    import build123d
    from OCP.TopAbs import TopAbs_SOLID, TopAbs_COMPOUND
    from OCP.TopExp import TopExp_Explorer
    from OCP.TopoDS import TopoDS

    root = build123d.import_step(step_path)
    shapes: list[tuple[str, Any, Bnd_Box]] = []

    # Try to get named children first
    children = list(getattr(root, "children", []) or [])
    if children:
        for i, child in enumerate(children):
            name = str(getattr(child, "label", None) or f"part_{i+1}").strip()
            bbox = _get_bbox(child)
            shapes.append((name or f"part_{i+1}", child, bbox))
        return shapes

    # Fallback: extract solids from TopoDS_Shape (skip top-level compound)
    # First check if root is a compound
    is_top_compound = False
    compound_exp = TopExp_Explorer(root.wrapped, TopAbs_COMPOUND)
    if compound_exp.More():
        top_compound = TopoDS.Compound_s(compound_exp.Current())
        # If the compound contains almost all geometry, skip it
        is_top_compound = True
    
    # Extract solids only
    explorer = TopExp_Explorer(root.wrapped, TopAbs_SOLID)
    count = 0
    while explorer.More():
        count += 1
        topods_shape = explorer.Current()
        sub = TopoDS.Solid_s(topods_shape)
        shape = build123d.Shape(obj=sub)
        shape.label = f"solid_{count}"
        bbox = _get_bbox(shape)
        shapes.append((shape.label, shape, bbox))
        explorer.Next()
    
    if not shapes and is_top_compound:
        # If no solids found but top is compound, extract compounds recursively
        compound_exp2 = TopExp_Explorer(root.wrapped, TopAbs_COMPOUND)
        comp_count = 0
        while compound_exp2.More():
            comp_count += 1
            topods_shape = compound_exp2.Current()
            sub = TopoDS.Compound_s(topods_shape)
            shape = build123d.Shape(obj=sub)
            shape.label = f"compound_{comp_count}"
            bbox = _get_bbox(shape)
            shapes.append((shape.label, shape, bbox))
            compound_exp2.Next()

    if not shapes:
        # Last resort: treat root as single shape
        bbox = _get_bbox(root)
        shapes.append(("assembly", root, bbox))

    return shapes


def _load_node_shape(
    node: AssemblyNodeSpec,
    parent_transform: tuple[float, ...] = IDENTITY_TRANSFORM,
) -> tuple[list[tuple[str, Any, Bnd_Box]], list[str]]:
    """Recursively load shapes for a node and its children.

    Returns (list of (name, shape, bbox), list of error messages).
    """
    import build123d

    world_transform = multiply_transforms(parent_transform, node.transform)
    results: list[tuple[str, Any, Bnd_Box]] = []
    errors: list[str] = []

    if node.children:
        for child in node.children:
            child_results, child_errors = _load_node_shape(child, world_transform)
            results.extend(child_results)
            errors.extend(child_errors)
        return results, errors

    # Leaf node: load STEP
    if node.source_path is None:
        errors.append(f"Node '{node.instance_id}' has no source_path")
        return results, errors

    entry = filesystem_entry(node.source_path)
    if entry is None:
        errors.append(f"Node '{node.instance_id}': cannot resolve source {node.path}")
        return results, errors

    try:
        if entry.kind == "assembly":
            # Nested assembly: recurse into its spec
            if entry.assembly_spec is None:
                errors.append(f"Node '{node.instance_id}': assembly missing spec")
                return results, errors
            child_results, child_errors = _load_spec_shapes(
                entry.assembly_spec, world_transform
            )
            results.extend(child_results)
            errors.extend(child_errors)
        else:
            # Part
            step_path = entry.step_path
            if step_path is None:
                errors.append(f"Node '{node.instance_id}': missing STEP path")
                return results, errors
            if _step_has_assembly_artifact(step_path):
                shape = _load_step_assembly_shape(step_path, label=node.instance_id)
            else:
                shape = _load_step_shape(step_path)
            located = shape.moved(_location_from_transform(world_transform))
            located.label = node.instance_id
            bbox = _get_bbox(located)
            results.append((node.instance_id, located, bbox))
    except Exception as exc:
        errors.append(f"Node '{node.instance_id}': failed to load shape: {exc}")

    return results, errors


def _load_spec_shapes(
    spec: AssemblySpec, parent_transform: tuple[float, ...] = IDENTITY_TRANSFORM
) -> tuple[list[tuple[str, Any, Bnd_Box]], list[str]]:
    results: list[tuple[str, Any, Bnd_Box]] = []
    errors: list[str] = []
    for node in assembly_spec_children(spec):
        node_results, node_errors = _load_node_shape(node, parent_transform)
        results.extend(node_results)
        errors.extend(node_errors)
    return results, errors


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------


class AssemblyVerifier:
    def __init__(
        self,
        shapes: list[tuple[str, Any, Bnd_Box]],
        *,
        min_gap: float = 5.0,
        motion_gap: float = 20.0,
        joints_map: dict[str, dict[str, Any]] | None = None,
        allowed_overlaps: list[dict[str, Any]] | None = None,
    ):
        self.shapes = shapes
        self.min_gap = min_gap
        self.motion_gap = motion_gap
        self.joints_map = joints_map or {}
        self.allowed_overlaps = allowed_overlaps or []
        self.interferences: list[dict[str, Any]] = []
        self.allowed_interferences: list[dict[str, Any]] = []
        self.clearance_warnings: list[dict[str, Any]] = []
        self.geometry_issues: list[dict[str, Any]] = []
        self.pairs_checked = 0
        self.pairs_skipped_bbox = 0

    def _is_allowed_overlap(self, name_a: str, name_b: str) -> dict[str, Any] | None:
        """Check if a pair is in the allowed-overlaps list."""
        for ao in self.allowed_overlaps:
            pair = ao.get("pair", [])
            if len(pair) == 2:
                if (pair[0] == name_a and pair[1] == name_b) or (pair[0] == name_b and pair[1] == name_a):
                    return ao
        return None

    def run_all(self) -> dict[str, Any]:
        t0 = time.perf_counter()

        # 1. Geometry validity
        for name, shape, _bbox in self.shapes:
            is_valid, issues = _check_geometry_validity(shape, name)
            if not is_valid:
                self.geometry_issues.append({
                    "part": name,
                    "valid": False,
                    "issues": issues[:5],  # cap detail
                })

        # 2. Pairwise checks
        n = len(self.shapes)
        for i in range(n):
            for j in range(i + 1, n):
                self._check_pair(i, j)

        elapsed = time.perf_counter() - t0

        return {
            "summary": {
                "parts": n,
                "moving_parts": len(self.joints_map),
                "pairs_checked": self.pairs_checked,
                "pairs_skipped_by_bbox": self.pairs_skipped_bbox,
                "interferences": len(self.interferences),
                "allowed_interferences": len(self.allowed_interferences),
                "clearance_warnings": len(self.clearance_warnings),
                "geometry_issues": len(self.geometry_issues),
                "elapsed_seconds": round(elapsed, 3),
            },
            "interferences": self.interferences,
            "allowed_interferences": self.allowed_interferences,
            "clearance_warnings": self.clearance_warnings,
            "geometry_issues": self.geometry_issues,
            "joints": list(self.joints_map.values()),
        }

    def _check_pair(self, i: int, j: int) -> None:
        name_a, shape_a, bbox_a = self.shapes[i]
        name_b, shape_b, bbox_b = self.shapes[j]

        # Fast bbox rejection
        bbox_gap = _bbox_min_gap(bbox_a, bbox_b)
        if bbox_gap > max(self.min_gap, self.motion_gap):
            self.pairs_skipped_bbox += 1
            return

        self.pairs_checked += 1

        # Interference check (only solid penetration, not face contact)
        has_interference, interf_vol = _check_interference(shape_a, shape_b)
        if has_interference:
            allowed = self._is_allowed_overlap(name_a, name_b)
            entry = {
                "part_a": name_a,
                "part_b": name_b,
                "bbox_gap_mm": round(bbox_gap, 3),
                "intersection_volume_mm3": round(interf_vol, 3),
            }
            if allowed:
                entry["allowed_reason"] = allowed.get("reason", "design intent")
                entry["allowed_type"] = allowed.get("type", "fit")
                self.allowed_interferences.append(entry)
            else:
                self.interferences.append(entry)
            return

        # Exact distance check
        exact_dist = _compute_exact_distance(shape_a, shape_b)

        # Determine effective threshold: moving parts use motion_gap
        is_moving_a = name_a in self.joints_map
        is_moving_b = name_b in self.joints_map
        effective_threshold = self.motion_gap if (is_moving_a or is_moving_b) else self.min_gap

        # Distance ≈ 0 with no solid penetration = normal face contact (coincident),
        # do NOT warn. Only warn when distance is positive but below threshold.
        if 0.01 < exact_dist < effective_threshold:
            self.clearance_warnings.append({
                "part_a": name_a,
                "part_b": name_b,
                "distance_mm": round(exact_dist, 3),
                "threshold_mm": effective_threshold,
                "severity": "WARNING",
                "moving": is_moving_a or is_moving_b,
            })


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _print_report(report: dict[str, Any]) -> int:
    summary = report["summary"]
    n_interf = summary["interferences"]
    n_warn = summary["clearance_warnings"]
    n_geom = summary["geometry_issues"]

    print("=" * 60)
    print("  Assembly Verification Report")
    print("=" * 60)
    print(f"  Parts checked:          {summary['parts']}")
    print(f"  Moving parts:           {summary.get('moving_parts', 0)}")
    print(f"  Pairs checked:          {summary['pairs_checked']}")
    print(f"  Pairs skipped (bbox):   {summary['pairs_skipped_by_bbox']}")
    print(f"  Elapsed:                {summary['elapsed_seconds']}s")
    print()

    # Geometry issues
    if n_geom:
        print(f"  GEOMETRY ISSUES: {n_geom}")
        for issue in report["geometry_issues"]:
            print(f"    ❌ {issue['part']}: invalid BRep ({len(issue['issues'])} issues)")
        print()

    # Allowed interferences (design intent)
    n_allowed = len(report.get("allowed_interferences", []))
    if n_allowed:
        print(f"  ALLOWED INTERFERENCES (design intent): {n_allowed} ℹ️")
        for interf in report["allowed_interferences"]:
            reason = interf.get("allowed_reason", "design intent")
            print(f"    ℹ️  {interf['part_a']}  ⟷  {interf['part_b']}  (vol={interf.get('intersection_volume_mm3', '?')}mm³) — {reason}")
        print()

    # Interferences
    if n_interf:
        print(f"  INTERFERENCES: {n_interf} 🔴")
        for interf in report["interferences"]:
            print(f"    🔴 {interf['part_a']}  ⟷  {interf['part_b']}  (vol={interf.get('intersection_volume_mm3', '?')}mm³)")
        print()
    else:
        print("  Interferences:          0 ✅")
        print()

    # Clearance warnings
    if n_warn:
        print(f"  CLEARANCE WARNINGS: {n_warn}")
        for warn in report["clearance_warnings"]:
            sev = "🔴" if warn["severity"] == "CRITICAL" else "🟡"
            print(
                f"    {sev} {warn['part_a']}  ⟷  {warn['part_b']}: "
                f"{warn['distance_mm']}mm (threshold {warn['threshold_mm']}mm)"
            )
        print()
    else:
        print("  Clearance warnings:     0 ✅")
        print()

    print("=" * 60)
    if n_interf or n_geom:
        print("  RESULT: FAILED")
        return 1
    if n_warn:
        print("  RESULT: PASSED WITH WARNINGS")
        return 0
    print("  RESULT: PASSED")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Verify an industrial automation assembly for interference and clearance."
    )
    parser.add_argument("assembly", type=Path, help="Assembly source .py file")
    parser.add_argument(
        "--min-gap",
        type=float,
        default=5.0,
        help="Minimum allowed gap between fixed parts (mm). Default: 5.0",
    )
    parser.add_argument(
        "--motion-gap",
        type=float,
        default=20.0,
        help="Minimum allowed gap for moving parts (mm). Default: 20.0",
    )
    parser.add_argument(
        "--joints",
        type=Path,
        default=None,
        help="Path to joints.json describing motion joints for envelope checking",
    )
    parser.add_argument(
        "--json-out",
        type=Path,
        default=None,
        help="Write detailed report to JSON file",
    )
    parser.add_argument(
        "--allowed-overlaps",
        type=Path,
        default=None,
        help="JSON file listing allowed overlapping pairs (design intent fits)",
    )
    args = parser.parse_args(argv)

    assembly_path = args.assembly.resolve()
    if not assembly_path.exists():
        print(f"Error: assembly file not found: {assembly_path}", file=sys.stderr)
        return 2

    # Load optional joints definition
    joints_map: dict[str, dict[str, Any]] = {}
    if args.joints and args.joints.exists():
        joints_data = json.loads(args.joints.read_text(encoding="utf-8"))
        for j in joints_data.get("joints", []):
            joints_map[j.get("part", "")] = j
        print(f"Loaded joints: {len(joints_map)} motion joint(s)")

    # Load optional allowed overlaps
    allowed_overlaps: list[dict[str, Any]] = []
    if args.allowed_overlaps and args.allowed_overlaps.exists():
        allowed_overlaps = json.loads(args.allowed_overlaps.read_text(encoding="utf-8"))
        print(f"Loaded allowed overlaps: {len(allowed_overlaps)} pair(s)")

    print(f"Loading assembly: {assembly_path}")

    # Support both Python assembly sources and direct STEP files
    if assembly_path.suffix.lower() in (".step", ".stp"):
        print("  (direct STEP input)")
        shapes = _load_step_shapes(assembly_path)
        errors = []
    else:
        spec = read_assembly_spec(assembly_path)
        print(f"  => {len(spec.instances)} top-level instance(s)")
        print("Loading component shapes...")
        shapes, errors = _load_spec_shapes(spec)

    if errors:
        for err in errors:
            print(f"  ⚠️  {err}", file=sys.stderr)
    print(f"  => {len(shapes)} leaf shapes loaded")

    if not shapes:
        print("Error: no shapes to verify", file=sys.stderr)
        return 2

    print(f"\nRunning verification (min_gap={args.min_gap}mm, motion_gap={args.motion_gap}mm)...")
    verifier = AssemblyVerifier(shapes, min_gap=args.min_gap, motion_gap=args.motion_gap, joints_map=joints_map, allowed_overlaps=allowed_overlaps)
    report = verifier.run_all()

    if args.json_out:
        args.json_out.write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(f"Detailed report written to: {args.json_out}\n")

    return _print_report(report)


if __name__ == "__main__":
    raise SystemExit(main())
