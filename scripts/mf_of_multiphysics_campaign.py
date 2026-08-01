# -*- coding: utf-8 -*-
"""Build a fail-closed Moldflow/OpenFOAM multiphysics calibration campaign.

This does not claim solver equivalence.  It inventories every Moldflow catalog
result, discovers OpenFOAM KPI coverage, and separates missing Cool truth from
existing Flow/Pack/Warp evidence.
"""
from __future__ import annotations

import sys
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import argparse
import json
import re
import sqlite3
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB = ROOT / "data/workspace/moldflow_bridge/mf_of_calibration.sqlite"
DEFAULT_OUT = ROOT / "data/workspace/moldflow_bridge/mf_of_multiphysics_campaign"
DEFAULT_MF_COOL_LOG = DEFAULT_OUT / "mf_cool_20260802/cool_task.log"


FAMILIES: tuple[tuple[str, tuple[str, ...], str, str], ...] = (
    ("fill", ("fill time", "fill_region", "polymer fill", "flow front"), "fill_time_s", "direct_kpi"),
    ("pressure_pack", ("pressure", "clamp force", "packing"), "pressure_drop_MPa", "direct_kpi"),
    ("weldline", ("weld", "meeting"), "weldline_location", "spatial_proxy"),
    ("warpage", ("deflection", "warpage", "warp"), "warpage_mm", "spatial_proxy"),
    ("sink_shrink", ("sink", "shrink", "volumetric shrinkage"), "sink_mark_risk", "model_proxy"),
    ("cooling", ("cool", "freeze", "frozen", "mold temperature", "temperature for warp"), "cooling_time_s", "cool_truth_required"),
    ("temperature", ("temperature",), "T_mean", "field_proxy"),
    ("rheology", ("viscosity", "shear rate", "shear stress", "flow direction", "orientation"), "shear_rate_max", "field_proxy"),
    ("air_trap", ("air trap",), "air_trap_count", "spatial_proxy"),
    ("density", ("density",), "density_mean", "field_proxy"),
)


def family_for(name: str) -> tuple[str, str, str]:
    low = name.lower().replace("_", " ")
    for family, words, of_kpi, mode in FAMILIES:
        if any(word in low for word in words):
            return family, of_kpi, mode
    return "other", "", "not_mapped"


def _loads(raw: Any) -> dict[str, Any]:
    if not raw:
        return {}
    try:
        value = json.loads(raw)
        return value if isinstance(value, dict) else {}
    except (TypeError, ValueError):
        return {}


def parse_mf_cool(log_path: Path) -> dict[str, Any]:
    if not log_path.is_file():
        return {"status": "NOT_RUN_ON_CURRENT_STUDY", "log": str(log_path)}
    text = log_path.read_text(encoding="utf-8", errors="replace")
    patterns = {
        "part_surface_T_max_K": r"Part surface temperature\s+- maximum\s+=\s+([0-9.]+)",
        "part_surface_T_min_K": r"Part surface temperature\s+- minimum\s+=\s+([0-9.]+)",
        "part_surface_T_avg_K": r"Part surface temperature\s+- average\s+=\s+([0-9.]+)",
        "cavity_surface_T_avg_K": r"Cavity surface temperature\s+- average\s+=\s+([0-9.]+)",
        "cycle_time_s": r"Cycle time\s+=\s+([0-9.]+)",
        "cpu_time_s": r"CPU time used\s+([0-9.]+)",
        "exit_code": r"EXIT=([0-9]+)",
    }
    values: dict[str, Any] = {}
    for key, pattern in patterns.items():
        match = re.search(pattern, text)
        if match:
            values[key] = int(match.group(1)) if key == "exit_code" else float(match.group(1))
    values.update({
        "status": "SUCCESS" if values.get("exit_code") == 0 and "cycle_time_s" in values else "INCOMPLETE",
        "log": str(log_path).replace("\\", "/"),
        "result_oc1": str(log_path.with_name("mf_minusx_cool_20260802.oc1")).replace("\\", "/"),
        "result_c2p": str(log_path.with_name("mf_minusx_cool_20260802.c2p")).replace("\\", "/"),
    })
    return values


