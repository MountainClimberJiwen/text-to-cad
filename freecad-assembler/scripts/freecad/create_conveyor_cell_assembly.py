# -*- coding: utf-8 -*-
import os
import sys

import FreeCAD as App
import Part


CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)
PROJECT_ROOT = os.path.dirname(os.path.dirname(CURRENT_DIR))

from step_importer import read_step_shape


DOC_NAME = "ConveyorLaserCell"
OUTPUT_FCSTD = os.path.join(PROJECT_ROOT, "models", "fcstd", f"{DOC_NAME}.FCStd")

STEP_DIR = os.path.join(PROJECT_ROOT, "models", "step")
CONVEYOR_STEP = os.path.join(STEP_DIR, "Conveyor.STEP")
RAIL_STEP = os.path.join(STEP_DIR, "HGR20.STEP")
MOTOR_STEP = os.path.join(STEP_DIR, "Nema17 4.4Kgcm Stepper Motor.step")
LASER_STEP = os.path.join(STEP_DIR, "3. CNC 3DP Laser Engraving Head Opt Lasers.step")


def reset_doc(doc_name):
    if doc_name in App.listDocuments():
        App.closeDocument(doc_name)
    return App.newDocument(doc_name)


def anchor_value(min_value, max_value, mode):
    if mode == "min":
        return min_value
    if mode == "max":
        return max_value
    if mode == "center":
        return (min_value + max_value) / 2.0
    raise ValueError(mode)


def bbox_anchor_point(bbox, anchor):
    ax, ay, az = anchor
    return App.Vector(
        anchor_value(bbox.XMin, bbox.XMax, ax),
        anchor_value(bbox.YMin, bbox.YMax, ay),
        anchor_value(bbox.ZMin, bbox.ZMax, az),
    )


def placement_for_anchor(shape, target_point, anchor, rotation=None):
    if rotation is None:
        rotation = App.Rotation()
    temp_shape = shape.copy()
    temp_shape.Placement = App.Placement(App.Vector(0, 0, 0), rotation)
    current_anchor = bbox_anchor_point(temp_shape.BoundBox, anchor)
    offset = target_point.sub(current_anchor)
    return App.Placement(offset, rotation)


def add_imported_part(document, name, step_path, target_point, anchor, rotation=None):
    shape = read_step_shape(step_path)
    obj = document.addObject("Part::Feature", name)
    obj.Shape = shape
    obj.Placement = placement_for_anchor(shape, target_point, anchor, rotation)
    return obj


def add_box(document, name, length, width, height, base):
    obj = document.addObject("Part::Box", name)
    obj.Length = float(length)
    obj.Width = float(width)
    obj.Height = float(height)
    obj.Placement = App.Placement(base, App.Rotation())
    return obj


def main():
    doc = reset_doc(DOC_NAME)

    conveyor = add_imported_part(
        doc,
        "ConveyorBase_STEP",
        CONVEYOR_STEP,
        App.Vector(0, 0, 0),
        ("center", "center", "min"),
    )
    doc.recompute()
    conveyor_bbox = conveyor.Shape.copy()
    conveyor_bbox.Placement = conveyor.Placement
    conveyor_box = conveyor_bbox.BoundBox

    conveyor_top = conveyor_box.ZMax
    conveyor_left = conveyor_box.XMin
    conveyor_right = conveyor_box.XMax
    conveyor_center_x = (conveyor_box.XMin + conveyor_box.XMax) / 2.0
    conveyor_center_y = (conveyor_box.YMin + conveyor_box.YMax) / 2.0

    rail_gap_y = 180.0
    rail_mount_z = conveyor_top + 120.0
    rail_left = add_imported_part(
        doc,
        "RailLeft_STEP",
        RAIL_STEP,
        App.Vector(conveyor_center_x, conveyor_center_y - rail_gap_y, rail_mount_z),
        ("center", "center", "min"),
    )
    rail_right = add_imported_part(
        doc,
        "RailRight_STEP",
        RAIL_STEP,
        App.Vector(conveyor_center_x, conveyor_center_y + rail_gap_y, rail_mount_z),
        ("center", "center", "min"),
    )

    bridge_plate = add_box(
        doc,
        "BridgePlate",
        520.0,
        420.0,
        16.0,
        App.Vector(conveyor_center_x - 260.0, conveyor_center_y - 210.0, rail_mount_z + 26.0),
    )
    bridge_post_left = add_box(
        doc,
        "BridgePostLeft",
        32.0,
        32.0,
        120.0,
        App.Vector(conveyor_center_x - 220.0, conveyor_center_y - rail_gap_y - 16.0, conveyor_top),
    )
    bridge_post_right = add_box(
        doc,
        "BridgePostRight",
        32.0,
        32.0,
        120.0,
        App.Vector(conveyor_center_x - 220.0, conveyor_center_y + rail_gap_y - 16.0, conveyor_top),
    )
    bridge_post_left_rear = add_box(
        doc,
        "BridgePostLeftRear",
        32.0,
        32.0,
        120.0,
        App.Vector(conveyor_center_x + 188.0, conveyor_center_y - rail_gap_y - 16.0, conveyor_top),
    )
    bridge_post_right_rear = add_box(
        doc,
        "BridgePostRightRear",
        32.0,
        32.0,
        120.0,
        App.Vector(conveyor_center_x + 188.0, conveyor_center_y + rail_gap_y - 16.0, conveyor_top),
    )
    carriage_plate = add_box(
        doc,
        "CarriagePlate",
        180.0,
        160.0,
        12.0,
        App.Vector(conveyor_center_x - 90.0, conveyor_center_y - 80.0, rail_mount_z + 44.0),
    )

    motor_rotation = App.Rotation(App.Vector(0, 1, 0), 90)
    motor = add_imported_part(
        doc,
        "DriveMotor_STEP",
        MOTOR_STEP,
        App.Vector(conveyor_left - 90.0, conveyor_center_y + rail_gap_y, rail_mount_z + 52.0),
        ("center", "center", "center"),
        motor_rotation,
    )
    motor_bracket = add_box(
        doc,
        "MotorBracket",
        16.0,
        120.0,
        90.0,
        App.Vector(conveyor_left - 40.0, conveyor_center_y + rail_gap_y - 60.0, rail_mount_z + 7.0),
    )

    laser = add_imported_part(
        doc,
        "LaserHead_STEP",
        LASER_STEP,
        App.Vector(conveyor_center_x, conveyor_center_y, rail_mount_z + 44.0),
        ("center", "center", "max"),
    )

    cable_tray = add_box(
        doc,
        "CableTray",
        640.0,
        40.0,
        30.0,
        App.Vector(conveyor_center_x - 320.0, conveyor_center_y + 220.0, rail_mount_z + 70.0),
    )
    sensor_bar = add_box(
        doc,
        "SensorBar",
        680.0,
        20.0,
        20.0,
        App.Vector(conveyor_center_x - 340.0, conveyor_center_y - 250.0, conveyor_top + 40.0),
    )

    doc.recompute()
    doc.saveAs(OUTPUT_FCSTD)

    print("Conveyor cell assembly created")
    print("Saved FCStd:", OUTPUT_FCSTD)
    for obj in (
        conveyor,
        rail_left,
        rail_right,
        bridge_plate,
        bridge_post_left,
        bridge_post_right,
        bridge_post_left_rear,
        bridge_post_right_rear,
        carriage_plate,
        motor,
        motor_bracket,
        laser,
        cable_tray,
        sensor_bar,
    ):
        print(obj.Name)


if __name__ == "__main__":
    main()
