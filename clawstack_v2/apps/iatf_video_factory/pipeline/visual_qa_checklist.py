# frozen_string_literal: false
"""Load and evaluate IATF Visual QA checklist (deterministic rules)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

_CHECKLIST_PATH = (
    Path(__file__).resolve().parent.parent / "config" / "iatf_visual_qa_checklist.json"
)


def load_checklist(path: Path | None = None) -> dict:
    p = path or _CHECKLIST_PATH
    return json.loads(p.read_text(encoding="utf-8"))


def mode_config(checklist: dict, mode: str) -> dict:
    modes = checklist.get("modes", {})
    if mode not in modes:
        raise ValueError(f"Unknown visual QA mode: {mode!r} (expected render|slide)")
    return modes[mode]


def default_sample_count(checklist: dict) -> int:
    return int(checklist.get("sample_count_default", 8))


def eval_fail_if(expr: str, metrics: dict[str, Any]) -> bool:
    """Return True when the rule should FAIL (fail_if condition is met).

    NameError (metric not yet measured) → False (skip, don't penalise).
    Other eval errors → True (fail-closed, expression malformed).
    """
    safe_globals = {"__builtins__": {}, "abs": abs, "len": len}
    try:
        return bool(eval(expr, safe_globals, dict(metrics)))  # noqa: S307
    except NameError:
        return False  # metric unavailable → skip this check
    except Exception:
        return True  # malformed expression → fail-closed


def run_deterministic_checks(
    checklist: dict,
    mode: str,
    metrics: dict[str, Any],
) -> tuple[list[dict], list[str]]:
    """Returns (check_results, failure_ids)."""
    cfg = mode_config(checklist, mode)
    results: list[dict] = []
    failure_ids: list[str] = []

    for rule in cfg.get("deterministic_checks", []):
        rid = rule["id"]
        expr = rule.get("fail_if", "False")
        failed = eval_fail_if(expr, metrics)
        evidence = _evidence_for_rule(rid, metrics, failed)
        results.append({"id": rid, "pass": not failed, "evidence": evidence})
        if failed:
            failure_ids.append(rid)

    return results, failure_ids


def vision_checks_for_mode(checklist: dict, mode: str) -> list[dict]:
    return list(mode_config(checklist, mode).get("vision_checks", []))


_EVIDENCE_KEYS: dict[str, list[str]] = {
    "R01": ["frame_count"],
    "R02": ["frame_count"],
    "R03": ["unique_dimensions_count", "width", "height"],
    "R04": ["width", "height"],
    "R05": ["dark_ratio_median"],
    "R06": ["edge_mean_median"],
    "R07": ["stddev_median"],
    "R08": ["center_stddev_median"],
    "R09": ["center_stddev_median", "center_saturation_std"],
    "R10": ["max_adjacent_ahash_distance"],
    "R11": ["first_last_pixel_diff"],
    "R12": ["mean_luminance_range", "max_adjacent_ahash_distance"],
    "R13": ["unique_ahash_count", "frame_count"],
    "R14": ["bright_ratio_median"],
    "R15": ["saturation_mean_median"],
    "R16": ["fps"],
    "R17": ["corrupt_frame_count"],
    "R18": ["audio_video_offset_ms"],
    "R19": ["has_audio"],
    "R20": ["output_mb"],
    "R21": ["width", "height"],
    "R22": ["video_codec"],
    "R23": ["audio_codec"],
    "R24": ["audio_bitrate_kbps"],
    "R25": ["max_identical_frame_streak"],
    "R26": ["subtitle_expected", "srt_exists"],
    "R27": ["center_50pct_mean_brightness"],
    "R28": ["inter_frame_brightness_variance_max"],
    "R29": ["r_channel_mean", "b_channel_mean"],
    "R30": ["video_duration_s"],
    "S01": ["frame_count"],
    "S02": ["unique_dimensions_count"],
    "S03": ["dark_ratio_median"],
    "S04": ["edge_mean_median", "stddev_median"],
    "S05": ["width", "height"],
    "S06": ["bright_ratio_median"],
    "S07": ["frame_count"],
    "S08": ["has_audio"],
    "S09": ["audio_duration", "video_duration"],
    "S10": ["output_mb"],
    "S11": ["corrupt_frame_count"],
    "S12": ["fps"],
    "S13": ["edge_mean_median"],
    "S14": ["unique_ahash_count", "frame_count"],
    "S15": ["stddev_median"],
    "S16": ["width", "height"],
    "S17": ["video_codec"],
    "S18": ["audio_codec"],
    "S19": ["audio_bitrate_kbps"],
    "S20": ["max_identical_frame_streak"],
    "S21": ["audio_peak_dbfs"],
    "S22": ["first_frame_bright_ratio", "first_frame_dark_ratio"],
    "S23": ["last_frame_bright_ratio", "last_frame_dark_ratio"],
    "S24": ["video_duration_s"],
    "S25": ["estimated_snr_db"],
}


def _evidence_for_rule(rule_id: str, metrics: dict[str, Any], failed: bool) -> str:
    prefix = rule_id.split("_")[0] if "_" in rule_id else rule_id[:3]
    keys = _EVIDENCE_KEYS.get(prefix, [])
    parts = [f"{k}={metrics.get(k, '?')}" for k in keys]
    status = "FAIL" if failed else "PASS"
    return f"{status}: " + (", ".join(parts) if parts else rule_id)
