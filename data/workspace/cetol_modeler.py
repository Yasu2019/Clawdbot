# -*- coding: utf-8 -*-
"""CETOL-class Modeler + Analyzer from part_manifest (not CAD-embedded).

Builds kinematic frames, features, joints, measures, Advisor flags, and
Analyzer cross-tables from actual geometry (bbox / holes / datums / PMI)
or from an explicit cetol_model JSON on the manifest.

Truth Gate: this is a CETOL-class workflow in our web stack. It is not
commercial Sigmetrix CETOL 6-sigma. Do not label SUCCESS / commercial parity.

Cybernet lesson: dimension contribution != tolerance contribution.
  dimension: |a_i * x_i_nominal| / sum |a_j * x_j_nominal|
  tolerance: (a_i * sigma_i)^2 / sigma_Y^2  (MSM)
"""
from __future__ import annotations

import json
import math
import re
import sys
from pathlib import Path
from typing import Any

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import numpy as np

_WORKSPACE = Path(__file__).resolve().parent
_APPS_DXF2STEP = _WORKSPACE / "apps" / "dxf2step"
for _p in (_WORKSPACE, _APPS_DXF2STEP):
    sp = str(_p)
    if sp in sys.path:
        sys.path.remove(sp)
    sys.path.insert(0, sp)
# DXF2STEP must win over scripts/part_geometry_contract.py
sys.path.insert(0, str(_APPS_DXF2STEP))

import tolerance_stackup_engine as tse  # noqa: E402
import cetol_process_physics as cpp  # noqa: E402

FORBIDDEN_GENERIC_FRAMES = ("BasePlate", "Bracket", "PinJoin", "GapSensor")
STATION_MAP = {
    "station1_blanking_set": "BL",
    "station2_bending_set": "BE",
    "station3_trim_set": "TR",
    "strip_thickness_var": "BL",
    "guide_play": "ASSY",
}


def _safe_float(v: Any, default: float = 0.0) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def part_slug(manifest: dict[str, Any], job_id: str | None = None) -> str:
    raw = (
        job_id
        or manifest.get("job_id")
        or Path(str(manifest.get("source_dxf") or "part")).stem
    )
    slug = re.sub(r"[^A-Za-z0-9]+", "_", str(raw)).strip("_") or "Part"
    return slug[:48]


def bbox_xyz(manifest: dict[str, Any]) -> tuple[float, float, float]:
    bbox = manifest.get("bbox_mm") or {}
    lx = _safe_float(bbox.get("Lx"))
    ly = _safe_float(bbox.get("Ly"))
    lz = _safe_float(bbox.get("Lz"))
    sheet = _safe_float(manifest.get("sheet_thickness_mm"), 1.0)
    if lx <= 0:
        lx = 40.0
    if ly <= 0:
        ly = 20.0
    if lz <= 0:
        lz = sheet if sheet > 0 else 2.0
    return lx, ly, lz


def _hole_xyz(hole: dict[str, Any], index: int, lx: float, ly: float, lz: float, n: int) -> tuple[float, float, float]:
    for key in ("xyz_mm", "center_mm", "position_mm"):
        xyz = hole.get(key)
        if isinstance(xyz, (list, tuple)) and len(xyz) >= 2:
            z = _safe_float(xyz[2], lz) if len(xyz) > 2 else lz
            return _safe_float(xyz[0]), _safe_float(xyz[1]), z
    if hole.get("x_mm") is not None or hole.get("y_mm") is not None:
        return (
            _safe_float(hole.get("x_mm"), (index + 1) * lx / (n + 1)),
            _safe_float(hole.get("y_mm"), ly * 0.5),
            _safe_float(hole.get("z_mm"), lz),
        )
    frac = (index + 1) / (n + 1)
    return lx * frac, ly * 0.5, lz


def _tol3(value: float, z_scale: float = 1.2) -> tuple[float, float, float]:
    t = max(_safe_float(value, 0.02), 0.001)
    return (t, t, t * z_scale)


def mmc_lmc_bonus(
    *,
    material_condition: str | None,
    position_tol_mm: float,
    hole_diameter_mm: float = 0.0,
    hole_size_tol_mm: float = 0.0,
    pin_diameter_mm: float = 0.0,
    pin_size_tol_mm: float = 0.0,
    pin_material_condition: str | None = None,
) -> dict[str, Any]:
    """ASME-style position bonus at MMC. Not a certified Y14.5 solver.

    Hole MMC: bonus = hole size tolerance (max departure toward LMC).
    Pin MMC: add pin size tolerance. LMC does not add assembly-float bonus.
    When both diameters exist: also record H_MMC - F_MMC clearance (floating fastener).
    """
    mc = str(material_condition or "").upper()
    pin_mc = str(pin_material_condition or "").upper()
    pos = max(_safe_float(position_tol_mm), 0.0)
    if mc not in ("MMC", "LMC") and pin_mc not in ("MMC", "LMC"):
        return {
            "status": "INSUFFICIENT",
            "bonus_mm": 0.0,
            "effective_position_tol_mm": pos,
            "reason": "no MMC/LMC in data",
        }
    hole_dia = _safe_float(hole_diameter_mm)
    hole_st = max(_safe_float(hole_size_tol_mm), 0.0)
    pin_dia = _safe_float(pin_diameter_mm)
    pin_st = max(_safe_float(pin_size_tol_mm), 0.0)
    if hole_dia <= 0 and pin_dia <= 0:
        return {
            "status": "INSUFFICIENT",
            "bonus_mm": 0.0,
            "effective_position_tol_mm": pos,
            "reason": "no hole/pin diameter",
        }
    if hole_st <= 0 and pin_st <= 0:
        return {
            "status": "INSUFFICIENT",
            "bonus_mm": 0.0,
            "effective_position_tol_mm": pos,
            "reason": "no size tolerance for bonus",
        }
    hole_bonus = hole_st if mc == "MMC" else 0.0
    pin_bonus = pin_st if pin_mc == "MMC" else 0.0
    bonus = hole_bonus + pin_bonus
    out: dict[str, Any] = {
        "status": "APPLIED" if bonus > 0 else "DECLARED",
        "bonus_mm": bonus,
        "effective_position_tol_mm": pos + bonus,
        "rule": "T_eff = T_pos + T_size(MMC). LMC adds no assembly-float bonus.",
        "formula": "ASME-style bonus = size_tol at MMC (max to LMC). Not certified Y14.5.",
        "material_condition": mc or None,
        "pin_material_condition": pin_mc or None,
    }
    if hole_dia > 0 and pin_dia > 0:
        h_mmc = hole_dia - hole_st
        f_mmc = pin_dia + pin_st
        out["clearance_mmc_mm"] = h_mmc - f_mmc
        out["floating_fastener"] = "H_MMC - F_MMC recorded; position not replaced by H-F"
    return out


