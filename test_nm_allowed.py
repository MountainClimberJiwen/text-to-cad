import sys, json
sys.path.insert(0, 'skills/industrial_cad/rl')
from env import CADEnv
import numpy as np
from scipy.optimize import minimize

allowed = json.loads(open('models/assemblies/vibratory_feeder_assembly.allowed_overlaps.json').read())

env = CADEnv(
    constraints_path='models/assemblies/vibratory_feeder_assembly.constraints.json',
    parts_dir='models',
    allowed_overlaps=allowed,
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

print(f"Nelder-Mead with allowed_overlaps ({n_dims}D)...")
result = minimize(objective, np.zeros(n_dims), method='Nelder-Mead', options={'maxiter': 50, 'disp': False})
print(f"Done: {result.nfev} evals, reward={-result.fun:.2f}")

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
