# -*- coding: utf-8 -*-
"""Probe Fable5 fleet nodes (K10 orchestrator view). Writes JSON summary."""
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
JST = timezone(timedelta(hours=9))
OUT = ROOT / "data" / "workspace" / "fable5_fleet_health.json"

if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

import cae_workload_router as router
import k10_satellite_dispatch as sjp


def _probe_node(node_id: str, token: str) -> dict[str, Any]:
    try:
        node = sjp.load_node(node_id)
        url = sjp.worker_base_url(node)
        ok, detail = sjp.probe_worker(url, token)
        return {"node": node_id, "url": url, "ok": ok, "detail": (detail or "")[:200]}
    except Exception as exc:
        return {"node": node_id, "ok": False, "error": str(exc)[:200]}


def main() -> int:
    parser = argparse.ArgumentParser(description="Fable5 fleet health probe")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--write", action="store_true", help="Write data/workspace/fable5_fleet_health.json")
    args = parser.parse_args()

    token = sjp.load_token()
    cfg = router.load_config()
    nodes = ["lavie", "red_lavie", "thinkpad"]
    probes = [_probe_node(n, token) for n in nodes]
    or_route = router.pick_host("press_blanking", cfg)
    mf_route = router.pick_host("resin_fill_cad", cfg)

    report: dict[str, Any] = {
        "schema": "clawstack.fable5_fleet_health.v1",
        "checked_at": datetime.now(JST).isoformat(),
        "probes": probes,
        "router": {
            "press_blanking": {"host": or_route.get("host"), "reason": or_route.get("reason")},
            "resin_fill_cad": {"host": mf_route.get("host"), "reason": mf_route.get("reason")},
        },
        "all_satellites_ok": all(p.get("ok") for p in probes if p.get("node") in ("lavie", "red_lavie")),
    }

    if args.write:
        OUT.parent.mkdir(parents=True, exist_ok=True)
        OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        report["written_to"] = str(OUT)

    print(json.dumps(report, ensure_ascii=False, indent=2) if args.json else json.dumps(report, ensure_ascii=False))
    return 0 if report["all_satellites_ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
