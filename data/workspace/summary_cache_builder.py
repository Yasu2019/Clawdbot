#!/usr/bin/env python3
"""
summary_cache_builder.py

ローカルLLM(Ollama)が空いているときだけ、
DBのtasksテーブルの request_summary を順次生成してキャッシュする。

- 最新のメールから遡って処理（request_date DESC）
- Ollamaが他のリクエストを処理中なら待機してリトライ
- エラー・タイムアウト時はバックオフして継続
- DBはローカル読み取りのみ（Gmail API / 外部API消費ゼロ）
"""
from __future__ import annotations

import json
import signal
import sqlite3
import sys
import time
import urllib.request
from datetime import datetime, timezone, timedelta
from pathlib import Path

# ─── 設定 ────────────────────────────────────────────
OLLAMA_BASE     = "http://ollama:11434"
OLLAMA_MODEL    = "qwen2.5-coder:7b"
SUMMARY_TIMEOUT = 180         # 1件あたりタイムアウト秒（CPU推論は遅いので余裕を持たせる）
BUSY_WAIT_SEC   = 45          # Ollama ビジー時の待機秒
DONE_WAIT_SEC   = 300         # 全件処理後の次回チェック間隔秒
INTER_REQ_SEC   = 2           # 正常完了後の次リクエストまでの間隔秒
SUMMARY_MAX_LEN = 800         # 本文の最大文字数（LLMに渡す）
LOG_PATH        = Path("/home/node/clawd/summary_cache_builder.log")
PID_PATH        = Path("/home/node/clawd/summary_cache_builder.pid")
JST             = timezone(timedelta(hours=9))

DB_CANDIDATES = [
    Path("/home/node/clawd/email_search.db"),
    Path(__file__).resolve().parent / "email_search.db",
]
# ─────────────────────────────────────────────────────


def find_db() -> Path:
    for p in DB_CANDIDATES:
        if p.exists():
            return p
    raise FileNotFoundError(f"email_search.db not found in {DB_CANDIDATES}")


