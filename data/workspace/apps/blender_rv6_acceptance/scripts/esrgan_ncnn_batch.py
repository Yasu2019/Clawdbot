#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ESRGAN NCNN Vulkan batch wrapper."""
import sys
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import argparse, subprocess
from pathlib import Path

def run_upscale(exe: str, input_dir: Path, output_dir: Path, scale: int, model: str):
    output_dir.mkdir(parents=True, exist_ok=True)
    images = sorted([p for p in input_dir.iterdir() if p.suffix.lower() in [".png", ".jpg", ".jpeg", ".webp"]])
    if not images: raise FileNotFoundError(f"No images found in {input_dir}")
    for img in images:
        out = output_dir / f"{img.stem}_x{scale}.png"
        cmd = [exe, "-i", str(img), "-o", str(out), "-s", str(scale), "-n", model]
        print("RUN:", " ".join(cmd)); subprocess.run(cmd, check=True)

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--input", required=True); ap.add_argument("--output", required=True)
    ap.add_argument("--exe", default="realesrgan-ncnn-vulkan"); ap.add_argument("--scale", type=int, default=2); ap.add_argument("--model", default="realesrgan-x4plus")
    a = ap.parse_args(); run_upscale(a.exe, Path(a.input), Path(a.output), a.scale, a.model)
if __name__ == "__main__": main()
