#!/usr/bin/env python3
"""
clawstack_health.py — Clawstack 全サービス Health Check CLI
=============================================================
使い方 (gateway コンテナ内):
  python3 /home/node/clawd/clawstack_health.py
  python3 /home/node/clawd/clawstack_health.py --json
  python3 /home/node/clawd/clawstack_health.py --service ollama qdrant

使い方 (ホストから):
  docker exec clawstack-unified-clawdbot-gateway-1 python3 /home/node/clawd/clawstack_health.py
"""

import argparse
import json
import sys
import time
import urllib.request
import urllib.error
from datetime import datetime, timezone, timedelta

JST = timezone(timedelta(hours=9))

# ── サービス定義 ──────────────────────────────────────────────────────────────
SERVICES = [
    {
        "name": "ollama",
        "url": "http://ollama:11434/api/tags",
        "method": "GET",
        "expect_status": 200,
        "desc": "Ollama LLM Server",
        "detail_fn": lambda r: f"{len(r.get('models', []))} models",
    },
    {
        "name": "infinity",
        "url": "http://infinity:7997/health",
        "method": "GET",
        "expect_status": 200,
        "desc": "Infinity Embedding Server",
    },
    {
        "name": "qdrant",
        "url": "http://qdrant:6333/healthz",
        "method": "GET",
        "expect_status": 200,
        "desc": "Qdrant Vector DB",
    },
    {
        "name": "qdrant_collections",
        "url": "http://qdrant:6333/collections",
        "method": "GET",
        "expect_status": 200,
        "desc": "Qdrant Collections",
        "detail_fn": lambda r: ", ".join(
            c["name"] for c in r.get("result", {}).get("collections", [])
        ) or "none",
    },
    {
        "name": "litellm",
        "url": "http://litellm:4000/health",
        "method": "GET",
        "expect_status": 200,
        "desc": "LiteLLM Proxy",
    },
    {
        "name": "langfuse",
        "url": "http://langfuse:3000/api/public/health",
        "method": "GET",
        "expect_status": 200,
        "desc": "Langfuse Observability",
    },
    {
        "name": "n8n",
        "url": "http://n8n:5678/healthz",
        "method": "GET",
        "expect_status": 200,
        "desc": "n8n Workflow Engine",
    },
    {
        "name": "paperless",
        "url": "http://paperless:8000/api/",
        "method": "GET",
        "expect_status": [200, 401],  # 401 = 認証あり = 正常
        "desc": "Paperless-ngx DMS",
    },
    {
        "name": "minio",
        "url": "http://minio:9000/minio/health/live",
        "method": "GET",
        "expect_status": 200,
        "desc": "MinIO Object Storage",
    },
    {
        "name": "redis",
        "url": "http://redis:6379",
        "method": None,  # TCP check via socket
        "desc": "Redis Cache",
    },
    {
        "name": "clickhouse",
        "url": "http://clickhouse:8123/ping",
        "method": "GET",
        "expect_status": 200,
        "desc": "ClickHouse (Langfuse)",
    },
    {
        "name": "searxng",
        "url": "http://searxng:8080/healthz",
        "method": "GET",
        "expect_status": 200,
        "desc": "SearXNG Search",
    },
    {
        "name": "docling",
        "url": "http://docling:5001/health",
        "method": "GET",
        "expect_status": [200, 404],
        "desc": "Docling PDF Converter",
    },
    {
        "name": "openclaw",
        "url": "http://localhost:18789/health",
        "method": "GET",
        "expect_status": [200, 404],
        "desc": "OpenClaw Gateway (self)",
    },
]


# ── チェック実行 ───────────────────────────────────────────────────────────────

def check_http(svc: dict, timeout: int = 5) -> dict:
    """HTTP チェック。status / latency / detail を返す。"""
    url = svc["url"]
    expected = svc.get("expect_status", 200)
    if isinstance(expected, int):
        expected = [expected]

    t0 = time.time()
    try:
        req = urllib.request.Request(url, method=svc.get("method", "GET"))
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            latency = int((time.time() - t0) * 1000)
            status = resp.status
            body = {}
            if "detail_fn" in svc:
                try:
                    body = json.loads(resp.read())
                except Exception:
                    body = {}
            detail = svc["detail_fn"](body) if "detail_fn" in svc else ""
            ok = status in expected
            return {"ok": ok, "status": status, "latency_ms": latency, "detail": detail}
    except urllib.error.HTTPError as e:
        latency = int((time.time() - t0) * 1000)
        ok = e.code in expected
        return {"ok": ok, "status": e.code, "latency_ms": latency, "detail": str(e.reason)}
    except Exception as e:
        latency = int((time.time() - t0) * 1000)
        return {"ok": False, "status": 0, "latency_ms": latency, "detail": str(e)[:80]}


