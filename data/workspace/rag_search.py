#!/usr/bin/env python3
"""
rag_search.py - Knowledge Base RAG Search for OpenClaw Agent
Usage: python3 /home/node/clawd/rag_search.py "your question here" [--collection universal_knowledge|iatf_knowledge] [--top 5] [--translate]
"""
import sys
import argparse
import requests

# === Endpoint config (Docker internal network) ===
INFINITY_URL      = "http://infinity:7997/embeddings"
OLLAMA_EMBED_URL  = "http://ollama:11434/api/embeddings"
OLLAMA_CHAT_URL   = "http://ollama:11434/api/chat"
QDRANT_URL        = "http://qdrant:6333"
TRANSLATE_MODEL   = "qwen2.5-coder:7b"
TRANSLATE_SYSTEM  = (
    "You are a technical translation assistant. Translate the Japanese query to English "
    "for searching English-language engineering documents. Output ONLY the English "
    "translation, no explanation. Keep technical terms (FMEA, CETOL, FEM, IATF) unchanged."
)

COLLECTIONS = {
    "universal_knowledge": {
        "embed_fn": "infinity",
        "model": "mixedbread-ai/mxbai-embed-large-v1",
        "dim": 1024,
        "desc": "PD知識・FMEA・公差・FEM・5Why・書籍ノウハウ",
    },
    "iatf_knowledge": {
        "embed_fn": "ollama",
        "model": "nomic-embed-text",
        "dim": 768,
        "desc": "IATF 16949 品質マネジメントシステム",
    },
}


def embed_infinity(text: str, model: str) -> list:
    resp = requests.post(INFINITY_URL, json={"model": model, "input": [text]}, timeout=30)
    resp.raise_for_status()
    return resp.json()["data"][0]["embedding"]


def embed_ollama(text: str, model: str) -> list:
    resp = requests.post(OLLAMA_EMBED_URL, json={"model": model, "prompt": text}, timeout=30)
    resp.raise_for_status()
    return resp.json()["embedding"]


def translate_to_english(query: str) -> str:
    resp = requests.post(OLLAMA_CHAT_URL, json={
        "model": TRANSLATE_MODEL,
        "messages": [
            {"role": "system", "content": TRANSLATE_SYSTEM},
            {"role": "user",   "content": query},
        ],
        "stream": False,
        "options": {"temperature": 0.1},
    }, timeout=30)
    resp.raise_for_status()
    return resp.json()["message"]["content"].strip()


def search_qdrant(collection: str, vector: list, top_k: int) -> list:
    url = f"{QDRANT_URL}/collections/{collection}/points/search"
    resp = requests.post(url, json={
        "vector": vector,
        "limit": top_k,
        "with_payload": True,
    }, timeout=15)
    resp.raise_for_status()
    return resp.json()["result"]


def main():
    parser = argparse.ArgumentParser(description="RAG Knowledge Search")
    parser.add_argument("query", help="Search query (Japanese OK)")
    parser.add_argument("--collection", "-c", default="universal_knowledge",
                        choices=list(COLLECTIONS.keys()),
                        help="Qdrant collection to search")
    parser.add_argument("--top", "-n", type=int, default=5, help="Number of results")
    parser.add_argument("--translate", "-T", action="store_true",
                        help="日本語クエリを英語翻訳してから検索 (CETOL/FEM系に有効)")
    args = parser.parse_args()

    col_cfg = COLLECTIONS[args.collection]
    query = args.query

    # 日→英翻訳オプション
    if args.translate:
        try:
            en_query = translate_to_english(query)
            print(f"[RAG] 翻訳: {query}")
            print(f"[RAG]   →  {en_query}")
            query = en_query
        except Exception as e:
            print(f"[WARN] 翻訳失敗 ({e})、元のクエリで検索します", file=sys.stderr)

    print(f"[RAG] コレクション: {args.collection} ({col_cfg['desc']})")
    print(f"[RAG] クエリ: {query}")
    print()

    # 1. Embed query
    try:
        if col_cfg["embed_fn"] == "infinity":
            vector = embed_infinity(query, col_cfg["model"])
        else:
            vector = embed_ollama(query, col_cfg["model"])
    except Exception as e:
        print(f"[ERROR] 埋め込み失敗: {e}", file=sys.stderr)
        sys.exit(1)

    # 2. Search Qdrant
    try:
        results = search_qdrant(args.collection, vector, args.top)  # type: ignore[arg-type]
    except Exception as e:
        print(f"[ERROR] Qdrant検索失敗: {e}", file=sys.stderr)
        sys.exit(1)

    if not results:
        print("該当する知識が見つかりませんでした。")
        sys.exit(0)

    # 3. Print results
    print(f"=== 検索結果 (上位{len(results)}件) ===\n")
    for i, r in enumerate(results, 1):
        payload = r.get("payload", {})
        score = r.get("score", 0)
        source = payload.get("source", payload.get("file", "不明"))
        text = payload.get("text", payload.get("content", ""))
        page = payload.get("page", "")
        page_str = f" / ページ {page}" if page else ""

        print(f"--- [{i}] スコア: {score:.4f} | ソース: {source}{page_str} ---")
        print(text[:800])
        print()


if __name__ == "__main__":
    main()
