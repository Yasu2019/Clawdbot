# -*- coding: utf-8 -*-
"""Persist DXF2STEP job outcomes to universal_growth.db (KPI + failure evidence)."""
from __future__ import annotations

import sys
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import json
import os
import sqlite3
from pathlib import Path

DOMAIN = "DXF2STEP"
DB_FILE = Path(__file__).resolve().parents[2] / "universal_growth.db"
JOBS_DIR = Path(__file__).resolve().parent / "jobs"


def _ensure_schema(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS growth_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            domain TEXT,
            challenge TEXT,
            status TEXT,
            know_how TEXT,
            artifact_path TEXT,
            difficulty INTEGER,
            evidence TEXT,
            source TEXT
        )
        """
    )
    cols = [r[1] for r in conn.execute("PRAGMA table_info(growth_records)").fetchall()]
    for name, ddl in [
        ("difficulty", "ALTER TABLE growth_records ADD COLUMN difficulty INTEGER"),
        ("evidence", "ALTER TABLE growth_records ADD COLUMN evidence TEXT"),
        ("source", "ALTER TABLE growth_records ADD COLUMN source TEXT"),
    ]:
        if name not in cols:
            try:
                conn.execute(ddl)
            except Exception:
                pass


def _job_already_recorded(conn: sqlite3.Connection, job_id: str) -> bool:
    needle = f'"job_id": "{job_id}"'
    n = conn.execute(
        "SELECT COUNT(*) FROM growth_records WHERE domain=? AND evidence LIKE ?",
        (DOMAIN, f"%{needle}%"),
    ).fetchone()[0]
    return int(n) > 0


def evaluate_outputs(output_dir: Path, build_log: dict) -> tuple[str, dict, list[str]]:
    """Return (status, kpi_values, failed_checks)."""
    layers = build_log.get("layers") or {}
    n_total = len(layers)
    n_done = sum(1 for v in layers.values() if (v or {}).get("status") == "done")
    n_failed = sum(1 for v in layers.values() if (v or {}).get("status") == "failed")

    combined_name = build_log.get("combined_step")
    combined_path = output_dir / combined_name if combined_name else None
    has_combined = bool(combined_path and combined_path.exists())

    fcstd_files = list(output_dir.glob("*.FCStd")) + list(output_dir.glob("*.fcstd"))
    step_files = list(output_dir.glob("*.step")) + list(output_dir.glob("*.stp"))
    has_fcstd = len(fcstd_files) > 0
    has_any_step = len(step_files) > 0 or has_combined

    preprocess = build_log.get("preprocess") or {}

    kpi_values = {
        "kpi_layers_total": n_total,
        "kpi_layers_done": n_done,
        "kpi_layers_failed": n_failed,
        "kpi_has_combined_step": bool(has_combined),
        "kpi_has_any_step": bool(has_any_step),
        "kpi_has_fcstd": bool(has_fcstd),
        "kpi_has_parametric_fcstd": bool(has_fcstd and n_done > 0),
        "kpi_multiview_reconstruction": bool(build_log.get("multiview_reconstruction") or build_log.get("manual_reconstruction")),
        "kpi_dropped_annotations": int(preprocess.get("dropped_annotation", 0)),
        "kpi_dropped_blocks": int(preprocess.get("dropped_block_insert", 0)),
    }

    failed: list[str] = []
    if n_total == 0 and not has_any_step:
        failed.append("no_layers_processed")
    if not has_any_step:
        failed.append("no_step_output")
    if n_failed > 0 and n_done == 0 and not has_any_step:
        failed.append("all_layers_failed")

    if has_any_step or has_combined or n_done > 0:
        status = "SUCCESS"
    else:
        status = "FAILED"

    return status, kpi_values, failed


def record_job(
    job_id: str,
    input_path: str,
    output_dir: str | Path,
    build_log: dict | None = None,
    source: str = "dxf2step_worker",
    skip_if_exists: bool = True,
) -> int | None:
    """Insert one growth_records row for a DXF2STEP job. Returns row id or None if skipped."""
    output_dir = Path(output_dir)
    log_path = output_dir / "build_log.json"
    if build_log is None:
        if not log_path.exists():
            return None
        build_log = json.loads(log_path.read_text(encoding="utf-8"))

    status, kpi_values, failed_checks = evaluate_outputs(output_dir, build_log)

    artifact = ""
    if build_log.get("combined_step"):
        p = output_dir / build_log["combined_step"]
        if p.exists():
            artifact = str(p)
    if not artifact:
        for pat in ("combined.step", "combined.STEP"):
            p = output_dir / pat
            if p.exists():
                artifact = str(p)
                break
    if not artifact:
        steps = sorted(output_dir.glob("*.step"))
        if steps:
            artifact = str(steps[0])

    challenge = f"DXF2STEP job {job_id}: {os.path.basename(input_path)}"
    if failed_checks:
        know_how = "FAIL: " + "; ".join(failed_checks[:8])
    else:
        know_how = f"OK layers={kpi_values['kpi_layers_done']}/{kpi_values['kpi_layers_total']} combined={kpi_values['kpi_has_combined_step']}"

    evidence = {
        "job_id": job_id,
        "input_path": input_path,
        "output_dir": str(output_dir),
        "kpi_values": kpi_values,
        "failed_checks": failed_checks,
        "build_log": build_log,
        "layer_summary": {
            k: {"status": (v or {}).get("status"), "entities": (v or {}).get("entities")}
            for k, v in (build_log.get("layers") or {}).items()
        },
    }

    DB_FILE.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_FILE), timeout=5.0)
    try:
        conn.execute("PRAGMA busy_timeout=5000")
        _ensure_schema(conn)
        if skip_if_exists and _job_already_recorded(conn, job_id):
            return None
        cur = conn.execute(
            "INSERT INTO growth_records (domain, challenge, status, know_how, artifact_path, difficulty, evidence, source) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                DOMAIN,
                challenge,
                status,
                know_how,
                artifact,
                None,
                json.dumps(evidence, ensure_ascii=False),
                source,
            ),
        )
        conn.commit()
        row_id = int(cur.lastrowid)
        refresh_dashboard_stats()
        return row_id
    finally:
        conn.close()


def refresh_dashboard_stats() -> None:
    """Regenerate growth_stats.json for the portal dashboard."""
    try:
        ws = Path(__file__).resolve().parents[2]
        import sys
        if str(ws) not in sys.path:
            sys.path.insert(0, str(ws))
        from universal_growth_daemon import export_stats_json
        export_stats_json()
    except Exception:
        pass


def import_historical_jobs(jobs_dir: Path | None = None, limit: int | None = None) -> dict:
    """Import jobs/*/output/build_log.json into universal_growth.db."""
    jobs_dir = jobs_dir or JOBS_DIR
    stats = {"scanned": 0, "imported": 0, "skipped": 0, "errors": 0}
    logs = sorted(jobs_dir.glob("*/output/build_log.json"))
    if limit is not None:
        logs = logs[: int(limit)]

    for log_path in logs:
        stats["scanned"] += 1
        job_id = log_path.parent.parent.name
        output_dir = log_path.parent
        input_dir = log_path.parent.parent / "input"
        input_files = list(input_dir.glob("*.dxf")) + list(input_dir.glob("*.DXF")) if input_dir.exists() else []
        input_path = str(input_files[0]) if input_files else ""

        try:
            build_log = json.loads(log_path.read_text(encoding="utf-8"))
            rid = record_job(job_id, input_path, output_dir, build_log, source="dxf2step_import", skip_if_exists=True)
            if rid is None:
                stats["skipped"] += 1
            else:
                stats["imported"] += 1
        except Exception:
            stats["errors"] += 1
    return stats


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Import dxf2step build logs into universal_growth.db")
    parser.add_argument("--jobs-dir", default=str(JOBS_DIR))
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()
    stats = import_historical_jobs(Path(args.jobs_dir), limit=args.limit)
    print(json.dumps(stats, ensure_ascii=False))
