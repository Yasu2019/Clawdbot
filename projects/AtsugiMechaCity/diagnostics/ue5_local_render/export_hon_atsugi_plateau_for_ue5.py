import sys
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import json
from pathlib import Path

import bpy
import mathutils


ROOT = Path(r"D:\Clawdbot_Docker_20260125")
SOURCE_BLEND = ROOT / "projects" / "AtsugiMechaCity" / "diagnostics" / "hon_atsugi_station" / "Hon_Atsugi_Station_Plateau_Mecha.blend"
OUT_DIR = ROOT / "projects" / "AtsugiMechaCity" / "diagnostics" / "ue5_local_render" / "plateau_export"
OUT_FBX = OUT_DIR / "Hon_Atsugi_Station_Plateau_CityOnly_UE5_CmScale.fbx"
REPORT = OUT_DIR / "hon_atsugi_plateau_ue5_export_report.json"


def mesh_objects():
    return [obj for obj in bpy.context.scene.objects if obj.type == "MESH"]


def join_named(name, objects):
    objects = [obj for obj in objects if obj and obj.type == "MESH"]
    if not objects:
        return None
    bpy.ops.object.select_all(action="DESELECT")
    for obj in objects:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = objects[0]
    bpy.ops.object.join()
    joined = bpy.context.view_layer.objects.active
    joined.name = name
    joined.data.name = name + "_Mesh"
    return joined


def set_origin_objects(objects):
    for obj in objects:
        obj.select_set(False)
    for obj in objects:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = objects[0] if objects else None


def world_bounds(objects):
    min_v = mathutils.Vector((float("inf"), float("inf"), float("inf")))
    max_v = mathutils.Vector((float("-inf"), float("-inf"), float("-inf")))
    for obj in objects:
        for corner in obj.bound_box:
            world = obj.matrix_world @ mathutils.Vector(corner)
            for axis in range(3):
                min_v[axis] = min(min_v[axis], world[axis])
                max_v[axis] = max(max_v[axis], world[axis])
    return min_v, max_v


def recenter_for_ue(objects):
    min_v, max_v = world_bounds(objects)
    offset = mathutils.Vector(((min_v.x + max_v.x) * 0.5, (min_v.y + max_v.y) * 0.5, min_v.z))
    for obj in objects:
        obj.location -= offset
    bpy.context.view_layer.update()
    return offset, world_bounds(objects)


def apply_transforms(objects):
    bpy.ops.object.select_all(action="DESELECT")
    for obj in objects:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = objects[0] if objects else None
    if objects:
        bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
        bpy.context.view_layer.update()


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.open_mainfile(filepath=str(SOURCE_BLEND))

    all_before = mesh_objects()
    buildings = [obj for obj in all_before if obj.name.startswith("HonAtsugi_Bldg_")]
    infra_prefixes = (
        "HonAtsugi_Roads",
        "HonAtsugi_EnhancedRoad_",
        "HonAtsugi_Sidewalk_",
        "HonAtsugi_LaneDash_",
        "HonAtsugi_Crosswalk_",
        "HonAtsugi_Rail_",
        "HonAtsugi_StationPlaza_",
    )
    infra = [obj for obj in all_before if obj.name.startswith(infra_prefixes)]
    terrain = [obj for obj in all_before if obj.name == "HonAtsugi_Terrain"]
    facade = [obj for obj in all_before if obj.name in {"HonAtsugi_Facade_Windows", "HonAtsugi_Facade_Signs"}]

    joined = []
    for name, group in [
        ("UE5_HonAtsugi_Terrain", terrain),
        ("UE5_HonAtsugi_Infrastructure", infra),
        ("UE5_HonAtsugi_Buildings", buildings),
        ("UE5_HonAtsugi_Facades", facade),
    ]:
        obj = join_named(name, group)
        if obj is not None:
            joined.append(obj)

    if not joined:
        raise RuntimeError("No mesh objects were prepared for UE5 export.")

    # Remove everything else so UE imports a compact, predictable scene.
    keep = set(joined)
    for obj in list(bpy.context.scene.objects):
        if obj not in keep:
            bpy.data.objects.remove(obj, do_unlink=True)

    recenter_offset, recentered_bounds = recenter_for_ue(joined)
    apply_transforms(joined)
    final_bounds = world_bounds(joined)
    set_origin_objects(joined)
    bpy.ops.export_scene.fbx(
        filepath=str(OUT_FBX),
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

    report = {
        "ok": OUT_FBX.exists() and OUT_FBX.stat().st_size > 0,
        "source_blend": str(SOURCE_BLEND),
        "output_fbx": str(OUT_FBX),
        "output_size": OUT_FBX.stat().st_size if OUT_FBX.exists() else 0,
        "input_mesh_count": len(all_before),
        "recenter_offset_m": [recenter_offset.x, recenter_offset.y, recenter_offset.z],
        "recentered_bounds_m": {
            "min": [recentered_bounds[0].x, recentered_bounds[0].y, recentered_bounds[0].z],
            "max": [recentered_bounds[1].x, recentered_bounds[1].y, recentered_bounds[1].z],
        },
        "final_bounds_m": {
            "min": [final_bounds[0].x, final_bounds[0].y, final_bounds[0].z],
            "max": [final_bounds[1].x, final_bounds[1].y, final_bounds[1].z],
        },
        "exported_meshes": [
            {
                "name": obj.name,
                "vertices": len(obj.data.vertices),
                "faces": len(obj.data.polygons),
                "materials": [mat.name for mat in obj.data.materials if mat is not None],
            }
            for obj in joined
        ],
        "api_cost": "none_local_blender_only",
    }
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
