import json
import math
from pathlib import Path

import bpy
import mathutils


ROOT = Path(r"D:\Clawdbot_Docker_20260125")
SCENE_BLEND = ROOT / "projects" / "AtsugiMechaCity" / "diagnostics" / "hon_atsugi_station" / "Hon_Atsugi_Station_Plateau_Mecha.blend"
OUT_DIR = ROOT / "services" / "ai_image_gen" / "outputs"
OUTPUT_BACKGROUND = OUT_DIR / "hon_atsugi_station_front_background_3d.png"
OUTPUT_REFERENCE = OUT_DIR / "hon_atsugi_station_front_reference_3d.png"
OUTPUT_DOM = OUT_DIR / "hon_atsugi_station_front_dom_cutout.png"
OUTPUT_REPORT = OUT_DIR / "hon_atsugi_station_front_render_report.json"


def material(name, color):
    mat = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    mat.diffuse_color = color
    return mat


def box(name, center, size, mat):
    cx, cy, cz = center
    sx, sy, sz = size
    x0, x1 = cx - sx / 2, cx + sx / 2
    y0, y1 = cy - sy / 2, cy + sy / 2
    z0, z1 = cz - sz / 2, cz + sz / 2
    verts = [
        (x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0),
        (x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1),
    ]
    faces = [(0, 1, 2, 3), (4, 7, 6, 5), (0, 4, 5, 1), (1, 5, 6, 2), (2, 6, 7, 3), (3, 7, 4, 0)]
    mesh = bpy.data.meshes.new(f"{name}_Mesh")
    mesh.from_pydata(verts, [], faces)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    obj.data.materials.append(mat)
    return obj


def rect(name, center, size, mat, z=None):
    cx, cy, cz = center
    sx, sy = size
    if z is None:
        z = cz
    verts = [
        (cx - sx / 2, cy - sy / 2, z),
        (cx + sx / 2, cy - sy / 2, z),
        (cx + sx / 2, cy + sy / 2, z),
        (cx - sx / 2, cy + sy / 2, z),
    ]
    mesh = bpy.data.meshes.new(f"{name}_Mesh")
    mesh.from_pydata(verts, [], [(0, 1, 2, 3)])
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    obj.data.materials.append(mat)
    return obj


def cylinder(name, location, radius, depth, mat, vertices=18):
    bpy.ops.mesh.primitive_cylinder_add(vertices=vertices, radius=radius, depth=depth, location=location)
    obj = bpy.context.object
    obj.name = name
    obj.data.materials.append(mat)
    return obj


def bounds(objects):
    min_v = mathutils.Vector((float("inf"), float("inf"), float("inf")))
    max_v = mathutils.Vector((float("-inf"), float("-inf"), float("-inf")))
    for obj in objects:
        for corner in obj.bound_box:
            point = obj.matrix_world @ mathutils.Vector(corner)
            for axis in range(3):
                min_v[axis] = min(min_v[axis], point[axis])
                max_v[axis] = max(max_v[axis], point[axis])
    return min_v, max_v


def look_at(obj, target):
    direction = mathutils.Vector(target) - obj.location
    obj.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()


def clear_previous():
    prefixes = (
        "StationFront_",
        "OSM_",
        "TempStation_",
        "FinalStation_",
        "FinalStationV2_",
    )
    for obj in list(bpy.context.scene.objects):
        if obj.name.startswith(prefixes):
            bpy.data.objects.remove(obj, do_unlink=True)


def remove_box_city_for_station_front():
    prefixes = (
        "HonAtsugi_Bldg_",
        "HonAtsugi_Facade_",
    )
    for obj in list(bpy.context.scene.objects):
        if obj.name.startswith(prefixes):
            bpy.data.objects.remove(obj, do_unlink=True)


