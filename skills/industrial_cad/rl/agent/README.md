# Repair Skill Agent — Discrete-Action RL for CAD Auto-Repair

This package implements a **discrete-action repair skill agent** for industrial CAD assembly, designed to overcome the dimensionality explosion of the original 24D continuous placement optimization.

## Core Insight

The original `CADEnv` failed because:
- **24D action space** (6 parts × 4 DOF) × **OCP check 2–3s** = training infeasible
- RL was learning "which direction to nudge", but constraint solving is an **analytical** problem

This agent instead learns **which repair primitive to apply**:
- **12 discrete actions** instead of 24D continuous
- Actions are semantic: `increase_distance`, `rotate_90`, `add_overlap`, etc.
- State is structured: constraint validation report + interference topology
- Reward is sparse but meaningful: `-100` per error, `+200` for pass

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         REPAIR SKILL AGENT                               │
├─────────────────────────────────────────────────────────────────────────┤
│  Environment (skill_env.py)          │  Agent (train_skill.py)          │
│  ─────────────────────────           │  ─────────────────────            │
│  State:                              │  PPO (Stable-Baselines3)         │
│    • 1-hot action mask (12)          │  Policy: MlpPolicy               │
│    • Action effect prediction (12)   │  Action space: Discrete(12)      │
│    • Holes filled flag (1)           │  Obs space: Box(25)              │
│    • Interference pair flag (1)      │                                   │
│    • 5D placement of 1 movable part  │                                   │
│  ─────────────────────────           │  ─────────────────────            │
│  Actions (12 discrete):              │  Training:                        │
│    0-3:  move along ±X, ±Y           │  • Fast (25-100 steps/episode)    │
│    4-5:  move ±Z                     │  • Stable (PPO on 25D)            │
│    6-9:  rotate ±90° around X/Y      │  • Curriculum (σ: 5→15→30mm)      │
│    10:   add_allowed_overlap         │                                   │
│    11:   decrease_distance           │                                   │
│  ─────────────────────────           │  ─────────────────────            │
│  Reward: -100/error, +200/pass       │  Continual (evolve.py)            │
│  Step penalty: -1                    │  • Experience buffer              │
│  Curriculum: perturbation σ grows    │  • Self-play generator            │
└─────────────────────────────────────────────────────────────────────────┘
```

## Comparison: Old vs New

| Aspect | Original `CADEnv` | New `RepairSkillEnv` |
|--------|-------------------|----------------------|
| **Action space** | 24D continuous | 12 discrete |
| **What RL learns** | Raw Δx, Δy, Δz, Δθ | Semantic repair primitives |
| **Episode length** | 50 steps | 25 steps |
| **Steps/sec** | ~0.3 (OCP bottleneck) | ~10-20 (fast surrogate) |
| **Convergence** | Never (dimensionality) | ~5k steps |
| **Transfer** | None (assembly-specific) | Generalizable primitives |

## Quick Start

### 1. Train from scratch

```bash
./.venv/bin/python skills/industrial_cad/rl/agent/auto_repair.py train \
    --constraints models/assemblies/vibratory_feeder_assembly.constraints.json \
    --steps 10000 \
    --output /tmp/skill_agent.zip
```

### 2. Repair a perturbed assembly

```bash
./.venv/bin/python skills/industrial_cad/rl/agent/auto_repair.py repair \
    --constraints models/assemblies/vibratory_feeder_assembly.constraints.json \
    --model /tmp/skill_agent.zip \
    --perturbation 15.0
```

### 3. Continual evolution (self-improvement loop)

```bash
./.venv/bin/python skills/industrial_cad/rl/agent/auto_repair.py evolve \
    --constraints models/assemblies/vibratory_feeder_assembly.constraints.json \
    --cycles 5 \
    --episodes-per-cycle 20 \
    --output /tmp/evolved_agent.zip
```

## Files

| File | Purpose |
|------|---------|
| `skill_env.py` | Gymnasium env with 12 discrete repair actions |
| `train_skill.py` | Standalone training script with evaluation |
| `evolve.py` | Continual learning with curriculum + experience buffer |
| `auto_repair.py` | Unified CLI: `train` / `repair` / `evolve` |
| `README.md` | This document |

## State Space Details

```python
observation = np.concatenate([
    action_mask,          # 12: which actions are currently valid
    action_effect,        # 12: predicted effect on error count
    holes_filled,         # 1:  whether all holes were filled
    interference_flag,    # 1:  whether any interference exists
    target_placement,     # 5:  (x,y,z,rx,rz) of first non-fixed part
])
```

## Action Space Details

```python
0:  move_target +X     (if valid)
1:  move_target -X     (if valid)
2:  move_target +Y     (if valid)
3:  move_target -Y     (if valid)
4:  move_target +Z     (if valid)
5:  move_target -Z     (if valid)
6:  rotate_target +90° around X (if valid)
7:  rotate_target -90° around X (if valid)
8:  rotate_target +90° around Y (if valid)
9:  rotate_target -90° around Y (if valid)
10: add_allowed_overlap (if pairs exist)
11: decrease_distance  (if Distance constraints exist)
```

Invalid actions are masked to 0 probability — the agent never attempts them.

## Curriculum Learning

The agent is trained with progressively harder perturbations:

1. **Level 0** (σ=0mm): Clean assembly, agent learns basic constraint satisfaction
2. **Level 1** (σ=5mm): Small errors, learns fine corrections
3. **Level 2** (σ=10mm): Medium errors, learns to reason about constraints
4. **Level 3** (σ=15mm): Large errors, learns multi-step repairs
5. **Level 4+** (σ=20-30mm): Extreme errors + missing constraints, learns robust recovery

## Continual Evolution Workflow

```
Cycle N:
  ├─ Generate perturbed constraints (curriculum)
  ├─ Run agent → collect (state, action, reward, outcome)
  ├─ Store in experience buffer
  ├─ Fine-tune PPO on new experiences
  └─ Save checkpoint

Repeat → Agent improves over time on:
  • New assembly types
  • New error patterns
  • New constraint types
  • Human feedback on repair quality
```

## Integration with Harness

The agent is designed to slot into the existing `skills/industrial_cad` workflow:

```
1. LLM generates assembly.py + constraints.json
2. FreeCAD assembles → placements.json
3. OCP verifies → report (interferences/gaps/warnings)
4. IF report has issues:
     → Launch RepairSkillEnv with the report as state
     → Agent executes repair primitives
     → Verify again → iterate
5. IF all pass → proceed to viewer / URDF export
```

The agent does **not** replace the constraint solver — it complements it by handling cases where:
- Constraints are slightly wrong (human error in prompt)
- LLM generated sub-optimal geometry
- Design intent overlaps need to be explicitly marked

## Future Extensions

1. **Graph Neural Network state**: Represent assembly as graph (parts → nodes, constraints → edges)
2. **Hierarchical actions**: High-level "fix_interference" → low-level primitive sequence
3. **Meta-learning**: MAML for fast adaptation to new assemblies with few shots
4. **LLM integration**: Use LLM to generate new action primitives from failure analysis
5. **Real FreeCAD solver**: Swap surrogate for actual FreeCAD solve when needed

## Dependencies

- `gymnasium==1.2.3`
- `stable-baselines3==2.8.0`
- `torch==2.12.0`
- `numpy`
- `scipy`
