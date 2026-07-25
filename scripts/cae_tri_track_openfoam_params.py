# -*- coding: utf-8 -*-
"""Build tri-track OpenFOAM resin_fill_cad params from DXF2STEP handoff + allocation sweep."""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

ROOT = Path(__file__).resolve().parents[1]
WORKSPACE = ROOT / "data" / "workspace"
ARCHIVE = WORKSPACE / "thinkpad_dxf2step_history"
OVERRIDES_PATH = WORKSPACE / "lavie_te_allocation_overrides.json"
DEFAULT_STEP = ROOT / "data" / "cae_te_workspace" / "samples" / "moldflow" / "pp_plate" / "pp_plate_100x60x2.step"
DEFAULT_GATE = ROOT / "data" / "cae_te_workspace" / "samples" / "moldflow" / "gate_spec_center.json"

OK_ADJUDICATIONS = frozenset({"GEOMETRY_OK", "GEOMETRY_PARTIAL_OK"})

# Categories that model filling only, with no packing stage of their own.
FILL_ONLY_CATEGORIES = frozenset({"resin_fill_vof"})


def _rel(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT)).replace("\\", "/")
    except ValueError:
        return str(path).replace("\\", "/")


def pick_dxf2step_handoff() -> dict[str, Any] | None:
    if not ARCHIVE.is_dir():
        return None
    candidates: list[tuple[float, dict[str, Any]]] = []
    for job_dir in ARCHIVE.iterdir():
        if not job_dir.is_dir() or not job_dir.name.startswith("tp-dxf-"):
            continue
        step = job_dir / "combined.step"
        if not step.exists():
            continue
        manifest = job_dir / "part_manifest.json"
        audit_path = job_dir / "combined_geometry_audit.json"
        adjudication = ""
        if audit_path.exists():
            try:
                adjudication = str(
                    json.loads(audit_path.read_text(encoding="utf-8-sig")).get("formal_adjudication") or ""
                )
            except Exception:
                adjudication = ""
        if adjudication and adjudication not in OK_ADJUDICATIONS:
            continue
        mtime = step.stat().st_mtime
        entry = {
            "trial_id": job_dir.name,
            "step_rel": _rel(step),
            "manifest_rel": _rel(manifest) if manifest.exists() else None,
            "adjudication": adjudication or "manifest_only",
        }
        candidates.append((mtime, entry))
    if not candidates:
        return None
    candidates.sort(key=lambda x: -x[0])
    return candidates[0][1]


def _sweep_value(bounds: list[float] | tuple[float, float], cycle_n: int, slots: int = 12) -> float:
    lo, hi = float(bounds[0]), float(bounds[1])
    if slots <= 1:
        return lo
    idx = int(cycle_n) % slots
    return lo + (hi - lo) * (idx / (slots - 1))


GOLDEN_SPEC_PATH = ROOT / "data" / "cae_te_workspace" / "samples" / "moldflow" / "golden_plate_case.json"
CAE_LOG_PATH = ROOT / "data" / "cae_te_workspace" / "results" / "cae_te_log.json"
MF_TO_OF_HANDOFF = (
    WORKSPACE / "moldflow_bridge" / "mf_to_of_handoff_box_xplus_d2_20260720.json"
)
_LEARNED_KEYS = ("inlet_velocity", "pack_pressure_MPa", "polymer_nu", "pack_inlet_velocity")


def _load_overrides() -> dict[str, Any]:
    if not OVERRIDES_PATH.exists():
        return {}
    try:
        return json.loads(OVERRIDES_PATH.read_text(encoding="utf-8-sig"))
    except Exception:
        return {}


def _mf_handoff_cfg(overrides: dict[str, Any] | None = None) -> dict[str, Any]:
    ov = overrides if overrides is not None else _load_overrides()
    cfg = ov.get("mf_to_of_handoff") or {}
    return cfg if isinstance(cfg, dict) else {}


def _mf_handoff_enabled(overrides: dict[str, Any] | None = None) -> bool:
    """True when allocation overrides force MFALIGN box (not plate)."""
    return bool(_mf_handoff_cfg(overrides).get("enabled"))


