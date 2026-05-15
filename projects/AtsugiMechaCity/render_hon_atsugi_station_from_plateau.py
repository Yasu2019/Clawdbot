import json
import math
import subprocess
from pathlib import Path

import bpy
import mathutils


ROOT = Path(r"D:\Clawdbot_Docker_20260125")
BLEND_PATH = ROOT / "Gundam" / "Atsugi_Front_Final.blend"
OUT_DIR = ROOT / "projects" / "AtsugiMechaCity" / "diagnostics" / "hon_atsugi_station"
SLICE_JSON = OUT_DIR / "hon_atsugi_station_plateau_slice.json"
OUTPUT_BLEND = OUT_DIR / "Hon_Atsugi_Station_Plateau_Mecha.blend"
OUTPUT_CLOSE = OUT_DIR / "Hon_Atsugi_Station_Plateau_Mecha_Close.png"
OUTPUT_WIDE = OUT_DIR / "Hon_Atsugi_Station_Plateau_Mecha_Wide.png"
OUTPUT_REPORT = OUT_DIR / "hon_atsugi_station_plateau_mecha_report.json"

HON_ATSUGI_LAT = 35.4393389
HON_ATSUGI_LON = 139.3643379
TARGET_RADIUS = 480.0
MECHA_NAME = "Zaku_Armature"
TARGET_HEIGHT_M = 32.0
MECHA_OFFSET = (60.0, -90.0)
MECHA_CLEARANCE_RADIUS = 34.0


def ensure_dir():
    OUT_DIR.mkdir(parents=True, exist_ok=True)


def material_once(name, color):
    mat = bpy.data.materials.get(name)
    if mat is None:
        mat = bpy.data.materials.new(name)
    mat.diffuse_color = color
    return mat


def world_bounds(objects):
    min_v = mathutils.Vector((float("inf"), float("inf"), float("inf")))
    max_v = mathutils.Vector((float("-inf"), float("-inf"), float("-inf")))
    found = False
    for obj in objects:
        if obj.type != "MESH":
            continue
        found = True
        for corner in obj.bound_box:
            world_corner = obj.matrix_world @ mathutils.Vector(corner)
            for axis in range(3):
                min_v[axis] = min(min_v[axis], world_corner[axis])
                max_v[axis] = max(max_v[axis], world_corner[axis])
    if not found:
        raise RuntimeError("No mesh bounds found.")
    return min_v, max_v


def descendants(obj):
    items = []
    pending = list(obj.children)
    while pending:
        child = pending.pop()
        items.append(child)
        pending.extend(child.children)
    return items


def look_at(obj, target):
    direction = mathutils.Vector(target) - obj.location
    obj.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()


def normalize_mecha(mecha, mecha_parts):
    mecha.rotation_euler = tuple(math.radians(v) for v in (90.0, 0.0, 0.0))
    bpy.context.view_layer.update()
    min_v, max_v = world_bounds(mecha_parts)
    current_height = max_v.z - min_v.z
    if current_height <= 0:
        raise RuntimeError("Mecha height is zero; cannot scale.")
    scale_factor = TARGET_HEIGHT_M / current_height
    mecha.scale = tuple(component * scale_factor for component in mecha.scale)
    bpy.context.view_layer.update()
    return float(scale_factor)


def set_group_bottom_to_z(root, mesh_objects, target_z):
    min_v, _max_v = world_bounds(mesh_objects)
    delta_z = target_z - min_v.z
    root.location.z += delta_z
    return float(delta_z)


def nearest_z(points, x, y):
    best = None
    best_d = float("inf")
    for px, py, pz in points:
        d = (px - x) ** 2 + (py - y) ** 2
        if d < best_d:
            best_d = d
            best = pz
    if best is None:
        return 0.0, 0.0
    return float(best), math.sqrt(best_d)


