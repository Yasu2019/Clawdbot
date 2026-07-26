# -*- coding: utf-8 -*-
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

import bmesh
import bpy
from mathutils import Matrix, Vector


def parse_args():
    parser = argparse.ArgumentParser(
        description="Clean, color, rig, validate, and export a Hunyuan3D character."
    )
    parser.add_argument("--input-glb", required=True)
    parser.add_argument("--turnaround", required=True)
    parser.add_argument("--output-dir", required=True)
    return parser.parse_args(sys.argv[sys.argv.index("--") + 1:])


def object_bounds(obj):
    points = [obj.matrix_world @ Vector(corner) for corner in obj.bound_box]
    minimum = Vector(tuple(min(point[i] for point in points) for i in range(3)))
    maximum = Vector(tuple(max(point[i] for point in points) for i in range(3)))
    return minimum, maximum


def mesh_metrics(obj):
    mesh = obj.data
    bm = bmesh.new()
    bm.from_mesh(mesh)
    non_manifold = sum(1 for edge in bm.edges if not edge.is_manifold)
    boundary = sum(1 for edge in bm.edges if edge.is_boundary)
    bm.free()
    return {
        "vertices": len(mesh.vertices),
        "edges": len(mesh.edges),
        "triangles": sum(len(poly.vertices) - 2 for poly in mesh.polygons),
        "polygons": len(mesh.polygons),
        "non_manifold_edges": non_manifold,
        "boundary_edges": boundary,
    }


def clean_mesh(obj):
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)

    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=0.00005)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(obj.data)
    bm.free()
    obj.data.validate(clean_customdata=False)
    obj.data.update()

    metrics = mesh_metrics(obj)
    if metrics["non_manifold_edges"] or metrics["boundary_edges"]:
        minimum, maximum = object_bounds(obj)
        height = max(maximum.z - minimum.z, 0.1)
        obj.data.remesh_voxel_size = height / 320.0
        obj.data.remesh_voxel_adaptivity = 0.0
        obj.data.use_remesh_preserve_volume = True
        bpy.ops.object.voxel_remesh()

    initial_triangles = sum(len(poly.vertices) - 2 for poly in obj.data.polygons)
    if initial_triangles > 110000:
        modifier = obj.modifiers.new("ProductionDecimate", "DECIMATE")
        modifier.decimate_type = "COLLAPSE"
        modifier.ratio = max(0.25, 100000.0 / initial_triangles)
        modifier.use_collapse_triangulate = True
        bpy.ops.object.modifier_apply(modifier=modifier.name)

    smooth = obj.modifiers.new("VolumePreservingSmooth", "LAPLACIANSMOOTH")
    smooth.iterations = 2
    smooth.lambda_factor = 0.025
    smooth.lambda_border = 0.01
    smooth.use_volume_preserve = True
    bpy.ops.object.modifier_apply(modifier=smooth.name)

    bm = bmesh.new()
    bm.from_mesh(obj.data)
    boundary_edges = [edge for edge in bm.edges if edge.is_boundary]
    if boundary_edges:
        bmesh.ops.holes_fill(bm, edges=boundary_edges, sides=0)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(obj.data)
    bm.free()

    for polygon in obj.data.polygons:
        polygon.use_smooth = True
    obj.data.validate(clean_customdata=False)
    obj.data.update()


def sample_rgb(pixels, width, height, x, y):
    x = max(0, min(width - 1, int(round(x))))
    y_from_top = max(0, min(height - 1, int(round(y))))
    y_from_bottom = height - 1 - y_from_top
    offset = int((y_from_bottom * width + x) * 4)
    return (
        pixels[offset],
        pixels[offset + 1],
        pixels[offset + 2],
        pixels[offset + 3],
    )


