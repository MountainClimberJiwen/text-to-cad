#!/usr/bin/env python3
"""
In-Context RL Assembly Loop (Kimi kimi-k2)
==========================================
Runs an iterative loop:
    LLM proposes action -> Solver computes geometry -> Verifier checks ->
    Reward computed -> Feedback injected into context -> LLM improves.

No model weights are updated; learning happens purely via in-context
accumulation of (action, outcome, reward) trajectories.

Usage:
    cd freecad-assembler
    KIMI_API_KEY=sk-xxx python3 icrl_assembly.py
"""

import copy
import json
import os
import sys
from typing import Dict, List, Any, Optional, Tuple

# ------------------------------------------------------------------
# Setup import path so we can use framework/ from repo root
# ------------------------------------------------------------------
REPO_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, REPO_ROOT)

from framework.ontology import (
    AssemblyIntent, PartSpec, Relation,
    PartType, RelationType, get_defaults
)
from framework.solver import AssemblySolver, BoundingBox
from framework.verifier import AssemblyVerifier, Violation

# ------------------------------------------------------------------
# Kimi API client (OpenAI-compatible)
# ------------------------------------------------------------------
from llm_http import call_llm as _call_llm

# Re-export for backward compat
call_kimi = _call_llm
KIMI_MODEL = "kimi-k2"


# ------------------------------------------------------------------
# Reward computation
# ------------------------------------------------------------------
def compute_reward(
    intent: AssemblyIntent,
    boxes: Dict[str, BoundingBox],
    violations: List[Violation],
    solver_errors: List[str],
) -> float:
    """Scalar reward for an assembly state. Higher is better."""
    reward = 0.0

    # 1. Coverage: every part must have coordinates
    n_parts = len(intent.parts)
    n_solved = len([n for n in boxes if n in {p.name for p in intent.parts}])
    reward += (n_solved / max(n_parts, 1)) * 10.0

    # 2. Penalize violations
    critical = sum(1 for v in violations if v.severity == "CRITICAL")
    warnings = sum(1 for v in violations if v.severity == "WARNING")
    infos = sum(1 for v in violations if v.severity == "INFO")
    reward -= critical * 8.0
    reward -= warnings * 2.0
    reward -= infos * 0.2

    # 3. Penalize solver auto-corrections (shows intent was sub-optimal)
    for err in solver_errors:
        if "RULE_" in err:
            reward -= 1.0
        if "CONTACT_VIOLATION" in err:
            reward -= 3.0
        if "UNSOLVED" in err:
            reward -= 5.0

    # 4. Structural bonus
    if critical == 0 and warnings == 0:
        reward += 15.0  # clean assembly bonus

    return round(reward, 2)


# ------------------------------------------------------------------
# State formatting for LLM context
# ------------------------------------------------------------------
def format_intent(intent: AssemblyIntent) -> str:
    lines = ["=== AssemblyIntent ==="]
    lines.append(f"Parts ({len(intent.parts)}):")
    for p in intent.parts:
        params = ", ".join(f"{k}={v}" for k, v in p.params.items() if not k.startswith("_"))
        lines.append(f"  - {p.name} ({p.part_type.value})  {params}")
    lines.append(f"Relations ({len(intent.relations)}):")
    for r in intent.relations:
        axis = f" axis={r.axis}" if r.axis else ""
        md = f" min_dist={r.min_dist}" if r.min_dist else ""
        lines.append(f"  - {r.source} --[{r.rel_type.value}]--> {r.target}{axis}{md}")
    return "\n".join(lines)


def format_verifier_report(violations: List[Violation]) -> str:
    if not violations:
        return "Verifier: NO VIOLATIONS (clean)"
    lines = ["Verifier Report:"]
    for v in violations:
        parts = ", ".join(v.parts_involved)
        lines.append(f"  [{v.severity}] {v.rule_id}: {v.message} (parts: {parts})")
    return "\n".join(lines)


def format_solver_errors(errors: List[str]) -> str:
    if not errors:
        return "Solver: NO ERRORS"
    lines = ["Solver Errors:"]
    for e in errors:
        lines.append(f"  - {e}")
    return "\n".join(lines)


