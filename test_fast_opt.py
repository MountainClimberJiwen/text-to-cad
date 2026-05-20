import sys
sys.path.insert(0, 'skills/industrial_cad/rl')
from env import CADEnv
import numpy as np
from scipy.optimize import differential_evolution
import time

env = CADEnv(
    constraints_path='models/assemblies/vibratory_feeder_assembly.constraints.json',
    parts_dir='models',
)

obs, info = env.reset(options={'perturbation': 15.0})
initial = env._initial_placements()
n_dims = env.n_movable * 4

def bbox_overlap_penalty():
    """Fast pure-Python bbox overlap check."""
    bboxes = {pid: env._transformed_bbox(pid) for pid in env.part_ids}
    penalty = 0.0
    n = len(env.part_ids)
    for i in range(n):
        for j in range(i + 1, n):
            pa = env.part_ids[i]
            pb = env.part_ids[j]
            bb_a = bboxes[pa]
            bb_b = bboxes[pb]
            # Check overlap in all 3 axes
            x_overlap = not (bb_a[3] < bb_b[0] or bb_b[3] < bb_a[0])
            y_overlap = not (bb_a[4] < bb_b[1] or bb_b[4] < bb_a[1])
            z_overlap = not (bb_a[5] < bb_b[2] or bb_b[5] < bb_a[2])
            if x_overlap and y_overlap and z_overlap:
                # Approximate overlap volume
                ox = max(0, min(bb_a[3], bb_b[3]) - max(bb_a[0], bb_b[0]))
                oy = max(0, min(bb_a[4], bb_b[4]) - max(bb_a[1], bb_b[1]))
                oz = max(0, min(bb_a[5], bb_b[5]) - max(bb_a[2], bb_b[2]))
                penalty += ox * oy * oz
    return penalty

def objective(x):
    for i, pid in enumerate(env.movable_part_ids):
        idx = i * 4
        p = initial[pid]
        env.placements[pid] = {
            'x': p['x'] + x[idx + 0] * env.step_size,
            'y': p['y'] + x[idx + 1] * env.step_size,
            'z': p['z'] + x[idx + 2] * env.step_size,
            'rz': p['rz'] + x[idx + 3] * env.rot_step_size,
        }
    
    # Fast constraint check
    report = env._fast_verify()
    
    # Fast bbox overlap penalty
    overlap = bbox_overlap_penalty()
    
    r = -5.0 * len(report['gap_errors']) - 0.001 * overlap
    if len(report['gap_errors']) == 0 and overlap < 1.0:
        r += 100.0
    return -r

bounds = [(-5.0, 5.0)] * n_dims
print(f"Fast optimize {n_dims}D with DE (max_iter=15, popsize=8)...")
t0 = time.time()
result = differential_evolution(objective, bounds, maxiter=15, popsize=8, polish=False, workers=1)
elapsed = time.time() - t0
print(f"Done: {result.nfev} evals in {elapsed:.1f}s ({result.nfev/elapsed:.1f} evals/sec)")
print(f"Best reward: {-result.fun:.2f}")

# Final full verify
for i, pid in enumerate(env.movable_part_ids):
    idx = i * 4
    p = initial[pid]
    env.placements[pid] = {
        'x': p['x'] + result.x[idx + 0] * env.step_size,
        'y': p['y'] + result.x[idx + 1] * env.step_size,
        'z': p['z'] + result.x[idx + 2] * env.step_size,
        'rz': p['rz'] + result.x[idx + 3] * env.rot_step_size,
    }
report = env._verify()
print(f"Final: interf={len(report['interferences'])}, gaps={len(report['gap_errors'])}, passed={report['all_passed']}")
for interf in report['interferences']:
    print(f"  🔴 {interf['part_a']} ⟷ {interf['part_b']} (vol={interf['volume']}mm³)")
