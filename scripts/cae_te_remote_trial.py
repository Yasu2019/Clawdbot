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
    parser.add_argument(
        "--no-cleanup-runs",
        action="store_true",
        help="Do not prune old data/cae_te_workspace/runs directories before this trial",
    )
    parser.add_argument("--skip-resource-check", action="store_true")
    parser.add_argument("--output", default="", help="Write trial JSON to this file")
    parser.add_argument(
        "--capture-paraview-only",
        action="store_true",
        help="Only capture/send ParaView PNG for --trial-id (no solver run)",
    )
    args = parser.parse_args()

    if args.workspace:
        os.environ["CAE_TE_WORKSPACE"] = str(Path(args.workspace).resolve())
    if args.no_cleanup_runs:
        os.environ["CAE_SKIP_RUN_CLEANUP"] = "1"

    if args.capture_paraview_only:
        import cae_te_paraview_capture as pvc

        ws = Path(args.workspace or os.environ.get("CAE_TE_WORKSPACE", ROOT / "data" / "cae_te_workspace"))
        tid = args.trial_id.strip()
        if not tid:
            print(json.dumps({"ok": False, "error": "trial-id required"}, ensure_ascii=False))
            return 1
        trial = pvc.find_trial(trial_id=tid) or {"id": tid}
        run_dir = pvc.resolve_run_dir(trial, ws)
        if not run_dir:
            print(json.dumps({"ok": False, "error": "run_dir not found"}, ensure_ascii=False))
            return 1
        png = pvc.capture_openfoam_run_dir(run_dir, skip_if_exists=False)
        if not png:
            print(json.dumps({"ok": False, "error": "capture_failed"}, ensure_ascii=False))
            return 1
        cap = f"[ParaView] {tid}\nOpenFOAM |U| snapshot"
        sent = pvc.send_png_telegram(png, cap)
        print(json.dumps({"ok": True, "paraview_png": str(png), "telegram_sent": sent}, ensure_ascii=False))
        return 0

    category = (args.category or "").strip()
    params: dict | None = None
    if args.params_file:
        params = json.loads(Path(args.params_file).read_text(encoding="utf-8-sig"))
    elif args.params_json:
        params = json.loads(args.params_json)

    phys = str((params or {}).get("physics_category") or "")
    if category in ("resin_flow", "resin_flow_opt") or category.startswith(
        "resin_fill"
    ) or phys.startswith("resin_fill"):
        os.environ["CAE_PARAVIEW_TELEGRAM"] = "0"
        os.environ["CAE_PARAVIEW_CAPTURE"] = "0"
        # Calibration trials retain scalar histories and fields; rendering a
        # video here adds cost and Windows multiprocessing can re-parse this
        # runner's CLI arguments. Callers may explicitly opt back in.
        os.environ.setdefault("CAE_FILL_VIDEO_TELEGRAM", "0")

    import cae_te_engine as engine

    host = args.host or os.environ.get("SATELLITE_NODE_ID", "k10")
    # Satellites render fill MP4 on K10 (lavie_cae_video_support pull path, INC-089 / T019).
    if str(host).lower() not in ("k10", ""):
        os.environ["CAE_FILL_VIDEO_TELEGRAM"] = "0"
    elif str(host).lower() == "lavie":
        # Back-compat if host label is lavie on K10 local test
        os.environ["CAE_FILL_VIDEO_TELEGRAM"] = "0"
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
