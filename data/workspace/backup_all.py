#!/usr/bin/env python3
"""
backup_all.py — Clawstack 全データバックアップ CLI
===================================================
バックアップ対象:
  1. PostgreSQL  (pg_dump → SQL ファイル)
  2. Qdrant      (snapshot API)
  3. MinIO       (mc mirror)
  4. ClickHouse  (backup コマンド → S3/local)

使い方 (gateway コンテナ内 — docker.sock マウント必須):
  python3 /home/node/clawd/backup_all.py
  python3 /home/node/clawd/backup_all.py --dry-run          # 実行確認のみ
  python3 /home/node/clawd/backup_all.py --target postgres   # 特定のみ
  python3 /home/node/clawd/backup_all.py --out /home/node/clawd/backups

使い方 (ホストから):
  docker exec clawstack-unified-clawdbot-gateway-1 python3 /home/node/clawd/backup_all.py

注意:
  - 破壊的操作は行わない (読み取り + 書き出しのみ)
  - ClickHouse は gateway から HTTP backup API 経由
  - PostgreSQL は gateway から pg_dump (psycopg2 不要、pg_dump バイナリを使用)
"""

import argparse
import json
import os
import subprocess
import sys
import urllib.request
from datetime import datetime, timezone, timedelta
from pathlib import Path

JST = timezone(timedelta(hours=9))

DEFAULT_OUT = Path("/home/node/clawd/backups")

# Docker コンテナ名 (gateway から docker exec)
CONTAINERS = {
    "postgres":   "clawstack-unified-postgres-1",
    "clickhouse": "clickhouse",
    "minio":      "clawstack-unified-minio-1",
}
QDRANT_URL   = "http://qdrant:6333"
POSTGRES_DSN = f"postgresql://postgres:{os.getenv('POSTGRES_PASSWORD', 'postgres')}@postgres:5432"

GREEN  = "\033[92m"
RED    = "\033[91m"
YELLOW = "\033[93m"
RESET  = "\033[0m"
BOLD   = "\033[1m"


def c(text, color): return f"{color}{text}{RESET}"


def log(msg, color=None):
    if color:
        print(f"  {c(msg, color)}", flush=True)
    else:
        print(f"  {msg}", flush=True)


# ── PostgreSQL ────────────────────────────────────────────────────────────────

def backup_postgres(out_dir: Path, dry_run: bool) -> dict:
    now_str = datetime.now(JST).strftime("%Y%m%d_%H%M%S")
    filename = out_dir / f"postgres_{now_str}.sql.gz"

    log(f"PostgreSQL → {filename}")
    if dry_run:
        return {"ok": True, "dry_run": True, "file": str(filename)}

    # gateway コンテナから postgres コンテナへ pg_dump (docker exec 経由)
    # または直接 psql/pg_dump が使える場合は直接呼ぶ
    cmd_inner = [
        "docker", "exec",
        CONTAINERS["postgres"],
        "pg_dump",
        "-U", "postgres",
        "--clean",
        "--if-exists",
        "-d", "postgres",
    ]
    try:
        result = subprocess.run(
            cmd_inner,
            capture_output=True,
            timeout=120,
        )
        if result.returncode != 0:
            err = result.stderr.decode(errors="replace")[:200]
            return {"ok": False, "error": f"pg_dump failed: {err}"}

        # gzip 圧縮して保存
        import gzip
        with gzip.open(filename, "wb") as f:
            f.write(result.stdout)

        size_mb = filename.stat().st_size / 1024 / 1024
        log(f"  PostgreSQL OK — {size_mb:.1f} MB", GREEN)
        return {"ok": True, "file": str(filename), "size_mb": round(size_mb, 2)}
    except Exception as e:
        return {"ok": False, "error": str(e)[:100]}


# ── Qdrant ────────────────────────────────────────────────────────────────────

