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
LOD2_DEST = "/Game/CodexGenerated/PlateauLOD2Buildings"
LOD2_FBX = BASE_DIR / "plateau_lod2_buildings_radius100.fbx"
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


def import_lod2_buildings():
    """PLATEAU LOD2 FBX (テクスチャ付き建物) をインポートしてアクターを返す。"""
    if not LOD2_FBX.exists():
        log("LOD2 FBX not found, skipping: " + str(LOD2_FBX))
        return None, None
    unreal.EditorAssetLibrary.make_directory(LOD2_DEST)
    existing = load_asset(LOD2_DEST + "/LOD2_Buildings")
    if existing is not None:
        log("Deleting cached LOD2 asset to force re-importing the 150m FBX")
        unreal.EditorAssetLibrary.delete_asset(LOD2_DEST + "/LOD2_Buildings")
        existing = None
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
    task.set_editor_property("filename", str(LOD2_FBX))
    task.set_editor_property("destination_path", LOD2_DEST)
    task.set_editor_property("destination_name", "LOD2_Buildings")
    task.set_editor_property("replace_existing", True)
    task.set_editor_property("automated", True)
    task.set_editor_property("save", True)
    task.set_editor_property("options", options)
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    imported = list(task.get_editor_property("imported_object_paths") or [])
    mesh = None
    for p in imported:
        asset = load_asset(p)
        if isinstance(asset, unreal.StaticMesh):
            mesh = asset
            break
    if mesh is None:
        mesh = load_asset(LOD2_DEST + "/LOD2_Buildings")
    if mesh is None:
        log("LOD2 import failed")
        return None, None
    actor = unreal.EditorLevelLibrary.spawn_actor_from_object(mesh, unreal.Vector(0.0, 0.0, 0.0))
    actor.set_actor_label("Codex_LOD2_Buildings")
    log("LOD2 Buildings spawned: " + str(len(imported)) + " assets imported")
    return mesh, actor


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


def set_actors_visible(actors, keys, visible):
    for key in keys:
        set_actor_visible(actors.get(key), visible)


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
    sun.get_component_by_class(unreal.DirectionalLightComponent).set_editor_property("intensity", 5.0)

    sky = unreal.EditorLevelLibrary.spawn_actor_from_class(unreal.SkyLight, target + unreal.Vector(0.0, 0.0, 2600.0))
    sky.set_actor_label("Codex_R100_SkyLight")
    sky.get_component_by_class(unreal.SkyLightComponent).set_editor_property("intensity", 1.8)

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
        "r.EyeAdaptation.MethodOverride -1",
        "r.ExposureOffset -1.5",
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


def spawn_street_readability_v1(cube, mats, surface_z, road_origin):
    if cube is None:
        return []
    actors = []

    tree_specs = [
        (-1680.0, -3820.0), (-1680.0, -2750.0), (-1680.0, -1680.0), (-1680.0, -620.0), (-1680.0, 420.0),
        (1680.0, -3600.0), (1680.0, -2520.0), (1680.0, -1450.0), (1680.0, -360.0), (1680.0, 720.0),
    ]
    for index, (x, y) in enumerate(tree_specs):
        actors.append(spawn_box(
            cube,
            "Readability_Tree_{0:02d}_Trunk".format(index),
            unreal.Vector(road_origin.x + x, road_origin.y + y, surface_z + 160.0),
            unreal.Vector(0.12, 0.12, 1.6),
            mats["tree_trunk"],
        ))
        actors.append(spawn_box(
            cube,
            "Readability_Tree_{0:02d}_Crown".format(index),
            unreal.Vector(road_origin.x + x, road_origin.y + y, surface_z + 360.0),
            unreal.Vector(0.78, 0.78, 0.72),
            mats["tree_leaf"],
        ))

    car_specs = [
        ("BlueCar_Close", -520.0, -4100.0, mats["car"]),
        ("WhiteVan_Mid", 720.0, -3150.0, mats["van_white"]),
        ("DarkCar_Mid", -740.0, -2140.0, mats["car_dark"]),
        ("Taxi_Far", 620.0, -1040.0, mats["taxi"]),
        ("WhiteCar_Far", -520.0, 140.0, mats["car2"]),
    ]
    for label, x, y, mat in car_specs:
        actors.append(spawn_box(
            cube,
            "Readability_" + label + "_Body",
            unreal.Vector(road_origin.x + x, road_origin.y + y, surface_z + 66.0),
            unreal.Vector(1.72, 0.78, 0.34),
            mat,
        ))
        actors.append(spawn_box(
            cube,
            "Readability_" + label + "_Cabin",
            unreal.Vector(road_origin.x + x, road_origin.y + y + 12.0, surface_z + 122.0),
            unreal.Vector(0.92, 0.56, 0.26),
            mats["car_glass"],
        ))

    for index, y in enumerate([-4300.0, -3450.0, -2600.0, -1750.0, -900.0, -50.0, 800.0]):
        for side, x in [("L", -1420.0), ("R", 1450.0)]:
            actors.append(spawn_box(
                cube,
                "Readability_StreetLight_{0}_{1}".format(side, index),
                unreal.Vector(road_origin.x + x, road_origin.y + y, surface_z + 240.0),
                unreal.Vector(0.055, 0.055, 4.8),
                mats["metal"],
            ))
            actors.append(spawn_box(
                cube,
                "Readability_StreetLight_{0}_{1}_Lamp".format(side, index),
                unreal.Vector(road_origin.x + x, road_origin.y + y + 46.0, surface_z + 480.0),
                unreal.Vector(0.46, 0.14, 0.16),
                mats["lamp_emissive"],
            ))

    for x in [-1180.0, 1180.0]:
        actors.append(spawn_box(
            cube,
            "Readability_TrafficSignal_Pole",
            unreal.Vector(road_origin.x + x, road_origin.y - 3530.0, surface_z + 230.0),
            unreal.Vector(0.065, 0.065, 4.6),
            mats["metal"],
        ))
        actors.append(spawn_box(
            cube,
            "Readability_TrafficSignal_Box",
            unreal.Vector(road_origin.x + x, road_origin.y - 3470.0, surface_z + 460.0),
            unreal.Vector(0.38, 0.11, 0.48),
            mats["sign"],
        ))

    for y in [-3900.0, -3000.0, -2100.0, -1200.0, -300.0, 600.0]:
        actors.append(spawn_box(
            cube,
            "Readability_RoadSide_Sign",
            unreal.Vector(road_origin.x - 1260.0, road_origin.y + y, surface_z + 235.0),
            unreal.Vector(0.06, 0.46, 0.70),
            mats["poster"],
        ))
    return actors


