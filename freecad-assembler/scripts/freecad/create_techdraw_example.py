# -*- coding: utf-8 -*-
import os
import shutil

import FreeCAD as App
import Part
import TechDraw


DOC_NAME = "TechDrawDetailedExample"
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(os.path.dirname(CURRENT_DIR))
OUTPUT_FCSTD = os.path.join(PROJECT_ROOT, "models", "fcstd", f"{DOC_NAME}.FCStd")
LOCAL_ASSET_DIR = os.path.join(PROJECT_ROOT, "assets", "techdraw")
LOCAL_TEMPLATE = os.path.join(LOCAL_ASSET_DIR, "A3_Landscape_TD.svg")

PLATE_LENGTH = 160.0
PLATE_WIDTH = 100.0
PLATE_THICKNESS = 12.0
BOSS_LENGTH = 72.0
BOSS_WIDTH = 44.0
BOSS_HEIGHT = 18.0
HOLE_RADIUS = 5.0
SLOT_RADIUS = 7.0
SLOT_LENGTH = 42.0


def reset_doc(doc_name):
    if doc_name in App.listDocuments():
        App.closeDocument(doc_name)
    return App.newDocument(doc_name)


def ensure_local_template():
    if os.path.exists(LOCAL_TEMPLATE):
        return LOCAL_TEMPLATE

    os.makedirs(LOCAL_ASSET_DIR, exist_ok=True)
    source_template = os.path.join(
        App.getResourceDir(),
        "Mod",
        "TechDraw",
        "Templates",
        "A3_Landscape_TD.svg",
    )
    shutil.copyfile(source_template, LOCAL_TEMPLATE)
    return LOCAL_TEMPLATE


def make_slot_shape(length, radius, depth, center):
    straight_len = max(length - 2.0 * radius, 0.0)
    left_center = App.Vector(center.x - straight_len / 2.0, center.y, center.z)
    right_center = App.Vector(center.x + straight_len / 2.0, center.y, center.z)

    slot = Part.makeCylinder(radius, depth, left_center)
    slot = slot.fuse(Part.makeCylinder(radius, depth, right_center))
    if straight_len > 0.0:
        slot = slot.fuse(
            Part.makeBox(
                straight_len,
                2.0 * radius,
                depth,
                App.Vector(left_center.x, center.y - radius, center.z),
            )
        )
    return slot


def build_demo_shape():
    base = Part.makeBox(PLATE_LENGTH, PLATE_WIDTH, PLATE_THICKNESS)

    boss = Part.makeBox(
        BOSS_LENGTH,
        BOSS_WIDTH,
        BOSS_HEIGHT,
        App.Vector(
            (PLATE_LENGTH - BOSS_LENGTH) / 2.0,
            (PLATE_WIDTH - BOSS_WIDTH) / 2.0,
            PLATE_THICKNESS,
        ),
    )

    part_shape = base.fuse(boss)

    hole_centers = (
        App.Vector(24.0, 20.0, 0.0),
        App.Vector(PLATE_LENGTH - 24.0, 20.0, 0.0),
        App.Vector(24.0, PLATE_WIDTH - 20.0, 0.0),
        App.Vector(PLATE_LENGTH - 24.0, PLATE_WIDTH - 20.0, 0.0),
    )
    for center in hole_centers:
        part_shape = part_shape.cut(
            Part.makeCylinder(HOLE_RADIUS, PLATE_THICKNESS + BOSS_HEIGHT, center)
        )

    slot = make_slot_shape(
        length=SLOT_LENGTH,
        radius=SLOT_RADIUS,
        depth=PLATE_THICKNESS + 1.0,
        center=App.Vector(PLATE_LENGTH / 2.0, 22.0, 0.0),
    )
    part_shape = part_shape.cut(slot)
    return part_shape


def find_top_horizontal_circular_edge(shape, radius, x_hint, y_hint, z_hint, tol=0.05):
    for index, edge in enumerate(shape.Edges, start=1):
        curve = getattr(edge, "Curve", None)
        if curve is None or not hasattr(curve, "Radius") or not hasattr(curve, "Center"):
            continue
        if abs(curve.Radius - radius) > tol:
            continue
        if abs(curve.Center.x - x_hint) > tol or abs(curve.Center.y - y_hint) > tol:
            continue
        if abs(curve.Center.z - z_hint) > tol:
            continue
        return f"Edge{index}"
    raise RuntimeError(f"No top circular edge found at ({x_hint}, {y_hint}, {z_hint})")


