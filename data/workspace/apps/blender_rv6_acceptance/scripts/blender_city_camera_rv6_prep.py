# -*- coding: utf-8 -*-
import sys
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

"""Blender script: 街路レベルカメラ、夕方/夜景向け基本ライティング、RV6向け出力設定。"""
import bpy, math, json
from mathutils import Vector
from pathlib import Path
OUTPUT_DIR = Path("renders"); OUTPUT_DIR.mkdir(exist_ok=True)
RV6_STRENGTH = 0.65; CAMERA_HEIGHT_M = 1.45; LENS_MM = 28

def ensure_camera():
    cam = bpy.data.objects.get("Street_Level_Camera")
    if cam is None:
        data = bpy.data.cameras.new("Street_Level_Camera")
        cam = bpy.data.objects.new("Street_Level_Camera", data)
        bpy.context.collection.objects.link(cam)
    bpy.context.scene.camera = cam
    return cam

def setup_camera(cam):
    cam.location = (0, -8, CAMERA_HEIGHT_M)
    direction = Vector((0, 0, 1.2)) - cam.location
    cam.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()
    cam.data.lens = LENS_MM
    cam.data.dof.use_dof = True
    cam.data.dof.focus_distance = 8
    cam.data.dof.aperture_fstop = 5.6

def setup_lighting():
    sun = bpy.data.objects.get("Evening_Key_Light")
    if sun is None:
        light_data = bpy.data.lights.new("Evening_Key_Light", type="SUN")
        sun = bpy.data.objects.new("Evening_Key_Light", light_data)
        bpy.context.collection.objects.link(sun)
    sun.rotation_euler = (math.radians(55), 0, math.radians(35))
    sun.data.energy = 1.2
    bpy.context.scene.world.color = (0.03, 0.035, 0.05)

def setup_render():
    scene = bpy.context.scene
    scene.frame_start = 1; scene.frame_end = 120
    scene.render.engine = "CYCLES"
    scene.cycles.samples = 96
    scene.render.resolution_x = 1920; scene.render.resolution_y = 1080; scene.render.fps = 24
    scene.render.filepath = str(OUTPUT_DIR / "frame_")
    scene.view_settings.view_transform = "Filmic"
    scene.view_settings.look = "Medium High Contrast"
    scene.view_settings.exposure = -0.1

def main():
    cam = ensure_camera(); setup_camera(cam); setup_lighting(); setup_render()
    (OUTPUT_DIR / "rv6_hint.json").write_text(json.dumps({"rv6_strength": RV6_STRENGTH, "camera": "street_level", "ue5": "not_used"}, ensure_ascii=False, indent=2), encoding="utf-8")
    print("Blender+RV6 prep complete. UE5 route is intentionally not used.")
if __name__ == "__main__": main()
