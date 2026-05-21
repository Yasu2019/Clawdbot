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


def spawn_box(cube, label, loc, scale, mat):
    actor = unreal.EditorLevelLibrary.spawn_actor_from_object(cube, loc)
    actor.set_actor_label("Codex_R100_" + label)
    actor.set_actor_scale3d(scale)
    set_actor_mat(actor, mat)
    return actor


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


def spawn_cinematic_station_front_set(cube, mats, surface_z, road_origin):
    if cube is None:
        return []
    actors = []

    storefronts = [
        ("Storefront_Left_01", -1610.0, -1040.0, 5.6, mats["storefront_red"]),
        ("Storefront_Left_02", -1610.0, -300.0, 5.6, mats["storefront_blue"]),
        ("Storefront_Right_01", 1710.0, -760.0, 5.2, mats["storefront_green"]),
        ("Storefront_Right_02", 1710.0, 40.0, 5.2, mats["storefront_yellow"]),
    ]
    for label, x, y, width, mat in storefronts:
        actors.append(spawn_box(
            cube,
            label + "_Wall",
            unreal.Vector(road_origin.x + x, road_origin.y + y, surface_z + 310.0),
            unreal.Vector(0.12, width, 2.4),
            mats["shop_wall"],
        ))
        actors.append(spawn_box(
            cube,
            label + "_Awning",
            unreal.Vector(road_origin.x + x * 0.995, road_origin.y + y, surface_z + 520.0),
            unreal.Vector(0.32, width * 0.55, 0.16),
            mat,
        ))
        actors.append(spawn_box(
            cube,
            label + "_Glass",
            unreal.Vector(road_origin.x + x * 0.992, road_origin.y + y - 130.0, surface_z + 285.0),
            unreal.Vector(0.05, width * 0.34, 0.95),
            mats["shop_glass"],
        ))
        actors.append(spawn_box(
            cube,
            label + "_Sign",
            unreal.Vector(road_origin.x + x * 0.99, road_origin.y + y + 150.0, surface_z + 650.0),
            unreal.Vector(0.07, width * 0.32, 0.22),
            mat,
        ))

    for side_x in [-1340.0, 1350.0]:
        for y in [-3950.0, -2950.0, -1950.0, -950.0, 50.0, 1050.0]:
            actors.append(spawn_box(
                cube,
                "Sidewalk_Tile",
                unreal.Vector(road_origin.x + side_x, road_origin.y + y, surface_z + 9.0),
                unreal.Vector(2.4, 2.1, 0.018),
                mats["paving_alt"],
            ))

    for y in [-4200.0, -3600.0, -3000.0, -2400.0, -1800.0, -1200.0]:
        for x in [-620.0, 620.0]:
            actors.append(spawn_box(
                cube,
                "Asphalt_RepairPatch",
                unreal.Vector(road_origin.x + x, road_origin.y + y, surface_z + 10.0),
                unreal.Vector(2.2, 1.25, 0.011),
                mats["road_patch"],
            ))

    for y in [-3800.0, -2600.0, -1400.0, -200.0]:
        actors.append(spawn_box(
            cube,
            "Manhole",
            unreal.Vector(road_origin.x + 430.0, road_origin.y + y, surface_z + 13.0),
            unreal.Vector(0.48, 0.48, 0.012),
            mats["manhole"],
        ))

    pole_specs = [
        ("SignalPole_L", -1250.0, -3460.0, 4.4),
        ("SignalPole_R", 1270.0, -3370.0, 4.0),
        ("StreetLamp_L1", -1380.0, -2200.0, 4.8),
        ("StreetLamp_R1", 1420.0, -1300.0, 4.8),
        ("StreetLamp_L2", -1380.0, -200.0, 4.8),
    ]
    for label, x, y, height in pole_specs:
        actors.append(spawn_box(
            cube,
            label,
            unreal.Vector(road_origin.x + x, road_origin.y + y, surface_z + height * 50.0),
            unreal.Vector(0.055, 0.055, height),
            mats["metal"],
        ))
        actors.append(spawn_box(
            cube,
            label + "_Head",
            unreal.Vector(road_origin.x + x, road_origin.y + y + 42.0, surface_z + height * 100.0),
            unreal.Vector(0.52, 0.12, 0.18),
            mats["lamp_emissive"],
        ))

    for y in [-3300.0, -2800.0, -2300.0, -1800.0, -1300.0, -800.0]:
        actors.append(spawn_box(
            cube,
            "GuardRail_Left",
            unreal.Vector(road_origin.x - 1130.0, road_origin.y + y, surface_z + 80.0),
            unreal.Vector(1.7, 0.045, 0.12),
            mats["metal"],
        ))
        actors.append(spawn_box(
            cube,
            "GuardRail_Right",
            unreal.Vector(road_origin.x + 1160.0, road_origin.y + y, surface_z + 80.0),
            unreal.Vector(1.7, 0.045, 0.12),
            mats["metal"],
        ))

    car_specs = [
        ("Taxi_A", -360.0, -3000.0, mats["taxi"]),
        ("DarkCar_A", 780.0, -2450.0, mats["car_dark"]),
        ("WhiteVan_A", -820.0, -1540.0, mats["van_white"]),
    ]
    for label, x, y, mat in car_specs:
        actors.append(spawn_box(
            cube,
            label + "_Body",
            unreal.Vector(road_origin.x + x, road_origin.y + y, surface_z + 64.0),
            unreal.Vector(1.65, 0.74, 0.34),
            mat,
        ))
        actors.append(spawn_box(
            cube,
            label + "_Cabin",
            unreal.Vector(road_origin.x + x, road_origin.y + y + 8.0, surface_z + 118.0),
            unreal.Vector(0.95, 0.58, 0.28),
            mats["car_glass"],
        ))

    for x in [-1540.0, 1540.0]:
        for y in [-1900.0, -560.0, 680.0]:
            actors.append(spawn_box(
                cube,
                "PosterPanel",
                unreal.Vector(road_origin.x + x, road_origin.y + y, surface_z + 440.0),
                unreal.Vector(0.06, 0.78, 0.52),
                mats["poster"],
            ))

    return actors


