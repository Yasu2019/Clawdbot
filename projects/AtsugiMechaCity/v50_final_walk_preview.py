import sys
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import argparse
import json
import math
import subprocess
from pathlib import Path

import bpy
from mathutils import Matrix, Vector


LEFT_UPPER_LEG = ["UpperLeg_L", "UpperLegCore_L"]
LEFT_LOWER_LEG = ["geometry_0.016", "geometry_0.027"]
LEFT_FOOT = ["geometry_0.013", "geometry_0.030", "geometry_0.025", "geometry_0.008"]
RIGHT_UPPER_LEG = ["UpperLeg_R", "UpperLegCore_R"]
RIGHT_LOWER_LEG = ["geometry_0.017", "geometry_0.028"]
RIGHT_FOOT = ["geometry_0.014", "geometry_0.031", "geometry_0.026", "geometry_0.029", "geometry_0.009"]
TORSO_NAMES = [
    "Torso_Core", "Pelvis_Center", "geometry_0", "geometry_0.001", "geometry_0.003",
    "geometry_0.004", "geometry_0.007", "geometry_0.010", "geometry_0.011", "geometry_0.015",
    "V50_RENDER_ShoulderSocket_L", "V50_RENDER_ShoulderSocket_R",
]
LEFT_HAND_PROXY = [
    "V50_PROXY_Hand_L_Palm", "V50_PROXY_Hand_L_Palm_Core",
    "V50_PROXY_Hand_L_Finger_A", "V50_PROXY_Hand_L_Finger_B", "V50_PROXY_Hand_L_Finger_C",
]
RIGHT_HAND_PROXY = ["geometry_0.006"]
# --- 2026-07-19 arm-fix (gate report HOLD_JOINT_DETACHMENT / INC-140系譜) ---
# 根本原因: 腕メッシュはアーマチュアに追従しておらず(ゲート実測: 全腕関節で
# マーカーと胴体/腕メッシュの距離が常時1.1〜1.4m)、腕は静的な置物だった。
# 対策: 脚と同じ実証済みパターン(剛体メッシュクラスタ+ピボット回転)を腕へ適用。
# クラスタ名は v50_joint_attachment_gate.py と同一定義(検証側と対で保守すること)。
LEFT_UPPER_ARM = ["geometry_0.012", "geometry_0.018", "geometry_0.020", "geometry_0.034"]
LEFT_LOWER_ARM = ["geometry_0.023", "geometry_0.032", "geometry_0.005"]
RIGHT_UPPER_ARM = ["geometry_0.002", "geometry_0.019", "geometry_0.021", "geometry_0.022"]
RIGHT_LOWER_ARM = ["geometry_0.024", "geometry_0.033"]
ARM_SWING_DEG = 12.0        # 肩の矢状面スイング振幅(脚11degと同程度)
ELBOW_BASE_DEG = 10.0       # 肘の常時屈曲
ELBOW_BEND_DEG = 15.0       # 肘の追加屈曲振幅
ELBOW_SIGN = -1.0           # 初回レンダーで屈曲方向が逆なら +1.0 に反転する
SHOULDER_OVERLAP = 0.03     # Xスナップ時に胴体へ食い込ませる量(見た目の密着)
HIDDEN_SOURCE_HANDS = LEFT_HAND_PROXY + RIGHT_HAND_PROXY
ARM_JOINT_MARKERS = {
    "V50_RIG_MARKER_shoulder_L": ("UpperArm_L", "head"),
    "V50_RIG_MARKER_elbow_L": ("LowerArm_L", "head"),
    "V50_RIG_MARKER_wrist_L": ("Hand_L", "head"),
    "V50_RIG_MARKER_shoulder_R": ("UpperArm_R", "head"),
    "V50_RIG_MARKER_elbow_R": ("LowerArm_R", "head"),
    "V50_RIG_MARKER_wrist_R": ("Hand_R", "head"),
}
JOINT_LOCK_OBJECT_PREFIX = "V50_PREVIEW_LOCK_"
RENDER_CONNECTOR_OBJECT_PREFIX = "V50_RENDER_"
SHOULDER_SOCKET_NAMES = ["V50_RENDER_ShoulderSocket_L", "V50_RENDER_ShoulderSocket_R"]
LEG_JOINT_LINKS = {
    "L_upper_leg": ("hip_L", "knee_L"),
    "L_lower_leg": ("knee_L", "ankle_L"),
    "R_upper_leg": ("hip_R", "knee_R"),
    "R_lower_leg": ("knee_R", "ankle_R"),
}


