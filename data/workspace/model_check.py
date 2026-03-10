#!/usr/bin/env python3
"""
model_check.py — モデル疎通確認 CLI
=====================================
使い方 (gateway コンテナ内):
  python3 /home/node/clawd/model_check.py
  python3 /home/node/clawd/model_check.py --ollama-only
  python3 /home/node/clawd/model_check.py --json

使い方 (ホストから):
  docker exec clawstack-unified-clawdbot-gateway-1 python3 /home/node/clawd/model_check.py
"""

import argparse
import json
import sys
import time
import urllib.request
import urllib.error
from datetime import datetime, timezone, timedelta

JST = timezone(timedelta(hours=9))

LITELLM_BASE = "http://litellm:4000"
OLLAMA_BASE  = "http://ollama:11434"
INFINITY_URL = "http://infinity:7997"

# LiteLLM 経由でテストするモデル (実際の短いプロンプト)
LITELLM_TEST_MODELS = [
    {"id": "google/gemini-2.5-flash",   "label": "Gemini 2.5 Flash (primary)"},
    {"id": "ollama/qwen2.5-coder:7b",   "label": "qwen2.5-coder:7b (fallback)"},
]

# Embedding モデルのテスト
EMBED_TESTS = [
    {
        "label": "Infinity mxbai-embed-large-v1",
        "url": f"{INFINITY_URL}/embeddings",
        "body": {"model": "mixedbread-ai/mxbai-embed-large-v1", "input": ["ping"]},
        "dim_expected": 1024,
    },
    {
        "label": "Ollama nomic-embed-text",
        "url": f"{OLLAMA_BASE}/api/embeddings",
        "body": {"model": "nomic-embed-text", "prompt": "ping"},
        "key": "embedding",
        "dim_expected": 768,
    },
]

GREEN  = "\033[92m"
RED    = "\033[91m"
YELLOW = "\033[93m"
RESET  = "\033[0m"
BOLD   = "\033[1m"


def c(text, color): return f"{color}{text}{RESET}"


def http_post(url, body, timeout=20, headers=None):
    data = json.dumps(body).encode()
    h = {"Content-Type": "application/json"}
    if headers:
        h.update(headers)
    req = urllib.request.Request(url, data=data, headers=h, method="POST")
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read()), int((time.time() - t0) * 1000)


def http_get(url, timeout=5):
    t0 = time.time()
    req = urllib.request.Request(url)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read()), int((time.time() - t0) * 1000)


def check_ollama_list():
    """Ollama モデル一覧取得。"""
    try:
        data, lat = http_get(f"{OLLAMA_BASE}/api/tags", timeout=5)
        models = [m["name"] for m in data.get("models", [])]
        return {"ok": True, "models": models, "latency_ms": lat}
    except Exception as e:
        return {"ok": False, "models": [], "error": str(e)[:80]}


def check_litellm_model(model_id, label, timeout=30):
    """LiteLLM 経由で短い補完テスト。"""
    try:
        body = {
            "model": model_id,
            "messages": [{"role": "user", "content": "Reply with just: OK"}],
            "max_tokens": 5,
        }
        data, lat = http_post(
            f"{LITELLM_BASE}/v1/chat/completions", body, timeout=timeout,
            headers={"Authorization": "Bearer local-dev-key"},
        )
        reply = data["choices"][0]["message"]["content"].strip()
        return {"ok": True, "reply": reply[:20], "latency_ms": lat}
    except urllib.error.HTTPError as e:
        body_bytes = e.read()[:200]
        return {"ok": False, "error": f"HTTP {e.code}: {body_bytes.decode(errors='replace')[:80]}"}
    except Exception as e:
        return {"ok": False, "error": str(e)[:80]}


def check_embed(test: dict, timeout=15):
    """embedding テスト。"""
    try:
        data, lat = http_post(test["url"], test["body"], timeout=timeout)
        # Infinity: data["data"][0]["embedding"] / Ollama: data["embedding"]
        if "key" in test:
            vec = data[test["key"]]
        else:
            vec = data["data"][0]["embedding"]
        dim = len(vec)
        ok  = dim == test["dim_expected"]
        return {"ok": ok, "dim": dim, "expected": test["dim_expected"], "latency_ms": lat}
    except Exception as e:
        return {"ok": False, "error": str(e)[:80]}


def main():
    parser = argparse.ArgumentParser(description="Clawstack モデル疎通確認")
    parser.add_argument("--ollama-only", action="store_true", help="Ollama 一覧のみ確認")
    parser.add_argument("--no-llm",     action="store_true", help="LLM 補完テストをスキップ")
    parser.add_argument("--no-embed",   action="store_true", help="embedding テストをスキップ")
    parser.add_argument("--json", "-j", action="store_true", help="JSON 出力")
    args = parser.parse_args()

    now = datetime.now(JST).strftime("%Y-%m-%d %H:%M:%S JST")
    results = {}

    if not args.json:
        print(f"\n{BOLD}=== Model Check — {now} ==={RESET}\n")

    # 1. Ollama モデル一覧
    print("  [Ollama] モデル一覧 ..." if not args.json else "", flush=True, end="")
    r = check_ollama_list()
    results["ollama_list"] = r
    if not args.json:
        if r["ok"]:
            print(f"\r  {c('✓', GREEN)} Ollama  {r['latency_ms']}ms  "
                  f"models: {', '.join(r['models']) or 'none'}")
        else:
            print(f"\r  {c('✗', RED)} Ollama  {r.get('error','?')}")

    if args.ollama_only:
        if args.json:
            print(json.dumps(results, ensure_ascii=False, indent=2))
        return

    # 2. LLM 補完テスト
    if not args.no_llm:
        print() if not args.json else None
        print(f"  {BOLD}[LLM] 補完テスト{RESET}" if not args.json else "")
        results["llm"] = {}
        for m in LITELLM_TEST_MODELS:
            if not args.json:
                print(f"    → {m['label']} ...", end="", flush=True)
            r = check_litellm_model(m["id"], m["label"])
            results["llm"][m["id"]] = r
            if not args.json:
                if r["ok"]:
                    print(f"\r    {c('✓', GREEN)} {m['label']:<40}  {r['latency_ms']}ms  reply: \"{r['reply']}\"")
                else:
                    print(f"\r    {c('✗', RED)} {m['label']:<40}  {r['error']}")

    # 3. Embedding テスト
    if not args.no_embed:
        print() if not args.json else None
        print(f"  {BOLD}[Embedding] テスト{RESET}" if not args.json else "")
        results["embedding"] = {}
        for t in EMBED_TESTS:
            if not args.json:
                print(f"    → {t['label']} ...", end="", flush=True)
            r = check_embed(t)
            results["embedding"][t["label"]] = r
            if not args.json:
                if r["ok"]:
                    print(f"\r    {c('✓', GREEN)} {t['label']:<45}  {r['latency_ms']}ms  dim={r['dim']}")
                else:
                    print(f"\r    {c('✗', RED)} {t['label']:<45}  {r.get('error','?')}")

    # サマリー
    all_ok = all(
        (v["ok"] if isinstance(v, dict) and "ok" in v else
         all(vv["ok"] for vv in v.values()))
        for v in results.values()
    )

    if args.json:
        print(json.dumps({"timestamp": now, "all_ok": all_ok, "checks": results},
                         ensure_ascii=False, indent=2))
    else:
        print()
        if all_ok:
            print(f"  {c('全チェック OK', GREEN)}\n")
        else:
            print(f"  {c('一部チェック失敗', RED)}\n")
            sys.exit(1)


if __name__ == "__main__":
    main()
