# -*- coding: utf-8 -*-
from __future__ import annotations
from datetime import datetime
from pathlib import Path
import shutil
from .paths import WORKSPACE, PRESETS_DIR, REMOTION_TEMPLATE
from .jsonio import load_json, save_json


def create_sample_project(name="sample_mecha_movie"):
    dst = WORKSPACE / name
    dst.mkdir(parents=True, exist_ok=True)
    for sub in ["input", "reference", "clips", "audio/dialogue", "audio/music", "audio/sfx", "output", "logs"]:
        (dst / sub).mkdir(parents=True, exist_ok=True)
    preset = load_json(PRESETS_DIR / "sample_project.json", {})
    preset["project_name"] = name
    preset["created_at"] = datetime.now().isoformat(timespec="seconds")
    save_json(dst / "project.json", preset)
    rdst = dst / "remotion"
    if not rdst.exists():
        shutil.copytree(REMOTION_TEMPLATE, rdst)
    return dst
