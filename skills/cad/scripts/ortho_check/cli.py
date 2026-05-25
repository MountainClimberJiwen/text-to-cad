from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Sequence

from common.catalog import (
    REPO_ROOT,
    CadSource,
    find_source_by_path,
    source_from_path,
    viewer_artifact_path_for_step_path,
)
from common.render import part_glb_path
from common.validators import geometry_summary_from_manifest

# Re-use snapshot renderer directly
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "snapshot"))
from snapshot.cli import (
    DEFAULT_BACKGROUND_COLOR,
    DEFAULT_MODEL_COLOR,
    load_mesh_instances,
    parse_rgb,
    render_mesh_instances,
)

ORTHographic_VIEWS = ("front", "top", "right")
DEFAULT_OUT_WIDTH = 1200
DEFAULT_OUT_HEIGHT = 900


@dataclass(frozen=True)
class CheckResult:
    source_ref: str
    cad_ref: str
    step_path: str | None
    glb_path: str | None
    views: tuple[str, ...]
    images: list[str] = field(default_factory=list)
    summary: dict[str, object] = field(default_factory=dict)
    checks: dict[str, object] = field(default_factory=dict)
    ok: bool = False
    errors: list[str] = field(default_factory=list)


def _display_path(path: Path) -> str:
    resolved = path.resolve()
    try:
        return resolved.relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return resolved.as_posix()


def _resolve_source(target: str) -> CadSource | None:
    target_path = Path(target.strip())
    resolved = target_path.resolve() if target_path.is_absolute() else (Path.cwd() / target_path).resolve()

    # Try discovery first
    source = find_source_by_path(resolved)
    if source is not None:
        return source

    # Fallback to direct path interpretation
    try:
        return source_from_path(resolved)
    except (OSError, RuntimeError, ValueError):
        return None


def _resolve_glb_path(source: CadSource) -> Path | None:
    if source.step_path is not None:
        return part_glb_path(source.step_path)
    return None


def _read_topology_manifest(source: CadSource) -> dict[str, object] | None:
    if source.step_path is None:
        return None
    manifest_path = viewer_artifact_path_for_step_path(source.step_path, ".topology.json")
    if not manifest_path.exists():
        return None
    try:
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
        return payload if isinstance(payload, dict) else None
    except (OSError, json.JSONDecodeError):
        return None


def _run_geometry_checks(manifest: dict[str, object] | None, mesh_instances: list[object]) -> dict[str, object]:
    checks: dict[str, object] = {}
    errors: list[str] = []

    # Mesh sanity
    total_vertices = sum(int(getattr(inst, "vertices", []).size) for inst in mesh_instances)
    total_triangles = sum(int(getattr(inst, "triangles", []).size) for inst in mesh_instances)
    checks["mesh_vertices"] = total_vertices
    checks["mesh_triangles"] = total_triangles
    if total_vertices == 0:
        errors.append("Mesh has zero vertices")
    if total_triangles == 0:
        errors.append("Mesh has zero triangles")

    # Topology / bbox sanity
    if manifest is not None:
        try:
            summary = geometry_summary_from_manifest(manifest)
        except Exception as exc:
            summary = {}
            errors.append(f"Failed to read geometry summary: {exc}")
        else:
            checks["face_count"] = summary.get("faceCount", 0)
            checks["edge_count"] = summary.get("edgeCount", 0)
            checks["shape_count"] = summary.get("shapeCount", 0)
            checks["occurrence_count"] = summary.get("occurrenceCount", 0)
            size = summary.get("size")
            if isinstance(size, (list, tuple)) and len(size) == 3:
                checks["bbox_size"] = list(size)
                if any(float(v) <= 0.0 for v in size):
                    errors.append(f"BBox has zero or negative dimension: {size}")
            else:
                errors.append("BBox size unavailable")
    else:
        errors.append("Topology manifest missing; skipping topology checks")

    checks["errors"] = errors
    return checks


