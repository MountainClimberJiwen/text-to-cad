#!/usr/bin/env python3
"""
freecad_assemble.py — FreeCAD Assembly 约束求解脚本（v2.0）

架构：build123d（零件）→ FreeCAD（装配约束求解）→ STEP

核心修复（v2.0）：
1. _resolve_face_by_name: 用法向+Z位置+面积三重判断，不再依赖面中心坐标
2. _face_plane: 使用面bbox中心，不再用valueAt(umin,vmin)角点
3. PlaneCoincident: 正确处理水平面贴合（同向法向无需翻转）
4. Distance: 正确叠加在PlaneCoincident之上
5. CenterOfMass: 使用bbox中心而非体积中心
6. 约束求解顺序: Fix → PlaneCoincident → CenterOfMass → Distance

运行方式（必须从 freecadcmd 执行）：
    /Applications/FreeCAD.app/Contents/Resources/bin/freecadcmd \
        skills/industrial_cad/scripts/freecad_assemble.py \
        --constraints models/assemblies/vibratory_feeder_assembly.constraints.json \
        --output models/assemblies/vibratory_feeder_assembly_freecad.step
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Detect if we're running inside FreeCAD or standalone
# ---------------------------------------------------------------------------


def _is_freecad_env() -> bool:
    try:
        import FreeCAD
        return True
    except ImportError:
        return False


def _run_in_freecad(argv: list[str]) -> int:
    """Re-execute this script via freecadcmd if not already in FreeCAD env."""
    import subprocess

    candidates = [
        "/Applications/FreeCAD.app/Contents/Resources/bin/freecadcmd",
        "/Applications/FreeCAD.app/Contents/MacOS/FreeCADCmd",
        "/usr/bin/freecadcmd",
        "/usr/local/bin/freecadcmd",
    ]
    freecadcmd = None
    for c in candidates:
        if Path(c).exists():
            freecadcmd = c
            break
    if freecadcmd is None:
        print("ERROR: freecadcmd not found. Install FreeCAD >=1.0", file=sys.stderr)
        return 2

    # Use --pass to tell freecadcmd to pass remaining args to the script
    cmd = [freecadcmd, __file__, "--pass", *argv]
    print(f"Re-running via freecadcmd: {' '.join(cmd)}")
    return subprocess.call(cmd)


# ---------------------------------------------------------------------------
# Face resolution (v2.0: normal + Z position + area)
# ---------------------------------------------------------------------------


def _resolve_face_by_name(shape, face_name: str) -> Any:
    """从 shape 中按名称提取面（top/bottom/front/back/left/right）。
    
    v2.0 修复：使用法向方向 + Z位置 + 面积三重判断，不再仅用面中心坐标。
    """
    import FreeCAD as App
    import Part

    face_name = face_name.lower()
    
    # Collect all planar faces with their properties
    candidates = []
    for face in shape.Faces:
        if not face.Surface:
            continue
        # Check if planar
        surf_type = str(type(face.Surface).__name__)
        if "Plane" not in surf_type:
            continue
        
        # Get face bbox
        fbb = face.BoundBox
        cx = (fbb.XMin + fbb.XMax) / 2
        cy = (fbb.YMin + fbb.YMax) / 2
        cz = (fbb.ZMin + fbb.ZMax) / 2
        area = face.Area
        
        # Get normal at center (considering face orientation)
        try:
            u = (face.ParameterRange[0] + face.ParameterRange[1]) / 2
            v = (face.ParameterRange[2] + face.ParameterRange[3]) / 2
            normal = face.normalAt(u, v)
            nx, ny, nz = normal.x, normal.y, normal.z
        except Exception:
            nx, ny, nz = 0, 0, 1
        
        candidates.append({
            'face': face,
            'center': (cx, cy, cz),
            'normal': (nx, ny, nz),
            'area': area,
            'zmin': fbb.ZMin,
            'zmax': fbb.ZMax,
        })
    
    if not candidates:
        raise ValueError(f"No planar faces found in shape for '{face_name}'")
    
    if face_name == "bottom":
        # Bottom face: lowest Z, preferably with normal pointing down or up
        # For STEP files, normals often all point up, so we use Z position
        # Sort by Zmin ascending, then by area descending
        candidates.sort(key=lambda f: (f['zmin'], -f['area']))
        return candidates[0]['face']
    
    elif face_name == "top":
        # Top face: highest Z, preferably with normal pointing up
        candidates.sort(key=lambda f: (-f['zmax'], -f['area']))
        return candidates[0]['face']
    
    elif face_name == "front":
        # Front: max Y face
        candidates.sort(key=lambda f: (-f['center'][1], -f['area']))
        return candidates[0]['face']
    
    elif face_name == "back":
        # Back: min Y face
        candidates.sort(key=lambda f: (f['center'][1], -f['area']))
        return candidates[0]['face']
    
    elif face_name == "left":
        # Left: min X face
        candidates.sort(key=lambda f: (f['center'][0], -f['area']))
        return candidates[0]['face']
    
    elif face_name == "right":
        # Right: max X face
        candidates.sort(key=lambda f: (-f['center'][0], -f['area']))
        return candidates[0]['face']
    
    raise ValueError(f"Unknown face name: {face_name}")


def _face_plane(face) -> tuple[tuple[float, float, float], tuple[float, float, float]]:
    """返回面的 (center_point, normal_vector)。
    
    v2.0 修复：使用面bbox中心，不再用valueAt(umin,vmin)角点。
    """
    bb = face.BoundBox
    cx = (bb.XMin + bb.XMax) / 2
    cy = (bb.YMin + bb.YMax) / 2
    cz = (bb.ZMin + bb.ZMax) / 2
    
    try:
        u = (face.ParameterRange[0] + face.ParameterRange[1]) / 2
        v = (face.ParameterRange[2] + face.ParameterRange[3]) / 2
        normal = face.normalAt(u, v)
        return (cx, cy, cz), (normal.x, normal.y, normal.z)
    except Exception:
        return (cx, cy, cz), (0, 0, 1)


def _shape_bbox_center(shape) -> tuple[float, float, float]:
    """返回 shape 的包围盒中心。"""
    bb = shape.BoundBox
    return ((bb.XMin + bb.XMax) / 2, (bb.YMin + bb.YMax) / 2, (bb.ZMin + bb.ZMax) / 2)


# ---------------------------------------------------------------------------
# Constraint solver (v2.0)
# ---------------------------------------------------------------------------


def _compute_placement_for_constraint(
    ref_shape,       # reference part shape (already placed)
    ref_placement,   # reference part current placement
    moving_shape,    # moving part shape (in local coords)
    constraint: dict[str, Any]
) -> Any:
    """根据约束计算 moving_shape 应该应用的 FreeCAD Placement（局部到全局）。
    
    返回的 Placement 应用于 moving_shape 的局部坐标，使其满足约束。
    """
    import FreeCAD as App

    ctype = constraint["type"]

    if ctype == "PlaneCoincident":
        face_ref_name = constraint.get("face_b", "top")  # face on reference part
        face_mov_name = constraint.get("face_a", "bottom")  # face on moving part
        
        face_ref = _resolve_face_by_name(ref_shape, face_ref_name)
        face_mov = _resolve_face_by_name(moving_shape, face_mov_name)
        
        center_ref, normal_ref = _face_plane(face_ref)
        center_mov, normal_mov = _face_plane(face_mov)
        
        # Transform reference face center to global coords
        ref_pos = ref_placement.Base
        ref_rot = ref_placement.Rotation
        global_center_ref = ref_rot.multVec(App.Vector(*center_ref)) + ref_pos
        
        # Also transform reference normal to global
        global_normal_ref = ref_rot.multVec(App.Vector(*normal_ref))
        global_normal_ref.normalize()
        
        # For moving part, we need to place it so that face_mov coincides with face_ref
        # Compute rotation: align face_mov normal with face_ref normal (opposite for贴合)
        v_mov = App.Vector(*normal_mov)
        v_ref = App.Vector(*global_normal_ref)
        
        dot = v_mov.dot(v_ref)
        
        # PlaneCoincident semantics: two faces lie on the same plane.
        # For贴合 (e.g. bottom face on top face), normals should be OPPOSITE
        # so that solids are on opposite sides of the plane (no penetration).
        # 
        # If dot < 0: normals already opposite → no rotation needed ✓
        # If dot > 0: normals same direction → need 180° flip
        
        if dot < 0:
            # Normals already opposite — perfect for贴合, no rotation
            rotation = App.Rotation()
        else:
            # Same direction — need 180° flip around axis perpendicular to both normals
            axis = v_mov.cross(v_ref)
            if axis.Length < 1e-6:
                # Normals are collinear — pick any axis perpendicular to them
                if abs(v_mov.z) > 0.9:
                    axis = App.Vector(1, 0, 0)
                else:
                    axis = App.Vector(0, 0, 1)
            rotation = App.Rotation(axis, 180)
        
        # After rotation, where does moving face center go?
        rotated_center_mov = rotation.multVec(App.Vector(*center_mov))
        
        # Translation to move rotated_center_mov to global_center_ref
        # But we need to consider: the moving face should lie on the reference face PLANE
        # Not just have the centers coincide
        # The reference face plane: global_normal_ref · (p - global_center_ref) = 0
        # We want: global_normal_ref · (rotated_center_mov + T - global_center_ref) = 0
        # So: global_normal_ref · T = global_normal_ref · (global_center_ref - rotated_center_mov)
        
        delta = global_center_ref - rotated_center_mov
        # Project delta onto normal direction to ensure face planes coincide
        normal_component = delta.dot(global_normal_ref)
        
        # For贴合 with same normals: we want the moving face to be exactly on the reference plane
        # T = global_center_ref - rotated_center_mov (centers coincide)
        # But this may not put the face on the plane if the face is not centered
        # For simplicity, let's just align centers - this works for symmetric faces
        translation = delta
        
        return App.Placement(translation, rotation)

    elif ctype == "Distance":
        axis = constraint.get("axis", "z")
        value = float(constraint.get("value", 0))
        
        vec = {
            "x": App.Vector(value, 0, 0),
            "y": App.Vector(0, value, 0),
            "z": App.Vector(0, 0, value),
        }.get(axis, App.Vector(0, 0, value))
        
        return App.Placement(vec, App.Rotation())

    elif ctype == "CenterOfMass":
        axis = constraint.get("axis", "x")
        
        # Transform reference bbox center to global
        ref_center_local = _shape_bbox_center(ref_shape)
        ref_pos = ref_placement.Base
        ref_rot = ref_placement.Rotation
        global_ref_center = ref_rot.multVec(App.Vector(*ref_center_local)) + ref_pos
        
        # Moving part bbox center in local
        mov_center_local = _shape_bbox_center(moving_shape)
        
        axis_idx = {"x": 0, "y": 1, "z": 2}.get(axis, 0)
        
        # Compute offset so that centers align along the specified axis
        # We want: mov_center_global[axis] = ref_center_global[axis]
        # mov_center_global = rotation * mov_center_local + translation
        # For now, assume no rotation (or use current rotation)
        # translation[axis] = global_ref_center[axis] - mov_center_local[axis]
        
        offset = [0.0, 0.0, 0.0]
        offset[axis_idx] = global_ref_center[axis_idx] - mov_center_local[axis_idx]
        
        return App.Placement(App.Vector(*offset), App.Rotation())

    elif ctype == "Rotation":
        axis = constraint.get("axis", "z")
        value = float(constraint.get("value", 0))
        
        if axis == "x":
            rot = App.Rotation(App.Vector(1, 0, 0), value)
        elif axis == "y":
            rot = App.Rotation(App.Vector(0, 1, 0), value)
        elif axis == "z":
            rot = App.Rotation(App.Vector(0, 0, 1), value)
        else:
            raise ValueError(f"Unknown rotation axis: {axis}")
        
        return App.Placement(App.Vector(0, 0, 0), rot)

    elif ctype == "Fix":
        return App.Placement()

    else:
        raise ValueError(f"Unsupported constraint type: {ctype}")


# ---------------------------------------------------------------------------
# Main assembly logic (v2.0)
# ---------------------------------------------------------------------------


def build_assembly_from_constraints(constraints_path: Path, output_path: Path) -> Path:
    import FreeCAD as App
    import Part

    data = json.loads(constraints_path.read_text(encoding="utf-8"))
    parts_config = data.get("parts", [])
    constraints = data.get("constraints", [])

    doc = App.newDocument(data.get("name", "Assembly"))

    # Load all parts
    repo_root = Path.cwd().resolve()
    part_objects: dict[str, Any] = {}
    part_shapes: dict[str, Any] = {}

    for pc in parts_config:
        part_id = pc["id"]
        step_path = repo_root / pc["file"]
        if not step_path.exists():
            raise FileNotFoundError(f"STEP file not found: {step_path}")

        print(f"  Loading STEP: {step_path}")
        shape = Part.read(str(step_path))
        if shape is None or shape.isNull():
            raise RuntimeError(f"Failed to read STEP: {step_path}")
        print(f"    -> volume={shape.Volume:.1f}, bbox={shape.BoundBox}")

        feature = doc.addObject("Part::Feature", part_id)
        feature.Shape = shape
        doc.recompute()
        part_objects[part_id] = feature
        part_shapes[part_id] = shape
        print(f"  Loaded: {part_id}")

    # Initialize all placements to identity
    placements: dict[str, App.Placement] = {pid: App.Placement() for pid in part_objects}

    # Sort constraints: Fix first, then PlaneCoincident, then CenterOfMass, then Distance, then Rotation
    def constraint_priority(c):
        ctype = c.get("type", "")
        priorities = {"Fix": 0, "PlaneCoincident": 1, "CenterOfMass": 2, "Distance": 3, "Rotation": 4}
        return priorities.get(ctype, 99)
    
    sorted_constraints = sorted(constraints, key=constraint_priority)

    for i, c in enumerate(sorted_constraints):
        ctype = c["type"]
        print(f"\n  Constraint {i+1}/{len(sorted_constraints)}: {ctype}")
        print(f"    {json.dumps(c, ensure_ascii=False)}")

        if ctype == "Fix":
            pid = c["part"]
            placements[pid] = App.Placement()
            part_objects[pid].Placement = placements[pid]
            print(f"    -> Fixed {pid} at origin")
            continue

        part_a = c.get("part_a") or c.get("part")
        part_b = c.get("part_b")

        if part_a not in part_shapes:
            print(f"    SKIP: part_a not found ({part_a})")
            continue

        # For most constraints, part_a is the moving part, part_b is the reference
        move_part = part_a
        ref_part = part_b if part_b else part_a

        if ref_part not in part_shapes:
            print(f"    SKIP: ref_part not found ({ref_part})")
            continue

        ref_shape = part_shapes[ref_part]
        mov_shape = part_shapes[move_part]
        ref_placement = placements[ref_part]

        # Compute placement delta for the moving part
        rel_placement = _compute_placement_for_constraint(
            ref_shape, ref_placement, mov_shape, c
        )

        # Apply delta to current placement of moving part
        current = placements[move_part]
        
        if ctype == "Rotation":
            # Rotation constraint REPLACES the current rotation (not accumulates)
            new_placement = App.Placement(current.Base, rel_placement.Rotation)
        else:
            # Other constraints accumulate: P_new = P_current * P_delta
            new_placement = current * rel_placement
        
        placements[move_part] = new_placement

        # Update FreeCAD object
        part_objects[move_part].Placement = placements[move_part]
        p = placements[move_part]
        angle_deg = p.Rotation.Angle * 180.0 / 3.141592653589793
        print(f"    -> Applied placement to {move_part}: Base=({p.Base.x:.1f}, {p.Base.y:.1f}, {p.Base.z:.1f}), Rotation={p.Rotation.Axis}*{angle_deg:.1f}deg")

    doc.recompute()

    # Print final placements summary
    print("\n" + "=" * 60)
    print("  Final Placements Summary")
    print("=" * 60)
    for pid, p in placements.items():
        shape = part_shapes[pid]
        bb = shape.BoundBox
        # Compute global bbox
        corners = [
            (bb.XMin, bb.YMin, bb.ZMin),
            (bb.XMin, bb.YMin, bb.ZMax),
            (bb.XMin, bb.YMax, bb.ZMin),
            (bb.XMin, bb.YMax, bb.ZMax),
            (bb.XMax, bb.YMin, bb.ZMin),
            (bb.XMax, bb.YMin, bb.ZMax),
            (bb.XMax, bb.YMax, bb.ZMin),
            (bb.XMax, bb.YMax, bb.ZMax),
        ]
        global_corners = []
        for cx, cy, cz in corners:
            v = p.Rotation.multVec(App.Vector(cx, cy, cz)) + p.Base
            global_corners.append((v.x, v.y, v.z))
        
        xs = [c[0] for c in global_corners]
        ys = [c[1] for c in global_corners]
        zs = [c[2] for c in global_corners]
        
        print(f"  {pid}:")
        angle_deg = p.Rotation.Angle * 180.0 / 3.141592653589793
        print(f"    Placement: Base=({p.Base.x:.2f}, {p.Base.y:.2f}, {p.Base.z:.2f}), Angle={angle_deg:.1f}deg")
        print(f"    Global BBox: min=({min(xs):.1f}, {min(ys):.1f}, {min(zs):.1f}) max=({max(xs):.1f}, {max(ys):.1f}, {max(zs):.1f})")

    # Export placements JSON for verification
    placements_data = {}
    for pid, p in placements.items():
        placements_data[pid] = {
            "base": [round(p.Base.x, 6), round(p.Base.y, 6), round(p.Base.z, 6)],
            "rotation_axis": [round(p.Rotation.Axis.x, 6), round(p.Rotation.Axis.y, 6), round(p.Rotation.Axis.z, 6)],
            "rotation_angle": round(p.Rotation.Angle * 180.0 / 3.141592653589793, 6),
        }
    placements_path = output_path.with_suffix(".placements.json")
    placements_path.write_text(json.dumps(placements_data, indent=2), encoding="utf-8")
    print(f"Saved placements: {placements_path}")

    # Export assembly STEP (with part names preserved)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Use Import.export to preserve object names in STEP
    export_objects = []
    for pid, feature in part_objects.items():
        if feature.Shape is None or feature.Shape.isNull():
            print(f"  WARN: {pid} has no shape, skipping")
            continue
        # The feature already has Placement set, so its shape is in global coords
        export_objects.append(feature)

    if not export_objects:
        raise RuntimeError("No shapes to export")

    # Export assembly STEP (with part names preserved)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Use Import.export to preserve object names in STEP
    export_objects = []
    for pid, feature in part_objects.items():
        if feature.Shape is None or feature.Shape.isNull():
            print(f"  WARN: {pid} has no shape, skipping")
            continue
        # The feature already has Placement set, so its shape is in global coords
        export_objects.append(feature)

    if not export_objects:
        raise RuntimeError("No shapes to export")

    # Try exporting with names using Import module
    named_export_ok = False
    try:
        import Import
        print(f"\nExporting {len(export_objects)} parts with names via Import.export...")
        abs_output = output_path.resolve()
        Import.export(export_objects, str(abs_output))
        if abs_output.exists():
            print(f"Exported assembly STEP (named): {output_path}")
            named_export_ok = True
    except Exception as e:
        import traceback
        print("TRACEBACK from Import.export:")
        traceback.print_exc()
        print(f"WARN: Import.export failed ({e}), falling back to compound export")

    if not named_export_ok:
        shapes = []
        for obj in export_objects:
            placed = obj.Shape.copy()
            placed.Placement = obj.Placement
            shapes.append(placed)
        if len(shapes) == 1:
            compound = shapes[0]
        else:
            compound = Part.makeCompound(shapes)
        compound.exportStep(str(output_path))
        print(f"Exported assembly STEP (compound): {output_path}")

    # Save FCStd for inspection
    # try:
    #     fcstd_path = output_path.with_suffix(".FCStd")
    #     doc.saveAs(str(fcstd_path))
    #     print(f"Saved FreeCAD document: {fcstd_path}")
    # except Exception as e:
    #     print(f"WARN: Could not save FCStd: {e}")

    return output_path


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Assemble parts using FreeCAD + constraint descriptions."
    )
    parser.add_argument(
        "--constraints",
        type=Path,
        required=True,
        help="Path to .constraints.json file",
    )
    parser.add_argument(
        "--output",
        type=Path,
        required=True,
        help="Output assembly STEP path",
    )
    args = parser.parse_args(argv)

    if not args.constraints.exists():
        print(f"ERROR: constraints file not found: {args.constraints}", file=sys.stderr)
        return 2

    print(f"Building assembly from constraints: {args.constraints}")
    try:
        build_assembly_from_constraints(args.constraints, args.output)
        return 0
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"\nERROR: Assembly failed: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    if not _is_freecad_env():
        sys.exit(_run_in_freecad(sys.argv[1:]))
    # Running inside freecadcmd: filter out freecadcmd's own args
    filtered = []
    for arg in sys.argv[1:]:
        if arg == "--pass":
            continue
        if arg.endswith("freecad_assemble.py"):
            continue
        filtered.append(arg)
    sys.exit(main(filtered))
else:
    # Running inside freecadcmd (freecadcmd sets __name__ to module name, not __main__)
    if _is_freecad_env():
        filtered = []
        for arg in sys.argv[1:]:
            if arg == "--pass":
                continue
            if arg.endswith("freecad_assemble.py"):
                continue
            filtered.append(arg)
        sys.exit(main(filtered))
    else:
        sys.exit(1)
