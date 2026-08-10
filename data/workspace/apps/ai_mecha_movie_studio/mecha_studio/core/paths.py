# -*- coding: utf-8 -*-
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WORKSPACE = ROOT / "workspace"
CONFIG_DIR = ROOT / "config"
PRESETS_DIR = ROOT / "presets"
WORKFLOWS_DIR = ROOT / "workflows"
REMOTION_TEMPLATE = ROOT / "remotion_template"

for p in (WORKSPACE, CONFIG_DIR, PRESETS_DIR, WORKFLOWS_DIR):
    p.mkdir(parents=True, exist_ok=True)
