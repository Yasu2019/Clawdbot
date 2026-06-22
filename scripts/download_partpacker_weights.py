# -*- coding: utf-8 -*-
import sys
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import argparse
import shutil
from pathlib import Path

from huggingface_hub import hf_hub_download


def main() -> int:
    parser = argparse.ArgumentParser(description="Download NVIDIA PartPacker weights.")
    parser.add_argument("--repo", default="nvidia/PartPacker")
    parser.add_argument("--file", choices=["vae.pt", "flow.pt"], required=True)
    parser.add_argument("--out-dir", default="D:/AI/PartPacker/pretrained")
    args = parser.parse_args()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    src = hf_hub_download(args.repo, args.file, resume_download=True)
    dst = out_dir / args.file
    shutil.copy2(src, dst)
    print(f"{args.file} {dst} {dst.stat().st_size}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
