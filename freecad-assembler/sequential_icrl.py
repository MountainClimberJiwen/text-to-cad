#!/usr/bin/env python3
"""
Sequential In-Context RL Assembly Agent (Kimi kimi-k2)
======================================================

Combines three ideas from the RL-Prompt-CAD research:
1. Prompt Optimizer    — dynamic feedback based on error type
2. Context Selector    — retrieve relevant in-context demonstrations
3. Sequential Assembly — topological sort reduces search space drastically

Pipeline:
    Phase 1: LLM plans BOM skeleton (parts + relations, no precise params)
    Phase 2: Topological sort determines legal assembly order
    Phase 3: Sequentially refine one part at a time:
             LLM places part → Incremental solve → Incremental verify
             → Prompt-optimized feedback → Fix if needed → Next part
    Phase 4: Full OCP geometric verification (optional bridge to env.py)

Usage:
    cd freecad-assembler
    export KIMI_API_KEY=sk-xxx
    python3 sequential_icrl.py
"""

import copy
import json
import os
import sys
from collections import defaultdict, deque
from typing import Dict, List, Any, Optional, Tuple, Set

REPO_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, REPO_ROOT)
sys.path.insert(0, os.path.join(REPO_ROOT, "..", "skills", "industrial_cad", "rl"))

from framework.ontology import (
    AssemblyIntent, PartSpec, Relation,
    PartType, RelationType, get_defaults, ENGINEERING_RULES
)
from framework.solver import AssemblySolver, BoundingBox
from framework.verifier import AssemblyVerifier, Violation
from framework.templates import (
    FullStationTemplate,
    VibrationFeederTemplate,
    GantryPickPlaceTemplate,
    FixtureStationTemplate,
)

from llm_http import call_llm as _call_llm, DOUBAO_MODEL as KIMI_MODEL


# ==================================================================
# 1. Assembly Sequencer — topological sort to enforce assembly order
# ==================================================================

class AssemblySequencer:
    """
    Builds a dependency DAG from relations and computes a legal
    assembly order via topological sort.

    This is the KEY to search-space reduction:
    Instead of optimizing all parts simultaneously, we ground one part
    at a time in a legal order.  The LLM only needs to reason about
    local relations to already-grounded parts.
    """

    # Relations where SOURCE depends on TARGET (target must be assembled first)
    DEPENDENCY_RELATIONS = {
        RelationType.SUPPORTED_BY,
        RelationType.MOUNTED_ON,
        RelationType.ALIGNED_CENTER,
        RelationType.GUIDES,
        RelationType.DRIVES,
    }

    def build_dependency_graph(self, intent: AssemblyIntent) -> Dict[str, List[str]]:
        """Return adjacency list: part_name -> list of parts it depends on."""
        graph = defaultdict(list)
        part_names = {p.name for p in intent.parts}

        for rel in intent.relations:
            if rel.rel_type in self.DEPENDENCY_RELATIONS:
                if rel.source in part_names and rel.target in part_names:
                    graph[rel.source].append(rel.target)
            # REACHES / CLEARANCE are not strict dependencies for ordering
        return graph

    def topological_sort(self, intent: AssemblyIntent) -> List[str]:
        """Kahn's algorithm. Returns assembly order (base-plate first).
        If cycles are detected, breaks them by removing offending relations."""
        graph = self.build_dependency_graph(intent)
        part_names = [p.name for p in intent.parts]

        def _sort(graph):
            in_degree = {name: 0 for name in part_names}
            adj = defaultdict(list)
            for src, deps in graph.items():
                for dep in deps:
                    if dep in in_degree:
                        adj[dep].append(src)
                        in_degree[src] += 1
            queue = deque([n for n, d in in_degree.items() if d == 0])
            # Force base_plate first
            queue_list = list(queue)
            if "base_plate" in queue_list:
                queue_list.remove("base_plate")
                queue_list.insert(0, "base_plate")
            queue = deque(queue_list)
            result = []
            while queue:
                node = queue.popleft()
                result.append(node)
                for neighbor in adj[node]:
                    in_degree[neighbor] -= 1
                    if in_degree[neighbor] == 0:
                        queue.append(neighbor)
            return result

        result = _sort(graph)
        if len(result) == len(part_names):
            return result

        # Cycle detected — break it by removing relations until graph is DAG
        print(f"  [WARN] Cycle detected. Breaking cycles by removing redundant relations...")
        unresolved = set(part_names) - set(result)
        for rel in list(intent.relations):
            if rel.source in unresolved and rel.target in unresolved:
                intent.relations.remove(rel)
                graph = self.build_dependency_graph(intent)
                result = _sort(graph)
                if len(result) == len(part_names):
                    print(f"  [WARN] Removed relation {rel.source} -> {rel.target} to break cycle")
                    return result

        # Last resort: remove any remaining dangling relations
        for rel in list(intent.relations):
            if rel.source in unresolved or rel.target in unresolved:
                intent.relations.remove(rel)
                graph = self.build_dependency_graph(intent)
                result = _sort(graph)
                if len(result) == len(part_names):
                    return result

        raise ValueError(f"Unresolvable cycle in assembly dependencies: {unresolved}")

    def get_assembly_stages(self, intent: AssemblyIntent) -> List[List[str]]:
        """
        Return stages where parts in the same stage can be assembled in parallel.
        Stage 0 = base plate, Stage 1 = parts directly on base, etc.
        """
        order = self.topological_sort(intent)
        graph = self.build_dependency_graph(intent)
        stage_of = {}

        for name in order:
            deps = graph.get(name, [])
            if not deps:
                stage_of[name] = 0
            else:
                stage_of[name] = max(stage_of[d] for d in deps if d in stage_of) + 1

        max_stage = max(stage_of.values()) if stage_of else 0
        stages = [[] for _ in range(max_stage + 1)]
        for name, st in stage_of.items():
            stages[st].append(name)
        return stages


