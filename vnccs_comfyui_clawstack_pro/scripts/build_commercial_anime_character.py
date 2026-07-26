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
import bmesh
from mathutils import Vector


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", required=True)
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    return parser.parse_args(argv)


def material(name, color, metallic=0.0, roughness=0.48):
    item = bpy.data.materials.new(name)
    item.diffuse_color = (*color, 1.0)
    item.use_nodes = True
    bsdf = item.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = (*color, 1.0)
    bsdf.inputs["Metallic"].default_value = metallic
    bsdf.inputs["Roughness"].default_value = roughness
    return item


def finish_part(obj, name, bone, mat, bevel=0.025):
    obj.name = name
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    if bevel:
        modifier = obj.modifiers.new("EdgeSoftening", "BEVEL")
        modifier.width = bevel
        modifier.segments = 2
        bpy.context.view_layer.objects.active = obj
        bpy.ops.object.modifier_apply(modifier=modifier.name)
    if mat:
        obj.data.materials.append(mat)
    group = obj.vertex_groups.new(name=bone)
    group.add([v.index for v in obj.data.vertices], 1.0, "REPLACE")
    obj["deform_bone"] = bone
    return obj


def sphere(name, location, scale, bone, mat, segments=32, rings=20):
    bpy.ops.mesh.primitive_uv_sphere_add(
        segments=segments, ring_count=rings, location=location
    )
    obj = bpy.context.object
    obj.scale = scale
    return finish_part(obj, name, bone, mat, bevel=0.0)


def cylinder(name, start, end, radius, bone, mat, vertices=24):
    start = Vector(start)
    end = Vector(end)
    delta = end - start
    bpy.ops.mesh.primitive_cylinder_add(
        vertices=vertices,
        radius=radius,
        depth=delta.length,
        location=(start + end) / 2,
    )
    obj = bpy.context.object
    obj.rotation_mode = "QUATERNION"
    obj.rotation_quaternion = Vector((0, 0, 1)).rotation_difference(delta.normalized())
    return finish_part(obj, name, bone, mat)


def cone(name, location, radius_bottom, radius_top, depth, bone, mat, vertices=48):
    bpy.ops.mesh.primitive_cone_add(
        vertices=vertices,
        radius1=radius_bottom,
        radius2=radius_top,
        depth=depth,
        location=location,
    )
    return finish_part(bpy.context.object, name, bone, mat)


def cube(name, location, scale, bone, mat, bevel=0.04):
    bpy.ops.mesh.primitive_cube_add(location=location)
    obj = bpy.context.object
    obj.scale = scale
    return finish_part(obj, name, bone, mat, bevel=bevel)


def torus(name, location, major_radius, minor_radius, bone, mat, rotation=(0, 0, 0)):
    bpy.ops.mesh.primitive_torus_add(
        major_radius=major_radius,
        minor_radius=minor_radius,
        major_segments=40,
        minor_segments=10,
        location=location,
        rotation=rotation,
    )
    return finish_part(bpy.context.object, name, bone, mat, bevel=0.0)


