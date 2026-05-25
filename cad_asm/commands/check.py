"""Three-view orthographic check for cad-asm workspace checkpoints."""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path
from typing import Any, Sequence

from build123d import import_step

# Make skills/cad/scripts importable for snapshot + glb helpers
_CAD_SCRIPTS = Path(__file__).resolve().parent.parent.parent / "skills" / "cad" / "scripts"
if str(_CAD_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_CAD_SCRIPTS))

from common.glb import export_shape_glb  # noqa: E402
from snapshot.cli import (  # noqa: E402
    DEFAULT_BACKGROUND_COLOR,
    DEFAULT_MODEL_COLOR,
    load_mesh_instances,
    parse_rgb,
    render_mesh_instances,
)

from cad_asm.core.state import WorkspaceState  # noqa: E402

ORTH_VIEWS = ("front", "top", "right")
DEFAULT_WIDTH = 1200
DEFAULT_HEIGHT = 900


def _flatten_imported(shape: Any) -> Any:
    """Normalize build123d import_step result to a single shape."""
    if isinstance(shape, list):
        if len(shape) == 1:
            return shape[0]
        from build123d import Compound

        return Compound(shape)
    return shape


def _render_checkpoint_views(
    step_path: Path,
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

    shape = _flatten_imported(import_step(str(step_path)))

    with tempfile.TemporaryDirectory() as td:
        glb_path = Path(td) / "check.glb"
        export_shape_glb(
            shape,
            glb_path,
            linear_deflection=0.5,
            angular_deflection=0.3,
        )
        mesh_instances = load_mesh_instances(glb_path)
        if not mesh_instances:
            raise RuntimeError("No mesh geometry loaded from temporary GLB")

        written: list[Path] = []
        stem = step_path.stem
        for view_name in views:
            png_out = out_dir / f"{stem}-{view_name}.png"
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


def _geometry_checks(shape: Any) -> dict[str, Any]:
    checks: dict[str, Any] = {}
    errors: list[str] = []

    # Bounding box
    try:
        bbox = shape.bounding_box()
        size = (float(bbox.size.X), float(bbox.size.Y), float(bbox.size.Z))
        checks["bbox_size"] = list(size)
        if any(v <= 0.0 for v in size):
            errors.append(f"Zero or negative bbox dimension: {size}")
    except Exception as exc:
        errors.append(f"BBox check failed: {exc}")
        checks["bbox_size"] = None

    # Volume
    try:
        vol = float(shape.volume) if hasattr(shape, "volume") else 0.0
        checks["volume"] = vol
        if vol <= 0.0:
            errors.append(f"Zero or negative volume: {vol}")
    except Exception as exc:
        errors.append(f"Volume check failed: {exc}")
        checks["volume"] = None

    # Face count
    try:
        face_count = len(shape.faces()) if hasattr(shape, "faces") else 0
        checks["face_count"] = face_count
        if face_count == 0:
            errors.append("No faces found")
    except Exception as exc:
        errors.append(f"Face count check failed: {exc}")
        checks["face_count"] = None

    checks["errors"] = errors
    return checks


def run(
    workspace: Path,
    *,
    out_dir: Path | None = None,
    views: Sequence[str] = ORTH_VIEWS,
    width: int = DEFAULT_WIDTH,
    height: int = DEFAULT_HEIGHT,
    model_color: tuple[float, float, float] = DEFAULT_MODEL_COLOR,
    background_color: tuple[float, float, float] = DEFAULT_BACKGROUND_COLOR,
    edges: bool = True,
    axes: bool = True,
) -> int:
    state_path = workspace / "state.json"
    if not state_path.exists():
        print("ERROR: workspace not initialized.")
        return 1

    ws = WorkspaceState.from_file(state_path)
    checkpoint = workspace / ws.checkpoint_file if ws.checkpoint_file else None
    if not checkpoint or not checkpoint.exists():
        print("ERROR: no assembly checkpoint found.")
        return 1

    if out_dir is None:
        out_dir = workspace / "checks"

    print(f"Checking {checkpoint.name} ...")

    # Geometry checks
    shape = _flatten_imported(import_step(str(checkpoint)))
    checks = _geometry_checks(shape)
    geo_errors: list[str] = list(checks.pop("errors", []))

    # Render
    written: list[Path] = []
    try:
        written = _render_checkpoint_views(
            checkpoint,
            out_dir,
            tuple(views),
            width=width,
            height=height,
            model_color=model_color,
            background_color=background_color,
            edges=edges,
            axes=axes,
        )
    except Exception as exc:
        geo_errors.append(f"Rendering failed: {exc}")

    # Report
    ok = len(geo_errors) == 0 and len(written) == len(views)
    status = "PASS" if ok else "FAIL"
    print(f"[{status}] {checkpoint.name}")
    for p in written:
        rel = _rel_path(p, workspace)
        print(f"  image: {rel}")
    for k, v in checks.items():
        print(f"  check {k}: {v}")
    for e in geo_errors:
        print(f"  error: {e}")

    report: dict[str, Any] = {
        "ok": ok,
        "checkpoint": str(checkpoint),
        "views": list(views),
        "images": [str(p) for p in written],
        "checks": checks,
        "errors": geo_errors,
    }
    report_path = out_dir / "check_report.json"
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=True), encoding="utf-8")
    print(f"  report: {_rel_path(report_path, workspace)}")

    return 0 if ok else 1


def _rel_path(path: Path, base: Path) -> str:
    try:
        return path.relative_to(base.resolve()).as_posix()
    except ValueError:
        return path.as_posix()