# ==================================================================
# 2. Prompt Optimizer — dynamic feedback based on error taxonomy
# ==================================================================

class PromptOptimizer:
    """
    Lightweight RL-APO layer.
    State = dominant error type from verifier.
    Action = select feedback template to inject into next prompt.
    No neural network needed at this stage; we use a rule-based selector
    that can later be replaced by a learned policy.
    """

    FEEDBACK_TEMPLATES = {
        "interference": (
            "⚠️ CRITICAL: Interference detected between parts. "
            "When placing the new part, ensure CLEARANCE relations are defined "
            "and no bounding boxes overlap with already-assembled parts."
        ),
        "missing_support": (
            "⚠️ WARNING: A part lacks proper support. "
            "Every non-base part must have at least one SUPPORTED_BY or MOUNTED_ON "
            "relation to an already-grounded part."
        ),
        "dimension_error": (
            "⚠️ WARNING: Dimensional rule violation. "
            "Refer to engineering rules: column height >= 8×beam thickness, "
            "beam width >= column span + 20mm, bowl diameter <= 40% base width, etc."
        ),
        "clearance": (
            "⚠️ WARNING: Clearance violation. "
            "Check that min_dist in CLEARANCE relations is respected, "
            "and that guided parts (cylinders > 50mm stroke) have guide rails."
        ),
        "contact_gap": (
            "⚠️ WARNING: Face contact gap too large. "
            "SUPPORTED_BY / MOUNTED_ON relations imply gap < 0.1mm. "
            "Align centers or adjust heights accordingly."
        ),
        "proportion": (
            "⚠️ WARNING: Part proportion issues. "
            "Very small parts may be invisible; very large parts may be mis-scaled."
        ),
        "unsolved": (
            "⚠️ CRITICAL: Some parts have no coordinates after solving. "
            "Ensure every part is connected to the base plate via a chain of relations."
        ),
        "default": "Please design the current part carefully, respecting all engineering rules.",
    }

    @classmethod
    def classify(cls, violations: List[Violation], solver_errors: List[str]) -> str:
        """Classify dominant error type."""
        if any("UNSOLVED" in e for e in solver_errors):
            return "unsolved"
        if any(v.severity == "CRITICAL" and v.rule_id == "INTERFERENCE" for v in violations):
            return "interference"
        if any(v.rule_id == "NO_SUPPORT" for v in violations):
            return "missing_support"
        if any(v.rule_id in ("TOO_SMALL", "TOO_LARGE") for v in violations):
            return "proportion"
        if any(v.rule_id == "CONTACT_GAP" for v in violations):
            return "contact_gap"
        if any(v.rule_id.startswith("CLEARANCE") for v in violations):
            return "clearance"
        if any("RULE_" in e for e in solver_errors):
            return "dimension_error"
        return "default"

    @classmethod
    def get_feedback(cls, violations: List[Violation], solver_errors: List[str]) -> str:
        error_type = cls.classify(violations, solver_errors)
        return cls.FEEDBACK_TEMPLATES.get(error_type, cls.FEEDBACK_TEMPLATES["default"])


