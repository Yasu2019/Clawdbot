# -*- coding: utf-8 -*-
"""
zaku_walk_origin_style.py
Auto-rigged Zaku walking animation — motion parameters from Gundam ORIGIN Zaku I reference.

Camera: dramatic low-angle (foot-level), 35mm lens, looking up at the mecha.
Walk: slow heavy stride (1.5s/step), minimal body bob, knee bend, ankle roll.

Run:
  & "C:\Program Files\Blender Foundation\Blender 5.1\blender.exe" --background `
    --python projects\AtsugiMechaCity\scenes\zaku_walk_origin_style.py

Test single frame first:
  ... -- --test-frame 1
"""
import bpy
import math
import sys
from pathlib import Path

# ===== CLI ARGS =====
_user_args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
_TEST_FRAME = None
if "--test-frame" in _user_args:
    _idx = _user_args.index("--test-frame")
    if _idx + 1 < len(_user_args):
        _TEST_FRAME = int(_user_args[_idx + 1])
# --verify: dump world-space foot/root positions across a stride, no render
_VERIFY = "--verify" in _user_args

# ===== CONFIG =====
PROJECT_ROOT = Path("D:/Clawdbot_Docker_20260125")
RIGGED_BLEND = Path("D:/Temp/Zaku_AutoRig_v2.blend")
HDRI_PATH = PROJECT_ROOT / "data/workspace/apps/blender_assets/polyhaven/hdri/abandoned_factory_canteen_01_1k.hdr"
OUT_DIR = PROJECT_ROOT / "projects/AtsugiMechaCity/output/zaku_walk_origin"
FRAMES_DIR = OUT_DIR / "frames"

# Walk parameters — derived from ORIGIN Zaku I reference analysis
TOTAL_FRAMES = 96          # 4 seconds at 24fps — 2.67 full strides
FPS = 24
STRIDE_FRAMES = 36         # 1.5 seconds per stride (heavy mecha)

# Hip swing: ±11° — REDUCED from 18°. The thigh is a rigid segment pivoting at the
# hip bone head; with no overlapping hip skirt, a larger swing opens a visible gap
# (mesh separation) at the hip joint. 11° keeps a readable stride (~1.4m foot travel
# on an 18m mecha) while keeping the rigid hinge gap small. (T031 discipline.)
HIP_SWING_DEG = 11.0
# Knee bend: ±22° — REDUCED from 35° for the same rigid-hinge-gap reason at the knee.
KNEE_BEND_DEG = 22.0
# Ankle toe-off: ±12° — rear foot lifts heel slightly
ANKLE_ROLL_DEG = 12.0
# Body bob: 0.08m (ORIGIN has almost no vertical bounce — heavy machine)
BODY_BOB_M = 0.08
# Forward lean: 4° constant
FORWARD_LEAN_DEG = 4.0
# Hip roll (weight shift): ±2.5°
HIP_ROLL_DEG = 2.5
# Arms: the auto-rig authored this Zaku in a literal T-POSE (arms straight out,
# hands ~7.4m from shoulders) AND the UpperArm bone pivot is offset from the true
# shoulder joint with NO overlapping shoulder armor. CONSEQUENCE (QC-confirmed via
# multi-angle sweep 0/-15/-25/-50°): ANY adduction to lower the arms swings the
# rigid arm segment OUT OF its shoulder socket -> the whole arm visibly DETACHES and
# floats off the body. There is no swing angle that both lowers the arm and keeps it
# attached. This is a RIG-LEVEL defect (needs correct shoulder pivot + overlapping
# armor or proper skinning), NOT fixable in animation.
#  -> Until the rig is fixed we leave the arms AT REST (attached, but T-posed) and
#     apply only a tiny fore/aft swing well within the no-gap range. Set
#     ARM_POSE_ENABLED=True only after the rig provides proper shoulder joints.
ARM_POSE_ENABLED = False   # rig detaches arms when posed — keep at rest for now
ARM_DOWN_DEG = 0.0         # (disabled) base adduction — detaches arm if non-zero
ARM_NEUTRAL_DEG = 0.0      # (disabled) fore/aft neutral
# Arm swing: ±3° only — small enough to stay within the shoulder socket (no detach)
ARM_SWING_DEG = 3.0
# Walk distance: 12m forward (-Y) in 96 frames
WALK_DIST = 12.0

