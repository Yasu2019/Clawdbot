# -*- coding: utf-8 -*-
"""数値リテラルを「バグ」と断じる前に、名前付き定義が無いかを機械的に確認する。

2026-08-18 導入。背景(実測):
  slope_down が斜面を降りない症状を追う中で、傾斜板の配置式にあった -0.92 を
  「ハードコードされたマジックナンバー」と誤認し、除去する変更をコミットした。
  実際には同じファイルに

      FLOOR_TOP = -0.92           # 床plane天面z(モデル固有)

  と名前付き定数として定義された正規の基準値だった。grep すれば1コマンドで
  行き当たったが、それをしなかった。誤りに基づいて有効な検証済みチェックポイントを
  無効化し、再学習まで起動した(すべて復旧済み)。

  「grep してから直す」を人手の努力目標にすると必ず抜ける。1コマンドに畳む。

使い方:
    python scripts/check_constant.py -0.92
    python scripts/check_constant.py 0.35 --path projects/AtsugiMechaCity

終了コード:
    0 = 名前付き定義なし(自由に変更してよい可能性が高い)
    2 = 名前付き定義またはコメントによる説明あり → **消す前に読むこと**
"""
import argparse
import os
import re
import subprocess
import sys

REPO = r"D:\Clawdbot_Docker_20260125"
# 「NAME = <値>」形式の定義。定数名は英大文字が慣例だが小文字も拾う。
DEF_RE = r'^[A-Za-z_][A-Za-z0-9_]*\s*=\s*{lit}\b'


SKIP_DIRS = {".git", "node_modules", "__pycache__", ".venv", "venv",
             ".beads", "buildcache", "site-packages"}
EXTS = (".py", ".yaml", ".yml", ".json", ".xml", ".ps1", ".sh", ".md")


def rg(pattern, path, extra=()):
    """ripgrep があれば使い、無ければ Python で走査する。(行のリスト) を返す。

    rg は PATH に無いことがある(2026-08-18 実測)。外部ツールの有無で
    チェックが素通りしては意味がないので、必ずフォールバックする。
    """
    cmd = ["rg", "--no-heading", "-n", "-e", pattern, path, *extra]
    try:
        p = subprocess.run(cmd, capture_output=True, text=True,
                           encoding="utf-8", errors="replace", timeout=120)
        return [ln for ln in p.stdout.splitlines() if ln.strip()]
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        pass
    rx = re.compile(pattern, re.M)
    out = []
    if os.path.isfile(path):
        files = [path]
    else:
        files = []
        for root, dirs, names in os.walk(path):
            dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
            files += [os.path.join(root, n) for n in names if n.endswith(EXTS)]
    for f in files:
        try:
            with open(f, encoding="utf-8", errors="replace") as fh:
                for i, line in enumerate(fh, 1):
                    if rx.search(line):
                        out.append(f"{f}:{i}:{line.rstrip()}")
        except OSError:
            continue
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("value", help="調べる数値リテラル(例: -0.92)")
    ap.add_argument("--path", default=REPO, help="検索範囲(既定: リポジトリ全体)")
    args = ap.parse_args()

    path = args.path if os.path.isabs(args.path) else os.path.join(REPO, args.path)
    lit = re.escape(args.value)

    defs = rg(DEF_RE.format(lit=lit), path)
    if defs is None:
        print("ripgrep(rg) が見つかりません。手動で grep してください。")
        return 2

    uses = rg(lit, path) or []
    # 定義行そのものは用例から除く
    def_set = set(defs)
    uses = [u for u in uses if u not in def_set]

    print(f"検索値: {args.value}   範囲: {path}")
    print()
    if defs:
        print(f"⚠ 名前付き定義が {len(defs)} 件あります。**消す前に必ず読むこと**:")
        for d in defs[:20]:
            print("   ", d.strip()[:160])
        print()
        print("この値は意味のある基準値である可能性が高い。")
        print("マジックナンバーとして除去する前に、定義とコメントを読むこと。")
    else:
        print("名前付き定義は見つかりませんでした。")

    if uses:
        print()
        print(f"他の使用箇所 {len(uses)} 件(先頭10件):")
        for u in uses[:10]:
            print("   ", u.strip()[:160])

    print()
    print("--- 変更前チェックリスト(T079w) ---")
    print(" [ ] この値は他の量と基準(座標原点・単位・符号)が同じか")
    print("     基準が違えば一定オフセットが出るのは正常であり、バグの証拠ではない")
    print(" [ ] 変更後の検証を、変更した式**以外**の独立した経路で行えるか")
    print("     式を式で検算するのは循環論法。実測・目視など別系統の証拠を取る")
    print(" [ ] 仮説が実測で確定したか")
    print("     確定前にコミット・既存成果の無効化・長時間ジョブ起動をしない")
    return 2 if defs else 0


if __name__ == "__main__":
    sys.exit(main())
