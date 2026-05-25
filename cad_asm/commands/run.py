"""Auto-run assembly loop."""
from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path

from cad_asm.commands import step
from cad_asm.core.state import WorkspaceState


def _write_auto_decision(workspace: Path, iteration: int) -> None:
    """Write an auto-approve decision so --continue can pick it up."""
    decisions_dir = workspace / "decisions"
    decisions_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    path = decisions_dir / f"{ts}_auto_{iteration:03d}.json"
    path.write_text(json.dumps({
        "decision": "approve",
        "reason": "auto-run",
        "timestamp": ts,
        "iteration": iteration,
    }, indent=2))


def run(workspace: Path, auto: bool = False, max_iterations: int = 100, poll_interval: float = 2.0) -> int:
    """
    Loop over assembly steps until complete, error, or review gate.

    Args:
        workspace: Workspace directory.
        auto: If True, auto-approve review gates and continue.
        max_iterations: Safety cap to prevent infinite loops.
        poll_interval: Seconds to sleep between polls when waiting for external decisions.

    Returns:
        0 — assembly complete
        1 — error
        2 — paused for review (only when auto=False)
    """
    state_path = workspace / "state.json"
    if not state_path.exists():
        print("ERROR: workspace not initialized. Run `cad-asm init` first.")
        return 1

    iteration = 0
    while iteration < max_iterations:
        ws = WorkspaceState.from_file(state_path)

        if ws.status == "done":
            print("Assembly already complete.")
            return 0

        if ws.status == "error":
            print(f"ERROR: {ws.last_error}")
            return 1

        # Execute one step
        rc = step.run(workspace, continue_=auto)

        if rc == 0:  # step placed successfully
            iteration += 1
            continue

        if rc == 2:  # in_review
            if auto:
                _write_auto_decision(workspace, ws.iteration)
                # Next loop iteration will pick up the decision via step.run(continue_=True)
                continue
            print("Assembly paused for review.")
            print(f"  Review file: {workspace / 'review' / 'pending.json'}")
            print("  Write a decision to decisions/ and run `cad-asm run --continue` or `cad-asm run --auto`")
            return 2

        if rc == 3:  # done
            print("Assembly complete!")
            return 0

        if rc == 1:  # error
            print(f"Step failed after {iteration} iterations.")
            return 1

    print(f"Reached max iterations ({max_iterations}). Stopping.")
    return 1
