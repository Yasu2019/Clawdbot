"""DB自己修復モジュール — LLM診断 + 自動修正 + ペンディングキューリプレイ

障害フロー:
  DB書き込み全リトライ失敗
    → エラーをルールベースで分類
    → 既知外エラーはローカルLLM (local_fast=qwen3:8b, 外部送信なし) で診断
    → 安全な修正 (起動待ち・docker start・テーブル作成) を実行
    → 修正後に1回リトライ
    → それでも失敗 → pending_db_records.jsonl に退避 + Telegram通知
  次回 run_pipeline.py 起動時:
    → pending_db_records.jsonl を検出
    → 同じLLM診断で根本原因を確認
    → DB接続後に一括リプレイ → キュークリア
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys

# 日本語Windows(cp932)でpsycopg2がサーバーレスポンスをcp932でデコードしようとする問題を防ぐ。
# psycopg2 import前にPGCLIENTENCODINGを設定することで接続ハンドシェイクをUTF-8で処理させる。
os.environ.setdefault("PGCLIENTENCODING", "UTF8")
# stdout/stderrをUTF-8に再設定。cp932環境でU+2014(—)などを含むprint文が
# UnicodeEncodeErrorになり、DB接続エラーと誤認されるのを防ぐ。
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
if hasattr(sys.stderr, "reconfigure"):
    try:
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
import time
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path

ROOT         = Path(__file__).resolve().parents[3]
PENDING_QUEUE = ROOT / "projects" / "CityCharacterPipeline" / "knowledge" / "pending_db_records.jsonl"
LITELLM_URL  = "http://127.0.0.1:4001/v1"
DIAG_MODEL   = "local_fast"   # qwen3:8b — ローカルLLM。エラー文字列のみ送信（認証情報含まず）


def _pg_connect(db_url: str):
    """psycopg2接続ヘルパー。URLを手動パースしてキーワード引数で接続。
    日本語WindowsのURL文字列パース時cp932エラーを回避する。
    """
    import psycopg2
    parsed = urllib.parse.urlparse(db_url)
    return psycopg2.connect(
        host=parsed.hostname or "127.0.0.1",
        port=parsed.port or 5432,
        dbname=(parsed.path or "/sim_trials").lstrip("/"),
        user=parsed.username or "postgres",
        password=parsed.password or "",
        connect_timeout=10,
        options="-c client_encoding=UTF8",
    )


# ── 既知エラーのルールテーブル ────────────────────────────────
# pattern: 正規表現, fix_type: 実行する修正の種別
_KNOWN_ERRORS: list[dict] = [
    {
        "pattern":   r"database system is starting up",
        "diagnosis": "PostgreSQL起動中。完全起動を待機してからリトライする。",
        "fix_type":  "wait",
        "wait_sec":  20,
    },
    {
        "pattern":   r"Connection (timed out|refused)|could not connect",
        "diagnosis": "PostgreSQLコンテナが停止中または到達不能。docker start を試みる。",
        "fix_type":  "docker_start",
    },
    {
        "pattern":   r"password authentication failed|role .* does not exist",
        "diagnosis": "DB接続URL のユーザー/パスワードが不正。DATABASE_URL 環境変数または knowledge_recorder.py の_DB_URLを確認すること。",
        "fix_type":  "notify_only",
    },
    {
        "pattern":   r'relation ".*" does not exist',
        "diagnosis": "テーブルが存在しない。_ensure_table() でCREATE TABLEを実行する。",
        "fix_type":  "create_table",
    },
    {
        "pattern":   r"could not locate a valid checkpoint record|invalid checkpoint",
        "diagnosis": "WAL破損（pg_resetwal必須）。自動修正は危険なため手動対応が必要。",
        "fix_type":  "notify_only",
    },
    {
        "pattern":   r"too many connections",
        "diagnosis": "PostgreSQL接続数上限到達。少し待機してリトライする。",
        "fix_type":  "wait",
        "wait_sec":  10,
    },
]


# ── LLM診断（ローカル専用・urllib使用） ─────────────────────────
def _llm_diagnose(error_str: str) -> dict:
    """ローカルLLM (qwen3:8b via LiteLLM) でエラーを診断する。

    - openaiパッケージ不要: urllib で直接LiteLLM REST APIを呼ぶ
    - 外部API送信なし: LiteLLMがローカルOllamaにルーティング
    - エラー文字列のみ送信（DB URL・パスワードは除去済み）
    - タイムアウト15秒。失敗時はrule外(notify_only)で返す
    """
    # 認証情報をマスク、ASCII安全化してLLMに送る
    safe_error = re.sub(r"password=\S+", "password=***", error_str)
    safe_error = re.sub(r"://\S+:\S+@", "://***:***@", safe_error)
    safe_error = safe_error[:500]

    prompt = (
        "あなたはPostgreSQLエラー診断AIです。"
        "以下のエラーを分析し、次のJSON形式のみで回答してください（他のテキスト不要）:\n"
        '{"diagnosis": "原因の説明（日本語50字以内）", '
        '"fix_type": "wait|docker_start|create_table|notify_only"}\n\n'
        f"エラー: {safe_error}"
    )
    body = json.dumps({
        "model":      DIAG_MODEL,
        "messages":   [{"role": "user", "content": prompt}],
        "max_tokens": 120,
    }).encode("utf-8")

    try:
        req = urllib.request.Request(
            f"{LITELLM_URL}/chat/completions",
            data=body,
            headers={"Content-Type": "application/json", "Authorization": "Bearer dummy"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            result = json.loads(resp.read().decode("utf-8"))
        raw = result["choices"][0]["message"]["content"].strip()
        m = re.search(r"\{.*\}", raw, re.DOTALL)
        if m:
            parsed = json.loads(m.group(0))
            return {
                "source":    "llm",
                "diagnosis": parsed.get("diagnosis", raw[:100]),
                "fix_type":  parsed.get("fix_type", "notify_only"),
            }
        return {"source": "llm", "diagnosis": raw[:100], "fix_type": "notify_only"}
    except Exception as e:
        return {
            "source":    "fallback",
            "diagnosis": f"LLM診断サービス不応答 ({e.__class__.__name__}): 手動確認を推奨",
            "fix_type":  "notify_only",
        }


# ── エラー分類 + 自動修正 ─────────────────────────────────────
def diagnose_and_fix(error_str: str) -> tuple[str, bool]:
    """エラー文字列を診断し、安全な自動修正を実行する。

    Returns:
        (diagnosis_text, was_fixed): 診断文と修正が実施されたかどうか
    """
    # ルールベース優先
    result: dict | None = None
    for rule in _KNOWN_ERRORS:
        if re.search(rule["pattern"], error_str, re.IGNORECASE):
            result = rule.copy()
            break

    # ルール外 → ローカルLLM診断
    if result is None:
        print("[DBHealer] 既知ルール外エラー。ローカルLLM (local_fast) で診断中...", flush=True)
        result = _llm_diagnose(error_str)
        print(f"[DBHealer] LLM診断結果 [{result['source']}]: {result['diagnosis']}", flush=True)
    else:
        print(f"[DBHealer] ルールベース診断: {result['diagnosis']}", flush=True)

    fix_type = result.get("fix_type", "notify_only")
    fixed    = False

    if fix_type == "wait":
        wait_sec = result.get("wait_sec", 20)
        print(f"[DBHealer] 修正: {wait_sec}秒待機後にリトライ", flush=True)
        time.sleep(wait_sec)
        fixed = True

    elif fix_type == "docker_start":
        print("[DBHealer] 修正: docker start clawstack-unified-postgres-1", flush=True)
        try:
            r = subprocess.run(
                ["docker", "start", "clawstack-unified-postgres-1"],
                capture_output=True, timeout=30,
            )
            if r.returncode == 0:
                print("[DBHealer] コンテナ起動完了。15秒待機...", flush=True)
                time.sleep(15)
                fixed = True
            else:
                print(f"[DBHealer] docker start 失敗: {r.stderr.decode()[:200]}", flush=True)
        except Exception as e:
            print(f"[DBHealer] docker start 例外: {e}", flush=True)

    elif fix_type == "create_table":
        # _ensure_table()が次のリトライで自動対応するので待機のみ
        print("[DBHealer] 修正: テーブル再作成を次リトライに委譲", flush=True)
        fixed = True

    elif fix_type == "notify_only":
        print(f"[DBHealer] 自動修正不可（手動対応必須）: {result['diagnosis']}", flush=True)
        _send_telegram_alert(error_str, result["diagnosis"])

    return result["diagnosis"], fixed


# ── ペンディングキュー ────────────────────────────────────────
def save_to_pending_queue(record: dict):
    """DB書き込み失敗時にペンディングキューに退避する。"""
    PENDING_QUEUE.parent.mkdir(parents=True, exist_ok=True)
    entry = {**record, "queued_at": datetime.now().isoformat()}
    with open(PENDING_QUEUE, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False, default=str) + "\n")
    count = sum(1 for _ in open(PENDING_QUEUE, encoding="utf-8"))
    print(f"[DBHealer] ペンディングキューに退避 (合計{count}件): {PENDING_QUEUE}", flush=True)


def replay_pending_queue(db_url: str) -> int:
    """起動時にペンディングキューを読み込み、LLM診断後にDBへ一括INSERT。

    成功件数を返す。失敗行はキューに残す。
    """
    if not PENDING_QUEUE.exists():
        return 0

    lines = [l.strip() for l in PENDING_QUEUE.read_text(encoding="utf-8").splitlines() if l.strip()]
    if not lines:
        return 0

    print(f"\n[DBHealer] ペンディングキュー検出: {len(lines)} 件をリプレイ中", flush=True)

    # リプレイ前に接続テスト + LLM診断で根本原因を確認
    try:
        import psycopg2
        conn_test = _pg_connect(db_url)
        conn_test.close()
        print("[DBHealer] DB接続 OK -- リプレイ開始", flush=True)
    except Exception as e:
        print(f"[DBHealer] DB接続失敗。診断を実行します: {e}", flush=True)
        diagnosis, fixed = diagnose_and_fix(str(e))
        if not fixed:
            print(f"[DBHealer] 自動修正不可のため今回はリプレイをスキップ: {diagnosis}", flush=True)
            return 0
        # 修正後に再テスト
        try:
            conn_test = _pg_connect(db_url)
            conn_test.close()
        except Exception as e2:
            print(f"[DBHealer] 修正後も接続失敗。スキップ: {e2}", flush=True)
            return 0

    try:
        import psycopg2
        conn = _pg_connect(db_url)
        cur  = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS city_render_trials (
                id SERIAL PRIMARY KEY, scene_name TEXT, project_tag TEXT,
                config_json JSONB, qa_scores JSONB, render_params JSONB,
                fmea_json JSONB, output_path TEXT, render_sec FLOAT,
                status TEXT, lessons TEXT, created_at TIMESTAMP DEFAULT NOW()
            )
        """)
        conn.commit()
    except Exception as e:
        print(f"[DBHealer] リプレイ用DB接続失敗: {e}", flush=True)
        return 0

    inserted, failed_lines = 0, []
    for line in lines:
        try:
            r = json.loads(line)
            cur.execute("""
                INSERT INTO city_render_trials
                  (scene_name, project_tag, config_json, qa_scores, render_params,
                   fmea_json, output_path, render_sec, status, lessons)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            """, (
                r.get("scene_name"),
                r.get("project_tag", "city_character"),
                r.get("config_json", "{}"),
                r.get("qa_scores", "{}"),
                r.get("render_params", "{}"),
                r.get("fmea_json", "{}"),
                r.get("output_path", ""),
                float(r.get("render_sec", 0.0)),
                r.get("status", "unknown"),
                r.get("lessons", ""),
            ))
            inserted += 1
        except Exception as e:
            print(f"[DBHealer] 1件リプレイ失敗: {e}", flush=True)
            failed_lines.append(line)

    conn.commit()
    cur.close()
    conn.close()

    if failed_lines:
        PENDING_QUEUE.write_text("\n".join(failed_lines) + "\n", encoding="utf-8")
        print(
            f"[DBHealer] リプレイ完了: {inserted}/{len(lines)} 件成功, "
            f"{len(failed_lines)} 件残留（次回に持ち越し）",
            flush=True,
        )
    else:
        PENDING_QUEUE.unlink()
        print(f"[DBHealer] リプレイ完了: {inserted} 件全件成功。キュークリア", flush=True)

    return inserted


