"""
geometry_processor.py — DXF / STEP ジオメトリ解析
"""
import math
import json
import subprocess
import tempfile
from pathlib import Path
from typing import Optional

import ezdxf
import numpy as np
from shapely.geometry import Polygon, LineString, MultiLineString, Point
from shapely.ops import unary_union, polygonize

# ── 定数 ─────────────────────────────────────────────────────────────────────
N_ARC = 64   # 円弧の近似分割数
TOL   = 1e-4

# スキップするレイヤーキーワード（寸法・テキスト等）
SKIP_LAYER_KW = [
    "dim", "defpoint", "hatch", "text", "note", "anno", "title",
    "border", "center", "hidden", "leader", "arrow", "phantom",
    "寸法", "文字", "注記", "中心", "ハッチ"
]

# 曲げ線レイヤーキーワード
BEND_LAYER_KW = [
    "bend", "fold", "form", "曲げ", "曲り", "折り", "フォーム"
]


def _is_skip_layer(name: str) -> bool:
    n = name.lower()
    return any(k in n for k in SKIP_LAYER_KW)


def _is_bend_layer(name: str) -> bool:
    n = name.lower()
    return any(k in n for k in BEND_LAYER_KW)


def _arc_to_points(cx, cy, r, a_start, a_end, n=N_ARC):
    """円弧を点列に変換"""
    if a_end <= a_start:
        a_end += 360.0
    angles = np.linspace(math.radians(a_start), math.radians(a_end), max(4, n))
    return [(cx + r * math.cos(a), cy + r * math.sin(a)) for a in angles]


def _circle_to_points(cx, cy, r, n=N_ARC):
    angles = np.linspace(0, 2 * math.pi, n, endpoint=False)
    return [(cx + r * math.cos(a), cy + r * math.sin(a)) for a in angles]


def _segments_to_polylines(segments, tol=0.5):
    """線分リストをチェーン接続してポリラインに変換"""
    if not segments:
        return []
    segs = [list(s) for s in segments]
    chains = []

    while segs:
        chain = list(segs.pop(0))
        changed = True
        while changed:
            changed = False
            for i, s in enumerate(segs):
                if math.dist(chain[-1], s[0]) < tol:
                    chain.extend(s[1:])
                    segs.pop(i)
                    changed = True
                    break
                elif math.dist(chain[-1], s[-1]) < tol:
                    chain.extend(reversed(s[:-1]))
                    segs.pop(i)
                    changed = True
                    break
                elif math.dist(chain[0], s[-1]) < tol:
                    chain = s[:-1] + chain
                    segs.pop(i)
                    changed = True
                    break
                elif math.dist(chain[0], s[0]) < tol:
                    chain = list(reversed(s[1:])) + chain
                    segs.pop(i)
                    changed = True
                    break
        chains.append(chain)
    return chains


def process_dxf(file_path: str) -> dict:
    """DXF ファイルを解析して部品ジオメトリ情報を返す"""
    doc = ezdxf.readfile(file_path)
    msp = doc.modelspace()

    contour_segments = []   # 外形線セグメント [(pt1, pt2), ...]
    hole_circles     = []   # 穴円 [(cx,cy,r), ...]
    bend_segments    = []   # 曲げ線
    all_points       = []

    for entity in msp:
        layer = entity.dxf.get('layer', '0')
        if _is_skip_layer(layer):
            continue

        is_bend = _is_bend_layer(layer)

        etype = entity.dxftype()

        if etype == 'LINE':
            s = (entity.dxf.start.x, entity.dxf.start.y)
            e = (entity.dxf.end.x,   entity.dxf.end.y)
            if is_bend:
                bend_segments.append((s, e))
            else:
                contour_segments.append((s, e))
            all_points.extend([s, e])

        elif etype == 'ARC':
            cx, cy = entity.dxf.center.x, entity.dxf.center.y
            r = entity.dxf.radius
            pts = _arc_to_points(cx, cy, r,
                                  entity.dxf.start_angle,
                                  entity.dxf.end_angle)
            for i in range(len(pts) - 1):
                contour_segments.append((pts[i], pts[i+1]))
            all_points.extend(pts)

        elif etype == 'CIRCLE':
            cx, cy = entity.dxf.center.x, entity.dxf.center.y
            r = entity.dxf.radius
            hole_circles.append((cx, cy, r))
            all_points.extend(_circle_to_points(cx, cy, r, 16))

        elif etype == 'LWPOLYLINE':
            pts = [(p[0], p[1]) for p in entity.get_points('xy')]
            if entity.closed and len(pts) >= 3:
                pts.append(pts[0])
            for i in range(len(pts) - 1):
                contour_segments.append((pts[i], pts[i+1]))
            all_points.extend(pts)

        elif etype == 'POLYLINE':
            pts = [(v.dxf.location.x, v.dxf.location.y)
                   for v in entity.vertices]
            for i in range(len(pts) - 1):
                contour_segments.append((pts[i], pts[i+1]))
            all_points.extend(pts)

        elif etype == 'SPLINE':
            try:
                pts = [(p[0], p[1]) for p in entity.flattening(0.1)]
                for i in range(len(pts) - 1):
                    contour_segments.append((pts[i], pts[i+1]))
                all_points.extend(pts)
            except Exception:
                pass

    if not all_points:
        raise ValueError("ジオメトリエンティティが見つかりません")

    xs = [p[0] for p in all_points]
    ys = [p[1] for p in all_points]
    bbox = {
        'min_x': float(min(xs)), 'max_x': float(max(xs)),
        'min_y': float(min(ys)), 'max_y': float(max(ys)),
    }
    width  = bbox['max_x'] - bbox['min_x']
    height = bbox['max_y'] - bbox['min_y']

    # 外形ポリライン構築
    chains = _segments_to_polylines(contour_segments)
    # 最長チェーンを外形とみなす
    outer_chain = max(chains, key=lambda c: len(c)) if chains else []

    # 穴の分類（小さい円 ＝ 穴）
    holes = []
    if hole_circles:
        ref = min(width, height)
        for cx, cy, r in hole_circles:
            if r < ref * 0.4:
                holes.append({'cx': float(cx), 'cy': float(cy), 'r': float(r)})

    # 曲げ線の解析
    bends = []
    for s, e in bend_segments:
        blen = math.dist(s, e)
        bends.append({
            'start': [float(s[0]), float(s[1])],
            'end':   [float(e[0]), float(e[1])],
            'length': float(blen),
            'angle_deg': 90.0  # デフォルト。ユーザーが後で設定
        })

    # SVG パス用の外形点列
    outer_pts = [[float(p[0]), float(p[1])] for p in outer_chain]

    return {
        'type': 'dxf',
        'dimensions': {
            'width':  round(width,  3),
            'height': round(height, 3),
            'bbox':   bbox,
        },
        'outer_profile': outer_pts,
        'holes': holes,
        'bends': bends,
        'stats': {
            'segments': len(contour_segments),
            'holes':    len(holes),
            'bends':    len(bends),
        },
        'layers': list({e.dxf.get('layer', '0')
                        for e in msp
                        if not _is_skip_layer(e.dxf.get('layer', '0'))}),
    }


