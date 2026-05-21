#!/usr/bin/env python3
"""
ACG-EF V3 Demo: End-to-end constraint-guided assembly generation.
"""
import sys
sys.path.insert(0, "/Users/jiwen/PycharmProjects/freecad-assembler")

from framework import FullStationTemplate, AssemblySolver, AssemblyVerifier

# Step 1: Generate intent from template (simulating LLM output)
print("=" * 60)
print("STEP 1: TEMPLATE INSTANTIATION")
print("=" * 60)

parts, relations = FullStationTemplate.create({
    "station_width": 800,
    "station_depth": 500,
    "bowl_diameter": 200,
    "gantry_span": 300,
    "gantry_height": 250,
    "vertical_stroke": 120,
    "horizontal_stroke": 250,
    "gripper_span": 20,
    "fix_has_push": True,
})

print(f"Parts: {len(parts)}")
print(f"Relations: {len(relations)}")
for p in parts:
    print(f"  {p.name}: type={p.part_type.value}, params={p.params}")

# Step 2: Constraint solving
print("\n" + "=" * 60)
print("STEP 2: CONSTRAINT SOLVING")
print("=" * 60)

from framework.ontology import AssemblyIntent
intent = AssemblyIntent()
intent.parts = parts
intent.relations = relations

solver = AssemblySolver(intent)
boxes = solver.solve()

print(f"Solved: {solver.solved}")
if solver.errors:
    print("Solver notes:")
    for e in solver.errors:
        print(f"  {e}")

print("\nSolved coordinates:")
for name, box in sorted(boxes.items()):
    print(f"  {name:25s}: center=({box.cx:7.1f}, {box.cy:7.1f}, {box.cz:7.1f})  size=({box.w:6.1f}x{box.d:6.1f}x{box.h:6.1f})")

# Step 3: Verification
print("\n" + "=" * 60)
print("STEP 3: VERIFICATION")
print("=" * 60)

verifier = AssemblyVerifier(boxes)
verifier.verify_all()
verifier.print_report()

# Step 4: Export FreeCAD script
print("\n" + "=" * 60)
print("STEP 4: EXPORT TO FREECAD")
print("=" * 60)

import os
out_dir = "/Users/jiwen/PycharmProjects/freecad-assembler/models/v3"
os.makedirs(out_dir, exist_ok=True)

fcscript = f"""import FreeCAD as App
import Part
import Mesh

doc = App.newDocument("poc_v3_station")
"""

colors = {
    "base": "(0.7, 0.7, 0.75)",
    "col": "(0.3, 0.3, 0.35)",
    "beam": "(0.4, 0.4, 0.45)",
    "bowl": "(0.85, 0.6, 0.2)",
    "hopper": "(0.5, 0.5, 0.55)",
    "cyl": "(0.2, 0.5, 0.8)",
    "slider": "(0.3, 0.7, 0.3)",
    "gripper": "(0.8, 0.2, 0.2)",
    "jaw": "(0.9, 0.3, 0.3)",
    "fix": "(0.6, 0.4, 0.2)",
    "plate": "(0.75, 0.75, 0.8)",
    "track": "(0.5, 0.5, 0.5)",
    "support": "(0.4, 0.4, 0.4)",
    "guide": "(0.2, 0.8, 0.6)",
    "piston": "(0.9, 0.9, 0.2)",
    "default": "(0.5, 0.5, 0.5)",
}

def pick_color(name: str) -> str:
    for key, col in colors.items():
        if key in name.lower():
            return col
    return colors["default"]

for name, box in boxes.items():
    col = pick_color(name)
    fcscript += f"""
box = doc.addObject("Part::Box", "{name}")
box.Length = {box.w}
box.Width = {box.d}
box.Height = {box.h}
box.Placement.Base = App.Vector({box.cx - box.w/2}, {box.cy - box.d/2}, {box.cz - box.h/2})
if hasattr(box, "ViewObject") and box.ViewObject:
    box.ViewObject.ShapeColor = {col}
"""

fcscript += """
doc.recompute()
"""

fc_path = f"{out_dir}/poc_v3_station.py"
with open(fc_path, "w") as f:
    f.write(fcscript)
print(f"FreeCAD script written to {fc_path}")

# Step 5: Run FreeCAD to export STEP
print("\nRunning FreeCAD export...")
cmd = f"""cat > /tmp/export_v3.py << 'PYEOF'
import sys
sys.path.insert(0, "/Users/jiwen/PycharmProjects/freecad-assembler")
exec(open("{fc_path}").read())
import Import
Import.export([doc.getObject(n) for n in doc.Objects if hasattr(doc.getObject(n), 'Shape')], "{out_dir}/poc_v3_station.step")
doc.saveAs("{out_dir}/poc_v3_station.FCStd")
PYEOF
/Applications/FreeCAD.app/Contents/Resources/bin/FreeCADCmd /tmp/export_v3.py"""

os.system(cmd)
print(f"STEP exported to {out_dir}/poc_v3_station.step")
print(f"FCStd saved to {out_dir}/poc_v3_station.FCStd")

print("\n" + "=" * 60)
print("DONE")
print("=" * 60)
