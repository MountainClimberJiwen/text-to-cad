# -*- coding: utf-8 -*-
import os
import tempfile
import zipfile

import FreeCAD as App
import Part


DOC_NAME = "Laser_Gantry"
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(os.path.dirname(CURRENT_DIR))
OUTPUT_FCSTD = os.path.join(PROJECT_ROOT, "models", "fcstd", f"{DOC_NAME}.FCStd")

MAIN_BEAM_LEN_Y = 800.0
MAIN_BEAM_W_X = 40.0
MAIN_BEAM_H_Z = 40.0

ARM_LEN_X = 500.0
ARM_W_Y = 40.0
ARM_H_Z = 20.0

ARM_CENTER_Y = 125.0
ARM_BOTTOM_Z = 40.0
ARM_CENTER_Z = ARM_BOTTOM_Z + ARM_H_Z / 2.0

MOTOR_STEP_PATH = os.path.join(PROJECT_ROOT, "models", "step", "Nema17 4.4Kgcm Stepper Motor.step")
LASER_STEP_PATH = os.path.join(PROJECT_ROOT, "models", "step", "3. CNC 3DP Laser Engraving Head Opt Lasers.step")

MOTOR_LOCAL_LCS_POS = App.Vector(0, 0, 0)
MOTOR_LOCAL_LCS_ROT = App.Rotation(App.Vector(0, 0, 1), 0)
LASER_LOCAL_LCS_POS = App.Vector(0, 0, 0)
LASER_LOCAL_LCS_ROT = App.Rotation(App.Vector(0, 0, 1), 0)

DEFAULT_CAMERA = (
    "OrthographicCamera { viewportMapping ADJUST_CAMERA position 0 -2000 1200 "
    "orientation 0.57735 0.57735 0.57735 2.0944 nearDistance 10 farDistance 100000 "
    "aspectRatio 1 focalDistance 2500 height 1400 }"
)


def reset_doc(doc_name):
    if doc_name in App.listDocuments():
        App.closeDocument(doc_name)
    return App.newDocument(doc_name)


def make_lcs(document, name, pos, rot=None):
    if rot is None:
        rot = App.Rotation(App.Vector(0, 0, 1), 0)
    lcs = document.addObject("PartDesign::CoordinateSystem", name)
    lcs.Placement = App.Placement(pos, rot)
    return lcs


def make_box(document, name, length_x, length_y, length_z, base_vec):
    obj = document.addObject("Part::Box", name)
    obj.Length = length_x
    obj.Width = length_y
    obj.Height = length_z
    obj.Placement = App.Placement(base_vec, App.Rotation())
    return obj


def import_step_as_feature(document, name, step_path):
    shape = Part.Shape()
    shape.read(step_path)
    obj = document.addObject("Part::Feature", name)
    obj.Shape = shape
    return obj


def align_by_lcs(target_pos, target_rot, local_pos, local_rot):
    target_pl = App.Placement(target_pos, target_rot)
    local_pl = App.Placement(local_pos, local_rot)
    return target_pl.multiply(local_pl.inverse())


def create_placeholder_motor(document, name):
    body = document.addObject("Part::Box", name)
    body.Length = 48.0
    body.Width = 42.0
    body.Height = 42.0
    body.Placement = App.Placement(App.Vector(0, -21.0, -21.0), App.Rotation())
    return body


def create_placeholder_laser(document, name):
    body = document.addObject("Part::Box", name)
    body.Length = 60.0
    body.Width = 60.0
    body.Height = 80.0
    body.Placement = App.Placement(App.Vector(-30.0, -30.0, -80.0), App.Rotation())
    return body


def build_gui_document_xml(document):
    hidden_names = {
        "Origin",
        "X_Axis",
        "Y_Axis",
        "Z_Axis",
        "XY_Plane",
        "XZ_Plane",
        "YZ_Plane",
    }
    visible_objects = [obj for obj in document.Objects if obj.Name not in hidden_names]

    lines = [
        "<?xml version='1.0' encoding='utf-8'?>",
        "<!--",
        " FreeCAD Document, see https://www.freecad.org for more information...",
        "-->",
        "<Document SchemaVersion=\"1\">",
        f"    <ViewProviderData Count=\"{len(visible_objects)}\">",
    ]

    for obj in visible_objects:
        lines.extend([
            f"        <ViewProvider name=\"{obj.Name}\" expanded=\"0\">",
            "            <Properties Count=\"1\">",
            "                <Property name=\"Visibility\" type=\"App::PropertyBool\">",
            "                    <Bool value=\"true\"/>",
            "                </Property>",
            "            </Properties>",
            "        </ViewProvider>",
        ])

    lines.extend([
        "    </ViewProviderData>",
        f"    <Camera settings=\"  {DEFAULT_CAMERA}  \"/>",
        "</Document>",
        "",
    ])
    return "\n".join(lines)