def _render_views(
    glb_path: Path,
    out_dir: Path,
    views: tuple[str, ...],
    *,
    width: int,
    height: int,
    model_color: tuple[float, float, float],
    background_color: tuple[float, float, float],
    edges: bool,
    axes: bool,
) -> list[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    mesh_instances = load_mesh_instances(glb_path)
    if not mesh_instances:
        raise RuntimeError(f"No mesh geometry found in {glb_path}")

    output_stem = glb_path.parent.name[1:] if glb_path.name.lower() == "model.glb" and glb_path.parent.name.startswith(".") else glb_path.stem
    cleaned = "".join(c if c.isalnum() or c in {"-", "_"} else "_" for c in output_stem).strip("_") or "check"

    written: list[Path] = []
    for view_name in views:
        png_out = out_dir / f"{cleaned}-{view_name}.png"
        render_mesh_instances(
            mesh_instances,
            png_out=png_out,
            view=view_name,
            width=width,
            height=height,
            model_color=model_color,
            background_color=background_color,
            edges=edges,
            axes=axes,
        )
        written.append(png_out)
    return written


def check_source(
    source: CadSource,
    *,
    out_dir: Path,
    views: tuple[str, ...] = ORTHographic_VIEWS,
    width: int = DEFAULT_OUT_WIDTH,
    height: int = DEFAULT_OUT_HEIGHT,
    model_color: tuple[float, float, float] = DEFAULT_MODEL_COLOR,
    background_color: tuple[float, float, float] = DEFAULT_BACKGROUND_COLOR,
    edges: bool = True,
    axes: bool = True,
) -> CheckResult:
    errors: list[str] = []
    images: list[str] = []
    summary: dict[str, object] = {}
    checks: dict[str, object] = {}
    glb_path_obj = _resolve_glb_path(source)

    if glb_path_obj is None:
        errors.append("No GLB path resolved for source")
        return CheckResult(
            source_ref=source.source_ref,
            cad_ref=source.cad_ref,
            step_path=str(source.step_path) if source.step_path else None,
            glb_path=None,
            views=views,
            errors=errors,
        )

    if not glb_path_obj.exists():
        errors.append(
            f"GLB not found: {_display_path(glb_path_obj)}. "
            "Run gen_step_part or gen_step_assembly first."
        )
        return CheckResult(
            source_ref=source.source_ref,
            cad_ref=source.cad_ref,
            step_path=str(source.step_path) if source.step_path else None,
            glb_path=str(glb_path_obj),
            views=views,
            errors=errors,
        )

    # Render
    try:
        written = _render_views(
            glb_path_obj,
            out_dir,
            views,
            width=width,
            height=height,
            model_color=model_color,
            background_color=background_color,
            edges=edges,
            axes=axes,
        )
        images = [_display_path(p) for p in written]
    except Exception as exc:
        errors.append(f"Rendering failed: {exc}")

    # Geometry checks
    manifest = _read_topology_manifest(source)
    try:
        if manifest is not None:
            summary = geometry_summary_from_manifest(manifest)
    except Exception as exc:
        errors.append(f"Geometry summary failed: {exc}")

    try:
        mesh_instances = load_mesh_instances(glb_path_obj)
        checks = _run_geometry_checks(manifest, mesh_instances)
        geo_errors = checks.pop("errors", [])
        if isinstance(geo_errors, list):
            errors.extend(geo_errors)
    except Exception as exc:
        errors.append(f"Mesh check failed: {exc}")

    ok = len(errors) == 0 and len(images) == len(views)

    return CheckResult(
        source_ref=source.source_ref,
        cad_ref=source.cad_ref,
        step_path=str(source.step_path) if source.step_path else None,
        glb_path=str(glb_path_obj),
        views=views,
        images=images,
        summary=summary,
        checks=checks,
        ok=ok,
        errors=errors,
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ortho_check",
        description="Orthographic three-view check for generated CAD results. "
                    "Renders front/top/right views and runs geometry sanity checks.",
    )
    parser.add_argument(
        "targets",
        nargs="+",
        help="Python generator, STEP/STP file, or @cad[...] ref to check.",
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        required=True,
        help="Directory to write check PNGs and report.",
    )
    parser.add_argument(
        "--views",
        default=",".join(ORTHographic_VIEWS),
        help="Comma-separated orthographic views. Default: front,top,right",
    )
    parser.add_argument("--width", type=int, default=DEFAULT_OUT_WIDTH, help="Output image width")
    parser.add_argument("--height", type=int, default=DEFAULT_OUT_HEIGHT, help="Output image height")
    parser.add_argument(
        "--color",
        default=",".join(str(c) for c in DEFAULT_MODEL_COLOR),
        help="Model RGB in 0..1, e.g. '0.80,0.84,0.90'",
    )
    parser.add_argument(
        "--background",
        default=",".join(str(c) for c in DEFAULT_BACKGROUND_COLOR),
        help="Background RGB in 0..1, e.g. '0.98,0.985,0.99'",
    )
    parser.add_argument("--no-edges", action="store_true", help="Disable feature edges")
    parser.add_argument("--no-axes", action="store_true", help="Disable orientation axes")
    parser.add_argument("--json", action="store_true", help="Emit JSON report to stdout")
    parser.add_argument("--report", type=Path, help="Write JSON report to this file")
    return parser


def _parse_views(raw: str) -> tuple[str, ...]:
    names = [v.strip() for v in raw.split(",") if v.strip()]
    allowed = {"front", "back", "right", "left", "top", "bottom", "isometric"}
    invalid = [n for n in names if n not in allowed]
    if invalid:
        raise ValueError(f"Invalid views: {invalid}. Allowed: {sorted(allowed)}")
    return tuple(names)


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)

    try:
        views = _parse_views(args.views)
    except ValueError as exc:
        parser.error(str(exc))

    try:
        model_color = parse_rgb(args.color)
        background_color = parse_rgb(args.background)
    except ValueError as exc:
        parser.error(str(exc))

    out_dir: Path = args.out_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    results: list[CheckResult] = []
    exit_code = 0

    for target in args.targets:
        source = _resolve_source(target)
        if source is None:
            result = CheckResult(
                source_ref=target,
                cad_ref=target,
                step_path=None,
                glb_path=None,
                views=views,
                errors=["CAD source not found"],
            )
            results.append(result)
            exit_code = 1
            continue

        result = check_source(
            source,
            out_dir=out_dir,
            views=views,
            width=args.width,
            height=args.height,
            model_color=model_color,
            background_color=background_color,
            edges=not args.no_edges,
            axes=not args.no_axes,
        )
        results.append(result)
        if not result.ok:
            exit_code = 1

        label = result.source_ref
        status = "PASS" if result.ok else "FAIL"
        print(f"[{status}] {label}")
        for img in result.images:
            print(f"  image: {img}")
        for key, value in result.checks.items():
            print(f"  check {key}: {value}")
        for err in result.errors:
            print(f"  error: {err}")

    report_payload = {
        "ok": all(r.ok for r in results),
        "results": [asdict(r) for r in results],
    }

    if args.report:
        args.report.write_text(json.dumps(report_payload, indent=2, ensure_ascii=True), encoding="utf-8")
        print(f"report: {_display_path(args.report)}")

    if args.json:
        print(json.dumps(report_payload, indent=2, ensure_ascii=True))

    return exit_code
