import json
import math
from pathlib import Path

import bpy
import mathutils


ROOT = Path(r"D:\Clawdbot_Docker_20260125")
SCENE_BLEND = ROOT / "projects" / "AtsugiMechaCity" / "diagnostics" / "hon_atsugi_station" / "Hon_Atsugi_Station_Plateau_Mecha.blend"
OSM_JSON = ROOT / "projects" / "AtsugiMechaCity" / "diagnostics" / "hon_atsugi_station" / "hon_atsugi_osm_station_query.json"
SLICE_JSON = ROOT / "projects" / "AtsugiMechaCity" / "diagnostics" / "hon_atsugi_station" / "hon_atsugi_station_plateau_slice.json"
OUT_DIR = ROOT / "services" / "ai_image_gen" / "outputs"
OUTPUT_BACKGROUND = OUT_DIR / "hon_atsugi_osm_station_background_3d.png"
OUTPUT_DOM = OUT_DIR / "hon_atsugi_osm_station_dom_cutout.png"
OUTPUT_REFERENCE = OUT_DIR / "hon_atsugi_osm_station_reference_3d.png"
OUTPUT_REPORT = OUT_DIR / "hon_atsugi_osm_station_render_report.json"

HON_ATSUGI_LAT = 35.4393389
HON_ATSUGI_LON = 139.3643379
TARGET_RADIUS = 520.0


def material(name, color):
    mat = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    mat.diffuse_color = color
    return mat


def nearest_z(points, x, y):
    best = 0.0
    best_d = float("inf")
    for px, py, pz in points:
        d = (px - x) ** 2 + (py - y) ** 2
        if d < best_d:
            best_d = d
            best = pz
    return float(best)


def look_at(obj, target):
    direction = mathutils.Vector(target) - obj.location
    obj.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()


def make_mesh(name, vertices, faces, mat):
    mesh = bpy.data.meshes.new(f"{name}_Mesh")
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    obj.data.materials.append(mat)
    return obj


def rectangle_for_segment(p0, p1, width):
    x0, y0, z0 = p0
    x1, y1, z1 = p1
    dx, dy = x1 - x0, y1 - y0
    length = math.hypot(dx, dy)
    if length < 0.001:
        return None
    nx, ny = -dy / length * width * 0.5, dx / length * width * 0.5
    return [
        (x0 - nx, y0 - ny, z0),
        (x1 - nx, y1 - ny, z1),
        (x1 + nx, y1 + ny, z1),
        (x0 + nx, y0 + ny, z0),
    ]


def add_segment_strip(name, points, width, mat):
    made = 0
    for index in range(len(points) - 1):
        rect = rectangle_for_segment(points[index], points[index + 1], width)
        if not rect:
            continue
        make_mesh(f"{name}_{index:03d}", rect, [(0, 1, 2, 3)], mat)
        made += 1
    return made


def add_polyline_sleepers(name, points, mat):
    made = 0
    spacing = 11.0
    for index in range(len(points) - 1):
        p0 = mathutils.Vector(points[index])
        p1 = mathutils.Vector(points[index + 1])
        segment = p1 - p0
        length = math.hypot(segment.x, segment.y)
        if length < spacing:
            continue
        angle = math.atan2(segment.y, segment.x) + math.pi * 0.5
        count = max(1, int(length / spacing))
        for item in range(count):
            t = (item + 0.5) / count
            center = p0.lerp(p1, t)
            dx = math.cos(angle) * 2.5
            dy = math.sin(angle) * 2.5
            along_dx = -math.sin(angle) * 0.32
            along_dy = math.cos(angle) * 0.32
            z = center.z + 0.03
            verts = [
                (center.x - dx - along_dx, center.y - dy - along_dy, z),
                (center.x + dx - along_dx, center.y + dy - along_dy, z),
                (center.x + dx + along_dx, center.y + dy + along_dy, z),
                (center.x - dx + along_dx, center.y - dy + along_dy, z),
            ]
            make_mesh(f"{name}_{index:03d}_{item:02d}", verts, [(0, 1, 2, 3)], mat)
            made += 1
    return made


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


