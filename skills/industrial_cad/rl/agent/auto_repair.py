#!/usr/bin/env python3
"""
Auto-Repair Agent — The entry point for the self-evolving CAD repair system.

This module unifies:
  1. **Diagnosis**: Parse constraint/geometry validation reports
  2. **Policy Execution**: Use trained skill agent to choose repair primitives
  3. **Effector**: Apply repairs and verify results
  4. **Learning**: Collect outcomes for continual improvement

Usage:
    # Train a new agent
    ./.venv/bin/python skills/industrial_cad/rl/agent/auto_repair.py train \
        --constraints models/assemblies/vibratory_feeder_assembly.constraints.json \
        --steps 10000

    # Repair a specific assembly with the trained agent
    ./.venv/bin/python skills/industrial_cad/rl/agent/auto_repair.py repair \
        --constraints models/assemblies/vibratory_feeder_assembly.constraints.json \
        --model /tmp/skill_agent.zip

    # Continual evolution — train → collect → fine-tune → repeat
    ./.venv/bin/python skills/industrial_cad/rl/agent/auto_repair.py evolve \
        --constraints models/assemblies/vibratory_feeder_assembly.constraints.json \
        --cycles 5
"""
from __future__ import annotations

import argparse
import json
import random
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from skill_env import RepairSkillEnv
from evolve import CurriculumGenerator, ExperienceBuffer


def cmd_train(argv):
    """Train a fresh skill agent from scratch."""
    parser = argparse.ArgumentParser(description="Train repair skill agent")
    parser.add_argument("--constraints", type=Path, required=True)
    parser.add_argument("--parts-dir", type=Path, default=None)
    parser.add_argument("--steps", type=int, default=10000)
    parser.add_argument("--output", type=Path, default=Path("/tmp/skill_agent.zip"))
    args, _ = parser.parse_known_args(argv)

    env = RepairSkillEnv(
        constraints_path=args.constraints,
        parts_dir=args.parts_dir,
        verbose=False,
    )

    from stable_baselines3 import PPO
    print(f"Training skill agent for {args.steps} steps...")
    model = PPO(
        "MlpPolicy", env,
        verbose=1,
        learning_rate=3e-4,
        n_steps=256,
        batch_size=64,
        n_epochs=5,
        ent_coef=0.05,
    )
    model.learn(total_timesteps=args.steps)
    model.save(args.output)
    print(f"Model saved: {args.output}")
    return 0


def cmd_repair(argv):
    """Run the trained agent on a specific assembly to repair it."""
    parser = argparse.ArgumentParser(description="Repair assembly with trained agent")
    parser.add_argument("--constraints", type=Path, required=True)
    parser.add_argument("--parts-dir", type=Path, default=None)
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--perturbation", type=float, default=15.0)
    parser.add_argument("--verbose", action="store_true")
    args, _ = parser.parse_known_args(argv)

    env = RepairSkillEnv(
        constraints_path=args.constraints,
        parts_dir=args.parts_dir,
        max_steps=30,
        verbose=args.verbose,
    )

    from stable_baselines3 import PPO
    model = PPO.load(args.model, env=env)

    obs, info = env.reset(options={"perturbation": args.perturbation})
    done = False
    total_reward = 0.0

    print(f"Repairing with σ={args.perturbation}mm perturbation...")
    while not done:
        action, _ = model.predict(obs, deterministic=True)
        obs, reward, terminated, truncated, info = env.step(action)
        total_reward += reward
        done = terminated or truncated
        env.render()

    report = info["report"]
    print(f"\nFinal report:")
    print(f"  All passed: {report['all_passed']}")
    print(f"  Interferences: {len(report['interferences'])}")
    print(f"  Gap errors: {len(report['gap_errors'])}")
    print(f"  Clearance warnings: {len(report['clearance_warnings'])}")
    print(f"  Total reward: {total_reward:.1f}")
    return 0


def cmd_evolve(argv):
    """Run continual evolution loop."""
    parser = argparse.ArgumentParser(description="Continually evolve agent")
    parser.add_argument("--constraints", type=Path, required=True)
    parser.add_argument("--parts-dir", type=Path, default=None)
    parser.add_argument("--cycles", type=int, default=5)
    parser.add_argument("--episodes-per-cycle", type=int, default=20)
    parser.add_argument("--fine-tune-steps", type=int, default=1000)
    parser.add_argument("--output", type=Path, default=Path("/tmp/evolved_agent.zip"))
    args, _ = parser.parse_known_args(argv)

    base_constraints = json.loads(Path(args.constraints).read_text(encoding="utf-8"))

    env = RepairSkillEnv(
        constraints_path=args.constraints,
        parts_dir=args.parts_dir,
        verbose=False,
    )

    from stable_baselines3 import PPO
    if args.output.exists():
        print(f"Loading existing model: {args.output}")
        model = PPO.load(args.output, env=env)
    else:
        print("Initializing new PPO model...")
        model = PPO(
            "MlpPolicy", env,
            verbose=1,
            learning_rate=3e-4,
            n_steps=128,
            batch_size=64,
            n_epochs=5,
            ent_coef=0.05,
        )

    curriculum = CurriculumGenerator(base_constraints)
    buffer = ExperienceBuffer(max_size=5000)

    for cycle in range(args.cycles):
        print(f"\n{'#'*60}")
        print(f"# EVOLUTION CYCLE {cycle + 1}/{args.cycles}")
        print(f"{'#'*60}")

        for ep in range(args.episodes_per_cycle):
            task = curriculum.next_task()
            env.cad_env.constraints_data = task

            obs, info = env.reset(options={"perturbation": random.uniform(5, 20)})
            done = False
            ep_reward = 0.0
            repair_seq = []

            while not done:
                action, _ = model.predict(obs, deterministic=False)
                obs, reward, terminated, truncated, info = env.step(action)
                ep_reward += reward
                repair_seq.append({"step": env.step_count, "action": int(action), "reward": float(reward)})
                done = terminated or truncated

            buffer.add(
                constraints=task,
                initial_report=info.get("report", {}),
                repair_sequence=repair_seq,
                final_report=info.get("report", {}),
                reward=ep_reward,
            )

        stats = buffer.stats()
        print(f"  Buffer: {stats}")

        if stats.get("total", 0) >= 10 and args.fine_tune_steps > 0:
            print(f"  Fine-tuning on {args.fine_tune_steps} steps...")
            model.learn(total_timesteps=args.fine_tune_steps, reset_num_timesteps=False)

        checkpoint = args.output.with_suffix(f".cycle{cycle+1}.zip")
        model.save(checkpoint)
        print(f"  Checkpoint: {checkpoint}")

    model.save(args.output)
    buffer.save(args.output.with_suffix(".buffer.json"))
    print(f"\nEvolution complete! Model: {args.output}")
    return 0


def main(argv: list[str] | None = None) -> int:
    """Dispatch subcommands."""
    if argv is None:
        argv = sys.argv[1:]

    if not argv or argv[0] in ("-h", "--help"):
        print(__doc__)
        print("\nCommands:")
        print("  train   — Train a fresh skill agent")
        print("  repair  — Run trained agent on a specific assembly")
        print("  evolve  — Continual evolution (self-improvement loop)")
        return 0

    cmd = argv[0]
    rest = argv[1:]

    if cmd == "train":
        return cmd_train(rest)
    elif cmd == "repair":
        return cmd_repair(rest)
    elif cmd == "evolve":
        return cmd_evolve(rest)
    else:
        print(f"Unknown command: {cmd}")
        print("Use: train, repair, or evolve")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
