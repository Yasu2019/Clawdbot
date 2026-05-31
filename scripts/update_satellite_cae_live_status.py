# -*- coding: utf-8 -*-
"""Aggregate satellite CAE live status for Portal (SJP-2)."""
from __future__ import annotations

import argparse
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
OUT = ROOT / "data" / "workspace" / "satellite_cae_live_status.json"
TE_LOG = ROOT / "data" / "cae_te_workspace" / "results" / "cae_te_log.json"
PARALLEL_LOG = ROOT / "data" / "workspace" / "parallel_cae_log.jsonl"
CAE_ENGINE_STATUS = ROOT / "data" / "state" / "cae_te_engine" / "status.json"
JST = timezone(timedelta(hours=9))

if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

import cae_workload_router as router


def tail_jsonl(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    last = ""
    for line in path.read_text(encoding="utf-8-sig", errors="replace").splitlines():
        if line.strip():
            last = line.strip()
    if not last:
        return None
    try:
        return json.loads(last)
    except json.JSONDecodeError:
        return None


def recent_trials_by_host(limit: int = 10) -> dict[str, int]:
    if not TE_LOG.exists():
        return {}
    data = json.loads(TE_LOG.read_text(encoding="utf-8-sig"))
    counts: dict[str, int] = {}
    for trial in (data.get("trials") or [])[:limit]:
        host = trial.get("host") or "k10"
        counts[host] = counts.get(host, 0) + 1
    return counts


def build_status() -> dict[str, Any]:
    cfg = router.load_config()
    lavie_ok, lavie_detail = router.probe_lavie_job_worker(cfg)
    busy, busy_reason = router.k10_cae_busy(cfg)
    resin_decision = router.pick_host("resin_flow", cfg)
    blank_decision = router.pick_host("press_blanking", cfg)

    engine_status: dict[str, Any] = {}
    if CAE_ENGINE_STATUS.exists():
        try:
            engine_status = json.loads(CAE_ENGINE_STATUS.read_text(encoding="utf-8-sig"))
        except Exception:
            pass

    te_summary: dict[str, Any] = {}
    if TE_LOG.exists():
        try:
            te_summary = json.loads(TE_LOG.read_text(encoding="utf-8-sig")).get("summary") or {}
        except Exception:
            pass

    parallel_last = tail_jsonl(PARALLEL_LOG)
    latest_trials = []
    if TE_LOG.exists():
        try:
            trials = json.loads(TE_LOG.read_text(encoding="utf-8-sig")).get("trials") or []
            for t in trials[:5]:
                latest_trials.append(
                    {
                        "id": t.get("id"),
                        "category": t.get("category"),
                        "verdict": t.get("verdict"),
                        "host": t.get("host", "k10"),
                    }
                )
        except Exception:
            pass

    overall = "ok"
    issues: list[str] = []
    if not lavie_ok:
        overall = "critical"
        issues.append(f"lavie worker offline: {lavie_detail}")
    elif not cfg.get("cae_workspace_sync", {}).get("enabled"):
        overall = "warning"
        issues.append("cae_workspace_sync disabled in router")

    return {
        "updated_at": datetime.now(JST).isoformat(),
        "overall": overall,
        "issues": issues,
        "lavie": {
            "online": lavie_ok,
            "probe": lavie_detail,
            "ip": (cfg.get("lavie") or {}).get("ip"),
            "job_worker_port": (cfg.get("lavie") or {}).get("job_worker_port", 5680),
        },
        "k10": {
            "cae_busy": busy,
            "busy_reason": busy_reason,
            "engine_status": engine_status,
        },
        "routing": {
            "resin_flow": resin_decision,
            "press_blanking": blank_decision,
        },
        "cae_te_log_summary": te_summary,
        "recent_trials_by_host": recent_trials_by_host(20),
        "latest_trials": latest_trials,
        "parallel_last": parallel_last,
        "runbook": "docs/SATELLITE_CAE_ONE_SHOT_RUNBOOK.md",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Update satellite CAE live status JSON")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    status = build_status()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    tmp = OUT.with_suffix(".tmp")
    tmp.write_text(json.dumps(status, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(OUT)

    if args.json:
        print(json.dumps(status, ensure_ascii=False, indent=2))
    else:
        print(f"[OK] wrote {OUT} overall={status['overall']} lavie_online={status['lavie']['online']}")
    return 0 if status["overall"] != "critical" else 1


if __name__ == "__main__":
    raise SystemExit(main())
