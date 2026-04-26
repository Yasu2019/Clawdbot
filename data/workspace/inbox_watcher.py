#!/usr/bin/env python3
"""
inbox_watcher.py — フォルダ監視 + OpenClaw判断エージェント (Phase 1.5)
======================================================================
/home/node/clawd/inbox/ を監視し、ファイルが投入されたら
ファイル内容を読み込んでOpenClawエージェントに判断させ、
判断結果に応じて自動ルーティングを実行する。

自動ルーティング:
  paperless → Paperless consume フォルダへコピー (自動OCR・アーカイブ)
  rag       → RAG ingestionキューへ移動 (Qdrant universal_knowledge)
  iatf      → Telegram通知のみ (IATF登録は人間が確認)
  manual    → Telegram通知のみ

Usage:
  python3 /home/node/clawd/inbox_watcher.py
  python3 /home/node/clawd/inbox_watcher.py --dry-run
"""

import os
import json
import time
import shutil
import subprocess
import urllib.request
import urllib.error
from pathlib import Path
from datetime import datetime, timezone, timedelta
import sys

SCRIPT_PATH = Path(__file__).resolve()
if str(SCRIPT_PATH.parent) not in sys.path:
    sys.path.insert(0, str(SCRIPT_PATH.parent))

from outbound_delivery_guard import ensure_allowed_telegram_chat_id, initialize_guard_status

# ── 設定 ─────────────────────────────────────────────────────────────────────

JST          = timezone(timedelta(hours=9))
INBOX_DIR    = Path("/home/node/clawd/inbox")
PROCESSED_DIR = INBOX_DIR / "processed"
RAG_QUEUE_DIR = Path("/home/node/clawd/rag_queue")       # RAG投入待ちキュー
PAPERLESS_CONSUME = Path("/home/node/clawd/paperless_consume")

LOG_FILE   = Path("/home/node/clawd/inbox_watcher.log")
STATE_FILE = Path("/home/node/clawd/inbox_watcher_state.json")

TELEGRAM_BOT = os.environ.get("TELEGRAM_BOT_TOKEN", "8085717200:AAHzacN6Q3xSunrLyvUTuHnKEf7Cd5YFdt4")
TELEGRAM_CID = os.environ.get("TELEGRAM_CHAT_ID",  "8173025084")

POLL_INTERVAL   = 5    # 監視間隔（秒）
AGENT_TIMEOUT   = 130  # OpenClawエージェントタイムアウト（秒）
FILE_STABLE_SEC = 2    # ファイル書き込み完了待ち（秒）
CONTENT_PREVIEW = 600  # OpenClawに渡すファイル内容の最大文字数

DRY_RUN = "--dry-run" in __import__("sys").argv


# ── ユーティリティ ─────────────────────────────────────────────────────────────

def now() -> datetime:
    return datetime.now(JST)

def log(msg: str):
    """ファイルのみに書き込む（print+redirect による重複を防ぐ）"""
    ts   = now().strftime("%Y-%m-%d %H:%M:%S JST")
    line = f"[{ts}] {msg}"
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(line + "\n")
            f.flush()
    except Exception:
        pass

def send_telegram(text: str):
    if not TELEGRAM_BOT or not TELEGRAM_CID:
        log("WARN: Telegram credentials not set")
        return
    chat_id = ensure_allowed_telegram_chat_id(TELEGRAM_CID, "inbox_watcher.send_telegram")
    if DRY_RUN:
        log(f"[dry-run] Telegram: {text[:120]}")
        return
    url  = f"https://api.telegram.org/bot{TELEGRAM_BOT}/sendMessage"
    data = json.dumps({
        "chat_id":    chat_id,
        "text":       text,
        "parse_mode": "HTML",
    }).encode()
    try:
        req = urllib.request.Request(
            url, data=data,
            headers={"Content-Type": "application/json"}
        )
        urllib.request.urlopen(req, timeout=10)
    except Exception as e:
        log(f"Telegram error: {e}")

def load_state() -> dict:
    try:
        with open(STATE_FILE, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"processed": []}

