# -*- coding: utf-8 -*-
"""LLM一次診断医: escalate_human(自動復旧の上限超え/意味ゲート連敗)が出た時に、
ローカルqwen3:14bが状況を読み、人間向けの診断要約と推奨手順を書く。

役割制約(growth_loop_quality_protocol準拠):
- **診断・助言のみ。コマンド実行・状態変更・ゲート判定は一切しない**
- 使用モデルはローカルのみ(qwen3:14b=現行ハード上限、API費ゼロ)
- Ollama停止時は静かにスキップ(診断がないだけで復旧系は影響なし)

出力: data/workspace/self_heal_diagnosis_latest.md + 履歴jsonl
"""
from __future__ import annotations

import sys

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import json
import urllib.request
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WS = ROOT / "data" / "workspace"
JST = timezone(timedelta(hours=9))
OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "qwen3:14b"
OUT_MD = WS / "self_heal_diagnosis_latest.md"
OUT_LOG = WS / "self_heal_diagnosis_log.jsonl"

CONTEXT_FILES = [
    ("self_heal_status", WS / "self_heal_status.json"),
    ("tri_track", WS / "k10_tri_track_cae_status.json"),
    ("supervisor", WS / "apps" / "mecha_motion_lab" / "supervisor_status.json"),
    ("growth_audit", WS / "growth_loop_audit_status.json"),
    ("dead_recheck", WS / "dead_project_recheck_status.json"),
]


def read_tail_jsonl(path: Path, n: int = 20) -> list:
    if not path.exists():
        return []
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    out = []
    for line in lines[-n:]:
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return out


def build_context() -> dict:
    """診断材料の収集(純関数的・テスト対象)。"""
    ctx = {"collected_at": datetime.now(JST).isoformat(),
           "heal_log_tail": read_tail_jsonl(WS / "self_heal_log.jsonl", 20)}
    for name, p in CONTEXT_FILES:
        try:
            ctx[name] = json.loads(p.read_text(encoding="utf-8"))
        except Exception as exc:
            ctx[name] = {"_unreadable": str(exc)[:80]}
    return ctx


def build_prompt(ctx: dict) -> str:
    escalations = [a for a in (ctx.get("self_heal_status") or {}).get("actions", [])
                   if a.get("action") == "escalate_human"]
    return (
        "あなたは製造業CAE/MLインフラの一次診断医です。自動復旧システムが人間への"
        "エスカレーションを発行しました。以下のJSON状態から、(1)何が起きているか3行以内 "
        "(2)最も可能性の高い根本原因の仮説を過去トラID(T050-T056系統)と関連づけて "
        "(3)人間が最初に実行すべき確認コマンド/手順を3つまで、日本語で簡潔に。"
        "コードや設定の変更提案はしない。実行もしない。\n\n"
        f"## エスカレーション\n{json.dumps(escalations, ensure_ascii=False)}\n\n"
        f"## システム状態\n{json.dumps(ctx, ensure_ascii=False)[:6000]}\n"
    )


def call_ollama(prompt: str) -> str | None:
    req = urllib.request.Request(
        OLLAMA_URL,
        data=json.dumps({"model": MODEL, "prompt": prompt, "stream": False,
                         "options": {"temperature": 0.2}}).encode("utf-8"),
        headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=420) as r:  # CPU推論≈7tok/s考慮
            return json.loads(r.read().decode("utf-8")).get("response")
    except Exception as exc:
        print(f"[diagnose] Ollama不達のためスキップ: {str(exc)[:80]}")
        return None


def main() -> int:
    ctx = build_context()
    diagnosis = call_ollama(build_prompt(ctx))
    now = datetime.now(JST).isoformat()
    if diagnosis:
        OUT_MD.write_text(
            f"# 自己修復 一次診断 (qwen3:14b・助言のみ)\n\n生成: {now}\n\n{diagnosis}\n\n"
            "---\n注意: これはローカルLLMの仮説です。実行前に過去トラDBと照合してください。\n",
            encoding="utf-8")
        with OUT_LOG.open("a", encoding="utf-8") as f:
            f.write(json.dumps({"at": now, "ok": True, "chars": len(diagnosis)},
                               ensure_ascii=False) + "\n")
        print(f"[diagnose] 診断書生成: {OUT_MD}")
    else:
        with OUT_LOG.open("a", encoding="utf-8") as f:
            f.write(json.dumps({"at": now, "ok": False, "note": "ollama_unreachable"},
                               ensure_ascii=False) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