def format_state_summary(
    intent: AssemblyIntent,
    solver: AssemblySolver,
    verifier: AssemblyVerifier,
    reward: float,
) -> str:
    parts = [
        format_intent(intent),
        "",
        format_solver_errors(solver.errors),
        "",
        format_verifier_report(verifier.violations),
        "",
        f"Reward: {reward}",
    ]
    return "\n".join(parts)


# ------------------------------------------------------------------
# Action application (mutates a copy of intent)
# ------------------------------------------------------------------
ACTION_SCHEMA = """
You must output a single JSON object with this exact schema:
{
  "thought": "string, analyze current failures and root cause",
  "action": "one of: modify_param | add_relation | remove_relation | add_part | remove_part | no_op",
  "target": "string, part name or relation target identifier",
  "changes": {},
  "reason": "string, why this action fixes the problem"
}

Action semantics:
- modify_param: changes["params"] = {"key": new_value, ...}
- add_relation: changes["relation"] = {"type": "supported_by", "source": "...", "target": "...", "axis": "x|y|z", "min_dist": number}
- remove_relation: changes["relation_index"] = integer (0-based index into current relations list)
- add_part: changes["part"] = {"name": "...", "type": "column|beam|...", "params": {...}}
- remove_part: changes["part_name"] = "..."
- no_op: declare the assembly is good enough; loop will terminate
""".strip()


def apply_action(intent: AssemblyIntent, action: Dict[str, Any]) -> AssemblyIntent:
    """Apply one LLM action to intent, returning a new intent."""
    intent = copy.deepcopy(intent)
    act = action.get("action", "no_op")
    changes = action.get("changes", {})

    if act == "no_op":
        return intent

    if act == "modify_param":
        target = action.get("target", "")
        new_params = changes.get("params", {})
        for p in intent.parts:
            if p.name == target:
                p.params.update(new_params)
                break

    elif act == "add_relation":
        rel_data = changes.get("relation", {})
        rel = Relation(
            rel_type=RelationType(rel_data["type"]),
            source=rel_data["source"],
            target=rel_data["target"],
            axis=rel_data.get("axis"),
            min_dist=rel_data.get("min_dist"),
        )
        intent.relations.append(rel)

    elif act == "remove_relation":
        idx = changes.get("relation_index", -1)
        if 0 <= idx < len(intent.relations):
            intent.relations.pop(idx)

    elif act == "add_part":
        pdata = changes.get("part", {})
        part = PartSpec(
            name=pdata["name"],
            part_type=PartType(pdata["type"]),
            params=pdata.get("params", {}),
        )
        intent.parts.append(part)

    elif act == "remove_part":
        pname = changes.get("part_name", "")
        intent.parts = [p for p in intent.parts if p.name != pname]
        intent.relations = [
            r for r in intent.relations
            if r.source != pname and r.target != pname
        ]

    return intent


# ------------------------------------------------------------------
# Prompt construction
# ------------------------------------------------------------------
def build_system_prompt() -> str:
    return """You are an expert mechanical assembly designer.
Your job is to iteratively improve an assembly intent (a list of parts and their relations).
You do NOT output coordinates; you only modify part parameters and topological relations.
A constraint solver will compute 3D positions afterwards.

## Engineering Rules (hard constraints that affect reward)
1. Gantry beam must be supported by two columns at both ends.
2. Column height must be >= 8 * beam thickness it supports.
3. Vertical cylinder stroke > 50mm must have guide rails.
4. Gripper jaw volume must be >= 0.1% of base plate volume.
5. Hopper must be independently supported, not on vibrating base.
6. SUPPORTED_BY relation implies face contact (gap < 0.1mm).
7. Beam width must cover column span + 20mm minimum.
8. Guide rail must be parallel to cylinder axis within 1 degree.
9. Vibration bowl diameter <= 40% of base plate width.

## Optimization Goals
- Minimize CRITICAL violations (collisions, missing supports).
- Minimize WARNING violations (gaps, proportion issues).
- Prefer fewer auto-corrections by the solver (shows robust design).
- Keep parts count reasonable; do not over-constrain.

## Output Format
""" + ACTION_SCHEMA + """

Be concise in thought/reason. Output ONLY the JSON object, no markdown fences.
"""