def apply_turnaround_colors(obj, image_path):
    image = bpy.data.images.load(str(image_path), check_existing=False)
    image_width, image_height = map(int, image.size)
    if image_width < 1480 or image_height < 1024:
        raise RuntimeError(
            f"Turnaround resolution too small: {image_width}x{image_height}"
        )
    pixels = list(image.pixels)
    minimum, maximum = object_bounds(obj)
    mesh_width = max(maximum.x - minimum.x, 1e-6)
    mesh_depth = max(maximum.y - minimum.y, 1e-6)
    mesh_height = max(maximum.z - minimum.z, 1e-6)

    color_layer = obj.data.color_attributes.get("COLOR_0")
    if color_layer:
        obj.data.color_attributes.remove(color_layer)
    color_layer = obj.data.color_attributes.new(
        name="COLOR_0", type="FLOAT_COLOR", domain="CORNER"
    )
    obj.data.color_attributes.active_color = color_layer
    obj.data.color_attributes.render_color_index = (
        list(obj.data.color_attributes).index(color_layer)
    )

    front_box = (80.0, 0.0, 600.0, 1024.0)
    side_box = (600.0, 0.0, 950.0, 1024.0)
    back_box = (960.0, 0.0, 1480.0, 1024.0)

    channel_sums = [0.0, 0.0, 0.0]
    channel_mins = [1.0, 1.0, 1.0]
    channel_maxs = [0.0, 0.0, 0.0]
    color_count = 0
    mapped_min = [float("inf"), float("inf")]
    mapped_max = [float("-inf"), float("-inf")]
    mapped_sum = [0.0, 0.0]
    view_counts = {"front": 0, "side": 0, "back": 0}
    dark_samples = 0
    target_points = {
        "front_top": (340.0, 300.0),
        "front_skirt": (340.0, 512.0),
        "side_torso": (775.0, 400.0),
        "back_skirt": (1220.0, 500.0),
    }
    closest_points = {
        name: {"distance": float("inf"), "mapped": None, "color": None}
        for name in target_points
    }
    for polygon in obj.data.polygons:
        normal = polygon.normal.normalized()
        for loop_index in polygon.loop_indices:
            vertex = obj.data.vertices[obj.data.loops[loop_index].vertex_index]
            co = obj.matrix_world @ vertex.co
            vertical = (co.z - minimum.z) / mesh_height
            normalized_x = abs(
                (co.x - (minimum.x + maximum.x) / 2.0) / mesh_width
            )

            if abs(normal.y) >= abs(normal.x):
                horizontal = (co.x - minimum.x) / mesh_width
                box = front_box if normal.y <= 0.0 else back_box
                view_name = "front" if normal.y <= 0.0 else "back"
                if normal.y > 0.0:
                    horizontal = 1.0 - horizontal
            else:
                horizontal = (co.y - minimum.y) / mesh_depth
                if normal.x < 0.0:
                    horizontal = 1.0 - horizontal
                box = side_box
                view_name = "side"

            x = box[0] + horizontal * (box[2] - box[0])
            y = box[3] - vertical * (box[3] - box[1])
            color = sample_rgb(
                pixels, image_width, image_height, x, y
            )
            if vertical < 0.14:
                semantic = (0.16, 0.10, 0.075, 1.0)
            elif vertical < 0.40:
                semantic = (0.055, 0.05, 0.055, 1.0)
            elif vertical < 0.62:
                semantic = (
                    (0.22, 0.055, 0.065, 1.0)
                    if 0.405 <= vertical <= 0.425
                    else (0.065, 0.065, 0.075, 1.0)
                )
            elif vertical < 0.77:
                semantic = (
                    (0.12, 0.24, 0.27, 1.0)
                    if normalized_x < 0.14 and normal.y <= 0.15
                    else (0.86, 0.82, 0.74, 1.0)
                )
            else:
                is_face = (
                    vertical < 0.93
                    and normalized_x < 0.23
                    and normal.y < -0.15
                )
                semantic = (
                    (0.82, 0.59, 0.46, 1.0)
                    if is_face
                    else (0.12, 0.075, 0.065, 1.0)
                )
            source_is_background = (
                sum(color[:3]) / 3.0 > 0.80
                and max(color[:3]) - min(color[:3]) < 0.10
            )
            source_is_warm_skin = (
                not source_is_background
                and color[0] > color[2] * 1.08
                and color[0] >= color[1]
            )
            is_hand = (
                0.36 < vertical < 0.52
                and normalized_x > 0.36
                and source_is_warm_skin
            )
            if is_hand:
                semantic = (0.82, 0.59, 0.46, 1.0)
            detail_weight = 0.0 if source_is_background else 0.15
            color = tuple(
                semantic[channel] * (1.0 - detail_weight)
                + color[channel] * detail_weight
                for channel in range(4)
            )
            color_layer.data[loop_index].color = color
            mapped_min[0] = min(mapped_min[0], x)
            mapped_min[1] = min(mapped_min[1], y)
            mapped_max[0] = max(mapped_max[0], x)
            mapped_max[1] = max(mapped_max[1], y)
            mapped_sum[0] += x
            mapped_sum[1] += y
            view_counts[view_name] += 1
            if sum(color[:3]) / 3.0 < 0.7:
                dark_samples += 1
            for name, target in target_points.items():
                distance = math.hypot(x - target[0], y - target[1])
                if distance < closest_points[name]["distance"]:
                    closest_points[name] = {
                        "distance": distance,
                        "mapped": [x, y],
                        "color": list(color),
                    }
            for channel in range(3):
                channel_sums[channel] += color[channel]
                channel_mins[channel] = min(channel_mins[channel], color[channel])
                channel_maxs[channel] = max(channel_maxs[channel], color[channel])
            color_count += 1

    material = bpy.data.materials.new("TurnaroundVertexColor")
    material.use_nodes = True
    material.diffuse_color = (1.0, 1.0, 1.0, 1.0)
    material.roughness = 0.72
    nodes = material.node_tree.nodes
    links = material.node_tree.links
    for node in list(nodes):
        nodes.remove(node)
    output = nodes.new("ShaderNodeOutputMaterial")
    shader = nodes.new("ShaderNodeBsdfPrincipled")
    vertex_color = nodes.new("ShaderNodeAttribute")
    vertex_color.attribute_name = "COLOR_0"
    links.new(vertex_color.outputs["Color"], shader.inputs["Base Color"])
    links.new(shader.outputs["BSDF"], output.inputs["Surface"])
    obj.data.materials.clear()
    obj.data.materials.append(material)
    obj.data.update()
    return {
        "min": channel_mins,
        "max": channel_maxs,
        "mean": [value / max(color_count, 1) for value in channel_sums],
        "samples": color_count,
        "mapped_min": mapped_min,
        "mapped_max": mapped_max,
        "mapped_mean": [
            value / max(color_count, 1) for value in mapped_sum
        ],
        "view_counts": view_counts,
        "dark_sample_ratio": dark_samples / max(color_count, 1),
        "reference_samples": {
            name: list(
                sample_rgb(
                    pixels, image_width, image_height, *point
                )
            )
            for name, point in target_points.items()
        },
        "closest_projected_samples": closest_points,
    }


