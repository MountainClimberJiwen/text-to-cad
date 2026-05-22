"""Execute one assembly step."""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

from build123d import Rotation as B3dRotation
from build123d import Location
from cad_asm.core.geometry import (
    apply_transform,
    check_interference,
    load_part,
    export_shape,
    solve_place_at,
    solve_align_face,
    solve_coaxial,
    solve_distance,
)
from cad_asm.core.review import (
    build_review_for_step,
    clear_pending_review,
    read_latest_decision,
    write_pending_review,
)
from cad_asm.core.state import PartState, StepStatus, WorkspaceState
from cad_asm.schemas.common import Transform, Rotation, Vector3
from cad_asm.schemas.task import AssemblyTask
from build123d import Vector
from build123d import Rotation as B3dRotation
from build123d import Location
def _resolve_next_part(task: AssemblyTask, ws: WorkspaceState) -> PartState | None:
    for ps in ws.parts:
        if ps.status == StepStatus.PENDING:
            return ps
    return None


def _find_constraints_for_part(task: AssemblyTask, part_id: str) -> list:
    """Find constraints where this part is part2 (the one being placed)."""
    return [c for c in task.constraints if c.part2 == part_id]


def _resolve_transform(task: AssemblyTask, part_id: str, ws: WorkspaceState, workspace: Path) -> dict:
    """Resolve transform for a part using its constraints."""
    constraints = _find_constraints_for_part(task, part_id)
    part_def = next((p for p in task.parts if p.id == part_id), None)

    # Default: use initial_transform if defined
    if part_def and part_def.initial_transform:
        default = part_def.initial_transform
    else:
        default = Transform()

    if not constraints:
        return {
            "position": default.position.model_dump(),
            "rotation": default.rotation.model_dump(),
        }

    # For MVP we only handle the first applicable constraint
    c = constraints[0]
    params = c.params

    if c.type == "place_at":
        return {
            "position": default.position.model_dump(),
            "rotation": default.rotation.model_dump(),
        }

    if c.type in ("align_face", "distance"):
        # Need to load part1 to compute relative placement
        ref_id = c.part1
        ref_def = next((p for p in task.parts if p.id == ref_id), None)
        if ref_def is None:
            raise ValueError(f"Constraint references unknown part: {ref_id}")

        # Load reference part geometry
        ref_shape = None
        for ps in ws.parts:
            if ps.part_id == ref_id and ps.part_file:
                from build123d import import_step
                ref_shape = import_step(str(workspace / ps.part_file))
                if isinstance(ref_shape, list):
                    ref_shape = ref_shape[0]
                break

        if ref_shape is None:
            # Reference part not yet placed or not found
            # Fallback to initial_transform
            return {
                "position": default.position.model_dump(),
                "rotation": default.rotation.model_dump(),
            }

        # Load current part geometry (at origin, no transform yet)
        current_shape = load_part(part_def.source, workspace, part_def.shape)

        if c.type == "align_face":
            face1 = params.get("face1", "top")
            face2 = params.get("face2", "bottom")
            offset = params.get("offset", 0.0)
            loc = solve_align_face(ref_shape, current_shape, face1, face2, offset)
            return _location_to_dict(loc)

        if c.type == "distance":
            face1 = params.get("face1", "top")
            face2 = params.get("face2", "bottom")
            dist = params.get("distance", 0.0)
            loc = solve_distance(ref_shape, current_shape, face1, face2, dist)
            return _location_to_dict(loc)

    if c.type == "coaxial":
        ref_id = c.part1
        ref_def = next((p for p in task.parts if p.id == ref_id), None)
        if ref_def is None:
            raise ValueError(f"Constraint references unknown part: {ref_id}")

        ref_shape = None
        for ps in ws.parts:
            if ps.part_id == ref_id and ps.part_file:
                from build123d import import_step
                ref_shape = import_step(str(workspace / ps.part_file))
                if isinstance(ref_shape, list):
                    ref_shape = ref_shape[0]
                break

        if ref_shape is None:
            return {
                "position": default.position.model_dump(),
                "rotation": default.rotation.model_dump(),
            }

        current_shape = load_part(part_def.source, workspace, part_def.shape)
        axis1 = params.get("axis1", "outer_cylinder")
        axis2 = params.get("axis2", "outer_cylinder")
        loc = solve_coaxial(ref_shape, current_shape, axis1, axis2)
        return _location_to_dict(loc)

    # Fallback
    return {
        "position": default.position.model_dump(),
        "rotation": default.rotation.model_dump(),
    }


def _location_to_dict(loc) -> dict:
    """Convert a build123d Location to our Transform dict (best-effort)."""
    pos = loc.position
    # Extract rotation matrix from OCP gp_Trsf
    trsf = loc.wrapped.Transformation()
    # Get the matrix values
    m00 = trsf.Value(1, 1)
    m01 = trsf.Value(1, 2)
    m02 = trsf.Value(1, 3)
    m10 = trsf.Value(2, 1)
    m11 = trsf.Value(2, 2)
    m12 = trsf.Value(2, 3)
    m20 = trsf.Value(3, 1)
    m21 = trsf.Value(3, 2)
    m22 = trsf.Value(3, 3)
    # Convert rotation matrix to axis-angle
    trace = m00 + m11 + m22
    if trace > 3.0 - 1e-6:
        # Identity
        return {
            "position": {"x": float(pos.X), "y": float(pos.Y), "z": float(pos.Z)},
            "rotation": {"axis": {"x": 0, "y": 0, "z": 1}, "angle_deg": 0},
        }
    angle = math.degrees(math.acos(max(-1.0, min(1.0, (trace - 1.0) / 2.0))))
    if angle < 1e-6:
        axis = Vector3(x=0, y=0, z=1)
    else:
        rx = m21 - m12
        ry = m02 - m20
        rz = m10 - m01
        norm = math.sqrt(rx*rx + ry*ry + rz*rz)
        if norm < 1e-6:
            axis = Vector3(x=0, y=0, z=1)
        else:
            axis = Vector3(x=rx/norm, y=ry/norm, z=rz/norm)
    return {
        "position": {"x": float(pos.X), "y": float(pos.Y), "z": float(pos.Z)},
        "rotation": {"axis": axis.model_dump(), "angle_deg": angle},
    }