def localizer():
    def convert(lat, lon, z):
        meters_per_deg_lat = 111_132.0
        meters_per_deg_lon = 111_320.0 * math.cos(math.radians(HON_ATSUGI_LAT))
        x = (lon - HON_ATSUGI_LON) * meters_per_deg_lon
        y = (lat - HON_ATSUGI_LAT) * meters_per_deg_lat
        return float(x), float(y), float(z)

    return convert


def remove_earlier_fake_station_details():
    prefixes = (
        "HonAtsugi_Rail_",
        "HonAtsugi_StationPlaza_",
        "HonAtsugi_EnhancedRoad_",
        "HonAtsugi_Sidewalk_",
        "HonAtsugi_LaneDash_",
        "HonAtsugi_Crosswalk_",
        "TempStation_",
        "FinalStation_",
        "FinalStationV2_",
    )
    for obj in list(bpy.context.scene.objects):
        if obj.name.startswith(prefixes):
            bpy.data.objects.remove(obj, do_unlink=True)


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    osm = json.loads(OSM_JSON.read_text(encoding="utf-8"))
    terrain = json.loads(SLICE_JSON.read_text(encoding="utf-8"))["terrain_vertices"]
    nodes = {item["id"]: item for item in osm["elements"] if item["type"] == "node"}
    ways = [item for item in osm["elements"] if item["type"] == "way"]
    to_local = localizer()

    bpy.ops.wm.open_mainfile(filepath=str(SCENE_BLEND))
    remove_earlier_fake_station_details()

    rail_mat = material("OSM_Odakyu_Rail_Steel", (0.06, 0.055, 0.05, 1.0))
    sleeper_mat = material("OSM_Rail_Sleepers", (0.10, 0.08, 0.065, 1.0))
    platform_mat = material("OSM_HonAtsugi_Platform_Concrete", (0.50, 0.49, 0.45, 1.0))
    platform_edge_mat = material("OSM_Platform_Edge_Line", (0.90, 0.84, 0.36, 1.0))
    station_mat = material("OSM_Station_Node_Blue", (0.03, 0.16, 0.45, 1.0))

    stats = {
        "rail_ways": 0,
        "rail_segments": 0,
        "sleepers": 0,
        "platform_ways": 0,
        "platform_segments": 0,
        "station_markers": 0,
    }

    platform_points = []
    rail_points = []
    for way in ways:
        tags = way.get("tags") or {}
        raw_points = []
        for node_id in way.get("nodes", []):
            node = nodes.get(node_id)
            if not node:
                continue
            x, y, _ = to_local(node["lat"], node["lon"], 0.0)
            if math.hypot(x, y) > TARGET_RADIUS + 40:
                continue
            z = nearest_z(terrain, x, y)
            raw_points.append((x, y, z + 0.55))
        if len(raw_points) < 2:
            continue
        if tags.get("railway") == "rail":
            stats["rail_ways"] += 1
            stats["rail_segments"] += add_segment_strip(f"OSM_Odakyu_Rail_{way['id']}", raw_points, 0.55, rail_mat)
            stats["sleepers"] += add_polyline_sleepers(f"OSM_Odakyu_Sleeper_{way['id']}", raw_points, sleeper_mat)
            rail_points.extend(raw_points)
        if tags.get("railway") == "platform" or tags.get("public_transport") == "platform":
            stats["platform_ways"] += 1
            if len(raw_points) > 3 and way.get("nodes", [None])[0] == way.get("nodes", [None])[-1]:
                make_mesh(f"OSM_HonAtsugi_Platform_{way['id']}", raw_points, [tuple(range(len(raw_points)))], platform_mat)
                stats["platform_segments"] += 1
            else:
                stats["platform_segments"] += add_segment_strip(f"OSM_HonAtsugi_Platform_{way['id']}", raw_points, 5.8, platform_mat)
            stats["platform_segments"] += add_segment_strip(f"OSM_HonAtsugi_PlatformEdge_{way['id']}", raw_points, 0.38, platform_edge_mat)
            platform_points.extend(raw_points)

    station_nodes = []
    for item in osm["elements"]:
        tags = item.get("tags") or {}
        if item["type"] != "node":
            continue
        if tags.get("railway") == "station" or tags.get("public_transport") == "station":
            x, y, _ = to_local(item["lat"], item["lon"], 0.0)
            if math.hypot(x, y) <= TARGET_RADIUS:
                z = nearest_z(terrain, x, y) + 10.0
                bpy.ops.mesh.primitive_cube_add(size=1.0, location=(x, y, z))
                marker = bpy.context.object
                marker.name = f"OSM_HonAtsugi_StationMarker_{item['id']}"
                marker.scale = (7.5, 0.8, 2.2)
                marker.data.materials.append(station_mat)
                station_nodes.append((x, y, z))
                stats["station_markers"] += 1

    mecha_objs = [
        obj for obj in bpy.context.scene.objects
        if obj.type == "MESH" and (obj.name.startswith("FrozenPose_") or "tmpsvjdp8mbobj" in obj.name)
    ]
    mecha_min, mecha_max = bounds(mecha_objs)
    mecha_center = (mecha_min + mecha_max) * 0.5
    target_points = platform_points or rail_points or [(0.0, 0.0, nearest_z(terrain, 0.0, 0.0))]
    avg_x = sum(p[0] for p in target_points) / len(target_points)
    avg_y = sum(p[1] for p in target_points) / len(target_points)
    avg_z = sum(p[2] for p in target_points) / len(target_points)

    scene = bpy.context.scene
    for engine in ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE"):
        try:
            scene.render.engine = engine
            break
        except TypeError:
            pass
    scene.render.resolution_x = 768
    scene.render.resolution_y = 512
    scene.view_settings.view_transform = "Standard"
    scene.view_settings.look = "Medium High Contrast"
    scene.view_settings.exposure = -0.22
    scene.view_settings.gamma = 1.0
    if scene.world is None:
        scene.world = bpy.data.worlds.new("OSM_HonAtsugi_World")
    scene.world.color = (0.55, 0.63, 0.75)

    cam_data = bpy.data.cameras.new("OSM_HonAtsugi_Camera")
    camera = bpy.data.objects.new("OSM_HonAtsugi_Camera", cam_data)
    bpy.context.collection.objects.link(camera)
    camera.data.type = "PERSP"
    camera.data.lens = 35
    camera.data.clip_end = 20000
    camera.location = (avg_x + 150, avg_y - 210, avg_z + 86)
    look_at(camera, (avg_x + 10, avg_y - 4, avg_z + 22))
    scene.camera = camera

    sun_data = bpy.data.lights.new("OSM_HonAtsugi_Sun", type="SUN")
    sun = bpy.data.objects.new("OSM_HonAtsugi_Sun", sun_data)
    bpy.context.collection.objects.link(sun)
    sun.rotation_euler = (math.radians(43), 0.0, math.radians(-32))
    sun.data.energy = 2.0
    sun.data.angle = math.radians(4.5)

    fill_data = bpy.data.lights.new("OSM_HonAtsugi_Fill", type="AREA")
    fill = bpy.data.objects.new("OSM_HonAtsugi_Fill", fill_data)
    bpy.context.collection.objects.link(fill)
    fill.location = (avg_x - 90, avg_y - 80, avg_z + 120)
    fill.data.energy = 260
    fill.data.size = 75

    for obj in mecha_objs:
        obj.hide_render = True
    scene.render.film_transparent = False
    scene.render.filepath = str(OUTPUT_BACKGROUND)
    bpy.ops.render.render(write_still=True)

    for obj in mecha_objs:
        obj.hide_render = False
    scene.render.filepath = str(OUTPUT_REFERENCE)
    bpy.ops.render.render(write_still=True)

    for obj in bpy.context.scene.objects:
        if obj.type == "MESH" and obj not in mecha_objs:
            obj.hide_render = True
    scene.render.film_transparent = True
    scene.render.filepath = str(OUTPUT_DOM)
    bpy.ops.render.render(write_still=True)

    report = {
        "source": "OpenStreetMap via Overpass query, transformed to PLATEAU local coordinates",
        "station_lat_lon": [HON_ATSUGI_LAT, HON_ATSUGI_LON],
        "outputs": {
            "background": str(OUTPUT_BACKGROUND),
            "dom_cutout": str(OUTPUT_DOM),
            "reference": str(OUTPUT_REFERENCE),
        },
        "stats": stats,
        "camera_target": [round(avg_x, 3), round(avg_y, 3), round(avg_z, 3)],
        "mecha_center": [round(float(v), 3) for v in mecha_center],
    }
    OUTPUT_REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
