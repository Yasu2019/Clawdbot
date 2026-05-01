"""Slide-first preflight gate for IATF video generation.

The pipeline must prove that the teaching material is readable and aligned
with the script before expensive rendering or MP4 composition starts.  This
module creates slide previews from the timeline, performs deterministic
script/slide consistency checks, and requires an explicit AI visual review
approval before the video stage is allowed to continue.
"""

from __future__ import annotations

import hashlib
import json
import os
import shlex
import subprocess
import sys
import time
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


SLIDE_SIZE = (1280, 720)
DEFAULT_TIMEOUT_SEC = 300


def run_slide_preflight(script: dict, timeline: list[dict], video_dir: Path, title: str) -> dict:
    preflight_dir = video_dir / "slide_preflight"
    slides_dir = preflight_dir / "slides"
    slides_dir.mkdir(parents=True, exist_ok=True)

    manifest = _render_slides(script, timeline, slides_dir, title)
    contact_sheet = preflight_dir / "contact_sheet.jpg"
    _write_contact_sheet(manifest["slides"], contact_sheet)
    manifest["contact_sheet"] = str(contact_sheet)

    failures = _validate_manifest(manifest, timeline)
    manifest["ok"] = not failures
    manifest["failures"] = failures
    manifest_path = preflight_dir / "slide_manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    request = _write_review_request(preflight_dir, manifest_path, contact_sheet, script, timeline)
    review = _run_ai_review(request)
    result = {
        "ok": manifest["ok"] and review["approved"],
        "manifest": str(manifest_path),
        "contact_sheet": str(contact_sheet),
        "review_request": str(request),
        "review": review,
        "failures": failures + ([] if review["approved"] else [review["reason"]]),
    }
    (preflight_dir / "slide_preflight_result.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    if not result["ok"]:
        raise RuntimeError(
            "Slide preflight failed before video generation: "
            f"{'; '.join(result['failures'])} / contact_sheet={contact_sheet}"
        )
    return result


def _render_slides(script: dict, timeline: list[dict], slides_dir: Path, title: str) -> dict:
    scene_names = {
        scene.get("scene_id"): scene.get("scene_name") or scene.get("scene_id", "")
        for scene in script.get("scenes", [])
    }
    slides = []
    count = len(timeline)
    for index, entry in enumerate(timeline):
        slide_path = slides_dir / f"slide_{index + 1:04d}.jpg"
        text = str(entry.get("text", "")).strip()
        scene_id = entry.get("scene_id", "")
        _render_one_slide(
            slide_path=slide_path,
            title=title,
            scene_label=scene_names.get(scene_id, scene_id),
            body=text,
            speaker=str(entry.get("character", "speaker")),
            index=index,
            count=count,
        )
        slides.append(
            {
                "index": index + 1,
                "file": str(slide_path),
                "scene_id": scene_id,
                "character": entry.get("character"),
                "start_sec": entry.get("start_sec"),
                "duration_sec": entry.get("duration_sec"),
                "text_sha256": _sha256(text),
                "text_length": len(text),
                "width": SLIDE_SIZE[0],
                "height": SLIDE_SIZE[1],
            }
        )
    return {
        "created_at": time.strftime("%Y-%m-%d %H:%M:%S %z"),
        "slide_count": count,
        "title": title,
        "script_model": script.get("model_used", "unknown"),
        "slides": slides,
    }


def _render_one_slide(
    slide_path: Path,
    title: str,
    scene_label: str,
    body: str,
    speaker: str,
    index: int,
    count: int,
) -> None:
    image = Image.new("RGB", SLIDE_SIZE, "#f8fafc")
    draw = ImageDraw.Draw(image)

    title_font = _font(38, bold=True)
    sub_font = _font(22, bold=True)
    body_font = _font(28)
    small_font = _font(18)

    draw.rectangle((0, 0, 1280, 82), fill="#102033")
    draw.text((48, 22), "IATF 16949 Training", font=title_font, fill="#ffffff")
    draw.text((48, 105), title[:72], font=sub_font, fill="#102033")
    if scene_label:
        draw.text((48, 142), str(scene_label)[:96], font=small_font, fill="#64748b")

    draw.rounded_rectangle((48, 184, 1232, 588), radius=8, fill="#ffffff", outline="#dbe3ee", width=2)
    _draw_wrapped(draw, body, (86, 226), body_font, 1080, "#1e293b")

    draw.text((86, 606), f"speaker: {speaker}", font=small_font, fill="#64748b")
    draw.text((1110, 606), f"{index + 1}/{count}", font=small_font, fill="#64748b")
    draw.rectangle((48, 660, 1232, 674), fill="#e2e8f0")
    progress_w = int(1184 * ((index + 1) / max(count, 1)))
    draw.rectangle((48, 660, 48 + progress_w, 674), fill="#2563eb")
    image.save(slide_path, quality=94)


def _draw_wrapped(draw: ImageDraw.ImageDraw, text: str, xy: tuple[int, int], font_obj, max_width: int, fill: str) -> None:
    x, y = xy
    lines: list[str] = []
    for paragraph in text.splitlines() or [text]:
        lines.extend(_wrap_by_pixels(draw, paragraph, font_obj, max_width) or [""])

    max_lines = 9
    for line in lines[:max_lines]:
        draw.text((x, y), line, font=font_obj, fill=fill)
        y += font_obj.size + 8
    if len(lines) > max_lines:
        draw.text((x, y), "...", font=font_obj, fill=fill)


def _wrap_by_pixels(draw: ImageDraw.ImageDraw, text: str, font_obj, max_width: int) -> list[str]:
    lines: list[str] = []
    current = ""
    for char in text:
        candidate = current + char
        bbox = draw.textbbox((0, 0), candidate, font=font_obj)
        if bbox[2] - bbox[0] <= max_width or not current:
            current = candidate
        else:
            lines.append(current)
            current = char
    if current:
        lines.append(current)
    return lines


def _write_contact_sheet(slides: list[dict], output: Path, sample_count: int = 12) -> None:
    if not slides:
        return
    indexes = _sample_indexes(len(slides), sample_count)
    thumb_w, thumb_h = 320, 180
    label_h = 34
    cols = 3
    rows = (len(indexes) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * thumb_w, rows * (thumb_h + label_h)), "white")
    draw = ImageDraw.Draw(sheet)
    for sheet_index, slide_index in enumerate(indexes):
        slide = slides[slide_index]
        image = Image.open(slide["file"]).convert("RGB")
        image.thumbnail((thumb_w, thumb_h))
        x = (sheet_index % cols) * thumb_w
        y = (sheet_index // cols) * (thumb_h + label_h)
        sheet.paste(image, (x + (thumb_w - image.width) // 2, y))
        draw.text((x + 8, y + thumb_h + 6), f"slide {slide['index']:04d}", fill="#111827")
    sheet.save(output, quality=92)


def _validate_manifest(manifest: dict, timeline: list[dict]) -> list[str]:
    failures: list[str] = []
    slides = manifest.get("slides", [])
    if not slides:
        failures.append("no_slides_generated")
    if len(slides) != len(timeline):
        failures.append(f"slide_count_mismatch:{len(slides)}!={len(timeline)}")

    for index, (slide, entry) in enumerate(zip(slides, timeline), start=1):
        text = str(entry.get("text", "")).strip()
        if not text:
            failures.append(f"blank_script_text:slide_{index:04d}")
        if slide.get("text_sha256") != _sha256(text):
            failures.append(f"text_hash_mismatch:slide_{index:04d}")
        if not Path(slide.get("file", "")).exists():
            failures.append(f"missing_slide_file:slide_{index:04d}")
        if slide.get("width") != SLIDE_SIZE[0] or slide.get("height") != SLIDE_SIZE[1]:
            failures.append(f"slide_size_mismatch:slide_{index:04d}")
    return failures


def _write_review_request(
    preflight_dir: Path,
    manifest_path: Path,
    contact_sheet: Path,
    script: dict,
    timeline: list[dict],
) -> Path:
    request = {
        "task": "Review IATF training slide deck before video generation.",
        "required_decision": {
            "approved": "boolean",
            "reason": "short Japanese or English explanation",
        },
        "pass_criteria": [
            "Slides are visually readable and not blank or malformed.",
            "Slide sequence matches the script/timeline order.",
            "Slide text communicates the same content as the script.",
            "No video generation should proceed if the deck is visually broken.",
        ],
        "contact_sheet": str(contact_sheet),
        "manifest": str(manifest_path),
        "slide_count": len(timeline),
        "script_model": script.get("model_used", "unknown"),
    }
    request_path = preflight_dir / "ai_review_request.json"
    request_path.write_text(json.dumps(request, ensure_ascii=False, indent=2), encoding="utf-8")
    return request_path


def _run_ai_review(request_path: Path) -> dict:
    mode = os.getenv("IATF_VIDEO_SLIDE_REVIEW_MODE", "ai_required").strip().lower()
    review_cmd = os.getenv("IATF_VIDEO_AI_REVIEW_CMD", "").strip()

    if mode == "local_only":
        return {
            "approved": True,
            "mode": mode,
            "reason": "deterministic slide checks only; AI visual review bypassed for local verification",
        }

    if not review_cmd:
        return {
            "approved": False,
            "mode": mode,
            "reason": "ai_review_required_but_IATF_VIDEO_AI_REVIEW_CMD_not_set",
        }

    timeout_sec = int(os.getenv("IATF_VIDEO_AI_REVIEW_TIMEOUT_SEC", str(DEFAULT_TIMEOUT_SEC)))
    command = shlex.split(review_cmd, posix=(os.name != "nt")) + [str(request_path)]
    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout_sec,
    )
    if result.returncode != 0:
        return {
            "approved": False,
            "mode": "ai_command",
            "reason": f"ai_review_command_failed:{result.returncode}:{result.stderr[-500:]}",
        }

    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        return {
            "approved": False,
            "mode": "ai_command",
            "reason": f"ai_review_non_json_output:{exc}",
            "stdout_tail": result.stdout[-500:],
        }
    return {
        "approved": payload.get("approved") is True,
        "mode": "ai_command",
        "reason": str(payload.get("reason", ""))[:1000],
        "raw": payload,
    }


def _sample_indexes(total: int, sample_count: int) -> list[int]:
    if total <= sample_count:
        return list(range(total))
    max_index = total - 1
    return sorted({round(i * max_index / (sample_count - 1)) for i in range(sample_count)})


def _font(size: int, bold: bool = False):
    candidates = [
        r"C:\Windows\Fonts\YuGothB.ttc" if bold else r"C:\Windows\Fonts\YuGothM.ttc",
        r"C:\Windows\Fonts\meiryob.ttc" if bold else r"C:\Windows\Fonts\meiryo.ttc",
        r"C:\Windows\Fonts\msgothic.ttc",
    ]
    for candidate in candidates:
        path = Path(candidate)
        if path.exists():
            return ImageFont.truetype(str(path), size=size)
    return ImageFont.load_default()


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


if __name__ == "__main__":
    if len(sys.argv) != 4:
        raise SystemExit("usage: slide_preflight.py SCRIPT_JSON TIMELINE_JSON VIDEO_DIR")
    script_path = Path(sys.argv[1])
    timeline_path = Path(sys.argv[2])
    target_dir = Path(sys.argv[3])
    report = run_slide_preflight(
        json.loads(script_path.read_text(encoding="utf-8")),
        json.loads(timeline_path.read_text(encoding="utf-8")),
        target_dir,
        target_dir.name,
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
