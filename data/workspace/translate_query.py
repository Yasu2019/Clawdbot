#!/usr/bin/env python3
"""
translate_query.py — 日→英クエリ翻訳 CLI (RAG品質向上)
========================================================
使い方 (gateway コンテナ内):
  python3 /home/node/clawd/translate_query.py "公差解析のポイントを教えて"
  python3 /home/node/clawd/translate_query.py "FMEAの実施手順" --model qwen2.5-coder:7b
  echo "なぜ不良が発生したか" | python3 /home/node/clawd/translate_query.py -
  python3 /home/node/clawd/translate_query.py "CETOL6 の基本" --json

使い方 (ホストから):
  docker exec clawstack-unified-clawdbot-gateway-1 \
    python3 /home/node/clawd/translate_query.py "公差解析のポイント"

用途:
  RAG 検索前に日本語クエリを英語に変換することで検索精度を向上させる。
  特に CETOL6/FEM ドキュメント (英語) への検索に有効。
"""

import argparse
import json
import os
import sys
import urllib.request
import urllib.error

OLLAMA_BASE = "http://ollama:11434"
DEFAULT_MODEL = os.getenv("OLLAMA_GEN_MODEL", "qwen3:8b")

SYSTEM_PROMPT = """\
You are a technical translation assistant specialized in manufacturing engineering, \
quality management, and CAE/CAD/simulation terminology.

Your task: Translate the given Japanese technical query into English, optimized for \
searching in English-language technical documentation.

Rules:
- Output ONLY the English translation. No explanation, no Japanese, no extra text.
- Keep technical terms (FMEA, CETOL, FEM, IATF, etc.) as-is.
- Make the translation suitable for document search (clear, specific, keyword-rich).
- If the input is already in English, output it unchanged.
"""


def translate(query: str, model: str = DEFAULT_MODEL, timeout: int = 30) -> str:
    body = {
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user",   "content": query},
        ],
        "stream": False,
        "options": {"temperature": 0.1},
    }
    data = json.dumps(body).encode()
    req = urllib.request.Request(
        f"{OLLAMA_BASE}/api/chat",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            result = json.loads(resp.read())
            return result["message"]["content"].strip()
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"Ollama HTTP {e.code}: {e.read().decode()[:100]}")
    except Exception as e:
        raise RuntimeError(str(e))


def main():
    parser = argparse.ArgumentParser(description="日→英クエリ翻訳 (RAG品質向上)")
    parser.add_argument("query", help="翻訳するクエリ (- で stdin から読む)")
    parser.add_argument("--model",   "-m", default=DEFAULT_MODEL,
                        help=f"使用モデル (default: {DEFAULT_MODEL})")
    parser.add_argument("--timeout", "-t", type=int, default=30, help="タイムアウト秒")
    parser.add_argument("--json",    "-j", action="store_true",   help="JSON 出力")
    parser.add_argument("--quiet",   "-q", action="store_true",   help="翻訳結果のみ出力")
    args = parser.parse_args()

    # stdin 対応
    if args.query == "-":
        query = sys.stdin.read().strip()
    else:
        query = args.query.strip()

    if not query:
        print("ERROR: クエリが空です", file=sys.stderr)
        sys.exit(1)

    try:
        translated = translate(query, args.model, args.timeout)
    except RuntimeError as e:
        print(f"[ERROR] {e}", file=sys.stderr)
        sys.exit(1)

    if args.json:
        print(json.dumps({"original": query, "translated": translated, "model": args.model},
                         ensure_ascii=False, indent=2))
    elif args.quiet:
        print(translated)
    else:
        print(f"[JP] {query}")
        print(f"[EN] {translated}")


if __name__ == "__main__":
    main()
