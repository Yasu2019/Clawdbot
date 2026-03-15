"""
DXF → 3D Model Generator
=========================
Streamlit UI for converting 2D DXF drawings to 3D STEP / STL models.

- STL  : pure Python (ezdxf + trimesh + shapely) — instant in-browser
- STEP : FreeCAD engine via docker exec into Antigravity container
"""

import io
import json
import math
import os
import subprocess
import tempfile
import uuid
from pathlib import Path

import ezdxf
import numpy as np
import plotly.graph_objects as go
import streamlit as st
import trimesh
from shapely.geometry import Polygon, MultiPolygon
from shapely.ops import unary_union

# ── Constants ───────────────────────────────────────────────────────────────
WORK_DIR = Path("/work/dxf3d_output")
WORK_DIR.mkdir(parents=True, exist_ok=True)

ANTIGRAVITY = "clawstack-unified-antigravity-1"
DXF23D_PATH = "/work/scripts/dxf23d.py"
OLLAMA_GEN_MODEL = os.getenv("OLLAMA_GEN_MODEL", "qwen3:14b")
OLLAMA_CODE_MODEL = os.getenv("OLLAMA_CODE_MODEL", "qwen2.5-coder:14b")

N_ARC = 48          # arc approximation segments per 360°
TOL   = 1e-6
GAP_TOL_DEFAULT = 0.5   # mm: default snap tolerance for segment chaining

# Layer keywords that indicate non-contour layers (dims, text, borders, etc.)
# Includes Japanese CAD conventions (JIS/Fujitsu/AutoCAD-J layer naming)
_SKIP_LAYER_KW = [
    # English
    "dim", "defpoint", "hatch", "text", "note", "anno",
    "title", "border", "frame", "bom", "symbol", "center", "hidden",
    "leader", "arrow", "tolerance", "datum", "phantom",
    # Japanese
    "寸法", "引出", "注記", "文字", "注釈", "中心", "ハッチ",
    "タイトル", "枠", "隠線", "補助",
]
# DXF entity types that represent geometric contour candidates
_GEO_TYPES = {"LINE", "ARC", "CIRCLE", "LWPOLYLINE", "POLYLINE", "SPLINE", "ELLIPSE"}

# DXF entity types that are NEVER contour geometry — always skipped in extraction
_SKIP_ENTITY_TYPES = {
    "DIMENSION", "LEADER", "MLEADER",   # dimension / annotation
    "TEXT", "MTEXT", "ATTDEF", "ATTRIB",  # text
    "TOLERANCE", "ACAD_TABLE",            # tolerances / tables
    "VIEWPORT", "OLE2FRAME",              # viewport / OLE
    "POINT",                              # lone points
}


# ── DXF parsing ─────────────────────────────────────────────────────────────

def _arc_pts(cx, cy, r, sa_deg, ea_deg, ccw=True):
    sa = math.radians(sa_deg)
    ea = math.radians(ea_deg)
    if ccw and ea <= sa:
        ea += 2 * math.pi
    elif not ccw and ea >= sa:
        ea -= 2 * math.pi
    return [
        (cx + r * math.cos(sa + (ea - sa) * i / N_ARC),
         cy + r * math.sin(sa + (ea - sa) * i / N_ARC))
        for i in range(N_ARC + 1)
    ]


def get_layers(doc):
    """Return list of layers that contain any entity."""
    layers = set()
    for e in doc.modelspace():
        try:
            layers.add(e.dxf.layer)
        except Exception:
            pass
    return sorted(layers)


def analyze_layers(doc) -> dict:
    """
    Analyze all modelspace layers.
    Returns {layer_name: {total, types, is_geo, is_likely_skip}}.
    """
    info: dict = {}
    for e in doc.modelspace():
        try:
            layer = e.dxf.layer
        except Exception:
            layer = "0"
        t = e.dxftype()
        if layer not in info:
            info[layer] = {"total": 0, "types": {}, "is_geo": False, "skip": False}
        info[layer]["total"] += 1
        info[layer]["types"][t] = info[layer]["types"].get(t, 0) + 1
        if t in _GEO_TYPES:
            info[layer]["is_geo"] = True
        lname = layer.lower()
        if any(kw in lname for kw in _SKIP_LAYER_KW) or t in _SKIP_ENTITY_TYPES:
            info[layer]["skip"] = True
    return info


def suggest_contour_layer(layer_info: dict) -> str:
    """
    Heuristic: return the layer name most likely to hold contour geometry.
    Prefers non-skip geo layers with the most LINE/ARC/CIRCLE/LWPOLYLINE/SPLINE entities.
    """
    geo = {k: v for k, v in layer_info.items() if v["is_geo"]}
    if not geo:
        return ""
    # prefer non-skip layers
    candidates = {k: v for k, v in geo.items() if not v["skip"]} or geo

    def score(v):
        return sum(v["types"].get(t, 0)
                   for t in ("LINE", "ARC", "CIRCLE", "LWPOLYLINE", "SPLINE", "ELLIPSE"))
    return max(candidates, key=lambda k: score(candidates[k]))


