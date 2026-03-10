
import FreeCAD as App
import Part
import importDXF

doc = App.newDocument("DXFImport")
importDXF.insert("D:/Clawdbot_Docker_20260125/data/workspace/apps/dxf2step/jobs/20260228_055943_32c99d7a/output/View.cleaned.dxf", "DXFImport")

# Combine all shapes into one
shapes = [obj.Shape for obj in doc.Objects if hasattr(obj, "Shape")]
if shapes:
    comp = Part.makeCompound(shapes)
    face = Part.Face(comp) # Try to make face
    solid = face.extrude(App.Vector(0, 0, 10))
    solid.exportStep("D:/Clawdbot_Docker_20260125/data/workspace/apps/dxf2step/jobs/20260228_055943_32c99d7a/output/View.step")
    print("Exported: D:/Clawdbot_Docker_20260125/data/workspace/apps/dxf2step/jobs/20260228_055943_32c99d7a/output/View.step")
else:
    print("No shapes found in D:/Clawdbot_Docker_20260125/data/workspace/apps/dxf2step/jobs/20260228_055943_32c99d7a/output/View.cleaned.dxf")
