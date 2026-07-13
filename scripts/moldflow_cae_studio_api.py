# -*- coding: utf-8 -*-
"""Moldflow CAE Studio API: STEP upload, STL preview, job export (port 8776)."""

import sys

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import json
import re
import sqlite3
from datetime import datetime
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

ROOT = Path(__file__).resolve().parents[1]
WORKSPACE = ROOT / "data" / "cae_te_workspace"
SAMPLES = WORKSPACE / "samples" / "moldflow"
UPLOADS = SAMPLES / "uploads"
JOBS = WORKSPACE / "jobs" / "moldflow_studio"
DEFAULT_STEP = SAMPLES / "cavity_plate_100x10x2.step"
PREVIEW_STL = SAMPLES / "cavity_preview.stl"
SOLVER_LANDSCAPE = ROOT / "data" / "workspace" / "moldflow_solver_landscape.json"
DEFAULT_PORT = 8776
MATERIAL_DB = ROOT / "data" / "workspace" / "moldflow_materials.db"

MATERIAL_PRESETS = {
    "pp_generic": {
        "name": "PP (generic)",
        "polymer_nu": 0.01,
        "T_melt_K": 513,
        "T_mold_K": 323,
        "thermal_shrink_alpha": 1.5e-4,
    },
    "abs_generic": {
        "name": "ABS (generic)",
        "polymer_nu": 0.012,
        "T_melt_K": 523,
        "T_mold_K": 333,
        "thermal_shrink_alpha": 8e-5,
    },
    "pc_generic": {
        "name": "PC (generic)",
        "polymer_nu": 0.008,
        "T_melt_K": 553,
        "T_mold_K": 353,
        "thermal_shrink_alpha": 6e-5,
    },
}


def _load_material_inventory(limit: int = 100) -> dict:
    limit = max(1, min(limit, 1000))
    if not MATERIAL_DB.exists():
        return {"ok": True, "database": str(MATERIAL_DB), "total": 0, "files": []}
    con = sqlite3.connect(str(MATERIAL_DB))
    con.row_factory = sqlite3.Row
    try:
        total = con.execute("SELECT COUNT(*) FROM moldflow_material_files").fetchone()[0]
        rows = con.execute(
            "SELECT file_name, relative_path, source_kind, vendor, version_tag, extension, "
            "size_bytes, sha256, modified_utc FROM moldflow_material_files "
            "ORDER BY source_kind, file_name LIMIT ?", (limit,)
        ).fetchall()
        return {"ok": True, "database": str(MATERIAL_DB), "total": total,
                "files": [dict(row) for row in rows]}
    finally:
        con.close()


def _load_golden_case_snapshot() -> dict:
    import moldflow_golden_case as mgc

    spec = json.loads(mgc.GOLDEN_SPEC.read_text(encoding="utf-8"))
    trials = mgc.load_trials(mgc.CAE_LOG)
    results = mgc.collect_golden_results(trials, list(spec.get("variants", {}).keys()))
    record = mgc.evaluate_golden(results, spec)
    return {
        "spec": spec,
        "record": record,
        "variants": list(spec.get("variants", {}).keys()),
        "log_path": str(mgc.CAE_LOG.relative_to(ROOT)),
    }


def _load_golden_log_snapshot() -> dict:
    import moldflow_golden_case as mgc

    try:
        return json.loads(mgc.CAE_LOG.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"trials": []}


def _load_solver_landscape_snapshot() -> dict:
    if not SOLVER_LANDSCAPE.exists():
        return {
            "schema": "clawstack.moldflow_solver_landscape.v1",
            "updated_at": None,
            "solvers": [],
            "implementation_backlog": [],
            "warning": "moldflow_solver_landscape.json not found",
        }
    return json.loads(SOLVER_LANDSCAPE.read_text(encoding="utf-8-sig"))


