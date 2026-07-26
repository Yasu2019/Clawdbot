import sys
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import argparse
import json
from pathlib import Path

import bpy
from mathutils import Matrix


MAPPING = [
    ("Hips", "mixamorig:Hips"),
    ("Spine", "mixamorig:Spine"),
    ("Chest", "mixamorig:Spine2"),
    ("Neck", "mixamorig:Neck"),
    ("Head", "mixamorig:Head"),
    ("Shoulder.L", "mixamorig:LeftShoulder"),
    ("UpperArm.L", "mixamorig:LeftArm"),
    ("LowerArm.L", "mixamorig:LeftForeArm"),
    ("Hand.L", "mixamorig:LeftHand"),
    ("Shoulder.R", "mixamorig:RightShoulder"),
    ("UpperArm.R", "mixamorig:RightArm"),
    ("LowerArm.R", "mixamorig:RightForeArm"),
    ("Hand.R", "mixamorig:RightHand"),
    ("UpperLeg.L", "mixamorig:LeftUpLeg"),
    ("LowerLeg.L", "mixamorig:LeftLeg"),
    ("Foot.L", "mixamorig:LeftFoot"),
    ("UpperLeg.R", "mixamorig:RightUpLeg"),
    ("LowerLeg.R", "mixamorig:RightLeg"),
    ("Foot.R", "mixamorig:RightFoot"),
]


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--target-blend", required=True)
    parser.add_argument("--idle", required=True)
    parser.add_argument("--walking", required=True)
    parser.add_argument("--talking", required=True)
    parser.add_argument("--output-dir", required=True)
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    return parser.parse_args(argv)


def target_rig():
    rigs = [
        obj for obj in bpy.context.scene.objects
        if obj.type == "ARMATURE" and obj.name == "CommercialAnimeHumanoid"
    ]
    if len(rigs) != 1:
        raise RuntimeError(f"Expected one target rig, found {len(rigs)}")
    return rigs[0]


def import_source(path):
    before = set(bpy.data.objects)
    before_actions = set(bpy.data.actions)
    bpy.ops.import_scene.fbx(filepath=str(path), use_anim=True)
    imported = [obj for obj in bpy.data.objects if obj not in before]
    rigs = [obj for obj in imported if obj.type == "ARMATURE"]
    actions = [action for action in bpy.data.actions if action not in before_actions]
    if len(rigs) != 1 or len(actions) != 1:
        raise RuntimeError(
            f"{path.name}: expected one rig/action, got {len(rigs)}/{len(actions)}"
        )
    return rigs[0], actions[0], imported


def clear_pose(rig):
    bpy.context.view_layer.objects.active = rig
    bpy.ops.object.mode_set(mode="POSE")
    for bone in rig.pose.bones:
        bone.matrix_basis.identity()
    bpy.ops.object.mode_set(mode="OBJECT")
    bpy.context.view_layer.update()


def retarget_action(rig, source_rig, source_action, name):
    scene = bpy.context.scene
    start = int(source_action.frame_range[0])
    end = int(source_action.frame_range[1])
    source_rig.animation_data_create()
    source_rig.animation_data.action = source_action
    clear_pose(rig)
    rig.animation_data_create()
    rig.animation_data.action = None
    action = bpy.data.actions.new(name=f"Heroine_{name}")
    action.use_fake_user = True
    rig.animation_data.action = action
    scene.frame_start = start
    scene.frame_end = end
    scene.frame_set(start)
    bpy.context.view_layer.update()
    source_baselines = {
        source_name: source_rig.pose.bones[source_name].matrix_basis.to_quaternion()
        for _, source_name in MAPPING
        if source_name in source_rig.pose.bones
    }

    for frame in range(start, end + 1):
        scene.frame_set(frame)
        bpy.context.view_layer.update()
        for target_name, source_name in MAPPING:
            source_bone = source_rig.pose.bones.get(source_name)
            target_bone = rig.pose.bones.get(target_name)
            if source_bone is None or target_bone is None:
                continue
            source_rest = source_rig.data.bones[source_name].matrix_local
            target_rest = rig.data.bones[target_name].matrix_local
            target_bone.rotation_mode = "QUATERNION"
            source_basis = (
                source_bone.matrix_basis.to_quaternion()
                @ source_baselines[source_name].inverted()
            )
            source_rest_rotation = source_rest.to_quaternion()
            target_rest_rotation = target_rest.to_quaternion()
            armature_space_delta = (
                source_rest_rotation
                @ source_basis
                @ source_rest_rotation.inverted()
            )
            target_bone.rotation_quaternion = (
                target_rest_rotation.inverted()
                @ armature_space_delta
                @ target_rest_rotation
            )
            target_bone.keyframe_insert(
                data_path="rotation_quaternion", frame=frame, group=target_name
            )
            if target_name == "Hips":
                target_bone.location = (0.0, 0.0, 0.0)
                target_bone.keyframe_insert(
                    data_path="location", frame=frame, group=target_name
                )
        bpy.context.view_layer.update()
    action["source_fbx"] = str(source_action.name)
    action["in_place"] = True
    action["source_frame_range"] = [start, end]
    rig.animation_data.action = None
    clear_pose(rig)
    return action, start, end


