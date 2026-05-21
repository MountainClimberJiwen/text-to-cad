# -*- coding: utf-8 -*-
import FreeCAD as App
import Part

doc = App.newDocument('POC_Station')

obj = doc.addObject('Part::Feature', 'base_plate')
obj.Shape = Part.makeBox(600, 450, 15)
obj.Placement.Base = App.Vector(0.0, 0.0, 0)
if hasattr(obj, 'ViewObject') and obj.ViewObject: obj.ViewObject.ShapeColor = (0.98, 0.98, 0.98)

obj = doc.addObject('Part::Feature', 'vib_bowl_base')
obj.Shape = Part.makeCylinder(90, 40)
obj.Placement.Base = App.Vector(440.0, 80.0, 15)
if hasattr(obj, 'ViewObject') and obj.ViewObject: obj.ViewObject.ShapeColor = (0.55, 0.6, 0.68)

obj = doc.addObject('Part::Feature', 'vib_bowl')
obj.Shape = Part.makeCylinder(80, 50)
obj.Placement.Base = App.Vector(440.0, 80.0, 15)
if hasattr(obj, 'ViewObject') and obj.ViewObject: obj.ViewObject.ShapeColor = (0.65, 0.7, 0.78)

obj = doc.addObject('Part::Feature', 'vib_track')
obj.Shape = Part.makeBox(100, 25, 8)
obj.Placement.Base = App.Vector(260.0, 67.5, 55)
if hasattr(obj, 'ViewObject') and obj.ViewObject: obj.ViewObject.ShapeColor = (0.5, 0.55, 0.6)

obj = doc.addObject('Part::Feature', 'hopper_stand')
obj.Shape = Part.makeBox(70, 70, 80)
obj.Placement.Base = App.Vector(425.0, -35.0, 15)
if hasattr(obj, 'ViewObject') and obj.ViewObject: obj.ViewObject.ShapeColor = (0.5, 0.55, 0.65)

obj = doc.addObject('Part::Feature', 'hopper')
obj.Shape = Part.makeBox(140, 110, 90)
obj.Placement.Base = App.Vector(390.0, -55.0, 95)
if hasattr(obj, 'ViewObject') and obj.ViewObject: obj.ViewObject.ShapeColor = (0.9, 0.9, 0.93)

obj = doc.addObject('Part::Feature', 'column')
obj.Shape = Part.makeBox(20, 60, 250)
obj.Placement.Base = App.Vector(290.0, 195.0, 15)
if hasattr(obj, 'ViewObject') and obj.ViewObject: obj.ViewObject.ShapeColor = (0.85, 0.8, 0.6)

obj = doc.addObject('Part::Feature', 'horiz_cyl')
obj.Shape = Part.makeBox(250, 30, 30)
obj.Placement.Base = App.Vector(175.0, 210.0, 265)
if hasattr(obj, 'ViewObject') and obj.ViewObject: obj.ViewObject.ShapeColor = (0.1, 0.1, 0.1)

obj = doc.addObject('Part::Feature', 'horiz_slider')
obj.Shape = Part.makeBox(40, 40, 25)
obj.Placement.Base = App.Vector(360.0, 205.0, 260)
if hasattr(obj, 'ViewObject') and obj.ViewObject: obj.ViewObject.ShapeColor = (0.3, 0.3, 0.35)

obj = doc.addObject('Part::Feature', 'vert_cyl')
obj.Shape = Part.makeBox(20, 20, 140)
obj.Placement.Base = App.Vector(370.0, 215.0, 120)
if hasattr(obj, 'ViewObject') and obj.ViewObject: obj.ViewObject.ShapeColor = (0.12, 0.12, 0.12)

obj = doc.addObject('Part::Feature', 'green_plate')
obj.Shape = Part.makeBox(8, 50, 60)
obj.Placement.Base = App.Vector(376.0, 200.0, 70)
if hasattr(obj, 'ViewObject') and obj.ViewObject: obj.ViewObject.ShapeColor = (0.18, 0.65, 0.25)