def add_edit_bone(armature, name, head, tail, parent=None, connected=False):
    bone = armature.edit_bones.new(name)
    bone.head = head
    bone.tail = tail
    if parent:
        bone.parent = parent
        bone.use_connect = connected
    return bone


def create_humanoid_rig(obj):
    minimum, maximum = object_bounds(obj)
    center_x = (minimum.x + maximum.x) / 2
    center_y = (minimum.y + maximum.y) / 2
    width = maximum.x - minimum.x
    height = maximum.z - minimum.z
    z0 = minimum.z

    armature_data = bpy.data.armatures.new("HeroineHumanoidRig")
    rig = bpy.data.objects.new("HeroineHumanoidRig", armature_data)
    bpy.context.collection.objects.link(rig)
    rig.show_in_front = True
    bpy.context.view_layer.objects.active = rig
    rig.select_set(True)
    bpy.ops.object.mode_set(mode="EDIT")

    c = Vector((center_x, center_y, 0.0))
    hips = add_edit_bone(
        armature_data, "Hips", c + Vector((0, 0, z0 + height * 0.43)),
        c + Vector((0, 0, z0 + height * 0.52))
    )
    spine = add_edit_bone(
        armature_data, "Spine", hips.tail, c + Vector((0, 0, z0 + height * 0.61)),
        hips, True
    )
    chest = add_edit_bone(
        armature_data, "Chest", spine.tail, c + Vector((0, 0, z0 + height * 0.70)),
        spine, True
    )
    neck = add_edit_bone(
        armature_data, "Neck", chest.tail, c + Vector((0, 0, z0 + height * 0.76)),
        chest, True
    )
    add_edit_bone(
        armature_data, "Head", neck.tail, c + Vector((0, 0, z0 + height * 0.93)),
        neck, True
    )

    for side, sign in (("L", 1.0), ("R", -1.0)):
        shoulder = Vector((center_x + sign * width * 0.17, center_y, z0 + height * 0.69))
        elbow = Vector((center_x + sign * width * 0.34, center_y, z0 + height * 0.56))
        wrist = Vector((center_x + sign * width * 0.46, center_y, z0 + height * 0.43))
        hand_end = Vector((center_x + sign * width * 0.48, center_y, z0 + height * 0.37))
        clavicle = add_edit_bone(
            armature_data, f"Shoulder.{side}", chest.tail, shoulder, chest
        )
        upper_arm = add_edit_bone(
            armature_data, f"UpperArm.{side}", shoulder, elbow, clavicle, True
        )
        lower_arm = add_edit_bone(
            armature_data, f"LowerArm.{side}", elbow, wrist, upper_arm, True
        )
        add_edit_bone(
            armature_data, f"Hand.{side}", wrist, hand_end, lower_arm, True
        )

        hip = Vector((center_x + sign * width * 0.11, center_y, z0 + height * 0.43))
        knee = Vector((center_x + sign * width * 0.10, center_y, z0 + height * 0.24))
        ankle = Vector((center_x + sign * width * 0.095, center_y, z0 + height * 0.055))
        toe = Vector((center_x + sign * width * 0.095, center_y - height * 0.075, z0 + height * 0.025))
        upper_leg = add_edit_bone(
            armature_data, f"UpperLeg.{side}", hip, knee, hips
        )
        lower_leg = add_edit_bone(
            armature_data, f"LowerLeg.{side}", knee, ankle, upper_leg, True
        )
        add_edit_bone(
            armature_data, f"Foot.{side}", ankle, toe, lower_leg, True
        )

    bpy.ops.object.mode_set(mode="OBJECT")

    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    rig.select_set(True)
    bpy.context.view_layer.objects.active = rig
    bpy.ops.object.parent_set(type="ARMATURE_AUTO")
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.vertex_group_limit_total(group_select_mode="ALL", limit=4)
    bpy.ops.object.vertex_group_normalize_all(
        group_select_mode="ALL", lock_active=False
    )
    return rig