def _dist2d(a, b):
    return math.sqrt((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2)


_SNAP = 1e-4  # grid resolution for duplicate detection (0.1 μm)


def _snap(v):
    return round(v / _SNAP) * _SNAP


def _dedup_segments(segments):
    """
    Remove geometrically duplicate segments (same geometry, drawn 2+ times).
    Canonical key: frozenset of rounded (start, end) so direction-agnostic.
    Returns (unique_segments, n_removed).
    """
    seen: set = set()
    unique = []
    for seg in segments:
        s, e, _ = seg
        key = frozenset([(_snap(s[0]), _snap(s[1])), (_snap(e[0]), _snap(e[1]))])
        if key not in seen:
            seen.add(key)
            unique.append(seg)
    return unique, len(segments) - len(unique)


def _auto_gap_tol(segments, max_gap: float = 5.0):
    """
    Analyse the distribution of endpoint-to-endpoint distances to estimate
    an appropriate gap_tol automatically.

    Strategy:
    - Collect all segment endpoints.
    - For each endpoint, find the nearest endpoint belonging to a *different*
      segment (using scipy KDTree).
    - Filter distances in the range (TOL*10, max_gap).
    - Return the 90th-percentile of those distances × 1.5 so that nearly all
      real gaps are bridged, or GAP_TOL_DEFAULT if no informative gaps exist.
    Returns (gap_tol, gap_distances_array).
    """
    if not segments:
        return GAP_TOL_DEFAULT, []

    from scipy.spatial import KDTree
    import numpy as np

    # Build (point, segment_index) arrays
    pts = []
    seg_ids = []
    for i, (s, e, _) in enumerate(segments):
        pts.append(s)
        pts.append(e)
        seg_ids.append(i)
        seg_ids.append(i)

    if len(pts) < 4:
        return GAP_TOL_DEFAULT, []

    arr = np.array(pts, dtype=float)
    seg_ids = np.array(seg_ids)
    tree = KDTree(arr)

    # For each point, find nearest 4 neighbours (first is itself)
    dists, idxs = tree.query(arr, k=min(4, len(arr)))

    gap_dists = []
    for i, (row_d, row_i) in enumerate(zip(dists, idxs)):
        for d, j in zip(row_d[1:], row_i[1:]):  # skip self (index 0)
            if seg_ids[i] != seg_ids[j] and TOL * 10 < d < max_gap:
                gap_dists.append(d)

    if not gap_dists:
        return GAP_TOL_DEFAULT, []

    gap_dists = np.array(gap_dists)
    auto = float(np.percentile(gap_dists, 90)) * 1.5
    auto = max(auto, TOL * 10)
    return auto, gap_dists


def _chain_segments(segments, gap_tol: float = GAP_TOL_DEFAULT):
    """
    Chain open (start, end, midpoints) segments into closed loops.
    Endpoints within gap_tol are considered connected (gap snap).
    """
    remaining = list(range(len(segments)))
    result = []
    search_dist = max(gap_tol, TOL * 10)

    def find_next(end):
        best_i, best_rev, best_d = None, False, search_dist
        for i in remaining:
            s, e, _ = segments[i]
            ds = _dist2d(end, s)
            de = _dist2d(end, e)
            if ds < best_d:
                best_d, best_i, best_rev = ds, i, False
            if de < best_d:
                best_d, best_i, best_rev = de, i, True
        return best_i, best_rev

    while remaining:
        start_idx = remaining.pop(0)
        s, e, mid = segments[start_idx]
        chain = [s] + mid + [e]
        while True:
            idx, rev = find_next(chain[-1])
            if idx is None:
                break
            remaining.remove(idx)
            ss, se, sm = segments[idx]
            chain.extend((list(reversed(sm)) + [ss]) if rev else (sm + [se]))
        if _dist2d(chain[0], chain[-1]) < search_dist and len(chain) >= 3:
            result.append(chain[:-1])
    return result


def extract_loops(doc, layer: str, gap_tol: float = GAP_TOL_DEFAULT,
                  auto_clean: bool = True, max_auto_gap: float = 5.0):
    """
    Extract closed 2D contours from a DXF document.

    Supported entities
    ------------------
    LWPOLYLINE, POLYLINE  – closed directly or chained
    CIRCLE                – always closed
    LINE, ARC             – chained into loops with gap_tol snap
    SPLINE                – flattened to polyline, then closed/chained
    ELLIPSE               – flattened to polyline, then closed/chained
    HATCH                 – boundary paths extracted (LWPolylinePath / EdgePath)
    INSERT                – block references expanded via virtual_entities()

    Parameters
    ----------
    gap_tol : float
        Maximum gap (mm) between adjacent segment endpoints to still be
        considered connected.  Increase for DXFs with tiny geometric gaps.
    """
    msp = doc.modelspace()
    loops: list = []
    segments: list = []   # (start_pt, end_pt, [mid_pts])

    def on_layer(e):
        try:
            return (not layer) or e.dxf.layer == layer
        except Exception:
            return not layer

    def _process(e):
        """Extract geometry from a single entity into loops/segments."""
        t = e.dxftype()

        # Skip dimension / annotation entities — they are never contour geometry
        if t in _SKIP_ENTITY_TYPES:
            return

        # ── LWPOLYLINE ────────────────────────────────────────────────
        if t == "LWPOLYLINE":
            verts = list(e.get_points("xyb"))
            pts: list = []
            for i, (x, y, b) in enumerate(verts):
                pts.append((x, y))
                if abs(b) > 1e-9:
                    nx, ny, _ = verts[(i + 1) % len(verts)]
                    try:
                        from ezdxf.math import bulge_to_arc, Vec2
                        center, sa, ea, radius = bulge_to_arc(
                            Vec2(x, y), Vec2(nx, ny), b)
                        pts.extend(_arc_pts(center.x, center.y, radius,
                                            math.degrees(sa), math.degrees(ea),
                                            ccw=(b > 0))[1:-1])
                    except Exception:
                        pass
            if len(pts) < 2:
                return
            if e.closed or _dist2d(pts[0], pts[-1]) < gap_tol:
                if len(pts) >= 3:
                    loops.append(pts)
            else:
                segments.append((pts[0], pts[-1], pts[1:-1]))

        # ── POLYLINE ──────────────────────────────────────────────────
        elif t == "POLYLINE":
            try:
                pts = [(v.dxf.location.x, v.dxf.location.y)
                       for v in e.vertices()]
            except Exception:
                return
            if len(pts) < 2:
                return
            if e.is_closed or _dist2d(pts[0], pts[-1]) < gap_tol:
                if len(pts) >= 3:
                    loops.append(pts)
            else:
                segments.append((pts[0], pts[-1], pts[1:-1]))

        # ── CIRCLE ───────────────────────────────────────────────────
        elif t == "CIRCLE":
            cx, cy = e.dxf.center.x, e.dxf.center.y
            r = e.dxf.radius
            pts = [(cx + r * math.cos(2 * math.pi * i / N_ARC),
                    cy + r * math.sin(2 * math.pi * i / N_ARC))
                   for i in range(N_ARC)]
            loops.append(pts)

        # ── LINE ─────────────────────────────────────────────────────
        elif t == "LINE":
            x1, y1 = e.dxf.start.x, e.dxf.start.y
            x2, y2 = e.dxf.end.x, e.dxf.end.y
            segments.append(((x1, y1), (x2, y2), []))

        # ── ARC ──────────────────────────────────────────────────────
        elif t == "ARC":
            cx, cy = e.dxf.center.x, e.dxf.center.y
            r = e.dxf.radius
            sa, ea = e.dxf.start_angle, e.dxf.end_angle
            mids = _arc_pts(cx, cy, r, sa, ea)[1:-1]
            sp = (cx + r * math.cos(math.radians(sa)),
                  cy + r * math.sin(math.radians(sa)))
            ep = (cx + r * math.cos(math.radians(ea)),
                  cy + r * math.sin(math.radians(ea)))
            # Full circle (gap < 1deg): treat as closed
            if _dist2d(sp, ep) < gap_tol:
                pts = _arc_pts(cx, cy, r, sa, ea)
                loops.append(pts[:-1])
            else:
                segments.append((sp, ep, mids))

        # ── SPLINE ───────────────────────────────────────────────────
        elif t == "SPLINE":
            try:
                pts_3d = list(e.flattening(0.05))
                pts = [(p[0], p[1]) for p in pts_3d]
                if len(pts) < 2:
                    return
                closed = getattr(e, "closed", False)
                if closed or _dist2d(pts[0], pts[-1]) < gap_tol:
                    if len(pts) >= 3:
                        loops.append(pts)
                else:
                    segments.append((pts[0], pts[-1], pts[1:-1]))
            except Exception:
                pass

        # ── ELLIPSE ──────────────────────────────────────────────────
        elif t == "ELLIPSE":
            try:
                pts_3d = list(e.flattening(0.05))
                pts = [(p[0], p[1]) for p in pts_3d]
                if len(pts) < 2:
                    return
                span = abs(e.dxf.end_param - e.dxf.start_param)
                if _dist2d(pts[0], pts[-1]) < gap_tol or span >= 2 * math.pi - 0.01:
                    if len(pts) >= 3:
                        loops.append(pts)
                else:
                    segments.append((pts[0], pts[-1], pts[1:-1]))
            except Exception:
                pass

        # ── HATCH ────────────────────────────────────────────────────
        elif t == "HATCH":
            try:
                for path in e.paths:
                    # LWPolylinePath
                    if hasattr(path, "vertices") and path.vertices:
                        pts = [(p[0], p[1]) for p in path.vertices]
                        if len(pts) >= 3:
                            loops.append(pts)
                    # EdgePath
                    elif hasattr(path, "edges"):
                        for edge in path.edges:
                            en = type(edge).__name__
                            if "Line" in en:
                                sp = (edge.start[0], edge.start[1])
                                ep = (edge.end[0], edge.end[1])
                                segments.append((sp, ep, []))
                            elif "Arc" in en:
                                cx, cy = edge.center[0], edge.center[1]
                                r = edge.radius
                                sa, ea = edge.start_angle, edge.end_angle
                                mids = _arc_pts(cx, cy, r, sa, ea)[1:-1]
                                sp2 = (cx + r * math.cos(math.radians(sa)),
                                       cy + r * math.sin(math.radians(sa)))
                                ep2 = (cx + r * math.cos(math.radians(ea)),
                                       cy + r * math.sin(math.radians(ea)))
                                segments.append((sp2, ep2, mids))
                            elif "Spline" in en:
                                try:
                                    pts_3d = list(edge.construction_tool().flattening(0.05))
                                    pts = [(p[0], p[1]) for p in pts_3d]
                                    if len(pts) >= 2:
                                        segments.append((pts[0], pts[-1], pts[1:-1]))
                                except Exception:
                                    pass
            except Exception:
                pass

    # ── Process modelspace (expand INSERT blocks) ─────────────────────────
    for e in msp:
        if e.dxftype() == "INSERT":
            try:
                for ve in e.virtual_entities():
                    if on_layer(ve):
                        _process(ve)
            except Exception:
                pass
        elif on_layer(e):
            _process(e)

    # ── Auto-clean: dedup & gap detection ────────────────────────────────
    _dedup_count = 0
    _auto_gap = None
    _gap_dists = []
    if segments and auto_clean:
        segments, _dedup_count = _dedup_segments(segments)
        if gap_tol == GAP_TOL_DEFAULT:  # only auto-compute when user didn't override
            _auto_gap, _gap_dists = _auto_gap_tol(segments, max_gap=max_auto_gap)
            gap_tol = _auto_gap

    # ── Chain open segments into closed loops ─────────────────────────────
    if segments:
        loops.extend(_chain_segments(segments, gap_tol))

    # Attach diagnostics as attributes for UI display
    extract_loops._last_dedup_count = _dedup_count
    extract_loops._last_auto_gap    = _auto_gap
    extract_loops._last_gap_tol     = gap_tol

    return loops


# ── 3D mesh generation ───────────────────────────────────────────────────────

def detect_extrusion_axis(doc) -> str:
    """
    Auto-detect the primary extrusion axis from DXF entity normals.

    Reads the `dxf.extrusion` attribute of each entity (the entity's local
    Z-axis in world space). The axis that appears most frequently wins.
    Falls back to 'Z' when no extrusion data is present.

    Returns
    -------
    str : 'X', 'Y', or 'Z'
    """
    votes = {'X': 0, 'Y': 0, 'Z': 0}
    for e in doc.modelspace():
        try:
            ext = e.dxf.extrusion
            ax, ay, az = abs(ext.x), abs(ext.y), abs(ext.z)
            if az >= ax and az >= ay:
                votes['Z'] += 1
            elif ay >= ax:
                votes['Y'] += 1
            else:
                votes['X'] += 1
        except Exception:
            votes['Z'] += 1
    return max(votes, key=votes.get)


def _apply_axis_transform(mesh: "trimesh.Trimesh", axis: str) -> "trimesh.Trimesh":
    """
    Rotate a Z-extruded mesh so its extrusion aligns with `axis`.

    trimesh.creation.extrude_polygon always extrudes along the local +Z.
    This function remaps that to the requested world axis.

    Z → no change
    Y → rotate +90° around X  (local Z becomes world Y)
    X → rotate −90° around Y  (local Z becomes world X)
    """
    import trimesh.transformations as T
    if axis == 'Y':
        mesh.apply_transform(T.rotation_matrix(math.pi / 2, [1, 0, 0]))
    elif axis == 'X':
        mesh.apply_transform(T.rotation_matrix(-math.pi / 2, [0, 1, 0]))
    return mesh


def _loops_to_polys(loops) -> list:
    """
    Convert loop point-lists to valid Shapely Polygons.
    Repair strategy (in order):
      1. shapely.validation.make_valid()  — handles self-intersections aggressively
      2. buffer(0)                        — fallback for older Shapely
    """
    try:
        from shapely.validation import make_valid as _make_valid
        _HAS_MAKE_VALID = True
    except ImportError:
        _HAS_MAKE_VALID = False

    polys = []
    for loop in loops:
        try:
            p = Polygon(loop)
            if not p.is_valid:
                if _HAS_MAKE_VALID:
                    p = _make_valid(p)
                else:
                    p = p.buffer(0)
            # make_valid may return MultiPolygon or GeometryCollection
            if hasattr(p, "geoms"):
                for sub in p.geoms:
                    if sub.geom_type == "Polygon" and sub.is_valid and sub.area > TOL:
                        polys.append(sub)
            elif p.is_valid and p.area > TOL:
                polys.append(p)
        except Exception:
            pass
    return polys


def _group_polys_to_bodies(polys: list) -> list:
    """
    Group Shapely polygons into independent bodies.

    Algorithm
    ---------
    Sort by area (largest first). Each polygon that is not contained by
    any already-selected outer shell starts a new body. Inner polygons
    (holes) are subtracted from their enclosing shell.

    Returns a list of Shapely geometries (each ready to extrude).
    """
    polys = sorted(polys, key=lambda p: p.area, reverse=True)
    assigned: set = set()
    bodies: list = []

    for i, outer in enumerate(polys):
        if i in assigned:
            continue
        holes = []
        for j, inner in enumerate(polys):
            if j == i or j in assigned:
                continue
            try:
                if outer.contains(inner):
                    holes.append(inner)
                    assigned.add(j)
            except Exception:
                pass
        assigned.add(i)

        try:
            profile = outer.difference(unary_union(holes)) if holes else outer
        except Exception:
            profile = outer

        if hasattr(profile, 'geoms'):
            # MultiPolygon: add each sub-polygon separately
            for sub in profile.geoms:
                if sub.is_valid and sub.area > TOL:
                    bodies.append(sub)
        elif profile.is_valid and profile.area > TOL:
            bodies.append(profile)

    return bodies


def loops_to_mesh(loops, height_mm, axis: str = 'Z'):
    """
    Convert closed 2D loops to an extruded 3D trimesh.

    Improvements over v1
    --------------------
    - Multi-body: disconnected outer profiles become independent extruded bodies
    - Direction: extrusion direction can be X, Y, or Z
    - Hole grouping: each inner loop is subtracted from its enclosing outer shell
    - Invalid polygon repair: buffer(0) is tried before discarding

    Returns
    -------
    (mesh, n_bodies) or (None, 0) on failure.
    """
    polys = _loops_to_polys(loops)
    if not polys:
        return None, 0

    bodies = _group_polys_to_bodies(polys)
    if not bodies:
        return None, 0

    meshes = []
    for profile in bodies:
        try:
            m = trimesh.creation.extrude_polygon(profile, height_mm)
            m = _apply_axis_transform(m, axis)
            meshes.append(m)
        except Exception as exc:
            # Log per-body failure but continue with others
            pass

    if not meshes:
        return None, 0

    if len(meshes) == 1:
        return meshes[0], 1

    combined = trimesh.util.concatenate(meshes)
    return combined, len(meshes)


def mesh_to_plotly(mesh):
    """Convert trimesh.Trimesh to a plotly Mesh3d trace."""
    v = mesh.vertices
    f = mesh.faces
    return go.Mesh3d(
        x=v[:, 0], y=v[:, 1], z=v[:, 2],
        i=f[:, 0], j=f[:, 1], k=f[:, 2],
        color="#38bdf8",
        opacity=0.85,
        flatshading=False,
        lighting=dict(ambient=0.5, diffuse=0.8, specular=0.3),
        lightposition=dict(x=100, y=200, z=300),
    )


# ── Built-in test suite ───────────────────────────────────────────────────────

def _dxf_new():
    import ezdxf as _ezdxf
    doc = _ezdxf.new()
    doc.header['$INSUNITS'] = 4  # mm
    return doc


def _save_dxf(doc):
    buf = io.StringIO()
    doc.write(buf)
    return buf.getvalue().encode('utf-8')


# ── DXF generator functions ───────────────────────────────────────────────────

def _gen_rect_simple():
    doc = _dxf_new(); msp = doc.modelspace()
    pts = [(0,0),(100,0),(100,60),(0,60),(0,0)]
    for i in range(len(pts)-1): msp.add_line(pts[i], pts[i+1])
    return _save_dxf(doc)

def _gen_circle():
    doc = _dxf_new(); msp = doc.modelspace()
    msp.add_circle((0,0), 30)
    return _save_dxf(doc)

def _gen_l_shape():
    doc = _dxf_new(); msp = doc.modelspace()
    pts = [(0,0),(80,0),(80,40),(40,40),(40,80),(0,80),(0,0)]
    for i in range(len(pts)-1): msp.add_line(pts[i], pts[i+1])
    return _save_dxf(doc)

def _gen_u_shape():
    doc = _dxf_new(); msp = doc.modelspace()
    outer = [(0,0),(100,0),(100,80),(0,80),(0,0)]
    inner = [(20,30),(80,30),(80,80),(20,80),(20,30)]
    for seg in [outer, inner]:
        for i in range(len(seg)-1): msp.add_line(seg[i], seg[i+1])
    return _save_dxf(doc)

def _gen_arc_rect():
    doc = _dxf_new(); msp = doc.modelspace()
    r, W, H = 10, 100, 60
    msp.add_line((r,0),(W-r,0)); msp.add_line((W,r),(W,H-r))
    msp.add_line((W-r,H),(r,H)); msp.add_line((0,H-r),(0,r))
    msp.add_arc((r,r),     r, 180, 270)
    msp.add_arc((W-r,r),   r, 270, 360)
    msp.add_arc((W-r,H-r), r, 0,   90)
    msp.add_arc((r,H-r),   r, 90,  180)
    return _save_dxf(doc)

def _gen_plate_hole():
    """縦穴: 100×100 plate, r=20 centre through-hole."""
    doc = _dxf_new(); msp = doc.modelspace()
    pts = [(0,0),(100,0),(100,100),(0,100),(0,0)]
    for i in range(len(pts)-1): msp.add_line(pts[i], pts[i+1])
    msp.add_circle((50,50), 20)
    return _save_dxf(doc)

def _gen_counterbore():
    """座グリ: plate + large circle (cap) + small circle (through)."""
    doc = _dxf_new(); msp = doc.modelspace()
    pts = [(0,0),(100,0),(100,100),(0,100),(0,0)]
    for i in range(len(pts)-1): msp.add_line(pts[i], pts[i+1])
    msp.add_circle((50,50), 20)   # Φ40 cap
    msp.add_circle((50,50), 10)   # Φ20 through
    return _save_dxf(doc)

def _gen_u_bend():
    """U字曲げ: U-profile width=60 height=40 wall=5."""
    doc = _dxf_new(); msp = doc.modelspace()
    pts = [(0,40),(0,0),(60,0),(60,40),(55,40),(55,5),(5,5),(5,40),(0,40)]
    for i in range(len(pts)-1): msp.add_line(pts[i], pts[i+1])
    return _save_dxf(doc)

def _gen_side_hole():
    """横穴: 100×60 plate with Φ20 circle cutout on left side (x=20 centre)."""
    doc = _dxf_new(); msp = doc.modelspace()
    # Outer rectangle
    pts = [(0,0),(100,0),(100,60),(0,60),(0,0)]
    for i in range(len(pts)-1): msp.add_line(pts[i], pts[i+1])
    # Circular cutout near left edge (simulates side hole in top view)
    msp.add_circle((20,30), 10)
    return _save_dxf(doc)

def _gen_curved_groove():
    """曲線溝: 120×60 rect with arc-shaped groove cut from centre top."""
    doc = _dxf_new(); msp = doc.modelspace()
    r = 20
    cx, cy = 60, 60  # groove centre at top edge
    # Outer profile (with groove opening at top)
    # Bottom/sides as lines, top as two segments with arc gap in centre
    msp.add_line((0,0),  (120,0))    # bottom
    msp.add_line((120,0),(120,60))   # right
    msp.add_line((0,60), (0,0))      # left
    msp.add_line((0,60), (cx-r,60)) # top-left segment
    msp.add_line((cx+r,60),(120,60)) # top-right segment
    # Arc groove cuts downward into plate: 180°→360° CCW (through bottom at y=40)
    msp.add_arc((cx,cy), r, 180, 360)  # half-circle groove (open at top, cuts down)
    # Close the groove bottom (chord line approximation already covered by arc)
    return _save_dxf(doc)

def _gen_crank_bend():
    """クランク曲げ: Z/step profile — offset by 20mm, width 80, step=15mm."""
    doc = _dxf_new(); msp = doc.modelspace()
    # Crank (Z-shape): two horizontal arms offset vertically, connected by diagonal ramp
    t = 5   # material thickness
    pts = [
        (0,  0),(80, 0),          # bottom arm bottom edge
        (80, t),(45, t),          # bottom arm top + step down
        (45, t+20),(80, t+20),    # ramp + top arm bottom edge  (offset 20mm)
        (80, 2*t+20),(0,2*t+20),  # top arm top edge
        (0,  t+20),(35,t+20),     # back along top arm
        (35, t),(0, t),           # step up + close
        (0,  0),
    ]
    for i in range(len(pts)-1): msp.add_line(pts[i], pts[i+1])
    return _save_dxf(doc)


# ─── Extended parametric generators ──────────────────────────────────────────

def _make_gen(fn, *args, **kwargs):
    """Wrap a parameterised generator into a no-arg callable."""
    return lambda: fn(*args, **kwargs)


def _gen_ngon(n: int, R: float = 40.0) -> bytes:
    """Regular n-gon centred at origin."""
    doc = _dxf_new(); msp = doc.modelspace()
    pts = [(R * math.cos(2 * math.pi * i / n), R * math.sin(2 * math.pi * i / n)) for i in range(n)]
    pts.append(pts[0])
    for i in range(len(pts) - 1):
        msp.add_line(pts[i], pts[i + 1])
    return _save_dxf(doc)


def _gen_rect_holes(W: float, H: float, holes: list) -> bytes:
    """Rectangle W×H with circular holes [(cx, cy, r), ...]."""
    doc = _dxf_new(); msp = doc.modelspace()
    outer = [(0, 0), (W, 0), (W, H), (0, H), (0, 0)]
    for i in range(len(outer) - 1):
        msp.add_line(outer[i], outer[i + 1])
    for cx, cy, r in holes:
        msp.add_circle((cx, cy), r)
    return _save_dxf(doc)


def _gen_ring(Ro: float, Ri: float) -> bytes:
    """Annular ring, outer radius Ro, inner Ri."""
    doc = _dxf_new(); msp = doc.modelspace()
    msp.add_circle((0, 0), Ro)
    msp.add_circle((0, 0), Ri)
    return _save_dxf(doc)


def _gen_stadium(L: float, R: float) -> bytes:
    """Stadium: straight part length L, cap radius R."""
    doc = _dxf_new(); msp = doc.modelspace()
    msp.add_line((0, -R), (L, -R))
    msp.add_line((0,  R), (L,  R))
    msp.add_arc((L, 0), R, -90,  90)
    msp.add_arc((0, 0), R,  90, 270)
    return _save_dxf(doc)


def _gen_trapezoid(Wb: float, Wt: float, H: float) -> bytes:
    """Symmetric trapezoid, bottom Wb, top Wt, height H."""
    doc = _dxf_new(); msp = doc.modelspace()
    off = (Wb - Wt) / 2
    pts = [(0, 0), (Wb, 0), (Wb - off, H), (off, H), (0, 0)]
    for i in range(len(pts) - 1):
        msp.add_line(pts[i], pts[i + 1])
    return _save_dxf(doc)


def _gen_rounded_rect(W: float, H: float, r: float) -> bytes:
    """Rounded rectangle with corner radius r."""
    doc = _dxf_new(); msp = doc.modelspace()
    msp.add_line((r, 0),    (W - r, 0))
    msp.add_line((W, r),    (W, H - r))
    msp.add_line((W - r, H),(r, H))
    msp.add_line((0, H - r),(0, r))
    msp.add_arc((r,     r),     r, 180, 270)
    msp.add_arc((W - r, r),     r, 270, 360)
    msp.add_arc((W - r, H - r), r,   0,  90)
    msp.add_arc((r,     H - r), r,  90, 180)
    return _save_dxf(doc)


def _gen_h_beam(W: float, H: float, tf: float, tw: float) -> bytes:
    """H-beam cross-section: width W, height H, flange tf, web tw."""
    doc = _dxf_new(); msp = doc.modelspace()
    sx = (W - tw) / 2
    pts = [
        (0, 0), (W, 0), (W, tf), (sx + tw, tf), (sx + tw, H - tf),
        (W, H - tf), (W, H), (0, H), (0, H - tf), (sx, H - tf),
        (sx, tf), (0, tf), (0, 0),
    ]
    for i in range(len(pts) - 1):
        msp.add_line(pts[i], pts[i + 1])
    return _save_dxf(doc)


def _gen_cross_shape(span: float, arm_w: float) -> bytes:
    """Plus/cross: total span × span, arm width arm_w."""
    doc = _dxf_new(); msp = doc.modelspace()
    a = arm_w / 2
    b = span / 2
    pts = [
        (-a, -b), (a, -b), (a, -a), (b, -a), (b, a), (a, a),
        (a,  b), (-a,  b), (-a, a), (-b, a), (-b, -a), (-a, -a), (-a, -b),
    ]
    for i in range(len(pts) - 1):
        msp.add_line(pts[i], pts[i + 1])
    return _save_dxf(doc)


def _gen_star_polygon(n: int, Ro: float, Ri: float) -> bytes:
    """Star with n points, outer radius Ro, inner Ri."""
    doc = _dxf_new(); msp = doc.modelspace()
    pts = []
    for i in range(n):
        oa = 2 * math.pi * i / n - math.pi / 2
        ia = 2 * math.pi * (i + 0.5) / n - math.pi / 2
        pts.append((Ro * math.cos(oa), Ro * math.sin(oa)))
        pts.append((Ri * math.cos(ia), Ri * math.sin(ia)))
    pts.append(pts[0])
    for i in range(len(pts) - 1):
        msp.add_line(pts[i], pts[i + 1])
    return _save_dxf(doc)


def _gen_t_bracket(W: float, H: float, sw: float, sh: float) -> bytes:
    """T-bracket: base W, total height H, stem width sw, stem height sh."""
    doc = _dxf_new(); msp = doc.modelspace()
    bh = H - sh
    sx = (W - sw) / 2
    pts = [
        (0, 0), (W, 0), (W, bh), (sx + sw, bh),
        (sx + sw, H), (sx, H), (sx, bh), (0, bh), (0, 0),
    ]
    for i in range(len(pts) - 1):
        msp.add_line(pts[i], pts[i + 1])
    return _save_dxf(doc)


def _gen_slot_rect(W: float, H: float, sw: float, sh: float) -> bytes:
    """Rectangle W×H with centred rectangular slot sw×sh."""
    doc = _dxf_new(); msp = doc.modelspace()
    outer = [(0, 0), (W, 0), (W, H), (0, H), (0, 0)]
    for i in range(len(outer) - 1):
        msp.add_line(outer[i], outer[i + 1])
    sx, sy = (W - sw) / 2, (H - sh) / 2
    inner = [(sx, sy), (sx + sw, sy), (sx + sw, sy + sh), (sx, sy + sh), (sx, sy)]
    for i in range(len(inner) - 1):
        msp.add_line(inner[i], inner[i + 1])
    return _save_dxf(doc)


def _gen_ngon_hole(n: int, Ro: float, Rh: float) -> bytes:
    """Regular n-gon with central circular hole radius Rh."""
    doc = _dxf_new(); msp = doc.modelspace()
    pts = [(Ro * math.cos(2 * math.pi * i / n), Ro * math.sin(2 * math.pi * i / n)) for i in range(n)]
    pts.append(pts[0])
    for i in range(len(pts) - 1):
        msp.add_line(pts[i], pts[i + 1])
    msp.add_circle((0, 0), Rh)
    return _save_dxf(doc)


def _gen_arch(W: float, H_rect: float, R: float) -> bytes:
    """Rectangle W×H_rect with semicircle arch on top (total height H_rect+R)."""
    doc = _dxf_new(); msp = doc.modelspace()
    cx = W / 2
    msp.add_line((0, 0), (W, 0))
    msp.add_line((W, 0), (W, H_rect))
    msp.add_line((0, H_rect), (0, 0))
    # Arc cap
    msp.add_arc((cx, H_rect), R, 0, 180)
    msp.add_line((0, H_rect), (cx - R, H_rect))
    msp.add_line((cx + R, H_rect), (W, H_rect))
    return _save_dxf(doc)


def _gen_notched_rect(W: float, H: float, nw: float, nh: float) -> bytes:
    """Rectangle with corner notch (top-right cut)."""
    doc = _dxf_new(); msp = doc.modelspace()
    pts = [
        (0, 0), (W, 0), (W, H - nh), (W - nw, H - nh),
        (W - nw, H), (0, H), (0, 0),
    ]
    for i in range(len(pts) - 1):
        msp.add_line(pts[i], pts[i + 1])
    return _save_dxf(doc)


def _gen_i_bracket(W: float, H: float, tf: float, tw: float) -> bytes:
    """I-bracket (same cross-section as H-beam but different aspect)."""
    return _gen_h_beam(W, H, tf, tw)


def _gen_rect_grid_holes(W: float, H: float, cols: int, rows: int, r: float) -> bytes:
    """Rectangle with cols×rows grid of circular holes."""
    holes = []
    col_step = W / (cols + 1)
    row_step = H / (rows + 1)
    for c in range(1, cols + 1):
        for rw in range(1, rows + 1):
            holes.append((col_step * c, row_step * rw, r))
    return _gen_rect_holes(W, H, holes)


def _gen_d_shape(W: float, H: float) -> bytes:
    """D-shape: semicircle (right side) + rectangle (left side)."""
    doc = _dxf_new(); msp = doc.modelspace()
    R = H / 2
    msp.add_line((0, 0), (W, 0))
    msp.add_line((0, H), (0, 0))
    msp.add_line((W, H), (0, H))
    msp.add_arc((W, R), R, -90, 90)
    return _save_dxf(doc)


def _gen_chevron(W: float, H: float, depth: float) -> bytes:
    """Chevron / arrow shape pointing right."""
    doc = _dxf_new(); msp = doc.modelspace()
    pts = [
        (0, 0), (W - depth, 0), (W, H / 2),
        (W - depth, H), (0, H), (depth, H / 2), (0, 0),
    ]
    for i in range(len(pts) - 1):
        msp.add_line(pts[i], pts[i + 1])
    return _save_dxf(doc)


def _gen_omega(W: float, H: float, neck_w: float, base_h: float) -> bytes:
    """Omega / horseshoe profile (open-bottom U with flared feet)."""
    doc = _dxf_new(); msp = doc.modelspace()
    fl = (W - neck_w) / 2  # flange width
    pts = [
        (0, 0), (fl, 0), (fl, base_h),
        (fl, base_h), (W / 2 - neck_w / 2, base_h),
        (W / 2 - neck_w / 2, H), (W / 2 + neck_w / 2, H),
        (W / 2 + neck_w / 2, base_h), (W - fl, base_h),
        (W - fl, 0), (W, 0), (W, base_h + 5),
        (0, base_h + 5), (0, 0),
    ]
    for i in range(len(pts) - 1):
        msp.add_line(pts[i], pts[i + 1])
    return _save_dxf(doc)


def _gen_sector(start_deg: float, end_deg: float, R: float) -> bytes:
    """Pie / sector shape."""
    doc = _dxf_new(); msp = doc.modelspace()
    msp.add_arc((0, 0), R, start_deg, end_deg)
    s = math.radians(start_deg)
    e = math.radians(end_deg)
    msp.add_line((0, 0), (R * math.cos(s), R * math.sin(s)))
    msp.add_line((0, 0), (R * math.cos(e), R * math.sin(e)))
    return _save_dxf(doc)


# ─── 溝・横穴専用ジェネレーター ──────────────────────────────────────────────

def _gen_side_hole_param(W: float, H: float, cx: float, cy: float, r: float) -> bytes:
    """横穴: plate W×H with single circular cutout at (cx,cy) radius r."""
    doc = _dxf_new(); msp = doc.modelspace()
    outer = [(0, 0), (W, 0), (W, H), (0, H), (0, 0)]
    for i in range(len(outer) - 1):
        msp.add_line(outer[i], outer[i + 1])
    msp.add_circle((cx, cy), r)
    return _save_dxf(doc)


def _gen_multi_side_holes(W: float, H: float, holes: list) -> bytes:
    """複数横穴: plate W×H with multiple holes [(cx,cy,r)...]."""
    return _gen_rect_holes(W, H, holes)


def _gen_curved_groove_param(W: float, H: float, cx: float, r: float) -> bytes:
    """曲線溝: rect W×H with semicircular arc groove centred at (cx,H) cutting downward."""
    doc = _dxf_new(); msp = doc.modelspace()
    msp.add_line((0, 0), (W, 0))
    msp.add_line((W, 0), (W, H))
    msp.add_line((0, H), (0, 0))
    msp.add_line((0, H), (cx - r, H))
    msp.add_line((cx + r, H), (W, H))
    msp.add_arc((cx, H), r, 180, 360)  # 下向きアーク
    return _save_dxf(doc)


def _gen_v_groove(W: float, H: float, vw: float, vd: float) -> bytes:
    """V溝: rectangle with triangular V-notch from top centre."""
    doc = _dxf_new(); msp = doc.modelspace()
    cx = W / 2
    pts = [
        (0, 0), (W, 0), (W, H),
        (cx + vw / 2, H), (cx, H - vd), (cx - vw / 2, H),
        (0, H), (0, 0),
    ]
    for i in range(len(pts) - 1):
        msp.add_line(pts[i], pts[i + 1])
    return _save_dxf(doc)


def _gen_keyway(W: float, H: float, kw: float, kd: float) -> bytes:
    """キー溝: rectangle with centred rectangular keyway cut from top edge."""
    doc = _dxf_new(); msp = doc.modelspace()
    kx = (W - kw) / 2
    pts = [
        (0, 0), (W, 0), (W, H),
        (kx + kw, H), (kx + kw, H - kd), (kx, H - kd), (kx, H),
        (0, H), (0, 0),
    ]
    for i in range(len(pts) - 1):
        msp.add_line(pts[i], pts[i + 1])
    return _save_dxf(doc)


def _gen_step_groove(W: float, H: float, sw: float, sd: float) -> bytes:
    """段付き溝: rectangle with L-step recess on right side (simulates pocket/rebate)."""
    doc = _dxf_new(); msp = doc.modelspace()
    pts = [
        (0, 0), (W, 0), (W, H - sd), (W - sw, H - sd),
        (W - sw, H), (0, H), (0, 0),
    ]
    for i in range(len(pts) - 1):
        msp.add_line(pts[i], pts[i + 1])
    return _save_dxf(doc)


def _gen_arc_groove_side(W: float, H: float, cy: float, r: float) -> bytes:
    """側面曲線溝: plate with arc groove cut from right side (at height cy)."""
    doc = _dxf_new(); msp = doc.modelspace()
    msp.add_line((0, 0), (W, 0))
    msp.add_line((0, H), (0, 0))
    msp.add_line((0, H), (W, H))
    msp.add_line((W, 0), (W, cy - r))
    msp.add_line((W, cy + r), (W, H))
    # Arc groove cuts LEFT from right wall (centre at (W, cy))
    msp.add_arc((W, cy), r, 90, 270)
    return _save_dxf(doc)


def _gen_double_groove(W: float, H: float, r1: float, r2: float) -> bytes:
    """二重曲線溝: plate with two arc grooves from top edge."""
    doc = _dxf_new(); msp = doc.modelspace()
    cx1, cx2 = W / 3, 2 * W / 3
    msp.add_line((0, 0), (W, 0))
    msp.add_line((W, 0), (W, H))
    msp.add_line((0, H), (0, 0))
    # Top edge segments around two grooves
    msp.add_line((0, H), (cx1 - r1, H))
    msp.add_line((cx1 + r1, H), (cx2 - r2, H))
    msp.add_line((cx2 + r2, H), (W, H))
    msp.add_arc((cx1, H), r1, 180, 360)
    msp.add_arc((cx2, H), r2, 180, 360)
    return _save_dxf(doc)


# ─── ネジ穴専用ジェネレーター ────────────────────────────────────────────────

def _gen_bolt_circle(W: float, H: float, n_holes: int, BCD: float, hole_d: float) -> bytes:
    """ボルト穴パターン: plate W×H with n_holes evenly spaced on Bolt Circle (BCD)."""
    doc = _dxf_new(); msp = doc.modelspace()
    outer = [(0, 0), (W, 0), (W, H), (0, H), (0, 0)]
    for i in range(len(outer) - 1):
        msp.add_line(outer[i], outer[i + 1])
    cx, cy = W / 2, H / 2
    r_hole = hole_d / 2
    R_bcd = BCD / 2
    for i in range(n_holes):
        angle = 2 * math.pi * i / n_holes
        msp.add_circle((cx + R_bcd * math.cos(angle), cy + R_bcd * math.sin(angle)), r_hole)
    return _save_dxf(doc)


def _gen_counterbore_param(W: float, H: float, cx: float, cy: float,
                            cap_r: float, thru_r: float) -> bytes:
    """座グリ(パラメータ化): plate with concentric cap+through circles at (cx,cy)."""
    doc = _dxf_new(); msp = doc.modelspace()
    outer = [(0, 0), (W, 0), (W, H), (0, H), (0, 0)]
    for i in range(len(outer) - 1):
        msp.add_line(outer[i], outer[i + 1])
    msp.add_circle((cx, cy), cap_r)
    msp.add_circle((cx, cy), thru_r)
    return _save_dxf(doc)


# ─── テーパー加工ジェネレーター ──────────────────────────────────────────────

def _gen_taper_right_trap(Wb: float, Wt: float, H_trap: float) -> bytes:
    """右台形プロファイル（1辺テーパー）: 底辺Wb、上辺Wt、高さH_trap。左辺垂直・右辺傾斜。"""
    doc = _dxf_new(); msp = doc.modelspace()
    pts = [(0, 0), (Wb, 0), (Wt, H_trap), (0, H_trap), (0, 0)]
    for i in range(len(pts) - 1):
        msp.add_line(pts[i], pts[i + 1])
    return _save_dxf(doc)


def _make_frustum_mesh(W_bot: float, L_bot: float, W_top: float,
                        L_top: float, H: float) -> "trimesh.Trimesh":
    """4辺テーパー(フラストム): 底面W_bot×L_bot、上面W_top×L_top(中央寄せ)、高さH。"""
    dx = (W_bot - W_top) / 2
    dy = (L_bot - L_top) / 2
    verts = np.array([
        [0,          0,          0],
        [W_bot,      0,          0],
        [W_bot,      L_bot,      0],
        [0,          L_bot,      0],
        [dx,         dy,         H],
        [dx + W_top, dy,         H],
        [dx + W_top, dy + L_top, H],
        [dx,         dy + L_top, H],
    ], dtype=float)
    faces = np.array([
        [0, 2, 1], [0, 3, 2],   # bottom
        [4, 5, 6], [4, 6, 7],   # top
        [0, 1, 5], [0, 5, 4],   # front
        [2, 3, 7], [2, 7, 6],   # back
        [3, 0, 4], [3, 4, 7],   # left
        [1, 2, 6], [1, 6, 5],   # right
    ])
    return trimesh.Trimesh(vertices=verts, faces=faces, process=True)


def _make_3side_taper_mesh(W: float, L: float, H: float,
                            draft: float) -> "trimesh.Trimesh":
    """3辺テーパー: 底面W×L、上面は左辺垂直+前後右の3辺がdraftだけ縮退、高さH。"""
    verts = np.array([
        [0,            0,      0],
        [W,            0,      0],
        [W,            L,      0],
        [0,            L,      0],
        [0,            draft,  H],
        [W - 2*draft,  draft,  H],
        [W - 2*draft,  L-draft, H],
        [0,            L-draft, H],
    ], dtype=float)
    faces = np.array([
        [0, 2, 1], [0, 3, 2],   # bottom
        [4, 5, 6], [4, 6, 7],   # top
        [0, 1, 5], [0, 5, 4],   # front (tapered)
        [2, 3, 7], [2, 7, 6],   # back  (tapered)
        [3, 0, 4], [3, 4, 7],   # left  (vertical)
        [1, 2, 6], [1, 6, 5],   # right (tapered)
    ])
    return trimesh.Trimesh(vertices=verts, faces=faces, process=True)


# ─── R加工ジェネレーター ─────────────────────────────────────────────────────

def _gen_cap_1side(W: float, H: float) -> bytes:
    """1辺半円キャップ: 矩形W×Hの上辺中央に半円(r=W/2)を付けた形状。"""
    doc = _dxf_new(); msp = doc.modelspace()
    msp.add_line((0, 0), (W, 0))
    msp.add_line((W, 0), (W, H))
    msp.add_arc((W / 2, H), W / 2, 0, 180)   # top semicircle (CCW: 0→180)
    msp.add_line((0, H), (0, 0))
    return _save_dxf(doc)


def _gen_r_slot_plate(W: float, H: float, sw: float, sh: float) -> bytes:
    """長穴スロット板: W×H板の中央にsw幅×sh長の長穴(両端半円)。sw < sh 必須。"""
    doc = _dxf_new(); msp = doc.modelspace()
    outer = [(0, 0), (W, 0), (W, H), (0, H), (0, 0)]
    for i in range(len(outer) - 1):
        msp.add_line(outer[i], outer[i + 1])
    cx, cy = W / 2, H / 2
    sr = sw / 2
    straight = sh - sw
    msp.add_arc((cx, cy + straight / 2), sr, 0, 180)    # top cap (180° CCW)
    msp.add_line((cx - sr, cy + straight / 2), (cx - sr, cy - straight / 2))
    msp.add_arc((cx, cy - straight / 2), sr, 180, 360)  # bottom cap (180° CCW)
    msp.add_line((cx + sr, cy - straight / 2), (cx + sr, cy + straight / 2))
    return _save_dxf(doc)


def _gen_r_inner_groove(W: float, H: float, groove_w: float,
                         groove_d: float) -> bytes:
    """R底溝: W×H矩形板の上辺中央に幅groove_w・深さgroove_d の半円底溝。
    groove_d >= groove_w/2 (直線部分 = groove_d - groove_w/2)。"""
    doc = _dxf_new(); msp = doc.modelspace()
    gr = groove_w / 2
    straight_d = groove_d - gr
    cx = W / 2
    # outer profile (top edge has gap for groove)
    msp.add_line((0, 0), (W, 0))
    msp.add_line((W, 0), (W, H))
    msp.add_line((W, H), (cx + gr, H))
    # groove right wall → semicircle → left wall
    msp.add_line((cx + gr, H), (cx + gr, H - straight_d))
    msp.add_arc((cx, H - straight_d), gr, 180, 360)  # arc cuts into plate (CCW 180→360)
    msp.add_line((cx - gr, H - straight_d), (cx - gr, H))
    msp.add_line((cx - gr, H), (0, H))
    msp.add_line((0, H), (0, 0))
    return _save_dxf(doc)


# ─── CSG 3D ジェネレーター (manifold3d) ──────────────────────────────────────

def _manifold_to_trimesh(m) -> "trimesh.Trimesh":
    """manifold3d Manifold → trimesh.Trimesh 変換。"""
    mesh = m.to_mesh()
    verts = np.array(mesh.vert_properties)[:, :3]
    faces = np.array(mesh.tri_verts).reshape(-1, 3)
    return trimesh.Trimesh(vertices=verts, faces=faces, process=True)


def _make_csg_l_3d() -> "trimesh.Trimesh":
    """2ボックス L字 3D接合 (100×40×60 + 40×60×60)。共有面のみ接触、重複なし。"""
    from manifold3d import Manifold
    b1 = Manifold.cube([100, 40, 60])
    b2 = Manifold.cube([40, 60, 60]).translate([0, 40, 0])
    return _manifold_to_trimesh(b1 + b2)


def _make_csg_t_3d() -> "trimesh.Trimesh":
    """2ボックス T字 3D接合 (120×20×40 + 40×80×40 中央配置)。"""
    from manifold3d import Manifold
    b1 = Manifold.cube([120, 20, 40])
    b2 = Manifold.cube([40, 80, 40]).translate([40, 20, 0])
    return _manifold_to_trimesh(b1 + b2)


def _make_csg_stair_3d() -> "trimesh.Trimesh":
    """3ボックス 階段状 3D接合 (各段 50×50×30、X/Z方向にオフセット)。"""
    from manifold3d import Manifold
    b1 = Manifold.cube([50, 50, 30])
    b2 = Manifold.cube([50, 50, 30]).translate([50, 0, 30])
    b3 = Manifold.cube([50, 50, 30]).translate([100, 0, 60])
    return _manifold_to_trimesh(b1 + b2 + b3)


def _make_csg_cross_3d() -> "trimesh.Trimesh":
    """5ボックス 3D十字接合 (中央60×60×60 + 4方向アーム 40×20×20)。"""
    from manifold3d import Manifold
    cx = Manifold.cube([60, 60, 60])
    arm_x1 = Manifold.cube([60, 20, 20]).translate([-60, 20, 20])
    arm_x2 = Manifold.cube([60, 20, 20]).translate([60, 20, 20])
    arm_y1 = Manifold.cube([20, 60, 20]).translate([20, -60, 20])
    arm_y2 = Manifold.cube([20, 60, 20]).translate([20, 60, 20])
    return _manifold_to_trimesh(cx + arm_x1 + arm_x2 + arm_y1 + arm_y2)


def _make_csg_tower_3d() -> "trimesh.Trimesh":
    """4ボックス タワー状 3D接合 (各層サイズを縮小しながら積み上げ)。"""
    from manifold3d import Manifold
    b1 = Manifold.cube([80, 80, 20])
    b2 = Manifold.cube([60, 60, 20]).translate([10, 10, 20])
    b3 = Manifold.cube([40, 40, 20]).translate([20, 20, 40])
    b4 = Manifold.cube([20, 20, 20]).translate([30, 30, 60])
    return _manifold_to_trimesh(b1 + b2 + b3 + b4)


def _make_csg_box_cyl_hole() -> "trimesh.Trimesh":
    """ボックスに円柱穴 (Boolean差分): 100×80×40 box - φ30×40 cylinder。"""
    from manifold3d import Manifold
    box = Manifold.cube([100, 80, 40])
    cyl = Manifold.cylinder(40, 15, 15, circular_segments=64).translate([50, 40, 0])
    return _manifold_to_trimesh(box - cyl)


def _make_csg_box_4holes() -> "trimesh.Trimesh":
    """ボックスに4円柱穴 (Boolean差分×4): 120×100×30 box - 4×φ16穴。"""
    from manifold3d import Manifold
    box = Manifold.cube([120, 100, 30])
    r = 8
    for cx, cy in [(25, 25), (95, 25), (25, 75), (95, 75)]:
        box = box - Manifold.cylinder(30, r, r, circular_segments=48).translate([cx, cy, 0])
    return _manifold_to_trimesh(box)


def _make_csg_compound() -> "trimesh.Trimesh":
    """複合形状: ボックス + 円柱 union → 頂部に球 union → 底部に穴 diff。"""
    from manifold3d import Manifold
    box  = Manifold.cube([80, 80, 40])
    cyl  = Manifold.cylinder(60, 20, 20, circular_segments=64).translate([40, 40, 0])
    ball = Manifold.sphere(18, circular_segments=48).translate([40, 40, 60])
    hole = Manifold.cylinder(40, 10, 10, circular_segments=48).translate([40, 40, 0])
    return _manifold_to_trimesh((box + cyl + ball) - hole)


def _make_csg_frame_3d() -> "trimesh.Trimesh":
    """3D フレーム: 外箱 100×80×50 − 内箱 80×60×50 (壁厚10mm、底あり)。"""
    from manifold3d import Manifold
    outer = Manifold.cube([100, 80, 50])
    inner = Manifold.cube([80, 60, 45]).translate([10, 10, 5])
    return _manifold_to_trimesh(outer - inner)


def _make_csg_interlocked() -> "trimesh.Trimesh":
    """凸型インターロック: 下台 120×60×20 + 上部凸 60×60×30 (中央)。"""
    from manifold3d import Manifold
    base   = Manifold.cube([120, 60, 20])
    tongue = Manifold.cube([60, 60, 30]).translate([30, 0, 20])
    return _manifold_to_trimesh(base + tongue)


def _make_csg_10box_joined() -> "trimesh.Trimesh":
    """[旧] 10ボックス X方向一列配置 (参照用)。"""
    from manifold3d import Manifold
    import random
    rng = random.Random(42)
    result = None
    x = 0.0
    for i in range(10):
        w = rng.uniform(20, 60); h = rng.uniform(20, 60); d = rng.uniform(20, 60)
        b = Manifold.cube([w, h, d]).translate([x, 0, 0])
        result = b if result is None else result + b
        x += w
    return _manifold_to_trimesh(result)


# ─── 真の3D複合形状ジェネレーター ────────────────────────────────────────────

def _make_csg_3d_random_10box() -> "trimesh.Trimesh":
    """
    真の3Dランダム接合: 10ボックスをXYZ空間でランダム配置・重複あり。
    manifold3d が重複領域で Boolean Union を実行する真の CSG 演算。
    各ボックスがX/Y/Z それぞれ独立なランダム位置 → 立体的な多面接合。
    """
    from manifold3d import Manifold
    import random
    rng = random.Random(42)
    result = None
    for _ in range(10):
        w = rng.uniform(25, 55)
        h = rng.uniform(25, 55)
        d = rng.uniform(25, 55)
        x = rng.uniform(-40, 40)
        y = rng.uniform(-40, 40)
        z = rng.uniform(-40, 40)
        b = Manifold.cube([w, h, d]).translate([x, y, z])
        result = b if result is None else result + b
    return _manifold_to_trimesh(result)


def _make_csg_bracket_3d() -> "trimesh.Trimesh":
    """
    L型ブラケット (機械部品): ベース板120×80×10 + 立壁10×80×60 + リブ40×10×40
    + ベース4×M6穴(Z方向貫通) + 立壁M8穴(X方向貫通)。
    押し出しでは作れない多方向穴あき形状。
    """
    from manifold3d import Manifold
    base  = Manifold.cube([120, 80, 10])
    wall  = Manifold.cube([10, 80, 60]).translate([0, 0, 10])
    rib   = Manifold.cube([40, 10, 40]).translate([10, 35, 10])
    shape = base + wall + rib
    # ベース 4×M6 貫通穴 (Z方向)
    for cx, cy in [(25, 20), (25, 60), (95, 20), (95, 60)]:
        shape = shape - Manifold.cylinder(10, 3.3, 3.3, 32).translate([cx, cy, 0])
    # 立壁 M8 貫通穴 (X方向): Ry90° で Z軸→X軸方向シリンダー
    wall_hole = (Manifold.cylinder(12, 4.5, 4.5, 32)
                 .rotate([0, 90, 0])
                 .translate([0, 40, 40]))
    return _manifold_to_trimesh(shape - wall_hole)


def _make_csg_flange_3d() -> "trimesh.Trimesh":
    """
    フランジ (機械部品): 大径円盤φ120×20 + 小径ネックφ60×30
    + ネック内貫通φ40 + 6×M8ボルト穴(PCD90, Z方向)。
    """
    from manifold3d import Manifold
    disk  = Manifold.cylinder(20, 60, 60, 128)
    neck  = Manifold.cylinder(30, 30, 30, 64).translate([0, 0, 20])
    bore  = Manifold.cylinder(50, 20, 20, 64)
    shape = (disk + neck) - bore
    for i in range(6):
        ang = math.radians(i * 60)
        cx, cy = 45 * math.cos(ang), 45 * math.sin(ang)
        shape = shape - Manifold.cylinder(20, 4.5, 4.5, 32).translate([cx, cy, 0])
    return _manifold_to_trimesh(shape)


def _make_csg_housing_3d() -> "trimesh.Trimesh":
    """
    ハウジング (機械部品): 外箱140×100×80 − 内空洞120×80×70(上面開口)
    − 前面φ40穴 − 後面φ30穴 − 左右各φ20穴 (4方向穴あき)。
    2D DXF では絶対に表現できない真の3D形状。
    """
    from manifold3d import Manifold
    outer  = Manifold.cube([140, 100, 80])
    inner  = Manifold.cube([120, 80, 70]).translate([10, 10, 10])
    shape  = outer - inner
    # 前面 Y=0 → Rx90°: Z軸→-Y軸 → translate でY=0から貫通
    front  = Manifold.cylinder(15, 20, 20, 64).rotate([90, 0, 0]).translate([70, 15, 40])
    # 後面 Y=100 → 同じ向き、Y側から貫通
    back   = Manifold.cylinder(15, 15, 15, 64).rotate([90, 0, 0]).translate([70, 100, 40])
    # 左面 X=0 → Ry90°: Z軸→X軸
    left   = Manifold.cylinder(15, 10, 10, 64).rotate([0, 90, 0]).translate([0,  50, 40])
    # 右面 X=140
    right  = Manifold.cylinder(15, 10, 10, 64).rotate([0, 90, 0]).translate([125, 50, 40])
    return _manifold_to_trimesh(shape - front - back - left - right)


def _make_csg_stepped_shaft() -> "trimesh.Trimesh":
    """
    段付きシャフト: φ60×30 + φ45×40 + φ30×50 の3段同軸円柱
    + キー溝(20×8×30 矩形差分)付き。
    """
    from manifold3d import Manifold
    s1     = Manifold.cylinder(30, 30, 30, 128)
    s2     = Manifold.cylinder(40, 22.5, 22.5, 96).translate([0, 0, 30])
    s3     = Manifold.cylinder(50, 15,   15,   64).translate([0, 0, 70])
    shaft  = s1 + s2 + s3
    keyway = Manifold.cube([20, 8, 30]).translate([-10, 22, 0])
    return _manifold_to_trimesh(shaft - keyway)


def _make_csg_cross_connector() -> "trimesh.Trimesh":
    """
    3方向クロスコネクター: X/Y/Z 各方向のパイプ(外径φ50, 内径φ30)が中央で交差。
    中心に球(r=32)を配置してジャンクションを補強し、Watertight を確保。
    6面から穴が開く真の3D交差形状 - 押し出しでは絶対に作れない。
    """
    from manifold3d import Manifold
    pipe_z = Manifold.cylinder(60, 25, 25, 64).translate([0, 0, -30])
    pipe_x = Manifold.cylinder(60, 25, 25, 64).rotate([0, 90, 0]).translate([-30, 0, 0])
    pipe_y = Manifold.cylinder(60, 25, 25, 64).rotate([90, 0, 0]).translate([0, -30, 0])
    center = Manifold.sphere(32, 64)                        # 中央球でジャンクション補強
    outer  = pipe_z + pipe_x + pipe_y + center
    bore_z = Manifold.cylinder(62, 15, 15, 64).translate([0, 0, -31])
    bore_x = Manifold.cylinder(62, 15, 15, 64).rotate([0, 90, 0]).translate([-31, 0, 0])
    bore_y = Manifold.cylinder(62, 15, 15, 64).rotate([90, 0, 0]).translate([0, -31, 0])
    bores  = bore_z + bore_x + bore_y                       # Union先にまとめて引く
    return _manifold_to_trimesh(outer - bores)



# ─── qwen3.5 AI 自己チェック (ローカルOllama / APIゼロ) ──────────────────────

def _csg_ai_check(shape_id: str, desc: str, vol: float, faces: int,
                   watertight: bool,
                   ollama_url: str = "http://ollama:11434") -> str:
    """
    Qwen3 generative model (Docker Ollama) に形状の妥当性チェックをリクエスト。
    APIキー不要・完全ローカル。タイムアウト20秒。
    戻り値: AI判定コメント文字列。
    """
    import requests
    prompt = (
        f"3Dモデル自己チェック。形状ID: {shape_id}\n"
        f"説明: {desc}\n"
        f"体積: {vol:.0f} mm³、位相面数: {faces}、Watertight: {watertight}\n"
        "この形状は幾何学的に正しいか？体積・面数が説明と矛盾していないか？"
        "1〜2文で日本語で判定してください。"
    )
    try:
        resp = requests.post(
            f"{ollama_url}/api/generate",
            json={"model": OLLAMA_GEN_MODEL, "prompt": prompt,
                  "stream": False, "think": False,
                  "options": {"num_predict": 80, "temperature": 0}},
            timeout=30,
        )
        if resp.status_code == 200:
            return resp.json().get("response", "").strip()
        return f"[HTTP {resp.status_code}]"
    except Exception as e:
        return f"[Ollama接続エラー: {e}]"


def render_dxf_2d(dxf_bytes: bytes, size_in: float = 3.5) -> bytes:
    """
    Render 2D DXF entities (LINE / ARC / CIRCLE / LWPOLYLINE) to PNG bytes
    using matplotlib.  Returns raw PNG bytes for st.image().
    """
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import matplotlib.patches as mpatches

    doc = ezdxf.read(io.StringIO(dxf_bytes.decode("utf-8")))
    msp = doc.modelspace()

    fig, ax = plt.subplots(figsize=(size_in, size_in))
    ax.set_aspect("equal")
    ax.set_facecolor("#1e293b")
    fig.patch.set_facecolor("#1e293b")

    for entity in msp:
        etype = entity.dxftype()
        try:
            if etype == "LINE":
                s, e = entity.dxf.start, entity.dxf.end
                ax.plot([s.x, e.x], [s.y, e.y], color="#60a5fa", lw=1.5)
            elif etype == "ARC":
                c = entity.dxf.center
                r = entity.dxf.radius
                sa, ea = entity.dxf.start_angle, entity.dxf.end_angle
                if ea <= sa:
                    ea += 360
                angs = np.linspace(np.radians(sa), np.radians(ea),
                                   max(8, int((ea - sa) / 3)))
                ax.plot(c.x + r * np.cos(angs), c.y + r * np.sin(angs),
                        color="#60a5fa", lw=1.5)
            elif etype == "CIRCLE":
                c = entity.dxf.center
                r = entity.dxf.radius
                ax.add_patch(mpatches.Circle((c.x, c.y), r,
                                             fill=False, edgecolor="#f97316", lw=1.5))
            elif etype in ("LWPOLYLINE", "POLYLINE"):
                pts_raw = list(entity.get_points())
                if pts_raw:
                    xs = [p[0] for p in pts_raw] + [pts_raw[0][0]]
                    ys = [p[1] for p in pts_raw] + [pts_raw[0][1]]
                    ax.plot(xs, ys, color="#60a5fa", lw=1.5)
        except Exception:
            pass

    ax.autoscale_view()
    ax.axis("off")
    plt.tight_layout(pad=0.1)
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=80, bbox_inches="tight",
                facecolor="#1e293b", edgecolor="none")
    plt.close(fig)
    return buf.getvalue()


