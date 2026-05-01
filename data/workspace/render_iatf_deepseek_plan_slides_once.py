"""Render DeepSeek plan check slides for IATF video gating.

This consumes the design pilot folder created by prepare_iatf_video_design_once.py
and renders readable front/middle/back review slides from DeepSeek's compact
video plan.  These slides are for approval before script/video generation.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[2]
STATUS_PATH = ROOT / "data/workspace/iatf_deepseek_plan_slides_status.json"
SLIDE_SIZE = (1280, 720)


def write_status(stage: str, **extra: object) -> None:
    payload = {
        "updated_at": time.strftime("%Y-%m-%d %H:%M:%S %z"),
        "stage": stage,
        **extra,
    }
    STATUS_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False), flush=True)


def find_design_dir() -> Path:
    candidates = [
        path
        for path in (ROOT / "data/iatf_videos").iterdir()
        if path.is_dir() and path.name.endswith("_design_pilot")
    ]
    if not candidates:
        raise RuntimeError("No *_design_pilot directory found")
    return max(candidates, key=lambda path: path.stat().st_mtime)


def font(size: int, bold: bool = False):
    candidates = [
        "C:/Windows/Fonts/meiryo.ttc",
        "C:/Windows/Fonts/YuGothM.ttc",
        "C:/Windows/Fonts/msgothic.ttc",
    ]
    for candidate in candidates:
        if Path(candidate).exists():
            return ImageFont.truetype(candidate, size=size, index=1 if bold else 0)
    return ImageFont.load_default()


def wrap(draw: ImageDraw.ImageDraw, text: str, font_obj, max_width: int) -> list[str]:
    lines: list[str] = []
    current = ""
    for char in str(text):
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


def draw_pill(draw: ImageDraw.ImageDraw, x: int, y: int, text: str, fill: str, font_obj) -> int:
    label = str(text)[:34]
    bbox = draw.textbbox((0, 0), label, font=font_obj)
    width = min(360, bbox[2] - bbox[0] + 28)
    draw.rounded_rectangle((x, y, x + width, y + 34), radius=8, fill=fill)
    draw.text((x + 14, y + 7), label, fill="#0f172a", font=font_obj)
    return width + 10


def render_plan_slide(
    slide_path: Path,
    title: str,
    subtitle: str,
    must_match: str,
    visual_evidence: list[str],
    render_plan: dict | None,
    constraints: list[str],
    index: int,
    total: int,
) -> None:
    image = Image.new("RGB", SLIDE_SIZE, "#f8fafc")
    draw = ImageDraw.Draw(image)
    title_font = font(36, bold=True)
    section_font = font(22, bold=True)
    body_font = font(23)
    small_font = font(17)

    draw.rectangle((0, 0, 1280, 84), fill="#12324d")
    draw.text((42, 22), title, fill="#ffffff", font=title_font)
    draw.text((42, 102), subtitle, fill="#12324d", font=section_font)
    draw.text((1110, 106), f"{index}/{total}", fill="#475569", font=small_font)

    y = 150
    draw.text((52, y), "Must Match", fill="#0f172a", font=section_font)
    y += 34
    for line in wrap(draw, must_match, body_font, 1120)[:3]:
        draw.text((76, y), line, fill="#1e293b", font=body_font)
        y += 32

    y += 16
    draw.text((52, y), "Visual Evidence", fill="#0f172a", font=section_font)
    y += 38
    x = 76
    for item in visual_evidence[:10]:
        step = draw_pill(draw, x, y, item, "#dbeafe", small_font)
        x += step
        if x > 1060:
            x = 76
            y += 44
    y += 58

    if render_plan:
        draw.text((52, y), "Render Plan", fill="#0f172a", font=section_font)
        y += 34
        render_lines = [
            f"Camera: {render_plan.get('camera', '')}",
            f"Background: {render_plan.get('background_context', '')}",
            "Foreground: " + " / ".join(render_plan.get("foreground_evidence", [])[:8]),
            "Forbidden: " + " / ".join(render_plan.get("forbidden", [])[:5]),
        ]
        for text in render_lines:
            for line in wrap(draw, text, body_font, 1120)[:2]:
                draw.text((76, y), line, fill="#334155", font=body_font)
                y += 31
            y += 4

    if constraints:
        draw.rectangle((42, 616, 1238, 672), fill="#fff7ed", outline="#fed7aa")
        draw.text((64, 632), "Key Constraint: " + constraints[(index - 1) % len(constraints)], fill="#7c2d12", font=small_font)

    image.save(slide_path, quality=93)


def write_contact_sheet(slide_paths: list[Path], output: Path) -> None:
    thumb_w, thumb_h = 320, 180
    label_h = 34
    cols = 3
    rows = (len(slide_paths) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * thumb_w, rows * (thumb_h + label_h)), "white")
    draw = ImageDraw.Draw(sheet)
    label_font = font(18)

    for index, path in enumerate(slide_paths):
        image = Image.open(path).convert("RGB")
        image.thumbnail((thumb_w, thumb_h))
        x = (index % cols) * thumb_w
        y = (index // cols) * (thumb_h + label_h)
        sheet.paste(image, (x + (thumb_w - image.width) // 2, y))
        draw.text((x + 8, y + thumb_h + 6), path.name, fill="#111827", font=label_font)
    sheet.save(output, quality=92)


def main() -> int:
    design_dir = find_design_dir()
    plan_path = design_dir / "deepseek_compact_video_plan.json"
    story_path = design_dir / "storyboard.json"
    intent_path = design_dir / "intent_map.json"
    if not plan_path.exists():
        raise RuntimeError(f"Missing DeepSeek compact plan: {plan_path}")

    write_status("load_plan", design_dir=str(design_dir))
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    storyboard = json.loads(story_path.read_text(encoding="utf-8"))
    intent = json.loads(intent_path.read_text(encoding="utf-8"))

    render_by_scene = {item.get("scene_id"): item for item in plan.get("render_plan", [])}
    constraints = plan.get("script_constraints", [])

    out_dir = design_dir / "deepseek_plan_check_slides"
    out_dir.mkdir(parents=True, exist_ok=True)

    slide_paths: list[Path] = []
    for index, slide in enumerate(plan.get("slide_plan", []), start=1):
        checkpoint = slide.get("checkpoint", "check")
        scene_id = slide.get("scene_id", "")
        scene = next((item for item in storyboard.get("scenes", []) if item.get("scene_id") == scene_id), {})
        title = f"{checkpoint.upper()} Check: {scene_id}"
        subtitle = f"箇条{intent.get('clause')} / {intent.get('topic')} / {scene.get('purpose', '')}"
        slide_path = out_dir / f"{index:02d}_{checkpoint}_{scene_id}.jpg"
        render_plan = render_by_scene.get(scene_id)
        render_plan_slide(
            slide_path=slide_path,
            title=title,
            subtitle=subtitle,
            must_match=slide.get("must_match", ""),
            visual_evidence=slide.get("visual_evidence", []),
            render_plan=render_plan,
            constraints=constraints,
            index=index,
            total=len(plan.get("slide_plan", [])),
        )
        slide_paths.append(slide_path)

    contact_sheet = out_dir / "contact_sheet.jpg"
    write_contact_sheet(slide_paths, contact_sheet)

    review = {
        "task": "Review DeepSeek compact video plan slides before script/video generation.",
        "source_plan": str(plan_path),
        "contact_sheet": str(contact_sheet),
        "slide_count": len(slide_paths),
        "pass_criteria": [
            "front/middle/back checkpoints exist",
            "each checkpoint includes concrete audit evidence",
            "render plan forbids low-information character-only footage",
            "slide content matches the source intent map and storyboard",
        ],
    }
    review_path = out_dir / "review_request.json"
    review_path.write_text(json.dumps(review, ensure_ascii=False, indent=2), encoding="utf-8")

    result = {
        "ok": True,
        "design_dir": str(design_dir),
        "slides_dir": str(out_dir),
        "contact_sheet": str(contact_sheet),
        "review_request": str(review_path),
        "slide_count": len(slide_paths),
    }
    (out_dir / "deepseek_plan_slides_result.json").write_text(
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
