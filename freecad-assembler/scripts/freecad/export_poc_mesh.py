# -*- coding: utf-8 -*-
import FreeCAD as App
import json
import os
doc = App.openDocument("/Users/jiwen/PycharmProjects/freecad-assembler/models/fcstd/poc_station.FCStd")
meshes = []
for obj in doc.Objects:
    if hasattr(obj, "Shape") and not obj.Shape.isNull():
        verts, tris = obj.Shape.tessellate(0.5)
        if verts:
            meshes.append({
                "name": obj.Name,
                "vertices": [(v.x, v.y, v.z) for v in verts],
                "triangles": list(tris),
                "placement": {
                    "base": (obj.Placement.Base.x, obj.Placement.Base.y, obj.Placement.Base.z),
                    "rotation": obj.Placement.Rotation.Q
                }
            })
out = "/Users/jiwen/PycharmProjects/freecad-assembler/models/preview/poc_mesh_data.json"
os.makedirs(os.path.dirname(out), exist_ok=True)
with open(out, "w") as f:
    json.dump(meshes, f)
print("MESH_OK")
