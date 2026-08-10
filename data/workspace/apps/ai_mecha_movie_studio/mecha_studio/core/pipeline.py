# -*- coding: utf-8 -*-
from __future__ import annotations
from pathlib import Path
from .jsonio import load_json, save_json
from ..adapters import ffmpeg


def recommend_route(project: dict):
    has_fbx = bool(project.get("inputs", {}).get("model_3d"))
    has_image = bool(project.get("inputs", {}).get("character_image"))
    has_drive = bool(project.get("inputs", {}).get("driving_video"))
    precision = project.get("preferences", {}).get("motion_precision", "auto")
    if has_image and has_drive and precision != "high_3d":
        return "scail2_fast_2d"
    if has_fbx:
        return "precise_3d"
    if has_image:
        return "image_to_3d_then_motion"
    return "manual_input_required"


def run_smoke(project_dir: Path):
    project = load_json(project_dir / "project.json", {})
    route = recommend_route(project)
    report = {"route": route, "steps": [], "status": "ok"}
    report["steps"].append({"stage": "route", "result": route})
    if ffmpeg.available():
        out = project_dir / "output" / "smoke_test.mp4"
        ffmpeg.make_smoke_video(out, 5)
        report["steps"].append({"stage": "ffmpeg", "result": str(out)})
    else:
        report["steps"].append({"stage": "ffmpeg", "result": "not_found"})
    save_json(project_dir / "logs" / "smoke_report.json", report)
    return report
