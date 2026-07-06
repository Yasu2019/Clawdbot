import os
import sys
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import argparse
import json
import ezdxf
import math
import re
import subprocess
from datetime import datetime
from collections import Counter, defaultdict

SHIBOKEN_PATCH = """
# Shiboken import hook patch to prevent console application crashes
import builtins
original_builtins_import = builtins.__import__

def custom_import(name, *args, **kwargs):
    if name == "ImportGui":
        raise ImportError("Mocked ImportError for ImportGui")
    try:
        res = original_builtins_import(name, *args, **kwargs)
        try:
            import ctypes
            ctypes.pythonapi.PyErr_Clear()
        except Exception:
            pass
        return res
    except Exception:
        raise

builtins.__import__ = custom_import
"""

# --- Geometry Utilities ---

def get_distance(p1, p2):
    return math.sqrt(sum((p1[i] - p2[i])**2 for i in range(len(p1))))

def snap_point(point, grid_size):
    return tuple(round(coord / grid_size) * grid_size for coord in point)

class DXFProcessor:
    def __init__(self, input_path, output_dir, dedup_tol=0.001, snap_tol=0.02):
        self._last_cluster_pick_mode = None
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

    def process(self, default_thickness=10.0, layer_configs=None, t_junction_tol=0.02):
        if layer_configs is None:
            layer_configs = {}

        os.makedirs(self.output_dir, exist_ok=True)
        layers = self.group_by_layer()
        skip_layers = self._frame_layers_to_skip(layers)
        if skip_layers:
            self.log_data["extrude_frame_layers_skipped"] = sorted(skip_layers)
            print(f"[process] skip frame layers before extrude: {sorted(skip_layers)}", flush=True)
        profile_hole_merges = self._find_profile_hole_layer_merges(layers, skip_layers)
        if profile_hole_merges:
            self.log_data["profile_hole_layer_merge"] = profile_hole_merges
            print(f"[process] profile+hole layer merge map: {profile_hole_merges}", flush=True)
        processed_layers = []   # tracks {name, dxf_path, entities} for reconstruction
        successful_steps = []   # tracks step paths for layers that produced STEP files

        layer_names = [n for n in layers.keys() if n not in skip_layers]
        n_layers = len(layer_names)
        print(f"[DXF loaded] {len(layers)} layers ({n_layers} after frame skip): {', '.join(layer_names)}", flush=True)

        for layer_idx, layer_name in enumerate(layer_names, 1):
            entities = list(layers[layer_name])
            outline_layer = profile_hole_merges.get(layer_name)
            if outline_layer:
                part_bb = self._get_layer_bbox(entities)
                outline_extra = self._extract_enclosing_outline_entities(
                    layers.get(outline_layer) or [],
                    part_bb or {},
                )
                merge_detail = {
                    "outline_layer": outline_layer,
                    "outline_entities_added": len(outline_extra),
                }
                if not outline_extra:
                    merge_detail["outline_skip_reason"] = (
                        "no_enclosing_closed_loop_on_frame_layer"
                    )
                else:
                    entities = entities + outline_extra
                    print(
                        f"[profile+hole] layer {layer_name} <- {len(outline_extra)} outline entities "
                        f"from skipped layer {outline_layer} (closed loop only)",
                        flush=True,
                    )
                self.log_data.setdefault("profile_hole_merge_detail", {})[layer_name] = merge_detail
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
            outer_lines, arc_entities, circle_entities = self.resolve_tjunctions(cleaned_entities, tol=t_junction_tol)
            outer_lines, arc_entities, circle_entities, n_drop = self._keep_largest_connected_cluster(
                outer_lines, arc_entities, circle_entities, tol=t_junction_tol
            )
            if not outer_lines and not arc_entities and not circle_entities:
                continue

            loop_qc = self._evaluate_closed_loop_qc(
                outer_lines,
                circle_entities,
                arc_entities,
                tol=t_junction_tol,
            )
            loop_qc["auxiliary_clusters_dropped"] = n_drop
            if not loop_qc.get("pass"):
                reason = str(loop_qc.get("reason") or "closed_loop_qc_fail")
                print(f"[DXF-QC04c] FAIL layer {layer_name}: {reason}", flush=True)
                self.log_data.setdefault("closed_loop_qc_failures", []).append(
                    {"layer": layer_name, "reason": reason, "qc": loop_qc}
                )
                self.log_data["layers"][layer_name] = {
                    "entities": len(cleaned_entities),
                    "thickness": thickness,
                    "status": "failed",
                    "closed_loop_qc": loop_qc,
                    "freecad_msg": f"DXF-QC04c blocked extrude: {reason}",
                }
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

            # Clean up old output files to prevent stale success readings on new failure
            step_path = os.path.join(self.output_dir, f"{layer_name}.step")
            fcstd_path = os.path.join(self.output_dir, f"{layer_name}.FCStd")
            png_path = os.path.join(self.output_dir, f"{layer_name}_views.png")
            for old_file in [step_path, fcstd_path, png_path]:
                if os.path.exists(old_file):
                    try:
                        os.remove(old_file)
                    except Exception:
                        pass

            # Generate FreeCAD Script
            fc_script = self.generate_freecad_script(layer_dxf, step_path, thickness)
            script_path = os.path.join(self.output_dir, f"{layer_name}.py")
            with open(script_path, 'w', encoding='utf-8') as f:
                f.write(fc_script)

            print(f"[FreeCAD] STEP generation for {layer_name} ...", flush=True)
            rc, msg = self.execute_freecad(script_path)
            step_exists = os.path.exists(step_path)
            holes_cut = 0
            profile_wires = 0
            hole_m = re.search(r"\[hole-cut\] through_holes=(\d+)", msg or "")
            if hole_m:
                holes_cut = int(hole_m.group(1))
            pw_m = re.search(r"\[hole-cut\] profile_wires=(\d+)", msg or "")
            if pw_m:
                profile_wires = int(pw_m.group(1))
            ng_multi = "NG_MULTIPLE_PROFILES" in (msg or "")
            layer_log = {
                "entities": len(cleaned_entities),
                "thickness": thickness,
                "status": "done" if step_exists and not ng_multi else "failed",
                "freecad_msg": msg[:500] if (not step_exists or ng_multi) else "",
                "step": os.path.basename(step_path) if step_exists else None,
                "fcstd": os.path.basename(fcstd_path) if os.path.exists(fcstd_path) else None,
            }
            if holes_cut:
                layer_log["holes_cut"] = holes_cut
            if profile_wires:
                layer_log["profile_wires"] = profile_wires
            if ng_multi:
                layer_log["profile_qc"] = {
                    "gate": "NG_MULTIPLE_PROFILES",
                    "pass": False,
                    "profile_wires": profile_wires,
                }
                self.log_data.setdefault("profile_qc_failures", []).append(
                    {"layer": layer_name, "profile_wires": profile_wires}
                )
                step_exists = False
                try:
                    os.remove(step_path)
                except Exception:
                    pass
            elif step_exists and profile_wires > 1:
                layer_log["status"] = "failed"
                layer_log["profile_qc"] = {
                    "gate": "DXF-QC04g",
                    "pass": False,
                    "reason": f"profile_wires={profile_wires}>1 (island-risk)",
                    "profile_wires": profile_wires,
                }
                self.log_data.setdefault("profile_qc_failures", []).append(
                    {"layer": layer_name, "profile_wires": profile_wires}
                )
                step_exists = False
                try:
                    os.remove(step_path)
                except Exception:
                    pass
            circle_n = int(loop_qc.get("circle_count") or 0)
            if step_exists and circle_n >= 3 and holes_cut < 1:
                layer_log["status"] = "failed"
                layer_log["hole_cut_qc"] = {
                    "gate": "DXF-QC04e",
                    "pass": False,
                    "reason": f"circle_count={circle_n} but through_holes_cut=0 (punch-risk)",
                }
                self.log_data.setdefault("hole_cut_qc_failures", []).append(
                    {"layer": layer_name, "circle_count": circle_n, "holes_cut": holes_cut}
                )
                step_exists = False
                try:
                    os.remove(step_path)
                except Exception:
                    pass
            if n_drop:
                layer_log["auxiliary_clusters_dropped"] = n_drop
            if self._last_cluster_pick_mode:
                layer_log["cluster_pick_mode"] = self._last_cluster_pick_mode
            layer_log["closed_loop_qc"] = loop_qc

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

        # Multi-view 3D reconstruction: intersect front/top/right slabs
        self._processed_layers_cache = processed_layers
        if len(successful_steps) >= 2:
            self.reconstruct_multiview(processed_layers)
            if not self.log_data.get("combined_quality_ok"):
                part = self._pick_part_layer_for_combined(processed_layers, successful_steps)
                if part:
                    print(
                        f"[process] multiview failed; fallback single_profile_extrude from layer {part}",
                        flush=True,
                    )
                    self._export_single_layer_combined(part)
        elif len(successful_steps) == 1:
            lone_layer = self._pick_part_layer_for_combined(processed_layers, successful_steps)
            if lone_layer:
                self._export_single_layer_combined(lone_layer)
            else:
                self.log_data["reconstruction_status"] = "frame_only_no_part"
                self.log_data["combined_quality_ok"] = False
                print("[process] only frame-like layer succeeded; no combined export", flush=True)

        with open(os.path.join(self.output_dir, "build_log.json"), 'w') as f:
            json.dump(self.log_data, f, indent=2)

        if self.log_data.get("closed_loop_qc_failures"):
            self.log_data["combined_quality_ok"] = False
            self.log_data["reconstruction_status"] = "closed_loop_qc_fail"
            with open(os.path.join(self.output_dir, "build_log.json"), "w", encoding="utf-8") as f:
                json.dump(self.log_data, f, indent=2)
        if self.log_data.get("hole_cut_qc_failures"):
            self.log_data["combined_quality_ok"] = False
            self.log_data["reconstruction_status"] = "hole_cut_qc_fail"
            with open(os.path.join(self.output_dir, "build_log.json"), "w", encoding="utf-8") as f:
                json.dump(self.log_data, f, indent=2)
        if self.log_data.get("profile_qc_failures"):
            self.log_data["combined_quality_ok"] = False
            self.log_data["reconstruction_status"] = "profile_qc_fail"
            with open(os.path.join(self.output_dir, "build_log.json"), "w", encoding="utf-8") as f:
                json.dump(self.log_data, f, indent=2)

        self._emit_part_manifest(default_thickness)

    def _emit_part_manifest(self, default_thickness: float) -> None:
        try:
            from part_geometry_contract import emit_part_manifest

            path = emit_part_manifest(
                source_dxf=self.input_path,
                output_dir=self.output_dir,
                build_log=self.log_data,
                default_thickness_mm=default_thickness,
            )
            self.log_data["part_manifest"] = os.path.basename(str(path))
            print(f"[manifest] wrote {path}", flush=True)
        except Exception as exc:
            err = str(exc)[:300]
            self.log_data["part_manifest_error"] = err
            print(f"[manifest] error: {err}", flush=True)
        with open(os.path.join(self.output_dir, "build_log.json"), "w", encoding="utf-8") as f:
            json.dump(self.log_data, f, indent=2)

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
        
        return f"""{SHIBOKEN_PATCH}
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

    # T043/5yk-2: annotation linetypes never represent cutting geometry
    # (centerlines, pitch circles, phantom/hidden). DASHED is intentionally
    # NOT listed (can be real hidden edges); BYLAYER/BYBLOCK are kept.
    ANNOTATION_LINETYPES = {
        "CENTER", "CENTERX2", "CENTER2",
        "DASHDOT", "DASHDOTX2", "DASHDOT2",
        "DOT", "DOTX2", "DOT2",
        "DIVIDE", "DIVIDEX2", "DIVIDE2",
        "PHANTOM", "PHANTOMX2", "PHANTOM2",
        "HIDDEN", "HIDDENX2", "HIDDEN2",
        "BORDER", "BORDERX2", "BORDER2",
    }

    def _entity_linetype(self, e) -> str:
        try:
            lt = str(getattr(e.dxf, "linetype", "") or "").upper()
        except Exception:
            return ""
        if lt in ("BYLAYER", "BYBLOCK"):
            return ""
        return lt

    def clean_geometry(self, entities):
        # 0. T043/5yk-2 (2026-07-06): drop annotation-linetype geometry before
        #    topology/QC. S1 evidence: open_endpoints 108->29, part outline
        #    (33600mm2) recovered as closed loop, 23 pitch circles removed.
        filtered = []
        dropped = 0
        for e in entities:
            if e.dxftype() in ("LINE", "ARC", "CIRCLE") and self._entity_linetype(e) in self.ANNOTATION_LINETYPES:
                dropped += 1
                continue
            filtered.append(e)
        if dropped:
            print(f"[linetype-filter] dropped {dropped} annotation-linetype entities (centerlines/pitch circles etc.)", flush=True)
            self.log_data["annotation_linetype_dropped"] = int(self.log_data.get("annotation_linetype_dropped") or 0) + dropped
        entities = filtered
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

    def _polyline_to_line_segments(self, entity, tol=0.02):
        """Expand LWPOLYLINE / POLYLINE into (x1,y1,x2,y2) segments; auto-close if nearly closed."""
        dxftype = entity.dxftype()
        if dxftype == "LWPOLYLINE":
            pts = [(float(x), float(y)) for x, y, *_ in entity.get_points("xy")]
            closed_flag = bool(entity.closed)
        elif dxftype == "POLYLINE":
            pts = [(float(v.dxf.location.x), float(v.dxf.location.y)) for v in entity.vertices()]
            closed_flag = bool(entity.is_closed)
        else:
            return []

        if len(pts) < 2:
            return []

        if len(pts) >= 3 and math.hypot(pts[0][0] - pts[-1][0], pts[0][1] - pts[-1][1]) <= tol:
            pts = pts[:-1]

        if closed_flag and pts:
            pts = pts + [pts[0]]
        elif len(pts) >= 3:
            pts = pts + [pts[0]]

        segs = []
        for i in range(len(pts) - 1):
            x1, y1 = pts[i]
            x2, y2 = pts[i + 1]
            if math.hypot(x2 - x1, y2 - y1) <= tol:
                continue
            segs.append((x1, y1, x2, y2))
        return segs

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
            elif e.dxftype() in ('LWPOLYLINE', 'POLYLINE'):
                line_raw.extend(self._polyline_to_line_segments(e, tol=tol))
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

    def _point_key(self, x, y, tol):
        g = tol
        return (round(x / g) * g, round(y / g) * g)

    def _cluster_line_segments(self, line_segs, tol=0.02):
        from collections import defaultdict

        parent: dict[int, int] = {}

        def find(a: int) -> int:
            parent.setdefault(a, a)
            if parent[a] != a:
                parent[a] = find(parent[a])
            return parent[a]

        def union(a: int, b: int) -> None:
            ra, rb = find(a), find(b)
            if ra != rb:
                parent[rb] = ra

        pt_id: dict[tuple[float, float], int] = {}
        next_id = 0
        clusters: dict[int, list] = defaultdict(list)
        for seg in line_segs:
            x1, y1, x2, y2 = seg
            p1 = self._point_key(x1, y1, tol)
            p2 = self._point_key(x2, y2, tol)
            for p in (p1, p2):
                if p not in pt_id:
                    pt_id[p] = next_id
                    next_id += 1
            union(pt_id[p1], pt_id[p2])
            clusters[find(pt_id[p1])].append(seg)
        return clusters

    def _bbox_of_line_segs(self, segs):
        xs, ys = [], []
        for x1, y1, x2, y2 in segs:
            xs.extend([x1, x2])
            ys.extend([y1, y2])
        return min(xs), min(ys), max(xs), max(ys)

    def _merge_nearby_line_clusters(self, clusters, gap=5.0):
        items = []
        for segs in clusters.values():
            xmin, ymin, xmax, ymax = self._bbox_of_line_segs(segs)
            items.append({"segs": list(segs), "bbox": (xmin, ymin, xmax, ymax)})

        def bboxes_near(b1, b2):
            x1min, y1min, x1max, y1max = b1
            x2min, y2min, x2max, y2max = b2
            dx = max(0.0, max(x2min - x1max, x1min - x2max))
            dy = max(0.0, max(y2min - y1max, y1min - y2max))
            return dx <= gap and dy <= gap

        merged = True
        while merged and len(items) > 1:
            merged = False
            for i in range(len(items)):
                for j in range(i + 1, len(items)):
                    if not bboxes_near(items[i]["bbox"], items[j]["bbox"]):
                        continue
                    items[i]["segs"].extend(items[j]["segs"])
                    items[i]["bbox"] = self._bbox_of_line_segs(items[i]["segs"])
                    items.pop(j)
                    merged = True
                    break
                if merged:
                    break
        return [item["segs"] for item in items]

    def _cluster_area_from_segs(self, segs) -> float:
        xmin, ymin, xmax, ymax = self._bbox_of_line_segs(segs)
        return max(xmax - xmin, 0.0) * max(ymax - ymin, 0.0)

    def _pick_part_cluster_segs(self, merged: list) -> tuple[list, int, str]:
        """Keep one island; drop layout strips and tiny fragments (INC-125 / D3)."""
        if not merged:
            return [], 0, "empty"
        if len(merged) == 1:
            return list(merged[0]), 0, "single"

        metrics: list[tuple[float, float, float, float, list]] = []
        for m in merged:
            xmin, ymin, xmax, ymax = self._bbox_of_line_segs(m)
            w = max(xmax - xmin, 0.0)
            h = max(ymax - ymin, 0.0)
            area = w * h
            aspect = max(w, h) / max(min(w, h), 1e-6)
            metrics.append((area, aspect, w, h, m))

        max_area = max(x[0] for x in metrics)
        candidates: list[tuple[float, list]] = []
        for area, aspect, w, h, m in metrics:
            if area < max_area * 0.08:
                continue
            if aspect > 10.0 and max(w, h) > 120.0:
                continue
            candidates.append((area, m))

        if not candidates:
            for area, aspect, w, h, m in sorted(metrics, key=lambda x: -x[0]):
                if aspect <= 12.0:
                    return list(m), len(merged) - 1, "fallback_largest_compact"
            largest = max(metrics, key=lambda x: x[0])
            return list(largest[4]), len(merged) - 1, "fallback_largest_any"

        pick = max(candidates, key=lambda x: x[0])[1]
        return list(pick), len(merged) - 1, "largest_non_strip_cluster"

    def _keep_largest_connected_cluster(self, line_segs, arc_entities, circle_entities, tol=0.02):
        """Drop auxiliary multiview clusters on the same layer (e.g. P38 layer 7 side view)."""
        if len(line_segs) < 2:
            return line_segs, arc_entities, circle_entities, 0
        raw_clusters = self._cluster_line_segments(line_segs, tol=tol)
        merged = self._merge_nearby_line_clusters(raw_clusters, gap=max(tol * 5, 2.0))
        if len(merged) <= 1:
            self._last_cluster_pick_mode = "single"
            return line_segs, arc_entities, circle_entities, 0

        kept_segs, dropped, mode = self._pick_part_cluster_segs(merged)
        self._last_cluster_pick_mode = mode
        if not kept_segs:
            kept_segs = list(line_segs)
        xmin, ymin, xmax, ymax = self._bbox_of_line_segs(kept_segs)
        x_margin = max(xmax - xmin, 1.0) * 0.05
        y_margin = max(ymax - ymin, 1.0) * 0.05

        def in_window(cx, cy):
            return (xmin - x_margin <= cx <= xmax + x_margin) and (ymin - y_margin <= cy <= ymax + y_margin)

        kept_arcs = [
            a for a in arc_entities
            if in_window(float(a.dxf.center.x), float(a.dxf.center.y))
        ]
        kept_circles = [
            c for c in circle_entities
            if in_window(float(c.dxf.center.x), float(c.dxf.center.y))
        ]
        print(
            f"[cluster-filter] mode={mode} dropped {dropped} auxiliary island(s); "
            f"kept {len(kept_segs)} segments",
            flush=True,
        )
        return kept_segs, kept_arcs, kept_circles, dropped

    def _discretize_arc_entity(self, arc_entity, *, tol: float = 0.02, segments: int = 12) -> list:
        """Approximate ARC as LINE segments for topology QC (DXF-QC04f)."""
        try:
            cx = float(arc_entity.dxf.center.x)
            cy = float(arc_entity.dxf.center.y)
            r = float(arc_entity.dxf.radius)
            sa = math.radians(float(arc_entity.dxf.start_angle))
            ea = math.radians(float(arc_entity.dxf.end_angle))
        except Exception:
            return []
        if r <= 0:
            return []
        if ea < sa:
            ea += 2.0 * math.pi
        span = ea - sa
        if span < 1e-9:
            return []
        n = max(4, int(segments))
        chord = 2.0 * r * math.sin(span / (2.0 * n))
        if chord < tol:
            n = max(4, int(math.ceil(span / max(tol / max(r, 1e-6), 1e-6))))
        out: list = []
        for i in range(n):
            t0 = sa + span * i / n
            t1 = sa + span * (i + 1) / n
            out.append(
                (
                    cx + r * math.cos(t0),
                    cy + r * math.sin(t0),
                    cx + r * math.cos(t1),
                    cy + r * math.sin(t1),
                )
            )
        return out

    def _topology_line_segs_for_qc(self, line_segs, arc_entities, *, tol: float = 0.02) -> list:
        topo = list(line_segs)
        for arc in arc_entities or []:
            topo.extend(self._discretize_arc_entity(arc, tol=tol))
        return topo

    def _closed_line_loops_from_segments(
        self, line_segs, *, tol: float = 0.02
    ) -> list[dict]:
        """Return closed degree-2 loops built from raw line segments."""
        adj: dict[tuple[float, float], list[tuple[float, float]]] = defaultdict(list)
        for x1, y1, x2, y2 in line_segs:
            a = self._point_key(x1, y1, tol)
            b = self._point_key(x2, y2, tol)
            if a == b:
                continue
            adj[a].append(b)
            adj[b].append(a)

        visited: set[tuple[float, float]] = set()
        loops: list[dict] = []
        for start in adj:
            if start in visited:
                continue
            stack = [start]
            comp: list[tuple[float, float]] = []
            while stack:
                node = stack.pop()
                if node in visited:
                    continue
                visited.add(node)
                comp.append(node)
                for nb in adj[node]:
                    if nb not in visited:
                        stack.append(nb)
            if len(comp) < 4:
                continue
            if not all(len(adj[n]) == 2 for n in comp):
                continue
            xs = [n[0] for n in comp]
            ys = [n[1] for n in comp]
            xmin, xmax = min(xs), max(xs)
            ymin, ymax = min(ys), max(ys)
            loops.append(
                {
                    "nodes": comp,
                    "area": max(xmax - xmin, 0.0) * max(ymax - ymin, 0.0),
                    "bbox": {
                        "cx": (xmin + xmax) / 2.0,
                        "cy": (ymin + ymax) / 2.0,
                        "xspan": xmax - xmin,
                        "yspan": ymax - ymin,
                    },
                }
            )
        return loops

    def _extract_enclosing_outline_entities(self, frame_entities, part_bb: dict, tol: float = 0.02) -> list:
        """Pull only a plate-scale closed outline from a skipped frame layer (not dimension ticks)."""
        part_area = float(part_bb.get("xspan") or 0) * float(part_bb.get("yspan") or 0)
        if part_area <= 0:
            return []
        part_cx = float(part_bb.get("cx") or 0)
        part_cy = float(part_bb.get("cy") or 0)

        line_entities: list = []
        raw_segs: list = []
        for e in frame_entities:
            if e.dxftype() == "LINE":
                line_entities.append(e)
                raw_segs.append(
                    (
                        float(e.dxf.start.x),
                        float(e.dxf.start.y),
                        float(e.dxf.end.x),
                        float(e.dxf.end.y),
                    )
                )
            elif e.dxftype() in ("LWPOLYLINE", "POLYLINE"):
                line_entities.append(e)
                raw_segs.extend(self._polyline_to_line_segments(e, tol=tol))

        if not raw_segs:
            return []

        loops = self._closed_line_loops_from_segments(raw_segs, tol=tol)
        best_loop = None
        best_area = 0.0
        for loop in loops:
            area = float(loop.get("area") or 0)
            if area > 150000.0:
                continue
            if area < part_area * 0.85:
                continue
            if area > part_area * 5.0:
                continue
            bb = loop.get("bbox") or {}
            if not self._point_in_bbox(part_cx, part_cy, bb, margin=2.0):
                continue
            if area > best_area:
                best_area = area
                best_loop = loop

        if not best_loop:
            return []

        loop_nodes = set(best_loop.get("nodes") or [])
        picked: list = []
        for e in line_entities:
            if e.dxftype() != "LINE":
                continue
            a = self._point_key(float(e.dxf.start.x), float(e.dxf.start.y), tol)
            b = self._point_key(float(e.dxf.end.x), float(e.dxf.end.y), tol)
            if a in loop_nodes and b in loop_nodes:
                picked.append(e)
        return picked

    def _wire_graph_stats(self, line_segs, tol: float = 0.02) -> dict:
        """Topology stats for DXF-QC04c closed outer loop gate."""
        adj: dict[tuple[float, float], list[tuple[float, float]]] = defaultdict(list)
        for x1, y1, x2, y2 in line_segs:
            a = self._point_key(x1, y1, tol)
            b = self._point_key(x2, y2, tol)
            if a == b:
                continue
            adj[a].append(b)
            adj[b].append(a)

        open_endpoints = sum(1 for n, v in adj.items() if len(v) == 1)
        odd_degree_nodes = sum(1 for n, v in adj.items() if len(v) % 2 == 1)

        visited: set[tuple[float, float]] = set()
        closed_component_max_area = 0.0
        closed_component_count = 0
        for start in adj:
            if start in visited:
                continue
            stack = [start]
            comp_nodes: list[tuple[float, float]] = []
            while stack:
                node = stack.pop()
                if node in visited:
                    continue
                visited.add(node)
                comp_nodes.append(node)
                for nb in adj[node]:
                    if nb not in visited:
                        stack.append(nb)
            if len(comp_nodes) < 3:
                continue
            if all(len(adj[n]) == 2 for n in comp_nodes):
                xs = [n[0] for n in comp_nodes]
                ys = [n[1] for n in comp_nodes]
                area = max(max(xs) - min(xs), 0.0) * max(max(ys) - min(ys), 0.0)
                closed_component_count += 1
                closed_component_max_area = max(closed_component_max_area, area)

        return {
            "nodes": len(adj),
            "segments": len(line_segs),
            "open_endpoints": open_endpoints,
            "odd_degree_nodes": odd_degree_nodes,
            "closed_component_count": closed_component_count,
            "closed_component_max_area": closed_component_max_area,
        }

    def _circle_bbox_area(self, circle_entities, arc_entities) -> float:
        xs: list[float] = []
        ys: list[float] = []
        for e in list(circle_entities) + list(arc_entities):
            try:
                cx = float(e.dxf.center.x)
                cy = float(e.dxf.center.y)
                r = float(e.dxf.radius)
                xs.extend([cx - r, cx + r])
                ys.extend([cy - r, cy + r])
            except Exception:
                continue
        if not xs:
            return 0.0
        return max(max(xs) - min(xs), 0.0) * max(max(ys) - min(ys), 0.0)

    def _bbox_area_from_segs(self, line_segs) -> float:
        if not line_segs:
            return 0.0
        xmin, ymin, xmax, ymax = self._bbox_of_line_segs(line_segs)
        return max(xmax - xmin, 0.0) * max(ymax - ymin, 0.0)

    def _evaluate_closed_loop_qc(
        self,
        line_segs,
        circle_entities,
        arc_entities,
        *,
        tol: float = 0.02,
    ) -> dict:
        """DXF-QC04c: hole layers need outer plate margin; block circle-only punch extrude."""
        circle_n = len(circle_entities)
        # T043/5yk fix (2026-07-06): arcs DO connect their endpoints, so include arc
        # chords in the topology graph. Without this, line-arc-line closed profiles
        # (e.g. S1: 102 lines + 101 arcs) count every arc junction as an open endpoint
        # and trip a false FAIL (open_endpoints=174). Full-circle arcs degenerate to
        # a == b and are skipped inside _wire_graph_stats.
        arc_chords = []
        for e in arc_entities:
            try:
                cx = float(e.dxf.center.x)
                cy = float(e.dxf.center.y)
                r = float(e.dxf.radius)
                a0 = math.radians(float(e.dxf.start_angle))
                a1 = math.radians(float(e.dxf.end_angle))
                arc_chords.append(
                    (cx + r * math.cos(a0), cy + r * math.sin(a0),
                     cx + r * math.cos(a1), cy + r * math.sin(a1))
                )
            except Exception:
                continue
        stats = self._wire_graph_stats(list(line_segs) + arc_chords, tol=tol)
        stats["segments"] = len(line_segs)  # keep reporting line-only segment count
        stats["arc_chords_added"] = len(arc_chords)
        circle_bbox_area = self._circle_bbox_area(circle_entities, arc_entities)
        line_bbox_area = self._bbox_area_from_segs(line_segs)
        line_to_hole_ratio = (
            line_bbox_area / circle_bbox_area if circle_bbox_area > 1e-6 else 0.0
        )
        result = {
            "gate": "DXF-QC04c",
            "pass": True,
            "reason": "ok",
            "circle_count": circle_n,
            "arc_count": len(arc_entities),
            "circle_bbox_area_mm2": round(circle_bbox_area, 3),
            "line_bbox_area_mm2": round(line_bbox_area, 3),
            "line_to_hole_bbox_ratio": round(line_to_hole_ratio, 4),
            **stats,
        }

        if circle_n == 0:
            return result

        seg_n = int(stats.get("segments") or 0)
        open_ep = int(stats.get("open_endpoints") or 0)

        if seg_n == 0:
            result.update({"pass": False, "reason": "holes_without_outer_line_segments"})
            return result

        if line_to_hole_ratio < 1.20:
            result.update(
                {
                    "pass": False,
                    "reason": (
                        f"line_to_hole_bbox_ratio={line_to_hole_ratio:.3f}<1.20 "
                        f"(outer plate margin missing; punch-risk)"
                    ),
                }
            )
            return result

        if line_to_hole_ratio < 1.35:
            open_limit = max(8, int(circle_n * 0.25))
            if open_ep > open_limit:
                result.update(
                    {
                        "pass": False,
                        "reason": (
                            f"open_endpoints={open_ep}>{open_limit} with "
                            f"line_to_hole_bbox_ratio={line_to_hole_ratio:.3f}<1.35"
                        ),
                    }
                )
                return result

        closed_area = float(stats.get("closed_component_max_area") or 0.0)
        if closed_area > 0 and closed_area < circle_bbox_area * 1.15:
            result.update(
                {
                    "pass": False,
                    "reason": (
                        f"closed_component_area={closed_area:.1f}"
                        f" < circle_bbox*1.15={circle_bbox_area * 1.15:.1f}"
                    ),
                }
            )
            return result

        # DXF-QC04f: plate-scale closed outer loop required (line+arc topology).
        topo_segs = self._topology_line_segs_for_qc(line_segs, arc_entities, tol=tol)
        topo_stats = self._wire_graph_stats(topo_segs, tol=tol)
        plate_closed_area = float(topo_stats.get("closed_component_max_area") or 0.0)
        plate_closed_count = int(topo_stats.get("closed_component_count") or 0)
        result["plate_closed_component_count"] = plate_closed_count
        result["plate_closed_component_max_area_mm2"] = round(plate_closed_area, 3)
        min_plate_area = max(circle_bbox_area * 1.08, line_bbox_area * 0.82)
        if plate_closed_count < 1 or plate_closed_area < min_plate_area:
            result.update(
                {
                    "pass": False,
                    "gate": "DXF-QC04f",
                    "reason": (
                        f"no_plate_closed_loop: plate_closed_area={plate_closed_area:.1f}"
                        f" < min={min_plate_area:.1f} (outer frame missing or fragmented)"
                    ),
                }
            )
            return result

        return result

    def _get_layer_bbox(self, entities):
        """Calculate bounding box (cx, cy, xspan, yspan) from ezdxf entities."""
        xs, ys = [], []
        for e in entities:
            if e.dxftype() == 'LINE':
                xs.extend([e.dxf.start[0], e.dxf.end[0]])
                ys.extend([e.dxf.start[1], e.dxf.end[1]])
            elif e.dxftype() == 'LWPOLYLINE':
                for x, y, *_ in e.get_points('xy'):
                    xs.append(float(x))
                    ys.append(float(y))
            elif e.dxftype() == 'POLYLINE':
                for v in e.vertices():
                    xs.append(float(v.dxf.location.x))
                    ys.append(float(v.dxf.location.y))
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

    def _layer_bbox_area(self, bb: dict) -> float:
        return max(float(bb.get("xspan") or 0), 0.0) * max(float(bb.get("yspan") or 0), 0.0)

    def _is_standard_drawing_frame(self, bb: dict) -> bool:
        """ISO A4-ish title block frame (~208x293 mm) -- not the press part."""
        w = float(bb.get("xspan") or 0)
        h = float(bb.get("yspan") or 0)
        if w > h:
            w, h = h, w
        return (200.0 <= w <= 220.0) and (285.0 <= h <= 300.0)

    def _is_drawing_sheet_bbox(self, bb: dict) -> bool:
        """Full A3/A2 drawing sheet border (420x297 / 594x420 mm) -- not the part profile."""
        w = float(bb.get("xspan") or 0)
        h = float(bb.get("yspan") or 0)
        if w > h:
            w, h = h, w
        a3 = (290.0 <= w <= 302.0) and (415.0 <= h <= 430.0)
        a2 = (415.0 <= w <= 430.0) and (585.0 <= h <= 600.0)
        return a3 or a2

    def _is_layout_layer_bbox(self, bb: dict) -> bool:
        return self._is_standard_drawing_frame(bb) or self._is_drawing_sheet_bbox(bb)

    def _frame_layers_to_skip(self, layers: dict) -> set[str]:
        skip: set[str] = set()
        sized: list[tuple[str, float]] = []
        for name, entities in layers.items():
            bb = self._get_layer_bbox(entities)
            if not bb:
                continue
            if self._is_layout_layer_bbox(bb):
                skip.add(name)
                continue
            sized.append((name, self._layer_bbox_area(bb)))
        if len(sized) < 2:
            return skip
        sized.sort(key=lambda item: item[1])
        min_area = sized[0][1]
        if min_area <= 0:
            return skip
        for name, area in sized:
            if area > min_area * 20:
                skip.add(name)
        return skip

    def _entity_type_counts(self, entities) -> Counter:
        return Counter(e.dxftype() for e in entities)

    def _bbox_region(self, bb: dict, margin: float = 0.0) -> tuple[float, float, float, float]:
        cx = float(bb.get("cx") or 0)
        cy = float(bb.get("cy") or 0)
        half_x = float(bb.get("xspan") or 0) / 2.0 + margin
        half_y = float(bb.get("yspan") or 0) / 2.0 + margin
        return cx - half_x, cy - half_y, cx + half_x, cy + half_y

    def _point_in_bbox(self, x: float, y: float, bb: dict, margin: float = 0.0) -> bool:
        xmin, ymin, xmax, ymax = self._bbox_region(bb, margin=margin)
        return xmin <= x <= xmax and ymin <= y <= ymax

    def _entity_midpoint(self, entity) -> tuple[float, float] | None:
        t = entity.dxftype()
        try:
            if t == "LINE":
                return (
                    (float(entity.dxf.start.x) + float(entity.dxf.end.x)) / 2.0,
                    (float(entity.dxf.start.y) + float(entity.dxf.end.y)) / 2.0,
                )
            if t == "CIRCLE":
                return float(entity.dxf.center.x), float(entity.dxf.center.y)
            if t == "ARC":
                return float(entity.dxf.center.x), float(entity.dxf.center.y)
            if t in ("LWPOLYLINE", "POLYLINE"):
                pts = list(entity.get_points("xy"))
                if not pts:
                    return None
                return (
                    sum(float(p[0]) for p in pts) / len(pts),
                    sum(float(p[1]) for p in pts) / len(pts),
                )
        except Exception:
            return None
        return None

    def _entities_near_part_bbox(self, entities, part_bb: dict, margin: float = 12.0) -> list:
        """Pull outline geometry from a frame layer without the A4 border rectangle."""
        geom_types = {"LINE", "ARC", "CIRCLE", "LWPOLYLINE", "POLYLINE"}
        out: list = []
        for e in entities:
            if e.dxftype() not in geom_types:
                continue
            mid = self._entity_midpoint(e)
            if mid and self._point_in_bbox(mid[0], mid[1], part_bb, margin=margin):
                out.append(e)
        return out

    def _find_profile_hole_layer_merges(self, layers: dict, skip_layers: set[str]) -> dict[str, str]:
        """Hole-heavy part layer + outline on skipped A4/frame layer (P20: layer 1 + 13)."""
        merges: dict[str, str] = {}
        for part_name, part_ents in layers.items():
            if part_name in skip_layers:
                continue
            counts = self._entity_type_counts(part_ents)
            circles = counts.get("CIRCLE", 0) + counts.get("ARC", 0)
            lines = counts.get("LINE", 0) + counts.get("LWPOLYLINE", 0) + counts.get("POLYLINE", 0)
            if circles < 3 or lines > circles:
                continue
            part_bb = self._get_layer_bbox(part_ents)
            if not part_bb:
                continue
            best_name = ""
            best_score = 0
            for skip_name in skip_layers:
                skip_ents = layers.get(skip_name) or []
                sc = self._entity_type_counts(skip_ents)
                if sc.get("LINE", 0) < 20:
                    continue
                skip_bb = self._get_layer_bbox(skip_ents)
                if not skip_bb:
                    continue
                if not self._point_in_bbox(part_bb["cx"], part_bb["cy"], skip_bb, margin=5.0):
                    continue
                score = sc.get("LINE", 0)
                if score > best_score:
                    best_score = score
                    best_name = skip_name
            if best_name:
                merges[part_name] = best_name
        return merges

    def _filter_frame_layers(self, layer_data: list) -> list:
        """Drop drawing-frame layers that dwarf the real part profile (e.g. S11 layer 1)."""
        if len(layer_data) < 2:
            return layer_data
        kept = [d for d in layer_data if not self._is_layout_layer_bbox(d["bb"])]
        if len(kept) < len(layer_data):
            dropped = [d["name"] for d in layer_data if d not in kept]
            self.log_data["reconstruction_frame_layers_dropped"] = dropped
            print(f"[reconstruct] dropped standard frame layers: {dropped}", flush=True)
            if kept:
                return kept
        sized = [(d, self._layer_bbox_area(d["bb"])) for d in layer_data]
        sized.sort(key=lambda item: item[1])
        min_area = sized[0][1]
        if min_area <= 0:
            return layer_data
        kept: list = []
        dropped: list[str] = []
        for d, area in sized:
            if area > min_area * 20:
                dropped.append(d["name"])
            else:
                kept.append(d)
        if dropped and kept:
            self.log_data["reconstruction_frame_layers_dropped"] = dropped
            print(
                f"[reconstruct] dropped frame-like layers (area>{min_area * 20:.1f}mm^2): {dropped}",
                flush=True,
            )
            return kept
        return layer_data

    def _pick_part_layer_for_combined(self, processed_layers: list, successful_steps: list) -> str | None:
        """Pick a successful non-frame layer for combined export."""
        ok_names = {os.path.basename(p).replace(".step", "") for p in successful_steps}
        candidates: list[tuple[str, float]] = []
        for pl in processed_layers:
            name = pl["name"]
            if name not in ok_names:
                continue
            bb = self._get_layer_bbox(pl["entities"])
            if not bb or self._is_layout_layer_bbox(bb):
                continue
            candidates.append((name, self._layer_bbox_area(bb)))
        if not candidates:
            return None
        candidates.sort(key=lambda item: item[1])
        if len(candidates) >= 2 and candidates[-1][1] > candidates[0][1] * 2.5:
            return candidates[0][0]
        return candidates[-1][0]

    def _export_single_layer_combined(self, layer_name: str) -> None:
        """Use one profile layer as combined output when multiview pairing is invalid."""
        import shutil

        src_step = os.path.join(self.output_dir, f"{layer_name}.step")
        src_fcstd = os.path.join(self.output_dir, f"{layer_name}.FCStd")
        combined_step = os.path.join(self.output_dir, "combined.step")
        combined_fcstd = os.path.join(self.output_dir, "combined.FCStd")
        combined_png = os.path.join(self.output_dir, "combined_views.png")
        if not os.path.exists(src_step):
            self.log_data["reconstruction_status"] = "single_layer_missing_step"
            self.log_data["combined_quality_ok"] = False
            return
        pl = next((p for p in getattr(self, "_processed_layers_cache", []) if p["name"] == layer_name), None)
        if pl:
            bb = self._get_layer_bbox(pl["entities"])
            if bb and self._is_layout_layer_bbox(bb):
                self.log_data["reconstruction_status"] = "frame_layer_rejected"
                self.log_data["combined_quality_ok"] = False
                print(f"[reconstruct] refuse combined from frame layer {layer_name}", flush=True)
                return
        shutil.copy2(src_step, combined_step)
        if os.path.exists(src_fcstd):
            shutil.copy2(src_fcstd, combined_fcstd)
        self.log_data["combined_step"] = os.path.basename(combined_step)
        self.log_data["combined_fcstd"] = (
            os.path.basename(combined_fcstd) if os.path.exists(combined_fcstd) else None
        )
        self.log_data["reconstruction_status"] = "single_profile_extrude"
        self.log_data["combined_quality_ok"] = True
        self.log_data["reconstruction_note"] = (
            f"Multiview skipped; promoted layer {layer_name} as combined solid (frame layers removed)."
        )
        print(f"[reconstruct] single-layer combined from {layer_name}", flush=True)
        self.render_step_views(combined_step, combined_png, "Combined 3D Reconstruction")
        self.log_data["combined_png"] = (
            os.path.basename(combined_png) if os.path.exists(combined_png) else None
        )

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
        """Convert host path for FreeCAD (docker container or native Linux)."""
        mode = os.environ.get("DXF2STEP_FREECAD_MODE", "docker").strip().lower()
        p = windows_path.replace("\\", "/")
        if mode in ("native", "linux"):
            return p
        p = p.replace("D:/Clawdbot_Docker_20260125/data/workspace", "/home/node/clawd")
        return p

    def generate_freecad_script(self, dxf_path, step_path, thickness):
        # Convert Windows paths to Linux container paths for use inside FreeCAD
        dxf_path = self._to_container_path(dxf_path)
        step_path = self._to_container_path(step_path)
        fcstd_path = step_path[:-5] + ".FCStd" if step_path.lower().endswith(".step") else step_path + ".FCStd"

        return f"""{SHIBOKEN_PATCH}
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
        wires = []
        for edge_group in sorted_edge_groups:
            try:
                wire = Part.Wire(edge_group)
                if wire.isClosed():
                    wires.append(wire)
            except Exception as we:
                print(f"Wire error: {{we}}")

        if wires:
            # Detect circles and find concentric pairs (counterbores)
            circles = []
            for w in wires:
                if len(w.Edges) == 1 and "Circle" in type(w.Edges[0].Curve).__name__:
                    circles.append({{
                        "wire": w,
                        "center": (round(w.Edges[0].Curve.Center.x, 3), round(w.Edges[0].Curve.Center.y, 3)),
                        "radius": w.Edges[0].Curve.Radius
                    }})
            
            concentric_pairs = []
            skip_wires = set()
            for i in range(len(circles)):
                for j in range(i + 1, len(circles)):
                    c1 = circles[i]
                    c2 = circles[j]
                    dist = ((c1["center"][0] - c2["center"][0])**2 + (c1["center"][1] - c2["center"][1])**2)**0.5
                    if dist < 0.05:
                        inner = c1 if c1["radius"] < c2["radius"] else c2
                        outer = c2 if c1["radius"] < c2["radius"] else c1
                        concentric_pairs.append((inner, outer))
                        skip_wires.add(outer["wire"])
            
            # Filter out outer wires of counterbores
            wires = [w for w in wires if w not in skip_wires]

            def _is_circle_wire(w):
                try:
                    return len(w.Edges) == 1 and "Circle" in type(w.Edges[0].Curve).__name__
                except Exception:
                    return False

            circle_wires = [w for w in wires if _is_circle_wire(w)]
            profile_wires = [w for w in wires if not _is_circle_wire(w)]
            print(f"[hole-cut] profile_wires={{len(profile_wires)}} circle_wires={{len(circle_wires)}}", flush=True)

            # Sort profile wires by the area of their face descending
            try:
                profile_wires.sort(key=lambda w: Part.Face(w).Area, reverse=True)
            except Exception as se:
                print(f"Wire sorting error: {{se}}")

            base_faces = []
            for w in profile_wires:
                try:
                    test_face = Part.Face(w)
                    contained = False
                    for i, base_face in enumerate(base_faces):
                        cut_face = base_face.cut(test_face)
                        # If the cut reduces the base_face area, test_face is inside it.
                        if base_face.Area - cut_face.Area > 0.1:
                            base_faces[i] = cut_face
                            contained = True
                            break
                    if not contained:
                        base_faces.append(test_face)
                except Exception as fe:
                    print(f"Face/containment error: {{fe}}")

            if len(base_faces) > 1:
                raise Exception('NG_MULTIPLE_PROFILES: 1つの面（レイヤー）に複数の独立した外形プロファイルが検出されました。基本DXFは部品単体の図面であるため、複数部品やバラ図はNG（未対応）対象となります。')

            if base_faces:
                # Extrude each outer face (with its cut holes) to a solid, then fuse them.
                solids = []
                for f in base_faces:
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

                    # DXF-QC04e: force through-holes; never leave CIRCLE wires as punch studs
                    holes_cut = 0
                    plate_bb = result.BoundBox
                    for w in circle_wires:
                        try:
                            circ = w.Edges[0].Curve
                            r = float(circ.Radius)
                            cx = float(circ.Center.x)
                            cy = float(circ.Center.y)
                            if r <= 0:
                                continue
                            if not (
                                plate_bb.XMin - 1.0 <= cx <= plate_bb.XMax + 1.0
                                and plate_bb.YMin - 1.0 <= cy <= plate_bb.YMax + 1.0
                            ):
                                continue
                            hole = Part.makeCylinder(
                                r,
                                float({thickness}) + 2.0,
                                App.Vector(cx, cy, -1.0),
                                App.Vector(0, 0, 1),
                            )
                            cut_try = result.cut(hole)
                            if cut_try.isValid() and getattr(cut_try, "Volume", 0) > 0:
                                result = cut_try
                                holes_cut += 1
                        except Exception as hce:
                            print(f"[hole-cut] skip: {{hce}}")
                    print(f"[hole-cut] through_holes={{holes_cut}}", flush=True)

                    # Apply counterbore pockets
                    for inner, outer in concentric_pairs:
                        try:
                            cx, cy = inner["center"]
                            R1 = inner["radius"]
                            R2 = outer["radius"]
                            d1 = R1 * 2.0
                            d2 = R2 * 2.0
                            h = min(5.0, {thickness} * 0.5)
                            jis_table = [
                                (3.2, 3.8,  5.8, 6.5,   3.3), # M3
                                (4.2, 4.8,  7.8, 8.5,   4.4), # M4
                                (5.2, 5.8,  9.2, 10.0,  5.4), # M5
                                (6.2, 6.8,  10.8, 11.5, 6.5), # M6
                                (8.2, 9.2,  13.8, 14.5, 8.6), # M8
                            ]
                            for j_d1_min, j_d1_max, j_d2_min, j_d2_max, j_h in jis_table:
                                if j_d1_min <= d1 <= j_d1_max and j_d2_min <= d2 <= j_d2_max:
                                    h = j_h
                                    break
                            
                            pocket = Part.makeCylinder(R2, h, App.Vector(cx, cy, {thickness} - h), App.Vector(0, 0, 1))
                            result = result.cut(pocket)
                            print(f"[Counterbore] Created M-type pocket at ({{cx}}, {{cy}}) outer radius {{R2}} depth {{h}}")
                        except Exception as cbe:
                            print(f"Counterbore pocket build failed: {{cbe}}")

                    try:
                        area = result.Area
                        volume = result.Volume
                        bbox = result.BoundBox
                        dim_x = bbox.XMax - bbox.XMin
                        dim_y = bbox.YMax - bbox.YMin
                        dim_z = bbox.ZMax - bbox.ZMin
                        print(f"Metrics: V={{volume:.1f}} A={{area:.1f}} D={{dim_x:.1f}}x{{dim_y:.1f}}x{{dim_z:.1f}}")
                    except Exception as me:
                        print(f"Metrics error: {{me}}")
                    
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
                print("No faces built after containment analysis")
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
            SHIBOKEN_PATCH + "\n"
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
            "    # Sort edges into closed loops then build analytical faces with holes\n"
            "    try:\n"
            "        sorted_groups = Part.sortEdges(edges)\n"
            "    except Exception as e:\n"
            "        print('sortEdges failed:', e)\n"
            "        return None\n"
            "    wires = []\n"
            "    for group in sorted_groups:\n"
            "        try:\n"
            "            wire = Part.Wire(group)\n"
            "            if wire.isClosed():\n"
            "                wires.append(wire)\n"
            "        except Exception as e:\n"
            "            pass\n"
            "    if not wires:\n"
            "        print('No closed wires for', view_type)\n"
            "        return None\n"
            "    try:\n"
            "        wires.sort(key=lambda w: Part.Face(w).Area, reverse=True)\n"
            "    except Exception as e:\n"
            "        print('Wire sort error in build_slab:', e)\n"
            "    base_faces = []\n"
            "    for w in wires:\n"
            "        try:\n"
            "            test_face = Part.Face(w)\n"
            "            contained = False\n"
            "            for i, base_face in enumerate(base_faces):\n"
            "                cut_face = base_face.cut(test_face)\n"
            "                if base_face.Area - cut_face.Area > 0.1:\n"
            "                    base_faces[i] = cut_face\n"
            "                    contained = True\n"
            "                    break\n"
            "            if not contained:\n"
            "                base_faces.append(test_face)\n"
            "        except Exception as e:\n"
            "            print('Face build error in build_slab:', e)\n"
            "\n"
            "    if len(base_faces) > 1:\n"
            "        raise Exception('NG_MULTIPLE_PROFILES: 1つの面（レイヤー）に複数の独立した外形プロファイルが検出されました。基本DXFは部品単体の図面であるため、複数部品やバラ図はNG（未対応）対象となります。')\n"
            "\n"
            "    solids = []\n"
            "    for f in base_faces:\n"
            "        try:\n"
            "            face_3d = f.transformGeometry(m)\n"
            "            sol_pos = face_3d.extrude(ev_pos)\n"
            "            sol_neg = face_3d.extrude(ev_neg)\n"
            "            solids.append(sol_pos.fuse(sol_neg))\n"
            "        except Exception as e:\n"
            "            print('Extrusion/fuse error in build_slab:', e)\n"
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
            "            try:\n"
            "                with open('" + c_combined.replace("combined.step", "reconstruct_warning.txt") + "', 'w', encoding='utf-8') as wf:\n"
            "                    wf.write('WARNING: 3D views intersection was empty (possible height mismatch or alignment discrepancy). Fell back to raw slabs compound.')\n"
            "            except Exception: pass\n"
            "            Part.makeCompound(slabs).exportStep('" + c_combined + "')\n"
            "    except Exception as e:\n"
            "        print('Intersection failed, compound fallback:', e)\n"
            "        try:\n"
            "            with open('" + c_combined.replace("combined.step", "reconstruct_warning.txt") + "', 'w', encoding='utf-8') as wf:\n"
            "                wf.write('WARNING: 3D views intersection failed (' + str(e) + '). Fell back to raw slabs compound.')\n"
            "        except Exception: pass\n"
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
            "import TechDraw\n"
            "import matplotlib\n"
            "matplotlib.use('Agg')\n"
            "import matplotlib.pyplot as plt\n"
            "import matplotlib.gridspec as gridspec\n"
            "\n"
            "shape = Part.read('" + c_step + "')\n"
            "bb = shape.BoundBox\n"
            "oc = App.Vector((bb.XMax + bb.XMin) / 2, (bb.YMax + bb.YMin) / 2, (bb.ZMax + bb.ZMin) / 2)\n"
            "dx = bb.XMax - bb.XMin\n"
            "dy = bb.YMax - bb.YMin\n"
            "dz = bb.ZMax - bb.ZMin\n"
            "max_span = max(dx, dy, dz, 1.0)\n"
            "half = max_span * 0.6\n"
            "\n"
            "def _coord(p, idx):\n"
            "    return (p.x, p.y, p.z)[idx]\n"
            "\n"
            "def hlr_side_view(shape, direction, map_pt):\n"
            "    \"\"\"Orthographic side view: visible HLR edges (outline + face features, no hidden).\"\"\"\n"
            "    out = []\n"
            "    try:\n"
            "        compounds = TechDraw.projectEx(shape, direction)\n"
            "        # projectEx: 0-6 visible (V..V6), 7-9 hidden (H..H2) -- skip hidden\n"
            "        for i in range(min(7, len(compounds))):\n"
            "            comp = compounds[i]\n"
            "            if comp is None or comp.isNull():\n"
            "                continue\n"
            "            for edge in comp.Edges:\n"
            "                try:\n"
            "                    pts = edge.discretize(40)\n"
            "                except Exception:\n"
            "                    continue\n"
            "                if len(pts) < 2:\n"
            "                    continue\n"
            "                out.append([map_pt(p) for p in pts])\n"
            "    except Exception as ex:\n"
            "        print('HLR projectEx failed:', direction, ex)\n"
            "    return out\n"
            "\n"
            "def map_front_pt(p):\n"
            "    # projectEx front: p.x=Z, p.y=-world_X\n"
            "    return (p.y - oc.x, p.x - oc.z)\n"
            "\n"
            "def map_right_pt(p):\n"
            "    # projectEx right: p.x=Z, p.y=-world_Y\n"
            "    return (-p.y - oc.y, p.x - oc.z)\n"
            "\n"
            "def outline_view(shape, direction, flip_u, oc_u, oc_v):\n"
            "    \"\"\"Exterior silhouette fallback via TechDraw.findShapeOutline.\"\"\"\n"
            "    out = []\n"
            "    try:\n"
            "        outline = TechDraw.findShapeOutline(shape, 1.0, direction)\n"
            "        if outline is None or outline.isNull():\n"
            "            return out\n"
            "        for edge in outline.Edges:\n"
            "            try:\n"
            "                pts = edge.discretize(40)\n"
            "            except Exception:\n"
            "                continue\n"
            "            if len(pts) < 2:\n"
            "                continue\n"
            "            out.append([(flip_u * p.x - oc_u, p.y - oc_v) for p in pts])\n"
            "    except Exception as ex:\n"
            "        print('Outline projection failed:', direction, ex)\n"
            "    return out\n"
            "\n"
            "def top_profile_view(shape, oc_u, oc_v):\n"
            "    \"\"\"Top view: all wires on +Z faces (outer profile + holes).\"\"\"\n"
            "    out = []\n"
            "    for face in shape.Faces:\n"
            "        try:\n"
            "            n = face.normalAt(0.5, 0.5)\n"
            "        except Exception:\n"
            "            continue\n"
            "        if n.z < 0.9:\n"
            "            continue\n"
            "        for wire in face.Wires:\n"
            "            for edge in wire.Edges:\n"
            "                try:\n"
            "                    pts = edge.discretize(40)\n"
            "                except Exception:\n"
            "                    continue\n"
            "                if len(pts) < 2:\n"
            "                    continue\n"
            "                out.append([(p.x - oc_u, p.y - oc_v) for p in pts])\n"
            "    return out\n"
            "\n"
            "def bbox_silhouette(oc_u, oc_v, umin, umax, vmin, vmax):\n"
            "    \"\"\"Last-resort side view: axis-aligned bbox outline (no internal edges).\"\"\"\n"
            "    corners = [\n"
            "        (umin - oc_u, vmin - oc_v), (umax - oc_u, vmin - oc_v),\n"
            "        (umax - oc_u, vmax - oc_v), (umin - oc_u, vmax - oc_v), (umin - oc_u, vmin - oc_v),\n"
            "    ]\n"
            "    return [corners]\n"
            "\n"
            "def wireframe_fallback(shape, u_idx, v_idx):\n"
            "    \"\"\"Legacy fallback: all edges projected (shows internal lines -- avoid if possible).\"\"\"\n"
            "    out = []\n"
            "    for edge in shape.Edges:\n"
            "        try:\n"
            "            pts = edge.discretize(40)\n"
            "        except Exception:\n"
            "            continue\n"
            "        if len(pts) < 2:\n"
            "            continue\n"
            "        out.append([\n"
            "            (_coord(p, u_idx) - _coord(oc, u_idx), _coord(p, v_idx) - _coord(oc, v_idx))\n"
            "            for p in pts\n"
            "        ])\n"
            "    return out\n"
            "\n"
            "# Third-angle: Top=XY profile, Front/Right=HLR visible edges only\n"
            "top_segs   = top_profile_view(shape, oc.x, oc.y)\n"
            "front_segs = hlr_side_view(shape, App.Vector(0, -1, 0), map_front_pt)\n"
            "right_segs = hlr_side_view(shape, App.Vector(1, 0, 0), map_right_pt)\n"
            "if not top_segs:\n"
            "    top_segs = outline_view(shape, App.Vector(0, 0, 1), 1, oc.x, oc.y)\n"
            "if not front_segs:\n"
            "    front_segs = outline_view(shape, App.Vector(0, -1, 0), -1, oc.x, oc.z)\n"
            "if not front_segs:\n"
            "    front_segs = bbox_silhouette(oc.x, oc.z, bb.XMin, bb.XMax, bb.ZMin, bb.ZMax)\n"
            "if not right_segs:\n"
            "    right_segs = outline_view(shape, App.Vector(1, 0, 0), 1, oc.y, oc.z)\n"
            "if not right_segs:\n"
            "    right_segs = bbox_silhouette(oc.y, oc.z, bb.YMin, bb.YMax, bb.ZMin, bb.ZMax)\n"
            "\n"
            "def draw_view(ax, segs_2d, title, flip_y=False):\n"
            "    for seg in segs_2d:\n"
            "        if len(seg) >= 2:\n"
            "            xs = [p[0] for p in seg]\n"
            "            ys = [p[1] for p in seg]\n"
            "            ax.plot(xs, ys, 'k-', linewidth=0.8, solid_capstyle='round')\n"
            "    ax.set_aspect('equal')\n"
            "    ax.set_xlim(-half, half)\n"
            "    ax.set_ylim(-half, half)\n"
            "    ax.set_title(title, fontsize=9, pad=5)\n"
            "    ax.set_facecolor('#F5F5F5')\n"
            "    ax.tick_params(left=False, bottom=False, labelleft=False, labelbottom=False)\n"
            "    for spine in ax.spines.values():\n"
            "        spine.set_color('#AAAAAA')\n"
            "        spine.set_linewidth(0.5)\n"
            "    if flip_y:\n"
            "        ax.invert_yaxis()\n"
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

        layer_data = self._filter_frame_layers(layer_data)
        if len(layer_data) < 2:
            if len(layer_data) == 1:
                self._export_single_layer_combined(layer_data[0]["name"])
                with open(os.path.join(self.output_dir, "build_log.json"), 'w') as f:
                    json.dump(self.log_data, f, indent=2)
            else:
                print("Not enough layers with bounding boxes for view assignment")
            return

        view_assignments = self._assign_views_auto(layer_data)
        self.log_data["view_assignments"] = view_assignments
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

        # Clean up old combined files to prevent stale success readings on failure
        combined_step = os.path.join(self.output_dir, "combined.step")
        combined_fcstd = os.path.join(self.output_dir, "combined.FCStd")
        combined_png = os.path.join(self.output_dir, "combined_views.png")
        for old_file in [combined_step, combined_fcstd, combined_png]:
            if os.path.exists(old_file):
                try:
                    os.remove(old_file)
                except Exception:
                    pass

        script = self.generate_reconstruction_script(view_map, combined_step)
        script_path = os.path.join(self.output_dir, "reconstruct_multiview.py")
        with open(script_path, 'w', encoding='utf-8') as f:
            f.write(script)

        print("[FreeCAD] Running multi-view reconstruction script ...", flush=True)
        rc, msg = self.execute_freecad(script_path)
        msg_l = (msg or "").lower()
        if "falling back to compound" in msg_l or "compound fallback" in msg_l:
            self.log_data["reconstruction_status"] = "compound_fallback"
            self.log_data["combined_quality_ok"] = False
            self.log_data["reconstruction_warning"] = (
                "3D view intersection failed or was empty; exported compound of misaligned slabs "
                "(TOP VIEW may show overlapping profiles)."
            )
        elif "intersection ok" in msg_l and "reconstruction complete" in msg_l:
            self.log_data["reconstruction_status"] = "intersection_ok"
            self.log_data["combined_quality_ok"] = True
        elif os.path.exists(combined_step):
            self.log_data["reconstruction_status"] = "combined_exported"
            self.log_data["combined_quality_ok"] = True

        if os.path.exists(combined_step):
            if self.log_data.get("reconstruction_status") == "compound_fallback":
                print("[NG] Combined STEP is compound fallback (overlapping views)", flush=True)
            else:
                print("[FreeCAD] Reconstruction STEP done - rendering combined preview ...", flush=True)
            combined_png = os.path.join(self.output_dir, "combined_views.png")
            self.render_step_views(combined_step, combined_png, "Combined 3D Reconstruction")
            combined_fcstd = (
                combined_step[:-5] + ".FCStd"
                if combined_step.lower().endswith(".step")
                else combined_step + ".FCStd"
            )
            self.log_data["combined_step"] = os.path.basename(combined_step)
            self.log_data["combined_fcstd"] = (
                os.path.basename(combined_fcstd) if os.path.exists(combined_fcstd) else None
            )
            self.log_data["combined_png"] = (
                os.path.basename(combined_png) if os.path.exists(combined_png) else None
            )
        else:
            print(f"Combined STEP not generated. rc={rc}")
            self.log_data["combined_step"] = None
            self.log_data["combined_quality_ok"] = False
            self.log_data["reconstruction_status"] = "failed"
            self.log_data["combined_error"] = msg[:300] if msg else "Unknown error"

        # Check and load reconstruction warning from the FreeCAD script run
        warning_file = os.path.join(self.output_dir, "reconstruct_warning.txt")
        if os.path.exists(warning_file):
            try:
                with open(warning_file, 'r', encoding='utf-8') as wf:
                    self.log_data["reconstruction_warning"] = wf.read().strip()
                os.remove(warning_file)
                print(f"[warning] loaded reconstruction warning: {self.log_data['reconstruction_warning']}")
            except Exception as wex:
                print(f"Failed to read warning file: {wex}")

        # Re-save build_log.json with combined step info
        with open(os.path.join(self.output_dir, "build_log.json"), 'w') as f:
            json.dump(self.log_data, f, indent=2)

    def execute_freecad(self, script_path):
        mode = os.environ.get("DXF2STEP_FREECAD_MODE", "docker").strip().lower()
        linux_script_path = self._to_container_path(script_path)
        if mode in ("native", "linux"):
            fc_cmd = os.environ.get("FREECAD_CMD", "FreeCADCmd")
            cmd = [fc_cmd, linux_script_path]
            timeout_sec = int(os.environ.get("DXF2STEP_FREECAD_TIMEOUT_SEC", "180"))
        else:
            container_name = "clawstack-unified-clawdbot-gateway-1"
            cmd = ["docker", "exec", container_name, "bash", "-c", f"FreeCADCmd '{linux_script_path}'"]
            timeout_sec = 120
        try:
            result = subprocess.run(cmd, capture_output=True, timeout=timeout_sec)
            stdout = result.stdout.decode('utf-8', errors='replace') if result.stdout else ""
            stderr = result.stderr.decode('utf-8', errors='replace') if result.stderr else ""
            if result.returncode != 0:
                print(f"FreeCAD exited with code {result.returncode}: {stderr}")
                return result.returncode, stderr
            print(stdout)
            return 0, stdout
        except subprocess.TimeoutExpired:
            print(f"FreeCAD timed out after {timeout_sec}s")
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
    parser.add_argument("--t-junction-tol", type=float, default=0.02)
    parser.add_argument("--snap-tol", type=float, default=0.02)
    args = parser.parse_args()
    
    processor = DXFProcessor(args.input, args.output, snap_tol=args.snap_tol)
    
    if args.manual_mode:
        assignments = json.loads(args.view_assignments)
        processor.process_manual(assignments)
    else:
        layer_configs = {}
        try:
            layer_configs = json.loads(args.layer_configs)
        except:
            print(f"Warning: Failed to parse layer-configs: {args.layer_configs}")
        processor.process(args.thickness, layer_configs, t_junction_tol=args.t_junction_tol)
