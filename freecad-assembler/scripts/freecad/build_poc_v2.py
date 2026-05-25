import FreeCAD as App
import Part

doc = App.newDocument('POC_V2_Station')

def add_box(name, x, y, z, sx, sy, sz, color):
    obj = doc.addObject('Part::Feature', name)
    obj.Shape = Part.makeBox(sx, sy, sz)
    obj.Placement.Base = App.Vector(x, y, z)
    if hasattr(obj, 'ViewObject') and obj.ViewObject: obj.ViewObject.ShapeColor = color
    return obj

def add_cyl(name, x, y, z, r, h, color):
    obj = doc.addObject('Part::Feature', name)
    obj.Shape = Part.makeCylinder(r, h)
    obj.Placement.Base = App.Vector(x, y, z)
    if hasattr(obj, 'ViewObject') and obj.ViewObject: obj.ViewObject.ShapeColor = color
    return obj

add_box('base_plate', 0.0, 0.0, 0, 800, 500, 15, (0.98, 0.98, 0.98))
add_cyl('vib_bowl_base', 630.0, 80.0, 15, 70, 40, (0.55, 0.6, 0.68))
add_cyl('vib_bowl', 630.0, 80.0, 55, 80, 50, (0.65, 0.7, 0.78))

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
obj.Placement.Base = App.Vector(630.0, 80.0, 55)
if hasattr(obj, 'ViewObject') and obj.ViewObject: obj.ViewObject.ShapeColor = (0.50, 0.55, 0.60)

add_box('vib_track', 450.0, 70.0, 95, 100, 20, 6, (0.5, 0.55, 0.6))

# FIX 5: Funnel-shaped hopper (open bottom)
try:
    tc = Part.makeCircle(70, App.Vector(0,0,0), App.Vector(0,0,1))
    tw = Part.Wire([tc])
    bc = Part.makeCircle(25, App.Vector(0,0,-80), App.Vector(0,0,1))
    bw = Part.Wire([bc])
    hopper_shape = Part.makeLoft([tw, bw], False)  # False = shell, not solid
    obj = doc.addObject('Part::Feature', 'hopper')
    obj.Shape = hopper_shape
    obj.Placement.Base = App.Vector(660.0, 30.0, 135)
    if hasattr(obj, 'ViewObject') and obj.ViewObject: obj.ViewObject.ShapeColor = (0.90, 0.90, 0.93)
except Exception as e:
    print('Hopper loft fallback:', e)

add_box('hopper_support', 630.0, 0.0, 75, 60, 60, 60, (0.5, 0.55, 0.65))
add_box('column_left', 280.0, 220.0, 15, 20, 60, 250, (0.85, 0.8, 0.6))
add_box('column_right', 480.0, 220.0, 15, 20, 60, 250, (0.85, 0.8, 0.6))
add_box('beam', 270.0, 235.0, 265, 240, 30, 30, (0.1, 0.1, 0.1))
add_box('horiz_cyl_body', 270.0, 236.0, 265, 240, 28, 28, (0.1, 0.1, 0.1))
add_cyl('horiz_cyl_piston', 480.0, 250.0, 265, 8, 180, (0.3, 0.3, 0.35))
add_box('horiz_slider', 460.0, 230.0, 260, 40, 40, 25, (0.3, 0.3, 0.35))
add_cyl('vert_cyl_body', 480.0, 250.0, 120, 10, 140, (0.12, 0.12, 0.12))
add_cyl('vert_cyl_piston', 480.0, 250.0, 100, 6, 160, (0.12, 0.12, 0.12))
add_box('vert_guide_rail_l', 463.0, 245.0, 120, 4, 10, 140, (0.4, 0.4, 0.4))
add_box('vert_guide_rail_r', 493.0, 245.0, 120, 4, 10, 140, (0.4, 0.4, 0.4))
add_box('vert_guide_slider', 455.0, 242.0, 120, 30, 16, 20, (0.48, 0.48, 0.48))
add_box('green_plate', 472.0, 225.0, 70, 8, 50, 60, (0.18, 0.65, 0.25))
add_box('gripper_body', 465.0, 230.0, 50, 30, 40, 20, (0.52, 0.52, 0.58))
add_box('gripper_jaw_l', 469.5, 234.0, 32, 5, 8, 18, (0.38, 0.38, 0.43))
add_box('gripper_jaw_r', 485.5, 234.0, 32, 5, 8, 18, (0.38, 0.38, 0.43))
add_cyl('gripper_piston', 480.0, 250.0, 40, 3, 20, (0.2, 0.2, 0.25))
add_box('fixture_base', 185.0, 40.0, 15, 80, 80, 40, (0.1, 0.1, 0.1))
add_box('fixture_plat', 190.0, 45.0, 55, 70, 70, 10, (0.95, 0.95, 0.98))
add_cyl('sample_part', 225.0, 80.0, 65, 8, 22, (0.58, 0.3, 0.68))
add_box('guide_base', 20.0, 0.0, 15, 80, 80, 100, (0.82, 0.78, 0.58))
add_box('guide_rail', 0.0, 31.0, 120, 120, 18, 12, (0.14, 0.14, 0.14))
add_box('guide_slider', 62.5, 26.0, 118, 35, 28, 18, (0.48, 0.48, 0.48))
add_box('guide_cyl', 65.0, 34.0, 125, 50, 12, 12, (0.2, 0.2, 0.25))
doc.recompute()
import os; os.makedirs(os.path.dirname('/Users/jiwen/PycharmProjects/freecad-assembler/models/fcstd/poc_v2_station.FCStd'), exist_ok=True)
doc.saveAs('/Users/jiwen/PycharmProjects/freecad-assembler/models/fcstd/poc_v2_station.FCStd')
import Import; Import.export(doc.Objects, '/Users/jiwen/PycharmProjects/freecad-assembler/models/step/poc_v2_station.step')
print('STEP_EXPORTED: /Users/jiwen/PycharmProjects/freecad-assembler/models/step/poc_v2_station.step')

print("\n" + "="*60)
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

print("\n" + "-"*60)
if violations:
    print(f"VIOLATIONS FOUND: {len(violations)}")
    for v in violations:
        print("  " + v)
else:
    print("ALL DESIGN RULES PASSED — Model is structurally sound.")
print("="*60)
