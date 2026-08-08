# -*- coding: utf-8 -*-
"""取り込んだリポジトリ資料をベクタ検索する。2026-08-08 導入。

ingest_repo_docs.py で clawstack_docs に入れたノウハウ・トラブル履歴・
プロトコルを、自然文で引くための最小ツール。取り込みが「入れただけ」で
終わらないよう、検索できることを確認する用途も兼ねる。

usage:
  python scripts/search_docs.py "WSLのDockerストレージが壊れた時の対処"
  python scripts/search_docs.py "GPU VRAM 競合" --top 8
  python scripts/search_docs.py "ポート 8188" --collection universal_knowledge
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.request

sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # P023

QDRANT = os.getenv("QDRANT_URL", "http://localhost:6333")
OLLAMA = os.getenv("OLLAMA_URL", "http://localhost:11434")
EMBED_MODEL = os.getenv("EMBED_MODEL", "mxbai-embed-large")
COLLECTION = os.getenv("DOCS_COLLECTION", "clawstack_docs")
MAX_QUERY_CHARS = 450  # 埋め込みモデルの512トークン上限に合わせる


def _post(url: str, obj: dict, timeout: int = 300) -> dict:
    req = urllib.request.Request(
        url, data=json.dumps(obj).encode("utf-8"),
        headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


def embed(text: str) -> list[float]:
    opts = {"num_gpu": int(os.getenv("EMBED_NUM_GPU", "0"))}
    d = _post(f"{OLLAMA}/api/embed",
              {"model": EMBED_MODEL, "input": [text[:MAX_QUERY_CHARS]], "options": opts})
    vs = d.get("embeddings")
    if not vs:
        raise RuntimeError(f"埋め込み取得に失敗: {str(d)[:200]}")
    return vs[0]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("query")
    ap.add_argument("--top", type=int, default=5)
    ap.add_argument("--collection", default=COLLECTION)
    ap.add_argument("--chars", type=int, default=320, help="本文の表示文字数")
    a = ap.parse_args()

    vec = embed(a.query)
    res = _post(f"{QDRANT}/collections/{a.collection}/points/search",
                {"vector": vec, "limit": a.top, "with_payload": True})
    hits = res.get("result", [])
    if not hits:
        print("該当なし")
        return 1
    print(f"検索: {a.query}  ({a.collection} / 上位{len(hits)}件)\n")
    for i, h in enumerate(hits, 1):
        pl = h.get("payload", {})
        path = pl.get("path") or pl.get("source") or "-"
        head = pl.get("heading") or ""
        body = (pl.get("text") or "").replace("\n", " ")[:a.chars]
        print(f"[{i}] score={h.get('score'):.4f}  {path}")
        if head:
            print(f"    見出し: {head}")
        print(f"    {body}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