def parse_args():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--blend", required=True)
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--frames", type=int, default=180)
    parser.add_argument("--fps", type=int, default=24)
    parser.add_argument("--candidate-json")
    parser.add_argument("--show-joint-locks", action="store_true")
    return parser.parse_args(argv)


def all_mesh_objects():
    return [
        obj for obj in bpy.context.scene.objects
        if obj.type == "MESH" and obj.name != "Ground" and not obj.hide_render
    ]


def bounds_for(objects):
    points = []
    for obj in objects:
        if obj.type != "MESH":
            continue
        points.extend(obj.matrix_world @ Vector(corner) for corner in obj.bound_box)
    lo = Vector((min(p.x for p in points), min(p.y for p in points), min(p.z for p in points)))
    hi = Vector((max(p.x for p in points), max(p.y for p in points), max(p.z for p in points)))
    return lo, hi


def center_of(names):
    objs = [bpy.data.objects[name] for name in names if name in bpy.data.objects]
    lo, hi = bounds_for(objs)
    return (lo + hi) * 0.5


def hide_diagnostics():
    hidden = []
    for obj in bpy.context.scene.objects:
        if (
            obj.type == "ARMATURE"
            or obj.name.startswith("V50_RIG_MARKER_")
            or obj.name.endswith("_SHARED_CORE")
            or obj.name in LEFT_HAND_PROXY
            or obj.name.startswith("V50_RENDER_Hand_L_")
        ):
            obj.hide_render = True
            obj.hide_viewport = True
            hidden.append(obj.name)
    return hidden


def material(name, color):
    mat = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    mat.diffuse_color = color
    if mat.use_nodes:
        bsdf = mat.node_tree.nodes.get("Principled BSDF")
        if bsdf:
            bsdf.inputs["Base Color"].default_value = color
            bsdf.inputs["Metallic"].default_value = 0.35
            bsdf.inputs["Roughness"].default_value = 0.45
    return mat


def delete_previous_render_connectors():
    for obj in list(bpy.data.objects):
        if obj.name.startswith(RENDER_CONNECTOR_OBJECT_PREFIX):
            bpy.data.objects.remove(obj, do_unlink=True)


def create_shoulder_sockets(shoulder_pivots):
    """2026-07-19 arm-fix: ソケットはアーマチュアのbone headでなく、メッシュ由来の
    肩ピボットに生成する(アーマチュアはメッシュから~1.2m変位しており信用できない)。"""
    delete_previous_render_connectors()
    mat = material("V50_render_shoulder_socket", (0.60, 0.62, 0.64, 1.0))
    created = []
    for side in ("L", "R"):
        point = shoulder_pivots.get(side)
        if point is None:
            continue
        bpy.ops.mesh.primitive_uv_sphere_add(segments=32, ring_count=16, radius=1.0, location=point)
        obj = bpy.context.object
        obj.name = f"V50_RENDER_ShoulderSocket_{side}"
        obj.data.name = f"{obj.name}_Mesh"
        # INC-140: bake location+scale into matrix_world explicitly. Setting obj.scale
        # alone leaves matrix_world stale until a depsgraph update, and base_matrices()
        # then captures the UNSCALED matrix -> set_torso_motion() re-applies it every
        # frame and the socket renders as a giant radius-1.0 sphere.
        obj.matrix_world = (
            Matrix.Translation(point)
            @ Matrix.Diagonal((0.105, 0.070, 0.092, 1.0))
        )
        obj.data.materials.append(mat)
        obj["v50_render_role"] = "shoulder_socket_attachment_surface"
        created.append(obj.name)
    bpy.context.view_layer.update()
    return created


def create_render_connectors(shoulder_pivots):
    shoulder_sockets = create_shoulder_sockets(shoulder_pivots)
    return shoulder_sockets


# --- 2026-07-19 arm-fix: メッシュ駆動の腕チェーン ---

def cluster_objs(names):
    return [bpy.data.objects[n] for n in names if n in bpy.data.objects
            and bpy.data.objects[n].type == "MESH"]