def add_dimension(doc, page, name, dim_type, refs3d, x, y, fmt=None):
    dim = doc.addObject("TechDraw::DrawViewDimension", name)
    dim.Type = dim_type
    dim.References3D = refs3d
    dim.X = float(x)
    dim.Y = float(y)
    if fmt:
        dim.FormatSpec = fmt
    page.addView(dim)
    return dim


def build_page(doc, part_obj):
    template_path = ensure_local_template()

    page = doc.addObject("TechDraw::DrawPage", "TechDrawPage")
    template = doc.addObject("TechDraw::DrawSVGTemplate", "PageTemplate")
    template.Template = template_path
    page.Template = template

    editable = template.EditableTexts
    editable["CompanyName"] = "Codex FreeCAD Demo"
    editable["DrawingTitle1"] = "Detailed TechDraw Example"
    editable["DrawingTitle2"] = "plate + boss + slot + hole pattern"
    editable["DrawnBy"] = "Codex"
    editable["CheckedBy"] = "FreeCAD"
    editable["Scale"] = "1:1"
    editable["Sheet"] = "1 / 1"
    editable["Code"] = "TD-EX-001"
    template.EditableTexts = editable

    proj = doc.addObject("TechDraw::DrawProjGroup", "OrthographicViews")
    proj.Source = [part_obj]
    proj.ProjectionType = "Third Angle"
    proj.Scale = 1.0
    proj.X = 115.0
    proj.Y = 150.0
    page.addView(proj)
    proj.addProjection("Front")
    proj.addProjection("Top")
    proj.addProjection("Right")

    iso = doc.addObject("TechDraw::DrawViewPart", "IsometricView")
    iso.Source = [part_obj]
    iso.Direction = App.Vector(1, -1, 1)
    iso.Scale = 0.65
    iso.X = 245.0
    iso.Y = 155.0
    iso.Caption = "ISOMETRIC"
    page.addView(iso)

    doc.recompute()

    add_dimension(
        doc,
        page,
        "DimOverallLength",
        "DistanceX",
        [(part_obj, ["Vertex1"]), (part_obj, ["Vertex2"])],
        115.0,
        44.0,
    )
    add_dimension(
        doc,
        page,
        "DimOverallWidth",
        "DistanceY",
        [(part_obj, ["Vertex1"]), (part_obj, ["Vertex4"])],
        26.0,
        112.0,
    )
    add_dimension(
        doc,
        page,
        "DimPlateThickness",
        "DistanceY",
        [(part_obj, ["Vertex1"]), (part_obj, ["Vertex5"])],
        198.0,
        150.0,
    )
    add_dimension(
        doc,
        page,
        "DimBossHeight",
        "DistanceY",
        [(part_obj, ["Vertex5"]), (part_obj, ["Vertex13"])],
        226.0,
        152.0,
    )
    add_dimension(
        doc,
        page,
        "DimBossLength",
        "DistanceX",
        [(part_obj, ["Vertex9"]), (part_obj, ["Vertex10"])],
        115.0,
        82.0,
    )

    hole_edge = find_top_horizontal_circular_edge(
        part_obj.Shape,
        radius=HOLE_RADIUS,
        x_hint=24.0,
        y_hint=20.0,
        z_hint=PLATE_THICKNESS,
    )
    add_dimension(
        doc,
        page,
        "DimHoleDiameter",
        "Diameter",
        [(part_obj, [hole_edge])],
        47.0,
        82.0,
        fmt="dia %%value",
    )

    slot_edge = find_top_horizontal_circular_edge(
        part_obj.Shape,
        radius=SLOT_RADIUS,
        x_hint=PLATE_LENGTH / 2.0 - (SLOT_LENGTH - 2.0 * SLOT_RADIUS) / 2.0,
        y_hint=22.0,
        z_hint=PLATE_THICKNESS,
    )
    add_dimension(
        doc,
        page,
        "DimSlotWidth",
        "Diameter",
        [(part_obj, [slot_edge])],
        117.0,
        116.0,
        fmt="slot %%value",
    )

    return page


def main():
    doc = reset_doc(DOC_NAME)

    part_obj = doc.addObject("Part::Feature", "DetailedPlate")
    part_obj.Shape = build_demo_shape()
    part_obj.Label = "Detailed Plate"

    doc.recompute()
    doc.saveAs(OUTPUT_FCSTD)

    page = build_page(doc, part_obj)
    doc.recompute()
    doc.save()

    print("TechDraw example created")
    print("Saved FCStd:", OUTPUT_FCSTD)
    print("Page:", page.Name)
    print("Part:", part_obj.Name)


if __name__ == "__main__":
    main()
