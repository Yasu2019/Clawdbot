import json
import math
from pathlib import Path

import bpy
import mathutils
from mathutils import bvhtree
from mathutils import kdtree


ROOT = Path(r"D:\Clawdbot_Docker_20260125")
BLEND_PATH = ROOT / "Gundam" / "Atsugi_Front_Final.blend"
TERRAIN_OBJ = ROOT / "apps" / "agi_designer" / "viewer" / "exports" / "Atsugi_Terrain.obj"
OUT_DIR = ROOT / "projects" / "AtsugiMechaCity" / "diagnostics" / "atsugi_terrain_grounding"
OUTPUT_BLEND = OUT_DIR / "Atsugi_Terrain_Grounded_Subset.blend"
OUTPUT_PNG = OUT_DIR / "Atsugi_Terrain_Grounded_Subset_Close.png"
OUTPUT_WIDE_PNG = OUT_DIR / "Atsugi_Terrain_Grounded_Subset_Wide.png"
OUTPUT_JSON = OUT_DIR / "atsugi_terrain_grounding_subset_report.json"

MECHA_NAME = "Zaku_Armature"
TARGET_HEIGHT_M = 18.0
UPRIGHT_ROTATION_DEGREES = (90.0, 0.0, 0.0)
RAY_MARGIN = 5000.0
ANCHOR_BUILDING_NAME = "Bldg"
BUILDING_TEST_LIMIT = 5
BUILDING_SUBSET_SELECTION = "raycast_hit"
ADJUST_BUILDINGS = "subset"
MAX_BUILDING_HIT_XY_DISTANCE = 0.001
MAX_BUILDING_ABS_DELTA_Z = 40.0
SNAP_MECHA_TO_NEAREST_TERRAIN_VERTEX = True
ALIGN_TERRAIN_LIKE_WEB_VIEWER = True
SNAP_TERRAIN_PATCH_TO_CITY_CENTER = True


def ensure_dir():
    OUT_DIR.mkdir(parents=True, exist_ok=True)


def descendants(obj):
    items = []
    pending = list(obj.children)
    while pending:
        child = pending.pop()
        items.append(child)
        pending.extend(child.children)
    return items


def world_bounds(objects):
    min_v = mathutils.Vector((float("inf"), float("inf"), float("inf")))
    max_v = mathutils.Vector((float("-inf"), float("-inf"), float("-inf")))
    found = False
    for obj in objects:
        if obj.type != "MESH":
            continue
        found = True
        for corner in obj.bound_box:
            world_corner = obj.matrix_world @ mathutils.Vector(corner)
            for axis in range(3):
                min_v[axis] = min(min_v[axis], world_corner[axis])
                max_v[axis] = max(max_v[axis], world_corner[axis])
    if not found:
        raise RuntimeError("No mesh objects found for bounds calculation.")
    return min_v, max_v


def import_obj(path):
    before = set(bpy.context.scene.objects)
    if hasattr(bpy.ops.wm, "obj_import"):
        bpy.ops.wm.obj_import(filepath=str(path))
    else:
        bpy.ops.import_scene.obj(filepath=str(path))
    return [obj for obj in bpy.context.scene.objects if obj not in before]


def material(name, color):
    mat = bpy.data.materials.new(name)
    mat.diffuse_color = color
    return mat


def material_once(name, color):
    mat = bpy.data.materials.get(name)
    if mat is None:
        mat = bpy.data.materials.new(name)
    mat.diffuse_color = color
    return mat


