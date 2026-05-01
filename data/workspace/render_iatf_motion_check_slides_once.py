"""Render motion-check slides from IATF Motion Table.

This creates a visual gate after motion_table.csv and before Blender/video
generation.  The slides make it easy to confirm that each important cut has:
spoken line, action, eye direction, and evidence on screen.
"""

from __future__ import annotations

import csv
import html
import json
import shutil
import time
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[2]
STATUS_PATH = ROOT / "data/workspace/iatf_motion_check_slides_status.json"
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


def pill(draw: ImageDraw.ImageDraw, x: int, y: int, text: str, fill: str, font_obj) -> int:
    label = str(text).strip()[:28]
    if not label:
        return 0
    bbox = draw.textbbox((0, 0), label, font=font_obj)
    width = min(300, bbox[2] - bbox[0] + 24)
    draw.rounded_rectangle((x, y, x + width, y + 32), radius=8, fill=fill)
    draw.text((x + 12, y + 6), label, fill="#102033", font=font_obj)
    return width + 10


def render_slide(row: dict, out_path: Path, index: int, total: int) -> None:
    image = Image.new("RGB", SLIDE_SIZE, "#f8fafc")
    draw = ImageDraw.Draw(image)
    title_font = font(34, bold=True)
    label_font = font(19, bold=True)
    body_font = font(23)
    small_font = font(17)

    priority = row.get("priority", "B")
    bar = "#7f1d1d" if priority == "A" else "#12324d"
    draw.rectangle((0, 0, 1280, 86), fill=bar)
    draw.text((42, 22), f"{row['cut_id']} / {row['scene_id']} / {row['character']}", fill="#ffffff", font=title_font)
    draw.text((1110, 28), f"{index}/{total}", fill="#e2e8f0", font=small_font)

    y = 116
    draw.text((48, y), "Spoken Line", fill="#0f172a", font=label_font)
    y += 30
    for line in wrap(draw, row.get("spoken_line", ""), body_font, 1130)[:3]:
        draw.text((72, y), line, fill="#1e293b", font=body_font)
        y += 32

    y += 16
    draw.text((48, y), "Motion", fill="#0f172a", font=label_font)
    y += 30
    motion_lines = [
        "Body: " + row.get("body_action", ""),
        "Arm: " + row.get("arm_action", ""),
        "Hand: " + row.get("hand_action", ""),
        "Eyes: " + row.get("eye_direction", ""),
    ]
    for item in motion_lines:
        for line in wrap(draw, item, body_font, 1130)[:1]:
            draw.text((72, y), line, fill="#334155", font=body_font)
            y += 30

    y += 18
    draw.text((48, y), "Evidence On Screen", fill="#0f172a", font=label_font)
    y += 34
    x = 72
    for evidence in row.get("evidence_on_screen", "").split("/"):
        step = pill(draw, x, y, evidence, "#dbeafe", small_font)
        x += step
        if x > 1080:
            x = 72
            y += 40

    draw.rectangle((42, 618, 1238, 674), fill="#fff7ed", outline="#fed7aa")
    footer = f"Motion source: {row.get('motion_source', '')} / Manual fix: {row.get('manual_fix_notes', '')}"
    draw.text((64, 634), footer[:160], fill="#7c2d12", font=small_font)

    image.save(out_path, quality=93)


