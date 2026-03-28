import os
import sys
import argparse
import json
import ezdxf
import math
import subprocess
from datetime import datetime
from collections import defaultdict

# --- Geometry Utilities ---

def get_distance(p1, p2):
    return math.sqrt(sum((p1[i] - p2[i])**2 for i in range(len(p1))))

def snap_point(point, grid_size):
    return tuple(round(coord / grid_size) * grid_size for coord in point)

class DXFProcessor:
    def __init__(self, input_path, output_dir, dedup_tol=0.001, snap_tol=0.02):
        self.input_path = input_path
        self.output_dir = output_dir
        self.dedup_tol = dedup_tol
        self.snap_tol = snap_tol
        self.doc = ezdxf.readfile(input_path)
        self.msp = self.doc.modelspace()
        self.log_data = {"layers": {}, "timestamp": datetime.now().isoformat()}

    def parse_thickness_from_name(self, name, default):
        # Try to find something like "PART_5mm" or "T3.2"
        import re
        match = re.search(r'([0-9]*\.?[0-9]+)\s*mm', name, re.IGNORECASE)
        if match:
            return float(match.group(1))
        match = re.search(r'T\s*([0-9]*\.?[0-9]+)', name, re.IGNORECASE)
        if match:
            return float(match.group(1))
        return default

    def process(self, default_thickness=10.0, layer_configs=None):
        if layer_configs is None:
            layer_configs = {}

        os.makedirs(self.output_dir, exist_ok=True)
        layers = self.group_by_layer()
        processed_layers = []   # tracks {name, dxf_path, entities} for reconstruction
        successful_steps = []   # tracks step paths for layers that produced STEP files

        layer_names = list(layers.keys())
        n_layers = len(layer_names)
        print(f"[DXF loaded] {n_layers} layers: {', '.join(layer_names)}", flush=True)

        for layer_idx, (layer_name, entities) in enumerate(layers.items(), 1):
            # Get thickness for this layer
            thickness = layer_configs.get(layer_name)
            if thickness is None:
                thickness = self.parse_thickness_from_name(layer_name, default_thickness)

            print(f"[Layer {layer_idx}/{n_layers}] {layer_name} - thickness {thickness}mm", flush=True)
            cleaned_entities = self.clean_geometry(entities)
            if not cleaned_entities:
                continue

            # Resolve T-junctions: split overlapping collinear segments and
            # remove shared internal edges, leaving only the outer boundary.
            outer_lines, arc_entities, circle_entities = self.resolve_tjunctions(cleaned_entities)
            if not outer_lines and not arc_entities and not circle_entities:
                continue

            # Create sub-DXF for FreeCAD
            layer_dxf = os.path.join(self.output_dir, f"{layer_name}.cleaned.dxf")
            new_doc = ezdxf.new()
            new_doc.header['$INSUNITS'] = 4  # 4 = mm (avoid FreeCAD 1000x scale from INSUNITS=6)
            new_msp = new_doc.modelspace()
            for x1, y1, x2, y2 in outer_lines:
                new_msp.add_line((x1, y1, 0), (x2, y2, 0))
            for e in arc_entities:
                new_msp.add_arc(e.dxf.center, e.dxf.radius, e.dxf.start_angle, e.dxf.end_angle)
            for e in circle_entities:
                new_msp.add_circle(e.dxf.center, e.dxf.radius)
            new_doc.saveas(layer_dxf)
            print(f"[T-junction] {layer_name}: {len(cleaned_entities)} raw → {len(outer_lines)} outer edges + {len(arc_entities)} arcs + {len(circle_entities)} circles", flush=True)

            # Track layer for multi-view reconstruction (original entities for bbox)
            processed_layers.append({
                'name': layer_name,
                'dxf_path': layer_dxf,
                'entities': entities,
            })

            # Generate FreeCAD Script
            step_path = os.path.join(self.output_dir, f"{layer_name}.step")
            fc_script = self.generate_freecad_script(layer_dxf, step_path, thickness)
            script_path = os.path.join(self.output_dir, f"{layer_name}.py")
            with open(script_path, 'w', encoding='utf-8') as f:
                f.write(fc_script)

            print(f"[FreeCAD] STEP generation for {layer_name} ...", flush=True)
            rc, msg = self.execute_freecad(script_path)
            step_exists = os.path.exists(step_path)
            layer_log = {
                "entities": len(cleaned_entities),
                "thickness": thickness,
                "status": "done" if step_exists else "failed",
                "freecad_msg": msg[:500] if not step_exists else ""
            }

            # Generate third-angle projection PNG if STEP was created
            if step_exists:
                successful_steps.append(step_path)
                print(f"[FreeCAD] STEP done - rendering preview for {layer_name} ...", flush=True)
                png_path = os.path.join(self.output_dir, f"{layer_name}_views.png")
                png_rc, png_msg = self.render_step_views(step_path, png_path, layer_name)
                layer_log["png"] = os.path.basename(png_path) if os.path.exists(png_path) else None
                if not os.path.exists(png_path):
                    layer_log["png_error"] = png_msg[:300]

            self.log_data["layers"][layer_name] = layer_log

        with open(os.path.join(self.output_dir, "build_log.json"), 'w') as f:
            json.dump(self.log_data, f, indent=2)

        # Multi-view 3D reconstruction: intersect front/top/right slabs
        if len(successful_steps) >= 2:
            self.reconstruct_multiview(processed_layers)

    def process_manual(self, view_assignments):
        """Reconstruct 3D from 2D views using intersection."""
        print("Manual Mode: Reconstructing from multi-view assignments...")
        os.makedirs(self.output_dir, exist_ok=True)
        
        fc_script = self.generate_manual_reconstruction_script(self.input_path, view_assignments)
        script_path = os.path.join(self.output_dir, "manual_reconstruct.py")
        with open(script_path, 'w', encoding='utf-8') as f:
            f.write(fc_script)
            
        self.execute_freecad(script_path)
        self.log_data["manual_reconstruction"] = "started"

    def generate_manual_reconstruction_script(self, dxf_path, assignments):
        dxf_path = dxf_path.replace('\\', '/')
        step_path = os.path.join(self.output_dir, "reconstructed.step").replace('\\', '/')
        
        return f"""
import FreeCAD as App
import Part
import importDXF

doc = App.newDocument("ManualReconstruction")
importDXF.insert("{dxf_path}", "ManualReconstruction")

views = {json.dumps(assignments)}
extrusions = []

for i, view in enumerate(views):
    v_type = view['type']
    
    # 1. Front (XY) -> Extrude Z
    if v_type == 'front':
        shape = Part.makeCompound([obj.Shape for obj in doc.Objects])
        ext = shape.extrude(App.Vector(0,0, 100))
        extrusions.append(ext)
    
    # 2. Side (YZ) -> Extrude X
    elif v_type == 'side':
        shape = Part.makeCompound([obj.Shape for obj in doc.Objects])
        shape.rotate(App.Vector(0,0,0), App.Vector(0,1,0), 90)
        ext = shape.extrude(App.Vector(100,0,0))
        extrusions.append(ext)

if len(extrusions) >= 2:
    result = extrusions[0]
    for other in extrusions[1:]:
        result = result.common(other)
    result.exportStep("{step_path}")
    print("Manual reconstruction complete.")
else:
    print("Need at least 2 views for reconstruction.")
"""

    def group_by_layer(self):
        layers = defaultdict(list)
        for e in self.msp:
            layers[e.dxf.layer].append(e)
        return layers

    def clean_geometry(self, entities):
        # 1. Dedup
        seen = set()
        unique = []
        for e in entities:
            if e.dxftype() == 'LINE':
                # Normalize line endpoints
                p1, p2 = sorted([snap_point(e.dxf.start, self.dedup_tol), snap_point(e.dxf.end, self.dedup_tol)])
                if (p1, p2) not in seen:
                    seen.add((p1, p2))
                    unique.append(e)
            else:
                unique.append(e) # Basic passthrough for ARCs etc.
        return unique

    def resolve_tjunctions(self, entities, tol=0.02):
        """
        Fix T-junction topology: when a DXF profile is drawn as overlapping
        rectangles (e.g. an L-shape encoded as two touching boxes), edge segments
        share a common interior point rather than a common endpoint.

        Algorithm:
          1. Collect all LINE endpoints.
          2. For each LINE segment, check whether any endpoint lies strictly on
             its interior. If so, split the segment there.
          3. Count occurrences of each sub-segment (by normalised key).
             Segments that appear EXACTLY ONCE are outer-boundary edges.
             Segments appearing 2+ times are shared internal edges — remove them.

        Returns (line_segs, arc_entities):
          line_segs   – list of (x1, y1, x2, y2) float tuples (outer boundary)
          arc_entities – original ARC entity objects (unchanged)
        """
        line_raw = []
        arc_entities = []
        circle_entities = []
        for e in entities:
            if e.dxftype() == 'LINE':
                s, en = e.dxf.start, e.dxf.end
                line_raw.append((float(s.x), float(s.y), float(en.x), float(en.y)))
            elif e.dxftype() == 'ARC':
                arc_entities.append(e)
            elif e.dxftype() == 'CIRCLE':
                circle_entities.append(e)

        # All endpoints (used as potential split points)
        endpoints = set()
        for x1, y1, x2, y2 in line_raw:
            endpoints.add((x1, y1))
            endpoints.add((x2, y2))

        def split_param(px, py, x1, y1, x2, y2):
            """Return t in (tol, 1-tol) if (px,py) lies strictly on seg interior."""
            dx, dy = x2 - x1, y2 - y1
            L2 = dx * dx + dy * dy
            if L2 < 1e-12:
                return None
            t = ((px - x1) * dx + (py - y1) * dy) / L2
            if t <= tol or t >= 1.0 - tol:
                return None
            # Perpendicular distance must be within tolerance
            dist = abs((px - x1) * dy - (py - y1) * dx) / math.sqrt(L2)
            if dist > tol:
                return None
            return t

        # Split every segment at all interior endpoint hits
        split_segs = []
        for x1, y1, x2, y2 in line_raw:
            ts = [0.0, 1.0]
            for px, py in endpoints:
                t = split_param(px, py, x1, y1, x2, y2)
                if t is not None:
                    ts.append(t)
            ts = sorted(set(ts))
            for i in range(len(ts) - 1):
                t0, t1 = ts[i], ts[i + 1]
                px0 = x1 + (x2 - x1) * t0;  py0 = y1 + (y2 - y1) * t0
                px1 = x1 + (x2 - x1) * t1;  py1 = y1 + (y2 - y1) * t1
                split_segs.append((px0, py0, px1, py1))

        # Count occurrences of each normalised segment
        def seg_key(x1, y1, x2, y2):
            g = tol
            a = (round(x1 / g) * g, round(y1 / g) * g)
            b = (round(x2 / g) * g, round(y2 / g) * g)
            return (min(a, b), max(a, b))

        from collections import Counter
        counts = Counter(seg_key(*s) for s in split_segs)

        # Keep only outer-boundary edges (appear exactly once)
        seen_keys = set()
        outer_segs = []
        for s in split_segs:
            k = seg_key(*s)
            if k not in seen_keys and counts[k] == 1:
                seen_keys.add(k)
                outer_segs.append(s)

        return outer_segs, arc_entities, circle_entities

    def _get_layer_bbox(self, entities):
        """Calculate bounding box (cx, cy, xspan, yspan) from ezdxf entities."""
        xs, ys = [], []
        for e in entities:
            if e.dxftype() == 'LINE':
                xs.extend([e.dxf.start[0], e.dxf.end[0]])
                ys.extend([e.dxf.start[1], e.dxf.end[1]])
            elif e.dxftype() == 'ARC':
                xs.extend([e.dxf.center[0] - e.dxf.radius, e.dxf.center[0] + e.dxf.radius])
                ys.extend([e.dxf.center[1] - e.dxf.radius, e.dxf.center[1] + e.dxf.radius])
        if not xs:
            return None
        xmin, xmax = min(xs), max(xs)
        ymin, ymax = min(ys), max(ys)
        return {
            'cx': (xmin + xmax) / 2,
            'cy': (ymin + ymax) / 2,
            'xspan': xmax - xmin,
            'yspan': ymax - ymin,
        }

    def _assign_views_auto(self, layer_data):
        """Assign front/top/right view roles based on 2D bounding box layout.

        layer_data: list of {'name': str, 'bb': dict from _get_layer_bbox()}
        Returns: {'layer_name': 'front'|'top'|'right'}
        Logic: layers sharing the dominant Y-center row → front (min X) and right (max X);
               layers with a different Y-center → top.
        """
        if not layer_data:
            return {}
        if len(layer_data) == 1:
            return {layer_data[0]['name']: 'front'}

        cys = [d['bb']['cy'] for d in layer_data]
        cy_range = max(cys) - min(cys)

        if cy_range < 1e-6:
            # All on same row — sort by X
            sorted_data = sorted(layer_data, key=lambda d: d['bb']['cx'])
            result = {}
            if len(sorted_data) >= 1:
                result[sorted_data[0]['name']] = 'front'
            if len(sorted_data) >= 2:
                result[sorted_data[-1]['name']] = 'right'
            return result

        # Cluster by Y with tolerance = 10% of Y range
        tol = max(cy_range * 0.1, 1.0)
        clusters = []
        for d in layer_data:
            cy = d['bb']['cy']
            placed = False
            for cluster in clusters:
                if abs(cy - cluster['mean_cy']) <= tol:
                    cluster['items'].append(d)
                    cluster['mean_cy'] = sum(x['bb']['cy'] for x in cluster['items']) / len(cluster['items'])
                    placed = True
                    break
            if not placed:
                clusters.append({'mean_cy': cy, 'items': [d]})

        # Largest cluster = front/right row
        clusters.sort(key=lambda c: len(c['items']), reverse=True)
        same_row = sorted(clusters[0]['items'], key=lambda d: d['bb']['cx'])
        diff_rows = [item for c in clusters[1:] for item in c['items']]

        view_map = {}
        if len(same_row) >= 1:
            view_map[same_row[0]['name']] = 'front'
        if len(same_row) >= 2:
            view_map[same_row[-1]['name']] = 'right'
        for d in diff_rows:
            view_map[d['name']] = 'top'

        return view_map

    def _to_container_path(self, windows_path):
        """Convert Windows host path to Linux container path."""
        p = windows_path.replace('\\', '/')
        p = p.replace('D:/Clawdbot_Docker_20260125/data/workspace', '/home/node/clawd')
        return p

    def generate_freecad_script(self, dxf_path, step_path, thickness):
        # Convert Windows paths to Linux container paths for use inside FreeCAD
        dxf_path = self._to_container_path(dxf_path)
        step_path = self._to_container_path(step_path)
        fcstd_path = step_path[:-5] + ".FCStd" if step_path.lower().endswith(".step") else step_path + ".FCStd"

        return f"""
import FreeCAD as App
import Part
import importDXF

doc = App.newDocument("DXFImport")
importDXF.insert("{dxf_path}", "DXFImport")

# Collect all edges from imported objects
edges = []
for obj in doc.Objects:
    if hasattr(obj, "Shape"):
        edges.extend(obj.Shape.Edges)

if edges:
    try:
        sorted_edge_groups = Part.sortEdges(edges)
        faces = []
        for edge_group in sorted_edge_groups:
            try:
                wire = Part.Wire(edge_group)
                if wire.isClosed():
                    face = Part.Face(wire)
                    faces.append(face)
            except Exception as we:
                print(f"Wire/Face error: {{we}}")

        if faces:
            # Extrude each closed face to a solid, then fuse all solids.
            # Using makeCompound().extrude() is WRONG: it creates separate
            # unjoined shells instead of a unified solid (e.g. L-shape from
            # two overlapping rectangles would give two separate boxes).
            solids = []
            for f in faces:
                try:
                    solids.append(f.extrude(App.Vector(0, 0, {thickness})))
                except Exception as se:
                    print(f"Extrude error: {{se}}")
            if solids:
                result = solids[0]
                for s in solids[1:]:
                    result = result.fuse(s)
                # Clean up coplanar face splits from Boolean fuse
                try:
                    cleaned = result.removeSplitter()
                    if cleaned.isValid() and getattr(cleaned, "Volume", 0) > 0:
                        result = cleaned
                        print(f"removeSplitter: {{len(result.Faces)}} faces")
                except Exception as rse:
                    print(f"removeSplitter skipped: {{rse}}")
                result.exportStep("{step_path}")
                try:
                    out_doc = App.newDocument("LayerModel")
                    obj = out_doc.addObject("Part::Feature", "LayerSolid")
                    obj.Shape = result
                    out_doc.recompute()
                    out_doc.saveAs("{fcstd_path}")
                    print(f"Saved FCStd: {fcstd_path}")
                except Exception as fce:
                    print(f"FCStd save failed: {{fce}}")
                print(f"Exported: {step_path}  faces={{len(result.Faces)}}")
            else:
                print("Extrusion failed for all faces")
        else:
            print("No closed faces found — check if DXF outlines form closed loops")
    except Exception as e:
        print(f"Error building solid: {{e}}")
else:
    print("No edges found in {dxf_path}")
"""

    def generate_reconstruction_script(self, view_map, combined_step):
        """Generate FreeCAD script for multi-view 3D reconstruction via slab intersection.

        Uses analytical B-Rep approach:
        - Edges are kept as-is (LINE -> Part.Line, ARC -> Part.Circle) — no discretization
        - transformGeometry(matrix) maps 2D DXF plane to the correct 3D view plane
        - removeSplitter() merges coplanar/same-surface faces into clean solid faces

        view_map: {'front': '/linux/path/Layer.cleaned.dxf', 'top': '...', 'right': '...'}
        combined_step: host path for the output combined.step
        """
        c_combined = self._to_container_path(combined_step)
        c_fcstd = c_combined[:-5] + ".FCStd" if c_combined.lower().endswith(".step") else c_combined + ".FCStd"

        views_list_str = "[\n"
        for view_type, dxf_path in view_map.items():
            c_path = self._to_container_path(dxf_path)
            views_list_str += "    ('" + view_type + "', '" + c_path + "'),\n"
        views_list_str += "]\n"

        script = (
            "import FreeCAD as App\n"
            "import Part\n"
            "\n"
            "def view_matrix(view_type, cx, cy):\n"
            "    \"\"\"Return (App.Matrix, ev_pos, ev_neg) that maps DXF-XY plane to 3D view plane.\n"
            "    All matrices are proper rotations (det=+1) to avoid face-normal inversion.\n"
            "    front : DXF(x,y,0) -> 3D( x-cx,     0, y-cy)  face in XZ, extrude +/-Y\n"
            "    top   : DXF(x,y,0) -> 3D( x-cx, y-cy,    0)  face in XY, extrude +/-Z\n"
            "    right : DXF(x,y,0) -> 3D(    0, x-cx, y-cy)  face in YZ, extrude +/-X\n"
            "    \"\"\"\n"
            "    m = App.Matrix()\n"
            "    if view_type == 'front':\n"
            "        m.A11=1;  m.A12=0;  m.A13=0;  m.A14=-cx\n"
            "        m.A21=0;  m.A22=0;  m.A23=-1; m.A24=0\n"
            "        m.A31=0;  m.A32=1;  m.A33=0;  m.A34=-cy\n"
            "        m.A41=0;  m.A42=0;  m.A43=0;  m.A44=1\n"
            "        return m, App.Vector(0, 1, 0), App.Vector(0, -1, 0)\n"
            "    elif view_type == 'top':\n"
            "        m.A11=1;  m.A12=0;  m.A13=0;  m.A14=-cx\n"
            "        m.A21=0;  m.A22=1;  m.A23=0;  m.A24=-cy\n"
            "        m.A31=0;  m.A32=0;  m.A33=1;  m.A34=0\n"
            "        m.A41=0;  m.A42=0;  m.A43=0;  m.A44=1\n"
            "        return m, App.Vector(0, 0, 1), App.Vector(0, 0, -1)\n"
            "    elif view_type == 'right':\n"
            "        m.A11=0;  m.A12=0;  m.A13=1;  m.A14=0\n"
            "        m.A21=1;  m.A22=0;  m.A23=0;  m.A24=-cx\n"
            "        m.A31=0;  m.A32=1;  m.A33=0;  m.A34=-cy\n"
            "        m.A41=0;  m.A42=0;  m.A43=0;  m.A44=1\n"
            "        return m, App.Vector(1, 0, 0), App.Vector(-1, 0, 0)\n"
            "    return None, None, None\n"
            "\n"
            "def build_slab(dxf_path, view_type, doc_name):\n"
            "    \"\"\"Build an infinite slab for one view using analytical B-Rep (no discretize).\"\"\"\n"
            "    import importDXF\n"
            "    doc = App.newDocument(doc_name)\n"
            "    importDXF.insert(dxf_path, doc_name)\n"
            "    edges = []\n"
            "    for obj in doc.Objects:\n"
            "        if hasattr(obj, 'Shape'):\n"
            "            edges.extend(obj.Shape.Edges)\n"
            "    if not edges:\n"
            "        print('No edges in', dxf_path)\n"
            "        return None\n"
            "    # Bounding box for centering and extrusion length\n"
            "    bb = Part.Compound(edges).BoundBox\n"
            "    cx = (bb.XMax + bb.XMin) / 2\n"
            "    cy = (bb.YMax + bb.YMin) / 2\n"
            "    ext = max(bb.XMax - bb.XMin, bb.YMax - bb.YMin, 1.0) * 3\n"
            "    m, ev_pos, ev_neg = view_matrix(view_type, cx, cy)\n"
            "    if m is None:\n"
            "        return None\n"
            "    ev_pos = App.Vector(ev_pos.x * ext, ev_pos.y * ext, ev_pos.z * ext)\n"
            "    ev_neg = App.Vector(ev_neg.x * ext, ev_neg.y * ext, ev_neg.z * ext)\n"
            "    # Sort edges into closed loops then build analytical faces\n"
            "    try:\n"
            "        sorted_groups = Part.sortEdges(edges)\n"
            "    except Exception as e:\n"
            "        print('sortEdges failed:', e)\n"
            "        return None\n"
            "    solids = []\n"
            "    for group in sorted_groups:\n"
            "        try:\n"
            "            wire = Part.Wire(group)\n"
            "            if not wire.isClosed():\n"
            "                continue\n"
            "            # Build face in the original DXF XY-plane\n"
            "            face_2d = Part.Face(wire)\n"
            "            # Map to correct 3D view plane (keeps LINE as plane, ARC as cylinder)\n"
            "            face_3d = face_2d.transformGeometry(m)\n"
            "            sol_pos = face_3d.extrude(ev_pos)\n"
            "            sol_neg = face_3d.extrude(ev_neg)\n"
            "            solids.append(sol_pos.fuse(sol_neg))\n"
            "        except Exception as e:\n"
            "            print('Group error for', view_type, ':', e)\n"
            "    if not solids:\n"
            "        print('No solids built for', view_type)\n"
            "        return None\n"
            "    result = solids[0]\n"
            "    for s in solids[1:]:\n"
            "        result = result.fuse(s)\n"
            "    print('Slab ready for', view_type,\n"
            "          '- faces:', len(result.Faces), '- volume:', result.Volume)\n"
            "    return result\n"
            "\n"
            "views_info = " + views_list_str +
            "\n"
            "slabs = []\n"
            "for idx, (view_type, dxf_path) in enumerate(views_info):\n"
            "    print('Building slab for', view_type, ':', dxf_path)\n"
            "    slab = build_slab(dxf_path, view_type, 'slab_' + str(idx))\n"
            "    if slab is not None:\n"
            "        slabs.append(slab)\n"
            "    else:\n"
            "        print('Slab FAILED for', view_type)\n"
            "\n"
            "print('Total slabs built:', len(slabs))\n"
            "\n"
            "if len(slabs) >= 2:\n"
            "    try:\n"
            "        result = slabs[0]\n"
            "        for other in slabs[1:]:\n"
            "            result = result.common(other)\n"
            "        vol = getattr(result, 'Volume', 0)\n"
            "        if vol > 0:\n"
            "            print('Intersection ok - faces before cleanup:', len(result.Faces))\n"
            "            # Step 1: merge coplanar/same-curvature faces\n"
            "            try:\n"
            "                cleaned = result.removeSplitter()\n"
            "                if getattr(cleaned, 'Volume', 0) > 0:\n"
            "                    result = cleaned\n"
            "                    print('removeSplitter done - faces:', len(result.Faces))\n"
            "            except Exception as e:\n"
            "                print('removeSplitter skipped:', e)\n"
            "            # Step 2: upgrade SurfaceOfExtrusion -> Plane / Cylinder\n"
            "            # Reconstruct each face from its ordered vertices as pure 3D lines,\n"
            "            # so Part.Face() can detect planarity and assign a Plane surface.\n"
            "            try:\n"
            "                upgraded_faces = []\n"
            "                for face in result.Faces:\n"
            "                    stype = type(face.Surface).__name__\n"
            "                    if 'Extrusion' in stype:\n"
            "                        try:\n"
            "                            pts = [v.Point for v in face.OuterWire.OrderedVertexes]\n"
            "                            new_edges = [Part.makeLine(pts[i], pts[(i+1) % len(pts)])\n"
            "                                         for i in range(len(pts))]\n"
            "                            new_wire = Part.Wire(Part.sortEdges(new_edges)[0])\n"
            "                            nf = Part.Face(new_wire)\n"
            "                            upgraded_faces.append(nf)\n"
            "                        except Exception as fe:\n"
            "                            print('  face rebuild failed, keeping original:', fe)\n"
            "                            upgraded_faces.append(face)\n"
            "                    else:\n"
            "                        upgraded_faces.append(face)\n"
            "                shell = Part.Shell(upgraded_faces)\n"
            "                upgraded = Part.Solid(shell)\n"
            "                if getattr(upgraded, 'Volume', 0) > 0:\n"
            "                    result = upgraded\n"
            "                    ftypes = {type(f.Surface).__name__ for f in result.Faces}\n"
            "                    print('Face upgrade done - types:', ftypes)\n"
            "                    # Step 3: second removeSplitter to merge coplanar Plane faces\n"
            "                    try:\n"
            "                        cleaned2 = result.removeSplitter()\n"
            "                        if getattr(cleaned2, 'Volume', 0) > 0:\n"
            "                            result = cleaned2\n"
            "                            print('2nd removeSplitter - faces:', len(result.Faces))\n"
            "                    except Exception as e2:\n"
            "                        print('2nd removeSplitter skipped:', e2)\n"
            "            except Exception as e:\n"
            "                print('Face upgrade skipped:', e)\n"
            "            result.exportStep('" + c_combined + "')\n"
            "            try:\n"
            "                out_doc = App.newDocument('ReconstructionResult')\n"
            "                obj = out_doc.addObject('Part::Feature', 'CombinedSolid')\n"
            "                obj.Shape = result\n"
            "                out_doc.recompute()\n"
            "                out_doc.saveAs('" + c_fcstd + "')\n"
            "                print('Saved FCStd:', '" + c_fcstd + "')\n"
            "            except Exception as fce:\n"
            "                print('FCStd save failed:', fce)\n"
            "            print('Reconstruction complete - volume:', result.Volume,\n"
            "                  '- faces:', len(result.Faces))\n"
            "        else:\n"
            "            print('Intersection empty, falling back to compound')\n"
            "            Part.makeCompound(slabs).exportStep('" + c_combined + "')\n"
            "    except Exception as e:\n"
            "        print('Intersection failed, compound fallback:', e)\n"
            "        Part.makeCompound(slabs).exportStep('" + c_combined + "')\n"
            "elif len(slabs) == 1:\n"
            "    slabs[0].exportStep('" + c_combined + "')\n"
            "    print('Only one slab, exported as-is')\n"
            "else:\n"
            "    print('No slabs built - reconstruction failed')\n"
        )
        return script

    def generate_png_render_script(self, step_path, png_path, layer_name):
        """Generate a FreeCAD Python script that renders third-angle projection PNGs."""
        c_step = self._to_container_path(step_path)
        c_png  = self._to_container_path(png_path)
        safe_layer = layer_name.replace("'", "\\'").replace('"', '\\"')

        # Build script using string concatenation to avoid f-string brace conflicts
        script = (
            "import FreeCAD as App\n"
            "import Part\n"
            "import matplotlib\n"
            "matplotlib.use('Agg')\n"
            "import matplotlib.pyplot as plt\n"
            "import matplotlib.gridspec as gridspec\n"
            "\n"
            "shape = Part.read('" + c_step + "')\n"
            "bb = shape.BoundBox\n"
            "cx = (bb.XMax + bb.XMin) / 2\n"
            "cy = (bb.YMax + bb.YMin) / 2\n"
            "cz = (bb.ZMax + bb.ZMin) / 2\n"
            "\n"
            "segments = []\n"
            "for edge in shape.Edges:\n"
            "    try:\n"
            "        pts = edge.discretize(50)\n"
            "        if pts:\n"
            "            segments.append([(p.x - cx, p.y - cy, p.z - cz) for p in pts])\n"
            "    except Exception:\n"
            "        pass\n"
            "\n"
            "def draw_view(ax, segs_2d, title, flip_y=False):\n"
            "    for seg in segs_2d:\n"
            "        if len(seg) >= 2:\n"
            "            xs = [p[0] for p in seg]\n"
            "            ys = [p[1] for p in seg]\n"
            "            ax.plot(xs, ys, 'k-', linewidth=0.8, solid_capstyle='round')\n"
            "    ax.set_aspect('equal', adjustable='datalim')\n"
            "    ax.margins(0.12)\n"
            "    # Ensure minimum visible height (for thin extruded plates)\n"
            "    ax.autoscale()\n"
            "    xlim = ax.get_xlim()\n"
            "    ylim = ax.get_ylim()\n"
            "    xspan = max(xlim[1] - xlim[0], 1e-6)\n"
            "    yspan = ylim[1] - ylim[0]\n"
            "    if yspan < xspan * 0.08:\n"
            "        mid_y = (ylim[0] + ylim[1]) / 2\n"
            "        ax.set_ylim(mid_y - xspan * 0.12, mid_y + xspan * 0.12)\n"
            "    ax.set_title(title, fontsize=9, pad=5)\n"
            "    ax.set_facecolor('#F5F5F5')\n"
            "    ax.tick_params(left=False, bottom=False, labelleft=False, labelbottom=False)\n"
            "    for spine in ax.spines.values():\n"
            "        spine.set_color('#AAAAAA')\n"
            "        spine.set_linewidth(0.5)\n"
            "    if flip_y:\n"
            "        ax.invert_yaxis()\n"
            "\n"
            "# Third-angle projection: Top=XY(flip Y), Front=XZ, Right=YZ\n"
            "top_segs   = [[(p[0],  p[1]) for p in s] for s in segments]\n"
            "front_segs = [[(p[0],  p[2]) for p in s] for s in segments]\n"
            "right_segs = [[(p[1],  p[2]) for p in s] for s in segments]\n"
            "\n"
            "fig = plt.figure(figsize=(14, 10), facecolor='white')\n"
            "gs = gridspec.GridSpec(2, 2, figure=fig, hspace=0.4, wspace=0.3)\n"
            "\n"
            "ax_top   = fig.add_subplot(gs[0, 0])\n"
            "ax_sym   = fig.add_subplot(gs[0, 1])\n"
            "ax_front = fig.add_subplot(gs[1, 0])\n"
            "ax_right = fig.add_subplot(gs[1, 1])\n"
            "\n"
            "draw_view(ax_top,   top_segs,   'Top View  (Hira-Men)', flip_y=True)\n"
            "draw_view(ax_front, front_segs, 'Front View  (Sho-Men)')\n"
            "draw_view(ax_right, right_segs, 'Right Side View  (Migi-Sokumen)')\n"
            "\n"
            "ax_sym.axis('off')\n"
            "ax_sym.set_facecolor('#FAFAFA')\n"
            "ax_sym.text(0.5, 0.62, 'Third Angle Projection',\n"
            "            ha='center', va='center', transform=ax_sym.transAxes,\n"
            "            fontsize=12, fontweight='bold', color='#333333')\n"
            "ax_sym.text(0.5, 0.45, 'Daisan-kakuho', ha='center', va='center',\n"
            "            transform=ax_sym.transAxes, fontsize=10, color='#555555')\n"
            "ax_sym.text(0.5, 0.28, 'ISO E  /  ANSI  /  JIS', ha='center', va='center',\n"
            "            transform=ax_sym.transAxes, fontsize=8, color='#888888')\n"
            "\n"
            "fig.suptitle('" + safe_layer + "  —  STEP Views', fontsize=13, fontweight='bold', y=1.01)\n"
            "plt.savefig('" + c_png + "', dpi=150, bbox_inches='tight', facecolor='white')\n"
            "plt.close()\n"
            "print('PNG saved: " + c_png + "')\n"
        )
        return script

    def render_step_views(self, step_path, png_path, layer_name):
        """Run FreeCAD to render third-angle projection PNG from a STEP file."""
        render_script_path = step_path.replace('.step', '_render.py')
        script = self.generate_png_render_script(step_path, png_path, layer_name)
        with open(render_script_path, 'w', encoding='utf-8') as f:
            f.write(script)
        rc, msg = self.execute_freecad(render_script_path)
        return rc, msg

    def reconstruct_multiview(self, processed_layers):
        """Assign front/top/right views, build slabs, intersect, export combined.step + PNG."""
        print("Multi-view reconstruction starting...")

        layer_data = []
        for pl in processed_layers:
            bb = self._get_layer_bbox(pl['entities'])
            if bb:
                layer_data.append({'name': pl['name'], 'bb': bb})

        if len(layer_data) < 2:
            print("Not enough layers with bounding boxes for view assignment")
            return

        view_assignments = self._assign_views_auto(layer_data)
        print(f"View assignments: {view_assignments}")

        # Build {view_type: dxf_path} — first assigned layer wins per view type
        view_map = {}
        for pl in processed_layers:
            vt = view_assignments.get(pl['name'])
            if vt and vt not in view_map:
                view_map[vt] = pl['dxf_path']

        if len(view_map) < 2:
            print(f"Not enough distinct views (got {len(view_map)}), skipping reconstruction")
            return

        print(f"View map: {view_map}")

        combined_step = os.path.join(self.output_dir, "combined.step")
        script = self.generate_reconstruction_script(view_map, combined_step)
        script_path = os.path.join(self.output_dir, "reconstruct_multiview.py")
        with open(script_path, 'w', encoding='utf-8') as f:
            f.write(script)

        print("[FreeCAD] Running multi-view reconstruction script ...", flush=True)
        rc, msg = self.execute_freecad(script_path)

        if os.path.exists(combined_step):
            print("[FreeCAD] Reconstruction STEP done - rendering combined preview ...", flush=True)
            combined_png = os.path.join(self.output_dir, "combined_views.png")
            self.render_step_views(combined_step, combined_png, "Combined 3D Reconstruction")
            self.log_data["combined_step"] = os.path.basename(combined_step)
            self.log_data["combined_png"] = (
                os.path.basename(combined_png) if os.path.exists(combined_png) else None
            )
        else:
            print(f"Combined STEP not generated. rc={rc}")
            self.log_data["combined_step"] = None
            self.log_data["combined_error"] = msg[:300] if msg else "Unknown error"

        # Re-save build_log.json with combined step info
        with open(os.path.join(self.output_dir, "build_log.json"), 'w') as f:
            json.dump(self.log_data, f, indent=2)

    def execute_freecad(self, script_path):
        container_name = "clawstack-unified-clawdbot-gateway-1"
        linux_script_path = self._to_container_path(script_path)

        # Use bash -c to avoid MSYS/Git Bash path conversion on Windows host
        cmd = ["docker", "exec", container_name, "bash", "-c", f"FreeCADCmd '{linux_script_path}'"]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            if result.returncode != 0:
                print(f"FreeCAD exited with code {result.returncode}: {result.stderr}")
                return result.returncode, result.stderr
            print(result.stdout)
            return 0, result.stdout
        except subprocess.TimeoutExpired:
            print("FreeCAD timed out after 120s")
            return -1, "Timeout"
        except Exception as e:
            print(f"FreeCAD launch error: {e}")
            return -1, str(e)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--thickness", type=float, default=10.0)
    parser.add_argument("--layer-configs", type=str, default="{}")
    parser.add_argument("--manual-mode", action="store_true")
    parser.add_argument("--view-assignments", type=str, default="[]")
    args = parser.parse_args()
    
    processor = DXFProcessor(args.input, args.output)
    
    if args.manual_mode:
        assignments = json.loads(args.view_assignments)
        processor.process_manual(assignments)
    else:
        layer_configs = {}
        try:
            layer_configs = json.loads(args.layer_configs)
        except:
            print(f"Warning: Failed to parse layer-configs: {args.layer_configs}")
        processor.process(args.thickness, layer_configs)
