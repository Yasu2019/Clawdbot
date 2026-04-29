"""Blenderアニメーションスクリプト生成 — DeepSeek V4 Pro が生成。
顎ボーン・瞼ボーン追加 + リップシンク + 瞬き + ボディモーション。"""
import json, requests, os, subprocess, tempfile
from pathlib import Path

LITELLM_URL = os.getenv("LITELLM_URL", "http://localhost:4001")
LITELLM_KEY = os.getenv("LITELLM_MASTER_KEY", "local-dev-key")

# コード生成はDeepSeek V4 Pro優先 (SWE-Bench 80.6%)
CODE_MODELS = ["opencode-go/deepseek-v4-pro", "google/gemini-2.5-flash", "local_fast"]

GLB_MAP = {
    "bulma":     "d:/Clawdbot_Docker_20260125/data/meshy_assets/bulma_mc.glb",
    "goku":      "d:/Clawdbot_Docker_20260125/data/meshy_assets/t_pose_characters/Gokuu_Orijinal.glb",
    "gohan":     "d:/Clawdbot_Docker_20260125/data/meshy_assets/gohan.glb",
    "android17": "d:/Clawdbot_Docker_20260125/data/meshy_assets/android17.glb",
    "android18": "d:/Clawdbot_Docker_20260125/data/meshy_assets/android18.glb",
    "roshi":     "d:/Clawdbot_Docker_20260125/data/meshy_assets/roshi.glb",
    "trunks":    "d:/Clawdbot_Docker_20260125/data/meshy_assets/trunks.glb",
}

POSE_ROTATIONS = {
    "neutral":      {"LeftArm": (0.4, 0, 1.2),  "RightArm": (0.4, 0, -1.2)},
    "point":        {"LeftArm": (0.0,-0.3, 0.3), "RightArm": (0.4, 0, -1.2)},
    "arms_crossed": {"LeftArm": (0.2, 0, 1.4),  "RightArm": (0.2, 0, -1.4)},
    "bow":          {"Spine":   (0.3, 0, 0),     "LeftArm": (0.4, 0, 1.2), "RightArm": (0.4, 0, -1.2)},
    "explain":      {"LeftArm": (0.0,-0.5, 0.6), "RightArm": (0.0, 0.5,-0.6)},
    "nod":          {"Neck":    (0.25,0, 0),      "Head":    (0.15, 0, 0)},
}