def snap_arm_chains():
    """腕チェーン全体を胴体外側面へXスナップし、可視ギャップを閉じる(平行移動のみ)。
    戻り値: side -> 適用した平行移動量(監査用)。"""
    torso = cluster_objs([n for n in TORSO_NAMES if not n.startswith("V50_RENDER_")])
    t_lo, t_hi = bounds_for(torso)
    moved = {}
    for side, chain in (("L", LEFT_UPPER_ARM + LEFT_LOWER_ARM),
                        ("R", RIGHT_UPPER_ARM + RIGHT_LOWER_ARM + RIGHT_HAND_PROXY)):
        objs = cluster_objs(chain)
        if not objs:
            moved[side] = 0.0
            continue
        a_lo, a_hi = bounds_for(objs)
        a_cx = (a_lo.x + a_hi.x) * 0.5
        t_cx = (t_lo.x + t_hi.x) * 0.5
        if a_cx < t_cx:   # 左腕(-X側): 腕の内側面 a_hi.x を胴体 t_lo.x+overlap へ
            dx = max((t_lo.x + SHOULDER_OVERLAP) - a_hi.x, 0.0)   # 内側(+X)への移動のみ
        else:             # 右腕(+X側): 腕の内側面 a_lo.x を胴体 t_hi.x-overlap へ
            dx = min((t_hi.x - SHOULDER_OVERLAP) - a_lo.x, 0.0)   # 内側(-X)への移動のみ
        for obj in objs:
            mw = obj.matrix_world.copy()
            mw.translation = mw.translation + Vector((dx, 0.0, 0.0))
            obj.matrix_world = mw
        moved[side] = round(float(dx), 4)
    bpy.context.view_layer.update()
    return moved


def arm_pivots():
    """スナップ後のメッシュ境界から肩/肘/手首ピボットを算出(脚の leg_pivot_y と同思想)。"""
    pivots = {}
    for side, upper, lower, hand in (
        ("L", LEFT_UPPER_ARM, LEFT_LOWER_ARM, LEFT_HAND_PROXY),
        ("R", RIGHT_UPPER_ARM, RIGHT_LOWER_ARM, RIGHT_HAND_PROXY),
    ):
        u = cluster_objs(upper)
        lo_objs = cluster_objs(lower)
        if not u or not lo_objs:
            continue
        u_lo, u_hi = bounds_for(u)
        l_lo, l_hi = bounds_for(lo_objs)
        cx = (u_lo.x + u_hi.x) * 0.5
        cy = (u_lo.y + u_hi.y) * 0.5
        pivots[(side, "shoulder")] = Vector((cx, cy, u_hi.z - 0.10 * (u_hi.z - u_lo.z)))
        pivots[(side, "elbow")] = Vector((cx, (l_lo.y + l_hi.y) * 0.5, (u_lo.z + l_hi.z) * 0.5))
        h = cluster_objs(hand)
        if h:
            h_lo, h_hi = bounds_for(h)
            wz = (l_lo.z + h_hi.z) * 0.5
        else:
            wz = l_lo.z
        pivots[(side, "wrist")] = Vector((cx, (l_lo.y + l_hi.y) * 0.5, wz))
    return pivots


def set_marker_world(name, point, frame):
    marker = ensure_marker(name)
    marker.parent = None
    marker.matrix_parent_inverse.identity()
    marker.matrix_world = Matrix.Translation(point)
    marker.keyframe_insert(data_path="location", frame=frame)


def delete_previous_joint_locks():
    for obj in list(bpy.data.objects):
        if obj.name.startswith(JOINT_LOCK_OBJECT_PREFIX):
            bpy.data.objects.remove(obj, do_unlink=True)


def create_sphere(name, radius, mat):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=24, ring_count=12, radius=radius)
    obj = bpy.context.object
    obj.name = name
    obj.data.materials.append(mat)
    return obj


def create_cylinder(name, radius, mat):
    bpy.ops.mesh.primitive_cylinder_add(vertices=24, radius=radius, depth=1.0)
    obj = bpy.context.object
    obj.name = name
    obj.data.materials.append(mat)
    return obj


def place_cylinder(obj, start, end):
    direction = end - start
    length = max(float(direction.length), 0.001)
    obj.location = (start + end) * 0.5
    obj.scale = (1.0, 1.0, length)
    obj.rotation_euler = direction.to_track_quat("Z", "Y").to_euler()


def key_transform(obj, frame):
    obj.keyframe_insert(data_path="location", frame=frame)
    obj.keyframe_insert(data_path="rotation_euler", frame=frame)
    obj.keyframe_insert(data_path="scale", frame=frame)