def save_state(state: dict):
    try:
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=2)
    except Exception as e:
        log(f"WARN: Could not save state: {e}")


# ── ファイル内容読み取り ────────────────────────────────────────────────────────

def extract_content(filepath: Path) -> str:
    """ファイルの内容を最大CONTENT_PREVIEW文字で返す"""
    ext = filepath.suffix.lower()

    # PDF — PyMuPDF
    if ext == ".pdf":
        try:
            import fitz
            doc  = fitz.open(str(filepath))
            text = ""
            for page in doc[:5]:
                text += page.get_text()
                if len(text) >= CONTENT_PREVIEW:
                    break
            doc.close()
            return text[:CONTENT_PREVIEW].strip() or "(テキスト抽出不可)"
        except Exception as e:
            return f"(PDF読み取りエラー: {e})"

    # Excel — openpyxl
    if ext in (".xlsx", ".xls"):
        try:
            import openpyxl
            wb = openpyxl.load_workbook(str(filepath), read_only=True, data_only=True)
            lines = []
            for ws in wb.worksheets[:2]:
                lines.append(f"[シート: {ws.title}]")
                for row in ws.iter_rows(max_row=8, values_only=True):
                    vals = [str(v) for v in row if v is not None]
                    if vals:
                        lines.append("  " + " | ".join(vals))
                if len("\n".join(lines)) >= CONTENT_PREVIEW:
                    break
            wb.close()
            return "\n".join(lines)[:CONTENT_PREVIEW] or "(データなし)"
        except Exception as e:
            return f"(Excel読み取りエラー: {e})"

    # テキスト系 — 直接読み込み
    if ext in (".txt", ".md", ".csv", ".json", ".xml", ".log", ".yaml", ".yml"):
        try:
            with open(filepath, encoding="utf-8", errors="replace") as f:
                return f.read(CONTENT_PREVIEW)
        except Exception as e:
            return f"(テキスト読み取りエラー: {e})"

    return "(バイナリファイル — 内容プレビュー不可)"


# ── OpenClawエージェント呼び出し ────────────────────────────────────────────────

def call_openclaw_agent(message: str) -> str:
    """OpenClawエージェントにメッセージを送り、レスポンスを返す"""
    if DRY_RUN:
        return "判断: テスト文書です。\nACTION: manual"
    try:
        result = subprocess.run(
            ["openclaw", "agent",
             "--message", message,
             "--json",
             "--timeout", "120"],
            capture_output=True, text=True,
            timeout=AGENT_TIMEOUT,
            env={**os.environ,
                 "PATH": "/usr/local/bin:/home/node/.npm-global/bin:" + os.environ.get("PATH", "")}
        )
        if result.returncode == 0:
            try:
                data = json.loads(result.stdout)
                return (data.get("response")
                        or data.get("message")
                        or str(data))
            except json.JSONDecodeError:
                return result.stdout.strip()
        else:
            return f"[Agent error] {result.stderr.strip()[:300]}"
    except subprocess.TimeoutExpired:
        return "[Agent timeout] 120秒を超えました\nACTION: manual"
    except Exception as e:
        return f"[Exception] {e}\nACTION: manual"


# ── ルーティング判定 ───────────────────────────────────────────────────────────

ACTION_KEYWORDS = {
    "paperless": ["paperless", "文書", "スキャン", "アーカイブ", "archive"],
    "rag":       ["rag", "ナレッジ", "knowledge", "技術資料", "マニュアル", "manual"],
    "iatf":      ["iatf", "品質", "工程", "process", "quality", "qms"],
    "manual":    ["manual", "手動", "確認", "unknown", "不明"],
}

