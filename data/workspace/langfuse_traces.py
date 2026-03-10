#!/usr/bin/env python3
"""
langfuse_traces.py — Langfuse トレース照会 CLI
================================================
使い方 (gateway コンテナ内):
  python3 /home/node/clawd/langfuse_traces.py --failed          # 直近の失敗トレース
  python3 /home/node/clawd/langfuse_traces.py --recent          # 直近20件
  python3 /home/node/clawd/langfuse_traces.py --fallback-rate   # fallback 率
  python3 /home/node/clawd/langfuse_traces.py --trace <id>      # 特定トレース
  python3 /home/node/clawd/langfuse_traces.py --json            # JSON 出力

使い方 (ホストから):
  docker exec clawstack-unified-clawdbot-gateway-1 python3 /home/node/clawd/langfuse_traces.py --failed
"""

import argparse
import base64
import json
import os
import sys
import urllib.request
import urllib.error
from datetime import datetime, timezone, timedelta

JST = timezone(timedelta(hours=9))

LANGFUSE_HOST       = os.getenv("LANGFUSE_HOST",       "http://langfuse:3000")
LANGFUSE_PUBLIC_KEY = os.getenv("LANGFUSE_PUBLIC_KEY", "pk-lf-07926c92-5480-4fb5-ae97-39e35a0a0ce5")
LANGFUSE_SECRET_KEY = os.getenv("LANGFUSE_SECRET_KEY", "sk-lf-9b4e86b1-ec3b-4826-aca7-b20bd68b1bd8")

GREEN  = "\033[92m"
RED    = "\033[91m"
YELLOW = "\033[93m"
RESET  = "\033[0m"
BOLD   = "\033[1m"


def c(text, color): return f"{color}{text}{RESET}"


def _auth_header():
    creds = base64.b64encode(
        f"{LANGFUSE_PUBLIC_KEY}:{LANGFUSE_SECRET_KEY}".encode()
    ).decode()
    return {"Authorization": f"Basic {creds}", "Accept": "application/json"}


def api_get(path: str, params: dict = None):
    """Langfuse REST API GET。"""
    url = f"{LANGFUSE_HOST}/api/public/{path}"
    if params:
        qs = "&".join(f"{k}={v}" for k, v in params.items())
        url = f"{url}?{qs}"
    req = urllib.request.Request(url, headers=_auth_header())
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        body = e.read().decode(errors="replace")[:200]
        raise RuntimeError(f"HTTP {e.code}: {body}")


def fmt_ts(ts: str) -> str:
    """ISO8601 → JST 文字列。"""
    if not ts:
        return "-"
    try:
        dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        return dt.astimezone(JST).strftime("%m/%d %H:%M:%S")
    except Exception:
        return ts[:19]


def cmd_recent(limit=20, output_json=False):
    """直近トレース一覧。"""
    data = api_get("traces", {"limit": limit, "orderBy": "timestamp.desc"})
    traces = data.get("data", [])

    if output_json:
        print(json.dumps(traces, ensure_ascii=False, indent=2))
        return

    print(f"\n{BOLD}=== 直近トレース (上位 {len(traces)} 件) ==={RESET}\n")
    fmt = "  {:<24} {:<12} {:<8} {:<10} {}"
    print(fmt.format("Time (JST)", "Name", "Latency", "Status", "ID"))
    print("  " + "-" * 80)
    for t in traces:
        lat = f"{t.get('latency', 0)}ms" if t.get("latency") else "-"
        st  = t.get("level", "-")
        color = GREEN if st in ("DEFAULT", "DEBUG") else RED if st == "ERROR" else YELLOW
        print(fmt.format(
            fmt_ts(t.get("timestamp", "")),
            (t.get("name") or "-")[:11],
            lat,
            c(st[:8], color),
            t.get("id", "")[:20],
        ))
    print()


