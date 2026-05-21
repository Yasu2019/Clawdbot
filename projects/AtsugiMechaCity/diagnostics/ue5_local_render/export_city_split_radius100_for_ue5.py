import sys
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import json
import math
from pathlib import Path

import bpy
import mathutils


ROOT = Path(r"D:\Clawdbot_Docker_20260125")
SOURCE_BLEND = ROOT / "projects" / "AtsugiMechaCity" / "diagnostics" / "hon_atsugi_station" / "Hon_Atsugi_Station_Plateau_Mecha.blend"
OUT_DIR = ROOT / "projects" / "AtsugiMechaCity" / "diagnostics" / "ue5_local_render" / "plateau_export" / "radius100_split"
REPORT = OUT_DIR / "radius100_split_export_report.json"
RADIUS_M = 100.0


def dist_xy(v):
    return math.sqrt((v.x * v.x) + (v.y * v.y))


def mesh_objects():
    return [obj for obj in bpy.context.scene.objects if obj.type == "MESH"]


def object_center_xy(obj):
    corners = [obj.matrix_world @ mathutils.Vector(corner) for corner in obj.bound_box]
    min_v = mathutils.Vector((min(c.x for c in corners), min(c.y for c in corners), min(c.z for c in corners)))
    max_v = mathutils.Vector((max(c.x for c in corners), max(c.y for c in corners), max(c.z for c in corners)))
    return (min_v + max_v) * 0.5


def material_index(materials, mat):
    if mat is None:
        return 0
    for index, existing in enumerate(materials):
        if existing and existing.name == mat.name:
            return index
    materials.append(mat)
    return len(materials) - 1


def build_category_mesh(name, objects, radius_m, selection_mode="face", radius_pad_m=0.0):
    vertices = []
    faces = []
    face_materials = []
    materials = []
    source_objects = 0
    source_faces = 0

    for obj in objects:
        include_object = selection_mode == "object" and dist_xy(object_center_xy(obj)) <= (radius_m + radius_pad_m)
        if selection_mode == "object" and not include_object:
            continue
        source_objects += 1
        mesh = obj.data
        world = obj.matrix_world
        for polygon in mesh.polygons:
            coords = [world @ mesh.vertices[index].co for index in polygon.vertices]
            center = mathutils.Vector((0.0, 0.0, 0.0))
            for coord in coords:
                center += coord
            center /= max(1, len(coords))
            if selection_mode == "face" and dist_xy(center) > (radius_m + radius_pad_m):
                continue
            start = len(vertices)
            vertices.extend([(coord.x, coord.y, coord.z) for coord in coords])
            faces.append(tuple(range(start, start + len(coords))))
            mat = mesh.materials[polygon.material_index] if polygon.material_index < len(mesh.materials) else None
            face_materials.append(material_index(materials, mat))
            source_faces += 1

    if not faces:
        return None, {
            "name": name,
            "source_objects": source_objects,
            "faces": 0,
            "vertices": 0,
            "materials": [],
            "exported": False,
        }

    new_mesh = bpy.data.meshes.new(name + "_Mesh")
    new_mesh.from_pydata(vertices, [], faces)
    new_mesh.update()
    for mat in materials:
        new_mesh.materials.append(mat)
    for index, mat_index in enumerate(face_materials):
        new_mesh.polygons[index].material_index = mat_index
    obj = bpy.data.objects.new(name, new_mesh)
    bpy.context.collection.objects.link(obj)
    return obj, {
        "name": name,
        "source_objects": source_objects,
        "faces": len(faces),
        "vertices": len(vertices),
        "materials": [mat.name for mat in materials if mat is not None],
        "exported": True,
    }


def world_bounds(objects):
    min_v = mathutils.Vector((float("inf"), float("inf"), float("inf")))
    max_v = mathutils.Vector((float("-inf"), float("-inf"), float("-inf")))
    found = False
    for obj in objects:
        if obj is None:
            continue
        found = True
        for corner in obj.bound_box:
            world = obj.matrix_world @ mathutils.Vector(corner)
            for axis in range(3):
                min_v[axis] = min(min_v[axis], world[axis])
                max_v[axis] = max(max_v[axis], world[axis])
    if not found:
        return None, None
    return min_v, max_v


def recenter_vertices(objects):
    min_v, max_v = world_bounds(objects)
    offset = mathutils.Vector(((min_v.x + max_v.x) * 0.5, (min_v.y + max_v.y) * 0.5, min_v.z))
    for obj in objects:
        for vertex in obj.data.vertices:
            vertex.co -= offset
        obj.data.update()
    return offset


def export_one(obj, filepath):
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.export_scene.fbx(
        filepath=str(filepath),
        use_selection=True,
        apply_unit_scale=True,
        bake_space_transform=False,
        object_types={"MESH"},
        mesh_smooth_type="FACE",
        use_mesh_modifiers=True,
        add_leaf_bones=False,
        path_mode="COPY",
        embed_textures=True,
        global_scale=1.0,
    )


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.open_mainfile(filepath=str(SOURCE_BLEND))

    all_meshes = mesh_objects()
    categories = {
        "Terrain": ([obj for obj in all_meshes if obj.name == "HonAtsugi_Terrain"], "face", 30.0),
        "Road": ([obj for obj in all_meshes if obj.name.startswith(("HonAtsugi_Roads", "HonAtsugi_EnhancedRoad_"))], "face", 20.0),
        "RoadMarkings": ([obj for obj in all_meshes if obj.name.startswith(("HonAtsugi_LaneDash_", "HonAtsugi_Crosswalk_"))], "face", 12.0),
        "Sidewalk": ([obj for obj in all_meshes if obj.name.startswith(("HonAtsugi_Sidewalk_", "HonAtsugi_StationPlaza_"))], "face", 16.0),
        "Buildings": ([obj for obj in all_meshes if obj.name.startswith("HonAtsugi_Bldg_")], "object", 25.0),
        "Windows": ([obj for obj in all_meshes if obj.name == "HonAtsugi_Facade_Windows"], "face", 8.0),
        "Signs": ([obj for obj in all_meshes if obj.name == "HonAtsugi_Facade_Signs"], "face", 8.0),
        "Rails": ([obj for obj in all_meshes if obj.name.startswith("HonAtsugi_Rail_")], "face", 20.0),
    }

    built = []
    report_items = []
    for name, (objects, mode, pad) in categories.items():
        obj, item = build_category_mesh("UE5_R100_" + name, objects, RADIUS_M, mode, pad)
        report_items.append(item)
        if obj is not None:
            built.append(obj)

    if not built:
        raise RuntimeError("No radius100 meshes were built.")

    offset = recenter_vertices(built)
    min_v, max_v = world_bounds(built)

    outputs = {}
    for obj in built:
        category = obj.name.replace("UE5_R100_", "")
        path = OUT_DIR / (category + ".fbx")
        export_one(obj, path)
        outputs[category] = {
            "fbx": str(path),
            "size": path.stat().st_size if path.exists() else 0,
        }

    report = {
        "ok": True,
        "source_blend": str(SOURCE_BLEND),
        "output_dir": str(OUT_DIR),
        "radius_m": RADIUS_M,
        "origin_policy": "selected_bounds_center_xy_min_z",
        "recenter_offset_m": [offset.x, offset.y, offset.z],
        "bounds_m": {
            "min": [min_v.x, min_v.y, min_v.z],
            "max": [max_v.x, max_v.y, max_v.z],
        },
        "categories": report_items,
        "outputs": outputs,
        "api_cost": "none_local_blender_only",
    }
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
