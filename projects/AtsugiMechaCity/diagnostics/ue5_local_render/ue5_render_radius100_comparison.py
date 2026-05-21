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
BASE_DIR = ROOT / "projects" / "AtsugiMechaCity" / "diagnostics" / "ue5_local_render"
SPLIT_DIR = BASE_DIR / "plateau_export" / "radius100_split"
OUT_DIR = BASE_DIR / "radius100_compare"
REPORT = OUT_DIR / "radius100_ue5_compare_report.json"
DESTINATION = "/Game/CodexGenerated/PlateauRadius100Split"
MATERIAL_DIR = "/Game/CodexGenerated/PlateauRadius100Materials"
TEXTURE_DIR = MATERIAL_DIR + "/Textures"
RESOLUTION = (1280, 720)


CATEGORIES = ["Terrain", "Road", "RoadMarkings", "Sidewalk", "Buildings", "Windows", "Signs", "Rails"]


def log(message):
    unreal.log("[UE5Radius100] " + message)
    print("[UE5Radius100] " + message)


def load_asset(path):
    return unreal.EditorAssetLibrary.load_asset(path)


def import_asset(path, name):
    if not path.exists():
        return None, []
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
    task.set_editor_property("filename", str(path))
    task.set_editor_property("destination_path", DESTINATION)
    task.set_editor_property("destination_name", "R100_" + name)
    task.set_editor_property("replace_existing", True)
    task.set_editor_property("automated", True)
    task.set_editor_property("save", True)
    task.set_editor_property("options", options)
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])

    imported = list(task.get_editor_property("imported_object_paths") or [])
    for object_path in imported:
        asset = load_asset(object_path)
        if isinstance(asset, unreal.StaticMesh):
            return asset, imported
    fallback = load_asset(DESTINATION + "/R100_" + name)
    return fallback, imported


def import_texture(path, name):
    if not path.exists():
        return None
    unreal.EditorAssetLibrary.make_directory(TEXTURE_DIR)
    asset_path = TEXTURE_DIR + "/" + name
    existing = load_asset(asset_path)
    if existing is not None:
        return existing
    task = unreal.AssetImportTask()
    task.set_editor_property("filename", str(path))
    task.set_editor_property("destination_path", TEXTURE_DIR)
    task.set_editor_property("destination_name", name)
    task.set_editor_property("replace_existing", True)
    task.set_editor_property("automated", True)
    task.set_editor_property("save", True)
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    return load_asset(asset_path)


def create_color_material(name, color, roughness=0.85, emissive=None, texture=None):
    unreal.EditorAssetLibrary.make_directory(MATERIAL_DIR)
    asset_path = MATERIAL_DIR + "/" + name
    existing = load_asset(asset_path)
    if existing is not None:
        return existing
    mat = unreal.AssetToolsHelpers.get_asset_tools().create_asset(name, MATERIAL_DIR, unreal.Material, unreal.MaterialFactoryNew())
    if mat is None:
        return None

    if texture is not None:
        tex = unreal.MaterialEditingLibrary.create_material_expression(mat, unreal.MaterialExpressionTextureSample, -560, 0)
        tex.set_editor_property("texture", texture)
        unreal.MaterialEditingLibrary.connect_material_property(tex, "RGB", unreal.MaterialProperty.MP_BASE_COLOR)
    else:
        base = unreal.MaterialEditingLibrary.create_material_expression(mat, unreal.MaterialExpressionConstant3Vector, -560, 0)
        base.set_editor_property("constant", color)
        unreal.MaterialEditingLibrary.connect_material_property(base, "", unreal.MaterialProperty.MP_BASE_COLOR)

    rough = unreal.MaterialEditingLibrary.create_material_expression(mat, unreal.MaterialExpressionConstant, -560, 180)
    rough.set_editor_property("r", roughness)
    unreal.MaterialEditingLibrary.connect_material_property(rough, "", unreal.MaterialProperty.MP_ROUGHNESS)

    if emissive is not None:
        em = unreal.MaterialEditingLibrary.create_material_expression(mat, unreal.MaterialExpressionConstant3Vector, -560, 330)
        em.set_editor_property("constant", emissive)
        unreal.MaterialEditingLibrary.connect_material_property(em, "", unreal.MaterialProperty.MP_EMISSIVE_COLOR)

    unreal.MaterialEditingLibrary.recompile_material(mat)
    unreal.EditorAssetLibrary.save_asset(asset_path, only_if_is_dirty=False)
    return mat


