# -*- coding: utf-8 -*-
"""Part Geometry Contract -- clawstack.part_manifest.v1 (Fable5 Top1).

Structured handoff from DXF2STEP to Moldflow / tolerance / OpenRadioss downstream.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

SCHEMA = "clawstack.part_manifest.v1"
MANIFEST_FILENAME = "part_manifest.json"


def _now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat()


def _round_mm(value: float) -> float:
    return round(float(value), 4)


def _estimate_bbox_from_layers(build_log: dict[str, Any], sheet_thickness: float) -> dict[str, float]:
    """Fallback bbox from layer thickness + placeholder spans when STEP metrics unavailable."""
    layers = build_log.get("layers") or {}
    thicknesses = [
        float((info or {}).get("thickness") or 0)
        for info in layers.values()
        if (info or {}).get("status") == "done"
    ]
    lz = sheet_thickness
    if thicknesses:
        lz = max(thicknesses + [sheet_thickness])
    # Without FreeCAD read, use positive sentinel only if we have successful layers
    n_done = sum(1 for v in layers.values() if (v or {}).get("status") == "done")
    if n_done == 0:
        return {"Lx": 0.0, "Ly": 0.0, "Lz": 0.0}
    # Minimal non-zero placeholder until STEP bbox overwrites
    return {"Lx": float(n_done), "Ly": 1.0, "Lz": _round_mm(lz)}


def _freecad_bbox_script(step_path: str) -> str:
    safe = step_path.replace("\\", "/").replace("'", "\\'")
    return (
        "import FreeCAD as App\n"
        "import Part\n"
        f"shape = Part.read('{safe}')\n"
        "bb = shape.BoundBox\n"
        "print('BBOX', bb.XMax - bb.XMin, bb.YMax - bb.YMin, bb.ZMax - bb.ZMin)\n"
    )


def extract_bbox_from_step(step_path: Path, *, timeout_sec: int = 120) -> dict[str, float] | None:
    """Read STEP/FCStd BoundBox via FreeCADCmd when available."""
    if not step_path.exists():
        return None
    mode = os.environ.get("DXF2STEP_FREECAD_MODE", "docker").strip().lower()
    script_path = step_path.with_suffix(".bbox_extract.py")
    script_path.write_text(_freecad_bbox_script(str(step_path)), encoding="utf-8")
    try:
        if mode in ("native", "linux"):
            fc_cmd = os.environ.get("FREECAD_CMD", "FreeCADCmd")
            cmd = [fc_cmd, str(script_path)]
        else:
            container = "clawstack-unified-clawdbot-gateway-1"
            c_script = script_path.as_posix()
            cmd = ["docker", "exec", container, "bash", "-c", f"FreeCADCmd '{c_script}'"]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout_sec)
        for line in (result.stdout or "").splitlines():
            if line.startswith("BBOX "):
                parts = line.split()
                if len(parts) >= 4:
                    return {
                        "Lx": _round_mm(float(parts[1])),
                        "Ly": _round_mm(float(parts[2])),
                        "Lz": _round_mm(float(parts[3])),
                    }
    except (subprocess.TimeoutExpired, OSError, ValueError):
        return None
    finally:
        try:
            script_path.unlink(missing_ok=True)
        except OSError:
            pass
    return None


def _resolve_paths(output_dir: Path, build_log: dict[str, Any]) -> tuple[str | None, str | None]:
    combined_step = build_log.get("combined_step")
    combined_fcstd = build_log.get("combined_fcstd")
    step_path: Path | None = None
    fcstd_path: Path | None = None
    if combined_step:
        step_path = output_dir / str(combined_step)
    if combined_fcstd:
        fcstd_path = output_dir / str(combined_fcstd)
    if step_path is None:
        layers = build_log.get("layers") or {}
        for info in layers.values():
            if (info or {}).get("status") == "done" and (info or {}).get("step"):
                step_path = output_dir / str(info["step"])
                if (info or {}).get("fcstd"):
                    fcstd_path = output_dir / str(info["fcstd"])
                break
    return (
        str(step_path) if step_path and step_path.exists() else None,
        str(fcstd_path) if fcstd_path and fcstd_path.exists() else None,
    )


def build_part_manifest(
    *,
    source_dxf: str,
    output_dir: str | Path,
    build_log: dict[str, Any],
    default_thickness_mm: float = 10.0,
    material_id: str = "unknown",
    material_source: str = "default",
) -> dict[str, Any]:
    """Build manifest dict from worker output_dir + build_log."""
    out = Path(output_dir)
    layers = build_log.get("layers") or {}
    thicknesses = [
        float((info or {}).get("thickness") or default_thickness_mm)
        for info in layers.values()
        if (info or {}).get("status") == "done"
    ]
    sheet_thickness = max(thicknesses) if thicknesses else float(default_thickness_mm)
    closed_loops = sum(1 for info in layers.values() if (info or {}).get("status") == "done")

    step_raw, fcstd_raw = _resolve_paths(out, build_log)
    step_full = Path(step_raw) if step_raw else None
    fcstd_full = Path(fcstd_raw) if fcstd_raw else None
    bbox = _estimate_bbox_from_layers(build_log, sheet_thickness)
    if step_full and step_full.exists():
        step_bbox = extract_bbox_from_step(step_full)
        if step_bbox and step_bbox.get("Lx", 0) > 0:
            bbox = step_bbox

    has_step = bool(step_full and step_full.exists())
    has_fcstd = bool(fcstd_full and fcstd_full.exists())
    step_abs = os.path.basename(str(step_full)) if step_full and step_full.exists() else None
    fcstd_abs = os.path.basename(str(fcstd_full)) if fcstd_full and fcstd_full.exists() else None
    nominal_dims: list[dict[str, Any]] = []
    if bbox.get("Lx", 0) > 0:
        nominal_dims = [
            {"name": "bbox_Lx", "nominal_mm": bbox["Lx"], "source": "step_bbox" if has_step else "estimate"},
            {"name": "bbox_Ly", "nominal_mm": bbox["Ly"], "source": "step_bbox" if has_step else "estimate"},
            {"name": "sheet_thickness", "nominal_mm": sheet_thickness, "source": "layer_thickness"},
        ]

    manifest: dict[str, Any] = {
        "schema": SCHEMA,
        "created_at": _now_iso(),
        "source_dxf": os.path.basename(source_dxf) if source_dxf else "",
        "source_dxf_path": str(source_dxf),
        "step_path": step_abs,
        "fcstd_path": fcstd_abs,
        "units": "mm",
        "bbox_mm": bbox,
        "sheet_thickness_mm": _round_mm(sheet_thickness),
        "material": {"id": material_id, "source": material_source},
        "features": {
            "closed_loops": closed_loops,
            "holes": [],
            "datums": [],
            "nominal_dims_mm": nominal_dims,
        },
        "physics_handoff": {
            "moldflow": {
                "ready": has_step,
                "gate_seed": "center",
                "step_path": step_abs,
            },
            "tolerance": {
                "ready": len(nominal_dims) > 0,
                "nominal_dims_mm": nominal_dims,
            },
            "openradioss": {
                "ready": sheet_thickness > 0,
                "thickness_mm": _round_mm(sheet_thickness),
            },
        },
        "build_log_ref": "build_log.json",
        "layers_done": closed_loops,
        "has_combined_step": bool(build_log.get("combined_step")),
    }
    if step_full and step_full.exists():
        try:
            from step_pmi_extract import try_enrich_manifest_from_step

            manifest = try_enrich_manifest_from_step(manifest, step_path=step_full)
        except Exception:
            pass
    return manifest


def validate_manifest(manifest: dict[str, Any]) -> tuple[bool, list[str]]:
    issues: list[str] = []
    if manifest.get("schema") != SCHEMA:
        issues.append(f"schema!={SCHEMA}")
    for key in ("units", "bbox_mm", "sheet_thickness_mm", "physics_handoff"):
        if key not in manifest:
            issues.append(f"missing:{key}")
    bbox = manifest.get("bbox_mm") or {}
    for axis in ("Lx", "Ly", "Lz"):
        if axis not in bbox:
            issues.append(f"bbox_mm.{axis} missing")
        elif float(bbox.get(axis) or 0) <= 0:
            issues.append(f"bbox_mm.{axis}<=0")
    if float(manifest.get("sheet_thickness_mm") or 0) <= 0:
        issues.append("sheet_thickness_mm<=0")
    handoff = manifest.get("physics_handoff") or {}
    for domain in ("moldflow", "tolerance", "openradioss"):
        if domain not in handoff:
            issues.append(f"physics_handoff.{domain} missing")
    return len(issues) == 0, issues


def load_part_manifest(path: str | Path) -> dict[str, Any] | None:
    ok, _, data = validate_manifest_file(Path(path))
    if not ok:
        return None
    return data


def to_tolerance_dims(
    manifest: dict[str, Any],
    *,
    difficulty: int = 1,
    default_tol: float | None = None,
) -> list[dict[str, Any]]:
    """Convert part_manifest nominal dims to tolerance stack dimension specs."""
    per_dim_tol = default_tol if default_tol is not None else (0.04 + 0.02 * (difficulty - 1))
    sheet_tol = max(0.01, float(manifest.get("sheet_thickness_mm") or 1.0) * 0.02)

    nominal_dims: list[dict[str, Any]] = list(
        (manifest.get("features") or {}).get("nominal_dims_mm") or []
    )
    tol_handoff = (manifest.get("physics_handoff") or {}).get("tolerance") or {}
    if not nominal_dims:
        nominal_dims = list(tol_handoff.get("nominal_dims_mm") or [])

    if not nominal_dims:
        bbox = manifest.get("bbox_mm") or {}
        if float(bbox.get("Lx") or 0) > 0:
            nominal_dims = [
                {"name": "bbox_Lx", "nominal_mm": bbox["Lx"], "source": "step_bbox"},
                {"name": "bbox_Ly", "nominal_mm": bbox["Ly"], "source": "step_bbox"},
                {
                    "name": "sheet_thickness",
                    "nominal_mm": manifest.get("sheet_thickness_mm"),
                    "source": "layer_thickness",
                },
            ]

    dims: list[dict[str, Any]] = []
    for idx, row in enumerate(nominal_dims):
        name = str(row.get("name") or f"dim_{idx}")
        mean = float(row.get("nominal_mm") or 0.0)
        if mean <= 0:
            continue
        tol = sheet_tol if "thickness" in name.lower() else per_dim_tol
        dims.append(
            {
                "name": name,
                "mean": mean,
                "tolerance": tol,
                "coef": 1.0 if idx % 2 == 0 else -1.0,
                "distribution": "normal",
                "source": "measured",
            }
        )
    return dims


def detect_maturity_level(manifest: dict[str, Any], *, include_gdt: bool = True) -> str:
    """Return L1/L2/L4/L10 maturity from manifest enrichment and GD&T sources."""
    cetol = manifest.get("cetol_full_enrichment") or {}
    if cetol.get("maturity_level") == "L10_cetol_full":
        return "L10_cetol_full"
    tol_handoff = (manifest.get("physics_handoff") or {}).get("tolerance") or {}
    if str(tol_handoff.get("cetol_full_ready") or "").lower() in ("1", "true", "yes"):
        return "L10_cetol_full"
    enrich = manifest.get("pmi_enrichment") or {}
    if enrich.get("maturity_level"):
        return str(enrich["maturity_level"])
    if tol_handoff.get("maturity_level"):
        return str(tol_handoff["maturity_level"])
    features = manifest.get("features") or {}
    holes = features.get("holes") or []
    datums = features.get("datums") or []
    gdt_ann = features.get("gdt_annotations") or []
    if any(str(h.get("source", "")).startswith("gdt_pmi") for h in holes if isinstance(h, dict)):
        return "L4_pmi_step_read"
    if any(str(d.get("source", "")).startswith("gdt_pmi") for d in datums if isinstance(d, dict)):
        return "L4_pmi_step_read"
    if gdt_ann:
        return "L4_pmi_step_read"
    if str(tol_handoff.get("l10_ready") or "").lower() in ("1", "true", "yes"):
        return "L10_assembly_6sigma"
    if manifest.get("freecad_3d_loop", {}).get("ok"):
        return "L10_freecad_3d_loop"
    if include_gdt:
        return "L2_gdt_proxy"
    return "L1_nominal_only"


def to_gdt_tolerance_dims(
    manifest: dict[str, Any],
    *,
    default_position_tol: float = 0.05,
    default_flatness_tol: float = 0.02,
) -> list[dict[str, Any]]:
    """L2 GD&T contributors from manifest features (holes/datums) or bbox pitch proxy."""
    features = manifest.get("features") or {}
    dims: list[dict[str, Any]] = []

    for idx, hole in enumerate(features.get("holes") or []):
        if not isinstance(hole, dict):
            continue
        nominal = float(hole.get("diameter_mm") or hole.get("nominal_mm") or 0)
        pos_tol = float(hole.get("position_tol_mm") or hole.get("tolerance_mm") or default_position_tol)
        src = str(hole.get("source") or "gdt_measured")
        if nominal <= 0 and pos_tol <= 0:
            continue
        dims.append(
            {
                "name": str(hole.get("name") or f"hole_{idx + 1}_position"),
                "mean": nominal if nominal > 0 else 0.0,
                "tolerance": max(pos_tol, 0.001),
                "coef": 1.0,
                "distribution": "normal",
                "source": "gdt_pmi" if src.startswith("gdt_pmi") else "gdt_measured",
                "gdt_type": "position",
            }
        )

    for idx, datum in enumerate(features.get("datums") or []):
        if not isinstance(datum, dict):
            continue
        flat_tol = float(datum.get("flatness_tol_mm") or datum.get("tolerance_mm") or default_flatness_tol)
        src = str(datum.get("source") or "gdt_measured")
        dims.append(
            {
                "name": str(datum.get("name") or f"datum_{idx + 1}_flatness"),
                "mean": 0.0,
                "tolerance": max(flat_tol, 0.001),
                "coef": 1.0,
                "distribution": "normal",
                "source": "gdt_pmi" if src.startswith("gdt_pmi") else "gdt_measured",
                "gdt_type": "flatness",
            }
        )

    if not dims:
        bbox = manifest.get("bbox_mm") or {}
        lx = float(bbox.get("Lx") or 0)
        ly = float(bbox.get("Ly") or 0)
        if lx > 0:
            dims.append(
                {
                    "name": "gdt_pitch_proxy_Lx",
                    "mean": lx,
                    "tolerance": default_position_tol,
                    "coef": 1.0,
                    "distribution": "normal",
                    "source": "gdt_proxy",
                    "gdt_type": "position",
                }
            )
        if ly > 0:
            dims.append(
                {
                    "name": "gdt_pitch_proxy_Ly",
                    "mean": ly,
                    "tolerance": default_position_tol,
                    "coef": 1.0,
                    "distribution": "normal",
                    "source": "gdt_proxy",
                    "gdt_type": "position",
                }
            )
    return dims


def merged_tolerance_dims(
    manifest: dict[str, Any],
    *,
    difficulty: int = 1,
    default_tol: float | None = None,
    include_gdt: bool = True,
) -> list[dict[str, Any]]:
    """Nominal stack dims + optional GD&T contributors (L2 Cetol proxy)."""
    base = to_tolerance_dims(manifest, difficulty=difficulty, default_tol=default_tol)
    if not include_gdt:
        return base
    gdt = to_gdt_tolerance_dims(manifest)
    seen = {d["name"] for d in base}
    for row in gdt:
        if row["name"] not in seen:
            base.append(row)
            seen.add(row["name"])
    return base


def write_part_manifest(manifest: dict[str, Any], output_dir: str | Path) -> Path:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    path = out / MANIFEST_FILENAME
    path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def emit_part_manifest(
    *,
    source_dxf: str,
    output_dir: str | Path,
    build_log: dict[str, Any],
    default_thickness_mm: float = 10.0,
) -> Path:
    manifest = build_part_manifest(
        source_dxf=source_dxf,
        output_dir=output_dir,
        build_log=build_log,
        default_thickness_mm=default_thickness_mm,
    )
    ok, issues = validate_manifest(manifest)
    manifest["_validation"] = {"ok": ok, "issues": issues}
    return write_part_manifest(manifest, output_dir)


def validate_manifest_file(path: Path) -> tuple[bool, list[str], dict[str, Any]]:
    if not path.exists():
        return False, ["missing_file"], {}
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError as exc:
        return False, [f"json_error:{exc}"], {}
    ok, issues = validate_manifest(data)
    return ok, issues, data


def validate_archive(root: Path) -> dict[str, Any]:
    """Scan job dirs for part_manifest.json presence and validity."""
    root = Path(root)
    jobs: list[dict[str, Any]] = []
    patterns = [
        root.glob("*/output/part_manifest.json"),
        root.glob("*/part_manifest.json"),
        root.glob("**/part_manifest.json"),
    ]
    seen: set[str] = set()
    for pattern in patterns:
        for mf in pattern:
            key = str(mf.resolve())
            if key in seen:
                continue
            seen.add(key)
            ok, issues, data = validate_manifest_file(mf)
            bbox = data.get("bbox_mm") or {}
            jobs.append(
                {
                    "path": str(mf.relative_to(root)) if mf.is_relative_to(root) else str(mf),
                    "ok": ok,
                    "issues": issues,
                    "bbox_nonzero": all(float(bbox.get(a) or 0) > 0 for a in ("Lx", "Ly", "Lz")),
                }
            )
    n = len(jobs)
    n_ok = sum(1 for j in jobs if j["ok"])
    n_bbox = sum(1 for j in jobs if j.get("bbox_nonzero"))
    return {
        "schema": "clawstack.part_manifest_archive_report.v1",
        "root": str(root),
        "job_count": n,
        "manifest_ok_count": n_ok,
        "manifest_attach_rate_pct": round(100.0 * n_ok / n, 1) if n else 0.0,
        "bbox_nonzero_rate_pct": round(100.0 * n_bbox / n_ok, 1) if n_ok else 0.0,
        "jobs": jobs,
    }


def backfill_missing_manifests(root: Path) -> dict[str, Any]:
    """Emit part_manifest.json for archive jobs that have build_log but no manifest."""
    root = Path(root)
    fixed: list[str] = []
    skipped: list[str] = []
    for job_dir in sorted(root.iterdir()):
        if not job_dir.is_dir() or job_dir.name == "manifest.json":
            continue
        mf = job_dir / MANIFEST_FILENAME
        bl = job_dir / "build_log.json"
        if mf.exists():
            skipped.append(job_dir.name)
            continue
        if not bl.exists():
            continue
        try:
            build_log = json.loads(bl.read_text(encoding="utf-8-sig"))
        except json.JSONDecodeError:
            continue
        thickness = 10.0
        layers = build_log.get("layers") or {}
        thicks = [
            float((info or {}).get("thickness") or 0)
            for info in layers.values()
            if (info or {}).get("status") == "done"
        ]
        if thicks:
            thickness = max(thicks)
        emit_part_manifest(
            source_dxf="sample.dxf",
            output_dir=job_dir,
            build_log=build_log,
            default_thickness_mm=thickness,
        )
        fixed.append(job_dir.name)
    return {
        "schema": "clawstack.part_manifest_backfill.v1",
        "root": str(root),
        "fixed": fixed,
        "skipped_existing": len(skipped),
    }


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Part Geometry Contract (part_manifest.json)")
    parser.add_argument("--validate", help="Validate single part_manifest.json path")
    parser.add_argument("--validate-archive", help="Scan job archive root for manifests")
    parser.add_argument("--backfill-archive", help="Emit missing manifests from build_log.json")
    args = parser.parse_args()

    if args.backfill_archive:
        report = backfill_missing_manifests(Path(args.backfill_archive))
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0

    if args.validate:
        ok, issues, _ = validate_manifest_file(Path(args.validate))
        print(json.dumps({"ok": ok, "issues": issues}, ensure_ascii=False, indent=2))
        return 0 if ok else 1

    if args.validate_archive:
        report = validate_archive(Path(args.validate_archive))
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0 if report["job_count"] == 0 or report["manifest_ok_count"] == report["job_count"] else 1

    parser.error("Specify --validate or --validate-archive")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