def spawn_facade_density_v2(cube, mats, surface_z, road_origin):
    if cube is None:
        return []
    actors = []

    facade_specs = [
        ("LeftA", -1510.0, -3880.0, 0.10, 8.0, 5, mats["shop_wall"], mats["storefront_red"]),
        ("LeftB", -1510.0, -2550.0, 0.10, 7.2, 5, mats["shop_wall"], mats["storefront_blue"]),
        ("LeftC", -1510.0, -1160.0, 0.10, 6.8, 4, mats["shop_wall"], mats["storefront_green"]),
        ("RightA", 1510.0, -3640.0, 0.10, 7.6, 5, mats["shop_wall"], mats["storefront_yellow"]),
        ("RightB", 1510.0, -2200.0, 0.10, 7.0, 5, mats["shop_wall"], mats["storefront_blue"]),
        ("RightC", 1510.0, -760.0, 0.10, 6.5, 4, mats["shop_wall"], mats["storefront_red"]),
    ]

    for label, x, y, thickness, width, floors, wall_mat, accent_mat in facade_specs:
        actors.append(spawn_box(
            cube,
            "FacadeDensity_{0}_Wall".format(label),
            unreal.Vector(road_origin.x + x, road_origin.y + y, surface_z + 760.0),
            unreal.Vector(thickness, width, 7.2),
            wall_mat,
        ))
        for floor in range(floors):
            z = surface_z + 300.0 + floor * 145.0
            for bay in [-2, -1, 0, 1, 2]:
                actors.append(spawn_box(
                    cube,
                    "FacadeDensity_{0}_Window_F{1}_B{2}".format(label, floor, bay),
                    unreal.Vector(road_origin.x + x - (18.0 if x > 0 else -18.0), road_origin.y + y + bay * 105.0, z),
                    unreal.Vector(0.035, 0.42, 0.38),
                    mats["window"],
                ))
        for bay, mat in [(-2, accent_mat), (-1, mats["poster"]), (1, accent_mat), (2, mats["sign"])]:
            actors.append(spawn_box(
                cube,
                "FacadeDensity_{0}_Sign_{1}".format(label, bay),
                unreal.Vector(road_origin.x + x - (22.0 if x > 0 else -22.0), road_origin.y + y + bay * 125.0, surface_z + 150.0),
                unreal.Vector(0.04, 0.58, 0.24),
                mat,
            ))
        actors.append(spawn_box(
            cube,
            "FacadeDensity_{0}_Awning".format(label),
            unreal.Vector(road_origin.x + x - (32.0 if x > 0 else -32.0), road_origin.y + y, surface_z + 238.0),
            unreal.Vector(0.28, width * 0.46, 0.12),
            accent_mat,
        ))

    for y in [-4200.0, -3700.0, -3200.0, -2700.0, -2200.0, -1700.0, -1200.0, -700.0, -200.0, 300.0]:
        actors.append(spawn_box(
            cube,
            "RoadCamera_AsphaltWear",
            unreal.Vector(road_origin.x - 240.0, road_origin.y + y, surface_z + 15.0),
            unreal.Vector(5.2, 1.4, 0.010),
            mats["road_patch"],
        ))
        actors.append(spawn_box(
            cube,
            "RoadCamera_CenterLane",
            unreal.Vector(road_origin.x + 260.0, road_origin.y + y + 180.0, surface_z + 20.0),
            unreal.Vector(0.11, 2.2, 0.011),
            mats["marking"],
        ))

    for x in [-1320.0, 1320.0]:
        for y in [-3950.0, -3150.0, -2350.0, -1550.0, -750.0, 50.0, 850.0]:
            actors.append(spawn_box(
                cube,
                "RoadCamera_CurbGuide",
                unreal.Vector(road_origin.x + x, road_origin.y + y, surface_z + 34.0),
                unreal.Vector(0.16, 3.1, 0.08),
                mats["sidewalk"],
            ))

    return actors