def align_terrain_to_city(terrain_objects, city_min, city_max):
    bpy.context.view_layer.update()
    raw_min = mathutils.Vector((float("inf"), float("inf"), float("inf")))
    raw_max = mathutils.Vector((float("-inf"), float("-inf"), float("-inf")))
    for obj in terrain_objects:
        for vertex in obj.data.vertices:
            co = vertex.co
            raw_min.x = min(raw_min.x, co.x)
            raw_min.y = min(raw_min.y, co.y)
            raw_min.z = min(raw_min.z, co.z)
            raw_max.x = max(raw_max.x, co.x)
            raw_max.y = max(raw_max.y, co.y)
            raw_max.z = max(raw_max.z, co.z)

    if raw_max.x == raw_min.x or raw_max.y == raw_min.y or raw_max.z == raw_min.z:
        raise RuntimeError("Terrain bounds are degenerate; cannot align to city.")

    raw_center = (raw_min + raw_max) / 2.0
    city_center = (city_min + city_max) / 2.0
    city_size = city_max - city_min
    raw_size = raw_max - raw_min
    if ALIGN_TERRAIN_LIKE_WEB_VIEWER:
        scale_x = 1.0
        scale_y = 1.0
        scale_z = 1.0
    else:
        scale_x = city_size.x / raw_size.x
        scale_y = city_size.y / raw_size.z
        scale_z = (scale_x + scale_y) / 2.0

    for obj in terrain_objects:
        obj.location = (0.0, 0.0, 0.0)
        obj.rotation_euler = (0.0, 0.0, 0.0)
        obj.scale = (1.0, 1.0, 1.0)
        for vertex in obj.data.vertices:
            raw = vertex.co.copy()
            if ALIGN_TERRAIN_LIKE_WEB_VIEWER:
                vertex.co.x = city_center.x + (raw.x - raw_center.x)
                vertex.co.y = city_center.y + (raw.z - raw_center.z)
                vertex.co.z = raw.y
            else:
                vertex.co.x = city_min.x + (raw.x - raw_min.x) * scale_x
                vertex.co.y = city_min.y + (raw.z - raw_min.z) * scale_y
                vertex.co.z = city_min.z + (raw.y - raw_min.y) * scale_z
        obj.data.update()
    bpy.context.view_layer.update()

    aligned_min, aligned_max = world_bounds(terrain_objects)
    return {
        "raw_min": [round(float(v), 6) for v in raw_min],
        "raw_max": [round(float(v), 6) for v in raw_max],
        "method": "web_viewer_center_no_scale" if ALIGN_TERRAIN_LIKE_WEB_VIEWER else "bbox_scale_to_city",
        "scale": [round(float(scale_x), 9), round(float(scale_y), 9), round(float(scale_z), 9)],
        "aligned_min": [round(float(v), 6) for v in aligned_min],
        "aligned_max": [round(float(v), 6) for v in aligned_max],
    }


def build_terrain_xy_sampler(terrain_objects):
    total_vertices = sum(len(obj.data.vertices) for obj in terrain_objects if obj.type == "MESH")
    tree = kdtree.KDTree(total_vertices)
    heights = []
    object_names = []
    coords = []
    index = 0
    for obj in terrain_objects:
        matrix = obj.matrix_world
        for vertex in obj.data.vertices:
            world = matrix @ vertex.co
            tree.insert((world.x, world.y, 0.0), index)
            heights.append(float(world.z))
            object_names.append(obj.name)
            coords.append((float(world.x), float(world.y), float(world.z)))
            index += 1
    tree.balance()
    return {
        "tree": tree,
        "heights": heights,
        "object_names": object_names,
        "coords": coords,
        "vertices": total_vertices,
    }


def terrain_height_by_nearest_xy(sampler, x, y):
    _co, index, distance = sampler["tree"].find((x, y, 0.0))
    return sampler["heights"][index], sampler["object_names"][index], float(distance), sampler["coords"][index]


def build_terrain_bvhs(terrain_objects, depsgraph):
    items = []
    for obj in terrain_objects:
        vertices = [obj.matrix_world @ vertex.co for vertex in obj.data.vertices]
        polygons = [tuple(poly.vertices) for poly in obj.data.polygons]
        tree = bvhtree.BVHTree.FromPolygons(vertices, polygons, all_triangles=False)
        if tree is not None:
            items.append({"name": obj.name, "tree": tree})
    return items


