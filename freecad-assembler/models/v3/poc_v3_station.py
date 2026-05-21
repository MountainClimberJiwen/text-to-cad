import FreeCAD as App
import Part
import Mesh

doc = App.newDocument("poc_v3_station")

box = doc.addObject("Part::Box", "base_plate")
box.Length = 800.0
box.Width = 500.0
box.Height = 15.0
box.Placement.Base = App.Vector(0.0, 0.0, 0.0)
if hasattr(box, "ViewObject") and box.ViewObject:
    box.ViewObject.ShapeColor = (0.7, 0.7, 0.75)

box = doc.addObject("Part::Box", "vib_bowl")
box.Length = 200.0
box.Width = 200.0
box.Height = 30.0
box.Placement.Base = App.Vector(550.0, 0.0, 15.0)
if hasattr(box, "ViewObject") and box.ViewObject:
    box.ViewObject.ShapeColor = (0.85, 0.6, 0.2)

box = doc.addObject("Part::Box", "vib_track")
box.Length = 20.0
box.Width = 10.0
box.Height = 150.0
box.Placement.Base = App.Vector(520.0, 95.0, 15.0)
if hasattr(box, "ViewObject") and box.ViewObject:
    box.ViewObject.ShapeColor = (0.5, 0.5, 0.5)

box = doc.addObject("Part::Box", "vib_hopper")
box.Length = 120.0
box.Width = 120.0
box.Height = 100.0
box.Placement.Base = App.Vector(620.0, -10.0, 95.0)
if hasattr(box, "ViewObject") and box.ViewObject:
    box.ViewObject.ShapeColor = (0.5, 0.5, 0.55)

box = doc.addObject("Part::Box", "vib_support")
box.Length = 20.0
box.Width = 20.0
box.Height = 80.0
box.Placement.Base = App.Vector(640.0, 90.0, 15.0)
if hasattr(box, "ViewObject") and box.ViewObject:
    box.ViewObject.ShapeColor = (0.4, 0.4, 0.4)

box = doc.addObject("Part::Box", "gantry_horiz_cyl")
box.Length = 25.0
box.Width = 25.0
box.Height = 290.0
box.Placement.Base = App.Vector(387.5, 237.5, 295.0)
if hasattr(box, "ViewObject") and box.ViewObject:
    box.ViewObject.ShapeColor = (0.2, 0.5, 0.8)

box = doc.addObject("Part::Box", "gantry_horiz_slider")
box.Length = 40.0
box.Width = 40.0
box.Height = 30.0
box.Placement.Base = App.Vector(380.0, 230.0, 295.0)
if hasattr(box, "ViewObject") and box.ViewObject:
    box.ViewObject.ShapeColor = (0.3, 0.7, 0.3)

box = doc.addObject("Part::Box", "gantry_vert_cyl")
box.Length = 20.0
box.Width = 20.0
box.Height = 160.0
box.Placement.Base = App.Vector(390.0, 240.0, 325.0)
if hasattr(box, "ViewObject") and box.ViewObject:
    box.ViewObject.ShapeColor = (0.2, 0.5, 0.8)

box = doc.addObject("Part::Box", "gantry_gripper")
box.Length = 40.0
box.Width = 25.0
box.Height = 20.0
box.Placement.Base = App.Vector(380.0, 237.5, 485.0)
if hasattr(box, "ViewObject") and box.ViewObject:
    box.ViewObject.ShapeColor = (0.8, 0.2, 0.2)

box = doc.addObject("Part::Box", "gantry_jaw_l")
box.Length = 10.857670466379625
box.Width = 20.358132124461797
box.Height = 27.144176165949062
box.Placement.Base = App.Vector(380.57116476681017, 239.8209339377691, 505.00000000000006)
if hasattr(box, "ViewObject") and box.ViewObject:
    box.ViewObject.ShapeColor = (0.9, 0.3, 0.3)

box = doc.addObject("Part::Box", "gantry_jaw_r")
box.Length = 10.857670466379625
box.Width = 20.358132124461797
box.Height = 27.144176165949062
box.Placement.Base = App.Vector(408.57116476681017, 239.8209339377691, 505.00000000000006)
if hasattr(box, "ViewObject") and box.ViewObject:
    box.ViewObject.ShapeColor = (0.9, 0.3, 0.3)

box = doc.addObject("Part::Box", "fix_base")
box.Length = 100.0
box.Width = 100.0
box.Height = 50.0
box.Placement.Base = App.Vector(100.0, 350.0, 15.0)
if hasattr(box, "ViewObject") and box.ViewObject:
    box.ViewObject.ShapeColor = (0.7, 0.7, 0.75)

box = doc.addObject("Part::Box", "fix_plate")
box.Length = 80.0
box.Width = 80.0
box.Height = 10.0
box.Placement.Base = App.Vector(110.0, 360.0, 65.0)
if hasattr(box, "ViewObject") and box.ViewObject:
    box.ViewObject.ShapeColor = (0.6, 0.4, 0.2)

box = doc.addObject("Part::Box", "fix_push_cyl")
box.Length = 16.0
box.Width = 16.0
box.Height = 80.0
box.Placement.Base = App.Vector(82.0, 392.0, 15.0)
if hasattr(box, "ViewObject") and box.ViewObject:
    box.ViewObject.ShapeColor = (0.2, 0.5, 0.8)

box = doc.addObject("Part::Box", "gantry_horiz_cyl_guide")
box.Length = 10.0
box.Width = 15.0
box.Height = 348.0
box.Placement.Base = App.Vector(414.5, 242.5, 266.0)
if hasattr(box, "ViewObject") and box.ViewObject:
    box.ViewObject.ShapeColor = (0.2, 0.5, 0.8)

box = doc.addObject("Part::Box", "gantry_vert_cyl_guide")
box.Length = 10.0
box.Width = 15.0
box.Height = 192.0
box.Placement.Base = App.Vector(412.0, 242.5, 309.0)
if hasattr(box, "ViewObject") and box.ViewObject:
    box.ViewObject.ShapeColor = (0.2, 0.5, 0.8)

box = doc.addObject("Part::Box", "gantry_left_col")
box.Length = 30.0
box.Width = 30.0
box.Height = 250.0
box.Placement.Base = App.Vector(235.0, 235.0, 15.0)
if hasattr(box, "ViewObject") and box.ViewObject:
    box.ViewObject.ShapeColor = (0.3, 0.3, 0.35)

box = doc.addObject("Part::Box", "gantry_right_col")
box.Length = 30.0
box.Width = 30.0
box.Height = 250.0
box.Placement.Base = App.Vector(535.0, 235.0, 15.0)
if hasattr(box, "ViewObject") and box.ViewObject:
    box.ViewObject.ShapeColor = (0.3, 0.3, 0.35)

box = doc.addObject("Part::Box", "gantry_beam")
box.Length = 350.0
box.Width = 30.0
box.Height = 30.0
box.Placement.Base = App.Vector(225.0, 235.0, 265.0)
if hasattr(box, "ViewObject") and box.ViewObject:
    box.ViewObject.ShapeColor = (0.4, 0.4, 0.45)

doc.recompute()