def remove_imported(imported, source_action):
    for obj in imported:
        if obj.animation_data:
            obj.animation_data.action = None
    for obj in imported:
        bpy.data.objects.remove(obj, do_unlink=True)
    if source_action.name in bpy.data.actions:
        bpy.data.actions.remove(source_action)


def render_action(rig, action, frame, path):
    rig.animation_data.action = action
    bpy.context.scene.frame_set(frame)
    bpy.context.view_layer.update()
    bpy.context.scene.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)
    rig.animation_data.action = None
    clear_pose(rig)


def export_assets(rig, output_dir, actions):
    character = bpy.data.objects.get("OriginalAdultHeroine_Commercial")
    if character is None:
        raise RuntimeError("Target character mesh missing")
    blend_path = output_dir / "commercial_heroine_v23_mixamo3.blend"
    glb_path = output_dir / "commercial_heroine_v23_mixamo3.glb"
    fbx_path = output_dir / "commercial_heroine_v23_mixamo3.fbx"
    for action in actions:
        action.use_fake_user = True
    bpy.ops.wm.save_as_mainfile(filepath=str(blend_path))
    bpy.ops.object.select_all(action="DESELECT")
    character.select_set(True)
    rig.select_set(True)
    bpy.context.view_layer.objects.active = rig
    bpy.ops.export_scene.gltf(
        filepath=str(glb_path),
        export_format="GLB",
        use_selection=True,
        export_skins=True,
        export_animations=True,
        export_animation_mode="ACTIONS",
        export_yup=True,
    )
    bpy.ops.export_scene.fbx(
        filepath=str(fbx_path),
        use_selection=True,
        object_types={"ARMATURE", "MESH"},
        add_leaf_bones=False,
        bake_anim=True,
        bake_anim_use_all_actions=True,
        axis_forward="-Z",
        axis_up="Y",
    )
    return blend_path, glb_path, fbx_path


def main():
    args = parse_args()
    output_dir = Path(args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.open_mainfile(filepath=str(Path(args.target_blend).resolve()))
    rig = target_rig()
    sources = [
        ("Idle", Path(args.idle).resolve()),
        ("Walking", Path(args.walking).resolve()),
        ("Talking", Path(args.talking).resolve()),
    ]
    actions = []
    details = []
    for name, path in sources:
        source_rig, source_action, imported = import_source(path)
        action, start, end = retarget_action(
            rig, source_rig, source_action, name
        )
        actions.append(action)
        remove_imported(imported, source_action)
        preview_path = output_dir / f"commercial_heroine_v23_{name.lower()}_preview.png"
        render_action(rig, action, (start + end) // 2, preview_path)
        details.append({
            "name": name,
            "source": str(path),
            "frames": [start, end],
            "preview": str(preview_path),
            "mapped_bones": len(MAPPING),
        })
    for action in list(bpy.data.actions):
        if not action.name.startswith("Heroine_"):
            bpy.data.actions.remove(action)
    bpy.ops.outliner.orphans_purge(do_recursive=True)
    blend_path, glb_path, fbx_path = export_assets(rig, output_dir, actions)
    report = {
        "target": str(Path(args.target_blend).resolve()),
        "animations": details,
        "action_count": len(actions),
        "outputs": {
            "blend": str(blend_path),
            "glb": str(glb_path),
            "fbx": str(fbx_path),
        },
        "quality_gate": "PENDING_VISUAL_AND_REIMPORT_QA",
    }
    report_path = output_dir / "commercial_heroine_v23_mixamo3_report.json"
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
