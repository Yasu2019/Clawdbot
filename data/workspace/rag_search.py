#!/usr/bin/env python3
"""
rag_search.py - Knowledge Base RAG Search for OpenClaw Agent
Usage: python3 /home/node/clawd/rag_search.py "your question here" [--collection universal_knowledge|iatf_knowledge] [--top 5] [--translate]
"""
from __future__ import annotations

import argparse
import os
import sys
from typing import Iterable

import requests


INFINITY_URL = os.getenv("INFINITY_URL", "http://infinity:7997/embeddings")
OLLAMA_EMBED_URL = os.getenv("OLLAMA_EMBED_URL", "http://ollama:11434/api/embeddings")
OLLAMA_CHAT_URL = os.getenv("OLLAMA_CHAT_URL", "http://ollama:11434/api/chat")
QDRANT_URL = os.getenv("QDRANT_URL", "http://qdrant:6333")
TRANSLATE_MODEL = os.getenv("OLLAMA_GEN_MODEL", "qwen3:8b")
TRANSLATE_SYSTEM = (
    "You are a technical translation assistant. Translate the Japanese query to English "
    "for searching English-language engineering documents. Output ONLY the English "
    "translation, no explanation. Keep technical terms (FMEA, CETOL, FEM, IATF) unchanged."
)

COLLECTIONS = {
    "universal_knowledge": {
        "embed_fn": "infinity",
        "model": "mixedbread-ai/mxbai-embed-large-v1",
        "dim": 1024,
        "desc": "PD knowledge, FMEA, tolerance, FEM, 5Why, books and internal manuals",
    },
    "iatf_knowledge": {
        "embed_fn": "ollama",
        "model": "nomic-embed-text",
        "dim": 768,
        "desc": "IATF 16949 quality management system knowledge",
    },
}

LAST_QDRANT_URL = QDRANT_URL


def candidate_urls(primary: str, fallbacks: Iterable[str]) -> list[str]:
    values: list[str] = []
    for item in [primary, *fallbacks]:
        value = (item or "").strip()
        if value and value not in values:
            values.append(value)
    return values


def qdrant_candidates() -> list[str]:
    return candidate_urls(
        QDRANT_URL,
        [
            "http://qdrant:6333",
            "http://host.docker.internal:6333",
            "http://127.0.0.1:6333",
        ],
    )


def infinity_embeddings_url() -> str:
    base = INFINITY_URL.rstrip("/")
    if base.endswith("/embeddings"):
        return base
    return f"{base}/embeddings"


def embed_infinity(text: str, model: str) -> list[float]:
    resp = requests.post(infinity_embeddings_url(), json={"model": model, "input": [text]}, timeout=30)
    resp.raise_for_status()
    return resp.json()["data"][0]["embedding"]


def embed_ollama(text: str, model: str) -> list[float]:
    resp = requests.post(OLLAMA_EMBED_URL, json={"model": model, "prompt": text}, timeout=30)
    resp.raise_for_status()
    return resp.json()["embedding"]


def translate_to_english(query: str) -> str:
    resp = requests.post(
        OLLAMA_CHAT_URL,
        json={
            "model": TRANSLATE_MODEL,
            "messages": [
                {"role": "system", "content": TRANSLATE_SYSTEM},
                {"role": "user", "content": query},
            ],
            "stream": False,
            "options": {"temperature": 0.1},
        },
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()["message"]["content"].strip()


def search_qdrant(collection: str, vector: list[float], top_k: int) -> list[dict]:
    global LAST_QDRANT_URL
    errors: list[str] = []
    for base_url in qdrant_candidates():
        try:
            url = f"{base_url}/collections/{collection}/points/search"
            resp = requests.post(
                url,
                json={"vector": vector, "limit": top_k, "with_payload": True},
                timeout=15,
            )
            resp.raise_for_status()
            LAST_QDRANT_URL = base_url
            return resp.json()["result"]
        except Exception as exc:
            errors.append(f"{base_url}: {exc}")
    raise RuntimeError(" | ".join(errors))


def main() -> None:
    parser = argparse.ArgumentParser(description="RAG Knowledge Search")
    parser.add_argument("query", help="Search query (Japanese OK)")
    parser.add_argument(
        "--collection",
        "-c",
        default="universal_knowledge",
        choices=list(COLLECTIONS.keys()),
        help="Qdrant collection to search",
    )
    parser.add_argument("--top", "-n", type=int, default=5, help="Number of results")
    parser.add_argument(
        "--translate",
        "-T",
        action="store_true",
        help="Translate Japanese query to English first (mainly useful for CETOL/FEM books)",
    )
    args = parser.parse_args()

    col_cfg = COLLECTIONS[args.collection]
    query = args.query

    if args.translate:
        try:
            en_query = translate_to_english(query)
            print(f"[RAG] translated from: {query}")
            print(f"[RAG] translated to  : {en_query}")
            query = en_query
        except Exception as exc:
            print(f"[WARN] translation failed ({exc}); using original query", file=sys.stderr)

    print(f"[RAG] collection: {args.collection} ({col_cfg['desc']})")
    print(f"[RAG] query: {query}")
    print(f"[RAG] Qdrant candidates: {', '.join(qdrant_candidates())}")
    print()

    try:
        if col_cfg["embed_fn"] == "infinity":
            vector = embed_infinity(query, col_cfg["model"])
        else:
            vector = embed_ollama(query, col_cfg["model"])
    except Exception as exc:
        print(f"[ERROR] embedding failed: {exc}", file=sys.stderr)
        raise SystemExit(1)

    try:
        results = search_qdrant(args.collection, vector, args.top)
    except Exception as exc:
        print(f"[ERROR] Qdrant search failed: {exc}", file=sys.stderr)
        raise SystemExit(1)

    print(f"[RAG] Qdrant endpoint used: {LAST_QDRANT_URL}\n")

    if not results:
        print("No relevant knowledge found.")
        raise SystemExit(0)

    print(f"=== Search results ({len(results)} hits) ===\n")
    for index, result in enumerate(results, 1):
        payload = result.get("payload", {})
        score = result.get("score", 0)
        source = payload.get("source", payload.get("file", "unknown"))
        text = payload.get("text", payload.get("content", ""))
        page = payload.get("page", "")
        page_str = f" / page {page}" if page else ""

        print(f"--- [{index}] score={score:.4f} | source: {source}{page_str} ---")
        print(text[:800])
        print()


if __name__ == "__main__":
    main()