def build(db_path: Path, study: str, mf_cool_log: Path = DEFAULT_MF_COOL_LOG) -> dict[str, Any]:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    study_rows = list(conn.execute(
        "SELECT * FROM studies WHERE study_name=? ORDER BY study_id", (study,)
    ))
    if not study_rows:
        raise SystemExit(f"study not found: {study}")
    study_ids = [int(row["study_id"]) for row in study_rows]
    placeholders = ",".join("?" for _ in study_ids)
    # Historical ingest created duplicate study rows after the SDY reference
    # changed.  Treat identical study_name rows as one calibration lineage.
    study_id = max(study_ids, key=lambda value: conn.execute(
        "SELECT count(*) FROM result_catalog WHERE study_id=?", (value,)
    ).fetchone()[0])
    catalog = list(conn.execute(
        "SELECT * FROM result_catalog WHERE study_id=? ORDER BY dsid", (study_id,)
    ))
    trials = list(conn.execute(
        f"SELECT * FROM of_trials WHERE study_id IN ({placeholders}) ORDER BY created_at", study_ids
    ))
    of_keys: set[str] = set()
    for trial in trials:
        of_keys.update(_loads(trial["kpis_json"]).keys())
        of_keys.update(_loads(trial["vs_mf_json"]).keys())

    mf_cool = parse_mf_cool(mf_cool_log)
    rows: list[dict[str, Any]] = []
    for item in catalog:
        mf_name = str(item["mf_name"] or item["safe_name"])
        family, of_kpi, mode = family_for(mf_name)
        mf_available = bool(item["has_csv"] or item["has_parquet"] or item["absmax"] is not None)
        of_available = bool(of_kpi and of_kpi in of_keys)
        if family == "cooling" and not mf_available:
            state = (
                "MF_COOL_SOLVED_FIELD_EXPORT_PENDING"
                if mf_cool.get("status") == "SUCCESS" else "PENDING_MF_COOL"
            )
        elif mf_available and of_available:
            state = "READY_COMPARE"
        elif mf_available:
            state = "PENDING_OF_EXTRACTOR"
        elif str(item["status"]) == "unavailable_on_study":
            state = "MF_UNAVAILABLE_ON_FLOW_WARP"
        else:
            state = "PENDING_MF_EXPORT"
        rows.append({
            "dsid": item["dsid"], "mf_name": mf_name, "safe_name": item["safe_name"],
            "family": family, "comparison_mode": mode, "mf_status": item["status"],
            "mf_available": mf_available, "mf_csv": item["csv_path"],
            "mf_absmax": item["absmax"], "unit": item["unit"],
            "of_kpi": of_kpi or None, "of_available": of_available, "state": state,
            "accuracy_band": "PROXY_GAP",
        })

    states = Counter(row["state"] for row in rows)
    families = Counter(row["family"] for row in rows)
    priorities = [
        {"rank": 1, "family": "fill", "action": "spatial RMSE for fill time/front and completion"},
        {"rank": 2, "family": "pressure_pack", "action": "pressure history/field error; calibrate rheology and V/P switch"},
        {"rank": 3, "family": "cooling", "action": "export solved MF Cool fields; compare freeze/cycle/T fields with queued OF Cool"},
        {"rank": 4, "family": "sink_shrink", "action": "replace pack-ratio-only proxy with PVT/thermal shrink calibration"},
        {"rank": 5, "family": "warpage", "action": "compare nodal displacement after calibrated pack+cool history"},
        {"rank": 6, "family": "weldline", "action": "compare ridge coordinates and distance distribution; location only"},
    ]
    return {
        "generated_at": datetime.now().astimezone().isoformat(),
        "study": study, "study_id": study_id, "study_lineage_ids": study_ids,
        "db": str(db_path).replace("\\", "/"),
        "accuracy_band": "PROXY_GAP", "never_claim": "MOLDFLOW_EQUIVALENT",
        "catalog_results": len(rows), "of_trials": len(trials),
        "of_kpis_discovered": sorted(of_keys), "state_counts": dict(states),
        "family_counts": dict(families), "priorities": priorities,
        "cooling_campaign": {
            "mf_status": mf_cool.get("status"),
            "mf_kpis": mf_cool,
            "required_sequence": "Cool on a SaveAs copy with real cooling circuits",
            "known_proven_recipe": "CreateNodeByXYZ -> channel 40480 beams -> CreateNDBC type 40020 -> cool.exe",
            "reference_evidence_only": {"study": "mf_strip_cool_v12_20260720", "circuits": 8, "cycle_s": 35.0},
            "of_category": "resin_fill_cool", "of_solver": "compressibleInterFoam",
            "minimum_common_kpis": ["cooling_time_s", "freeze_time_s", "T_min", "T_max", "warpage_mm"],
            "gate": "Do not calibrate cooling against the old reference as if it were the minus-X study",
        },
        "rows": rows,
    }


def write_report(result: dict[str, Any], out_dir: Path) -> tuple[Path, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = out_dir / "campaign_latest.json"
    md_path = out_dir / "campaign_latest.md"
    json_path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    lines = [
        "# Moldflow vs OpenFOAM multiphysics campaign", "",
        f"- Study: `{result['study']}`", f"- Catalog: **{result['catalog_results']}** results",
        f"- OF trials: **{result['of_trials']}**", "- Label: **PROXY_GAP**", "",
        "## Coverage", "", "| State | Count |", "|---|---:|",
    ]
    lines += [f"| {key} | {value} |" for key, value in sorted(result["state_counts"].items())]
    lines += ["", "## Priority", ""]
    lines += [f"{p['rank']}. **{p['family']}** - {p['action']}" for p in result["priorities"]]
    cool = result["cooling_campaign"]
    cool_text = (
        f"Moldflow Cool solved successfully: cycle={cool['mf_kpis'].get('cycle_time_s')} s, "
        f"part surface average={cool['mf_kpis'].get('part_surface_T_avg_K')} K. "
        "Field plots still require CSV export before spatial comparison."
        if cool.get("mf_status") == "SUCCESS"
        else "Current minus-X study has no Moldflow Cool truth. Use a SaveAs copy with cooling circuits."
    )
    lines += ["", "## Cooling gate", "", cool_text, ""]
    md_path.write_text("\n".join(lines), encoding="utf-8")
    return json_path, md_path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--study", default="mf_fc_warp_v2_20260720_(copy)_minusX")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--mf-cool-log", type=Path, default=DEFAULT_MF_COOL_LOG)
    args = parser.parse_args()
    result = build(args.db, args.study, args.mf_cool_log)
    json_path, md_path = write_report(result, args.out)
    print(json.dumps({
        "json": str(json_path), "markdown": str(md_path),
        "catalog_results": result["catalog_results"], "state_counts": result["state_counts"],
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
