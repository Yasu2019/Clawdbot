# -*- coding: utf-8 -*-
"""着手前に「ローカル知識で足りるか」を判定し、足りなければ外部調査を促す。

2026-08-10 導入。背景(実測):
  RL歩行の終了条件が業界標準から逸脱していた件で、自前の試行錯誤を数時間続けたが、
  答えは公開実装(unitree_rl_gym G1)に1行で書かれていた。
    terminate_after_contacts_on = ["pelvis"]
    penalize_contacts_on        = ["hip", "knee"]
  収集コーパスを検索すると humanoid 15件 / legged 8件しかなく、この分野の文献は
  実質ゼロだった。「30万件収集済み」の実態が一意5,591件であることに加え、
  **収集分野が北極星と噛み合っていない**ことが具体的に示された。
  ローカルに無いなら外部を見るしかないが、その判断が人手の勘に委ねられていた。

本ツールがすること:
  1. ローカル知識(Qdrant clawstack_docs / FTS knowhow_ja / pdftext_ja / material_ja)
     を横断して件数を数える
  2. 閾値未満なら「ローカル不足」と判定し、外部調査すべき旨と具体的な調べ先を出す
  3. 判定結果を標準出力に残す(黙って自前実装に走らない)

usage:
  python scripts/research_gate.py "humanoid RL termination contact"
  python scripts/research_gate.py "順送金型 クリアランス" --min-hits 5
"""
from __future__ import annotations

import argparse
import json
import os
import sqlite3
import sys
import urllib.request
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # P023

REPO = Path(r"D:\Clawdbot_Docker_20260125")
FTS_DB = REPO / "data" / "workspace" / "universal_growth_fts_ja.db"
QDRANT = os.getenv("QDRANT_URL", "http://localhost:6333")
OLLAMA = os.getenv("OLLAMA_URL", "http://localhost:11434")
EMBED_MODEL = os.getenv("EMBED_MODEL", "mxbai-embed-large")
COLLECTION = "clawstack_docs"
MIN_TRIGRAM_CHARS = 3      # FTS5 trigram は3文字未満だと必ず0件になる


def fts_counts(terms: list[str]) -> dict:
    """全語が**同一文書に共起**する件数を数える。

    2026-08-10: 当初は語ごとの件数を合計していたが、'contact'(1518件)や
    'termination'(197件)のような一般語が無関係文書に大量ヒットし、
    「ローカルに知見あり」と誤判定した(まさに外部調査が必要だった題材で)。
    FTS5 の MATCH は空白区切りを AND として扱うので、クエリ全体を渡す。
    """
    out = {}
    if not FTS_DB.exists():
        return out
    usable = [t for t in terms if len(t) >= MIN_TRIGRAM_CHARS]
    if not usable:
        return {t: 0 for t in ("knowhow_ja", "pdftext_ja", "material_ja")}
    expr = " ".join(f'"{t}"' for t in usable)   # 全語AND
    con = sqlite3.connect(f"file:{FTS_DB}?mode=ro", uri=True, timeout=60)
    for tbl in ("knowhow_ja", "pdftext_ja", "material_ja"):
        try:
            out[tbl] = con.execute(
                f"SELECT COUNT(*) FROM {tbl} WHERE {tbl} MATCH ?", (expr,)).fetchone()[0]
        except Exception:
            out[tbl] = 0
    return out


def qdrant_hits(query: str, threshold: float = 0.75) -> tuple[int, float]:
    """閾値0.75の根拠(実測): このコーパスでは無関係な文書でも0.65〜0.72が出る。
    例) 「best_walker チェックポイント選定」-> PROMISES.md が 0.666。
    真に関連する T077(VRAM競合)でも0.72程度なので、0.60では判別できない。
    """
    """意味検索でスコア閾値を超えた件数と最高スコア。"""
    try:
        body = json.dumps({"model": EMBED_MODEL, "input": [query[:450]],
                           "options": {"num_gpu": 0}}).encode()
        req = urllib.request.Request(f"{OLLAMA}/api/embed", data=body,
                                     headers={"Content-Type": "application/json"})
        vec = json.load(urllib.request.urlopen(req, timeout=300))["embeddings"][0]
        body = json.dumps({"vector": vec, "limit": 10, "with_payload": False}).encode()
        req = urllib.request.Request(
            f"{QDRANT}/collections/{COLLECTION}/points/search", data=body,
            headers={"Content-Type": "application/json"})
        res = json.load(urllib.request.urlopen(req, timeout=120))["result"]
        scores = [h["score"] for h in res]
        return sum(1 for s in scores if s >= threshold), (max(scores) if scores else 0.0)
    except Exception as e:
        print(f"  (意味検索に失敗: {type(e).__name__})")
        return 0, 0.0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("query")
    ap.add_argument("--min-hits", type=int, default=3,
                    help="これ未満なら『ローカル不足』と判定する")
    a = ap.parse_args()

    terms = [t for t in a.query.replace("　", " ").split() if t]
    print(f"調査対象: {a.query}\n")

    n_sem, top = qdrant_hits(a.query)
    print(f"意味検索 clawstack_docs : score>=0.75 が {n_sem} 件 (最高 {top:.3f})")

    fts = fts_counts(terms)
    for k, v in fts.items():
        print(f"全文検索 {k:<12}: {v} 件 (全語AND一致)")
    short = [t for t in terms if len(t) < MIN_TRIGRAM_CHARS]
    if short:
        print(f"  ※ {short} は3文字未満のためtrigram検索では必ず0件です")

    total_fts = sum(fts.values())
    print()
    if n_sem >= a.min_hits or total_fts >= a.min_hits:
        print("判定: ローカル知識で着手可能。search_docs.py で内容を読んでから進めること。")
        return 0

    print("判定: **ローカル知識が不足しています。外部調査を先に行ってください。**")
    print()
    print("推奨する調べ先(この順):")
    print("  1. 公開実装の設定ファイル — 論文より速く確実。例:")
    print("     github.com/leggedrobotics/legged_gym (四足/脚式の基準実装)")
    print("     github.com/unitreerobotics/unitree_rl_gym (実機ヒューマノイド G1/H1)")
    print("  2. WebSearch でライブラリ名+設定キー名を検索(概念語だけで探さない)")
    print("  3. 一次情報(論文/公式ドキュメント)で裏を取る")
    print()
    print("外部で得た知見は必ず記録すること:")
    print('  python scripts/record_finding.py --title "..." --what "..." --why "..." --how "..."')
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
