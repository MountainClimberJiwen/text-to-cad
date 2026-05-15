# CAD-RL: Model-Free Reinforcement Learning for CAD Assembly Optimization

## Overview

CAD-RL 将「文本→CAD→装配→验证」的完整流水线建模为一个 **马尔可夫决策过程 (MDP)**，通过 model-free 强化学习（PPO）自动优化零件 Placement，使装配同时满足：

1. **设计意图约束**（constraints.json 定义的 Fix/PlaneCoincident/Distance/CenterOfMass/Rotation）
2. **实际几何可行性**（无干涉、间隙合格、BRep 有效）

与传统梯度下降或遗传算法不同，RL Agent **不需要任何几何先验模型**，完全通过「试错→验证→奖励」的闭环自主学习修复策略。

---

## Architecture

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Prompt    │────▶│  LLM/Code   │────▶│  CAD Code   │
└─────────────┘     └─────────────┘     └─────────────┘
                                               │
                                               ▼
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  Optimized  │◀────│  PPO Agent  │◀────│   CADEnv    │
│ Placements  │     │  (Policy)   │     │  (MDP Env)  │
└─────────────┘     └─────────────┘     └─────────────┘
                                               │
                                               ▼
                                      ┌─────────────────┐
                                      │  Verification   │
                                      │  • check_gap    │
                                      │  • verify_asm   │
                                      └─────────────────┘
                                               │
                                               ▼
                                      ┌─────────────────┐
                                      │  Reward Signal  │
                                      │  -10 × interf   │
                                      │  -5  × gap_err  │
                                      │  +100 if pass   │
                                      └─────────────────┘
```

---

## Environment Design (MDP)

### State Space

每个零件的当前 Placement（x, y, z, rz）+ 验证指标：

```python
obs = [x1, y1, z1, rz1, ..., xN, yN, zN, rzN, n_interf, n_gap_err, n_warn]
dim = 4 × N_parts + 3
```

### Action Space

对每个 **可移动零件** 施加微小平移/旋转：

```python
action = [dx1, dy1, dz1, drz1, ..., dxM, dyM, dzM, drzM]
dim = 4 × N_movable
range: [-1, 1]  (scaled by step_size / rot_step_size)
```

Fixed 零件（如 BasePlate）不会被 Agent 移动。

### Reward Function

```python
reward = -10.0 × n_interferences
         - 5.0  × n_gap_errors
         - 1.0  × n_clearance_warnings
         - 0.01 × ||action||²
         - 0.1
         + 100.0 if all_passed
```

### Episode Dynamics

- **Reset**: 从 constraints.json 解析初始 Placement（可选择添加随机扰动）
- **Step**: Agent 调整 Placement → 验证几何 → 返回 reward
- **Termination**: 所有约束满足且 0 干涉，或达到 max_steps

### Speed Optimization

完整 OCP 几何检查（BRepAlgoAPI_Common）较慢（~1.7s/步）。环境默认每 5 步执行一次完整检查，其余步骤只进行快速约束 gap 检查，**平均速度提升至 ~0.4s/步**。

---

## Usage

### 1. 训练 Agent

```bash
./.venv/bin/python skills/industrial_cad/rl/train.py \
  --constraints models/assemblies/vibratory_feeder_assembly.constraints.json \
  --total-timesteps 20000 \
  --max-steps 50 \
  --step-size 1.0 \
  --output models/assemblies/vibratory_feeder_assembly.rl.placements.json
```

参数说明：
- `--total-timesteps`: 总训练步数
- `--max-steps`: 每个 episode 的最大步数
- `--step-size`: 位置调整步长（mm）
- `--rot-step-size`: 旋转调整步长（deg）
- `--geometry-check-interval`: 完整几何检查间隔（默认 5）

### 2. 使用训练好的模型

```python
from stable_baselines3 import PPO
from skills.industrial_cad.rl.env import CADEnv

env = CADEnv("models/assemblies/vibratory_feeder_assembly.constraints.json")
model = PPO.load("/path/to/model")

obs, _ = env.reset()
for _ in range(50):
    action, _ = model.predict(obs, deterministic=True)
    obs, reward, terminated, truncated, info = env.step(action)
    if terminated:
        break

env.export_best_placements("optimized.placements.json")
```

### 3. 集成到生成流水线

```python
# 在 LLM 生成初始 CAD 代码后，运行 RL 优化
from skills.industrial_cad.rl.train import train_ppo

env = CADEnv(constraints_path=constraints_file)
model, best_reward, best_placements = train_ppo(env, total_timesteps=5000)

# 用优化后的 placements 更新 constraints.json 或 assembly.py
env.export_best_placements(output_file)
```

---

## Key Design Decisions

### 1. 为什么不用传统优化器？

| 方法 | 需要梯度 | 需要几何模型 | 处理离散约束 | 探索能力 |
|------|---------|-------------|-------------|---------|
| 梯度下降 | ✅ | ✅ | ❌ | 弱 |
| 遗传算法 | ❌ | ❌ | ✅ | 中 |
| **RL (PPO)** | ❌ | ❌ | ✅ | **强** |

RL 的优势在于：
- **Model-free**: 不需要 CAD 核的微分信息
- **自动探索**: 自动发现「先移动 A 再旋转 B」的组合修复策略
- **可扩展**: 容易扩展到更复杂的 action space（如添加/删除约束）

### 2. Action Space 为什么是连续而不是离散？

CAD Placement 是连续空间问题。离散动作（如 `move_left/move_right`）需要非常细粒度的离散化才能达到足够精度，导致维度爆炸。连续动作通过 `step_size` 缩放即可实现任意精度。

### 3. 如何处理 Fixed 零件？

Fixed 零件（如 BasePlate）从 action space 中排除，Agent 无法移动它们。这保证了约束的硬性要求不会被违反。

### 4. 为什么需要 `allowed_overlaps`？

某些几何重叠是设计意图（如螺栓穿过孔、滑块嵌入导轨）。`verify_assembly.py` 的 `--allowed-overlaps` 配置让 RL 训练可以忽略这些「假干涉」，专注于真正的设计问题。

---

## Future Extensions

1. **Hierarchical RL**: 上层 Agent 选择约束类型，下层 Agent 优化参数
2. **Constraint Discovery**: Action space 扩展为「添加/删除/修改约束」，让 Agent 自动发现缺失的约束
3. **Multi-Objective**: 同时优化重量、成本、可制造性
4. **Surrogate Model**: 训练神经网络替代 OCP 验证器，将每步时间降至 <10ms
5. **LLM + RL 联合训练**: LLM 生成初始代码，RL 微调参数，形成端到端可微流水线

---

## Files

| 文件 | 说明 |
|------|------|
| `env.py` | Gymnasium 环境（MDP 定义） |
| `train.py` | PPO 训练脚本 |
| `README.md` | 本文档 |
