#!/usr/bin/env python3
"""
workflow_backup.py — n8n Workflow Export / Backup CLI
======================================================
使い方 (gateway コンテナ内):
  python3 /home/node/clawd/workflow_backup.py                         # 全 workflow を export
  python3 /home/node/clawd/workflow_backup.py --out /home/node/clawd/n8n_backup
  python3 /home/node/clawd/workflow_backup.py --list                  # 一覧のみ表示
  python3 /home/node/clawd/workflow_backup.py --id <workflow_id>      # 特定 workflow のみ

使い方 (ホストから):
  docker exec clawstack-unified-clawdbot-gateway-1 python3 /home/node/clawd/workflow_backup.py
  docker cp clawstack-unified-clawdbot-gateway-1:/home/node/clawd/n8n_backup ./n8n_backup_local
"""

import argparse
import json
import os
import sys
import urllib.request
import urllib.error
from datetime import datetime, timezone, timedelta
from pathlib import Path

JST = timezone(timedelta(hours=9))

N8N_BASE    = "http://n8n:5678/api/v1"
N8N_API_KEY = "n8n_api_clawstack_f39c126b684f59ab50cc3fdedd82891086bfc633601067c9"
DEFAULT_OUT = Path("/home/node/clawd/n8n_backup")

GREEN  = "\033[92m"
RED    = "\033[91m"
YELLOW = "\033[93m"
RESET  = "\033[0m"
BOLD   = "\033[1m"


def c(text, color): return f"{color}{text}{RESET}"


def api_get(path: str):
    url = f"{N8N_BASE}/{path}"
    req = urllib.request.Request(url, headers={
        "X-N8N-API-KEY": N8N_API_KEY,
        "Accept": "application/json",
    })
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read())


def get_all_workflows():
    """全 workflow を取得 (ページネーション対応)。"""
    workflows = []
    cursor = None
    while True:
        path = "workflows?limit=100"
        if cursor:
            path += f"&cursor={cursor}"
        data = api_get(path)
        workflows.extend(data.get("data", []))
        next_cursor = data.get("nextCursor")
        if not next_cursor:
            break
        cursor = next_cursor
    return workflows


def get_workflow_detail(wf_id: str):
    return api_get(f"workflows/{wf_id}")


def cmd_list(workflows):
    print(f"\n{BOLD}=== n8n Workflow 一覧 ({len(workflows)} 件) ==={RESET}\n")
    fmt = "  {:<30} {:<8} {:<10} {}"
    print(fmt.format("Name", "Active", "Nodes", "ID"))
    print("  " + "-" * 70)
    for w in workflows:
        active = c("Active", GREEN) if w.get("active") else c("Inactive", YELLOW)
        nodes  = len(w.get("nodes", []))
        print(fmt.format(
            (w.get("name") or "-")[:29],
            active,
            str(nodes),
            w.get("id", "-"),
        ))
    print()


def cmd_export(workflows, out_dir: Path, target_id: str = None):
    out_dir.mkdir(parents=True, exist_ok=True)
    now_str = datetime.now(JST).strftime("%Y%m%d_%H%M%S")
    backup_dir = out_dir / now_str
    backup_dir.mkdir(parents=True, exist_ok=True)

    targets = [w for w in workflows if not target_id or w["id"] == target_id]
    if not targets:
        print(c(f"[ERROR] workflow が見つかりません: {target_id}", RED))
        sys.exit(1)

    print(f"\n{BOLD}=== n8n Workflow Export → {backup_dir} ==={RESET}\n")

    ok_count = 0
    all_data = []
    for w in targets:
        wid  = w["id"]
        name = (w.get("name") or wid)[:50].replace("/", "_").replace(" ", "_")
        print(f"  → {name} ({wid}) ...", end="", flush=True)
        try:
            detail = get_workflow_detail(wid)
            filename = backup_dir / f"{name}__{wid}.json"
            with open(filename, "w", encoding="utf-8") as f:
                json.dump(detail, f, ensure_ascii=False, indent=2)
            all_data.append(detail)
            ok_count += 1
            print(f"\r  {c('✓', GREEN)} {name:<45}  {len(detail.get('nodes', []))} nodes")
        except Exception as e:
            print(f"\r  {c('✗', RED)} {name:<45}  {e}")

    # 全件まとめた manifest も保存
    manifest_path = backup_dir / "_manifest.json"
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump({
            "exported_at": datetime.now(JST).isoformat(),
            "count": ok_count,
            "workflows": [{"id": w["id"], "name": w.get("name"), "active": w.get("active")}
                          for w in targets],
        }, f, ensure_ascii=False, indent=2)

    print(f"\n  {c(f'完了 {ok_count}/{len(targets)} 件', GREEN if ok_count == len(targets) else RED)}")
    print(f"  保存先: {backup_dir}\n")

    # 古いバックアップを 7 世代で自動削除
    prune_old_backups(out_dir, keep=7)

    return ok_count


def prune_old_backups(out_dir: Path, keep: int = 7):
    """タイムスタンプ名のサブディレクトリを keep 件に絞る。"""
    dirs = sorted(
        [d for d in out_dir.iterdir() if d.is_dir() and d.name[0].isdigit()],
        reverse=True,
    )
    for old in dirs[keep:]:
        import shutil
        shutil.rmtree(old, ignore_errors=True)
        print(f"  {c('🗑 pruned', YELLOW)}  {old.name}")


def main():
    parser = argparse.ArgumentParser(description="n8n Workflow Export/Backup")
    parser.add_argument("--list",  "-l", action="store_true", help="一覧のみ表示 (export しない)")
    parser.add_argument("--id",    "-i", metavar="ID",        help="特定 workflow ID のみ export")
    parser.add_argument("--out",   "-o", default=str(DEFAULT_OUT), help="出力ディレクトリ")
    args = parser.parse_args()

    try:
        workflows = get_all_workflows()
    except Exception as e:
        print(c(f"[ERROR] n8n API 接続失敗: {e}", RED), file=sys.stderr)
        sys.exit(1)

    if args.list:
        cmd_list(workflows)
    else:
        cmd_export(workflows, Path(args.out), args.id)


if __name__ == "__main__":
    main()