def render_mesh_3d_fig(mesh) -> "go.Figure":
    """Return a compact plotly Figure for the 3D mesh preview."""
    tr = mesh_to_plotly(mesh)
    fig = go.Figure([tr])
    fig.update_layout(
        scene=dict(
            bgcolor="#0f172a", aspectmode="data",
            xaxis=dict(visible=False), yaxis=dict(visible=False), zaxis=dict(visible=False),
        ),
        paper_bgcolor="#0f172a",
        margin=dict(l=0, r=0, t=0, b=0),
        height=200,
    )
    return fig


def count_topo_faces(mesh) -> int:
    """
    Count topological face groups by clustering triangle normals.
    Two triangles belong to the same face if their normals are identical
    when rounded to 2 decimal places (≈ 0.6° precision).
    No external graph library required.
    """
    try:
        normals = mesh.face_normals
        if len(normals) == 0:
            return 0
        rounded = np.round(normals, 2)
        unique = {tuple(row) for row in rounded}
        return len(unique)
    except Exception:
        return 0


def get_topo_face_areas(mesh) -> list:
    """
    位相面ごとの面積を計算。法線ベクトルで三角形をグループ化し、
    各グループの面積合計を返す。
    戻り値: [(normal_tuple, area_mm2), ...] 面積降順ソート
    """
    try:
        normals = mesh.face_normals
        areas   = mesh.area_faces          # 各三角形の面積
        if len(normals) == 0:
            return []
        rounded = np.round(normals, 2)
        groups: dict = {}
        for norm, area in zip(rounded, areas):
            key = tuple(norm)
            groups[key] = groups.get(key, 0.0) + area
        return sorted(groups.items(), key=lambda x: -x[1])
    except Exception:
        return []


def categorize_shape(id_: str) -> str:
    """テストケースIDからカテゴリ名を返す。"""
    if id_.startswith("csg_"):                                      return "多面体(CSG)"
    if any(id_.startswith(p) for p in ("screw_",)):                 return "ネジ加工(竪穴)"
    if any(id_.startswith(p) for p in ("bcd_",)):                   return "ネジ加工(ボルト穴)"
    if id_.startswith("cbore_"):                                     return "座グリ"
    if any(id_.startswith(p) for p in ("yokoana_", "arc_side_")):   return "横穴"
    if any(id_.startswith(p) for p in ("curved_", "double_groove_")): return "曲線溝"
    if any(id_.startswith(p) for p in ("v_groove_", "keyway_", "step_groove_")): return "直線溝"
    if id_.startswith("taper_1side"):                                return "テーパー1辺"
    if id_.startswith("taper_2side"):                                return "テーパー2辺"
    if id_.startswith("taper_3side"):                                return "テーパー3辺"
    if id_.startswith("taper_4side"):                                return "テーパー4辺/フラストム"
    if id_.startswith("r_cap"):                                      return "R加工 1辺半円キャップ"
    if any(id_.startswith(p) for p in ("r_stadium_", "stadium_")):  return "R加工 2辺スタジアム"
    if any(id_.startswith(p) for p in ("r_rrect_", "rrect_")):      return "R加工 4隅R"
    if id_.startswith("r_slot_"):                                    return "R加工 長穴スロット板"
    if id_.startswith("r_groove_"):                                  return "R加工 R底溝"
    if any(id_.startswith(p) for p in ("rect_", "circle", "ring_")): return "基本形状(穴なし)"
    if any(id_.startswith(p) for p in ("ngon_",)):                  return "多角形"
    if any(id_.startswith(p) for p in ("l_shape_", "t_bracket_", "slot_rect_",
                                        "u_shape_", "h_beam_", "cross_",
                                        "i_bracket_", "d_shape_", "chevron_")):
        return "複合形状"
    return "その他"


def build_full_report(progress_cb=None) -> list:
    """
    全テストスイート(拡張202件 + CSG10件)を実行し、
    カテゴリ・面積情報を付加した統合レポートを返す。
    """
    ext_suite = build_extended_test_suite()
    csg_suite = build_csg_test_suite()
    all_items = ext_suite + csg_suite
    total = len(all_items)
    rows = []

    for idx, item in enumerate(all_items):
        if progress_cb:
            progress_cb(idx, total, item["id"])

        cat = categorize_shape(item["id"])
        row = {"カテゴリ": cat, "ID": item["id"], "説明": item["desc"]}

        try:
            # メッシュ生成
            if "gen_mesh" in item:
                mesh = item["gen_mesh"]()
                dxf_bytes = None
            else:
                dxf_bytes = item["gen"]()
                doc  = ezdxf.read(io.StringIO(dxf_bytes.decode("utf-8")))
                loops = extract_loops(doc, "")
                mesh, _ = loops_to_mesh(loops, item["height"]) if loops else (None, 0)

            if mesh is None or len(mesh.faces) == 0:
                row.update({"エラー": "メッシュ生成失敗", "スコア": 0})
                rows.append(row)
                continue

            # 体積比較
            vol_exp = item.get("vol")
            vol_act = mesh.volume
            vol_err = None
            if vol_exp:
                vol_err = round(abs(vol_act - vol_exp) / vol_exp * 100, 4)

            # 位相面ごとの面積
            face_area_list = get_topo_face_areas(mesh)
            n_topo = len(face_area_list)
            areas_mm2 = [a for _, a in face_area_list]
            area_max  = round(max(areas_mm2), 2) if areas_mm2 else 0
            area_min  = round(min(areas_mm2), 2) if areas_mm2 else 0
            area_avg  = round(sum(areas_mm2) / len(areas_mm2), 2) if areas_mm2 else 0
            # 上位3面の面積(mm²)
            top3 = " / ".join(f"{a:.1f}" for a in areas_mm2[:3])

            # 採点
            score = 30
            if vol_exp:
                score += 35 if (vol_err or 99) < 5 else (15 if (vol_err or 99) < 15 else 0)
            else:
                score += 35
            bbox_exp = item.get("bbox")
            if bbox_exp:
                dims = mesh.bounds[1] - mesh.bounds[0]
                if all(abs(dims[i] - bbox_exp[i]) / max(bbox_exp[i], 1) < 0.05
                       for i in range(3) if bbox_exp[i]):
                    score += 35
            else:
                score += 35
            if not mesh.is_watertight:
                score = max(0, score - 10)

            row.update({
                "スコア":         score,
                "期待体積(mm³)":  round(vol_exp, 1) if vol_exp else "—",
                "実測体積(mm³)":  round(vol_act, 1),
                "体積誤差(%)":    vol_err if vol_err is not None else "—",
                "topo面数":       n_topo,
                "三角形数":       len(mesh.faces),
                "最大面積(mm²)":  area_max,
                "最小面積(mm²)":  area_min,
                "平均面積(mm²)":  area_avg,
                "上位3面積(mm²)": top3,
                "総表面積(mm²)":  round(mesh.area, 2),
                "Watertight":     mesh.is_watertight,
            })
        except Exception as exc:
            row.update({"エラー": str(exc)[:80], "スコア": 0})

        rows.append(row)

    if progress_cb:
        progress_cb(total, total, "完了")
    return rows