def build_plateau_slice():
    helper = r'''
import json
import math
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from pyproj import Transformer

root = Path(sys.argv[1])
out_path = Path(sys.argv[2])
lat = float(sys.argv[3])
lon = float(sys.argv[4])
radius = float(sys.argv[5])
transformer = Transformer.from_crs("EPSG:6697", "EPSG:6677", always_xy=False)
station_y, station_x, _station_z = transformer.transform(lat, lon, 0.0)
station = (float(station_x), float(-station_y))
ns_gml = "http://www.opengis.net/gml"
pos_list_tag = f"{{{ns_gml}}}posList"
ns_bldg = "http://www.opengis.net/citygml/building/2.0"
building_tag = f"{{{ns_bldg}}}Building"

def convert_triplets(values):
    lats, lons, alts = [], [], []
    for index in range(0, len(values), 3):
        lats.append(float(values[index]))
        lons.append(float(values[index + 1]))
        alts.append(float(values[index + 2]))
    ys, xs, zs = transformer.transform(lats, lons, alts)
    pts = []
    for x, y, z in zip(xs, ys, zs):
        pts.append([float(x - station[0]), float(-y - station[1]), float(z)])
    return pts

def near(points, margin=0.0):
    limit = radius + margin
    for x, y, _z in points:
        if math.hypot(x, y) <= limit:
            return True
    return False

dem_files = [
    "53391229_dem_6697_op.gml",
    "53391228_dem_6697_op.gml",
    "53391239_dem_6697_op.gml",
    "53391238_dem_6697_op.gml",
]
bldg_files = [
    "53391229_bldg_6697_op.gml",
    "53391228_bldg_6697_op.gml",
    "53391239_bldg_6697_op.gml",
    "53391238_bldg_6697_op.gml",
]
tran_files = [
    "53391229_tran_6697_op.gml",
    "53391228_tran_6697_op.gml",
    "53391239_tran_6697_op.gml",
    "53391238_tran_6697_op.gml",
]

terrain_vertices = []
terrain_faces = []
for file_name in dem_files:
    path = root / "data" / "PLATEAU" / "Atsugi" / "udx" / "dem" / file_name
    for _event, elem in ET.iterparse(path, events=("end",)):
        if elem.tag == pos_list_tag and elem.text:
            values = elem.text.strip().split()
            if len(values) in (9, 12):
                pts = convert_triplets(values[:9])
                cx = sum(p[0] for p in pts) / 3.0
                cy = sum(p[1] for p in pts) / 3.0
                if math.hypot(cx, cy) <= radius:
                    start = len(terrain_vertices)
                    terrain_vertices.extend(pts)
                    terrain_faces.append([start, start + 1, start + 2])
        elem.clear()

road_vertices = []
road_faces = []
for file_name in tran_files:
    path = root / "data" / "PLATEAU" / "Atsugi" / "udx" / "tran" / file_name
    for _event, elem in ET.iterparse(path, events=("end",)):
        if elem.tag == pos_list_tag and elem.text:
            values = elem.text.strip().split()
            if len(values) >= 9 and len(values) % 3 == 0:
                pts = convert_triplets(values)
                if len(pts) >= 4 and pts[0] == pts[-1]:
                    pts = pts[:-1]
                if len(pts) >= 3 and near(pts, 40.0):
                    start = len(road_vertices)
                    road_vertices.extend([[p[0], p[1], p[2] + 0.12] for p in pts])
                    for index in range(1, len(pts) - 1):
                        road_faces.append([start, start + index, start + index + 1])
        elem.clear()

buildings = []
for file_name in bldg_files:
    path = root / "data" / "PLATEAU" / "Atsugi" / "udx" / "bldg" / file_name
    for _event, elem in ET.iterparse(path, events=("end",)):
        if elem.tag == building_tag:
            points = []
            for pos_list in elem.iter(pos_list_tag):
                if not pos_list.text:
                    continue
                values = pos_list.text.strip().split()
                if len(values) >= 9 and len(values) % 3 == 0:
                    points.extend(convert_triplets(values))
            if points and near(points, 20.0):
                xs = [p[0] for p in points]
                ys = [p[1] for p in points]
                zs = [p[2] for p in points]
                min_x, max_x = min(xs), max(xs)
                min_y, max_y = min(ys), max(ys)
                min_z, max_z = min(zs), max(zs)
                if (max_x - min_x) >= 1.0 and (max_y - min_y) >= 1.0 and (max_z - min_z) >= 2.0:
                    buildings.append([min_x, max_x, min_y, max_y, min_z, max_z])
            elem.clear()

payload = {
    "station": {"lat": lat, "lon": lon, "raw_x": station[0], "raw_y": station[1]},
    "radius": radius,
    "terrain_vertices": terrain_vertices,
    "terrain_faces": terrain_faces,
    "road_vertices": road_vertices,
    "road_faces": road_faces,
    "buildings": buildings,
}
out_path.write_text(json.dumps(payload), encoding="utf-8")
'''
    result = subprocess.run(
        ["python", "-c", helper, str(ROOT), str(SLICE_JSON), str(HON_ATSUGI_LAT), str(HON_ATSUGI_LON), str(TARGET_RADIUS)],
        check=False,
        capture_output=True,
        text=True,
        timeout=240,
    )
    if result.returncode != 0:
        raise RuntimeError(f"PLATEAU slice helper failed: {result.stderr.strip()}")
    return json.loads(SLICE_JSON.read_text(encoding="utf-8"))


