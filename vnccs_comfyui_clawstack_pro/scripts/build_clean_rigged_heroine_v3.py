import sys
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import argparse
import json
import math
from pathlib import Path

import bpy
from mathutils import Vector


def material(name, color, metallic=0.0, roughness=0.5):
    mat = bpy.data.materials.new(name)
    mat.diffuse_color = (*color, 1.0)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = (*color, 1.0)
    bsdf.inputs["Metallic"].default_value = metallic
    bsdf.inputs["Roughness"].default_value = roughness
    return mat


def smooth(obj, bevel=0.0):
    for polygon in obj.data.polygons:
        polygon.use_smooth = True
    if bevel:
        mod = obj.modifiers.new("EdgeSoftening", "BEVEL")
        mod.width = bevel
        mod.segments = 2
    return obj


def sphere(name, location, scale, mat):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=32, ring_count=20, location=location)
    obj = bpy.context.object
    obj.name = name
    obj.scale = scale
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    obj.data.materials.append(mat)
    return smooth(obj)


def cube(name, location, scale, mat, bevel=0.04):
    bpy.ops.mesh.primitive_cube_add(location=location)
    obj = bpy.context.object
    obj.name = name
    obj.scale = scale
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    obj.data.materials.append(mat)
    return smooth(obj, bevel)


def cylinder_between(name, start, end, radius, mat):
    start, end = Vector(start), Vector(end)
    delta = end - start
    bpy.ops.mesh.primitive_cylinder_add(vertices=24, radius=radius, depth=delta.length,
                                       location=(start + end) * 0.5)
    obj = bpy.context.object
    obj.name = name
    obj.rotation_mode = "QUATERNION"
    obj.rotation_quaternion = Vector((0, 0, 1)).rotation_difference(delta.normalized())
    obj.data.materials.append(mat)
    return smooth(obj, radius * 0.15)


def cone(name, location, radii, depth, mat):
    bpy.ops.mesh.primitive_cone_add(vertices=40, radius1=radii[0], radius2=radii[1],
                                   depth=depth, location=location)
    obj = bpy.context.object
    obj.name = name
    obj.data.materials.append(mat)
    return smooth(obj, 0.018)


def make_rig():
    bpy.ops.object.armature_add(enter_editmode=True, location=(0, 0, 0))
    rig = bpy.context.object
    rig.name = "OriginalHeroine_Rig"
    arm = rig.data
    arm.name = rig.name
    arm.edit_bones.remove(arm.edit_bones[0])
    bones = {
        "Hips": ((0, 0, 0.88), (0, 0, 1.00), None),
        "Spine": ((0, 0, 0.96), (0, 0, 1.15), "Hips"),
        "Chest": ((0, 0, 1.12), (0, 0, 1.37), "Spine"),
        "Neck": ((0, 0, 1.34), (0, 0, 1.43), "Chest"),
        "Head": ((0, 0, 1.42), (0, 0, 1.67), "Neck"),
        "Shoulder.L": ((0.04, 0, 1.34), (0.18, 0, 1.33), "Chest"),
        "UpperArm.L": ((0.18, 0, 1.33), (0.36, 0, 1.14), "Shoulder.L"),
        "LowerArm.L": ((0.36, 0, 1.14), (0.43, 0, 0.93), "UpperArm.L"),
        "Hand.L": ((0.43, 0, 0.93), (0.45, -0.01, 0.84), "LowerArm.L"),
        "Shoulder.R": ((-0.04, 0, 1.34), (-0.18, 0, 1.33), "Chest"),
        "UpperArm.R": ((-0.18, 0, 1.33), (-0.36, 0, 1.14), "Shoulder.R"),
        "LowerArm.R": ((-0.36, 0, 1.14), (-0.43, 0, 0.93), "UpperArm.R"),
        "Hand.R": ((-0.43, 0, 0.93), (-0.45, -0.01, 0.84), "LowerArm.R"),
        "UpperLeg.L": ((0.10, 0, 0.91), (0.11, 0, 0.53), "Hips"),
        "LowerLeg.L": ((0.11, 0, 0.53), (0.11, 0, 0.19), "UpperLeg.L"),
        "Foot.L": ((0.11, 0, 0.19), (0.11, -0.16, 0.08), "LowerLeg.L"),
        "UpperLeg.R": ((-0.10, 0, 0.91), (-0.11, 0, 0.53), "Hips"),
        "LowerLeg.R": ((-0.11, 0, 0.53), (-0.11, 0, 0.19), "UpperLeg.R"),
        "Foot.R": ((-0.11, 0, 0.19), (-0.11, -0.16, 0.08), "LowerLeg.R"),
    }
    for name, (head, tail, parent) in bones.items():
        bone = arm.edit_bones.new(name)
        bone.head, bone.tail = head, tail
        if parent:
            bone.parent = arm.edit_bones[parent]
    bpy.ops.object.mode_set(mode="OBJECT")
    rig.show_in_front = True
    return rig


