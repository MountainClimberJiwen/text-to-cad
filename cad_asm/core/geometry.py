"""Geometry engine wrapping build123d."""
from __future__ import annotations

import importlib.util
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from build123d import (
    Box,
    Cone,
    Cylinder,
    Location,
    Part,
    Rotation as B3dRotation,
    Shape,
    Sphere,
    Torus,
    Vector,
    export_stl,
    export_step,
)
from build123d import GeomType
from OCP.gp import gp_Pnt

from cad_asm.schemas.common import Transform, Vector3
from cad_asm.schemas.shape import ShapeDef
from cad_asm.schemas.task import PartSource


def _load_python_part(path: Path) -> Part:
    """Execute a Python file that should define a top-level variable named `part`."""
    spec = importlib.util.spec_from_file_location("user_part", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load part script: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules["user_part"] = module
    spec.loader.exec_module(module)
    part = getattr(module, "part", None)
    if part is None:
        raise RuntimeError(f"Part script {path} did not define a `part` variable")
    if not isinstance(part, (Part, Shape)):
        raise RuntimeError(f"`part` in {path} is not a build123d Part/Shape")
    return part if isinstance(part, Part) else Part(part)


def load_part(source: PartSource | None, workspace_root: Path, shape: ShapeDef | None = None) -> Part:
    """Load a single part from its source definition or inline shape."""
    if shape is not None:
        return build_shape(shape)

    if source is None:
        raise ValueError("Part requires either `source` or `shape`")

    if source.type == "python":
        if not source.path:
            raise ValueError("Python part source requires `path`")
        script_path = workspace_root / source.path
        if not script_path.exists():
            script_path = Path(source.path)
        return _load_python_part(script_path)

    if source.type in ("step", "stl"):
        raise NotImplementedError(f"Source type '{source.type}' not yet implemented in MVP")

    if source.type == "build123d":
        if not source.expression:
            raise ValueError("build123d source requires `expression`")
        return eval(source.expression, {"__builtins__": __builtins__, "Box": Box, "Part": Part})

    raise ValueError(f"Unknown source type: {source.type}")


def build_shape(def_: ShapeDef) -> Part:
    """Recursively build a Part from a declarative ShapeDef."""
    result: Part | None = None

    if def_.type == "box":
        p = def_.params
        result = Part(Box(p.get("width", 1), p.get("height", 1), p.get("depth", 1)))

    elif def_.type == "cylinder":
        p = def_.params
        result = Part(Cylinder(p.get("radius", 1), p.get("height", 1)))

    elif def_.type == "sphere":
        p = def_.params
        result = Part(Sphere(p.get("radius", 1)))

    elif def_.type == "cone":
        p = def_.params
        result = Part(Cone(p.get("bottom_radius", 1), p.get("top_radius", 0), p.get("height", 1)))

    elif def_.type == "torus":
        p = def_.params
        result = Part(Torus(p.get("major_radius", 1), p.get("minor_radius", 0.2)))

    elif def_.type == "union":
        if not def_.children:
            raise ValueError("union requires at least one child")
        children = [build_shape(c) for c in def_.children]
        result = children[0]
        for c in children[1:]:
            result += c

    elif def_.type == "subtract":
        if len(def_.children) < 2:
            raise ValueError("subtract requires at least two children")
        children = [build_shape(c) for c in def_.children]
        result = children[0]
        for c in children[1:]:
            result -= c

    elif def_.type == "library":
        p = def_.params
        from cad_asm.library import build_library_part
        result = build_library_part(p.get("ref"), p.get("params", {}))

    elif def_.type == "intersect":
        if len(def_.children) < 2:
            raise ValueError("intersect requires at least two children")
        children = [build_shape(c) for c in def_.children]
        result = children[0]
        for c in children[1:]:
            result &= c

    else:
        raise ValueError(f"Unknown shape type: {def_.type}")

    if def_.transform is not None:
        result = apply_transform(result, def_.transform)

    return result


def _to_location(t: Transform) -> Location:
    """Convert schema Transform to build123d Location."""
    pos = t.position
    rot = t.rotation
    loc = Location((pos.x, pos.y, pos.z))
    if rot.angle_deg != 0.0:
        ax = (rot.axis.x, rot.axis.y, rot.axis.z)
        loc *= Location(B3dRotation(ax, rot.angle_deg))
    return loc


def apply_transform(shape: Part, t: Transform) -> Part:
    return shape.locate(_to_location(t))


def export_shape(shape: Part, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    suffix = path.suffix.lower()
    if suffix == ".step":
        export_step(shape, str(path))
    elif suffix == ".stl":
        export_stl(shape, str(path))
    else:
        raise ValueError(f"Unsupported export format: {suffix}")


# ---------------------------------------------------------------------------
# Interference detection (volume-based)
# ---------------------------------------------------------------------------

def check_interference(existing: Part, new_part: Part, tol: float = 1e-6) -> dict[str, Any]:
    """Return interference analysis between existing assembly and new part."""
    intersection = existing.intersect(new_part)
    inter_volume = float(intersection.volume) if hasattr(intersection, "volume") else 0.0
    has_interference = inter_volume > tol

    result: dict[str, Any] = {
        "intersection_volume": inter_volume,
        "safe": not has_interference,
    }
    if has_interference:
        result["warning"] = f"Volume interference detected: {inter_volume:.4f} mm³"
    return result


# ---------------------------------------------------------------------------
# Face / feature selectors
# ---------------------------------------------------------------------------

@dataclass
class FaceInfo:
    face: Any  # build123d Face
    geom_type: GeomType
    center: Vector
    normal: Vector | None = None
    axis: Axis | None = None


def _get_face_info(face) -> FaceInfo:
    center = face.center()
    geom = face.geom_type
    normal = face.normal_at(center) if geom == GeomType.PLANE else None
    axis = None
    if geom == GeomType.CYLINDER:
        try:
            axis = face.axis_of_rotation
        except Exception:
            pass
    return FaceInfo(face=face, geom_type=geom, center=center, normal=normal, axis=axis)


def select_face(shape: Part, selector: str) -> FaceInfo:
    """Select a face from a shape by a semantic selector.

    Selectors for planar faces:
        top, bottom, front, back, left, right
    Selectors for cylindrical faces:
        outer_cylinder, inner_cylinder
    """
    faces = [_get_face_info(f) for f in shape.faces()]

    if selector in ("top", "bottom", "front", "back", "left", "right"):
        candidates = [f for f in faces if f.geom_type == GeomType.PLANE and f.normal is not None]
        if not candidates:
            raise ValueError(f"No planar faces found for selector '{selector}'")

        def score(f: FaceInfo) -> float:
            n = f.normal
            if selector == "top":
                return n.Z
            if selector == "bottom":
                return -n.Z
            if selector == "front":
                return n.Y
            if selector == "back":
                return -n.Y
            if selector == "right":
                return n.X
            if selector == "left":
                return -n.X
            return 0.0

        best = max(candidates, key=score)
        if abs(score(best)) < 0.5:
            raise ValueError(f"Could not confidently identify '{selector}' face (best score {score(best)})")
        return best

    if selector in ("outer_cylinder", "inner_cylinder"):
        cyls = [f for f in faces if f.geom_type == GeomType.CYLINDER]
        if not cyls:
            raise ValueError(f"No cylindrical faces found for selector '{selector}'")
        # Outer = largest radius
        if selector == "outer_cylinder":
            return max(cyls, key=lambda f: getattr(f.face, "radius", 0.0) or 0.0)
        # Inner = smallest radius (non-zero)
        inner = [c for c in cyls if getattr(c.face, "radius", 0.0) > 1e-6]
        if not inner:
            raise ValueError("No inner cylindrical face found")
        return min(inner, key=lambda f: getattr(f.face, "radius", float("inf")))

    raise ValueError(f"Unknown face selector: {selector}")


# ---------------------------------------------------------------------------
# Constraint solvers
# ---------------------------------------------------------------------------

def solve_place_at(transform: Transform) -> Location:
    """Absolute placement constraint."""
    return _to_location(transform)


def _transform_vector(vec: Vector, location: Location) -> Vector:
    """Apply a Location transformation to a Vector."""
    p = gp_Pnt(vec.X, vec.Y, vec.Z)
    p.Transform(location.wrapped.Transformation())
    return Vector(p.X(), p.Y(), p.Z())


def solve_align_face(part1: Part, part2: Part, face1: str, face2: str, offset: float = 0.0) -> Location:
    """Align two faces so that they are coplanar and facing each other.

    Part2 is moved so that its `face2` lies on the same plane as part1's `face1`,
    with the normals pointing in opposite directions (faces touching).
    """
    f1 = select_face(part1, face1)
    f2 = select_face(part2, face2)

    if f1.normal is None or f2.normal is None:
        raise ValueError("align_face requires planar faces")

    # Strategy:
    # 1. Rotate part2 so that f2.normal points opposite to f1.normal
    # 2. Translate part2 so that f2.center lies on the plane of f1

    n1 = f1.normal
    n2 = f2.normal

    # Rotation that maps n2 -> -n1
    target = Vector(-n1.X, -n1.Y, -n1.Z)
    rot_loc = _rotation_between_vectors(n2, target)

    # After rotation, where is f2.center?
    rotated_f2_center = _transform_vector(f2.face.center(), rot_loc)

    # Move part2 so that f2.center aligns with f1.center in the plane normal direction
    # plus any user-specified offset along the normal.
    translation = f1.center - rotated_f2_center + n1 * offset

    return Location(translation) * rot_loc


def solve_coaxial(part1: Part, part2: Part, axis1: str, axis2: str) -> Location:
    """Align two cylindrical axes."""
    f1 = select_face(part1, axis1)
    f2 = select_face(part2, axis2)

    if f1.axis is None or f2.axis is None:
        raise ValueError("coaxial requires cylindrical faces with identifiable axes")

    ax1 = f1.axis
    ax2 = f2.axis

    # Rotation to align ax2 direction with ax1 direction
    dir1 = Vector(ax1.direction.X, ax1.direction.Y, ax1.direction.Z)
    dir2 = Vector(ax2.direction.X, ax2.direction.Y, ax2.direction.Z)
    rot_loc = _rotation_between_vectors(dir2, dir1)

    # After rotation, translate so that ax2 origin lies on ax1
    rotated_ax2_origin = _transform_vector(
        Vector(ax2.position.X, ax2.position.Y, ax2.position.Z), rot_loc
    )
    translation = Vector(ax1.position.X, ax1.position.Y, ax1.position.Z) - rotated_ax2_origin

    return Location(translation) * rot_loc


def solve_distance(part1: Part, part2: Part, face1: str, face2: str, distance: float) -> Location:
    """Place part2 so that face1 and face2 are separated by a given distance."""
    # Start with align_face but offset by distance along the normal
    return solve_align_face(part1, part2, face1, face2, offset=distance)


# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------

def _rotation_between_vectors(v_from: Vector, v_to: Vector) -> Location:
    """Return a Location representing the rotation that maps v_from to v_to."""
    v_from = v_from.normalized()
    v_to = v_to.normalized()

    dot = v_from.dot(v_to)
    if dot > 0.99999:
        return Location((0, 0, 0))
    if dot < -0.99999:
        # 180 deg rotation around any perpendicular axis
        perp = Vector(1, 0, 0) if abs(v_from.X) < 0.9 else Vector(0, 1, 0)
        perp = (perp - v_from * perp.dot(v_from)).normalized()
        return Location(B3dRotation((perp.X, perp.Y, perp.Z), 180))

    axis_vec = v_from.cross(v_to).normalized()
    angle = v_from.get_signed_angle(v_to, axis_vec)
    return Location(B3dRotation((axis_vec.X, axis_vec.Y, axis_vec.Z), angle))