def apply_deterministic_weights(obj, rig, image_path):
    minimum, maximum = object_bounds(obj)
    center_x = (minimum.x + maximum.x) / 2.0
    width = max(maximum.x - minimum.x, 1e-6)
    height = max(maximum.z - minimum.z, 1e-6)
    image = bpy.data.images.load(str(image_path), check_existing=False)
    image_width, image_height = map(int, image.size)
    pixels = list(image.pixels)
    groups = {group.name: group for group in obj.vertex_groups}
    arm_group_names = [
        name
        for name in groups
        if name.startswith(("Shoulder.", "UpperArm.", "LowerArm.", "Hand."))
    ]
    corrected = 0
    corrected_indices = set()

    for vertex in obj.data.vertices:
        co = obj.matrix_world @ vertex.co
        vertical = (co.z - minimum.z) / height
        normalized_x = abs((co.x - center_x) / width)
        front_x = 80.0 + ((co.x - minimum.x) / width) * 520.0
        front_y = 1024.0 - vertical * 1024.0
        front_color = sample_rgb(
            pixels, image_width, image_height, front_x, front_y
        )
        front_luminance = sum(front_color[:3]) / 3.0
        front_is_background = (
            front_luminance > 0.80
            and max(front_color[:3]) - min(front_color[:3]) < 0.10
        )
        arm_weight = 0.0
        for membership in vertex.groups:
            group_name = obj.vertex_groups[membership.group].name
            if group_name in arm_group_names:
                arm_weight += membership.weight
        skirt_half_width = max(0.17, 0.45 - (vertical - 0.40) * 1.0)
        is_skirt = (
            arm_weight > 0.01
            and 0.34 <= vertical < 0.68
            and (
                front_luminance <= 0.45
                or normalized_x <= skirt_half_width
                or (vertical < 0.44 and front_is_background)
            )
        )
        if not is_skirt:
            continue
        for group_name in arm_group_names:
            groups[group_name].remove([vertex.index])
        groups["Hips"].add([vertex.index], 0.8, "REPLACE")
        groups["Spine"].add([vertex.index], 0.2, "REPLACE")
        corrected += 1
        corrected_indices.add(vertex.index)
    obj.data.update()
    print(f"[OK] Removed arm weights from {corrected} skirt vertices")
    return corrected_indices