def spawn_precision_street_assets_v2(cube, mats, surface_z, road_origin):
    if cube is None:
        return []
    actors = []
    # Assets follow curb lines and lanes instead of scattered foreground-only placement.
    for index, y in enumerate([-4300.0, -3650.0, -3000.0, -2350.0, -1700.0, -1050.0, -400.0, 250.0, 900.0]):
        side = -1 if index % 2 == 0 else 1
        x = side * 1040.0
        actors.append(spawn_box(
            cube,
            "Precision_Car_{0:02d}_Body".format(index),
            unreal.Vector(road_origin.x + x, road_origin.y + y, surface_z + 68.0),
            unreal.Vector(1.65, 0.72, 0.34),
            [mats["car"], mats["car2"], mats["taxi"], mats["car_dark"], mats["van_white"]][index % 5],
        ))
        actors.append(spawn_box(
            cube,
            "Precision_Car_{0:02d}_Cabin".format(index),
            unreal.Vector(road_origin.x + x, road_origin.y + y + 12.0, surface_z + 122.0),
            unreal.Vector(0.92, 0.54, 0.25),
            mats["car_glass"],
        ))

    for index, y in enumerate([-4380.0, -3720.0, -3060.0, -2400.0, -1740.0, -1080.0, -420.0, 240.0, 900.0]):
        for side, x in [("L", -1540.0), ("R", 1540.0)]:
            actors.append(spawn_box(
                cube,
                "Precision_Tree_{0}_{1}_Trunk".format(side, index),
                unreal.Vector(road_origin.x + x, road_origin.y + y, surface_z + 150.0),
                unreal.Vector(0.10, 0.10, 1.5),
                mats["tree_trunk"],
            ))
            actors.append(spawn_box(
                cube,
                "Precision_Tree_{0}_{1}_Crown".format(side, index),
                unreal.Vector(road_origin.x + x, road_origin.y + y, surface_z + 340.0),
                unreal.Vector(0.66, 0.66, 0.66),
                mats["tree_leaf"],
            ))
            actors.append(spawn_box(
                cube,
                "Precision_Lamp_{0}_{1}_Pole".format(side, index),
                unreal.Vector(road_origin.x + x * 0.92, road_origin.y + y + 260.0, surface_z + 245.0),
                unreal.Vector(0.05, 0.05, 4.9),
                mats["metal"],
            ))
            actors.append(spawn_box(
                cube,
                "Precision_Lamp_{0}_{1}_Head".format(side, index),
                unreal.Vector(road_origin.x + x * 0.92, road_origin.y + y + 310.0, surface_z + 492.0),
                unreal.Vector(0.44, 0.12, 0.16),
                mats["lamp_emissive"],
            ))

    for x, y in [(-1180.0, -3680.0), (1180.0, -3620.0), (-1180.0, -980.0), (1180.0, -900.0)]:
        actors.append(spawn_box(
            cube,
            "Precision_Signal_Pole",
            unreal.Vector(road_origin.x + x, road_origin.y + y, surface_z + 230.0),
            unreal.Vector(0.065, 0.065, 4.6),
            mats["metal"],
        ))
        actors.append(spawn_box(
            cube,
            "Precision_Signal_Box",
            unreal.Vector(road_origin.x + x, road_origin.y + y + 60.0, surface_z + 465.0),
            unreal.Vector(0.42, 0.12, 0.50),
            mats["sign"],
        ))

    return actors