def make_rig():
    bpy.ops.object.armature_add(enter_editmode=True, location=(0, 0, 0))
    rig = bpy.context.object
    rig.name = "CommercialAnimeHumanoid"
    armature = rig.data
    armature.name = "CommercialAnimeHumanoid"
    armature.edit_bones.remove(armature.edit_bones[0])

    bones = {
        "Hips": ((0, 0, 1.55), (0, 0, 1.78), None),
        "Spine": ((0, 0, 1.70), (0, 0, 2.08), "Hips"),
        "Chest": ((0, 0, 2.02), (0, 0, 2.38), "Spine"),
        "Neck": ((0, 0, 2.36), (0, 0, 2.52), "Chest"),
        "Head": ((0, 0, 2.50), (0, 0, 3.12), "Neck"),
        "Shoulder.L": ((0.08, 0, 2.32), (0.30, 0, 2.31), "Chest"),
        "UpperArm.L": ((0.30, 0, 2.31), (0.70, -0.01, 2.14), "Shoulder.L"),
        "LowerArm.L": ((0.70, -0.01, 2.14), (0.98, -0.03, 1.87), "UpperArm.L"),
        "Hand.L": ((0.98, -0.03, 1.87), (1.10, -0.05, 1.70), "LowerArm.L"),
        "Shoulder.R": ((-0.08, 0, 2.32), (-0.30, 0, 2.31), "Chest"),
        "UpperArm.R": ((-0.30, 0, 2.31), (-0.70, -0.01, 2.14), "Shoulder.R"),
        "LowerArm.R": ((-0.70, -0.01, 2.14), (-0.98, -0.03, 1.87), "UpperArm.R"),
        "Hand.R": ((-0.98, -0.03, 1.87), (-1.10, -0.05, 1.70), "LowerArm.R"),
        "UpperLeg.L": ((0.18, 0, 1.58), (0.20, 0, 1.00), "Hips"),
        "LowerLeg.L": ((0.20, 0, 1.00), (0.20, 0, 0.43), "UpperLeg.L"),
        "Foot.L": ((0.20, 0, 0.43), (0.20, -0.24, 0.18), "LowerLeg.L"),
        "UpperLeg.R": ((-0.18, 0, 1.58), (-0.20, 0, 1.00), "Hips"),
        "LowerLeg.R": ((-0.20, 0, 1.00), (-0.20, 0, 0.43), "UpperLeg.R"),
        "Foot.R": ((-0.20, 0, 0.43), (-0.20, -0.24, 0.18), "LowerLeg.R"),
    }
    for name, (head, tail, parent) in bones.items():
        bone = armature.edit_bones.new(name)
        bone.head = head
        bone.tail = tail
        if parent:
            bone.parent = armature.edit_bones[parent]
            bone.use_connect = False
    bpy.ops.object.mode_set(mode="OBJECT")
    rig.show_in_front = True
    return rig


def build_character(materials):
    skin = materials["skin"]
    hair = materials["hair"]
    eye = materials["eye"]
    white = materials["white"]
    teal = materials["teal"]
    charcoal = materials["charcoal"]
    red = materials["red"]
    brown = materials["brown"]
    parts = []

    parts += [
        sphere("Head", (0, 0, 2.76), (0.39, 0.34, 0.46), "Head", skin),
        sphere("HairCap", (0, 0.035, 2.91), (0.42, 0.35, 0.37), "Head", hair),
        sphere("HairBack", (0, 0.17, 2.70), (0.42, 0.19, 0.43), "Head", hair),
        sphere("Eye_L", (0.145, -0.324, 2.82), (0.075, 0.025, 0.105), "Head", eye, 24, 16),
        sphere("Eye_R", (-0.145, -0.324, 2.82), (0.075, 0.025, 0.105), "Head", eye, 24, 16),
        sphere("EyeHighlight_L", (0.165, -0.349, 2.855), (0.018, 0.008, 0.022), "Head", white, 16, 10),
        sphere("EyeHighlight_R", (-0.125, -0.349, 2.855), (0.018, 0.008, 0.022), "Head", white, 16, 10),
        sphere("Pupil_L", (0.145, -0.347, 2.81), (0.030, 0.009, 0.050), "Head", hair, 16, 10),
        sphere("Pupil_R", (-0.145, -0.347, 2.81), (0.030, 0.009, 0.050), "Head", hair, 16, 10),
        sphere("Nose", (0, -0.357, 2.72), (0.025, 0.018, 0.035), "Head", skin, 16, 10),
        sphere("Mouth", (0, -0.341, 2.64), (0.07, 0.012, 0.018), "Head", red, 20, 10),
        sphere("Blush_L", (0.235, -0.323, 2.69), (0.06, 0.01, 0.025), "Head", red, 16, 8),
        sphere("Blush_R", (-0.235, -0.323, 2.69), (0.06, 0.01, 0.025), "Head", red, 16, 8),
    ]
    for x, angle in ((0.22, -0.18), (-0.22, 0.18), (0.0, 0.0)):
        lock = sphere(
            f"Bang_{x:+.2f}", (x, -0.255, 2.99), (0.13, 0.10, 0.30), "Head", hair, 24, 16
        )
        lock.rotation_euler.y = angle
        parts.append(lock)
    parts += [
        sphere("Torso", (0, 0, 2.08), (0.38, 0.25, 0.44), "Chest", teal),
        cube("Jacket_L", (0.30, 0.02, 2.13), (0.15, 0.245, 0.39), "Chest", white, bevel=0.09),
        cube("Jacket_R", (-0.30, 0.02, 2.13), (0.15, 0.245, 0.39), "Chest", white, bevel=0.09),
        cone("Skirt", (0, 0.02, 1.52), 0.64, 0.34, 0.78, "Hips", charcoal),
        torus("SkirtHem", (0, 0.02, 1.14), 0.59, 0.035, "Hips", red),
    ]
    for side, sign in (("L", 1), ("R", -1)):
        shoulder = (0.30 * sign, 0, 2.31)
        elbow = (0.70 * sign, -0.01, 2.14)
        wrist = (0.98 * sign, -0.03, 1.87)
        hand = (1.07 * sign, -0.05, 1.73)
        parts += [
            sphere(f"Shoulder_{side}", shoulder, (0.18, 0.20, 0.20), f"UpperArm.{side}", white),
            cylinder(f"UpperArm_{side}", shoulder, elbow, 0.145, f"UpperArm.{side}", white),
            cylinder(f"LowerArm_{side}", elbow, wrist, 0.125, f"LowerArm.{side}", charcoal),
            sphere(f"Hand_{side}", hand, (0.12, 0.085, 0.18), f"Hand.{side}", skin, 24, 16),
            sphere(
                f"Thumb_{side}",
                (1.055 * sign, -0.125, 1.76),
                (0.055, 0.045, 0.085),
                f"Hand.{side}",
                skin,
                16,
                10,
            ),
        ]
        hip = (0.18 * sign, 0, 1.58)
        knee = (0.20 * sign, 0, 1.00)
        ankle = (0.20 * sign, 0, 0.43)
        parts += [
            cylinder(f"UpperLeg_{side}", hip, knee, 0.15, f"UpperLeg.{side}", charcoal),
            cylinder(f"LowerLeg_{side}", knee, ankle, 0.135, f"LowerLeg.{side}", charcoal),
            sphere(f"Boot_{side}", (0.20 * sign, -0.08, 0.28), (0.17, 0.28, 0.28), f"Foot.{side}", brown),
        ]
    return parts