def terrain_height_at(depsgraph, terrain_objects, x, y, z_min, z_max, sampler=None, bvhs=None):
    origin = mathutils.Vector((x, y, z_max + RAY_MARGIN))
    end = mathutils.Vector((x, y, z_min - RAY_MARGIN))
    direction = (end - origin).normalized()
    distance = (end - origin).length
    best = None
    best_obj = None
    if bvhs:
        for item in bvhs:
            location, _normal, _face_index, _hit_distance = item["tree"].ray_cast(origin, direction, distance)
            if location is None:
                continue
            if best is None or location.z > best.z:
                best = location
                best_obj = item["name"]
    else:
        for obj in terrain_objects:
            matrix_inv = obj.matrix_world.inverted()
            local_origin = matrix_inv @ origin
            local_end = matrix_inv @ end
            local_ray = local_end - local_origin
            local_distance = local_ray.length
            if local_distance <= 0:
                continue
            local_direction = local_ray.normalized()
            hit, location, _normal, _face_index = obj.evaluated_get(depsgraph).ray_cast(
                local_origin,
                local_direction,
                distance=local_distance,
            )
            if not hit:
                continue
            world_location = obj.matrix_world @ location
            if best is None or world_location.z > best.z:
                best = world_location
                best_obj = obj.name
    if best is None:
        if sampler is None:
            return None, None, None, None
        height, obj_name, distance, coord = terrain_height_by_nearest_xy(sampler, x, y)
        return height, obj_name, distance, coord
    return float(best.z), best_obj, 0.0, (float(x), float(y), float(best.z))


def set_object_bottom_to_z(obj, target_z):
    min_v, _max_v = world_bounds([obj])
    delta_z = target_z - min_v.z
    obj.location.z += delta_z
    return float(delta_z)


def set_group_bottom_to_z(root, mesh_objects, target_z):
    min_v, _max_v = world_bounds(mesh_objects)
    delta_z = target_z - min_v.z
    root.location.z += delta_z
    return float(delta_z)


def look_at(obj, target):
    direction = mathutils.Vector(target) - obj.location
    obj.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()


def normalize_mecha(mecha, mecha_parts):
    mecha.rotation_euler = tuple(math.radians(v) for v in UPRIGHT_ROTATION_DEGREES)
    bpy.context.view_layer.update()
    min_v, max_v = world_bounds(mecha_parts)
    current_height = max_v.z - min_v.z
    if current_height <= 0:
        raise RuntimeError("Mecha height is zero; cannot scale.")
    scale_factor = TARGET_HEIGHT_M / current_height
    mecha.scale = tuple(component * scale_factor for component in mecha.scale)
    bpy.context.view_layer.update()
    return float(scale_factor)


def find_anchor_building(building_meshes, preferred_name=None):
    if preferred_name:
        for obj in building_meshes:
            if obj.name == preferred_name:
                min_v, max_v = world_bounds([obj])
                center = (min_v + max_v) / 2.0
                return {
                    "object": obj,
                    "name": obj.name,
                    "center": center,
                    "street_z": float(min_v.z),
                    "height": float(max_v.z - min_v.z),
                    "bounds_min": min_v,
                    "bounds_max": max_v,
                }
    for obj in building_meshes:
        min_v, max_v = world_bounds([obj])
        if max_v.z - min_v.z > 5.0:
            center = (min_v + max_v) / 2.0
            return {
                "object": obj,
                "name": obj.name,
                "center": center,
                "street_z": float(min_v.z),
                "height": float(max_v.z - min_v.z),
                "bounds_min": min_v,
                "bounds_max": max_v,
            }
    min_v, max_v = world_bounds(building_meshes)
    return {
        "object": None,
        "name": None,
        "center": (min_v + max_v) / 2.0,
        "street_z": float(min_v.z),
        "height": float(max_v.z - min_v.z),
        "bounds_min": min_v,
        "bounds_max": max_v,
    }


