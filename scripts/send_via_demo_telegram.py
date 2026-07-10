# -*- coding: utf-8 -*-
"""Visual Inspection AI デモ結果をTelegramへ送信(ホスト実行)。

最新の demo_runs を自動選択し、各ケースの判定画像+ヒートマップをキャプション付きで送る。
認証: TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID (env または ルート/scripts の .env — 既存慣例と同一)
実行: python scripts\send_via_demo_telegram.py [--dir <demo_runsサブフォルダ>]
"""
from __future__ import annotations

import sys

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import argparse
import json
import mimetypes
import os
import urllib.request
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNS = ROOT / "projects" / "visual_inspection_ai" / "data" / "demo_runs"


def load_telegram() -> tuple[str, str]:
    bot = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip().strip('"')
    chat = os.environ.get("TELEGRAM_CHAT_ID", "").strip().strip('"')
    for env_path in (ROOT / ".env", ROOT / "scripts" / ".env"):
        if not env_path.exists():
            continue
        for line in env_path.read_text(encoding="utf-8", errors="replace").splitlines():
            if line.startswith("TELEGRAM_BOT_TOKEN=") and not bot:
                bot = line.split("=", 1)[1].strip().strip('"')
            if line.startswith("TELEGRAM_CHAT_ID=") and not chat:
                chat = line.split("=", 1)[1].strip().strip('"')
    if not bot or not chat:
        raise RuntimeError("TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID missing (.env確認)")
    return bot, chat


def send_photo(bot: str, chat: str, path: Path, caption: str) -> None:
    boundary = uuid.uuid4().hex
    data = b""
    for name, value in (("chat_id", chat), ("caption", caption[:1024])):
        data += (f"--{boundary}\r\nContent-Disposition: form-data; name=\"{name}\"\r\n\r\n{value}\r\n").encode("utf-8")
    mime = mimetypes.guess_type(str(path))[0] or "image/png"
    data += (f"--{boundary}\r\nContent-Disposition: form-data; name=\"photo\"; filename=\"{path.name}\"\r\n"
             f"Content-Type: {mime}\r\n\r\n").encode("utf-8")
    data += path.read_bytes() + f"\r\n--{boundary}--\r\n".encode("utf-8")
    req = urllib.request.Request(
        f"https://api.telegram.org/bot{bot}/sendPhoto", data=data,
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"})
    with urllib.request.urlopen(req, timeout=60) as r:
        ok = json.loads(r.read().decode("utf-8")).get("ok")
    print(("[ok] " if ok else "[NG] ") + path.name)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default=None)
    args = ap.parse_args()
    run_dir = Path(args.dir) if args.dir else sorted(RUNS.iterdir())[-1]
    summary = json.loads((run_dir / "summary.json").read_text(encoding="utf-8"))
    bot, chat = load_telegram()
    n_ok = sum(r["judged_correctly"] for r in summary["results"])
    header = (f"🔍 Visual Inspection AI デモ ({summary['at'][:16]})\n"
              f"判定成績: {n_ok}/{len(summary['results'])} 正解\n"
              f"しきい値: 校正済み(review/ng) + ECCアライメント有効")
    send_photo(bot, chat, run_dir / "case1_good_annotated.png", header)
    for r in summary["results"]:
        cap = (f"{'✅' if r['judged_correctly'] else '❌'} {r['label']}: 判定={r['decision']} "
               f"(期待: {r['expect']}) score={r['score']} 不良領域={r['regions']}")
        p_ann = run_dir / f"{r['case']}_annotated.png"
        p_heat = run_dir / f"{r['case']}_heatmap.png"
        if r["case"] != "case1_good" and p_ann.exists():
            send_photo(bot, chat, p_ann, cap)
        if p_heat.exists() and r["decision"] != "OK":
            send_photo(bot, chat, p_heat, f"↑ {r['label']} の異常ヒートマップ(赤=異常)")
    print(f"送信完了: {run_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
