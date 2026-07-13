# -*- coding: utf-8 -*-
"""Safe 24/365 supervisor for Moldflow-class capability improvement.

This supervisor observes evidence, ranks the next smallest experiment, and
writes durable status. It never edits solver code or promotes a candidate to
production. Trials are delegated to the existing CAE harness only when
explicitly requested and permitted by cooldown/budget gates.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config" / "moldflow_continuous_improvement.json"
WORKSPACE = ROOT / "data" / "workspace"
STATUS = WORKSPACE / "moldflow_continuous_improvement_status.json"
HISTORY = WORKSPACE / "moldflow_continuous_improvement_history.jsonl"
CAE_LOG = ROOT / "data" / "cae_te_workspace" / "results" / "cae_te_log.json"


def load_json(path: Path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception:
        return default


def parse_time(value: str | None):
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=datetime.now().astimezone().tzinfo)
        return parsed
    except ValueError:
        return None


def latest_reference_trial(cfg: dict) -> dict:
    doc = load_json(CAE_LOG, {})
    trials = doc.get("trials", []) if isinstance(doc, dict) else []
    prefixes = tuple(str(x) for x in cfg.get("trial_id_prefixes", []))
    matches = [t for t in trials if str(t.get("id", "")).startswith(prefixes)]
    # cae_te_log stores newest trials first today, but ordering is not part of
    # its schema. Select by timestamp instead of relying on list position.
    return max(matches, key=lambda t: str(t.get("timestamp", ""))) if matches else {}


def reproducibility_evidence(cfg: dict) -> dict:
    """Count deterministic hard-gate passes for the configured promotion candidate."""
    doc = load_json(CAE_LOG, {})
    trials = doc.get("trials", []) if isinstance(doc, dict) else []
    prefix = str(cfg.get("promotion_trial_prefix", ""))
    hard = cfg["hard_gates"]
    pressure_reference = float(cfg["reference"]["max_injection_pressure_mpa"])
    pressure_tolerance = float(
        cfg.get("calibration_tolerances", {}).get(
            "max_injection_pressure_absolute_error_pct", 10.0
        )
    )
    weight_reference = float(cfg["reference"]["part_weight_g"])
    weight_tolerance = float(
        cfg.get("calibration_tolerances", {}).get("part_weight_absolute_error_pct", 5.0)
    )
    temperature_reference = float(cfg["reference"]["max_bulk_temperature_c"])
    temperature_tolerance = float(
        cfg.get("calibration_tolerances", {}).get(
            "max_bulk_temperature_absolute_error_pct", 5.0
        )
    )
    qualifying = []
    for trial in trials:
        if not prefix or not str(trial.get("id", "")).startswith(prefix):
            continue
        defects = observed_defects(trial)
        try:
            fill = float(defects.get("fill_fraction_pct"))
            alpha = float(defects.get("alpha_max"))
            fill_time = float(defects.get("fill_time_s"))
            pressure = float(defects.get("max_injection_pressure_proxy_mpa"))
            weight = float(defects.get("part_weight_proxy_g"))
            temperature = float(defects.get("max_bulk_temperature_proxy_c"))
        except (TypeError, ValueError):
            continue
        pressure_error_pct = abs(pressure - pressure_reference) / pressure_reference * 100.0
        weight_error_pct = abs(weight - weight_reference) / weight_reference * 100.0
        temperature_error_pct = (
            abs(temperature - temperature_reference) / temperature_reference * 100.0
        )
        if (
            trial.get("verdict") == "SUCCESS"
            and fill >= float(hard["fill_fraction_min_pct"])
            and float(hard["alpha_polymer_min"]) <= alpha <= float(hard["alpha_polymer_max"])
            and pressure_error_pct <= pressure_tolerance
            and weight_error_pct <= weight_tolerance
            and temperature_error_pct <= temperature_tolerance
        ):
            qualifying.append(
                {
                    "id": trial.get("id"),
                    "fill_fraction_pct": fill,
                    "fill_time_s": fill_time,
                    "alpha_max": alpha,
                    "max_injection_pressure_proxy_mpa": pressure,
                    "max_injection_pressure_error_pct": pressure_error_pct,
                    "part_weight_proxy_g": weight,
                    "part_weight_error_pct": weight_error_pct,
                    "max_bulk_temperature_proxy_c": temperature,
                    "max_bulk_temperature_error_pct": temperature_error_pct,
                }
            )
    fills = [row["fill_fraction_pct"] for row in qualifying]
    times = [row["fill_time_s"] for row in qualifying]
    pressures = [
        float(row["max_injection_pressure_proxy_mpa"])
        for row in qualifying
        if row.get("max_injection_pressure_proxy_mpa") is not None
    ]
    weights = [row["part_weight_proxy_g"] for row in qualifying]
    temperatures = [row["max_bulk_temperature_proxy_c"] for row in qualifying]
    fill_spread = (max(fills) - min(fills)) if fills else None
    time_spread = (max(times) - min(times)) if times else None
    required = int(cfg["promotion"]["minimum_repeated_passes"])
    max_spread = float(hard["reproducibility_spread_max_pct"])
    reproducible = bool(
        len(qualifying) >= required
        and fill_spread is not None
        and fill_spread <= max_spread
    )
    return {
        "candidate_prefix": prefix,
        "qualifying_passes": len(qualifying),
        "required_passes": required,
        "fill_spread_percentage_points": fill_spread,
        "fill_time_spread_s": time_spread,
        "injection_pressure_spread_mpa": (
            max(pressures) - min(pressures) if pressures else None
        ),
        "part_weight_spread_g": max(weights) - min(weights) if weights else None,
        "max_bulk_temperature_spread_c": (
            max(temperatures) - min(temperatures) if temperatures else None
        ),
        "reproducible": reproducible,
        "production_promotion_allowed": False,
        "trials": qualifying[:10],
    }


def observed_defects(trial: dict) -> dict:
    """Return trial defects enriched with alpha evidence from its run artifact."""
    defects = dict(trial.get("defects_detected") or {})
    nonphysical = defects.get("nonphysical") or {}
    if nonphysical.get("alpha_max") is not None:
        defects["alpha_max"] = nonphysical["alpha_max"]
    run_dir_raw = trial.get("run_dir")
    if run_dir_raw:
        run_dir = Path(str(run_dir_raw))
        kpi = load_json(run_dir / "vof_fill_kpis.json", {})
        if kpi.get("alpha_max") is not None:
            defects["alpha_max"] = kpi["alpha_max"]
        pressure = load_json(run_dir / "injection_pressure_kpi.json", {})
        if pressure.get("maximum_injection_pressure_proxy_mpa") is not None:
            defects["max_injection_pressure_proxy_mpa"] = pressure[
                "maximum_injection_pressure_proxy_mpa"
            ]
            defects["max_injection_pressure_error_pct"] = pressure.get(
                "absolute_error_pct"
            )
            defects["max_injection_pressure_peak_time_s"] = pressure.get("peak_time_s")
        weight = load_json(run_dir / "part_weight_kpi.json", {})
        if weight.get("part_weight_proxy_g") is not None:
            defects["part_weight_proxy_g"] = weight["part_weight_proxy_g"]
            defects["part_weight_error_pct"] = weight.get("absolute_error_pct")
        temperature = load_json(run_dir / "bulk_temperature_kpi.json", {})
        if temperature.get("maximum_bulk_temperature_proxy_c") is not None:
            defects["max_bulk_temperature_proxy_c"] = temperature[
                "maximum_bulk_temperature_proxy_c"
            ]
            defects["max_bulk_temperature_error_pct"] = temperature.get(
                "absolute_error_pct"
            )
    return defects


def decide(trial: dict, cfg: dict) -> dict:
    defects = observed_defects(trial)
    alpha = defects.get("alpha_max")
    fill = defects.get("fill_fraction_pct")
    hard = cfg["hard_gates"]
    if alpha is None or float(alpha) > float(hard["alpha_polymer_max"]):
        return {
            "priority": "P0",
            "capability": "bounded_vof_fill",
            "decision_rule": "IF alpha.polymer > 1.05 THEN reject the run and stabilize VOF before material calibration BECAUSE phase fraction is nonphysical.",
            "next_experiment": "Reduce adaptive time step and interface Courant limit; enable bounded-alpha safeguards; run one fixed reference trial.",
        }
    if fill is None or float(fill) < float(hard["fill_fraction_min_pct"]):
        return {
            "priority": "P1",
            "capability": "complete_fill",
            "decision_rule": "IF bounded fill < 99% THEN calibrate inlet/end-time before adding downstream physics BECAUSE pressure and thermal KPIs are not comparable on a short shot.",
            "next_experiment": "Calibrate gate flow and vent topology against the 0.9 s commercial reference without permitting polymer loss.",
        }
    pressure = defects.get("max_injection_pressure_proxy_mpa")
    if pressure is None:
        return {
            "priority": "P2",
            "capability": "injection_pressure_observability",
            "decision_rule": "IF fill is bounded and complete but gate pressure is absent THEN extract a defined gate gauge-pressure KPI before tuning BECAUSE an unmeasured KPI cannot be calibrated.",
            "next_experiment": "Extract written-time gate-face-average gauge pressure and compare it with 10.8794 MPa.",
        }
    reference = float(cfg["reference"]["max_injection_pressure_mpa"])
    error_pct = abs(float(pressure) - reference) / reference * 100.0
    tolerance = float(
        cfg.get("calibration_tolerances", {}).get(
            "max_injection_pressure_absolute_error_pct", 10.0
        )
    )
    if error_pct > tolerance:
        return {
            "priority": "P2",
            "capability": "injection_pressure_calibration",
            "decision_rule": f"IF gate pressure error ({error_pct:.2f}%) exceeds {tolerance:.2f}% THEN tune one pressure-driving parameter while preserving the fill hard gates BECAUSE fill-time agreement alone is insufficient.",
            "next_experiment": "Separate trapped-air backpressure from polymer flow resistance, then vary only the validated vent/backpressure parameter toward 10.8794 MPa.",
        }
    weight = defects.get("part_weight_proxy_g")
    if weight is None:
        return {
            "priority": "P3",
            "capability": "part_weight_observability",
            "decision_rule": "IF fill and injection pressure pass but weight is absent THEN extract alpha-volume times material density before tuning BECAUSE weight must be independently observable.",
            "next_experiment": "Extract polymer volume and density-based part weight and compare it with 9.0911 g.",
        }
    weight_reference = float(cfg["reference"]["part_weight_g"])
    weight_error_pct = abs(float(weight) - weight_reference) / weight_reference * 100.0
    weight_tolerance = float(
        cfg.get("calibration_tolerances", {}).get("part_weight_absolute_error_pct", 5.0)
    )
    if weight_error_pct > weight_tolerance:
        return {
            "priority": "P3",
            "capability": "part_weight_calibration",
            "decision_rule": f"IF part-weight error ({weight_error_pct:.2f}%) exceeds {weight_tolerance:.2f}% THEN calibrate polymer melt density while preserving fill and pressure gates BECAUSE density directly maps filled volume to mass.",
            "next_experiment": "Set the measured effective melt density near 765.07 kg/m3, rerun once, and reject it if pressure or fill regresses.",
        }
    temperature = defects.get("max_bulk_temperature_proxy_c")
    if temperature is None:
        return {
            "priority": "P4",
            "capability": "bulk_temperature_observability",
            "decision_rule": "IF fill, pressure, and weight pass but temperature history is absent THEN record runtime extrema before tuning BECAUSE final temperature misses the fill-history maximum.",
            "next_experiment": "Record fieldMinMax(T) and alpha-weighted bulk temperature every step, then compare with 241.0592 C.",
        }
    temperature_reference = float(cfg["reference"]["max_bulk_temperature_c"])
    temperature_error_pct = abs(float(temperature) - temperature_reference) / temperature_reference * 100.0
    temperature_tolerance = float(
        cfg.get("calibration_tolerances", {}).get(
            "max_bulk_temperature_absolute_error_pct", 5.0
        )
    )
    if temperature_error_pct > temperature_tolerance:
        return {
            "priority": "P4",
            "capability": "bulk_temperature_calibration",
            "decision_rule": f"IF maximum bulk-temperature error ({temperature_error_pct:.2f}%) exceeds {temperature_tolerance:.2f}% THEN tune one thermal input while preserving fill, pressure, and weight gates.",
            "next_experiment": "Calibrate melt temperature or thermal transport one parameter at a time toward 241.0592 C.",
        }
    return {
        "priority": "P5",
        "capability": "wall_shear_calibration",
        "decision_rule": "IF fill, pressure, weight, and bulk temperature pass THEN add the next commercial rheology KPI sequentially.",
        "next_experiment": "Define wall shear stress and shear-rate proxies and compare with 0.1644 MPa and 5565.3267 1/s.",
    }


def trial_allowed(
    cfg: dict, previous: dict, now: datetime, latest_trial: dict | None = None
) -> tuple[bool, str]:
    candidates = [
        parse_time(previous.get("last_trial_at")),
        parse_time((latest_trial or {}).get("timestamp")),
    ]
    known = [value for value in candidates if value is not None]
    last = max(known) if known else None
    if last and now - last < timedelta(hours=float(cfg["minimum_trial_cooldown_hours"])):
        return False, "cooldown"
    day = now.date().isoformat()
    if previous.get("trial_day") == day and int(previous.get("trials_today", 0)) >= int(cfg["max_trials_per_day"]):
        return False, "daily_budget"
    return True, "allowed"


def postprocess_trial(run_dir: Path, cfg: dict) -> dict:
    """Create comparable KPI artifacts for an executed trial."""
    result: dict = {}
    commands = [
        (
            "injection_pressure",
            ROOT / "scripts" / "moldflow_injection_pressure_kpi.py",
            "--commercial-reference-mpa",
            cfg["reference"]["max_injection_pressure_mpa"],
        ),
        (
            "part_weight",
            ROOT / "scripts" / "moldflow_part_weight_kpi.py",
            "--commercial-reference-g",
            cfg["reference"]["part_weight_g"],
        ),
        (
            "bulk_temperature",
            ROOT / "scripts" / "moldflow_bulk_temperature_kpi.py",
            "--commercial-reference-c",
            cfg["reference"]["max_bulk_temperature_c"],
        ),
    ]
    for name, script, flag, reference in commands:
        completed = subprocess.run(
            [sys.executable, str(script), str(run_dir), flag, str(reference)],
            cwd=ROOT,
            timeout=120,
            capture_output=True,
            text=True,
        )
        result[name] = {
            "returncode": completed.returncode,
            "output_tail": (completed.stdout + completed.stderr)[-1000:],
        }
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--execute-trial", action="store_true")
    args = parser.parse_args()
    cfg = load_json(CONFIG, {})
    if not cfg.get("enabled"):
        print("[SKIP] disabled")
        return 0
    now = datetime.now(timezone.utc)
    previous = load_json(STATUS, {})
    trial = latest_reference_trial(cfg)
    observed = observed_defects(trial)
    reproducibility = reproducibility_evidence(cfg)
    action = decide(trial, cfg)
    allowed, reason = trial_allowed(cfg, previous, now, trial)
    record = {
        "schema": cfg["schema"],
        "checked_at": now.isoformat(),
        "mode": "execute_one_trial" if args.execute_trial else "observe_plan",
        "reference_trial": trial.get("id"),
        "reference_verdict": trial.get("verdict"),
        "observed": observed,
        "action": action,
        "trial_allowed": allowed,
        "trial_gate_reason": reason,
        "automatic_production_promotion": False,
        "promotion_evidence": reproducibility,
    }
    params = ROOT / str(cfg.get("trial_params_file", ""))
    if args.execute_trial and allowed and params.exists():
        prefix = str(cfg.get("promotion_trial_prefix") or "moldflow_ci_candidate")
        trial_id = prefix + "_auto_" + now.strftime("%Y%m%d_%H%M%S")
        cmd = [sys.executable, str(ROOT / "scripts" / "cae_te_remote_trial.py"), "--category", "resin_fill_cad", "--trial-id", trial_id, "--params-file", str(params), "--no-cleanup-runs"]
        trial_env = os.environ.copy()
        trial_env["CAE_FILL_VIDEO_TELEGRAM"] = "0"
        result = subprocess.run(
            cmd, cwd=ROOT, timeout=1800, capture_output=True, text=True, env=trial_env
        )
        record["executed_trial_id"] = trial_id
        record["trial_returncode"] = result.returncode
        record["trial_output_tail"] = (result.stdout + result.stderr)[-4000:]
        run_dir = ROOT / "data" / "cae_te_workspace" / "runs" / trial_id
        if result.returncode == 0 and run_dir.exists():
            record["postprocess"] = postprocess_trial(run_dir, cfg)
        record["last_trial_at"] = now.isoformat()
        day = now.date().isoformat()
        record["trial_day"] = day
        record["trials_today"] = int(previous.get("trials_today", 0)) + 1 if previous.get("trial_day") == day else 1
    else:
        record["last_trial_at"] = previous.get("last_trial_at")
        record["trial_day"] = previous.get("trial_day")
        record["trials_today"] = previous.get("trials_today", 0)
    STATUS.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
    with HISTORY.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False) + "\n")
    print(json.dumps(record, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
