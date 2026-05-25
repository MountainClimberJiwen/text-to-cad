"""
AgentInterface — Programmatic API for external agents to drive cad-asm.

This module exposes cad-asm as a Python API so external agents
(Hermes, Claude Code, Kimi, etc.) can:
  1. Initialize a workspace
  2. Run/step the assembly loop
  3. Query status
  4. Export results

No CLI or shell required.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from cad_asm.commands import init, run, step, verify, export
from cad_asm.core.state import WorkspaceState
from cad_asm.schemas.task import AssemblyTask


class AgentInterface:
    """
    High-level interface for external agents.

    Usage:
        api = AgentInterface()
        ws = api.init_task(task_dict, "/tmp/ws")
        result = api.run(ws, auto=True)
        if result["status"] == "in_review":
            # Agent inspects review, decides, then continues
            api.decide(ws, "approve")
            result = api.run(ws, auto=True)
        step_file = api.export(ws, "step")
    """

    def init_task(self, task: dict[str, Any], workspace: str | Path) -> Path:
        """Initialize workspace from a task dict."""
        ws = Path(workspace)
        task_path = ws / "task.json"
        ws.mkdir(parents=True, exist_ok=True)
        task_path.write_text(json.dumps(task, indent=2, ensure_ascii=False))
        rc = init.run(task_path, ws, force=False)
        if rc != 0:
            raise RuntimeError(f"init failed with code {rc}")
        return ws

    def run(self, workspace: str | Path, auto: bool = False, max_iterations: int = 100) -> dict[str, Any]:
        """Run assembly loop."""
        ws = Path(workspace)
        rc = run.run(ws, auto=auto, max_iterations=max_iterations)
        return self.status(workspace) | {"return_code": rc}

    def step(self, workspace: str | Path, continue_: bool = False) -> dict[str, Any]:
        """Execute single step."""
        ws = Path(workspace)
        rc = step.run(ws, continue_=continue_)
        return self.status(workspace) | {"return_code": rc}

    def decide(self, workspace: str | Path, decision: str, reason: str = "", modified_transform: dict[str, Any] | None = None) -> None:
        """Write an external decision to the decisions directory."""
        ws = Path(workspace)
        decisions_dir = ws / "decisions"
        decisions_dir.mkdir(parents=True, exist_ok=True)
        from datetime import datetime, timezone
        ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        payload: dict[str, Any] = {
            "decision": decision,
            "reason": reason,
            "timestamp": ts,
        }
        if modified_transform:
            payload["modified_transform"] = modified_transform
        path = decisions_dir / f"{ts}_agent.json"
        path.write_text(json.dumps(payload, indent=2, ensure_ascii=False))

    def status(self, workspace: str | Path) -> dict[str, Any]:
        """Read current workspace state."""
        ws = Path(workspace)
        state_path = ws / "state.json"
        if not state_path.exists():
            return {"status": "not_initialized", "workspace": str(ws)}

        ws_state = WorkspaceState.from_file(state_path)
        review_path = ws / "review" / "pending.json"
        review = None
        if review_path.exists():
            review = json.loads(review_path.read_text())

        return {
            "status": ws_state.status,
            "iteration": ws_state.iteration,
            "parts": [
                {
                    "id": p.part_id,
                    "status": p.status.value,
                    "file": p.part_file,
                    "error": p.error_message,
                }
                for p in ws_state.parts
            ],
            "checkpoint": ws_state.checkpoint_file,
            "last_error": ws_state.last_error,
            "review": review,
        }

    def export(self, workspace: str | Path, fmt: str = "step") -> str | None:
        """Export final assembly. Returns file path or None."""
        ws = Path(workspace)
        rc = export.run(ws, fmt)
        if rc != 0:
            return None
        # Find exported file
        outputs = list((ws / "outputs").glob(f"*.{fmt}")) if (ws / "outputs").exists() else []
        if outputs:
            return str(outputs[0])
        checkpoint = ws / "checkpoint.step"
        if checkpoint.exists():
            return str(checkpoint)
        return None