def spawn_foreground_road(cube, mats, surface_z, road_origin):
    if cube is None:
        return []
    actors = []
    road = unreal.EditorLevelLibrary.spawn_actor_from_object(
        cube,
        unreal.Vector(road_origin.x - 120.0, road_origin.y - 3350.0, surface_z + 18.0),
    )
    road.set_actor_label("Codex_R100_Foreground_Asphalt")
    road.set_actor_scale3d(unreal.Vector(34.0, 76.0, 0.04))
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
    surface_z = road_bounds_max[2] + 6.0
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
        "road": create_color_material("M_R100_Road_Asphalt_Dark_v3", unreal.LinearColor(0.014, 0.015, 0.016, 1.0), 0.96),
        "road_patch": create_color_material("M_R100_Road_RepairPatch", unreal.LinearColor(0.030, 0.031, 0.032, 1.0), 0.98),
        "manhole": create_color_material("M_R100_Manhole_DarkMetal", unreal.LinearColor(0.075, 0.073, 0.066, 1.0), 0.55),
        "marking": create_color_material("M_R100_Road_Marking_Bright_v2", unreal.LinearColor(0.95, 0.90, 0.68, 1.0), 0.58),
        "sidewalk": create_color_material("M_R100_Sidewalk_Concrete_v2", unreal.LinearColor(0.50, 0.48, 0.42, 1.0), 0.88),
        "paving_alt": create_color_material("M_R100_Paving_AltBlocks", unreal.LinearColor(0.42, 0.40, 0.36, 1.0), 0.90),
        "building": create_color_material("M_R100_Building_WarmConcrete_v2", unreal.LinearColor(0.50, 0.49, 0.44, 1.0), 0.84),
        "building2": create_color_material("M_R100_Building_CoolConcrete_v2", unreal.LinearColor(0.32, 0.37, 0.39, 1.0), 0.82),
        "window": create_color_material("M_R100_Window_DarkGlass", unreal.LinearColor(0.025, 0.10, 0.16, 1.0), 0.25, unreal.LinearColor(0.0, 0.045, 0.09, 1.0)),
        "sign": create_color_material("M_R100_Sign_Emissive", unreal.LinearColor(0.85, 0.12, 0.05, 1.0), 0.45, unreal.LinearColor(1.1, 0.08, 0.03, 1.0)),
        "shop_wall": create_color_material("M_R100_Shop_Wall_OffWhite", unreal.LinearColor(0.68, 0.65, 0.58, 1.0), 0.78),
        "shop_glass": create_color_material("M_R100_Shop_Glass", unreal.LinearColor(0.02, 0.075, 0.10, 1.0), 0.22, unreal.LinearColor(0.0, 0.035, 0.055, 1.0)),
        "storefront_red": create_color_material("M_R100_Storefront_Red", unreal.LinearColor(0.78, 0.05, 0.035, 1.0), 0.48, unreal.LinearColor(0.55, 0.02, 0.01, 1.0)),
        "storefront_blue": create_color_material("M_R100_Storefront_Blue", unreal.LinearColor(0.03, 0.12, 0.64, 1.0), 0.46, unreal.LinearColor(0.02, 0.04, 0.36, 1.0)),
        "storefront_green": create_color_material("M_R100_Storefront_Green", unreal.LinearColor(0.03, 0.42, 0.18, 1.0), 0.50, unreal.LinearColor(0.01, 0.19, 0.06, 1.0)),
        "storefront_yellow": create_color_material("M_R100_Storefront_Yellow", unreal.LinearColor(0.95, 0.64, 0.08, 1.0), 0.48, unreal.LinearColor(0.55, 0.28, 0.02, 1.0)),
        "rail": create_color_material("M_R100_Rail_Metal", unreal.LinearColor(0.12, 0.12, 0.11, 1.0), 0.42),
        "metal": create_color_material("M_R100_Prop_Metal", unreal.LinearColor(0.10, 0.10, 0.095, 1.0), 0.48),
        "lamp_emissive": create_color_material("M_R100_Lamp_Emissive", unreal.LinearColor(1.0, 0.86, 0.52, 1.0), 0.28, unreal.LinearColor(1.0, 0.68, 0.25, 1.0)),
        "car": create_color_material("M_R100_Prop_CarBlue", unreal.LinearColor(0.05, 0.16, 0.38, 1.0), 0.35),
        "car2": create_color_material("M_R100_Prop_CarWhite", unreal.LinearColor(0.75, 0.73, 0.68, 1.0), 0.40),
        "taxi": create_color_material("M_R100_Taxi_Yellow", unreal.LinearColor(0.98, 0.68, 0.06, 1.0), 0.36),
        "car_dark": create_color_material("M_R100_Car_Dark", unreal.LinearColor(0.035, 0.04, 0.052, 1.0), 0.32),
        "van_white": create_color_material("M_R100_Van_White", unreal.LinearColor(0.80, 0.79, 0.74, 1.0), 0.42),
        "car_glass": create_color_material("M_R100_Car_Glass", unreal.LinearColor(0.012, 0.044, 0.065, 1.0), 0.20, unreal.LinearColor(0.0, 0.025, 0.045, 1.0)),
        "poster": create_color_material("M_R100_Poster_Mixed", unreal.LinearColor(0.92, 0.18, 0.44, 1.0), 0.44, unreal.LinearColor(0.32, 0.04, 0.12, 1.0)),
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
    cinematic_set = spawn_cinematic_station_front_set(cube, mats, surface_z, road_origin)
    results.append(capture_variant(world, component, render_target, "cinematic_station_front_set"))

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
        "cinematic_set_count": len(cinematic_set),
        "foreground_road_count": len(foreground_road),
        "sky_backdrop": sky_actor is not None,
        "variants": results,
        "api_cost": "none_local_ue5_only",
    }
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


main()
