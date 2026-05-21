"""Review / approval logic."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from cad_asm.core.state import ReviewRequest, WorkspaceState


def write_pending_review(workspace: Path, review: ReviewRequest) -> Path:
    review_dir = workspace / "review"
    review_dir.mkdir(parents=True, exist_ok=True)
    path = review_dir / "pending.json"
    path.write_text(json.dumps({
        "iteration": review.iteration,
        "part_id": review.part_id,
        "proposed_transform": review.proposed_transform,
        "warnings": review.warnings,
        "notes": review.notes,
    }, indent=2))
    return path


def read_latest_decision(workspace: Path) -> dict[str, Any] | None:
    decisions_dir = workspace / "decisions"
    if not decisions_dir.exists():
        return None
    files = sorted(decisions_dir.glob("*.json"))
    if not files:
        return None
    return json.loads(files[-1].read_text())


def clear_pending_review(workspace: Path) -> None:
    pending = workspace / "review" / "pending.json"
    if pending.exists():
        pending.unlink()


def build_review_for_step(
    ws: WorkspaceState,
    part_id: str,
    proposed_transform: dict[str, Any],
    interference: dict[str, Any],
) -> ReviewRequest:
    warnings: list[str] = []
    notes: list[str] = []
    inter_vol = interference.get("intersection_volume", 0.0)
    if inter_vol > 1e-6:
        warnings.append(f"Volume interference: {inter_vol:.4f} mm³")
    if interference.get("warning"):
        warnings.append(interference["warning"])
    notes.append(f"Placing part '{part_id}' at transform {proposed_transform}")
    return ReviewRequest(
        iteration=ws.iteration,
        part_id=part_id,
        proposed_transform=proposed_transform,
        warnings=warnings,
        notes=notes,
    )
