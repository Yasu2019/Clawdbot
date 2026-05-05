#!/usr/bin/env python3
"""ComfyUI API submit stub.
This does not submit by default. It prints the payload path and reminds the operator to verify node IDs.
"""
import argparse, json
from pathlib import Path

if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--workflow', default='comfyui_workflows/ltx23_3pass_v2v_template.json')
    ap.add_argument('--submit', action='store_true')
    args = ap.parse_args()
    wf = Path(args.workflow)
    if not wf.exists():
        raise SystemExit(f"Workflow not found: {wf}")
    data = json.loads(wf.read_text(encoding='utf-8'))
    if not args.submit:
        print("Dry run only. Verify ComfyUI node IDs, model filenames, and license before submit.")
        print(json.dumps({"workflow": str(wf), "status": "dry_run", "ue5_allowed": False}, ensure_ascii=False, indent=2))
    else:
        raise SystemExit("Submission intentionally disabled in this template. Implement after environment verification.")