def set_actor_mat(actor, mat):
    if actor is None or mat is None:
        return
    comp = actor.get_component_by_class(unreal.StaticMeshComponent)
    if comp is None:
        return
    for index in range(max(1, comp.get_num_materials())):
        comp.set_material(index, mat)


def set_actor_visible(actor, visible):
    if actor is None:
        return
    comp = actor.get_component_by_class(unreal.StaticMeshComponent)
    if comp is not None:
        comp.set_visibility(visible, True)
    try:
        actor.set_actor_hidden_in_game(not visible)
    except Exception:
        pass


def actor_bounds(actors):
    found = False
    min_x = min_y = min_z = float("inf")
    max_x = max_y = max_z = float("-inf")
    for actor in actors:
        if actor is None:
            continue
        origin, extent = actor.get_actor_bounds(False)
        found = True
        min_x = min(min_x, origin.x - extent.x)
        min_y = min(min_y, origin.y - extent.y)
        min_z = min(min_z, origin.z - extent.z)
        max_x = max(max_x, origin.x + extent.x)
        max_y = max(max_y, origin.y + extent.y)
        max_z = max(max_z, origin.z + extent.z)
    if not found:
        raise RuntimeError("No actor bounds available.")
    origin = unreal.Vector((min_x + max_x) * 0.5, (min_y + max_y) * 0.5, (min_z + max_z) * 0.5)
    extent = unreal.Vector((max_x - min_x) * 0.5, (max_y - min_y) * 0.5, (max_z - min_z) * 0.5)
    return origin, extent, [min_x, min_y, min_z], [max_x, max_y, max_z]


def set_first_existing_property(obj, names, value):
    for name in names:
        try:
            obj.set_editor_property(name, value)
            return name
        except Exception:
            pass
    return None


def setup_lighting(world, target):
    sky_atmosphere_class = getattr(unreal, "SkyAtmosphere", None)
    if sky_atmosphere_class is not None:
        unreal.EditorLevelLibrary.spawn_actor_from_class(sky_atmosphere_class, target)

    fog_class = getattr(unreal, "ExponentialHeightFog", None)
    if fog_class is not None:
        fog = unreal.EditorLevelLibrary.spawn_actor_from_class(fog_class, target)
        fog.set_actor_label("Codex_R100_HeightFog")

    sun = unreal.EditorLevelLibrary.spawn_actor_from_class(unreal.DirectionalLight, target + unreal.Vector(-3000.0, -5000.0, 9000.0))
    sun.set_actor_label("Codex_R100_Sun")
    sun.set_actor_rotation(unreal.Rotator(-34.0, -42.0, 0.0), False)
    sun.get_component_by_class(unreal.DirectionalLightComponent).set_editor_property("intensity", 9.0)

    sky = unreal.EditorLevelLibrary.spawn_actor_from_class(unreal.SkyLight, target + unreal.Vector(0.0, 0.0, 2600.0))
    sky.set_actor_label("Codex_R100_SkyLight")
    sky.get_component_by_class(unreal.SkyLightComponent).set_editor_property("intensity", 2.8)

    pp = unreal.EditorLevelLibrary.spawn_actor_from_class(unreal.PostProcessVolume, target)
    pp.set_actor_label("Codex_R100_PostProcess")
    set_first_existing_property(pp, ["b_unbound", "unbound", "is_unbound"], True)

    for cmd in [
        "r.Lumen.DiffuseIndirect.Allow 0",
        "r.Lumen.Reflections.Allow 0",
        "r.ScreenPercentage 100",
        "r.Tonemapper.Sharpen 1",
        "r.ViewDistanceScale 1",
        "r.Shadow.Virtual.Enable 0",
    ]:
        unreal.SystemLibrary.execute_console_command(world, cmd)


