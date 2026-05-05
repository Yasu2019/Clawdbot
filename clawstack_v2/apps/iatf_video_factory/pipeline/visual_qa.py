# frozen_string_literal: false
"""Visual QA gate for IATF video frames.

The video pipeline must not treat "PNG files exist" as success.  This
module samples rendered frames, writes a contact sheet for AI/human visual
inspection, and fails closed when frames look blank, static, or inconsistent.
"""

from __future__ import annotations

import json
from pathlib import Path
from statistics import median

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageOps, ImageStat


DEFAULT_SAMPLE_COUNT = 6


def inspect_frames(frames_dir: Path, report_dir: Path, sample_count: int = DEFAULT_SAMPLE_COUNT) -> dict:
    report_dir.mkdir(parents=True, exist_ok=True)
    frames = sorted(frames_dir.glob("frame_*.png"))
    if not frames:
        report = {
            "ok": False,
            "reason": "no frames found",
            "frame_count": 0,
            "samples": [],
            "failures": ["no_frames"],
        }
        _write_report(report, report_dir)
        return report

    sample_paths = _sample_paths(frames, sample_count)
    samples = [_inspect_one(path) for path in sample_paths]
    failures = _detect_failures(frames, samples)
    report = {
        "ok": not failures,
        "reason": "ok" if not failures else "; ".join(failures),
        "frame_count": len(frames),
        "samples": samples,
        "failures": failures,
    }

    sheet_path = report_dir / "contact_sheet.jpg"
    _write_contact_sheet(samples, sheet_path)
    report["contact_sheet"] = str(sheet_path)
    _write_report(report, report_dir)
    return report


def assert_visual_quality(frames_dir: Path, report_dir: Path, sample_count: int = DEFAULT_SAMPLE_COUNT) -> dict:
    report = inspect_frames(frames_dir, report_dir, sample_count)
    if not report["ok"]:
        raise RuntimeError(
            "Visual QA failed before MP4 compose: "
            f"{report['reason']} / contact_sheet={report.get('contact_sheet')}"
        )
    return report


def _sample_paths(frames: list[Path], sample_count: int) -> list[Path]:
    if len(frames) <= sample_count:
        return frames

    max_index = len(frames) - 1
    indexes = sorted({round(i * max_index / (sample_count - 1)) for i in range(sample_count)})
    return [frames[index] for index in indexes]


def _inspect_one(path: Path) -> dict:
    image = Image.open(path).convert("RGB")
    gray = ImageOps.grayscale(image)
    stat = ImageStat.Stat(gray)
    hist = gray.histogram()
    total = image.width * image.height
    edges = gray.filter(ImageFilter.FIND_EDGES)
    edge_mean = ImageStat.Stat(edges).mean[0]

    return {
        "file": str(path),
        "name": path.name,
        "width": image.width,
        "height": image.height,
        "mean": round(stat.mean[0], 2),
        "stddev": round(stat.stddev[0], 2),
        "dark_ratio": round(sum(hist[:25]) / total, 4),
        "bright_ratio": round(sum(hist[230:]) / total, 4),
        "edge_mean": round(edge_mean, 2),
        "ahash": _average_hash(gray),
    }


def _detect_failures(frames: list[Path], samples: list[dict]) -> list[str]:
    failures = []
    dimensions = {(sample["width"], sample["height"]) for sample in samples}
    edge_values = [sample["edge_mean"] for sample in samples]
    stddev_values = [sample["stddev"] for sample in samples]
    hashes = [sample["ahash"] for sample in samples]
    hash_distances = [
        _hash_distance(hashes[index], hashes[index + 1])
        for index in range(len(hashes) - 1)
    ]

    if len(frames) < 30:
        failures.append("too_few_frames")
    if len(dimensions) > 1:
        failures.append(f"inconsistent_frame_dimensions:{sorted(dimensions)}")
    mean_values_all = [sample["mean"] for sample in samples]
    bright_bg = mean_values_all and median(mean_values_all) > 120
    # 明背景（白スライド等）では stddev/edge が低くなるため閾値を緩める
    edge_threshold = 1.5 if bright_bg else 3.5
    std_threshold = 5.0 if bright_bg else 18.0
    if edge_values and median(edge_values) < edge_threshold:
        failures.append(f"low_visual_detail:edge_median={median(edge_values):.2f}")
    if stddev_values and median(stddev_values) < std_threshold:
        failures.append(f"low_contrast:stddev_median={median(stddev_values):.2f}")
    mean_values = [sample["mean"] for sample in samples]
    mean_range = max(mean_values) - min(mean_values) if mean_values else 0
    # ahash が似ていても輝度レンジが広い場合はトーキングヘッド動画の正常変化
    if hash_distances and max(hash_distances) <= 2 and mean_range < 30:
        failures.append("sample_frames_are_nearly_identical")
    return failures


def _average_hash(gray: Image.Image) -> str:
    small = gray.resize((8, 8), Image.Resampling.LANCZOS)
    pixels = list(small.getdata())
    average = sum(pixels) / len(pixels)
    bits = ["1" if pixel >= average else "0" for pixel in pixels]
    return "".join(bits)


def _hash_distance(left: str, right: str) -> int:
    return sum(1 for a, b in zip(left, right) if a != b)


def _write_contact_sheet(samples: list[dict], sheet_path: Path) -> None:
    thumb_w, thumb_h = 320, 180
    label_h = 44
    cols = 2
    rows = (len(samples) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * thumb_w, rows * (thumb_h + label_h)), "white")

    for index, sample in enumerate(samples):
        image = Image.open(sample["file"]).convert("RGB")
        image.thumbnail((thumb_w, thumb_h))
        x = (index % cols) * thumb_w
        y = (index // cols) * (thumb_h + label_h)
        sheet.paste(image, (x + (thumb_w - image.width) // 2, y))
        draw = ImageDraw.Draw(sheet)
        draw.text((x + 8, y + thumb_h + 4), sample["name"], fill=(20, 20, 20))
        draw.text(
            (x + 8, y + thumb_h + 20),
            f"edge={sample['edge_mean']} std={sample['stddev']} size={sample['width']}x{sample['height']}",
            fill=(20, 20, 20),
        )
    sheet.save(sheet_path, quality=90)


def _write_report(report: dict, report_dir: Path) -> None:
    (report_dir / "visual_qa_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
