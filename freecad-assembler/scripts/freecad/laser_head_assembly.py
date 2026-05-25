# -*- coding: utf-8 -*-
import os
import sys

import FreeCAD as App

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)
PROJECT_ROOT = os.path.dirname(os.path.dirname(CURRENT_DIR))

from step_importer import get_step_summary, import_step_feature


DOC_NAME = "LaserHeadAssembly"
OUTPUT_FCSTD = os.path.join(PROJECT_ROOT, "models", "fcstd", f"{DOC_NAME}.FCStd")
LASER_STEP_PATH = os.path.join(PROJECT_ROOT, "models", "step", "3. CNC 3DP Laser Engraving Head Opt Lasers.step")


def reset_doc(doc_name):
    if doc_name in App.listDocuments():
        App.closeDocument(doc_name)
    return App.newDocument(doc_name)


def add_box(doc, name, length, width, height, x, y, z):
    obj = doc.addObject("Part::Box", name)
    obj.Length = float(length)
    obj.Width = float(width)
    obj.Height = float(height)
    obj.Placement = App.Placement(App.Vector(float(x), float(y), float(z)), App.Rotation())
    return obj


def add_cylinder(doc, name, radius, height, x, y, z):
    obj = doc.addObject("Part::Cylinder", name)
    obj.Radius = float(radius)
    obj.Height = float(height)
    obj.Placement = App.Placement(App.Vector(float(x), float(y), float(z)), App.Rotation())
    return obj


doc = reset_doc(DOC_NAME)

# Base frame
base_plate = add_box(doc, "BasePlate", 420, 280, 16, -210, -140, -20)
left_post = add_box(doc, "LeftPost", 24, 24, 220, -170, -40, -4)
right_post = add_box(doc, "RightPost", 24, 24, 220, 146, -40, -4)
rear_brace = add_box(doc, "RearBrace", 340, 24, 24, -170, 70, 150)
top_beam = add_box(doc, "TopBeam", 340, 36, 28, -170, -18, 188)

# Motion subassembly
x_rail = add_box(doc, "XRail", 300, 18, 16, -150, -9, 156)
carriage_plate = add_box(doc, "CarriagePlate", 120, 90, 12, -60, -45, 128)
front_mount_plate = add_box(doc, "FrontMountPlate", 96, 12, 118, -48, -6, 24)
rear_mount_plate = add_box(doc, "RearMountPlate", 96, 12, 118, -48, -76, 24)
left_clamp = add_box(doc, "LeftClamp", 12, 70, 118, -60, -76, 24)
right_clamp = add_box(doc, "RightClamp", 12, 70, 118, 48, -76, 24)
bottom_saddle = add_box(doc, "BottomSaddle", 120, 90, 18, -60, -76, 24)
rear_spine = add_box(doc, "RearSpine", 24, 36, 150, -12, -112, 12)
bridge_block = add_box(doc, "BridgeBlock", 80, 26, 24, -40, -58, 116)
cable_guard = add_box(doc, "CableGuard", 140, 18, 18, -70, 50, 170)

# Decorative/fixture details to make the assembly more readable in 3D.
standoff_1 = add_cylinder(doc, "Standoff_1", 5, 26, -32, -32, 102)
standoff_2 = add_cylinder(doc, "Standoff_2", 5, 26, 22, -32, 102)
standoff_3 = add_cylinder(doc, "Standoff_3", 5, 26, -32, 22, 102)
standoff_4 = add_cylinder(doc, "Standoff_4", 5, 26, 22, 22, 102)

laser_head = import_step_feature(
    doc,
    "LaserHead_STEP",
    LASER_STEP_PATH,
    0,
    0,
    32,
    App.Rotation(App.Vector(0, 0, 1), 180),
)

doc.recompute()
doc.saveAs(OUTPUT_FCSTD)

print("Laser assembly created")
print("Saved FCStd:", OUTPUT_FCSTD)
print("STEP summary:", get_step_summary(LASER_STEP_PATH))
for obj in [
    base_plate,
    left_post,
    right_post,
    rear_brace,
    top_beam,
    x_rail,
    carriage_plate,
    front_mount_plate,
    rear_mount_plate,
    left_clamp,
    right_clamp,
    bottom_saddle,
    rear_spine,
    bridge_block,
    cable_guard,
    standoff_1,
    standoff_2,
    standoff_3,
    standoff_4,
    laser_head,
]:
    print(obj.Name)
