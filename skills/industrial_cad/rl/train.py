#!/usr/bin/env python3
"""
CAD-RL Training Script — PPO-based optimization of CAD assembly placements.

Usage:
    ./.venv/bin/python skills/industrial_cad/rl/train.py \
        --constraints models/assemblies/vibratory_feeder_assembly.constraints.json \
        --total-timesteps 5000 \
        --perturbation 15.0 \
        --output models/assemblies/vibratory_feeder_assembly.rl.placements.json
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from env import CADEnv


def make_vec_env(env, n_envs: int = 1, perturbation: float = 0.0):
    """Create vectorized environments for faster training."""
    from gymnasium.vector import SyncVectorEnv
    def _make():
        def _init():
            # Clone env and set perturbation
            new_env = CADEnv(
                constraints_path=env.constraints_path,
                parts_dir=env.parts_dir,
                step_size=env.step_size,
                rot_step_size=env.rot_step_size,
                max_steps=env.max_steps,
                geometry_check_interval=env.geometry_check_interval,
                allowed_overlaps=env.allowed_overlaps,
            )
            new_env._perturbation = perturbation
            # Monkey-patch reset to use perturbation
            orig_reset = new_env.reset
            def reset_with_perturb(seed=None, options=None):
                opts = options or {}
                if perturbation > 0:
                    opts["perturbation"] = perturbation
                return orig_reset(seed=seed, options=opts)
            new_env.reset = reset_with_perturb
            return new_env
        return _init
    return SyncVectorEnv([_make() for _ in range(n_envs)])


def train_ppo(env, total_timesteps: int = 10000, n_steps: int = 128, verbose: int = 1):
    """Train a PPO agent on the CAD environment."""
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
        ent_coef=0.01,
    )

    print(f"Training PPO for {total_timesteps} timesteps (n_steps={n_steps})...")
    t0 = time.perf_counter()
    model.learn(total_timesteps=total_timesteps)
    elapsed = time.perf_counter() - t0
    print(f"Training complete in {elapsed:.1f}s")
    return model


def evaluate_policy(env, model, n_episodes: int = 5, perturbation: float = 0.0):
    """Evaluate a trained policy."""
    print(f"\nEvaluating policy ({n_episodes} episodes, perturbation={perturbation}mm)...")
    all_rewards = []
    all_reports = []

    for ep in range(n_episodes):
        options = {"perturbation": perturbation} if perturbation > 0 else {}
        obs, info = env.reset(options=options)
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
        all_rewards.append(ep_reward)
        all_reports.append(report)
        print(f"  Episode {ep+1}: reward={ep_reward:.2f}, steps={steps}, "
              f"interferences={len(report['interferences'])}, "
              f"gap_errors={len(report['gap_errors'])}, "
              f"warnings={len(report['clearance_warnings'])}, "
              f"passed={report['all_passed']}")

    print(f"\nMean reward: {np.mean(all_rewards):.2f} ± {np.std(all_rewards):.2f}")
    pass_rate = sum(1 for r in all_reports if r["all_passed"]) / n_episodes
    print(f"Pass rate: {pass_rate*100:.0f}%")
    return all_rewards, all_reports


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Train RL agent to optimize CAD assembly placements")
    parser.add_argument("--constraints", type=Path, required=True, help="Path to .constraints.json")
    parser.add_argument("--parts-dir", type=Path, default=None, help="Directory containing part STEP files")
    parser.add_argument("--total-timesteps", type=int, default=5000, help="Total training timesteps")
    parser.add_argument("--perturbation", type=float, default=10.0, help="Initial placement perturbation σ (mm)")
    parser.add_argument("--output", type=Path, default=None, help="Output best placements JSON")
    parser.add_argument("--model-path", type=Path, default=None, help="Save trained model to this path")
    parser.add_argument("--eval-episodes", type=int, default=5, help="Number of evaluation episodes")
    parser.add_argument("--step-size", type=float, default=2.0, help="Position action step size (mm)")
    parser.add_argument("--rot-step-size", type=float, default=2.0, help="Rotation action step size (deg)")
    parser.add_argument("--max-steps", type=int, default=50, help="Max steps per episode")
    parser.add_argument("--geometry-check-interval", type=int, default=5, help="Full geometry check interval")
    parser.add_argument("--verbose", type=int, default=1, help="Verbosity level")
    args = parser.parse_args(argv)

    # Load allowed overlaps if present
    allowed_overlaps_path = Path(str(args.constraints).replace(".constraints.json", ".allowed_overlaps.json"))
    allowed_overlaps = []
    if allowed_overlaps_path.exists():
        allowed_overlaps = json.loads(allowed_overlaps_path.read_text(encoding="utf-8"))

    # Create environment
    env = CADEnv(
        constraints_path=args.constraints,
        parts_dir=args.parts_dir,
        step_size=args.step_size,
        rot_step_size=args.rot_step_size,
        max_steps=args.max_steps,
        geometry_check_interval=args.geometry_check_interval,
        allowed_overlaps=allowed_overlaps,
    )

    # Baseline
    print("=" * 60)
    print("Baseline: Initial placement from constraints.json")
    print("=" * 60)
    obs, info = env.reset()
    report = info["report"]
    print(f"Interferences: {len(report['interferences'])}")
    print(f"Gap errors:    {len(report['gap_errors'])}")
    print(f"Warnings:      {len(report['clearance_warnings'])}")
    print(f"All passed:    {report['all_passed']}")
    for interf in report["interferences"]:
        print(f"  🔴 {interf['part_a']} ⟷ {interf['part_b']} (vol={interf['volume']}mm³)")

    # Perturbed baseline
    if args.perturbation > 0:
        print(f"\nPerturbed baseline (σ={args.perturbation}mm):")
        obs, info = env.reset(options={"perturbation": args.perturbation})
        report = info["report"]
        print(f"Interferences: {len(report['interferences'])}")
        print(f"Gap errors:    {len(report['gap_errors'])}")
        print(f"All passed:    {report['all_passed']}")

    # Train
    print("\n" + "=" * 60)
    print("Training PPO Agent")
    print("=" * 60)
    adaptive_n_steps = min(2048, max(args.total_timesteps // 10, 64), args.max_steps * 2)
    print(f"  n_steps={adaptive_n_steps}, total_timesteps={args.total_timesteps}, perturbation={args.perturbation}mm")

    # Wrap env with perturbation
    def make_env():
        def _init():
            e = CADEnv(
                constraints_path=args.constraints,
                parts_dir=args.parts_dir,
                step_size=args.step_size,
                rot_step_size=args.rot_step_size,
                max_steps=args.max_steps,
                geometry_check_interval=args.geometry_check_interval,
                allowed_overlaps=allowed_overlaps,
            )
            return e
        return _init

    from stable_baselines3.common.env_util import make_vec_env as sb3_make_vec_env
    vec_env = sb3_make_vec_env(make_env(), n_envs=1)
    model = train_ppo(vec_env, total_timesteps=args.total_timesteps, n_steps=adaptive_n_steps, verbose=args.verbose)

    # Evaluate without perturbation
    rewards_clean, reports_clean = evaluate_policy(env, model, n_episodes=args.eval_episodes, perturbation=0.0)

    # Evaluate with perturbation
    if args.perturbation > 0:
        rewards_pert, reports_pert = evaluate_policy(env, model, n_episodes=args.eval_episodes, perturbation=args.perturbation)

    # Save best placements from clean eval
    best_ep = max(range(len(rewards_clean)), key=lambda i: rewards_clean[i])
    if reports_clean[best_ep]["all_passed"]:
        print(f"\n✅ Best episode {best_ep+1} passed all checks!")
    else:
        print(f"\n⚠️  Best episode {best_ep+1} did not fully pass.")

    # Save model
    if args.model_path:
        model.save(args.model_path)
        print(f"Model saved to: {args.model_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
