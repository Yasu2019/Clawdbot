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


def create_shoulder_sockets(armature):
    delete_previous_render_connectors()
    mat = material("V50_render_shoulder_socket", (0.60, 0.62, 0.64, 1.0))
    created = []
    for side, bone_name in (("L", "UpperArm_L"), ("R", "UpperArm_R")):
        point = bone_point(armature, bone_name, "head")
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


def create_render_connectors(armature):
    shoulder_sockets = create_shoulder_sockets(armature)
    return shoulder_sockets


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


def hand_proxy_offsets(armature):
    pose_bone = armature.pose.bones.get("Hand_L")
    if pose_bone is None:
        return {}
    objs = [bpy.data.objects[name] for name in LEFT_HAND_PROXY if bpy.data.objects.get(name)]
    if not objs:
        return {}
    lo, hi = bounds_for(objs)
    center = (lo + hi) * 0.5
    offsets = {}
    for obj in objs:
        offsets[obj.name] = obj.matrix_world.translation - center
    return offsets


def update_left_hand_proxy(armature, offsets, frame):
    pose_bone = armature.pose.bones.get("Hand_L")
    if pose_bone is None:
        return
    wrist_world = armature.matrix_world @ pose_bone.head
    target_center = wrist_world + Vector((-0.055, 0.0, -0.025))
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


def update_visible_joint_locks(armature, cores, links, pivots, frame):
    bpy.context.view_layer.update()
    points = {
        "L": {
            "shoulder": bone_point(armature, "UpperArm_L", "head"),
            "elbow": bone_point(armature, "LowerArm_L", "head"),
            "wrist": bone_point(armature, "Hand_L", "head"),
            "hand": safe_center(LEFT_HAND_PROXY),
            "hip": pivots["hip_L"],
            "knee": pivots["knee_L"],
            "ankle": pivots["ankle_L"],
        },
        "R": {
            "shoulder": bone_point(armature, "UpperArm_R", "head"),
            "elbow": bone_point(armature, "LowerArm_R", "head"),
            "wrist": bone_point(armature, "Hand_R", "head"),
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


def set_torso_motion(torso_bases, frame, frames):
    phase = (frame - 1) / max(frames - 1, 1)
    bob = 0.040 * (0.5 - 0.5 * math.cos(phase * math.tau * 4.0))
    sway = math.radians(1.8) * math.sin(phase * math.tau * 2.0)
    torso_center = center_of([name for name in TORSO_NAMES if name in bpy.data.objects])
    transform = Matrix.Translation((0.0, 0.0, bob)) @ rotation_at_pivot(torso_center, sway, "Z")
    for name, base in torso_bases.items():
        obj = bpy.data.objects.get(name)
        if obj:
            obj.matrix_world = transform @ base


def animate(frames, candidate, show_joint_locks: bool):
    armature = bpy.data.objects.get("V50_Generic_Armature")
    if armature is None:
        raise RuntimeError("V50_Generic_Armature not found")
    render_connectors = create_render_connectors(armature)
    leg_names = LEFT_UPPER_LEG + LEFT_LOWER_LEG + LEFT_FOOT + RIGHT_UPPER_LEG + RIGHT_LOWER_LEG + RIGHT_FOOT
    leg_bases = base_matrices(leg_names)
    torso_bases = base_matrices(TORSO_NAMES)
    hand_offsets = hand_proxy_offsets(armature)
    lock_cores, lock_links = ({}, {})
    if show_joint_locks:
        lock_cores, lock_links = create_joint_locks()
    y = center_of(TORSO_NAMES).y
    pivots = {
        "hip_L": Vector((-0.20, y, 0.02)),
        "knee_L": Vector((-0.24, y, -0.50)),
        "ankle_L": Vector((-0.25, y, -0.88)),
        "hip_R": Vector((0.22, y, 0.02)),
        "knee_R": Vector((0.25, y, -0.50)),
        "ankle_R": Vector((0.26, y, -0.88)),
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
        set_torso_motion(torso_bases, frame, frames)
        apply_group(LEFT_UPPER_LEG + LEFT_LOWER_LEG + LEFT_FOOT, leg_bases, pivots["hip_L"], swing_l)
        apply_group(LEFT_LOWER_LEG + LEFT_FOOT, leg_bases, pivots["knee_L"], knee_l)
        apply_group(LEFT_FOOT, leg_bases, pivots["ankle_L"], foot_l)
        apply_group(RIGHT_UPPER_LEG + RIGHT_LOWER_LEG + RIGHT_FOOT, leg_bases, pivots["hip_R"], swing_r)
        apply_group(RIGHT_LOWER_LEG + RIGHT_FOOT, leg_bases, pivots["knee_R"], knee_r)
        apply_group(RIGHT_FOOT, leg_bases, pivots["ankle_R"], foot_r)
        pose_armature(armature, frame, frames, candidate)
        update_arm_joint_markers(armature, frame)
        update_left_hand_proxy(armature, hand_offsets, frame)
        if show_joint_locks:
            update_visible_joint_locks(armature, lock_cores, lock_links, pivots, frame)
        bpy.context.view_layer.update()

        lock_names = [obj.name for obj in list(lock_cores.values()) + list(lock_links.values())] if show_joint_locks else []
        for name in set(leg_names + TORSO_NAMES + HIDDEN_SOURCE_HANDS + lock_names + render_connectors):
            obj = bpy.data.objects.get(name)
            if obj:
                obj.keyframe_insert(data_path="location", frame=frame)
                obj.keyframe_insert(data_path="rotation_euler", frame=frame)
                obj.keyframe_insert(data_path="scale", frame=frame)
        for bone in armature.pose.bones:
            bone.keyframe_insert(data_path="rotation_euler", frame=frame)
        lo, hi = bounds_for(all_mesh_objects())
        frame_audits.append({
            "frame": frame,
            "bounds_min": [round(float(lo[i]), 6) for i in range(3)],
            "bounds_max": [round(float(hi[i]), 6) for i in range(3)],
        })
    return frame_audits, render_connectors


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
    frame_audits, render_connectors = animate(args.frames, candidate, args.show_joint_locks)
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
        "method": "candidate-scaled rigid-object leg pivots plus existing armature arms",
        "candidate": candidate,
        "frame_audits": frame_audits,
    }
    (out_dir / "v50_final_walk_preview_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
