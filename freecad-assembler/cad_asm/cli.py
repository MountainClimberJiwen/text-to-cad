"""cad-asm CLI entry point."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from cad_asm.commands import init, step, verify, export, lib


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

    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
