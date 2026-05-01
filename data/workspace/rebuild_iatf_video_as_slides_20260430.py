from __future__ import annotations

import json
import subprocess
import textwrap
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[2]
VIDEO_DIR = next(path for path in (ROOT / "data" / "iatf_videos").iterdir() if path.is_dir())
TIMELINE_PATH = VIDEO_DIR / "timeline.json"
SCRIPT_PATH = VIDEO_DIR / "script.json"
MASTER_AUDIO = VIDEO_DIR / "master_audio.wav"
OUT_DIR = VIDEO_DIR / "slide_rebuild_20260430"
SLIDE_DIR = OUT_DIR / "slides"
OUTPUT_MP4 = VIDEO_DIR / f"{VIDEO_DIR.name}_slide_rebuild.mp4"
FFMPEG = Path(
    r"C:\Users\yasu\AppData\Local\Microsoft\WinGet\Packages"
    r"\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe"
    r"\ffmpeg-8.1-full_build\bin\ffmpeg.exe"
)


def font(size: int, bold: bool = False):
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


TITLE_FONT = font(42, bold=True)
SUB_FONT = font(24, bold=True)
BODY_FONT = font(28)
SMALL_FONT = font(18)


def wrap_by_pixels(draw: ImageDraw.ImageDraw, text: str, font_obj, max_width: int) -> list[str]:
    lines = []
    current = ""
    for char in text:
      if char == "\n":
          lines.append(current)
          current = ""
          continue
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


def draw_wrapped(draw: ImageDraw.ImageDraw, text: str, xy: tuple[int, int], max_width: int, fill, line_gap: int = 8):
    x, y = xy
    lines = []
    for paragraph in text.splitlines() or [text]:
        lines.extend(wrap_by_pixels(draw, paragraph, BODY_FONT, max_width) or [""])
    for line in lines[:9]:
        draw.text((x, y), line, font=BODY_FONT, fill=fill)
        y += BODY_FONT.size + line_gap
    if len(lines) > 9:
        draw.text((x, y), "...", font=BODY_FONT, fill=fill)
    return y


def scene_names(script: dict) -> dict:
    return {scene.get("scene_id"): scene.get("scene_name", scene.get("scene_id", "")) for scene in script.get("scenes", [])}


def render_slide(entry: dict, index: int, count: int, scene_label: str, output: Path):
    image = Image.new("RGB", (1280, 720), "#f8fafc")
    draw = ImageDraw.Draw(image)

    draw.rectangle((0, 0, 1280, 86), fill="#0f172a")
    draw.text((48, 24), "IATF 16949 教材", font=TITLE_FONT, fill="#ffffff")
    draw.text((48, 105), "箇条 10.2.4 ポカヨケ", font=SUB_FONT, fill="#0f172a")
    draw.text((48, 145), scene_label, font=SMALL_FONT, fill="#64748b")

    draw.rounded_rectangle((48, 188, 1232, 586), radius=10, fill="#ffffff", outline="#dbe3ee", width=2)
    draw_wrapped(draw, entry.get("text", ""), (86, 228), max_width=1080, fill="#1e293b")

    speaker = entry.get("character", "speaker")
    draw.text((86, 605), f"話者: {speaker}", font=SMALL_FONT, fill="#64748b")
    draw.text((1110, 605), f"{index + 1}/{count}", font=SMALL_FONT, fill="#64748b")

    progress_w = int(1184 * ((index + 1) / count))
    draw.rectangle((48, 660, 1232, 674), fill="#e2e8f0")
    draw.rectangle((48, 660, 48 + progress_w, 674), fill="#2563eb")
    image.save(output, quality=95)


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    SLIDE_DIR.mkdir(parents=True, exist_ok=True)
    timeline = json.loads(TIMELINE_PATH.read_text(encoding="utf-8"))
    script = json.loads(SCRIPT_PATH.read_text(encoding="utf-8"))
    names = scene_names(script)

    concat_path = OUT_DIR / "concat.txt"
    slide_paths = []
    for index, entry in enumerate(timeline):
        slide_path = SLIDE_DIR / f"slide_{index + 1:04d}.jpg"
        render_slide(entry, index, len(timeline), names.get(entry.get("scene_id"), entry.get("scene_id", "")), slide_path)
        slide_paths.append(slide_path)

    with concat_path.open("w", encoding="utf-8") as handle:
        for entry, slide_path in zip(timeline, slide_paths):
            duration = max(float(entry.get("duration_sec", 3.0)), 1.0)
            handle.write(f"file '{slide_path.as_posix()}'\n")
            handle.write(f"duration {duration:.3f}\n")
        handle.write(f"file '{slide_paths[-1].as_posix()}'\n")

    cmd = [
        str(FFMPEG),
        "-y",
        "-f",
        "concat",
        "-safe",
        "0",
        "-i",
        str(concat_path),
        "-i",
        str(MASTER_AUDIO),
        "-c:v",
        "libx264",
        "-crf",
        "20",
        "-preset",
        "medium",
        "-c:a",
        "aac",
        "-b:a",
        "192k",
        "-pix_fmt",
        "yuv420p",
        "-shortest",
        str(OUTPUT_MP4),
    ]
    subprocess.run(cmd, check=True, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=3600)
    print(json.dumps({"output": str(OUTPUT_MP4), "slides": len(slide_paths), "concat": str(concat_path)}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
