
import FreeCAD as App
import Part
import importDXF

doc = App.newDocument("DXFImport")
importDXF.insert("/home/node/clawd/apps/dxf2step/jobs/20260305_054528_b54dc019/output/Front.cleaned.dxf", "DXFImport")

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
            # Extrude each closed face to a solid, then fuse all solids.
            # Using makeCompound().extrude() is WRONG: it creates separate
            # unjoined shells instead of a unified solid (e.g. L-shape from
            # two overlapping rectangles would give two separate boxes).
            solids = []
            for f in faces:
                try:
                    solids.append(f.extrude(App.Vector(0, 0, 60.0)))
                except Exception as se:
                    print(f"Extrude error: {se}")
            if solids:
                result = solids[0]
                for s in solids[1:]:
                    result = result.fuse(s)
                result.exportStep("/home/node/clawd/apps/dxf2step/jobs/20260305_054528_b54dc019/output/Front.step")
                print(f"Exported: /home/node/clawd/apps/dxf2step/jobs/20260305_054528_b54dc019/output/Front.step  faces={len(result.Faces)}")
            else:
                print("Extrusion failed for all faces")
        else:
            print("No closed faces found — check if DXF outlines form closed loops")
    except Exception as e:
        print(f"Error building solid: {e}")
else:
    print("No edges found in /home/node/clawd/apps/dxf2step/jobs/20260305_054528_b54dc019/output/Front.cleaned.dxf")