def _apply_safe_moldflow_defaults(params: dict, category: str | None = None) -> tuple[dict, bool]:
    """Keep generated cooling demos on the currently verified stable proxy path."""
    out = dict(params or {})
    physics = str(out.get("physics_category") or category or "")
    if physics != "resin_fill_cool":
        return out, False
    changed = False
    for key, value in (("bounded_alpha", True), ("closed_cavity", False)):
        if out.get(key) != value:
            out[key] = value
            changed = True
    if str(out.get("viscosity_model") or "").lower() != "const":
        out["viscosity_model"] = "const"
        changed = True
    out.setdefault("pack_pressure_MPa", 0.0)
    out["physics_category"] = "resin_fill_cool"
    return out, changed


_LEARNED_PARAM_KEYS = ("inlet_velocity", "pack_pressure_MPa", "polymer_nu", "pack_inlet_velocity")
_LEARNED_CATEGORIES = ("resin_fill_cad", "resin_fill_vof", "resin_fill_pack", "resin_fill_cool")


def _load_learned_params_snapshot(cycle_n: int | None = None, trials: list | None = None) -> dict:
    """Return Fable5 learner suggestions for direct CAE Studio application."""
    import moldflow_golden_case as mgc
    import resin_fill_param_learner as learner

    if trials is None:
        trials = mgc.load_trials(mgc.CAE_LOG)
    cae_trials = [
        t for t in trials
        if str(t.get("category") or "").startswith("resin_fill")
    ]
    good = learner.collect_good_params(cae_trials, list(_LEARNED_PARAM_KEYS))
    resolved_cycle = int(cycle_n) if cycle_n is not None else len(cae_trials) + 1
    suggested, meta = learner.propose_params(resolved_cycle, good)
    golden_due = False
    golden_variant = None
    try:
        spec = json.loads(mgc.GOLDEN_SPEC.read_text(encoding="utf-8"))
        every = int((spec.get("schedule") or {}).get("inject_every_n_cycles", 25))
        variants = list((spec.get("variants") or {}).keys())
        if every > 0 and resolved_cycle % every == 0 and variants:
            golden_due = True
            golden_variant = variants[(resolved_cycle // every) % len(variants)]
    except Exception:
        pass
    return {
        "source": "resin_fill_param_learner",
        "cycle_n": resolved_cycle,
        "learned_keys": list(_LEARNED_PARAM_KEYS),
        "eligible_categories": list(_LEARNED_CATEGORIES),
        "good_pool": len(good),
        "suggested_params": suggested,
        "sampling": meta,
        "golden_due": golden_due,
        "golden_variant": golden_variant,
    }


def _rel_or_str(path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


MATURITY_LATEST = ROOT / "data" / "workspace" / "apps" / "growth_dashboard" / "commercial_benchmark_maturity_latest.json"
GOLDEN_ERROR_LOG = ROOT / "data" / "workspace" / "moldflow_golden_error_log.jsonl"


def _load_maturity_snapshot() -> dict:
    """成熟度評価(commercial_benchmark_maturity)のMOLDFLOW行を返す(読み取り専用・再計算しない)。"""
    if not MATURITY_LATEST.exists():
        return {"available": False, "product": None,
                "note": "commercial_benchmark_maturity_latest.json not found"}
    doc = None
    for _ in range(3):  # 全体書き換え方式JSONのためリトライ読込(検証メモ2026-07-07)
        try:
            doc = json.loads(MATURITY_LATEST.read_text(encoding="utf-8-sig"))
            break
        except (json.JSONDecodeError, OSError):
            import time as _time
            _time.sleep(0.5)
    if doc is None:
        return {"available": False, "product": None,
                "note": "maturity json 読込失敗(書き換え中の可能性・リトライ超過)"}
    product = None
    for row in doc.get("matrix") or []:
        if "MOLDFLOW" in str(row.get("product_id", "")).upper():
            product = row
            break
    assessed_at = doc.get("assessed_at")
    age_h = None
    if assessed_at:
        try:
            ts = datetime.fromisoformat(str(assessed_at).replace("Z", "+00:00"))
            now = datetime.now(ts.tzinfo) if ts.tzinfo else datetime.now()
            age_h = round((now - ts).total_seconds() / 3600.0, 1)
        except (ValueError, TypeError):
            pass
    return {
        "available": product is not None,
        "assessed_at": assessed_at,
        "age_hours": age_h,
        "stale": bool(age_h is not None and age_h > 26),
        "product": product,
        "source": _rel_or_str(MATURITY_LATEST),
    }


def _load_golden_error_trend(limit: int = 50) -> dict:
    """ゴールデンケース誤差推移(moldflow_golden_case.pyがjsonl追記)。未発生ならrecords空+note。"""
    limit = max(1, min(int(limit), 500))
    if not GOLDEN_ERROR_LOG.exists():
        return {"available": False, "records": [], "count_total": 0,
                "note": "moldflow_golden_error_log.jsonl 未生成(ゴールデンケース未実行。発効条件はFABLE5_FINAL_SESSION_HANDOVER_20260707.md §0参照)"}
    records = []
    for line in GOLDEN_ERROR_LOG.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            records.append(json.loads(line))
        except json.JSONDecodeError:
            continue  # 追記途中の行は無視(安全側)
    return {"available": True, "records": records[-limit:], "count_total": len(records),
            "source": _rel_or_str(GOLDEN_ERROR_LOG)}


MAX_UPLOAD_BYTES = 512 * 1024 * 1024  # 512MB上限(cgi版には無かった安全弁)


def _parse_multipart(headers, rfile) -> dict:
    """multipart/form-data の自前パース(cgiモジュール代替・Python3.13対応)。

    返り値: {field_name: (filename, content_bytes)}。
    旧cgi版と異なり全体をメモリに読むため MAX_UPLOAD_BYTES で上限を設ける。
    """
    ctype = headers.get("Content-Type", "")
    m = re.search(r'boundary="?([^";]+)"?', ctype)
    if not m:
        raise ValueError("multipart boundary not found")
    boundary = m.group(1).encode("utf-8")
    length = int(headers.get("Content-Length", "0") or 0)
    if length <= 0:
        raise ValueError("empty body")
    if length > MAX_UPLOAD_BYTES:
        raise ValueError(f"upload too large (>{MAX_UPLOAD_BYTES} bytes)")
    body = rfile.read(length)
    fields = {}
    for part in body.split(b"--" + boundary):
        if part in (b"", b"--", b"--\r\n") or part == b"\r\n":
            continue
        if part.startswith(b"\r\n"):
            part = part[2:]
        head, sep, content = part.partition(b"\r\n\r\n")
        if not sep:
            continue
        if content.endswith(b"\r\n"):
            content = content[:-2]
        head_text = head.decode("utf-8", errors="replace")
        nm = re.search(r'name="([^"]*)"', head_text)
        if not nm:
            continue
        fn = re.search(r'filename="([^"]*)"', head_text)
        fields[nm.group(1)] = ((fn.group(1) if fn else ""), content)
    return fields


def _safe_name(name: str) -> str:
    base = Path(name).name
    return re.sub(r"[^\w.\-]+", "_", base)[:120] or "upload.step"


def _write_bbox_preview_stl(stl_path: Path, bbox: dict[str, float]) -> Path:
    """Write a lightweight box STL when gmsh is not available for UI preview."""
    lx = float(bbox.get("length", 100.0) or 100.0)
    ly = float(bbox.get("width", 10.0) or 10.0)
    lz = float(bbox.get("height", 2.0) or 2.0)
    ox = float(bbox.get("xmin", 0.0) or 0.0)
    oy = float(bbox.get("ymin", 0.0) or 0.0)
    oz = float(bbox.get("zmin", 0.0) or 0.0)
    x0, x1 = ox, ox + lx
    y0, y1 = oy, oy + ly
    z0, z1 = oz, oz + lz
    vertices = {
        "000": (x0, y0, z0),
        "100": (x1, y0, z0),
        "110": (x1, y1, z0),
        "010": (x0, y1, z0),
        "001": (x0, y0, z1),
        "101": (x1, y0, z1),
        "111": (x1, y1, z1),
        "011": (x0, y1, z1),
    }
    faces = [
        ((0, 0, -1), ("000", "110", "100"), ("000", "010", "110")),
        ((0, 0, 1), ("001", "101", "111"), ("001", "111", "011")),
        ((0, -1, 0), ("000", "100", "101"), ("000", "101", "001")),
        ((0, 1, 0), ("010", "011", "111"), ("010", "111", "110")),
        ((-1, 0, 0), ("000", "001", "011"), ("000", "011", "010")),
        ((1, 0, 0), ("100", "110", "111"), ("100", "111", "101")),
    ]
    lines = ["solid cavity_preview"]
    for normal, tri_a, tri_b in faces:
        for tri in (tri_a, tri_b):
            lines.append(f"  facet normal {normal[0]} {normal[1]} {normal[2]}")
            lines.append("    outer loop")
            for key in tri:
                x, y, z = vertices[key]
                lines.append(f"      vertex {x:.6f} {y:.6f} {z:.6f}")
            lines.append("    endloop")
            lines.append("  endfacet")
    lines.append("endsolid cavity_preview")
    stl_path.parent.mkdir(parents=True, exist_ok=True)
    stl_path.write_text("\n".join(lines) + "\n", encoding="ascii")
    return stl_path


def _ensure_preview(step: Path | None = None) -> Path:
    import moldflow_cavity_mesh as mcm
    import moldflow_step_case_builder as mscb

    SAMPLES.mkdir(parents=True, exist_ok=True)
    step_p = step or (DEFAULT_STEP if DEFAULT_STEP.exists() else mscb.ensure_sample_step())
    if step_p.exists():
        bbox = mscb.step_bbox_mm(step_p)
    else:
        bbox = {"length": 100.0, "width": 10.0, "height": 2.0, "xmin": 0, "ymin": 0, "zmin": 0}
    try:
        mcm.export_stl_preview(PREVIEW_STL, bbox, step_path=step_p)
    except RuntimeError as exc:
        if "gmsh Python package required" not in str(exc):
            raise
        _write_bbox_preview_stl(PREVIEW_STL, bbox)
    return PREVIEW_STL


class CaeStudioHandler(BaseHTTPRequestHandler):
    server_version = "MoldflowCaeStudio/1.1"

    def _cors(self) -> None:
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def do_OPTIONS(self) -> None:
        self.send_response(204)
        self._cors()
        self.end_headers()

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path in ("/health", "/api/health"):
            self._json(200, {"ok": True, "service": "moldflow_cae_studio", "port": DEFAULT_PORT})
            return
        if parsed.path in ("/api/preview.stl", "/api/stl"):
            try:
                qs = parse_qs(parsed.query)
                step_q = qs.get("step", [""])[0]
                step_p = Path(step_q) if step_q else None
                if step_p and not step_p.is_absolute():
                    step_p = (ROOT / step_p).resolve()
                stl = _ensure_preview(step_p)
            except Exception as exc:
                self._json(500, {"error": str(exc)})
                return
            self._send_bytes(stl.read_bytes(), "model/stl")
            return
        if parsed.path == "/api/bbox":
            import moldflow_step_case_builder as mscb

            qs = parse_qs(parsed.query)
            step_q = qs.get("step", [""])[0]
            if step_q:
                step = Path(step_q)
                if not step.is_absolute():
                    step = (ROOT / step).resolve()
            else:
                step = DEFAULT_STEP if DEFAULT_STEP.exists() else mscb.ensure_sample_step()
            bbox = mscb.step_bbox_mm(step)
            self._json(200, {"bbox_mm": bbox, "step": str(step)})
            return
        if parsed.path == "/api/materials":
            self._json(200, {"presets": MATERIAL_PRESETS})
            return
        if parsed.path == "/api/material-inventory":
            try:
                limit = int(parse_qs(parsed.query).get("limit", ["100"])[0])
                self._json(200, _load_material_inventory(limit))
            except Exception as exc:
                self._json(500, {"error": str(exc)})
            return
        if parsed.path == "/api/solver-landscape":
            try:
                self._json(200, _load_solver_landscape_snapshot())
            except Exception as exc:
                self._json(500, {"error": str(exc)})
            return
        if parsed.path in ("/api/golden-case", "/api/golden-log"):
            try:
                if parsed.path == "/api/golden-case":
                    self._json(200, _load_golden_case_snapshot())
                else:
                    import moldflow_golden_case as mgc
                    self._json(200, {"path": str(mgc.CAE_LOG.relative_to(ROOT)), **_load_golden_log_snapshot()})
            except Exception as exc:
                self._json(500, {"error": str(exc)})
            return
        if parsed.path == "/api/learned-params":
            try:
                qs = parse_qs(parsed.query)
                cycle_raw = qs.get("cycle_n", [""])[0]
                cycle_n = int(cycle_raw) if cycle_raw else None
                self._json(200, _load_learned_params_snapshot(cycle_n=cycle_n))
            except Exception as exc:
                self._json(500, {"error": str(exc)})
            return
        if parsed.path == "/api/maturity":
            try:
                self._json(200, _load_maturity_snapshot())
            except Exception as exc:
                self._json(500, {"error": str(exc)})
            return
        if parsed.path == "/api/golden-error-trend":
            try:
                qs = parse_qs(parsed.query)
                limit = int(qs.get("limit", ["50"])[0])
                self._json(200, _load_golden_error_trend(limit))
            except Exception as exc:
                self._json(500, {"error": str(exc)})
            return
        self._json(404, {"error": "not found"})

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        ctype = self.headers.get("Content-Type", "")
        if parsed.path == "/api/upload-step" and "multipart/form-data" in ctype:
            self._handle_upload_step()
            return
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length) if length else b"{}"
        try:
            payload = json.loads(body.decode("utf-8"))
        except json.JSONDecodeError:
            self._json(400, {"error": "invalid json"})
            return
        if parsed.path == "/api/gate-advice":
            try:
                import moldflow_gate_advisor as advisor

                self._json(200, advisor.advise_gates(
                    dict(payload.get("bbox_mm") or {}),
                    payload.get("thickness_mm"),
                    payload.get("material_id"),
                ))
            except Exception as exc:
                self._json(500, {"error": str(exc)})
            return
        if parsed.path == "/api/preview":
            self._handle_preview(payload)
        elif parsed.path == "/api/defect-preview":
            self._handle_defect_preview(payload)
        elif parsed.path == "/api/export-job":
            self._handle_export_job(payload)
        else:
            self._json(404, {"error": "not found"})

    def _handle_preview(self, payload: dict) -> None:
        step_raw = payload.get("step_path", "")
        step_p = Path(step_raw) if step_raw else None
        if step_p and not step_p.is_absolute():
            step_p = (ROOT / step_p).resolve()
        try:
            stl = _ensure_preview(step_p)
            import moldflow_step_case_builder as mscb

            if step_p and step_p.exists():
                bbox = mscb.step_bbox_mm(step_p)
            else:
                bbox = mscb.step_bbox_mm(
                    DEFAULT_STEP if DEFAULT_STEP.exists() else mscb.ensure_sample_step()
                )
            self._json(
                200,
                {
                    "stl_url": f"/api/preview.stl?step={step_p.as_posix() if step_p else ''}",
                    "bbox_mm": bbox,
                    "path": str(stl),
                    "step_path": str(step_p) if step_p else None,
                },
            )
        except Exception as exc:
            self._json(500, {"error": str(exc)})

    def _handle_defect_preview(self, payload: dict) -> None:
        try:
            import cae_te_engine as engine

            params = dict(payload.get("process") or payload.get("openfoam_params") or {})
            defects = dict(payload.get("defects") or {})
            kpis = dict(payload.get("kpis") or {})
            step_raw = payload.get("step_path") or ""
            if step_raw:
                step_p = Path(step_raw)
                if not step_p.is_absolute():
                    step_p = (ROOT / step_p).resolve()
                if step_p.exists():
                    import moldflow_step_case_builder as mscb

                    bbox = mscb.step_bbox_mm(step_p)
                    kpis.setdefault("cad_bbox_length_mm", bbox.get("length", 0))
                    kpis.setdefault("cad_bbox_width_mm", bbox.get("width", 0))
                    kpis.setdefault("cad_bbox_height_mm", bbox.get("height", 0))
            if "fill_fraction_pct" not in defects:
                defects["fill_fraction_pct"] = payload.get("fill_fraction_pct", 95.0)
            preview = engine._estimate_sink_flash_kpis(defects, params, kpis)
            self._json(200, {"preview": preview})
        except Exception as exc:
            self._json(500, {"error": str(exc)})

    def _handle_upload_step(self) -> None:
        try:
            UPLOADS.mkdir(parents=True, exist_ok=True)
            fields = _parse_multipart(self.headers, self.rfile)
            if "file" not in fields:
                self._json(400, {"error": "missing file field"})
                return
            filename, content = fields["file"]
            if not content:
                self._json(400, {"error": "empty upload"})
                return
            fname = _safe_name(filename or "upload.step")
            stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            dest = UPLOADS / f"{stamp}_{fname}"
            dest.write_bytes(content)
            import moldflow_step_case_builder as mscb

            bbox = mscb.step_bbox_mm(dest)
            _ensure_preview(dest)
            rel = dest.relative_to(ROOT).as_posix()
            self._json(
                200,
                {
                    "step_path": rel,
                    "bbox_mm": bbox,
                    "stl_url": f"/api/preview.stl?step={rel}",
                },
            )
        except Exception as exc:
            self._json(500, {"error": str(exc)})

    def _handle_export_job(self, payload: dict) -> None:
        try:
            JOBS.mkdir(parents=True, exist_ok=True)
            stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            job_id = payload.get("job_id") or f"studio_{stamp}"
            safe_id = re.sub(r"[^\w\-]+", "_", str(job_id))[:80]
            gate_spec = payload.get("gate_spec") or {}
            gate_path = SAMPLES / f"gate_spec_{safe_id}.json"
            gate_path.write_text(json.dumps(gate_spec, ensure_ascii=False, indent=2), encoding="utf-8")

            category = str(payload.get("category", "resin_fill_cad"))
            params = dict(payload.get("openfoam_params") or {})
            params, safe_defaults_applied = _apply_safe_moldflow_defaults(params, category)
            params["gate_spec_path"] = gate_path.relative_to(ROOT).as_posix()
            step = payload.get("step_path")
            if step:
                params["step_path"] = step

            job_doc = {
                "job_id": safe_id,
                "created_at": datetime.now().isoformat(),
                "category": category,
                "analysis": payload.get("analysis") or {},
                "process": _apply_safe_moldflow_defaults(payload.get("process") or {}, category)[0],
                "material": payload.get("material") or {},
                "gate_spec_path": params["gate_spec_path"],
                "openfoam_params": params,
                "safe_defaults_applied": safe_defaults_applied,
                "trial_command": (
                    "python scripts/cae_te_remote_trial.py "
                    f"--category {category} "
                    f"--trial-id {safe_id} "
                    f"--params-file {JOBS.relative_to(ROOT).as_posix()}/{safe_id}_params.json"
                ),
            }
            job_path = JOBS / f"{safe_id}.json"
            params_path = JOBS / f"{safe_id}_params.json"
            job_path.write_text(json.dumps(job_doc, ensure_ascii=False, indent=2), encoding="utf-8")
            params_path.write_text(json.dumps(params, ensure_ascii=False, indent=2), encoding="utf-8")
            self._json(200, {"job_id": safe_id, "job_path": str(job_path.relative_to(ROOT)), "params_path": str(params_path.relative_to(ROOT)), "safe_defaults_applied": safe_defaults_applied})
        except Exception as exc:
            self._json(500, {"error": str(exc)})

    def _send_bytes(self, data: bytes, mime: str) -> None:
        self.send_response(200)
        self._cors()
        self.send_header("Content-Type", mime)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _json(self, code: int, obj: dict) -> None:
        data = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self._cors()
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, fmt: str, *args) -> None:
        print(f"[cae-studio] {self.address_string()} {fmt % args}", flush=True)


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Moldflow CAE Studio API")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--ensure-preview", action="store_true")
    args = parser.parse_args()
    if args.ensure_preview:
        p = _ensure_preview()
        print(f"[OK] preview: {p}")
    host = "127.0.0.1"
    httpd = HTTPServer((host, args.port), CaeStudioHandler)
    print(f"Moldflow CAE Studio API http://{host}:{args.port}", flush=True)
    httpd.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