def _parse_step_text(file_path: str) -> dict:
    """
    STEP テキストパーサー（FreeCAD 不要のフォールバック）
    ISO 10303-21 テキストから座標・円柱面を抽出。
    """
    import re

    with open(file_path, 'r', errors='replace') as f:
        content = f.read()

    # CARTESIAN_POINT から全座標を収集
    pts = re.findall(
        r'CARTESIAN_POINT\s*\([^,]+,\s*\(([^)]+)\)\)', content)
    coords = []
    for p in pts:
        try:
            vals = [float(x.strip()) for x in p.split(',') if x.strip()]
            if len(vals) >= 2:
                coords.append(vals)
        except ValueError:
            pass

    if not coords:
        raise ValueError("STEP ファイルから座標を抽出できません")

    xs = [c[0] for c in coords]
    ys = [c[1] for c in coords]
    zs = [c[2] for c in coords if len(c) > 2]

    bbox = {
        'min_x': float(min(xs)), 'max_x': float(max(xs)),
        'min_y': float(min(ys)), 'max_y': float(max(ys)),
    }
    width  = bbox['max_x'] - bbox['min_x']
    height = bbox['max_y'] - bbox['min_y']
    depth  = float(max(zs) - min(zs)) if zs else 0.0

    # CYLINDRICAL_SURFACE → 穴
    cyl_radii = re.findall(
        r'CYLINDRICAL_SURFACE\s*\([^,]+,[^,]+,\s*([\d.eE+\-]+)\)', content)
    holes = []
    seen_r = set()
    cx_mid = (bbox['min_x'] + bbox['max_x']) / 2
    cy_mid = (bbox['min_y'] + bbox['max_y']) / 2
    for r_str in cyl_radii:
        try:
            r = round(float(r_str), 4)
            if r > 0 and r < min(width, height) * 0.4 and r not in seen_r:
                seen_r.add(r)
                # 穴の中心は AXIS2_PLACEMENT_3D の直前 CARTESIAN_POINT を参照
                # 簡易: 全点から該当半径に近い座標を推定（正確にはエンティティ参照追跡が必要）
                holes.append({'cx': cx_mid, 'cy': cy_mid, 'r': r})
        except ValueError:
            pass

    # AXIS2_PLACEMENT_3D と CARTESIAN_POINT の対応から穴中心を特定（ベストエフォート）
    # #nn=CYLINDRICAL_SURFACE('...',#ref,r) → #ref=AXIS2_PLACEMENT_3D('',#pt,...) → #pt=CARTESIAN_POINT
    entity_map = {}
    for line in content.splitlines():
        m = re.match(r'#(\d+)\s*=\s*(.+)', line.strip())
        if m:
            entity_map[int(m.group(1))] = m.group(2)

    holes_refined = []
    for line in content.splitlines():
        m = re.match(
            r'#(\d+)\s*=\s*CYLINDRICAL_SURFACE\s*\([^,]+,#(\d+),\s*([\d.eE+\-]+)\)',
            line.strip())
        if not m:
            continue
        r = float(m.group(3))
        if r <= 0 or r >= min(width, height) * 0.4:
            continue
        axis_id = int(m.group(2))
        axis_def = entity_map.get(axis_id, '')
        pt_m = re.search(r'#(\d+)', axis_def)
        if pt_m:
            pt_id  = int(pt_m.group(1))
            pt_def = entity_map.get(pt_id, '')
            coord_m = re.search(r'\(([^)]+)\)', pt_def)
            if coord_m:
                try:
                    vals = [float(x.strip()) for x in coord_m.group(1).split(',')]
                    holes_refined.append({'cx': vals[0], 'cy': vals[1], 'r': r})
                    continue
                except Exception:
                    pass
        holes_refined.append({'cx': cx_mid, 'cy': cy_mid, 'r': r})

    final_holes = holes_refined if holes_refined else holes

    outer_pts = [
        [bbox['min_x'], bbox['min_y']],
        [bbox['max_x'], bbox['min_y']],
        [bbox['max_x'], bbox['max_y']],
        [bbox['min_x'], bbox['max_y']],
        [bbox['min_x'], bbox['min_y']],
    ]

    return {
        'type':  'step',
        'parse_method': 'text_parser',
        'dimensions': {
            'width':  round(width,  3),
            'height': round(height, 3),
            'depth':  round(depth,  3),
            'bbox':   bbox,
        },
        'outer_profile': outer_pts,
        'holes': final_holes,
        'bends': [],
        'stats': {
            'points': len(coords),
            'holes':  len(final_holes),
            'bends':  0,
        },
        'layers': ['0'],
        'warning': 'STEP テキストパーサーを使用（精度限定）。'
                   'Antigravity コンテナを起動すると FreeCAD による高精度解析が使えます。',
    }


