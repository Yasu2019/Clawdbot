# -*- coding: utf-8 -*-
"""発見・対策を全知識系統へ**1コマンドで**記録する。

2026-08-10 導入。背景(実測):
  CLAUDE.md は「Beads・Byterover queue・Obsidian Vault(FailureKnowledge/)・
  auto-memory に記録済み」と述べていたが、実態は乖離していた:
    - Beads          : 記録あり(278メモリ)
    - Obsidian       : **FailureKnowledge/ は存在しない**(実在は トラブルシューティング/)
    - graphify       : manifest が 7/30 から未更新。hookは毎回 600秒でタイムアウト
    - Byterover      : コンテナ未稼働・.env設定なし = **記録先が存在しない**
    - Turso          : メール用スクリプトのみ。知識記録には未使用
  「複数系統に書く」を人手の努力目標にすると必ず抜ける。1コマンドに畳む。

記録先(実在が確認できたもののみ):
  1. Beads          `bd remember`(全AI共有の一次記録)
  2. Obsidian Vault `data/workspace/obsidian_vault/トラブルシューティング/`
  3. auto-memory    `~/.claude/projects/<proj>/memory/`(Claude Code のセッション跨ぎ記憶)
  4. ByteRover      `brv curate`(2026-08-10 追加。ローカル利用は無課金・ログイン不要)
  Turso はメール用途のみのため対象外。graphify は別問題(hookが毎回600秒でタイムアウト)。

文字コード規約(グローバルルール 2026-08-08):
  書き込みは encoding="utf-8" を明示し、書き戻して U+FFFD と化け記号を検証する。

usage:
  python scripts/record_finding.py --title "..." --what "..." --why "..." --how "..."
  python scripts/record_finding.py --title "..." --what "..." --tags rl,reward --dry-run
"""
from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
import time
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # P023

REPO = Path(r"D:\Clawdbot_Docker_20260125")
OBSIDIAN = REPO / "data" / "workspace" / "obsidian_vault" / "トラブルシューティング"
AUTO_MEMORY = Path(r"C:\Users\yasu\.claude\projects\D--Clawdbot-Docker-20260125\memory")
MOJIBAKE_MARKS = "縺繧繝"


def slug(s: str, maxlen: int = 50) -> str:
    s = re.sub(r"[^\w\u3040-\u30ff\u4e00-\u9fff-]+", "_", s).strip("_")
    return s[:maxlen] or "finding"


def write_verified(path: Path, text: str) -> bool:
    """UTF-8で書き、読み戻して化けが無いか検証する(グローバルルール)。"""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    back = path.read_text(encoding="utf-8")
    bad = back.count("\ufffd") + sum(back.count(m) for m in MOJIBAKE_MARKS)
    if back != text or bad:
        path.unlink(missing_ok=True)
        print(f"  × 検証失敗のため削除: {path} (化け {bad} 件)")
        return False
    return True


def to_beads(title: str, body: str) -> bool:
    try:
        r = subprocess.run(["bd", "remember", f"{title}: {body}"],
                           cwd=str(REPO), capture_output=True, text=True,
                           encoding="utf-8", errors="replace", timeout=180)
        ok = r.returncode == 0
        print(f"  {'✓' if ok else '×'} Beads" + ("" if ok else f" ({(r.stderr or '')[:80]})"))
        return ok
    except Exception as e:
        print(f"  × Beads ({type(e).__name__}: {e})")
        return False


def to_obsidian(title: str, what: str, why: str, how: str, tags: list[str],
                evidence: str) -> bool:
    stamp = time.strftime("%Y%m%d")
    path = OBSIDIAN / f"{stamp}_{slug(title)}.md"
    tagline = " ".join(f"#{t}" for t in tags) if tags else ""
    text = (
        f"---\ncreated: {time.strftime('%Y-%m-%d %H:%M')}\n"
        f"tags: [{', '.join(tags)}]\nsource: scripts/record_finding.py\n---\n\n"
        f"# {title}\n\n{tagline}\n\n"
        f"## 何が起きていたか\n\n{what}\n\n"
        f"## なぜそうなったか\n\n{why or '(未記入)'}\n\n"
        f"## どう対処したか\n\n{how or '(未記入)'}\n\n"
        f"## 証拠(実測値)\n\n{evidence or '(未記入)'}\n")
    ok = write_verified(path, text)
    print(f"  {'✓' if ok else '×'} Obsidian: {path}")
    return ok