# Camera — low angle like ORIGIN (foot-level looking up)
CAM_LENS_MM = 35
# Camera starts at side-front, low. Ends close to passing legs.
CAM_HEIGHT = 5.0  # 5m off ground — knee level for 18m mecha
# Camera at side, dolly tracking mecha as it walks past
# X=20 keeps safe distance, Y moves with the mecha
CAM_START = (20.0, 2.0, CAM_HEIGHT)     # side, slightly ahead of start pos
CAM_END = (16.0, -10.0, CAM_HEIGHT)     # follows mecha walk direction

# Render
RENDER_W = 1080   # vertical format like the ORIGIN YouTube short
RENDER_H = 1920
SAMPLES = 64

# Ground plane
GROUND_SIZE = 200.0


def p(msg):
    print(f"[ZakuWalk] {msg}", flush=True)


p("=== START: Zaku Walk (ORIGIN Style) ===")
OUT_DIR.mkdir(parents=True, exist_ok=True)
FRAMES_DIR.mkdir(parents=True, exist_ok=True)

# ===== LOAD RIGGED BLEND =====
p(f"Loading rigged blend: {RIGGED_BLEND}")
bpy.ops.wm.open_mainfile(filepath=str(RIGGED_BLEND))
scene = bpy.context.scene
scene.render.fps = FPS
scene.frame_start = 1
scene.frame_end = TOTAL_FRAMES

# Find armature
armature = None
for obj in scene.objects:
    if obj.type == "ARMATURE":
        armature = obj
        break

if not armature:
    raise RuntimeError("No armature found in blend file")

p(f"Armature: {armature.name}, bones: {len(armature.data.bones)}")

# ===== HDRI ENVIRONMENT =====
if scene.world is None:
    scene.world = bpy.data.worlds.new("World")
world = scene.world
world.use_nodes = True
nt = world.node_tree
nt.nodes.clear()
bg = nt.nodes.new("ShaderNodeBackground")
env = nt.nodes.new("ShaderNodeTexEnvironment")
out = nt.nodes.new("ShaderNodeOutputWorld")
nt.links.new(env.outputs["Color"], bg.inputs["Color"])
nt.links.new(bg.outputs["Background"], out.inputs["Surface"])
bg.inputs["Strength"].default_value = 0.4  # dim factory interior
if HDRI_PATH.exists():
    env.image = bpy.data.images.load(str(HDRI_PATH))
    p(f"HDRI loaded: {HDRI_PATH.name}")
else:
    p(f"WARNING: HDRI not found: {HDRI_PATH}")

# ===== GROUND PLANE (wet reflective floor like ORIGIN) =====
bpy.ops.mesh.primitive_plane_add(size=GROUND_SIZE, location=(0, 0, 0))
ground = bpy.context.active_object
ground.name = "GroundPlane"

mat_ground = bpy.data.materials.new("WetConcrete")
mat_ground.use_nodes = True
gnt = mat_ground.node_tree
gnt.nodes.clear()
principled = gnt.nodes.new("ShaderNodeBsdfPrincipled")
output_node = gnt.nodes.new("ShaderNodeOutputMaterial")
gnt.links.new(principled.outputs["BSDF"], output_node.inputs["Surface"])
# Dark wet concrete — slightly reflective
principled.inputs["Base Color"].default_value = (0.03, 0.03, 0.035, 1.0)
principled.inputs["Roughness"].default_value = 0.15   # wet = low roughness = reflective
principled.inputs["Metallic"].default_value = 0.0
ground.data.materials.clear()
ground.data.materials.append(mat_ground)

