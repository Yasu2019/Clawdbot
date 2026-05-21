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
SCREEN_DIR = Path(r"D:\Clawdbot_Docker_20260125\projects\AtsugiMechaCity\Saved\Screenshots\WindowsEditor")
REPORT = OUT_DIR / "ue5_render_asset_scene_report.json"


def log(msg):
    unreal.log("[UE5AssetScene] " + msg)
    print("[UE5AssetScene] " + msg)


def look_at_rotation(src, target):
    return unreal.MathLibrary.find_look_at_rotation(src, target)


def latest_screenshot(after_ts):
    if not SCREEN_DIR.exists():
        return None
    files = [p for p in SCREEN_DIR.glob("HighresScreenshot*.png") if p.stat().st_mtime >= after_ts]
    if not files:
        return None
    return max(files, key=lambda p: p.stat().st_mtime)


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    before = time.time() - 5.0

    unreal.EditorLevelLibrary.new_level("/Temp/Codex_UE5_Local_Render_{0}".format(int(time.time())))
    city_asset = unreal.EditorAssetLibrary.load_asset("/Game/Atsugi/Atsugi_Front_Final")
    zaku_asset = unreal.EditorAssetLibrary.load_asset("/Game/Atsugi/Zaku_Posed")
    if city_asset is None:
        raise RuntimeError("Atsugi_Front_Final asset not found")

    city = unreal.EditorLevelLibrary.spawn_actor_from_object(city_asset, unreal.Vector(0.0, 0.0, 0.0))
    city.set_actor_label("Codex_Atsugi_City_Asset")
    city.set_actor_scale3d(unreal.Vector(1.0, 1.0, 1.0))

    origin, extent = city.get_actor_bounds(False)
    target = unreal.Vector(origin.x, origin.y, origin.z + extent.z * 0.35)

    zaku_name = None
    if zaku_asset is not None:
        zaku_loc = unreal.Vector(origin.x + extent.x * 0.12, origin.y - extent.y * 0.08, origin.z + 30.0)
        zaku = unreal.EditorLevelLibrary.spawn_actor_from_object(zaku_asset, zaku_loc)
        zaku.set_actor_label("Codex_Zaku_Posed")
        zaku.set_actor_scale3d(unreal.Vector(1.0, 1.0, 1.0))
        zaku_name = zaku.get_name()
        target = zaku_loc + unreal.Vector(0.0, 0.0, 180.0)

    sun = unreal.EditorLevelLibrary.spawn_actor_from_class(unreal.DirectionalLight, unreal.Vector(0.0, 0.0, extent.z + 3000.0))
    sun.set_actor_label("Codex_Sun")
    sun.set_actor_rotation(unreal.Rotator(-38.0, -35.0, 0.0), False)
    sun.get_component_by_class(unreal.DirectionalLightComponent).set_editor_property("intensity", 5.0)

    sky = unreal.EditorLevelLibrary.spawn_actor_from_class(unreal.SkyLight, unreal.Vector(0.0, 0.0, extent.z + 2400.0))
    sky.set_actor_label("Codex_SkyLight")
    sky.get_component_by_class(unreal.SkyLightComponent).set_editor_property("intensity", 1.3)

    camera_distance = max(extent.x, extent.y) * 0.92
    camera_loc = unreal.Vector(
        target.x + camera_distance * 0.45,
        target.y - camera_distance * 0.62,
        target.z + max(180.0, extent.z * 0.12),
    )
    camera_rot = look_at_rotation(camera_loc, target)
    unreal.EditorLevelLibrary.set_level_viewport_camera_info(camera_loc, camera_rot)

    world = unreal.EditorLevelLibrary.get_editor_world()
    for cmd in [
        "r.Lumen.DiffuseIndirect.Allow 1",
        "r.Lumen.Reflections.Allow 1",
        "r.ScreenPercentage 100",
        "r.Tonemapper.Sharpen 1",
        "r.ExposureOffset 0",
        "HighResShot 1920x1080",
    ]:
        unreal.SystemLibrary.execute_console_command(world, cmd)

    found = None
    for _ in range(90):
        found = latest_screenshot(before)
        if found is not None and found.stat().st_size > 0:
            break
        time.sleep(1.0)

    report = {
        "ok": found is not None,
        "screenshot": str(found) if found else None,
        "screenshot_size": found.stat().st_size if found else 0,
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