def process_step(file_path: str) -> dict:
    """
    STEP ファイルを解析。
    1. Antigravity コンテナの FreeCAD を優先使用（高精度）
    2. FreeCAD 不可時は STEP テキストパーサーにフォールバック
    """
    ANTIGRAVITY = "clawstack-unified-antigravity-1"

    # Antigravity 稼働確認
    check = subprocess.run(
        ['docker', 'inspect', '--format', '{{.State.Running}}', ANTIGRAVITY],
        capture_output=True, text=True)
    freecad_available = check.returncode == 0 and check.stdout.strip() == 'true'

    if freecad_available:
        step_filename = Path(file_path).name
        step_container_path = f"/tmp/pdie_{step_filename}"
        subprocess.run(['docker', 'cp', file_path, f'{ANTIGRAVITY}:{step_container_path}'])

        script = f"""
import FreeCAD, Part, json, sys
shape = Part.read('{step_container_path}')
bb    = shape.BoundBox
holes = []
for f in shape.Faces:
    if hasattr(f.Surface, 'Radius'):
        c = f.Surface.Center
        holes.append({{'cx': c.x, 'cy': c.y, 'r': f.Surface.Radius}})
outer = [[bb.XMin,bb.YMin],[bb.XMax,bb.YMin],[bb.XMax,bb.YMax],[bb.XMin,bb.YMax],[bb.XMin,bb.YMin]]
result = {{'type':'step','parse_method':'freecad',
  'dimensions':{{'width':round(bb.XLength,3),'height':round(bb.YLength,3),
    'depth':round(bb.ZLength,3),'bbox':{{'min_x':bb.XMin,'max_x':bb.XMax,'min_y':bb.YMin,'max_y':bb.YMax}}}},
  'outer_profile':outer,'holes':holes,'bends':[],
  'stats':{{'faces':len(shape.Faces),'edges':len(shape.Edges),'holes':len(holes),'bends':0}},
  'layers':['0']}}
print(json.dumps(result))
"""
        with tempfile.NamedTemporaryFile(suffix='.py', mode='w',
                                         dir='/tmp', delete=False) as f:
            f.write(script)
            script_path = f.name
            
        script_filename = Path(script_path).name
        script_container_path = f"/tmp/{script_filename}"
        subprocess.run(['docker', 'cp', script_path, f'{ANTIGRAVITY}:{script_container_path}'])

        try:
            result = subprocess.run(
                ['docker', 'exec', ANTIGRAVITY, 'freecadcmd', script_container_path],
                capture_output=True, text=True, timeout=60)
            for line in result.stdout.splitlines():
                if line.startswith('{'):
                    return json.loads(line)
        except Exception:
            pass
        finally:
            Path(script_path).unlink(missing_ok=True)
            subprocess.run(['docker', 'exec', ANTIGRAVITY, 'rm', '-f', step_container_path, script_container_path])

    # FreeCAD 不可 → テキストパーサー
    return _parse_step_text(file_path)


def analyze_file(file_path: str, file_ext: str) -> dict:
    """ファイル拡張子に応じて適切な解析を実行"""
    ext = file_ext.lower().lstrip('.')
    if ext == 'dxf':
        return process_dxf(file_path)
    elif ext in ('stp', 'step'):
        return process_step(file_path)
    else:
        raise ValueError(f"未対応ファイル形式: {ext}")