# ── Telegram通知 ──────────────────────────────────────────────
def _send_telegram_alert(error_str: str, diagnosis: str):
    """Telegram でDB障害を通知する。secrets/notification.json からトークンを読む。"""
    try:
        secret_path = ROOT / "clawstack_v2" / "secrets" / "notification.json"
        chat_id     = os.getenv("TELEGRAM_CHAT_ID", "8173025084")
        token       = None
        if secret_path.exists():
            secret = json.loads(secret_path.read_text(encoding="utf-8"))
            token  = secret.get("telegram_bot_token")
        if not token:
            print("[DBHealer] Telegram token 未設定 -- 通知スキップ", flush=True)
            return
        safe_error = str(error_str)[:300].replace("change_me", "***")
        msg = (
            "🚨 CityCharacterPipeline DB障害\n\n"
            f"診断: {diagnosis}\n\n"
            f"エラー概要: {safe_error}\n\n"
            "対応: pending_db_records.jsonl に退避済み。次回起動時に自動リプレイを試みます。"
        )
        body = urllib.parse.urlencode({"chat_id": chat_id, "text": msg}).encode("utf-8")
        req  = urllib.request.Request(
            f"https://api.telegram.org/bot{token}/sendMessage",
            data=body, method="POST",
        )
        with urllib.request.urlopen(req, timeout=10) as res:
            print(f"[DBHealer] Telegram通知: {res.status}", flush=True)
    except Exception as e:
        print(f"[DBHealer] Telegram通知失敗: {e}", flush=True)