def add_station_front_details(base_z):
    mats = {
        "road": material("StationFront_Asphalt", (0.055, 0.055, 0.052, 1)),
        "crosswalk": material("StationFront_Crosswalk_White", (0.91, 0.90, 0.84, 1)),
        "sidewalk": material("StationFront_Sidewalk_Block", (0.42, 0.39, 0.33, 1)),
        "curb": material("StationFront_Curb_Light", (0.74, 0.72, 0.66, 1)),
        "building": material("StationFront_Commercial_Wall", (0.62, 0.63, 0.60, 1)),
        "glass": material("StationFront_Glass", (0.08, 0.12, 0.15, 1)),
        "sign_blue": material("StationFront_Sign_Blue", (0.05, 0.10, 0.70, 1)),
        "sign_yellow": material("StationFront_Sign_Yellow", (0.95, 0.72, 0.08, 1)),
        "sign_red": material("StationFront_Sign_Red", (0.75, 0.06, 0.05, 1)),
        "sign_green": material("StationFront_Sign_Green", (0.04, 0.48, 0.20, 1)),
        "metal": material("StationFront_Dark_Metal", (0.06, 0.065, 0.065, 1)),
        "deck": material("StationFront_Pedestrian_Deck", (0.46, 0.48, 0.46, 1)),
        "plant": material("StationFront_Planting", (0.08, 0.28, 0.10, 1)),
    }

    z = base_z + 0.18
    stats = {"crosswalk_stripes": 0, "sign_panels": 0, "windows": 0, "bollards": 0, "lamps": 0}

    rect("StationFront_Road_Plaza", (30, -92, z), (260, 95), mats["road"])
    rect("StationFront_Sidewalk_Foreground", (30, -151, z + 0.05), (265, 30), mats["sidewalk"])
    rect("StationFront_Station_Plaza", (48, -38, z + 0.04), (185, 46), mats["sidewalk"])
    rect("StationFront_Curb_Edge", (30, -118, z + 0.08), (265, 2.4), mats["curb"])

    # A broad scramble-style crossing, inspired by the station-front reference photos.
    for i in range(13):
        y = -116 + i * 3.2
        rect(f"StationFront_Crosswalk_Main_{i:02d}", (23, y, z + 0.12), (245, 1.28), mats["crosswalk"])
        stats["crosswalk_stripes"] += 1
    for i in range(7):
        x = -94 + i * 9.5
        rect(f"StationFront_Crosswalk_Side_{i:02d}", (x, -68, z + 0.12), (1.15, 72), mats["crosswalk"])
        stats["crosswalk_stripes"] += 1

    # Commercial building row facing the crossing.
    building_specs = [
        ("LeftGlassTower", (-74, -5, base_z + 32), (30, 22, 62), mats["building"], mats["glass"]),
        ("CenterNarrowSign", (-28, -1, base_z + 26), (24, 18, 50), mats["building"], mats["glass"]),
        ("CenterWhiteBlock", (18, 4, base_z + 25), (34, 18, 48), mats["building"], mats["glass"]),
        ("RightStationMall", (77, 8, base_z + 30), (58, 22, 58), mats["building"], mats["glass"]),
    ]
    for name, center, size, wall, glass in building_specs:
        box(f"StationFront_Building_{name}", center, size, wall)
        cx, cy, cz = center
        sx, _sy, sz = size
        floors = max(4, int(sz / 7))
        cols = max(3, int(sx / 8))
        for floor in range(floors):
            for col in range(cols):
                wx = cx - sx * 0.38 + col * sx * 0.76 / max(1, cols - 1)
                wz = base_z + 8 + floor * 6.0
                box(f"StationFront_Window_{name}_{floor:02d}_{col:02d}", (wx, cy - 11.2, wz), (3.6, 0.25, 2.0), glass)
                stats["windows"] += 1

    sign_mats = [mats["sign_blue"], mats["sign_yellow"], mats["sign_red"], mats["sign_green"]]
    sign_specs = [
        (-30, -10.4, base_z + 35, 15, 0.35, 5),
        (-30, -10.5, base_z + 27, 17, 0.35, 4),
        (18, -5.4, base_z + 16, 26, 0.35, 5),
        (77, -3.5, base_z + 29, 34, 0.35, 11),
        (92, -3.7, base_z + 50, 11, 0.35, 19),
    ]
    for index, spec in enumerate(sign_specs):
        box(f"StationFront_Sign_{index:02d}", spec[:3], spec[3:], sign_mats[index % len(sign_mats)])
        stats["sign_panels"] += 1

    # Pedestrian deck on the right side, visible in the user's reference.
    box("StationFront_PedestrianDeck_Right", (130, -19, base_z + 17), (68, 6, 3.2), mats["deck"])
    for x in (104, 126, 150):
        cylinder(f"StationFront_DeckPillar_{x}", (x, -19, base_z + 8.5), 0.65, 15.0, mats["metal"])

    # Street furniture.
    for i, x in enumerate(range(-92, 111, 14)):
        cylinder(f"StationFront_Bollard_{i:02d}", (x, -58, base_z + 1.15), 0.32, 1.9, mats["metal"], 14)
        stats["bollards"] += 1
    for i, x in enumerate((-104, -40, 36, 108)):
        cylinder(f"StationFront_LampPost_{i:02d}", (x, -70, base_z + 6.0), 0.22, 11.0, mats["metal"], 14)
        box(f"StationFront_LampHead_{i:02d}", (x + 1.5, -70, base_z + 12.0), (3.2, 0.6, 0.45), mats["metal"])
        stats["lamps"] += 1
    cylinder("StationFront_TrafficSignalPole", (118, -66, base_z + 6.5), 0.28, 13.0, mats["metal"], 14)
    box("StationFront_TrafficSignalHead", (113, -66, base_z + 12.3), (5.5, 0.7, 1.2), mats["metal"])

    rect("StationFront_Planting_Roundabout", (92, -41, base_z + 0.28), (22, 10), mats["plant"])
    return stats