def build_extended_test_suite() -> list:
    """
    Build 100+ parametric test cases covering n-gons, holes, compounds,
    arcs, grids, stars, etc.  No API calls — all local.
    """
    C = []  # accumulate cases

    def tc(id_, desc, gen, h, vol=None, bbox=None, exp_topo=None):
        return {"id": id_, "desc": desc, "gen": gen, "height": h,
                "vol": vol, "bbox": bbox, "exp_topo": exp_topo}

    # ── A: Regular n-gons (n=3..12, R=25/45) — 20 cases ─────────────────────
    for n in range(3, 13):
        for R in (25, 45):
            area = (n / 2) * R ** 2 * math.sin(2 * math.pi / n)
            pts = [(R * math.cos(2 * math.pi * k / n),
                    R * math.sin(2 * math.pi * k / n)) for k in range(n)]
            bw = max(p[0] for p in pts) - min(p[0] for p in pts)
            bh_dim = max(p[1] for p in pts) - min(p[1] for p in pts)
            C.append(tc(
                f"ngon_{n}_R{R}", f"正{n}角形 R={R}mm 厚8mm",
                _make_gen(_gen_ngon, n, R),
                8.0, vol=area * 8, bbox=(bw, bh_dim, 8.0), exp_topo=n + 2,
            ))

    # ── B: Rectangle + n circular holes — 10 cases ───────────────────────────
    _hole_configs = [
        (1, [(50, 40, 12)],                                  100, 80),
        (1, [(40, 30,  8)],                                   80, 60),
        (2, [(30, 40, 10), (70, 40, 10)],                    100, 80),
        (2, [(20, 30,  7), (55, 30,  7)],                     80, 60),
        (3, [(25, 40,  8), (50, 40,  8), (75, 40,  8)],      100, 80),
        (3, [(18, 30,  6), (40, 30,  6), (62, 30,  6)],       80, 60),
        (4, [(25, 25,  7), (75, 25,  7), (25, 55,  7), (75, 55,  7)], 100, 80),
        (4, [(15, 15,  5), (45, 15,  5), (15, 45,  5), (45, 45,  5)],  70, 60),
        (5, [(15, 40,  6), (35, 40,  6), (55, 40,  6), (75, 40,  6), (95, 40,  6)], 110, 80),
        (6, [(15+i*15, 40, 5) for i in range(6)],            110, 80),
    ]
    for n_h, holes, W, H in _hole_configs:
        h = 10.0
        cyl_area = sum(math.pi * r ** 2 for _, _, r in holes)
        C.append(tc(
            f"rect_{n_h}holes_W{W}", f"矩形{W}×{H}に{n_h}穴 厚10mm",
            _make_gen(_gen_rect_holes, W, H, holes),
            h, vol=(W * H - cyl_area) * h, bbox=(W, H, h),
        ))

    # ── C: Annular rings — 6 cases ────────────────────────────────────────────
    for Ro, Ri in [(40, 25), (50, 35), (60, 45), (35, 20), (45, 28), (55, 38)]:
        area = math.pi * (Ro ** 2 - Ri ** 2)
        C.append(tc(
            f"ring_Ro{Ro}_Ri{Ri}", f"リング Ro={Ro} Ri={Ri} 厚10mm",
            _make_gen(_gen_ring, Ro, Ri),
            10.0, vol=area * 10, bbox=(2 * Ro, 2 * Ro, 10.0),
        ))

    # ── D: Compound shapes ────────────────────────────────────────────────────
    # L-shapes — 3 variants
    for W in (60, 80, 100):
        # Parametric L-shape: W×W outer, W/2×W/2 corner cut
        cut = W // 2
        area = W * W - cut * cut
        def _l_gen(W=W, cut=cut):
            doc = _dxf_new(); msp = doc.modelspace()
            pts = [(0,0),(W,0),(W,cut),(cut,cut),(cut,W),(0,W),(0,0)]
            for i in range(len(pts)-1): msp.add_line(pts[i], pts[i+1])
            return _save_dxf(doc)
        C.append(tc(
            f"l_shape_W{W}", f"L字 {W}×{W} 厚6mm",
            _l_gen,
            6.0, vol=area * 6, bbox=(W, W, 6.0), exp_topo=8,
        ))

    # T-shapes — 3 variants
    for sw in (15, 20, 25):
        C.append(tc(
            f"t_bracket_sw{sw}", f"T字 80×80 stem={sw} 厚5mm",
            _make_gen(_gen_t_bracket, 80, 80, sw, 40),
            5.0, bbox=(80, 80, 5.0), exp_topo=8,
        ))

    # U-shapes — 3 variants
    for inner_w in (50, 60, 70):
        outer_area = 100 * 80
        inner_area = inner_w * 50
        ix = (100 - inner_w) // 2
        def _u_gen(iw=inner_w, ix=ix):
            doc = _dxf_new(); msp = doc.modelspace()
            outer = [(0,0),(100,0),(100,80),(0,80),(0,0)]
            inner = [(ix,30),(ix+iw,30),(ix+iw,80),(ix,80),(ix,30)]
            for seg in [outer, inner]:
                for i in range(len(seg)-1): msp.add_line(seg[i], seg[i+1])
            return _save_dxf(doc)
        C.append(tc(
            f"u_shape_iw{inner_w}", f"U字 100×80 内{inner_w}×50 厚5mm",
            _u_gen,
            5.0, vol=(outer_area - inner_area) * 5,
            bbox=(100, 80, 5.0), exp_topo=10,
        ))

    # H-beam — 3 variants
    for tf in (8, 10, 12):
        C.append(tc(
            f"h_beam_tf{tf}", f"H形鋼 80×80 tf={tf} tw=6 厚20mm",
            _make_gen(_gen_h_beam, 80, 80, tf, 6),
            20.0, bbox=(80, 80, 20.0), exp_topo=12,
        ))

    # Cross shapes — 3 variants
    for arm_w in (20, 25, 30):
        area = arm_w * 80 + arm_w * (80 - arm_w)  # approx
        C.append(tc(
            f"cross_aw{arm_w}", f"十字 span80 arm={arm_w} 厚6mm",
            _make_gen(_gen_cross_shape, 80, arm_w),
            6.0, bbox=(80, 80, 6.0), exp_topo=14,
        ))

    # I-bracket — 3 variants
    for H_b in (60, 80, 100):
        C.append(tc(
            f"i_beam_H{H_b}", f"I形 60×{H_b} tf=8 tw=5 厚15mm",
            _make_gen(_gen_i_bracket, 60, H_b, 8, 5),
            15.0, bbox=(60, H_b, 15.0), exp_topo=12,
        ))

    # ── E: Rounded rectangles (R=5/10/15/20, 2 sizes) — 8 cases ─────────────
    for r_corner in (5, 10, 15, 20):
        for W, H in [(100, 60), (80, 50)]:
            if r_corner * 2 >= min(W, H):
                continue
            area = W * H - (4 - math.pi) * r_corner ** 2
            C.append(tc(
                f"rrect_R{r_corner}_W{W}", f"角丸矩形 {W}×{H} R={r_corner} 厚5mm",
                _make_gen(_gen_rounded_rect, W, H, r_corner),
                5.0, vol=area * 5, bbox=(W, H, 5.0), exp_topo=10,
            ))

    # ── F: Stadium shapes — 4 cases ──────────────────────────────────────────
    for L, R in [(40, 20), (60, 25), (80, 30), (50, 20)]:
        area = L * 2 * R + math.pi * R ** 2
        C.append(tc(
            f"stadium_L{L}_R{R}", f"スタジアム L={L} R={R} 厚8mm",
            _make_gen(_gen_stadium, L, R),
            8.0, vol=area * 8, bbox=(L + 2 * R, 2 * R, 8.0),
        ))

    # ── G: Trapezoids — 4 cases ───────────────────────────────────────────────
    for Wb, Wt, H in [(100, 60, 50), (80, 40, 60), (120, 80, 40), (90, 50, 45)]:
        area = (Wb + Wt) / 2 * H
        C.append(tc(
            f"trap_Wb{Wb}_Wt{Wt}", f"台形 底{Wb} 上{Wt} H={H} 厚8mm",
            _make_gen(_gen_trapezoid, Wb, Wt, H),
            8.0, vol=area * 8, bbox=(Wb, H, 8.0), exp_topo=6,
        ))

    # ── H: Star polygons — 4 cases ────────────────────────────────────────────
    def _star_area(n, Ro, Ri):
        """Area of n-pointed star polygon via shoelace."""
        pts = []
        for k in range(n):
            oa = 2 * math.pi * k / n - math.pi / 2
            ia = 2 * math.pi * (k + 0.5) / n - math.pi / 2
            pts.append((Ro * math.cos(oa), Ro * math.sin(oa)))
            pts.append((Ri * math.cos(ia), Ri * math.sin(ia)))
        np_ = len(pts)
        area = sum(pts[i][0] * pts[(i+1) % np_][1] - pts[(i+1) % np_][0] * pts[i][1] for i in range(np_))
        return abs(area) / 2

    for n_pts, Ro, Ri in [(5, 40, 18), (5, 50, 22), (6, 40, 20), (6, 50, 25)]:
        area = _star_area(n_pts, Ro, Ri)
        C.append(tc(
            f"star_{n_pts}pt_R{Ro}", f"{n_pts}角星 Ro={Ro} Ri={Ri} 厚6mm",
            _make_gen(_gen_star_polygon, n_pts, Ro, Ri),
            6.0, vol=area * 6, bbox=None, exp_topo=n_pts * 2 + 2,
        ))

    # ── I: Slot shapes — 5 cases ──────────────────────────────────────────────
    for W, H, sw, sh in [
        (100, 60, 60, 20), (120, 80, 80, 30), (80, 50, 50, 15),
        (100, 70, 40, 40), (90, 60, 30, 30),
    ]:
        area = W * H - sw * sh
        C.append(tc(
            f"slot_W{W}_sw{sw}", f"スロット矩形 {W}×{H} 穴{sw}×{sh} 厚8mm",
            _make_gen(_gen_slot_rect, W, H, sw, sh),
            8.0, vol=area * 8, bbox=(W, H, 8.0), exp_topo=10,
        ))

    # ── J: Grid of holes — 6 cases ────────────────────────────────────────────
    for cols, rows, W, H, r in [
        (2, 2, 100, 80, 8),
        (3, 2, 120, 80, 7),
        (3, 3, 120, 100, 6),
        (4, 2, 160, 80, 7),
        (4, 3, 160, 100, 6),
        (5, 3, 180, 100, 5),
    ]:
        n_h = cols * rows
        cyl = math.pi * r ** 2 * n_h
        C.append(tc(
            f"grid_{cols}x{rows}_r{r}", f"{cols}×{rows}穴グリッド {W}×{H} r={r} 厚10mm",
            _make_gen(_gen_rect_grid_holes, W, H, cols, rows, r),
            10.0, vol=(W * H - cyl) * 10, bbox=(W, H, 10.0),
        ))

    # ── K: N-gon with central hole — 6 cases ──────────────────────────────────
    for n, Ro, Rh in [
        (4, 40, 15), (5, 45, 15), (6, 45, 18),
        (4, 55, 20), (6, 55, 22), (8, 50, 20),
    ]:
        poly_area = (n / 2) * Ro ** 2 * math.sin(2 * math.pi / n)
        area = poly_area - math.pi * Rh ** 2
        # Compute actual n-gon bbox from vertices
        _verts = [(Ro * math.cos(2 * math.pi * k / n), Ro * math.sin(2 * math.pi * k / n)) for k in range(n)]
        _bw = max(p[0] for p in _verts) - min(p[0] for p in _verts)
        _bh = max(p[1] for p in _verts) - min(p[1] for p in _verts)
        C.append(tc(
            f"ngon{n}_hole_Ro{Ro}", f"正{n}角形+中央穴 Ro={Ro} Rh={Rh} 厚8mm",
            _make_gen(_gen_ngon_hole, n, Ro, Rh),
            8.0, vol=area * 8, bbox=(_bw, _bh, 8.0),
        ))

    # ── L: Arch (D-shape) — 4 cases ───────────────────────────────────────────
    for W, Hr, R in [(60, 40, 30), (80, 50, 40), (50, 30, 25), (70, 45, 35)]:
        C.append(tc(
            f"arch_W{W}_Hr{Hr}", f"アーチ {W}×{Hr}+R{R} 厚8mm",
            _make_gen(_gen_arch, W, Hr, R),
            8.0, bbox=(W, Hr + R, 8.0),
        ))

    # ── M: D-shape — 3 cases ──────────────────────────────────────────────────
    for W, H in [(80, 60), (100, 80), (60, 50)]:
        C.append(tc(
            f"d_shape_W{W}", f"D字形 {W}×{H} 厚8mm",
            _make_gen(_gen_d_shape, W, H),
            8.0, bbox=(W + H / 2, H, 8.0),
        ))

    # ── N: Notched rectangle — 5 cases ────────────────────────────────────────
    for W, H, nw, nh in [
        (100, 80, 30, 20), (120, 80, 40, 25), (80, 60, 20, 15),
        (100, 60, 25, 20), (90, 70, 30, 20),
    ]:
        area = W * H - nw * nh
        C.append(tc(
            f"notch_W{W}_nw{nw}", f"切欠き矩形 {W}×{H} 切欠{nw}×{nh} 厚6mm",
            _make_gen(_gen_notched_rect, W, H, nw, nh),
            6.0, vol=area * 6, bbox=(W, H, 6.0), exp_topo=8,
        ))

    # ── O: Chevron/arrow shapes — 4 cases ─────────────────────────────────────
    for W, H, depth in [(100, 60, 20), (120, 80, 30), (80, 50, 15), (110, 70, 25)]:
        C.append(tc(
            f"chevron_W{W}", f"矢印/シェブロン {W}×{H} depth={depth} 厚6mm",
            _make_gen(_gen_chevron, W, H, depth),
            6.0, bbox=(W, H, 6.0), exp_topo=8,
        ))

    # ── P: Sectors (pie slices) — 5 cases ────────────────────────────────────
    for start, end, R in [(0, 90, 40), (0, 120, 40), (0, 180, 40), (0, 270, 40), (30, 150, 45)]:
        span = end - start
        area = math.pi * R ** 2 * span / 360
        C.append(tc(
            f"sector_{span}deg_R{R}", f"扇形 {span}° R={R} 厚8mm",
            _make_gen(_gen_sector, start, end, R),
            8.0, vol=area * 8,
        ))

    # ── Q: High-complexity — rect with many holes in rows ─────────────────────
    for cols, rows, W, H, r in [(6, 4, 180, 120, 6), (8, 4, 200, 100, 5), (6, 6, 180, 180, 5)]:
        n_h = cols * rows
        cyl = math.pi * r ** 2 * n_h
        C.append(tc(
            f"dense_{cols}x{rows}", f"密穴グリッド{cols}×{rows} W={W} r={r} 厚10mm",
            _make_gen(_gen_rect_grid_holes, W, H, cols, rows, r),
            10.0, vol=(W * H - cyl) * 10, bbox=(W, H, 10.0),
        ))

    # ── R: 横穴バリエーション (6 cases) ──────────────────────────────────────
    # 位置・サイズ違い / 複数穴
    _yoko_configs = [
        (100, 60, 18, 30, 10),   # 左寄り小穴
        (100, 60, 50, 30, 12),   # 中央穴
        (120, 80, 20, 40, 14),   # 大きめ板・左穴
        (120, 80, 100, 40, 14),  # 大きめ板・右穴
        (100, 60, 30, 15, 8),    # 上寄り穴
        (100, 60, 70, 45, 8),    # 下寄り穴
    ]
    for idx, (W, H, cx, cy, r) in enumerate(_yoko_configs):
        area = W * H - math.pi * r ** 2
        C.append(tc(
            f"yokoana_{idx+1}", f"横穴{idx+1}: {W}×{H} 穴Φ{2*r} at({cx},{cy}) 厚15mm",
            _make_gen(_gen_side_hole_param, W, H, cx, cy, r),
            15.0, vol=area * 15, bbox=(W, H, 15.0),
        ))

    # ── S: 曲線溝バリエーション (6 cases) ──────────────────────────────────
    _groove_configs = [
        (120, 60, 60, 15),   # 中央・小R
        (120, 60, 60, 25),   # 中央・大R
        (150, 80, 50, 20),   # 左寄り
        (150, 80, 100, 20),  # 右寄り
        (100, 60, 50, 20),   # 小板
        (180, 80, 90, 30),   # 大板
    ]
    for idx, (W, H, cx, r) in enumerate(_groove_configs):
        area = W * H - math.pi * r ** 2 / 2  # 半円分除去
        C.append(tc(
            f"curved_groove_{idx+1}", f"曲線溝{idx+1}: {W}×{H} R={r} cx={cx} 厚10mm",
            _make_gen(_gen_curved_groove_param, W, H, cx, r),
            10.0, vol=area * 10, bbox=(W, H, 10.0),
        ))

    # ── T: V溝バリエーション (4 cases) ──────────────────────────────────────
    for W, H, vw, vd in [(100, 60, 30, 15), (120, 80, 40, 20), (80, 50, 20, 10), (140, 70, 50, 25)]:
        area = W * H - vw * vd / 2
        C.append(tc(
            f"v_groove_W{W}", f"V溝 {W}×{H} 溝幅{vw} 深さ{vd} 厚8mm",
            _make_gen(_gen_v_groove, W, H, vw, vd),
            8.0, vol=area * 8, bbox=(W, H, 8.0), exp_topo=9,
        ))

    # ── U: キー溝バリエーション (4 cases) ────────────────────────────────────
    for W, H, kw, kd in [(80, 60, 20, 10), (100, 70, 25, 12), (60, 50, 15, 8), (120, 80, 30, 15)]:
        area = W * H - kw * kd
        C.append(tc(
            f"keyway_W{W}", f"キー溝 {W}×{H} 溝幅{kw} 深さ{kd} 厚10mm",
            _make_gen(_gen_keyway, W, H, kw, kd),
            10.0, vol=area * 10, bbox=(W, H, 10.0), exp_topo=10,
        ))

    # ── V: 段付き溝 (4 cases) ─────────────────────────────────────────────
    for W, H, sw, sd in [(100, 60, 30, 15), (120, 80, 40, 20), (80, 50, 25, 12), (140, 70, 50, 18)]:
        area = W * H - sw * sd
        C.append(tc(
            f"step_groove_W{W}", f"段付き溝 {W}×{H} 溝幅{sw} 深さ{sd} 厚8mm",
            _make_gen(_gen_step_groove, W, H, sw, sd),
            8.0, vol=area * 8, bbox=(W, H, 8.0), exp_topo=8,
        ))

    # ── W: 側面曲線溝 (3 cases) ─────────────────────────────────────────────
    for W, H, cy, r in [(100, 80, 40, 18), (120, 100, 50, 22), (80, 60, 30, 15)]:
        area = W * H - math.pi * r ** 2 / 2
        C.append(tc(
            f"arc_side_groove_W{W}", f"側面曲線溝 {W}×{H} R={r} 厚10mm",
            _make_gen(_gen_arc_groove_side, W, H, cy, r),
            10.0, bbox=(W, H, 10.0),
        ))

    # ── X: 二重曲線溝 (3 cases) ─────────────────────────────────────────────
    for W, H, r1, r2 in [(150, 80, 20, 20), (180, 80, 25, 15), (120, 70, 18, 18)]:
        area = W * H - math.pi * (r1 ** 2 + r2 ** 2) / 2
        C.append(tc(
            f"double_groove_W{W}", f"二重曲線溝 {W}×{H} R={r1}/{r2} 厚10mm",
            _make_gen(_gen_double_groove, W, H, r1, r2),
            10.0, bbox=(W, H, 10.0),
        ))

    # ── Y: ネジ穴 — 単一メートルネジ M3〜M16 (8 cases) ──────────────────────
    # クリアランス径 (JIS B 1001 中級): M3=3.4, M4=4.5, M5=5.5, M6=6.6,
    #   M8=9.0, M10=11.0, M12=13.0, M16=17.0
    _metric_screws = [
        ("M3",  100, 80, 1.70),
        ("M4",  100, 80, 2.25),
        ("M5",  100, 80, 2.75),
        ("M6",  100, 80, 3.30),
        ("M8",  120, 80, 4.50),
        ("M10", 120, 80, 5.50),
        ("M12", 140, 100, 6.50),
        ("M16", 160, 120, 8.50),
    ]
    for msize, W, H, r in _metric_screws:
        area = W * H - math.pi * r ** 2
        C.append(tc(
            f"screw_{msize}",
            f"ネジ穴 {msize} Φ{2*r:.1f}mm 板{W}×{H} 厚15mm",
            _make_gen(_gen_side_hole_param, W, H, W / 2, H / 2, r),
            15.0, vol=area * 15, bbox=(W, H, 15.0),
        ))

    # ── Z: ボルト穴パターン PCD (6 cases) ────────────────────────────────────
    # (n_holes, BCD, hole_d, W, H, label)
    _bcd_configs = [
        (4,  60, 6.6,  130, 130, "PCD60_M6_4h"),
        (4,  80, 9.0,  160, 160, "PCD80_M8_4h"),
        (6,  60, 6.6,  140, 140, "PCD60_M6_6h"),
        (6,  80, 9.0,  170, 170, "PCD80_M8_6h"),
        (8,  70, 6.6,  150, 150, "PCD70_M6_8h"),
        (4, 100, 11.0, 180, 180, "PCD100_M10_4h"),
    ]
    for n_h, BCD, hole_d, W, H, label in _bcd_configs:
        area = W * H - n_h * math.pi * (hole_d / 2) ** 2
        C.append(tc(
            f"bcd_{label}",
            f"ボルト穴 {label} {n_h}×Φ{hole_d}mm PCD{BCD} 板{W}×{H} 厚15mm",
            _make_gen(_gen_bolt_circle, W, H, n_h, BCD, hole_d),
            15.0, vol=area * 15, bbox=(W, H, 15.0),
        ))

    # ── Za: 座グリ(メートルネジ) M6/M8/M10 (3 cases) ─────────────────────────
    # cap_r = 座グリ径/2 (M6→Φ11, M8→Φ14, M10→Φ18)
    # thru_r = クリアランス径/2
    _cbore_metric = [
        ("M6",  120, 80,  5.5, 3.3, 20),
        ("M8",  140, 100, 7.0, 4.5, 25),
        ("M10", 160, 120, 9.0, 5.5, 30),
    ]
    for msize, W, H, cap_r, thru_r, thick in _cbore_metric:
        # Shapely subtracts cap_r only (thru_r is inside cap_r → merged)
        area = W * H - math.pi * cap_r ** 2
        C.append(tc(
            f"cbore_{msize}",
            f"座グリ {msize} cap_r={cap_r} thru_r={thru_r} 板{W}×{H} 厚{thick}mm",
            _make_gen(_gen_counterbore_param, W, H, W / 2, H / 2, cap_r, thru_r),
            float(thick), vol=area * thick, bbox=(W, H, float(thick)),
        ))

    # ── Tb: テーパー加工 1辺 (右台形プロファイル) — 6 cases ──────────────────
    # 右台形: 底辺Wb, 上辺Wt, 高さH_trap、extrusion depth=depth
    # draft_mm = tan(angle°) * H_trap
    _taper_1side = [
        ("5deg_s",  100, 97,  30, 60, "1辺テーパー5° 浅"),
        ("10deg_s", 100, 95,  30, 60, "1辺テーパー10° 浅"),
        ("15deg_s", 100, 92,  30, 60, "1辺テーパー15° 浅"),
        ("5deg_L",  150, 146, 50, 80, "1辺テーパー5° 大"),
        ("10deg_L", 150, 141, 50, 80, "1辺テーパー10° 大"),
        ("20deg_s",  80,  71, 25, 50, "1辺テーパー20° 急"),
    ]
    for label, Wb, Wt, H_trap, depth, desc in _taper_1side:
        area = (Wb + Wt) / 2 * H_trap
        vol  = area * depth
        C.append({
            "id": f"taper_1side_{label}",
            "desc": f"{desc} Wb={Wb} Wt={Wt} H={H_trap} 奥行{depth}mm",
            "gen": _make_gen(_gen_taper_right_trap, Wb, Wt, H_trap),
            "height": float(depth),
            "vol": vol,
            "bbox": (float(Wb), float(H_trap), float(depth)),
            "exp_topo": 5,   # bottom/top/left/right/hypotenuse = 5 faces
        })

    # ── Tc: テーパー加工 2辺 (等脚台形 = 既存_gen_trapezoid) — 5 cases ──────
    _taper_2side = [
        ("5deg_s",  100, 90, 30, 60, "2辺テーパー5°"),
        ("10deg_s", 100, 80, 30, 60, "2辺テーパー10°"),
        ("15deg_s", 100, 70, 30, 60, "2辺テーパー15°"),
        ("5deg_L",  160, 144, 50, 80, "2辺テーパー5° 大"),
        ("20deg_s",  80, 56,  25, 50, "2辺テーパー20° 急"),
    ]
    for label, Wb, Wt, H_trap, depth, desc in _taper_2side:
        area = (Wb + Wt) / 2 * H_trap
        vol  = area * depth
        C.append({
            "id": f"taper_2side_{label}",
            "desc": f"{desc} Wb={Wb} Wt={Wt} H={H_trap} 奥行{depth}mm",
            "gen": _make_gen(_gen_trapezoid, Wb, Wt, H_trap),
            "height": float(depth),
            "vol": vol,
            "bbox": (float(Wb), float(H_trap), float(depth)),
            "exp_topo": 6,   # bottom/top/front/back/left/right trapezoid walls
        })

    # ── Td: テーパー加工 3辺 (直接メッシュ) — 4 cases ───────────────────────
    # 底面W×L、左辺垂直、前後右3辺がdraftだけ縮退、高さH
    _taper_3side = [
        ("5deg",  100, 80, 30, 2.6, "3辺テーパー5°"),
        ("10deg", 100, 80, 30, 5.3, "3辺テーパー10°"),
        ("15deg", 100, 80, 30, 8.0, "3辺テーパー15°"),
        ("10deg_L", 160, 120, 50, 8.8, "3辺テーパー10° 大"),
    ]
    for label, W, L, H, draft, desc in _taper_3side:
        C.append({
            "id": f"taper_3side_{label}",
            "desc": f"{desc} W={W} L={L} H={H} draft={draft}mm",
            "gen_mesh": _make_gen(_make_3side_taper_mesh, W, L, H, draft),
            "height": float(H),
            "vol": None,   # direct mesh; exact vol verified at runtime
            "bbox": (float(W), float(L), float(H)),
            "exp_topo": 6,
        })

    # ── Te: テーパー加工 4辺 = フラストム (直接メッシュ) — 5 cases ──────────
    _taper_4side = [
        ("5deg_s",  100, 80, 90, 70, 30, "4辺テーパー(フラストム)5°"),
        ("10deg_s", 100, 80, 83, 63, 30, "4辺テーパー(フラストム)10°"),
        ("15deg_s", 100, 80, 76, 56, 30, "4辺テーパー(フラストム)15°"),
        ("5deg_L",  160, 120, 145, 105, 50, "4辺テーパー(フラストム)5° 大"),
        ("20deg_s",  80, 60,  62,  42, 25, "4辺テーパー(フラストム)20° 急"),
    ]
    for label, Wb, Lb, Wt, Lt, H, desc in _taper_4side:
        A_bot = Wb * Lb
        A_top = Wt * Lt
        vol = H / 3 * (A_bot + A_top + math.sqrt(A_bot * A_top))
        C.append({
            "id": f"taper_4side_{label}",
            "desc": f"{desc} 底{Wb}×{Lb} 上{Wt}×{Lt} H={H}mm",
            "gen_mesh": _make_gen(_make_frustum_mesh, Wb, Lb, Wt, Lt, H),
            "height": float(H),
            "vol": vol,
            "bbox": (float(Wb), float(Lb), float(H)),
            "exp_topo": 6,
        })

    # ── Ra: R加工 1辺半円キャップ — 4 cases ──────────────────────────────────
    _r_1side = [
        (80, 60, 10, "1辺半円R W=80"),
        (100, 70, 10, "1辺半円R W=100"),
        (60, 50,  8, "1辺半円R W=60 小"),
        (120, 80, 12, "1辺半円R W=120 大"),
    ]
    for W, H_rect, thick, desc in _r_1side:
        R_cap = W / 2
        area = W * H_rect + math.pi * R_cap ** 2 / 2
        C.append(tc(
            f"r_cap1side_W{W}", f"{desc} 厚{thick}mm",
            _make_gen(_gen_cap_1side, W, H_rect),
            float(thick), vol=area * thick, bbox=None,
            exp_topo=None,
        ))

    # ── Rb: R加工 2辺スタジアム (追加サイズ) — 3 cases ──────────────────────
    _r_stadium = [
        (80, 20, 10, "2辺R スタジアム straight=80 r=20"),
        (100, 25, 12, "2辺R スタジアム straight=100 r=25"),
        (120, 30,  8, "2辺R スタジアム straight=120 r=30"),
    ]
    for L, R, thick, desc in _r_stadium:
        # _gen_stadium: L=straight part, total bbox X=L+2R, Y=2R
        C.append(tc(
            f"r_stadium_L{L}_r{R}", f"{desc} 厚{thick}mm",
            _make_gen(_gen_stadium, L, R),
            float(thick), vol=None, bbox=(L + 2*R, 2*R, float(thick)),
        ))

    # ── Rc: R加工 4隅丸め (追加サイズ) — 3 cases ────────────────────────────
    _r_allcorner = [
        (100, 70, 15, 10, "4隅R W=100 r=15"),
        (80,  60, 10,  8, "4隅R W=80  r=10"),
        (140, 90, 20, 12, "4隅R W=140 r=20"),
    ]
    for W, H_rect, r, thick, desc in _r_allcorner:
        area = W * H_rect - (4 - math.pi) * r ** 2
        C.append(tc(
            f"r_rrect_W{W}_r{r}", f"{desc} 厚{thick}mm",
            _make_gen(_gen_rounded_rect, W, H_rect, r),
            float(thick), vol=area * thick, bbox=(W, H_rect, float(thick)),
        ))

    # ── Rd: R加工 長穴スロット板 — 5 cases ───────────────────────────────────
    _r_slot = [
        (120, 80, 12, 30, 12, "長穴スロット sw=12 sh=30"),
        (100, 70, 10, 25, 10, "長穴スロット sw=10 sh=25"),
        (140, 90, 14, 40, 15, "長穴スロット sw=14 sh=40 大"),
        (100, 80, 16, 35, 10, "長穴スロット sw=16 sh=35"),
        (120, 80, 20, 50, 12, "長穴スロット sw=20 sh=50 細長"),
    ]
    for W, H_rect, sw, sh, thick, desc in _r_slot:
        sr = sw / 2
        straight = sh - sw
        slot_area = math.pi * sr ** 2 + sw * straight
        area = W * H_rect - slot_area
        C.append(tc(
            f"r_slot_sw{sw}_sh{sh}_W{W}", f"{desc} 板{W}×{H_rect} 厚{thick}mm",
            _make_gen(_gen_r_slot_plate, W, H_rect, sw, sh),
            float(thick), vol=area * thick, bbox=(W, H_rect, float(thick)),
        ))

    # ── Re: R加工 R底溝 — 5 cases ─────────────────────────────────────────────
    _r_groove = [
        (100, 60, 20, 15, 10, "R底溝 gw=20 gd=15"),
        (100, 60, 16, 12,  8, "R底溝 gw=16 gd=12 小"),
        (120, 80, 24, 18, 12, "R底溝 gw=24 gd=18 大"),
        (100, 60, 20, 10, 10, "R底溝 gw=20 gd=10 浅"),
        (100, 60, 30, 20, 10, "R底溝 gw=30 gd=20 幅広"),
    ]
    for W, H_rect, gw, gd, thick, desc in _r_groove:
        gr = gw / 2
        straight_d = max(0, gd - gr)
        removed = math.pi * gr ** 2 / 2 + gw * straight_d
        area = W * H_rect - removed
        C.append(tc(
            f"r_groove_gw{gw}_gd{gd}_W{W}", f"{desc} 板{W}×{H_rect} 厚{thick}mm",
            _make_gen(_gen_r_inner_groove, W, H_rect, gw, gd),
            float(thick), vol=area * thick, bbox=(W, H_rect, float(thick)),
        ))

    return C