# ===== SUN LIGHT (factory overhead) =====
for obj in list(scene.objects):
    if obj.type == "LIGHT":
        bpy.data.objects.remove(obj, do_unlink=True)

bpy.ops.object.light_add(type="SUN", location=(0, 0, 50))
sun = bpy.context.active_object
sun.name = "FactoryLight"
sun.data.energy = 3.0
sun.rotation_euler = (math.radians(60), 0, math.radians(30))

# Rim light from behind — adds edge definition like ORIGIN shots
bpy.ops.object.light_add(type="AREA", location=(0, 25, 30))
rim = bpy.context.active_object
rim.name = "RimLight"
rim.data.energy = 500
rim.data.size = 10
rim.rotation_euler = (math.radians(-45), 0, 0)

p("Lighting setup complete")

# ===== WALK ANIMATION =====
p(f"Generating walk: {TOTAL_FRAMES}f, stride={STRIDE_FRAMES}f, swing=±{HIP_SWING_DEG}°")

bpy.context.view_layer.objects.active = armature
armature.select_set(True)
bpy.ops.object.mode_set(mode="POSE")

TAU = math.tau

# Bone references
pb = armature.pose.bones
bone_names = {
    "root": "Root",
    "hips": "Hips",
    "chest": "Chest",
    "neck": "Neck",
    "head": "Head",
    "mono_eye": "MonoEye",
    "upper_leg_l": "UpperLeg_L",
    "upper_leg_r": "UpperLeg_R",
    "lower_leg_l": "LowerLeg_L",
    "lower_leg_r": "LowerLeg_R",
    "foot_l": "Foot_L",
    "foot_r": "Foot_R",
    "upper_arm_l": "UpperArm_L",
    "upper_arm_r": "UpperArm_R",
    "lower_arm_l": "LowerArm_L",
    "lower_arm_r": "LowerArm_R",
}

# Verify bones exist
for key, name in bone_names.items():
    if name not in pb:
        p(f"WARNING: bone '{name}' not found in armature")

# Temporarily disable LIMIT_ROTATION constraints during animation
disabled_constraints = []
for pbone in pb:
    for c in pbone.constraints:
        if c.type == "LIMIT_ROTATION" and c.mute is False:
            c.mute = True
            disabled_constraints.append((pbone.name, c.name))

p(f"Temporarily muted {len(disabled_constraints)} LIMIT_ROTATION constraints for animation")

# Clear existing animation
if armature.animation_data:
    armature.animation_data_clear()

# Set Euler mode on ALL pose bones ONCE before animating. Switching rotation_mode
# from QUATERNION to XYZ resets rotation_euler, so doing it per-frame (after setting
# the euler) silently zeroed the FIRST frame's pose — visible as arms snapping to the
# splayed rest pose on frame 1. Set the mode up front so every keyframe sticks.
for pbone in pb:
    pbone.rotation_mode = "XYZ"

# Capture armature object's base world position. Forward travel + body bob are
# applied to the ARMATURE OBJECT (true world space), NOT a pose bone — pose-bone
# .location is in the bone's local rest frame, and Root points up, so writing
# walk distance there sinks the model through the floor instead of moving it.
base_loc = armature.location.copy()

