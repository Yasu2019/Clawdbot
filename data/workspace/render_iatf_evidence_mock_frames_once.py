"""Render evidence-centered mock frames before Blender generation.

This is the next gate after Motion Table.  It creates simple 16:9 storyboard
frames where the visual subject is audit evidence, not characters.  The output
is used to confirm that Blender should build scenes around work cards, QMI,
labels, FIFO, old stock, and nonconforming areas.
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
STATUS_PATH = ROOT / "data/workspace/iatf_evidence_mock_status.json"
FRAME_SIZE = (1280, 720)


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


def evidence_items(row: dict) -> list[str]:
    raw = row.get("evidence_on_screen", "")
    items = [item.strip() for item in raw.split("/") if item.strip()]
    return items or ["監査証拠"]


def draw_document(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int], title: str, lines: list[str], color: str) -> None:
    x1, y1, x2, y2 = box
    title_font = font(22, bold=True)
    body_font = font(18)
    draw.rounded_rectangle(box, radius=10, fill="#ffffff", outline=color, width=4)
    draw.rectangle((x1, y1, x2, y1 + 48), fill=color)
    draw.text((x1 + 18, y1 + 12), title[:28], fill="#ffffff", font=title_font)
    y = y1 + 66
    for line in lines[:6]:
        draw.text((x1 + 20, y), line[:42], fill="#1e293b", font=body_font)
        y += 30
    draw.rectangle((x1 + 20, y2 - 48, x2 - 20, y2 - 26), fill="#e2e8f0")
    draw.rectangle((x1 + 20, y2 - 48, x1 + 140, y2 - 26), fill=color)


def draw_box_label(draw: ImageDraw.ImageDraw, x: int, y: int, label: str, accent: str) -> None:
    title_font = font(24, bold=True)
    small_font = font(17)
    draw.rounded_rectangle((x, y, x + 230, y + 130), radius=8, fill="#fef3c7", outline="#b45309", width=3)
    draw.line((x + 20, y + 30, x + 210, y + 30), fill="#92400e", width=2)
    draw.text((x + 32, y + 48), label, fill="#78350f", font=title_font)
    draw.text((x + 32, y + 88), "PACK QTY", fill="#92400e", font=small_font)
    draw.rectangle((x + 170, y + 14, x + 210, y + 54), fill=accent)


def draw_shelf(draw: ImageDraw.ImageDraw, x: int, y: int, label: str, color: str) -> None:
    label_font = font(20, bold=True)
    draw.rounded_rectangle((x, y, x + 260, y + 110), radius=8, fill="#f1f5f9", outline="#64748b", width=3)
    draw.rectangle((x + 14, y + 16, x + 246, y + 46), fill=color)
    draw.text((x + 28, y + 20), label[:18], fill="#ffffff", font=label_font)
    draw.line((x + 14, y + 68, x + 246, y + 68), fill="#94a3b8", width=3)


def render_frame(row: dict, path: Path, index: int, total: int) -> None:
    image = Image.new("RGB", FRAME_SIZE, "#eef2f7")
    draw = ImageDraw.Draw(image)
    title_font = font(28, bold=True)
    section_font = font(20, bold=True)
    body_font = font(20)
    small_font = font(16)

    draw.rectangle((0, 0, 1280, 76), fill="#0f2d46")
    draw.text((34, 20), f"{row['cut_id']}  {row['scene_id']}  Evidence Mock", fill="#ffffff", font=title_font)
    draw.text((1148, 26), f"{index}/{total}", fill="#dbeafe", font=small_font)

    # Left panel: spoken line and motion cue.
    draw.rounded_rectangle((34, 104, 410, 666), radius=10, fill="#ffffff", outline="#cbd5e1", width=2)
    draw.text((58, 128), "Narration", fill="#0f172a", font=section_font)
    y = 162
    for line in wrap(draw, row.get("spoken_line", ""), body_font, 318)[:7]:
        draw.text((58, y), line, fill="#1e293b", font=body_font)
        y += 30
    y += 18
    draw.text((58, y), "Motion Cue", fill="#0f172a", font=section_font)
    y += 34
    for key in ["body_action", "arm_action", "eye_direction"]:
        text = f"{key}: {row.get(key, '')}"
        for line in wrap(draw, text, small_font, 318)[:2]:
            draw.text((58, y), line, fill="#475569", font=small_font)
            y += 24

    # Main evidence stage.
    draw.rounded_rectangle((438, 104, 1246, 666), radius=12, fill="#f8fafc", outline="#94a3b8", width=2)
    draw.text((468, 130), "Audit Evidence On Screen", fill="#0f172a", font=section_font)
    items = evidence_items(row)
    item_text = " / ".join(items)
    draw.text((468, 160), item_text[:90], fill="#475569", font=small_font)

    # Evidence layout primitives.
    if any("作業カード" in item for item in items):
        draw_document(
            draw,
            (468, 204, 782, 486),
            "作業カード",
            ["顧客別 梱包数量", "40個 / 50個", "最新版を現場で確認", "承認済み文書"],
            "#2563eb",
        )
    if any("QMI" in item for item in items):
        draw_document(
            draw,
            (810, 204, 1214, 486),
            "QMI",
            ["梱包指示", "品質管理指示", "現場コピーと照合", "改訂番号を確認"],
            "#059669",
        )
    if any(("40個" in item or "箱" in item or "容器" in item) for item in items):
        draw_box_label(draw, 492, 512, "40個", "#22c55e")
    if any("50個" in item for item in items):
        draw_box_label(draw, 748, 512, "50個", "#ef4444")
    if any("FIFO" in item for item in items):
        draw_shelf(draw, 1002, 512, "FIFO", "#7c3aed")
    if any("旧品" in item for item in items):
        draw_shelf(draw, 470, 512, "旧品", "#f97316")
    if any("不適合" in item for item in items):
        draw_shelf(draw, 748, 512, "不適合品", "#dc2626")
    if not any(key in item_text for key in ["作業カード", "QMI", "40個", "50個", "FIFO", "旧品", "不適合"]):
        draw_document(
            draw,
            (568, 220, 1110, 520),
            "監査まとめ",
            items[:6],
            "#334155",
        )

    # Camera/exclusion footer.
    footer = f"Camera target: {row.get('eye_direction', '')} / Forbidden: evidence out-of-focus, character-only frame"
    draw.rectangle((438, 682, 1246, 710), fill="#fffbeb")
    draw.text((458, 688), footer[:120], fill="#92400e", font=small_font)
    image.save(path, quality=93)


def write_contact_sheet(frames: list[Path], output: Path) -> None:
    thumb_w, thumb_h = 320, 180
    label_h = 34
    cols = 3
    rows = (len(frames) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * thumb_w, rows * (thumb_h + label_h)), "white")
    draw = ImageDraw.Draw(sheet)
    label_font = font(18)
    for index, path in enumerate(frames):
        image = Image.open(path).convert("RGB")
        image.thumbnail((thumb_w, thumb_h))
        x = (index % cols) * thumb_w
        y = (index // cols) * (thumb_h + label_h)
        sheet.paste(image, (x + (thumb_w - image.width) // 2, y))
        draw.text((x + 8, y + thumb_h + 6), path.name, fill="#111827", font=label_font)
    sheet.save(output, quality=92)


def qa_frames(rows: list[dict], frames: list[Path]) -> dict:
    failures: list[str] = []
    evidence_all = " / ".join(row.get("evidence_on_screen", "") for row in rows)
    for key in ["作業カード", "QMI", "40個", "50個", "FIFO"]:
        if key not in evidence_all:
            failures.append(f"missing_visual_evidence:{key}")
    for path in frames:
        if path.stat().st_size < 20_000:
            failures.append(f"small_or_blank_frame:{path.name}")
    return {
        "ok": not failures,
        "failures": failures,
        "frame_count": len(frames),
    }


def write_index(contact_sheet: Path, frames: list[Path], output: Path) -> None:
    links = "\n".join(
        f'<li><a href="{html.escape(frame.name)}">{html.escape(frame.name)}</a></li>'
        for frame in frames
    )
    output.write_text(
        f"""<!doctype html>
