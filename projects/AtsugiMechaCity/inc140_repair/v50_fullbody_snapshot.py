# -*- coding: utf-8 -*-
"""Read-only full-body snapshot of the welded V50 build (front + side), framing the
WHOLE height. Does not modify pipeline scripts. Hides diagnostics like the preview."""
import sys
if hasattr(sys.stdout, "reconfigure"):
    try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception: pass
import bpy, mathutils
from mathutils import Vector

argv = sys.argv[sys.argv.index("--")+1:] if "--" in sys.argv else []
INP = argv[argv.index("--input")+1]
OUTDIR = argv[argv.index("--outdir")+1]

bpy.ops.wm.open_mainfile(filepath=INP)

HIDE_PREFIX = ("V50_RIG_MARKER_", "V50_PROXY_Hand_L_", "V50_PREVIEW_LOCK_")
HIDE_EXACT = {"Ground","Robot_Mechanical_Armature","V50_Generic_Armature",
              "L_ELBOW_SHARED_CORE","R_ELBOW_SHARED_CORE","L_WRIST_SHARED_CORE","R_WRIST_SHARED_CORE"}

visible = []
for o in bpy.data.objects:
    if o.type != "MESH":
        o.hide_render = True; continue
    if o.name in HIDE_EXACT or o.name.startswith(HIDE_PREFIX):
        o.hide_render = True; continue
    o.hide_render = False
    visible.append(o)

lo = Vector((1e18,)*3); hi = Vector((-1e18,)*3)
for o in visible:
    for c in o.bound_box:
        w = o.matrix_world @ Vector(c)
        for i in range(3):
            lo[i]=min(lo[i],w[i]); hi[i]=max(hi[i],w[i])
center=(lo+hi)*0.5; size=hi-lo
print(f"VISIBLE_MESHES={len(visible)} height_z={size.z:.3f} width_x={size.x:.3f} depth_y={size.y:.3f}")
print(f"center={[round(center[i],3) for i in range(3)]}")

scene=bpy.context.scene
scene.render.engine="BLENDER_WORKBENCH"
scene.display.shading.light="STUDIO"
scene.render.resolution_x=720; scene.render.resolution_y=960  # portrait to fit tall robot
scene.render.image_settings.file_format="PNG"

cam_data=bpy.data.cameras.new("SNAP_CAM"); cam=bpy.data.objects.new("SNAP_CAM",cam_data)
scene.collection.objects.link(cam); cam.data.type="ORTHO"
cam.data.sensor_fit="VERTICAL"
cam.data.ortho_scale=float(size.z)*1.15
scene.camera=cam
dist=max(float(size.y),float(size.x),float(size.z))*3.0+5.0

def shoot(name, offset, up="Z"):
    cam.location=center+offset
    d=center-cam.location
    cam.rotation_euler=d.to_track_quat("-Z","Y").to_euler()
    scene.render.filepath=str(OUTDIR.rstrip("/")+"/"+name)
    bpy.ops.render.render(write_still=True)
    print("SHOT",name)

shoot("fullbody_front.png", Vector((0.0,-dist,0.0)))
shoot("fullbody_side.png",  Vector((dist,0.0,0.0)))
print("DONE")
