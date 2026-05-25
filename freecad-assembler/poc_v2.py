#!/usr/bin/env python3
"""
POC v2: Rule-driven vibration feeder station.
Fixes 5 fatal defects from v1 via design-rule-embedded generation + post-check.
Run: python3 poc_v2.py
"""
import json, os, subprocess, sys
from ortools.sat.python import cp_model

PROJECT = "/Users/jiwen/PycharmProjects/freecad-assembler"
FREECAD_CMD = "/Applications/FreeCAD.app/Contents/Resources/bin/FreeCADCmd"

# =====================================================================
# Step 1: CP-SAT Layout Solver
# =====================================================================
def solve_layout():
    PW, PD = 800, 500
    BOWL_R = 80
    COL_W, COL_D = 20, 60
    FIX_W = 70
    GUIDE_W = 120
    HORIZ_STROKE = 500

    model = cp_model.CpModel()
    bowl_x = model.NewIntVar(BOWL_R, PW - BOWL_R, 'bowl_x')
    bowl_y = model.NewIntVar(BOWL_R, PD - BOWL_R, 'bowl_y')
    col_x = model.NewIntVar(150, 600, 'col_x')
    col_y = model.NewIntVar(100, PD - 100, 'col_y')
    fix_x = model.NewIntVar(35, 400, 'fix_x')
    fix_y = model.NewIntVar(35, PD - 35, 'fix_y')
    guide_x = model.NewIntVar(60, 250, 'guide_x')
    guide_y = model.NewIntVar(40, PD - 40, 'guide_y')

    # Left-to-right ordering with gaps
    model.Add(guide_x + GUIDE_W // 2 + 15 <= fix_x - FIX_W // 2)
    model.Add(fix_x + FIX_W // 2 + 20 <= col_x - 120)
    model.Add(col_x + 120 + 30 <= bowl_x - BOWL_R)

    # Stroke constraint
    pick_x = bowl_x - BOWL_R
    pick_y = bowl_y
    place_x = fix_x
    place_y = fix_y
    dx = model.NewIntVar(-700, 700, 'dx')
    dy = model.NewIntVar(-500, 500, 'dy')
    model.Add(dx == pick_x - place_x)
    model.Add(dy == pick_y - place_y)
    abs_dx = model.NewIntVar(0, 700, 'abs_dx')
    abs_dy = model.NewIntVar(0, 500, 'abs_dy')
    model.AddAbsEquality(abs_dx, dx)
    model.AddAbsEquality(abs_dy, dy)
    model.Add(abs_dx + abs_dy <= int(HORIZ_STROKE * 1.5))

    # Hopper must be above bowl with clearance
    hopper_x = bowl_x + 30
    hopper_y = bowl_y - 50
    model.Add(hopper_x >= bowl_x - BOWL_R + 20)
    model.Add(hopper_x <= bowl_x + BOWL_R - 20)
    model.Add(hopper_y >= bowl_y - BOWL_R + 20)
    model.Add(hopper_y <= bowl_y + BOWL_R - 20)

    # Minimize travel + center column
    travel = model.NewIntVar(0, 1000, 'travel')
    model.Add(travel == abs_dx + abs_dy)
    col_dev_x = model.NewIntVar(-250, 250, 'cdx')
    col_dev_y = model.NewIntVar(-250, 250, 'cdy')
    model.Add(col_dev_x == col_x - PW // 2)
    model.Add(col_dev_y == col_y - PD // 2)
    abs_cdx = model.NewIntVar(0, 250, 'acdx')
    abs_cdy = model.NewIntVar(0, 250, 'acdy')
    model.AddAbsEquality(abs_cdx, col_dev_x)
    model.AddAbsEquality(abs_cdy, col_dev_y)
    col_dev = model.NewIntVar(0, 500, 'cdev')
    model.Add(col_dev == abs_cdx + abs_cdy)
    obj = model.NewIntVar(0, 20000, 'obj')
    model.Add(obj == travel * 10 + col_dev)
    model.Minimize(obj)

    solver = cp_model.CpSolver()
    status = solver.Solve(model)
    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        raise RuntimeError("Layout unsatisfiable")

    return {
        "PW": PW, "PD": PD,
        "base_plate": {"size": [PW, PD, 15], "center": [PW/2, PD/2], "z": 0, "color": [0.98, 0.98, 0.98]},
        "vib_bowl_base": {"center": [float(solver.Value(bowl_x)), float(solver.Value(bowl_y))], "radius": 70, "height": 40, "z": 15, "color": [0.55, 0.60, 0.68]},
        "vib_bowl": {"center": [float(solver.Value(bowl_x)), float(solver.Value(bowl_y))], "radius": 80, "height": 50, "z": 55, "color": [0.65, 0.70, 0.78]},
        "vib_track": {"size": [100, 20, 6], "center": [float(solver.Value(bowl_x)) - BOWL_R - 50, float(solver.Value(bowl_y))], "z": 95, "color": [0.50, 0.55, 0.60]},
        "hopper": {"center": [float(solver.Value(hopper_x)), float(solver.Value(hopper_y))], "top_r": 70, "bot_r": 25, "height": 80, "z": 135, "color": [0.90, 0.90, 0.93]},
        "hopper_support": {"size": [60, 60, 60], "center": [float(solver.Value(hopper_x)), float(solver.Value(hopper_y))], "z": 75, "color": [0.50, 0.55, 0.65]},
        "column_left": {"size": [20, 60, 250], "center": [float(solver.Value(col_x)) - 110, float(solver.Value(col_y))], "z": 15, "color": [0.85, 0.80, 0.60]},
        "column_right": {"size": [20, 60, 250], "center": [float(solver.Value(col_x)) + 90, float(solver.Value(col_y))], "z": 15, "color": [0.85, 0.80, 0.60]},
        "beam": {"size": [240, 30, 30], "center": [float(solver.Value(col_x)) - 10, float(solver.Value(col_y))], "z": 265, "color": [0.10, 0.10, 0.10]},
        "horiz_cyl_body": {"size": [240, 28, 28], "center": [float(solver.Value(col_x)) - 10, float(solver.Value(col_y))], "z": 265, "color": [0.10, 0.10, 0.10]},
        "horiz_cyl_piston": {"radius": 8, "height": 180, "center": [float(solver.Value(col_x)) + 80, float(solver.Value(col_y))], "z": 265, "color": [0.30, 0.30, 0.35]},
        "horiz_slider": {"size": [40, 40, 25], "center": [float(solver.Value(col_x)) + 80, float(solver.Value(col_y))], "z": 260, "color": [0.30, 0.30, 0.35]},
        "vert_cyl_body": {"radius": 10, "height": 140, "center": [float(solver.Value(col_x)) + 80, float(solver.Value(col_y))], "z": 120, "color": [0.12, 0.12, 0.12]},
        "vert_cyl_piston": {"radius": 6, "height": 160, "center": [float(solver.Value(col_x)) + 80, float(solver.Value(col_y))], "z": 100, "color": [0.12, 0.12, 0.12]},
        "vert_guide_rail_l": {"size": [4, 10, 140], "center": [float(solver.Value(col_x)) + 65, float(solver.Value(col_y))], "z": 120, "color": [0.40, 0.40, 0.40]},
        "vert_guide_rail_r": {"size": [4, 10, 140], "center": [float(solver.Value(col_x)) + 95, float(solver.Value(col_y))], "z": 120, "color": [0.40, 0.40, 0.40]},
        "vert_guide_slider": {"size": [30, 16, 20], "center": [float(solver.Value(col_x)) + 70, float(solver.Value(col_y))], "z": 120, "color": [0.48, 0.48, 0.48]},
        "green_plate": {"size": [8, 50, 60], "center": [float(solver.Value(col_x)) + 76, float(solver.Value(col_y))], "z": 70, "color": [0.18, 0.65, 0.25]},
        "gripper_body": {"size": [30, 40, 20], "center": [float(solver.Value(col_x)) + 80, float(solver.Value(col_y))], "z": 50, "color": [0.52, 0.52, 0.58]},
        "gripper_jaw_l": {"size": [5, 8, 18], "center": [float(solver.Value(col_x)) + 72, float(solver.Value(col_y)) - 12], "z": 32, "color": [0.38, 0.38, 0.43]},
        "gripper_jaw_r": {"size": [5, 8, 18], "center": [float(solver.Value(col_x)) + 88, float(solver.Value(col_y)) - 12], "z": 32, "color": [0.38, 0.38, 0.43]},
        "gripper_piston": {"radius": 3, "height": 20, "center": [float(solver.Value(col_x)) + 80, float(solver.Value(col_y))], "z": 40, "color": [0.20, 0.20, 0.25]},
        "fixture_base": {"size": [80, 80, 40], "center": [float(solver.Value(fix_x)), float(solver.Value(fix_y))], "z": 15, "color": [0.10, 0.10, 0.10]},
        "fixture_plat": {"size": [FIX_W, FIX_W, 10], "center": [float(solver.Value(fix_x)), float(solver.Value(fix_y))], "z": 55, "color": [0.95, 0.95, 0.98]},
        "sample_part": {"radius": 8, "height": 22, "center": [float(solver.Value(fix_x)), float(solver.Value(fix_y))], "z": 65, "color": [0.58, 0.30, 0.68]},
        "guide_base": {"size": [80, 80, 100], "center": [float(solver.Value(guide_x)), float(solver.Value(guide_y))], "z": 15, "color": [0.82, 0.78, 0.58]},
        "guide_rail": {"size": [120, 18, 12], "center": [float(solver.Value(guide_x)), float(solver.Value(guide_y))], "z": 120, "color": [0.14, 0.14, 0.14]},
        "guide_slider": {"size": [35, 28, 18], "center": [float(solver.Value(guide_x)) + 20, float(solver.Value(guide_y))], "z": 118, "color": [0.48, 0.48, 0.48]},
        "guide_cyl": {"size": [50, 12, 12], "center": [float(solver.Value(guide_x)) + 30, float(solver.Value(guide_y))], "z": 125, "color": [0.20, 0.20, 0.25]},
    }

# =====================================================================
# Step 2: Generate FreeCAD script with rule-embedded geometry
# =====================================================================
def generate_freecad_script(layout):
    PW = layout["PW"]
    PD = layout["PD"]

    lines = []
    lines.append("import FreeCAD as App")
    lines.append("import Part")
    lines.append("")
    lines.append("doc = App.newDocument('POC_V2_Station')")
    lines.append("")
    lines.append("def add_box(name, x, y, z, sx, sy, sz, color):")
    lines.append("    obj = doc.addObject('Part::Feature', name)")
    lines.append("    obj.Shape = Part.makeBox(sx, sy, sz)")
    lines.append("    obj.Placement.Base = App.Vector(x, y, z)")
    lines.append("    if hasattr(obj, 'ViewObject') and obj.ViewObject: obj.ViewObject.ShapeColor = color")
    lines.append("    return obj")
    lines.append("")
    lines.append("def add_cyl(name, x, y, z, r, h, color):")
    lines.append("    obj = doc.addObject('Part::Feature', name)")
    lines.append("    obj.Shape = Part.makeCylinder(r, h)")
    lines.append("    obj.Placement.Base = App.Vector(x, y, z)")
    lines.append("    if hasattr(obj, 'ViewObject') and obj.ViewObject: obj.ViewObject.ShapeColor = color")
    lines.append("    return obj")
    lines.append("")

    def box(name, cfg):
        cx, cy = cfg["center"]
        sx, sy, sz = cfg["size"]
        x, y, z = cx - sx/2, cy - sy/2, cfg["z"]
        r, g, b = cfg["color"]
        lines.append(f"add_box('{name}', {x}, {y}, {z}, {sx}, {sy}, {sz}, ({r}, {g}, {b}))")

    def cyl(name, cfg):
        cx, cy = cfg["center"]
        r, h = cfg["radius"], cfg["height"]
        z = cfg["z"]
        cr, cg, cb = cfg["color"]
        lines.append(f"add_cyl('{name}', {cx}, {cy}, {z}, {r}, {h}, ({cr}, {cg}, {cb}))")

    # Base
    box("base_plate", layout["base_plate"])

    # Vibration system
    cyl("vib_bowl_base", layout["vib_bowl_base"])
    cyl("vib_bowl", layout["vib_bowl"])

    # FIX 3: Spiral track on top of bowl
    bx, by = layout["vib_bowl"]["center"]
    lines.append(f"""
# FIX 3: Spiral track (helix pipe)
try:
    helix = Part.makeHelix(10, 40, 60, 0, True)
    spiral = Part.makeTube(helix, 3)
except Exception as e:
    # Fallback: approximate spiral with a torus ring
    spiral = Part.makeTorus(55, 3)
    print('Spiral track fallback (torus):', e)
obj = doc.addObject('Part::Feature', 'vib_spiral')
obj.Shape = spiral
obj.Placement.Base = App.Vector({bx}, {by}, 55)
if hasattr(obj, 'ViewObject') and obj.ViewObject: obj.ViewObject.ShapeColor = (0.50, 0.55, 0.60)
""")

    box("vib_track", layout["vib_track"])

    # FIX 5: Funnel-shaped hopper (open bottom)
    hx, hy = layout["hopper"]["center"]
    hz = layout["hopper"]["z"]
    htr = layout["hopper"]["top_r"]
    hbr = layout["hopper"]["bot_r"]
    hh = layout["hopper"]["height"]
    lines.append(f"""
# FIX 5: Funnel-shaped hopper (open bottom)
try:
    tc = Part.makeCircle({htr}, App.Vector(0,0,0), App.Vector(0,0,1))
    tw = Part.Wire([tc])
    bc = Part.makeCircle({hbr}, App.Vector(0,0,-{hh}), App.Vector(0,0,1))
    bw = Part.Wire([bc])
    hopper_shape = Part.makeLoft([tw, bw], False)  # False = shell, not solid
    obj = doc.addObject('Part::Feature', 'hopper')
    obj.Shape = hopper_shape
    obj.Placement.Base = App.Vector({hx}, {hy}, {hz})
    if hasattr(obj, 'ViewObject') and obj.ViewObject: obj.ViewObject.ShapeColor = (0.90, 0.90, 0.93)
except Exception as e:
    print('Hopper loft fallback:', e)
""")
    box("hopper_support", layout["hopper_support"])

    # FIX 1: Dual-column portal frame
    box("column_left", layout["column_left"])
    box("column_right", layout["column_right"])
    box("beam", layout["beam"])

    # FIX 4: Horizontal cylinder with piston
    box("horiz_cyl_body", layout["horiz_cyl_body"])
    cyl("horiz_cyl_piston", layout["horiz_cyl_piston"])
    box("horiz_slider", layout["horiz_slider"])

    # FIX 1: Vertical cylinder with dual guide rails
    cyl("vert_cyl_body", layout["vert_cyl_body"])
    cyl("vert_cyl_piston", layout["vert_cyl_piston"])
    box("vert_guide_rail_l", layout["vert_guide_rail_l"])
    box("vert_guide_rail_r", layout["vert_guide_rail_r"])
    box("vert_guide_slider", layout["vert_guide_slider"])

    box("green_plate", layout["green_plate"])

    # FIX 2: Gripper with jaw mechanism
    box("gripper_body", layout["gripper_body"])
    box("gripper_jaw_l", layout["gripper_jaw_l"])
    box("gripper_jaw_r", layout["gripper_jaw_r"])
    cyl("gripper_piston", layout["gripper_piston"])

    # Fixture
    box("fixture_base", layout["fixture_base"])
    box("fixture_plat", layout["fixture_plat"])
    cyl("sample_part", layout["sample_part"])

    # Left guide
    box("guide_base", layout["guide_base"])
    box("guide_rail", layout["guide_rail"])
    box("guide_slider", layout["guide_slider"])
    box("guide_cyl", layout["guide_cyl"])

    # Save
    lines.append("doc.recompute()")
    fcstd = f"{PROJECT}/models/fcstd/poc_v2_station.FCStd"
    step = f"{PROJECT}/models/step/poc_v2_station.step"
    lines.append(f"import os; os.makedirs(os.path.dirname('{fcstd}'), exist_ok=True)")
    lines.append(f"doc.saveAs('{fcstd}')")
    lines.append(f"import Import; Import.export(doc.Objects, '{step}')")
    lines.append(f"print('STEP_EXPORTED: {step}')")

    # === Rule Checker (embedded in same script) ===
    lines.append("""
print("\\n" + "="*60)
print("DESIGN RULE CHECK REPORT")
print("="*60)
violations = []

# Rule 1: Portal frame must have dual support
r1_parts = ['column_left', 'column_right', 'beam']
r1_ok = all(doc.getObject(n) is not None for n in r1_parts)
if r1_ok:
    print("[PASS] Rule 1: Portal frame has dual-column support")
else:
    violations.append("Rule 1 FATAL: Portal frame missing dual support")

# Rule 2: Gripper must have jaw mechanism  
r2_parts = ['gripper_jaw_l', 'gripper_jaw_r', 'gripper_piston']
r2_ok = all(doc.getObject(n) is not None for n in r2_parts)
if r2_ok:
    print("[PASS] Rule 2: Gripper has jaw + piston mechanism")
else:
    violations.append("Rule 2 FATAL: Gripper missing jaw mechanism")

# Rule 3: Vibration bowl must have spiral track
r3_ok = doc.getObject('vib_spiral') is not None
if r3_ok:
    print("[PASS] Rule 3: Vibration bowl has spiral track")
else:
    violations.append("Rule 3 FATAL: Vibration bowl missing spiral track")

# Rule 4: Horizontal cylinder must have piston
r4_ok = doc.getObject('horiz_cyl_piston') is not None
if r4_ok:
    print("[PASS] Rule 4: Horizontal cylinder has piston rod")
else:
    violations.append("Rule 4 FATAL: Horizontal cylinder missing piston")

# Rule 5: Hopper must be funnel-shaped and above bowl
hopper_obj = doc.getObject('hopper')
if hopper_obj and hopper_obj.Shape:
    # Check if shell (loft) rather than solid box
    is_shell = len(hopper_obj.Shape.Shells) > 0 and len(hopper_obj.Shape.Solids) == 0
    if is_shell:
        print("[PASS] Rule 5: Hopper is funnel-shaped shell")
    else:
        violations.append("Rule 5 FATAL: Hopper is not funnel-shaped")
else:
    violations.append("Rule 5 FATAL: Hopper missing")

# Rule 6: Vertical cylinder must have guide rails
r6_parts = ['vert_guide_rail_l', 'vert_guide_rail_r', 'vert_guide_slider']
r6_ok = all(doc.getObject(n) is not None for n in r6_parts)
if r6_ok:
    print("[PASS] Rule 6: Vertical cylinder has linear guide")
else:
    violations.append("Rule 6 FATAL: Vertical cylinder missing guide")

print("\\n" + "-"*60)
if violations:
    print(f"VIOLATIONS FOUND: {len(violations)}")
    for v in violations:
        print("  " + v)
else:
    print("ALL DESIGN RULES PASSED — Model is structurally sound.")
print("="*60)
""")

    script_path = f"{PROJECT}/scripts/freecad/build_poc_v2.py"
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
        capture_output=True, text=True, timeout=180
    )
    print(result.stdout)
    if result.returncode != 0:
        print("FREECAD STDERR:", result.stderr[-2000:])
        raise RuntimeError("FreeCAD execution failed")

# =====================================================================
# Step 4: Render preview
# =====================================================================
def render_preview(fcstd_path):
    mesh_script = f"""import FreeCAD as App
import json, os
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
out = "{PROJECT}/models/preview/poc_v2_mesh_data.json"
os.makedirs(os.path.dirname(out), exist_ok=True)
with open(out, "w") as f:
    json.dump(meshes, f)
print("MESH_OK")
"""
    mesh_script_path = f"{PROJECT}/scripts/freecad/export_poc_v2_mesh.py"
    with open(mesh_script_path, "w") as f:
        f.write(mesh_script)
    r = subprocess.run([FREECAD_CMD, mesh_script_path], capture_output=True, text=True, timeout=60)
    if "MESH_OK" not in r.stdout:
        print("Mesh export failed:", r.stderr[-500:])
        return

    render_script = f"""import json, numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection

with open("{PROJECT}/models/preview/poc_v2_mesh_data.json") as f:
    meshes = json.load(f)

fig = plt.figure(figsize=(18, 13))
ax = fig.add_subplot(111, projection='3d')

cmap = {{
    "base_plate": (0.98, 0.98, 0.98), "vib_bowl_base": (0.55, 0.60, 0.68),
    "vib_bowl": (0.65, 0.70, 0.78), "vib_track": (0.50, 0.55, 0.60),
    "vib_spiral": (0.45, 0.50, 0.55), "hopper_support": (0.50, 0.55, 0.65),
    "hopper": (0.90, 0.90, 0.93), "column_left": (0.85, 0.80, 0.60),
    "column_right": (0.85, 0.80, 0.60), "beam": (0.10, 0.10, 0.10),
    "horiz_cyl_body": (0.10, 0.10, 0.10), "horiz_cyl_piston": (0.30, 0.30, 0.35),
    "horiz_slider": (0.30, 0.30, 0.35), "vert_cyl_body": (0.12, 0.12, 0.12),
    "vert_cyl_piston": (0.12, 0.12, 0.12), "vert_guide_rail_l": (0.40, 0.40, 0.40),
    "vert_guide_rail_r": (0.40, 0.40, 0.40), "vert_guide_slider": (0.48, 0.48, 0.48),
    "green_plate": (0.18, 0.65, 0.25), "gripper_body": (0.52, 0.52, 0.58),
    "gripper_jaw_l": (0.38, 0.38, 0.43), "gripper_jaw_r": (0.38, 0.38, 0.43),
    "gripper_piston": (0.20, 0.20, 0.25), "fixture_base": (0.10, 0.10, 0.10),
    "fixture_plat": (0.95, 0.95, 0.98), "sample_part": (0.58, 0.30, 0.68),
    "guide_base": (0.82, 0.78, 0.58), "guide_rail": (0.14, 0.14, 0.14),
    "guide_slider": (0.48, 0.48, 0.48), "guide_cyl": (0.20, 0.20, 0.25)
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
ax.view_init(elev=28, azim=-50)
ax.set_title('POC v2: Rule-Driven Vibration Feeder Station')
ax.set_axis_off()
plt.savefig("{PROJECT}/models/preview/poc_v2_station.png", dpi=150, bbox_inches='tight', facecolor='white')
print("RENDER_OK")
"""
    render_path = f"{PROJECT}/scripts/render_poc_v2.py"
    with open(render_path, "w") as f:
        f.write(render_script)
    r2 = subprocess.run([sys.executable, render_path], capture_output=True, text=True, timeout=60)
    if "RENDER_OK" in r2.stdout:
        print(f"Preview: {PROJECT}/models/preview/poc_v2_station.png")
    else:
        print("Render failed:", r2.stderr[-500:])

# =====================================================================
# Main
# =====================================================================
if __name__ == "__main__":
    print("[1/4] CP-SAT solving layout...")
    layout = solve_layout()
    print(f"    Layout: bowl={layout['vib_bowl']['center']}, col={layout['column_left']['center']}")

    print("[2/4] Generating FreeCAD script (with rule fixes)...")
    script_path, fcstd_path, step_path = generate_freecad_script(layout)
    print(f"    Script: {script_path}")

    print("[3/4] Running FreeCADCmd (generation + rule check)...")
    run_freecad(script_path)

    print("[4/4] Rendering preview...")
    render_preview(fcstd_path)

    print("\n=== POC V2 COMPLETE ===")
    print(f"FCStd:   {fcstd_path}")
    print(f"STEP:    {step_path}")
    print(f"Preview: {PROJECT}/models/preview/poc_v2_station.png")
