#!/usr/bin/env python3
"""
Continual Evolution — Self-improving CAD Repair Agent.

This script implements the full lifecycle:
  1. Train on synthetic failures (curriculum learning)
  2. Evaluate on real assemblies
  3. Collect human feedback / real-world outcomes
  4. Fine-tune on new experiences (online learning)
  5. Save improved model

Usage:
    ./.venv/bin/python skills/industrial_cad/rl/agent/evolve.py \
        --constraints models/assemblies/vibratory_feeder_assembly.constraints.json \
        --cycles 5 \
        --output-model /tmp/evolved_agent.zip
"""
from __future__ import annotations

import argparse
import json
import random
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from skill_env import RepairSkillEnv


class ExperienceBuffer:
    """Store and sample repair experiences for continual learning."""

    def __init__(self, max_size: int = 10000):
        self.buffer = []
        self.max_size = max_size

    def add(self, constraints: dict, initial_report: dict, repair_sequence: list, final_report: dict, reward: float):
        """Add a repair episode to the buffer."""
        entry = {
            "constraints": constraints,
            "initial_report": initial_report,
            "repair_sequence": repair_sequence,
            "final_report": final_report,
            "reward": reward,
            "timestamp": time.time(),
        }
        self.buffer.append(entry)
        if len(self.buffer) > self.max_size:
            self.buffer.pop(0)

    def sample(self, n: int, success_only: bool = False) -> list:
        """Sample experiences for replay."""
        candidates = self.buffer
        if success_only:
            candidates = [e for e in self.buffer if e["final_report"].get("all_passed", False)]
        if not candidates:
            return []
        return random.sample(candidates, min(n, len(candidates)))

    def stats(self) -> dict:
        """Return buffer statistics."""
        if not self.buffer:
            return {}
        rewards = [e["reward"] for e in self.buffer]
        passed = sum(1 for e in self.buffer if e["final_report"].get("all_passed", False))
        return {
            "total": len(self.buffer),
            "success_rate": passed / len(self.buffer),
            "mean_reward": np.mean(rewards),
            "max_reward": max(rewards),
        }

    def save(self, path: str | Path):
        Path(path).write_text(json.dumps(self.buffer, indent=2, default=str), encoding="utf-8")


class CurriculumGenerator:
    """Generate progressively harder training tasks."""

    def __init__(self, base_constraints: dict):
        self.base_constraints = base_constraints
        self.level = 0

    def next_task(self) -> dict:
        """Generate a perturbed version of the base constraints."""
        self.level += 1
        perturbed = json.loads(json.dumps(self.base_constraints))

        # Level 1: Small perturbations (5mm)
        # Level 2: Medium perturbations (10mm)
        # Level 3+: Large perturbations + missing constraints
        sigma = min(5.0 + self.level * 3.0, 30.0)

        for c in perturbed.get("constraints", []):
            if c.get("type") == "Distance":
                original = float(c.get("value", 0))
                noise = random.gauss(0, sigma)
                c["value"] = round(original + noise, 2)

        # Advanced levels: randomly remove a constraint
        if self.level >= 4 and random.random() < 0.3:
            constraints = perturbed.get("constraints", [])
            non_fix = [i for i, c in enumerate(constraints) if c.get("type") != "Fix"]
            if non_fix:
                idx = random.choice(non_fix)
                removed = constraints.pop(idx)
                print(f"  [Curriculum] Removed constraint: {removed}")

        return perturbed

    def reset(self):
        self.level = 0