def frames_from_manifest(
    manifest: dict[str, Any],
    *,
    job_id: str | None = None,
) -> list[dict[str, Any]]:
    """Kinematic frames from bbox / holes / datums. Never the old 4-name demo."""
    explicit = manifest.get("cetol_model") or manifest.get("cetol_frames")
    if isinstance(explicit, dict) and isinstance(explicit.get("frames"), list) and explicit["frames"]:
        return [dict(f) for f in explicit["frames"] if isinstance(f, dict)]

    slug = part_slug(manifest, job_id)
    lx, ly, lz = bbox_xyz(manifest)
    sheet = _safe_float(manifest.get("sheet_thickness_mm"), lz)
    feats = manifest.get("features") or {}
    holes = [h for h in (feats.get("holes") or []) if isinstance(h, dict)]
    datums = [d for d in (feats.get("datums") or []) if isinstance(d, dict)]

    datum_flat = 0.02
    if datums:
        datum_flat = max(_safe_float(datums[0].get("flatness_tol_mm"), 0.02), 0.001)

    frames: list[dict[str, Any]] = [
        {
            "name": f"{slug}_DieBase",
            "role": "datum",
            "t_nom": (0.0, 0.0, 0.0),
            "r_nom": (0.0, 0.0, 0.0),
            "t_tol": _tol3(datum_flat),
            "r_tol": (0.01, 0.01, 0.01),
            "source": "gdt_pmi" if datums else "gdt_proxy",
            "geometric_form": {
                "flatness_mm": datum_flat,
                "tilt_deg": math.degrees(math.atan(datum_flat / max(lx, 1.0))),
                "source": "chase1996_form",
            },
        },
        {
            "name": f"{slug}_Strip",
            "role": "part",
            "t_nom": (0.0, 0.0, sheet if sheet > 0 else lz),
            "r_nom": (0.0, 0.0, 0.0),
            "t_tol": _tol3(min(0.05, max(0.01, sheet * 0.005))),
            "r_tol": (0.02, 0.02, 0.02),
            "source": "measured",
        },
        {
            "name": f"{slug}_Pitch",
            "role": "measure_close",
            "t_nom": (lx, 0.0, 0.0),
            "r_nom": (0.0, 0.0, 0.0),
            "t_tol": _tol3(0.04),
            "r_tol": (0.02, 0.02, 0.02),
            "source": "gdt_proxy",
        },
        {
            "name": f"{slug}_GapZ",
            "role": "measure_close",
            "t_nom": (0.0, 0.0, lz),
            "r_nom": (0.0, 0.0, 0.0),
            "t_tol": _tol3(0.03, 1.0),
            "r_tol": (0.01, 0.01, 0.01),
            "source": "pmi" if (feats.get("gdt_annotations") or datums) else "measured",
        },
    ]
    n_holes = min(len(holes), 6)
    for i, hole in enumerate(holes[:6]):
        hx, hy, hz = _hole_xyz(hole, i, lx, ly, lz, n_holes)
        pos_tol = max(_safe_float(hole.get("position_tol_mm") or hole.get("tolerance_mm"), 0.05), 0.001)
        hname = re.sub(r"[^A-Za-z0-9]+", "_", str(hole.get("name") or f"hole_{i + 1}")).strip("_")
        bonus = mmc_lmc_bonus(
            material_condition=str(hole.get("mmc") or hole.get("material_condition") or "") or None,
            position_tol_mm=pos_tol,
            hole_diameter_mm=_safe_float(hole.get("diameter_mm")),
            hole_size_tol_mm=_safe_float(hole.get("diameter_tol_mm") or hole.get("size_tol_mm")),
            pin_diameter_mm=_safe_float(hole.get("pin_diameter_mm")),
            pin_size_tol_mm=_safe_float(hole.get("pin_tol_mm") or hole.get("pin_size_tol_mm")),
            pin_material_condition=str(hole.get("pin_mmc") or hole.get("pin_material_condition") or "") or None,
        )
        eff = _safe_float(bonus.get("effective_position_tol_mm"), pos_tol) or pos_tol
        rec = dict(bonus)
        rec["feature"] = str(hole.get("name") or hname)
        frames.append({
            "name": f"{slug}_{hname}",
            "role": "feature_cylinder",
            "t_nom": (hx, hy, hz),
            "r_nom": (0.0, 0.0, 0.0),
            "t_tol": (eff, eff, pos_tol * 0.5),
            "r_tol": (0.015, 0.015, 0.02),
            "source": str(hole.get("source") or "gdt_measured"),
            "diameter_mm": _safe_float(hole.get("diameter_mm")),
            "mmc_bonus": rec,
        })
    tilt = float((frames[0].get("geometric_form") or {}).get("tilt_deg") or 0.01)
    frames[0]["r_tol"] = (max(0.01, tilt), max(0.01, tilt), 0.01)
    orh = (manifest.get("physics_handoff") or {}).get("openradioss") or {}
    if isinstance(orh, dict):
        sb = _safe_float(orh.get("springback_mm"))
        if abs(sb) > 1e-12:
            frames.append({
                "name": f"{slug}_Springback",
                "role": "process",
                "t_nom": (0.0, 0.0, sb),
                "r_nom": (0.0, 0.0, 0.0),
                "t_tol": (0.0, 0.0, max(abs(sb) * 0.1, 0.01)),
                "r_tol": (0.0, 0.0, 0.0),
                "source": "openradioss",
            })
    names = [str(f["name"]) for f in frames]
    for n in names:
        if n in FORBIDDEN_GENERIC_FRAMES:
            raise ValueError(f"generic frame {n} leaked into {slug} model")
    return frames


def loop_from_frames(frames: list[dict[str, Any]]) -> tse.VectorLoop3D:
    loop = tse.VectorLoop3D()
    for f in frames:
        if not f.get("name") or "t_nom" not in f:
            continue
        loop.add_frame(
            str(f["name"]),
            tuple(f.get("t_nom") or (0.0, 0.0, 0.0)),  # type: ignore[arg-type]
            tuple(f.get("r_nom") or (0.0, 0.0, 0.0)),  # type: ignore[arg-type]
            tuple(f.get("t_tol") or (0.0, 0.0, 0.0)),  # type: ignore[arg-type]
            tuple(f.get("r_tol") or (0.0, 0.0, 0.0)),  # type: ignore[arg-type]
            source=str(f.get("source") or "synthetic"),
            role=str(f.get("role") or "frame"),
        )
    return loop


def default_measures(manifest: dict[str, Any]) -> list[dict[str, Any]]:
    feats = manifest.get("features") or {}
    holes = [h for h in (feats.get("holes") or []) if isinstance(h, dict)]
    lx_guess, _ly_guess, _lz_guess = bbox_xyz(manifest)
    measures = [
        {
            "id": "gap_z",
            "label": "Gap Z (sheet / cavity height)",
            "kind": "linear",
            "direction": (0.0, 0.0, 1.0),
            "from_feature": "DieBase",
            "to_feature": "GapZ",
        },
        {
            "id": "pitch_x",
            "label": "Pitch X (strip / hole pitch)",
            "kind": "linear",
            "direction": (1.0, 0.0, 0.0),
            "from_feature": "DieBase",
            "to_feature": "Pitch",
        },
        {
            "id": "float_y",
            "label": "Assembly float Y",
            "kind": "linear",
            "direction": (0.0, 1.0, 0.0),
            "from_feature": "DieBase",
            "to_feature": "Strip",
        },
    ]
    if len(holes) >= 1:
        measures.append({
            "id": "hole_float",
            "label": "Hole position float (pin-hole clearance)",
            "kind": "linear",
            "direction": (1.0, 0.0, 0.0),
            "from_feature": "Strip",
            "to_feature": str(holes[0].get("name") or "hole_1"),
        })
    if len(holes) >= 2:
        a = holes[0].get("xyz_mm") or [0, 0, 0]
        b = holes[1].get("xyz_mm") or [lx_guess, 0, 0]
        dx = _safe_float(b[0], 0.0) - _safe_float(a[0], 0.0) if isinstance(b, (list, tuple)) and isinstance(a, (list, tuple)) else lx_guess
        dy = 0.0
        if isinstance(a, (list, tuple)) and isinstance(b, (list, tuple)) and len(a) > 1 and len(b) > 1:
            dy = _safe_float(b[1], 0.0) - _safe_float(a[1], 0.0)
        nrm = (dx * dx + dy * dy) ** 0.5 or 1.0
        measures.append({
            "id": "hole_pitch",
            "label": "Hole-to-hole pitch (STEP XYZ)",
            "kind": "linear",
            "direction": (dx / nrm, dy / nrm, 0.0),
            "from_feature": str(holes[0].get("name") or "hole_1"),
            "to_feature": str(holes[1].get("name") or "hole_2"),
            "nominal_mm": round(nrm, 4),
            "source": "step_topology",
        })
        measures.append({
            "id": "angular_rz",
            "label": "Hole-pair angular (strip twist)",
            "kind": "angular",
            "direction": (0.0, 0.0, 1.0),
            "axis": (0.0, 0.0, 1.0),
            "from_feature": "DieBase",
            "to_feature": "Strip",
        })
    return measures


def dual_contribution(
    dims: list[tse.StackDimension],
    *,
    nominals: dict[str, float] | None = None,
) -> dict[str, Any]:
    """Dimension contribution vs tolerance (MSM variance) contribution."""
    nominals = nominals or {}
    dim_abs: list[tuple[str, float]] = []
    for d in dims:
        x_nom = nominals.get(d.name)
        if x_nom is None:
            x_nom = d.mean if abs(d.mean) > 1e-12 else abs(d.coef)
        dim_abs.append((d.name, abs(d.coef * x_nom)))
    dim_sum = sum(v for _, v in dim_abs) or 1.0
    msm = tse.msm_stack(dims)
    tol_map = msm.get("sensitivity") or {}
    rows = []
    for name, v in dim_abs:
        tol = tol_map.get(name) or {}
        rows.append({
            "name": name,
            "dimension_contribution": round(v / dim_sum, 4),
            "tolerance_contribution": round(float(tol.get("contribution") or 0.0), 4),
            "sigma_mm": tol.get("sigma_mm"),
        })
    return {
        "schema": "clawstack.cetol_dual_contribution.v1",
        "lesson": "dimension_contribution uses |a*x_nominal|; tolerance_contribution uses (a*sigma)^2/sigmaY^2",
        "rows": rows,
    }