def select_building_subset(building_meshes, anchor, limit):
    ranked = []
    anchor_center = anchor["center"]
    for obj in building_meshes:
        min_v, max_v = world_bounds([obj])
        height = max_v.z - min_v.z
        if height <= 1.0:
            continue
        center = (min_v + max_v) / 2.0
        distance = math.hypot(center.x - anchor_center.x, center.y - anchor_center.y)
        ranked.append({
            "object": obj,
            "center": center,
            "bounds_min": min_v,
            "bounds_max": max_v,
            "height": height,
            "distance_to_anchor": distance,
        })
    ranked.sort(key=lambda item: item["distance_to_anchor"])
    return ranked[:limit]


def find_building_terrain_candidates(
    depsgraph,
    terrain_meshes,
    terrain_min,
    terrain_max,
    terrain_sampler,
    terrain_bvhs,
    building_meshes,
    anchor,
    limit,
):
    candidates = []
    skipped_counts = {
        "no_terrain_hit": 0,
        "nearest_terrain_sample_too_far": 0,
        "delta_z_exceeds_guard": 0,
    }
    for obj in building_meshes:
        min_v, max_v = world_bounds([obj])
        height = max_v.z - min_v.z
        if height <= 1.0:
            continue
        center = (min_v + max_v) / 2.0
        terrain_z, hit_obj, hit_distance, _hit_coord = terrain_height_at(
            depsgraph,
            terrain_meshes,
            center.x,
            center.y,
            terrain_min.z,
            terrain_max.z,
            terrain_sampler,
            terrain_bvhs,
        )
        if terrain_z is None:
            skipped_counts["no_terrain_hit"] += 1
            continue
        planned_delta_z = terrain_z - min_v.z
        if hit_distance is None or hit_distance > MAX_BUILDING_HIT_XY_DISTANCE:
            skipped_counts["nearest_terrain_sample_too_far"] += 1
            continue
        if abs(planned_delta_z) > MAX_BUILDING_ABS_DELTA_Z:
            skipped_counts["delta_z_exceeds_guard"] += 1
            continue
        candidates.append({
            "object": obj,
            "center": center,
            "bounds_min": min_v,
            "bounds_max": max_v,
            "height": height,
            "distance_to_anchor": math.hypot(center.x - anchor["center"].x, center.y - anchor["center"].y),
            "terrain_z": terrain_z,
            "hit_obj": hit_obj,
            "hit_distance": hit_distance,
            "planned_delta_z": planned_delta_z,
        })
    candidates.sort(key=lambda item: (abs(item["planned_delta_z"]), item["distance_to_anchor"]))
    return candidates[:limit], len(candidates), skipped_counts


def offset_terrain_z(terrain_objects, delta_z):
    for obj in terrain_objects:
        for vertex in obj.data.vertices:
            vertex.co.z += delta_z
        obj.data.update()
    bpy.context.view_layer.update()


def offset_terrain_xy(terrain_objects, delta_x, delta_y):
    for obj in terrain_objects:
        for vertex in obj.data.vertices:
            vertex.co.x += delta_x
            vertex.co.y += delta_y
        obj.data.update()
    bpy.context.view_layer.update()


def best_terrain_z_grid(depsgraph, terrain_meshes, terrain_min, terrain_max, center_x, center_y, sampler, bvhs):
    best = None
    samples = []
    for dx in range(-100, 101, 50):
        for dy in range(-100, 101, 50):
            x = center_x + dx
            y = center_y + dy
            z, obj_name, hit_distance, coord = terrain_height_at(
                depsgraph,
                terrain_meshes,
                x,
                y,
                terrain_min.z,
                terrain_max.z,
                sampler,
                bvhs,
            )
            samples.append({
                "x": round(float(x), 6),
                "y": round(float(y), 6),
                "z": None if z is None else round(float(z), 6),
                "distance": None if hit_distance is None else round(float(hit_distance), 6),
            })
            if z is None:
                continue
            if best is None or z > best["z"]:
                best = {"z": float(z), "obj": obj_name, "distance": float(hit_distance or 0.0), "coord": coord}
    return best, samples