BLENDER_BASE_SCRIPT = '''
import bpy, math, json, os, random

# ── ユーティリティ ──────────────────────────────────────────────
def clear_scene():
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete()
    for d in [bpy.data.meshes, bpy.data.armatures, bpy.data.cameras, bpy.data.lights]:
        for item in list(d):
            d.remove(item)

def setup_camera(pos=(0, 4, 1.5), target_z=1.0):
    bpy.ops.object.camera_add(location=pos)
    cam = bpy.context.object
    cam.rotation_euler = (math.radians(90), 0, math.radians(180))
    bpy.context.scene.camera = cam

def setup_lighting():
    bpy.ops.object.light_add(type="SUN", location=(2, -2, 5))
    sun = bpy.context.object
    sun.data.energy = 3
    bpy.ops.object.light_add(type="AREA", location=(-2, 2, 3))
    fill = bpy.context.object
    fill.data.energy = 500

def import_glb(glb_path, scale=2.2):
    bpy.ops.import_scene.gltf(filepath=glb_path)
    for obj in bpy.context.selected_objects:
        obj.scale = (scale, scale, scale)
    return bpy.context.selected_objects

def add_jaw_bone(armature_obj):
    """顎ボーンを追加してリップシンクに使用"""
    bpy.context.view_layer.objects.active = armature_obj
    bpy.ops.object.mode_set(mode="EDIT")
    arm = armature_obj.data
    head_bone = arm.edit_bones.get("mixamorig:Head") or arm.edit_bones.get("Head")
    if head_bone and "jaw" not in [b.name for b in arm.edit_bones]:
        jaw = arm.edit_bones.new("jaw_bone")
        jaw.head = head_bone.head + (0, 0.05, -0.02)
        jaw.tail = head_bone.head + (0, 0.05, -0.06)
        jaw.parent = head_bone
    bpy.ops.object.mode_set(mode="OBJECT")

def add_eyelid_bones(armature_obj):
    """瞼ボーンを追加して瞬きに使用"""
    bpy.context.view_layer.objects.active = armature_obj
    bpy.ops.object.mode_set(mode="EDIT")
    arm = armature_obj.data
    head_bone = arm.edit_bones.get("mixamorig:Head") or arm.edit_bones.get("Head")
    if head_bone:
        for side, x_offset in [("L", 0.03), ("R", -0.03)]:
            bname = f"eyelid_{side}"
            if bname not in [b.name for b in arm.edit_bones]:
                el = arm.edit_bones.new(bname)
                el.head = head_bone.head + (x_offset, 0.08, 0.04)
                el.tail = head_bone.head + (x_offset, 0.08, 0.02)
                el.parent = head_bone
    bpy.ops.object.mode_set(mode="OBJECT")

def set_pose(armature_obj, pose_data, frame):
    """ポーズ設定とキーフレーム挿入"""
    bpy.context.scene.frame_set(frame)
    pose = armature_obj.pose
    for bone_suffix, rot in pose_data.items():
        for prefix in ["mixamorig:", "mixamorig", ""]:
            bname = prefix + bone_suffix
            pbone = pose.bones.get(bname)
            if pbone:
                pbone.rotation_mode = "XYZ"
                pbone.rotation_euler = rot
                pbone.keyframe_insert("rotation_euler", frame=frame)
                break

def animate_breathing(armature_obj, fps, total_frames):
    """呼吸アニメーション (Spine/Hips)"""
    pose = armature_obj.pose
    for frame in range(0, total_frames, fps // 4):
        t = frame / fps
        for bone_suffix in ["mixamorig:Spine", "Spine"]:
            pbone = pose.bones.get(bone_suffix)
            if pbone:
                bpy.context.scene.frame_set(frame)
                pbone.rotation_mode = "XYZ"
                pbone.rotation_euler[0] = math.sin(t * 0.5) * 0.015
                pbone.keyframe_insert("rotation_euler", frame=frame)

def animate_blink(armature_obj, fps, total_frames, seed=42):
    """ランダム瞬き (3〜6秒間隔)"""
    random.seed(seed)
    frame = fps * 2
    while frame < total_frames:
        interval = random.randint(fps * 3, fps * 6)
        frame += interval
        if frame >= total_frames:
            break
        for side in ["L", "R"]:
            bname = f"eyelid_{side}"
            pbone = armature_obj.pose.bones.get(bname)
            if pbone:
                pbone.rotation_mode = "XYZ"
                for f, angle in [(frame, 0), (frame+2, 0.3), (frame+4, 0)]:
                    bpy.context.scene.frame_set(f)
                    pbone.rotation_euler[0] = angle
                    pbone.keyframe_insert("rotation_euler", frame=f)

def animate_lipsync(armature_obj, phoneme_timeline, fps):
    """Rhubarb出力のフォネームタイムラインからリップシンク"""
    jaw_bone = armature_obj.pose.bones.get("jaw_bone")
    if not jaw_bone:
        return
    jaw_bone.rotation_mode = "XYZ"
    PHONEME_ANGLES = {
        "A": 0.25, "B": 0.0,  "C": 0.12, "D": 0.08,
        "E": 0.18, "F": 0.04, "G": 0.15, "H": 0.10,
        "X": 0.0,
    }
    for entry in phoneme_timeline:
        frame_s = int(entry["start"] * fps)
        frame_e = int(entry["end"] * fps)
        angle = PHONEME_ANGLES.get(entry["value"], 0.05)
        for f, a in [(frame_s, angle), (frame_e, 0.0)]:
            bpy.context.scene.frame_set(f)
            jaw_bone.rotation_euler[0] = a
            jaw_bone.keyframe_insert("rotation_euler", frame=f)

def setup_render(output_dir, fps=30, width=1280, height=720):
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE"
    scene.render.fps = fps
    scene.render.image_settings.file_format = "PNG"
    scene.render.resolution_x = width
    scene.render.resolution_y = height
    scene.render.filepath = str(output_dir) + "/frame_"
    scene.render.use_overwrite = False
    eevee = scene.eevee
    eevee.taa_render_samples = 8
'''

