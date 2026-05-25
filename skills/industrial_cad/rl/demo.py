#!/usr/bin/env python3
"""
CAD-RL Demo — 快速演示环境交互与随机策略基准。

Usage:
    ./.venv/bin/python skills/industrial_cad/rl/demo.py \
        --constraints models/assemblies/vibratory_feeder_assembly.constraints.json
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from env import CADEnv


def random_policy_demo(env: CADEnv, n_episodes: int = 3, max_steps: int = 20):
    """Run random policy as baseline."""
    print("=" * 60)
    print("Random Policy Baseline")
    print("=" * 60)

    for ep in range(n_episodes):
        obs, info = env.reset()
        ep_reward = 0.0
        steps = 0
        done = False

        while not done and steps < max_steps:
            action = env.action_space.sample()
            obs, reward, terminated, truncated, info = env.step(action)
            ep_reward += reward
            done = terminated or truncated
            steps += 1

        report = info["report"]
        print(f"\nEpisode {ep+1}: steps={steps}, reward={ep_reward:.2f}")
        print(f"  Interferences: {len(report['interferences'])}")
        print(f"  Gap errors:    {len(report['gap_errors'])}")
        print(f"  Warnings:      {len(report['clearance_warnings'])}")
        print(f"  Passed:        {report['all_passed']}")
        for interf in report["interferences"]:
            print(f"    🔴 {interf['part_a']} ⟷ {interf['part_b']} (vol={interf['volume']}mm³)")


def zero_action_demo(env: CADEnv):
    """Evaluate doing nothing (maintain initial placement)."""
    print("\n" + "=" * 60)
    print("Zero-Action Policy (maintain initial placement)")
    print("=" * 60)

    obs, info = env.reset()
    ep_reward = 0.0
    steps = 0
    done = False

    while not done and steps < 20:
        action = env.action_space.sample() * 0  # Zero action
        obs, reward, terminated, truncated, info = env.step(action)
        ep_reward += reward
        done = terminated or truncated
        steps += 1

    report = info["report"]
    print(f"Steps: {steps}, Reward: {ep_reward:.2f}")
    print(f"  Interferences: {len(report['interferences'])}")
    print(f"  Gap errors:    {len(report['gap_errors'])}")
    print(f"  Warnings:      {len(report['clearance_warnings'])}")
    print(f"  Passed:        {report['all_passed']}")


def perturbation_repair_demo(env: CADEnv, perturbation: float = 10.0, max_steps: int = 30):
    """Demo: start with perturbed placement, show agent needs to recover."""
    print("\n" + "=" * 60)
    print(f"Perturbation Recovery Demo (σ={perturbation}mm)")
    print("=" * 60)

    obs, info = env.reset(options={"perturbation": perturbation})
    initial_report = info["report"]
    print(f"Initial state: interf={len(initial_report['interferences'])}, "
          f"gaps={len(initial_report['gap_errors'])}, "
          f"passed={initial_report['all_passed']}")

    # Simple greedy recovery: always move towards expected placement
    expected = env._initial_placements()
    ep_reward = 0.0

    for step in range(max_steps):
        # Greedy action: move 20% towards expected
        action = []
        for pid in env.movable_part_ids:
            e = expected[pid]
            a = env.placements[pid]
            action.extend([
                (e["x"] - a["x"]) / env.step_size * 0.2,
                (e["y"] - a["y"]) / env.step_size * 0.2,
                (e["z"] - a["z"]) / env.step_size * 0.2,
                (e["rz"] - a["rz"]) / env.rot_step_size * 0.2,
            ])
        action = env.action_space.sample() * 0  # Not used, we override below

        # Actually we need to use the greedy action, but Gymnasium expects
        # action in [-1, 1]. Let's compute it properly.
        action = []
        for pid in env.movable_part_ids:
            e = expected[pid]
            a = env.placements[pid]
            # Normalize to [-1, 1] range (clamped)
            dx = max(-1, min(1, (e["x"] - a["x"]) / env.step_size * 0.3))
            dy = max(-1, min(1, (e["y"] - a["y"]) / env.step_size * 0.3))
            dz = max(-1, min(1, (e["z"] - a["z"]) / env.step_size * 0.3))
            drz = max(-1, min(1, (e["rz"] - a["rz"]) / env.rot_step_size * 0.3))
            action.extend([dx, dy, dz, drz])
        action = [float(v) for v in action]

        obs, reward, terminated, truncated, info = env.step(action)
        ep_reward += reward

        report = info["report"]
        if step % 5 == 0 or report["all_passed"]:
            print(f"  Step {step+1}: reward={reward:.2f}, "
                  f"interf={len(report['interferences'])}, "
                  f"gaps={len(report['gap_errors'])}, "
                  f"passed={report['all_passed']}")

        if report["all_passed"]:
            print(f"  ✅ Recovered in {step+1} steps! Total reward: {ep_reward:.2f}")
            break
    else:
        print(f"  ⚠️  Not fully recovered after {max_steps} steps. Total reward: {ep_reward:.2f}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="CAD-RL Environment Demo")
    parser.add_argument("--constraints", type=Path, required=True, help="Path to .constraints.json")
    parser.add_argument("--parts-dir", type=Path, default=None, help="Directory containing part STEP files")
    parser.add_argument("--step-size", type=float, default=2.0, help="Position step size (mm)")
    parser.add_argument("--rot-step-size", type=float, default=2.0, help="Rotation step size (deg)")
    parser.add_argument("--geometry-check-interval", type=int, default=5, help="Full geometry check interval")
    args = parser.parse_args(argv)

    # Load allowed overlaps if present alongside constraints file
    allowed_overlaps_path = Path(str(args.constraints).replace(".constraints.json", ".allowed_overlaps.json"))
    allowed_overlaps = []
    if allowed_overlaps_path.exists():
        allowed_overlaps = json.loads(allowed_overlaps_path.read_text(encoding="utf-8"))

    env = CADEnv(
        constraints_path=args.constraints,
        parts_dir=args.parts_dir,
        step_size=args.step_size,
        rot_step_size=args.rot_step_size,
        geometry_check_interval=args.geometry_check_interval,
        allowed_overlaps=allowed_overlaps,
        max_steps=30,
    )

    # 1. Baseline: zero action
    zero_action_demo(env)

    # 2. Random policy
    random_policy_demo(env, n_episodes=2, max_steps=20)

    # 3. Perturbation + greedy recovery
    perturbation_repair_demo(env, perturbation=10.0, max_steps=30)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
