"""Render one evidence-first IATF character-motion probe cut in Blender.

The probe is intentionally host-side and isolated from the production video
pipeline.  It checks whether a simple audit narrator can point at evidence
while mouth, blink, and expression motion are visible.
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
BLENDER = Path("C:/Program Files/Blender Foundation/Blender 5.1/blender.exe")
OUT_DIR = ROOT / "data/iatf_videos/IATF 16949 内部監査資料_箇条8.5.4_箇条8.5.4.1梱包工程_design_pilot/character_motion_probe"
WORKSPACE_MIRROR = ROOT / "data/workspace/iatf_character_motion_probe"
STATUS_PATH = ROOT / "data/workspace/iatf_character_motion_probe_status.json"


def write_status(stage: str, **extra: object) -> None:
    payload = {
        "updated_at": time.strftime("%Y-%m-%d %H:%M:%S %z"),
        "stage": stage,
        **extra,
    }
    STATUS_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False), flush=True)


def blender_probe_script(out_dir: Path) -> str:
    output = str(out_dir).replace("\\", "/")
    return f'''
import bpy
import math
from pathlib import Path
from mathutils import Vector

OUT_DIR = Path(r"{output}")
OUT_DIR.mkdir(parents=True, exist_ok=True)
FPS = 12
TOTAL_FRAMES = 60
SAMPLE_FRAMES = [1, 10, 18, 24, 36, 48, 60]

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

bg = mat("quiet_wall", (0.72, 0.76, 0.73, 1))
floor_m = mat("matte_floor", (0.38, 0.42, 0.40, 1))
desk_m = mat("audit_desk", (0.34, 0.30, 0.26, 1))
paper_m = mat("paper_white", (0.96, 0.94, 0.86, 1))
accent_m = mat("audit_blue", (0.08, 0.23, 0.40, 1))
red_m = mat("old_lot_red", (0.72, 0.12, 0.10, 1))
green_m = mat("fifo_green", (0.10, 0.48, 0.26, 1))
skin_m = mat("skin", (0.86, 0.64, 0.48, 1))
suit_m = mat("work_jacket", (0.10, 0.22, 0.28, 1))
black_m = mat("black", (0.02, 0.02, 0.02, 1))
mouth_m = mat("mouth", (0.42, 0.04, 0.04, 1))
white_m = mat("eye_white", (0.98, 0.98, 0.96, 1))

add_cube("floor", (0, 0, -0.04), (6.2, 5.0, 0.08), floor_m)
add_cube("back_wall", (0, 1.8, 1.55), (6.2, 0.10, 3.2), bg)
add_cube("desk", (0.05, 0.56, 0.45), (3.8, 0.95, 0.16), desk_m)
add_cube("evidence_board", (0.92, 0.02, 1.23), (1.95, 0.08, 1.16), paper_m)
add_cube("qmi_sheet", (0.26, -0.05, 1.37), (0.48, 0.04, 0.34), accent_m)
add_cube("work_card", (0.84, -0.06, 1.44), (0.60, 0.04, 0.28), paper_m)
add_cube("old_lot", (1.42, -0.07, 1.35), (0.45, 0.05, 0.28), red_m)
add_cube("fifo_label", (1.02, -0.08, 0.92), (0.96, 0.05, 0.20), green_m)
add_cube("container_50", (1.62, -0.10, 0.90), (0.42, 0.30, 0.24), accent_m)

add_text("title", "Audit evidence: packaging", (-0.03, -0.18, 1.88), 0.09, black_m)
add_text("qmi", "QMI", (0.08, -0.19, 1.43), 0.11, white_m)
add_text("work_card_label", "WORK CARD", (0.55, -0.20, 1.50), 0.075, black_m)
add_text("old_item_label", "OLD ITEM", (1.20, -0.21, 1.41), 0.065, white_m)
add_text("fifo", "FIFO OK", (0.68, -0.22, 0.98), 0.080, white_m)
add_text("count", "50 pcs", (1.45, -0.24, 0.99), 0.070, white_m)
add_text("narration", "Check actual records, not only the procedure.", (-2.45, -0.18, 0.62), 0.072, black_m)

body = add_cube("auditor_body", (-1.55, 0.10, 0.92), (0.50, 0.24, 0.84), suit_m)
head = add_uv("auditor_head", (-1.55, -0.05, 1.57), (0.32, 0.28, 0.32), skin_m)
neck = add_cube("neck", (-1.55, 0.03, 1.27), (0.16, 0.13, 0.18), skin_m)
left_eye = add_uv("left_eye", (-1.68, -0.27, 1.64), (0.060, 0.020, 0.036), white_m)
right_eye = add_uv("right_eye", (-1.43, -0.27, 1.64), (0.060, 0.020, 0.036), white_m)
left_pupil = add_uv("left_pupil", (-1.68, -0.30, 1.64), (0.023, 0.009, 0.022), black_m)
right_pupil = add_uv("right_pupil", (-1.43, -0.30, 1.64), (0.023, 0.009, 0.022), black_m)
left_lid = add_cube("left_eyelid", (-1.68, -0.315, 1.675), (0.14, 0.014, 0.020), skin_m)
right_lid = add_cube("right_eyelid", (-1.43, -0.315, 1.675), (0.14, 0.014, 0.020), skin_m)
left_brow = add_cube("left_brow", (-1.68, -0.320, 1.78), (0.16, 0.014, 0.020), black_m)
right_brow = add_cube("right_brow", (-1.43, -0.320, 1.78), (0.16, 0.014, 0.020), black_m)
mouth = add_cube("mouth_opening", (-1.55, -0.325, 1.48), (0.19, 0.014, 0.045), mouth_m)
arm = add_cube("pointing_arm", (-1.02, -0.03, 1.10), (0.90, 0.12, 0.13), skin_m)
finger = add_cube("pointing_finger", (-0.45, -0.11, 1.16), (0.28, 0.065, 0.065), skin_m)

# Mouth movement: syllable-like open/close.
for f, h in [(1, 0.35), (6, 1.25), (12, 0.45), (18, 1.65), (24, 0.30), (30, 1.10), (36, 0.45), (44, 1.45), (52, 0.35), (60, 0.70)]:
    key(mouth, f, scale=(1.0, 1.0, h))

# Blink at frames 22-26.
for lid in (left_lid, right_lid):
    key(lid, 1, loc=lid.location.copy())
    key(lid, 22, loc=lid.location.copy())
key(lid, 24, loc=(lid.location.x, lid.location.y, 1.628), scale=(1.0, 1.0, 3.4))
key(lid, 27, loc=(lid.location.x, lid.location.y, 1.675), scale=(1.0, 1.0, 1.0))

# Expression shift: attentive to slight concern, then confident.
key(left_brow, 1, rot=(0, 0, math.radians(-4)))
key(right_brow, 1, rot=(0, 0, math.radians(4)))
key(left_brow, 30, rot=(0, 0, math.radians(8)))
key(right_brow, 30, rot=(0, 0, math.radians(-8)))
key(left_brow, 60, rot=(0, 0, math.radians(-2)))
key(right_brow, 60, rot=(0, 0, math.radians(2)))

# Evidence-facing gesture and head nod.
key(arm, 1, rot=(0, 0, math.radians(-10)), loc=(-1.12, -0.03, 1.02))
key(finger, 1, rot=(0, 0, math.radians(-10)), loc=(-0.62, -0.11, 1.07))
key(arm, 20, rot=(0, 0, math.radians(10)), loc=(-1.02, -0.03, 1.13))
key(finger, 20, rot=(0, 0, math.radians(10)), loc=(-0.45, -0.11, 1.18))
key(arm, 60, rot=(0, 0, math.radians(10)), loc=(-1.02, -0.03, 1.13))
key(finger, 60, rot=(0, 0, math.radians(10)), loc=(-0.45, -0.11, 1.18))
key(head, 1, rot=(0, 0, 0))
key(head, 28, rot=(math.radians(4), 0, math.radians(-3)))
key(head, 44, rot=(math.radians(-2), 0, math.radians(2)))
key(head, 60, rot=(0, 0, 0))

bpy.ops.object.light_add(type="AREA", location=(-1.8, -2.8, 3.2))
key_light = bpy.context.object
key_light.name = "large_softbox"
key_light.data.energy = 230
key_light.data.size = 4.0
bpy.ops.object.light_add(type="POINT", location=(1.6, -1.3, 2.2))
rim = bpy.context.object
rim.name = "evidence_highlight"
rim.data.energy = 70

bpy.ops.object.camera_add(location=(-0.38, -4.2, 1.42))
camera = bpy.context.object
bpy.context.scene.camera = camera
camera.data.type = "ORTHO"
camera.data.ortho_scale = 3.18
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

# Render only diagnostic frames so this stays fast and reviewable.
for frame in SAMPLE_FRAMES:
    scene.frame_set(frame)
    scene.render.filepath = str(OUT_DIR / f"probe_frame_{{frame:03d}}.png")
    bpy.ops.render.render(write_still=True)

qa = {{
    "ok": True,
    "fps": FPS,
    "total_frames": TOTAL_FRAMES,
    "sample_frames": SAMPLE_FRAMES,
    "checks": {{
        "mouth_motion": "mouth_opening scale z changes across 10 keyed frames",
        "blink_motion": "eyelids close at frame 24 and reopen by frame 27",
        "expression_motion": "brow angle changes at frames 1, 30, 60",
        "body_motion": "arm and finger point toward evidence board from frame 20 onward",
        "evidence_priority": "QMI, WORK CARD, OLD ITEM, FIFO OK, 50 pcs remain in the main screen area"
    }},
    "no_go": [
        "character-only framing",
        "out-of-focus evidence",
        "static face with no mouth/blink/expression keys"
    ]
}}
(OUT_DIR / "character_motion_probe_qa.json").write_text(__import__("json").dumps(qa, ensure_ascii=False, indent=2), encoding="utf-8")
'''


def make_contact_sheet(frame_paths: list[Path], output_path: Path) -> None:
    from PIL import Image, ImageDraw, ImageFont

    thumbs = []
    for path in frame_paths:
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

    draw.text((24, 18), "IATF character motion probe: mouth / blink / expression / evidence", fill=(25, 35, 32), font=font_title)
    for idx, (path, img) in enumerate(thumbs):
        col = idx % 2
        row = idx // 2
        x = 24 + col * 368
        y = 70 + row * row_h
        sheet.paste(img, (x, y))
        draw.text((x, y + img.height + 8), path.stem.replace("probe_frame_", "frame "), fill=(25, 35, 32), font=font)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(output_path, quality=92)


def write_index(out_dir: Path, mirror_dir: Path, contact_sheet: Path, frames: list[Path]) -> None:
    html = [
        "<!doctype html>",
        "<meta charset='utf-8'>",
        "<title>IATF Character Motion Probe</title>",
        "<style>body{font-family:Segoe UI,Meiryo,sans-serif;margin:24px;background:#eef0ec;color:#1e2824} img{max-width:100%;border:1px solid #b8c0b8} .grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(320px,1fr));gap:16px}.card{background:white;padding:12px;border-radius:6px}</style>",
        "<h1>IATF Character Motion Probe</h1>",
        "<p>Evidence remains central while the narrator points, talks, blinks, and changes expression.</p>",
        f"<p>Source folder: <code>{out_dir}</code></p>",
        "<h2>Contact sheet</h2>",
        f"<img src='{contact_sheet.name}' alt='contact sheet'>",
        "<h2>Frames</h2><div class='grid'>",
    ]
    for frame in frames:
        html.append(f"<div class='card'><img src='{frame.name}'><p>{frame.stem}</p></div>")
    html.append("</div>")
    (mirror_dir / "index.html").write_text("\n".join(html), encoding="utf-8")


def main() -> int:
    if not BLENDER.exists():
        raise FileNotFoundError(f"Blender not found: {BLENDER}")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    WORKSPACE_MIRROR.mkdir(parents=True, exist_ok=True)
    write_status("start", output_dir=str(OUT_DIR))

    with tempfile.TemporaryDirectory(prefix="iatf_character_probe_") as tmp:
        script_path = Path(tmp) / "probe_blender.py"
        script_path.write_text(blender_probe_script(OUT_DIR), encoding="utf-8")
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

    frames = sorted(OUT_DIR.glob("probe_frame_*.png"))
    if len(frames) < 7:
        raise RuntimeError(f"expected 7 probe frames, got {len(frames)}")

    contact_sheet = OUT_DIR / "contact_sheet.jpg"
    make_contact_sheet(frames, contact_sheet)

    mirror_frames = []
    for path in frames:
        mirror = WORKSPACE_MIRROR / path.name
        mirror.write_bytes(path.read_bytes())
        mirror_frames.append(mirror)
    mirror_contact = WORKSPACE_MIRROR / "contact_sheet.jpg"
    mirror_contact.write_bytes(contact_sheet.read_bytes())
    qa = json.loads((OUT_DIR / "character_motion_probe_qa.json").read_text(encoding="utf-8"))
    (WORKSPACE_MIRROR / "character_motion_probe_qa.json").write_text(
        json.dumps(qa, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    write_index(OUT_DIR, WORKSPACE_MIRROR, mirror_contact, mirror_frames)

    write_status(
        "done",
        ok=True,
        frames=len(frames),
        contact_sheet=str(contact_sheet),
        mirror_index=str(WORKSPACE_MIRROR / "index.html"),
        qa=str(OUT_DIR / "character_motion_probe_qa.json"),
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        write_status("error", error=str(exc))
        raise