for f in range(1, TOTAL_FRAMES + 1):
    scene.frame_set(f)
    t = (f - 1) / max(TOTAL_FRAMES - 1, 1)  # 0..1
    phase = (f / STRIDE_FRAMES) * TAU

    # --- FORWARD WALK + BODY BOB (armature object, world space) ---
    walk_y = -t * WALK_DIST  # walk in -Y direction (world)
    bob_z = abs(math.sin(phase)) * BODY_BOB_M
    armature.location = (base_loc.x, base_loc.y + walk_y, base_loc.z + bob_z)
    armature.keyframe_insert(data_path="location", frame=f)

    # --- HIPS: forward lean + roll (weight shift) ---
    hips_bone = pb.get("Hips")
    if hips_bone:
        lean_x = math.radians(FORWARD_LEAN_DEG)
        roll_y = math.sin(phase) * math.radians(HIP_ROLL_DEG)
        hips_bone.rotation_euler = (lean_x, roll_y, 0)
        hips_bone.rotation_mode = "XYZ"
        hips_bone.keyframe_insert(data_path="rotation_euler", frame=f)

    # --- UPPER LEGS: hip swing (main walking motion) ---
    swing_rad = math.radians(HIP_SWING_DEG)
    # L leg: sin(phase), R leg: sin(phase + pi) = opposite
    upper_leg_l = pb.get("UpperLeg_L")
    upper_leg_r = pb.get("UpperLeg_R")
    if upper_leg_l:
        upper_leg_l.rotation_euler = (math.sin(phase) * swing_rad, 0, 0)
        upper_leg_l.rotation_mode = "XYZ"
        upper_leg_l.keyframe_insert(data_path="rotation_euler", frame=f)
    if upper_leg_r:
        upper_leg_r.rotation_euler = (math.sin(phase + math.pi) * swing_rad, 0, 0)
        upper_leg_r.rotation_mode = "XYZ"
        upper_leg_r.keyframe_insert(data_path="rotation_euler", frame=f)

    # --- LOWER LEGS: knee bend ---
    # Knee bends backward (positive X rotation in local space) during swing-through
    # Max bend when upper leg passes vertical (phase + pi/2)
    knee_rad = math.radians(KNEE_BEND_DEG)
    lower_leg_l = pb.get("LowerLeg_L")
    lower_leg_r = pb.get("LowerLeg_R")
    if lower_leg_l:
        # Knee only bends backward (0 to +knee_rad), peaks during swing phase
        knee_l = max(0, math.sin(phase - math.pi / 4)) * knee_rad
        lower_leg_l.rotation_euler = (knee_l, 0, 0)
        lower_leg_l.rotation_mode = "XYZ"
        lower_leg_l.keyframe_insert(data_path="rotation_euler", frame=f)
    if lower_leg_r:
        knee_r = max(0, math.sin(phase + math.pi - math.pi / 4)) * knee_rad
        lower_leg_r.rotation_euler = (knee_r, 0, 0)
        lower_leg_r.rotation_mode = "XYZ"
        lower_leg_r.keyframe_insert(data_path="rotation_euler", frame=f)

    # --- FEET: ankle roll (toe-off on rear leg) ---
    ankle_rad = math.radians(ANKLE_ROLL_DEG)
    foot_l = pb.get("Foot_L")
    foot_r = pb.get("Foot_R")
    if foot_l:
        # Toe points down when leg is behind (negative swing = pushing off)
        ankle_l = max(0, -math.sin(phase)) * ankle_rad
        foot_l.rotation_euler = (ankle_l, 0, 0)
        foot_l.rotation_mode = "XYZ"
        foot_l.keyframe_insert(data_path="rotation_euler", frame=f)
    if foot_r:
        ankle_r = max(0, -math.sin(phase + math.pi)) * ankle_rad
        foot_r.rotation_euler = (ankle_r, 0, 0)
        foot_r.rotation_mode = "XYZ"
        foot_r.keyframe_insert(data_path="rotation_euler", frame=f)

    # --- ARMS: lower to sides (base pose) + fore/aft counter-swing ---
    # The rig rest pose splays the arms out sideways (T/A-pose). Apply a constant
    # adduction on local X to bring them down, a neutral on local Y for straight-
    # down hang, then the walking swing on local Y (opposite to same-side leg).
    arm_rad = math.radians(ARM_SWING_DEG)
    base_x = math.radians(ARM_DOWN_DEG)
    neutral_y = math.radians(ARM_NEUTRAL_DEG)
    upper_arm_l = pb.get("UpperArm_L")
    upper_arm_r = pb.get("UpperArm_R")
    if ARM_POSE_ENABLED:
        # Lowered-arm pose (requires a FIXED rig — currently detaches the arm).
        # Arm bones are MIRRORED (L/R local-Y flipped), so the right arm's neutral is
        # the mirror of the left's; both use the same swing term so they hang down and
        # swing OPPOSITE each other.
        if upper_arm_l:
            upper_arm_l.rotation_euler = (base_x, neutral_y + math.sin(phase + math.pi) * arm_rad, 0)
            upper_arm_l.keyframe_insert(data_path="rotation_euler", frame=f)
        if upper_arm_r:
            upper_arm_r.rotation_euler = (base_x, -neutral_y + math.sin(phase + math.pi) * arm_rad, 0)
            upper_arm_r.keyframe_insert(data_path="rotation_euler", frame=f)
    else:
        # SAFE MODE: arms stay at rest (attached T-pose). Only a tiny local-X swing,
        # small enough to stay inside the shoulder socket (no detachment).
        if upper_arm_l:
            upper_arm_l.rotation_euler = (-math.sin(phase) * arm_rad, 0, 0)
            upper_arm_l.keyframe_insert(data_path="rotation_euler", frame=f)
        if upper_arm_r:
            upper_arm_r.rotation_euler = (-math.sin(phase + math.pi) * arm_rad, 0, 0)
            upper_arm_r.keyframe_insert(data_path="rotation_euler", frame=f)

    # --- CHEST: subtle counter-rotation to hips ---
    chest_bone = pb.get("Chest")
    if chest_bone:
        chest_bone.rotation_euler = (0, -roll_y * 0.3, 0)
        chest_bone.rotation_mode = "XYZ"
        chest_bone.keyframe_insert(data_path="rotation_euler", frame=f)

