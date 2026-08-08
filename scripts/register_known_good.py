# -*- coding: utf-8 -*-
"""チェックポイントを known_good へ登録する。検証に通らないものは登録できない。

2026-08-08 導入。背景(実測):
  known_good の11件すべてが現環境で転倒した(生存 0/11)。ファイル名に VERIFIED /
  ADOPTED と付いた6件も例外なし。原因は学習後に v50_walk_env.py が7回改変され
  (+未コミット96行)、観測・報酬・地形が変わったこと。
  **チェックポイントは学習時の環境とセットでしか意味を持たない**のに、
  環境バージョンが記録されておらず、環境変更時の再検証も行われていなかった。
  さらに travel は転倒滑走を含む(T067)ため、名前の数字は実力を示さない。

本ツールが強制すること:
  1. 現環境での実測(verify_known_good_ckpts と同じ条件)に通ること
     - fell=false かつ min_upright が閾値以上 かつ travel が閾値以上
  2. 環境のコミットハッシュと作業ツリーの汚れ有無を記録すること
  3. フレーム画像の目視確認を人間が宣言すること(--visually-checked)
     目視していないものは登録できない(数値だけの合格判定は禁止)

usage:
  python scripts/register_known_good.py --ckpt <path> --name <登録名> --visually-checked
  python scripts/register_known_good.py --ckpt <path> --dry-run
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import time
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # P023

REPO = Path(r"D:\Clawdbot_Docker_20260125")
KNOWN_GOOD = Path(r"C:\v50_work\autonomy\known_good")
LEDGER = KNOWN_GOOD / "registry.json"
ENV_FILE = REPO / "projects" / "AtsugiMechaCity" / "rl_integration" / "stage_a" / "v50_walk_env.py"

MIN_TRAVEL = 1.0
MIN_UPRIGHT = 0.5


def env_fingerprint() -> dict:
    """学習環境の同一性を後から照合できるようにする。"""
    def git(*args: str) -> str:
        try:
            return subprocess.run(["git", *args], cwd=str(REPO), capture_output=True,
                                  text=True, encoding="utf-8", errors="replace",
                                  timeout=60).stdout.strip()
        except Exception as e:
            return f"<取得失敗 {type(e).__name__}>"
    dirty = git("status", "--porcelain", str(ENV_FILE))
    return {
        "repo_head": git("rev-parse", "HEAD"),
        "env_file": str(ENV_FILE.relative_to(REPO)).replace("\\", "/"),
        "env_last_commit": git("log", "-1", "--format=%H %ad", "--", str(ENV_FILE)),
        "env_uncommitted": bool(dirty),
        "env_uncommitted_detail": dirty[:200],
    }


def verify(ckpt: Path) -> dict:
    sys.path.insert(0, str(REPO / "scripts"))
    import verify_known_good_ckpts as V
    rec = V.run_one(ckpt, seconds=8)
    rec["verdict"] = V.verdict(rec)
    return rec


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ckpt", required=True)
    ap.add_argument("--name", default=None, help="登録名(省略時は元のファイル名)")
    ap.add_argument("--visually-checked", action="store_true",
                    help="フレーム画像を目視し、連結・姿勢・接地に異常が無いことを確認した")
    ap.add_argument("--note", default="")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    src = Path(a.ckpt)
    if not src.exists():
        print(f"チェックポイントがありません: {src}")
        return 3

    print(f"検証中: {src.name}")
    rec = verify(src)
    travel = rec.get("final_travel_m", rec.get("final_travel", 0.0)) or 0.0
    upright = rec.get("min_upright", 0.0) or 0.0
    fell = rec.get("fell", True)
    print(f"  判定={rec['verdict']} fell={fell} travel={travel} min_upright={upright}")

    reasons = []
    if rec.get("status") != "ok":
        reasons.append(f"測定に失敗した({rec.get('status')})")
    if fell:
        reasons.append("転倒している(fell=true)")
    if travel < MIN_TRAVEL:
        reasons.append(f"前進が不足({travel:.2f} < {MIN_TRAVEL})")
    if upright < MIN_UPRIGHT:
        reasons.append(f"姿勢が保てていない(min_upright {upright} < {MIN_UPRIGHT})")
    if not a.visually_checked:
        reasons.append("フレーム目視の宣言が無い(--visually-checked)")

    if reasons:
        print("\n登録できません:")
        for r in reasons:
            print(f"  - {r}")
        print(f"\nフレーム画像: {rec.get('frames_dir', '(なし)')}")
        return 4

    entry = {
        "name": a.name or src.name,
        "registered_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "source": str(src),
        "measured": {k: rec.get(k) for k in
                     ("fell", "final_travel_m", "min_upright", "first_fall_sec",
                      "single_support_frac", "double_support_frac", "flight_frac",
                      "commanded_vx", "terrain", "obs")},
        "environment": env_fingerprint(),
        "visually_checked": True,
        "note": a.note,
    }
    if a.dry_run:
        print("\n[dry-run] 登録内容:")
        print(json.dumps(entry, ensure_ascii=False, indent=2))
        return 0

    KNOWN_GOOD.mkdir(parents=True, exist_ok=True)
    dst = KNOWN_GOOD / (a.name or src.name)
    shutil.copy2(src, dst)
    entry["path"] = str(dst)

    ledger = {"schema": "clawstack.known_good_registry.v1", "entries": []}
    if LEDGER.exists():
        try:
            ledger = json.loads(LEDGER.read_text(encoding="utf-8"))
        except Exception:
            pass
    ledger["entries"].append(entry)
    LEDGER.write_text(json.dumps(ledger, ensure_ascii=False, indent=2), encoding="utf-8")
    # 書き戻して化けが無いか確認する(グローバルルール 2026-08-08)
    back = LEDGER.read_text(encoding="utf-8")
    bad = back.count("\ufffd") + sum(back.count(m) for m in "縺繧繝")
    print(f"\n登録しました: {dst}")
    print(f"台帳: {LEDGER} (化け文字 {bad} 件)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