def _apply_mf_handoff(params: dict[str, Any], overrides: dict[str, Any] | None = None) -> dict[str, Any]:
    """Apply Dynabook Moldflow Fill KPI handoff when requested or allocation-enabled.

    Opt-in: params.apply_mf_to_of_handoff in {1,true,yes,on} or mf_to_of_handoff_path set,
    or lavie_te_allocation_overrides.json mf_to_of_handoff.enabled=true (MFALIGN v2 box).
    """
    explicit_path = params.get("mf_to_of_handoff_path")
    flag = str(params.get("apply_mf_to_of_handoff", "")).lower()
    cfg = _mf_handoff_cfg(overrides)
    opted_in = (
        flag in ("1", "true", "yes", "on")
        or bool(explicit_path)
        or bool(cfg.get("enabled"))
    )
    if not opted_in:
        return params
    path = Path(str(explicit_path)) if explicit_path else Path(str(cfg.get("path") or MF_TO_OF_HANDOFF))
    if not path.is_absolute():
        path = ROOT / path
    if not path.is_file():
        out = dict(params)
        out["mf_to_of_handoff_error"] = f"handoff missing: {path}"
        return out
    try:
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        import mf_to_of_handoff as m2o

        merged = m2o.apply_handoff_to_params(
            params,
            handoff_path=path,
            overwrite=bool(params.get("mf_to_of_overwrite", True)),
        )
        merged["apply_mf_to_of_handoff"] = True
        merged["geometry_source"] = "mf_to_of_handoff"
        if cfg.get("stl_path"):
            merged["stl_path"] = str(cfg["stl_path"]).replace("\\", "/")
            # Prefer box STL over any leftover plate STEP.
            merged.pop("step_path", None)
        if cfg.get("geometry_family"):
            merged["geometry_family"] = cfg["geometry_family"]
        if cfg.get("viz_policy"):
            merged["viz_policy"] = cfg["viz_policy"]
        if cfg.get("forbid_stl_fill_time_contour"):
            merged["forbid_stl_fill_time_contour"] = True
        if cfg.get("lavie_case"):
            merged["lavie_mfalign_case"] = cfg["lavie_case"]
        return merged
    except Exception as exc:
        params = dict(params)
        params["mf_to_of_handoff_error"] = str(exc)[:160]
        return params

def _align_pack_end_time_to_fill(params: dict[str, Any]) -> dict[str, Any]:
    """Stop the packing default from truncating a fill-only analysis.

    cae_te_engine derives controlDict endTime from pack_end_time and never reads
    analysis_end_time_s, so a shorter packing horizon short-shots the run while
    the solver still exits with returncode 0 (INC-161).
    """
    if str(params.get("physics_category") or "") not in FILL_ONLY_CATEGORIES:
        return params
    if params.get("cool_end_time") is not None:
        return params
    try:
        fill_end = float(params["analysis_end_time_s"])
        pack_end = float(params["pack_end_time"])
    except (KeyError, TypeError, ValueError):
        return params
    if fill_end > pack_end:
        params = dict(params)
        params["pack_end_time"] = round(fill_end, 6)
        params["pack_end_time_source"] = "analysis_end_time_s"
    return params


