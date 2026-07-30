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


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-glb", required=True)
    parser.add_argument("--reference-image", required=True)
    parser.add_argument("--output-dir", required=True)
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    return parser.parse_args(argv)


def point_at(obj, target):
    obj.rotation_euler = (Vector(target) - obj.location).to_track_quat("-Z", "Y").to_euler()


def bounds(obj):
    points = [obj.matrix_world @ Vector(corner) for corner in obj.bound_box]
    minimum = Vector(tuple(min(point[i] for point in points) for i in range(3)))
    maximum = Vector(tuple(max(point[i] for point in points) for i in range(3)))
    return minimum, maximum


def normalize_mesh(obj):
    minimum, maximum = bounds(obj)
    height = maximum.z - minimum.z
    factor = 1.70 / max(height, 0.001)
    obj.scale *= factor
    bpy.context.view_layer.update()
    minimum, maximum = bounds(obj)
    center_x = (minimum.x + maximum.x) * 0.5
    center_y = (minimum.y + maximum.y) * 0.5
    obj.location += Vector((-center_x, -center_y, -minimum.z))
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    return factor


def simplify_mesh(obj, target_triangles=120000):
    triangles = sum(max(1, len(poly.vertices) - 2) for poly in obj.data.polygons)
    if triangles <= target_triangles:
        return triangles, triangles
    modifier = obj.modifiers.new("RigReadyDecimate", "DECIMATE")
    modifier.ratio = max(0.05, target_triangles / triangles)
    modifier.use_collapse_triangulate = True
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.modifier_apply(modifier=modifier.name)
    result = sum(max(1, len(poly.vertices) - 2) for poly in obj.data.polygons)
    return triangles, result


def solid_material(name, color, roughness=0.5, metallic=0.0):
    material = bpy.data.materials.new(name)
    material.diffuse_color = (*color, 1.0)
    material.use_nodes = True
    bsdf = material.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = (*color, 1.0)
    bsdf.inputs["Roughness"].default_value = roughness
    bsdf.inputs["Metallic"].default_value = metallic
    return material


def projected_material(image_path):
    material = bpy.data.materials.new("ReferenceFront_PBR")
    material.use_nodes = True
    nodes = material.node_tree.nodes
    links = material.node_tree.links
    bsdf = nodes.get("Principled BSDF")
    texture = nodes.new("ShaderNodeTexImage")
    texture.image = bpy.data.images.load(str(image_path), check_existing=True)
    texture.interpolation = "Linear"
    links.new(texture.outputs["Color"], bsdf.inputs["Base Color"])
    bsdf.inputs["Roughness"].default_value = 0.48
    return material


def assign_materials_and_uv(obj, reference_image):
    materials = [
        projected_material(reference_image),
        solid_material("Skin_PBR", (0.82, 0.55, 0.42), 0.58),
        solid_material("Hair_PBR", (0.055, 0.025, 0.022), 0.34),
        solid_material("Jacket_PBR", (0.82, 0.77, 0.68), 0.54),
        solid_material("Top_PBR", (0.035, 0.22, 0.25), 0.46),
        solid_material("Skirt_PBR", (0.025, 0.026, 0.035), 0.58),
        solid_material("Tights_PBR", (0.018, 0.018, 0.024), 0.66),
        solid_material("BootLeather_PBR", (0.11, 0.045, 0.025), 0.38),
    ]
    for material in materials:
        obj.data.materials.append(material)

    minimum, maximum = bounds(obj)
    width = maximum.x - minimum.x
    height = maximum.z - minimum.z
    uv_layer = obj.data.uv_layers.new(name="ReferenceProjection")
    for loop in obj.data.loops:
        vertex = obj.data.vertices[loop.vertex_index].co
        x_norm = (vertex.x - minimum.x) / max(width, 0.001)
        z_norm = (vertex.z - minimum.z) / max(height, 0.001)
        u = 0.246 + x_norm * 0.509
        v = 0.033 + z_norm * 0.952
        uv_layer.data[loop.index].uv = (u, v)

    for polygon in obj.data.polygons:
        center = polygon.center
        # Keep the photographic projection on surfaces that genuinely face the
        # reference camera. Grazing faces otherwise stretch bright edge pixels
        # across the character sides.
        front_facing = center.y < 0.015 and polygon.normal.y < -0.72
        if front_facing:
            polygon.material_index = 0
        elif center.z > 1.34:
            polygon.material_index = 1 if center.y < -0.10 else 2
        elif abs(center.x) > 0.23 and 0.64 < center.z < 0.86:
            polygon.material_index = 1
        elif center.z > 1.03:
            polygon.material_index = 3
        elif center.z > 0.78:
            polygon.material_index = 4 if abs(center.x) < 0.16 else 3
        elif center.z > 0.47:
            polygon.material_index = 5
        elif center.z > 0.14:
            polygon.material_index = 6
        else:
            polygon.material_index = 7
        polygon.use_smooth = True
    return materials


