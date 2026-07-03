import sys, json
if hasattr(sys.stdout,"reconfigure"):
    try: sys.stdout.reconfigure(encoding="utf-8",errors="replace")
    except Exception: pass
import bpy
from mathutils import Vector
argv=sys.argv[sys.argv.index("--")+1:] if "--" in sys.argv else []
INP=argv[argv.index("--input")+1]; ORIGJ=argv[argv.index("--orig")+1]
with open(ORIGJ,encoding="utf-8") as f: ORIG=json.load(f)
bpy.ops.wm.open_mainfile(filepath=INP)
def wc(o):
    lo=Vector((1e18,)*3); hi=Vector((-1e18,)*3)
    for c in o.bound_box:
        w=o.matrix_world@Vector(c)
        for i in range(3): lo[i]=min(lo[i],w[i]); hi[i]=max(hi[i],w[i])
    return (lo+hi)*0.5
rows=[]
for o in bpy.data.objects:
    if o.type!="MESH" or o.name not in ORIG: continue
    c=wc(o); oc=Vector(ORIG[o.name]["center"])
    d=(c-oc).length
    rows.append((d,o.name,[round(c[i],3) for i in range(3)],[round(oc[i],3) for i in range(3)],bool(o.hide_render),bool(o.hide_viewport)))
rows.sort(reverse=True)
print("displacement vs ORIGINAL (top 25):")
for d,nm,c,oc,hr,hv in rows[:25]:
    print(f"{d:6.3f}  {nm:28s} now={c} orig={oc} hide_r={int(hr)} hide_v={int(hv)}")
# also list meshes in ORIG that are MISSING in current build
cur={o.name for o in bpy.data.objects if o.type=="MESH"}
missing=[n for n in ORIG if n not in cur]
print("MISSING vs orig:", missing)
extra=[o.name for o in bpy.data.objects if o.type=="MESH" and o.name not in ORIG]
print("EXTRA vs orig:", extra)
