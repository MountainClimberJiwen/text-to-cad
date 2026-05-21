import json, numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection

with open("/Users/jiwen/PycharmProjects/freecad-assembler/models/preview/poc_v2_mesh_data.json") as f:
    meshes = json.load(f)

fig = plt.figure(figsize=(18, 13))
ax = fig.add_subplot(111, projection='3d')

cmap = {
    "base_plate": (0.98, 0.98, 0.98), "vib_bowl_base": (0.55, 0.60, 0.68),
    "vib_bowl": (0.65, 0.70, 0.78), "vib_track": (0.50, 0.55, 0.60),
    "vib_spiral": (0.45, 0.50, 0.55), "hopper_support": (0.50, 0.55, 0.65),
    "hopper": (0.90, 0.90, 0.93), "column_left": (0.85, 0.80, 0.60),
    "column_right": (0.85, 0.80, 0.60), "beam": (0.10, 0.10, 0.10),
    "horiz_cyl_body": (0.10, 0.10, 0.10), "horiz_cyl_piston": (0.30, 0.30, 0.35),
    "horiz_slider": (0.30, 0.30, 0.35), "vert_cyl_body": (0.12, 0.12, 0.12),
    "vert_cyl_piston": (0.12, 0.12, 0.12), "vert_guide_rail_l": (0.40, 0.40, 0.40),
    "vert_guide_rail_r": (0.40, 0.40, 0.40), "vert_guide_slider": (0.48, 0.48, 0.48),
    "green_plate": (0.18, 0.65, 0.25), "gripper_body": (0.52, 0.52, 0.58),
    "gripper_jaw_l": (0.38, 0.38, 0.43), "gripper_jaw_r": (0.38, 0.38, 0.43),
    "gripper_piston": (0.20, 0.20, 0.25), "fixture_base": (0.10, 0.10, 0.10),
    "fixture_plat": (0.95, 0.95, 0.98), "sample_part": (0.58, 0.30, 0.68),
    "guide_base": (0.82, 0.78, 0.58), "guide_rail": (0.14, 0.14, 0.14),
    "guide_slider": (0.48, 0.48, 0.48), "guide_cyl": (0.20, 0.20, 0.25)
}

all_v = []
for mesh in meshes:
    verts = np.array(mesh["vertices"])
    tris = np.array(mesh["triangles"])
    if len(tris) == 0: continue
    q = mesh["placement"]["rotation"]
    x, y, z, w = q
    R = np.array([[
        1-2*(y*y+z*z), 2*(x*y-z*w), 2*(x*z+y*w)],
        [2*(x*y+z*w), 1-2*(x*x+z*z), 2*(y*z-x*w)],
        [2*(x*z-y*w), 2*(y*z+x*w), 1-2*(x*x+y*y)]])
    vr = verts @ R.T
    b = mesh["placement"]["base"]
    vr += np.array([b[0], b[1], b[2]])
    all_v.append(vr)
    faces = vr[tris]
    c = cmap.get(mesh["name"], (0.6, 0.6, 0.6))
    ax.add_collection3d(Poly3DCollection(faces, alpha=0.95, facecolor=c, edgecolor='none'))

all_v = np.vstack(all_v)
rng = np.array([all_v[:,0].max()-all_v[:,0].min(),
                all_v[:,1].max()-all_v[:,1].min(),
                all_v[:,2].max()-all_v[:,2].min()]).max()/2.0
mx, my, mz = (all_v[:,0].max()+all_v[:,0].min())*0.5, (all_v[:,1].max()+all_v[:,1].min())*0.5, (all_v[:,2].max()+all_v[:,2].min())*0.5
ax.set_xlim(mx-rng, mx+rng); ax.set_ylim(my-rng, my+rng); ax.set_zlim(mz-rng, mz+rng)
ax.view_init(elev=28, azim=-50)
ax.set_title('POC v2: Rule-Driven Vibration Feeder Station')
ax.set_axis_off()
plt.savefig("/Users/jiwen/PycharmProjects/freecad-assembler/models/preview/poc_v2_station.png", dpi=150, bbox_inches='tight', facecolor='white')
print("RENDER_OK")
