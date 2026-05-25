# -*- coding: utf-8 -*-
"""
Extract tessellated mesh from all Part objects and save to JSON for external rendering.
"""
import FreeCAD as App
import json
import os

doc = App.openDocument("/Users/jiwen/PycharmProjects/freecad-assembler/models/fcstd/vibration_station.FCStd")

meshes = []
for obj in doc.Objects:
    if hasattr(obj, "Shape") and not obj.Shape.isNull():
        # tessellate returns (vertices, triangles)
        # vertices: list of App.Vector
        # triangles: list of (i1, i2, i3) int tuples
        verts, tris = obj.Shape.tessellate(0.5)
        if not verts:
            continue
        meshes.append({
            "name": obj.Name,
            "vertices": [(v.x, v.y, v.z) for v in verts],
            "triangles": list(tris),
            "placement": {
                "base": (obj.Placement.Base.x, obj.Placement.Base.y, obj.Placement.Base.z),
                "rotation": obj.Placement.Rotation.Q
            }
        })

out_path = "/Users/jiwen/PycharmProjects/freecad-assembler/models/preview/mesh_data.json"
os.makedirs(os.path.dirname(out_path), exist_ok=True)
with open(out_path, "w") as f:
    json.dump(meshes, f)
print("Mesh data saved to", out_path, "objects:", len(meshes))
