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
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # P023

PY = r"C:\v50_work\genesis_venv\Scripts\python.exe"
REPO = Path(r"D:\Clawdbot_Docker_20260125")
KNOWN_GOOD = Path(r"C:\v50_work\autonomy\known_good")
LEDGER = KNOWN_GOOD / "registry.json"
ENV_FILE = REPO / "projects" / "AtsugiMechaCity" / "rl_integration" / "stage_a" / "v50_walk_env.py"

# 合否は複数envの実測で判定する(1envは例外個体を引くため使わない)。
# 閾値は過去実績 T067(survival 0.817 / travel 2.373m / single_contact 0.732)を
# 下回らない水準に置く。single_contact は「引きずり/両足接地のまま進む」を弾くため必須。
MIN_SURVIVAL = 0.80
MIN_TRAVEL = 1.5
MIN_SINGLE_CONTACT = 0.50
MIN_ON_TRACK = 0.80


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


def verify(ckpt: Path, n_envs: int = 256, speeds: str = "0.25,0.331") -> dict:
    """verify_policy.py(複数env・フレッシュリロード)で判定する。

    2026-08-10: 当初は1envレンダ(render_walk_rsl)で判定していたが、
    実際に成立した方策(256envで survival 0.938〜1.000)を「完全転倒」と誤って
    拒否した。1envはDRが単一サンプルになるうえ初期位相も1通りで、
    転ぶ個体を引くと実力を過小評価する(T067の既知の罠)。
    合否は必ず複数envの survival_rate で判定する。
    """
    stage_a = REPO / "projects" / "AtsugiMechaCity" / "rl_integration" / "stage_a"
    cmd = [PY, str(stage_a / "verify_policy.py"), "--ckpt", str(ckpt),
           "--ref-json", r"C:\v50_work\refs\walk.json",
           "--n-envs", str(n_envs), "--seconds", "8", "--speeds", speeds]
    r = subprocess.run(cmd, cwd=str(stage_a), capture_output=True, text=True,
                       encoding="utf-8", errors="replace", timeout=3600)
    m = re.search(r"VERIFY_POLICY:\s*(\{.*\})", r.stdout or "")
    if not m:
        return {"status": "no_verify_output", "stderr_tail": (r.stderr or "")[-300:]}
    data = json.loads(m.group(1))
    by = data.get("by_speed", [])
    worst = min(by, key=lambda x: x.get("survival_rate", 0)) if by else {}
    return {"status": "ok", "by_speed": by, "worst": worst,
            "survival_rate": worst.get("survival_rate", 0.0),
            "travel_m": worst.get("travel_m", 0.0),
            "single_contact_frac": worst.get("single_contact_frac", 0.0),
            "frac_survivors_on_track": worst.get("frac_survivors_on_track", 0.0)}


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

    print(f"検証中: {src.name} (verify_policy 256env)")
    rec = verify(src)
    surv = rec.get("survival_rate", 0.0)
    travel = rec.get("travel_m", 0.0)
    onefoot = rec.get("single_contact_frac", 0.0)
    ontrack = rec.get("frac_survivors_on_track", 0.0)
    for s in rec.get("by_speed", []):
        print(f"  cmd_vx={s.get('cmd_vx')}: survival={s.get('survival_rate')} "
              f"travel={s.get('travel_m')}m 単脚={s.get('single_contact_frac')} "
              f"直進率={s.get('frac_survivors_on_track')}")

    reasons = []
    if rec.get("status") != "ok":
        reasons.append(f"測定に失敗した({rec.get('status')}) {rec.get('stderr_tail','')[:120]}")
    if surv < MIN_SURVIVAL:
        reasons.append(f"生存率が不足(最悪速度で {surv} < {MIN_SURVIVAL})")
    if travel < MIN_TRAVEL:
        reasons.append(f"前進が不足({travel:.2f}m < {MIN_TRAVEL}m)")
    if onefoot < MIN_SINGLE_CONTACT:
        reasons.append(f"単脚支持が不足({onefoot} < {MIN_SINGLE_CONTACT} = 引きずり/両足接地の疑い)")
    if ontrack < MIN_ON_TRACK:
        reasons.append(f"直進できていない({ontrack} < {MIN_ON_TRACK})")
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
        "measured": {"by_speed": rec.get("by_speed"), "worst": rec.get("worst")},
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
