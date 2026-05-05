#!/usr/bin/env python3
"""
Auto Manual AI pipeline skeleton.
Safe-by-default: reads input video, writes derived files only to output directory.
Requires ffmpeg in PATH for actual video splitting/extraction.
"""
from __future__ import annotations
import argparse, json, os, subprocess, hashlib
from pathlib import Path


def run(cmd: list[str]) -> None:
    print("+", " ".join(cmd))
    subprocess.run(cmd, check=True)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda: f.read(1024*1024), b''):
            h.update(b)
    return h.hexdigest()


def split_video(video: Path, outdir: Path, chunk_minutes: int) -> list[Path]:
    chunks = outdir / "chunks"
    chunks.mkdir(parents=True, exist_ok=True)
    pattern = chunks / "chunk_%03d.mp4"
    run(["ffmpeg", "-y", "-i", str(video), "-c", "copy", "-map", "0", "-segment_time", str(chunk_minutes*60), "-f", "segment", str(pattern)])
    return sorted(chunks.glob("chunk_*.mp4"))


def extract_frames(chunk: Path, outdir: Path, interval_sec: int) -> list[Path]:
    frame_dir = outdir / "frames" / chunk.stem
    frame_dir.mkdir(parents=True, exist_ok=True)
    run(["ffmpeg", "-y", "-i", str(chunk), "-vf", f"fps=1/{interval_sec}", str(frame_dir / "frame_%05d.jpg")])
    return sorted(frame_dir.glob("*.jpg"))


def write_ai_packet(video: Path, chunk: Path, frames: list[Path], outdir: Path) -> Path:
    packet = {
        "video_name": video.name,
        "video_sha256": sha256_file(video),
        "chunk": chunk.name,
        "frames": [{"image": str(p), "ocr_text": "", "note": "OCR未実行。必要に応じてPaddleOCR/Tesseractで補完"} for p in frames],
        "instruction": "prompts/opencodego_main_prompt.mdを使い、操作手順書チャンクを生成する"
    }
    packet_path = outdir / "ai_packets" / f"{chunk.stem}.json"
    packet_path.parent.mkdir(parents=True, exist_ok=True)
    packet_path.write_text(json.dumps(packet, ensure_ascii=False, indent=2), encoding="utf-8")
    return packet_path


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("video")
    ap.add_argument("--out", default="outputs/run_auto_manual")
    ap.add_argument("--chunk-minutes", type=int, default=5)
    ap.add_argument("--frame-interval", type=int, default=2)
    args = ap.parse_args()
    video = Path(args.video).resolve()
    outdir = Path(args.out).resolve()
    outdir.mkdir(parents=True, exist_ok=True)
    if not video.exists():
        raise FileNotFoundError(video)
    chunks = split_video(video, outdir, args.chunk_minutes)
    packets = []
    for chunk in chunks:
        frames = extract_frames(chunk, outdir, args.frame_interval)
        packets.append(str(write_ai_packet(video, chunk, frames, outdir)))
    manifest = {"video": str(video), "packets": packets, "next_step": "OpenCodeGOで各packetを手順化し、final_merge_prompt.mdで統合"}
    (outdir / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