def build_user_prompt(
    intent: AssemblyIntent,
    solver: AssemblySolver,
    verifier: AssemblyVerifier,
    reward: float,
    trajectory: List[Dict[str, Any]],
    iteration: int,
) -> str:
    lines = [
        f"## Iteration {iteration}",
        "",
        format_state_summary(intent, solver, verifier, reward),
        "",
    ]

    if trajectory:
        lines.append("## Past Attempts (learn from these)")
        for i, tr in enumerate(trajectory[-5:], 1):  # keep last 5 in context
            lines.append(f"\n[Attempt {i}]")
            lines.append(f"Action: {json.dumps(tr['action'], ensure_ascii=False)}")
            lines.append(f"Reward: {tr['reward']}")
            lines.append(f"Outcome: {tr.get('outcome', 'N/A')}")
        lines.append("")

    lines.append("## Your Task")
    lines.append("Analyze the current state and propose the SINGLE best next action.")
    lines.append("If the assembly is already perfect (no violations, high reward), use action='no_op'.")
    return "\n".join(lines)


# ------------------------------------------------------------------
# LLM call
# ------------------------------------------------------------------
# call_kimi is imported from kimi_http above


# ------------------------------------------------------------------
# Core ICRL loop
# ------------------------------------------------------------------
def icrl_loop(
    initial_intent: AssemblyIntent,
    max_iters: int = 8,
    reward_threshold: float = 20.0,
) -> Tuple[AssemblyIntent, List[Dict[str, Any]], float]:
    """
    Run in-context RL assembly optimization.
    Returns: (best_intent, trajectory, best_reward)
    """
    system_prompt = build_system_prompt()
    messages: List[Dict[str, str]] = [{"role": "system", "content": system_prompt}]

    current = copy.deepcopy(initial_intent)
    trajectory: List[Dict[str, Any]] = []
    best_intent = copy.deepcopy(initial_intent)
    best_reward = -float("inf")

    for it in range(1, max_iters + 1):
        print(f"\n{'='*60}")
        print(f"Iteration {it}/{max_iters}")
        print(f"{'='*60}")

        # Solve & verify current intent
        solver = AssemblySolver(current)
        boxes = solver.solve()
        verifier = AssemblyVerifier(boxes)
        violations = verifier.verify_all()
        reward = compute_reward(current, boxes, violations, solver.errors)

        print(f"Reward: {reward} | Solved: {len(boxes)}/{len(current.parts)} | "
              f"Violations: C={sum(1 for v in violations if v.severity=='CRITICAL')} "
              f"W={sum(1 for v in violations if v.severity=='WARNING')}")

        if reward > best_reward:
            best_reward = reward
            best_intent = copy.deepcopy(current)
            print("[NEW BEST]")

        if reward >= reward_threshold:
            print("Reward threshold reached. Stopping early.")
            break

        # Build prompt with trajectory
        user_prompt = build_user_prompt(
            current, solver, verifier, reward, trajectory, it
        )
        messages.append({"role": "user", "content": user_prompt})

        # Call LLM
        print("Calling Kimi...")
        action = call_kimi(messages)
        print(f"Action: {json.dumps(action, ensure_ascii=False, indent=2)}")

        # Record trajectory
        trajectory.append({
            "iteration": it,
            "action": action,
            "reward": reward,
            "outcome": "critical" if any(v.severity == "CRITICAL" for v in violations) else "ok",
        })

        # Apply action
        if action.get("action") == "no_op":
            print("LLM declared no_op. Stopping.")
            break

        current = apply_action(current, action)

        # Append to message history for in-context memory
        messages.append({"role": "assistant", "content": json.dumps(action, ensure_ascii=False)})

    return best_intent, trajectory, best_reward