def inject_gui_document(fcstd_path, document):
    gui_xml = build_gui_document_xml(document)
    fd, temp_path = tempfile.mkstemp(suffix=".FCStd")
    os.close(fd)
    try:
        with zipfile.ZipFile(fcstd_path, "r") as src, zipfile.ZipFile(temp_path, "w", zipfile.ZIP_DEFLATED) as dst:
            for info in src.infolist():
                if info.filename == "GuiDocument.xml":
                    continue
                dst.writestr(info, src.read(info.filename))
            dst.writestr("GuiDocument.xml", gui_xml.encode("utf-8"))
        os.replace(temp_path, fcstd_path)
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)


doc = reset_doc(DOC_NAME)

main_beam = make_box(
    doc,
    "Y_MainBeam_40x40",
    MAIN_BEAM_W_X,
    MAIN_BEAM_LEN_Y,
    MAIN_BEAM_H_Z,
    App.Vector(-MAIN_BEAM_W_X / 2.0, 0.0, 0.0),
)
lcs_main_origin = make_lcs(doc, "LCS_MainOrigin", App.Vector(0, 0, 20))

arm = make_box(
    doc,
    "X_Arm_20x40",
    ARM_LEN_X,
    ARM_W_Y,
    ARM_H_Z,
    App.Vector(-ARM_LEN_X / 2.0, ARM_CENTER_Y - ARM_W_Y / 2.0, ARM_BOTTOM_Z),
)
lcs_arm_mount = make_lcs(doc, "LCS_Arm_Mount", App.Vector(0, ARM_CENTER_Y, ARM_BOTTOM_Z))
lcs_arm_end = make_lcs(doc, "LCS_Arm_End", App.Vector(ARM_LEN_X / 2.0, ARM_CENTER_Y, ARM_CENTER_Z))
lcs_arm_bottom_center = make_lcs(doc, "LCS_Arm_Bottom_Center", App.Vector(0, ARM_CENTER_Y, ARM_BOTTOM_Z))

lcs_motor_local = make_lcs(doc, "LCS_MotorX_Face", MOTOR_LOCAL_LCS_POS, MOTOR_LOCAL_LCS_ROT)
if MOTOR_STEP_PATH and os.path.exists(MOTOR_STEP_PATH):
    motor_obj = import_step_as_feature(doc, "MotorX_STEP", MOTOR_STEP_PATH)
else:
    motor_obj = create_placeholder_motor(doc, "MotorX_Placeholder")
motor_obj.Placement = align_by_lcs(
    App.Vector(ARM_LEN_X / 2.0, ARM_CENTER_Y, ARM_CENTER_Z),
    App.Rotation(App.Vector(0, 0, 1), 0),
    MOTOR_LOCAL_LCS_POS,
    MOTOR_LOCAL_LCS_ROT,
)

lcs_laser_local = make_lcs(doc, "LCS_Laser_Mount", LASER_LOCAL_LCS_POS, LASER_LOCAL_LCS_ROT)
if LASER_STEP_PATH and os.path.exists(LASER_STEP_PATH):
    laser_obj = import_step_as_feature(doc, "Laser_STEP", LASER_STEP_PATH)
else:
    laser_obj = create_placeholder_laser(doc, "Laser_Placeholder")
laser_obj.Placement = align_by_lcs(
    App.Vector(0, ARM_CENTER_Y, ARM_BOTTOM_Z),
    App.Rotation(App.Vector(0, 0, 1), 0),
    LASER_LOCAL_LCS_POS,
    LASER_LOCAL_LCS_ROT,
)

doc.recompute()
doc.saveAs(OUTPUT_FCSTD)
inject_gui_document(OUTPUT_FCSTD, doc)

print("Assembly complete")
print("Saved FCStd:", OUTPUT_FCSTD)
print("Main beam:", main_beam.Name)
print("Arm:", arm.Name)
print("Motor:", motor_obj.Name)
print("Laser:", laser_obj.Name)
print("Main origin:", tuple(lcs_main_origin.Placement.Base))
print("Arm mount:", tuple(lcs_arm_mount.Placement.Base))
print("Arm end:", tuple(lcs_arm_end.Placement.Base))
print("Arm bottom center:", tuple(lcs_arm_bottom_center.Placement.Base))
