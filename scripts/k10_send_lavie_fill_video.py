# -*- coding: utf-8 -*-
"""CLI: send LAVIE VOF fill MP4 via K10 pull render (see lavie_cae_video_support)."""

import sys

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

import argparse

import lavie_cae_video_support as lcv


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--trial-id", default="lavie365-resin_fill_cad-live01")
    parser.add_argument("--category", default="resin_fill_cad")
    parser.add_argument("--run-dir", default="")
    args = parser.parse_args()

    result = lcv.send_fill_video_after_success(
        args.trial_id,
        category=args.category,
        run_dir=args.run_dir,
        k10_pull_only=True,
    )
    print(result, flush=True)
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