# ==================================================================
# 3. Context Selector — retrieve relevant demonstrations
# ==================================================================

class ContextSelector:
    """
    RL-ICL Selector (lightweight version).
    Maintains a library of successful assembly templates.
    Given the current BOM, retrieves the most relevant example(s)
    to prepend as few-shot demonstrations.
    """

    CASE_LIBRARY = [
        {
            "task_type": "vibration_feeder",
            "keywords": {"vibration", "bowl", "hopper", "feeder"},
            "template_fn": VibrationFeederTemplate.create,
            "description": "Vibration bowl feeder with hopper and linear track.",
        },
        {
            "task_type": "gantry_pick_place",
            "keywords": {"gantry", "pick", "place", "gripper", "beam", "column"},
            "template_fn": GantryPickPlaceTemplate.create,
            "description": "Gantry-based pick-and-place with horizontal/vertical cylinders and gripper.",
        },
        {
            "task_type": "fixture_station",
            "keywords": {"fixture", "plate", "clamp", "locate"},
            "template_fn": FixtureStationTemplate.create,
            "description": "Fixture station with base, plate, and optional push cylinder.",
        },
        {
            "task_type": "full_station",
            "keywords": {"full", "station", "complete", "assembly line"},
            "template_fn": FullStationTemplate.create,
            "description": "Complete station combining vibration feeder + gantry + fixture.",
        },
    ]

    @classmethod
    def select(cls, intent: AssemblyIntent, k: int = 1) -> List[Dict[str, Any]]:
        """Score each case by keyword overlap with current part types."""
        current_keywords = set()
        for p in intent.parts:
            current_keywords.add(p.part_type.value)
            # add component words
            current_keywords.update(p.part_type.value.split("_"))

        scored = []
        for case in cls.CASE_LIBRARY:
            score = len(current_keywords & case["keywords"])
            scored.append((score, case))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [case for _, case in scored[:k]]

    @classmethod
    def format_demonstration(cls, case: Dict[str, Any]) -> str:
        return (
            f"### Example: {case['task_type']}\n"
            f"Description: {case['description']}\n"
            f"Typical parts: {', '.join(sorted(case['keywords']))}\n"
        )


# ==================================================================
# 4. Sequential ICRL Agent
# ==================================================================

