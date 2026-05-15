#!/usr/bin/env python3
"""
SkillEnv — High-level RL environment for learning Auto-Repair strategies.

The agent learns WHICH repair primitive to apply, not raw placement deltas.
This is a discrete-action MDP with a small action space (~12 actions),
making PPO much more sample-efficient than the 24D continuous parameter space.

Repair Primitives (Actions):
  0-5:  MOVE_X/Y/Z(part, +/-step)  — direct placement adjustment
  6-7:  ROTATE_Z(part, +/-step)     — rotation adjustment
  8-9:  INCREASE/DECREASE_DISTANCE(part, axis) — modify constraint value
  10:   REORDER_CONSTRAINTS         — change solve priority
  11:   DONE                        — stop repair

State (Observation):
  - Interference matrix (n_parts × n_parts)
  - Gap error matrix (n_parts × 4 axes)
  - Current placements (n_parts × 4)
  - Last action reward (scalar)
  - Step count (normalized)
  - Previous action (one-hot)
"""
from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

import gymnasium as gym
import numpy as np

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from env import CADEnv


class SkillAction:
    """Repair primitive definitions."""
    MOVE_XP = 0   # Move part +X
    MOVE_XN = 1   # Move part -X
    MOVE_YP = 2
    MOVE_YN = 3
    MOVE_ZP = 4
    MOVE_ZN = 5
    ROT_ZP = 6
    ROT_ZN = 7
    INC_DIST = 8  # Increase Distance constraint
    DEC_DIST = 9  # Decrease Distance constraint
    REORDER = 10
    DONE = 11

    NAMES = [
        "MOVE_X+", "MOVE_X-", "MOVE_Y+", "MOVE_Y-",
        "MOVE_Z+", "MOVE_Z-", "ROT_Z+", "ROT_Z-",
        "INC_DIST", "DEC_DIST", "REORDER", "DONE",
    ]

    N_ACTIONS = 12