def log(msg: str) -> None:
    ts = datetime.now(JST).strftime("%Y-%m-%d %H:%M:%S JST")
    line = f"[{ts}] {msg}"
    print(line, flush=True)
    try:
        with LOG_PATH.open("a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass


def ollama_get(path: str, timeout: int = 5) -> dict:
    req = urllib.request.Request(f"{OLLAMA_BASE}{path}", method="GET")
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def is_ollama_busy() -> bool:
    """Ollamaが他のリクエストを処理中か判定（size_vram > 0 = GPU使用中）"""
    try:
        data = ollama_get("/api/ps", timeout=5)
        for m in data.get("models", []):
            if m.get("size_vram", 0) > 0:
                return True
        return False
    except Exception:
        return False  # 接続失敗時はビジーとみなさず通常続行


def is_ollama_available() -> bool:
    try:
        ollama_get("/api/tags", timeout=5)
        return True
    except Exception:
        return False


def generate_summary(subject: str, body: str) -> str | None:
    body_trimmed = (body or "")[:SUMMARY_MAX_LEN]
    prompt = (
        "以下はメールの件名と本文です。依頼内容を日本語で2〜3文に要約してください。\n"
        "挨拶・署名・宣伝文句は除外し、何を・いつまでに・どうしてほしいかを中心にまとめてください。\n\n"
        f"【件名】{subject}\n【本文】{body_trimmed}\n\n【要約】"
    )
    payload = json.dumps({
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": 0.2, "num_predict": 120},
    }).encode("utf-8")
    req = urllib.request.Request(
        f"{OLLAMA_BASE}/api/generate",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=SUMMARY_TIMEOUT) as resp:
        result = json.loads(resp.read().decode("utf-8"))
        text = result.get("response", "").strip()
        return text if text else None


def fetch_uncached(con: sqlite3.Connection, limit: int = 50) -> list[dict]:
    rows = con.execute(
        """
        SELECT source, source_id, request_subject, request_body, request_date
        FROM tasks
        WHERE COALESCE(request_summary, '') = ''
          AND COALESCE(request_body, '') <> ''
        ORDER BY request_date DESC
        LIMIT ?
        """,
        (limit,),
    ).fetchall()
    return [dict(r) for r in rows]


def save_summary(con: sqlite3.Connection, source: str, source_id: str, summary: str) -> None:
    con.execute(
        "UPDATE tasks SET request_summary = ? WHERE source = ? AND source_id = ?",
        (summary, source, source_id),
    )
    con.commit()


def run_forever(db_path: Path) -> None:
    log(f"起動 — DB: {db_path}  モデル: {OLLAMA_MODEL}")
    PID_PATH.write_text(str(PID_PATH.resolve()), encoding="utf-8")

    processed_total = 0
    consecutive_errors = 0

    while True:
        # Ollama が起動していない場合は待機
        if not is_ollama_available():
            log("Ollama 未応答 — 60秒後リトライ")
            time.sleep(60)
            continue

        con = sqlite3.connect(db_path, timeout=30)
        con.row_factory = sqlite3.Row
        try:
            uncached = fetch_uncached(con)
        finally:
            con.close()

        if not uncached:
            log(f"未キャッシュ件数: 0 — {DONE_WAIT_SEC}秒後に再チェック (累計処理: {processed_total}件)")
            time.sleep(DONE_WAIT_SEC)
            continue

        log(f"未キャッシュ: {len(uncached)}件 — 処理開始")

        for task in uncached:
            source    = task["source"]
            source_id = task["source_id"]
            subject   = task["request_subject"] or ""
            body      = task["request_body"] or ""
            req_date  = task["request_date"] or ""

            # Ollama がビジーなら待機
            wait_count = 0
            while is_ollama_busy():
                if wait_count == 0:
                    log(f"  Ollama ビジー — {BUSY_WAIT_SEC}秒待機中...")
                wait_count += 1
                time.sleep(BUSY_WAIT_SEC)

            # 要約生成
            try:
                summary = generate_summary(subject, body)
                if summary:
                    con = sqlite3.connect(db_path, timeout=30)
                    try:
                        save_summary(con, source, source_id, summary)
                    finally:
                        con.close()
                    processed_total += 1
                    consecutive_errors = 0
                    short_id = source_id[:40] if len(source_id) > 40 else source_id
                    log(f"  ✓ [{req_date}] {short_id[:35]} → キャッシュ保存 (累計{processed_total}件)")
                else:
                    log(f"  空レスポンス — スキップ: {source_id[:40]}")

            except TimeoutError:
                consecutive_errors += 1
                wait = min(BUSY_WAIT_SEC * consecutive_errors, 300)
                log(f"  タイムアウト (連続{consecutive_errors}回) — {wait}秒待機")
                time.sleep(wait)

            except Exception as e:
                consecutive_errors += 1
                wait = min(30 * consecutive_errors, 300)
                log(f"  エラー: {e} — {wait}秒待機")
                time.sleep(wait)

            else:
                time.sleep(INTER_REQ_SEC)

        # 1バッチ完了 → 次のバッチへ（少し休憩）
        time.sleep(5)


def main() -> None:
    import os

    # 多重起動防止
    if PID_PATH.exists():
        try:
            existing_pid = int(PID_PATH.read_text().strip().split("\n")[0])
            # /proc/{pid} が存在すれば既に起動中
            if Path(f"/proc/{existing_pid}").exists():
                print(f"Already running (PID {existing_pid}) — exit", flush=True)
                sys.exit(0)
        except Exception:
            pass
    PID_PATH.write_text(str(os.getpid()), encoding="utf-8")

    # シグナルハンドラ（SIGTERM/SIGINT で正常終了）
    def _stop(sig, frame):  # noqa
        log("停止シグナル受信 — 終了します")
        try:
            PID_PATH.unlink(missing_ok=True)
        except Exception:
            pass
        sys.exit(0)

    signal.signal(signal.SIGTERM, _stop)
    signal.signal(signal.SIGINT, _stop)

    db_path = find_db()
    run_forever(db_path)


if __name__ == "__main__":
    main()