def spawn_props(cube, mats):
    if cube is None:
        return []
    props = []
    specs = [
        ("TrafficPole_A", unreal.Vector(-760.0, -900.0, 2140.0), unreal.Vector(0.08, 0.08, 3.6), mats["metal"]),
        ("TrafficHead_A", unreal.Vector(-760.0, -900.0, 2520.0), unreal.Vector(0.62, 0.12, 0.28), mats["sign"]),
        ("StreetLight_A", unreal.Vector(930.0, -620.0, 2350.0), unreal.Vector(0.07, 0.07, 4.2), mats["metal"]),
        ("Car_A", unreal.Vector(360.0, -1700.0, 1898.0), unreal.Vector(1.65, 0.78, 0.38), mats["car"]),
        ("Car_B", unreal.Vector(-720.0, -520.0, 1898.0), unreal.Vector(1.38, 0.66, 0.34), mats["car2"]),
        ("GuardRail_A", unreal.Vector(-160.0, -780.0, 1918.0), unreal.Vector(4.8, 0.05, 0.16), mats["metal"]),
        ("StoreSign_A", unreal.Vector(1120.0, -330.0, 2600.0), unreal.Vector(1.9, 0.08, 0.44), mats["sign"]),
    ]
    for label, loc, scale, mat in specs:
        actor = unreal.EditorLevelLibrary.spawn_actor_from_object(cube, loc)
        actor.set_actor_label("Codex_R100_" + label)
        actor.set_actor_scale3d(scale)
        set_actor_mat(actor, mat)
        props.append(actor)
    return props


def spawn_proxy_buildings(cube, mats, surface_z):
    if cube is None:
        return []
    actors = []
    specs = [
        ("LeftFacade", unreal.Vector(-1550.0, -650.0, surface_z + 1450.0), unreal.Vector(7.5, 0.42, 14.5), mats["building"]),
        ("RightFacade", unreal.Vector(1750.0, -150.0, surface_z + 1300.0), unreal.Vector(6.2, 0.42, 13.0), mats["building2"]),
        ("MidFacade", unreal.Vector(720.0, 2400.0, surface_z + 950.0), unreal.Vector(4.5, 0.36, 9.5), mats["building"]),
    ]
    for label, loc, scale, mat in specs:
        actor = unreal.EditorLevelLibrary.spawn_actor_from_object(cube, loc)
        actor.set_actor_label("Codex_R100_Proxy_" + label)
        actor.set_actor_scale3d(scale)
        set_actor_mat(actor, mat)
        actors.append(actor)

    window_specs = []
    for x in [-1780.0, -1550.0, -1320.0]:
        for z in [surface_z + 700.0, surface_z + 1050.0, surface_z + 1400.0, surface_z + 1750.0, surface_z + 2100.0]:
            window_specs.append((unreal.Vector(x, -702.0, z), unreal.Vector(0.72, 0.025, 0.20)))
    for x in [1550.0, 1750.0, 1950.0]:
        for z in [surface_z + 650.0, surface_z + 1000.0, surface_z + 1350.0, surface_z + 1700.0]:
            window_specs.append((unreal.Vector(x, -202.0, z), unreal.Vector(0.60, 0.025, 0.18)))
    for index, (loc, scale) in enumerate(window_specs):
        actor = unreal.EditorLevelLibrary.spawn_actor_from_object(cube, loc)
        actor.set_actor_label("Codex_R100_Proxy_Window_{0:02d}".format(index))
        actor.set_actor_scale3d(scale)
        set_actor_mat(actor, mats["window"])
        actors.append(actor)
    return actors


def spawn_foreground_road(cube, mats, surface_z, road_origin):
    if cube is None:
        return []
    actors = []
    road = unreal.EditorLevelLibrary.spawn_actor_from_object(
        cube,
            unreal.Vector(road_origin.x - 120.0, road_origin.y - 2050.0, surface_z - 16.0),
    )
    road.set_actor_label("Codex_R100_Foreground_Asphalt")
    road.set_actor_scale3d(unreal.Vector(34.0, 46.0, 0.04))
    set_actor_mat(road, mats["road"])
    actors.append(road)

    for offset_y in [-3900.0, -2700.0, -1500.0, -300.0, 900.0]:
        stripe = unreal.EditorLevelLibrary.spawn_actor_from_object(
            cube,
            unreal.Vector(road_origin.x - 120.0, road_origin.y + offset_y, surface_z + 6.0),
        )
        stripe.set_actor_label("Codex_R100_Foreground_LaneStripe")
        stripe.set_actor_scale3d(unreal.Vector(0.12, 3.8, 0.012))
        set_actor_mat(stripe, mats["marking"])
        actors.append(stripe)

    for offset_x in [-1300.0, -950.0, -600.0, -250.0, 100.0, 450.0, 800.0, 1150.0]:
        crosswalk = unreal.EditorLevelLibrary.spawn_actor_from_object(
            cube,
            unreal.Vector(road_origin.x + offset_x, road_origin.y - 3300.0, surface_z + 8.0),
        )
        crosswalk.set_actor_label("Codex_R100_Foreground_Crosswalk")
        crosswalk.set_actor_scale3d(unreal.Vector(0.22, 2.6, 0.012))
        set_actor_mat(crosswalk, mats["marking"])
        actors.append(crosswalk)

    for x, y in [(-1760.0, -2050.0), (1560.0, -2050.0)]:
        curb = unreal.EditorLevelLibrary.spawn_actor_from_object(
            cube,
            unreal.Vector(road_origin.x + x, road_origin.y + y, surface_z + 18.0),
        )
        curb.set_actor_label("Codex_R100_Foreground_Curb")
        curb.set_actor_scale3d(unreal.Vector(0.18, 45.0, 0.12))
        set_actor_mat(curb, mats["sidewalk"])
        actors.append(curb)
    return actors


