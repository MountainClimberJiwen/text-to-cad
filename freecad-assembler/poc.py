#!/usr/bin/env python3
"""
POC: ortools CP-SAT + FreeCAD vibration feeder station assembly.
Run: python3 poc.py
Outputs:
  - models/fcstd/poc_station.FCStd
  - models/step/poc_station.step
  - models/preview/poc_station.png
"""
import json
import os
import subprocess
import sys
from ortools.sat.python import cp_model

PROJECT = "/Users/jiwen/PycharmProjects/freecad-assembler"
FREECAD_CMD = "/Applications/FreeCAD.app/Contents/Resources/bin/FreeCADCmd"

# =====================================================================
# Step 1: CP-SAT Layout Solver (coordinates in mm)
# =====================================================================
def solve_layout():
    PW, PD = 600, 450          # 底板尺寸 (mm)
    BOWL_R = 80                # 振动盘半径
    COL_W, COL_D = 20, 60      # 立柱截面
    FIX_W = 70                 # 工装台宽度
    GUIDE_W, GUIDE_D = 120, 80 # 导向机构占地
    HORIZ_STROKE = 200         # 水平气缸行程 (mm)

    model = cp_model.CpModel()

    # 变量：各模块中心XY（mm）
    bowl_x = model.NewIntVar(BOWL_R, PW - BOWL_R, 'bowl_x')
    bowl_y = model.NewIntVar(BOWL_R, PD - BOWL_R, 'bowl_y')
    col_x = model.NewIntVar(50, 380, 'col_x')
    col_y = model.NewIntVar(50, PD - 50, 'col_y')
    fix_x = model.NewIntVar(35, 295, 'fix_x')
    fix_y = model.NewIntVar(35, PD - 35, 'fix_y')
    guide_x = model.NewIntVar(60, 170, 'guide_x')
    guide_y = model.NewIntVar(40, PD - 40, 'guide_y')

    # 结构顺序（从左到右）
    # guide右边缘 + 间隔 <= fix左边缘
    model.Add(guide_x + GUIDE_W // 2 + 30 <= fix_x - FIX_W // 2)
    # fix右边缘 + 间隔 <= col左边缘
    model.Add(fix_x + FIX_W // 2 + 40 <= col_x - COL_W // 2)
    # col右边缘 + 间隔 <= bowl左边缘
    model.Add(col_x + COL_W // 2 + 50 <= bowl_x - BOWL_R)

    # 夹爪取料位 = 振动盘左边缘出料口
    pick_x = bowl_x - BOWL_R
    pick_y = bowl_y

    # 夹爪放料位 = 工装台中心正上方（水平投影）
    place_x = fix_x
    place_y = fix_y

    # 行程约束：欧氏距离 <= HORIZ_STROKE
    # CP-SAT 处理平方复杂，用曼哈顿距离作为上界：|dx|+|dy| <= stroke * sqrt(2)
    dx = model.NewIntVar(-500, 500, 'dx')
    dy = model.NewIntVar(-500, 500, 'dy')
    model.Add(dx == pick_x - place_x)
    model.Add(dy == pick_y - place_y)
    abs_dx = model.NewIntVar(0, 500, 'abs_dx')
    abs_dy = model.NewIntVar(0, 500, 'abs_dy')
    model.AddAbsEquality(abs_dx, dx)
    model.AddAbsEquality(abs_dy, dy)
    model.Add(abs_dx + abs_dy <= int(HORIZ_STROKE * 1.414))

    # 软目标1：行程最短
    travel = model.NewIntVar(0, 1000, 'travel')
    model.Add(travel == abs_dx + abs_dy)

    # 软目标2：立柱尽量居中
    col_dev_x = model.NewIntVar(-250, 250, 'col_dev_x')
    col_dev_y = model.NewIntVar(-200, 200, 'col_dev_y')
    model.Add(col_dev_x == col_x - PW // 2)
    model.Add(col_dev_y == col_y - PD // 2)
    abs_col_dev_x = model.NewIntVar(0, 250, 'abs_col_dev_x')
    abs_col_dev_y = model.NewIntVar(0, 200, 'abs_col_dev_y')
    model.AddAbsEquality(abs_col_dev_x, col_dev_x)
    model.AddAbsEquality(abs_col_dev_y, col_dev_y)
    col_dev = model.NewIntVar(0, 500, 'col_dev')
    model.Add(col_dev == abs_col_dev_x + abs_col_dev_y)

    # 组合目标：travel 优先，然后居中
    # 用加权和：travel * 10 + col_dev
    obj = model.NewIntVar(0, 10000, 'obj')
    model.Add(obj == travel * 10 + col_dev)
    model.Minimize(obj)

    solver = cp_model.CpSolver()
    status = solver.Solve(model)

    if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        layout = {
            "base_plate": {"size": [PW, PD, 15], "center": [PW/2, PD/2], "z": 0, "color": [0.98, 0.98, 0.98]},
            "vib_bowl": {
                "center": [float(solver.Value(bowl_x)), float(solver.Value(bowl_y))],
                "radius": BOWL_R, "height": 50, "z": 15,
                "color": [0.65, 0.70, 0.78]
            },
            "vib_bowl_base": {
                "center": [float(solver.Value(bowl_x)), float(solver.Value(bowl_y))],
                "radius": 90, "height": 40, "z": 15,
                "color": [0.55, 0.60, 0.68]
            },
            "vib_track": {
                "size": [100, 25, 8],
                "center": [float(solver.Value(bowl_x)) - BOWL_R - 50, float(solver.Value(bowl_y))],
                "z": 55, "color": [0.50, 0.55, 0.60]
            },
            "hopper_stand": {
                "size": [70, 70, 80],
                "center": [float(solver.Value(bowl_x)) + 20, float(solver.Value(bowl_y)) - 80],
                "z": 15, "color": [0.50, 0.55, 0.65]
            },
            "hopper": {
                "size": [140, 110, 90],
                "center": [float(solver.Value(bowl_x)) + 20, float(solver.Value(bowl_y)) - 80],
                "z": 95, "color": [0.90, 0.90, 0.93]
            },
            "column": {
                "size": [COL_W, COL_D, 250],
                "center": [float(solver.Value(col_x)), float(solver.Value(col_y))],
                "z": 15, "color": [0.85, 0.80, 0.60]
            },
            "horiz_cyl": {
                "size": [250, 30, 30],
                "center": [float(solver.Value(col_x)), float(solver.Value(col_y))],
                "z": 265, "color": [0.10, 0.10, 0.10]
            },
            "horiz_slider": {
                "size": [40, 40, 25],
                "center": [float(solver.Value(col_x)) + 80, float(solver.Value(col_y))],
                "z": 260, "color": [0.30, 0.30, 0.35]
            },
            "vert_cyl": {
                "size": [20, 20, 140],
                "center": [float(solver.Value(col_x)) + 80, float(solver.Value(col_y))],
                "z": 120, "color": [0.12, 0.12, 0.12]
            },
            "green_plate": {
                "size": [8, 50, 60],
                "center": [float(solver.Value(col_x)) + 80, float(solver.Value(col_y))],
                "z": 70, "color": [0.18, 0.65, 0.25]
            },
            "gripper_body": {
                "size": [30, 28, 20],
                "center": [float(solver.Value(col_x)) + 80, float(solver.Value(col_y))],
                "z": 50, "color": [0.52, 0.52, 0.58]
            },
            "gripper_jaw_l": {
                "size": [5, 8, 18],
                "center": [float(solver.Value(col_x)) + 80 - 8, float(solver.Value(col_y))],
                "z": 32, "color": [0.38, 0.38, 0.43]
            },
            "gripper_jaw_r": {
                "size": [5, 8, 18],
                "center": [float(solver.Value(col_x)) + 80 + 8, float(solver.Value(col_y))],
                "z": 32, "color": [0.38, 0.38, 0.43]
            },
            "fixture_base": {
                "size": [80, 80, 40],
                "center": [float(solver.Value(fix_x)), float(solver.Value(fix_y))],
                "z": 15, "color": [0.10, 0.10, 0.10]
            },
            "fixture_plat": {
                "size": [FIX_W, FIX_W, 10],
                "center": [float(solver.Value(fix_x)), float(solver.Value(fix_y))],
                "z": 55, "color": [0.95, 0.95, 0.98]
            },
            "sample_part": {
                "radius": 8, "height": 22,
                "center": [float(solver.Value(fix_x)), float(solver.Value(fix_y))],
                "z": 65, "color": [0.58, 0.30, 0.68]
            },
            "guide_base": {
                "size": [80, 80, 100],
                "center": [float(solver.Value(guide_x)), float(solver.Value(guide_y))],
                "z": 15, "color": [0.82, 0.78, 0.58]
            },
            "guide_rail": {
                "size": [120, 18, 12],
                "center": [float(solver.Value(guide_x)), float(solver.Value(guide_y))],
                "z": 120, "color": [0.14, 0.14, 0.14]
            },
            "guide_slider": {
                "size": [35, 28, 18],
                "center": [float(solver.Value(guide_x)) + 20, float(solver.Value(guide_y))],
                "z": 118, "color": [0.48, 0.48, 0.48]
            },
            "guide_cyl": {
                "size": [50, 12, 12],
                "center": [float(solver.Value(guide_x)) + 30, float(solver.Value(guide_y))],
                "z": 125, "color": [0.20, 0.20, 0.25]
            },
            "pick_point": {
                "x": float(solver.Value(pick_x)),
                "y": float(solver.Value(pick_y)),
                "z": 65
            },
            "place_point": {
                "x": float(solver.Value(place_x)),
                "y": float(solver.Value(place_y)),
                "z": 65
            },
            "stroke_mm": float(solver.Value(travel))
        }
        return layout
    else:
        raise RuntimeError("CP-SAT layout unsatisfiable")

# =====================================================================
# Step 2: Generate FreeCAD script from CP-SAT layout
# =====================================================================
def generate_freecad_script(layout):
    lines = []
    lines.append("# -*- coding: utf-8 -*-")
    lines.append("import FreeCAD as App")
    lines.append("import Part")
    lines.append("")
    lines.append("doc = App.newDocument('POC_Station')")
    lines.append("")

    def box(name, cfg):
        cx, cy = cfg["center"]
        sx, sy, sz = cfg["size"]
        x = cx - sx/2
        y = cy - sy/2
        z = cfg["z"]
        r, g, b = cfg["color"]
        lines.append(f"obj = doc.addObject('Part::Feature', '{name}')")
        lines.append(f"obj.Shape = Part.makeBox({sx}, {sy}, {sz})")
        lines.append(f"obj.Placement.Base = App.Vector({x}, {y}, {z})")
        lines.append(f"if hasattr(obj, 'ViewObject') and obj.ViewObject: obj.ViewObject.ShapeColor = ({r}, {g}, {b})")
        lines.append("")

    def cyl(name, cfg):
        cx, cy = cfg["center"]
        r = cfg["radius"]
        h = cfg["height"]
        z = cfg["z"]
        cr, cg, cb = cfg["color"]
        lines.append(f"obj = doc.addObject('Part::Feature', '{name}')")
        lines.append(f"obj.Shape = Part.makeCylinder({r}, {h})")
        lines.append(f"obj.Placement.Base = App.Vector({cx}, {cy}, {z})")
        lines.append(f"if hasattr(obj, 'ViewObject') and obj.ViewObject: obj.ViewObject.ShapeColor = ({cr}, {cg}, {cb})")
        lines.append("")

    box("base_plate", layout["base_plate"])
    cyl("vib_bowl_base", layout["vib_bowl_base"])
    cyl("vib_bowl", layout["vib_bowl"])
    box("vib_track", layout["vib_track"])
    box("hopper_stand", layout["hopper_stand"])
    box("hopper", layout["hopper"])
    box("column", layout["column"])
    box("horiz_cyl", layout["horiz_cyl"])
    box("horiz_slider", layout["horiz_slider"])
    box("vert_cyl", layout["vert_cyl"])
    box("green_plate", layout["green_plate"])
    box("gripper_body", layout["gripper_body"])
    box("gripper_jaw_l", layout["gripper_jaw_l"])
    box("gripper_jaw_r", layout["gripper_jaw_r"])
    box("fixture_base", layout["fixture_base"])
    box("fixture_plat", layout["fixture_plat"])
    cyl("sample_part", layout["sample_part"])
    box("guide_base", layout["guide_base"])
    box("guide_rail", layout["guide_rail"])
    box("guide_slider", layout["guide_slider"])
    box("guide_cyl", layout["guide_cyl"])

    lines.append("doc.recompute()")
    fcstd = f"{PROJECT}/models/fcstd/poc_station.FCStd"
    step = f"{PROJECT}/models/step/poc_station.step"
    lines.append(f"import os; os.makedirs(os.path.dirname('{fcstd}'), exist_ok=True)")
    lines.append(f"doc.saveAs('{fcstd}')")
    lines.append(f"import Import; Import.export(doc.Objects, '{step}')")
    lines.append(f"print('DONE: {step}')")

    script_path = f"{PROJECT}/scripts/freecad/build_poc_station.py"
    os.makedirs(os.path.dirname(script_path), exist_ok=True)
    with open(script_path, "w") as f:
        f.write("\n".join(lines))
    return script_path, fcstd, step

# =====================================================================
# Step 3: Run FreeCADCmd
# =====================================================================
def run_freecad(script_path):
    result = subprocess.run(
        [FREECAD_CMD, script_path],
        capture_output=True, text=True, timeout=120
    )
    print(result.stdout)
    if result.returncode != 0:
        print("FREECAD STDERR:", result.stderr)
        raise RuntimeError("FreeCAD execution failed")

# =====================================================================
# Step 4: Render preview with matplotlib (system python)
# =====================================================================
def render_preview(fcstd_path):
    mesh_script = f"""# -*- coding: utf-8 -*-
import FreeCAD as App
import json
import os
doc = App.openDocument("{fcstd_path}")
meshes = []
for obj in doc.Objects:
    if hasattr(obj, "Shape") and not obj.Shape.isNull():
        verts, tris = obj.Shape.tessellate(0.5)
        if verts:
            meshes.append({{
                "name": obj.Name,
                "vertices": [(v.x, v.y, v.z) for v in verts],
                "triangles": list(tris),
                "placement": {{
                    "base": (obj.Placement.Base.x, obj.Placement.Base.y, obj.Placement.Base.z),
                    "rotation": obj.Placement.Rotation.Q
                }}
            }})
out = "{PROJECT}/models/preview/poc_mesh_data.json"
os.makedirs(os.path.dirname(out), exist_ok=True)
with open(out, "w") as f:
    json.dump(meshes, f)
print("MESH_OK")
"""
    mesh_script_path = f"{PROJECT}/scripts/freecad/export_poc_mesh.py"
    with open(mesh_script_path, "w") as f:
        f.write(mesh_script)

    r = subprocess.run([FREECAD_CMD, mesh_script_path], capture_output=True, text=True, timeout=60)
    if "MESH_OK" not in r.stdout:
        print("Mesh export failed:", r.stderr)
        return

    render_script = f"""import json, numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection

with open("{PROJECT}/models/preview/poc_mesh_data.json") as f:
    meshes = json.load(f)

fig = plt.figure(figsize=(16, 12))
ax = fig.add_subplot(111, projection='3d')

cmap = {{
    "base_plate": (0.98, 0.98, 0.98), "vib_bowl_base": (0.55, 0.60, 0.68),
    "vib_bowl": (0.65, 0.70, 0.78), "vib_track": (0.50, 0.55, 0.60),
    "hopper_stand": (0.50, 0.55, 0.65), "hopper": (0.90, 0.90, 0.93),
    "column": (0.85, 0.80, 0.60), "horiz_cyl": (0.10, 0.10, 0.10),
    "horiz_slider": (0.30, 0.30, 0.35), "vert_cyl": (0.12, 0.12, 0.12),
    "green_plate": (0.18, 0.65, 0.25), "gripper_body": (0.52, 0.52, 0.58),
    "gripper_jaw_l": (0.38, 0.38, 0.43), "gripper_jaw_r": (0.38, 0.38, 0.43),
    "fixture_base": (0.10, 0.10, 0.10), "fixture_plat": (0.95, 0.95, 0.98),
    "sample_part": (0.58, 0.30, 0.68), "guide_base": (0.82, 0.78, 0.58),
    "guide_rail": (0.14, 0.14, 0.14), "guide_slider": (0.48, 0.48, 0.48),
    "guide_cyl": (0.20, 0.20, 0.25)
}}

all_v = []
for mesh in meshes:
    verts = np.array(mesh["vertices"])
    tris = np.array(mesh["triangles"])
    if len(tris) == 0: continue
    q = mesh["placement"]["rotation"]
    x, y, z, w = q
    R = np.array([[
        1-2*(y*y+z*z), 2*(x*y-z*w), 2*(x*z+y*w)],
        [2*(x*y+z*w), 1-2*(x*x+z*z), 2*(y*z-x*w)],
        [2*(x*z-y*w), 2*(y*z+x*w), 1-2*(x*x+y*y)]])
    vr = verts @ R.T
    b = mesh["placement"]["base"]
    vr += np.array([b[0], b[1], b[2]])
    all_v.append(vr)
    faces = vr[tris]
    c = cmap.get(mesh["name"], (0.6, 0.6, 0.6))
    ax.add_collection3d(Poly3DCollection(faces, alpha=0.95, facecolor=c, edgecolor='none'))

all_v = np.vstack(all_v)
rng = np.array([all_v[:,0].max()-all_v[:,0].min(),
                all_v[:,1].max()-all_v[:,1].min(),
                all_v[:,2].max()-all_v[:,2].min()]).max()/2.0
mx, my, mz = (all_v[:,0].max()+all_v[:,0].min())*0.5, (all_v[:,1].max()+all_v[:,1].min())*0.5, (all_v[:,2].max()+all_v[:,2].min())*0.5
ax.set_xlim(mx-rng, mx+rng); ax.set_ylim(my-rng, my+rng); ax.set_zlim(mz-rng, mz+rng)
ax.view_init(elev=30, azim=-55)
ax.set_title('POC Vibration Feeder Station (ortools CP-SAT + FreeCAD)')
ax.set_axis_off()
plt.savefig("{PROJECT}/models/preview/poc_station.png", dpi=150, bbox_inches='tight', facecolor='white')
print("RENDER_OK")
"""
    render_path = f"{PROJECT}/scripts/render_poc.py"
    with open(render_path, "w") as f:
        f.write(render_script)

    r2 = subprocess.run([sys.executable, render_path], capture_output=True, text=True, timeout=60)
    if "RENDER_OK" in r2.stdout:
        print(f"Preview saved: {PROJECT}/models/preview/poc_station.png")
    else:
        print("Render failed:", r2.stderr)

# =====================================================================
# Main
# =====================================================================
if __name__ == "__main__":
    print("[1/4] ortools CP-SAT solving layout...")
    layout = solve_layout()
    with open(f"{PROJECT}/models/preview/poc_layout.json", "w") as f:
        json.dump(layout, f, indent=2)
    print(f"    Layout: bowl=({layout['vib_bowl']['center'][0]:.1f}, {layout['vib_bowl']['center'][1]:.1f}), "
          f"col=({layout['column']['center'][0]:.1f}, {layout['column']['center'][1]:.1f}), "
          f"stroke={layout['stroke_mm']:.1f}mm")

    print("[2/4] Generating FreeCAD script...")
    script_path, fcstd_path, step_path = generate_freecad_script(layout)
    print(f"    Script: {script_path}")

    print("[3/4] Running FreeCADCmd...")
    run_freecad(script_path)
    print(f"    STEP: {step_path}")
    print(f"    FCStd: {fcstd_path}")

    print("[4/4] Rendering preview...")
    render_preview(fcstd_path)

    print("\n=== POC COMPLETE ===")
    print(f"Open STEP:     {step_path}")
    print(f"Open FCStd:    {fcstd_path}")
    print(f"Open Preview:  {PROJECT}/models/preview/poc_station.png")