bpy.ops.object.mode_set(mode="OBJECT")
p("Walk keyframes complete")

# ===== VERIFY MODE: dump world positions, prove it's a walk cycle =====
if _VERIFY:
    import mathutils

    def world_head(bone_name):
        pbone = armature.pose.bones.get(bone_name)
        if not pbone:
            return None
        return armature.matrix_world @ pbone.head

    def world_tail(bone_name):
        pbone = armature.pose.bones.get(bone_name)
        if not pbone:
            return None
        return armature.matrix_world @ pbone.tail

    p("=== VERIFY: world-space positions across one stride (36f) ===")
    p("frame | rootY  bobZ  | FootL(Y,Z)        FootR(Y,Z)        | gait")
    foot_l_y_series = []
    foot_r_y_series = []
    foot_l_z_series = []
    foot_r_z_series = []
    root_y_series = []
    # Arm swing tracked RELATIVE to root (subtract body travel) so we measure the
    # actual fore/aft swing, not the whole body moving forward.
    hand_l_rel_y_series = []
    hand_r_rel_y_series = []
    for f in range(1, STRIDE_FRAMES * 2 + 1, 3):
        scene.frame_set(f)
        bpy.context.view_layer.update()
        rb = armature.pose.bones.get("Root")
        root_loc = armature.matrix_world @ rb.head if rb else mathutils.Vector((0, 0, 0))
        fl = world_tail("Foot_L")
        fr = world_tail("Foot_R")
        hl = world_tail("Hand_L") or world_tail("LowerArm_L")
        hr = world_tail("Hand_R") or world_tail("LowerArm_R")
        if hl and hr:
            hand_l_rel_y_series.append(hl.y - root_loc.y)
            hand_r_rel_y_series.append(hr.y - root_loc.y)
        if fl and fr:
            foot_l_y_series.append(fl.y)
            foot_r_y_series.append(fr.y)
            foot_l_z_series.append(fl.z)
            foot_r_z_series.append(fr.z)
            root_y_series.append(root_loc.y)
            # Which foot is forward (more negative Y = forward, walk dir is -Y)
            lead = "L-fwd" if fl.y < fr.y else "R-fwd"
            p(f"  {f:3d} | {root_loc.y:6.2f} {root_loc.z:5.2f} | "
              f"({fl.y:7.2f},{fl.z:6.2f})  ({fr.y:7.2f},{fr.z:6.2f}) | {lead}")

    # Analysis
    def amplitude(series):
        return max(series) - min(series) if series else 0.0

    fl_y_amp = amplitude(foot_l_y_series)
    fr_y_amp = amplitude(foot_r_y_series)
    fl_z_amp = amplitude(foot_l_z_series)
    fr_z_amp = amplitude(foot_r_z_series)
    root_travel = (root_y_series[0] - root_y_series[-1]) if len(root_y_series) > 1 else 0.0

    p("=== VERDICT ===")
    p(f"Foot_L forward/back swing (Y amplitude): {fl_y_amp:.2f}m")
    p(f"Foot_R forward/back swing (Y amplitude): {fr_y_amp:.2f}m")
    p(f"Foot_L lift (Z amplitude):               {fl_z_amp:.2f}m")
    p(f"Foot_R lift (Z amplitude):               {fr_z_amp:.2f}m")
    p(f"Root forward travel over 2 strides:      {root_travel:.2f}m")

    walk_ok = fl_y_amp > 0.5 and fr_y_amp > 0.5
    # Check feet are out of phase: when L is forward, R should be back
    out_of_phase = False
    if len(foot_l_y_series) == len(foot_r_y_series) and foot_l_y_series:
        diffs = [l - r for l, r in zip(foot_l_y_series, foot_r_y_series)]
        out_of_phase = (max(diffs) > 0.3) and (min(diffs) < -0.3)
    # MUST advance forward — a walk that doesn't move is not a walk (T031 lesson)
    forward_ok = abs(root_travel) > WALK_DIST * 0.5
    # Feet MUST NOT sink through the floor (z >= -0.5m tolerance)
    foot_min_z = min(foot_l_z_series + foot_r_z_series) if foot_l_z_series else 0.0
    grounded_ok = foot_min_z > -0.5
    p(f"Feet swing detected (>0.5m):   {'YES' if walk_ok else 'NO'}")
    p(f"Feet alternate (out of phase): {'YES' if out_of_phase else 'NO'}")
    p(f"Body advances forward (>{WALK_DIST*0.5:.0f}m): {'YES' if forward_ok else 'NO'}  (travel={root_travel:.2f}m)")
    p(f"Feet stay on floor (z>-0.5):   {'YES' if grounded_ok else 'NO'}  (min foot z={foot_min_z:.2f}m)")
    valid = walk_ok and out_of_phase and forward_ok and grounded_ok
    p(f"WALK CYCLE VALID: {'YES — genuinely walking forward, feet on ground' if valid else 'NO — broken (see failed checks above)'}")

    # ===== ARM CHECK: T-pose vs natural fore/aft swing =====
    p("=== ARM CHECK ===")
    # Rest-pose geometry at frame 1: are arms hanging (hand below shoulder, near body)
    # or sticking out sideways (T-pose: hand far in X, level with shoulder in Z)?
    scene.frame_set(1)
    bpy.context.view_layer.update()
    sh_l = world_head("UpperArm_L")   # shoulder
    hand_l = world_tail("Hand_L") or world_tail("LowerArm_L")
    tpose_note = "unknown"
    if sh_l and hand_l:
        side = abs(hand_l.x - sh_l.x)     # sideways reach from shoulder
        drop = sh_l.z - hand_l.z          # how far the hand hangs below shoulder
        p(f"Rest pose L arm: shoulder z={sh_l.z:.2f}, hand z={hand_l.z:.2f}, "
          f"sideways reach={side:.2f}m, hang drop={drop:.2f}m")
        if drop > side:
            tpose_note = f"ARMS HANG DOWN (drop {drop:.2f}m > side {side:.2f}m) — NOT a T-pose"
        else:
            tpose_note = f"ARMS STICK OUT SIDEWAYS (side {side:.2f}m >= drop {drop:.2f}m) — T/A-POSE-like"
        p(tpose_note)
    hl_amp = amplitude(hand_l_rel_y_series)
    hr_amp = amplitude(hand_r_rel_y_series)
    p(f"Hand_L fore/aft swing (relative to body): {hl_amp:.2f}m")
    p(f"Hand_R fore/aft swing (relative to body): {hr_amp:.2f}m")
    arm_out_of_phase = False
    if len(hand_l_rel_y_series) == len(hand_r_rel_y_series) and hand_l_rel_y_series:
        adiffs = [l - r for l, r in zip(hand_l_rel_y_series, hand_r_rel_y_series)]
        arm_out_of_phase = (max(adiffs) > 0.05) and (min(adiffs) < -0.05)
    arms_swing = hl_amp > 0.05 and hr_amp > 0.05
    p(f"Arms swing fore/aft (>0.05m):  {'YES' if arms_swing else 'NO'}")
    p(f"Arms alternate (counter-swing): {'YES' if arm_out_of_phase else 'NO'}")
    p("=== VERIFY DONE (no render) ===")
    sys.exit(0)

