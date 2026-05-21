import sys
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import json
import random
import time
from pathlib import Path

import unreal

OUT_DIR = Path(r"D:\Clawdbot_Docker_20260125\projects\AtsugiMechaCity\diagnostics\ue5_local_render")
OUTPUT_NAME = "Atsugi_UE5_procedural_city.exr"
OUTPUT_PATH = OUT_DIR / OUTPUT_NAME
REPORT = OUT_DIR / "ue5_render_procedural_city_report.json"
GENERATED_MATERIAL_DIR = "/Game/CodexGenerated"


def log(msg):
    unreal.log("[UE5ProceduralCity] " + msg)
    print("[UE5ProceduralCity] " + msg)


def load(path):
    asset = unreal.EditorAssetLibrary.load_asset(path)
    if asset is None:
        log("missing asset: {0}".format(path))
    return asset


def set_mat(actor, mat):
    if mat is None:
        return
    component = actor.get_component_by_class(unreal.StaticMeshComponent)
    if component:
        component.set_material(0, mat)


def spawn_mesh(mesh, name, loc, scale, mat=None, rot=None):
    actor = unreal.EditorLevelLibrary.spawn_actor_from_object(mesh, loc, rot or unreal.Rotator(0.0, 0.0, 0.0))
    actor.set_actor_label(name)
    actor.set_actor_scale3d(scale)
    set_mat(actor, mat)
    return actor


def create_color_material(name, base_color, roughness=0.82, metallic=0.0, emissive=None):
    try:
        asset_path = "{0}/{1}".format(GENERATED_MATERIAL_DIR, name)
        existing = unreal.EditorAssetLibrary.load_asset(asset_path)
        if existing is not None:
            return existing

        unreal.EditorAssetLibrary.make_directory(GENERATED_MATERIAL_DIR)
        tools = unreal.AssetToolsHelpers.get_asset_tools()
        mat = tools.create_asset(name, GENERATED_MATERIAL_DIR, unreal.Material, unreal.MaterialFactoryNew())
        if mat is None:
            raise RuntimeError("create_asset returned None for {0}".format(asset_path))

        base = unreal.MaterialEditingLibrary.create_material_expression(mat, unreal.MaterialExpressionConstant3Vector, -420, 0)
        base.set_editor_property("constant", base_color)
        unreal.MaterialEditingLibrary.connect_material_property(base, "", unreal.MaterialProperty.MP_BASE_COLOR)

        rough = unreal.MaterialEditingLibrary.create_material_expression(mat, unreal.MaterialExpressionConstant, -420, 180)
        rough.set_editor_property("r", roughness)
        unreal.MaterialEditingLibrary.connect_material_property(rough, "", unreal.MaterialProperty.MP_ROUGHNESS)

        metal = unreal.MaterialEditingLibrary.create_material_expression(mat, unreal.MaterialExpressionConstant, -420, 320)
        metal.set_editor_property("r", metallic)
        unreal.MaterialEditingLibrary.connect_material_property(metal, "", unreal.MaterialProperty.MP_METALLIC)

        if emissive is not None:
            em = unreal.MaterialEditingLibrary.create_material_expression(mat, unreal.MaterialExpressionConstant3Vector, -420, 470)
            em.set_editor_property("constant", emissive)
            unreal.MaterialEditingLibrary.connect_material_property(em, "", unreal.MaterialProperty.MP_EMISSIVE_COLOR)

        unreal.MaterialEditingLibrary.recompile_material(mat)
        unreal.EditorAssetLibrary.save_asset(asset_path, only_if_is_dirty=False)
        return mat
    except Exception as exc:
        log("color material fallback for {0}: {1}".format(name, exc))
        return None


def spawn_text(text, loc, rot, size, color):
    actor = unreal.EditorLevelLibrary.spawn_actor_from_class(unreal.TextRenderActor, loc, rot)
    actor.set_actor_label("Codex_Sign_{0}".format(text))
    comp = actor.get_component_by_class(unreal.TextRenderComponent)
    comp.set_text(text)
    comp.set_editor_property("world_size", size)
    comp.set_editor_property("text_render_color", color)
    return actor