class SequentialICRLAgent:
    """
    Main agent that runs the sequential assembly loop.
    """

    def __init__(
        self,
        max_refinement_iters: int = 5,
        reward_threshold: float = 20.0,
        use_precise_verification: bool = False,
    ):
        self.max_refinement_iters = max_refinement_iters
        self.reward_threshold = reward_threshold
        self.use_precise_verification = use_precise_verification
        self.sequencer = AssemblySequencer()
        self.prompt_optimizer = PromptOptimizer()
        self.context_selector = ContextSelector()
        self.trajectory: List[Dict[str, Any]] = []

    # ------------------------------------------------------------------
    # Phase 1: LLM plans BOM skeleton
    # ------------------------------------------------------------------
    def plan_bom(self, user_requirement: str) -> AssemblyIntent:
        """
        Ask LLM to produce a BOM skeleton: part list + relations,
        without precise numeric parameters.
        """
        system_msg = (
            "You are an expert automation equipment designer. "
            "Given a user requirement, output a JSON skeleton of the assembly.\n\n"
            "Rules:\n"
            "1. List ALL parts needed (use standard part types).\n"
            "2. List ALL relations between parts (SUPPORTED_BY, MOUNTED_ON, etc.).\n"
            "3. Do NOT include exact coordinates; use relative relations only.\n"
            "4. Include estimated parameters (width, height, span, stroke) as rough numbers.\n"
            "5. The base_plate must be the first part.\n\n"
            "Output schema:\n"
            '{"parts": [{"name": "...", "type": "base_plate|column|beam|...", "params": {...}}], '
            '"relations": [{"type": "supported_by", "source": "...", "target": "...", "axis": "x|y|z"}]}'
        )

        user_msg = f"User requirement: {user_requirement}\n\nGenerate the assembly skeleton."

        messages = [
            {"role": "system", "content": system_msg},
            {"role": "user", "content": user_msg},
        ]

        raw = _call_kimi(messages, temperature=0.4)
        intent = self._parse_skeleton(raw)
        print(f"[Phase 1] Planned BOM: {len(intent.parts)} parts, {len(intent.relations)} relations")
        return intent

    def _parse_skeleton(self, raw: Dict[str, Any]) -> AssemblyIntent:
        """Parse LLM JSON into AssemblyIntent, filling defaults."""
        intent = AssemblyIntent()

        for pdata in raw.get("parts", []):
            try:
                ptype = PartType(pdata["type"])
            except ValueError:
                # fallback: try fuzzy match
                ptype = PartType.BASE_PLATE
                for pt in PartType:
                    if pt.value in pdata["type"].lower().replace(" ", "_"):
                        ptype = pt
                        break
            params = copy.deepcopy(get_defaults(ptype))
            params.update(pdata.get("params", {}))
            part = PartSpec(name=pdata["name"], part_type=ptype, params=params)
            intent.parts.append(part)

        for rdata in raw.get("relations", []):
            try:
                rtype = RelationType(rdata["type"])
            except ValueError:
                continue
            rel = Relation(
                rel_type=rtype,
                source=rdata["source"],
                target=rdata["target"],
                axis=rdata.get("axis"),
                min_dist=rdata.get("min_dist"),
            )
            intent.relations.append(rel)

        # Ensure base_plate exists
        has_base = any(p.part_type == PartType.BASE_PLATE for p in intent.parts)
        if not has_base:
            intent.parts.insert(0, PartSpec(
                name="base_plate",
                part_type=PartType.BASE_PLATE,
                params=get_defaults(PartType.BASE_PLATE),
            ))

        return intent

    # ------------------------------------------------------------------
    # Phase 2 + 3: Sequential refinement
    # ------------------------------------------------------------------
    def sequential_refine(self, skeleton: AssemblyIntent) -> Tuple[AssemblyIntent, float]:
        """
        Ground parts one-by-one in topological order.
        Returns the best intent and its reward.
        """
        order = self.sequencer.topological_sort(skeleton)
        stages = self.sequencer.get_assembly_stages(skeleton)
        print(f"[Phase 2] Assembly order: {' -> '.join(order)}")
        print(f"[Phase 2] Stages: {[s for s in stages]}")

        # Retrieve relevant demonstrations
        demos = self.context_selector.select(skeleton, k=1)
        demo_text = "\n".join(ContextSelector.format_demonstration(d) for d in demos)

        # Start with base plate only
        current = AssemblyIntent()
        base_part = next(
            (copy.deepcopy(p) for p in skeleton.parts if p.part_type == PartType.BASE_PLATE),
            PartSpec(name="base_plate", part_type=PartType.BASE_PLATE, params=get_defaults(PartType.BASE_PLATE))
        )
        current.parts.append(base_part)
        current.relations = []
        grounded_names: Set[str] = {base_part.name}

        best_reward = -float("inf")
        best_intent = copy.deepcopy(current)

        # Process remaining parts in order
        for part_name in order:
            if part_name in grounded_names:
                continue

            part_spec = next((copy.deepcopy(p) for p in skeleton.parts if p.name == part_name), None)
            if part_spec is None:
                print(f"  [WARN] Part '{part_name}' in order but not in skeleton, skipping")
                continue

            print(f"\n  >>> Grounding: {part_name} ({part_spec.part_type.value})")

            # Find relations in skeleton that involve this part and already-grounded parts
            relevant_relations = [
                copy.deepcopy(r) for r in skeleton.relations
                if (r.source == part_name and r.target in grounded_names) or
                   (r.target == part_name and r.source in grounded_names)
            ]

            # Try to place this part (with possible retries)
            placed_intent, reward = self._place_part_with_retry(
                current=current,
                part_spec=part_spec,
                relevant_relations=relevant_relations,
                demo_text=demo_text,
                max_retries=self.max_refinement_iters,
            )

            current = placed_intent
            grounded_names.add(part_name)

            if reward > best_reward:
                best_reward = reward
                best_intent = copy.deepcopy(current)
                print(f"      [NEW BEST reward={best_reward}]")

        return best_intent, best_reward

    def _place_part_with_retry(
        self,
        current: AssemblyIntent,
        part_spec: PartSpec,
        relevant_relations: List[Relation],
        demo_text: str,
        max_retries: int,
    ) -> Tuple[AssemblyIntent, float]:
        """
        Ask LLM to place a single part, retry with optimized feedback if verification fails.
        """
        working = copy.deepcopy(current)
        working.parts.append(copy.deepcopy(part_spec))
        working.relations.extend(copy.deepcopy(relevant_relations))

        best_reward = -float("inf")
        best_intent = copy.deepcopy(working)

        feedback = ""

        for attempt in range(1, max_retries + 1):
            # Build focused prompt for this single part
            messages = self._build_placement_prompt(
                current=current,
                part_spec=part_spec,
                relevant_relations=relevant_relations,
                demo_text=demo_text,
                feedback=feedback,
                attempt=attempt,
            )

            action = _call_llm(messages, temperature=0.3, provider="doubao")
            print(f"      Attempt {attempt}: {json.dumps(action, ensure_ascii=False)[:200]}")

            # Apply action to working intent
            working = self._apply_placement_action(working, part_spec.name, action)

            # Solve & verify (incremental — only check new part vs grounded)
            solver = AssemblySolver(working)
            boxes = solver.solve()

            # Full verify for now (lightweight enough for small assemblies)
            verifier = AssemblyVerifier(boxes)
            violations = verifier.verify_all()

            # Compute reward
            reward = self._compute_incremental_reward(
                working, boxes, violations, solver.errors, part_spec.name
            )

            if reward > best_reward:
                best_reward = reward
                best_intent = copy.deepcopy(working)

            # Check if acceptable
            critical = [v for v in violations if v.severity == "CRITICAL"]
            unsolved = [e for e in solver.errors if "UNSOLVED" in e]

            if not critical and not unsolved and reward >= 10:
                print(f"      ✓ Accepted (reward={reward})")
                return best_intent, best_reward

            # Generate optimized feedback for next attempt
            feedback = self.prompt_optimizer.get_feedback(violations, solver.errors)
            print(f"      ✗ Failed (reward={reward}), feedback: {feedback[:100]}...")

        print(f"      → Best after retries: reward={best_reward}")
        return best_intent, best_reward

    def _build_placement_prompt(
        self,
        current: AssemblyIntent,
        part_spec: PartSpec,
        relevant_relations: List[Relation],
        demo_text: str,
        feedback: str,
        attempt: int,
    ) -> List[Dict[str, str]]:
        """Build a highly-focused prompt for placing ONE part."""
        # Summarize already-grounded parts
        solver = AssemblySolver(current)
        solver.solve()
        grounded_summary = []
        for p in current.parts:
            box = solver.boxes.get(p.name)
            if box:
                grounded_summary.append(
                    f"  {p.name}: center=({box.cx:.1f},{box.cy:.1f},{box.cz:.1f}) "
                    f"size=({box.w:.1f},{box.d:.1f},{box.h:.1f})"
                )

        rel_text = []
        for r in relevant_relations:
            axis = f" axis={r.axis}" if r.axis else ""
            md = f" min_dist={r.min_dist}" if r.min_dist else ""
            rel_text.append(f"  - {r.source} --[{r.rel_type.value}]--> {r.target}{axis}{md}")

        defaults = get_defaults(part_spec.part_type)
        param_hint = ", ".join(f"{k}={v}" for k, v in defaults.items())

        system_msg = (
            "You are a precision mechanical designer. "
            "Your task is to determine the exact parameters for ONE new part being added to an existing assembly.\n\n"
            "Engineering Rules:\n"
            + "\n".join(f"- {r['description']}" for r in ENGINEERING_RULES.values()) +
            "\n\n"
            "You may output:\n"
            '- {"action": "set_params", "params": {"x":..., "y":..., "height":...}}\n'
            '- {"action": "add_relation", "relation": {"type": "supported_by", "source": "...", "target": "...", "axis": "z"}}\n'
            '- {"action": "modify_relation", "index": 0, "changes": {"axis": "y"}}\n'
            '- {"action": "no_op", "reason": "parameters are good"}\n'
        )

        user_msg_parts = [
            f"## Attempt {attempt}",
            f"## New Part: {part_spec.name} (type={part_spec.part_type.value})",
            f"Default parameters for this type: {param_hint}",
            "",
            "## Already Grounded Parts",
            "\n".join(grounded_summary) if grounded_summary else "  (none)",
            "",
            "## Planned Relations for New Part",
            "\n".join(rel_text) if rel_text else "  (none yet)",
            "",
        ]

        if feedback:
            user_msg_parts.append(f"## Feedback from Previous Attempt\n{feedback}\n")

        if demo_text:
            user_msg_parts.append(f"## Reference Example\n{demo_text}\n")

        user_msg_parts.append(
            "## Task\n"
            f"Determine the exact parameters for '{part_spec.name}' so that:\n"
            "1. It satisfies all planned relations to already-grounded parts.\n"
            "2. It respects engineering rules.\n"
            "3. It does not interfere with already-grounded parts.\n"
            "Output a single JSON action."
        )

        return [
            {"role": "system", "content": system_msg},
            {"role": "user", "content": "\n".join(user_msg_parts)},
        ]

    def _apply_placement_action(
        self,
        intent: AssemblyIntent,
        target_part_name: str,
        action: Dict[str, Any],
    ) -> AssemblyIntent:
        """Apply a single-part placement action."""
        intent = copy.deepcopy(intent)
        act = action.get("action", "no_op")

        if act == "set_params":
            new_params = action.get("params", {})
            for p in intent.parts:
                if p.name == target_part_name:
                    p.params.update(new_params)
                    break

        elif act == "add_relation":
            rdata = action.get("relation", {})
            try:
                rel = Relation(
                    rel_type=RelationType(rdata["type"]),
                    source=rdata["source"],
                    target=rdata["target"],
                    axis=rdata.get("axis"),
                    min_dist=rdata.get("min_dist"),
                )
                intent.relations.append(rel)
            except (KeyError, ValueError):
                pass

        elif act == "modify_relation":
            idx = action.get("index", -1)
            changes = action.get("changes", {})
            if 0 <= idx < len(intent.relations):
                rel = intent.relations[idx]
                if "axis" in changes:
                    rel.axis = changes["axis"]
                if "min_dist" in changes:
                    rel.min_dist = changes["min_dist"]

        return intent

    def _compute_incremental_reward(
        self,
        intent: AssemblyIntent,
        boxes: Dict[str, BoundingBox],
        violations: List[Violation],
        solver_errors: List[str],
        new_part_name: str,
    ) -> float:
        """Reward focused on the newly added part."""
        reward = 0.0

        # 1. New part must be solved
        if new_part_name in boxes:
            reward += 5.0
        else:
            reward -= 10.0

        # 2. Penalize violations involving the new part
        for v in violations:
            if new_part_name in v.parts_involved:
                if v.severity == "CRITICAL":
                    reward -= 8.0
                elif v.severity == "WARNING":
                    reward -= 2.0

        # 3. Penalize unsolved parts
        unsolved = [e for e in solver_errors if "UNSOLVED" in e]
        reward -= len(unsolved) * 5.0

        # 4. Penalize solver auto-corrections
        for e in solver_errors:
            if "RULE_" in e:
                reward -= 0.5
            if "CONTACT_VIOLATION" in e:
                reward -= 2.0

        # 5. Bonus if clean
        critical_involving_new = [
            v for v in violations
            if v.severity == "CRITICAL" and new_part_name in v.parts_involved
        ]
        if not critical_involving_new and new_part_name in boxes:
            reward += 5.0

        return round(reward, 2)

    # ------------------------------------------------------------------
    # Phase 4: Optional precise verification via OCP
    # ------------------------------------------------------------------
    def precise_verify(self, intent: AssemblyIntent) -> Optional[Dict[str, Any]]:
        """
        Bridge to skills/industrial_cad/rl/env.py for exact geometry verification.
        Requires the intent to be exportable to constraints.json format.
        """
        if not self.use_precise_verification:
            return None

        # TODO: convert intent to constraints.json and run CADEnv
        # This is a placeholder for integration with the OCP pipeline
        print("[Phase 4] Precise OCP verification not yet integrated (placeholder)")
        return None

    # ------------------------------------------------------------------
    # Main entry point
    # ------------------------------------------------------------------
    def run(self, user_requirement: str) -> Tuple[AssemblyIntent, List[Dict[str, Any]]]:
        print("=" * 60)
        print("Sequential ICRL Assembly Agent")
        print("=" * 60)

        # Phase 1
        skeleton = self.plan_bom(user_requirement)

        # Phase 2 + 3
        best_intent, best_reward = self.sequential_refine(skeleton)

        # Phase 4
        self.precise_verify(best_intent)

        print("\n" + "=" * 60)
        print("RESULT")
        print("=" * 60)
        print(f"Best reward: {best_reward}")
        print(f"Parts: {len(best_intent.parts)}")
        print(f"Relations: {len(best_intent.relations)}")

        return best_intent, self.trajectory