def write_contact_sheet(slides: list[Path], output: Path) -> None:
    thumb_w, thumb_h = 320, 180
    label_h = 34
    cols = 3
    rows = (len(slides) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * thumb_w, rows * (thumb_h + label_h)), "white")
    draw = ImageDraw.Draw(sheet)
    label_font = font(18)
    for index, path in enumerate(slides):
        image = Image.open(path).convert("RGB")
        image.thumbnail((thumb_w, thumb_h))
        x = (index % cols) * thumb_w
        y = (index // cols) * (thumb_h + label_h)
        sheet.paste(image, (x + (thumb_w - image.width) // 2, y))
        draw.text((x + 8, y + thumb_h + 6), path.name, fill="#111827", font=label_font)
    sheet.save(output, quality=92)


def write_index_html(contact_sheet: Path, slides: list[Path], output: Path) -> None:
    slide_links = "\n".join(
        f'<li><a href="{html.escape(path.name)}">{html.escape(path.name)}</a></li>'
        for path in slides
    )
    output.write_text(
        f"""<!doctype html>
<html lang="ja"><head><meta charset="utf-8"><title>IATF Motion Check Slides</title>
<style>body{{font-family:system-ui,'Meiryo',sans-serif;margin:24px;background:#f8fafc;color:#102033}}img{{max-width:100%;height:auto;border:1px solid #cbd5e1;background:white}}.wrap{{max-width:1100px;margin:auto}}</style>
</head><body><div class="wrap">
<h1>IATF Motion Check Slides</h1>
<p>Motion Tableから生成した動画前チェック用スライドです。</p>
<img src="{html.escape(contact_sheet.name)}">
<h2>Slides</h2><ul>{slide_links}</ul>
</div></body></html>""",
        encoding="utf-8",
    )


def qa_rows(rows: list[dict]) -> dict:
    failures: list[str] = []
    checkpoints = {
        "作業カード": False,
        "QMI": False,
        "40個": False,
        "50個": False,
        "FIFO": False,
    }
    for row in rows:
        evidence = row.get("evidence_on_screen", "")
        for key in checkpoints:
            if key in evidence:
                checkpoints[key] = True
        if row.get("priority") == "A" and not evidence:
            failures.append(f"{row.get('cut_id')}:priority_A_without_evidence")
        if not row.get("eye_direction"):
            failures.append(f"{row.get('cut_id')}:missing_eye_direction")
        if not row.get("body_action") or not row.get("arm_action"):
            failures.append(f"{row.get('cut_id')}:missing_body_or_arm_action")
    for key, found in checkpoints.items():
        if not found:
            failures.append(f"missing_checkpoint_evidence:{key}")
    return {
        "ok": not failures,
        "failures": failures,
        "checkpoints": checkpoints,
        "row_count": len(rows),
    }


def main() -> int:
    design_dir = find_design_dir()
    motion_table = design_dir / "motion_lab_partial/motion_table.csv"
    if not motion_table.exists():
        raise RuntimeError(f"Missing motion table: {motion_table}")

    write_status("load_motion_table", motion_table=str(motion_table))
    with motion_table.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    qa = qa_rows(rows)

    out_dir = design_dir / "motion_check_slides"
    out_dir.mkdir(parents=True, exist_ok=True)
    slides = []
    for index, row in enumerate(rows, start=1):
        slide_path = out_dir / f"{index:02d}_{row['cut_id']}_{row['scene_id']}.jpg"
        render_slide(row, slide_path, index, len(rows))
        slides.append(slide_path)

    contact_sheet = out_dir / "contact_sheet.jpg"
    write_contact_sheet(slides, contact_sheet)
    (out_dir / "motion_check_qa.json").write_text(
        json.dumps(qa, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    write_index_html(contact_sheet, slides, out_dir / "index.html")

    mirror = ROOT / "data/workspace/iatf_motion_check_slides"
    if mirror.exists():
        shutil.rmtree(mirror)
    shutil.copytree(out_dir, mirror)

    result = {
        "ok": qa["ok"],
        "design_dir": str(design_dir),
        "slides_dir": str(out_dir),
        "contact_sheet": str(contact_sheet),
        "review_html": str(out_dir / "index.html"),
        "mirror_review_html": str(mirror / "index.html"),
        "row_count": len(rows),
        "failures": qa["failures"],
    }
    (out_dir / "motion_check_slides_result.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    write_status("done", **result)
    return 0 if qa["ok"] else 2


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        write_status("error", error=str(exc))
        raise