def spawn_explicit_ground_road_sidewalk_v1(cube, mats, surface_z, road_origin):
    if cube is None:
        return []
    actors = []

    # Dark asphalt base — PLATEAU Sidewalk (road_patch) now dark too, so contrast shows.
    actors.append(spawn_box(
        cube,
        "ExplicitGround_CityBase",
        unreal.Vector(road_origin.x, road_origin.y - 1800.0, surface_z - 18.0),
        unreal.Vector(62.0, 92.0, 0.045),
        mats["road"],
    ))

    # Main road corridor — thicker so visible at oblique camera angle.
    actors.append(spawn_box(
        cube,
        "ExplicitRoad_Main_Asphalt",
        unreal.Vector(road_origin.x - 40.0, road_origin.y - 2400.0, surface_z + 7.0),
        unreal.Vector(22.0, 86.0, 0.35),
        mats["road"],
    ))
    actors.append(spawn_box(
        cube,
        "ExplicitRoad_Cross_Asphalt",
        unreal.Vector(road_origin.x - 160.0, road_origin.y - 950.0, surface_z + 8.0),
        unreal.Vector(62.0, 15.0, 0.30),
        mats["road"],
    ))

    for x, label in [(-1540.0, "Left"), (1540.0, "Right")]:
        actors.append(spawn_box(
            cube,
            "ExplicitSidewalk_{0}_Long".format(label),
            unreal.Vector(road_origin.x + x, road_origin.y - 2400.0, surface_z + 18.0),
            unreal.Vector(7.2, 86.0, 0.28),
            mats["sidewalk"],
        ))

    for y, label in [(-950.0, "NearCross"), (-3600.0, "FarCross")]:
        actors.append(spawn_box(
            cube,
            "ExplicitSidewalk_{0}_Cross".format(label),
            unreal.Vector(road_origin.x - 120.0, road_origin.y + y, surface_z + 19.0),
            unreal.Vector(62.0, 5.4, 0.28),
            mats["sidewalk"],
        ))

    # Curbs as readable height breaks between road and sidewalk.
    for x, label in [(-1140.0, "LeftRoadEdge"), (1080.0, "RightRoadEdge")]:
        actors.append(spawn_box(
            cube,
            "ExplicitCurb_{0}".format(label),
            unreal.Vector(road_origin.x + x, road_origin.y - 2400.0, surface_z + 42.0),
            unreal.Vector(0.20, 86.0, 0.35),
            mats["marking"],
        ))

    for y in [-4700.0, -3900.0, -3100.0, -2300.0, -1500.0, -700.0, 100.0, 900.0]:
        actors.append(spawn_box(
            cube,
            "ExplicitLaneDash",
            unreal.Vector(road_origin.x - 40.0, road_origin.y + y, surface_z + 34.0),
            unreal.Vector(0.12, 2.8, 0.08),
            mats["marking"],
        ))

    for x in [-980.0, -660.0, -340.0, -20.0, 300.0, 620.0, 940.0]:
        actors.append(spawn_box(
            cube,
            "ExplicitCrosswalkStripe",
            unreal.Vector(road_origin.x + x, road_origin.y - 3580.0, surface_z + 36.0),
            unreal.Vector(0.18, 4.4, 0.08),
            mats["marking"],
        ))

    for x in [-1780.0, -1280.0, 1280.0, 1780.0]:
        for y in [-4600.0, -3600.0, -2600.0, -1600.0, -600.0, 400.0, 1200.0]:
            actors.append(spawn_box(
                cube,
                "ExplicitPavingTile",
                unreal.Vector(road_origin.x + x, road_origin.y + y, surface_z + 24.0),
                unreal.Vector(2.0, 1.8, 0.010),
                mats["paving_alt"],
            ))

    return actors


