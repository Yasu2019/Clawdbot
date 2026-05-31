# -*- coding: utf-8 -*-
"""Run a single CAE T&E trial (local or LAVIE satellite). Outputs JSON for SJP-2."""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

os.environ.setdefault("PGCLIENTENCODING", "UTF8")

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))


def main() -> int:
    parser = argparse.ArgumentParser(description="Single CAE trial runner (SJP-2)")
    parser.add_argument("--category", default="", help="Experiment category")
    parser.add_argument("--exp-id", default="", help="Experiment id (overrides category lookup)")
    parser.add_argument("--trial-id", default="", help="Trial id override")
    parser.add_argument("--params-json", default="", help="JSON object of trial parameters")
    parser.add_argument("--params-file", default="", help="Path to JSON params file")
    parser.add_argument("--workspace", default="", help="CAE_TE_WORKSPACE override")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--timeout", type=int, default=600)
    parser.add_argument("--host", default="", help="Host label for log entry (k10/lavie)")
    parser.add_argument("--no-append-log", action="store_true", help="Do not write cae_te_log.json")
    parser.add_argument("--skip-resource-check", action="store_true")
    parser.add_argument("--output", default="", help="Write trial JSON to this file")
    args = parser.parse_args()

    if args.workspace:
        os.environ["CAE_TE_WORKSPACE"] = str(Path(args.workspace).resolve())

    import cae_te_engine as engine

    params: dict | None = None
    if args.params_file:
        params = json.loads(Path(args.params_file).read_text(encoding="utf-8-sig"))
    elif args.params_json:
        params = json.loads(args.params_json)

    host = args.host or os.environ.get("SATELLITE_NODE_ID", "k10")
    try:
        trial_entry = engine.run_single_trial(
            category=args.category or None,
            exp_id=args.exp_id or None,
            params=params,
            trial_id=args.trial_id or None,
            dry_run=args.dry_run,
            timeout=args.timeout,
            skip_resource_check=args.skip_resource_check,
            append_log=not args.no_append_log,
            host=host,
        )
    except Exception as exc:
        err = {"verdict": "ERROR", "error": str(exc), "host": host}
        print(json.dumps(err, ensure_ascii=False))
        if args.output:
            Path(args.output).write_text(json.dumps(err, ensure_ascii=False, indent=2), encoding="utf-8")
        return 1

    payload = json.dumps(trial_entry, ensure_ascii=False)
    print(payload)
    if args.output:
        out_path = Path(args.output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(trial_entry, ensure_ascii=False, indent=2), encoding="utf-8")

    verdict = trial_entry.get("verdict", "ERROR")
    ok = verdict in {"SUCCESS", "DRY_RUN", "FAILED", "SKIPPED", "PREGATE_FAIL"}
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
