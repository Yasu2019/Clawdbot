
import FreeCAD as App
import Part
import importDXF

doc = App.newDocument("DXFImport")
importDXF.insert("/home/node/clawd/apps/dxf2step/test_output_S1/1.cleaned.dxf", "DXFImport")

# Collect all edges from imported objects
edges = []
for obj in doc.Objects:
    if hasattr(obj, "Shape"):
        edges.extend(obj.Shape.Edges)

if edges:
    try:
        sorted_edge_groups = Part.sortEdges(edges)
        wires = []
        for edge_group in sorted_edge_groups:
            try:
                wire = Part.Wire(edge_group)
                if wire.isClosed():
                    wires.append(wire)
            except Exception as we:
                print(f"Wire error: {we}")

        if wires:
            # Detect circles and find concentric pairs (counterbores)
            circles = []
            for w in wires:
                if len(w.Edges) == 1 and "Circle" in type(w.Edges[0].Curve).__name__:
                    circles.append({
                        "wire": w,
                        "center": (round(w.Edges[0].Curve.Center.x, 3), round(w.Edges[0].Curve.Center.y, 3)),
                        "radius": w.Edges[0].Curve.Radius
                    })
            
            concentric_pairs = []
            skip_wires = set()
            for i in range(len(circles)):
                for j in range(i + 1, len(circles)):
                    c1 = circles[i]
                    c2 = circles[j]
                    dist = ((c1["center"][0] - c2["center"][0])**2 + (c1["center"][1] - c2["center"][1])**2)**0.5
                    if dist < 0.05:
                        inner = c1 if c1["radius"] < c2["radius"] else c2
                        outer = c2 if c1["radius"] < c2["radius"] else c1
                        concentric_pairs.append((inner, outer))
                        skip_wires.add(outer["wire"])
            
            # Filter out outer wires of counterbores
            wires = [w for w in wires if w not in skip_wires]

            # Sort wires by the area of their face descending
            try:
                wires.sort(key=lambda w: Part.Face(w).Area, reverse=True)
            except Exception as se:
                print(f"Wire sorting error: {se}")

            base_faces = []
            for w in wires:
                try:
                    test_face = Part.Face(w)
                    contained = False
                    for i, base_face in enumerate(base_faces):
                        cut_face = base_face.cut(test_face)
                        # If the cut reduces the base_face area, test_face is inside it.
                        if base_face.Area - cut_face.Area > 0.1:
                            base_faces[i] = cut_face
                            contained = True
                            break
                    if not contained:
                        base_faces.append(test_face)
                except Exception as fe:
                    print(f"Face/containment error: {fe}")

            if len(base_faces) > 1:
                raise Exception("NG_MULTIPLE_PROFILES: 1つの面（レイヤー）に複数の独立した外形プロファイルが検出されました。基本DXFは部品単体の図面であるため、複数部品やバラ図はNG（未対応）対象となります。")

            if base_faces:
                # Extrude each outer face (with its cut holes) to a solid, then fuse them.
                solids = []
                for f in base_faces:
                    try:
                        solids.append(f.extrude(App.Vector(0, 0, 3.0)))
                    except Exception as se:
                        print(f"Extrude error: {se}")
                if solids:
                    result = solids[0]
                    for s in solids[1:]:
                        result = result.fuse(s)
                    # Clean up coplanar face splits from Boolean fuse
                    try:
                        cleaned = result.removeSplitter()
                        if cleaned.isValid() and getattr(cleaned, "Volume", 0) > 0:
                            result = cleaned
                            print(f"removeSplitter: {len(result.Faces)} faces")
                    except Exception as rse:
                        print(f"removeSplitter skipped: {rse}")

                    # Apply counterbore pockets
                    for inner, outer in concentric_pairs:
                        try:
                            cx, cy = inner["center"]
                            R1 = inner["radius"]
                            R2 = outer["radius"]
                            d1 = R1 * 2.0
                            d2 = R2 * 2.0
                            h = min(5.0, 3.0 * 0.5)
                            jis_table = [
                                (3.2, 3.8,  5.8, 6.5,   3.3), # M3
                                (4.2, 4.8,  7.8, 8.5,   4.4), # M4
                                (5.2, 5.8,  9.2, 10.0,  5.4), # M5
                                (6.2, 6.8,  10.8, 11.5, 6.5), # M6
                                (8.2, 9.2,  13.8, 14.5, 8.6), # M8
                            ]
                            for j_d1_min, j_d1_max, j_d2_min, j_d2_max, j_h in jis_table:
                                if j_d1_min <= d1 <= j_d1_max and j_d2_min <= d2 <= j_d2_max:
                                    h = j_h
                                    break
                            
                            pocket = Part.makeCylinder(R2, h, App.Vector(cx, cy, 3.0 - h), App.Vector(0, 0, 1))
                            result = result.cut(pocket)
                            print(f"[Counterbore] Created M-type pocket at ({cx}, {cy}) outer radius {R2} depth {h}")
                        except Exception as cbe:
                            print(f"Counterbore pocket build failed: {cbe}")

                    try:
                        area = result.Area
                        volume = result.Volume
                        bbox = result.BoundBox
                        dim_x = bbox.XMax - bbox.XMin
                        dim_y = bbox.YMax - bbox.YMin
                        dim_z = bbox.ZMax - bbox.ZMin
                        print(f"Metrics: V={volume:.1f} A={area:.1f} D={dim_x:.1f}x{dim_y:.1f}x{dim_z:.1f}")
                    except Exception as me:
                        print(f"Metrics error: {me}")
                    
                    result.exportStep("/home/node/clawd/apps/dxf2step/test_output_S1/1.step")
                    try:
                        out_doc = App.newDocument("LayerModel")
                        obj = out_doc.addObject("Part::Feature", "LayerSolid")
                        obj.Shape = result
                        out_doc.recompute()
                        out_doc.saveAs("/home/node/clawd/apps/dxf2step/test_output_S1/1.FCStd")
                        print(f"Saved FCStd: /home/node/clawd/apps/dxf2step/test_output_S1/1.FCStd")
                    except Exception as fce:
                        print(f"FCStd save failed: {fce}")
                    print(f"Exported: /home/node/clawd/apps/dxf2step/test_output_S1/1.step  faces={len(result.Faces)}")
                else:
                    print("Extrusion failed for all faces")
            else:
                print("No faces built after containment analysis")
        else:
            print("No closed faces found — check if DXF outlines form closed loops")
    except Exception as e:
        print(f"Error building solid: {e}")
else:
    print("No edges found in /home/node/clawd/apps/dxf2step/test_output_S1/1.cleaned.dxf")