# ===== CAMERA (ORIGIN-style low angle) =====
for obj in list(scene.objects):
    if obj.type == "CAMERA":
        bpy.data.objects.remove(obj, do_unlink=True)

cam_data = bpy.data.cameras.new("WalkCamera")
cam_obj = bpy.data.objects.new("WalkCamera", cam_data)
scene.collection.objects.link(cam_obj)
scene.camera = cam_obj
cam_data.lens = CAM_LENS_MM
cam_data.clip_end = 500

# Track-To: camera follows the mecha hips area
track_con = cam_obj.constraints.new(type="TRACK_TO")
track_con.target = armature
track_con.subtarget = "Chest"
track_con.track_axis = "TRACK_NEGATIVE_Z"
track_con.up_axis = "UP_Y"

# Dolly keyframes
cam_obj.animation_data_clear()
for f in range(1, TOTAL_FRAMES + 1):
    t = (f - 1) / max(TOTAL_FRAMES - 1, 1)
    te = t * t * (3 - 2 * t)  # smoothstep
    cx = CAM_START[0] + (CAM_END[0] - CAM_START[0]) * te
    cy = CAM_START[1] + (CAM_END[1] - CAM_START[1]) * te
    cz = CAM_START[2] + (CAM_END[2] - CAM_START[2]) * te
    cam_obj.location = (cx, cy, cz)
    cam_obj.keyframe_insert(data_path="location", frame=f)