obj = doc.addObject('Part::Feature', 'gripper_body')
obj.Shape = Part.makeBox(30, 28, 20)
obj.Placement.Base = App.Vector(365.0, 211.0, 50)
if hasattr(obj, 'ViewObject') and obj.ViewObject: obj.ViewObject.ShapeColor = (0.52, 0.52, 0.58)

obj = doc.addObject('Part::Feature', 'gripper_jaw_l')
obj.Shape = Part.makeBox(5, 8, 18)
obj.Placement.Base = App.Vector(369.5, 221.0, 32)
if hasattr(obj, 'ViewObject') and obj.ViewObject: obj.ViewObject.ShapeColor = (0.38, 0.38, 0.43)

obj = doc.addObject('Part::Feature', 'gripper_jaw_r')
obj.Shape = Part.makeBox(5, 8, 18)
obj.Placement.Base = App.Vector(385.5, 221.0, 32)
if hasattr(obj, 'ViewObject') and obj.ViewObject: obj.ViewObject.ShapeColor = (0.38, 0.38, 0.43)

obj = doc.addObject('Part::Feature', 'fixture_base')
obj.Shape = Part.makeBox(80, 80, 40)
obj.Placement.Base = App.Vector(175.0, 40.0, 15)
if hasattr(obj, 'ViewObject') and obj.ViewObject: obj.ViewObject.ShapeColor = (0.1, 0.1, 0.1)

obj = doc.addObject('Part::Feature', 'fixture_plat')
obj.Shape = Part.makeBox(70, 70, 10)
obj.Placement.Base = App.Vector(180.0, 45.0, 55)
if hasattr(obj, 'ViewObject') and obj.ViewObject: obj.ViewObject.ShapeColor = (0.95, 0.95, 0.98)

obj = doc.addObject('Part::Feature', 'sample_part')
obj.Shape = Part.makeCylinder(8, 22)
obj.Placement.Base = App.Vector(215.0, 80.0, 65)
if hasattr(obj, 'ViewObject') and obj.ViewObject: obj.ViewObject.ShapeColor = (0.58, 0.3, 0.68)

obj = doc.addObject('Part::Feature', 'guide_base')
obj.Shape = Part.makeBox(80, 80, 100)
obj.Placement.Base = App.Vector(20.0, 0.0, 15)
if hasattr(obj, 'ViewObject') and obj.ViewObject: obj.ViewObject.ShapeColor = (0.82, 0.78, 0.58)

obj = doc.addObject('Part::Feature', 'guide_rail')
obj.Shape = Part.makeBox(120, 18, 12)
obj.Placement.Base = App.Vector(0.0, 31.0, 120)
if hasattr(obj, 'ViewObject') and obj.ViewObject: obj.ViewObject.ShapeColor = (0.14, 0.14, 0.14)

obj = doc.addObject('Part::Feature', 'guide_slider')
obj.Shape = Part.makeBox(35, 28, 18)
obj.Placement.Base = App.Vector(62.5, 26.0, 118)
if hasattr(obj, 'ViewObject') and obj.ViewObject: obj.ViewObject.ShapeColor = (0.48, 0.48, 0.48)

obj = doc.addObject('Part::Feature', 'guide_cyl')
obj.Shape = Part.makeBox(50, 12, 12)
obj.Placement.Base = App.Vector(65.0, 34.0, 125)
if hasattr(obj, 'ViewObject') and obj.ViewObject: obj.ViewObject.ShapeColor = (0.2, 0.2, 0.25)

doc.recompute()
import os; os.makedirs(os.path.dirname('/Users/jiwen/PycharmProjects/freecad-assembler/models/fcstd/poc_station.FCStd'), exist_ok=True)
doc.saveAs('/Users/jiwen/PycharmProjects/freecad-assembler/models/fcstd/poc_station.FCStd')
import Import; Import.export(doc.Objects, '/Users/jiwen/PycharmProjects/freecad-assembler/models/step/poc_station.step')
print('DONE: /Users/jiwen/PycharmProjects/freecad-assembler/models/step/poc_station.step')