def create_joint_locks():
    delete_previous_joint_locks()
    core_mat = material("V50_preview_joint_lock_core", (0.68, 0.68, 0.62, 1.0))
    link_mat = material("V50_preview_joint_lock_link", (0.70, 0.72, 0.72, 1.0))
    cores = {}
    links = {}
    for side in ("L", "R"):
        for joint in ("shoulder", "elbow", "wrist", "hand"):
            cores[(side, joint)] = create_sphere(
                f"{JOINT_LOCK_OBJECT_PREFIX}{side}_{joint}_core",
                0.046 if joint != "hand" else 0.070,
                core_mat,
            )
        for link in ("upper_arm", "forearm", "hand_lock"):
            links[(side, link)] = create_cylinder(
                f"{JOINT_LOCK_OBJECT_PREFIX}{side}_{link}_link",
                0.060,
                link_mat,
            )
    for side in ("L", "R"):
        for joint in ("hip", "knee", "ankle"):
            cores[(side, joint)] = create_sphere(
                f"{JOINT_LOCK_OBJECT_PREFIX}{side}_{joint}_core",
                0.045,
                core_mat,
            )
        for link in ("upper_leg", "lower_leg"):
            links[(side, link)] = create_cylinder(
                f"{JOINT_LOCK_OBJECT_PREFIX}{side}_{link}_link",
                0.060,
                link_mat,
            )
    return cores, links


def setup_camera(out_dir, frames, fps):
    out_dir = Path(out_dir).resolve()
    meshes = all_mesh_objects()
    lo, hi = bounds_for(meshes)
    center = (lo + hi) * 0.5
    size = hi - lo
    cam_data = bpy.data.cameras.new("V50_Final_Walk_Camera")
    cam = bpy.data.objects.new("V50_Final_Walk_Camera", cam_data)
    bpy.context.collection.objects.link(cam)
    cam.data.type = "ORTHO"
    # INC-140: fit the FULL body height. With the default AUTO sensor fit on a 16:9
    # frame, ortho_scale maps to the horizontal extent and crops ~40% of the robot
    # vertically (upper body off-screen). VERTICAL fit + 1.52 factor reproduces the
    # original V50 baseline framing (robot ~66% of frame height).
    cam.data.sensor_fit = "VERTICAL"
    cam.data.ortho_scale = max(float(size.z) * 1.52, 2.35)
    cam.location = center + Vector((0.0, -max(float(size.z) * 3.2, 8.5), float(size.z) * 0.20))
    direction = center + Vector((0.0, 0.0, 0.05)) - cam.location
    cam.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()
    bpy.context.scene.camera = cam

    scene = bpy.context.scene
    scene.render.engine = "BLENDER_WORKBENCH"
    scene.display.shading.light = "STUDIO"
    scene.render.resolution_x = 960
    scene.render.resolution_y = 540
    scene.frame_start = 1
    scene.frame_end = frames
    scene.render.fps = fps
    scene.render.image_settings.file_format = "PNG"
    frames_dir = out_dir / "frames"
    frames_dir.mkdir(parents=True, exist_ok=True)
    scene.render.filepath = str(frames_dir / "frame_")
    return frames_dir


def base_matrices(names):
    return {name: bpy.data.objects[name].matrix_world.copy() for name in names if name in bpy.data.objects}


def rotation_at_pivot(pivot, angle_rad, axis="X"):
    axis_vec = {
        "X": Vector((1.0, 0.0, 0.0)),
        "Y": Vector((0.0, 1.0, 0.0)),
        "Z": Vector((0.0, 0.0, 1.0)),
    }[axis]
    return Matrix.Translation(pivot) @ Matrix.Rotation(angle_rad, 4, axis_vec) @ Matrix.Translation(-pivot)


def apply_group(names, bases, pivot, angle_deg):
    transform = rotation_at_pivot(pivot, math.radians(angle_deg), "X")
    for name in names:
        obj = bpy.data.objects.get(name)
        if obj and name in bases:
            obj.matrix_world = transform @ bases[name]


def load_candidate(path):
    if not path:
        return {}
    payload = json.loads(Path(path).read_text(encoding="utf-8-sig"))
    return payload.get("candidate") or payload


def candidate_value(candidate, key, default):
    try:
        return float(candidate.get(key, default))
    except Exception:
        return float(default)