def msm_what_if(
    dims: list[tse.StackDimension],
    overrides: dict[str, float],
    *,
    lsl: float = -0.05,
    usl: float = 0.05,
) -> dict[str, Any]:
    """Recompute MSM Cpk/contribution without Monte Carlo or CAD rebuild."""
    new_dims: list[tse.StackDimension] = []
    for d in dims:
        tol = overrides[d.name] if d.name in overrides else d.tolerance
        new_dims.append(tse.StackDimension(
            d.name, d.mean, float(tol), d.coef, d.distribution, d.source,
        ))
    return tse.msm_stack(new_dims, lsl=lsl, usl=usl)


def openradioss_contributor(
    manifest: dict[str, Any],
    *,
    manifest_path: Path | None = None,
) -> dict[str, Any]:
    """Optional springback contributor. Fail-closed if missing -- never fake."""
    orh = (manifest.get("physics_handoff") or {}).get("openradioss") or {}
    if not isinstance(orh, dict):
        orh = {}
    for key in ("springback_mm", "kpi_springback_mm", "springback_angle_deg"):
        if orh.get(key) is not None:
            return {
                "present": True,
                "status": "USED",
                "field": key,
                "value": orh.get(key),
                "source": "physics_handoff.openradioss",
            }
    if manifest_path is not None:
        for name in ("springback.json", "openradioss_kpis.json", "or_kpis.json"):
            p = manifest_path.parent / name
            if not p.is_file():
                continue
            try:
                data = json.loads(p.read_text(encoding="utf-8"))
            except Exception:
                continue
            if not isinstance(data, dict):
                continue
            for key in ("springback_mm", "kpi_springback_mm", "springback_angle_deg"):
                if data.get(key) is not None:
                    return {
                        "present": True,
                        "status": "USED",
                        "field": key,
                        "value": data.get(key),
                        "source": name,
                    }
    return {
        "present": False,
        "status": "INSUFFICIENT",
        "reason": "no OpenRadioss springback artifact",
        "truth_gate": "fail_closed",
    }


def station_contributors(manifest: dict[str, Any]) -> list[dict[str, Any]]:
    """Progressive-die BL / PI / BE contributors when manifest supports them."""
    import tolerance_l10_assembly as tla

    rows: list[dict[str, Any]] = []
    for d in tla.progressive_die_station_dims(manifest):
        rows.append({
            "name": d.name,
            "station": STATION_MAP.get(d.name, "ASSY"),
            "tolerance_mm": d.tolerance,
            "coef": d.coef,
            "distribution": d.distribution,
            "source": d.source,
        })
    feats = manifest.get("features") or {}
    holes = [h for h in (feats.get("holes") or []) if isinstance(h, dict)]
    if holes:
        pos = max(_safe_float(holes[0].get("position_tol_mm"), 0.05), 0.001)
        rows.append({
            "name": "station_pierce_hole_position",
            "station": "PI",
            "tolerance_mm": pos,
            "coef": 1.0,
            "distribution": "normal",
            "source": "assembly_l10",
        })
    return rows


def gdt_labels(manifest: dict[str, Any]) -> list[dict[str, Any]]:
    feats = manifest.get("features") or {}
    labels: list[dict[str, Any]] = []
    asme_solver = False
    for i, hole in enumerate((feats.get("holes") or []) if isinstance(feats, dict) else []):
        if not isinstance(hole, dict):
            continue
        mmc = hole.get("mmc") or hole.get("material_condition")
        labels.append({
            "feature": str(hole.get("name") or f"hole_{i + 1}"),
            "type": "position",
            "tolerance_mm": _safe_float(hole.get("position_tol_mm") or hole.get("tolerance_mm"), 0.05),
            "diameter_mm": _safe_float(hole.get("diameter_mm")),
            "datum_ref": hole.get("datum_ref") or hole.get("drf") or None,
            "material_condition": mmc if mmc in ("MMC", "LMC", "RFS") else None,
            "fcf": _fcf_text("position", hole),
        })
    for i, datum in enumerate((feats.get("datums") or []) if isinstance(feats, dict) else []):
        if not isinstance(datum, dict):
            continue
        labels.append({
            "feature": str(datum.get("name") or f"datum_{i + 1}"),
            "type": "flatness",
            "tolerance_mm": _safe_float(datum.get("flatness_tol_mm") or datum.get("tolerance_mm"), 0.02),
            "datum_id": datum.get("id") or datum.get("letter"),
            "material_condition": None,
            "fcf": _fcf_text("flatness", datum),
        })
    for ann in (feats.get("gdt_annotations") or []) if isinstance(feats, dict) else []:
        if isinstance(ann, dict):
            labels.append({
                "feature": str(ann.get("feature") or ann.get("name") or "pmi"),
                "type": str(ann.get("gdt_type") or ann.get("type") or "unknown"),
                "tolerance_mm": _safe_float(ann.get("tolerance_mm"), 0.0),
                "material_condition": ann.get("material_condition"),
                "fcf": str(ann.get("fcf") or _fcf_text(str(ann.get("type") or "unknown"), ann)),
                "source": "pmi",
            })
    return labels


def _fcf_text(kind: str, rec: dict[str, Any]) -> str:
    tol = rec.get("position_tol_mm") or rec.get("flatness_tol_mm") or rec.get("tolerance_mm") or 0.05
    diam = rec.get("diameter_symbol") or (chr(8960) if kind == "position" else "")
    mc = rec.get("mmc") or rec.get("material_condition") or ""
    mc_s = f"|{mc}" if mc in ("MMC", "LMC", "RFS") else ""
    drf = rec.get("datum_ref") or rec.get("drf") or rec.get("letter") or ""
    drf_s = f"|{drf}" if drf else ""
    if kind == "position":
        return f"[POS|{diam}{tol}{mc_s}{drf_s}]"
    if kind == "flatness":
        return f"[FLT|{tol}]"
    return f"[{kind[:3].upper()}|{tol}]"


def build_features(manifest: dict[str, Any], slug: str, lx: float, ly: float, lz: float) -> list[dict[str, Any]]:
    feats = manifest.get("features") or {}
    out = [
        {"id": f"{slug}_plane_xy", "kind": "plane", "label": "Datum plane XY", "origin": [0, 0, 0], "normal": [0, 0, 1]},
        {"id": f"{slug}_plane_xz", "kind": "plane", "label": "Side plane XZ", "origin": [0, 0, 0], "normal": [0, 1, 0]},
        {"id": f"{slug}_bbox", "kind": "solid", "label": f"Part bbox {lx:.1f}x{ly:.1f}x{lz:.1f} mm", "size_mm": [lx, ly, lz]},
    ]
    for i, hole in enumerate((feats.get("holes") or []) if isinstance(feats, dict) else []):
        if not isinstance(hole, dict):
            continue
        hx, hy, hz = _hole_xyz(hole, i, lx, ly, lz, max(1, len(feats.get("holes") or [])))
        out.append({
            "id": f"{slug}_{hole.get('name') or f'hole_{i+1}'}",
            "kind": "cylinder",
            "label": str(hole.get("name") or f"hole_{i+1}"),
            "diameter_mm": _safe_float(hole.get("diameter_mm")),
            "pin_diameter_mm": _safe_float(hole.get("pin_diameter_mm")),
            "origin": [hx, hy, hz],
            "axis": [0, 0, 1],
        })
    for i, datum in enumerate((feats.get("datums") or []) if isinstance(feats, dict) else []):
        if not isinstance(datum, dict):
            continue
        out.append({
            "id": f"{slug}_datum_{datum.get('letter') or i+1}",
            "kind": "datum",
            "label": str(datum.get("name") or f"datum {datum.get('letter') or i+1}"),
            "letter": datum.get("letter"),
        })
    return out


_LOCK_T_MM = 0.002
_LOCK_R_DEG = 0.002


def _frame_matches_joint_end(frame_name: str, token: str) -> bool:
    tok = re.sub(r"[^A-Za-z0-9]+", "_", str(token or "")).strip("_")
    if len(tok) < 2:
        return False
    fn = str(frame_name or "")
    if tok == fn:
        return True
    fn_l = fn.lower()
    tok_l = tok.lower()
    if fn_l.endswith("_" + tok_l) or fn_l == tok_l:
        return True
    last = tok_l.split("_")[-1]
    if len(last) >= 2 and (fn_l.endswith("_" + last) or fn_l == last):
        return True
    return False


