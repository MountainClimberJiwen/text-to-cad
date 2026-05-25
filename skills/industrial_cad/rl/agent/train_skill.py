#!/usr/bin/env python3
"""
Train a Repair Skill Agent using PPO on discrete repair primitives.

This trains the agent to learn WHICH repair action to apply, not raw deltas.
The small discrete action space (12 actions) makes PPO much more sample-efficient
than the 24D continuous parameter optimization.

Usage:
    ./.venv/bin/python skills/industrial_cad/rl/agent/train_skill.py \
        --constraints models/assemblies/vibratory_feeder_assembly.constraints.json \
        --total-timesteps 10000 \
        --output-model /tmp/skill_agent.zip
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from skill_env import RepairSkillEnv


def train_skill_agent(
    env: RepairSkillEnv,
    total_timesteps: int = 10000,
    n_steps: int = 256,
    verbose: int = 1,
):
    """Train PPO on the skill environment."""
    try:
        from stable_baselines3 import PPO
    except ImportError:
        print("ERROR: stable-baselines3 not installed. Run: pip install stable-baselines3", file=sys.stderr)
        sys.exit(1)

    model = PPO(
        "MlpPolicy",
        env,
        verbose=verbose,
        learning_rate=3e-4,
        n_steps=n_steps,
        batch_size=min(64, n_steps),
        n_epochs=5,
        gamma=0.99,
        gae_lambda=0.95,
        clip_range=0.2,
        ent_coef=0.05,  # Higher entropy for exploration
    )

    print(f"Training skill agent: {total_timesteps} steps, n_steps={n_steps}")
    t0 = time.time()
    model.learn(total_timesteps=total_timesteps)
    elapsed = time.time() - t0
    print(f"Training complete in {elapsed:.1f}s ({total_timesteps/elapsed:.1f} steps/sec)")
    return model


def evaluate_skill(env: RepairSkillEnv, model, n_episodes: int = 10, perturbation: float = 15.0):
    """Evaluate the trained skill agent."""
    print(f"\nEvaluating skill agent ({n_episodes} episodes, σ={perturbation}mm)...")
    results = []

    for ep in range(n_episodes):
        obs, info = env.reset(options={"perturbation": perturbation})
        done = False
        ep_reward = 0.0
        steps = 0
        while not done:
            action, _ = model.predict(obs, deterministic=True)
            obs, reward, terminated, truncated, info = env.step(action)
            ep_reward += reward
            done = terminated or truncated
            steps += 1

        report = info["report"]
        passed = report["all_passed"]
        results.append({
            "reward": ep_reward,
            "steps": steps,
            "passed": passed,
            "interferences": len(report["interferences"]),
            "gaps": len(report["gap_errors"]),
        })
        status = "✅" if passed else "❌"
        print(f"  {status} Ep {ep+1}: reward={ep_reward:7.1f}, steps={steps:2d}, "
              f"interf={len(report['interferences'])}, gaps={len(report['gap_errors'])}, passed={passed}")

    pass_rate = sum(1 for r in results if r["passed"]) / n_episodes
    mean_reward = np.mean([r["reward"] for r in results])
    mean_steps = np.mean([r["steps"] for r in results])
    print(f"\nPass rate: {pass_rate*100:.0f}%")
    print(f"Mean reward: {mean_reward:.1f}")
    print(f"Mean steps to resolve: {mean_steps:.1f}")
    return results


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Train repair skill agent")
    parser.add_argument("--constraints", type=Path, required=True)
    parser.add_argument("--parts-dir", type=Path, default=None)
    parser.add_argument("--total-timesteps", type=int, default=5000)
    parser.add_argument("--perturbation", type=float, default=15.0)
    parser.add_argument("--max-steps", type=int, default=30)
    parser.add_argument("--n-steps", type=int, default=256)
    parser.add_argument("--eval-episodes", type=int, default=10)
    parser.add_argument("--output-model", type=Path, default=None)
    parser.add_argument("--verbose", type=int, default=1)
    args = parser.parse_args(argv)

    # Create environment
    env = RepairSkillEnv(
        constraints_path=args.constraints,
        parts_dir=args.parts_dir,
        perturbation=args.perturbation,
        max_steps=args.max_steps,
        verbose=args.verbose >= 2,
    )

    # Baseline: random policy
    print("=" * 60)
    print("Baseline: Random Policy")
    print("=" * 60)
    obs, info = env.reset(options={"perturbation": args.perturbation})
    random_rewards = []
    for _ in range(5):
        obs, info = env.reset(options={"perturbation": args.perturbation})
        ep_reward = 0.0
        done = False
        while not done:
            action = env.action_space.sample()
            obs, reward, terminated, truncated, info = env.step(action)
            ep_reward += reward
            done = terminated or truncated
        random_rewards.append(ep_reward)
    print(f"Random mean reward: {np.mean(random_rewards):.1f} ± {np.std(random_rewards):.1f}")

    # Train
    print("\n" + "=" * 60)
    print("Training Repair Skill Agent (PPO)")
    print("=" * 60)
    model = train_skill_agent(env, total_timesteps=args.total_timesteps, n_steps=args.n_steps, verbose=args.verbose)

    # Evaluate
    print("\n" + "=" * 60)
    print("Evaluation: Clean State")
    print("=" * 60)
    evaluate_skill(env, model, n_episodes=args.eval_episodes, perturbation=0.0)

    print("\n" + "=" * 60)
    print(f"Evaluation: Perturbed State (σ={args.perturbation}mm)")
    print("=" * 60)
    evaluate_skill(env, model, n_episodes=args.eval_episodes, perturbation=args.perturbation)

    # Save
    if args.output_model:
        model.save(args.output_model)
        print(f"\nModel saved to: {args.output_model}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
