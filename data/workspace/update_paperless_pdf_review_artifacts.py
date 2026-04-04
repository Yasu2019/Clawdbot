#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path


JST = timezone(timedelta(hours=9))
WORKSPACE = Path(__file__).resolve().parent
STATUS_PATH = WORKSPACE / "paperless_pdf_review_artifacts_status.json"
REVIEW_SCRIPT = WORKSPACE / "build_paperless_pdf_review_report.py"
BENCHMARK_SCRIPT = WORKSPACE / "build_paperless_pdf_benchmark.py"


def now_jst_text() -> str:
    return datetime.now(JST).strftime("%Y-%m-%d %H:%M:%S JST")


def run_python(script: Path, args: list[str], timeout_seconds: int) -> dict:
    command = [sys.executable, str(script), *args]
    try:
        proc = subprocess.run(
            command,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout_seconds,
        )
        return {
            "command": " ".join(command),
            "returncode": proc.returncode,
            "stdout": proc.stdout.strip(),
            "stderr": proc.stderr.strip(),
            "timedOut": False,
        }
    except subprocess.TimeoutExpired as exc:
        return {
            "command": " ".join(command),
            "returncode": None,
            "stdout": (exc.stdout or "").strip() if isinstance(exc.stdout, str) else "",
            "stderr": (exc.stderr or "").strip() if isinstance(exc.stderr, str) else "",
            "timedOut": True,
        }


def main() -> None:
    parser = argparse.ArgumentParser(description="Refresh Paperless review artifacts.")
    parser.add_argument("--review-limit", type=int, default=8)
    parser.add_argument("--benchmark-limit", type=int, default=12)
    parser.add_argument("--reason", default="manual")
    args = parser.parse_args()

    review = run_python(REVIEW_SCRIPT, ["--limit", str(args.review_limit)], 300)
    benchmark = run_python(BENCHMARK_SCRIPT, ["--limit", str(args.benchmark_limit)], 120)

    ok = review.get("returncode") == 0 and benchmark.get("returncode") == 0 and not review.get("timedOut") and not benchmark.get("timedOut")
    payload = {
        "updatedAt": now_jst_text(),
        "service": "paperless_pdf_review_artifacts",
        "reason": args.reason,
        "ok": ok,
        "reviewLimit": args.review_limit,
        "benchmarkLimit": args.benchmark_limit,
        "review": review,
        "benchmark": benchmark,
    }
    STATUS_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False))
    raise SystemExit(0 if ok else 1)


if __name__ == "__main__":
    main()