def add_mesh_object(name, vertices, faces, material):
    mesh = bpy.data.meshes.new(f"{name}_Mesh")
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    obj.data.materials.append(material)
    return obj


def add_building_box(name, box, material):
    min_x, max_x, min_y, max_y, min_z, max_z = box
    vertices = [
        (min_x, min_y, min_z),
        (max_x, min_y, min_z),
        (max_x, max_y, min_z),
        (min_x, max_y, min_z),
        (min_x, min_y, max_z),
        (max_x, min_y, max_z),
        (max_x, max_y, max_z),
        (min_x, max_y, max_z),
    ]
    faces = [
        (0, 1, 2, 3),
        (4, 7, 6, 5),
        (0, 4, 5, 1),
        (1, 5, 6, 2),
        (2, 6, 7, 3),
        (3, 7, 4, 0),
    ]
    return add_mesh_object(name, vertices, faces, material)


def box_intersects_clearance(box, center, radius):
    min_x, max_x, min_y, max_y, _min_z, _max_z = box
    closest_x = min(max(center[0], min_x), max_x)
    closest_y = min(max(center[1], min_y), max_y)
    return math.hypot(closest_x - center[0], closest_y - center[1]) <= radius


def render(path, target, ground_z, ortho_scale, offset, look_height):
    camera_data = bpy.data.cameras.new("HonAtsugi_Camera")
    camera = bpy.data.objects.new("HonAtsugi_Camera", camera_data)
    bpy.context.collection.objects.link(camera)
    camera.data.type = "ORTHO"
    camera.data.ortho_scale = ortho_scale
    camera.location = (target[0] + offset[0], target[1] + offset[1], ground_z + offset[2])
    camera.data.clip_end = 20000
    look_at(camera, (target[0], target[1], ground_z + look_height))
    bpy.context.scene.camera = camera

    sun_data = bpy.data.lights.new("HonAtsugi_Sun", type="SUN")
    sun = bpy.data.objects.new("HonAtsugi_Sun", sun_data)
    bpy.context.collection.objects.link(sun)
    sun.location = (target[0] - 100, target[1] - 120, ground_z + 180)
    sun.data.energy = 2.6

    bpy.context.scene.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)