p(f"Camera: {CAM_START} -> {CAM_END}, {CAM_LENS_MM}mm, track=Hips")

# ===== RENDER SETUP =====
scene.render.engine = "CYCLES"
scene.cycles.device = "CPU"
scene.cycles.samples = SAMPLES
try:
    scene.cycles.use_denoising = True
    scene.cycles.denoiser = "OPENIMAGEDENOISE"
except Exception:
    pass

scene.render.resolution_x = RENDER_W
scene.render.resolution_y = RENDER_H
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = "PNG"
scene.render.image_settings.color_mode = "RGB"

# Film transparent off — we want the ground plane visible
scene.render.film_transparent = False

p(f"Render: {RENDER_W}x{RENDER_H}, {SAMPLES} samples, CYCLES CPU+OIDN")

# ===== RENDER =====
if _TEST_FRAME is not None:
    # Single frame test
    scene.frame_set(_TEST_FRAME)
    test_path = str(OUT_DIR / f"test_frame_{_TEST_FRAME:04d}.png")
    scene.render.filepath = test_path
    bpy.ops.render.render(write_still=True)
    p(f"Test frame rendered: {test_path}")
else:
    # Full sequence
    scene.render.filepath = str(FRAMES_DIR) + "/walk_"
    bpy.ops.render.render(animation=True)
    p(f"All {TOTAL_FRAMES} frames rendered to {FRAMES_DIR}")

p("=== DONE ===")