def parse_action(agent_response: str, filepath: Path) -> str:
    """
    エージェント応答から ACTION: タグを抽出、なければキーワードで推定。
    Returns: 'paperless' | 'rag' | 'iatf' | 'manual'
    """
    # 明示的なACTIONタグを探す
    for line in agent_response.splitlines():
        if line.strip().upper().startswith("ACTION:"):
            action = line.split(":", 1)[1].strip().lower()
            for key in ACTION_KEYWORDS:
                if key in action:
                    return key
            return "manual"

    # ファイル種別による簡易フォールバック
    ext = filepath.suffix.lower()
    if ext == ".pdf":
        return "paperless"
    if ext in (".xlsx", ".xls", ".csv"):
        resp_lower = agent_response.lower()
        if any(k in resp_lower for k in ["iatf", "品質", "工程", "fmea", "apqp"]):
            return "iatf"
        if any(k in resp_lower for k in ["rag", "ナレッジ", "技術"]):
            return "rag"
    return "manual"


# ── ルーティング実行 ───────────────────────────────────────────────────────────

ACTION_EMOJI = {
    "paperless": "📄",
    "rag":       "🧠",
    "iatf":      "📋",
    "manual":    "👤",
}
ACTION_LABEL = {
    "paperless": "Paperless自動投入",
    "rag":       "RAGキュー追加",
    "iatf":      "IATF確認依頼（要手動）",
    "manual":    "手動確認",
}

def execute_action(action: str, filepath: Path) -> str:
    """アクションを実行し、結果メッセージを返す"""
    if DRY_RUN:
        return f"[dry-run] ACTION={action} — 実行スキップ"

    if action == "paperless":
        try:
            dest = PAPERLESS_CONSUME / filepath.name
            if dest.exists():
                ts   = int(time.time())
                dest = PAPERLESS_CONSUME / f"{filepath.stem}_{ts}{filepath.suffix}"
            shutil.copy2(str(filepath), str(dest))
            log(f"Copied to Paperless consume: {dest.name}")
            return f"Paperless consume フォルダへコピー済み: {dest.name}"
        except Exception as e:
            log(f"Paperless copy error: {e}")
            return f"Paperlessコピー失敗: {e}"

    if action == "rag":
        try:
            RAG_QUEUE_DIR.mkdir(parents=True, exist_ok=True)
            dest = RAG_QUEUE_DIR / filepath.name
            if dest.exists():
                ts   = int(time.time())
                dest = RAG_QUEUE_DIR / f"{filepath.stem}_{ts}{filepath.suffix}"
            shutil.copy2(str(filepath), str(dest))
            log(f"Added to RAG queue: {dest.name}")
            return f"RAGキューへ追加: {dest.name}"
        except Exception as e:
            log(f"RAG queue error: {e}")
            return f"RAGキュー追加失敗: {e}"

    # iatf / manual — 通知のみ
    return "Telegram通知のみ（手動対応が必要）"


def move_to_processed(filepath: Path) -> Path:
    """処理済みフォルダへ移動（重複回避）"""
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    dest = PROCESSED_DIR / filepath.name
    if dest.exists():
        dest = PROCESSED_DIR / f"{filepath.stem}_{int(time.time())}{filepath.suffix}"
    if not DRY_RUN:
        filepath.rename(dest)
    return dest


# ── メイン処理 ────────────────────────────────────────────────────────────────

