import sys
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import json
import time
from pathlib import Path

import unreal


ROOT = Path(r"D:\Clawdbot_Docker_20260125")
OUT_DIR = ROOT / "projects" / "AtsugiMechaCity" / "diagnostics" / "ue5_local_render"
FBX_PATH = OUT_DIR / "plateau_export" / "Hon_Atsugi_Station_Plateau_CityOnly_UE5_CmScale.fbx"
OUTPUT_NAME = "Atsugi_UE5_plateau_city_real_asset_cmscale.exr"
OUTPUT_PATH = OUT_DIR / OUTPUT_NAME
REPORT = OUT_DIR / "ue5_import_render_plateau_fbx_report.json"
DESTINATION = "/Game/CodexGenerated/PlateauHonAtsugiCityOnlyCmScale"


def log(message):
    unreal.log("[UE5PlateauFBX] " + message)
    print("[UE5PlateauFBX] " + message)


def set_first_existing_property(obj, names, value):
    for name in names:
        try:
            obj.set_editor_property(name, value)
            return name
        except Exception:
            pass
    return None


def import_fbx():
    if not FBX_PATH.exists():
        raise RuntimeError("FBX not found: {0}".format(FBX_PATH))

    unreal.EditorAssetLibrary.make_directory(DESTINATION)
    options = unreal.FbxImportUI()
    options.set_editor_property("import_mesh", True)
    options.set_editor_property("import_textures", True)
    options.set_editor_property("import_materials", True)
    options.set_editor_property("import_as_skeletal", False)
    options.set_editor_property("create_physics_asset", False)
    options.static_mesh_import_data.set_editor_property("combine_meshes", True)
    options.static_mesh_import_data.set_editor_property("generate_lightmap_u_vs", True)
    options.static_mesh_import_data.set_editor_property("auto_generate_collision", False)

    task = unreal.AssetImportTask()
    task.set_editor_property("filename", str(FBX_PATH))
    task.set_editor_property("destination_path", DESTINATION)
    task.set_editor_property("destination_name", "Hon_Atsugi_Station_Plateau_CityOnly_UE5_CmScale")
    task.set_editor_property("replace_existing", True)
    task.set_editor_property("automated", True)
    task.set_editor_property("save", True)
    task.set_editor_property("options", options)

    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    paths = list(task.get_editor_property("imported_object_paths") or [])
    meshes = []
    for path in paths:
        asset = unreal.EditorAssetLibrary.load_asset(path)
        if isinstance(asset, unreal.StaticMesh):
            meshes.append(asset)
    if meshes:
        return meshes[0], paths

    fallback = unreal.EditorAssetLibrary.load_asset(DESTINATION + "/Hon_Atsugi_Station_Plateau_CityOnly_UE5_CmScale")
    if isinstance(fallback, unreal.StaticMesh):
        return fallback, paths
    raise RuntimeError("UE5 import finished but no StaticMesh asset was found. Imported paths: {0}".format(paths))


def create_color_material(name, color, roughness=0.9, emissive=None):
    asset_dir = "/Game/CodexGenerated/PlateauRenderMaterials"
    asset_path = asset_dir + "/" + name
    existing = unreal.EditorAssetLibrary.load_asset(asset_path)
    if existing is not None:
        return existing
    unreal.EditorAssetLibrary.make_directory(asset_dir)
    mat = unreal.AssetToolsHelpers.get_asset_tools().create_asset(name, asset_dir, unreal.Material, unreal.MaterialFactoryNew())
    if mat is None:
        return None

    base = unreal.MaterialEditingLibrary.create_material_expression(mat, unreal.MaterialExpressionConstant3Vector, -420, 0)
    base.set_editor_property("constant", color)
    unreal.MaterialEditingLibrary.connect_material_property(base, "", unreal.MaterialProperty.MP_BASE_COLOR)

    rough = unreal.MaterialEditingLibrary.create_material_expression(mat, unreal.MaterialExpressionConstant, -420, 180)
    rough.set_editor_property("r", roughness)
    unreal.MaterialEditingLibrary.connect_material_property(rough, "", unreal.MaterialProperty.MP_ROUGHNESS)

    if emissive is not None:
        em = unreal.MaterialEditingLibrary.create_material_expression(mat, unreal.MaterialExpressionConstant3Vector, -420, 330)
        em.set_editor_property("constant", emissive)
        unreal.MaterialEditingLibrary.connect_material_property(em, "", unreal.MaterialProperty.MP_EMISSIVE_COLOR)

    unreal.MaterialEditingLibrary.recompile_material(mat)
    unreal.EditorAssetLibrary.save_asset(asset_path, only_if_is_dirty=False)
    return mat


