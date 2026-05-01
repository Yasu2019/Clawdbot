"""FreeCAD macro: create a simple plate and export STEP.
Run from FreeCAD macro editor or FreeCADCmd.exe.
"""
import os
import FreeCAD as App
import Part

root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
out_dir = os.path.join(root, "outputs", "freecad_plate")
os.makedirs(out_dir, exist_ok=True)

doc = App.newDocument("FreeCAD_Plate_Sample")
length = 100.0
width = 20.0
thickness = 2.0

box = Part.makeBox(length, width, thickness)
# Move so center is near origin
box.translate(App.Vector(-length/2, -width/2, 0))

# Cut holes
for x in (-30, 30):
    cyl = Part.makeCylinder(3.0, thickness + 2, App.Vector(x, 0, -1), App.Vector(0, 0, 1))
    box = box.cut(cyl)

obj = doc.addObject("Part::Feature", "plate_with_holes")
obj.Shape = box
doc.recompute()

step_path = os.path.join(out_dir, "freecad_plate.step")
Part.export([obj], step_path)
print("Exported:", step_path)
