import json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection

with open("/Users/jiwen/PycharmProjects/freecad-assembler/models/preview/mesh_data.json") as f:
    meshes = json.load(f)

fig = plt.figure(figsize=(14, 10))
ax = fig.add_subplot(111, projection='3d')

color_map = {
    "base_plate": (0.95, 0.95, 0.95),
    "vib_bowl_base": (0.55, 0.6, 0.7),
    "vib_bowl_top": (0.65, 0.7, 0.8),
    "vib_track": (0.5, 0.55, 0.6),
    "hopper": (0.88, 0.88, 0.9),
    "hopper_stand": (0.45, 0.5, 0.6),
    "guide_base": (0.8, 0.75, 0.55),
    "guide_rail": (0.12, 0.12, 0.12),
    "guide_slider": (0.45, 0.45, 0.45),
    "hc_left": (0.7, 0.73, 0.75),
    "guide_cyl": (0.18, 0.18, 0.22),
    "column": (0.8, 0.75, 0.55),
    "horiz_cyl": (0.08, 0.08, 0.08),
    "vert_cyl": (0.1, 0.1, 0.1),
    "green_plate": (0.15, 0.6, 0.2),
    "gripper_body": (0.5, 0.5, 0.55),
    "gripper_jaw_l": (0.35, 0.35, 0.4),
    "gripper_jaw_r": (0.35, 0.35, 0.4),
    "fixture_base": (0.08, 0.08, 0.08),
    "fixture_plat": (0.9, 0.9, 0.93),
    "sample_part": (0.55, 0.25, 0.65),
}

all_verts = []

for mesh in meshes:
    verts = np.array(mesh["vertices"])
    tris = np.array(mesh["triangles"])
    if len(tris) == 0:
        continue
    q = mesh["placement"]["rotation"]
    x, y, z, w = q
    R = np.array([
        [1-2*(y*y+z*z), 2*(x*y-z*w), 2*(x*z+y*w)],
        [2*(x*y+z*w), 1-2*(x*x+z*z), 2*(y*z-x*w)],
        [2*(x*z-y*w), 2*(y*z+x*w), 1-2*(x*x+y*y)]
    ])
    verts_rot = verts @ R.T
    b = mesh["placement"]["base"]
    verts_rot += np.array([b[0], b[1], b[2]])
    all_verts.append(verts_rot)
    faces = verts_rot[tris]
    color = color_map.get(mesh["name"], (0.6, 0.6, 0.6))
    poly3d = Poly3DCollection(faces, alpha=0.95, facecolor=color, edgecolor='none')
    ax.add_collection3d(poly3d)

all_v = np.vstack(all_verts)
max_range = np.array([all_v[:,0].max()-all_v[:,0].min(),
                      all_v[:,1].max()-all_v[:,1].min(),
                      all_v[:,2].max()-all_v[:,2].min()]).max() / 2.0
mid_x = (all_v[:,0].max()+all_v[:,0].min()) * 0.5
mid_y = (all_v[:,1].max()+all_v[:,1].min()) * 0.5
mid_z = (all_v[:,2].max()+all_v[:,2].min()) * 0.5
ax.set_xlim(mid_x - max_range, mid_x + max_range)
ax.set_ylim(mid_y - max_range, mid_y + max_range)
ax.set_zlim(mid_z - max_range, mid_z + max_range)
ax.view_init(elev=28, azim=-55)
ax.set_title('Vibration Feeder Station - 3D Preview')
ax.set_axis_off()

out_path = "/Users/jiwen/PycharmProjects/freecad-assembler/models/preview/vibration_station.png"
plt.savefig(out_path, dpi=150, bbox_inches='tight', facecolor='white')
print("Saved preview to", out_path)