<html lang="ja"><head><meta charset="utf-8"><title>IATF Evidence Mock Frames</title>
<style>body{{font-family:system-ui,'Meiryo',sans-serif;margin:24px;background:#f8fafc;color:#102033}}img{{max-width:100%;height:auto;border:1px solid #cbd5e1;background:white}}.wrap{{max-width:1100px;margin:auto}}</style>
</head><body><div class="wrap">
<h1>IATF Evidence Mock Frames</h1>
<p>Blender前の証拠物中心レンダー設計です。</p>
<img src="{html.escape(contact_sheet.name)}">
<h2>Frames</h2><ul>{links}</ul>
</div></body></html>""",
        encoding="utf-8",
    )


def main() -> int:
    design_dir = find_design_dir()
    motion_table = design_dir / "motion_lab_partial/motion_table.csv"
    if not motion_table.exists():
        raise RuntimeError(f"Missing motion table: {motion_table}")

    write_status("load_motion_table", motion_table=str(motion_table))
    with motion_table.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))

    out_dir = design_dir / "evidence_mock_frames"
    out_dir.mkdir(parents=True, exist_ok=True)
    frames: list[Path] = []
    for index, row in enumerate(rows, start=1):
        frame_path = out_dir / f"{index:02d}_{row['cut_id']}_{row['scene_id']}.jpg"
        render_frame(row, frame_path, index, len(rows))
        frames.append(frame_path)

    contact_sheet = out_dir / "contact_sheet.jpg"
    write_contact_sheet(frames, contact_sheet)
    qa = qa_frames(rows, frames)
    (out_dir / "evidence_mock_qa.json").write_text(
        json.dumps(qa, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    write_index(contact_sheet, frames, out_dir / "index.html")

    mirror = ROOT / "data/workspace/iatf_evidence_mock_frames"
    if mirror.exists():
        shutil.rmtree(mirror)
    shutil.copytree(out_dir, mirror)

    result = {
        "ok": qa["ok"],
        "design_dir": str(design_dir),
        "frames_dir": str(out_dir),
        "contact_sheet": str(contact_sheet),
        "review_html": str(out_dir / "index.html"),
        "mirror_review_html": str(mirror / "index.html"),
        "frame_count": len(frames),
        "failures": qa["failures"],
    }
    (out_dir / "evidence_mock_result.json").write_text(
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