def run_evolution_cycle(
    env: RepairSkillEnv,
    model,
    curriculum: CurriculumGenerator,
    buffer: ExperienceBuffer,
    n_episodes: int = 20,
    fine_tune_steps: int = 1000,
):
    """Run one evolution cycle: collect → evaluate → fine-tune."""
    print(f"\n{'='*60}")
    print(f"Evolution Cycle: Collecting {n_episodes} experiences")
    print(f"{'='*60}")

    # Collect experiences
    for ep in range(n_episodes):
        task = curriculum.next_task()
        env.cad_env.constraints_data = task

        obs, info = env.reset(options={"perturbation": random.uniform(5, 20)})
        done = False
        ep_reward = 0.0
        repair_seq = []

        while not done:
            action, _ = model.predict(obs, deterministic=False)  # Explore
            obs, reward, terminated, truncated, info = env.step(action)
            ep_reward += reward
            repair_seq.append({
                "step": env.step_count,
                "action": action,
                "reward": reward,
            })
            done = terminated or truncated

        buffer.add(
            constraints=task,
            initial_report=info.get("report", {}),
            repair_sequence=repair_seq,
            final_report=info.get("report", {}),
            reward=ep_reward,
        )

    stats = buffer.stats()
    print(f"Buffer stats: {stats}")

    # Fine-tune on collected experiences
    if fine_tune_steps > 0 and stats.get("total", 0) >= 10:
        print(f"\nFine-tuning on {fine_tune_steps} steps...")
        model.learn(total_timesteps=fine_tune_steps, reset_num_timesteps=False)

    return model


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Continually evolve repair skill agent")
    parser.add_argument("--constraints", type=Path, required=True)
    parser.add_argument("--parts-dir", type=Path, default=None)
    parser.add_argument("--cycles", type=int, default=5, help="Number of evolution cycles")
    parser.add_argument("--episodes-per-cycle", type=int, default=20)
    parser.add_argument("--fine-tune-steps", type=int, default=1000)
    parser.add_argument("--output-model", type=Path, default=Path("/tmp/evolved_agent.zip"))
    parser.add_argument("--experience-buffer", type=Path, default=Path("/tmp/experience_buffer.json"))
    parser.add_argument("--verbose", type=int, default=1)
    args = parser.parse_args(argv)

    try:
        from stable_baselines3 import PPO
    except ImportError:
        print("ERROR: stable-baselines3 not installed", file=sys.stderr)
        sys.exit(1)

    # Load base constraints
    base_constraints = json.loads(Path(args.constraints).read_text(encoding="utf-8"))

    # Create environment
    env = RepairSkillEnv(
        constraints_path=args.constraints,
        parts_dir=args.parts_dir,
        perturbation=15.0,
        max_steps=30,
        verbose=False,
    )

    # Initialize or load model
    if args.output_model.exists():
        print(f"Loading existing model: {args.output_model}")
        model = PPO.load(args.output_model, env=env)
    else:
        print("Initializing new PPO model...")
        model = PPO(
            "MlpPolicy",
            env,
            verbose=args.verbose,
            learning_rate=3e-4,
            n_steps=128,
            batch_size=64,
            n_epochs=5,
            ent_coef=0.05,
        )

    # Initialize components
    curriculum = CurriculumGenerator(base_constraints)
    buffer = ExperienceBuffer(max_size=5000)

    # Evolution loop
    for cycle in range(args.cycles):
        print(f"\n{'#'*60}")
        print(f"# EVOLUTION CYCLE {cycle + 1}/{args.cycles}")
        print(f"{'#'*60}")

        model = run_evolution_cycle(
            env, model, curriculum, buffer,
            n_episodes=args.episodes_per_cycle,
            fine_tune_steps=args.fine_tune_steps,
        )

        # Save checkpoint
        checkpoint_path = args.output_model.with_suffix(f".cycle{cycle+1}.zip")
        model.save(checkpoint_path)
        print(f"Checkpoint saved: {checkpoint_path}")

    # Final save
    model.save(args.output_model)
    buffer.save(args.experience_buffer)
    print(f"\n{'='*60}")
    print(f"Evolution complete!")
    print(f"Final model: {args.output_model}")
    print(f"Experience buffer: {args.experience_buffer}")
    print(f"Total experiences: {len(buffer.buffer)}")
    print(f"Success rate: {buffer.stats().get('success_rate', 0)*100:.1f}%")
    print(f"{'='*60}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