def join_and_bind(parts, rig):
    bpy.ops.object.select_all(action="DESELECT")
    for part in parts:
        part.select_set(True)
    bpy.context.view_layer.objects.active = parts[0]
    bpy.ops.object.join()
    character = bpy.context.object
    character.name = "OriginalAdultHeroine_Commercial"
    for bone in rig.data.bones:
        if character.vertex_groups.get(bone.name) is None:
            character.vertex_groups.new(name=bone.name)
    modifier = character.modifiers.new("HumanoidRig", "ARMATURE")
    modifier.object = rig
    character.parent = rig
    return character


def mesh_metrics(obj):
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    boundary = sum(1 for edge in bm.edges if edge.is_boundary)
    non_manifold = sum(1 for edge in bm.edges if not edge.is_manifold)
    bm.free()
    return {
        "vertices": len(obj.data.vertices),
        "polygons": len(obj.data.polygons),
        "triangles": sum(max(1, len(p.vertices) - 2) for p in obj.data.polygons),
        "boundary_edges": boundary,
        "non_manifold_edges": non_manifold,
        "materials": len(obj.data.materials),
        "vertex_groups": len(obj.vertex_groups),
    }


def point_at(obj, target):
    obj.rotation_euler = (Vector(target) - obj.location).to_track_quat("-Z", "Y").to_euler()


def setup_render():
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x = 720
    scene.render.resolution_y = 900
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    if scene.world is None:
        scene.world = bpy.data.worlds.new("CommercialCharacterWorld")
    scene.world.color = (0.025, 0.028, 0.035)
    bpy.ops.object.camera_add(location=(4.3, -7.2, 3.2))
    camera = bpy.context.object
    camera.data.lens = 65
    point_at(camera, (0, 0, 1.65))
    scene.camera = camera
    for name, location, energy, size in (
        ("Key", (4, -5, 7), 700, 4.0),
        ("Fill", (-4, -3, 4), 450, 3.0),
        ("Rim", (0, 4, 6), 650, 3.0),
    ):
        data = bpy.data.lights.new(name, "AREA")
        data.energy = energy
        data.shape = "DISK"
        data.size = size
        light = bpy.data.objects.new(name, data)
        bpy.context.collection.objects.link(light)
        light.location = location
        point_at(light, (0, 0, 1.7))


