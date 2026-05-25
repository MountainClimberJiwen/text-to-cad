# -*- coding: utf-8 -*-
import os

import FreeCAD as App
import Part


def ensure_step_exists(step_path):
    if not os.path.exists(step_path):
        raise FileNotFoundError(step_path)


def read_step_shape(step_path):
    ensure_step_exists(step_path)
    shape = Part.Shape()
    shape.read(step_path)
    return shape


def import_step_feature(doc, name, step_path, x=0.0, y=0.0, z=0.0, rot=None):
    shape = read_step_shape(step_path)
    obj = doc.addObject("Part::Feature", name)
    obj.Shape = shape
    if rot is None:
        rot = App.Rotation()
    obj.Placement = App.Placement(App.Vector(float(x), float(y), float(z)), rot)
    return obj


def get_step_summary(step_path):
    shape = read_step_shape(step_path)
    box = shape.BoundBox
    return {
        "solids": len(shape.Solids),
        "faces": len(shape.Faces),
        "edges": len(shape.Edges),
        "bbox": {
            "xmin": box.XMin,
            "ymin": box.YMin,
            "zmin": box.ZMin,
            "xmax": box.XMax,
            "ymax": box.YMax,
            "zmax": box.ZMax,
            "xlen": box.XLength,
            "ylen": box.YLength,
            "zlen": box.ZLength,
        },
    }