def pose_armature(armature, frame, frames, candidate):
    phase = (frame - 1) / max(frames - 1, 1)
    phase_offset = candidate_value(candidate, "phase_offset", 0.0)
    arm_scale = candidate_value(candidate, "arm_scale", 1.0)
    cycle = (phase + phase_offset) * math.tau * 2.0
    swing = math.sin(cycle)
    bend_l = (math.sin(cycle - math.pi / 3.0) + 1.0) * 0.5
    bend_r = 1.0 - bend_l
    values = {
        "UpperArm_L": (math.radians((-10.0 + 12.0 * swing) * arm_scale), 0.0, math.radians(7.0 * arm_scale)),
        "LowerArm_L": (math.radians((-18.0 - 18.0 * bend_l) * arm_scale), 0.0, 0.0),
        "Hand_L": (math.radians((-8.0 - 8.0 * bend_l) * arm_scale), 0.0, 0.0),
        "UpperArm_R": (math.radians((-10.0 - 12.0 * swing) * arm_scale), 0.0, math.radians(-7.0 * arm_scale)),
        "LowerArm_R": (math.radians((-18.0 - 18.0 * bend_r) * arm_scale), 0.0, 0.0),
        "Hand_R": (math.radians((-8.0 - 8.0 * bend_r) * arm_scale), 0.0, 0.0),
    }
    for bone in armature.pose.bones:
        bone.rotation_mode = "XYZ"
        bone.rotation_euler = (0.0, 0.0, 0.0)
    for name, euler in values.items():
        if name in armature.pose.bones:
            armature.pose.bones[name].rotation_euler = euler


def ensure_marker(name):
    obj = bpy.data.objects.get(name)
    if obj is not None:
        return obj
    bpy.ops.object.empty_add(type="SPHERE", location=(0.0, 0.0, 0.0))
    obj = bpy.context.object
    obj.name = name
    obj.empty_display_size = 0.04
    return obj


def update_arm_joint_markers(armature, frame):
    bpy.context.view_layer.update()
    for marker_name, (bone_name, endpoint) in ARM_JOINT_MARKERS.items():
        pose_bone = armature.pose.bones.get(bone_name)
        if pose_bone is None:
            continue
        local_point = pose_bone.head if endpoint == "head" else pose_bone.tail
        marker = ensure_marker(marker_name)
        marker.parent = None
        marker.matrix_parent_inverse.identity()
        marker.matrix_world = Matrix.Translation(armature.matrix_world @ local_point)
        marker.keyframe_insert(data_path="location", frame=frame)


def hand_proxy_offsets():
    """2026-07-19 arm-fix: アーマチュア非依存。プロキシ群のクラスタ中心からの相対
    オフセットのみ保持し、配置はメッシュ由来の手首ピボットに追従させる。"""
    objs = [bpy.data.objects[name] for name in LEFT_HAND_PROXY if bpy.data.objects.get(name)]
    if not objs:
        return {}
    lo, hi = bounds_for(objs)
    center = (lo + hi) * 0.5
    offsets = {}
    for obj in objs:
        offsets[obj.name] = obj.matrix_world.translation - center
    return offsets


def update_left_hand_proxy(wrist_world, offsets, frame):
    if wrist_world is None:
        return
    target_center = wrist_world + Vector((0.0, 0.0, -0.055))
    for name, offset in offsets.items():
        obj = bpy.data.objects.get(name)
        if obj is None:
            continue
        # INC-140: proxies are parented (to geometry_0.005), so .location is in
        # PARENT space. Writing world coordinates into it displaced the proxies.
        # Set the world translation via matrix_world, then key the resulting local
        # location.
        mw = obj.matrix_world.copy()
        mw.translation = target_center + offset
        obj.matrix_world = mw
        obj.keyframe_insert(data_path="location", frame=frame)


def bone_point(armature, bone_name, endpoint="head"):
    pose_bone = armature.pose.bones.get(bone_name)
    if pose_bone is None:
        return None
    local_point = pose_bone.head if endpoint == "head" else pose_bone.tail
    return armature.matrix_world @ local_point


def safe_center(names):
    objs = [bpy.data.objects[name] for name in names if name in bpy.data.objects]
    if not objs:
        return None
    lo, hi = bounds_for(objs)
    return (lo + hi) * 0.5


