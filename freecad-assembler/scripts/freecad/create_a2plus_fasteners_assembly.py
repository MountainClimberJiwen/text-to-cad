# -*- coding: utf-8 -*-
import os
import sys
import traceback

import FreeCAD as App
import FreeCADGui
import Part


CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)
PROJECT_ROOT = os.path.dirname(os.path.dirname(CURRENT_DIR))

FREECAD_MOD_DIR = os.path.expanduser("~/Library/Application Support/FreeCAD/Mod")
for mod_name in ("A2plus", "Fasteners"):
    mod_path = os.path.join(FREECAD_MOD_DIR, mod_name)
    if mod_path not in sys.path:
        sys.path.insert(0, mod_path)


def ensure_gui_stubs():
    no_op = lambda *args, **kwargs: None
    for attr in (
        "addCommand",
        "addWorkbench",
        "addIconPath",
        "addLanguagePath",
        "updateLocale",
        "addPreferencePage",
    ):
        if not hasattr(FreeCADGui, attr):
            setattr(FreeCADGui, attr, no_op)


ensure_gui_stubs()

print("Loading A2plus and Fasteners modules...")
import a2p_importpart
import a2p_constraints
import a2p_importedPart_class
import a2p_solversystem
import a2p_topomapper
import FastenersCmd
print("Modules loaded")


_ORIGINAL_CREATE_TOPO_NAMES = a2p_topomapper.TopoMapper.createTopoNames
_ORIGINAL_SETUP_PROXIES = a2p_constraints.BasicConstraint.setupProxies


def patch_a2plus_for_headless():
    def create_topo_names_headless(self, desiredShapeLabel=None):
        if App.GuiUp:
            return _ORIGINAL_CREATE_TOPO_NAMES(self, desiredShapeLabel)

        allow_sketches = desiredShapeLabel is not None
        self.detectPartDesignDocument()
        self.getTopLevelObjects(allow_sketches)

        if desiredShapeLabel is not None:
            self.topLevelShapes = [
                obj_name
                for obj_name in self.topLevelShapes
                if self.doc.getObject(obj_name).Label == desiredShapeLabel
            ]

        shapes = []
        face_colors = []
        default_color = (0.8, 0.8, 0.8, 0.0)

        for obj_name in self.topLevelShapes:
            ob = self.doc.getObject(obj_name)
            temp_shape = self.makePlacedShape(ob)
            shapes.append(temp_shape)
            for _face in temp_shape.Faces:
                face_colors.append(default_color)

        if not shapes:
            raise RuntimeError("No top-level shapes available for A2plus import")

        if len(shapes) == 1:
            solid = shapes[0]
        else:
            solid = Part.makeCompound(shapes)

        return [], solid, face_colors, 0

    def setup_proxies_headless(self):
        c = self.constraintObject
        from a2p_viewProviderProxies import ConstraintObjectProxy

        c.Proxy = ConstraintObjectProxy()
        if c.ViewObject is not None:
            return _ORIGINAL_SETUP_PROXIES(self)

    a2p_topomapper.TopoMapper.createTopoNames = create_topo_names_headless
    a2p_constraints.BasicConstraint.setupProxies = setup_proxies_headless


patch_a2plus_for_headless()


ASSEMBLY_NAME = "A2plusFastenersDemo"
PLATE_A_NAME = "Plate_A"
PLATE_B_NAME = "Plate_B"

PLATE_A_PATH = os.path.join(PROJECT_ROOT, "models", "fcstd", f"{PLATE_A_NAME}.FCStd")
PLATE_B_PATH = os.path.join(PROJECT_ROOT, "models", "fcstd", f"{PLATE_B_NAME}.FCStd")
ASSEMBLY_PATH = os.path.join(PROJECT_ROOT, "models", "fcstd", f"{ASSEMBLY_NAME}.FCStd")

PLATE_LENGTH = 120.0
PLATE_WIDTH = 80.0
PLATE_THICKNESS = 8.0
HOLE_RADIUS = 3.2
HOLE_X = 25.0
HOLE_Y = 20.0
HOLE_PATTERN = (
    (HOLE_X, HOLE_Y),
    (PLATE_LENGTH - HOLE_X, HOLE_Y),
    (HOLE_X, PLATE_WIDTH - HOLE_Y),
    (PLATE_LENGTH - HOLE_X, PLATE_WIDTH - HOLE_Y),
)


class SelectionRef:
    def __init__(self, obj, subelement_name):
        self.Object = obj
        self.ObjectName = obj.Name
        self.SubElementNames = [subelement_name]


def reset_doc(doc_name):
    if doc_name in App.listDocuments():
        App.closeDocument(doc_name)
    return App.newDocument(doc_name)


def build_plate_shape():
    plate = Part.makeBox(PLATE_LENGTH, PLATE_WIDTH, PLATE_THICKNESS)
    for x, y in HOLE_PATTERN:
        hole = Part.makeCylinder(HOLE_RADIUS, PLATE_THICKNESS, App.Vector(x, y, 0))
        plate = plate.cut(hole)
    return plate


def save_plate(doc_name, output_path, label):
    doc = reset_doc(doc_name)
    obj = doc.addObject("Part::Feature", label)
    obj.Shape = build_plate_shape()
    obj.Label = label
    doc.recompute()
    doc.saveAs(output_path)
    App.closeDocument(doc.Name)


