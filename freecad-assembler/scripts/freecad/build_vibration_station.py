# -*- coding: utf-8 -*-
import FreeCAD as App
import Part
import os

def reset_doc(name):
    if name in App.listDocuments():
        App.closeDocument(name)
    return App.newDocument(name)

doc = reset_doc("VibrationFeederStation")

# ========== 0. 白色安装底板 ==========
base = doc.addObject("Part::Feature", "base_plate")
base.Shape = Part.makeBox(400, 300, 10)
base.Placement.Base = App.Vector(0, 0, 0)
if hasattr(base, "ViewObject") and base.ViewObject is not None:
    base.ViewObject.ShapeColor = (1.0, 1.0, 1.0)

# ========== 1. 振动盘 (右下) ==========
# 主体：圆柱底座 + 螺旋轨道近似为阶梯圆柱
bowl_base = doc.addObject("Part::Feature", "vib_bowl_base")
bowl_base.Shape = Part.makeCylinder(90, 40)
bowl_base.Placement.Base = App.Vector(280, 150, 10)
if hasattr(bowl_base, "ViewObject") and bowl_base.ViewObject is not None:
    bowl_base.ViewObject.ShapeColor = (0.7, 0.75, 0.8)

bowl_top = doc.addObject("Part::Feature", "vib_bowl_top")
bowl_top.Shape = Part.makeCylinder(100, 20)
bowl_top.Placement.Base = App.Vector(280, 150, 50)
if hasattr(bowl_top, "ViewObject") and bowl_top.ViewObject is not None:
    bowl_top.ViewObject.ShapeColor = (0.75, 0.8, 0.85)

# 出料轨道（向左延伸的方条）
track = doc.addObject("Part::Feature", "vib_track")
track.Shape = Part.makeBox(80, 20, 5)
track.Placement.Base = App.Vector(200, 140, 55)
if hasattr(track, "ViewObject") and track.ViewObject is not None:
    track.ViewObject.ShapeColor = (0.6, 0.65, 0.7)

# ========== 2. 料斗 (右上) ==========
hopper = doc.addObject("Part::Feature", "hopper")
outer = Part.makeBox(120, 100, 80)
inner = Part.makeBox(100, 80, 75)
inner.translate(App.Vector(10, 10, 5))
hopper.Shape = outer.cut(inner)
hopper.Placement.Base = App.Vector(250, 60, 70)
if hasattr(hopper, "ViewObject") and hopper.ViewObject is not None:
    hopper.ViewObject.ShapeColor = (0.9, 0.9, 0.92)

hopper_stand = doc.addObject("Part::Feature", "hopper_stand")
hopper_stand.Shape = Part.makeBox(60, 60, 60)
hopper_stand.Placement.Base = App.Vector(280, 80, 10)
if hasattr(hopper_stand, "ViewObject") and hopper_stand.ViewObject is not None:
    hopper_stand.ViewObject.ShapeColor = (0.5, 0.55, 0.65)

# ========== 3. 左侧导向送料机构 ==========
guide_base = doc.addObject("Part::Feature", "guide_base")
guide_base.Shape = Part.makeBox(60, 60, 80)
guide_base.Placement.Base = App.Vector(30, 120, 10)
if hasattr(guide_base, "ViewObject") and guide_base.ViewObject is not None:
    guide_base.ViewObject.ShapeColor = (0.85, 0.8, 0.6)

guide_rail = doc.addObject("Part::Feature", "guide_rail")
guide_rail.Shape = Part.makeBox(100, 15, 10)
guide_rail.Placement.Base = App.Vector(30, 142, 90)
if hasattr(guide_rail, "ViewObject") and guide_rail.ViewObject is not None:
    guide_rail.ViewObject.ShapeColor = (0.15, 0.15, 0.15)

guide_slider = doc.addObject("Part::Feature", "guide_slider")
guide_slider.Shape = Part.makeBox(30, 20, 12)
guide_slider.Placement.Base = App.Vector(50, 140, 90)
if hasattr(guide_slider, "ViewObject") and guide_slider.ViewObject is not None:
    guide_slider.ViewObject.ShapeColor = (0.5, 0.5, 0.5)

hc_left = doc.addObject("Part::Feature", "hc_left")
hc_left.Shape = Part.makeCylinder(8, 80, App.Vector(40, 147, 95), App.Vector(1, 0, 0))
if hasattr(hc_left, "ViewObject") and hc_left.ViewObject is not None:
    hc_left.ViewObject.ShapeColor = (0.75, 0.78, 0.8)

guide_cyl = doc.addObject("Part::Feature", "guide_cyl")
guide_cyl.Shape = Part.makeCylinder(10, 50, App.Vector(50, 150, 95), App.Vector(0, 0, 1))
if hasattr(guide_cyl, "ViewObject") and guide_cyl.ViewObject is not None:
    guide_cyl.ViewObject.ShapeColor = (0.2, 0.2, 0.25)