def check_redis_tcp(timeout: int = 3) -> dict:
    """Redis TCP 疎通確認 (socket)。"""
    import socket
    t0 = time.time()
    try:
        with socket.create_connection(("redis", 6379), timeout=timeout) as s:
            s.sendall(b"PING\r\n")
            data = s.recv(64)
            latency = int((time.time() - t0) * 1000)
            ok = b"PONG" in data
            return {"ok": ok, "status": 200 if ok else 0, "latency_ms": latency,
                    "detail": data.decode(errors="replace").strip()}
    except Exception as e:
        return {"ok": False, "status": 0, "latency_ms": int((time.time() - t0) * 1000),
                "detail": str(e)[:80]}


def check_embedding(timeout: int = 10) -> dict:
    """Infinity embedding 疎通 (実際に embed してみる)。"""
    t0 = time.time()
    try:
        body = json.dumps({"model": "mixedbread-ai/mxbai-embed-large-v1",
                           "input": ["health check"]}).encode()
        req = urllib.request.Request(
            "http://infinity:7997/embeddings",
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read())
            latency = int((time.time() - t0) * 1000)
            dim = len(data["data"][0]["embedding"])
            return {"ok": True, "status": 200, "latency_ms": latency,
                    "detail": f"dim={dim}"}
    except Exception as e:
        return {"ok": False, "status": 0, "latency_ms": int((time.time() - t0) * 1000),
                "detail": str(e)[:80]}


# ── 出力 ──────────────────────────────────────────────────────────────────────

GREEN  = "\033[92m"
RED    = "\033[91m"
YELLOW = "\033[93m"
RESET  = "\033[0m"
BOLD   = "\033[1m"


def colored(text, color):
    return f"{color}{text}{RESET}"


def print_result(name, desc, result):
    icon = colored("✓ OK  ", GREEN) if result["ok"] else colored("✗ FAIL", RED)
    lat  = f"{result['latency_ms']:4d}ms"
    det  = f"  {result['detail']}" if result.get("detail") else ""
    print(f"  {icon}  {name:<22} {lat}  {desc}{det}")


# ── メイン ────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Clawstack 全サービス Health Check")
    parser.add_argument("--service", "-s", nargs="*",
                        help="チェックするサービス名を限定 (例: ollama qdrant)")
    parser.add_argument("--json", "-j", action="store_true", help="JSON 出力")
    parser.add_argument("--timeout", "-t", type=int, default=5, help="タイムアウト秒 (default=5)")
    parser.add_argument("--embed", "-e", action="store_true",
                        help="Infinity embedding の実疎通テストを追加")
    args = parser.parse_args()

    now = datetime.now(JST).strftime("%Y-%m-%d %H:%M:%S JST")
    print(f"\n{BOLD}=== Clawstack Health Check — {now} ==={RESET}\n")

    target_names = set(args.service) if args.service else None
    results = {}

    for svc in SERVICES:
        name = svc["name"]
        if target_names and name not in target_names:
            continue

        if svc.get("method") is None and name == "redis":
            r = check_redis_tcp(args.timeout)
        else:
            r = check_http(svc, args.timeout)

        results[name] = {**r, "desc": svc["desc"]}
        if not args.json:
            print_result(name, svc["desc"], r)

    # オプション: embedding 実疎通
    if args.embed and (not target_names or "infinity_embed" in target_names):
        r = check_embedding(args.timeout * 2)
        results["infinity_embed"] = {**r, "desc": "Infinity Embedding (実テスト)"}
        if not args.json:
            print_result("infinity_embed", "Infinity Embedding (実テスト)", r)

    # サマリー
    total  = len(results)
    ok_cnt = sum(1 for r in results.values() if r["ok"])
    fail   = total - ok_cnt

    if args.json:
        print(json.dumps({"timestamp": now, "summary": {"total": total, "ok": ok_cnt, "fail": fail},
                          "services": results}, ensure_ascii=False, indent=2))
    else:
        print()
        status_str = colored(f"OK {ok_cnt}/{total}", GREEN) if fail == 0 \
            else colored(f"FAIL {fail}/{total}", RED)
        print(f"{BOLD}  結果: {status_str}{RESET}\n")
        if fail > 0:
            print(colored("  [失敗サービス]", RED))
            for name, r in results.items():
                if not r["ok"]:
                    print(f"    - {name}: {r['detail']}")
            print()
            sys.exit(1)


if __name__ == "__main__":
    main()