def import_a2plus_part_headless(doc, file_path):
    source_doc = App.openDocument(file_path)
    try:
        source_obj = None
        for obj in source_doc.Objects:
            if hasattr(obj, "Shape") and not obj.Shape.isNull():
                source_obj = obj
                break
        if source_obj is None:
            raise RuntimeError(f"No shape found in {file_path}")

        name = os.path.splitext(os.path.basename(file_path))[0].replace(" ", "_")
        imported = doc.addObject("Part::FeaturePython", name)
        a2p_importedPart_class.Proxy_importPart(imported)
        imported.Label = name
        imported.Shape = source_obj.Shape.copy()
        imported.sourceFile = file_path
        imported.sourcePart = source_obj.Name
        imported.localSourceObject = source_obj.Name
        imported.muxInfo = []
        imported.timeLastImport = os.path.getmtime(file_path)
        imported.fixedPosition = not any(
            hasattr(obj, "fixedPosition") and obj.fixedPosition for obj in doc.Objects if obj != imported
        )
        imported.subassemblyImport = False
        imported.updateColors = False
        return imported
    finally:
        App.closeDocument(source_doc.Name)


def circular_edges_at_z(shape, z_value=None, tolerance=0.01):
    matches = []
    for index, edge in enumerate(shape.Edges, start=1):
        curve = getattr(edge, "Curve", None)
        if not curve or not hasattr(curve, "Radius") or not hasattr(curve, "Center"):
            continue
        center = curve.Center
        if z_value is not None and abs(center.z - z_value) > tolerance:
            continue
        matches.append((index, center))
    matches.sort(key=lambda item: (round(item[1].x, 6), round(item[1].y, 6)))
    return [f"Edge{index}" for index, _center in matches]


def top_circular_edges(shape, tolerance=0.01):
    circles = []
    for index, edge in enumerate(shape.Edges, start=1):
        curve = getattr(edge, "Curve", None)
        if not curve or not hasattr(curve, "Radius") or not hasattr(curve, "Center"):
            continue
        circles.append((index, curve.Center))
    if not circles:
        return []
    top_z = max(center.z for _index, center in circles)
    matches = [
        (index, center)
        for index, center in circles
        if abs(center.z - top_z) <= tolerance
    ]
    matches.sort(key=lambda item: (round(item[1].x, 6), round(item[1].y, 6)))
    return [f"Edge{index}" for index, _center in matches]


def face_name_at_z(shape, z_value, tolerance=0.01):
    candidates = []
    for index, face in enumerate(shape.Faces, start=1):
        try:
            center = face.CenterOfMass
            _normal = face.normalAt(0, 0)
        except Exception:
            continue
        if abs(center.z - z_value) <= tolerance:
            candidates.append((face.Area, index))
    if candidates:
        candidates.sort(reverse=True)
        return f"Face{candidates[0][1]}"
    raise RuntimeError(f"Face not found at z={z_value}")


def add_plate_constraints(plate_a, plate_b):
    hole_edge_a = circular_edges_at_z(plate_a.Shape)[0]
    hole_edge_b = circular_edges_at_z(plate_b.Shape)[0]

    constraint = a2p_constraints.CircularEdgeConstraint(
        (SelectionRef(plate_a, hole_edge_a), SelectionRef(plate_b, hole_edge_b))
    )
    constraint.constraintObject.offset = PLATE_THICKNESS
    constraint.constraintObject.lockRotation = True


def add_fastener(doc, target_obj, edge_name, name):
    fastener = doc.addObject("Part::FeaturePython", name)
    FastenersCmd.FSScrewObject(fastener, "ISO4762", (target_obj, [edge_name]))
    fastener.Diameter = "M6"
    fastener.Thread = False
    fastener.Offset = 0.0
    return fastener


def build_assembly():
    save_plate(PLATE_A_NAME, PLATE_A_PATH, PLATE_A_NAME)
    save_plate(PLATE_B_NAME, PLATE_B_PATH, PLATE_B_NAME)

    doc = reset_doc(ASSEMBLY_NAME)
    App.setActiveDocument(doc.Name)
    doc.saveAs(ASSEMBLY_PATH)

    plate_a = import_a2plus_part_headless(doc, PLATE_A_PATH)
    plate_b = import_a2plus_part_headless(doc, PLATE_B_PATH)
    plate_b.Placement.Base = App.Vector(0, 0, 30)
    doc.recompute()
    App.setActiveDocument(doc.Name)

    add_plate_constraints(plate_a, plate_b)
    a2p_solversystem.solveConstraints(doc, useTransaction=False)
    doc.recompute()

    top_hole_edges = top_circular_edges(plate_b.Shape)
    fasteners = []
    for index, edge_name in enumerate(top_hole_edges, start=1):
        fasteners.append(add_fastener(doc, plate_b, edge_name, f"Bolt_M6x20_{index}"))

    doc.recompute()
    doc.save()

    print("Assembly created")
    print("Assembly file:", ASSEMBLY_PATH)
    print("Parts:", PLATE_A_PATH, PLATE_B_PATH)
    print("Imported objects:", plate_a.Name, plate_b.Name)
    print("Constraints:", len([obj for obj in doc.Objects if "ConstraintInfo" in obj.Content]))
    print("Fasteners:", ", ".join(obj.Name for obj in fasteners))


try:
    print("Starting assembly build")
    build_assembly()
    print("Done")
except Exception:
    traceback.print_exc()
    raise
