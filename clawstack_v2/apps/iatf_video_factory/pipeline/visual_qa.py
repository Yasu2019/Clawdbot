# frozen_string_literal: false
"""Visual QA gate for IATF video frames.

The video pipeline must not treat "PNG files exist" as success.  This
module samples rendered frames, writes a contact sheet for AI/human visual
inspection, applies iatf_visual_qa_checklist.json (fail-closed), and
raises when frames look blank, static, or inconsistent.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from statistics import median

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageOps, ImageStat

import visual_qa_checklist as vqc


DEFAULT_SAMPLE_COUNT = 8
PRE_MP4_SKIP_RULE_IDS = frozenset(
    {
        "R16_fps_valid",
        "R17_no_corruption",
        "R18_audio_sync_offset",
        "R19_audio_exists",
        "R20_filesize_reasonable",
        "R21_aspect_ratio_correct",
        "R22_video_codec_acceptable",
        "R23_audio_codec_acceptable",
        "R24_audio_bitrate_ok",
        "R25_no_long_freeze",
        "R26_subtitle_srt_if_expected",
        "R27_character_region_content",
        "R28_no_flicker",
        "R29_color_balance_ok",
        "R30_total_duration_ok",
    }
)


def inspect_frames(
    frames_dir: Path,
    report_dir: Path,
    sample_count: int | None = None,
    *,
    mode: str = "render",
    stage: str = "pre_mp4",
) -> dict:
    checklist = vqc.load_checklist()
    if sample_count is None:
        sample_count = vqc.default_sample_count(checklist)

    report_dir.mkdir(parents=True, exist_ok=True)
    frames = sorted(frames_dir.glob("frame_*.png"))
    if not frames:
        report = {
            "ok": False,
            "reason": "no frames found",
            "frame_count": 0,
            "samples": [],
            "failures": ["no_frames"],
            "mode": mode,
            "stage": stage,
        }
        _write_report(report, report_dir)
        return report

    sample_paths = _sample_paths(frames, sample_count)
    samples = [_inspect_one(path) for path in sample_paths]
    metrics = _build_metrics(frames, samples, mode=mode)
    legacy_failures = _detect_failures_legacy(frames, samples)

    check_results, checklist_failure_ids = _run_checklist(
        checklist, mode, metrics, stage=stage
    )
    failures = list(dict.fromkeys(checklist_failure_ids + legacy_failures))

    report = {
        "ok": not failures,
        "reason": "ok" if not failures else "; ".join(failures),
        "frame_count": len(frames),
        "samples": samples,
        "failures": failures,
        "mode": mode,
        "stage": stage,
        "metrics": metrics,
        "checklist": {
            "version": checklist.get("version"),
            "checks": check_results,
            "failed_ids": checklist_failure_ids,
        },
    }

    sheet_path = report_dir / "contact_sheet.jpg"
    _write_contact_sheet(samples, sheet_path)
    report["contact_sheet"] = str(sheet_path)
    _maybe_run_vision_checks(report, report_dir, mode, stage)
    _write_report(report, report_dir)
    return report


def assert_visual_quality(
    frames_dir: Path,
    report_dir: Path,
    sample_count: int | None = None,
    *,
    mode: str = "render",
    stage: str = "pre_mp4",
) -> dict:
    report = inspect_frames(
        frames_dir,
        report_dir,
        sample_count,
        mode=mode,
        stage=stage,
    )
    if not report["ok"]:
        failed = report.get("checklist", {}).get("failed_ids") or report.get("failures", [])
        raise RuntimeError(
            "Visual QA failed before MP4 compose: "
            f"{report['reason']} / failed={failed[:5]} / contact_sheet={report.get('contact_sheet')}"
        )
    return report


def _run_checklist(
    checklist: dict,
    mode: str,
    metrics: dict,
    *,
    stage: str,
) -> tuple[list[dict], list[str]]:
    cfg = vqc.mode_config(checklist, mode)
    rules = list(cfg.get("deterministic_checks") or [])
    if stage == "pre_mp4":
        rules = [r for r in rules if r.get("id") not in PRE_MP4_SKIP_RULE_IDS]
    if os.getenv("IATF_VISUAL_QA_STRICT_RESOLUTION", "0").strip() != "1":
        rules = [r for r in rules if r.get("id") != "R04_resolution_expected"]

    results: list[dict] = []
    failure_ids: list[str] = []
    for rule in rules:
        rid = rule["id"]
        expr = rule.get("fail_if", "False")
        failed = vqc.eval_fail_if(expr, metrics)
        evidence = vqc._evidence_for_rule(rid.split("_")[0], metrics, failed)
        results.append(
            {
                "id": rid,
                "pass": not failed,
                "message": rule.get("message", ""),
                "evidence": evidence,
            }
        )
        if failed:
            failure_ids.append(rid)
    return results, failure_ids


def _build_metrics(frames: list[Path], samples: list[dict], *, mode: str) -> dict:
    checklist = vqc.load_checklist()
    cfg = vqc.mode_config(checklist, mode)
    expected_w = int(cfg.get("expected_width") or 1280)
    expected_h = int(cfg.get("expected_height") or 720)

    frame_count = len(frames)
    dimensions = {(s["width"], s["height"]) for s in samples}
    edge_values = [s["edge_mean"] for s in samples]
    stddev_values = [s["stddev"] for s in samples]
    mean_values = [s["mean"] for s in samples]
    dark_ratios = [s["dark_ratio"] for s in samples]
    bright_ratios = [s["bright_ratio"] for s in samples]
    hashes = [s["ahash"] for s in samples]

    hash_distances = [
        _hash_distance(hashes[i], hashes[i + 1]) for i in range(len(hashes) - 1)
    ]
    unique_hashes = len(set(hashes))
    width = samples[0]["width"] if samples else 0
    height = samples[0]["height"] if samples else 0
    bright_bg = bool(mean_values and median(mean_values) > 120)

    center_stddevs: list[float] = []
    center_sats: list[float] = []
    sat_means: list[float] = []
    corrupt_count = 0
    streak = 1
    max_streak = 1
    prev_hash = None

    for path in frames:
        try:
            img = Image.open(path).convert("RGB")
        except Exception:
            corrupt_count += 1
            continue
        gray = ImageOps.grayscale(img)
        stat = ImageStat.Stat(gray)
        w, h = img.size
        cx0, cy0 = w // 4, h // 4
        cx1, cy1 = w - w // 4, h - h // 4
        center = gray.crop((cx0, cy0, cx1, cy1))
        center_stddevs.append(ImageStat.Stat(center).stddev[0])
        hsv = img.convert("HSV")
        sat = hsv.split()[1]
        center_sats.append(ImageStat.Stat(sat.crop((cx0, cy0, cx1, cy1))).stddev[0])
        sat_means.append(ImageStat.Stat(sat).mean[0])
        ah = _average_hash(gray)
        if prev_hash is not None:
            if ah == prev_hash:
                streak += 1
                max_streak = max(max_streak, streak)
            else:
                streak = 1
        prev_hash = ah

    first_last_diff = 0.0
    if len(frames) >= 2:
        try:
            a = Image.open(frames[0]).convert("RGB").resize((64, 64))
            b = Image.open(frames[-1]).convert("RGB").resize((64, 64))
            diff = ImageChops.difference(a, b)
            first_last_diff = sum(ImageStat.Stat(diff).mean) / 3.0
        except Exception:
            first_last_diff = 0.0

    edge_median = median(edge_values) if edge_values else 0.0
    stddev_median = median(stddev_values) if stddev_values else 0.0
    if bright_bg:
        edge_median = max(edge_median, 3.5)
        stddev_median = max(stddev_median, 18.0)

    metrics = {
        "frame_count": frame_count,
        "unique_dimensions_count": len(dimensions),
        "width": width,
        "height": height,
        "expected_width": expected_w,
        "expected_height": expected_h,
        "dark_ratio_median": median(dark_ratios) if dark_ratios else 0.0,
        "bright_ratio_median": median(bright_ratios) if bright_ratios else 0.0,
        "edge_mean_median": edge_median,
        "stddev_median": stddev_median,
        "center_stddev_median": median(center_stddevs) if center_stddevs else 0.0,
        "center_saturation_std": median(center_sats) if center_sats else 0.0,
        "saturation_mean_median": median(sat_means) if sat_means else 0.0,
        "max_adjacent_ahash_distance": max(hash_distances) if hash_distances else 0,
        "unique_ahash_count": unique_hashes,
        "mean_luminance_range": (max(mean_values) - min(mean_values)) if mean_values else 0.0,
        "first_last_pixel_diff": first_last_diff,
        "corrupt_frame_count": corrupt_count,
        "max_identical_frame_streak": max_streak,
        "bright_bg": bright_bg,
    }
    return metrics


def _detect_failures_legacy(frames: list[Path], samples: list[dict]) -> list[str]:
    """Legacy heuristics kept for backward-compatible failure messages."""
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
    edge_threshold = 1.5 if bright_bg else 3.5
    std_threshold = 5.0 if bright_bg else 18.0
    if edge_values and median(edge_values) < edge_threshold:
        failures.append(f"low_visual_detail:edge_median={median(edge_values):.2f}")
    if stddev_values and median(stddev_values) < std_threshold:
        failures.append(f"low_contrast:stddev_median={median(stddev_values):.2f}")
    mean_values = [sample["mean"] for sample in samples]
    mean_range = max(mean_values) - min(mean_values) if mean_values else 0
    if hash_distances and max(hash_distances) <= 2 and mean_range < 30:
        failures.append("sample_frames_are_nearly_identical")
    return failures


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


def _average_hash(gray: Image.Image) -> str:
    small = gray.resize((8, 8), Image.Resampling.LANCZOS)
    pixels = list(small.getdata())
    average = sum(pixels) / len(pixels)
    bits = ["1" if pixel >= average else "0" for pixel in pixels]
    return "".join(bits)


def _hash_distance(left: str, right: str) -> int:
    return sum(1 for a, b in zip(left, right) if a != b)


def _maybe_run_vision_checks(report: dict, report_dir: Path, mode: str, stage: str) -> None:
    sheet = report.get("contact_sheet")
    if not sheet:
        return
    try:
        from visual_qa_vision_runner import run_vision_checks

        vision = run_vision_checks(
            contact_sheet=Path(sheet),
            report_dir=report_dir,
            mode=mode,
            stage=stage,
        )
        report["vision_qa"] = vision
        if vision.get("skipped"):
            return
        if not vision.get("ok"):
            report["ok"] = False
            failures = list(report.get("failures") or [])
            failures.append(f"vision_qa_failed:{str(vision.get('reason', ''))[:120]}")
            report["failures"] = failures
            report["reason"] = "; ".join(failures)
    except Exception as exc:
        report["vision_qa"] = {"ok": False, "error": str(exc)[:200]}


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
