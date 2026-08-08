# -*- coding: utf-8 -*-
"""リポジトリのMarkdown資料(ノウハウ・理論・トラブル履歴・プロトコル)をQdrantへ取り込む。

2026-08-08 導入。背景(実測):
  universal_knowledge 1236点の内訳は paperless 1234 / rl_anything_skill 2 で、
  リポジトリのMDは **0件** だった。docs・protocols・memory・obsidian_vault 等
  8000超のMDがどのベクタDBにも入っておらず、過去の失敗知見を検索できない状態。
  さらに埋め込みサーバ(infinity)のコンテナが存在せず、LiteLLM /embeddings は500、
  LightRAG のchunks/entitiesも0件だった。そこで稼働中のOllamaで同一モデル
  (mxbai-embed-large / 1024次元)を使い、既存コレクションと次元を揃える。

設計:
  - 冪等: point ID は (相対パス + チャンク番号) のUUID5。再実行で重複しない。
  - 差分更新: マニフェストにファイルのsha256を記録し、変更が無ければスキップ。
  - 再開可能: 途中終了してもマニフェストの分だけ飛ばして続きから。
  - 見出しを保持したチャンク分割(Markdownの構造を壊さない)。

usage:
  python scripts/ingest_repo_docs.py --dry-run
  python scripts/ingest_repo_docs.py --roots docs protocols
  python scripts/ingest_repo_docs.py --limit 200
  python scripts/ingest_repo_docs.py --stats
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import time
import urllib.request
import uuid
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # P023

REPO = Path(r"D:\Clawdbot_Docker_20260125")
QDRANT = os.getenv("QDRANT_URL", "http://localhost:6333")
OLLAMA = os.getenv("OLLAMA_URL", "http://localhost:11434")
EMBED_MODEL = os.getenv("EMBED_MODEL", "mxbai-embed-large")  # 1024次元(既存コレクションと同じ)
COLLECTION = os.getenv("DOCS_COLLECTION", "clawstack_docs")
VECTOR_SIZE = 1024
MANIFEST = REPO / "data" / "state" / "ingest_repo_docs_manifest.json"
NAMESPACE = uuid.UUID("6f1d0c9a-3b2e-4f77-9a10-2c5b8e4d7a01")

# 取り込み対象。生成物だらけのディレクトリは既定では入れない(ノイズになるため)。
DEFAULT_ROOTS = [
    "docs",
    "protocols",
    "projects",
    "clawstack_v2",
    "services",
    "data/workspace/memory",
    "data/workspace/knowledge",
    "data/workspace/obsidian_vault",
]
EXTRA_FILES = ["CLAUDE.md", "data/workspace/PROMISES.md", "ByteRover.md"]

EXCLUDE_PARTS = ("node_modules", "site-packages", ".venv", ".git", "graphify-out",
                 "__pycache__", "ComfyUI_app", "dist", "backups")
MIN_CHARS = 120          # これ未満のファイルは索引価値が低い
# mxbai-embed-large の入力上限は512トークン。日本語は概ね1文字=1トークンのため、
# 実測で「500文字OK / 600文字はHTTP 500」だった。安全側で450文字に切る。
CHUNK_CHARS = 450
CHUNK_OVERLAP = 80
EMBED_TIMEOUT = 300
EMBED_SUB_BATCH = 16      # 1リクエストあたりのチャンク数(タイムアウト回避)


# ------------------------------------------------------------------ helpers

def _post(url: str, obj: dict, timeout: int = 60) -> dict:
    req = urllib.request.Request(
        url, data=json.dumps(obj).encode("utf-8"),
        headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


def _put(url: str, obj: dict, timeout: int = 60) -> dict:
    req = urllib.request.Request(
        url, data=json.dumps(obj).encode("utf-8"),
        headers={"Content-Type": "application/json"}, method="PUT")
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


def _get(url: str, timeout: int = 30) -> dict:
    with urllib.request.urlopen(url, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


def embed_batch(texts: list[str]) -> list[list[float]]:
    """/api/embed のバッチ入力を使う(1件ずつの /api/embeddings より速い)。

    埋め込みは既定でCPU実行(num_gpu=0)。RL学習/CAEがGPUリースを保持している最中に
    VRAMを奪って学習を落とさないため(gpu_arbiterと同じ趣旨)。
    GPUが空いている時に速度が要るなら EMBED_NUM_GPU=999 を指定する。
    """
    opts = {"num_gpu": int(os.getenv("EMBED_NUM_GPU", "0"))}
    safe = [t[:CHUNK_CHARS] for t in texts]  # 上限超過はHTTP 500になるため必ず切る
    # 1リクエストに全チャンクを渡すとタイムアウトする(実測 約6秒/件のため
    # 312チャンクのファイルで2000秒必要になり300秒上限を超える)。小分けにする。
    out: list[list[float]] = []
    for i in range(0, len(safe), EMBED_SUB_BATCH):
        part = safe[i:i + EMBED_SUB_BATCH]
        d = _post(f"{OLLAMA}/api/embed",
                  {"model": EMBED_MODEL, "input": part, "options": opts},
                  timeout=EMBED_TIMEOUT)
        vs = d.get("embeddings")
        if not vs or len(vs) != len(part):
            raise RuntimeError(f"埋め込み取得に失敗: {str(d)[:200]}")
        out.extend(vs)
    return out


def sha256_text(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8", "replace")).hexdigest()


def iter_docs(roots: list[str]) -> list[Path]:
    seen: set[Path] = set()
    out: list[Path] = []
    for r in roots:
        base = REPO / r
        if base.is_file() and base.suffix.lower() == ".md":
            if base not in seen:
                seen.add(base); out.append(base)
            continue
        if not base.is_dir():
            continue
        for p in base.rglob("*.md"):
            if any(part in EXCLUDE_PARTS for part in p.parts):
                continue
            if p in seen:
                continue
            seen.add(p); out.append(p)
    return sorted(out)


def split_markdown(text: str) -> list[tuple[str, str]]:
    """(見出しパンくず, 本文) のリスト。見出し構造を保ったまま分割する。"""
    lines = text.splitlines()
    sections: list[tuple[str, list[str]]] = []
    crumbs: list[str] = []
    cur: list[str] = []
    cur_crumb = ""
    for ln in lines:
        m = re.match(r"^(#{1,6})\s+(.*)$", ln)
        if m:
            if cur:
                sections.append((cur_crumb, cur)); cur = []
            level = len(m.group(1)); title = m.group(2).strip()
            crumbs = crumbs[:level - 1] + [title]
            cur_crumb = " > ".join(crumbs)
        else:
            cur.append(ln)
    if cur:
        sections.append((cur_crumb, cur))

    chunks: list[tuple[str, str]] = []
    for crumb, body_lines in sections:
        body = "\n".join(body_lines).strip()
        if not body:
            continue
        if len(body) <= CHUNK_CHARS:
            chunks.append((crumb, body)); continue
        i = 0
        while i < len(body):
            piece = body[i:i + CHUNK_CHARS]
            chunks.append((crumb, piece))
            if i + CHUNK_CHARS >= len(body):
                break
            i += CHUNK_CHARS - CHUNK_OVERLAP
    return chunks


def ensure_collection() -> None:
    try:
        _get(f"{QDRANT}/collections/{COLLECTION}")
        return
    except Exception:
        pass
    _put(f"{QDRANT}/collections/{COLLECTION}",
         {"vectors": {"size": VECTOR_SIZE, "distance": "Cosine"}})
    print(f"コレクションを作成しました: {COLLECTION} ({VECTOR_SIZE}次元 / Cosine)")


def load_manifest() -> dict:
    try:
        return json.loads(MANIFEST.read_text(encoding="utf-8"))
    except Exception:
        return {"schema": "clawstack.ingest_repo_docs.v1", "files": {}}


def save_manifest(m: dict) -> None:
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    tmp = MANIFEST.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(m, ensure_ascii=False, indent=1), encoding="utf-8")
    os.replace(tmp, MANIFEST)


def upsert(points: list[dict]) -> None:
    _put(f"{QDRANT}/collections/{COLLECTION}/points?wait=true",
         {"points": points}, timeout=180)


# --------------------------------------------------------------------- main

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--roots", nargs="*", default=None)
    ap.add_argument("--limit", type=int, default=0, help="処理するファイル数の上限(0=無制限)")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--stats", action="store_true", help="コレクションの現状だけ表示")
    ap.add_argument("--force", action="store_true", help="変更なしでも再取り込みする")
    ap.add_argument("--batch", type=int, default=32)
    a = ap.parse_args()

    if a.stats:
        try:
            info = _get(f"{QDRANT}/collections/{COLLECTION}")["result"]
            print(f"{COLLECTION}: {info.get('points_count')} 点 / "
                  f"{info['config']['params']['vectors']}")
        except Exception as e:
            print(f"{COLLECTION} は未作成か取得できません: {e}")
        m = load_manifest()
        print(f"マニフェスト記録済みファイル: {len(m.get('files', {}))}")
        return 0

    roots = a.roots if a.roots else DEFAULT_ROOTS + EXTRA_FILES
    files = iter_docs(roots)
    print(f"対象ルート: {roots}")
    print(f"検出したMarkdown: {len(files)} 件")

    man = load_manifest()
    todo: list[tuple[Path, str, str]] = []
    skipped_small = 0
    for p in files:
        try:
            text = p.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue
        if len(text.strip()) < MIN_CHARS:
            skipped_small += 1
            continue
        rel = str(p.relative_to(REPO)).replace("\\", "/")
        h = sha256_text(text)
        if not a.force and man["files"].get(rel, {}).get("sha256") == h:
            continue
        todo.append((p, rel, text))
    print(f"小さすぎて除外: {skipped_small} 件 / 取り込み対象(新規・変更): {len(todo)} 件")

    if a.limit:
        todo = todo[:a.limit]
        print(f"--limit により {len(todo)} 件に制限")
    if a.dry_run:
        for p, rel, text in todo[:20]:
            print(f"  {rel}  ({len(text)} chars, {len(split_markdown(text))} chunks)")
        if len(todo) > 20:
            print(f"  ... 他 {len(todo)-20} 件")
        return 0
    if not todo:
        print("取り込む変更はありません。")
        return 0

    ensure_collection()
    t0 = time.time()
    done_files = 0
    done_chunks = 0
    buf: list[dict] = []
    for p, rel, text in todo:
        chunks = split_markdown(text)
        if not chunks:
            continue
        stat = p.stat()
        # 見出しパンくずを本文先頭に足すと検索一致率が上がる
        texts = [(f"{c}\n\n{b}" if c else b) for c, b in chunks]
        try:
            vecs = embed_batch(texts)
        except Exception as e:
            print(f"\n埋め込み失敗 {rel}: {e}")
            save_manifest(man)
            return 2
        for idx, payload_text in enumerate(texts):
            crumb = chunks[idx][0]
            vec = vecs[idx]
            pid = str(uuid.uuid5(NAMESPACE, f"{rel}#{idx}"))
            buf.append({
                "id": pid,
                "vector": vec,
                "payload": {
                    "source": "repo_md",
                    "path": rel,
                    "heading": crumb,
                    "chunk_index": idx,
                    "chunk_total": len(chunks),
                    "text": payload_text[:6000],
                    "modified": time.strftime("%Y-%m-%d %H:%M",
                                              time.localtime(stat.st_mtime)),
                    "ingested_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
                },
            })
            done_chunks += 1
        # ファイル単位で必ずflushしてからマニフェストに記録する。
        # 先に記録すると、未upsertのまま「取り込み済み」と誤認して恒久的に取りこぼす。
        if buf:
            upsert(buf); buf = []
        man["files"][rel] = {"sha256": sha256_text(text), "chunks": len(chunks),
                             "ingested_at": time.strftime("%Y-%m-%dT%H:%M:%S")}
        done_files += 1
        # 毎ファイル保存する。まとめ書きにすると、途中終了時に
        # upsert済みなのにマニフェスト未記録の分を再取り込みすることになる。
        # (二重起動でマニフェストを奪い合う事故も起きたため保存間隔は詰める)
        save_manifest(man)
        if done_files % 5 == 0:
            el = time.time() - t0
            rate = done_files / el * 60 if el else 0
            print(f"\r  {done_files}/{len(todo)} ファイル / {done_chunks} チャンク "
                  f"({rate:.0f} 件/分)", end="", flush=True)
    if buf:
        upsert(buf)
    save_manifest(man)
    print(f"\n完了: {done_files} ファイル / {done_chunks} チャンク "
          f"/ {time.time()-t0:.0f} 秒")
    try:
        info = _get(f"{QDRANT}/collections/{COLLECTION}")["result"]
        print(f"{COLLECTION} 総点数: {info.get('points_count')}")
    except Exception:
        pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