def set_mat(actor, mat):
    component = actor.get_component_by_class(unreal.StaticMeshComponent)
    if component and mat is not None:
        component.set_material(0, mat)


def apply_plateau_materials(actor):
    component = actor.get_component_by_class(unreal.StaticMeshComponent)
    if component is None:
        return []
    mats = {
        "terrain": create_color_material("Codex_Mat_PLATEAU_Terrain", unreal.LinearColor(0.16, 0.24, 0.15, 1.0), 0.92),
        "building": create_color_material("Codex_Mat_PLATEAU_Building", unreal.LinearColor(0.50, 0.52, 0.49, 1.0), 0.84),
        "road": create_color_material("Codex_Mat_PLATEAU_Asphalt", unreal.LinearColor(0.020, 0.022, 0.024, 1.0), 0.96),
        "sidewalk": create_color_material("Codex_Mat_PLATEAU_Sidewalk", unreal.LinearColor(0.46, 0.45, 0.40, 1.0), 0.90),
        "line": create_color_material("Codex_Mat_PLATEAU_RoadLine", unreal.LinearColor(0.90, 0.86, 0.72, 1.0), 0.64),
        "window": create_color_material(
            "Codex_Mat_PLATEAU_Window",
            unreal.LinearColor(0.025, 0.12, 0.20, 1.0),
            0.25,
            unreal.LinearColor(0.0, 0.06, 0.12, 1.0),
        ),
        "sign": create_color_material(
            "Codex_Mat_PLATEAU_Sign",
            unreal.LinearColor(0.80, 0.12, 0.06, 1.0),
            0.45,
            unreal.LinearColor(0.90, 0.08, 0.03, 1.0),
        ),
        "rail": create_color_material("Codex_Mat_PLATEAU_Rail", unreal.LinearColor(0.10, 0.10, 0.095, 1.0), 0.45),
        "plaza": create_color_material("Codex_Mat_PLATEAU_Plaza", unreal.LinearColor(0.30, 0.29, 0.26, 1.0), 0.86),
    }
    assignments = []
    for index in range(component.get_num_materials()):
        current = component.get_material(index)
        name = current.get_name() if current is not None else ""
        key = "building"
        lower = name.lower()
        if "terrain" in lower:
            key = "terrain"
        elif "road_white" in lower or "line" in lower:
            key = "line"
        elif "road" in lower or "asphalt" in lower:
            key = "road"
        elif "sidewalk" in lower:
            key = "sidewalk"
        elif "window" in lower or "glass" in lower:
            key = "window"
        elif "sign" in lower:
            key = "sign"
        elif "rail" in lower:
            key = "rail"
        elif "plaza" in lower or "paving" in lower:
            key = "plaza"
        if mats.get(key) is not None:
            component.set_material(index, mats[key])
            assignments.append({"slot": index, "source": name, "assigned": key})
    return assignments


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    if OUTPUT_PATH.exists():
        OUTPUT_PATH.unlink()

    mesh, imported_paths = import_fbx()
    unreal.EditorLevelLibrary.new_level("/Temp/Codex_UE5_PlateauFBX_{0}".format(int(time.time())))
    world = unreal.EditorLevelLibrary.get_editor_world()

    actor = unreal.EditorLevelLibrary.spawn_actor_from_object(mesh, unreal.Vector(0.0, 0.0, 0.0))
    actor.set_actor_label("Codex_HonAtsugi_PLATEAU_RealAsset")
    material_assignments = apply_plateau_materials(actor)
    origin, extent = actor.get_actor_bounds(False)
    target = unreal.Vector(origin.x + extent.x * 0.10, origin.y - extent.y * 0.08, origin.z + extent.z * 0.22)

    cube = unreal.EditorAssetLibrary.load_asset("/Engine/BasicShapes/Cube.Cube")
    sky_mat = create_color_material(
        "Codex_Mat_Plateau_ClearSky",
        unreal.LinearColor(0.12, 0.42, 0.90, 1.0),
        0.95,
        unreal.LinearColor(0.03, 0.15, 0.35, 1.0),
    )
    if cube is not None:
        # A simple camera-facing-ish sky wall. The real city mesh remains the subject; this avoids black void.
        sky = unreal.EditorLevelLibrary.spawn_actor_from_object(
            cube,
            unreal.Vector(origin.x + extent.x * 0.95, origin.y + extent.y * 0.60, origin.z + extent.z * 0.90),
        )
        sky.set_actor_label("Codex_Plateau_Sky_Backdrop")
        sky.set_actor_scale3d(unreal.Vector(0.18, max(20.0, extent.y / 260.0), max(10.0, extent.z / 80.0)))
        set_mat(sky, sky_mat)

    sun = unreal.EditorLevelLibrary.spawn_actor_from_class(unreal.DirectionalLight, target + unreal.Vector(0.0, -8000.0, 12000.0))
    sun.set_actor_label("Codex_Sun")
    sun.set_actor_rotation(unreal.Rotator(-36.0, -42.0, 0.0), False)
    sun.get_component_by_class(unreal.DirectionalLightComponent).set_editor_property("intensity", 10.0)

    sky = unreal.EditorLevelLibrary.spawn_actor_from_class(unreal.SkyLight, target + unreal.Vector(0.0, 0.0, 6000.0))
    sky.set_actor_label("Codex_SkyLight")
    sky.get_component_by_class(unreal.SkyLightComponent).set_editor_property("intensity", 2.2)

    pp = unreal.EditorLevelLibrary.spawn_actor_from_class(unreal.PostProcessVolume, target)
    pp.set_actor_label("Codex_PostProcess")
    set_first_existing_property(pp, ["b_unbound", "unbound", "is_unbound"], True)

    camera_loc = unreal.Vector(
        origin.x - extent.x * 0.38,
        origin.y - extent.y * 0.42,
        origin.z + max(180.0, extent.z * 0.11),
    )
    camera_rot = unreal.MathLibrary.find_look_at_rotation(camera_loc, target)

    render_target = unreal.TextureRenderTarget2D()
    render_target.set_editor_property("size_x", 1920)
    render_target.set_editor_property("size_y", 1080)
    render_target.set_editor_property("target_gamma", 2.2)
    render_target.set_editor_property("clear_color", unreal.LinearColor(0.42, 0.55, 0.75, 1.0))

    capture = unreal.EditorLevelLibrary.spawn_actor_from_class(unreal.SceneCapture2D, camera_loc, camera_rot)
    capture.set_actor_label("Codex_Capture2D")
    component = capture.get_component_by_class(unreal.SceneCaptureComponent2D)
    component.set_editor_property("texture_target", render_target)
    component.set_editor_property("fov_angle", 52.0)
    if hasattr(unreal, "SceneCaptureSource"):
        component.set_editor_property("capture_source", unreal.SceneCaptureSource.SCS_FINAL_COLOR_LDR)

    for cmd in [
        "r.Lumen.DiffuseIndirect.Allow 1",
        "r.Lumen.Reflections.Allow 1",
        "r.ScreenPercentage 100",
        "r.Tonemapper.Sharpen 1",
        "r.ViewDistanceScale 2",
    ]:
        unreal.SystemLibrary.execute_console_command(world, cmd)

    component.capture_scene()
    time.sleep(2.0)
    unreal.RenderingLibrary.export_render_target(world, render_target, str(OUT_DIR), OUTPUT_NAME)

    report = {
        "ok": OUTPUT_PATH.exists() and OUTPUT_PATH.stat().st_size > 0,
        "output": str(OUTPUT_PATH),
        "output_size": OUTPUT_PATH.stat().st_size if OUTPUT_PATH.exists() else 0,
        "fbx": str(FBX_PATH),
        "imported_paths": imported_paths,
        "asset": mesh.get_path_name(),
        "bounds_origin": [origin.x, origin.y, origin.z],
        "bounds_extent": [extent.x, extent.y, extent.z],
        "camera_location": [camera_loc.x, camera_loc.y, camera_loc.z],
        "camera_rotation": [camera_rot.pitch, camera_rot.yaw, camera_rot.roll],
        "material_assignments": material_assignments,
        "scale_strategy": "blender_global_scale_1_city_only",
        "api_cost": "none_local_ue5_only",
    }
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


main()
