# -*- coding: utf-8 -*-
"""Resolve vendor vs live Clawstack engine (portable: vendor wins unless env set)."""
from __future__ import annotations

import os
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


def workbench_root() -> Path:
    return Path(__file__).resolve().parent.parent


def add_engine_paths() -> Path:
    """Prefer CLAWSTACK_CETOL_ROOT/data/workspace, else bundled vendor/."""
    root = workbench_root()
    vendor = root / "vendor"
    env = (os.environ.get("CLAWSTACK_CETOL_ROOT") or "").strip()
    chosen = vendor
    if env:
        live = Path(env) / "data" / "workspace"
        if (live / "cetol_modeler.py").is_file():
            chosen = live
    for p in (chosen, vendor):
        sp = str(p)
        if p.is_dir() and sp not in sys.path:
            sys.path.insert(0, sp)
    return chosen
