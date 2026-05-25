"""Verify current assembly."""
from __future__ import annotations

from pathlib import Path

from cad_asm.core.state import StepStatus, WorkspaceState
from cad_asm.schemas.task import AssemblyTask


def run(workspace: Path) -> int:
    state_path = workspace / "state.json"
    if not state_path.exists():
        print("ERROR: workspace not initialized.")
        return 1

    ws = WorkspaceState.from_file(state_path)
    task = AssemblyTask.from_file(workspace / "task.json")

    pending = sum(1 for p in ws.parts if p.status == StepStatus.PENDING)
    in_review = sum(1 for p in ws.parts if p.status == StepStatus.IN_REVIEW)
    done = sum(1 for p in ws.parts if p.status == StepStatus.DONE)
    errors = sum(1 for p in ws.parts if p.status == StepStatus.ERROR)

    print(f"Task: {task.task_id}")
    print(f"Status: {ws.status}")
    print(f"  Pending:   {pending}")
    print(f"  In review: {in_review}")
    print(f"  Done:      {done}")
    print(f"  Errors:    {errors}")
    if ws.checkpoint_file:
        print(f"Checkpoint: {workspace / ws.checkpoint_file}")
    else:
        print("Checkpoint: none")

    if ws.last_error:
        print(f"Last error: {ws.last_error}")

    return 0
