#!/usr/bin/env python3
"""Render a turntable PNG sequence from a GLB mesh.

Uses the rasterizer from skills/cad/scripts/snapshot/cli.py.
"""
from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path

import numpy as np

# Add skills/cad/scripts to path so we can import snapshot.cli
SKILL_DIR = Path(__file__).resolve().parent.parent / "skills" / "cad" / "scripts"
if str(SKILL_DIR) not in sys.path:
    sys.path.insert(0, str(SKILL_DIR))

from snapshot.cli import (
    CameraView,
    load_mesh_instances,
    render_mesh_instances,
    parse_rgb,
    _rgb_default,
    DEFAULT_MODEL_COLOR,
    DEFAULT_BACKGROUND_COLOR,
)


def rotate_direction_around_y(direction: tuple[float, float, float], angle_deg: float) -> tuple[float, float, float]:
    angle_rad = math.radians(angle_deg)
    x, y, z = direction
    x_new = x * math.cos(angle_rad) + z * math.sin(angle_rad)
    z_new = -x * math.sin(angle_rad) + z * math.cos(angle_rad)
    length = math.sqrt(x_new**2 + y**2 + z_new**2)
    return (x_new / length, y / length, z_new / length)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Render a turntable PNG sequence from a GLB mesh.")
    parser.add_argument("input", type=Path, help="Path to a GLB mesh.")
    parser.add_argument("--out-dir", type=Path, required=True, help="Directory for frame PNGs.")
    parser.add_argument("--frames", type=int, default=60, help="Number of frames. Default: 60")
    parser.add_argument("--width", type=int, default=1400, help="Frame width")
    parser.add_argument("--height", type=int, default=900, help="Frame height")
    parser.add_argument("--color", default=_rgb_default(DEFAULT_MODEL_COLOR), help="Model RGB in 0..1")
    parser.add_argument("--background", default=_rgb_default(DEFAULT_BACKGROUND_COLOR), help="Background RGB in 0..1")
    parser.add_argument("--start-angle", type=float, default=0.0, help="Start angle in degrees")
    parser.add_argument("--no-edges", action="store_true", help="Disable feature edges")
    parser.add_argument("--no-axes", action="store_true", help="Disable axes overlay")
    parser.add_argument("--elevation", type=float, default=45.0, help="Camera elevation in degrees")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    mesh_instances = load_mesh_instances(args.input)
    if not mesh_instances:
        raise RuntimeError(f"No mesh geometry found in {args.input}")

    args.out_dir.mkdir(parents=True, exist_ok=True)

    model_color = parse_rgb(args.color)
    background_color = parse_rgb(args.background)
    base_direction = (
        math.cos(math.radians(args.elevation)),
        math.sin(math.radians(args.elevation)),
        math.cos(math.radians(args.elevation)),
    )

    for i in range(args.frames):
        angle = args.start_angle + (360.0 * i / args.frames)
        direction = rotate_direction_around_y(base_direction, angle)
        view = CameraView(name=f"frame_{i:04d}", direction=direction, up=(0.0, 1.0, 0.0))
        out_path = args.out_dir / f"frame_{i:04d}.png"
        render_mesh_instances(
            mesh_instances,
            png_out=out_path,
            view=view,
            width=args.width,
            height=args.height,
            model_color=model_color,
            background_color=background_color,
            edges=not args.no_edges,
            axes=not args.no_axes,
        )
        print(f"saved {out_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