def setup_camera_and_lights(target, base_z):
    scene = bpy.context.scene
    for engine in ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE"):
        try:
            scene.render.engine = engine
            break
        except TypeError:
            pass
    scene.render.resolution_x = 1024
    scene.render.resolution_y = 576
    scene.view_settings.view_transform = "Standard"
    scene.view_settings.look = "Medium High Contrast"
    scene.view_settings.exposure = -0.12
    scene.view_settings.gamma = 1.0
    if scene.world is None:
        scene.world = bpy.data.worlds.new("StationFront_World")
    scene.world.color = (0.60, 0.70, 0.88)
    scene.world.use_nodes = True
    bg = scene.world.node_tree.nodes.get("Background")
    if bg:
        bg.inputs["Color"].default_value = (0.60, 0.70, 0.88, 1.0)
        bg.inputs["Strength"].default_value = 0.48

    cam_data = bpy.data.cameras.new("StationFront_Camera")
    camera = bpy.data.objects.new("StationFront_Camera", cam_data)
    bpy.context.collection.objects.link(camera)
    camera.data.type = "PERSP"
    camera.data.lens = 29
    camera.data.clip_end = 20000
    camera.location = (target.x - 18, target.y - 170, base_z + 26)
    look_at(camera, (target.x + 0, target.y - 52, base_z + 20))
    scene.camera = camera

    sun_data = bpy.data.lights.new("StationFront_Sun", type="SUN")
    sun = bpy.data.objects.new("StationFront_Sun", sun_data)
    bpy.context.collection.objects.link(sun)
    sun.rotation_euler = (math.radians(42), 0.0, math.radians(-38))
    sun.data.energy = 2.3
    sun.data.angle = math.radians(4.5)

    fill_data = bpy.data.lights.new("StationFront_Fill", type="AREA")
    fill = bpy.data.objects.new("StationFront_Fill", fill_data)
    bpy.context.collection.objects.link(fill)
    fill.location = (target.x - 90, target.y - 60, base_z + 82)
    fill.data.energy = 240
    fill.data.size = 70


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.open_mainfile(filepath=str(SCENE_BLEND))
    clear_previous()
    remove_box_city_for_station_front()

    mecha_objs = [
        obj for obj in bpy.context.scene.objects
        if obj.type == "MESH" and (obj.name.startswith("FrozenPose_") or "tmpsvjdp8mbobj" in obj.name)
    ]
    if not mecha_objs:
        raise RuntimeError("No DOM mesh found in scene.")
    mecha_min, mecha_max = bounds(mecha_objs)
    mecha_center = (mecha_min + mecha_max) * 0.5
    base_z = float(mecha_min.z)

    stats = add_station_front_details(base_z)
    setup_camera_and_lights(mecha_center, base_z)
    bpy.context.view_layer.update()

    for obj in mecha_objs:
        obj.hide_render = True
    bpy.context.scene.render.film_transparent = False
    bpy.context.scene.render.filepath = str(OUTPUT_BACKGROUND)
    bpy.ops.render.render(write_still=True)

    for obj in mecha_objs:
        obj.hide_render = False
    bpy.context.scene.render.film_transparent = False
    bpy.context.scene.render.filepath = str(OUTPUT_REFERENCE)
    bpy.ops.render.render(write_still=True)

    for obj in bpy.context.scene.objects:
        if obj.type == "MESH" and obj not in mecha_objs:
            obj.hide_render = True
    for obj in mecha_objs:
        obj.hide_render = False
    bpy.context.scene.render.film_transparent = True
    bpy.context.scene.render.filepath = str(OUTPUT_DOM)
    bpy.ops.render.render(write_still=True)

    report = {
        "source_reference": "User-provided local Hon-Atsugi station-front screenshots used as visual reference only; not used as texture.",
        "outputs": {
            "background": str(OUTPUT_BACKGROUND),
            "reference": str(OUTPUT_REFERENCE),
            "dom_cutout": str(OUTPUT_DOM),
        },
        "procedural_features": stats,
        "note": "This is station-front/crossing composition; railway platform is intentionally not emphasized because it is not visible in the reference photos.",
    }
    OUTPUT_REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