def _dict_to_location(d: dict):
    """Convert our Transform dict to a build123d Location."""
    pos = d["position"]
    rot = d["rotation"]
    loc = Location((pos["x"], pos["y"], pos["z"]))
    if rot["angle_deg"] != 0.0:
        ax = (rot["axis"]["x"], rot["axis"]["y"], rot["axis"]["z"])
        loc *= Location(B3dRotation(ax, rot["angle_deg"]))
    return loc


def run(workspace: Path, continue_: bool = False) -> int:
    state_path = workspace / "state.json"
    if not state_path.exists():
        print("ERROR: workspace not initialized. Run `cad-asm init` first.")
        return 1

    ws = WorkspaceState.from_file(state_path)
    task = AssemblyTask.from_file(workspace / "task.json")

    if ws.status == "done":
        print("Assembly already complete.")
        return 3

    if ws.status == "in_review":
        if not continue_:
            print("Assembly is waiting for review. Use --continue after providing a decision.")
            return 2
        decision = read_latest_decision(workspace)
        if decision is None:
            print("No decision found in decisions/. Waiting for review.")
            return 2
        dec = decision.get("decision", "")
        if dec == "reject":
            current = next((p for p in ws.parts if p.status == StepStatus.IN_REVIEW), None)
            if current:
                current.status = StepStatus.ERROR
                current.error_message = decision.get("reason", "Rejected by reviewer")
            clear_pending_review(workspace)
            ws.status = "running"
            ws.to_file(state_path)
            print(f"Rejected part '{current.part_id if current else '?'}. Skipping.")
            return 0
        elif dec == "modify":
            clear_pending_review(workspace)
            ws.status = "running"
            ws.to_file(state_path)
            print("Decision processed: modify. Re-running step with updated parameters.")
            return 0
        # approve
        for ps in ws.parts:
            if ps.status == StepStatus.IN_REVIEW:
                ps.status = StepStatus.DONE
                break
        clear_pending_review(workspace)
        ws.status = "running"
        ws.to_file(state_path)

    # Normal step execution
    part_state = _resolve_next_part(task, ws)
    if part_state is None:
        ws.status = "done"
        ws.to_file(state_path)
        print("All parts placed. Assembly complete.")
        return 3

    part_id = part_state.part_id
    part_def = next((p for p in task.parts if p.id == part_id), None)
    if part_def is None:
        ws.last_error = f"Part definition not found for {part_id}"
        ws.status = "error"
        ws.to_file(state_path)
        print(f"ERROR: {ws.last_error}")
        return 1

    # Load geometry
    try:
        shape = load_part(part_def.source, workspace, part_def.shape)
    except Exception as e:
        ws.last_error = f"Failed to load part {part_id}: {e}"
        ws.status = "error"
        ws.to_file(state_path)
        print(f"ERROR: {ws.last_error}")
        return 1

    # Resolve transform
    transform_dict = _resolve_transform(task, part_id, ws, workspace)

    # If a modified transform was provided via decision, use it
    if continue_:
        decision = read_latest_decision(workspace)
        if decision and decision.get("decision") == "modify" and "modified_transform" in decision:
            transform_dict = decision["modified_transform"]

    # Apply transform
    t = Transform(
        position=Vector3(**transform_dict["position"]),
        rotation=Rotation(
            axis=Vector3(**transform_dict["rotation"]["axis"]),
            angle_deg=transform_dict["rotation"]["angle_deg"],
        ),
    )
    placed = apply_transform(shape, t)

    # Save individual part
    part_file = workspace / "parts" / f"{part_id}.step"
    export_shape(placed, part_file)
    part_state.part_file = str(part_file.relative_to(workspace))

    # Build or load assembly checkpoint
    checkpoint_path = workspace / "checkpoint.step"
    existing_assembly = None
    if checkpoint_path.exists() and ws.checkpoint_file:
        from build123d import import_step
        assembly = import_step(str(checkpoint_path))
        if not isinstance(assembly, list):
            assembly = [assembly]
        existing_assembly = assembly[0]
        for s in assembly[1:]:
            existing_assembly += s
        combined = existing_assembly + placed
    else:
        combined = placed

    export_shape(combined, checkpoint_path)
    ws.checkpoint_file = str(checkpoint_path.relative_to(workspace))

    # Interference check against existing assembly (skip if first part)
    if existing_assembly is not None:
        interference = check_interference(existing_assembly, placed)
    else:
        interference = {"intersection_volume": 0.0, "safe": True}

    # Review gate
    if task.review_each_step:
        review = build_review_for_step(ws, part_id, transform_dict, interference)
        write_pending_review(workspace, review)
        part_state.status = StepStatus.IN_REVIEW
        ws.status = "in_review"
        ws.iteration += 1
        ws.to_file(state_path)
        print(f"Placed '{part_id}' (pending review)")
        print(f"  Review written to: {workspace / 'review' / 'pending.json'}")
        return 2

    # No review needed
    part_state.status = StepStatus.DONE
    part_state.resolved_transform = transform_dict
    ws.iteration += 1
    ws.to_file(state_path)
    print(f"Placed '{part_id}' -> {part_file}")
    return 0
