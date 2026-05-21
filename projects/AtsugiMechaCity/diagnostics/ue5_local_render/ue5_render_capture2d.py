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

OUT_DIR = Path(r"D:\Clawdbot_Docker_20260125\projects\AtsugiMechaCity\diagnostics\ue5_local_render")
REPORT = OUT_DIR / "ue5_render_capture2d_report.json"
OUTPUT_NAME = "Atsugi_UE5_capture2d.png"
OUTPUT_PATH = OUT_DIR / OUTPUT_NAME


def log(msg):
    unreal.log("[UE5Capture2D] " + msg)
    print("[UE5Capture2D] " + msg)


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    if OUTPUT_PATH.exists():
        OUTPUT_PATH.unlink()

    unreal.EditorLevelLibrary.new_level("/Temp/Codex_UE5_Capture2D_{0}".format(int(time.time())))
    world = unreal.EditorLevelLibrary.get_editor_world()

    city_asset = unreal.EditorAssetLibrary.load_asset("/Game/Atsugi/Atsugi_Front_Final")
    zaku_asset = unreal.EditorAssetLibrary.load_asset("/Game/Atsugi/Zaku_Posed")
    if city_asset is None:
        raise RuntimeError("Atsugi_Front_Final asset not found")

    city = unreal.EditorLevelLibrary.spawn_actor_from_object(city_asset, unreal.Vector(0.0, 0.0, 0.0))
    city.set_actor_label("Codex_Atsugi_City_Asset")
    origin, extent = city.get_actor_bounds(False)

    target = unreal.Vector(origin.x, origin.y, origin.z + max(120.0, extent.z * 0.15))
    zaku_name = None
    if zaku_asset is not None:
        zaku_loc = unreal.Vector(origin.x + extent.x * 0.04, origin.y - extent.y * 0.04, origin.z + 30.0)
        zaku = unreal.EditorLevelLibrary.spawn_actor_from_object(zaku_asset, zaku_loc)
        zaku.set_actor_label("Codex_Zaku_Posed")
        zaku_name = zaku.get_name()
        target = zaku_loc + unreal.Vector(0.0, 0.0, 220.0)

    sun = unreal.EditorLevelLibrary.spawn_actor_from_class(unreal.DirectionalLight, target + unreal.Vector(0.0, 0.0, 6000.0))
    sun.set_actor_label("Codex_Sun")
    sun.set_actor_rotation(unreal.Rotator(-35.0, -40.0, 0.0), False)
    sun.get_component_by_class(unreal.DirectionalLightComponent).set_editor_property("intensity", 8.0)

    sky = unreal.EditorLevelLibrary.spawn_actor_from_class(unreal.SkyLight, target + unreal.Vector(0.0, 0.0, 3000.0))
    sky.set_actor_label("Codex_SkyLight")
    sky.get_component_by_class(unreal.SkyLightComponent).set_editor_property("intensity", 1.4)

    distance = max(extent.x, extent.y) * 0.34
    camera_loc = unreal.Vector(
        target.x + distance * 0.65,
        target.y - distance * 0.85,
        target.z + max(220.0, extent.z * 0.055),
    )
    camera_rot = unreal.MathLibrary.find_look_at_rotation(camera_loc, target)

    render_target = unreal.TextureRenderTarget2D()
    render_target.set_editor_property("size_x", 1920)
    render_target.set_editor_property("size_y", 1080)
    render_target.set_editor_property("target_gamma", 2.2)
    render_target.set_editor_property("clear_color", unreal.LinearColor(0.50, 0.62, 0.78, 1.0))

    capture = unreal.EditorLevelLibrary.spawn_actor_from_class(unreal.SceneCapture2D, camera_loc, camera_rot)
    capture.set_actor_label("Codex_Capture2D")
    component = capture.get_component_by_class(unreal.SceneCaptureComponent2D)
    component.set_editor_property("texture_target", render_target)
    component.set_editor_property("fov_angle", 36.0)
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
        "city_actor": city.get_name(),
        "zaku_actor": zaku_name,
        "city_origin": [origin.x, origin.y, origin.z],
        "city_extent": [extent.x, extent.y, extent.z],
        "camera_location": [camera_loc.x, camera_loc.y, camera_loc.z],
        "camera_rotation": [camera_rot.pitch, camera_rot.yaw, camera_rot.roll],
        "api_cost": "none_local_ue5_only",
    }
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


main()
