"""One-shot host harness for first-half IATF video generation.

This intentionally lives outside the app code.  It reuses the existing
iatf_video_factory pipeline, writes artifacts under data/iatf_videos, and
does not change Docker, Rails, or database schema.
"""

from __future__ import annotations

import json
import math
import os
import sys
import time
from copy import deepcopy
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
APP_DIR = ROOT / "clawstack_v2/apps/iatf_video_factory"
STATUS_PATH = ROOT / "data/workspace/iatf_first_half_video_status.json"
sys.path.insert(0, str(APP_DIR))

import run_host  # noqa: E402


def write_status(stage: str, **extra: object) -> None:
    payload = {
        "updated_at": time.strftime("%Y-%m-%d %H:%M:%S %z"),
        "stage": stage,
        **extra,
    }
    STATUS_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False), flush=True)


def first_half_script(script: dict) -> dict:
    lines = []
    for scene_index, scene in enumerate(script.get("scenes", [])):
        for line_index, line in enumerate(scene.get("lines", [])):
            lines.append((scene_index, line_index, line))

    if not lines:
        raise RuntimeError("script has no dialogue lines")

    keep_count = max(1, math.ceil(len(lines) / 2))
    keep_by_scene: dict[int, set[int]] = {}
    for scene_index, line_index, _line in lines[:keep_count]:
        keep_by_scene.setdefault(scene_index, set()).add(line_index)

    partial = deepcopy(script)
    partial["source_model_used"] = script.get("model_used", "unknown")
    partial["segment"] = "first_half"
    partial["model_used"] = script.get("model_used", "unknown")
    new_scenes = []
    for scene_index, scene in enumerate(script.get("scenes", [])):
        keep_indexes = keep_by_scene.get(scene_index, set())
        if not keep_indexes:
            continue
        new_scene = deepcopy(scene)
        new_scene["lines"] = [
            deepcopy(line)
            for line_index, line in enumerate(scene.get("lines", []))
            if line_index in keep_indexes
        ]
        if new_scene["lines"]:
            new_scene["duration_sec"] = sum(float(line.get("duration_sec", 0) or 0) for line in new_scene["lines"])
            new_scenes.append(new_scene)
    partial["scenes"] = new_scenes
    partial["total_duration_sec"] = sum(float(scene.get("duration_sec", 0) or 0) for scene in new_scenes)
    return partial


def main() -> int:
    os.environ.setdefault("IATF_VIDEO_SLIDE_REVIEW_MODE", "local_only")

    pdfs = run_host.list_pending(1)
    if not pdfs:
        raise RuntimeError("no pending IATF PDFs found")

    pdf_path = pdfs[0]
    stem = pdf_path.stem
    out_stem = f"{stem}_first_half"
    video_dir = run_host.OUTPUT_DIR / out_stem
    frames_dir = video_dir / "frames"
    audio_dir = run_host.AUDIO_DIR / out_stem
    video_dir.mkdir(parents=True, exist_ok=True)
    frames_dir.mkdir(parents=True, exist_ok=True)
    audio_dir.mkdir(parents=True, exist_ok=True)

    parts = stem.replace("箇条", "").split("_")
    clause = parts[1].strip() if len(parts) > 1 else "?"
    topic = parts[2].strip() if len(parts) > 2 else stem

    write_status("start", pdf=str(pdf_path), output_dir=str(video_dir))

    script_path = video_dir / "script_full.json"
    partial_script_path = video_dir / "script_first_half.json"
    timeline_path = video_dir / "timeline_first_half.json"

    if partial_script_path.exists() and timeline_path.exists():
        write_status("resume_script_audio", pdf=str(pdf_path))
        script = json.loads(partial_script_path.read_text(encoding="utf-8"))
        timeline = json.loads(timeline_path.read_text(encoding="utf-8"))
    else:
        write_status("extract_pdf", pdf=str(pdf_path))
        pdf_text = run_host.extract_pdf(pdf_path)

        write_status("generate_script_opencode_go", chars=len(pdf_text), clause=clause, topic=topic)
        full_script = run_host.generate_script(pdf_text, clause, topic)
        script_path.write_text(json.dumps(full_script, ensure_ascii=False, indent=2), encoding="utf-8")

        script = first_half_script(full_script)
        partial_script_path.write_text(json.dumps(script, ensure_ascii=False, indent=2), encoding="utf-8")

        write_status(
            "render_voicevox",
            model=script.get("model_used", "unknown"),
            scenes=len(script.get("scenes", [])),
        )
        timeline = run_host.render_audio(script, audio_dir)
        timeline_path.write_text(json.dumps(timeline, ensure_ascii=False, indent=2), encoding="utf-8")

    total_sec = max(e["start_sec"] + e["duration_sec"] for e in timeline) + 2.0
    write_status("slide_preflight", lines=len(timeline), duration_sec=round(total_sec, 2))
    preflight = run_host.slide_preflight_gate(script, timeline, video_dir, out_stem)

    write_status(
        "awaiting_codex_visual_review",
        contact_sheet=preflight["contact_sheet"],
        note="Manual Codex visual inspection must approve this contact sheet before Blender generation.",
    )

    # The caller inspects the contact sheet before rerunning with this flag.
    if os.getenv("IATF_FIRST_HALF_VISUAL_APPROVED", "").strip() != "1":
        return 2

    write_status("build_phonemes", duration_sec=round(total_sec, 2))
    phonemes = run_host.build_phonemes_fallback(timeline)

    existing_frames = len(list(frames_dir.glob("frame_*.png")))
    expected_frames = int(total_sec * 30)
    if existing_frames < expected_frames * 0.95:
        write_status("render_blender", existing_frames=existing_frames, expected_frames=expected_frames)
        if not run_host.render_blender(timeline, phonemes, frames_dir):
            raise RuntimeError("Blender render failed")
    else:
        write_status("reuse_existing_frames", existing_frames=existing_frames, expected_frames=expected_frames)

    write_status("visual_qa_frames")
    visual_report = run_host.visual_qa_frames(frames_dir, video_dir)

    write_status("compose_mp4")
    output_mp4 = run_host.compose_mp4(timeline, frames_dir, video_dir, out_stem, total_sec)

    result = {
        "ok": True,
        "pdf": str(pdf_path),
        "output_mp4": str(output_mp4),
        "duration_sec": round(total_sec, 2),
        "script_model": script.get("model_used", "unknown"),
        "slide_contact_sheet": preflight["contact_sheet"],
        "visual_qa_contact_sheet": visual_report.get("contact_sheet"),
    }
    (video_dir / "first_half_result.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    write_status("done", **result)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        write_status("error", error=str(exc))
        raise
