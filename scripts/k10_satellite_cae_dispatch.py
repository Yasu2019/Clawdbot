# -*- coding: utf-8 -*-
"""K10 CAE trial orchestrator: route to K10 local or LAVIE satellite (SJP-2)."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
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
REGISTRY_DIR = ROOT / "data" / "workspace"
TE_LOG = ROOT / "data" / "cae_te_workspace" / "results" / "cae_te_log.json"
CAE_LOG = REGISTRY_DIR / "satellite_cae_log.jsonl"
JST = timezone(timedelta(hours=9))

if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

import cae_workload_router as router
import k10_satellite_dispatch as sjp


def merge_trial_into_log(trial_entry: dict[str, Any]) -> None:
    te_log_path = TE_LOG
    te_log_path.parent.mkdir(parents=True, exist_ok=True)
    if te_log_path.exists():
        te_log = json.loads(te_log_path.read_text(encoding="utf-8-sig"))
    else:
        te_log = {"trials": [], "summary": {}}

    te_log["trials"].insert(0, trial_entry)
    te_log["trials"] = te_log["trials"][:500]
    te_log["summary"] = {
        "total_trials": len(te_log["trials"]),
        "success": sum(1 for t in te_log["trials"] if t.get("verdict") == "SUCCESS"),
        "failed": sum(1 for t in te_log["trials"] if t.get("verdict") == "FAILED"),
        "success_rate_pct": 0,
        "last_updated": datetime.now(JST).isoformat(),
    }
    total = te_log["summary"]["total_trials"]
    if total > 0:
        te_log["summary"]["success_rate_pct"] = round(
            te_log["summary"]["success"] / total * 100, 1
        )
    tmp = te_log_path.with_suffix(".tmp")
    tmp.write_text(json.dumps(te_log, ensure_ascii=False, indent=2), encoding="utf-8")
    for attempt in range(8):
        try:
            tmp.replace(te_log_path)
            break
        except PermissionError:
            if attempt >= 7:
                raise
            time.sleep(0.3 + attempt * 0.1)
            te_log = json.loads(te_log_path.read_text(encoding="utf-8-sig"))
            te_log["trials"].insert(0, trial_entry)
            te_log["trials"] = te_log["trials"][:500]
            tmp.write_text(json.dumps(te_log, ensure_ascii=False, indent=2), encoding="utf-8")


def append_cae_log(entry: dict[str, Any]) -> None:
    REGISTRY_DIR.mkdir(parents=True, exist_ok=True)
    entry = dict(entry)
    entry["logged_at"] = datetime.now(JST).isoformat()
    with CAE_LOG.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry, ensure_ascii=False) + "\n")


def run_local_trial(
    *,
    category: str,
    params: dict | None,
    trial_id: str,
    dry_run: bool,
    timeout: int,
) -> dict[str, Any]:
    cmd = [
        sys.executable,
        str(ROOT / "scripts" / "cae_te_remote_trial.py"),
        "--category",
        category,
        "--host",
        "k10",
        "--timeout",
        str(timeout),
        "--no-append-log",
    ]
    if trial_id:
        cmd.extend(["--trial-id", trial_id])
    if dry_run:
        cmd.append("--dry-run")
    if params:
        cmd.extend(["--params-json", json.dumps(params, ensure_ascii=False)])

    proc = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=timeout + 60,
        encoding="utf-8",
        errors="replace",
        cwd=str(ROOT),
    )
    if proc.returncode != 0 and not proc.stdout.strip():
        return {
            "verdict": "ERROR",
            "error": proc.stderr[-2000:] or f"exit {proc.returncode}",
            "host": "k10",
        }
    last_line = proc.stdout.strip().splitlines()[-1]
    return json.loads(last_line)


def run_lavie_trial(
    *,
    node: str,
    category: str,
    params: dict | None,
    trial_id: str,
    dry_run: bool,
    timeout: int,
    token: str,
    cfg: dict[str, Any],
) -> dict[str, Any]:
    sync_cfg = cfg.get("cae_workspace_sync") or {}
    workspace = sync_cfg.get("lavie_work_dir") or "E:/clawstack_satellite/data/work/cae_te_workspace"
    repo_root = sync_cfg.get("lavie_repo_root") or "C:/lavie_usb_pack"

    payload: dict[str, Any] = {
        "category": category,
        "dry_run": dry_run,
        "timeout_sec": timeout,
        "workspace_root": workspace,
        "repo_root": repo_root,
    }
    if params:
        payload["params"] = params
    if trial_id:
        payload["trial_id"] = trial_id

    job = {
        "job_id": trial_id or f"{node}-cae-{uuid.uuid4().hex[:8]}",
        "type": "cae_trial",
        "timeout_sec": timeout + 120,
        "payload": payload,
        "report": {"mode": "sync"},
    }

    node_info = sjp.load_node(node)
    base_url = sjp.worker_base_url(node_info)
    result = sjp.dispatch_job(base_url, token, job, timeout)
    trial_entry = (result.get("metrics") or {}).get("cae_trial")
    if not trial_entry and result.get("status") == "ok":
        trial_entry = result.get("metrics", {}).get("trial_entry")
    if not trial_entry:
        trial_entry = {
            "verdict": "ERROR",
            "error": result.get("error") or "missing cae_trial metrics",
            "host": node,
            "worker_result": {k: result.get(k) for k in ("status", "exit_code", "failure_tags")},
        }
    return {"job": job, "worker_result": result, "trial_entry": trial_entry}


def main() -> int:
    parser = argparse.ArgumentParser(description="Dispatch CAE trial (SJP-2)")
    parser.add_argument("--category", required=True, help="CAE category e.g. press_blanking")
    parser.add_argument("--params-json", default="", help="Optional JSON params")
    parser.add_argument("--params-file", default="")
    parser.add_argument("--trial-id", default="")
    parser.add_argument("--node", default="lavie", help="Satellite node when routed to lavie")
    parser.add_argument("--host", default="", choices=["", "k10", "lavie"], help="Force host")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--timeout", type=int, default=600)
    parser.add_argument("--no-merge-log", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    params: dict | None = None
    if args.params_file:
        params = json.loads(Path(args.params_file).read_text(encoding="utf-8-sig"))
    elif args.params_json:
        params = json.loads(args.params_json)

    cfg = router.load_config()
    if args.host:
        decision = {"host": args.host, "reason": "forced", "category": args.category}
    else:
        decision = router.pick_host(args.category, cfg)

    trial_id = args.trial_id or f"cae-{args.category}-{uuid.uuid4().hex[:8]}"
    print(f"[cae-dispatch] category={args.category} host={decision['host']} reason={decision.get('reason')}")

    try:
        if decision["host"] == "lavie":
            token = sjp.load_token()
            bundle = run_lavie_trial(
                node=args.node,
                category=args.category,
                params=params,
                trial_id=trial_id,
                dry_run=args.dry_run,
                timeout=args.timeout,
                token=token,
                cfg=cfg,
            )
            trial_entry = bundle["trial_entry"]
            trial_entry.setdefault("host", "lavie")
            worker_result = bundle["worker_result"]
        else:
            trial_entry = run_local_trial(
                category=args.category,
                params=params,
                trial_id=trial_id,
                dry_run=args.dry_run,
                timeout=args.timeout,
            )
            trial_entry.setdefault("host", "k10")
            worker_result = {"status": "ok", "local": True}

        if not args.no_merge_log and trial_entry.get("id"):
            merge_trial_into_log(trial_entry)

        log_entry = {
            "category": args.category,
            "decision": decision,
            "trial_id": trial_id,
            "trial_entry": trial_entry,
            "dry_run": args.dry_run,
        }
        append_cae_log(log_entry)

        out = {
            "decision": decision,
            "trial_entry": trial_entry,
            "worker_result_status": worker_result.get("status"),
            "te_log": str(TE_LOG),
            "cae_log": str(CAE_LOG),
        }
        if args.json:
            print(json.dumps(out, ensure_ascii=False, indent=2))
        else:
            print(f"verdict={trial_entry.get('verdict')} host={trial_entry.get('host')}")
            print(f"te_log: {TE_LOG}")

        verdict = trial_entry.get("verdict", "ERROR")
        ok = verdict in {"SUCCESS", "DRY_RUN", "FAILED", "SKIPPED", "PREGATE_FAIL"}
        if args.dry_run and decision.get("host") == "lavie" and trial_entry.get("host") == "lavie":
            ok = True
        print(f"\nRESULT: {'PASS' if ok else 'FAIL'}")
        return 0 if ok else 1
    except Exception as exc:
        print(f"[NG] {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