def separate_arm_skirt_bridges(obj, skirt_indices):
    minimum, maximum = object_bounds(obj)
    mesh_height = max(maximum.z - minimum.z, 1e-6)
    arm_prefixes = ("Shoulder.", "UpperArm.", "LowerArm.", "Hand.")
    arm_vertices = set()
    for vertex in obj.data.vertices:
        for membership in vertex.groups:
            group_name = obj.vertex_groups[membership.group].name
            if group_name.startswith(arm_prefixes) and membership.weight > 0.05:
                arm_vertices.add(vertex.index)
                break
    bridge_faces = [
        polygon.index
        for polygon in obj.data.polygons
        if (
            sum(
                ((obj.matrix_world @ obj.data.vertices[index].co).z - minimum.z)
                / mesh_height
                for index in polygon.vertices
            )
            / len(polygon.vertices)
            < 0.58
        )
        if any(index in skirt_indices for index in polygon.vertices)
        and any(index in arm_vertices for index in polygon.vertices)
    ]
    if bridge_faces:
        bpy.context.view_layer.objects.active = obj
        obj.select_set(True)
        bpy.ops.object.mode_set(mode="EDIT")
        bpy.ops.mesh.select_all(action="DESELECT")
        bpy.ops.object.mode_set(mode="OBJECT")
        for face_index in bridge_faces:
            obj.data.polygons[face_index].select = True
        bpy.ops.object.mode_set(mode="EDIT")
        bpy.ops.mesh.delete(type="FACE")
        bpy.ops.object.mode_set(mode="OBJECT")
        obj.data.update()
    print(f"[OK] Removed {len(bridge_faces)} arm-skirt bridge faces")
    return len(bridge_faces)


def point_at(obj, target):
    obj.rotation_euler = (target - obj.location).to_track_quat("-Z", "Y").to_euler()