def add_camera_and_light(target_center, terrain_z):
    camera_data = bpy.data.cameras.new("Terrain_Grounding_Diagnostic_Camera")
    camera = bpy.data.objects.new("Terrain_Grounding_Diagnostic_Camera", camera_data)
    bpy.context.collection.objects.link(camera)
    bpy.context.scene.camera = camera
    camera.data.type = "ORTHO"
    camera.data.ortho_scale = 260
    camera.location = (
        target_center.x + 180,
        target_center.y - 260,
        terrain_z + 140,
    )
    camera.data.clip_end = 20000
    look_at(camera, (target_center.x, target_center.y, terrain_z + TARGET_HEIGHT_M * 0.35))

    sun_data = bpy.data.lights.new("Terrain_Grounding_Diagnostic_Sun", type="SUN")
    sun = bpy.data.objects.new("Terrain_Grounding_Diagnostic_Sun", sun_data)
    bpy.context.collection.objects.link(sun)
    sun.location = (target_center.x - 80, target_center.y - 120, terrain_z + 160)
    sun.data.energy = 2.2


def render_diagnostic(path, target_center, terrain_z, ortho_scale):
    add_camera_and_light(target_center, terrain_z)
    bpy.context.scene.camera.data.ortho_scale = ortho_scale
    bpy.context.scene.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)


