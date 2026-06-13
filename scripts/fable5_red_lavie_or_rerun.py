# -*- coding: utf-8 -*-
"""Recover red_lavie (if reachable) and run press_blanking with part_manifest on red_lavie."""
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
GOLDEN = ROOT / "data" / "workspace" / "thinkpad_dxf2step_history" / "tp-dxf-44920df6" / "part_manifest.json"
RUNS = ROOT / "data" / "cae_te_workspace" / "runs"

if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

import cae_workload_router as router
import k10_red_lavie_auto_recovery as red_recovery
import k10_satellite_cae_dispatch as cae_dispatch
import k10_satellite_dispatch as sjp


def _now() -> str:
    return datetime.now(JST).isoformat()


def probe_red_lavie(cfg: dict[str, Any]) -> dict[str, Any]:
    node = sjp.load_node("red_lavie")
    url = sjp.worker_base_url(node)
    try:
        token = sjp.load_token()
        ok, detail = sjp.probe_worker(url, token)
        return {"online": ok, "url": url, "detail": (detail or "")[:300]}
    except Exception as exc:
        return {"online": False, "url": url, "detail": str(exc)[:300]}


def run_press_blanking_on_red(
    manifest_path: Path,
    *,
    timeout: int,
    dry_run: bool,
    try_recovery: bool,
) -> dict[str, Any]:
    cfg = router.load_config()
    report: dict[str, Any] = {
        "schema": "clawstack.fable5_red_lavie_or_rerun.v1",
        "started_at": _now(),
        "manifest_path": str(manifest_path.resolve()),
        "dry_run": dry_run,
    }

    probe = probe_red_lavie(cfg)
    report["probe_before"] = probe

    if not probe.get("online") and try_recovery:
        report["recovery"] = red_recovery.run_full_recovery(skip_power=False)
        probe = probe_red_lavie(cfg)
        report["probe_after_recovery"] = probe

    if not probe.get("online"):
        report["overall_ok"] = False
        report["overall_verdict"] = "RED_LAVIE_OFFLINE"
        report["message"] = "red_lavie unreachable; run when node is online on Tailscale"
        report["finished_at"] = _now()
        return report

    inline: dict | None = None
    try:
        loaded = json.loads(manifest_path.read_text(encoding="utf-8"))
        if isinstance(loaded, dict):
            inline = loaded
    except Exception:
        pass

    params: dict[str, Any] = {
        "part_manifest_path": str(manifest_path.resolve()),
        "part_manifest_loaded": True,
    }
    if inline:
        params["part_manifest"] = inline

    trial_id = f"RED-OR-{uuid.uuid4().hex[:8]}"
    token = sjp.load_token()
    bundle = cae_dispatch.run_lavie_trial(
        node="red_lavie",
        category="press_blanking",
        params=params,
        trial_id=trial_id,
        dry_run=dry_run,
        timeout=timeout,
        token=token,
        cfg=cfg,
    )
    entry = bundle.get("trial_entry") or {}
    verdict = str(entry.get("verdict") or "ERROR").upper()
    ok = verdict in ("SUCCESS", "PASS", "OK", "DRY_RUN")

    report["trial_id"] = trial_id
    report["host"] = "red_lavie"
    report["trial_entry"] = {
        k: entry.get(k)
        for k in ("verdict", "geometry_source", "duration_sec", "returncode", "host", "error")
        if k in entry
    }
    report["overall_ok"] = ok
    report["overall_verdict"] = verdict if ok else "FAILED"
    report["finished_at"] = _now()
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Red LAVIE recovery + OpenRadioss press_blanking rerun")
    parser.add_argument("--part-manifest", default=str(GOLDEN.relative_to(ROOT)))
    parser.add_argument("--timeout", type=int, default=900)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--no-recovery", action="store_true", help="Skip auto-recovery attempt")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    manifest_path = Path(args.part_manifest)
    if not manifest_path.is_absolute():
        manifest_path = (ROOT / manifest_path).resolve()
    if not manifest_path.exists():
        print(f"[NG] manifest missing: {manifest_path}", file=sys.stderr)
        return 1

    report = run_press_blanking_on_red(
        manifest_path,
        timeout=args.timeout,
        dry_run=args.dry_run,
        try_recovery=not args.no_recovery,
    )

    run_id = f"red_lavie_or_{datetime.now(JST).strftime('%Y%m%d_%H%M%S')}"
    out_dir = RUNS / run_id
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "red_lavie_or_report.json"
    out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    report["report_path"] = str(out_path)

    if args.json or True:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report.get("overall_ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