def spawn_peripheral_building_walls(cube, mats, surface_z, road_origin):
    if cube is None:
        return []
    actors = []

    side_specs = [
        (-5200.0, "WestBlock"),
        (5200.0, "EastBlock"),
    ]
    for side_x, label_prefix in side_specs:
        slab_params = [
            (-4800.0, 9.0, 62.0),
            (-3200.0, 10.5, 65.0),
            (-1600.0, 8.0, 60.0),
            (0.0, 11.0, 68.0),
            (1600.0, 9.5, 58.0),
        ]
        for index, (y, width, height) in enumerate(slab_params):
            actors.append(spawn_box(
                cube,
                "{0}_Slab_{1:02d}".format(label_prefix, index),
                unreal.Vector(road_origin.x + side_x, road_origin.y + y, surface_z + height * 50.0),
                unreal.Vector(5.2, width, height),
                [mats["building"], mats["building2"]][index % 2],
            ))
            inner_x = side_x - 260.0 if side_x < 0 else side_x + 260.0
            for floor in range(max(1, int(height / 3))):
                for bay in range(-1, 2):
                    actors.append(spawn_box(
                        cube,
                        "{0}_Win_{1:02d}_F{2}_B{3}".format(label_prefix, index, floor, bay),
                        unreal.Vector(
                            road_origin.x + inner_x,
                            road_origin.y + y + bay * 280.0,
                            surface_z + 420.0 + floor * 310.0,
                        ),
                        unreal.Vector(0.04, 0.82, 0.52),
                        mats["window"],
                    ))

    back_slabs = [
        (-7800.0, -4200.0, 4.8, 35.0),
        (-7800.0, -2200.0, 4.2, 40.0),
        (-7800.0, -200.0, 5.0, 32.0),
        (-7800.0, 1800.0, 3.8, 38.0),
        (-7800.0, 3600.0, 4.5, 30.0),
        (-9500.0, -3000.0, 14.0, 42.0),
        (-9500.0, 0.0, 16.0, 45.0),
        (-9500.0, 3000.0, 12.0, 38.0),
    ]
    for index, (y, x_off, depth, height) in enumerate(back_slabs):
        actors.append(spawn_box(
            cube,
            "BackFill_Slab_{0:02d}".format(index),
            unreal.Vector(road_origin.x + x_off, road_origin.y + y, surface_z + height * 50.0),
            unreal.Vector(depth, 16.0, height),
            [mats["building"], mats["building2"]][index % 2],
        ))

    # Tall sky-blockers in the north direction — wide slabs (20-25m) give ~12deg angular coverage
    # each; spaced at ~8deg intervals for continuous north-arc coverage across the full camera FOV.
    north_sky_specs = [
        (-3000.0, 2500.0, 22.0, 58.0),
        (-3000.0, -500.0, 18.0, 62.0),
        (-3000.0, -3000.0, 18.0, 55.0),
        (3200.0, 2500.0, 22.0, 72.0),
        (3200.0, -500.0, 22.0, 75.0),
        (3200.0, -3000.0, 20.0, 68.0),
        (3800.0, -750.0, 18.0, 78.0),
        (4100.0, -200.0, 18.0, 76.0),
        (-2200.0, 2600.0, 20.0, 55.0),
        (-1800.0, 3500.0, 25.0, 60.0),
        (-1000.0, 2500.0, 22.0, 58.0),
        (500.0, 2400.0, 22.0, 62.0),
        (1200.0, 2000.0, 22.0, 65.0),
        (2000.0, 3500.0, 22.0, 68.0),
        (2000.0, 1900.0, 22.0, 65.0),
        (-4500.0, 1000.0, 15.0, 45.0),
        (4700.0, 1000.0, 15.0, 58.0),
        (-4500.0, -2000.0, 12.0, 42.0),
        (4700.0, -2000.0, 15.0, 55.0),
        # v35追加: 中央北側の隙間を埋める（road_camera視野外のみ）
        (0.0, 2500.0, 24.0, 70.0),
        (0.0, 1000.0, 24.0, 72.0),
        (-1600.0, 3000.0, 22.0, 62.0),
        (1600.0, 3000.0, 22.0, 68.0),
        (-3000.0, 1000.0, 20.0, 60.0),
        (3200.0, 1000.0, 20.0, 70.0),
    ]
    for index, (x_off, y_off, depth, height) in enumerate(north_sky_specs):
        actors.append(spawn_box(
            cube,
            "NorthSkyBlock_{0:02d}".format(index),
            unreal.Vector(road_origin.x + x_off, road_origin.y + y_off, surface_z + height * 50.0),
            unreal.Vector(depth, 18.0, height),
            [mats["building"], mats["building2"]][index % 2],
        ))

    # Northwest blockers — seal sky for explicit_ground camera upper-left corner.
    nw_sky_specs = [
        (-2500.0, -5000.0, 6.0, 52.0),
        (-3500.0, -4500.0, 7.0, 58.0),
        (-4200.0, -3500.0, 7.0, 55.0),
        (-2000.0, -6000.0, 5.5, 50.0),
        (-3000.0, -6500.0, 6.5, 48.0),
    ]
    for index, (x_off, y_off, depth, height) in enumerate(nw_sky_specs):
        actors.append(spawn_box(
            cube,
            "NWSkyBlock_{0:02d}".format(index),
            unreal.Vector(road_origin.x + x_off, road_origin.y + y_off, surface_z + height * 50.0),
            unreal.Vector(depth, 18.0, height),
            [mats["building"], mats["building2"]][index % 2],
        ))

    # East blockers — seal sky for overview left (east) side.
    east_sky_specs = [
        (3500.0, 3500.0, 9.0, 75.0),
        (4500.0, 2000.0, 9.0, 72.0),
        (4500.0, -1000.0, 9.0, 70.0),
        (3500.0, -2500.0, 9.0, 68.0),
        (5200.0, 500.0, 10.0, 65.0),
        (5200.0, -3000.0, 10.0, 62.0),
        (3000.0, 5000.0, 9.0, 78.0),
        (4000.0, 5000.0, 9.0, 75.0),
        (2500.0, 4500.0, 9.0, 80.0),
        (3500.0, 4500.0, 9.0, 78.0),
        (2500.0, 6500.0, 9.0, 72.0),
        (3500.0, 6500.0, 9.0, 70.0),
        (4500.0, 6000.0, 9.0, 68.0),
    ]
    for index, (x_off, y_off, depth, height) in enumerate(east_sky_specs):
        actors.append(spawn_box(
            cube,
            "EastSkyBlock_{0:02d}".format(index),
            unreal.Vector(road_origin.x + x_off, road_origin.y + y_off, surface_z + height * 50.0),
            unreal.Vector(depth, 18.0, height),
            [mats["building"], mats["building2"]][index % 2],
        ))

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

    # PLATEAU LOD2 建物 (テクスチャ付き) をインポートして追加
    lod2_mesh, lod2_actor = import_lod2_buildings()
    lod2_bounds = None
    if lod2_actor:
        lod2_origin, lod2_extent, lod2_min, lod2_max = actor_bounds([lod2_actor])
        lod2_bounds = (lod2_min, lod2_max)
        log("LOD2 bounds min: {0}".format(lod2_min))
        log("LOD2 bounds max: {0}".format(lod2_max))

    origin, extent, bounds_min, bounds_max = actor_bounds(list(actors.values()))
    road_actor_list = [
        actor for key, actor in actors.items()
        if key in {"Road", "RoadMarkings", "Sidewalk", "Rails"}
    ]
    road_origin, road_extent, road_bounds_min, road_bounds_max = actor_bounds(road_actor_list or list(actors.values()))
    surface_z = road_bounds_max[2] + 6.0
    log("road_origin: {0}  surface_z: {1}".format(road_origin, surface_z))
    log("road bounds: min={0}  max={1}".format(road_bounds_min, road_bounds_max))

    # LOD2アクターをsurface_zに揃えるzオフセット（surface_z計算後に実行）
    if lod2_actor and lod2_bounds:
        lod2_min_z = lod2_bounds[0][2]
        lod2_z_offset = surface_z - lod2_min_z
        lod2_actor.set_actor_location(
            unreal.Vector(road_origin.x, road_origin.y, lod2_z_offset),
            False, False
        )
        log("LOD2 z_offset: {0}cm (lod2_min_z={1} surface_z={2})".format(
            lod2_z_offset, lod2_min_z, surface_z))
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
    concrete_tex = import_texture(ROOT / "data" / "workspace" / "apps" / "blender_assets" / "polyhaven" / "textures" / "brushed_concrete" / "diffuse.png", "T_R100_Concrete_Diffuse")
    sidewalk_tex = import_texture(ROOT / "data" / "workspace" / "apps" / "blender_assets" / "polyhaven" / "textures" / "concrete_floor" / "diffuse.png", "T_R100_Sidewalk_Diffuse")
    mats = {
        "terrain": create_color_material("M_R100_Terrain_MutedGreen", unreal.LinearColor(0.14, 0.22, 0.14, 1.0), 0.92),
        "road": create_color_material("M_R100_Road_Asphalt_Dark_v6_Tex", unreal.LinearColor(0.010, 0.011, 0.012, 1.0), 0.97, texture=asphalt_tex),
        "road_patch": create_color_material("M_R100_Road_RepairPatch_v4_Tex", unreal.LinearColor(0.025, 0.026, 0.027, 1.0), 0.98, texture=asphalt_tex),
        "manhole": create_color_material("M_R100_Manhole_DarkMetal", unreal.LinearColor(0.075, 0.073, 0.066, 1.0), 0.55),
        "marking": create_color_material("M_R100_Road_Marking_Bright_v2", unreal.LinearColor(0.95, 0.90, 0.68, 1.0), 0.58),
        "sidewalk": create_color_material("M_R100_Sidewalk_Concrete_v5_Tex", unreal.LinearColor(0.72, 0.70, 0.65, 1.0), 0.86, texture=sidewalk_tex),
        "paving_alt": create_color_material("M_R100_Paving_AltBlocks_v4", unreal.LinearColor(0.62, 0.60, 0.55, 1.0), 0.88),
        "building": create_color_material("M_R100_Building_WarmConcrete_v2_Tex", unreal.LinearColor(0.50, 0.49, 0.44, 1.0), 0.84, texture=concrete_tex),
        "building2": create_color_material("M_R100_Building_CoolConcrete_v2_Tex", unreal.LinearColor(0.32, 0.37, 0.39, 1.0), 0.82, texture=concrete_tex),
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
        "sky": create_color_material("M_R100_Sky_Backdrop_Dusk_v1", unreal.LinearColor(0.04, 0.06, 0.13, 1.0), 0.95, unreal.LinearColor(0.01, 0.02, 0.07, 1.0)),
        "tree_leaf": create_color_material("M_R100_Tree_Leaf", unreal.LinearColor(0.08, 0.28, 0.09, 1.0), 0.82),
        "tree_trunk": create_color_material("M_R100_Tree_Trunk", unreal.LinearColor(0.16, 0.09, 0.045, 1.0), 0.86),
    }

    sky_actor = None
    cube = load_asset("/Engine/BasicShapes/Cube.Cube")
    if cube is not None:
        sky_actor = unreal.EditorLevelLibrary.spawn_actor_from_object(
            cube,
            unreal.Vector(target.x, target.y + 22000.0, surface_z + 12000.0),
        )
        sky_actor.set_actor_label("Codex_R100_Sky_Backdrop")
        sky_actor.set_actor_scale3d(unreal.Vector(260.0, 0.10, 240.0))
        set_actor_mat(sky_actor, mats["sky"])

    results = []
    results.append(capture_variant(world, component, render_target, "baseline"))
    set_actors_visible(actors, ["Terrain"], False)
    results.append(capture_variant(world, component, render_target, "clean_city_terrain_off"))

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
    street_readability = spawn_street_readability_v1(cube, mats, surface_z, road_origin)
    results.append(capture_variant(world, component, render_target, "street_readability_v1"))
    angle_camera_loc = unreal.Vector(road_origin.x - 4300.0, road_origin.y - 7600.0, surface_z + 820.0)
    angle_camera_target = unreal.Vector(road_origin.x + 220.0, road_origin.y - 1250.0, surface_z + 520.0)
    angle_camera_rot = unreal.MathLibrary.find_look_at_rotation(angle_camera_loc, angle_camera_target)
    capture.set_actor_location(angle_camera_loc, False, False)
    capture.set_actor_rotation(angle_camera_rot, False)
    component.set_editor_property("fov_angle", 58.0)
    results.append(capture_variant(world, component, render_target, "street_readability_angle_v1"))
    facade_density = spawn_facade_density_v2(cube, mats, surface_z, road_origin)
    precision_street_assets = spawn_precision_street_assets_v2(cube, mats, surface_z, road_origin)
    road_camera_loc = unreal.Vector(road_origin.x - 2450.0, road_origin.y - 6550.0, surface_z + 310.0)
    road_camera_target = unreal.Vector(road_origin.x + 260.0, road_origin.y - 1850.0, surface_z + 250.0)
    road_camera_rot = unreal.MathLibrary.find_look_at_rotation(road_camera_loc, road_camera_target)
    capture.set_actor_location(road_camera_loc, False, False)
    capture.set_actor_rotation(road_camera_rot, False)
    component.set_editor_property("fov_angle", 35.0)
    results.append(capture_variant(world, component, render_target, "facade_density_road_camera_v2"))
    overview_camera_loc = unreal.Vector(road_origin.x - 5200.0, road_origin.y - 8500.0, surface_z + 2500.0)
    overview_camera_target = unreal.Vector(road_origin.x + 240.0, road_origin.y - 1700.0, surface_z + 520.0)
    overview_camera_rot = unreal.MathLibrary.find_look_at_rotation(overview_camera_loc, overview_camera_target)
    capture.set_actor_location(overview_camera_loc, False, False)
    capture.set_actor_rotation(overview_camera_rot, False)
    component.set_editor_property("fov_angle", 52.0)
    results.append(capture_variant(world, component, render_target, "street_precision_overview_v2"))
    explicit_ground = spawn_explicit_ground_road_sidewalk_v1(cube, mats, surface_z, road_origin)
    ground_camera_loc = unreal.Vector(road_origin.x - 2100.0, road_origin.y - 6200.0, surface_z + 245.0)
    ground_camera_target = unreal.Vector(road_origin.x - 40.0, road_origin.y - 2350.0, surface_z + 210.0)
    ground_camera_rot = unreal.MathLibrary.find_look_at_rotation(ground_camera_loc, ground_camera_target)
    capture.set_actor_location(ground_camera_loc, False, False)
    capture.set_actor_rotation(ground_camera_rot, False)
    component.set_editor_property("fov_angle", 46.0)
    results.append(capture_variant(world, component, render_target, "explicit_ground_road_sidewalk_v1"))
    ground_overview_loc = unreal.Vector(road_origin.x - 4800.0, road_origin.y - 7800.0, surface_z + 980.0)
    ground_overview_target = unreal.Vector(road_origin.x - 40.0, road_origin.y - 2200.0, surface_z + 350.0)
    ground_overview_rot = unreal.MathLibrary.find_look_at_rotation(ground_overview_loc, ground_overview_target)
    capture.set_actor_location(ground_overview_loc, False, False)
    capture.set_actor_rotation(ground_overview_rot, False)
    component.set_editor_property("fov_angle", 58.0)
    results.append(capture_variant(world, component, render_target, "explicit_ground_overview_v1"))

    peripheral_walls = spawn_peripheral_building_walls(cube, mats, surface_z, road_origin)
    sealed_camera_loc = unreal.Vector(road_origin.x - 1800.0, road_origin.y - 6400.0, surface_z + 450.0)
    sealed_camera_target = unreal.Vector(road_origin.x - 400.0, road_origin.y - 2600.0, surface_z + 300.0)
    sealed_camera_rot = unreal.MathLibrary.find_look_at_rotation(sealed_camera_loc, sealed_camera_target)
    capture.set_actor_location(sealed_camera_loc, False, False)
    capture.set_actor_rotation(sealed_camera_rot, False)
    component.set_editor_property("fov_angle", 38.0)
    results.append(capture_variant(world, component, render_target, "ground_sky_sealed_v1"))
    sealed_overview_loc = unreal.Vector(road_origin.x + 200.0, road_origin.y + 7500.0, surface_z + 2800.0)
    sealed_overview_target = unreal.Vector(road_origin.x - 80.0, road_origin.y - 2800.0, surface_z + 400.0)
    sealed_overview_rot = unreal.MathLibrary.find_look_at_rotation(sealed_overview_loc, sealed_overview_target)
    capture.set_actor_location(sealed_overview_loc, False, False)
    capture.set_actor_rotation(sealed_overview_rot, False)
    component.set_editor_property("fov_angle", 58.0)
    results.append(capture_variant(world, component, render_target, "ground_sky_sealed_overview_v1"))

    # --- v35: LOD2特化 3カメラセット ---
    # Hide procedural blocker walls and proxy buildings to let pure PLATEAU LOD2 shine
    for wall in peripheral_walls:
        set_actor_visible(wall, False)
    for bldg in proxy_buildings:
        set_actor_visible(bldg, False)

    # sealed_v35: FOV38°, 高度450cmで奥行きを出す
    capture.set_actor_location(sealed_camera_loc, False, False)
    capture.set_actor_rotation(sealed_camera_rot, False)
    component.set_editor_property("fov_angle", 38.0)
    results.append(capture_variant(world, component, render_target, "lod2_sealed_v35"))

    # overview_v35: LOD2建物z_max=102m(10200cm)より高い高度から俯瞰
    overview_v35_loc = unreal.Vector(road_origin.x - 6000.0, road_origin.y - 10000.0, surface_z + 15000.0)
    overview_v35_target = unreal.Vector(road_origin.x + 240.0, road_origin.y - 1700.0, surface_z + 2000.0)
    overview_v35_rot = unreal.MathLibrary.find_look_at_rotation(overview_v35_loc, overview_v35_target)
    capture.set_actor_location(overview_v35_loc, False, False)
    capture.set_actor_rotation(overview_v35_rot, False)
    component.set_editor_property("fov_angle", 68.0)
    results.append(capture_variant(world, component, render_target, "lod2_overview_v35"))

    # road_v35: sealed_cameraと同一XY（LOD2除外ゾーン中心）Z=1200cm, FOV50°
    # Z=12mでsky-blockerスラブより低く、建物除外ゾーン内なので壁面干渉なし
    road_v35_loc = unreal.Vector(road_origin.x - 1800.0, road_origin.y - 6400.0, surface_z + 1200.0)
    road_v35_target = unreal.Vector(road_origin.x - 400.0, road_origin.y - 2600.0, surface_z + 300.0)
    road_v35_rot = unreal.MathLibrary.find_look_at_rotation(road_v35_loc, road_v35_target)
    capture.set_actor_location(road_v35_loc, False, False)
    capture.set_actor_rotation(road_v35_rot, False)
    component.set_editor_property("fov_angle", 50.0)
    results.append(capture_variant(world, component, render_target, "lod2_road_v35"))

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
        "angle_camera_location_cm": [angle_camera_loc.x, angle_camera_loc.y, angle_camera_loc.z],
        "angle_camera_target_cm": [angle_camera_target.x, angle_camera_target.y, angle_camera_target.z],
        "angle_camera_rotation": [angle_camera_rot.pitch, angle_camera_rot.yaw, angle_camera_rot.roll],
        "road_camera_location_cm": [road_camera_loc.x, road_camera_loc.y, road_camera_loc.z],
        "road_camera_target_cm": [road_camera_target.x, road_camera_target.y, road_camera_target.z],
        "road_camera_rotation": [road_camera_rot.pitch, road_camera_rot.yaw, road_camera_rot.roll],
        "overview_camera_location_cm": [overview_camera_loc.x, overview_camera_loc.y, overview_camera_loc.z],
        "overview_camera_target_cm": [overview_camera_target.x, overview_camera_target.y, overview_camera_target.z],
        "overview_camera_rotation": [overview_camera_rot.pitch, overview_camera_rot.yaw, overview_camera_rot.roll],
        "ground_camera_location_cm": [ground_camera_loc.x, ground_camera_loc.y, ground_camera_loc.z],
        "ground_camera_target_cm": [ground_camera_target.x, ground_camera_target.y, ground_camera_target.z],
        "ground_camera_rotation": [ground_camera_rot.pitch, ground_camera_rot.yaw, ground_camera_rot.roll],
        "ground_overview_location_cm": [ground_overview_loc.x, ground_overview_loc.y, ground_overview_loc.z],
        "ground_overview_target_cm": [ground_overview_target.x, ground_overview_target.y, ground_overview_target.z],
        "ground_overview_rotation": [ground_overview_rot.pitch, ground_overview_rot.yaw, ground_overview_rot.roll],
        "terrain_enabled_after_baseline": False,
        "props_count": len(props),
        "proxy_building_count": len(proxy_buildings),
        "cinematic_set_count": len(cinematic_set),
        "street_readability_count": len(street_readability),
        "facade_density_count": len(facade_density),
        "precision_street_assets_count": len(precision_street_assets),
        "explicit_ground_count": len(explicit_ground),
        "peripheral_walls_count": len(peripheral_walls),
        "sealed_camera_location_cm": [sealed_camera_loc.x, sealed_camera_loc.y, sealed_camera_loc.z],
        "sealed_camera_target_cm": [sealed_camera_target.x, sealed_camera_target.y, sealed_camera_target.z],
        "sealed_overview_location_cm": [sealed_overview_loc.x, sealed_overview_loc.y, sealed_overview_loc.z],
        "foreground_road_count": len(foreground_road),
        "sky_backdrop": sky_actor is not None,
        "variants": results,
        "api_cost": "none_local_ue5_only",
    }
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


main()
