#!/usr/bin/env python3
"""
qdrant_snapshot.py — Qdrant Snapshot 管理 CLI
===============================================
使い方 (gateway コンテナ内):
  python3 /home/node/clawd/qdrant_snapshot.py list                     # 全 collection の snapshot 一覧
  python3 /home/node/clawd/qdrant_snapshot.py create                   # 全 collection の snapshot 作成
  python3 /home/node/clawd/qdrant_snapshot.py create --collection universal_knowledge
  python3 /home/node/clawd/qdrant_snapshot.py delete <snapshot_name> --collection <col>
  python3 /home/node/clawd/qdrant_snapshot.py status                   # collection 状態確認

使い方 (ホストから):
  docker exec clawstack-unified-clawdbot-gateway-1 python3 /home/node/clawd/qdrant_snapshot.py create
"""

import argparse
import json
import sys
import urllib.request
import urllib.error
from datetime import datetime, timezone, timedelta

JST      = timezone(timedelta(hours=9))
QDRANT   = "http://qdrant:6333"

GREEN  = "\033[92m"
RED    = "\033[91m"
YELLOW = "\033[93m"
RESET  = "\033[0m"
BOLD   = "\033[1m"


def c(text, color): return f"{color}{text}{RESET}"


def http_get(url):
    req = urllib.request.Request(url, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read())


def http_post(url, body=None):
    data = json.dumps(body or {}).encode()
    req = urllib.request.Request(url, data=data,
                                  headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.loads(resp.read())


def http_delete(url):
    req = urllib.request.Request(url, method="DELETE",
                                  headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read())


def get_collections() -> list[str]:
    data = http_get(f"{QDRANT}/collections")
    return [c["name"] for c in data.get("result", {}).get("collections", [])]


def list_snapshots(collections: list[str]):
    print(f"\n{BOLD}=== Qdrant Snapshots ==={RESET}\n")
    for col in collections:
        try:
            data = http_get(f"{QDRANT}/collections/{col}/snapshots")
            snaps = data.get("result", [])
            if snaps:
                print(f"  {c(col, BOLD)} ({len(snaps)} snapshots)")
                for s in snaps:
                    size = s.get("size", 0)
                    size_mb = size / 1024 / 1024
                    created = s.get("creation_time", "-")
                    print(f"    - {s['name']:<60}  {size_mb:7.1f} MB  {created}")
            else:
                print(f"  {col}  {c('(snapshot なし)', YELLOW)}")
        except Exception as e:
            print(f"  {col}  {c(f'ERROR: {e}', RED)}")
    print()


def create_snapshots(collections: list[str]):
    print(f"\n{BOLD}=== Snapshot 作成 ==={RESET}\n")
    results = {}
    for col in collections:
        print(f"  → {col} ...", end="", flush=True)
        try:
            data = http_post(f"{QDRANT}/collections/{col}/snapshots")
            snap_name = data.get("result", {}).get("name", "?")
            print(f"\r  {c('✓', GREEN)} {col:<35}  snapshot: {snap_name}")
            results[col] = {"ok": True, "name": snap_name}
        except Exception as e:
            print(f"\r  {c('✗', RED)} {col:<35}  {e}")
            results[col] = {"ok": False, "error": str(e)}

    ok = sum(1 for r in results.values() if r["ok"])
    print(f"\n  {c(f'完了 {ok}/{len(collections)}', GREEN if ok == len(collections) else RED)}\n")
    return results


def delete_snapshot(collection: str, name: str):
    print(f"  → DELETE {collection}/{name} ...", end="", flush=True)
    try:
        http_delete(f"{QDRANT}/collections/{collection}/snapshots/{name}")
        print(f"\r  {c('✓', GREEN)} 削除完了: {name}")
    except Exception as e:
        print(f"\r  {c('✗', RED)} {e}")
        sys.exit(1)


def show_status(collections: list[str]):
    print(f"\n{BOLD}=== Qdrant Collection 状態 ==={RESET}\n")
    fmt = "  {:<35} {:>8} {:>8}  {}"
    print(fmt.format("Collection", "Points", "Dim", "Status"))
    print("  " + "-" * 70)
    for col in collections:
        try:
            data = http_get(f"{QDRANT}/collections/{col}")
            info = data.get("result", {})
            cfg  = info.get("config", {}).get("params", {})
            vecs = info.get("vectors_count", info.get("points_count", "?"))
            dim  = cfg.get("vectors", {}).get("size", "?") if isinstance(cfg.get("vectors"), dict) else "?"
            st   = info.get("status", "-")
            color = GREEN if st == "green" else RED
            print(fmt.format(col, str(vecs), str(dim), c(st, color)))
        except Exception as e:
            print(fmt.format(col, "-", "-", c(f"ERROR: {e}", RED)))
    print()


def main():
    parser = argparse.ArgumentParser(description="Qdrant Snapshot 管理")
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("list",   help="Snapshot 一覧")
    sub.add_parser("status", help="Collection 状態確認")

    p_create = sub.add_parser("create", help="Snapshot 作成")
    p_create.add_argument("--collection", "-c", help="対象 collection (省略=全て)")

    p_delete = sub.add_parser("delete", help="Snapshot 削除")
    p_delete.add_argument("name",         help="Snapshot 名")
    p_delete.add_argument("--collection", "-c", required=True, help="対象 collection")

    args = parser.parse_args()

    try:
        all_cols = get_collections()
    except Exception as e:
        print(c(f"[ERROR] Qdrant 接続失敗: {e}", RED), file=sys.stderr)
        sys.exit(1)

    if args.cmd == "list":
        list_snapshots(all_cols)

    elif args.cmd == "status":
        show_status(all_cols)

    elif args.cmd == "create":
        targets = [args.collection] if args.collection else all_cols
        create_snapshots(targets)

    elif args.cmd == "delete":
        delete_snapshot(args.collection, args.name)


if __name__ == "__main__":
    main()
