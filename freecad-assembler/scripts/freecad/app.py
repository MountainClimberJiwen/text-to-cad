# -*- coding: utf-8 -*-
import os
import sys

import FreeCAD as App

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)
PROJECT_ROOT = os.path.dirname(os.path.dirname(CURRENT_DIR))

from step_importer import get_step_summary, import_step_feature


DOC_NAME = "MotorStepAssembly"
OUTPUT_FCSTD = os.path.join(PROJECT_ROOT, "models", "fcstd", f"{DOC_NAME}.FCStd")
MOTOR_STEP_PATH = os.path.join(PROJECT_ROOT, "models", "step", "Nema17 4.4Kgcm Stepper Motor.step")


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

base_plate = add_box(doc, "BasePlate", 160, 120, 10, -80, -60, -70)
mount_plate = add_box(doc, "MountPlate", 80, 80, 6, -40, -40, -54)

standoff_1 = add_cylinder(doc, "Standoff_1", 3, 14, -15.5, -15.5, -68)
standoff_2 = add_cylinder(doc, "Standoff_2", 3, 14, 15.5, -15.5, -68)
standoff_3 = add_cylinder(doc, "Standoff_3", 3, 14, -15.5, 15.5, -68)
standoff_4 = add_cylinder(doc, "Standoff_4", 3, 14, 15.5, 15.5, -68)

if not os.path.exists(MOTOR_STEP_PATH):
    raise FileNotFoundError(MOTOR_STEP_PATH)

motor = import_step_feature(doc, "Nema17Motor_STEP", MOTOR_STEP_PATH, 0, 0, 0)
motor_summary = get_step_summary(MOTOR_STEP_PATH)

doc.recompute()
doc.saveAs(OUTPUT_FCSTD)

print("Motor assembly created")
print("Saved FCStd:", OUTPUT_FCSTD)
print("STEP summary:", motor_summary)
for obj in [
    base_plate,
    mount_plate,
    standoff_1,
    standoff_2,
    standoff_3,
    standoff_4,
    motor,
]:
    print(obj.Name)