def capture_variant(world, capture_component, render_target, name):
    output_name = "r100_" + name + ".exr"
    output_path = OUT_DIR / output_name
    if output_path.exists():
        output_path.unlink()
    capture_component.capture_scene()
    time.sleep(1.2)
    unreal.RenderingLibrary.export_render_target(world, render_target, str(OUT_DIR), output_name)
    return {
        "name": name,
        "exr": str(output_path),
        "size": output_path.stat().st_size if output_path.exists() else 0,
        "ok": output_path.exists() and output_path.stat().st_size > 0,
    }


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    unreal.EditorLevelLibrary.new_level("/Temp/Codex_R100_Compare_{0}".format(int(time.time())))
    world = unreal.EditorLevelLibrary.get_editor_world()

    actors = {}
    imports = {}
    for category in CATEGORIES:
        mesh, imported = import_asset(SPLIT_DIR / (category + ".fbx"), category)
        imports[category] = imported
        if mesh is None:
            continue
        actor = unreal.EditorLevelLibrary.spawn_actor_from_object(mesh, unreal.Vector(0.0, 0.0, 0.0))
        actor.set_actor_label("Codex_R100_" + category)
        actors[category] = actor

    if not actors:
        raise RuntimeError("No split FBX actors were imported.")

    origin, extent, bounds_min, bounds_max = actor_bounds(list(actors.values()))
    road_actor_list = [
        actor for key, actor in actors.items()
        if key in {"Road", "RoadMarkings", "Sidewalk", "Rails"}
    ]
    road_origin, road_extent, road_bounds_min, road_bounds_max = actor_bounds(road_actor_list or list(actors.values()))
    surface_z = max(road_bounds_min[2], road_bounds_max[2] - 80.0)
    target = unreal.Vector(road_origin.x + 180.0, road_origin.y + 950.0, surface_z + 250.0)
    camera_loc = unreal.Vector(road_origin.x - 900.0, road_origin.y - 5350.0, surface_z + 165.0)
    camera_rot = unreal.MathLibrary.find_look_at_rotation(camera_loc, target)

    setup_lighting(world, target)

    render_target = unreal.TextureRenderTarget2D()
    render_target.set_editor_property("size_x", RESOLUTION[0])
    render_target.set_editor_property("size_y", RESOLUTION[1])
    render_target.set_editor_property("target_gamma", 2.2)
    render_target.set_editor_property("clear_color", unreal.LinearColor(0.48, 0.63, 0.86, 1.0))

    capture = unreal.EditorLevelLibrary.spawn_actor_from_class(unreal.SceneCapture2D, camera_loc, camera_rot)
    capture.set_actor_label("Codex_R100_Capture2D")
    component = capture.get_component_by_class(unreal.SceneCaptureComponent2D)
    component.set_editor_property("texture_target", render_target)
    component.set_editor_property("fov_angle", 46.0)
    if hasattr(unreal, "SceneCaptureSource"):
        component.set_editor_property("capture_source", unreal.SceneCaptureSource.SCS_FINAL_COLOR_LDR)

    asphalt_tex = import_texture(ROOT / "data" / "workspace" / "apps" / "blender_assets" / "polyhaven" / "textures" / "asphalt_floor" / "diffuse.png", "T_R100_Asphalt_Diffuse")
    mats = {
        "terrain": create_color_material("M_R100_Terrain_MutedGreen", unreal.LinearColor(0.14, 0.22, 0.14, 1.0), 0.92),
        "road": create_color_material("M_R100_Road_Asphalt_Dark_v2", unreal.LinearColor(0.014, 0.015, 0.016, 1.0), 0.96),
        "marking": create_color_material("M_R100_Road_Marking_Bright_v2", unreal.LinearColor(0.95, 0.90, 0.68, 1.0), 0.58),
        "sidewalk": create_color_material("M_R100_Sidewalk_Concrete_v2", unreal.LinearColor(0.50, 0.48, 0.42, 1.0), 0.88),
        "building": create_color_material("M_R100_Building_WarmConcrete_v2", unreal.LinearColor(0.50, 0.49, 0.44, 1.0), 0.84),
        "building2": create_color_material("M_R100_Building_CoolConcrete_v2", unreal.LinearColor(0.32, 0.37, 0.39, 1.0), 0.82),
        "window": create_color_material("M_R100_Window_DarkGlass", unreal.LinearColor(0.025, 0.10, 0.16, 1.0), 0.25, unreal.LinearColor(0.0, 0.045, 0.09, 1.0)),
        "sign": create_color_material("M_R100_Sign_Emissive", unreal.LinearColor(0.85, 0.12, 0.05, 1.0), 0.45, unreal.LinearColor(1.1, 0.08, 0.03, 1.0)),
        "rail": create_color_material("M_R100_Rail_Metal", unreal.LinearColor(0.12, 0.12, 0.11, 1.0), 0.42),
        "metal": create_color_material("M_R100_Prop_Metal", unreal.LinearColor(0.10, 0.10, 0.095, 1.0), 0.48),
        "car": create_color_material("M_R100_Prop_CarBlue", unreal.LinearColor(0.05, 0.16, 0.38, 1.0), 0.35),
        "car2": create_color_material("M_R100_Prop_CarWhite", unreal.LinearColor(0.75, 0.73, 0.68, 1.0), 0.40),
        "sky": create_color_material("M_R100_Sky_Backdrop", unreal.LinearColor(0.16, 0.43, 0.82, 1.0), 0.95, unreal.LinearColor(0.03, 0.14, 0.32, 1.0)),
    }

    sky_actor = None
    cube = load_asset("/Engine/BasicShapes/Cube.Cube")
    if cube is not None:
        sky_actor = unreal.EditorLevelLibrary.spawn_actor_from_object(
            cube,
            unreal.Vector(target.x, target.y + 22000.0, surface_z + 6500.0),
        )
        sky_actor.set_actor_label("Codex_R100_Sky_Backdrop")
        sky_actor.set_actor_scale3d(unreal.Vector(180.0, 0.10, 90.0))
        set_actor_mat(sky_actor, mats["sky"])

    results = []
    results.append(capture_variant(world, component, render_target, "baseline"))

    cube = load_asset("/Engine/BasicShapes/Cube.Cube")

    for category, key in [("Terrain", "terrain"), ("Road", "road"), ("RoadMarkings", "marking"), ("Sidewalk", "sidewalk"), ("Rails", "rail")]:
        set_actor_mat(actors.get(category), mats[key])
    foreground_road = spawn_foreground_road(cube, mats, surface_z, road_origin)
    results.append(capture_variant(world, component, render_target, "pbr_road"))

    for category, key in [("Buildings", "building"), ("Windows", "window"), ("Signs", "sign")]:
        set_actor_mat(actors.get(category), mats[key])
    set_actor_visible(actors.get("Windows"), False)
    proxy_buildings = spawn_proxy_buildings(cube, mats, surface_z)
    props = spawn_props(cube, mats)
    results.append(capture_variant(world, component, render_target, "pbr_road_building_props"))

    report = {
        "ok": all(item["ok"] for item in results),
        "output_dir": str(OUT_DIR),
        "resolution": list(RESOLUTION),
        "split_dir": str(SPLIT_DIR),
        "destination": DESTINATION,
        "imports": imports,
        "bounds_min_cm": bounds_min,
        "bounds_max_cm": bounds_max,
        "road_bounds_min_cm": road_bounds_min,
        "road_bounds_max_cm": road_bounds_max,
        "surface_z_cm": surface_z,
        "camera_location_cm": [camera_loc.x, camera_loc.y, camera_loc.z],
        "camera_target_cm": [target.x, target.y, target.z],
        "camera_rotation": [camera_rot.pitch, camera_rot.yaw, camera_rot.roll],
        "props_count": len(props),
        "proxy_building_count": len(proxy_buildings),
        "foreground_road_count": len(foreground_road),
        "sky_backdrop": sky_actor is not None,
        "variants": results,
        "api_cost": "none_local_ue5_only",
    }
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


main()