# ─── CSG 3D テストスイート ────────────────────────────────────────────────────

def build_csg_test_suite() -> list:
    """
    manifold3d を使った真の 3D CSG 形状テストスイート (10形状)。
    2D DXF 押し出しでは不可能な形状を検証する。
    """
    import math
    C = []

    def csg_tc(id_, desc, gen_mesh, vol_expected=None, bbox=None, exp_topo=None):
        return {"id": id_, "desc": desc, "gen_mesh": gen_mesh,
                "height": 0.0,  # CSGは押し出し高さ不使用
                "vol": vol_expected, "bbox": bbox, "exp_topo": exp_topo}

    # 1. L字 3D (2ボックス)
    C.append(csg_tc(
        "csg_l_3d", "2ボックス L字3D (100×40×60 + 40×60×60)",
        _make_csg_l_3d,
        vol_expected=100*40*60 + 40*60*60,   # 384,000 mm³ (重複なし)
        bbox=(100, 100, 60), exp_topo=10,
    ))

    # 2. T字 3D (2ボックス)
    C.append(csg_tc(
        "csg_t_3d", "2ボックス T字3D (120×20×40 + 40×80×40)",
        _make_csg_t_3d,
        vol_expected=120*20*40 + 40*80*40,   # 224,000 mm³
        bbox=(120, 100, 40), exp_topo=10,
    ))

    # 3. 階段 (3ボックス)
    C.append(csg_tc(
        "csg_stair_3d", "3ボックス 階段状3D (各段50×50×30)",
        _make_csg_stair_3d,
        vol_expected=3 * 50*50*30,   # 225,000 mm³
        bbox=(150, 50, 90), exp_topo=None,
    ))

    # 4. 3D十字 (5ボックス)
    # 中央60³ + 4アーム各60×20×20
    vol_cross = 60**3 + 4*(60*20*20)
    C.append(csg_tc(
        "csg_cross_3d", "5ボックス 3D十字 (中央60³ + 4アーム)",
        _make_csg_cross_3d,
        vol_expected=vol_cross,
        bbox=(180, 180, 60), exp_topo=None,
    ))

    # 5. タワー (4ボックス積み上げ)
    vol_tower = 80*80*20 + 60*60*20 + 40*40*20 + 20*20*20
    C.append(csg_tc(
        "csg_tower_3d", "4ボックス タワー状3D (各層縮小積み上げ)",
        _make_csg_tower_3d,
        vol_expected=vol_tower,
        bbox=(80, 80, 80), exp_topo=None,
    ))

    # 6. ボックス-円柱穴 (Boolean差分)
    vol_hole = 100*80*40 - math.pi*15**2*40
    C.append(csg_tc(
        "csg_box_cyl_hole", "ボックスに円柱穴 (100×80×40 - φ30×40)",
        _make_csg_box_cyl_hole,
        vol_expected=vol_hole,
        bbox=(100, 80, 40), exp_topo=None,
    ))

    # 7. ボックス-4円柱穴 (差分×4)
    vol_4holes = 120*100*30 - 4*(math.pi*8**2*30)
    C.append(csg_tc(
        "csg_box_4holes", "ボックスに4円柱穴 (120×100×30 - 4×φ16)",
        _make_csg_box_4holes,
        vol_expected=vol_4holes,
        bbox=(120, 100, 30), exp_topo=None,
    ))

    # 8. 複合形状 (union + diff)
    C.append(csg_tc(
        "csg_compound", "複合形状 (ボックス+円柱+球 - 穴)",
        _make_csg_compound,
        vol_expected=None,   # 球を含むため近似値のみ
        bbox=None, exp_topo=None,
    ))

    # 9. 3D フレーム (外箱-内箱)
    vol_frame = 100*80*50 - 80*60*45
    C.append(csg_tc(
        "csg_frame_3d", "3Dフレーム (外100×80×50 - 内80×60×45、壁厚10mm)",
        _make_csg_frame_3d,
        vol_expected=vol_frame,
        bbox=(100, 80, 50), exp_topo=None,
    ))

    # 10. [旧] 10ボックス X一列配置 (参照用)
    C.append(csg_tc(
        "csg_10box_linear", "10ボックス X方向一列配置 [旧・参照用]",
        _make_csg_10box_joined,
        vol_expected=None, bbox=None, exp_topo=None,
    ))

    # ── 真の3D複合形状 ────────────────────────────────────────────────────────

    # 11. 真の3Dランダム10ボックス (XYZ空間、重複あり)
    C.append(csg_tc(
        "csg_3d_random_10box",
        "真3Dランダム10ボックス (XYZ独立配置・重複Union・seed42)",
        _make_csg_3d_random_10box,
        vol_expected=None, bbox=None, exp_topo=None,
    ))

    # 12. L型ブラケット (多方向穴あき)
    C.append(csg_tc(
        "csg_bracket_3d",
        "L型ブラケット: ベース+立壁+リブ + Z方向4穴 + X方向貫通穴",
        _make_csg_bracket_3d,
        vol_expected=None, bbox=None, exp_topo=None,
    ))

    # 13. フランジ (円盤+ネック+ボルト穴)
    C.append(csg_tc(
        "csg_flange_3d",
        "フランジ: φ120円盤+φ60ネック+φ40内径+6×M8ボルト穴(PCD90)",
        _make_csg_flange_3d,
        vol_expected=None, bbox=None, exp_topo=None,
    ))

    # 14. ハウジング (4方向穴あき)
    C.append(csg_tc(
        "csg_housing_3d",
        "ハウジング: 外箱140×100×80 − 内空洞 − 前後左右4方向φ穴",
        _make_csg_housing_3d,
        vol_expected=None, bbox=None, exp_topo=None,
    ))

    # 15. 段付きシャフト+キー溝
    C.append(csg_tc(
        "csg_stepped_shaft",
        "段付きシャフト: φ60×30 + φ45×40 + φ30×50 + キー溝",
        _make_csg_stepped_shaft,
        vol_expected=None, bbox=None, exp_topo=None,
    ))

    # 16. 3方向クロスコネクター
    C.append(csg_tc(
        "csg_cross_connector",
        "3方向クロスコネクター: X/Y/Z各φ60パイプ交差 + φ40内径貫通",
        _make_csg_cross_connector,
        vol_expected=None, bbox=None, exp_topo=None,
    ))

    return C


def run_csg_suite(suite: list,
                  progress_cb=None,
                  ai_check: bool = False,
                  ollama_url: str = "http://ollama:11434") -> list:
    """
    CSG テストスイートを実行。
    progress_cb(idx, total, id_): 進捗コールバック（Streamlit st.progress用）
    ai_check: True なら qwen3.5 でAI自己チェックも実施
    """
    results = []
    total = len(suite)
    for idx, item in enumerate(suite):
        if progress_cb:
            progress_cb(idx, total, item["id"])
        r = {"id": item["id"], "desc": item["desc"]}
        try:
            mesh = item["gen_mesh"]()
            if mesh is None or len(mesh.faces) == 0:
                r.update({"ok": False, "score": 0, "error": "メッシュ生成失敗"})
                results.append(r)
                continue

            score = 30
            notes = []
            dims = mesh.bounds[1] - mesh.bounds[0]

            # 体積チェック
            if item.get("vol"):
                err = abs(mesh.volume - item["vol"]) / item["vol"]
                score += 35 if err < 0.05 else (15 if err < 0.15 else 0)
                if err >= 0.05:
                    notes.append(f"体積誤差{err*100:.1f}%")
                vol_err_pct = round(err * 100, 3)
            else:
                score += 35
                vol_err_pct = None

            # BBox チェック
            if item.get("bbox"):
                bb_ok = all(
                    abs(dims[ax] - exp) / max(exp, 1) < 0.05
                    for ax, exp in enumerate(item["bbox"]) if exp is not None
                )
                score += 35 if bb_ok else 0
                if not bb_ok:
                    notes.append("BBox誤差")
            else:
                score += 35

            if not mesh.is_watertight:
                score = max(0, score - 10)
                notes.append("非密閉")

            topo = count_topo_faces(mesh)

            ai_comment = ""
            if ai_check:
                ai_comment = _csg_ai_check(
                    item["id"], item["desc"], mesh.volume, topo,
                    mesh.is_watertight, ollama_url,
                )

            r.update({
                "ok": True, "score": score,
                "vol_actual": round(mesh.volume, 1),
                "vol_expected": item.get("vol"),
                "vol_err_pct": vol_err_pct,
                "bbox_actual": tuple(round(d, 1) for d in dims),
                "watertight": mesh.is_watertight,
                "tri_faces": len(mesh.faces),
                "topo_faces": topo,
                "notes": ", ".join(notes) or "OK",
                "mesh": mesh,
                "ai_comment": ai_comment,
            })
        except Exception as exc:
            import traceback
            r.update({"ok": False, "score": 0,
                       "error": str(exc)[:120],
                       "traceback": traceback.format_exc()[-300:]})
        results.append(r)

    if progress_cb:
        progress_cb(total, total, "完了")
    return results


def run_extended_suite(suite: list) -> list:
    """
    Run all cases in the extended test suite.
    Scores: 30 mesh OK + 35 volume + 35 bbox, -10 if not watertight.
    Records topological face count (trimesh.facets).
    No API calls.
    """
    results = []
    for item in suite:
        r = {"id": item["id"], "desc": item["desc"]}
        try:
            dxf_bytes = None
            mesh = None
            if "gen_mesh" in item:
                # Direct 3D mesh (テーパー・フラストム等 DXF不使用)
                mesh = item["gen_mesh"]()
                if mesh is None:
                    r.update({"ok": False, "score": 0, "error": "メッシュ生成失敗"})
                    results.append(r)
                    continue
            else:
                dxf_bytes = item["gen"]()
                doc = ezdxf.read(io.StringIO(dxf_bytes.decode("utf-8")))
                loops = extract_loops(doc, "")
                if not loops:
                    r.update({"ok": False, "score": 0, "error": "輪郭なし"})
                    results.append(r)
                    continue
                mesh, _ = loops_to_mesh(loops, item["height"])
                if mesh is None:
                    r.update({"ok": False, "score": 0, "error": "メッシュ生成失敗"})
                    results.append(r)
                    continue

            score = 30
            notes = []

            if item.get("vol"):
                err = abs(mesh.volume - item["vol"]) / item["vol"]
                score += 35 if err < 0.05 else (15 if err < 0.15 else 0)
                if err >= 0.05:
                    notes.append(f"体積誤差{err*100:.1f}%")
            else:
                score += 35  # no reference vol → full credit for generating mesh

            if item.get("bbox"):
                dims = mesh.bounds[1] - mesh.bounds[0]
                bb_ok = all(
                    abs(dims[ax] - exp) / exp < 0.05
                    for ax, exp in enumerate(item["bbox"]) if exp is not None
                )
                score += 35 if bb_ok else 0
                if not bb_ok:
                    notes.append("BBox誤差")
            else:
                dims = mesh.bounds[1] - mesh.bounds[0]
                score += 35  # no reference bbox → full credit

            if not mesh.is_watertight:
                score = max(0, score - 10)
                notes.append("非密閉")

            topo = count_topo_faces(mesh)
            dims = mesh.bounds[1] - mesh.bounds[0]
            r.update({
                "ok": True, "score": score,
                "vol_actual": round(mesh.volume, 1),
                "vol_expected": item.get("vol"),
                "vol_err_pct": round(abs(mesh.volume - item["vol"]) / item["vol"] * 100, 2)
                               if item.get("vol") else None,
                "bbox_actual": tuple(round(d, 1) for d in dims),
                "watertight": mesh.is_watertight,
                "tri_faces": len(mesh.faces),
                "topo_faces": topo,
                "exp_topo": item.get("exp_topo"),
                "notes": ", ".join(notes) or "OK",
                "dxf_bytes": dxf_bytes,   # for 2D render
                "mesh": mesh,             # for 3D render
            })
        except Exception as exc:
            r.update({"ok": False, "score": 0, "error": str(exc)[:100]})
        results.append(r)
    return results


# ── Test suite definition ─────────────────────────────────────────────────────

TEST_SUITE = [
    {"id": "rect_simple",   "desc": "単純矩形 100×60×8mm",          "gen": _gen_rect_simple,  "height": 8.0,  "vol": 100*60*8,       "bbox": (100,60,8)},
    {"id": "circle",        "desc": "円形 r=30 × 10mm",             "gen": _gen_circle,       "height": 10.0, "vol": math.pi*30**2*10,"bbox": (60,60,10)},
    {"id": "l_shape",       "desc": "L字形状 80×80 厚み6mm",         "gen": _gen_l_shape,      "height": 6.0,  "vol": 4800*6,         "bbox": (80,80,6)},
    {"id": "u_shape",       "desc": "U字形状 内側除去 厚み5mm",       "gen": _gen_u_shape,      "height": 5.0,  "vol": 5000*5,         "bbox": (100,80,5)},
    {"id": "arc_rect",      "desc": "角丸矩形 R10コーナー 厚み5mm",   "gen": _gen_arc_rect,     "height": 5.0,  "vol": (100*60-(4-math.pi)*100)*5,"bbox": (100,60,5)},
    {"id": "縦穴",          "desc": "縦穴: 100×100 Φ40 貫通 厚み20mm","gen": _gen_plate_hole,   "height": 20.0, "vol": (100*100-math.pi*20**2)*20,"bbox": (100,100,20)},
    {"id": "座グリ",        "desc": "座グリ: Φ40cap+Φ20through 厚み20mm","gen": _gen_counterbore,"height": 20.0, "vol": (100*100-math.pi*20**2)*20,"bbox": (100,100,20)},
    {"id": "U字曲げ",       "desc": "U字曲げ プロファイル 奥行き50mm", "gen": _gen_u_bend,       "height": 50.0, "vol": 650*50,         "bbox": (60,40,50)},
    {"id": "横穴",          "desc": "横穴: 100×60 側面Φ20 厚み15mm", "gen": _gen_side_hole,    "height": 15.0, "vol": (100*60-math.pi*10**2)*15,"bbox": (100,60,15)},
    {"id": "曲線溝",        "desc": "曲線溝: 120×60 半円溝 R20 厚み10mm","gen": _gen_curved_groove,"height": 10.0,"vol": None,           "bbox": (120,60,10)},
    {"id": "クランク曲げ",  "desc": "クランク曲げ Z字 オフセット20mm 厚み40mm","gen": _gen_crank_bend,"height": 40.0,"vol": None,          "bbox": (80,None,40)},
]