def make_rig():
    bpy.ops.object.armature_add(enter_editmode=True, location=(0, 0, 0))
    rig = bpy.context.object
    rig.name = "OriginalAdultHeroine_Humanoid"
    armature = rig.data
    armature.name = rig.name
    armature.edit_bones.remove(armature.edit_bones[0])
    bones = {
        "Hips": ((0, 0, 0.78), (0, 0, 0.92), None),
        "Spine": ((0, 0, 0.86), (0, 0, 1.10), "Hips"),
        "Chest": ((0, 0, 1.06), (0, 0, 1.30), "Spine"),
        "Neck": ((0, 0, 1.29), (0, 0, 1.41), "Chest"),
        "Head": ((0, 0, 1.40), (0, 0, 1.68), "Neck"),
        "Shoulder.L": ((0.04, 0, 1.28), (0.16, 0, 1.27), "Chest"),
        "UpperArm.L": ((0.16, 0, 1.27), (0.29, 0, 1.05), "Shoulder.L"),
        "LowerArm.L": ((0.29, 0, 1.05), (0.36, 0, 0.84), "UpperArm.L"),
        "Hand.L": ((0.36, 0, 0.84), (0.39, -0.01, 0.70), "LowerArm.L"),
        "Shoulder.R": ((-0.04, 0, 1.28), (-0.16, 0, 1.27), "Chest"),
        "UpperArm.R": ((-0.16, 0, 1.27), (-0.29, 0, 1.05), "Shoulder.R"),
        "LowerArm.R": ((-0.29, 0, 1.05), (-0.36, 0, 0.84), "UpperArm.R"),
        "Hand.R": ((-0.36, 0, 0.84), (-0.39, -0.01, 0.70), "LowerArm.R"),
        "UpperLeg.L": ((0.095, 0, 0.82), (0.10, 0, 0.47), "Hips"),
        "LowerLeg.L": ((0.10, 0, 0.47), (0.105, 0, 0.14), "UpperLeg.L"),
        "Foot.L": ((0.105, 0, 0.14), (0.105, -0.14, 0.06), "LowerLeg.L"),
        "UpperLeg.R": ((-0.095, 0, 0.82), (-0.10, 0, 0.47), "Hips"),
        "LowerLeg.R": ((-0.10, 0, 0.47), (-0.105, 0, 0.14), "UpperLeg.R"),
        "Foot.R": ((-0.105, 0, 0.14), (-0.105, -0.14, 0.06), "LowerLeg.R"),
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


def primary_bone(position):
    x, y, z = position
    side = "L" if x >= 0 else "R"
    if z > 1.35:
        return "Head"
    if z > 1.27 and abs(x) < 0.18:
        return "Neck"
    if abs(x) > 0.17 and 0.66 < z < 1.34:
        if z > 1.20 and abs(x) < 0.22:
            return f"Shoulder.{side}"
        if z > 1.07:
            return f"UpperArm.{side}"
        if z > 0.84:
            return f"LowerArm.{side}"
        return f"Hand.{side}"
    # The generated skirt is fused to the body. Its broad shell must follow the
    # pelvis rather than split between both thighs, or it fans apart in motion.
    if 0.47 < z < 0.82 and (abs(x) > 0.145 or abs(y) > 0.075):
        return "Hips"
    if z < 0.78 and abs(x) > 0.045:
        if z > 0.47:
            return f"UpperLeg.{side}"
        if z > 0.14:
            return f"LowerLeg.{side}"
        return f"Foot.{side}"
    if z > 1.05:
        return "Chest"
    if z > 0.86:
        return "Spine"
    return "Hips"


def assign_deterministic_weights(obj, rig):
    obj.data.validate(verbose=True, clean_customdata=False)
    obj.data.update(calc_edges=True)
    groups = {bone.name: obj.vertex_groups.new(name=bone.name) for bone in rig.data.bones}
    counts = {name: 0 for name in groups}
    for vertex in obj.data.vertices:
        name = primary_bone(vertex.co)
        groups[name].add([vertex.index], 1.0, "REPLACE")
        counts[name] += 1
    modifier = obj.modifiers.new("HumanoidRig", "ARMATURE")
    modifier.object = rig
    modifier.use_vertex_groups = True
    obj.parent = rig
    return counts


def pose_rig(rig, posed):
    bpy.context.view_layer.objects.active = rig
    bpy.ops.object.mode_set(mode="POSE")
    for bone in rig.pose.bones:
        bone.rotation_mode = "XYZ"
        bone.rotation_euler = (0, 0, 0)
    if posed:
        values = {
            "Head": (0, 0, math.radians(-7)),
            "Chest": (math.radians(4), 0, math.radians(3)),
            "UpperArm.L": (math.radians(-20), 0, math.radians(-6)),
            "LowerArm.L": (math.radians(-10), 0, math.radians(8)),
            "UpperArm.R": (math.radians(18), 0, math.radians(5)),
            "LowerArm.R": (math.radians(8), 0, math.radians(-7)),
            "UpperLeg.L": (math.radians(11), 0, 0),
            "UpperLeg.R": (math.radians(-11), 0, 0),
            "LowerLeg.L": (math.radians(-8), 0, 0),
            "LowerLeg.R": (math.radians(8), 0, 0),
        }
        for name, rotation in values.items():
            rig.pose.bones[name].rotation_euler = rotation
    bpy.ops.object.mode_set(mode="OBJECT")
    bpy.context.view_layer.update()


def setup_render():
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x = 720
    scene.render.resolution_y = 900
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.view_settings.look = "AgX - Medium High Contrast"
    if scene.world is None:
        scene.world = bpy.data.worlds.new("HeroineV2World")
    scene.world.color = (0.022, 0.028, 0.04)
    bpy.ops.object.camera_add(location=(0.58, -3.4, 1.08))
    camera = bpy.context.object
    camera.data.lens = 68
    point_at(camera, (0, 0, 0.88))
    scene.camera = camera
    for name, location, energy, size in (
        ("Key", (2.2, -2.8, 3.1), 850, 3.0),
        ("Fill", (-2.2, -1.4, 1.8), 420, 2.5),
        ("Rim", (0, 2.0, 2.8), 700, 2.2),
    ):
        data = bpy.data.lights.new(name, "AREA")
        data.energy = energy
        data.shape = "DISK"
        data.size = size
        light = bpy.data.objects.new(name, data)
        bpy.context.collection.objects.link(light)
        light.location = location
        point_at(light, (0, 0, 0.9))
    bpy.ops.mesh.primitive_plane_add(size=8, location=(0, 0, -0.015))
    floor = bpy.context.object
    floor.data.materials.append(solid_material("Floor_PBR", (0.025, 0.032, 0.048), 0.7))


def render(scene, path):
    scene.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)


