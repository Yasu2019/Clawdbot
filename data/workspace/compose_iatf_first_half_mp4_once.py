"""One-shot: visual QA + MP4 compose for already-rendered first_half_opencode frames.

Skips phoneme / Blender steps entirely.  Use when 1790 frames already exist
but the pipeline stalled at visual QA (T006 ahash bug, now fixed).
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
APP_DIR = ROOT / "clawstack_v2/apps/iatf_video_factory"
STATUS_PATH = ROOT / "data/workspace/iatf_first_half_opencode_render_status.json"
sys.path.insert(0, str(APP_DIR))
import run_host  # noqa: E402


def write_status(stage: str, **extra: object) -> None:
    payload = {"updated_at": time.strftime("%Y-%m-%d %H:%M:%S %z"), "stage": stage, **extra}
    STATUS_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False), flush=True)


def main() -> int:
    candidates = [
        p for p in (ROOT / "data/iatf_videos").iterdir()
        if p.is_dir() and p.name.endswith("_first_half_opencode")
    ]
    if not candidates:
        raise RuntimeError("first_half_opencode directory not found")
    video_dir = max(candidates, key=lambda p: p.stat().st_mtime)
    frames_dir = video_dir / "frames"
    timeline_path = video_dir / "timeline_first_half.json"
    script_path = video_dir / "script_first_half.json"

    frame_count = len(list(frames_dir.glob("frame_*.png")))
    print(f"[info] video_dir={video_dir.name}", flush=True)
    print(f"[info] frames={frame_count}", flush=True)
    if frame_count == 0:
        raise RuntimeError(f"No frames found in {frames_dir}")

    timeline = json.loads(timeline_path.read_text(encoding="utf-8"))
    script = json.loads(script_path.read_text(encoding="utf-8"))
    total_sec = max(e["start_sec"] + e["duration_sec"] for e in timeline) + 2.0
    fps = 6

    write_status("visual_qa_frames", frame_count=frame_count)
    visual_report = run_host.visual_qa_frames(frames_dir, video_dir)
    print(f"[visual_qa] ok={visual_report['ok']} reason={visual_report['reason']}", flush=True)

    write_status("compose_mp4", total_sec=round(total_sec, 2), fps=fps)
    stem = f"{video_dir.name}_{fps}fps_preview"
    output_mp4 = run_host.compose_mp4(timeline, frames_dir, video_dir, stem, total_sec, fps=fps)

    result = {
        "ok": True,
        "output_mp4": str(output_mp4),
        "duration_sec": round(total_sec, 2),
        "fps": fps,
        "frame_count": frame_count,
        "script_model": script.get("model_used", "unknown"),
        "visual_qa_contact_sheet": visual_report.get("contact_sheet"),
    }
    (video_dir / "first_half_opencode_result.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    write_status("done", **result)
    print(f"\n[done] MP4: {output_mp4}", flush=True)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        write_status("error", error=str(exc))
        raise
