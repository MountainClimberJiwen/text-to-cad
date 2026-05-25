#!/usr/bin/env python3
"""
CAD Assembly Placement Optimizer — Black-box optimization.

Uses scipy.optimize.differential_evolution with a TWO-STAGE strategy:
  Stage 1: Fast constraint-gap-only objective for 95% of evaluations (~0ms each)
  Stage 2: Full OCP geometry verification only on promising candidates

This makes 24D optimization practical: 1000+ evals in <1 minute.

Usage:
    ./.venv/bin/python skills/industrial_cad/rl/optimize.py \
        --constraints models/assemblies/vibratory_feeder_assembly.constraints.json \
        --perturbation 15.0 \
        --max-iter 30 \
        --output models/assemblies/vibratory_feeder_assembly.opt.placements.json
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np
from scipy.optimize import differential_evolution, minimize

sys.path.insert(0, str(Path(__file__).resolve().parent))
from env import CADEnv


class FastPlacementOptimizer:
    """
    Two-stage optimizer:
      - Fast objective: _fast_verify (constraint gaps only, ~0ms)
      - Slow objective: _verify (full OCP geometry, ~2.5s)
    """

    def __init__(self, env: CADEnv, perturbation: float = 15.0, full_check_interval: int = 20):
        self.env = env
        self.perturbation = perturbation
        self.full_check_interval = full_check_interval
        self.n_dims = env.n_movable * 4
        self.bounds = [(-3.0, 3.0)] * self.n_dims
        self.eval_count = 0
        self.full_check_count = 0
        self.best_reward = -float("inf")
        self.best_x = None
        self.best_placements = None
        self.history = []

    def _set_placements(self, x: np.ndarray):
        """Apply candidate adjustment to placements (relative to initial)."""
        # Start from initial (constraint-derived) placements
        initial = self.env._initial_placements()
        for i, pid in enumerate(self.env.movable_part_ids):
            idx = i * 4
            p = initial[pid]
            self.env.placements[pid] = {
                "x": p["x"] + x[idx + 0] * self.env.step_size,
                "y": p["y"] + x[idx + 1] * self.env.step_size,
                "z": p["z"] + x[idx + 2] * self.env.step_size,
                "rz": p["rz"] + x[idx + 3] * self.env.rot_step_size,
            }

    def objective(self, x: np.ndarray) -> float:
        """Two-stage objective: fast most of the time, full check occasionally."""
        self.eval_count += 1
        self._set_placements(x)

        # Stage 1: Fast check (constraint gaps only)
        fast_report = self.env._fast_verify()
        fast_reward = self._compute_reward(fast_report)

        # Stage 2: Full geometry check on promising candidates or periodically
        do_full = (
            fast_reward > self.best_reward * 0.8  # Promising
            or self.eval_count % self.full_check_interval == 0  # Periodic
        )

        if do_full:
            self.full_check_count += 1
            full_report = self.env._verify()
            # Merge: use full report's interferences, fast report's gaps
            report = {
                "interferences": full_report["interferences"],
                "gap_errors": fast_report["gap_errors"],
                "clearance_warnings": full_report["clearance_warnings"],
                "all_passed": (
                    len(full_report["interferences"]) == 0
                    and len(fast_report["gap_errors"]) == 0
                    and len(full_report["clearance_warnings"]) == 0
                ),
            }
        else:
            report = {
                "interferences": [],  # Unknown without full check
                "gap_errors": fast_report["gap_errors"],
                "clearance_warnings": [],
                "all_passed": False,  # Conservative: assume not passed
            }

        reward = self._compute_reward(report)

        if reward > self.best_reward:
            self.best_reward = reward
            self.best_x = x.copy()
            self.best_placements = {pid: p.copy() for pid, p in self.env.placements.items()}

        self.history.append({
            "eval": self.eval_count,
            "reward": reward,
            "fast_reward": fast_reward,
            "full_check": do_full,
            "interferences": len(report["interferences"]),
            "gap_errors": len(report["gap_errors"]),
            "passed": report["all_passed"],
        })

        return -reward

    def _compute_reward(self, report: dict) -> float:
        w = self.env.reward_weights
        r = 0.0
        r += w["interference"] * len(report["interferences"])
        r += w["gap_error"] * len(report["gap_errors"])
        r += w["clearance_warning"] * len(report["clearance_warnings"])
        if report["all_passed"]:
            r += w["all_passed"]
        return r

    def optimize(self, max_iter: int = 30, pop_size: int = 10) -> dict:
        """Run differential evolution."""
        print(f"DE: max_iter={max_iter}, pop_size={pop_size}, dims={self.n_dims}")
        print(f"Strategy: fast check every eval, full check every {self.full_check_interval} evals + on promising candidates")
        t0 = time.perf_counter()

        result = differential_evolution(
            self.objective,
            self.bounds,
            maxiter=max_iter,
            popsize=pop_size,
            tol=0.01,
            polish=True,
            workers=1,
            disp=False,
        )

        elapsed = time.perf_counter() - t0
        print(f"\nDE complete: {self.eval_count} evals ({self.full_check_count} full checks) in {elapsed:.1f}s")
        print(f"Best reward: {-result.fun:.2f}")
        print(f"Speed: {self.eval_count / elapsed:.1f} evals/sec")
        return result

    def local_refinement(self, max_iter: int = 100):
        """Nelder-Mead local refinement starting from DE best."""
        if self.best_x is None:
            return None
        print(f"\nNelder-Mead refinement: max_iter={max_iter}")
        self.eval_count = 0
        self.full_check_count = 0
        t0 = time.perf_counter()

        result = minimize(
            self.objective,
            self.best_x,
            method="Nelder-Mead",
            options={"maxiter": max_iter, "disp": False},
        )

        elapsed = time.perf_counter() - t0
        print(f"NM complete: {self.eval_count} evals ({self.full_check_count} full) in {elapsed:.1f}s")
        print(f"Best reward: {-result.fun:.2f}")
        return result

    def final_verify(self) -> dict:
        """Run full verification on best solution."""
        if self.best_x is not None:
            self._set_placements(self.best_x)
        return self.env._verify()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Optimize CAD assembly placements")
    parser.add_argument("--constraints", type=Path, required=True, help="Path to .constraints.json")
    parser.add_argument("--parts-dir", type=Path, default=None, help="Directory containing part STEP files")
    parser.add_argument("--perturbation", type=float, default=15.0, help="Initial perturbation σ (mm)")
    parser.add_argument("--max-iter", type=int, default=30, help="DE max iterations")
    parser.add_argument("--pop-size", type=int, default=10, help="DE population size multiplier")
    parser.add_argument("--full-check-interval", type=int, default=20, help="Full geometry check every N evals")
    parser.add_argument("--refine", action="store_true", help="Run Nelder-Mead refinement after DE")
    parser.add_argument("--output", type=Path, default=None, help="Output optimized placements JSON")
    parser.add_argument("--step-size", type=float, default=2.0, help="Position step size (mm)")
    parser.add_argument("--rot-step-size", type=float, default=2.0, help="Rotation step size (deg)")
    args = parser.parse_args(argv)

    # Load allowed overlaps
    allowed_path = Path(str(args.constraints).replace(".constraints.json", ".allowed_overlaps.json"))
    allowed_overlaps = []
    if allowed_path.exists():
        allowed_overlaps = json.loads(allowed_path.read_text(encoding="utf-8"))

    env = CADEnv(
        constraints_path=args.constraints,
        parts_dir=args.parts_dir,
        step_size=args.step_size,
        rot_step_size=args.rot_step_size,
        max_steps=1,
        geometry_check_interval=1,
        allowed_overlaps=allowed_overlaps,
    )

    # Baselines
    print("=" * 60)
    print("Baseline (no perturbation)")
    print("=" * 60)
    obs, info = env.reset()
    r = info["report"]
    print(f"Interferences: {len(r['interferences'])}, Gap errors: {len(r['gap_errors'])}, Passed: {r['all_passed']}")

    print(f"\nPerturbed baseline (σ={args.perturbation}mm)")
    obs, info = env.reset(options={"perturbation": args.perturbation})
    r = info["report"]
    print(f"Interferences: {len(r['interferences'])}, Gap errors: {len(r['gap_errors'])}, Passed: {r['all_passed']}")

    # Optimize
    print("\n" + "=" * 60)
    print("Differential Evolution Optimization")
    print("=" * 60)
    opt = FastPlacementOptimizer(env, perturbation=args.perturbation, full_check_interval=args.full_check_interval)
    de_result = opt.optimize(max_iter=args.max_iter, pop_size=args.pop_size)

    # Optional refinement
    if args.refine:
        nm_result = opt.local_refinement(max_iter=100)

    # Final verification
    final_report = opt.final_verify()
    print(f"\nFinal verification (full OCP):")
    print(f"  Interferences: {len(final_report['interferences'])}")
    print(f"  Gap errors:    {len(final_report['gap_errors'])}")
    print(f"  Warnings:      {len(final_report['clearance_warnings'])}")
    print(f"  All passed:    {final_report['all_passed']}")
    for interf in final_report["interferences"]:
        print(f"    🔴 {interf['part_a']} ⟷ {interf['part_b']} (vol={interf['volume']}mm³)")

    # Convergence stats
    passed_count = sum(1 for h in opt.history if h["passed"])
    full_count = sum(1 for h in opt.history if h["full_check"])
    print(f"\nStats: {passed_count}/{len(opt.history)} evals reached all-passed, {full_count} full checks")
    best_rewards = []
    best_so_far = -float("inf")
    for h in opt.history:
        best_so_far = max(best_so_far, h["reward"])
        best_rewards.append(best_so_far)
    print(f"Reward: {best_rewards[0]:.1f} → {best_rewards[-1]:.1f}")

    # Save
    if args.output and opt.best_placements:
        env.placements = opt.best_placements
        env.export_best_placements(args.output)
        print(f"\nSaved to: {args.output}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