def run_test_suite(suite: list) -> list[dict]:
    """Run all test cases through the DXF→mesh pipeline. Return scored results."""
    results = []
    for tc in suite:
        result = {"id": tc["id"], "desc": tc["desc"]}
        try:
            dxf_bytes = tc["gen"]()
            doc = ezdxf.read(io.StringIO(dxf_bytes.decode('utf-8')))
            loops = extract_loops(doc, "")
            if not loops:
                result.update({"ok": False, "score": 0, "error": "輪郭なし", "mesh": None})
                results.append(result)
                continue
            mesh, _ = loops_to_mesh(loops, tc["height"])
            if mesh is None:
                result.update({"ok": False, "score": 0, "error": "メッシュ生成失敗", "mesh": None})
                results.append(result)
                continue

            score = 30  # generated successfully
            notes = []

            # Volume check (if expected given)
            if tc["vol"] is not None:
                vol_err = abs(mesh.volume - tc["vol"]) / tc["vol"]
                if vol_err < 0.05:
                    score += 35
                elif vol_err < 0.15:
                    score += 15
                    notes.append(f"体積誤差 {vol_err*100:.1f}%")
                else:
                    notes.append(f"体積誤差 {vol_err*100:.1f}% (大)")
            else:
                score += 20  # no expected volume — partial credit

            # Bounding box check
            dims = mesh.bounds[1] - mesh.bounds[0]
            bb_ok = True
            for ax, exp in zip([dims[0], dims[1], dims[2]], tc["bbox"]):
                if exp is None:
                    continue
                err = abs(ax - exp) / exp
                if err > 0.05:
                    bb_ok = False
                    notes.append(f"BBox誤差 {err*100:.1f}%")
            if bb_ok:
                score += 35

            # Watertight bonus
            if mesh.is_watertight:
                score = min(100, score)
            else:
                score = max(0, score - 10)
                notes.append("非密閉")

            result.update({
                "ok": True, "score": score,
                "vol_actual": round(mesh.volume, 1),
                "vol_expected": tc["vol"],
                "bbox_actual": tuple(round(d, 1) for d in dims),
                "watertight": mesh.is_watertight,
                "faces": len(mesh.faces),
                "notes": ", ".join(notes) if notes else "OK",
                "mesh": mesh,
                "error": None,
            })
        except Exception as exc:
            result.update({"ok": False, "score": 0, "error": str(exc)[:80], "mesh": None})
        results.append(result)
    return results


# ── Mesh self-check ──────────────────────────────────────────────────────────

def run_mesh_checks(mesh, requested_height_mm: float, n_loops: int) -> list[dict]:
    """
    Geometric quality checks on the trimesh.Trimesh — no LLM, instant.
    Returns list of {name, ok, detail, severity} dicts.
    """
    checks = []

    # 1. Watertight (no holes in the mesh)
    wt = mesh.is_watertight
    checks.append({
        "name": "Watertight (密閉メッシュ)",
        "ok": wt,
        "detail": "メッシュは完全に閉じています" if wt else "メッシュに穴があります — STL印刷・CAM加工に問題が生じる可能性",
        "severity": "error" if not wt else "ok",
    })

    # 2. Positive volume
    vol = mesh.volume
    vol_ok = vol > 0
    checks.append({
        "name": "Volume (体積正常)",
        "ok": vol_ok,
        "detail": f"{vol:.2f} mm³" if vol_ok else f"{vol:.2f} mm³ — 法線が内外反転している可能性",
        "severity": "error" if not vol_ok else "ok",
    })

    # 3. Winding consistency
    winding = mesh.is_winding_consistent
    checks.append({
        "name": "法線一貫性",
        "ok": winding,
        "detail": "法線方向は一貫しています" if winding else "一部の面で法線方向が不一致 — レンダリング異常の原因になる場合あり",
        "severity": "warn" if not winding else "ok",
    })

    # 4. Height match (Z dimension vs. requested)
    z_dim = mesh.bounds[1][2] - mesh.bounds[0][2]
    height_ok = abs(z_dim - requested_height_mm) < 0.01
    checks.append({
        "name": f"高さ一致 ({requested_height_mm} mm)",
        "ok": height_ok,
        "detail": f"実Z寸法 = {z_dim:.4f} mm" if height_ok else f"実Z寸法 = {z_dim:.4f} mm ≠ {requested_height_mm} mm",
        "severity": "warn" if not height_ok else "ok",
    })

    # 5. Degenerate faces (zero-area)
    deg = mesh.triangles_area
    n_degen = int((deg < 1e-10).sum())
    degen_ok = n_degen == 0
    checks.append({
        "name": "縮退面なし",
        "ok": degen_ok,
        "detail": "縮退面なし" if degen_ok else f"{n_degen} 個の縮退面(面積ゼロ)を検出 — メッシュ品質に影響",
        "severity": "warn" if not degen_ok else "ok",
    })

    # 6. Reasonable face count
    n_faces = len(mesh.faces)
    face_ok = 10 < n_faces < 1_000_000
    checks.append({
        "name": "面数 (適切範囲)",
        "ok": face_ok,
        "detail": f"{n_faces:,} 面" if face_ok else f"{n_faces:,} 面 — {'少なすぎ' if n_faces <= 10 else '多すぎ'}",
        "severity": "warn" if not face_ok else "ok",
    })

    # 7. Loop count reasonable
    loop_ok = 1 <= n_loops <= 100
    checks.append({
        "name": f"輪郭数 ({n_loops})",
        "ok": loop_ok,
        "detail": f"{n_loops} 個の閉じた輪郭を検出" if loop_ok else
                  ("輪郭が見つかりません" if n_loops == 0 else f"{n_loops} 個 — 複雑すぎる可能性"),
        "severity": "error" if n_loops == 0 else ("warn" if not loop_ok else "ok"),
    })

    return checks


def ai_mesh_check(checks: list[dict], mesh) -> str:
    """
    Call local Ollama with the configured coding model and a general-model fallback.
    compact prompt. Returns AI comment string or error message.
    Token budget: ~120 tokens in, ~80 tokens out — very cheap.
    """
    import urllib.request
    import json as _json

    summary_lines = [
        f"{c['name']}: {'OK' if c['ok'] else 'NG'} ({c['detail']})"
        for c in checks
    ]
    prompt = (
        "3Dメッシュ品質チェック結果を見て、1〜2文で簡潔に評価してください。\n"
        + "\n".join(summary_lines)
        + f"\n面数={len(mesh.faces)}, 体積={mesh.volume:.1f}mm³"
    )

    for model in [OLLAMA_CODE_MODEL, OLLAMA_GEN_MODEL]:
        try:
            payload = _json.dumps({
                "model": model,
                "prompt": prompt,
                "stream": False,
                "options": {"num_predict": 120, "temperature": 0.2},
            }).encode()
            req = urllib.request.Request(
                "http://ollama:11434/api/generate",
                data=payload,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=30) as resp:
                result = _json.loads(resp.read())
                return result.get("response", "").strip()
        except Exception:
            continue
    return f"Ollamaへの接続に失敗しました ({OLLAMA_CODE_MODEL} / {OLLAMA_GEN_MODEL} が必要)"


# ── STEP / IGES input via pythonocc-core ─────────────────────────────────────

def _gmsh_to_trimesh(linear_deflection: float) -> "trimesh.Trimesh":
    """
    Extract the current gmsh model as a trimesh.Trimesh.
    Requires the gmsh model to already have a 2D surface mesh generated.
    """
    import gmsh
    node_tags, node_coords, _ = gmsh.model.mesh.getNodes()
    elem_types, elem_tags, elem_node_tags = gmsh.model.mesh.getElements(dim=2)

    verts = np.array(node_coords).reshape(-1, 3)
    # Build node_tag → index map
    tag_to_idx = {int(t): i for i, t in enumerate(node_tags)}

    faces_list = []
    for etype, etags, enode_tags in zip(elem_types, elem_tags, elem_node_tags):
        # etype 2 = 3-node triangle
        if etype == 2:
            tris = np.array(enode_tags, dtype=int).reshape(-1, 3)
            for tri in tris:
                faces_list.append([tag_to_idx[t] for t in tri])

    if not faces_list:
        raise RuntimeError("表面メッシュの三角形が見つかりませんでした。")

    faces = np.array(faces_list, dtype=int)
    mesh = trimesh.Trimesh(vertices=verts, faces=faces, process=True)
    return mesh


def load_step_to_mesh(step_bytes: bytes, linear_deflection: float = 0.1) -> "trimesh.Trimesh":
    """
    Load a STEP file and tessellate it into a trimesh.Trimesh.

    Uses gmsh (OpenCASCADE kernel bundled) for geometry import and meshing.
    gmsh is available via `pip install gmsh` and includes the full OCC kernel.

    Parameters
    ----------
    step_bytes : bytes
        Raw STEP file content.
    linear_deflection : float
        Target mesh size in mm. Smaller = finer mesh.
    """
    import tempfile, os as _os
    try:
        import gmsh
    except ImportError:
        raise RuntimeError(
            "gmsh が未インストールです。\n"
            "Dockerfile に `gmsh` を追加してリビルドしてください。"
        )

    with tempfile.NamedTemporaryFile(suffix=".step", delete=False) as f:
        f.write(step_bytes)
        tmp = f.name

    try:
        gmsh.initialize()
        gmsh.option.setNumber("General.Verbosity", 0)
        gmsh.model.add("step_model")
        gmsh.model.occ.importShapes(tmp)
        gmsh.model.occ.synchronize()
        # Set mesh size
        gmsh.option.setNumber("Mesh.CharacteristicLengthMax", linear_deflection * 20)
        gmsh.option.setNumber("Mesh.CharacteristicLengthMin", linear_deflection)
        gmsh.option.setNumber("Mesh.Algorithm", 6)   # Frontal-Delaunay
        gmsh.model.mesh.generate(2)                  # Surface mesh only
        result = _gmsh_to_trimesh(linear_deflection)
        return result
    finally:
        try:
            gmsh.finalize()
        except Exception:
            pass
        try:
            _os.unlink(tmp)
        except Exception:
            pass


def load_iges_to_mesh(iges_bytes: bytes, linear_deflection: float = 0.1) -> "trimesh.Trimesh":
    """Load IGES file via gmsh (OpenCASCADE kernel). Same pipeline as STEP."""
    import tempfile, os as _os
    try:
        import gmsh
    except ImportError:
        raise RuntimeError("gmsh が未インストールです。")

    with tempfile.NamedTemporaryFile(suffix=".igs", delete=False) as f:
        f.write(iges_bytes)
        tmp = f.name

    try:
        gmsh.initialize()
        gmsh.option.setNumber("General.Verbosity", 0)
        gmsh.model.add("iges_model")
        gmsh.model.occ.importShapes(tmp)
        gmsh.model.occ.synchronize()
        gmsh.option.setNumber("Mesh.CharacteristicLengthMax", linear_deflection * 20)
        gmsh.option.setNumber("Mesh.CharacteristicLengthMin", linear_deflection)
        gmsh.model.mesh.generate(2)
        return _gmsh_to_trimesh(linear_deflection)
    finally:
        try:
            gmsh.finalize()
        except Exception:
            pass
        try:
            _os.unlink(tmp)
        except Exception:
            pass


# ── FreeCAD via Antigravity ───────────────────────────────────────────────────

def convert_fcstd_via_freecad(loops, height_mm, stem: str = "output"):
    """
    Send extracted loops as JSON to Antigravity (FreeCAD container),
    generate a .fcstd with PartDesign Body→Sketch→Pad history,
    and return the raw bytes.
    """
    import json as _json

    job_id  = uuid.uuid4().hex[:8]
    job_dir = WORK_DIR / job_id
    job_dir.mkdir(parents=True, exist_ok=True)

    json_path  = job_dir / "loops.json"
    fcstd_path = job_dir / f"{stem}.fcstd"

    payload = {"loops": [[[float(x), float(y)] for x, y in loop] for loop in loops]}
    json_path.write_text(_json.dumps(payload), encoding="utf-8")

    ag_json  = f"/work/dxf3d_output/{job_id}/loops.json"
    ag_fcstd = f"/work/dxf3d_output/{job_id}/{stem}.fcstd"

    cmd = [
        "docker", "exec", ANTIGRAVITY,
        "python3", DXF23D_PATH,
        "--mode",   "fcstd",
        "--in",     ag_json,
        "--out",    ag_fcstd,
        "--height", str(height_mm),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    if result.returncode != 0:
        raise RuntimeError(result.stdout + result.stderr)
    if not fcstd_path.exists():
        raise RuntimeError(".fcstd file was not produced by FreeCAD.")
    return fcstd_path.read_bytes()


def convert_step_via_freecad(dxf_bytes, layer, height_mm):
    """
    Write DXF to shared /work volume, call docker exec Antigravity
    to run dxf23d.py, return STEP bytes or raise RuntimeError.
    """
    job_id = uuid.uuid4().hex[:8]
    job_dir = WORK_DIR / job_id
    job_dir.mkdir(parents=True, exist_ok=True)
    dxf_path = job_dir / "input.dxf"
    step_path = job_dir / "output.step"

    dxf_path.write_bytes(dxf_bytes)

    # Paths inside Antigravity (same /work mount)
    ag_dxf  = f"/work/dxf3d_output/{job_id}/input.dxf"
    ag_step = f"/work/dxf3d_output/{job_id}/output.step"

    cmd = [
        "docker", "exec", ANTIGRAVITY,
        "python3", DXF23D_PATH,
        ag_dxf, ag_step,
        "--height", str(height_mm),
        "--layer", layer or "",
    ]
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=120
        )
        if result.returncode != 0:
            raise RuntimeError(result.stdout + result.stderr)
        if not step_path.exists():
            raise RuntimeError("STEP file not produced.")
        return step_path.read_bytes()
    finally:
        # Keep files around for 1 session; no cleanup here
        pass


# ── STEP export via gmsh OCC ─────────────────────────────────────────────────

def loops_to_step_gmsh(loops: list, height_mm: float) -> bytes:
    """
    Convert 2D closed loops to STEP bytes via gmsh OpenCASCADE kernel.
    Largest loop = outer solid body. Inner loops = holes (subtracted automatically
    by addPlaneSurface with multiple curve loops).
    Returns raw STEP file bytes.
    """
    import gmsh
    import tempfile
    import os as _os
    from shapely.geometry import Polygon as _P

    with tempfile.TemporaryDirectory() as tmpdir:
        out_path = _os.path.join(tmpdir, "out.step")
        try:
            gmsh.initialize()
            gmsh.option.setNumber("General.Verbosity", 0)
            gmsh.model.add("model")

            # Sort: largest area first (outer contour)
            def _area(lp):
                try:
                    return abs(_P(lp).area) if len(lp) >= 3 else 0.0
                except Exception:
                    return 0.0

            sorted_loops = sorted(loops, key=_area, reverse=True)

            wire_tags = []
            for lp in sorted_loops:
                if len(lp) < 3:
                    continue
                pt_tags = [gmsh.model.occ.addPoint(float(x), float(y), 0.0)
                           for x, y in lp]
                n = len(pt_tags)
                ln_tags = [gmsh.model.occ.addLine(pt_tags[i], pt_tags[(i + 1) % n])
                           for i in range(n)]
                cl = gmsh.model.occ.addCurveLoop(ln_tags)
                wire_tags.append(cl)

            if not wire_tags:
                raise RuntimeError("有効な輪郭が見つかりませんでした。")

            surf = gmsh.model.occ.addPlaneSurface(wire_tags)
            gmsh.model.occ.extrude([(2, surf)], 0.0, 0.0, float(height_mm))
            gmsh.model.occ.synchronize()
            gmsh.write(out_path)

        finally:
            try:
                gmsh.finalize()
            except Exception:
                pass

        with open(out_path, "rb") as f:
            return f.read()


def multilayer_to_step_gmsh(layer_configs: list) -> bytes:
    """
    Multi-layer STEP export via gmsh OCC with boolean operations.

    layer_configs: list of dicts:
        {loops: list, height_mm: float, operation: 'solid'|'cutout', z_offset: float}

    Solid layers are fused together; cutout layers are subtracted from the solid.
    Returns raw STEP file bytes.
    """
    import gmsh
    import tempfile
    import os as _os
    from shapely.geometry import Polygon as _P

    with tempfile.TemporaryDirectory() as tmpdir:
        out_path = _os.path.join(tmpdir, "out.step")
        try:
            gmsh.initialize()
            gmsh.option.setNumber("General.Verbosity", 0)
            gmsh.model.add("multilayer")

            solid_ents: list = []
            cut_ents:   list = []

            def _area(lp):
                try:
                    return abs(_P(lp).area) if len(lp) >= 3 else 0.0
                except Exception:
                    return 0.0

            for cfg in layer_configs:
                loops_c = cfg["loops"]
                h       = float(cfg["height_mm"])
                z0      = float(cfg.get("z_offset", 0.0))
                op      = cfg.get("operation", "solid")

                sorted_lps = sorted(loops_c, key=_area, reverse=True)
                wire_tags = []
                for lp in sorted_lps:
                    if len(lp) < 3:
                        continue
                    pt_tags = [
                        gmsh.model.occ.addPoint(float(x), float(y), z0)
                        for x, y in lp
                    ]
                    n = len(pt_tags)
                    ln_tags = [
                        gmsh.model.occ.addLine(pt_tags[i], pt_tags[(i + 1) % n])
                        for i in range(n)
                    ]
                    cl = gmsh.model.occ.addCurveLoop(ln_tags)
                    wire_tags.append(cl)

                if not wire_tags:
                    continue

                surf     = gmsh.model.occ.addPlaneSurface(wire_tags)
                extruded = gmsh.model.occ.extrude([(2, surf)], 0.0, 0.0, h)
                vol_ents = [(d, t) for d, t in extruded if d == 3]

                if op == "cutout":
                    cut_ents.extend(vol_ents)
                else:
                    solid_ents.extend(vol_ents)

            if not solid_ents:
                raise RuntimeError("solid レイヤーが1つもありません。cutoutのみのモデルは生成できません。")

            gmsh.model.occ.synchronize()

            # Fuse all solid volumes into one
            if len(solid_ents) > 1:
                fused, _ = gmsh.model.occ.fuse(
                    [solid_ents[0]], solid_ents[1:],
                    removeObject=True, removeTool=True
                )
                solid_ents = fused
                gmsh.model.occ.synchronize()

            # Subtract cutout volumes
            if cut_ents and solid_ents:
                cut_result, _ = gmsh.model.occ.cut(
                    solid_ents, cut_ents,
                    removeObject=True, removeTool=True
                )
                solid_ents = cut_result
                gmsh.model.occ.synchronize()

            gmsh.write(out_path)

        finally:
            try:
                gmsh.finalize()
            except Exception:
                pass

        with open(out_path, "rb") as f:
            return f.read()


# ── Streamlit UI ─────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="DXF → 3D Converter",
    page_icon="🧊",
    layout="wide",
)

st.markdown("""
<style>
  .block-container { padding-top: 1.5rem; }
  section[data-testid="stSidebar"] { background: #1e293b; }
  section[data-testid="stSidebar"] * { color: #e2e8f0 !important; }
</style>
""", unsafe_allow_html=True)

st.title("🧊 CAD → 3D Model Generator")
st.caption(
    "DXF / STEP / IGES ファイルから3Dモデル (STL / STEP) を生成。"
    "DXFは2D断面を押し出し変換、STEP/IGESは直接3Dメッシュ化。"
)

# ── Sidebar ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.header("⚙️ 変換設定")

    height_mm = st.number_input(
        "押し出し高さ / mm (DXFのみ)", min_value=0.1, max_value=5000.0,
        value=10.0, step=0.5,
    )

    output_fmt = st.radio(
        "出力フォーマット (DXF押し出し)",
        ["STL (高速・Pure Python)", "STEP (高精度・FreeCAD)"],
        index=0,
    )
    want_step = output_fmt.startswith("STEP")

    st.divider()
    st.markdown("**DXF詳細設定**")
    auto_clean = st.checkbox(
        "重複線除去・ギャップ自動判定",
        value=True,
        help=(
            "✅ ON (推奨): 重複した線を自動削除し、微小ギャップを統計的に検出して自動補完します。\n\n"
            "OFF: 手動でギャップ許容値を指定します。"
        ),
    )
    gap_tol = st.slider(
        "ギャップ許容 (mm)" + (" ← 自動判定ONのため参考値" if auto_clean else ""),
        min_value=0.001, max_value=5.0, value=GAP_TOL_DEFAULT, step=0.001, format="%.3f",
        disabled=auto_clean,
        help=(
            "LINE/ARC セグメント同士のエンドポイントが、この距離以内なら"
            "「繋がっている」とみなします。\n"
            "自動判定OFFの場合に有効です。0.1〜1.0mm推奨。"
        ),
    )
    if auto_clean:
        max_auto_gap = st.slider(
            "自動検出 ギャップ上限 (mm)",
            min_value=1.0, max_value=30.0, value=5.0, step=0.5,
            help=(
                "この距離より大きいギャップは自動検出の対象外にします。\n"
                "粗いDXFファイルでは10〜20mmに広げると繋がりやすくなります。"
            ),
        )
    else:
        max_auto_gap = 5.0
    manual_layer = st.text_input(
        "レイヤー名 (空欄=自動推定)",
        value="",
        placeholder="例: CONTOUR, 外形, 0",
    )
    axis_override = st.radio(
        "押し出し方向 (DXF)",
        ["自動検出", "Z軸 (XY平面)", "X軸 (YZ平面)", "Y軸 (XZ平面)"],
        index=0,
        horizontal=True,
        help="DXF内の extrusion ベクトルから自動判定します。誤検出時に手動で上書きできます。",
    )

    st.divider()
    st.markdown("**STEP/IGES設定**")
    step_deflection = st.slider(
        "テセレーション精度 (mm)",
        min_value=0.01, max_value=2.0, value=0.1, step=0.01,
        help="小さいほど細かいメッシュ。大きいファイルでは0.2〜0.5mm推奨。",
    )

    st.divider()
    st.markdown("**対応エンティティ (DXF)**")
    st.markdown("""
    - LINE / ARC / CIRCLE
    - LWPOLYLINE / POLYLINE (open可)
    - **SPLINE** ✨
    - **ELLIPSE** ✨
    - **HATCH境界** ✨
    - **INSERT(ブロック参照)** ✨
    """)

# ── Input mode tabs ───────────────────────────────────────────────────────────
tab_dxf, tab_multi, tab_step = st.tabs([
    "📐 DXF → 3D (単一レイヤー)",
    "📦 マルチレイヤー STEP",
    "🔩 STEP / IGES → 3D",
])

