"""Initialize an assembly workspace from a task.json."""
from __future__ import annotations

import shutil
from pathlib import Path

from cad_asm.core.state import PartState, StepStatus, WorkspaceState
from cad_asm.schemas.task import AssemblyTask


def run(task_path: Path, workspace: Path, force: bool = False) -> int:
    if workspace.exists() and any(workspace.iterdir()) and not force:
        print(f"ERROR: workspace {workspace} already exists and is not empty. Use --force to overwrite.")
        return 1

    if force and workspace.exists():
        shutil.rmtree(workspace)

    task = AssemblyTask.from_file(task_path)
    task_dir = task_path.parent

    # Create workspace structure
    (workspace / "parts").mkdir(parents=True, exist_ok=True)
    (workspace / "review").mkdir(parents=True, exist_ok=True)
    (workspace / "decisions").mkdir(parents=True, exist_ok=True)
    (workspace / "output").mkdir(parents=True, exist_ok=True)
    (workspace / "log").mkdir(parents=True, exist_ok=True)

    # Copy part source files into workspace/parts/ (only for external python sources)
    for p in task.parts:
        if p.source and p.source.type == "python" and p.source.path:
            src = task_dir / p.source.path
            if src.exists():
                dst = workspace / "parts" / src.name
                shutil.copy2(src, dst)
                p.source.path = str(dst.relative_to(workspace))

    # Write canonical task.json into workspace
    task.to_file(workspace / "task.json")

    # Initialize state
    state = WorkspaceState(
        task_id=task.task_id,
        parts=[PartState(part_id=p.id, status=StepStatus.PENDING) for p in task.parts],
        pending_constraints=[c.model_dump() for c in task.constraints],
    )
    state.to_file(workspace / "state.json")

    print(f"Initialized workspace: {workspace}")
    print(f"  Task: {task.task_id} ({task.name or 'unnamed'})")
    print(f"  Parts: {len(task.parts)}")
    print(f"  Constraints: {len(task.constraints)}")
    return 0