def render_validation(rig, output_dir):
    scene = bpy.context.scene
    rest_path = output_dir / "commercial_heroine_v23_rest.png"
    scene.render.filepath = str(rest_path)
    bpy.ops.render.render(write_still=True)
    bpy.context.view_layer.objects.active = rig
    bpy.ops.object.mode_set(mode="POSE")
    rig.pose.bones["UpperArm.L"].rotation_mode = "XYZ"
    rig.pose.bones["UpperArm.R"].rotation_mode = "XYZ"
    rig.pose.bones["UpperArm.L"].rotation_euler.y = math.radians(-38)
    rig.pose.bones["UpperArm.R"].rotation_euler.y = math.radians(38)
    rig.pose.bones["Head"].rotation_mode = "XYZ"
    rig.pose.bones["Head"].rotation_euler.z = math.radians(-8)
    bpy.ops.object.mode_set(mode="OBJECT")
    bpy.context.view_layer.update()
    pose_path = output_dir / "commercial_heroine_v23_pose.png"
    scene.render.filepath = str(pose_path)
    bpy.ops.render.render(write_still=True)
    bpy.context.view_layer.objects.active = rig
    bpy.ops.object.mode_set(mode="POSE")
    for bone in rig.pose.bones:
        bone.matrix_basis.identity()
    bpy.ops.object.mode_set(mode="OBJECT")
    bpy.context.view_layer.update()
    return rest_path, pose_path


def export(character, rig, output_dir):
    blend_path = output_dir / "commercial_heroine_v23.blend"
    glb_path = output_dir / "commercial_heroine_v23.glb"
    fbx_path = output_dir / "commercial_heroine_v23.fbx"
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
        export_normals=True,
        export_yup=True,
    )
    bpy.ops.export_scene.fbx(
        filepath=str(fbx_path),
        use_selection=True,
        object_types={"ARMATURE", "MESH"},
        add_leaf_bones=False,
        bake_anim=False,
        axis_forward="-Z",
        axis_up="Y",
    )
    return blend_path, glb_path, fbx_path


def main():
    args = parse_args()
    output_dir = Path(args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    materials = {
        "skin": material("Skin_PBR", (0.82, 0.56, 0.43), roughness=0.62),
        "hair": material("Hair_PBR", (0.095, 0.045, 0.04), roughness=0.38),
        "eye": material("Eyes_PBR", (0.035, 0.11, 0.14), roughness=0.22),
        "white": material("Jacket_PBR", (0.86, 0.82, 0.74), roughness=0.55),
        "teal": material("Top_PBR", (0.07, 0.30, 0.34), roughness=0.46),
        "charcoal": material("Skirt_Tights_PBR", (0.035, 0.035, 0.045), roughness=0.58),
        "red": material("Accent_PBR", (0.34, 0.025, 0.035), roughness=0.44),
        "brown": material("BootLeather_PBR", (0.14, 0.065, 0.035), roughness=0.36),
    }
    rig = make_rig()
    character = join_and_bind(build_character(materials), rig)
    metrics = mesh_metrics(character)
    setup_render()
    rest_path, pose_path = render_validation(rig, output_dir)
    blend_path, glb_path, fbx_path = export(character, rig, output_dir)
    report = {
        "quality_target": "COMMERCIAL_STYLIZED_CHARACTER",
        "mesh": metrics,
        "bones": len(rig.data.bones),
        "armature_modifier": any(m.type == "ARMATURE" for m in character.modifiers),
        "outputs": {
            "blend": str(blend_path),
            "glb": str(glb_path),
            "fbx": str(fbx_path),
            "rest_preview": str(rest_path),
            "pose_preview": str(pose_path),
        },
        "quality_gate": "PENDING_REIMPORT_AND_VISUAL_QA",
    }
    report_path = output_dir / "commercial_heroine_v23_report.json"
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