def main():
    random.seed(42)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    if OUTPUT_PATH.exists():
        OUTPUT_PATH.unlink()

    unreal.EditorLevelLibrary.new_level("/Temp/Codex_UE5_ProceduralCity_{0}".format(int(time.time())))
    world = unreal.EditorLevelLibrary.get_editor_world()

    cube = load("/Engine/BasicShapes/Cube.Cube")
    if cube is None:
        raise RuntimeError("Engine cube mesh not found")

    fallback_mats = [
        load("/Game/Atsugi/pbr_material"),
        load("/Game/Atsugi/pbr_material_001"),
        load("/Game/Atsugi/pbr_material_002"),
        load("/Game/Atsugi/pbr_material_003"),
        load("/Game/Atsugi/pbr_material_004"),
        load("/Game/Atsugi/pbr_material_005"),
        load("/Game/Atsugi/pbr_material_006"),
    ]
    fallback_mats = [m for m in fallback_mats if m is not None]
    zaku_asset = None

    road_mat = create_color_material("Codex_Mat_Asphalt_v2", unreal.LinearColor(0.018, 0.020, 0.022, 1.0), 0.94) or (fallback_mats[0] if fallback_mats else None)
    lane_mat = create_color_material("Codex_Mat_LanePaint_v2", unreal.LinearColor(1.0, 0.95, 0.70, 1.0), 0.72) or (fallback_mats[-1] if fallback_mats else None)
    glass_mat = create_color_material("Codex_Mat_GlassBlue_v2", unreal.LinearColor(0.02, 0.20, 0.36, 1.0), 0.18, 0.20, unreal.LinearColor(0.0, 0.18, 0.32, 1.0)) or (fallback_mats[-1] if fallback_mats else None)
    sign_mat = create_color_material("Codex_Mat_SignGlow_v2", unreal.LinearColor(1.0, 0.78, 0.12, 1.0), 0.45, 0.0, unreal.LinearColor(3.0, 2.0, 0.35, 1.0)) or lane_mat
    sky_mat = create_color_material("Codex_Mat_SkyBackdrop_v2", unreal.LinearColor(0.10, 0.38, 0.82, 1.0), 0.96, 0.0, unreal.LinearColor(0.02, 0.08, 0.18, 1.0)) or glass_mat
    sidewalk_mat = create_color_material("Codex_Mat_Sidewalk_v2", unreal.LinearColor(0.56, 0.53, 0.47, 1.0), 0.90) or lane_mat
    red_mat = create_color_material("Codex_Mat_TrafficRed", unreal.LinearColor(0.75, 0.04, 0.025, 1.0), 0.40, 0.0, unreal.LinearColor(2.0, 0.08, 0.04, 1.0)) or sign_mat
    amber_mat = create_color_material("Codex_Mat_TrafficAmber", unreal.LinearColor(0.95, 0.58, 0.08, 1.0), 0.38, 0.0, unreal.LinearColor(2.0, 1.0, 0.12, 1.0)) or sign_mat
    green_mat = create_color_material("Codex_Mat_TrafficGreen", unreal.LinearColor(0.05, 0.7, 0.22, 1.0), 0.40, 0.0, unreal.LinearColor(0.08, 1.7, 0.34, 1.0)) or sign_mat
    facade_mats = [
        create_color_material("Codex_Mat_ConcreteA_v2", unreal.LinearColor(0.54, 0.52, 0.47, 1.0), 0.88),
        create_color_material("Codex_Mat_ConcreteB_v2", unreal.LinearColor(0.28, 0.36, 0.42, 1.0), 0.84),
        create_color_material("Codex_Mat_OfficeDark_v2", unreal.LinearColor(0.035, 0.055, 0.075, 1.0), 0.62),
        create_color_material("Codex_Mat_TileWarm_v2", unreal.LinearColor(0.62, 0.42, 0.28, 1.0), 0.86),
    ]
    facade_mats = [m for m in facade_mats if m is not None] or fallback_mats

    spawn_mesh(cube, "Codex_Road_Main", unreal.Vector(0.0, 0.0, -15.0), unreal.Vector(95.0, 18.0, 0.12), road_mat)
    spawn_mesh(cube, "Codex_Road_Cross", unreal.Vector(900.0, 0.0, -12.0), unreal.Vector(18.0, 80.0, 0.10), road_mat)
    spawn_mesh(cube, "Codex_Sky_Backdrop", unreal.Vector(6200.0, 0.0, 2300.0), unreal.Vector(0.35, 140.0, 42.0), sky_mat)
    spawn_mesh(cube, "Codex_Left_Sidewalk", unreal.Vector(0.0, -1375.0, 8.0), unreal.Vector(95.0, 4.3, 0.14), sidewalk_mat)
    spawn_mesh(cube, "Codex_Right_Sidewalk", unreal.Vector(0.0, 1375.0, 8.0), unreal.Vector(95.0, 4.3, 0.14), sidewalk_mat)

    for x in range(-4200, 5200, 650):
        spawn_mesh(cube, "Codex_LaneStripe", unreal.Vector(float(x), 0.0, 5.0), unreal.Vector(1.9, 0.10, 0.02), lane_mat)
    for x in range(-4000, 4500, 380):
        for offset, y in enumerate([-610.0, -550.0, -490.0, 490.0, 550.0, 610.0]):
            spawn_mesh(
                cube,
                "Codex_AsphaltPatch",
                unreal.Vector(float(x + (offset % 3) * 55), y, 7.0),
                unreal.Vector(1.2 + (offset % 2) * 0.5, 0.035, 0.012),
                glass_mat if offset % 3 == 0 else road_mat,
            )
    for y in [-1050.0, 1050.0]:
        spawn_mesh(cube, "Codex_Curb", unreal.Vector(0.0, y, 25.0), unreal.Vector(95.0, 0.45, 0.22), lane_mat)
    for y in range(-820, 860, 170):
        spawn_mesh(cube, "Codex_Crosswalk", unreal.Vector(900.0, float(y), 11.0), unreal.Vector(4.9, 0.42, 0.016), lane_mat)

    building_count = 0
    for side_y in [-1900.0, 1900.0]:
        for i, x in enumerate(range(-4300, 5000, 620)):
            width = random.choice([3.5, 4.2, 5.0, 5.8])
            depth = random.choice([4.5, 5.5, 6.5])
            height = random.choice([8.0, 11.0, 14.0, 18.0, 22.0])
            y = side_y + (random.random() - 0.5) * 120.0
            mat = facade_mats[(i + (0 if side_y < 0 else 3)) % max(1, len(facade_mats))] if facade_mats else None
            spawn_mesh(
                cube,
                "Codex_Building_{0}".format(building_count),
                unreal.Vector(float(x), y, height * 50.0),
                unreal.Vector(width, depth, height),
                mat,
            )
            for floor in range(2, int(height), 3):
                z = floor * 100.0 + 25.0
                facade_y = y - (depth * 50.0 + 6.0) if side_y > 0 else y + (depth * 50.0 + 6.0)
                spawn_mesh(
                    cube,
                    "Codex_WindowBand_{0}_{1}".format(building_count, floor),
                    unreal.Vector(float(x), facade_y, z),
                    unreal.Vector(width * 0.72, 0.035, 0.16),
                    glass_mat,
                )
            for floor in range(1, int(height), 4):
                z = floor * 100.0 + 50.0
                facade_y = y - (depth * 50.0 + 12.0) if side_y > 0 else y + (depth * 50.0 + 12.0)
                for col in [-0.32, 0.0, 0.32]:
                    spawn_mesh(
                        cube,
                        "Codex_WindowCell_{0}_{1}_{2}".format(building_count, floor, col),
                        unreal.Vector(float(x) + width * 38.0 * col, facade_y, z),
                        unreal.Vector(0.20, 0.025, 0.22),
                        glass_mat,
                    )
            building_count += 1

    for x in [-2400.0, -650.0, 1250.0, 3100.0]:
        pole = spawn_mesh(cube, "Codex_TrafficPole", unreal.Vector(x, -1180.0, 220.0), unreal.Vector(0.10, 0.10, 4.4), glass_mat)
        pole.set_actor_rotation(unreal.Rotator(0.0, 0.0, 0.0), False)
        spawn_mesh(cube, "Codex_TrafficBox", unreal.Vector(x, -1180.0, 470.0), unreal.Vector(0.55, 0.16, 0.38), sign_mat)
        spawn_mesh(cube, "Codex_TrafficRed", unreal.Vector(x - 35.0, -1196.0, 492.0), unreal.Vector(0.13, 0.025, 0.13), red_mat)
        spawn_mesh(cube, "Codex_TrafficAmber", unreal.Vector(x, -1196.0, 492.0), unreal.Vector(0.13, 0.025, 0.13), amber_mat)
        spawn_mesh(cube, "Codex_TrafficGreen", unreal.Vector(x + 35.0, -1196.0, 492.0), unreal.Vector(0.13, 0.025, 0.13), green_mat)
        spawn_text("ATSUGI", unreal.Vector(x, -1225.0, 640.0), unreal.Rotator(0.0, 90.0, 0.0), 105.0, unreal.Color(245, 245, 230, 255))

    for x, label in [(-3200.0, "CAFE"), (-1050.0, "HOTEL"), (1450.0, "TECH"), (3550.0, "SHOP")]:
        spawn_mesh(cube, "Codex_Billboard_{0}".format(label), unreal.Vector(x, 1295.0, 650.0), unreal.Vector(2.2, 0.10, 0.85), sign_mat)
        spawn_text(label, unreal.Vector(x, 1340.0, 640.0), unreal.Rotator(0.0, -90.0, 0.0), 130.0, unreal.Color(255, 242, 190, 255))
    for x, label in [(-2300.0, "ROUTE 246"), (350.0, "ATSUGI CITY")]:
        spawn_mesh(cube, "Codex_OverheadSign_{0}".format(label), unreal.Vector(x, -40.0, 920.0), unreal.Vector(0.08, 5.2, 0.75), green_mat)
        spawn_text(label, unreal.Vector(x - 8.0, -330.0, 910.0), unreal.Rotator(0.0, 3.0, 0.0), 95.0, unreal.Color(235, 255, 220, 255))

    if zaku_asset is not None:
        zaku = unreal.EditorLevelLibrary.spawn_actor_from_object(zaku_asset, unreal.Vector(-450.0, -250.0, 82.0), unreal.Rotator(0.0, 25.0, 0.0))
        zaku.set_actor_label("Codex_Zaku_Posed")
        zaku.set_actor_scale3d(unreal.Vector(0.95, 0.95, 0.95))

    sun = unreal.EditorLevelLibrary.spawn_actor_from_class(unreal.DirectionalLight, unreal.Vector(0.0, -3000.0, 6500.0))
    sun.set_actor_label("Codex_Sun")
    sun.set_actor_rotation(unreal.Rotator(-42.0, -35.0, 0.0), False)
    sun.get_component_by_class(unreal.DirectionalLightComponent).set_editor_property("intensity", 12.0)

    sky = unreal.EditorLevelLibrary.spawn_actor_from_class(unreal.SkyLight, unreal.Vector(0.0, 0.0, 3000.0))
    sky.set_actor_label("Codex_SkyLight")
    sky.get_component_by_class(unreal.SkyLightComponent).set_editor_property("intensity", 2.6)

    for x in [-3500.0, -1600.0, 450.0, 2400.0, 4100.0]:
        rect = unreal.EditorLevelLibrary.spawn_actor_from_class(unreal.RectLight, unreal.Vector(x, -1250.0, 520.0))
        rect.set_actor_label("Codex_StreetLight")
        rect.set_actor_rotation(unreal.Rotator(-70.0, 75.0, 0.0), False)
        comp = rect.get_component_by_class(unreal.RectLightComponent)
        comp.set_editor_property("intensity", 360.0)
        comp.set_editor_property("source_width", 220.0)
        comp.set_editor_property("source_height", 80.0)

    camera_loc = unreal.Vector(-3900.0, -360.0, 420.0)
    target = unreal.Vector(2550.0, 80.0, 620.0)
    camera_rot = unreal.MathLibrary.find_look_at_rotation(camera_loc, target)

    render_target = unreal.TextureRenderTarget2D()
    render_target.set_editor_property("size_x", 1920)
    render_target.set_editor_property("size_y", 1080)
    render_target.set_editor_property("target_gamma", 2.2)
    render_target.set_editor_property("clear_color", unreal.LinearColor(0.35, 0.45, 0.58, 1.0))

    capture = unreal.EditorLevelLibrary.spawn_actor_from_class(unreal.SceneCapture2D, camera_loc, camera_rot)
    capture.set_actor_label("Codex_Capture2D")
    component = capture.get_component_by_class(unreal.SceneCaptureComponent2D)
    component.set_editor_property("texture_target", render_target)
    component.set_editor_property("fov_angle", 49.0)
    if hasattr(unreal, "SceneCaptureSource"):
        component.set_editor_property("capture_source", unreal.SceneCaptureSource.SCS_FINAL_COLOR_LDR)

    for cmd in [
        "r.Lumen.DiffuseIndirect.Allow 1",
        "r.Lumen.Reflections.Allow 1",
        "r.ScreenPercentage 100",
        "r.Tonemapper.Sharpen 1",
    ]:
        unreal.SystemLibrary.execute_console_command(world, cmd)

    component.capture_scene()
    time.sleep(2.0)
    unreal.RenderingLibrary.export_render_target(world, render_target, str(OUT_DIR), OUTPUT_NAME)

    report = {
        "ok": OUTPUT_PATH.exists() and OUTPUT_PATH.stat().st_size > 0,
        "output": str(OUTPUT_PATH),
        "output_size": OUTPUT_PATH.stat().st_size if OUTPUT_PATH.exists() else 0,
        "building_count": building_count,
        "camera_location": [camera_loc.x, camera_loc.y, camera_loc.z],
        "camera_rotation": [camera_rot.pitch, camera_rot.yaw, camera_rot.roll],
        "api_cost": "none_local_ue5_only",
    }
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


main()