def render_pose(obj, rig, output_path):
    minimum, maximum = object_bounds(obj)
    center = (minimum + maximum) / 2
    height = maximum.z - minimum.z
    camera_data = bpy.data.cameras.new("ValidationCamera")
    camera = bpy.data.objects.new("ValidationCamera", camera_data)
    bpy.context.collection.objects.link(camera)
    bpy.context.scene.camera = camera
    camera.location = center + Vector((height * 0.75, -height * 2.25, height * 0.18))
    camera.data.lens = 58
    point_at(camera, center + Vector((0, 0, height * 0.03)))

    for name, location, energy, size in (
        ("Key", center + Vector((height * 1.5, -height * 1.5, height * 2.0)), 125, 4.0),
        ("Fill", center + Vector((-height, -height, height)), 80, 3.0),
        ("Rim", center + Vector((0, height * 1.5, height * 2.0)), 105, 3.0),
    ):
        data = bpy.data.lights.new(name, "AREA")
        data.energy = energy
        data.size = size
        light = bpy.data.objects.new(name, data)
        bpy.context.collection.objects.link(light)
        light.location = location
        point_at(light, center)

    world = bpy.context.scene.world or bpy.data.worlds.new("World")
    bpy.context.scene.world = world
    world.color = (0.035, 0.035, 0.035)
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x = 720
    scene.render.resolution_y = 900
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    rest_output_path = output_path.with_name(
        output_path.stem.replace("_pose", "_rest") + output_path.suffix
    )
    scene.render.filepath = str(rest_output_path)
    bpy.ops.render.render(write_still=True)

    bpy.context.view_layer.objects.active = rig
    bpy.ops.object.mode_set(mode="POSE")
    for bone_name, angle in (("UpperArm.L", -28), ("UpperArm.R", 22)):
        pose_bone = rig.pose.bones[bone_name]
        pivot = pose_bone.head.copy()
        pose_bone.matrix = (
            Matrix.Translation(pivot)
            @ Matrix.Rotation(math.radians(angle), 4, "Y")
            @ Matrix.Translation(-pivot)
            @ pose_bone.matrix
        )
    bpy.ops.object.mode_set(mode="OBJECT")
    bpy.context.view_layer.update()
    scene.render.filepath = str(output_path)
    bpy.ops.render.render(write_still=True)
    bpy.context.view_layer.objects.active = rig
    bpy.ops.object.mode_set(mode="POSE")
    for pose_bone in rig.pose.bones:
        pose_bone.matrix_basis.identity()
    bpy.ops.object.mode_set(mode="OBJECT")
    bpy.context.view_layer.update()
    return rest_output_path


def export_assets(obj, rig, output_dir):
    blend_path = output_dir / "original_adult_heroine_textured_rigged_v21.blend"
    glb_path = output_dir / "original_adult_heroine_textured_rigged_v21.glb"
    fbx_path = output_dir / "original_adult_heroine_textured_rigged_v21.fbx"

    for pose_bone in rig.pose.bones:
        pose_bone.rotation_mode = "QUATERNION"
        pose_bone.rotation_quaternion.identity()
    bpy.context.view_layer.update()
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
    turnaround = Path(args.turnaround).resolve()
    output_dir = Path(args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    if not input_glb.is_file():
        raise FileNotFoundError(input_glb)
    if not turnaround.is_file():
        raise FileNotFoundError(turnaround)

    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(input_glb))
    mesh_objects = [obj for obj in bpy.context.scene.objects if obj.type == "MESH"]
    if len(mesh_objects) != 1:
        raise RuntimeError(f"Expected one mesh, found {len(mesh_objects)}")
    character = mesh_objects[0]
    character.name = "OriginalAdultHeroine"

    before = mesh_metrics(character)
    clean_mesh(character)
    after = mesh_metrics(character)
    color_stats = apply_turnaround_colors(character, turnaround)
    rig = create_humanoid_rig(character)
    skirt_indices = apply_deterministic_weights(character, rig, turnaround)
    bridge_faces_removed = separate_arm_skirt_bridges(character, skirt_indices)

    preview_path = output_dir / "original_adult_heroine_textured_rigged_v21_pose.png"
    rest_preview_path = render_pose(character, rig, preview_path)
    blend_path, glb_path, fbx_path = export_assets(character, rig, output_dir)

    report = {
        "source_glb": str(input_glb),
        "source_turnaround": str(turnaround),
        "mesh_before": before,
        "mesh_after": after,
        "vertex_color": color_stats,
        "armature_bones": len(rig.data.bones),
        "vertex_groups": len(character.vertex_groups),
        "has_armature_modifier": any(
            modifier.type == "ARMATURE" for modifier in character.modifiers
        ),
        "arm_skirt_bridge_faces_removed": bridge_faces_removed,
        "outputs": {
            "blend": str(blend_path),
            "glb": str(glb_path),
            "fbx": str(fbx_path),
            "rest_preview": str(rest_preview_path),
            "pose_preview": str(preview_path),
        },
        "quality_gate": "REQUIRES_VISUAL_POSE_REVIEW",
    }
    report_path = output_dir / "original_adult_heroine_textured_rigged_v21_report.json"
    report_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
