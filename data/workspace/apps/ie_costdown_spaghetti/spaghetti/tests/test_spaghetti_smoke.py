#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
cmd = [
    sys.executable,
    str(ROOT / "spaghetti/core/spaghetti_analyzer.py"),
    "--input", str(ROOT / "spaghetti/samples/sample_trace_before.csv"),
    "--layout", str(ROOT / "spaghetti/config/sample_layout.json"),
    "--output", str(ROOT / "spaghetti/reports/test_before")
]
print("RUN:", " ".join(cmd))
subprocess.check_call(cmd)
assert (ROOT / "spaghetti/reports/test_before/spaghetti.png").exists()
assert (ROOT / "spaghetti/reports/test_before/report.md").exists()
print("OK")
