# -*- coding: utf-8 -*-
"""
qc_multiview.py — QC sampling renderer for the Zaku walk.

Renders FRONT / SIDE / BACK views at sampled frames so joint gaps (shoulder
detachment, thigh/hip split, knee) can be visually inspected from every angle.
Per QC protocol: sample every N frames (default 5) — NOT just one hero frame.

Run (default: every 5 frames, low-res fast):
  & "C:\\Program Files\\Blender Foundation\\Blender 5.1\\blender.exe" --background `
    --python projects\\AtsugiMechaCity\\scenes\\qc_multiview.py -- --every 5

Specific frames:
  ... -- --frames 1,10,19,28

Output: output/zaku_walk_origin/qc/qc_f<NNNN>_<view>.png  (+ qc_contact_f<NNNN>.png)
"""
import bpy
import sys
import math
from pathlib import Path

_args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []


def _arg(flag, default=None):
    if flag in _args:
        i = _args.index(flag)
        if i + 1 < len(_args):
            return _args[i + 1]
    return default


SCENE_SCRIPT = Path("D:/Clawdbot_Docker_20260125/projects/AtsugiMechaCity/scenes/zaku_walk_origin_style.py")
OUT_DIR = Path("D:/Clawdbot_Docker_20260125/projects/AtsugiMechaCity/output/zaku_walk_origin/qc")
QC_W, QC_H = 640, 900
QC_SAMPLES = 20

# Build the animated scene by running the deliverable script up to the VERIFY block.
_src = SCENE_SCRIPT.read_text(encoding="utf-8").split("# ===== VERIFY MODE")[0]
exec(_src)  # noqa: provides `armature`, `scene`, etc.

scene = bpy.context.scene
OUT_DIR.mkdir(parents=True, exist_ok=True)

# Which frames to sample
if _arg("--frames"):
    frames = [int(x) for x in _arg("--frames").split(",")]
else:
    every = int(_arg("--every", "5"))
    frames = list(range(1, scene.frame_end + 1, every))

print(f"[QC] sampling frames: {frames}", flush=True)

# Mecha walks toward -Y (it faces -Y). Define 3 orbit cameras around the body.
# distance/height tuned to frame the full ~18m mecha.
DIST = 46.0
HEIGHT = 9.0
VIEWS = {
    "front": (0.0, -DIST),   # in front of the mecha, looking +Y at its face
    "side":  (DIST, 0.0),    # camera on +X, looking -X
    "back":  (0.0, DIST),    # behind, looking -Y
}

# Remove deliverable cameras, set up our own orbit camera (re-pointed per view).
for o in list(scene.objects):
    if o.type == "CAMERA":
        bpy.data.objects.remove(o, do_unlink=True)
cam_d = bpy.data.cameras.new("QCCam")
cam = bpy.data.objects.new("QCCam", cam_d)
scene.collection.objects.link(cam)
scene.camera = cam
cam_d.lens = 50
cam_d.clip_end = 600
trk = cam.constraints.new(type="TRACK_TO")
trk.target = armature
trk.subtarget = "Chest"
trk.track_axis = "TRACK_NEGATIVE_Z"
trk.up_axis = "UP_Y"

scene.render.engine = "CYCLES"
scene.cycles.device = "CPU"
scene.cycles.samples = QC_SAMPLES
scene.render.resolution_x = QC_W
scene.render.resolution_y = QC_H
scene.render.resolution_percentage = 100
scene.render.film_transparent = False

for fr in frames:
    scene.frame_set(fr)
    ay = armature.location.y  # body has moved in -Y; follow it
    for view, (dx, dy) in VIEWS.items():
        cam.location = (dx, ay + dy, HEIGHT)
        scene.render.filepath = str(OUT_DIR / f"qc_f{fr:04d}_{view}.png")
        bpy.ops.render.render(write_still=True)
    print(f"[QC] frame {fr}: front/side/back rendered", flush=True)

print("[QC] DONE", flush=True)
