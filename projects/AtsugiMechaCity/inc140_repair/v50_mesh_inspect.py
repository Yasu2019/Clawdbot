# -*- coding: utf-8 -*-
import sys, json
if hasattr(sys.stdout, "reconfigure"):
    try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception: pass
import bpy, bmesh, mathutils

OUT = r"D:\tmp\v50_mesh_inspect_report.json"

def world_bbox(obj):
    lo = mathutils.Vector((1e18,)*3); hi = mathutils.Vector((-1e18,)*3)
    for c in obj.bound_box:
        w = obj.matrix_world @ mathutils.Vector(c)
        for i in range(3):
            lo[i] = min(lo[i], w[i]); hi[i] = max(hi[i], w[i])
    return lo, hi

def islands(bm):
    # count connected components over vertices via edges
    seen = set(); comps = 0
    verts = bm.verts
    for v in verts:
        if v.index in seen: continue
        comps += 1; stack=[v]; seen.add(v.index)
        while stack:
            cur = stack.pop()
            for e in cur.link_edges:
                o = e.other_vert(cur)
                if o.index not in seen:
                    seen.add(o.index); stack.append(o)
    return comps

def analyze(obj):
    me = obj.data
    bm = bmesh.new(); bm.from_mesh(me)
    bm.verts.ensure_lookup_table(); bm.edges.ensure_lookup_table(); bm.faces.ensure_lookup_table()
    boundary = sum(1 for e in bm.edges if len(e.link_faces) == 1)
    nonman   = sum(1 for e in bm.edges if len(e.link_faces) > 2)
    degen = 0
    for f in bm.faces:
        if f.calc_area() < 1e-9: degen += 1
    comp = islands(bm) if len(bm.verts) <= 200000 else -1
    lo, hi = world_bbox(obj)
    dim = [round(hi[i]-lo[i],5) for i in range(3)]
    bm.free()
    return {
        "name": obj.name, "hide_render": bool(obj.hide_render),
        "parent": obj.parent.name if obj.parent else None,
        "parent_bone": obj.parent_bone or None,
        "verts": len(me.vertices), "faces": len(me.polygons),
        "islands": comp, "boundary_edges": boundary, "nonmanifold_edges": nonman,
        "degenerate_faces": degen,
        "bbox_min": [round(lo[i],4) for i in range(3)],
        "bbox_max": [round(hi[i],4) for i in range(3)],
        "dims": dim,
        "center": [round((lo[i]+hi[i])*0.5,4) for i in range(3)],
    }

meshes = [o for o in bpy.data.objects if o.type == "MESH"]
rows = [analyze(o) for o in meshes]
report = {"blend": bpy.data.filepath, "mesh_count": len(rows), "meshes": rows}
with open(OUT, "w", encoding="utf-8") as f:
    json.dump(report, f, ensure_ascii=False, indent=2)

# concise stdout summary sorted by name
print(f"MESH_COUNT={len(rows)}")
for r in sorted(rows, key=lambda x: x["name"]):
    flag = ""
    if r["nonmanifold_edges"]>0: flag += " NONMANIFOLD"
    if r["degenerate_faces"]>0: flag += " DEGEN"
    if r["islands"]>1: flag += f" ISLANDS={r['islands']}"
    print(f"{r['name'][:38]:38s} v={r['verts']:6d} f={r['faces']:6d} bnd={r['boundary_edges']:5d} "
          f"dims={r['dims']} hr={int(r['hide_render'])} bone={r['parent_bone']}{flag}")
print("WROTE", OUT)
