# -*- coding: utf-8 -*-
"""graphify のグラフを**明示的に**再構築する(コミット時フックの代替)。

2026-08-10 導入。背景(実測):
  `.beads/hooks/post-commit` に埋め込まれた graphify フックが、コミットのたびに
  600秒でタイムアウトして失敗し続けていた(manifest は 7/30 から未更新)。

  切り分けた結果:
    - フックは既に**差分再構築**(changed_paths を渡している)。それでも
      1ファイル変更の再構築が **400秒以上** かかり終わらない。
      つまりタイムアウト延長では解決しない。
    - manifest 9,413件の内訳は .json 5,106 / **.mp4 1,934** / .py 1,651 /
      .ps1 407 ... で、コードグラフに動画と生成JSONが大量に混ざっている。
    - `graphify-out/.graphify_build.json` に excludes を置いても
      `_rebuild_code()` はそれを読まない(CLI の scan 経路専用)。
      graphify CLI 側にも scan/rebuild サブコマンドが無い(install/path/explain 等のみ)。

  よってコミット毎の自動再構築は取り下げ、**明示実行**に切り替える。
  毎コミットで600秒を捨て続けるより、必要なときに回す方が実害が小さい。

フックの無効化(恒久):
  git config --local core.hooksPath は beads が使うため触らない。
  代わりに公式スイッチを使う:
      git config --local graphify.skipHook true   ← 記録用
      setx GRAPHIFY_SKIP_HOOK 1                   ← 実際に効くのはこちら
  フック側は `[ "${GRAPHIFY_SKIP_HOOK:-0}" = "1" ] && exit 0` を持っている。

usage:
  python scripts/graphify_rebuild.py --status      # 最終更新と規模を見る
  python scripts/graphify_rebuild.py --run         # 再構築(長時間・要覚悟)
  python scripts/graphify_rebuild.py --run --timeout 7200
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # P023

REPO = Path(r"D:\Clawdbot_Docker_20260125")
OUT = REPO / "graphify-out"
MANIFEST = OUT / "manifest.json"
PY_FILE = OUT / ".graphify_python"


def graphify_python() -> str | None:
    if PY_FILE.is_file():
        p = PY_FILE.read_text(encoding="utf-8").strip()
        if p and Path(p).exists():
            return p
    return None


def status() -> int:
    if not MANIFEST.is_file():
        print("manifest がありません。まだ一度も構築されていません。")
        return 1
    mtime = MANIFEST.stat().st_mtime
    age_h = (time.time() - mtime) / 3600
    try:
        m = json.loads(MANIFEST.read_text(encoding="utf-8"))
        n = len(m) if isinstance(m, list) else len(m.get("files", m))
    except Exception:
        n = "?"
    print(f"manifest: {n} 件 / 最終更新 "
          f"{time.strftime('%Y-%m-%d %H:%M', time.localtime(mtime))} "
          f"({age_h:.1f} 時間前)")
    print(f"python  : {graphify_python() or '(未特定)'}")
    skip = os.environ.get("GRAPHIFY_SKIP_HOOK", "0")
    print(f"フック   : GRAPHIFY_SKIP_HOOK={skip} "
          f"({'無効化済み(明示実行のみ)' if skip == '1' else '有効(毎コミットで走る)'})")
    if age_h > 24:
        print("\n※ 24時間以上更新されていません。グラフは現状と乖離しています。")
    return 0


def run(timeout: int) -> int:
    py = graphify_python()
    if not py:
        print("graphify の python を特定できません。")
        return 3
    code = (
        "import time,sys\n"
        "from pathlib import Path\n"
        "sys.stdout.reconfigure(encoding='utf-8', errors='replace')\n"
        "from graphify.watch import _rebuild_code\n"
        "t=time.time()\n"
        "_rebuild_code(Path('.').resolve(), changed_paths=None, force=False)\n"
        "print('rebuild完了', round(time.time()-t,1), '秒', flush=True)\n")
    env = dict(os.environ, PYTHONHASHSEED="0", GRAPHIFY_MAX_WORKERS="4")
    print(f"再構築を開始します(上限 {timeout} 秒)。長時間かかります。")
    t0 = time.time()
    try:
        r = subprocess.run([py, "-u", "-c", code], cwd=str(REPO), env=env,
                           timeout=timeout, text=True, encoding="utf-8",
                           errors="replace")
        print(f"終了コード {r.returncode} / {time.time()-t0:.0f} 秒")
        return r.returncode
    except subprocess.TimeoutExpired:
        print(f"{timeout} 秒で打ち切りました。対象を絞らない限り完走しません。")
        return 4


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--status", action="store_true")
    ap.add_argument("--run", action="store_true")
    ap.add_argument("--timeout", type=int, default=7200)
    a = ap.parse_args()
    if a.run:
        return run(a.timeout)
    return status()


if __name__ == "__main__":
    raise SystemExit(main())