# ========== 4. 中间门架搬运机构 ==========
column = doc.addObject("Part::Feature", "column")
column.Shape = Part.makeBox(20, 60, 200)
column.Placement.Base = App.Vector(180, 120, 10)
if hasattr(column, "ViewObject") and column.ViewObject is not None:
    column.ViewObject.ShapeColor = (0.85, 0.8, 0.6)

horiz_cyl = doc.addObject("Part::Feature", "horiz_cyl")
horiz_cyl.Shape = Part.makeCylinder(12, 120, App.Vector(180, 150, 210), App.Vector(1, 0, 0))
if hasattr(horiz_cyl, "ViewObject") and horiz_cyl.ViewObject is not None:
    horiz_cyl.ViewObject.ShapeColor = (0.1, 0.1, 0.1)

vert_cyl = doc.addObject("Part::Feature", "vert_cyl")
vert_cyl.Shape = Part.makeCylinder(10, 80, App.Vector(200, 150, 130), App.Vector(0, 0, 1))
if hasattr(vert_cyl, "ViewObject") and vert_cyl.ViewObject is not None:
    vert_cyl.ViewObject.ShapeColor = (0.12, 0.12, 0.12)

green_plate = doc.addObject("Part::Feature", "green_plate")
green_plate.Shape = Part.makeBox(8, 40, 50)
green_plate.Placement.Base = App.Vector(196, 130, 80)
if hasattr(green_plate, "ViewObject") and green_plate.ViewObject is not None:
    green_plate.ViewObject.ShapeColor = (0.2, 0.7, 0.3)

# ========== 5. 产品夹爪 (中下) ==========
gripper_body = doc.addObject("Part::Feature", "gripper_body")
gripper_body.Shape = Part.makeBox(20, 25, 15)
gripper_body.Placement.Base = App.Vector(190, 137, 65)
if hasattr(gripper_body, "ViewObject") and gripper_body.ViewObject is not None:
    gripper_body.ViewObject.ShapeColor = (0.55, 0.55, 0.6)

jaw_l = doc.addObject("Part::Feature", "gripper_jaw_l")
jaw_l.Shape = Part.makeBox(4, 8, 15)
jaw_l.Placement.Base = App.Vector(192, 145, 50)
if hasattr(jaw_l, "ViewObject") and jaw_l.ViewObject is not None:
    jaw_l.ViewObject.ShapeColor = (0.4, 0.4, 0.45)

jaw_r = doc.addObject("Part::Feature", "gripper_jaw_r")
jaw_r.Shape = Part.makeBox(4, 8, 15)
jaw_r.Placement.Base = App.Vector(204, 145, 50)
if hasattr(jaw_r, "ViewObject") and jaw_r.ViewObject is not None:
    jaw_r.ViewObject.ShapeColor = (0.4, 0.4, 0.45)

# ========== 6. 中间工装平台 ==========
fixture_base = doc.addObject("Part::Feature", "fixture_base")
fixture_base.Shape = Part.makeBox(60, 60, 30)
fixture_base.Placement.Base = App.Vector(160, 120, 10)
if hasattr(fixture_base, "ViewObject") and fixture_base.ViewObject is not None:
    fixture_base.ViewObject.ShapeColor = (0.1, 0.1, 0.1)

fixture_plat = doc.addObject("Part::Feature", "fixture_plat")
fixture_plat.Shape = Part.makeBox(50, 50, 8)
fixture_plat.Placement.Base = App.Vector(165, 125, 40)
if hasattr(fixture_plat, "ViewObject") and fixture_plat.ViewObject is not None:
    fixture_plat.ViewObject.ShapeColor = (0.95, 0.95, 0.98)

sample_part = doc.addObject("Part::Feature", "sample_part")
sample_part.Shape = Part.makeCylinder(6, 20)
sample_part.Placement.Base = App.Vector(190, 150, 48)
if hasattr(sample_part, "ViewObject") and sample_part.ViewObject is not None:
    sample_part.ViewObject.ShapeColor = (0.6, 0.3, 0.7)

# ========== 保存 ==========
doc.recompute()
fcstd_path = "/Users/jiwen/PycharmProjects/freecad-assembler/models/fcstd/vibration_station.FCStd"
step_path = "/Users/jiwen/PycharmProjects/freecad-assembler/models/step/vibration_station.step"
os.makedirs(os.path.dirname(fcstd_path), exist_ok=True)
os.makedirs(os.path.dirname(step_path), exist_ok=True)
doc.saveAs(fcstd_path)

import Import
Import.export(doc.Objects, step_path)
print("FCStd:", fcstd_path)
print("STEP:", step_path)
print("Objects:", [o.Name for o in doc.Objects])