def pin_hole_clearance_mm(hole_diameter_mm: float, pin_diameter_mm: float = 0.0) -> float:
    """Radial clearance from hole-pin diameters, else 2% of hole dia."""
    hd = _safe_float(hole_diameter_mm)
    pd = _safe_float(pin_diameter_mm)
    if hd > 0 and pd > 0 and hd > pd:
        return max((hd - pd) * 0.5, 0.01)
    return max(hd * 0.02, 0.02)


def _default_constrained_dof(kind: str) -> list[str]:
    k = str(kind or "").lower()
    if k == "pin_hole_float":
        return ["Tx", "Ty"]
    if k == "fixed":
        return ["Tx", "Ty", "Tz", "Rx", "Ry", "Rz"]
    if k == "secondary_planar":
        return ["Rz"]
    if k == "revolute":
        return ["Tx", "Ty", "Tz", "Rx", "Ry"]
    return ["Tz", "Rx", "Ry"]


def _set_frame_dof(frame: dict[str, Any], dof: str, *, lock: bool, float_mm: float = 0.0) -> None:
    t_tol = list(frame.get("t_tol") or (0.0, 0.0, 0.0))
    r_tol = list(frame.get("r_tol") or (0.0, 0.0, 0.0))
    while len(t_tol) < 3:
        t_tol.append(0.0)
    while len(r_tol) < 3:
        r_tol.append(0.0)
    d = str(dof or "")
    if lock:
        if d == "Tx":
            t_tol[0] = min(float(t_tol[0]), _LOCK_T_MM)
        elif d == "Ty":
            t_tol[1] = min(float(t_tol[1]), _LOCK_T_MM)
        elif d == "Tz":
            t_tol[2] = min(float(t_tol[2]), _LOCK_T_MM)
        elif d == "Rx":
            r_tol[0] = min(float(r_tol[0]), _LOCK_R_DEG)
        elif d == "Ry":
            r_tol[1] = min(float(r_tol[1]), _LOCK_R_DEG)
        elif d == "Rz":
            r_tol[2] = min(float(r_tol[2]), _LOCK_R_DEG)
    else:
        if d == "Tx":
            t_tol[0] = max(float(t_tol[0]), float_mm)
        elif d == "Ty":
            t_tol[1] = max(float(t_tol[1]), float_mm)
    frame["t_tol"] = (float(t_tol[0]), float(t_tol[1]), float(t_tol[2]))
    frame["r_tol"] = (float(r_tol[0]), float(r_tol[1]), float(r_tol[2]))
    if lock:
        ld = list(frame.get("locked_dofs") or [])
        if d not in ld:
            ld.append(d)
        frame["locked_dofs"] = ld


