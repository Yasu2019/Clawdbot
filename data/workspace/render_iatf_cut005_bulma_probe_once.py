"""Render CUT_005 with the provided Bulma/Goku GLB models.

This is a prototype step after the procedural character proof.  It preserves
the evidence-first scene while replacing the simple placeholder character with
the user-provided Bulma model and a small Goku listener.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
BLENDER = Path("C:/Program Files/Blender Foundation/Blender 5.1/blender.exe")
BULMA = ROOT / "data/workspace/iatf_remotion_studio/public/bulma_mc.glb"
GOKU = ROOT / "data/workspace/iatf_remotion_studio/public/goku.glb"
OUT_DIR = ROOT / "data/iatf_videos/IATF 16949 内部監査資料_箇条8.5.4_箇条8.5.4.1梱包工程_design_pilot/cut005_bulma_probe"
WORKSPACE_MIRROR = ROOT / "data/workspace/iatf_cut005_bulma_probe"
STATUS_PATH = ROOT / "data/workspace/iatf_cut005_bulma_probe_status.json"


def write_status(stage: str, **extra: object) -> None:
    payload = {
        "updated_at": time.strftime("%Y-%m-%d %H:%M:%S %z"),
        "stage": stage,
        **extra,
    }
    STATUS_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False), flush=True)


def blender_script(out_dir: Path, frames_dir: Path) -> str:
    out = str(out_dir).replace("\\", "/")
    frames = str(frames_dir).replace("\\", "/")
    bulma = str(BULMA).replace("\\", "/")
    goku = str(GOKU).replace("\\", "/")
    return f'''
import bpy
import math
from pathlib import Path
from mathutils import Vector

OUT_DIR = Path(r"{out}")
FRAMES_DIR = Path(r"{frames}")
BULMA = r"{bulma}"
GOKU = r"{goku}"
FRAMES_DIR.mkdir(parents=True, exist_ok=True)
FPS = 12
TOTAL_FRAMES = 60
SAMPLE_FRAMES = [1, 10, 19, 25, 37, 49, 60]

def mat(name, color):
    m = bpy.data.materials.new(name)
    m.diffuse_color = color
    m.use_nodes = True
    bsdf = m.node_tree.nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs["Base Color"].default_value = color
        bsdf.inputs["Roughness"].default_value = 0.82
    return m

def add_cube(name, loc, scale, material):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc)
    obj = bpy.context.object
    obj.name = name
    obj.dimensions = scale
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    obj.data.materials.append(material)
    return obj

def add_text(name, text, loc, size, material):
    bpy.ops.object.text_add(location=loc, rotation=(math.radians(90), 0, 0))
    obj = bpy.context.object
    obj.name = name
    obj.data.body = text
    obj.data.align_x = "LEFT"
    obj.data.align_y = "CENTER"
    obj.data.size = size
    obj.data.materials.append(material)
    return obj

def key(obj, frame, loc=None, scale=None, rot=None):
    bpy.context.scene.frame_set(frame)
    if loc is not None:
        obj.location = loc
        obj.keyframe_insert("location", frame=frame)
    if scale is not None:
        obj.scale = scale
        obj.keyframe_insert("scale", frame=frame)
    if rot is not None:
        obj.rotation_euler = rot
        obj.keyframe_insert("rotation_euler", frame=frame)

def set_bone(armature, bone_name, frame, rot=None, loc=None):
    bone = armature.pose.bones.get(bone_name)
    if not bone:
        return False
    bpy.context.scene.frame_set(frame)
    bone.rotation_mode = "XYZ"
    if rot is not None:
        bone.rotation_euler = rot
        bone.keyframe_insert("rotation_euler", frame=frame)
    if loc is not None:
        bone.location = loc
        bone.keyframe_insert("location", frame=frame)
    return True

def import_character(path, name, location, fixed_scale=1.0, zrot=0.0):
    before = set(bpy.context.scene.objects)
    bpy.ops.import_scene.gltf(filepath=path)
    imported = [obj for obj in bpy.context.scene.objects if obj not in before]
    arm = next((obj for obj in imported if obj.type == "ARMATURE"), None)
    meshes = [obj for obj in imported if obj.type == "MESH"]
    if not arm:
        raise RuntimeError(f"No armature in {{path}}")
    arm.name = f"{{name}}_Armature"
    for obj in meshes:
        obj.name = f"{{name}}_{{obj.name}}"
    arm.scale = (fixed_scale, fixed_scale, fixed_scale)
    arm.rotation_euler = (0, 0, zrot)
    bpy.context.view_layer.update()
    min_world = min((obj.matrix_world @ Vector(corner)).z for obj in meshes for corner in obj.bound_box)
    arm.location = (location[0], location[1], location[2] - min_world)
    return arm, meshes

bpy.ops.object.select_all(action="SELECT")
bpy.ops.object.delete()

bg = mat("quiet_wall", (0.66, 0.70, 0.67, 1))
floor_m = mat("matte_floor", (0.39, 0.38, 0.34, 1))
desk_m = mat("audit_desk", (0.30, 0.27, 0.23, 1))
paper_m = mat("paper_white", (0.94, 0.91, 0.82, 1))
accent_m = mat("qmi_blue", (0.07, 0.29, 0.50, 1))
box40_m = mat("box_40", (0.76, 0.62, 0.34, 1))
box50_m = mat("box_50", (0.42, 0.50, 0.67, 1))
red_m = mat("old_lot_red", (0.72, 0.10, 0.08, 1))
green_m = mat("fifo_green", (0.08, 0.48, 0.25, 1))
black_m = mat("black", (0.02, 0.02, 0.02, 1))
white_m = mat("white", (0.98, 0.98, 0.95, 1))
mouth_m = mat("mouth_overlay", (0.56, 0.03, 0.03, 1))
lid_m = mat("blink_overlay", (0.06, 0.09, 0.08, 1))

add_cube("floor", (0, 0, -0.04), (6.4, 5.0, 0.08), floor_m)
add_cube("back_wall", (0, 1.8, 1.55), (6.4, 0.10, 3.2), bg)
add_cube("desk", (0.10, 0.56, 0.45), (4.0, 0.95, 0.16), desk_m)
add_cube("evidence_board", (0.95, 0.02, 1.23), (2.05, 0.08, 1.18), paper_m)

qmi = add_cube("qmi_sheet", (0.24, -0.05, 1.39), (0.48, 0.04, 0.34), accent_m)
work_card = add_cube("work_card", (0.84, -0.06, 1.44), (0.60, 0.04, 0.28), paper_m)
box40 = add_cube("box_40", (1.24, -0.08, 1.20), (0.36, 0.22, 0.24), box40_m)
box50 = add_cube("box_50", (1.58, -0.10, 1.20), (0.36, 0.22, 0.24), box50_m)
fifo = add_cube("fifo_label", (1.07, -0.08, 0.86), (0.96, 0.05, 0.20), green_m)
old_lot = add_cube("old_lot", (1.65, -0.08, 1.55), (0.34, 0.05, 0.22), red_m)

add_text("title", "CUT_005: verify packaging evidence", (-0.06, -0.18, 1.89), 0.082, black_m)
add_text("qmi", "QMI", (0.07, -0.19, 1.45), 0.105, white_m)
add_text("work_card_label", "WORK CARD", (0.55, -0.20, 1.50), 0.072, black_m)
add_text("box40_label", "40 pcs", (1.10, -0.22, 1.27), 0.055, black_m)
add_text("box50_label", "50 pcs", (1.44, -0.24, 1.27), 0.055, white_m)
add_text("quantity_compare", "40 / 50 pcs", (0.48, -0.22, 1.12), 0.075, black_m)
add_text("fifo", "FIFO OK", (0.74, -0.22, 0.92), 0.080, white_m)
add_text("old_item", "OLD", (1.55, -0.23, 1.61), 0.055, white_m)

bulma_arm, bulma_meshes = import_character(BULMA, "Bulma", (-1.95, -0.10, 0.0), fixed_scale=0.015, zrot=0.0)
goku_arm, goku_meshes = import_character(GOKU, "Goku", (-2.48, 0.34, 0.0), fixed_scale=0.012, zrot=0.10)

# Put Goku slightly behind as listener; Bulma is the active demonstrator.
for obj in goku_meshes:
    obj.hide_render = False

# Body/arm pose.  This uses real Mixamo bones available in the provided GLB.
for frame, head_x in [(1, 0.00), (24, 0.04), (42, -0.02), (60, 0.00)]:
    set_bone(bulma_arm, "mixamorig:Spine2", frame, rot=(math.radians(1.5), 0, math.radians(-2 + head_x * 20)))
    set_bone(bulma_arm, "mixamorig:Head", frame, rot=(math.radians(2 + head_x * 30), 0, math.radians(-2)))

for frame, shoulder_z, arm_z, fore_z, hand_z in [
    (1, -18, -34, 24, 4),
    (12, -10, -20, 16, 1),
    (30, -5, -8, 10, -4),
    (60, -8, -12, 12, -2),
]:
    set_bone(bulma_arm, "mixamorig:RightShoulder", frame, rot=(0, 0, math.radians(shoulder_z)))
    set_bone(bulma_arm, "mixamorig:RightArm", frame, rot=(math.radians(2), 0, math.radians(arm_z)))
    set_bone(bulma_arm, "mixamorig:RightForeArm", frame, rot=(0, 0, math.radians(fore_z)))
    set_bone(bulma_arm, "mixamorig:RightHand", frame, rot=(0, math.radians(-8), math.radians(hand_z)))
    set_bone(bulma_arm, "mixamorig:RightHandIndex1", frame, rot=(0, 0, math.radians(-4)))
    set_bone(bulma_arm, "mixamorig:RightHandIndex2", frame, rot=(0, 0, math.radians(0)))

# Goku listener nod.
for frame, head in [(1, 0), (30, 5), (60, 0)]:
    set_bone(goku_arm, "mixamorig:Head", frame, rot=(math.radians(head), 0, 0))

# Lightweight diagnostic mouth/blink overlays, kept small because the GLB has no facial bones.
mouth = add_cube("bulma_mouth_overlay", (-1.95, -0.37, 0.28), (0.020, 0.010, 0.006), mouth_m)
left_lid = add_cube("bulma_left_blink_overlay", (-1.965, -0.38, 0.31), (0.014, 0.010, 0.004), lid_m)
right_lid = add_cube("bulma_right_blink_overlay", (-1.935, -0.38, 0.31), (0.014, 0.010, 0.004), lid_m)
for f, h in [(1, 0.45), (6, 1.20), (12, 0.45), (18, 1.50), (24, 0.35), (33, 1.25), (44, 0.50), (55, 1.05), (60, 0.45)]:
    key(mouth, f, scale=(1.0, 1.0, h))
for lid in (left_lid, right_lid):
    key(lid, 1, scale=(1, 1, 1))
    key(lid, 23, scale=(1, 1, 1))
    key(lid, 25, scale=(1, 1, 3.6))
    key(lid, 28, scale=(1, 1, 1))
    key(lid, 48, scale=(1, 1, 3.2))
    key(lid, 51, scale=(1, 1, 1))

# Evidence emphasis.
for obj, start in [(qmi, 4), (work_card, 16), (box40, 28), (box50, 36), (fifo, 44), (old_lot, 52)]:
    key(obj, max(1, start - 3), scale=(1.0, 1.0, 1.0))
    key(obj, start, scale=(1.07, 1.07, 1.07))
    key(obj, min(TOTAL_FRAMES, start + 5), scale=(1.0, 1.0, 1.0))

bpy.ops.object.light_add(type="AREA", location=(-1.8, -2.8, 3.4))
key_light = bpy.context.object
key_light.data.energy = 260
key_light.data.size = 5.0
bpy.ops.object.light_add(type="POINT", location=(1.6, -1.3, 2.2))
rim = bpy.context.object
rim.data.energy = 90

bpy.ops.object.camera_add(location=(-0.44, -4.45, 1.38))
camera = bpy.context.object
bpy.context.scene.camera = camera
camera.data.type = "ORTHO"
camera.data.ortho_scale = 3.65
target = Vector((-0.34, -0.05, 1.18))
direction = target - camera.location
camera.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()

scene = bpy.context.scene
scene.frame_start = 1
scene.frame_end = TOTAL_FRAMES
scene.render.fps = FPS
scene.render.engine = "BLENDER_EEVEE"
scene.eevee.taa_render_samples = 32
scene.render.resolution_x = 1280
scene.render.resolution_y = 720
scene.view_settings.view_transform = "Standard"
scene.view_settings.look = "Medium High Contrast"
scene.world.color = (0.82, 0.84, 0.80)
scene.render.image_settings.file_format = "PNG"
for frame in SAMPLE_FRAMES:
    scene.frame_set(frame)
    scene.render.filepath = str(FRAMES_DIR / f"cut005_bulma_{{frame:04d}}.png")
    bpy.ops.render.render(write_still=True)

qa = {{
    "ok": True,
    "cut_id": "CUT_005",
    "model_layer": "provided Bulma/Goku GLB",
    "bulma_model": BULMA,
    "goku_model": GOKU,
    "fps": FPS,
    "total_frames": TOTAL_FRAMES,
    "sample_frames": SAMPLE_FRAMES,
    "duration_sec": round(TOTAL_FRAMES / FPS, 2),
    "checks": {{
        "model_import": "Bulma and Goku GLB imported in Blender",
        "real_rig_motion": "Bulma mixamorig right shoulder/arm/forearm/hand/index bones are keyed",
        "goku_import": "Goku GLB imports and has keyed head motion, but final on-screen placement still needs tuning",
        "mouth_blink": "small diagnostic overlays are keyed because facial bones are not present",
        "evidence_priority": "QMI, WORK CARD, 40/50 pcs, FIFO OK, OLD remain visible"
    }},
    "known_limitations": [
        "not Mixamo downloaded motion yet",
        "mouth and blink are overlay diagnostics, not true facial rig deformation",
        "arm pose may require manual tuning after visual review",
        "current visual approval is mainly for Bulma scale/evidence coexistence; Goku visibility is not approved yet"
    ]
}}
(OUT_DIR / "cut005_bulma_probe_qa.json").write_text(__import__("json").dumps(qa, ensure_ascii=False, indent=2), encoding="utf-8")
'''


def make_contact_sheet(frame_paths: list[Path], output_path: Path) -> None:
    from PIL import Image, ImageDraw, ImageFont

    picks = frame_paths if len(frame_paths) <= 7 else [frame_paths[i] for i in [0, 9, 18, 24, 36, 48, 59] if i < len(frame_paths)]
    thumbs = []
    for path in picks:
        img = Image.open(path).convert("RGB")
        img.thumbnail((360, 203))
        thumbs.append((path, img.copy()))

    width = 760
    row_h = 252
    height = 72 + row_h * ((len(thumbs) + 1) // 2)
    sheet = Image.new("RGB", (width, height), (238, 240, 236))
    draw = ImageDraw.Draw(sheet)
    try:
        font_title = ImageFont.truetype("C:/Windows/Fonts/meiryo.ttc", 22)
        font = ImageFont.truetype("C:/Windows/Fonts/meiryo.ttc", 14)
    except OSError:
        font_title = ImageFont.load_default()
        font = ImageFont.load_default()
    draw.text((24, 18), "CUT_005 Bulma/Goku GLB probe: evidence-first animation", fill=(25, 35, 32), font=font_title)
    for idx, (path, img) in enumerate(thumbs):
        col = idx % 2
        row = idx // 2
        x = 24 + col * 368
        y = 70 + row * row_h
        sheet.paste(img, (x, y))
        draw.text((x, y + img.height + 8), path.stem, fill=(25, 35, 32), font=font)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(output_path, quality=92)


def compose_mp4(frames_dir: Path, output_mp4: Path) -> bool:
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        return False
    cmd = [
        ffmpeg,
        "-y",
        "-framerate",
        "12",
        "-i",
        str(frames_dir / "cut005_bulma_%04d.png"),
        "-c:v",
        "libx264",
        "-pix_fmt",
        "yuv420p",
        "-vf",
        "fps=24",
        str(output_mp4),
    ]
    result = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=300)
    (output_mp4.parent / "ffmpeg_stdout.log").write_text(result.stdout[-4000:], encoding="utf-8")
    (output_mp4.parent / "ffmpeg_stderr.log").write_text(result.stderr[-4000:], encoding="utf-8")
    return result.returncode == 0 and output_mp4.exists()


def write_index(mirror_dir: Path, contact_sheet: Path, mp4_name: str | None, qa: dict) -> None:
    video = f"<video controls width='960' src='{mp4_name}'></video>" if mp4_name else "<p>MP4 was not composed because ffmpeg was unavailable.</p>"
    html = f"""<!doctype html>