def to_byterover(title: str, body: str) -> bool:
    """ByteRover CLI(brv) へ記録する。

    2026-08-10 実測:
      - `brv` 3.10.0 は導入済みで、ローカル利用に**課金もログインも不要**
        (`brv login` は "optional for local usage" と明記。課金はクラウド同期のみ)。
      - `brv curate --detach` は成功する(success:true / taskId発行)。
      - 一方 `brv query` は現状 4096トークンのローカルLLM上限を超えて失敗する
        (request 23754 tokens exceeds context size 4096)。
        **書き込みは有効・読み出しは未整備**という状態なので、記録先としてのみ使う。
    """
    try:
        r = subprocess.run(
            ["brv", "curate", f"{title}: {body}", "--detach", "--format", "json"],
            cwd=str(REPO), capture_output=True, text=True,
            encoding="utf-8", errors="replace", timeout=300, shell=(os.name == "nt"))
        ok = r.returncode == 0 and '"success":true' in (r.stdout or "").replace(" ", "")
        print(f"  {'✓' if ok else '×'} ByteRover"
              + ("" if ok else f" ({((r.stdout or '') + (r.stderr or ''))[:100]})"))
        return ok
    except FileNotFoundError:
        print("  - ByteRover (brv 未インストール — スキップ)")
        return True          # 未導入は失敗扱いにしない
    except Exception as e:
        print(f"  × ByteRover ({type(e).__name__}: {e})")
        return False


def to_auto_memory(title: str, what: str, why: str, how: str, tags: list[str]) -> bool:
    name = slug(title, 40).lower().replace("_", "-")
    path = AUTO_MEMORY / f"finding_{slug(title, 40).lower()}.md"
    text = (
        f"---\nname: {name}\n"
        f"description: {what.splitlines()[0][:100] if what else title}\n"
        f"metadata:\n  type: project\n---\n\n"
        f"{what}\n\n**Why:** {why or '(未記入)'}\n\n"
        f"**How to apply:** {how or '(未記入)'}\n")
    ok = write_verified(path, text)
    print(f"  {'✓' if ok else '×'} auto-memory: {path}")
    return ok


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--title", required=True)
    ap.add_argument("--what", required=True, help="何が起きていたか(症状・事実)")
    ap.add_argument("--why", default="", help="なぜそうなったか(根本原因)")
    ap.add_argument("--how", default="", help="どう対処したか(最小変更)")
    ap.add_argument("--evidence", default="", help="実測値・ログ")
    ap.add_argument("--tags", default="", help="カンマ区切り")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    tags = [t.strip() for t in a.tags.split(",") if t.strip()]
    body = " / ".join(x for x in [a.what, a.why, a.how, a.evidence] if x)

    if a.dry_run:
        print("[dry-run] 記録先:")
        print(f"  Beads      : bd remember \"{a.title}: {body[:70]}...\"")
        print(f"  Obsidian   : {OBSIDIAN / (time.strftime('%Y%m%d') + '_' + slug(a.title) + '.md')}")
        print(f"  auto-memory: {AUTO_MEMORY / ('finding_' + slug(a.title, 40).lower() + '.md')}")
        return 0

    print(f"記録: {a.title}")
    results = [
        to_beads(a.title, body),
        to_obsidian(a.title, a.what, a.why, a.how, tags, a.evidence),
        to_auto_memory(a.title, a.what, a.why, a.how, tags),
        to_byterover(a.title, body),
    ]
    n_ok = sum(results)
    print(f"\n{n_ok}/{len(results)} 系統へ記録しました。")
    if n_ok < len(results):
        print("失敗した系統があります。原因を確認してください(黙って進めない)。")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