def main():
    ensure_dir()
    payload = build_plateau_slice()

    bpy.ops.wm.open_mainfile(filepath=str(BLEND_PATH))
    for obj in list(bpy.data.objects):
        if obj.type == "MESH" and obj.name.startswith("Bldg"):
            bpy.data.objects.remove(obj, do_unlink=True)

    terrain_mat = material_once("HonAtsugi_Terrain_Matte", (0.22, 0.34, 0.25, 1.0))
    road_mat = material_once("HonAtsugi_Road_Asphalt", (0.05, 0.052, 0.048, 1.0))
    bldg_mat = material_once("HonAtsugi_Building_Grey", (0.68, 0.7, 0.68, 1.0))
    mecha_mat = material_once("HonAtsugi_Mecha_Muted_Green", (0.28, 0.38, 0.24, 1.0))

    terrain = add_mesh_object("HonAtsugi_Terrain", payload["terrain_vertices"], payload["terrain_faces"], terrain_mat)
    roads = add_mesh_object("HonAtsugi_Roads", payload["road_vertices"], payload["road_faces"], road_mat)
    terrain_points = payload["terrain_vertices"]
    mecha_x = MECHA_OFFSET[0]
    mecha_y = MECHA_OFFSET[1]
    mecha_z, mecha_z_distance = nearest_z(terrain_points, mecha_x, mecha_y)
    station_z, station_z_distance = nearest_z(terrain_points, 0.0, 0.0)
    building_boxes = []
    skipped_for_mecha = 0
    for box in payload["buildings"]:
        if box_intersects_clearance(box, (mecha_x, mecha_y), MECHA_CLEARANCE_RADIUS):
            skipped_for_mecha += 1
            continue
        building_boxes.append(box)
    buildings = [add_building_box(f"HonAtsugi_Bldg_{index:04d}", box, bldg_mat) for index, box in enumerate(building_boxes)]

    mecha = bpy.data.objects.get(MECHA_NAME)
    mecha_report = None
    if mecha:
        mecha_parts = [obj for obj in descendants(mecha) if obj.type == "MESH"]
        if mecha_parts:
            scale_factor = normalize_mecha(mecha, mecha_parts)
            for part in mecha_parts:
                part.data.materials.clear()
                part.data.materials.append(mecha_mat)
            mecha.location.x = mecha_x
            mecha.location.y = mecha_y
            bpy.context.view_layer.update()
            delta_z = set_group_bottom_to_z(mecha, mecha_parts, mecha_z)
            bpy.context.view_layer.update()
            mecha_min, mecha_max = world_bounds(mecha_parts)
            mecha_report = {
                "name": mecha.name,
                "placement_xy": [round(mecha_x, 6), round(mecha_y, 6)],
                "terrain_z": round(mecha_z, 6),
                "terrain_nearest_distance": round(mecha_z_distance, 6),
                "scale_factor": round(scale_factor, 6),
                "delta_z": round(delta_z, 6),
                "bounds_min": [round(float(v), 6) for v in mecha_min],
                "bounds_max": [round(float(v), 6) for v in mecha_max],
            }

    bpy.context.scene.render.engine = "BLENDER_WORKBENCH"
    bpy.context.scene.display.shading.light = "STUDIO"
    bpy.context.scene.display.shading.color_type = "MATERIAL"
    if hasattr(bpy.context.scene.display.shading, "show_shadows"):
        bpy.context.scene.display.shading.show_shadows = True
    if hasattr(bpy.context.scene.display.shading, "show_cavity"):
        bpy.context.scene.display.shading.show_cavity = True
    if bpy.context.scene.world:
        bpy.context.scene.world.color = (0.55, 0.62, 0.7)
    bpy.context.scene.render.resolution_x = 1280
    bpy.context.scene.render.resolution_y = 720

    bpy.ops.wm.save_as_mainfile(filepath=str(OUTPUT_BLEND))
    render(OUTPUT_CLOSE, (mecha_x, mecha_y), mecha_z, 260, (190, -280, 210), 36)
    render(OUTPUT_WIDE, (0.0, 0.0), station_z, 760, (520, -760, 360), 48)

    report = {
        "ok": True,
        "station": payload["station"],
        "radius": payload["radius"],
        "output_blend": str(OUTPUT_BLEND),
        "output_close": str(OUTPUT_CLOSE),
        "output_wide": str(OUTPUT_WIDE),
        "terrain": {"vertices": len(payload["terrain_vertices"]), "faces": len(payload["terrain_faces"])},
        "roads": {"vertices": len(payload["road_vertices"]), "faces": len(payload["road_faces"])},
        "buildings": {
            "source_count": len(payload["buildings"]),
            "rendered_count": len(buildings),
            "skipped_for_mecha_clearance": skipped_for_mecha,
            "mecha_clearance_radius": MECHA_CLEARANCE_RADIUS,
        },
        "station_terrain_z": round(station_z, 6),
        "station_terrain_nearest_distance": round(station_z_distance, 6),
        "mecha": mecha_report,
    }
    OUTPUT_REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