def bind(obj, rig, bone_name):
    group = obj.vertex_groups.new(name=bone_name)
    group.add(list(range(len(obj.data.vertices))), 1.0, "REPLACE")
    mod = obj.modifiers.new("Rig", "ARMATURE")
    mod.object = rig
    obj.parent = rig


def build_character(rig):
    skin = material("Skin", (0.93, 0.66, 0.55), roughness=0.56)
    hair = material("ChestnutHair", (0.12, 0.045, 0.028), roughness=0.32)
    white = material("IvoryJacket", (0.82, 0.86, 0.88), metallic=0.05, roughness=0.4)
    teal = material("TealTop", (0.025, 0.30, 0.34), metallic=0.08, roughness=0.42)
    charcoal = material("CharcoalSkirt", (0.025, 0.030, 0.045), roughness=0.48)
    tights = material("Tights", (0.018, 0.022, 0.034), roughness=0.62)
    leather = material("BrownLeather", (0.16, 0.055, 0.025), metallic=0.12, roughness=0.32)
    eye_white = material("EyeWhite", (0.92, 0.94, 0.96), roughness=0.3)
    amber = material("AmberEye", (0.75, 0.28, 0.035), metallic=0.05, roughness=0.22)
    accent = material("HairClip", (0.05, 0.75, 0.78), metallic=0.2, roughness=0.3)
    pieces = []

    pieces += [(sphere("Head", (0, -0.020, 1.54), (0.125, 0.105, 0.155), skin), "Head")]
    pieces += [(sphere("HairCap", (0, 0.035, 1.575), (0.145, 0.125, 0.175), hair), "Head")]
    for x, tilt in ((-0.105, -1), (-0.065, -1), (0.065, 1), (0.105, 1)):
        bpy.ops.mesh.primitive_cone_add(vertices=20, radius1=0.017, radius2=0.029,
                                       depth=0.205, location=(x, -0.108, 1.53),
                                       rotation=(0, math.radians(tilt * 8), 0))
        lock = bpy.context.object
        lock.name = "TaperedHairLock"
        lock.data.materials.append(hair)
        pieces.append((smooth(lock, 0.006), "Head"))
    for x in (-0.055, 0.055):
        pieces.append((sphere("EyeWhite", (x, -0.119, 1.565), (0.032, 0.012, 0.020), eye_white), "Head"))
        pieces.append((sphere("Iris", (x, -0.131, 1.565), (0.012, 0.006, 0.013), amber), "Head"))
        pieces.append((cube("Eyebrow", (x, -0.127, 1.600), (0.026, 0.004, 0.004), hair, 0.003), "Head"))
    pieces.append((cube("Mouth", (0, -0.130, 1.505), (0.025, 0.004, 0.004),
                        material("Lip", (0.55, 0.12, 0.12), roughness=0.5), 0.003), "Head"))
    pieces.append((cube("HairClip", (0.100, -0.108, 1.63), (0.028, 0.007, 0.010), accent, 0.006), "Head"))

    pieces.append((cone("TorsoTop", (0, 0, 1.18), (0.20, 0.155), 0.34, teal), "Chest"))
    pieces.append((cube("JacketLeft", (0.135, -0.005, 1.19), (0.075, 0.105, 0.17), white, 0.045), "Chest"))
    pieces.append((cube("JacketRight", (-0.135, -0.005, 1.19), (0.075, 0.105, 0.17), white, 0.045), "Chest"))
    pieces.append((cube("Belt", (0, -0.105, 0.985), (0.19, 0.016, 0.025), leather, 0.008), "Hips"))
    pieces.append((cube("Buckle", (0, -0.126, 0.985), (0.034, 0.010, 0.031), accent, 0.006), "Hips"))
    pieces.append((cone("PleatedSkirt", (0, 0, 0.83), (0.31, 0.20), 0.35, charcoal), "Hips"))
    for x in (-0.12, 0.12):
        side = "L" if x > 0 else "R"
        pieces.append((cylinder_between("Thigh", (x, 0, 0.76), (x, 0, 0.53), 0.070, tights), f"UpperLeg.{side}"))
        pieces.append((cylinder_between("Shin", (x, 0, 0.53), (x, 0, 0.19), 0.058, tights), f"LowerLeg.{side}"))
        pieces.append((cylinder_between("Boot", (x, 0, 0.37), (x, 0, 0.09), 0.075, leather), f"LowerLeg.{side}"))
        pieces.append((cube("BootFoot", (x, -0.075, 0.075), (0.075, 0.14, 0.065), leather, 0.025), f"Foot.{side}"))
    for sign, side in ((1, "L"), (-1, "R")):
        shoulder = (0.18 * sign, 0, 1.32)
        elbow = (0.36 * sign, 0, 1.14)
        wrist = (0.43 * sign, 0, 0.93)
        pieces.append((cylinder_between("UpperSleeve", shoulder, elbow, 0.078, white), f"UpperArm.{side}"))
        pieces.append((cylinder_between("LowerSleeve", elbow, wrist, 0.065, white), f"LowerArm.{side}"))
        pieces.append((sphere("Hand", (0.445 * sign, -0.005, 0.875), (0.052, 0.038, 0.075), skin), f"Hand.{side}"))
    for obj, bone in pieces:
        bind(obj, rig, bone)
    return pieces


