import sys
sys.path.insert(0, 'skills/industrial_cad/rl')
from env import CADEnv
import numpy as np
from scipy.optimize import minimize

env = CADEnv(
    constraints_path='models/assemblies/vibratory_feeder_assembly.constraints.json',
    parts_dir='models',
)

obs, info = env.reset(options={'perturbation': 15.0})
initial = env._initial_placements()
n_dims = env.n_movable * 4

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
    report = env._verify()
    r = -10.0 * len(report['interferences']) - 5.0 * len(report['gap_errors']) - 1.0 * len(report['clearance_warnings'])
    if report['all_passed']:
        r += 100.0
    return -r

result = minimize(objective, np.zeros(n_dims), method='Nelder-Mead', options={'maxiter': 50, 'disp': False})

# Final verify
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

print(f"\nBest x: {result.x}")
print(f"Expected x (from constraints): all zeros")