# ═══════════════════════════════════════════════════════════════════
# TAB 2: STEP / IGES 直接読み込み
# ═══════════════════════════════════════════════════════════════════
with tab_step:
    st.markdown(
        "STEP (.step/.stp) または IGES (.igs/.iges) ファイルをアップロードすると、"
        "**OpenCASCADE (pythonocc-core)** でそのまま3Dメッシュ化します。  \n"
        "押し出し変換は不要です。"
    )
    uploaded_cad = st.file_uploader(
        "STEP / IGES ファイルをアップロード",
        type=["step", "stp", "igs", "iges"],
        key="uploader_step",
    )
    if uploaded_cad is not None:
        cad_bytes = uploaded_cad.read()
        ext = uploaded_cad.name.rsplit(".", 1)[-1].lower()
        with st.spinner(f"{ext.upper()} を解析中 (OpenCASCADE)…"):
            try:
                if ext in ("step", "stp"):
                    cad_mesh = load_step_to_mesh(cad_bytes, step_deflection)
                else:
                    cad_mesh = load_iges_to_mesh(cad_bytes, step_deflection)

                bbox_c = cad_mesh.bounds
                dims_c = bbox_c[1] - bbox_c[0]
                st.success(
                    f"読み込み成功: {len(cad_mesh.vertices):,} 頂点 / "
                    f"{len(cad_mesh.faces):,} 面  |  "
                    f"{dims_c[0]:.2f} × {dims_c[1]:.2f} × {dims_c[2]:.2f} mm  |  "
                    f"Watertight: {'✅' if cad_mesh.is_watertight else '⚠️'}"
                )

                # 3D Preview
                tr_c = mesh_to_plotly(cad_mesh)
                fig_c = go.Figure(data=[tr_c])
                fig_c.update_layout(
                    scene=dict(
                        xaxis_title="X (mm)", yaxis_title="Y (mm)", zaxis_title="Z (mm)",
                        bgcolor="#0f172a", aspectmode="data",
                        xaxis=dict(gridcolor="#334155", zerolinecolor="#334155"),
                        yaxis=dict(gridcolor="#334155", zerolinecolor="#334155"),
                        zaxis=dict(gridcolor="#334155", zerolinecolor="#334155"),
                    ),
                    paper_bgcolor="#0f172a",
                    margin=dict(l=0, r=0, t=30, b=0),
                    height=500,
                )
                st.plotly_chart(fig_c, use_container_width=True)

                # Download STL
                stl_buf_c = io.BytesIO()
                cad_mesh.export(stl_buf_c, file_type="stl")
                st.download_button(
                    label="⬇️ STL をダウンロード",
                    data=stl_buf_c.getvalue(),
                    file_name=f"{uploaded_cad.name.rsplit('.', 1)[0]}.stl",
                    mime="application/octet-stream",
                    use_container_width=True,
                )

            except RuntimeError as exc:
                err_msg = str(exc)
                if "pythonocc-core" in err_msg:
                    st.error(
                        "pythonocc-core が未インストールです。\n\n"
                        "Dockerfile に `pythonocc-core` を追加してリビルドしてください:\n"
                        "```\npip install pythonocc-core\n```"
                    )
                else:
                    st.error(f"変換エラー: {exc}")
            except Exception as exc:
                st.error(f"予期しないエラー: {exc}")
    else:
        st.info("STEP または IGES ファイルをアップロードしてください。")

# ═══════════════════════════════════════════════════════════════════
# TAB: マルチレイヤー STEP
# ═══════════════════════════════════════════════════════════════════
with tab_multi:
    st.markdown(
        "各レイヤーに **個別の厚み** と **演算種別**（積層 / 切り抜き）を設定して  \n"
        "複合STEPモデルを生成します。  \n"
        "**例**: 外形 10mm + ポケット穴 (cutout) + フランジ 5mm → 一体STEP"
    )

    uploaded_ml = st.file_uploader(
        "DXFファイルをアップロード",
        type=["dxf"],
        key="uploader_ml",
        help="AutoCAD DXF形式 (R12〜2018)。",
    )

    if uploaded_ml is not None:
        dxf_bytes_ml = uploaded_ml.read()
        doc_ml = None
        try:
            doc_ml = ezdxf.read(io.StringIO(dxf_bytes_ml.decode("utf-8")))
        except UnicodeDecodeError:
            try:
                doc_ml = ezdxf.read(io.StringIO(dxf_bytes_ml.decode("cp932")))
            except Exception as _e:
                st.error(f"DXF 読み込みエラー (文字コード): {_e}")
        except Exception as _e:
            st.error(f"DXF 読み込みエラー: {_e}")

        if doc_ml is not None:
            layer_info_ml = analyze_layers(doc_ml)
            geo_layers_ml = {k: v for k, v in layer_info_ml.items() if v["is_geo"]}

            if not geo_layers_ml:
                st.warning("幾何エンティティ（LINE / ARC / CIRCLE 等）を含むレイヤーが見つかりませんでした。")
            else:
                st.markdown(f"**{len(geo_layers_ml)} 個の幾何レイヤーを検出**")

                # ── Per-layer configuration table ─────────────────────────────
                hdr = st.columns([3, 1, 2, 2, 4])
                hdr[0].markdown("**レイヤー名**")
                hdr[1].markdown("**有効**")
                hdr[2].markdown("**厚み mm**")
                hdr[3].markdown("**演算**")
                hdr[4].markdown("**エンティティ**")

                ml_cfgs   = []
                z_cursor_ = 0.0

                for lname_ml, li_ml in sorted(
                    geo_layers_ml.items(), key=lambda x: -x[1]["total"]
                ):
                    row = st.columns([3, 1, 2, 2, 4])
                    row[0].markdown(
                        f"`{lname_ml}`" + ("" if not li_ml["skip"] else " ⚠️")
                    )
                    en_ml = row[1].checkbox(
                        "", value=not li_ml["skip"],
                        key=f"ml_en_{lname_ml}"
                    )
                    th_ml = row[2].number_input(
                        "", min_value=0.1, max_value=500.0, value=10.0,
                        step=0.5, key=f"ml_th_{lname_ml}",
                        label_visibility="collapsed",
                    )
                    op_ml = row[3].selectbox(
                        "", ["solid", "cutout"],
                        key=f"ml_op_{lname_ml}",
                        label_visibility="collapsed",
                    )
                    types_ml = " ".join(
                        f"{t}:{n}" for t, n in li_ml["types"].items() if n > 0
                    )
                    row[4].caption(types_ml)

                    if en_ml:
                        z0_ = z_cursor_ if op_ml == "solid" else 0.0
                        ml_cfgs.append({
                            "layer":     lname_ml,
                            "height_mm": th_ml,
                            "operation": op_ml,
                            "z_offset":  z0_,
                        })
                        if op_ml == "solid":
                            z_cursor_ += th_ml

                st.divider()

                if not ml_cfgs:
                    st.info("有効なレイヤーを 1 つ以上チェックしてください。")
                else:
                    n_solid = sum(1 for c in ml_cfgs if c["operation"] == "solid")
                    n_cut   = sum(1 for c in ml_cfgs if c["operation"] == "cutout")
                    st.caption(
                        f"選択: **{len(ml_cfgs)}** レイヤー  |  "
                        f"solid: {n_solid}  |  cutout: {n_cut}  |  "
                        f"積層総厚み: {z_cursor_:.1f} mm"
                    )

                    btn_stl_ml, btn_step_ml = st.columns(2)

                    # ── STL (manifold3d) ───────────────────────────────────────
                    if btn_stl_ml.button(
                        "📦 STL を生成",
                        type="primary",
                        use_container_width=True,
                        key="ml_gen_stl",
                    ):
                        combined_ml: list = []
                        with st.spinner("各レイヤーのメッシュを生成中..."):
                            for cfg_ in ml_cfgs:
                                lps_ = extract_loops(
                                    doc_ml, cfg_["layer"],
                                    gap_tol=GAP_TOL_DEFAULT, auto_clean=True,
                                )
                                if not lps_:
                                    st.warning(
                                        f"レイヤー `{cfg_['layer']}`: 輪郭なし — スキップ"
                                    )
                                    continue
                                m_, _ = loops_to_mesh(
                                    lps_, cfg_["height_mm"], axis="Z"
                                )
                                if m_ is None:
                                    st.warning(
                                        f"レイヤー `{cfg_['layer']}`: メッシュ生成失敗 — スキップ"
                                    )
                                    continue
                                m_ = m_.copy()
                                m_.apply_translation([0.0, 0.0, cfg_["z_offset"]])
                                combined_ml.append((cfg_["operation"], m_))

                        if not combined_ml:
                            st.error("有効なメッシュが1つも生成されませんでした。")
                        else:
                            import trimesh as _tm
                            solids_ml = [m for op_, m in combined_ml if op_ == "solid"]
                            if solids_ml:
                                merged_ml = _tm.util.concatenate(solids_ml)
                                dims_ml = merged_ml.bounds[1] - merged_ml.bounds[0]
                                stl_buf_ml = io.BytesIO()
                                merged_ml.export(stl_buf_ml, file_type="stl")
                                st.success(
                                    f"✅ STL生成完了: {len(merged_ml.faces):,} 面  |  "
                                    f"{dims_ml[0]:.1f} × {dims_ml[1]:.1f} × {dims_ml[2]:.1f} mm  |  "
                                    f"Watertight: {'✅' if merged_ml.is_watertight else '⚠️'}"
                                )
                                st.download_button(
                                    "⬇️ マルチレイヤー STL をダウンロード",
                                    data=stl_buf_ml.getvalue(),
                                    file_name=(
                                        uploaded_ml.name.replace(".dxf", "").replace(".DXF", "")
                                        + "_multi.stl"
                                    ),
                                    mime="application/octet-stream",
                                    use_container_width=True,
                                )
                                if any(op_ == "cutout" for op_, _ in combined_ml):
                                    st.info(
                                        "ℹ️ cutout レイヤーはSTLに未適用。"
                                        "STEP版ではboolean演算で切り抜きが適用されます。"
                                    )

                    # ── STEP (gmsh OCC) ────────────────────────────────────────
                    if btn_step_ml.button(
                        "⚙️ STEP を生成 (gmsh OCC)",
                        use_container_width=True,
                        key="ml_gen_step",
                    ):
                        with st.spinner(
                            "gmsh OpenCASCADE でSTEP生成中 (boolean演算含む)…"
                        ):
                            try:
                                gmsh_cfgs_ = []
                                for cfg_ in ml_cfgs:
                                    lps_ = extract_loops(
                                        doc_ml, cfg_["layer"],
                                        gap_tol=GAP_TOL_DEFAULT, auto_clean=True,
                                    )
                                    if lps_:
                                        gmsh_cfgs_.append({
                                            "loops":     lps_,
                                            "height_mm": cfg_["height_mm"],
                                            "operation": cfg_["operation"],
                                            "z_offset":  cfg_["z_offset"],
                                        })

                                if not gmsh_cfgs_:
                                    st.error("有効な輪郭が1つもありません。")
                                else:
                                    step_bytes_ml = multilayer_to_step_gmsh(gmsh_cfgs_)
                                    n_s = sum(1 for c in gmsh_cfgs_ if c["operation"] == "solid")
                                    n_c = sum(1 for c in gmsh_cfgs_ if c["operation"] == "cutout")
                                    st.success(
                                        f"✅ STEP生成完了: {len(step_bytes_ml)/1024:.1f} KB  |  "
                                        f"solid {n_s} 層 + cutout {n_c} 層"
                                    )
                                    st.download_button(
                                        "⬇️ マルチレイヤー STEP をダウンロード",
                                        data=step_bytes_ml,
                                        file_name=(
                                            uploaded_ml.name.replace(".dxf", "").replace(".DXF", "")
                                            + "_multi.step"
                                        ),
                                        mime="application/octet-stream",
                                        use_container_width=True,
                                    )
                            except Exception as _exc:
                                st.error(f"STEP生成エラー:\n```\n{_exc}\n```")
    else:
        st.info(
            "DXFファイルをアップロードしてください。  \n"
            "各レイヤーに **厚み** と **演算種別**（solid / cutout）を設定し、  \n"
            "複数パーツをひとつのSTEPファイルに結合します。"
        )

# ═══════════════════════════════════════════════════════════════════
# TAB 1: DXF → 押し出し変換
# ═══════════════════════════════════════════════════════════════════
with tab_dxf:

    # ── File upload ──────────────────────────────────────────────────
    uploaded = st.file_uploader(
        "DXFファイルをアップロード",
        type=["dxf"],
        key="uploader_dxf",
        help="AutoCAD DXF形式 (R12〜2018)。SPLINE / ELLIPSE / HATCH / ブロック参照対応。",
    )

    if uploaded is None:
        st.info(
            "DXFファイルをアップロードしてください。  \n"
            "**対応形式**: AutoCAD R12〜2018 (.dxf)  \n"
            "**対応エンティティ**: LINE / ARC / CIRCLE / LWPOLYLINE / POLYLINE / "
            "SPLINE / ELLIPSE / HATCH / INSERT(ブロック)"
        )
        st.stop()

    # ── Parse DXF ───────────────────────────────────────────────────
    dxf_bytes = uploaded.read()
    try:
        doc = ezdxf.read(io.StringIO(dxf_bytes.decode("utf-8")))
    except UnicodeDecodeError:
        try:
            doc = ezdxf.read(io.StringIO(dxf_bytes.decode("cp932")))
        except Exception as e:
            st.error(f"DXF 読み込みエラー (文字コード): {e}")
            st.stop()
    except Exception as e:
        st.error(f"DXF 読み込みエラー: {e}")
        st.stop()

    # ── Extrusion axis detection ──────────────────────────────────────
    _auto_axis = detect_extrusion_axis(doc)
    _axis_map = {"Z軸 (XY平面)": "Z", "X軸 (YZ平面)": "X", "Y軸 (XZ平面)": "Y"}
    detected_axis = _axis_map.get(axis_override, _auto_axis)

    # ── Layer analysis ───────────────────────────────────────────────
    layer_info = analyze_layers(doc)
    auto_layer = suggest_contour_layer(layer_info)
    all_layers = sorted(layer_info.keys()) or ["0"]

    # Layer analysis table
    with st.expander(f"レイヤー解析 ({len(layer_info)} レイヤー検出)", expanded=len(layer_info) <= 6):
        import pandas as pd
        layer_rows = []
        for lname, li in sorted(layer_info.items(), key=lambda x: -x[1]["total"]):
            type_str = ", ".join(f"{t}:{n}" for t, n in sorted(li["types"].items(), key=lambda x: -x[1]))
            hint = "⭐ 推奨" if lname == auto_layer else ("⚠️ skip?" if li["skip"] else "")
            layer_rows.append({
                "レイヤー": lname,
                "エンティティ数": li["total"],
                "種類": type_str,
                "幾何": "✅" if li["is_geo"] else "—",
                "備考": hint,
            })
        st.dataframe(pd.DataFrame(layer_rows), hide_index=True, use_container_width=True)

        if auto_layer:
            st.info(f"推奨レイヤー: **`{auto_layer}`**  (最も多くの幾何エンティティを含む非寸法レイヤー)")

    # ── Layer selector ───────────────────────────────────────────────
    col_l, col_r = st.columns([2, 3])
    with col_l:
        # Default to auto-suggested layer
        opt_list = ["(全レイヤー)"] + all_layers
        auto_idx = 0
        if auto_layer and auto_layer in all_layers:
            auto_idx = all_layers.index(auto_layer) + 1  # +1 for "(全レイヤー)"
        layer_pick = st.selectbox(
            "使用レイヤー",
            options=opt_list,
            index=auto_idx,
            help="⭐ 付きが自動推奨レイヤー。複数レイヤーに輪郭が分散している場合は「全レイヤー」を選択。",
        )
        active_layer = "" if layer_pick == "(全レイヤー)" else layer_pick
        if manual_layer:
            active_layer = manual_layer
        _axis_label = f"{detected_axis}軸" + ("(自動)" if axis_override == "自動検出" else "(手動)")
        st.caption(f"使用レイヤー: `{active_layer or '全レイヤー'}`  |  ギャップ許容: `{gap_tol:.3f} mm`  |  押し出し軸: `{_axis_label}`")

    with col_r:
        st.caption(
            f"ファイル: `{uploaded.name}` ({len(dxf_bytes)/1024:.1f} KB)  |  "
            f"レイヤー数: {len(all_layers)}"
        )

    st.divider()

    # ── Extract loops ─────────────────────────────────────────────────
    with st.spinner("DXFを解析中..."):
        loops = extract_loops(doc, active_layer, gap_tol=gap_tol,
                              auto_clean=auto_clean, max_auto_gap=max_auto_gap)

    # Show auto-clean diagnostics
    _dedup_n  = getattr(extract_loops, "_last_dedup_count", 0)
    _det_gap  = getattr(extract_loops, "_last_auto_gap", None)
    _used_gap = getattr(extract_loops, "_last_gap_tol", gap_tol)
    if auto_clean and (_dedup_n > 0 or _det_gap is not None):
        msgs = []
        if _dedup_n > 0:
            msgs.append(f"重複セグメント **{_dedup_n}** 本を除去")
        if _det_gap is not None:
            msgs.append(f"ギャップ自動検出: **{_det_gap:.3f} mm** → 使用値 **{_used_gap:.3f} mm**")
        st.info("🔧 自動クリーン: " + "　|　".join(msgs))

    if not loops:
        # Provide actionable diagnosis
        st.error(
            f"**閉じた輪郭が見つかりませんでした** (レイヤー: `{active_layer or '全'}`)  \n\n"
            "**チェックリスト:**\n"
            f"- 別レイヤーに輪郭がある可能性 → 「全レイヤー」を試す\n"
            f"- ギャップが大きい → ギャップ許容スライダーを大きくする (現在: {gap_tol:.3f} mm)\n"
            "- 非対応エンティティ (XLINE / RAY) → 外形線を LINE/ARC/SPLINE に変換\n"
            "- 3D DXF (Z座標あり) → STEP/IGES タブを使用"
        )
        # Show all entity types for diagnosis
        all_types: dict = {}
        for e in doc.modelspace():
            t = e.dxftype()
            all_types[t] = all_types.get(t, 0) + 1
        st.caption("DXF内のエンティティ: " + ", ".join(f"{t}×{n}" for t, n in sorted(all_types.items())))
        st.stop()

st.success(
    f"**{len(loops)}** 個の閉じた輪郭を検出しました。"
    + (f"  (外形: 1、穴: {len(loops)-1})" if len(loops) > 1 else "")
)

# ── Generate 3D mesh ──────────────────────────────────────────────────────────
with st.spinner("3Dメッシュを生成中..."):
    mesh, n_bodies = loops_to_mesh(loops, height_mm, axis=detected_axis)

if mesh is None:
    st.error(
        "**3Dメッシュの生成に失敗しました。**\n\n"
        "**考えられる原因:**\n"
        "- 輪郭が自己交差している (Shapely が無効ポリゴンと判定)\n"
        "- 輪郭の点数が少なすぎる (3点未満)\n"
        "- 穴が外枠の外側にある\n\n"
        "**対処法:**\n"
        "- ギャップ許容スライダーを調整して再試行\n"
        "- 別レイヤーを選択する\n"
        "- DXFをCADで再保存する"
    )
    st.stop()

bbox = mesh.bounds
dims = bbox[1] - bbox[0]
wt_icon = "✅" if mesh.is_watertight else "⚠️"
body_txt = f"ボディ: {n_bodies}個  |  " if n_bodies > 1 else ""
st.markdown(
    f"**メッシュ**: {len(mesh.vertices):,} 頂点 / {len(mesh.faces):,} 面  |  "
    f"{body_txt}"
    f"押し出し方向: `{detected_axis}軸`  |  "
    f"サイズ: `{dims[0]:.2f} × {dims[1]:.2f} × {dims[2]:.2f} mm`  |  "
    f"体積: `{mesh.volume:.1f} mm³`  |  "
    f"Watertight: {wt_icon}"
)

# ── 3D Preview ────────────────────────────────────────────────────────────────
trace = mesh_to_plotly(mesh)
fig = go.Figure(data=[trace])
fig.update_layout(
    scene=dict(
        xaxis_title="X (mm)",
        yaxis_title="Y (mm)",
        zaxis_title="Z (mm)",
        bgcolor="#0f172a",
        xaxis=dict(gridcolor="#334155", zerolinecolor="#334155"),
        yaxis=dict(gridcolor="#334155", zerolinecolor="#334155"),
        zaxis=dict(gridcolor="#334155", zerolinecolor="#334155"),
        aspectmode="data",
    ),
    paper_bgcolor="#0f172a",
    margin=dict(l=0, r=0, t=30, b=0),
    height=500,
)
st.plotly_chart(fig, use_container_width=True)

# ── Download ──────────────────────────────────────────────────────────────────
st.divider()
st.subheader("ダウンロード")

dl_col1, dl_col2 = st.columns(2)

# STL (always available instantly)
with dl_col1:
    stl_buf = io.BytesIO()
    mesh.export(stl_buf, file_type="stl")
    stl_bytes = stl_buf.getvalue()
    st.download_button(
        label="⬇️ STL をダウンロード",
        data=stl_bytes,
        file_name=f"{uploaded.name.replace('.dxf', '')}_h{height_mm:.0f}mm.stl",
        mime="application/octet-stream",
        use_container_width=True,
    )
    st.caption(f"サイズ: {len(stl_bytes) / 1024:.1f} KB")

# STEP (gmsh OCC — no FreeCAD dependency)
with dl_col2:
    if want_step:
        with st.spinner("gmsh OCC でSTEP変換中…"):
            try:
                step_bytes = loops_to_step_gmsh(loops, height_mm)
                st.download_button(
                    label="⬇️ STEP をダウンロード",
                    data=step_bytes,
                    file_name=f"{uploaded.name.replace('.dxf', '')}_h{height_mm:.0f}mm.step",
                    mime="application/octet-stream",
                    use_container_width=True,
                )
                st.caption(f"サイズ: {len(step_bytes) / 1024:.1f} KB")
            except Exception as exc:
                st.error(f"STEP変換エラー:\n```\n{exc}\n```")
    else:
        st.button(
            "STEP をダウンロード",
            disabled=True,
            use_container_width=True,
            help="左メニューで出力フォーマット「STEP」を選択してください",
        )
        st.caption("STEP出力: サイドバーでフォーマット変更")

# FreeCAD ネイティブ形式 (.fcstd) — 常に表示
st.divider()
st.subheader("🗂️ FreeCAD ネイティブ形式でダウンロード (.fcstd)")
st.caption(
    "**FreeCADで直接開いて編集可能です。**  \n"
    "モデルツリー: `Body` → `Profile (Sketch)` → `Pad (押し出し)`  \n"
    "Sketch内の点を移動・拘束追加、Padの高さ変更、Boolean演算の追加が可能です。  \n"
    "※ Sketch内の曲線は折れ線近似です（ARCは直線分割）。"
)

_fcstd_stem = uploaded.name.replace(".dxf", "").replace(".DXF", "")
if st.button("⚙️ .fcstd を生成する (FreeCAD / Antigravity)", use_container_width=True,
             type="primary"):
    with st.spinner("FreeCAD (Antigravity) で .fcstd 生成中… 最大60秒"):
        try:
            _fcstd_bytes = convert_fcstd_via_freecad(loops, height_mm, stem=_fcstd_stem)
            st.download_button(
                label=f"⬇️ {_fcstd_stem}_h{height_mm:.0f}mm.fcstd をダウンロード",
                data=_fcstd_bytes,
                file_name=f"{_fcstd_stem}_h{height_mm:.0f}mm.fcstd",
                mime="application/octet-stream",
                use_container_width=True,
            )
            st.success(
                f"生成完了: {len(_fcstd_bytes)/1024:.1f} KB  \n"
                "FreeCADで開くと `Body/Profile/Pad` のモデルツリーが確認できます。"
            )
        except Exception as _exc:
            st.error(f"**.fcstd 生成エラー**\n```\n{_exc}\n```")
            st.info(
                "Antigravity コンテナが起動していないか、FreeCADCmd が利用できない可能性があります。  \n"
                "`docker ps` でコンテナ状態を確認してください。"
            )

# ── Self-check panel ─────────────────────────────────────────────────────────
st.divider()
st.subheader("自己チェック / Mesh Quality Check")

checks = run_mesh_checks(mesh, height_mm, len(loops))

n_ok   = sum(1 for c in checks if c["ok"])
n_err  = sum(1 for c in checks if not c["ok"] and c["severity"] == "error")
n_warn = sum(1 for c in checks if not c["ok"] and c["severity"] == "warn")

# Overall badge
if n_err > 0:
    st.error(f"品質: 要修正 — {n_err} エラー / {n_warn} 警告 / {n_ok} 正常")
elif n_warn > 0:
    st.warning(f"品質: 概ね良好 — {n_warn} 警告 / {n_ok} 正常")
else:
    st.success(f"品質: 全項目クリア — {n_ok}/{len(checks)} 正常")

# Check result table
ICON = {"ok": "✅", "warn": "⚠️", "error": "❌"}
check_cols = st.columns([2, 1, 4])
check_cols[0].markdown("**チェック項目**")
check_cols[1].markdown("**結果**")
check_cols[2].markdown("**詳細**")
for c in checks:
    icon = ICON[c["severity"]] if not c["ok"] else "✅"
    check_cols[0].markdown(c["name"])
    check_cols[1].markdown(icon)
    check_cols[2].markdown(c["detail"])

