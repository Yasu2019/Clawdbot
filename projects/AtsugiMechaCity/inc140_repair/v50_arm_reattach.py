# -*- coding: utf-8 -*-
"""INC-140 arm reattachment: restore V50 arm meshes to ORIGINAL positions and move
arm bones/markers/shared-cores to anatomically correct pivots derived from the
original mesh clusters. Non-destructive: saves to --output."""
import sys, json
if hasattr(sys.stdout,"reconfigure"):
    try: sys.stdout.reconfigure(encoding="utf-8",errors="replace")
    except Exception: pass
import bpy
from mathutils import Matrix, Vector

argv=sys.argv[sys.argv.index("--")+1:] if "--" in sys.argv else []
INP=argv[argv.index("--input")+1]
ORIGJ=argv[argv.index("--orig-json")+1]
OUT=argv[argv.index("--output")+1]

with open(ORIGJ,encoding="utf-8") as f: ORIG=json.load(f)

ARM_MESHES = [
    # UpperArm_L cluster
    "geometry_0.012","geometry_0.018","geometry_0.020","geometry_0.034",
    # LowerArm_L cluster
    "geometry_0.023","geometry_0.032","geometry_0.005",
    # UpperArm_R cluster
    "geometry_0.002","geometry_0.019","geometry_0.021","geometry_0.022",
    # LowerArm_R cluster
    "geometry_0.024","geometry_0.033",
    # Hand_R
    "geometry_0.006",
]

def orig_center(name):
    return Vector(ORIG[name]["center"])

# Joint pivots derived from ORIGINAL mesh cluster anchors
shoulder_L = orig_center("geometry_0.012")            # shoulder ball shell L
shoulder_R = orig_center("geometry_0.022")            # shoulder ball shell R
elbow_L    = orig_center("geometry_0.023")            # elbow cap L
elbow_R    = orig_center("geometry_0.024")            # elbow cap R
# wrist: distal end between forearm shells and hand region
g5c=orig_center("geometry_0.005"); g5d=Vector(ORIG["geometry_0.005"]["dims"])
wrist_L = Vector((g5c.x, g5c.y, g5c.z + g5d.z*0.25))  # upper quarter of forearm-end mesh
g6c=orig_center("geometry_0.006"); g6d=Vector(ORIG["geometry_0.006"]["dims"])
wrist_R = Vector((g6c.x, g6c.y, g6c.z + g6d.z*0.55))  # just above hand mesh top

PIVOTS = {
    "shoulder_L": shoulder_L, "elbow_L": elbow_L, "wrist_L": wrist_L,
    "shoulder_R": shoulder_R, "elbow_R": elbow_R, "wrist_R": wrist_R,
}
print("PIVOTS:")
for k,v in PIVOTS.items(): print(f"  {k}: {[round(v[i],3) for i in range(3)]}")

bpy.ops.wm.open_mainfile(filepath=INP)

# --- 1) move arm bones on EVERY armature that has them ---
# The build contains two armatures: Robot_Mechanical_Armature (legacy action) and
# V50_Generic_Armature (the one arm meshes are bone-parented to and the one
# v50_final_walk_preview.py animates). Both must agree on the new pivots.
hand_tail_L = wrist_L + Vector((-0.12, 0.0, -0.12))
hand_tail_R = wrist_R + Vector(( 0.12, 0.0, -0.12))
targets=[o for o in bpy.data.objects if o.type=="ARMATURE" and "UpperArm_L" in o.data.bones]
if not targets:
    raise RuntimeError("no armature with UpperArm_L found")
for arm_obj in targets:
    print(f"ARMATURE: {arm_obj.name}")
    inv = arm_obj.matrix_world.inverted()
    bpy.context.view_layer.objects.active = arm_obj
    arm_obj.hide_set(False); arm_obj.hide_viewport=False
    bpy.ops.object.mode_set(mode="EDIT")
    eb = arm_obj.data.edit_bones

    def set_bone(name, head_w, tail_w):
        b = eb.get(name)
        if b is None:
            print(f"  WARN bone missing: {name}"); return
        b.use_connect = False
        b.head = inv @ head_w
        b.tail = inv @ tail_w
        print(f"  BONE {name}: head={[round((head_w)[i],3) for i in range(3)]} tail={[round((tail_w)[i],3) for i in range(3)]}")

    set_bone("UpperArm_L", shoulder_L, elbow_L)
    set_bone("LowerArm_L", elbow_L, wrist_L)
    set_bone("Hand_L", wrist_L, hand_tail_L)
    set_bone("UpperArm_R", shoulder_R, elbow_R)
    set_bone("LowerArm_R", elbow_R, wrist_R)
    set_bone("Hand_R", wrist_R, hand_tail_R)
    bpy.ops.object.mode_set(mode="OBJECT")
bpy.context.view_layer.update()

# --- 2) restore arm mesh world matrices from ORIGINAL (after bone edit) ---
moved=0
for name in ARM_MESHES:
    o=bpy.data.objects.get(name)
    if o is None:
        print(f"  WARN mesh missing: {name}"); continue
    if name not in ORIG:
        print(f"  WARN not in orig dump: {name}"); continue
    o.matrix_world = Matrix(ORIG[name]["matrix_world"])
    moved+=1
print(f"MESHES_RESTORED={moved}")

# --- 3) markers + shared cores to new pivots ---
MARKER_MAP={
    "V50_RIG_MARKER_shoulder_L":"shoulder_L","V50_RIG_MARKER_elbow_L":"elbow_L","V50_RIG_MARKER_wrist_L":"wrist_L",
    "V50_RIG_MARKER_shoulder_R":"shoulder_R","V50_RIG_MARKER_elbow_R":"elbow_R","V50_RIG_MARKER_wrist_R":"wrist_R",
}
CORE_MAP={
    "L_ELBOW_SHARED_CORE":"elbow_L","R_ELBOW_SHARED_CORE":"elbow_R",
    "L_WRIST_SHARED_CORE":"wrist_L","R_WRIST_SHARED_CORE":"wrist_R",
}
for nm,key in {**MARKER_MAP,**CORE_MAP}.items():
    o=bpy.data.objects.get(nm)
    if o is None:
        print(f"  WARN marker missing: {nm}"); continue
    p=PIVOTS[key]
    if o.parent:
        o.matrix_world = Matrix.Translation(p) @ o.matrix_world.to_3x3().to_4x4()
    else:
        o.location = p
print("MARKERS_UPDATED")

# proxy left hand pieces: keep hidden but park them at wrist_L so they are not stray
for nm in ["V50_PROXY_Hand_L_Palm","V50_PROXY_Hand_L_Palm_Core",
           "V50_PROXY_Hand_L_Finger_A","V50_PROXY_Hand_L_Finger_B","V50_PROXY_Hand_L_Finger_C"]:
    o=bpy.data.objects.get(nm)
    if o is not None:
        cur=o.matrix_world.translation
        o.matrix_world = Matrix.Translation(Vector(wrist_L) - cur) @ o.matrix_world

bpy.ops.wm.save_as_mainfile(filepath=OUT)
print("SAVED", OUT)