# ==================================================================
# 5. Utilities & Demo
# ==================================================================

def format_intent(intent: AssemblyIntent) -> str:
    lines = [f"AssemblyIntent: {len(intent.parts)} parts, {len(intent.relations)} relations"]
    lines.append("Parts:")
    for p in intent.parts:
        params = ", ".join(f"{k}={v}" for k, v in p.params.items() if not k.startswith("_"))
        lines.append(f"  {p.name}: {p.part_type.value}  ({params})")
    lines.append("Relations:")
    for r in intent.relations:
        axis = f" axis={r.axis}" if r.axis else ""
        md = f" min_dist={r.min_dist}" if r.min_dist else ""
        lines.append(f"  {r.source} --[{r.rel_type.value}]--> {r.target}{axis}{md}")
    return "\n".join(lines)


def save_intent(intent: AssemblyIntent, path: str, metadata: Dict[str, Any]):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w") as f:
        json.dump({
            **metadata,
            "parts": [
                {"name": p.name, "type": p.part_type.value, "params": p.params}
                for p in intent.parts
            ],
            "relations": [
                {"type": r.rel_type.value, "source": r.source, "target": r.target,
                 "axis": r.axis, "min_dist": r.min_dist}
                for r in intent.relations
            ],
        }, f, indent=2, ensure_ascii=False)