def update_visible_joint_locks(arm_points, cores, links, pivots, frame):
    """2026-07-19 arm-fix: 腕関節点はアーマチュアでなくメッシュ駆動FKの計算点を使う。"""
    bpy.context.view_layer.update()
    points = {
        "L": {
            "shoulder": arm_points.get(("L", "shoulder")),
            "elbow": arm_points.get(("L", "elbow")),
            "wrist": arm_points.get(("L", "wrist")),
            "hand": safe_center(LEFT_HAND_PROXY),
            "hip": pivots["hip_L"],
            "knee": pivots["knee_L"],
            "ankle": pivots["ankle_L"],
        },
        "R": {
            "shoulder": arm_points.get(("R", "shoulder")),
            "elbow": arm_points.get(("R", "elbow")),
            "wrist": arm_points.get(("R", "wrist")),
            "hand": safe_center(["geometry_0.006"]),
            "hip": pivots["hip_R"],
            "knee": pivots["knee_R"],
            "ankle": pivots["ankle_R"],
        },
    }
    for side, side_points in points.items():
        for joint, point in side_points.items():
            core = cores.get((side, joint))
            if core is None or point is None:
                continue
            core.location = point
            core.rotation_euler = (0.0, 0.0, 0.0)
            core.scale = (1.0, 1.0, 1.0)
            key_transform(core, frame)
        arm_link_points = {
            "upper_arm": ("shoulder", "elbow"),
            "forearm": ("elbow", "wrist"),
            "hand_lock": ("wrist", "hand"),
            "upper_leg": ("hip", "knee"),
            "lower_leg": ("knee", "ankle"),
        }
        for link, (start_key, end_key) in arm_link_points.items():
            start = side_points.get(start_key)
            end = side_points.get(end_key)
            obj = links.get((side, link))
            if obj is None or start is None or end is None:
                continue
            place_cylinder(obj, start, end)
            key_transform(obj, frame)


def set_torso_motion(torso_bases, frame, frames, torso_center):
    """2026-07-19 arm-fix: 変換行列を返す(腕チェーンが胴体に追従合成するため)。
    torso_center は rest時に一度だけ算出した固定値を渡す(毎フレーム再計算だと
    直前フレームの変換が混入してドリフトする)。"""
    phase = (frame - 1) / max(frames - 1, 1)
    bob = 0.040 * (0.5 - 0.5 * math.cos(phase * math.tau * 4.0))
    sway = math.radians(1.8) * math.sin(phase * math.tau * 2.0)
    transform = Matrix.Translation((0.0, 0.0, bob)) @ rotation_at_pivot(torso_center, sway, "Z")
    for name, base in torso_bases.items():
        obj = bpy.data.objects.get(name)
        if obj:
            obj.matrix_world = transform @ base
    return transform