def backup_qdrant(out_dir: Path, dry_run: bool) -> dict:
    log("Qdrant snapshots ...")

    # collection 一覧取得
    try:
        req = urllib.request.Request(f"{QDRANT_URL}/collections")
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
        collections = [c["name"] for c in data.get("result", {}).get("collections", [])]
    except Exception as e:
        return {"ok": False, "error": f"Qdrant collection 取得失敗: {e}"}

    if dry_run:
        log(f"  [dry-run] {len(collections)} collections: {', '.join(collections)}")
        return {"ok": True, "dry_run": True, "collections": collections}

    results = {}
    for col in collections:
        log(f"  → snapshot: {col} ...", end="\r" if sys.stdout.isatty() else "\n")
        try:
            snap_req = urllib.request.Request(
                f"{QDRANT_URL}/collections/{col}/snapshots",
                data=b"{}",
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(snap_req, timeout=60) as resp:
                snap_data = json.loads(resp.read())
            snap_name = snap_data.get("result", {}).get("name", "?")
            log(f"  {c('✓', GREEN)} {col:<35}  {snap_name}")
            results[col] = {"ok": True, "snapshot": snap_name}
        except Exception as e:
            log(f"  {c('✗', RED)} {col:<35}  {e}")
            results[col] = {"ok": False, "error": str(e)[:80]}

    all_ok = all(r["ok"] for r in results.values())
    return {"ok": all_ok, "collections": results}


# ── ClickHouse ────────────────────────────────────────────────────────────────

def backup_clickhouse(out_dir: Path, dry_run: bool) -> dict:
    now_str = datetime.now(JST).strftime("%Y%m%d_%H%M%S")
    backup_name = f"clickhouse_backup_{now_str}"
    log(f"ClickHouse → {backup_name}")

    if dry_run:
        return {"ok": True, "dry_run": True, "backup_name": backup_name}

    # ClickHouse HTTP API で BACKUP DATABASE
    backup_dir = f"/var/lib/clickhouse/backups/{backup_name}"
    sql = f"BACKUP DATABASE langfuse TO Disk('backups', '{backup_name}')"
    try:
        data = sql.encode()
        req = urllib.request.Request(
            "http://clickhouse:8123/?user=langfuse&password=langfuse",
            data=data,
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=120) as resp:
            result = resp.read().decode()
        log(f"  ClickHouse OK — {result.strip()[:80]}", GREEN)
        return {"ok": True, "backup_name": backup_name, "result": result.strip()[:80]}
    except Exception as e:
        # ClickHouse backup disk が設定されていない場合は警告のみ
        msg = str(e)[:100]
        log(f"  ClickHouse backup skipped: {msg}", YELLOW)
        return {"ok": True, "skipped": True, "reason": msg}


# ── MinIO ─────────────────────────────────────────────────────────────────────

def backup_minio(out_dir: Path, dry_run: bool) -> dict:
    now_str = datetime.now(JST).strftime("%Y%m%d_%H%M%S")
    local_path = out_dir / f"minio_{now_str}"
    log(f"MinIO → {local_path}")

    if dry_run:
        return {"ok": True, "dry_run": True, "path": str(local_path)}

    # mc コマンドが gateway コンテナにある場合は直接実行
    # なければ docker exec で minio コンテナ内の mc を使う
    mc_cmd = None
    for mc in ["mc", "/usr/local/bin/mc"]:
        result = subprocess.run(["which", mc], capture_output=True)
        if result.returncode == 0:
            mc_cmd = mc
            break

    if not mc_cmd:
        log("  mc コマンドなし — MinIO backup スキップ (mc CLI が必要)", YELLOW)
        return {"ok": True, "skipped": True, "reason": "mc not found in gateway container"}

    local_path.mkdir(parents=True, exist_ok=True)
    minio_url = "http://minio:9000"
    minio_user = os.getenv("MINIO_ROOT_USER", "minioadmin")
    minio_pass = os.getenv("MINIO_ROOT_PASSWORD", "minioadmin")

    try:
        # mc alias 設定
        subprocess.run(
            [mc_cmd, "alias", "set", "local-backup", minio_url, minio_user, minio_pass],
            capture_output=True, check=True, timeout=10,
        )
        # mirror (読み取りのみ)
        result = subprocess.run(
            [mc_cmd, "mirror", "local-backup", str(local_path)],
            capture_output=True, timeout=300,
        )
        if result.returncode == 0:
            log(f"  MinIO OK → {local_path}", GREEN)
            return {"ok": True, "path": str(local_path)}
        else:
            err = result.stderr.decode()[:100]
            return {"ok": False, "error": err}
    except Exception as e:
        return {"ok": False, "error": str(e)[:100]}


# ── メイン ────────────────────────────────────────────────────────────────────

TARGETS = {
    "postgres":   backup_postgres,
    "qdrant":     backup_qdrant,
    "clickhouse": backup_clickhouse,
    "minio":      backup_minio,
}


def main():
    parser = argparse.ArgumentParser(description="Clawstack 全データバックアップ")
    parser.add_argument("--target",  "-t", nargs="*", choices=list(TARGETS.keys()),
                        help="対象を限定 (省略=全て)")
    parser.add_argument("--dry-run", "-n", action="store_true",
                        help="実行内容を表示するだけで実際のバックアップはしない")
    parser.add_argument("--out",     "-o", default=str(DEFAULT_OUT),
                        help=f"出力ディレクトリ (default: {DEFAULT_OUT})")
    parser.add_argument("--json",    "-j", action="store_true", help="JSON 結果出力")
    args = parser.parse_args()

    now = datetime.now(JST).strftime("%Y-%m-%d %H:%M:%S JST")
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    targets = args.target or list(TARGETS.keys())

    if args.dry_run:
        print(f"\n{BOLD}{c('=== DRY RUN ===', YELLOW)} — 実際のバックアップは行いません\n{RESET}")
    else:
        print(f"\n{BOLD}=== Clawstack Backup — {now} ==={RESET}")
        print(f"  出力先: {out_dir}\n")

    results = {}
    for name in targets:
        print(f"{BOLD}[{name}]{RESET}")
        fn = TARGETS[name]
        try:
            r = fn(out_dir, args.dry_run)
        except Exception as e:
            r = {"ok": False, "error": str(e)[:100]}
            log(f"  {c('✗ 予期しないエラー:', RED)} {e}")
        results[name] = r
        print()

    # サマリー
    ok  = sum(1 for r in results.values() if r.get("ok"))
    all_ok = ok == len(targets)

    if args.json:
        print(json.dumps({"timestamp": now, "dry_run": args.dry_run,
                          "summary": {"total": len(targets), "ok": ok},
                          "results": results}, ensure_ascii=False, indent=2))
    else:
        color = GREEN if all_ok else RED
        print(f"  {c(f'完了 {ok}/{len(targets)}', color)}\n")
        if not all_ok:
            sys.exit(1)


if __name__ == "__main__":
    main()
