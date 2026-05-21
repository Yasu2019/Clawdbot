import sys
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import json
import math
import time
from pathlib import Path

import unreal

OUT_DIR = Path(r"D:\Clawdbot_Docker_20260125\projects\AtsugiMechaCity\diagnostics\ue5_local_render")
OUT_DIR.mkdir(parents=True, exist_ok=True)
OUT_PNG = OUT_DIR / "Atsugi_UE5_local_still.png"
REPORT = OUT_DIR / "ue5_render_still_report.json"


def log(message):
    unreal.log("[UE5LocalRender] " + message)
    print("[UE5LocalRender] " + message)


def look_at(actor, target):
    loc = actor.get_actor_location()
    dx = target.x - loc.x
    dy = target.y - loc.y
    dz = target.z - loc.z
    yaw = math.degrees(math.atan2(dy, dx))
    distance_xy = math.sqrt(dx * dx + dy * dy)
    pitch = math.degrees(math.atan2(dz, distance_xy))
    rot = unreal.Rotator(pitch, yaw, 0.0)
    actor.set_actor_rotation(rot, False)


def main():
    level_path = "/Game/Atsugi/Atsugi_Map"
    log("loading level " + level_path)
    unreal.EditorLevelLibrary.load_level(level_path)

    actors = unreal.EditorLevelLibrary.get_all_level_actors()
    mesh_actors = [a for a in actors if "StaticMeshActor" in str(a.get_class().get_name())]
    zaku = next((a for a in actors if "Zaku" in a.get_name()), None)

    target = unreal.Vector(0.0, 0.0, 250.0)
    if zaku:
        target = zaku.get_actor_location()
        target.z += 260.0
        log("found Zaku actor: " + zaku.get_name())
    else:
        log("Zaku actor not found; using map center target")

    camera_location = unreal.Vector(target.x + 1150.0, target.y - 1650.0, target.z + 520.0)
    camera = unreal.EditorLevelLibrary.spawn_actor_from_class(unreal.CineCameraActor, camera_location)
    camera.set_actor_label("Codex_Local_Render_Camera")
    look_at(camera, target)
    camera_component = camera.get_cine_camera_component()
    camera_component.set_editor_property("current_focal_length", 38.0)
    camera_component.set_editor_property("current_aperture", 5.6)
    unreal.EditorLevelLibrary.set_level_viewport_camera_info(camera_location, camera.get_actor_rotation())

    sun = unreal.EditorLevelLibrary.spawn_actor_from_class(unreal.DirectionalLight, unreal.Vector(0.0, 0.0, 900.0))
    sun.set_actor_label("Codex_Local_Render_Sun")
    sun.set_actor_rotation(unreal.Rotator(-42.0, -34.0, 0.0), False)
    sun.get_component_by_class(unreal.DirectionalLightComponent).set_editor_property("intensity", 4.5)

    sky = unreal.EditorLevelLibrary.spawn_actor_from_class(unreal.SkyLight, unreal.Vector(0.0, 0.0, 500.0))
    sky.set_actor_label("Codex_Local_Render_SkyLight")
    sky.get_component_by_class(unreal.SkyLightComponent).set_editor_property("intensity", 1.15)

    world = unreal.EditorLevelLibrary.get_editor_world()
    unreal.SystemLibrary.execute_console_command(world, "r.Lumen.DiffuseIndirect.Allow 1")
    unreal.SystemLibrary.execute_console_command(world, "r.Lumen.Reflections.Allow 1")
    unreal.SystemLibrary.execute_console_command(world, "r.ScreenPercentage 100")
    unreal.SystemLibrary.execute_console_command(world, "r.Tonemapper.Sharpen 1")

    unreal.AutomationLibrary.finish_loading_before_screenshot()
    task = unreal.AutomationLibrary.take_high_res_screenshot(
        1920,
        1080,
        str(OUT_PNG),
        camera=camera,
        mask_enabled=False,
        capture_hdr=False,
        delay=1.0,
        force_game_view=True,
    )

    status = "submitted"
    for _ in range(240):
        if OUT_PNG.exists() and OUT_PNG.stat().st_size > 0:
            status = "file_written"
            break
        time.sleep(0.5)

    report = {
        "ok": OUT_PNG.exists() and OUT_PNG.stat().st_size > 0,
        "status": status,
        "output_png": str(OUT_PNG),
        "output_size": OUT_PNG.stat().st_size if OUT_PNG.exists() else 0,
        "level": level_path,
        "actor_count": len(actors),
        "static_mesh_actor_count": len(mesh_actors),
        "zaku_actor": zaku.get_name() if zaku else None,
        "task_type": str(type(task)),
        "api_cost": "none_local_ue5_only",
    }
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


main()
