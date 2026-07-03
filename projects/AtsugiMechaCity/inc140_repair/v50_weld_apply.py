# -*- coding: utf-8 -*-
"""Weld unwelded (triangle-soup) meshes in the V50 build and save to a NEW blend.
Read source via --input, write welded to --output. Does NOT touch the source file.
Detection: a mesh is 'unwelded' when boundary_edges > faces*0.5 (verts ~= faces*3).
Fix per mesh: remove_doubles -> recalc normals consistent (outward) -> shade smooth.
"""
import sys, json
if hasattr(sys.stdout, "reconfigure"):
    try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception: pass
import bpy, bmesh

argv = sys.argv[sys.argv.index("--")+1:] if "--" in sys.argv else []
INP = argv[argv.index("--input")+1]
OUT = argv[argv.index("--output")+1]
REPORT = argv[argv.index("--report")+1]

bpy.ops.wm.open_mainfile(filepath=INP)

def edge_stats(bm):
    bnd = sum(1 for e in bm.edges if len(e.link_faces) == 1)
    non = sum(1 for e in bm.edges if len(e.link_faces) > 2)
    return bnd, non

rows = []
for obj in [o for o in bpy.data.objects if o.type == "MESH"]:
    me = obj.data
    if len(me.polygons) == 0:
        continue
    bm = bmesh.new(); bm.from_mesh(me)
    bnd0, non0 = edge_stats(bm)
    faces0 = len(bm.faces); verts0 = len(bm.verts)
    unwelded = bnd0 > faces0 * 0.5
    if not unwelded:
        bm.free()
        continue
    maxdim = max(obj.dimensions) or 1.0
    thr = max(1e-6, maxdim * 0.0005)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=thr)
    bm.normal_update()
    # recalc normals consistent outward
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(me)
    bm.free()
    # shade smooth
    for p in me.polygons:
        p.use_smooth = True
    me.update()
    # re-measure
    bm2 = bmesh.new(); bm2.from_mesh(me)
    bnd1, non1 = edge_stats(bm2)
    faces1 = len(bm2.faces); verts1 = len(bm2.verts)
    bm2.free()
    rows.append({"name": obj.name, "thr": round(thr,6),
                 "verts": [verts0, verts1], "faces": [faces0, faces1],
                 "boundary": [bnd0, bnd1], "nonman": [non0, non1]})
    print(f"WELDED {obj.name:18s} v {verts0:7d}->{verts1:6d}  bnd {bnd0:7d}->{bnd1:5d}  nonman {non0}->{non1}")

bpy.ops.wm.save_as_mainfile(filepath=OUT)
with open(REPORT, "w", encoding="utf-8") as f:
    json.dump({"input": INP, "output": OUT, "welded_count": len(rows), "meshes": rows}, f, ensure_ascii=False, indent=2)
print(f"WELDED_COUNT={len(rows)}")
print("SAVED", OUT)
