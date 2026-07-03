# -*- coding: utf-8 -*-
"""Dump world matrices + bbox centers of all mesh objects in the ORIGINAL V50 blend."""
import sys, json
if hasattr(sys.stdout,"reconfigure"):
    try: sys.stdout.reconfigure(encoding="utf-8",errors="replace")
    except Exception: pass
import bpy
from mathutils import Vector

argv=sys.argv[sys.argv.index("--")+1:] if "--" in sys.argv else []
INP=argv[argv.index("--input")+1]; OUT=argv[argv.index("--out")+1]
bpy.ops.wm.open_mainfile(filepath=INP)

data={}
for o in bpy.data.objects:
    if o.type!="MESH": continue
    lo=Vector((1e18,)*3); hi=Vector((-1e18,)*3)
    for c in o.bound_box:
        w=o.matrix_world@Vector(c)
        for i in range(3): lo[i]=min(lo[i],w[i]); hi[i]=max(hi[i],w[i])
    ctr=(lo+hi)*0.5
    data[o.name]={
        "matrix_world":[list(row) for row in o.matrix_world],
        "center":[round(ctr[i],6) for i in range(3)],
        "dims":[round(hi[i]-lo[i],6) for i in range(3)],
    }
with open(OUT,"w",encoding="utf-8") as f: json.dump(data,f,indent=1)
print(f"DUMPED {len(data)} objects -> {OUT}")
