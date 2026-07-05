# -*- coding: utf-8 -*-
"""Mandatory per-trial KPI evolution gate (all CAE tracks)."""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

ROOT = Path(__file__).resolve().parents[1]
WORKSPACE = ROOT / "data" / "workspace"
STATE_PATH = WORKSPACE / "cae_trial_evolution_state.json"
JST = timezone(timedelta(hours=9))

EVOLUTION_FAIL_VERDICT = "FAILED_NO_EVOLUTION"


def _now_iso() -> str:
    return datetime.now(JST).isoformat(timespec="seconds")


def _load_state() -> dict[str, Any]:
    if not STATE_PATH.exists():
        return {"schema": "clawstack.cae_trial_evolution_state.v1", "tracks": {}}
    try:
        return json.loads(STATE_PATH.read_text(encoding="utf-8-sig"))
    except Exception:
        return {"schema": "clawstack.cae_trial_evolution_state.v1", "tracks": {}}


def _save_state(state: dict[str, Any]) -> None:
    state["updated_at"] = _now_iso()
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _round_f(v: Any, nd: int = 6) -> float | None:
    try:
        return round(float(v), nd)
    except (TypeError, ValueError):
        return None


def _trial_params(trial_entry: dict[str, Any]) -> dict[str, Any]:
    params = dict(trial_entry.get("params") or {})
    for key in ("variant", "case_label"):
        if trial_entry.get(key) is not None:
            params[key] = trial_entry.get(key)
    return params


def _trial_kpis(trial_entry: dict[str, Any]) -> dict[str, Any]:
    defects = dict(trial_entry.get("defects_detected") or trial_entry.get("defects") or {})
    out: dict[str, Any] = {}
    for key in (
        "fill_fraction_pct",
        "fill_time_s",
        "fill_complete",
        "pressure_drop_MPa",
        "short_shot_risk",
        "pack_pressure_ratio",
        "yield_pct",
        "springback_deg",
        "press_force_tons",
        "warpage_mm",
        # fem_impact QCゲート実測値 (KPI無しトラック対策: 進化判定の材料にする)
        "qc_bbox_diag",
        "qc_coord_abs_max",
        "qc_displacement_abs_max",
    ):
        if key in defects:
            val = defects[key]
            if isinstance(val, (int, float)):
                out[key] = _round_f(val)
            elif isinstance(val, bool):
                out[key] = val
            elif val is not None:
                out[key] = str(val)
    return out


def fingerprint_trial(track: str, trial_entry: dict[str, Any]) -> str:
    payload = {
        "track": track,
        "category": trial_entry.get("category"),
        "params": _trial_params(trial_entry),
        "kpis": _trial_kpis(trial_entry),
        "geometry": {
            "step_path": trial_entry.get("step_path") or _trial_params(trial_entry).get("step_path"),
            "case_dir": trial_entry.get("case_dir"),
        },
    }
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:24]


def _stdout_flags(trial_entry: dict[str, Any]) -> list[str]:
    flags: list[str] = []
    wr = trial_entry.get("worker_result") or {}
    stdout = str(wr.get("stdout_tail") or "")
    if "FEM_IMPACT_SKIP_RECOMPUTE" in stdout:
        flags.append("fem_skip_recompute")
    if "FEM_IMPACT_REUSE_VTK" in stdout:
        flags.append("fem_reuse_vtk")
    return flags


def check_evolution(track: str, trial_entry: dict[str, Any]) -> tuple[bool, str, str]:
    """Return (evolved_ok, fingerprint, reason)."""
    fp = fingerprint_trial(track, trial_entry)
    state = _load_state()
    tracks = state.setdefault("tracks", {})
    prev = tracks.get(track) or {}
    prev_fp = str(prev.get("fingerprint") or "")
    prev_verdict = str(prev.get("verdict") or "")
    flags = _stdout_flags(trial_entry)

    if flags and "fem_skip_recompute" in flags and prev_fp == fp:
        return False, fp, "FEM cache hit without KPI/param change (SKIP_RECOMPUTE)"

    if prev_fp and prev_fp == fp and prev_verdict in ("SUCCESS", "DRY_RUN"):
        return False, fp, "identical params+KPI fingerprint vs prior trial on this track"

    if prev_fp and prev_fp == fp:
        return False, fp, "identical fingerprint vs prior trial (no measurable evolution)"

    return True, fp, "evolved"


def record_trial(track: str, trial_entry: dict[str, Any], *, fingerprint: str) -> None:
    state = _load_state()
    tracks = state.setdefault("tracks", {})
    tracks[track] = {
        "trial_id": trial_entry.get("id") or trial_entry.get("trial_id"),
        "verdict": trial_entry.get("verdict"),
        "category": trial_entry.get("category"),
        "fingerprint": fingerprint,
        "kpis": _trial_kpis(trial_entry),
        "at": _now_iso(),
    }
    _save_state(state)


def apply_evolution_gate(track: str, result: dict[str, Any]) -> dict[str, Any]:
    """Downgrade SUCCESS to FAILED_NO_EVOLUTION when KPI/params did not evolve."""
    trial_entry = result.get("trial_entry")
    if not isinstance(trial_entry, dict):
        return result

    verdict = str(result.get("verdict") or trial_entry.get("verdict") or "")
    if verdict not in ("SUCCESS", "DRY_RUN"):
        evolved, fp, reason = check_evolution(track, trial_entry)
        trial_entry["evolution_gate"] = {
            "ok": evolved,
            "fingerprint": fp,
            "reason": reason,
            "enforced": False,
        }
        result["trial_entry"] = trial_entry
        return result

    evolved, fp, reason = check_evolution(track, trial_entry)
    gate = {
        "ok": evolved,
        "fingerprint": fp,
        "reason": reason,
        "enforced": True,
        "policy": "P026 mandatory per-trial evolution",
    }
    trial_entry["evolution_gate"] = gate

    if not evolved:
        trial_entry["verdict"] = EVOLUTION_FAIL_VERDICT
        trial_entry["evolution_gate_fail_reason"] = reason
        result["verdict"] = EVOLUTION_FAIL_VERDICT
    else:
        record_trial(track, trial_entry, fingerprint=fp)

    result["trial_entry"] = trial_entry
    return result