def process_file(filepath: Path, state: dict):
    fname   = filepath.name
    size_kb = filepath.stat().st_size / 1024
    log(f"New file detected: {fname} ({size_kb:.1f} KB)")

    # ファイル書き込み完了チェック
    size_before = filepath.stat().st_size
    time.sleep(FILE_STABLE_SEC)
    if not filepath.exists():
        log(f"File disappeared: {fname}")
        return
    if filepath.stat().st_size != size_before:
        log(f"File still writing, skip this cycle: {fname}")
        return

    try:
        # ── 1. ファイル内容を抽出 ──────────────────────────────────────────
        content = extract_content(filepath)
        content_summary = (content[:400] + "...") if len(content) > 400 else content

        # ── 2. OpenClawに判断依頼 ─────────────────────────────────────────
        prompt = f"""Clawstack inbox に新しいファイルが投入されました。

【ファイル情報】
ファイル名: {fname}
サイズ: {size_kb:.1f} KB
拡張子: {filepath.suffix.lower()}

【ファイル内容（抜粋）】
{content_summary}

【判断依頼】
このファイルの内容と用途を分析し、以下の形式で回答してください：

1. 内容の要約（1〜2文）
2. 推奨アクション（1文）
3. 最後の行に必ず: ACTION: paperless|rag|iatf|manual のいずれか

ルール:
- PDF文書・スキャン → ACTION: paperless
- 技術資料・マニュアル・研究文書 → ACTION: rag
- 品質/工程/IATF/FMEA/APQP関連 → ACTION: iatf
- その他・不明・要確認 → ACTION: manual

日本語で簡潔に回答してください。"""

        log(f"Calling OpenClaw agent for: {fname}")
        judgment = call_openclaw_agent(prompt)
        log(f"Agent judgment: {judgment[:200]}")

        # ── 3. アクション解析・実行 ────────────────────────────────────────
        action       = parse_action(judgment, filepath)
        action_result = execute_action(action, filepath)

        # ── 4. Telegram通知 ────────────────────────────────────────────────
        emoji = ACTION_EMOJI.get(action, "📁")
        label = ACTION_LABEL.get(action, action)

        msg = (
            f"<b>{emoji} [Inbox] 新着ファイル処理完了</b>\n"
            f"📄 <code>{fname}</code>  ({size_kb:.1f} KB)\n\n"
            f"<b>🤖 OpenClaw判断:</b>\n{judgment.strip()}\n\n"
            f"<b>⚡ 実行アクション:</b> {label}\n"
            f"<i>{action_result}</i>"
        )
        send_telegram(msg)

        # ── 5. 元ファイルをprocessedへ移動 ────────────────────────────────
        dest = move_to_processed(filepath)
        log(f"Moved to processed: {dest.name}  action={action}")

        # ── 6. 状態保存 ────────────────────────────────────────────────────
        state.setdefault("processed", []).append({
            "file":      fname,
            "timestamp": now().isoformat(),
            "action":    action,
            "judgment":  judgment[:300],
        })
        state["processed"] = state["processed"][-100:]
        save_state(state)

    except Exception as e:
        log(f"Error processing {fname}: {e}")
        send_telegram(f"<b>⚠️ [Inbox Watcher] 処理エラー</b>\nファイル: {fname}\nエラー: {e}")


def main():
    INBOX_DIR.mkdir(parents=True, exist_ok=True)
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    RAG_QUEUE_DIR.mkdir(parents=True, exist_ok=True)

    log("=" * 60)
    log("Inbox Watcher Phase 1.5 started" + (" [DRY-RUN]" if DRY_RUN else ""))
    log(f"Watching : {INBOX_DIR}")
    log(f"Paperless: {PAPERLESS_CONSUME}")
    log(f"RAG queue: {RAG_QUEUE_DIR}")
    log(f"Poll     : {POLL_INTERVAL}s")
    log("=" * 60)

    send_telegram(
        "<b>📥 [Inbox Watcher] Phase 1.5 起動</b>\n"
        "ファイル内容読み取り + 自動ルーティング有効\n"
        "• PDF → Paperless自動投入\n"
        "• 技術資料 → RAGキュー追加\n"
        "• IATF/品質 → Telegram通知（要手動）"
        + (" (dry-run mode)" if DRY_RUN else "")
    )

    state = load_state()
    seen  = {
        f.name
        for f in INBOX_DIR.iterdir()
        if f.is_file() and not f.name.startswith(".")
    }
    if seen:
        log(f"Startup: ignoring {len(seen)} pre-existing file(s)")

    while True:
        try:
            current = {
                f.name
                for f in INBOX_DIR.iterdir()
                if f.is_file() and not f.name.startswith(".")
            }
            for fname in sorted(current - seen):
                filepath = INBOX_DIR / fname
                if filepath.exists():
                    process_file(filepath, state)

            seen = {
                f.name
                for f in INBOX_DIR.iterdir()
                if f.is_file() and not f.name.startswith(".")
            }
        except Exception as e:
            log(f"Watcher loop error: {e}")

        time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    initialize_guard_status("inbox_watcher.startup")
    main()
