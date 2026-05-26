"""VLM-based three-view visual check command for cad-asm."""
from __future__ import annotations

from pathlib import Path
from typing import Sequence

from cad_asm.core.vlm_review import run_vlm_review


def run(
    workspace: Path,
    *,
    out_dir: Path | None = None,
    extra_instructions: str | None = None,
    dry_run: bool = False,
) -> int:
    result = run_vlm_review(
        workspace,
        out_dir=out_dir,
        extra_instructions=extra_instructions,
        dry_run=dry_run,
    )
    return 0 if result.get("ok") else 1
