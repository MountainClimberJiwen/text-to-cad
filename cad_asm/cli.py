"""cad-asm CLI entry point."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from cad_asm.commands import init, step, verify, export, lib, check, vlm_check


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="cad-asm", description="Agent-agnostic CAD assembly CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    # init
    p_init = sub.add_parser("init", help="Initialize an assembly workspace")
    p_init.add_argument("--task", "-t", type=Path, required=True, help="Path to task.json")
    p_init.add_argument("--workspace", "-w", type=Path, default=Path("."), help="Workspace directory")
    p_init.add_argument("--force", action="store_true", help="Overwrite existing workspace")

    # step
    p_step = sub.add_parser("step", help="Execute one assembly step")
    p_step.add_argument("--workspace", "-w", type=Path, default=Path("."), help="Workspace directory")
    p_step.add_argument("--continue", dest="continue_", action="store_true", help="Continue after review decision")

    # verify
    p_verify = sub.add_parser("verify", help="Verify current assembly state")
    p_verify.add_argument("--workspace", "-w", type=Path, default=Path("."), help="Workspace directory")

    # export
    p_export = sub.add_parser("export", help="Export final assembly")
    p_export.add_argument("--workspace", "-w", type=Path, default=Path("."), help="Workspace directory")
    p_export.add_argument("--format", "-f", choices=["step", "stl", "urdf"], default=None, help="Export format")

    # lib-search
    p_lib_search = sub.add_parser("lib-search", help="Search standard parts library by query")
    p_lib_search.add_argument("query", help="Natural language query (e.g. 'pneumatic cylinder')")
    p_lib_search.add_argument("--threshold", type=float, default=0.2, help="Minimum match score")
    p_lib_search.add_argument("--top-k", type=int, default=3, help="Max results")

    # lib-list
    p_lib_list = sub.add_parser("lib-list", help="List all available standard parts")

    # check
    p_check = sub.add_parser("check", help="Run three-view orthographic check on the assembly checkpoint")
    p_check.add_argument("--workspace", "-w", type=Path, default=Path("."), help="Workspace directory")
    p_check.add_argument("--out-dir", "-o", type=Path, default=None, help="Output directory for check images (default: workspace/checks)")
    p_check.add_argument("--views", default=",".join(check.ORTH_VIEWS), help="Comma-separated views")
    p_check.add_argument("--width", type=int, default=check.DEFAULT_WIDTH, help="Image width")
    p_check.add_argument("--height", type=int, default=check.DEFAULT_HEIGHT, help="Image height")
    p_check.add_argument("--color", default=",".join(str(c) for c in check.DEFAULT_MODEL_COLOR), help="Model RGB")
    p_check.add_argument("--background", default=",".join(str(c) for c in check.DEFAULT_BACKGROUND_COLOR), help="Background RGB")
    p_check.add_argument("--no-edges", action="store_true", help="Disable feature edges")
    p_check.add_argument("--no-axes", action="store_true", help="Disable orientation axes")

    # vlm-check
    p_vlm = sub.add_parser("vlm-check", help="Run VLM-based visual review on three-view snapshots")
    p_vlm.add_argument("--workspace", "-w", type=Path, default=Path("."), help="Workspace directory")
    p_vlm.add_argument("--out-dir", type=Path, default=None, dest="vlm_out_dir", help="Output directory (default: workspace/checks)")
    p_vlm.add_argument("--instructions", type=str, default=None, help="Extra prompt instructions for the VLM")
    p_vlm.add_argument("--dry-run", action="store_true", help="Skip VLM call and return mock response")
    p_vlm.add_argument("--provider", choices=["kimi", "doubao"], default=None, help="VLM provider (default: kimi, auto-fallback to doubao)")

    args = parser.parse_args(argv)

    if args.command == "init":
        return init.run(args.task, args.workspace, args.force)
    if args.command == "step":
        return step.run(args.workspace, args.continue_)
    if args.command == "verify":
        return verify.run(args.workspace)
    if args.command == "export":
        return export.run(args.workspace, args.format)
    if args.command == "lib-search":
        return lib.run_search(args.query, args.threshold, args.top_k)
    if args.command == "lib-list":
        return lib.run_list()

    if args.command == "check":
        try:
            model_color = check.parse_rgb(args.color)
            background_color = check.parse_rgb(args.background)
        except ValueError as exc:
            parser.error(str(exc))
        views = [v.strip() for v in args.views.split(",") if v.strip()]
        return check.run(
            args.workspace,
            out_dir=args.out_dir,
            views=views,
            width=args.width,
            height=args.height,
            model_color=model_color,
            background_color=background_color,
            edges=not args.no_edges,
            axes=not args.no_axes,
        )

    if args.command == "vlm-check":
        return vlm_check.run(
            args.workspace,
            out_dir=args.vlm_out_dir,
            extra_instructions=args.instructions,
            dry_run=args.dry_run,
            provider=args.provider,
        )

    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
