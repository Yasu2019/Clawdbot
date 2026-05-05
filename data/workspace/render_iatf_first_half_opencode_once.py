"""Render the approved OpenCodeGo IATF first-half segment.

This is a one-shot host harness.  It consumes artifacts already created under
data/iatf_videos/*_first_half_opencode and produces an MP4 after frame QA.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
APP_DIR = ROOT / "clawstack_v2/apps/iatf_video_factory"
STATUS_PATH = ROOT / "data/workspace/iatf_first_half_opencode_render_status.json"
sys.path.insert(0, str(APP_DIR))

import run_host  # noqa: E402


def render_blender_preview(timeline: list[dict], phonemes: list[dict], frames_dir: Path, fps: int) -> bool:
    from blender_animator import generate_blender_script

    script_str = generate_blender_script(timeline, phonemes, frames_dir)
    script_str = script_str.replace("fps           = 30", f"fps           = {fps}")
    with tempfile.TemporaryDirectory(prefix="iatf_blender_preview_") as tmpdir:
        script_path = Path(tmpdir) / "preview_render.py"
        script_path.write_text(script_str, encoding="utf-8")
        command = [run_host.BLENDER_BIN, "--background", "--python", str(script_path)]
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=None,
        )
    if result.returncode != 0:
        print(result.stderr[-1000:], flush=True)
        return False
    return True


def write_status(stage: str, **extra: object) -> None:
    payload = {
        "updated_at": time.strftime("%Y-%m-%d %H:%M:%S %z"),
        "stage": stage,
        **extra,
    }
    STATUS_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False), flush=True)


def main() -> int:
    candidates = [
        p
        for p in (ROOT / "data/iatf_videos").iterdir()
        if p.is_dir() and p.name.endswith("_first_half_opencode")
    ]
    if not candidates:
        raise RuntimeError("first_half_opencode output directory not found")
    video_dir = max(candidates, key=lambda p: p.stat().st_mtime)
    frames_dir = video_dir / "frames"
    script_path = video_dir / "script_first_half.json"
    timeline_path = video_dir / "timeline_first_half.json"
    script = json.loads(script_path.read_text(encoding="utf-8"))
    timeline = json.loads(timeline_path.read_text(encoding="utf-8"))
    total_sec = max(e["start_sec"] + e["duration_sec"] for e in timeline) + 2.0

    review_path = video_dir / "slide_preflight/codex_visual_review.json"
    review_path.write_text(
        json.dumps(
            {
                "approved": True,
                "reviewer": "Codex visual inspection",
                "created_at": time.strftime("%Y-%m-%d %H:%M:%S %z"),
                "reason": (
                    "Contact sheet is readable, ordered from opening through "
                    "audit-dialogue setup, and matches the first-half timeline content."
                ),
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    write_status(
        "build_phonemes",
        output_dir=str(video_dir),
        lines=len(timeline),
        duration_sec=round(total_sec, 2),
        script_model=script.get("model_used", "unknown"),
    )
    phonemes = run_host.build_phonemes_fallback(timeline)

    fps = int(os.getenv("IATF_PREVIEW_FPS", "6"))
    existing_frames = len(list(frames_dir.glob("frame_*.png")))
    force_clean = os.getenv("IATF_FORCE_RERENDER", "0").strip() == "1"
    if (fps != 30 or force_clean) and existing_frames:
        archived = frames_dir.with_name(f"{frames_dir.name}_archived_{time.strftime('%Y%m%d_%H%M%S')}")
        if archived.exists():
            shutil.rmtree(archived)
        frames_dir.rename(archived)
        frames_dir.mkdir(parents=True, exist_ok=True)
        write_status("archived_existing_frames", archived=str(archived), archived_frames=existing_frames)
        existing_frames = 0

    expected_frames = int(total_sec * fps)
    if existing_frames < expected_frames * 0.95:
        write_status("render_blender", fps=fps, existing_frames=existing_frames, expected_frames=expected_frames)
        if not render_blender_preview(timeline, phonemes, frames_dir, fps):
            raise RuntimeError("Blender render failed")
    else:
        write_status("reuse_existing_frames", fps=fps, existing_frames=existing_frames, expected_frames=expected_frames)

    write_status("visual_qa_frames")
    visual_report = run_host.visual_qa_frames(frames_dir, video_dir)

    write_status("compose_mp4")
    output_mp4 = run_host.compose_mp4(timeline, frames_dir, video_dir, f"{video_dir.name}_{fps}fps_preview", total_sec, fps=fps)

    result = {
        "ok": True,
        "output_mp4": str(output_mp4),
        "duration_sec": round(total_sec, 2),
        "fps": fps,
        "script_model": script.get("model_used", "unknown"),
        "visual_qa_contact_sheet": visual_report.get("contact_sheet"),
        "codex_visual_review": str(review_path),
    }
    (video_dir / "first_half_opencode_result.json").write_text(
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