def animate(rig):
    scene = bpy.context.scene
    scene.frame_start, scene.frame_end, scene.render.fps = 1, 72, 24
    keys = {
        1: {},
        18: {"Chest": (0.05, 0, -0.08), "Head": (0, 0.08, 0.10),
             "UpperArm.L": (-0.25, 0.02, -0.20), "LowerArm.L": (-0.35, 0, 0.12)},
        36: {"Chest": (-0.03, 0, 0.07), "Head": (0, -0.05, -0.08),
             "UpperArm.R": (0.28, 0.02, 0.18), "LowerArm.R": (0.38, 0, -0.14)},
        54: {"Chest": (0.04, 0, -0.04), "Head": (0, 0.04, 0.05),
             "UpperLeg.L": (0.10, 0, 0), "LowerLeg.L": (-0.12, 0, 0)},
        72: {},
    }
    for frame, values in keys.items():
        scene.frame_set(frame)
        for bone in rig.pose.bones:
            bone.rotation_mode = "XYZ"
            bone.rotation_euler = values.get(bone.name, (0, 0, 0))
            bone.keyframe_insert("rotation_euler")


def setup_scene(output_dir):
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x, scene.render.resolution_y = 720, 900
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.world = bpy.data.worlds.new("CleanHeroineWorld")
    scene.world.color = (0.012, 0.016, 0.026)
    floor_mat = material("Floor", (0.018, 0.027, 0.045), metallic=0.15, roughness=0.55)
    bpy.ops.mesh.primitive_plane_add(size=8, location=(0, 0, 0))
    bpy.context.object.data.materials.append(floor_mat)
    bpy.ops.object.light_add(type="AREA", location=(2.5, -3.5, 4.0))
    bpy.context.object.data.energy, bpy.context.object.data.shape, bpy.context.object.data.size = 950, "DISK", 4.0
    bpy.ops.object.light_add(type="AREA", location=(-2.2, 0.5, 2.8))
    bpy.context.object.data.energy, bpy.context.object.data.color, bpy.context.object.data.size = 700, (0.25, 0.55, 1.0), 3.0
    bpy.ops.object.camera_add(location=(2.65, -5.7, 2.15))
    camera = bpy.context.object
    direction = Vector((0, 0, 0.93)) - camera.location
    camera.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()
    camera.data.lens = 66
    scene.camera = camera
    scene.render.filepath = str(output_dir / "clean_heroine_v3_frame_001.png")
    return scene


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:])
    output_dir = Path(args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    rig = make_rig()
    pieces = build_character(rig)
    animate(rig)
    scene = setup_scene(output_dir)
    previews = {}
    for frame in (1, 18, 36, 54, 72):
        scene.frame_set(frame)
        path = output_dir / f"clean_heroine_v3_frame_{frame:03d}.png"
        scene.render.filepath = str(path)
        bpy.ops.render.render(write_still=True)
        previews[str(frame)] = str(path)
    frames_dir = output_dir / "motion_frames"
    frames_dir.mkdir(parents=True, exist_ok=True)
    for frame in range(scene.frame_start, scene.frame_end + 1):
        scene.frame_set(frame)
        scene.render.filepath = str(frames_dir / f"frame_{frame:04d}.png")
        bpy.ops.render.render(write_still=True)
    blend_path = output_dir / "clean_heroine_v3_rigged.blend"
    fbx_path = output_dir / "clean_heroine_v3_rigged.fbx"
    glb_path = output_dir / "clean_heroine_v3_rigged.glb"
    bpy.ops.wm.save_as_mainfile(filepath=str(blend_path))
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.export_scene.fbx(filepath=str(fbx_path), use_selection=True, add_leaf_bones=False,
                             bake_anim=True, bake_anim_use_all_actions=True)
    bpy.ops.export_scene.gltf(filepath=str(glb_path), export_format="GLB", export_animations=True)
    report = {
        "design": "original adult stylized heroine",
        "pieces": len(pieces),
        "bones": len(rig.data.bones),
        "frames": [1, 18, 36, 54, 72],
        "previews": previews,
        "blend": str(blend_path),
        "fbx": str(fbx_path),
        "glb": str(glb_path),
        "motion_frames": str(frames_dir),
        "quality_gate": "PENDING_VISUAL_QA",
    }
    (output_dir / "clean_heroine_v3_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