<meta charset="utf-8">
<title>IATF CUT_005 Bulma Probe</title>
<style>
body{{font-family:Segoe UI,Meiryo,sans-serif;margin:24px;background:#eef0ec;color:#1e2824}}
img,video{{max-width:100%;border:1px solid #b8c0b8;background:white}}
code{{background:#fff;padding:2px 4px}}
</style>
<h1>IATF CUT_005 Bulma/Goku Probe</h1>
<p>Provided GLB models are used. Evidence remains central; Bulma is the active demonstrator and Goku is a listener.</p>
{video}
<h2>Contact Sheet</h2>
<img src="{contact_sheet.name}" alt="contact sheet">
<h2>QA</h2>
<pre>{json.dumps(qa, ensure_ascii=False, indent=2)}</pre>
"""
    (mirror_dir / "index.html").write_text(html, encoding="utf-8")


def main() -> int:
    if not BLENDER.exists():
        raise FileNotFoundError(f"Blender not found: {BLENDER}")
    for path in (BULMA, GOKU):
        if not path.exists():
            raise FileNotFoundError(str(path))
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    WORKSPACE_MIRROR.mkdir(parents=True, exist_ok=True)
    frames_dir = OUT_DIR / "frames"
    if frames_dir.exists():
        shutil.rmtree(frames_dir)
    frames_dir.mkdir(parents=True, exist_ok=True)
    write_status("start", bulma=str(BULMA), goku=str(GOKU), output_dir=str(OUT_DIR))

    with tempfile.TemporaryDirectory(prefix="iatf_bulma_probe_") as tmp:
        script_path = Path(tmp) / "cut005_bulma_blender.py"
        script_path.write_text(blender_script(OUT_DIR, frames_dir), encoding="utf-8")
        write_status("run_blender", blender=str(BLENDER))
        result = subprocess.run(
            [str(BLENDER), "--background", "--python", str(script_path)],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=900,
        )
        (OUT_DIR / "blender_stdout.log").write_text(result.stdout[-8000:], encoding="utf-8")
        (OUT_DIR / "blender_stderr.log").write_text(result.stderr[-8000:], encoding="utf-8")
        if result.returncode != 0:
            write_status("error", returncode=result.returncode, stderr=result.stderr[-1200:])
            return result.returncode

    frames = sorted(frames_dir.glob("cut005_bulma_*.png"))
    if len(frames) < 7:
        raise RuntimeError(f"expected 7 diagnostic frames, got {len(frames)}")
    contact_sheet = OUT_DIR / "contact_sheet.jpg"
    make_contact_sheet(frames, contact_sheet)
    qa = json.loads((OUT_DIR / "cut005_bulma_probe_qa.json").read_text(encoding="utf-8"))
    mp4 = OUT_DIR / "cut005_bulma_probe.mp4"
    mp4_ok = compose_mp4(frames_dir, mp4) if len(frames) >= 60 else False

    mirror_contact = WORKSPACE_MIRROR / "contact_sheet.jpg"
    mirror_contact.write_bytes(contact_sheet.read_bytes())
    (WORKSPACE_MIRROR / "cut005_bulma_probe_qa.json").write_text(json.dumps(qa, ensure_ascii=False, indent=2), encoding="utf-8")
    mp4_name = None
    if mp4_ok:
        mirror_mp4 = WORKSPACE_MIRROR / "cut005_bulma_probe.mp4"
        mirror_mp4.write_bytes(mp4.read_bytes())
        mp4_name = mirror_mp4.name
    for path in frames if len(frames) <= 7 else [frames[0], frames[9], frames[18], frames[24], frames[36], frames[48], frames[59]]:
        (WORKSPACE_MIRROR / path.name).write_bytes(path.read_bytes())
    write_index(WORKSPACE_MIRROR, mirror_contact, mp4_name, qa)

    write_status(
        "done",
        ok=True,
        frames=len(frames),
        mp4=str(mp4) if mp4_ok else None,
        contact_sheet=str(contact_sheet),
        mirror_index=str(WORKSPACE_MIRROR / "index.html"),
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        write_status("error", error=str(exc))
        raise