def export_assets(obj, rig, output_dir):
    blend_path = output_dir / "original_adult_heroine_v2_rigged.blend"
    glb_path = output_dir / "original_adult_heroine_v2_rigged.glb"
    fbx_path = output_dir / "original_adult_heroine_v2_rigged.fbx"
    bpy.ops.wm.save_as_mainfile(filepath=str(blend_path))
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    rig.select_set(True)
    bpy.context.view_layer.objects.active = rig
    bpy.ops.export_scene.gltf(
        filepath=str(glb_path),
        export_format="GLB",
        use_selection=True,
        export_skins=True,
        export_normals=True,
        export_texcoords=True,
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
    input_glb = Path(args.input_glb).resolve()
    reference_image = Path(args.reference_image).resolve()
    output_dir = Path(args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(input_glb))
    meshes = [obj for obj in bpy.context.scene.objects if obj.type == "MESH"]
    candidates = [obj for obj in meshes if len(obj.data.vertices) > 1000]
    if len(candidates) != 1:
        raise RuntimeError(f"Expected one character mesh, found {len(candidates)}")
    character = candidates[0]
    for obj in list(meshes):
        if obj != character:
            bpy.data.objects.remove(obj, do_unlink=True)
    character.name = "OriginalAdultHeroine_v2"
    scale_factor = normalize_mesh(character)
    triangles_before, triangles_after = simplify_mesh(character)
    materials = assign_materials_and_uv(character, reference_image)
    rig = make_rig()
    weight_counts = assign_deterministic_weights(character, rig)
    setup_render()
    scene = bpy.context.scene
    pose_rig(rig, False)
    rest_path = output_dir / "original_adult_heroine_v2_rest.png"
    render(scene, rest_path)
    pose_rig(rig, True)
    pose_path = output_dir / "original_adult_heroine_v2_pose.png"
    render(scene, pose_path)
    pose_rig(rig, False)
    blend_path, glb_path, fbx_path = export_assets(character, rig, output_dir)
    report = {
        "input_glb": str(input_glb),
        "reference_image": str(reference_image),
        "scale_factor": scale_factor,
        "triangles_before": triangles_before,
        "triangles_after": triangles_after,
        "materials": len(materials),
        "bones": len(rig.data.bones),
        "weight_counts": weight_counts,
        "outputs": {
            "blend": str(blend_path),
            "glb": str(glb_path),
            "fbx": str(fbx_path),
            "rest": str(rest_path),
            "pose": str(pose_path),
        },
        "quality_gate": "PENDING_VISUAL_QA",
    }
    report_path = output_dir / "original_adult_heroine_v2_report.json"
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