def animate(frames, candidate, show_joint_locks: bool):
    # 2026-07-19 arm-fix: アーマチュアは任意(腕はメッシュ駆動FKへ移行)。
    armature = bpy.data.objects.get("V50_Generic_Armature")
    arm_snap = snap_arm_chains()
    ap = arm_pivots()
    shoulder_pivots = {s: ap.get((s, "shoulder")) for s in ("L", "R")}
    render_connectors = create_render_connectors(shoulder_pivots)
    leg_names = LEFT_UPPER_LEG + LEFT_LOWER_LEG + LEFT_FOOT + RIGHT_UPPER_LEG + RIGHT_LOWER_LEG + RIGHT_FOOT
    leg_bases = base_matrices(leg_names)
    torso_bases = base_matrices(TORSO_NAMES)
    arm_names = (LEFT_UPPER_ARM + LEFT_LOWER_ARM + RIGHT_UPPER_ARM
                 + RIGHT_LOWER_ARM + RIGHT_HAND_PROXY)
    arm_bases = base_matrices(arm_names)
    torso_center_rest = center_of([n for n in TORSO_NAMES if n in bpy.data.objects])
    hand_offsets = hand_proxy_offsets()
    lock_cores, lock_links = ({}, {})
    if show_joint_locks:
        lock_cores, lock_links = create_joint_locks()
    # INC-140: pivot depth (Y) is derived per joint from the adjacent segment
    # clusters instead of a single flattened torso Y. After restoring the original
    # stride pose (legs staggered in depth), a torso-Y axis line sits up to 0.5 in
    # front of the real joint and produces wrong swing arcs.
    def leg_pivot_y(parent_names, child_names):
        return (center_of(parent_names).y + center_of(child_names).y) * 0.5

    pivots = {
        "hip_L": Vector((-0.20, leg_pivot_y(TORSO_NAMES, LEFT_UPPER_LEG), 0.02)),
        "knee_L": Vector((-0.24, leg_pivot_y(LEFT_UPPER_LEG, LEFT_LOWER_LEG), -0.50)),
        "ankle_L": Vector((-0.25, leg_pivot_y(LEFT_LOWER_LEG, LEFT_FOOT), -0.88)),
        "hip_R": Vector((0.22, leg_pivot_y(TORSO_NAMES, RIGHT_UPPER_LEG), 0.02)),
        "knee_R": Vector((0.25, leg_pivot_y(RIGHT_UPPER_LEG, RIGHT_LOWER_LEG), -0.50)),
        "ankle_R": Vector((0.26, leg_pivot_y(RIGHT_LOWER_LEG, RIGHT_FOOT), -0.88)),
    }

    frame_audits = []
    hip_scale = candidate_value(candidate, "hip_scale", 1.0)
    knee_scale = candidate_value(candidate, "knee_scale", 1.0)
    ankle_scale = candidate_value(candidate, "ankle_scale", 1.0)
    phase_offset = candidate_value(candidate, "phase_offset", 0.0)
    for frame in range(1, frames + 1):
        phase = (frame - 1) / max(frames - 1, 1)
        cycle = (phase + phase_offset) * math.tau * 2.0
        swing_l = 11.0 * hip_scale * math.sin(cycle)
        swing_r = -11.0 * hip_scale * math.sin(cycle)
        knee_l = 10.0 * knee_scale * max(0.0, -math.sin(cycle))
        knee_r = 10.0 * knee_scale * max(0.0, math.sin(cycle))
        foot_l = -5.0 * ankle_scale * max(0.0, -math.sin(cycle))
        foot_r = -5.0 * ankle_scale * max(0.0, math.sin(cycle))

        bpy.context.scene.frame_set(frame)
        t_torso = set_torso_motion(torso_bases, frame, frames, torso_center_rest)
        apply_group(LEFT_UPPER_LEG + LEFT_LOWER_LEG + LEFT_FOOT, leg_bases, pivots["hip_L"], swing_l)
        apply_group(LEFT_LOWER_LEG + LEFT_FOOT, leg_bases, pivots["knee_L"], knee_l)
        apply_group(LEFT_FOOT, leg_bases, pivots["ankle_L"], foot_l)
        apply_group(RIGHT_UPPER_LEG + RIGHT_LOWER_LEG + RIGHT_FOOT, leg_bases, pivots["hip_R"], swing_r)
        apply_group(RIGHT_LOWER_LEG + RIGHT_FOOT, leg_bases, pivots["knee_R"], knee_r)
        apply_group(RIGHT_FOOT, leg_bases, pivots["ankle_R"], foot_r)

        # --- 2026-07-19 arm-fix: メッシュ駆動FK(胴体変換に合成、脚と同パターン) ---
        arm_scale = candidate_value(candidate, "arm_scale", 1.0)
        swing = math.sin(cycle)
        arm_points = {}
        for side, upper, lower, sgn, bend in (
            ("L", LEFT_UPPER_ARM, LEFT_LOWER_ARM, -1.0,
             (math.sin(cycle - math.pi / 3.0) + 1.0) * 0.5),
            ("R", RIGHT_UPPER_ARM, RIGHT_LOWER_ARM, 1.0,
             1.0 - (math.sin(cycle - math.pi / 3.0) + 1.0) * 0.5),
        ):
            p_sh = ap.get((side, "shoulder"))
            p_el = ap.get((side, "elbow"))
            p_wr = ap.get((side, "wrist"))
            if p_sh is None or p_el is None:
                continue
            ang_sh = math.radians(sgn * ARM_SWING_DEG * arm_scale) * swing
            ang_el = math.radians(ELBOW_SIGN * (ELBOW_BASE_DEG + ELBOW_BEND_DEG * bend) * arm_scale)
            t_sh = t_torso @ rotation_at_pivot(p_sh, ang_sh, "X")
            t_el = t_sh @ rotation_at_pivot(p_el, ang_el, "X")
            for name in upper:
                obj = bpy.data.objects.get(name)
                if obj and name in arm_bases:
                    obj.matrix_world = t_sh @ arm_bases[name]
            for name in lower:
                obj = bpy.data.objects.get(name)
                if obj and name in arm_bases:
                    obj.matrix_world = t_el @ arm_bases[name]
            arm_points[(side, "shoulder")] = t_torso @ p_sh
            arm_points[(side, "elbow")] = t_sh @ p_el
            arm_points[(side, "wrist")] = (t_el @ p_wr) if p_wr is not None else None
        # 右手メッシュは前腕に剛体追従(手首の追加回転は無し=分離リスク最小)
        for name in RIGHT_HAND_PROXY:
            obj = bpy.data.objects.get(name)
            if obj and name in arm_bases and ("R", "elbow") in arm_points:
                p_el = ap.get(("R", "elbow"))
                ang_el = math.radians(ELBOW_SIGN * (ELBOW_BASE_DEG + ELBOW_BEND_DEG
                          * (1.0 - (math.sin(cycle - math.pi / 3.0) + 1.0) * 0.5)) * arm_scale)
                t_sh = t_torso @ rotation_at_pivot(ap[("R", "shoulder")],
                        math.radians(1.0 * ARM_SWING_DEG * arm_scale) * swing, "X")
                obj.matrix_world = (t_sh @ rotation_at_pivot(p_el, ang_el, "X")) @ arm_bases[name]

        # ゲート用マーカーはメッシュ由来FK点に配置(アーマチュア非依存)
        for (side, joint), point in arm_points.items():
            if point is not None:
                set_marker_world(f"V50_RIG_MARKER_{joint}_{side}", point, frame)
        if armature is not None:
            pose_armature(armature, frame, frames, candidate)
        update_left_hand_proxy(arm_points.get(("L", "wrist")), hand_offsets, frame)
        if show_joint_locks:
            update_visible_joint_locks(arm_points, lock_cores, lock_links, pivots, frame)
        bpy.context.view_layer.update()

        lock_names = [obj.name for obj in list(lock_cores.values()) + list(lock_links.values())] if show_joint_locks else []
        for name in set(leg_names + TORSO_NAMES + arm_names + HIDDEN_SOURCE_HANDS + lock_names + render_connectors):
            obj = bpy.data.objects.get(name)
            if obj:
                obj.keyframe_insert(data_path="location", frame=frame)
                obj.keyframe_insert(data_path="rotation_euler", frame=frame)
                obj.keyframe_insert(data_path="scale", frame=frame)
        if armature is not None:
            for bone in armature.pose.bones:
                bone.keyframe_insert(data_path="rotation_euler", frame=frame)
        lo, hi = bounds_for(all_mesh_objects())
        frame_audits.append({
            "frame": frame,
            "bounds_min": [round(float(lo[i]), 6) for i in range(3)],
            "bounds_max": [round(float(hi[i]), 6) for i in range(3)],
        })
    return frame_audits, render_connectors, arm_snap