class RepairSkillEnv(gym.Env):
    """
    Model-free RL environment where the agent learns repair strategies.

    Episode flow:
      1. Start from a perturbed/failed assembly state
      2. Agent selects a repair primitive
      3. Environment applies the primitive and re-verifies
      4. Reward = improvement in verification score
      5. Episode ends when all checks pass or max_steps reached

    Action masking: Invalid actions (e.g. INC_DIST when no Distance constraints)
    are detected at runtime and penalized rather than masked, because
    Stable-Baselines3's PPO does not natively support action masks for Discrete spaces.
    """

    metadata = {"render_modes": ["human"]}

    def __init__(
        self,
        constraints_path: str | Path,
        parts_dir: str | Path | None = None,
        perturbation: float = 15.0,
        max_steps: int = 30,
        step_size: float = 5.0,
        rot_step_size: float = 5.0,
        dist_delta: float = 5.0,
        verbose: bool = False,
        fast_mode: bool = True,
    ):
        super().__init__()
        self.verbose = verbose
        self.perturbation = perturbation
        self.max_steps = max_steps
        self.step_size = step_size
        self.rot_step_size = rot_step_size
        self.dist_delta = dist_delta
        self.fast_mode = fast_mode

        # Low-level CAD environment (for geometry verification)
        self.cad_env = CADEnv(
            constraints_path=constraints_path,
            parts_dir=parts_dir,
            step_size=step_size,
            rot_step_size=rot_step_size,
            max_steps=1,
            geometry_check_interval=1,
        )

        self.n_parts = self.cad_env.n_parts
        self.n_movable = self.cad_env.n_movable
        self.part_ids = self.cad_env.part_ids
        self.movable_part_ids = self.cad_env.movable_part_ids

        # Action space: discrete choice of repair primitive
        self.action_space = gym.spaces.Discrete(SkillAction.N_ACTIONS)

        # Observation space
        obs_dim = (
            self.n_parts * self.n_parts +      # interference matrix
            self.n_parts * 4 +                  # gap matrix
            self.n_parts * 4 +                  # placements
            1 +                                 # last reward
            1 +                                 # normalized step
            SkillAction.N_ACTIONS               # previous action one-hot
        )
        self.observation_space = gym.spaces.Box(
            low=-np.inf, high=np.inf, shape=(obs_dim,), dtype=np.float32
        )

        # Episode state
        self.step_count = 0
        self.last_reward = 0.0
        self.prev_action = SkillAction.DONE
        self.best_reward = -float("inf")
        self.best_step = 0
        self.repair_history = []
        self.action_mask = np.ones(SkillAction.N_ACTIONS, dtype=np.int32)

    # ------------------------------------------------------------------
    # Action validity
    # ------------------------------------------------------------------
    def _compute_action_mask(self, report: dict) -> np.ndarray:
        """Determine which actions are currently meaningful."""
        mask = np.ones(SkillAction.N_ACTIONS, dtype=np.int32)

        # MOVE/ROT actions are always valid if there are movable parts
        if not self.movable_part_ids:
            mask[:8] = 0  # Disable all move/rotate

        # INC_DIST/DEC_DIST only valid if Distance constraints exist
        has_distance = any(
            c.get("type") == "Distance"
            for c in self.cad_env.constraints_data.get("constraints", [])
        )
        if not has_distance:
            mask[SkillAction.INC_DIST] = 0
            mask[SkillAction.DEC_DIST] = 0

        # REORDER only valid if there are multiple constraints
        if len(self.cad_env.constraints_data.get("constraints", [])) <= 2:
            mask[SkillAction.REORDER] = 0

        return mask

    def _is_action_valid(self, action: int, report: dict) -> bool:
        """Check if an action makes sense in the current state."""
        mask = self._compute_action_mask(report)
        return bool(mask[action])

    def _verify(self) -> dict:
        """Run verification — fast bbox-only or full OCP depending on mode."""
        if not self.fast_mode:
            return self.cad_env._verify()

        # Fast mode: bbox-only proxy (no OCP calls, ~1ms)
        interferences = []
        clearance_warnings = []
        bboxes = {}
        for pid in self.part_ids:
            p = self.cad_env.placements[pid]
            bb = self.cad_env.part_bboxes[pid]
            rz = math.radians(p["rz"])
            cr, sr = math.cos(rz), math.sin(rz)
            tx, ty, tz = p["x"], p["y"], p["z"]
            corners = [
                (bb[0], bb[1], bb[2]), (bb[0], bb[1], bb[5]),
                (bb[0], bb[4], bb[2]), (bb[0], bb[4], bb[5]),
                (bb[3], bb[1], bb[2]), (bb[3], bb[1], bb[5]),
                (bb[3], bb[4], bb[2]), (bb[3], bb[4], bb[5]),
            ]
            xs = [cr * x - sr * y + tx for x, y, z in corners]
            ys = [sr * x + cr * y + ty for x, y, z in corners]
            zs = [z + tz for x, y, z in corners]
            bboxes[pid] = (min(xs), min(ys), min(zs), max(xs), max(ys), max(zs))

        for i, pa in enumerate(self.part_ids):
            for pb in self.part_ids[i + 1:]:
                ba, bb = bboxes[pa], bboxes[pb]
                # Bbox overlap check
                overlap = (
                    ba[0] < bb[3] and ba[3] > bb[0] and
                    ba[1] < bb[4] and ba[4] > bb[1] and
                    ba[2] < bb[5] and ba[5] > bb[2]
                )
                if overlap and not self.cad_env._is_allowed_overlap(pa, pb):
                    # Estimate overlap volume proxy
                    dx = min(ba[3], bb[3]) - max(ba[0], bb[0])
                    dy = min(ba[4], bb[4]) - max(ba[1], bb[1])
                    dz = min(ba[5], bb[5]) - max(ba[2], bb[2])
                    vol = max(0, dx) * max(0, dy) * max(0, dz)
                    if vol > 0.1:
                        interferences.append({
                            "part_a": pa, "part_b": pb, "volume": round(vol, 1),
                        })
                    continue
                # Bbox clearance check
                if not overlap:
                    gap_x = max(0, max(ba[0], bb[0]) - min(ba[3], bb[3]))
                    gap_y = max(0, max(ba[1], bb[1]) - min(ba[4], bb[4]))
                    gap_z = max(0, max(ba[2], bb[2]) - min(ba[5], bb[5]))
                    min_gap = max(gap_x, gap_y, gap_z)
                    if 0 < min_gap < self.cad_env.min_gap_threshold:
                        clearance_warnings.append({
                            "part_a": pa, "part_b": pb,
                            "distance": round(min_gap, 3),
                            "threshold": self.cad_env.min_gap_threshold,
                        })

        # Constraint gap check (always fast)
        expected = self.cad_env._initial_placements()
        gap_errors = []
        for pid in self.part_ids:
            e = expected[pid]
            a = self.cad_env.placements[pid]
            for axis in ("x", "y", "z"):
                err = abs(a[axis] - e[axis])
                if err > 0.5:
                    gap_errors.append({
                        "part": pid, "axis": axis,
                        "expected": round(e[axis], 2), "actual": round(float(a[axis]), 2),
                        "error": round(err, 2),
                    })
            rz_err = abs(a["rz"] - e["rz"])
            if rz_err > 180:
                rz_err = 360 - rz_err
            if rz_err > 0.5:
                gap_errors.append({
                    "part": pid, "axis": "rz",
                    "expected": round(e["rz"], 2), "actual": round(float(a["rz"]), 2),
                    "error": round(rz_err, 2),
                })

        all_passed = len(interferences) == 0 and len(gap_errors) == 0 and len(clearance_warnings) == 0
        return {
            "interferences": interferences,
            "gap_errors": gap_errors,
            "clearance_warnings": clearance_warnings,
            "all_passed": all_passed,
        }

    # ------------------------------------------------------------------
    # Gymnasium API
    # ------------------------------------------------------------------
    def reset(self, seed: int | None = None, options: dict | None = None):
        super().reset(seed=seed)
        self.step_count = 0
        self.last_reward = 0.0
        self.prev_action = SkillAction.DONE
        self.best_reward = -float("inf")
        self.best_step = 0
        self.repair_history = []

        # Start from perturbed state
        pert = (options or {}).get("perturbation", self.perturbation)
        self.cad_env.reset(options={"perturbation": pert})

        # Run initial verification
        report = self._verify()
        self.initial_score = self._score(report)
        self.last_score = self.initial_score

        obs = self._get_obs(report)
        self.action_mask = self._compute_action_mask(report)
        info = {"report": report, "initial_score": self.initial_score}
        return obs, info

    def step(self, action: int):
        self.step_count += 1
        action = int(action)
        self.prev_action = action

        # Get state before action
        report_before = self._verify()

        # Check action validity
        valid = self._is_action_valid(action, report_before)

        # Apply repair primitive (only if valid; invalid gets no-op)
        if valid:
            self._apply_primitive(action)
        report_after = self._verify()

        # Compute reward based on improvement
        score_before = self._score(report_before)
        score_after = self._score(report_after)
        improvement = score_after - score_before

        # Reward shaping
        reward = improvement * 10.0  # Scale up improvements
        if not valid:
            reward -= 5.0  # Penalty for choosing invalid action
        if action == SkillAction.DONE:
            reward += 5.0 if report_after["all_passed"] else -10.0
        elif report_after["all_passed"]:
            reward += 20.0  # Bonus for reaching all-passed

        self.last_reward = reward
        self.last_score = score_after

        if score_after > self.best_reward:
            self.best_reward = score_after
            self.best_step = self.step_count

        self.repair_history.append({
            "step": self.step_count,
            "action": SkillAction.NAMES[action],
            "score_before": score_before,
            "score_after": score_after,
            "reward": reward,
        })

        terminated = bool(report_after["all_passed"]) or action == SkillAction.DONE
        truncated = self.step_count >= self.max_steps

        obs = self._get_obs(report_after)
        self.action_mask = self._compute_action_mask(report_after)
        info = {"report": report_after, "improvement": improvement}

        if self.verbose and (self.step_count <= 3 or report_after["all_passed"]):
            status = " " if valid else "[INVALID]"
            print(f"  Step {self.step_count}: {status}{SkillAction.NAMES[action]:12s} "
                  f"score={score_after:6.1f} ({improvement:+.1f}) reward={reward:+.1f}")

        return obs, float(reward), terminated, truncated, info

    def render(self):
        if self.verbose:
            print(f"\nRepair history (best at step {self.best_step}, score={self.best_reward:.1f}):")
            for h in self.repair_history:
                print(f"  {h['step']:2d}. {h['action']:12s}  score={h['score_after']:6.1f}  reward={h['reward']:+.1f}")

    # ------------------------------------------------------------------
    # Repair primitives
    # ------------------------------------------------------------------
    def _apply_primitive(self, action: int):
        """Apply a repair primitive to the current state."""
        if action == SkillAction.DONE:
            return

        # Select target part: the one with the worst score contribution
        target_part = self._select_target_part()
        if target_part is None:
            return

        if action in (SkillAction.MOVE_XP, SkillAction.MOVE_XN):
            delta = self.step_size if action == SkillAction.MOVE_XP else -self.step_size
            self.cad_env.placements[target_part]["x"] += delta

        elif action in (SkillAction.MOVE_YP, SkillAction.MOVE_YN):
            delta = self.step_size if action == SkillAction.MOVE_YP else -self.step_size
            self.cad_env.placements[target_part]["y"] += delta

        elif action in (SkillAction.MOVE_ZP, SkillAction.MOVE_ZN):
            delta = self.step_size if action == SkillAction.MOVE_ZP else -self.step_size
            self.cad_env.placements[target_part]["z"] += delta

        elif action in (SkillAction.ROT_ZP, SkillAction.ROT_ZN):
            delta = self.rot_step_size if action == SkillAction.ROT_ZP else -self.rot_step_size
            self.cad_env.placements[target_part]["rz"] += delta

        elif action in (SkillAction.INC_DIST, SkillAction.DEC_DIST):
            self._adjust_distance_constraint(target_part, +1 if action == SkillAction.INC_DIST else -1)

        elif action == SkillAction.REORDER:
            self._reorder_constraints()

    def _select_target_part(self) -> str | None:
        """Heuristic: select the part most involved in errors."""
        report = self._verify()
        error_count = {pid: 0 for pid in self.part_ids}

        for interf in report["interferences"]:
            error_count[interf["part_a"]] += 1
            error_count[interf["part_b"]] += 1
        for gap in report["gap_errors"]:
            error_count[gap["part"]] += 1
        for warn in report["clearance_warnings"]:
            error_count[warn["part_a"]] += 1
            error_count[warn["part_b"]] += 1

        # Pick movable part with most errors
        movable_errors = {pid: error_count[pid] for pid in self.movable_part_ids}
        if not any(movable_errors.values()):
            # No errors — pick a random movable part for exploration
            return self.np_random.choice(self.movable_part_ids)
        return max(movable_errors, key=movable_errors.get)

    def _adjust_distance_constraint(self, part: str, direction: int):
        """Adjust the Distance constraint for the given part."""
        constraints = self.cad_env.constraints_data.get("constraints", [])
        for c in constraints:
            if c.get("type") == "Distance" and c.get("part_a") == part:
                axis = c.get("axis", "z")
                c["value"] = float(c.get("value", 0)) + direction * self.dist_delta
                break

    def _reorder_constraints(self):
        """Shuffle constraint priority to explore different solve orders."""
        constraints = self.cad_env.constraints_data.get("constraints", [])
        if len(constraints) > 2:
            # Move a random non-Fix constraint to the front
            non_fix = [i for i, c in enumerate(constraints) if c.get("type") != "Fix"]
            if non_fix:
                idx = self.np_random.choice(non_fix)
                c = constraints.pop(idx)
                constraints.insert(1, c)  # After Fix

    # ------------------------------------------------------------------
    # Scoring & observation
    # ------------------------------------------------------------------
    def _score(self, report: dict) -> float:
        """Compute a scalar score from verification report (higher is better)."""
        s = 0.0
        s -= 10.0 * len(report["interferences"])
        s -= 5.0 * len(report["gap_errors"])
        s -= 1.0 * len(report["clearance_warnings"])
        if report["all_passed"]:
            s += 100.0
        return s

    def _get_obs(self, report: dict) -> np.ndarray:
        """Build observation vector from verification report."""
        n = self.n_parts
        part_idx = {pid: i for i, pid in enumerate(self.part_ids)}

        # Interference matrix (symmetric)
        interf_mat = np.zeros((n, n), dtype=np.float32)
        for interf in report["interferences"]:
            i = part_idx[interf["part_a"]]
            j = part_idx[interf["part_b"]]
            interf_mat[i, j] = interf_mat[j, i] = 1.0

        # Gap matrix (part × axis)
        gap_mat = np.zeros((n, 4), dtype=np.float32)
        axis_idx = {"x": 0, "y": 1, "z": 2, "rz": 3}
        for gap in report["gap_errors"]:
            i = part_idx[gap["part"]]
            a = axis_idx.get(gap["axis"], 0)
            gap_mat[i, a] = gap["error"] / 100.0  # Normalize

        # Placements
        placements = np.zeros((n, 4), dtype=np.float32)
        for i, pid in enumerate(self.part_ids):
            p = self.cad_env.placements[pid]
            placements[i] = [p["x"] / 500.0, p["y"] / 500.0, p["z"] / 500.0, p["rz"] / 180.0]

        # Last reward
        last_r = np.array([self.last_reward / 100.0], dtype=np.float32)

        # Normalized step
        step = np.array([self.step_count / self.max_steps], dtype=np.float32)

        # Previous action one-hot
        prev_act = np.zeros(SkillAction.N_ACTIONS, dtype=np.float32)
        prev_act[self.prev_action] = 1.0

        obs = np.concatenate([
            interf_mat.flatten(),
            gap_mat.flatten(),
            placements.flatten(),
            last_r,
            step,
            prev_act,
        ])
        return obs

    def export_best_state(self, out_path: str | Path):
        """Export the best-found placements."""
        self.cad_env.export_best_placements(out_path)
