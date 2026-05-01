"""Render a short CUT_005 IATF Blender motion segment.

This is the first real animation step after the character-motion probe.  It is
kept isolated from the production pipeline and renders a short evidence-first
preview video for visual approval before full first-half generation.
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
OUT_DIR = ROOT / "data/iatf_videos/IATF 16949 内部監査資料_箇条8.5.4_箇条8.5.4.1梱包工程_design_pilot/cut005_motion_segment"
WORKSPACE_MIRROR = ROOT / "data/workspace/iatf_cut005_motion_segment"
STATUS_PATH = ROOT / "data/workspace/iatf_cut005_motion_segment_status.json"


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
    return f'''
import bpy
import math
from pathlib import Path
from mathutils import Vector

OUT_DIR = Path(r"{out}")
FRAMES_DIR = Path(r"{frames}")
FRAMES_DIR.mkdir(parents=True, exist_ok=True)
FPS = 12
TOTAL_FRAMES = 60

def mat(name, color):
    m = bpy.data.materials.new(name)
    m.diffuse_color = color
    m.use_nodes = True
    bsdf = m.node_tree.nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs["Base Color"].default_value = color
        bsdf.inputs["Roughness"].default_value = 0.84
    return m

def add_cube(name, loc, scale, material):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc)
    obj = bpy.context.object
    obj.name = name
    obj.dimensions = scale
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    obj.data.materials.append(material)
    return obj

def add_uv(name, loc, scale, material):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=32, ring_count=16, location=loc)
    obj = bpy.context.object
    obj.name = name
    obj.scale = scale
    obj.data.materials.append(material)
    return obj

def add_text(name, text, loc, size, material, align="LEFT"):
    bpy.ops.object.text_add(location=loc, rotation=(math.radians(90), 0, 0))
    obj = bpy.context.object
    obj.name = name
    obj.data.body = text
    obj.data.align_x = align
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
skin_m = mat("skin", (0.88, 0.66, 0.50, 1))
suit_m = mat("work_jacket", (0.08, 0.35, 0.42, 1))
black_m = mat("black", (0.02, 0.02, 0.02, 1))
mouth_m = mat("mouth", (0.52, 0.03, 0.03, 1))
white_m = mat("white", (0.98, 0.98, 0.95, 1))
caption_m = mat("caption", (0.05, 0.08, 0.08, 1))

add_cube("floor", (0, 0, -0.04), (6.3, 5.0, 0.08), floor_m)
add_cube("back_wall", (0, 1.8, 1.55), (6.3, 0.10, 3.2), bg)
add_cube("desk", (0.05, 0.56, 0.45), (3.9, 0.95, 0.16), desk_m)
add_cube("evidence_board", (0.92, 0.02, 1.23), (2.05, 0.08, 1.18), paper_m)

qmi = add_cube("qmi_sheet", (0.21, -0.05, 1.39), (0.48, 0.04, 0.34), accent_m)
work_card = add_cube("work_card", (0.82, -0.06, 1.44), (0.60, 0.04, 0.28), paper_m)
box40 = add_cube("box_40", (1.22, -0.08, 1.20), (0.36, 0.22, 0.24), box40_m)
box50 = add_cube("box_50", (1.56, -0.10, 1.20), (0.36, 0.22, 0.24), box50_m)
fifo = add_cube("fifo_label", (1.05, -0.08, 0.86), (0.96, 0.05, 0.20), green_m)
old_lot = add_cube("old_lot", (1.63, -0.08, 1.55), (0.34, 0.05, 0.22), red_m)

add_text("title", "CUT_005: verify packaging evidence", (-0.08, -0.18, 1.89), 0.085, black_m)
add_text("qmi", "QMI", (0.04, -0.19, 1.45), 0.105, white_m)
add_text("work_card_label", "WORK CARD", (0.53, -0.20, 1.50), 0.072, black_m)
add_text("box40_label", "40 pcs", (1.08, -0.22, 1.27), 0.055, black_m)
add_text("box50_label", "50 pcs", (1.42, -0.24, 1.27), 0.055, white_m)
add_text("quantity_compare", "40 / 50 pcs", (0.46, -0.22, 1.12), 0.075, black_m)
add_text("fifo", "FIFO OK", (0.72, -0.22, 0.92), 0.080, white_m)
add_text("old_item", "OLD", (1.53, -0.23, 1.61), 0.055, white_m)
add_text("caption", "作業カード・QMI・40/50個表示・FIFOラベルを順に確認", (-2.30, -0.19, 0.57), 0.058, caption_m)

body = add_cube("auditor_body", (-1.55, 0.10, 0.92), (0.50, 0.24, 0.84), suit_m)
head = add_uv("auditor_head", (-1.55, -0.05, 1.57), (0.32, 0.28, 0.32), skin_m)
neck = add_cube("neck", (-1.55, 0.03, 1.27), (0.16, 0.13, 0.18), skin_m)
add_uv("left_eye", (-1.68, -0.27, 1.64), (0.060, 0.020, 0.036), white_m)
add_uv("right_eye", (-1.43, -0.27, 1.64), (0.060, 0.020, 0.036), white_m)
add_uv("left_pupil", (-1.68, -0.30, 1.64), (0.023, 0.009, 0.022), black_m)
add_uv("right_pupil", (-1.43, -0.30, 1.64), (0.023, 0.009, 0.022), black_m)
left_lid = add_cube("left_eyelid", (-1.68, -0.315, 1.675), (0.14, 0.014, 0.020), skin_m)
right_lid = add_cube("right_eyelid", (-1.43, -0.315, 1.675), (0.14, 0.014, 0.020), skin_m)
left_brow = add_cube("left_brow", (-1.68, -0.320, 1.78), (0.16, 0.014, 0.020), black_m)
right_brow = add_cube("right_brow", (-1.43, -0.320, 1.78), (0.16, 0.014, 0.020), black_m)
mouth = add_cube("mouth_opening", (-1.55, -0.325, 1.48), (0.19, 0.014, 0.045), mouth_m)
arm = add_cube("pointing_arm", (-1.12, -0.03, 1.02), (0.90, 0.12, 0.13), skin_m)
finger = add_cube("pointing_finger", (-0.62, -0.11, 1.07), (0.28, 0.065, 0.065), skin_m)

# Character motion: talk, blink, expression, and point toward evidence in sequence.
for f, h in [(1, 0.35), (5, 1.25), (10, 0.45), (15, 1.65), (20, 0.30), (26, 1.10), (32, 0.45), (39, 1.45), (47, 0.35), (55, 1.00), (60, 0.45)]:
    key(mouth, f, scale=(1.0, 1.0, h))

for lid in (left_lid, right_lid):
    key(lid, 1, loc=lid.location.copy(), scale=(1.0, 1.0, 1.0))
    key(lid, 22, loc=lid.location.copy(), scale=(1.0, 1.0, 1.0))
    key(lid, 24, loc=(lid.location.x, lid.location.y, 1.628), scale=(1.0, 1.0, 3.4))
    key(lid, 27, loc=(lid.location.x, lid.location.y, 1.675), scale=(1.0, 1.0, 1.0))
    key(lid, 48, loc=(lid.location.x, lid.location.y, 1.628), scale=(1.0, 1.0, 3.2))
    key(lid, 51, loc=(lid.location.x, lid.location.y, 1.675), scale=(1.0, 1.0, 1.0))

key(left_brow, 1, rot=(0, 0, math.radians(-4)))
key(right_brow, 1, rot=(0, 0, math.radians(4)))
key(left_brow, 30, rot=(0, 0, math.radians(8)))
key(right_brow, 30, rot=(0, 0, math.radians(-8)))
key(left_brow, 60, rot=(0, 0, math.radians(-2)))
key(right_brow, 60, rot=(0, 0, math.radians(2)))
key(head, 1, rot=(0, 0, 0))
key(head, 28, rot=(math.radians(4), 0, math.radians(-3)))
key(head, 44, rot=(math.radians(-2), 0, math.radians(2)))
key(head, 60, rot=(0, 0, 0))

key(arm, 1, rot=(0, 0, math.radians(-10)), loc=(-1.12, -0.03, 1.02))
key(finger, 1, rot=(0, 0, math.radians(-10)), loc=(-0.62, -0.11, 1.07))
key(arm, 14, rot=(0, 0, math.radians(4)), loc=(-1.03, -0.03, 1.12))
key(finger, 14, rot=(0, 0, math.radians(4)), loc=(-0.52, -0.11, 1.16))
key(arm, 30, rot=(0, 0, math.radians(11)), loc=(-1.00, -0.03, 1.15))
key(finger, 30, rot=(0, 0, math.radians(11)), loc=(-0.43, -0.11, 1.20))
key(arm, 60, rot=(0, 0, math.radians(8)), loc=(-1.01, -0.03, 1.13))
key(finger, 60, rot=(0, 0, math.radians(8)), loc=(-0.45, -0.11, 1.18))

# Evidence emphasis: slight sequential pop without moving labels out of view.
for obj, start in [(qmi, 4), (work_card, 16), (box40, 28), (box50, 36), (fifo, 44), (old_lot, 52)]:
    key(obj, max(1, start - 3), scale=(1.0, 1.0, 1.0))
    key(obj, start, scale=(1.07, 1.07, 1.07))
    key(obj, min(TOTAL_FRAMES, start + 5), scale=(1.0, 1.0, 1.0))

bpy.ops.object.light_add(type="AREA", location=(-1.8, -2.8, 3.2))
key_light = bpy.context.object
key_light.name = "large_softbox"
key_light.data.energy = 230
key_light.data.size = 4.0
bpy.ops.object.light_add(type="POINT", location=(1.6, -1.3, 2.2))
rim = bpy.context.object
rim.name = "evidence_highlight"
rim.data.energy = 75

bpy.ops.object.camera_add(location=(-0.38, -4.2, 1.42))
camera = bpy.context.object
bpy.context.scene.camera = camera
camera.data.type = "ORTHO"
camera.data.ortho_scale = 3.20
target = Vector((-0.38, -0.04, 1.26))
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
scene.render.filepath = str(FRAMES_DIR / "cut005_")
bpy.ops.render.render(animation=True, write_still=True)

qa = {{
    "ok": True,
    "cut_id": "CUT_005",
    "fps": FPS,
    "total_frames": TOTAL_FRAMES,
    "duration_sec": round(TOTAL_FRAMES / FPS, 2),
    "spoken_line": "梱包工程を確認します。作業カード、QMI、箱の40個/50個表示、FIFOラベルを順に見せてください。",
    "checks": {{
        "mouth_motion": "mouth_opening scale changes across the segment",
        "blink_motion": "eyelids close at frames 24 and 48",
        "expression_motion": "brows and head are keyed",
        "evidence_priority": "QMI, WORK CARD, 40 pcs, 50 pcs, FIFO OK, OLD remain visible",
        "not_character_only": "evidence board stays in the right half of the screen"
    }},
    "approval_gate": "Human/Codex visual review required before first-half generation"
}}
(OUT_DIR / "cut005_motion_segment_qa.json").write_text(__import__("json").dumps(qa, ensure_ascii=False, indent=2), encoding="utf-8")
'''


def make_contact_sheet(frame_paths: list[Path], output_path: Path) -> None:
    from PIL import Image, ImageDraw, ImageFont

    picks = [frame_paths[i] for i in [0, 9, 18, 24, 36, 48, 59] if i < len(frame_paths)]
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
    draw.text((24, 18), "CUT_005 motion segment: evidence-first character animation", fill=(25, 35, 32), font=font_title)
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
        str(frames_dir / "cut005_%04d.png"),
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
<title>IATF CUT_005 Motion Segment</title>
<style>
body{{font-family:Segoe UI,Meiryo,sans-serif;margin:24px;background:#eef0ec;color:#1e2824}}
img,video{{max-width:100%;border:1px solid #b8c0b8;background:white}}
code{{background:#fff;padding:2px 4px}}
</style>
<h1>IATF CUT_005 Motion Segment</h1>
<p>人物は説明補助、監査証拠は主役。口パク・瞬き・表情・指差しを含む短い実動画プレビューです。</p>
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
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    WORKSPACE_MIRROR.mkdir(parents=True, exist_ok=True)
    frames_dir = OUT_DIR / "frames"
    if frames_dir.exists():
        shutil.rmtree(frames_dir)
    frames_dir.mkdir(parents=True, exist_ok=True)

    write_status("start", output_dir=str(OUT_DIR))
    with tempfile.TemporaryDirectory(prefix="iatf_cut005_segment_") as tmp:
        script_path = Path(tmp) / "cut005_blender.py"
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

    frames = sorted(frames_dir.glob("cut005_*.png"))
    if len(frames) < 60:
        raise RuntimeError(f"expected 60 frames, got {len(frames)}")

    contact_sheet = OUT_DIR / "contact_sheet.jpg"
    make_contact_sheet(frames, contact_sheet)
    qa = json.loads((OUT_DIR / "cut005_motion_segment_qa.json").read_text(encoding="utf-8"))
    mp4 = OUT_DIR / "cut005_motion_segment.mp4"
    mp4_ok = compose_mp4(frames_dir, mp4)

    mirror_contact = WORKSPACE_MIRROR / "contact_sheet.jpg"
    mirror_contact.write_bytes(contact_sheet.read_bytes())
    (WORKSPACE_MIRROR / "cut005_motion_segment_qa.json").write_text(json.dumps(qa, ensure_ascii=False, indent=2), encoding="utf-8")
    mp4_name = None
    if mp4_ok:
        mirror_mp4 = WORKSPACE_MIRROR / "cut005_motion_segment.mp4"
        mirror_mp4.write_bytes(mp4.read_bytes())
        mp4_name = mirror_mp4.name
    for path in [frames[0], frames[9], frames[18], frames[24], frames[36], frames[48], frames[59]]:
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