def main():
    ensure_dir()
    bpy.ops.wm.open_mainfile(filepath=str(BLEND_PATH))

    building_meshes = [
        obj for obj in bpy.data.objects
        if obj.type == "MESH" and obj.name.startswith("Bldg")
    ]
    if not building_meshes:
        raise RuntimeError("No Bldg meshes found. Check the Atsugi map import.")

    imported = import_obj(TERRAIN_OBJ)
    terrain_meshes = [obj for obj in imported if obj.type == "MESH"]
    if not terrain_meshes:
        raise RuntimeError(f"No terrain mesh imported from {TERRAIN_OBJ}.")
    for obj in terrain_meshes:
        obj.name = f"Terrain_Raycast_{obj.name}"
        obj.hide_render = False
        obj.hide_viewport = False
        obj.data.materials.clear()
        obj.data.materials.append(material("Terrain_Diagnostic_Matte", (0.22, 0.34, 0.25, 1.0)))

    city_min_before, city_max_before = world_bounds(building_meshes)
    terrain_alignment = align_terrain_to_city(terrain_meshes, city_min_before, city_max_before)
    bpy.context.view_layer.update()
    depsgraph = bpy.context.evaluated_depsgraph_get()
    terrain_min, terrain_max = world_bounds(terrain_meshes)
    terrain_sampler = build_terrain_xy_sampler(terrain_meshes)
    terrain_bvhs = build_terrain_bvhs(terrain_meshes, depsgraph)
    city_center = (city_min_before + city_max_before) / 2.0
    anchor = find_anchor_building(building_meshes, ANCHOR_BUILDING_NAME)
    terrain_horizontal_offset = (0.0, 0.0)

    if SNAP_TERRAIN_PATCH_TO_CITY_CENTER:
        _height, _obj_name, nearest_distance, nearest_coord = terrain_height_by_nearest_xy(
            terrain_sampler,
            city_center.x,
            city_center.y,
        )
        terrain_horizontal_offset = (
            float(city_center.x - nearest_coord[0]),
            float(city_center.y - nearest_coord[1]),
        )
        offset_terrain_xy(terrain_meshes, terrain_horizontal_offset[0], terrain_horizontal_offset[1])
        depsgraph = bpy.context.evaluated_depsgraph_get()
        terrain_min, terrain_max = world_bounds(terrain_meshes)
        terrain_sampler = build_terrain_xy_sampler(terrain_meshes)
        terrain_bvhs = build_terrain_bvhs(terrain_meshes, depsgraph)

    best_grid_hit, terrain_grid_samples = best_terrain_z_grid(
        depsgraph,
        terrain_meshes,
        terrain_min,
        terrain_max,
        city_center.x,
        city_center.y,
        terrain_sampler,
        terrain_bvhs,
    )
    terrain_vertical_offset = 0.0
    if best_grid_hit is not None:
        terrain_vertical_offset = anchor["street_z"] - best_grid_hit["z"] - 1.0
        offset_terrain_z(terrain_meshes, terrain_vertical_offset)
        depsgraph = bpy.context.evaluated_depsgraph_get()
        terrain_min, terrain_max = world_bounds(terrain_meshes)
        terrain_sampler = build_terrain_xy_sampler(terrain_meshes)
        terrain_bvhs = build_terrain_bvhs(terrain_meshes, depsgraph)

    terrain_z_center, terrain_hit_obj, terrain_distance_center, terrain_coord_center = terrain_height_at(
        depsgraph,
        terrain_meshes,
        city_center.x,
        city_center.y,
        terrain_min.z,
        terrain_max.z,
        terrain_sampler,
        terrain_bvhs,
    )
    if terrain_z_center is None:
        raise RuntimeError("Terrain raycast failed at city center. Coordinate systems may not overlap.")

    building_reports = []
    adjusted_count = 0
    building_candidate_summary = None
    if ADJUST_BUILDINGS == "subset":
        if BUILDING_SUBSET_SELECTION == "raycast_hit":
            subset, candidate_count, skipped_counts = find_building_terrain_candidates(
                depsgraph,
                terrain_meshes,
                terrain_min,
                terrain_max,
                terrain_sampler,
                terrain_bvhs,
                building_meshes,
                anchor,
                BUILDING_TEST_LIMIT,
            )
            building_candidate_summary = {
                "selection": BUILDING_SUBSET_SELECTION,
                "raycast_hit_candidate_count": candidate_count,
                "skipped_counts": skipped_counts,
            }
        else:
            subset = select_building_subset(building_meshes, anchor, BUILDING_TEST_LIMIT)
            building_candidate_summary = {"selection": BUILDING_SUBSET_SELECTION}
        for item in subset:
            obj = item["object"]
            min_v = item["bounds_min"]
            max_v = item["bounds_max"]
            center = item["center"]
            if "terrain_z" in item:
                terrain_z = item["terrain_z"]
                hit_obj = item["hit_obj"]
                hit_distance = item["hit_distance"]
            else:
                terrain_z, hit_obj, hit_distance, _hit_coord = terrain_height_at(
                    depsgraph,
                    terrain_meshes,
                    center.x,
                    center.y,
                    terrain_min.z,
                    terrain_max.z,
                    terrain_sampler,
                    terrain_bvhs,
                )
            if terrain_z is None:
                building_reports.append({
                    "name": obj.name,
                    "status": "skipped",
                    "reason": "no_terrain_hit",
                    "center": [round(float(v), 6) for v in center],
                    "height": round(float(item["height"]), 6),
                    "distance_to_anchor": round(float(item["distance_to_anchor"]), 6),
                })
                continue
            planned_delta_z = terrain_z - min_v.z
            status = "moved"
            reason = None
            if hit_distance is None or hit_distance > MAX_BUILDING_HIT_XY_DISTANCE:
                status = "skipped"
                reason = "nearest_terrain_sample_too_far"
            elif abs(planned_delta_z) > MAX_BUILDING_ABS_DELTA_Z:
                status = "skipped"
                reason = "delta_z_exceeds_guard"

            delta_z = 0.0
            if status == "moved":
                delta_z = set_object_bottom_to_z(obj, terrain_z)
                obj.data.materials.clear()
                obj.data.materials.append(material_once("Moved_Building_Diagnostic_Cyan", (0.2, 0.72, 0.9, 1.0)))
                adjusted_count += 1
            building_reports.append({
                "name": obj.name,
                "status": status,
                "reason": reason,
                "terrain_z": round(terrain_z, 6),
                "street_z_before": round(float(min_v.z), 6),
                "planned_delta_z": round(planned_delta_z, 6),
                "delta_z": round(delta_z, 6),
                "hit_obj": hit_obj,
                "hit_xy_distance": round(hit_distance or 0.0, 6),
                "center": [round(float(v), 6) for v in center],
                "height": round(float(item["height"]), 6),
                "distance_to_anchor": round(float(item["distance_to_anchor"]), 6),
            })
        bpy.context.view_layer.update()
    elif ADJUST_BUILDINGS:
        raise RuntimeError("Only ADJUST_BUILDINGS='subset' or False is supported in this diagnostic script.")
    else:
        building_reports.append({
            "status": "skipped",
            "reason": "building terrain raycast is not reliable after bbox alignment; buildings left at source elevation",
        })

    bpy.context.view_layer.update()
    mecha = bpy.data.objects.get(MECHA_NAME)
    mecha_report = None
    if mecha:
        mecha_parts = [obj for obj in descendants(mecha) if obj.type == "MESH"]
        if mecha_parts:
            scale_factor = normalize_mecha(mecha, mecha_parts)
            mecha.location.x = anchor["center"].x + 20.0
            mecha.location.y = anchor["center"].y + 20.0
            bpy.context.view_layer.update()
            terrain_z, hit_obj, hit_distance, hit_coord = terrain_height_at(
                depsgraph,
                terrain_meshes,
                mecha.location.x,
                mecha.location.y,
                terrain_min.z,
                terrain_max.z,
                terrain_sampler,
                terrain_bvhs,
            )
            if SNAP_MECHA_TO_NEAREST_TERRAIN_VERTEX and hit_distance and hit_distance > 0.001 and hit_coord:
                mecha.location.x = hit_coord[0]
                mecha.location.y = hit_coord[1]
                bpy.context.view_layer.update()
                terrain_z, hit_obj, hit_distance, hit_coord = terrain_height_at(
                    depsgraph,
                    terrain_meshes,
                    mecha.location.x,
                    mecha.location.y,
                    terrain_min.z,
                    terrain_max.z,
                    terrain_sampler,
                    terrain_bvhs,
                )
            delta_z = set_group_bottom_to_z(mecha, mecha_parts, terrain_z)
            bpy.context.view_layer.update()
            mecha_min, mecha_max = world_bounds(mecha_parts)
            mecha_report = {
                "name": mecha.name,
                "scale_factor": round(scale_factor, 6),
                "terrain_z": round(terrain_z, 6),
                "delta_z": round(delta_z, 6),
                "hit_obj": hit_obj,
                "hit_xy_distance": round(hit_distance or 0.0, 6),
                "snap_to_nearest_terrain_vertex": SNAP_MECHA_TO_NEAREST_TERRAIN_VERTEX,
                "placement_xy": [round(float(mecha.location.x), 6), round(float(mecha.location.y), 6)],
                "bounds_min": [round(float(v), 6) for v in mecha_min],
                "bounds_max": [round(float(v), 6) for v in mecha_max],
            }

    city_min_after, city_max_after = world_bounds(building_meshes)
    moved_or_tested_buildings = [
        bpy.data.objects.get(item["name"]) for item in building_reports
        if item.get("name") and bpy.data.objects.get(item["name"])
    ]
    if moved_or_tested_buildings:
        subset_min, subset_max = world_bounds(moved_or_tested_buildings)
        target_center = (subset_min + subset_max) / 2.0
        camera_ground_z = min(item.get("terrain_z", terrain_z_center) for item in building_reports if item.get("terrain_z") is not None)
    elif mecha_report:
        target_center = (mathutils.Vector(mecha_report["bounds_min"]) + mathutils.Vector(mecha_report["bounds_max"])) / 2.0
        camera_ground_z = mecha_report["terrain_z"]
    else:
        target_center = mathutils.Vector((city_center.x, city_center.y, terrain_z_center))
        camera_ground_z = terrain_z_center

    bpy.context.scene.render.engine = "BLENDER_WORKBENCH"
    bpy.context.scene.display.shading.light = "STUDIO"
    bpy.context.scene.display.shading.color_type = "MATERIAL"
    bpy.context.scene.render.resolution_x = 1280
    bpy.context.scene.render.resolution_y = 720
    bpy.context.scene.render.filepath = str(OUTPUT_PNG)
    if bpy.context.scene.world:
        bpy.context.scene.world.color = (0.55, 0.62, 0.7)

    audit = {
        "blend_path": str(BLEND_PATH),
        "terrain_obj": str(TERRAIN_OBJ),
        "output_blend": str(OUTPUT_BLEND),
        "output_png": str(OUTPUT_PNG),
        "output_wide_png": str(OUTPUT_WIDE_PNG),
        "building_count": len(building_meshes),
        "building_adjustment_enabled": ADJUST_BUILDINGS,
        "building_subset_selection": BUILDING_SUBSET_SELECTION,
        "building_test_limit": BUILDING_TEST_LIMIT,
        "building_hit_xy_distance_guard": MAX_BUILDING_HIT_XY_DISTANCE,
        "building_abs_delta_z_guard": MAX_BUILDING_ABS_DELTA_Z,
        "building_adjusted_count": adjusted_count,
        "building_candidate_summary": building_candidate_summary,
        "city_bounds_before": {
            "min": [round(float(v), 6) for v in city_min_before],
            "max": [round(float(v), 6) for v in city_max_before],
        },
        "city_bounds_after": {
            "min": [round(float(v), 6) for v in city_min_after],
            "max": [round(float(v), 6) for v in city_max_after],
        },
        "terrain_bounds": {
            "min": [round(float(v), 6) for v in terrain_min],
            "max": [round(float(v), 6) for v in terrain_max],
        },
        "terrain_alignment": terrain_alignment,
        "anchor_building": {
            "name": anchor["name"],
            "center": [round(float(v), 6) for v in anchor["center"]],
            "street_z": round(float(anchor["street_z"]), 6),
            "height": round(float(anchor["height"]), 6),
            "bounds_min": [round(float(v), 6) for v in anchor["bounds_min"]],
            "bounds_max": [round(float(v), 6) for v in anchor["bounds_max"]],
        },
        "terrain_horizontal_snap_enabled": SNAP_TERRAIN_PATCH_TO_CITY_CENTER,
        "terrain_horizontal_offset": [round(float(v), 6) for v in terrain_horizontal_offset],
        "terrain_vertical_offset": round(float(terrain_vertical_offset), 6),
        "terrain_grid_best_before_vertical_offset": None if best_grid_hit is None else {
            "z": round(float(best_grid_hit["z"]), 6),
            "distance": round(float(best_grid_hit["distance"]), 6),
            "coord": [round(float(v), 6) for v in best_grid_hit["coord"]],
        },
        "terrain_grid_samples": terrain_grid_samples,
        "city_center": [round(float(v), 6) for v in city_center],
        "terrain_z_at_city_center": round(float(terrain_z_center), 6),
        "terrain_hit_obj_at_city_center": terrain_hit_obj,
        "terrain_hit_xy_distance_at_city_center": round(terrain_distance_center or 0.0, 6),
        "terrain_coord_at_or_nearest_city_center": [round(float(v), 6) for v in terrain_coord_center],
        "terrain_sampler_vertices": terrain_sampler["vertices"],
        "terrain_bvh_count": len(terrain_bvhs),
        "mecha": mecha_report,
        "building_report_sample": building_reports[:50],
    }
    OUTPUT_JSON.write_text(json.dumps(audit, ensure_ascii=False, indent=2), encoding="utf-8")

    bpy.ops.wm.save_as_mainfile(filepath=str(OUTPUT_BLEND))
    render_diagnostic(OUTPUT_PNG, target_center, camera_ground_z, 220)
    render_diagnostic(OUTPUT_WIDE_PNG, city_center, terrain_z_center, 900)
    print(json.dumps({"ok": True, **audit}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
