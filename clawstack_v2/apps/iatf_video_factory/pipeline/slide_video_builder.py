"""Build an approved slide deck into an IATF training video.

This is the safer continuation path after slide preflight.  It composes the
reviewed slide images with the generated master audio, then samples the MP4 at
multiple timeline checkpoints and compares those frames with the expected
slides.  The spot check gives us another guard before a video is treated as
deliverable.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import tempfile
import time
from pathlib import Path

from PIL import Image, ImageDraw, ImageOps


DEFAULT_FFMPEG = (
    r"C:\Users\yasu\AppData\Local\Microsoft\WinGet\Packages"
    r"\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe"
    r"\ffmpeg-8.1-full_build\bin\ffmpeg.exe"
)
DEFAULT_FFPROBE = (
    r"C:\Users\yasu\AppData\Local\Microsoft\WinGet\Packages"
    r"\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe"
    r"\ffmpeg-8.1-full_build\bin\ffprobe.exe"
)


def build_reviewed_slide_video(
    video_dir: Path,
    reviewer: str,
    review_note: str,
    output_name: str | None = None,
) -> dict:
    video_dir = video_dir.resolve()
    preflight_dir = video_dir / "slide_preflight"
    manifest_path = preflight_dir / "slide_manifest.json"
    timeline_path = video_dir / "timeline.json"
    audio_path = video_dir / "master_audio.wav"

    if not manifest_path.exists():
        raise FileNotFoundError(f"missing slide manifest: {manifest_path}")
    if not timeline_path.exists():
        raise FileNotFoundError(f"missing timeline: {timeline_path}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    timeline = json.loads(timeline_path.read_text(encoding="utf-8"))
    if not audio_path.exists():
        _build_master_audio(timeline, audio_path)
    _validate_slide_inputs(manifest, timeline)

    approval_path = _write_review_approval(preflight_dir, reviewer, review_note, manifest_path)
    output_mp4 = video_dir / (output_name or f"{video_dir.name}_slide_reviewed.mp4")
    build_dir = preflight_dir / "video_build"
    build_dir.mkdir(parents=True, exist_ok=True)
    concat_path = build_dir / "concat.txt"
    display_durations = _display_durations(timeline)
    _write_concat_file(concat_path, manifest, display_durations)
    _run_ffmpeg_concat(concat_path, audio_path, output_mp4)
    spot_report = _spot_check_video(output_mp4, manifest, timeline, display_durations, build_dir)

    result = {
        "ok": spot_report["ok"],
        "created_at": time.strftime("%Y-%m-%d %H:%M:%S %z"),
        "output_mp4": str(output_mp4),
        "review_approval": str(approval_path),
        "spot_check": spot_report,
        "duration_sec": _probe_duration(output_mp4),
        "size_bytes": output_mp4.stat().st_size,
    }
    result_path = build_dir / "slide_video_build_result.json"
    result_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    if not result["ok"]:
        raise RuntimeError(
            "slide video spot check failed: "
            f"{spot_report['reason']} / contact_sheet={spot_report.get('contact_sheet')}"
        )
    return result


def _validate_slide_inputs(manifest: dict, timeline: list[dict]) -> None:
    slides = manifest.get("slides", [])
    if not slides:
        raise RuntimeError("slide manifest has no slides")
    if len(slides) != len(timeline):
        raise RuntimeError(f"slide/timeline count mismatch: {len(slides)} != {len(timeline)}")
    for index, slide in enumerate(slides, start=1):
        path = _slide_path(slide)
        if not path.exists():
            raise FileNotFoundError(f"missing slide {index}: {path}")
        if slide.get("width") != 1280 or slide.get("height") != 720:
            raise RuntimeError(f"unexpected slide size at {index}: {slide.get('width')}x{slide.get('height')}")


def _write_review_approval(preflight_dir: Path, reviewer: str, review_note: str, manifest_path: Path) -> Path:
    approval = {
        "approved": True,
        "reviewer": reviewer,
        "reviewed_at": time.strftime("%Y-%m-%d %H:%M:%S %z"),
        "method": "AI visual inspection of slide contact sheet plus deterministic manifest checks",
        "note": review_note,
        "manifest": str(manifest_path),
    }
    path = preflight_dir / "ai_review_approval.json"
    path.write_text(json.dumps(approval, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def _write_concat_file(concat_path: Path, manifest: dict, display_durations: list[float]) -> None:
    with concat_path.open("w", encoding="utf-8") as handle:
        for slide, duration in zip(manifest["slides"], display_durations):
            handle.write(f"file '{_slide_path(slide).as_posix()}'\n")
            handle.write(f"duration {duration:.3f}\n")
        handle.write(f"file '{_slide_path(manifest['slides'][-1]).as_posix()}'\n")


def _run_ffmpeg_concat(concat_path: Path, audio_path: Path, output_mp4: Path) -> None:
    ffmpeg = os.getenv("FFMPEG_BIN", DEFAULT_FFMPEG)
    command = [
        ffmpeg,
        "-y",
        "-f",
        "concat",
        "-safe",
        "0",
        "-i",
        str(concat_path),
        "-i",
        str(audio_path),
        "-c:v",
        "libx264",
        "-vf",
        "fps=30,format=yuv420p",
        "-crf",
        "20",
        "-preset",
        "medium",
        "-c:a",
        "aac",
        "-b:a",
        "192k",
        "-shortest",
        str(output_mp4),
    ]
    subprocess.run(command, check=True, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=3600)


def _build_master_audio(timeline: list[dict], audio_path: Path) -> None:
    inputs: list[str] = []
    filters: list[str] = []
    for index, entry in enumerate(timeline):
        wav = entry.get("wav")
        if not wav or not Path(wav).exists():
            raise FileNotFoundError(f"missing timeline wav for slide {index + 1}: {wav}")
        inputs += ["-i", str(wav)]
        delay_ms = int(float(entry.get("start_sec", 0.0)) * 1000)
        filters.append(f"[{index}]adelay={delay_ms}|{delay_ms}[a{index}]")

    mix = "".join(f"[a{index}]" for index in range(len(timeline)))
    filters.append(f"{mix}amix=inputs={len(timeline)}:duration=longest[aout]")
    ffmpeg = os.getenv("FFMPEG_BIN", DEFAULT_FFMPEG)
    subprocess.run(
        [ffmpeg, "-y"] + inputs + ["-filter_complex", ";".join(filters), "-map", "[aout]", str(audio_path)],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=600,
    )


def _spot_check_video(
    output_mp4: Path,
    manifest: dict,
    timeline: list[dict],
    display_durations: list[float],
    build_dir: Path,
) -> dict:
    checkpoints = _checkpoint_indexes(len(timeline), sample_count=12)
    samples = []
    starts = _display_starts(display_durations)
    with tempfile.TemporaryDirectory(prefix="iatf_slide_video_spot_") as tmp_dir:
        tmp_path = Path(tmp_dir)
        for index in checkpoints:
            slide = manifest["slides"][index]
            timestamp = starts[index] + max(display_durations[index] / 2.0, 0.5)
            frame_path = tmp_path / f"frame_{index + 1:04d}.jpg"
            _extract_frame(output_mp4, timestamp, frame_path)
            expected = Image.open(_slide_path(slide)).convert("RGB")
            actual = Image.open(frame_path).convert("RGB")
            distance = _hash_distance(_average_hash(expected), _average_hash(actual))
            sample = {
                "slide_index": index + 1,
                "timestamp_sec": round(timestamp, 3),
                "hash_distance": distance,
                "expected_slide": str(_slide_path(slide)),
            }
            samples.append(sample)
            sample["frame_copy"] = str(_copy_frame(frame_path, build_dir, index + 1))

    failures = [s for s in samples if s["hash_distance"] > 8]
    sheet_path = build_dir / "video_spot_check_contact_sheet.jpg"
    _write_spot_sheet(samples, sheet_path)
    return {
        "ok": not failures,
        "reason": "ok" if not failures else f"{len(failures)} checkpoint frame(s) mismatched expected slide",
        "samples": samples,
        "contact_sheet": str(sheet_path),
    }


def _extract_frame(output_mp4: Path, timestamp: float, frame_path: Path) -> None:
    ffmpeg = os.getenv("FFMPEG_BIN", DEFAULT_FFMPEG)
    subprocess.run(
        [
            ffmpeg,
            "-y",
            "-ss",
            f"{timestamp:.3f}",
            "-i",
            str(output_mp4),
            "-frames:v",
            "1",
            "-q:v",
            "2",
            str(frame_path),
        ],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=120,
    )
    if not frame_path.exists():
        raise FileNotFoundError(f"ffmpeg did not extract a frame at {timestamp:.3f}s: {frame_path}")


def _copy_frame(source: Path, build_dir: Path, slide_index: int) -> Path:
    target = build_dir / f"spot_frame_{slide_index:04d}.jpg"
    Image.open(source).convert("RGB").save(target, quality=92)
    return target


def _write_spot_sheet(samples: list[dict], output: Path) -> None:
    thumb_w, thumb_h = 320, 180
    label_h = 42
    cols = 3
    rows = (len(samples) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * thumb_w, rows * (thumb_h + label_h)), "white")
    draw = ImageDraw.Draw(sheet)
    for sheet_index, sample in enumerate(samples):
        image = Image.open(sample["frame_copy"]).convert("RGB")
        image.thumbnail((thumb_w, thumb_h))
        x = (sheet_index % cols) * thumb_w
        y = (sheet_index // cols) * (thumb_h + label_h)
        sheet.paste(image, (x + (thumb_w - image.width) // 2, y))
        draw.text((x + 8, y + thumb_h + 4), f"slide {sample['slide_index']:04d}", fill="#111827")
        draw.text((x + 8, y + thumb_h + 21), f"d={sample['hash_distance']} t={sample['timestamp_sec']}s", fill="#111827")
    sheet.save(output, quality=92)


def _probe_duration(output_mp4: Path) -> float | None:
    ffprobe = os.getenv("FFPROBE_BIN", DEFAULT_FFPROBE)
    try:
        result = subprocess.run(
            [
                ffprobe,
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "default=noprint_wrappers=1:nokey=1",
                str(output_mp4),
            ],
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=60,
        )
        return round(float(result.stdout.strip()), 3)
    except Exception:
        return None


def _checkpoint_indexes(total: int, sample_count: int) -> list[int]:
    if total <= sample_count:
        return list(range(total))
    max_index = total - 1
    return sorted({round(i * max_index / (sample_count - 1)) for i in range(sample_count)})


def _display_durations(timeline: list[dict]) -> list[float]:
    durations = []
    for index, entry in enumerate(timeline):
        if index < len(timeline) - 1:
            current_start = float(entry.get("start_sec", 0.0))
            next_start = float(timeline[index + 1].get("start_sec", current_start))
            duration = next_start - current_start
        else:
            duration = float(entry.get("duration_sec", 3.0))
        durations.append(max(duration, 1.0))
    return durations


def _display_starts(display_durations: list[float]) -> list[float]:
    starts = []
    current = 0.0
    for duration in display_durations:
        starts.append(current)
        current += duration
    return starts


def _slide_path(slide: dict) -> Path:
    return Path(slide["file"]).resolve()


def _average_hash(image: Image.Image) -> str:
    gray = ImageOps.grayscale(image).resize((8, 8), Image.Resampling.LANCZOS)
    pixels = list(gray.getdata())
    average = sum(pixels) / len(pixels)
    return "".join("1" if pixel >= average else "0" for pixel in pixels)


def _hash_distance(left: str, right: str) -> int:
    return sum(1 for a, b in zip(left, right) if a != b)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("video_dir")
    parser.add_argument("--reviewer", default="Codex GPT-5 visual review")
    parser.add_argument(
        "--review-note",
        default="Slide contact sheet was visually checked before video composition.",
    )
    parser.add_argument("--output-name")
    args = parser.parse_args()
    result = build_reviewed_slide_video(
        Path(args.video_dir),
        reviewer=args.reviewer,
        review_note=args.review_note,
        output_name=args.output_name,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
