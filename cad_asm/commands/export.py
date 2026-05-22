"""Export final assembly."""
from __future__ import annotations

from pathlib import Path

from cad_asm.core.geometry import export_shape
from cad_asm.core.state import WorkspaceState
from cad_asm.schemas.task import AssemblyTask


def run(workspace: Path, format_: str | None = None) -> int:
    state_path = workspace / "state.json"
    if not state_path.exists():
        print("ERROR: workspace not initialized.")
        return 1

    ws = WorkspaceState.from_file(state_path)
    task = AssemblyTask.from_file(workspace / "task.json")

    checkpoint = workspace / ws.checkpoint_file if ws.checkpoint_file else None
    if not checkpoint or not checkpoint.exists():
        print("ERROR: no assembly checkpoint found.")
        return 1

    from build123d import import_step

    shapes = import_step(str(checkpoint))
    if isinstance(shapes, list):
        assembly = shapes[0]
        for s in shapes[1:]:
            assembly += s
    else:
        assembly = shapes

    out_dir = workspace / "output"
    out_dir.mkdir(parents=True, exist_ok=True)

    exported = []
    if format_ is None or format_ == "step":
        if task.outputs.step:
            p = out_dir / task.outputs.step
        else:
            p = out_dir / f"{task.task_id}.step"
        export_shape(assembly, p)
        exported.append(str(p))
        print(f"Exported STEP: {p}")

    if format_ == "stl":
        if task.outputs.stl:
            p = out_dir / task.outputs.stl
        else:
            p = out_dir / f"{task.task_id}.stl"
        export_shape(assembly, p)
        exported.append(str(p))
        print(f"Exported STL: {p}")

    # Simple URDF (MVP: box approximations)
    if format_ == "urdf":
        urdf_path = out_dir / (task.outputs.urdf or f"{task.task_id}.urdf")
        urdf_path.write_text(_generate_urdf(task, assembly, workspace))
        exported.append(str(urdf_path))
        print(f"Exported URDF: {urdf_path}")

    if not exported:
        print("Nothing exported.")
        return 1

    return 0


def _generate_urdf(task: AssemblyTask, assembly, workspace: Path) -> str:
    # Very basic URDF with links for each placed part
    links = []
    for p in task.parts:
        links.append(f"""  <link name="{p.id}">
    <visual>
      <geometry>
        <box size="0.1 0.1 0.1"/>
      </geometry>
    </visual>
    <collision>
      <geometry>
        <box size="0.1 0.1 0.1"/>
      </geometry>
    </collision>
  </link>""")

    return f"""<?xml version="1.0"?>
<robot name="{task.task_id}">
{chr(10).join(links)}
</robot>
"""
