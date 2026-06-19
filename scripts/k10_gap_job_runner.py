# -*- coding: utf-8 -*-
"""SJP-3: lightweight K10 gap jobs (DXF2STEP + Cetol/TOLERANCE proxy) while heavy CAE runs elsewhere."""
from __future__ import annotations

import argparse
import json
import sys
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

ROOT = Path(__file__).resolve().parents[1]
JST = timezone(timedelta(hours=9))
OUT_DIR = ROOT / "data" / "workspace" / "sjp3_gap_jobs"
LOG_PATH = ROOT / "data" / "workspace" / "sjp3_gap_log.jsonl"

if str(ROOT / "data" / "workspace") not in sys.path:
    sys.path.insert(0, str(ROOT / "data" / "workspace"))

import growth_domain_runners as growth


def append_log(entry: dict[str, Any]) -> None:
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    entry = dict(entry)
    entry["logged_at"] = datetime.now(JST).isoformat()
    with LOG_PATH.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry, ensure_ascii=False) + "\n")


def probe_dxf2step_api() -> tuple[bool, str, str]:
    """Host FastAPI (8002). Docker Streamlit dxf3d_app is on 8003 (different API)."""
    import httpx

    url = "http://127.0.0.1:8002/api/dxf2step/health"
    try:
        r = httpx.get(url, timeout=4)
        if r.status_code == 200:
            body = r.json()
            if body.get("status") == "ok":
                mode = body.get("engine", {}).get("mode", "?")
                return True, url, f"engine={mode}"
        return False, url, f"status={r.status_code}"
    except Exception as exc:
        return False, url, str(exc)[:120]


def run_dxf2step_gap(out_dir: Path, difficulty: int = 1) -> dict[str, Any]:
    """DXF2STEP gap check: proxy KPI + optional API health ping."""
    run_id = f"sjp3-dxf-{uuid.uuid4().hex[:8]}"
    job_dir = out_dir / run_id
    job_dir.mkdir(parents=True, exist_ok=True)

    sample_dxf = ROOT / "data" / "workspace" / "apps" / "dxf2step" / "jobs"
    dxf_count = len(list(sample_dxf.glob("**/input/*.dxf"))) if sample_dxf.exists() else 0
    api_ok, api_url, api_detail = probe_dxf2step_api()

    artifact = {
        "domain": "DXF2STEP",
        "run_id": run_id,
        "difficulty": difficulty,
        "host": "k10",
        "kpi_values": {
            "kpi_sample_dxf_count": dxf_count,
            "kpi_api_reachable": api_ok,
            "kpi_api_url": api_url,
            "kpi_pipeline_ready": dxf_count > 0 and api_ok,
        },
        "notes": "sjp3_gap_v1 (proxy; real conversion via dxf2step API when online)",
    }
    artifact_path = job_dir / "dxf2step_gap.json"
    artifact_path.write_text(json.dumps(artifact, ensure_ascii=False, indent=2), encoding="utf-8")
    ok = bool(artifact["kpi_values"]["kpi_pipeline_ready"])
    return {
        "job": "dxf2step",
        "run_id": run_id,
        "ok": ok,
        "verdict": "PASS" if ok else "WARN",
        "artifact": str(artifact_path),
        "api_detail": api_detail,
        "log": f"DXF2STEP gap: samples={dxf_count} api={api_detail}",
    }


def run_tolerance_gap(out_dir: Path, difficulty: int = 1) -> dict[str, Any]:
    run_id = f"sjp3-tol-{uuid.uuid4().hex[:8]}"
    job_dir = out_dir / run_id
    job_dir.mkdir(parents=True, exist_ok=True)
    params = {"chain_length": 3, "gdt_feature_count": 2, "spec_limit_mm": 0.5}
    hist = ROOT / "data" / "workspace" / "thinkpad_dxf2step_history"
    manifests = sorted(
        hist.glob("*/part_manifest.json"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    if manifests:
        params["part_manifest_path"] = str(manifests[0].resolve())
    result = growth.run_tolerance_analysis_proxy(job_dir, difficulty, params)
    return {
        "job": "tolerance_analysis",
        "run_id": run_id,
        "ok": result.ok,
        "verdict": "PASS" if result.ok else "FAIL",
        "artifact": result.artifact_path,
        "runtime_sec": result.runtime_sec,
        "log": result.log_text,
    }


RUNNERS = {
    "dxf2step": run_dxf2step_gap,
    "tolerance": run_tolerance_gap,
    "cetol": run_tolerance_gap,
}


def run_gap_jobs(jobs: list[str], difficulty: int = 1) -> dict[str, Any]:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    results: list[dict[str, Any]] = []
    for name in jobs:
        key = name.strip().lower()
        fn = RUNNERS.get(key)
        if not fn:
            results.append({"job": name, "verdict": "ERROR", "error": f"unknown job {name}"})
            continue
        try:
            entry = fn(OUT_DIR, difficulty)
            results.append(entry)
            print(f"[sjp3-gap] {entry.get('job')} verdict={entry.get('verdict')} {entry.get('log', '')[:120]}")
        except Exception as exc:
            results.append({"job": key, "verdict": "ERROR", "error": str(exc)})
            print(f"[sjp3-gap] ERROR {key}: {exc}")
    summary = {
        "jobs": results,
        "all_ok": all(r.get("verdict") in {"PASS", "WARN"} for r in results),
    }
    append_log(summary)
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description="SJP-3 K10 gap jobs")
    parser.add_argument(
        "--jobs",
        default="tolerance,dxf2step",
        help="Comma list: tolerance,cetol,dxf2step",
    )
    parser.add_argument("--difficulty", type=int, default=1)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    job_list = [j.strip() for j in args.jobs.split(",") if j.strip()]
    summary = run_gap_jobs(job_list, args.difficulty)
    if args.json:
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    print(f"\nlog: {LOG_PATH}")
    ok = summary.get("all_ok", False)
    print(f"RESULT: {'PASS' if ok else 'FAIL'}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