def _build_golden_params(cycle_n: int) -> dict[str, Any] | None:
    """25サイクル毎にゴールデンケース(固定条件)を投入 (G3基準相関)。変種a/b交互。"""
    # MFALIGN box mode: never inject plate golden (user / bd mlqd / h9fc).
    if _mf_handoff_enabled():
        return None
    try:
        spec = json.loads(GOLDEN_SPEC_PATH.read_text(encoding="utf-8-sig"))
    except Exception:
        return None
    every = int((spec.get("schedule") or {}).get("inject_every_n_cycles", 25))
    if every <= 0 or int(cycle_n) % every != 0:
        return None
    variants = list((spec.get("variants") or {}).items())
    if not variants:
        return None
    name, vparams = variants[(int(cycle_n) // every) % len(variants)]
    geo = spec.get("geometry", {})
    params: dict[str, Any] = dict(spec.get("fixed_params") or {})
    params.update(vparams)
    params["golden_case"] = name
    params["gate_spec_path"] = geo.get("gate_spec_path", _rel(DEFAULT_GATE))
    params["step_path"] = geo.get("step_path", _rel(DEFAULT_STEP))
    params["geometry_source"] = "golden_case"
    return params


def build_openfoam_cad_params(cycle_n: int) -> dict[str, Any]:
    overrides = _load_overrides()
    mf_box = _mf_handoff_enabled(overrides)

    # G3: 定期ゴールデン投入 (固定条件 → moldflow_golden_case.py が誤差を追跡)
    # Skipped while MFALIGN box handoff is enabled (no plate).
    golden = _build_golden_params(cycle_n)
    if golden is not None:
        return golden

    ranges = (overrides.get("param_overrides") or {}).get("resin_fill_cad") or {}

    # G4: 決定論的学習サンプラ (2026-07-07 — 固定グリッド永久巡回=学習不在の是正)
    learned: dict[str, Any] = {}
    meta: dict[str, Any] = {}
    try:
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        import moldflow_golden_case as mgc
        import resin_fill_param_learner as learner

        trials = mgc.load_trials(CAE_LOG_PATH)
        cat_trials = [t for t in trials if t.get("category") == "resin_fill_cad"]
        good = learner.collect_good_params(cat_trials, list(_LEARNED_KEYS))
        lr = {k: tuple(v) for k, v in ranges.items()
              if isinstance(v, (list, tuple)) and len(v) == 2}
        learned, meta = learner.propose_params(cycle_n, good, lr)
    except Exception as exc:  # 学習器の不調で本体を止めない (フォールバック=旧グリッド)
        meta = {"mode": "legacy_sweep_fallback", "error": str(exc)[:120]}
        learned = {
            "polymer_nu": round(_sweep_value(ranges.get("polymer_nu") or [0.005, 0.02], cycle_n), 5),
            "inlet_velocity": round(_sweep_value(ranges.get("inlet_velocity") or [0.6, 1.15], cycle_n + 3), 4),
            "pack_pressure_MPa": round(_sweep_value(ranges.get("pack_pressure_MPa") or [5.0, 25.0], cycle_n + 7), 3),
            "pack_inlet_velocity": round(_sweep_value(ranges.get("pack_inlet_velocity") or [0.03, 0.1], cycle_n + 5), 4),
        }

    params: dict[str, Any] = {
        "physics_category": "resin_fill_vof",
        "mesh_mode": "blockmesh_bbox",
        "mesh_nx": 40,
        "gate_count": 1,
        "gate_position": "center",
        "gate_width_mm": 2.0,
        "gate_spec_path": _rel(DEFAULT_GATE) if DEFAULT_GATE.exists() else str(DEFAULT_GATE),
        "pack_end_time": 0.32,
        "sampling": meta,
    }
    params.update(learned)

    if mf_box:
        # Force MFALIGN v2 box shell + phi20 / gate=+X phi2 (not plate, not DXF2STEP).
        cfg = _mf_handoff_cfg(overrides)
        params["geometry_source"] = "mf_to_of_handoff"
        params["apply_mf_to_of_handoff"] = True
        params["mf_to_of_overwrite"] = True
        params["mf_to_of_handoff_path"] = str(cfg.get("path") or _rel(MF_TO_OF_HANDOFF)).replace("\\", "/")
        if cfg.get("stl_path"):
            params["stl_path"] = str(cfg["stl_path"]).replace("\\", "/")
        params["forbid_plate_geometry"] = True
        return _align_pack_end_time_to_fill(_apply_mf_handoff(params, overrides))

    handoff = pick_dxf2step_handoff()
    params["geometry_source"] = "dxf2step_handoff" if handoff else "default_sample"
    if handoff:
        params["step_path"] = handoff["step_rel"]
        if handoff.get("manifest_rel"):
            params["part_manifest_path"] = handoff["manifest_rel"]
        params["dxf2step_trial_id"] = handoff["trial_id"]
        params["geometry_adjudication"] = handoff.get("adjudication")
    else:
        params["step_path"] = _rel(DEFAULT_STEP) if DEFAULT_STEP.exists() else str(DEFAULT_STEP)
    return _align_pack_end_time_to_fill(_apply_mf_handoff(params, overrides))