# ------------------------------------------------------------------
# Demo: intentionally broken intent to test self-repair
# ------------------------------------------------------------------
def make_broken_intent() -> AssemblyIntent:
    """
    Create an assembly with deliberate defects that LLM should fix:
    1. Gantry span=200 but beam_width only 220 -> barely covers columns (RULE_BEAM_001)
    2. Vertical cylinder stroke=80 (>50) but no guide rail (RULE_CYLINDER_001)
    3. Fixture plate missing ALIGNED_CENTER relation on y-axis
    4. Hopper placed directly on base (should be on support)
    """
    from framework.templates import FullStationTemplate

    # Start from a valid template then introduce defects
    parts, relations = FullStationTemplate.create({
        "station_width": 800,
        "station_depth": 500,
        "gantry_span": 200,        # defect: too small for robust coverage
        "gantry_height": 200,      # defect: column height < 8 * beam_height (beam_h=30, need >=240)
        "vertical_stroke": 80,     # defect: >50 but no guide rail in template (actually template adds one... let us remove it)
        "bowl_diameter": 400,      # defect: > 40% of 800 = 320 (RULE_VIB_BOWL_001)
    })

    intent = AssemblyIntent()
    intent.parts = parts
    intent.relations = relations

    # Defect A: Make beam_width too small to cover columns + 20mm margin
    for p in intent.parts:
        if p.name == "gantry":
            p.params["beam_width"] = 210  # span(200)+col_size(30)=230, need >=250

    # Defect B: Remove the guide rail relation that template auto-adds for long stroke
    # We remove any GUIDES relation targeting gantry_vert_cyl
    intent.relations = [
        r for r in intent.relations
        if not (r.rel_type == RelationType.GUIDES and "vert_cyl" in r.target)
    ]
    # Also remove the auto-added guide part if present
    intent.parts = [p for p in intent.parts if "vert_cyl_guide" not in p.name]

    # Defect C: Remove one ALIGNED_CENTER for fixture plate
    intent.relations = [
        r for r in intent.relations
        if not (r.source == "fix_plate" and r.rel_type == RelationType.ALIGNED_CENTER and r.axis == "y")
    ]

    return intent


def main():
    print("=" * 60)
    print("In-Context RL Assembly Loop (Kimi kimi-k2)")
    print("=" * 60)

    # Validate API key
    if not KIMI_API_KEY or KIMI_API_KEY.startswith("YOUR_"):
        print("ERROR: Set KIMI_API_KEY environment variable.")
        sys.exit(1)

    # Test API connectivity
    print("\nTesting Kimi API connectivity...")
    try:
        client = get_client()
        models = client.models.list()
        model_ids = [m.id for m in models.data]
        if KIMI_MODEL not in model_ids:
            print(f"Warning: {KIMI_MODEL} not in available models: {model_ids}")
        else:
            print(f"OK: {KIMI_MODEL} is available.")
    except Exception as e:
        print(f"API test failed: {e}")
        sys.exit(1)

    # Build broken intent
    print("\nBuilding intentionally broken intent...")
    initial = make_broken_intent()
    print(format_intent(initial))

    # Run ICRL loop
    print("\n" + "=" * 60)
    print("Starting ICRL optimization loop")
    print("=" * 60)

    best_intent, trajectory, best_reward = icrl_loop(
        initial_intent=initial,
        max_iters=6,
        reward_threshold=22.0,
    )

    # Final summary
    print("\n" + "=" * 60)
    print("FINAL SUMMARY")
    print("=" * 60)
    print(f"Best reward achieved: {best_reward}")
    print(f"Iterations used: {len(trajectory)}")
    print("\nBest Intent:")
    print(format_intent(best_intent))

    # Save result
    out_path = os.path.join(REPO_ROOT, "checkpoint", "icrl_best_intent.json")
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w") as f:
        json.dump({
            "reward": best_reward,
            "iterations": len(trajectory),
            "trajectory": trajectory,
            "parts": [
                {"name": p.name, "type": p.part_type.value, "params": p.params}
                for p in best_intent.parts
            ],
            "relations": [
                {"type": r.rel_type.value, "source": r.source, "target": r.target,
                 "axis": r.axis, "min_dist": r.min_dist}
                for r in best_intent.relations
            ],
        }, f, indent=2, ensure_ascii=False)
    print(f"\nSaved best intent to: {out_path}")

    # Optional: run solver on best intent and print verifier report
    solver = AssemblySolver(best_intent)
    boxes = solver.solve()
    verifier = AssemblyVerifier(boxes)
    verifier.verify_all()
    verifier.print_report()


if __name__ == "__main__":
    main()