def encode_mp4(out_dir, frames_dir, fps):
    out_dir = Path(out_dir).resolve()
    frames_dir = Path(frames_dir).resolve()
    mp4 = out_dir / "v50_fullbody_normalized_final_walk_preview.mp4"
    cmd = [
        "ffmpeg", "-y", "-framerate", str(fps), "-i", str(frames_dir / "frame_%04d.png"),
        "-c:v", "libx264", "-pix_fmt", "yuv420p", str(mp4.resolve()),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        (out_dir / "ffmpeg_error.txt").write_text((result.stdout or "") + "\n" + (result.stderr or ""), encoding="utf-8")
        return None, result.returncode
    return mp4, result.returncode


def main():
    args = parse_args()
    out_dir = Path(args.out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    candidate = load_candidate(args.candidate_json)
    bpy.ops.wm.open_mainfile(filepath=str(Path(args.blend)))
    hidden = hide_diagnostics()
    frames_dir = setup_camera(out_dir, args.frames, args.fps)
    frame_audits, render_connectors, arm_snap = animate(args.frames, candidate, args.show_joint_locks)
    bpy.ops.wm.save_as_mainfile(filepath=str(out_dir / "v50_final_walk_preview.blend"))
    bpy.ops.render.render(animation=True)
    mp4, ffmpeg_returncode = encode_mp4(out_dir, frames_dir, args.fps)
    report = {
        "schema": "clawstack.v50_final_walk_preview.v1",
        "source_blend": str(Path(args.blend)),
        "out_blend": str(out_dir / "v50_final_walk_preview.blend"),
        "mp4": str(mp4) if mp4 else None,
        "frames_dir": str(frames_dir),
        "frames": args.frames,
        "fps": args.fps,
        "ffmpeg_returncode": ffmpeg_returncode,
        "hidden_diagnostics": hidden,
        "render_connectors": render_connectors,
        "method": "candidate-scaled rigid-object pivots for legs AND arms (mesh-driven FK, arm-fix 2026-07-19)",
        "arm_snap_dx": arm_snap,
        "candidate": candidate,
        "frame_audits": frame_audits,
    }
    (out_dir / "v50_final_walk_preview_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
