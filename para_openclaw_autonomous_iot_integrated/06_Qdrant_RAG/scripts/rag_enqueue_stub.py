#!/usr/bin/env python3
# Stub: adapt to existing Clawstack ingestion pipeline.
# Intended behavior: scan PARA folders, convert docs to text/markdown, enqueue embeddings into Qdrant.
from pathlib import Path
import argparse, json

if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--base", required=True)
    args = ap.parse_args()
    base = Path(args.base) / "02_PARA_Vault"
    files = [str(p) for p in base.rglob("*") if p.is_file()]
    print(json.dumps({"enqueue_candidates": len(files), "sample": files[:20]}, ensure_ascii=False, indent=2))