BLENDER_SCENE_TEMPLATE = '''
# ── メインシーン構成 ────────────────────────────────────────────
timeline_data = {timeline_json}
phoneme_data  = {phoneme_json}
output_dir    = r"{output_dir}"
fps           = 30

clear_scene()
setup_camera()
setup_lighting()
setup_render(output_dir, fps)

# キャラクター別GLBをロード・配置
CHARACTER_POSITIONS = {{
    "bulma":      (0,   0, 0),
    "goku":       (-1.5,0, 0),
    "gohan":      (1.5, 0, 0),
    "android17":  (-2.5,0, 0),
    "android18":  (2.5, 0, 0),
    "roshi":      (0, 0.5, 0),
    "trunks":     (2.0, 0, 0),
}}
GLB_MAP = {glb_map_json}
active_chars = list(set(e["character"] for e in timeline_data))
armatures = {{}}

for char in active_chars:
    glb = GLB_MAP.get(char)
    if not glb or not __import__("os").path.exists(glb):
        print(f"GLB not found for {{char}}: {{glb}}")
        continue
    objs = import_glb(glb)
    for obj in objs:
        obj.location = CHARACTER_POSITIONS.get(char, (0,0,0))
    arm = next((o for o in objs if o.type == "ARMATURE"), None)
    if arm:
        add_jaw_bone(arm)
        add_eyelid_bones(arm)
        armatures[char] = arm

# 総フレーム数を計算
if timeline_data:
    last = max(e["start_sec"] + e["duration_sec"] for e in timeline_data)
    total_frames = int((last + 2) * fps)
else:
    total_frames = fps * 60

bpy.context.scene.frame_end = total_frames

# 全キャラ共通アニメーション
for char, arm in armatures.items():
    animate_breathing(arm, fps, total_frames)
    animate_blink(arm, fps, total_frames, seed=hash(char) % 1000)

# タイムライン別ポーズ・リップシンク
POSE_ROTATIONS = {pose_rotations_json}
for entry in timeline_data:
    char  = entry["character"]
    arm   = armatures.get(char)
    if not arm:
        continue
    frame_s = int(entry["start_sec"] * fps)
    frame_e = int((entry["start_sec"] + entry["duration_sec"]) * fps)
    pose_key = entry.get("pose", "neutral")
    pose_data = POSE_ROTATIONS.get(pose_key, POSE_ROTATIONS["neutral"])
    set_pose(arm, pose_data, frame_s)
    set_pose(arm, pose_data, frame_e)

    # リップシンク
    phonemes = [p for p in phoneme_data if p.get("character") == char]
    if phonemes:
        animate_lipsync(arm, phonemes, fps)

bpy.ops.render.render(animation=True, write_still=True)
print("Render complete:", total_frames, "frames")
'''


def generate_blender_script(timeline: list, phoneme_data: list, output_dir: Path) -> str:
    glb_map_json = json.dumps(GLB_MAP)
    pose_rotations_json = json.dumps(
        {k: list(v.values()) if isinstance(list(v.values())[0], tuple)
         else {bk: list(bv) for bk, bv in v.items()}
         for k, v in POSE_ROTATIONS.items()}
    )
    # POSE_ROTATIONSをJSONシリアライズ可能な形式に
    pose_dict = {}
    for pose_name, bone_dict in POSE_ROTATIONS.items():
        pose_dict[pose_name] = {k: list(v) for k, v in bone_dict.items()}

    script = (
        BLENDER_BASE_SCRIPT
        + BLENDER_SCENE_TEMPLATE.format(
            timeline_json=json.dumps(timeline, ensure_ascii=False),
            phoneme_json=json.dumps(phoneme_data, ensure_ascii=False),
            output_dir=str(output_dir).replace("\\", "/"),
            glb_map_json=json.dumps(GLB_MAP),
            pose_rotations_json=json.dumps(pose_dict),
        )
    )
    return script


def run_blender(script_path: Path, blender_bin: str = "blender") -> bool:
    cmd = [blender_bin, "--background", "--python", str(script_path)]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=3600)
    if result.returncode != 0:
        print("BLENDER STDERR:", result.stderr[-2000:])
        return False
    return True
