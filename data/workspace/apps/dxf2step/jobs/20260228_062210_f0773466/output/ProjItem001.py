
import FreeCAD as App
import Part
import importDXF

doc = App.newDocument("DXFImport")
importDXF.insert("/home/node/clawd/apps/dxf2step/jobs/20260228_062210_f0773466/output/ProjItem001.cleaned.dxf", "DXFImport")

# Collect all edges from imported objects
edges = []
for obj in doc.Objects:
    if hasattr(obj, "Shape"):
        edges.extend(obj.Shape.Edges)

if edges:
    try:
        sorted_edge_groups = Part.sortEdges(edges)
        faces = []
        for edge_group in sorted_edge_groups:
            try:
                wire = Part.Wire(edge_group)
                if wire.isClosed():
                    face = Part.Face(wire)
                    faces.append(face)
            except Exception as we:
                print(f"Wire/Face error: {we}")

        if faces:
            solid = Part.makeCompound(faces).extrude(App.Vector(0, 0, 10.0))
            solid.exportStep("/home/node/clawd/apps/dxf2step/jobs/20260228_062210_f0773466/output/ProjItem001.step")
            print("Exported: /home/node/clawd/apps/dxf2step/jobs/20260228_062210_f0773466/output/ProjItem001.step")
        else:
            print("No closed faces found — check if DXF outlines form closed loops")
    except Exception as e:
        print(f"Error building solid: {e}")
else:
    print("No edges found in /home/node/clawd/apps/dxf2step/jobs/20260228_062210_f0773466/output/ProjItem001.cleaned.dxf")