def apply_joint_constraints_to_frames(
    frames: list[dict[str, Any]],
    joints: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Apply listed joints to kinematic t_tol/r_tol (not commercial CETOL mates).

    planar/fixed lock residual 0.002 mm / 0.002 deg. pin_hole_float keeps
    Tx/Ty at least clearance_mm on the joint `to` frame.
    """
    out = [dict(f) for f in frames]
    for j in joints:
        if not isinstance(j, dict):
            continue
        kind = str(j.get("kind") or "")
        dofs = [str(x) for x in (j.get("constrained_dof") or _default_constrained_dof(kind))]
        target = str(j.get("to") or "")
        lock = kind != "pin_hole_float"
        clearance = max(_safe_float(j.get("clearance_mm"), 0.05), 0.01)
        for f in out:
            if not _frame_matches_joint_end(str(f.get("name") or ""), target):
                continue
            for d in dofs:
                _set_frame_dof(f, d, lock=lock, float_mm=clearance)
            f["joint_driven"] = True
    return out


def locked_param_names(frames: list[dict[str, Any]]) -> list[str]:
    names: list[str] = []
    seen: set[str] = set()
    for f in frames:
        fname = str(f.get("name") or "")
        for d in f.get("locked_dofs") or []:
            n = fname + "_" + str(d)
            if n not in seen:
                seen.add(n)
                names.append(n)
    return names


def _joint_equality_rows(loop: tse.VectorLoop3D, joints: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Closed-loop h(x,u)=0 rows from mates. Float joints stay inequalities."""
    rows: list[dict[str, Any]] = []
    for j in joints:
        if not isinstance(j, dict) or j.get("float"):
            continue
        fi = loop.frame_index(str(j.get("from") or ""))
        ti = loop.frame_index(str(j.get("to") or ""))
        if fi is None or ti is None:
            continue
        for dof in j.get("constrained_dof") or []:
            d = str(dof)
            h0 = loop.relative_dof(fi, ti, d, {})
            rows.append({
                "joint_id": j.get("id"),
                "from_idx": fi,
                "to_idx": ti,
                "dof": d,
                "h0": h0,
            })
    return rows


def _h_joint(
    loop: tse.VectorLoop3D,
    rows: list[dict[str, Any]],
    deltas: dict[int, tuple[list[float], list[float]]],
) -> np.ndarray:
    return np.array([
        loop.relative_dof(int(r["from_idx"]), int(r["to_idx"]), str(r["dof"]), deltas) - float(r["h0"])
        for r in rows
    ], dtype=float)


def _jac_for_names(
    loop: tse.VectorLoop3D,
    rows: list[dict[str, Any]],
    specs: list[dict[str, Any]],
    names: list[str],
    eps: float = 1e-5,
) -> tuple[list[str], np.ndarray]:
    byname = {str(p["name"]): p for p in specs}
    used: list[str] = []
    cols: list[np.ndarray] = []
    for n in names:
        p = byname.get(n)
        if not p:
            continue
        hp = _h_joint(loop, rows, loop._param_delta(p, 1.0, eps))
        hm = _h_joint(loop, rows, loop._param_delta(p, -1.0, eps))
        cols.append((hp - hm) / (2.0 * eps))
        used.append(n)
    if not cols:
        return used, np.zeros((len(rows), 0), dtype=float)
    return used, np.column_stack(cols)


def _values_to_deltas(
    specs: list[dict[str, Any]],
    values: dict[str, float],
) -> dict[int, tuple[list[float], list[float]]]:
    out: dict[int, tuple[list[float], list[float]]] = {}
    for p in specs:
        val = float(values.get(str(p["name"])) or 0.0)
        if abs(val) < 1e-18:
            continue
        idx = int(p["idx"])
        dt, dr = out.get(idx, ([0.0, 0.0, 0.0], [0.0, 0.0, 0.0]))
        dt = list(dt)
        dr = list(dr)
        if p.get("kind") == "t":
            dt[int(p["axis"])] += val
        else:
            dr[int(p["axis"])] += math.degrees(val)
        out[idx] = (dt, dr)
    return out


def closed_loop_nonlinear_mc(
    loop: tse.VectorLoop3D,
    rows: list[dict[str, Any]],
    u_names: list[str],
    measures: dict[str, Any],
    *,
    n: int = 800,
    seed: int = 11,
) -> dict[str, Any]:
    """Gao-style modified MC: nonlinear h, B frozen at nominal. Independent of MSM."""
    specs = loop.param_specs()
    u_used, b_mat = _jac_for_names(loop, rows, specs, u_names)
    if b_mat.size:
        scales = np.maximum(np.linalg.norm(b_mat, axis=1), 1e-18)
        b_mat = b_mat / scales.reshape(-1, 1)
    else:
        scales = np.array([])
    if b_mat.size == 0 or int(np.linalg.matrix_rank(b_mat, tol=1e-8)) < 1:
        return {"applied": False, "reason": "singular_B"}
    binv = np.linalg.pinv(b_mat, rcond=1e-8)
    x_specs = [p for p in specs if str(p["name"]) not in set(u_used)]
    rng = np.random.default_rng(seed)
    mids = [str(k) for k, v in measures.items() if isinstance(v, dict)]
    acc: dict[str, list[float]] = {mid: [] for mid in mids}
    for _ in range(int(n)):
        x_val: dict[str, float] = {
            str(p["name"]): float(rng.normal(0.0, float(p["sigma"])))
            for p in x_specs
        }
        u_val: dict[str, float] = {un: 0.0 for un in u_used}
        for _k in range(2):
            deltas = _values_to_deltas(specs, {**x_val, **u_val})
            h = _h_joint(loop, rows, deltas)
            if scales.size:
                h = h / scales
            du = -binv @ h
            for i, un in enumerate(u_used):
                u_val[un] = float(u_val[un] + du[i])
        deltas = _values_to_deltas(specs, {**x_val, **u_val})
        for mid in mids:
            res = measures[mid]
            kind = str(res.get("kind") or "linear")
            direction = tuple(res.get("direction") or (0.0, 0.0, 1.0))
            acc[mid].append(loop._gap_with_deltas(
                (float(direction[0]), float(direction[1]), float(direction[2])),
                deltas,
                quantity="angular" if kind == "angular" else "linear",
                from_idx=loop.frame_index(res.get("from_frame")),
                to_idx=loop.frame_index(res.get("to_frame")),
            ))
    out_sigma: dict[str, float] = {}
    for mid, ys in acc.items():
        arr = np.array(ys, dtype=float)
        out_sigma[mid] = float(np.std(arr, ddof=1)) if arr.size > 2 else 0.0
    return {
        "applied": True,
        "method": "modified_mc_frozen_B",
        "n_samples": int(n),
        "sigma": out_sigma,
        "note": "Nonlinear closed-loop MC (Gao modified). Not Sigmetrix CETOL MC.",
    }


def apply_dlm_closed_loop(
    loop: tse.VectorLoop3D,
    loop_multi: dict[str, Any],
    frames: list[dict[str, Any]],
    joints: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Gao/Chase DLM with joint-local h(x,u). Also reduces angular CTQs.

    Not commercial CETOL closed-loop (no CAD mate solver).
    """
    joints = [j for j in (joints or []) if isinstance(j, dict)]
    u_names = locked_param_names(frames)
    measures = loop_multi.get("measures") or {}
    info: dict[str, Any] = {
        "applied": False,
        "method": "joint_local_pinv_BA",
        "n_u": len(u_names),
        "note": "Joint-local DLM analog (Gao/Chase). Not commercial CETOL closed-loop.",
    }
    rows = _joint_equality_rows(loop, joints)
    info["n_h"] = len(rows)
    if len(rows) < 1 or len(u_names) < 1:
        info["reason"] = "no_locked_dofs" if not u_names else "no_joint_rows"
        loop_multi["closed_loop"] = info
        return loop_multi
    specs = loop.param_specs()
    u_list, b_mat = _jac_for_names(loop, rows, specs, u_names)
    scales = np.maximum(np.linalg.norm(b_mat, axis=1), 1e-18) if b_mat.size else np.array([])
    if b_mat.size:
        b_mat = b_mat / scales.reshape(-1, 1)
    try:
        rank = int(np.linalg.matrix_rank(b_mat, tol=1e-8)) if b_mat.size else 0
        cond = float(np.linalg.cond(b_mat)) if rank >= 1 else float("inf")
    except Exception:
        rank, cond = 0, float("inf")
    info["rank"] = rank
    info["cond_B"] = cond
    if rank < 1:
        info["reason"] = "singular_B"
        loop_multi["closed_loop"] = info
        return loop_multi
    binv = np.linalg.pinv(b_mat, rcond=1e-8)
    x_all = [str(p["name"]) for p in specs if str(p["name"]) not in set(u_list)]
    info["applied"] = True
    info["u_names"] = u_list
    info["n_x"] = len(x_all)
    for _mid, res in measures.items():
        if not isinstance(res, dict):
            continue
        sens = res.get("sensitivity") or {}
        all_names = [str(n) for n in sens.keys()]
        x_list = [n for n in all_names if n not in u_list]
        if not x_list:
            res["closed_loop"] = {"applied": False, "reason": "no_manufactured_x"}
            continue
        x_used, a_mat = _jac_for_names(loop, rows, specs, x_list)
        if a_mat.size and scales.size:
            a_mat = a_mat / scales.reshape(-1, 1)
        a_u = np.array([float((sens.get(n) or {}).get("sensitivity") or 0.0) for n in u_list], dtype=float)
        a_x = np.array([float((sens.get(n) or {}).get("sensitivity") or 0.0) for n in x_used], dtype=float)
        a_red_map: dict[str, float] = {n: float((sens.get(n) or {}).get("sensitivity") or 0.0) for n in x_list}
        if a_mat.size and len(x_used) == a_mat.shape[1]:
            reduced = a_x - a_u @ (binv @ a_mat)
            for i, name in enumerate(x_used):
                a_red_map[name] = float(reduced[i])
        new_sens: dict[str, dict[str, Any]] = {}
        total_var = 0.0
        wc = 0.0
        for name in x_list:
            old = sens.get(name) or {}
            old_a = float(old.get("sensitivity") or 0.0)
            sig_mm = float(old.get("sigma_mm") or 0.0)
            sig_p = (sig_mm / abs(old_a)) if abs(old_a) > 1e-18 else 0.0
            new_a = float(a_red_map.get(name) or 0.0)
            var = (new_a * sig_p) ** 2
            total_var += var
            wc += abs(new_a) * (sig_p * 6.0)
            new_sens[name] = {
                "sensitivity": new_a,
                "sigma_mm": round(math.sqrt(var), 6),
                "contribution": 0.0,
            }
        for name in u_list:
            new_sens[name] = {
                "sensitivity": 0.0,
                "sigma_mm": 0.0,
                "contribution": 0.0,
                "dlm_assembly_variable": True,
            }
        denom = total_var if total_var > 0 else 1.0
        for name, row in new_sens.items():
            if name in u_list:
                continue
            row["contribution"] = round((float(row["sigma_mm"]) ** 2) / denom, 4)
        max_c = max(
            (float(v.get("contribution") or 0.0) for n, v in new_sens.items() if n not in u_list),
            default=0.0,
        )
        res["sensitivity"] = new_sens
        res["rss_3sigma_mm"] = 3.0 * math.sqrt(total_var)
        res["worst_case_stack_mm"] = wc
        res["coupling"] = "uncoupled" if (total_var <= 1e-18 or max_c <= 1e-6) else "coupled"
        res["closed_loop"] = {"applied": True, "n_u": len(u_list), "n_x": len(x_list), "method": "joint_local"}
        if isinstance(res.get("sota"), dict):
            sota = dict(res["sota"])
            sota["sigma"] = math.sqrt(max(0.0, total_var + float(sota.get("var_extra") or 0.0)))
            sota["dlm_reduced"] = True
            res["sota"] = sota
    contrib_names: list[str] = []
    seen: set[str] = set()
    for res in measures.values():
        if not isinstance(res, dict):
            continue
        for n in (res.get("sensitivity") or {}):
            if n not in seen:
                seen.add(n)
                contrib_names.append(n)
    cross: dict[str, dict[str, float]] = {}
    for name in contrib_names:
        row: dict[str, float] = {}
        for mid, res in measures.items():
            if not isinstance(res, dict):
                continue
            srow = (res.get("sensitivity") or {}).get(name) or {}
            row[str(mid)] = float(srow.get("contribution") or 0.0)
        cross[name] = row
    loop_multi["cross_table"] = cross
    coupling: dict[str, Any] = {}
    for mid, res in measures.items():
        if not isinstance(res, dict):
            continue
        status = str(res.get("coupling") or "")
        sens = res.get("sensitivity") or {}
        mx = max((float((v or {}).get("contribution") or 0.0) for v in sens.values()), default=0.0)
        cl = res.get("closed_loop") or {}
        coupling[str(mid)] = {
            "status": status or ("uncoupled" if mx <= 1e-6 else "coupled"),
            "max_contribution": mx,
            "note": "joint-local DLM" if cl.get("applied") else str(cl.get("reason") or ""),
        }
    loop_multi["measure_coupling"] = coupling
    loop_multi["closed_loop"] = info
    if info.get("applied"):
        loop_multi["closed_loop_mc"] = closed_loop_nonlinear_mc(loop, rows, u_list, measures)
    return loop_multi


def kinematic_loop_golden() -> dict[str, Any]:
    """Analytic 3D vector-loop checks. Not a commercial CETOL 3D pass."""
    cases: list[dict[str, Any]] = []
    loop_z = tse.VectorLoop3D()
    loop_z.add_frame(
        "Zonly", (0.0, 0.0, 5.0), (0.0, 0.0, 0.0),
        (0.0, 0.0, 0.1), (0.0, 0.0, 0.0), source="analytic",
    )
    a_z = float(((loop_z.solve((0.0, 0.0, 1.0), second_order=False).get("sensitivity") or {}).get("Zonly_Tz") or {}).get("sensitivity") or 0.0)
    err_z = abs(a_z - 1.0) * 100.0
    cases.append({"id": "tz_unit", "got": a_z, "ref": 1.0, "err_pct": round(err_z, 4), "ok": err_z <= 1.0})
    loop_r = tse.VectorLoop3D()
    loop_r.add_frame(
        "Hinge", (0.0, 0.0, 0.0), (0.0, 0.0, 0.0),
        (0.0, 0.0, 0.0), (1.0, 0.0, 0.0), source="analytic",
    )
    loop_r.add_frame(
        "Arm", (0.0, 10.0, 0.0), (0.0, 0.0, 0.0),
        (0.0, 0.0, 0.0), (0.0, 0.0, 0.0), source="analytic",
    )
    a_r = float(((loop_r.solve((0.0, 0.0, 1.0), second_order=False).get("sensitivity") or {}).get("Hinge_Rx") or {}).get("sensitivity") or 0.0)
    err_r = abs(a_r - 10.0) / 10.0 * 100.0
    cases.append({"id": "rx_lever_10mm", "got": a_r, "ref": 10.0, "err_pct": round(err_r, 4), "ok": err_r <= 1.0})
    max_err = max(float(c["err_pct"]) for c in cases)
    all_ok = all(bool(c["ok"]) for c in cases)
    return {
        "schema": "clawstack.cetol_loop_kinematic_golden.v1",
        "verdict": "PASS" if all_ok else "FAIL",
        "cetol_3d_equivalent": False,
        "note": "Open-chain analytic lever/Tz only. Not Sigmetrix CETOL 3D.",
        "max_err_pct": round(max_err, 4),
        "cases": cases,
    }


def analyze_constraint_state(
    frames: list[dict[str, Any]],
    joints: list[dict[str, Any]],
) -> dict[str, Any]:
    """3-2-1 lock map analog. Not a CAD constraint solver / commercial TIM."""
    lock_map: dict[tuple[str, str], list[str]] = {}
    float_n = 0
    for j in joints:
        if not isinstance(j, dict):
            continue
        kind = str(j.get("kind") or "")
        dofs = [str(x) for x in (j.get("constrained_dof") or _default_constrained_dof(kind))]
        jid = str(j.get("id") or "")
        target = str(j.get("to") or "")
        is_float = kind == "pin_hole_float"
        matched = [
            str(f.get("name") or "")
            for f in frames
            if _frame_matches_joint_end(str(f.get("name") or ""), target)
        ]
        for fname in matched:
            for d in dofs:
                if is_float:
                    float_n += 1
                    continue
                lock_map.setdefault((fname, d), []).append(jid)
    conflicts = [
        {"frame": k[0], "dof": k[1], "joints": v}
        for k, v in lock_map.items() if len(v) > 1
    ]
    per_body: dict[str, list[str]] = {}
    for fname, dof in lock_map:
        bucket = per_body.setdefault(fname, [])
        if dof not in bucket:
            bucket.append(dof)
    bodies: list[dict[str, Any]] = []
    status = "PROPER"
    if conflicts:
        status = "OVERCONSTRAINED"
    if not lock_map:
        status = "UNDERCONSTRAINED"
    for fname, dofs in per_body.items():
        n = len(dofs)
        is_part = fname.lower().endswith("_strip") or "_strip" in fname.lower()
        rec: dict[str, Any] = {
            "frame": fname, "locked_dof": sorted(dofs), "n_locked": n,
        }
        if n > 6 or any(c["frame"] == fname for c in conflicts):
            rec["status"] = "OVERCONSTRAINED"
            status = "OVERCONSTRAINED"
        elif is_part and n < 3:
            rec["status"] = "UNDERCONSTRAINED"
            if status != "OVERCONSTRAINED":
                status = "UNDERCONSTRAINED"
        elif is_part and n < 6:
            rec["status"] = "PARTIAL"
            if status not in ("OVERCONSTRAINED", "UNDERCONSTRAINED"):
                status = "PARTIAL"
        else:
            rec["status"] = "PROPER" if n == 6 else "LOCKED"
        bodies.append(rec)
    return {
        "schema": "clawstack.cetol_constraint_state.v1",
        "status": status,
        "note": "Lock-count analog of 3-2-1. Not CAD TIM / commercial CETOL over-constraint.",
        "duplicate_locks": conflicts,
        "bodies": bodies,
        "n_lock_slots": len(lock_map),
        "n_float_slots": float_n,
    }


def build_joints(manifest: dict[str, Any], slug: str, features: list[dict[str, Any]]) -> list[dict[str, Any]]:
    holes = [f for f in features if f.get("kind") == "cylinder"]
    joints: list[dict[str, Any]] = []
    seq = 1
    cad = [dict(j) for j in (manifest.get("freecad_assembly_joints") or []) if isinstance(j, dict)]
    if cad:
        for i, j in enumerate(cad):
            rec = dict(j)
            rec.setdefault("id", rec.get("id") or f"{slug}_cad_{i}")
            rec.setdefault("sequence", seq)
            rec.setdefault("constrained_dof", _default_constrained_dof(str(rec.get("kind") or "")))
            rec.setdefault("float", str(rec.get("kind") or "") == "pin_hole_float")
            if str(rec.get("kind") or "") == "pin_hole_float" and _safe_float(rec.get("clearance_mm")) <= 0:
                hd = max((_safe_float(h.get("diameter_mm")) for h in holes), default=0.0)
                pd = max((_safe_float(h.get("pin_diameter_mm")) for h in holes), default=0.0)
                rec["clearance_mm"] = pin_hole_clearance_mm(hd, pd)
            joints.append(rec)
            seq += 1
    have_planar = any(
        str(j.get("kind") or "") in ("planar_contact", "fixed") and str(j.get("to") or "").strip()
        for j in joints
    )
    have_pin = any(
        str(j.get("kind") or "") == "pin_hole_float" and str(j.get("to") or "").strip()
        for j in joints
    )
    have_rz = any(
        str(j.get("kind") or "") == "secondary_planar" and str(j.get("to") or "").strip()
        for j in joints
    )
    if not have_planar:
        joints.append({
            "id": f"{slug}_j_die_strip",
            "kind": "planar_contact",
            "from": f"{slug}_DieBase",
            "to": f"{slug}_Strip",
            "sequence": seq,
            "float": False,
            "constrained_dof": ["Tz", "Rx", "Ry"],
        })
        seq += 1
    if not have_pin:
        for i, h in enumerate(holes[:4]):
            joints.append({
                "id": f"{slug}_j_{h['id']}",
                "kind": "pin_hole_float",
                "from": f"{slug}_Strip",
                "to": h["id"],
                "sequence": seq,
                "float": True,
                "constrained_dof": ["Tx", "Ty"],
                "clearance_mm": pin_hole_clearance_mm(
                    _safe_float(h.get("diameter_mm"), 4.0),
                    _safe_float(h.get("pin_diameter_mm")),
                ),
            })
            seq += 1
    if len(holes) >= 2 and not have_rz:
        joints.append({
            "id": f"{slug}_j_secondary_contact",
            "kind": "secondary_planar",
            "from": holes[0]["id"],
            "to": holes[1]["id"],
            "sequence": seq,
            "float": False,
            "constrained_dof": ["Rz"],
            "note": "Second pin removes remaining in-plane rotation after first float joint",
        })
    return joints


def advisor(
    *,
    manifest: dict[str, Any],
    frames: list[dict[str, Any]],
    joints: list[dict[str, Any]],
    measures: list[dict[str, Any]],
    dimensions: list[dict[str, Any]],
    gdt: list[dict[str, Any]],
    or_contrib: dict[str, Any],
    constraint_state: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    flags: list[dict[str, Any]] = []
    feats = manifest.get("features") or {}
    holes = feats.get("holes") or []
    datums = feats.get("datums") or []
    bbox = manifest.get("bbox_mm") or {}
    if _safe_float(bbox.get("Lx")) <= 0 or _safe_float(bbox.get("Ly")) <= 0:
        flags.append({"code": "geometry_insufficient", "severity": "warn",
                      "text": "bbox Lx/Ly missing or zero; frames used fallback sizes"})
    if holes and not datums:
        flags.append({"code": "missing_datums", "severity": "warn",
                      "text": "holes present but no datum features -- DRF incomplete"})
    pin_joints = [j for j in joints if j.get("kind") == "pin_hole_float"]
    if holes and not pin_joints:
        flags.append({"code": "underconstrained_joint", "severity": "warn",
                      "text": "hole features have no pin/float joint"})
    seen_m: set[str] = set()
    for m in measures:
        mid = str(m.get("id") or "")
        if mid in seen_m:
            flags.append({"code": "duplicate_measure", "severity": "warn", "text": f"duplicate measure {mid}"})
        seen_m.add(mid)
    used_names = {str(d.get("name") or "") for d in dimensions}
    for d in dimensions:
        src = str(d.get("source") or "")
        if src.startswith("synthetic") and d.get("name") not in used_names:
            flags.append({"code": "unused_dimension", "severity": "info",
                          "text": f"dimension {d.get('name')} unused"})
            break
    pmi_n = 0
    enr = manifest.get("pmi_enrichment") or {}
    if isinstance(enr, dict):
        pmi_n = int(enr.get("pmi_dim_count") or 0)
    if pmi_n == 0 and not gdt:
        flags.append({"code": "insufficient_gdt", "severity": "info",
                      "text": "INSUFFICIENT -- no PMI/GD&T; ASME solver not claimed"})
    mmc_present = any(x.get("material_condition") in ("MMC", "LMC") for x in gdt)
    mmc_applied = any(
        isinstance(f.get("mmc_bonus"), dict) and f["mmc_bonus"].get("status") == "APPLIED"
        for f in frames
    )
    if gdt and not mmc_present and not mmc_applied:
        flags.append({"code": "mmc_lmc_absent", "severity": "info",
                      "text": "INSUFFICIENT -- MMC/LMC not in data; bonus tolerance not solved"})
    if not or_contrib.get("present"):
        flags.append({"code": "openradioss_absent", "severity": "info",
                      "text": "OpenRadioss springback missing (fail-closed, not faked)"})
    frame_names = [str(f.get("name") or "") for f in frames]
    leaked = [n for n in frame_names if n in FORBIDDEN_GENERIC_FRAMES]
    if leaked:
        flags.append({"code": "hardcoded_unrelated_frames", "severity": "error",
                      "text": "generic frames " + ",".join(leaked) + " on this job -- reject"})
    cst = constraint_state or {}
    cst_status = str(cst.get("status") or "")
    if cst_status == "OVERCONSTRAINED":
        flags.append({"code": "overconstrained_joint", "severity": "warn",
                      "text": "same DOF locked by more than one joint (analog, not CAD TIM)"})
    elif cst_status == "UNDERCONSTRAINED":
        flags.append({"code": "underconstrained_dof", "severity": "warn",
                      "text": "too few locked DOFs on the moving part (analog 3-2-1)"})
    elif cst_status == "PARTIAL":
        flags.append({"code": "partial_constraint", "severity": "info",
                      "text": "part locked in Z/tilt but not a full 6-DOF 3-2-1 set"})
    if not flags:
        flags.append({"code": "advisor_ok", "severity": "ok", "text": "no structural flags"})
    return flags


def build_tim(
    *,
    variations: list[dict[str, Any]],
    gdt: list[dict[str, Any]],
    cross_table: dict[str, Any],
    measures: list[dict[str, Any]],
    frames: list[dict[str, Any]],
    advisor_flags: list[dict[str, Any]],
    measure_coupling: dict[str, Any] | None = None,
    constraint_state: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Web TIM analog: variations, loop DOFs, GD&T, unused, MMC. Not CAD TIM."""
    used_by: dict[str, list[str]] = {}
    for name, row in (cross_table or {}).items():
        if not isinstance(row, dict):
            continue
        mids = [str(mid) for mid, v in row.items() if abs(_safe_float(v)) > 1e-4]
        used_by[str(name)] = mids
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    for d in variations:
        n = str(d.get("name") or "")
        if not n:
            continue
        status = "DUPLICATE" if n in seen else ("USED" if used_by.get(n) else "UNUSED")
        seen.add(n)
        rows.append({
            "name": n,
            "kind": "variation_1d",
            "source": d.get("source"),
            "tolerance_mm": d.get("tolerance"),
            "status": status,
            "used_by_ctq": used_by.get(n) or [],
        })
    for name, mids in used_by.items():
        rows.append({
            "name": name,
            "kind": "loop_dof",
            "status": "USED" if mids else "UNUSED",
            "used_by_ctq": mids,
        })
    mmc_applied = 0
    for f in frames:
        rec = f.get("mmc_bonus") if isinstance(f.get("mmc_bonus"), dict) else None
        if not rec:
            continue
        if rec.get("status") == "APPLIED":
            mmc_applied += 1
        rows.append({
            "name": rec.get("feature") or f.get("name"),
            "kind": "mmc_bonus",
            "status": rec.get("status"),
            "bonus_mm": rec.get("bonus_mm"),
            "effective_position_tol_mm": rec.get("effective_position_tol_mm"),
            "reason": rec.get("reason") or rec.get("formula"),
            "used_by_ctq": used_by.get(str(f.get("name") or ""), []),
        })
    for g in gdt:
        mc = g.get("material_condition")
        rows.append({
            "name": g.get("feature"),
            "kind": "gdt_" + str(g.get("type") or "fcf"),
            "status": "DECLARED" if mc in ("MMC", "LMC") else "INSUFFICIENT",
            "material_condition": mc,
            "fcf": g.get("fcf"),
            "used_by_ctq": [],
        })
    coupling_rows = []
    for mid, info in (measure_coupling or {}).items():
        coupling_rows.append({
            "measure": mid,
            "status": (info or {}).get("status"),
            "max_contribution": (info or {}).get("max_contribution"),
            "note": (info or {}).get("note"),
        })
    unused_n = sum(1 for r in rows if r.get("status") == "UNUSED" and r.get("kind") == "variation_1d")
    return {
        "schema": "clawstack.cetol_tim.v1",
        "note": "Web TIM analog. Not Creo / SOLIDWORKS / Sigmetrix CAD TIM.",
        "rows": rows,
        "measure_coupling": coupling_rows,
        "unused_count": unused_n,
        "mmc_applied_count": mmc_applied,
        "constraint_state": constraint_state or {},
        "advisor_codes": [str(a.get("code") or "") for a in advisor_flags],
        "measure_ids": [str(m.get("id") or "") for m in measures],
    }


def build_cetol_model(
    manifest: dict[str, Any],
    *,
    job_id: str | None = None,
    l10_report: dict[str, Any] | None = None,
    manifest_path: Path | None = None,
    lsl: float = -0.05,
    usl: float = 0.05,
) -> dict[str, Any]:
    slug = part_slug(manifest, job_id)
    lx, ly, lz = bbox_xyz(manifest)
    frames = frames_from_manifest(manifest, job_id=job_id)
    measures = default_measures(manifest)
    features = build_features(manifest, slug, lx, ly, lz)
    joints = build_joints(manifest, slug, features)
    frames = apply_joint_constraints_to_frames(frames, joints)
    constraint_state = analyze_constraint_state(frames, joints)
    loop = loop_from_frames(frames)
    loop_multi = loop.solve_measures(measures)
    loop_multi = apply_dlm_closed_loop(loop, loop_multi, frames, joints=joints)
    gdt = gdt_labels(manifest)
    or_c = openradioss_contributor(manifest, manifest_path=manifest_path)
    stations = station_contributors(manifest)

    dims_raw: list[tse.StackDimension] = []
    if l10_report and l10_report.get("dimensions"):
        for d in l10_report["dimensions"]:
            dims_raw.append(tse.StackDimension(
                str(d.get("name") or "dim"),
                _safe_float(d.get("mean")),
                max(_safe_float(d.get("tolerance"), 0.05), 0.0),
                _safe_float(d.get("coef"), 1.0),
                str(d.get("distribution") or "normal"),
                str(d.get("source") or "measured"),
            ))
    else:
        import tolerance_l10_assembly as tla
        dims_raw = tla.build_l10_stack_dimensions(manifest)

    nominals = {f"{slug}_Pitch": lx, f"{slug}_GapZ": lz, f"{slug}_Strip": _safe_float(manifest.get("sheet_thickness_mm"), lz)}
    for d in dims_raw:
        if abs(d.mean) > 1e-9:
            nominals[d.name] = d.mean
    dual = dual_contribution(dims_raw, nominals=nominals)
    msm = tse.msm_stack(dims_raw, lsl=lsl, usl=usl)

    primary = loop_multi["measures"].get("gap_z") or next(iter(loop_multi["measures"].values()), {})
    top_sens = None
    gap_sens = (primary.get("sensitivity") or {})
    if gap_sens:
        top_sens = max(gap_sens.items(), key=lambda kv: float((kv[1] or {}).get("contribution") or 0.0))[0]

    product_def = {
        "source_dxf": manifest.get("source_dxf"),
        "step_path": manifest.get("step_path"),
        "has_combined_step": manifest.get("has_combined_step"),
        "pmi_enrichment": manifest.get("pmi_enrichment") or {},
        "maturity_hint": (l10_report or {}).get("maturity_level") or manifest.get("maturity_level"),
        "units": manifest.get("units") or "mm",
    }

    dim_dicts = [
        {
            "name": d.name, "mean": d.mean, "tolerance": d.tolerance,
            "coef": d.coef, "source": d.source, "distribution": d.distribution,
        }
        for d in dims_raw
    ]
    flags = advisor(
        manifest=manifest, frames=frames, joints=joints, measures=measures,
        dimensions=dim_dicts, gdt=gdt, or_contrib=or_c,
        constraint_state=constraint_state,
    )
    gap_sota = (primary.get("sota") or {}) if isinstance(primary, dict) else {}
    gld_1d = msm.get("gld") or {}
    dev_mu = float(gap_sota.get("mean_shift") or 0.0)
    dev_sig = float(gap_sota.get("sigma") or 0.0)
    loop_gld: dict[str, Any] = {}
    loop_cpk = None
    if dev_sig > 1e-12:
        loop_gld = tse.gld_yield_from_moments(
            dev_mu, dev_sig,
            float(gap_sota.get("skewness") or 0.0),
            float(gap_sota.get("excess_kurtosis") or 0.0),
            lsl, usl,
        )
        loop_cpk = min((usl - dev_mu) / (3.0 * dev_sig), (dev_mu - lsl) / (3.0 * dev_sig))
    cannot = cpp.build_cetol_cannot_bundle(
        manifest,
        or_contrib=or_c,
        lx_mm=lx,
        ly_mm=ly,
        lsl=lsl,
        usl=usl,
        rigid_sigma_mm=dev_sig,
    )
    flags.extend(cannot.get("advisor") or [])
    tails = tse.tail_model_bundle(
        dev_mu, dev_sig,
        float(gap_sota.get("skewness") or 0.0),
        float(gap_sota.get("excess_kurtosis") or 0.0),
        lsl, usl,
    ) if dev_sig > 1e-12 else {}
    joint_y = tse.joint_ctq_yield(loop_multi.get("measures") or {}, lsl=lsl, usl=usl)
    mc_loop = loop_multi.get("closed_loop_mc") or {}
    mc_sig = float((mc_loop.get("sigma") or {}).get("gap_z") or 0.0)
    sota_sig = float(gap_sota.get("sigma") or 0.0)
    mc_agree = None
    if mc_loop.get("applied") and sota_sig > 1e-12 and mc_sig > 0:
        mc_agree = abs(mc_sig - sota_sig) / sota_sig <= 0.15
    process_in_loop = any(str(f.get("source") or "") == "openradioss" for f in frames)
    capability = {
        "cad_addin": "skipped_by_user",
        "joint_local_dlm": bool((loop_multi.get("closed_loop") or {}).get("applied")),
        "relative_feature_measures": True,
        "nonlinear_closed_mc": bool(mc_loop.get("applied")),
        "mc_sota_agree_15pct": mc_agree,
        "multi_ctq_joint_yield": bool(joint_y.get("applied")),
        "three_tail_models": bool(tails),
        "geometric_form": any(isinstance(f.get("geometric_form"), dict) for f in frames),
        "openradioss_in_loop": process_in_loop,
        "progressive_die_stations": bool(stations),
        "process_physics_cetol_cannot": True,
        "commercial_claim": False,
        "note": (
            "Method coverage vs documented CETOL 6-sigma (Gao DLM, Glancy SOTA) "
            "plus process physics CETOL cannot implement. "
            "Not a validated head-to-head on Sigmetrix assemblies."
        ),
    }
    msm_sota = {
        "schema": "clawstack.cetol_msm_sota.v1",
        "truth_gate": "UNVALIDATED",
        "commercial_cetol_equivalent": False,
        "note": "1D MSM+GLD and loop SOTA truncated 4-moment MSM. Not Sigmetrix CETOL SOTA+GLD table.",
        "linear_msm": {
            "sigma": msm.get("sigma"),
            "Cpk": msm.get("Cpk"),
            "yield_rate": msm.get("yield_rate"),
            "yield_rate_gld": msm.get("yield_rate_gld"),
            "gld_status": gld_1d.get("status"),
        },
        "loop_sota": {
            "mean": gap_sota.get("mean"),
            "sigma": gap_sota.get("sigma"),
            "mean_shift": gap_sota.get("mean_shift"),
            "var_extra": gap_sota.get("var_extra"),
            "skewness": gap_sota.get("skewness"),
            "excess_kurtosis": gap_sota.get("excess_kurtosis"),
            "method": gap_sota.get("method"),
            "cross_derivatives": bool(gap_sota.get("cross_derivatives")),
            "cross_pairs": gap_sota.get("cross_pairs"),
            "cross_top_n": gap_sota.get("cross_top_n"),
            "full_cross": bool(gap_sota.get("full_cross")),
            "n_dof": gap_sota.get("n_dof"),
            "dlm_reduced": bool(gap_sota.get("dlm_reduced")),
            "Cpk": loop_cpk,
            "yield_rate_gld": loop_gld.get("yield_rate"),
            "gld": loop_gld,
            "tails": tails,
            "mc_sigma_gap_z": mc_sig,
            "mc_sota_agree_15pct": mc_agree,
        },
        "joint_ctq_yield": joint_y,
    }
    tim = build_tim(
        variations=dim_dicts,
        gdt=gdt,
        cross_table=loop_multi.get("cross_table") or {},
        measures=measures,
        frames=frames,
        advisor_flags=flags,
        measure_coupling=loop_multi.get("measure_coupling") or {},
        constraint_state=constraint_state,
    )
    return {
        "schema": "clawstack.cetol_model.v1",
        "truth_gate": {
            "commercial_cetol_equivalent": False,
            "status": "UNVALIDATED",
            "note": "CETOL-class Modeler/Analyzer on STEP/Three.js. Not Sigmetrix CETOL 6-sigma.",
        },
        "job_id": job_id or manifest.get("job_id"),
        "part_slug": slug,
        "bbox_mm": {"Lx": lx, "Ly": ly, "Lz": lz},
        "sheet_thickness_mm": _safe_float(manifest.get("sheet_thickness_mm")),
        "assembly": {
            "id": slug,
            "label": slug,
            "parts": [
                {"id": f"{slug}_DieBase", "label": "Die / datum base"},
                {"id": f"{slug}_Strip", "label": "Strip / part"},
            ],
        },
        "features": features,
        "joints": joints,
        "assembly_sequence": [
            {
                "seq": int(j.get("sequence") or i + 1),
                "joint_id": j.get("id"),
                "kind": j.get("kind"),
                "from": j.get("from"),
                "to": j.get("to"),
                "float": bool(j.get("float")),
                "note": j.get("note") or (
                    "planar mate first (datum)" if j.get("kind") == "planar_contact"
                    else "pin-hole float" if j.get("kind") == "pin_hole_float"
                    else "secondary constraint"
                ),
            }
            for i, j in enumerate(joints)
        ],
        "measures": measures,
        "variations": dim_dicts,
        "frames": frames,
        "vector_loop_3d": primary,
        "vector_loop_measures": loop_multi,
        "dual_contribution": dual,
        "cross_table": loop_multi.get("cross_table") or {},
        "msm": {k: msm.get(k) for k in (
            "Cp", "Cpk", "yield_rate", "yield_rate_gld", "sigma",
            "skewness", "excess_kurtosis", "sensitivity", "gld",
        )},
        "msm_sota": msm_sota,
        "closed_loop": loop_multi.get("closed_loop") or {},
        "closed_loop_mc": loop_multi.get("closed_loop_mc") or {},
        "joint_ctq_yield": joint_y,
        "capability_beyond_cetol": capability,
        "cetol_cannot": cannot,
        "tim": tim,
        "measure_coupling": loop_multi.get("measure_coupling") or {},
        "station_contributors": stations,
        "openradioss": or_c,
        "gdt": gdt,
        "product_definition": product_def,
        "advisor": flags,
        "constraint_state": constraint_state,
        "sensitivity_animation": {
            "driver": top_sens,
            "measure": "gap_z",
            "exaggeration_default": 50.0,
            "note": "Perturb highest-contribution kinematic DOF on the assembly, not connector mating.",
        },
        "forbidden_generic_frames": list(FORBIDDEN_GENERIC_FRAMES),
        "cad_asset": dict(manifest.get("cad_asset") or {}),
    }