def cmd_failed(limit=50, output_json=False):
    """失敗トレース一覧。"""
    # Langfuse v3: level=ERROR でフィルタ
    data = api_get("traces", {"limit": limit, "orderBy": "timestamp.desc", "level": "ERROR"})
    traces = data.get("data", [])

    if output_json:
        print(json.dumps(traces, ensure_ascii=False, indent=2))
        return

    print(f"\n{BOLD}=== 失敗トレース (ERROR, 上位 {len(traces)} 件) ==={RESET}\n")
    if not traces:
        print(c("  失敗トレースなし — システム正常", GREEN))
        print()
        return

    for t in traces:
        ts   = fmt_ts(t.get("timestamp", ""))
        name = (t.get("name") or "-")[:30]
        tid  = t.get("id", "")[:20]
        lat  = f"{t.get('latency', 0)}ms" if t.get("latency") else "-"
        tags = ", ".join(t.get("tags") or [])
        print(f"  {c('✗', RED)} [{ts}] {name}  {lat}  id={tid}")
        if tags:
            print(f"       tags: {tags}")
        # 入力の先頭だけ表示
        inp = t.get("input")
        if inp:
            inp_str = json.dumps(inp, ensure_ascii=False)[:120]
            print(f"       input: {inp_str}")
        print()


def cmd_fallback_rate(hours=24, output_json=False):
    """fallback 率確認 (モデルタグで集計)。"""
    # 直近 N 時間のトレースを取得して model タグで集計
    data = api_get("traces", {"limit": 200, "orderBy": "timestamp.desc"})
    traces = data.get("data", [])

    model_counts: dict = {}
    total = 0
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)

    for t in traces:
        ts_str = t.get("timestamp", "")
        try:
            ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
            if ts < cutoff:
                continue
        except Exception:
            pass
        total += 1
        tags = t.get("tags") or []
        for tag in tags:
            if tag.startswith("model:"):
                model = tag[6:]
                model_counts[model] = model_counts.get(model, 0) + 1

    if output_json:
        out = {"hours": hours, "total": total, "by_model": model_counts,
               "fallback_rate": {k: f"{v/total*100:.1f}%" for k, v in model_counts.items()} if total else {}}
        print(json.dumps(out, ensure_ascii=False, indent=2))
        return

    print(f"\n{BOLD}=== Fallback 率 (直近 {hours}h, トレース {total} 件) ==={RESET}\n")
    if not model_counts:
        print("  モデルタグ付きトレースなし (Langfuse instrumentationが必要)")
    else:
        for model, cnt in sorted(model_counts.items(), key=lambda x: -x[1]):
            pct = cnt / total * 100 if total else 0
            bar = "█" * int(pct / 5)
            color = GREEN if "gemini" in model.lower() else YELLOW
            print(f"  {c(model, color):<45}  {cnt:4d}件  {pct:5.1f}%  {bar}")
    print()


def cmd_trace(trace_id: str, output_json=False):
    """特定トレース詳細。"""
    data = api_get(f"traces/{trace_id}")

    if output_json:
        print(json.dumps(data, ensure_ascii=False, indent=2))
        return

    print(f"\n{BOLD}=== トレース詳細: {trace_id[:20]} ==={RESET}\n")
    print(f"  Name     : {data.get('name', '-')}")
    print(f"  Time     : {fmt_ts(data.get('timestamp', ''))}")
    print(f"  Latency  : {data.get('latency', '-')}ms")
    print(f"  Level    : {data.get('level', '-')}")
    print(f"  Tags     : {', '.join(data.get('tags') or [])}")
    print(f"  Input    : {json.dumps(data.get('input'), ensure_ascii=False)[:200]}")
    print(f"  Output   : {json.dumps(data.get('output'), ensure_ascii=False)[:200]}")
    print()


def main():
    parser = argparse.ArgumentParser(description="Langfuse トレース照会")
    grp = parser.add_mutually_exclusive_group()
    grp.add_argument("--recent",      "-r", action="store_true",  help="直近トレース一覧")
    grp.add_argument("--failed",      "-f", action="store_true",  help="失敗トレース一覧")
    grp.add_argument("--fallback-rate", "-F", action="store_true", help="fallback率・モデル別集計")
    grp.add_argument("--trace",       "-t", metavar="ID",         help="特定トレース詳細")
    parser.add_argument("--limit",    "-n", type=int, default=20, help="取得件数 (default=20)")
    parser.add_argument("--hours",    type=int, default=24,       help="集計時間範囲 (default=24h)")
    parser.add_argument("--json",     "-j", action="store_true",  help="JSON 出力")
    args = parser.parse_args()

    try:
        if args.failed:
            cmd_failed(args.limit, args.json)
        elif args.fallback_rate:
            cmd_fallback_rate(args.hours, args.json)
        elif args.trace:
            cmd_trace(args.trace, args.json)
        else:
            cmd_recent(args.limit, args.json)
    except RuntimeError as e:
        print(f"{c('[ERROR]', RED)} {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