def main():
    agent = SequentialICRLAgent(
        max_refinement_iters=4,
        reward_threshold=15.0,
        use_precise_verification=False,
    )

    # Demo: design a pick-and-place station with vibration feeder
    requirement = (
        "Design a pick-and-place automation station with:\n"
        "- A vibration bowl feeder (diameter 200mm) on the right side\n"
        "- A gantry pick-and-place mechanism in the center (span 300mm, height 250mm)\n"
        "- A fixture station on the left side for part locating\n"
        "- All mounted on an 800×500mm aluminum base plate\n"
        "- Horizontal stroke 200mm, vertical stroke 100mm, gripper span 20mm"
    )

    best_intent, trajectory = agent.run(requirement)

    # Save result
    out_path = os.path.join(REPO_ROOT, "checkpoint", "sequential_icrl_result.json")
    save_intent(best_intent, out_path, {
        "requirement": requirement,
        "trajectory_length": len(trajectory),
    })
    print(f"\nSaved result to: {out_path}")

    # Final solver + verifier report
    print("\n" + "=" * 60)
    print("Final Verification Report")
    print("=" * 60)
    solver = AssemblySolver(best_intent)
    boxes = solver.solve()
    verifier = AssemblyVerifier(boxes)
    verifier.verify_all()
    verifier.print_report()


if __name__ == "__main__":
    main()