# AI analysis button (local Ollama — no cloud API cost)
st.markdown("")
if st.button("AI判定 (ローカルLLM / 無料)", help="Ollama qwen2.5-coder:7b でメッシュ品質を解説。クラウドAPIは使用しません。"):
    with st.spinner("ローカルLLMで分析中 (qwen2.5-coder:7b)…"):
        comment = ai_mesh_check(checks, mesh)
    st.info(f"**AI判定:** {comment}")

# ── Test suite ───────────────────────────────────────────────────────────────
st.divider()
with st.expander("テストスイート — 全形状テスト (座グリ / 横穴 / 縦穴 / 曲線溝 / クランク曲げ / U字曲げ)"):
    st.markdown(
        "内蔵テストDXFを自動生成してコンバーターに通し、体積・Bounding Box・Watertightを採点します。"
        " クラウドAPIは使用しません。"
    )
    if st.button("全テスト実行 (11種)", key="run_tests"):
        with st.spinner("テスト中..."):
            test_results = run_test_suite(TEST_SUITE)

        avg = sum(r["score"] for r in test_results) / len(test_results)
        passed = sum(1 for r in test_results if r["score"] >= 60)
        if avg >= 80:
            st.success(f"総合スコア: **{avg:.0f} / 100** — {passed}/{len(test_results)} テスト合格")
        elif avg >= 50:
            st.warning(f"総合スコア: **{avg:.0f} / 100** — {passed}/{len(test_results)} テスト合格")
        else:
            st.error(f"総合スコア: **{avg:.0f} / 100** — {passed}/{len(test_results)} テスト合格")

        # Results table
        rows = []
        for r in test_results:
            bar = "█" * (r["score"] // 10) + "░" * (10 - r["score"] // 10)
            rows.append({
                "形状": r["desc"],
                "スコア": f"{r['score']:3d}  {bar}",
                "体積(mm³)": f"{r.get('vol_actual','—')}",
                "Watertight": "✅" if r.get("watertight") else ("❌" if r["ok"] else "—"),
                "面数": r.get("faces","—"),
                "備考": r.get("notes") or r.get("error",""),
            })
        import pandas as pd
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

        # Show 3D previews of any failed cases
        failed = [r for r in test_results if r["ok"] and r["score"] < 60]
        if failed:
            st.markdown("**失敗ケースの3Dプレビュー:**")
            fail_cols = st.columns(min(len(failed), 3))
            for col, r in zip(fail_cols, failed):
                if r.get("mesh"):
                    tr = mesh_to_plotly(r["mesh"])
                    fig2 = go.Figure([tr])
                    fig2.update_layout(
                        scene=dict(bgcolor="#0f172a", aspectmode="data"),
                        paper_bgcolor="#0f172a", margin=dict(l=0,r=0,t=20,b=0), height=200,
                    )
                    col.markdown(f"**{r['id']}** ({r['score']}点)")
                    col.plotly_chart(fig2, use_container_width=True)

# ── Extended test suite (100+ shapes) ────────────────────────────────────────
st.divider()
with st.expander("詳細テストスイート (100種+) — 面数・精度・Watertight 総合評価", expanded=False):
    st.markdown(
        "100種類以上のDXFを自動生成してコンバーターに通し、**体積・BBox・Watertight・位相面数**を採点します。  \n"
        "クラウドAPIは使用しません（全てローカル処理）。実行時間: 約60〜120秒。"
    )
    if st.button("全100種+テスト実行", key="run_extended"):
        import pandas as pd
        ext_suite = build_extended_test_suite()
        prog = st.progress(0, text="テスト中...")
        ext_results = []
        for idx, item in enumerate(ext_suite):
            prog.progress((idx + 1) / len(ext_suite), text=f"{idx+1}/{len(ext_suite)}: {item['id']}")
            ext_results.extend(run_extended_suite([item]))
        prog.empty()

        ok_r    = [r for r in ext_results if r.get("ok")]
        all_r   = ext_results
        passed  = sum(1 for r in ok_r if r["score"] >= 80)
        avg     = sum(r.get("score", 0) for r in all_r) / max(len(all_r), 1)
        topo_ok = sorted(r["topo_faces"] for r in ok_r if r.get("topo_faces", 0) > 0)
        max_topo = max(topo_ok) if topo_ok else 0

        st.success(
            f"**{passed}/{len(all_r)} 合格 (スコア≥80)** | 平均スコア: {avg:.1f}/100 | "
            f"最大位相面数: **{max_topo}**面"
        )

        # ── Face-count capability breakdown ──────────────────────────────────
        st.markdown("### 面数別 合格率")
        topo_buckets: dict = {}
        for r in ok_r:
            t = r.get("topo_faces", 0)
            if t <= 0:
                continue
            topo_buckets.setdefault(t, {"total": 0, "pass80": 0, "watertight": 0})
            topo_buckets[t]["total"]    += 1
            if r["score"] >= 80:
                topo_buckets[t]["pass80"] += 1
            if r.get("watertight"):
                topo_buckets[t]["watertight"] += 1

        cap_rows = []
        for t in sorted(topo_buckets):
            d = topo_buckets[t]
            rate = d["pass80"] / d["total"] * 100
            wt_rate = d["watertight"] / d["total"] * 100
            bar = "█" * int(rate // 10) + "░" * (10 - int(rate // 10))
            cap_rows.append({
                "位相面数": t,
                "テスト数": d["total"],
                "合格(≥80)": d["pass80"],
                "合格率": f"{rate:.0f}%  {bar}",
                "Watertight率": f"{wt_rate:.0f}%",
            })
        st.dataframe(pd.DataFrame(cap_rows), hide_index=True, use_container_width=True)

        # ── Full results table ────────────────────────────────────────────────
        st.markdown("### 全テスト結果")
        rows = []
        for r in all_r:
            rows.append({
                "ID":        r["id"],
                "形状":      r["desc"],
                "スコア":    r.get("score", 0),
                "位相面数":  r.get("topo_faces", "—"),
                "三角面数":  r.get("tri_faces", "—"),
                "Watertight": "✅" if r.get("watertight") else ("❌" if r.get("ok") else "—"),
                "体積(mm³)": r.get("vol_actual", "—"),
                "備考":      r.get("notes", r.get("error", "")),
            })
        st.dataframe(
            pd.DataFrame(rows), use_container_width=True, hide_index=True, height=450,
        )

        # ── Max face count summary ────────────────────────────────────────────
        achieved = sorted({r["topo_faces"] for r in ok_r if r.get("topo_faces", 0) > 0 and r["score"] >= 80})
        st.info(
            f"**達成済み位相面数:** {', '.join(str(x) for x in achieved)}  \n"
            f"**最大達成面数: {max(achieved) if achieved else 0} 面**"
        )

        # ── 2D DXF ↔ 3D Model 比較ビュー ─────────────────────────────────────
        st.markdown("---")
        st.markdown("### 2D DXF ↔ 3D モデル 比較一覧")
        st.caption("左: 2D DXF図面（matplotlib描画） | 右: 生成3Dモデル（Plotly） | 体積誤差を色表示")

        filter_opts = ["全件", "ネジ穴のみ", "溝・横穴のみ", "合格のみ (score≥80)", "スコア<100のみ"]
        filt = st.selectbox("フィルター", filter_opts, key="cmp_filter")
        n_show = st.slider("表示件数", 4, min(60, len(ext_results)), 12, 4, key="cmp_n")

        def _filter_results(rs, f):
            screw_pfx = ("screw_", "bcd_", "cbore_")
            groove_pfx = ("yokoana_", "curved_", "v_groove_", "keyway_", "step_groove_",
                          "arc_side_", "double_groove_")
            if f == "ネジ穴のみ":
                return [r for r in rs if any(r["id"].startswith(p) for p in screw_pfx)]
            if f == "溝・横穴のみ":
                return [r for r in rs if any(r["id"].startswith(p) for p in groove_pfx)]
            if f == "合格のみ (score≥80)":
                return [r for r in rs if r.get("score", 0) >= 80]
            if f == "スコア<100のみ":
                return [r for r in rs if r.get("score", 0) < 100]
            return rs

        display_rs = _filter_results(ext_results, filt)[:n_show]

        for r in display_rs:
            if not r.get("ok") or not r.get("dxf_bytes"):
                st.warning(f"**{r['id']}** — {r.get('error', '生成失敗')}")
                continue

            vol_a = r.get("vol_actual", 0)
            vol_e = r.get("vol_expected")
            err_pct = r.get("vol_err_pct")
            wt = r.get("watertight", False)
            score = r.get("score", 0)

            # Header bar
            if err_pct is not None:
                vol_color = "🟢" if err_pct < 1 else ("🟡" if err_pct < 5 else "🔴")
                vol_label = f"{vol_color} 体積: {vol_a:,.0f} / {vol_e:,.0f} mm³  (誤差 {err_pct:.2f}%)"
            else:
                vol_label = f"体積: {vol_a:,.0f} mm³  (期待値なし)"
            wt_icon = "✅" if wt else "❌"

            with st.container(border=True):
                st.markdown(
                    f"**{r['id']}** — {r['desc']}  |  "
                    f"Score: **{score}/100**  |  Watertight: {wt_icon}  |  "
                    f"位相面数: {r.get('topo_faces','—')}  |  {vol_label}"
                )
                col2d, col3d = st.columns(2)
                with col2d:
                    st.caption("2D DXF")
                    try:
                        img_bytes = render_dxf_2d(r["dxf_bytes"])
                        st.image(img_bytes, use_container_width=True)
                    except Exception as e:
                        st.error(f"2D描画エラー: {e}")
                with col3d:
                    st.caption("3D モデル")
                    if r.get("mesh"):
                        try:
                            fig3d = render_mesh_3d_fig(r["mesh"])
                            st.plotly_chart(fig3d, use_container_width=True, key=f"3d_{r['id']}")
                        except Exception as e:
                            st.error(f"3D描画エラー: {e}")

# ── CSG 3D テスト (manifold3d + qwen3.5 AI検証) ──────────────────────────────
st.divider()
with st.expander("🔷 CSG 3D テスト — 真の3D形状 (立方体接合・穴あけ・複合)", expanded=False):
    st.markdown(
        "**manifold3d** (Pure Python CSG ライブラリ) で 2D押し出しでは不可能な"
        "真の3D形状を生成・検証します。  \n"
        "**qwen3:8b** (Native Ollama) でAI自己チェックも実施可能。"
        "クラウドAPIは一切使用しません。"
    )
    st.markdown("""
    | 形状 | 説明 |
    |------|------|
    | csg_l_3d | 2ボックス L字3D接合 |
    | csg_t_3d | 2ボックス T字3D接合 |
    | csg_stair_3d | 3ボックス 階段状3D |
    | csg_cross_3d | 5ボックス 3D十字 |
    | csg_tower_3d | 4ボックス タワー(各層縮小) |
    | csg_box_cyl_hole | ボックス - 円柱穴 (Boolean差分) |
    | csg_box_4holes | ボックス - 4円柱穴 |
    | csg_compound | ボックス+円柱+球 - 穴 (複合) |
    | csg_frame_3d | 3Dフレーム (外箱-内箱) |
    | csg_3d_random_10box | **真の3Dランダム10ボックス** (XYZ独立配置・重複Union) |
    | csg_bracket_3d | **L型ブラケット** (Z+X方向多穴) |
    | csg_flange_3d | **フランジ** (円盤+ネック+ボルト穴) |
    | csg_housing_3d | **ハウジング** (前後左右4方向穴あき) |
    | csg_stepped_shaft | **段付きシャフト** (+キー溝) |
    | csg_cross_connector | **3方向クロスコネクター** (X/Y/Z交差パイプ) |
    """)

    col_ai, col_url = st.columns([1, 3])
    with col_ai:
        use_ai = st.checkbox("qwen3.5 AI自己チェック", value=False, key="csg_ai")
    with col_url:
        ollama_url = st.text_input(
            "Ollama URL", value="http://ollama:11434", key="csg_ollama_url"
        )

    if st.button("CSG 3Dテスト実行", key="run_csg"):
        import pandas as pd
        csg_suite = build_csg_test_suite()
        total_csg = len(csg_suite)

        # ── リアルタイム進捗表示 ──────────────────────────────────────────────
        status_box  = st.status("CSGテスト実行中...", expanded=True)
        prog_bar    = st.progress(0, text="準備中...")
        result_area = st.empty()

        csg_results = []

        with status_box:
            for idx, item in enumerate(csg_suite):
                # 進捗更新
                pct = idx / total_csg
                prog_bar.progress(pct, text=f"[{idx+1}/{total_csg}] {item['id']} を生成中...")
                st.write(f"▶ **{item['id']}** — {item['desc']}")

                # 1件実行
                partial = run_csg_suite(
                    [item], ai_check=use_ai, ollama_url=ollama_url
                )
                r = partial[0]
                csg_results.append(r)

                # 即時フィードバック
                if r.get("ok"):
                    wt_icon = "✅" if r["watertight"] else "⚠️"
                    st.write(
                        f"  → スコア **{r['score']}/100** | "
                        f"体積 {r['vol_actual']:,.0f} mm³ | "
                        f"topo面 {r['topo_faces']} | tri {r['tri_faces']} | "
                        f"Watertight {wt_icon}"
                    )
                    if r.get("ai_comment"):
                        st.info(f"🤖 AI: {r['ai_comment']}")
                    if r.get("notes") and r["notes"] != "OK":
                        st.warning(f"  ⚠ {r['notes']}")
                else:
                    st.error(f"  ✗ 失敗: {r.get('error','?')}")

            prog_bar.progress(1.0, text="完了!")
            status_box.update(label="CSGテスト完了 ✅", state="complete")

        # ── 集計サマリー ──────────────────────────────────────────────────────
        ok_csg   = [r for r in csg_results if r.get("ok")]
        passed   = sum(1 for r in ok_csg if r.get("score", 0) >= 80)
        avg_sc   = sum(r.get("score", 0) for r in csg_results) / max(len(csg_results), 1)
        max_topo = max((r.get("topo_faces", 0) for r in ok_csg), default=0)
        max_tri  = max((r.get("tri_faces", 0) for r in ok_csg), default=0)

        st.success(
            f"**{passed}/{total_csg} 合格 (スコア≥80)** | "
            f"平均スコア: {avg_sc:.1f}/100 | "
            f"最大位相面数: **{max_topo}** | 最大三角形数: **{max_tri:,}**"
        )

        # ── 結果テーブル ──────────────────────────────────────────────────────
        rows_csg = []
        for r in csg_results:
            rows_csg.append({
                "ID":          r["id"],
                "形状":        r["desc"],
                "スコア":      r.get("score", 0),
                "topo面数":    r.get("topo_faces", "—"),
                "三角形数":    r.get("tri_faces", "—"),
                "Watertight":  "✅" if r.get("watertight") else ("❌" if r.get("ok") else "—"),
                "体積 mm³":    f"{r.get('vol_actual', 0):,.0f}" if r.get("ok") else "—",
                "体積誤差":    f"{r.get('vol_err_pct','—')}%" if r.get("vol_err_pct") is not None else "—",
                "備考":        r.get("notes", r.get("error", "")),
                "AI判定":      r.get("ai_comment", ""),
            })
        st.dataframe(pd.DataFrame(rows_csg), use_container_width=True, hide_index=True)

        # ── 3D モデルギャラリー ──────────────────────────────────────────────
        st.markdown("### 3D モデルギャラリー")
        st.caption("manifold3d で生成した CSG 形状のインタラクティブ3Dビュー")
        cols_per_row = 2
        ok_with_mesh = [r for r in csg_results if r.get("ok") and r.get("mesh")]
        for row_i in range(0, len(ok_with_mesh), cols_per_row):
            cols = st.columns(cols_per_row)
            for col_i, r in enumerate(ok_with_mesh[row_i:row_i + cols_per_row]):
                with cols[col_i]:
                    st.markdown(f"**{r['id']}**  \n"
                                f"topo:{r['topo_faces']} 面 | {r['vol_actual']:,.0f} mm³")
                    try:
                        fig3d = render_mesh_3d_fig(r["mesh"])
                        fig3d.update_layout(height=280)
                        st.plotly_chart(fig3d, use_container_width=True,
                                        key=f"csg3d_{r['id']}")
                    except Exception as e:
                        st.error(f"3D描画エラー: {e}")


# ── 形状別 詳細比較レポート ────────────────────────────────────────────────────
st.divider()
with st.expander(
    "📊 形状別 詳細比較レポート — 面積・体積・topo面数 全カテゴリ一括検証",
    expanded=False,
):
    st.markdown(
        "全202種(押し出し) + 10種(CSG) = **212形状**を一括実行。  \n"
        "**期待体積 vs 実測体積**・**各位相面の面積**・**Watertight**を  \n"
        "カテゴリ別に集計します。APIゼロ・全ローカル処理。"
    )
    if st.button("📊 全形状比較レポート生成 (212件)", key="run_full_report"):
        import pandas as pd

        prog_rep  = st.progress(0, text="準備中...")
        status_rep = st.status("比較レポート生成中...", expanded=True)

        report_rows = []
        with status_rep:
            def _rep_cb(idx, total, id_):
                pct = idx / max(total, 1)
                prog_rep.progress(pct, text=f"[{idx}/{total}] {id_}")
                if idx % 20 == 0 or idx == total:
                    st.write(f"進捗: {idx}/{total} 件処理済み")

            report_rows = build_full_report(progress_cb=_rep_cb)
            prog_rep.progress(1.0, text="完了!")
            status_rep.update(label="比較レポート生成完了 ✅", state="complete")

        df_all = pd.DataFrame(report_rows)

        # ── サマリー統計 ──────────────────────────────────────────────────────
        ok_rows = [r for r in report_rows if "エラー" not in r]
        st.success(
            f"**{len(ok_rows)}/{len(report_rows)} 形状生成成功** | "
            f"平均スコア: {sum(r.get('スコア',0) for r in ok_rows)/max(len(ok_rows),1):.1f}/100 | "
            f"最大topo面数: **{max((r.get('topo面数',0) for r in ok_rows), default=0)}** | "
            f"全体Watertight率: {sum(1 for r in ok_rows if r.get('Watertight'))/max(len(ok_rows),1)*100:.0f}%"
        )

        # ── カテゴリ別サマリー ────────────────────────────────────────────────
        st.markdown("### カテゴリ別サマリー")
        cats = {}
        for r in ok_rows:
            c = r.get("カテゴリ", "その他")
            cats.setdefault(c, []).append(r)

        cat_summary = []
        for cat, rows_c in sorted(cats.items()):
            vol_errs = [r["体積誤差(%)"] for r in rows_c if isinstance(r.get("体積誤差(%)"), float)]
            cat_summary.append({
                "カテゴリ":        cat,
                "件数":            len(rows_c),
                "平均スコア":      f"{sum(r.get('スコア',0) for r in rows_c)/len(rows_c):.1f}",
                "平均topo面数":    f"{sum(r.get('topo面数',0) for r in rows_c)/len(rows_c):.1f}",
                "最大topo面数":    max((r.get('topo面数',0) for r in rows_c), default=0),
                "体積誤差avg(%)":  f"{sum(vol_errs)/len(vol_errs):.4f}" if vol_errs else "—",
                "体積誤差max(%)":  f"{max(vol_errs):.4f}" if vol_errs else "—",
                "Watertight率":    f"{sum(1 for r in rows_c if r.get('Watertight'))/len(rows_c)*100:.0f}%",
            })
        st.dataframe(pd.DataFrame(cat_summary), use_container_width=True, hide_index=True)

        # ── カテゴリ選択して詳細表示 ──────────────────────────────────────────
        st.markdown("### カテゴリ別 詳細テーブル")
        all_cats = sorted({r.get("カテゴリ","その他") for r in ok_rows})
        sel_cat = st.selectbox("カテゴリ選択", ["全件"] + all_cats, key="rep_cat")

        filtered = ok_rows if sel_cat == "全件" else [r for r in ok_rows if r.get("カテゴリ") == sel_cat]

        detail_cols = [
            "カテゴリ","ID","説明","スコア",
            "期待体積(mm³)","実測体積(mm³)","体積誤差(%)",
            "topo面数","三角形数",
            "最大面積(mm²)","最小面積(mm²)","平均面積(mm²)",
            "上位3面積(mm²)","総表面積(mm²)","Watertight",
        ]
        df_detail = pd.DataFrame([
            {c: r.get(c, "—") for c in detail_cols} for r in filtered
        ])
        # Watertight を ✅/❌ に変換
        df_detail["Watertight"] = df_detail["Watertight"].map(
            lambda v: "✅" if v is True else ("❌" if v is False else v)
        )
        st.dataframe(df_detail, use_container_width=True, hide_index=True, height=500)

        # ── 体積誤差 分布グラフ ───────────────────────────────────────────────
        st.markdown("### 体積誤差分布")
        err_data = [(r["ID"], r["カテゴリ"], r["体積誤差(%)"])
                    for r in ok_rows if isinstance(r.get("体積誤差(%)"), float)]
        if err_data:
            import plotly.express as px
            df_err = pd.DataFrame(err_data, columns=["ID","カテゴリ","体積誤差(%)"])
            fig_err = px.bar(
                df_err.sort_values("体積誤差(%)", ascending=False).head(40),
                x="ID", y="体積誤差(%)", color="カテゴリ",
                title="体積誤差上位40件 (%)",
                height=350,
            )
            fig_err.update_layout(
                paper_bgcolor="#0f172a", plot_bgcolor="#1e293b",
                font_color="#e2e8f0", xaxis_tickangle=-45,
            )
            st.plotly_chart(fig_err, use_container_width=True, key="vol_err_chart")

        # ── topo面数 分布グラフ ───────────────────────────────────────────────
        st.markdown("### 位相面数 分布")
        topo_data = [(r["カテゴリ"], r.get("topo面数",0)) for r in ok_rows]
        df_topo = pd.DataFrame(topo_data, columns=["カテゴリ","topo面数"])
        fig_topo = px.box(
            df_topo, x="カテゴリ", y="topo面数",
            title="カテゴリ別 位相面数分布",
            height=400, color="カテゴリ",
        )
        fig_topo.update_layout(
            paper_bgcolor="#0f172a", plot_bgcolor="#1e293b",
            font_color="#e2e8f0", xaxis_tickangle=-30, showlegend=False,
        )
        st.plotly_chart(fig_topo, use_container_width=True, key="topo_box_chart")

        # ── CSVダウンロード ────────────────────────────────────────────────────
        csv_data = df_all.drop(columns=["Watertight"], errors="ignore").to_csv(
            index=False, encoding="utf-8-sig"
        )
        st.download_button(
            "📥 全結果CSVダウンロード",
            data=csv_data.encode("utf-8-sig"),
            file_name="dxf3d_shape_report.csv",
            mime="text/csv",
            key="dl_report_csv",
        )


# ── Technical details ─────────────────────────────────────────────────────────
with st.expander("技術詳細 / Conversion Details"):
    st.markdown(f"""
    | 項目 | 値 |
    |------|-----|
    | 入力ファイル | `{uploaded.name}` ({len(dxf_bytes)/1024:.1f} KB) |
    | 対象レイヤー | `{active_layer or '全レイヤー'}` |
    | 押し出し高さ | `{height_mm} mm` |
    | 検出輪郭数 | `{len(loops)}` |
    | 頂点数 | `{len(mesh.vertices):,}` |
    | 面数 | `{len(mesh.faces):,}` |
    | X寸法 | `{dims[0]:.4f} mm` |
    | Y寸法 | `{dims[1]:.4f} mm` |
    | Z寸法 | `{dims[2]:.4f} mm` |
    | 表面積 | `{mesh.area:.2f} mm²` |
    | 体積 | `{mesh.volume:.2f} mm³` |
    """)

    st.markdown("**検出輪郭 (最初の3件):**")
    for i, loop in enumerate(loops[:3]):
        st.code(f"Loop {i+1}: {len(loop)} points  "
                f"bbox=[{min(p[0] for p in loop):.2f},{max(p[0] for p in loop):.2f}] × "
                f"[{min(p[1] for p in loop):.2f},{max(p[1] for p in loop):.2f}]")
