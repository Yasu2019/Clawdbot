#!/usr/bin/env python3
"""
ingest_eml_to_qdrant.py
.eml ファイルをバッチ処理で Qdrant universal_knowledge に埋め込む。

ソース: /home/node/clawd/paperless_consume/email/**/*.eml
  フォルダ構造: email/{category}/{person}/{filename}.eml

パイプライン:
  .eml 解析 → チャンク収集 → Infinity バッチ embed (32件/回) → Qdrant バッチ upsert

実行:
  docker exec clawstack-unified-clawdbot-gateway-1 \
    python3 /home/node/clawd/ingest_eml_to_qdrant.py
"""

import os
import sys
import json
import hashlib
import requests
import traceback
from pathlib import Path
from datetime import datetime
from email import message_from_bytes, message_from_string
from email.header import decode_header

# ── Configuration ────────────────────────────────────────────────────────────────
EMAIL_ROOT   = "/home/node/clawd/paperless_consume/email"
STATE_FILE   = "/home/node/clawd/ingest_eml_state.json"
LOG_FILE     = "/home/node/clawd/ingest_eml.log"

INFINITY_URL = "http://infinity:7997/embeddings"
QDRANT_URL   = "http://qdrant:6333"
COLLECTION   = "universal_knowledge"
EMBED_MODEL  = "mixedbread-ai/mxbai-embed-large-v1"
EMBED_DIM    = 1024

CHUNK_SIZE   = 600   # chars
EMBED_BATCH  = 8     # Infinity への1回あたりのチャンク数（長文メール対応で小さめ）
QDRANT_BATCH = 32    # Qdrant upsert の1回あたりのポイント数
LOG_INTERVAL = 100   # 何件ごとに進捗ログを出すか

# ── Logging ──────────────────────────────────────────────────────────────────────
def log(msg, level="INFO"):
    ts   = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] [{level}] {msg}"
    if sys.stdout.isatty():
        print(line, flush=True)
    else:
        try:
            with open(LOG_FILE, "a", encoding="utf-8") as f:
                f.write(line + "\n")
        except Exception:
            pass

# ── State ─────────────────────────────────────────────────────────────────────────
def load_state():
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"processed": {}}

def save_state(state):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)

# ── Email parsing ────────────────────────────────────────────────────────────────
def decode_mime_words(s):
    if not s:
        return ""
    parts = decode_header(s)
    decoded = []
    for raw, enc in parts:
        if isinstance(raw, bytes):
            for charset in [enc or "utf-8", "iso-2022-jp", "utf-8", "cp932", "latin-1"]:
                try:
                    decoded.append(raw.decode(charset))
                    break
                except Exception:
                    continue
            else:
                decoded.append(raw.decode("utf-8", errors="replace"))
        else:
            decoded.append(str(raw))
    return "".join(decoded)

def extract_body(msg):
    body = ""
    if msg.is_multipart():
        for part in msg.walk():
            ct   = part.get_content_type()
            disp = str(part.get("Content-Disposition", ""))
            if ct == "text/plain" and "attachment" not in disp:
                payload = part.get_payload(decode=True)
                if payload:
                    charset = part.get_content_charset() or "utf-8"
                    for enc in [charset, "iso-2022-jp", "utf-8", "cp932", "latin-1"]:
                        try:
                            body += payload.decode(enc)
                            break
                        except Exception:
                            continue
    else:
        payload = msg.get_payload(decode=True)
        if payload:
            charset = msg.get_content_charset() or "utf-8"
            for enc in [charset, "iso-2022-jp", "utf-8", "cp932", "latin-1"]:
                try:
                    body = payload.decode(enc)
                    break
                except Exception:
                    continue
    return body.strip()

def parse_eml(filepath):
    try:
        rel   = Path(filepath).relative_to(EMAIL_ROOT)
        parts = rel.parts
        category = parts[0] if len(parts) > 1 else "その他"
        person   = parts[1] if len(parts) > 2 else ""

        raw = Path(filepath).read_bytes()
        msg = None
        for enc in ["utf-8", "iso-2022-jp", "cp932", "latin-1"]:
            try:
                msg = message_from_string(raw.decode(enc))
                break
            except Exception:
                continue
        if msg is None:
            msg = message_from_bytes(raw)

        subject = decode_mime_words(msg.get("subject", ""))
        from_   = decode_mime_words(msg.get("from", ""))
        to_     = decode_mime_words(msg.get("to", ""))
        date_   = msg.get("date", "")
        body    = extract_body(msg)

        return {
            "filepath": filepath,
            "category": category,
            "person":   person,
            "subject":  subject,
            "from":     from_,
            "to":       to_,
            "date":     date_,
            "body":     body,
        }
    except Exception as e:
        log(f"  Parse error {Path(filepath).name}: {e}", "WARN")
        return None

def make_chunks(meta):
    """件名+本文を CHUNK_SIZE ごとに分割して (chunk_text, payload_base) のリストを返す。"""
    subject   = meta["subject"]
    full_text = f"件名: {subject}\n差出人: {meta['from']}\n日付: {meta['date']}\n\n{meta['body']}".strip()
    if len(full_text) < 20:
        return []

    rel_path = str(Path(meta["filepath"]).relative_to(EMAIL_ROOT))
    base_payload = {
        "source":   f"email/{rel_path}",
        "category": meta["category"],
        "person":   meta["person"],
        "subject":  subject,
        "from":     meta["from"],
        "to":       meta["to"],
        "date":     meta["date"],
    }
    result = []
    for ci, start in enumerate(range(0, len(full_text), CHUNK_SIZE)):
        chunk = full_text[start:start + CHUNK_SIZE]
        if not chunk.strip():
            continue
        pid = int(hashlib.md5(f"email::{meta['filepath']}::c{ci}".encode()).hexdigest()[:15], 16)
        result.append((chunk, {**base_payload, "chunk": ci, "content": chunk}, pid))
    return result

# ── Infinity batch embed ─────────────────────────────────────────────────────────
def batch_embed(texts):
    """テキストリストを Infinity にまとめて送り、ベクトルリストを返す。失敗時は1件ずつリトライ。"""
    try:
        resp = requests.post(
            INFINITY_URL,
            json={"model": EMBED_MODEL, "input": texts},
            timeout=120,
        )
        resp.raise_for_status()
        data = resp.json()["data"]
        return [d["embedding"] for d in data]
    except Exception as e:
        log(f"  Embed batch error (batch_size={len(texts)}): {e} — 1件ずつリトライ", "WARN")
        # 1件ずつフォールバック
        results = []
        for t in texts:
            try:
                r = requests.post(
                    INFINITY_URL,
                    json={"model": EMBED_MODEL, "input": t},
                    timeout=120,
                )
                r.raise_for_status()
                results.append(r.json()["data"][0]["embedding"])
            except Exception as e2:
                log(f"  Embed single error: {e2}", "WARN")
                results.append(None)
        return results

# ── Qdrant batch upsert ──────────────────────────────────────────────────────────
def batch_upsert(points):
    """points = [{"id": int, "vector": list, "payload": dict}]"""
    try:
        resp = requests.put(
            f"{QDRANT_URL}/collections/{COLLECTION}/points",
            json={"points": points},
            timeout=30,
        )
        resp.raise_for_status()
        return len(points)
    except Exception as e:
        log(f"  Qdrant batch error: {e}", "WARN")
        return 0

# ── Main ─────────────────────────────────────────────────────────────────────────
def main():
    log("=" * 60)
    log("  ingest_eml_to_qdrant.py 開始 (バッチモード)")
    log(f"  ソース: {EMAIL_ROOT}")
    log(f"  Embed batch={EMBED_BATCH}  Qdrant batch={QDRANT_BATCH}")
    log("=" * 60)

    state     = load_state()
    processed = state.get("processed", {})

    all_emls = sorted(Path(EMAIL_ROOT).rglob("*.eml"))
    total    = len(all_emls)
    pending  = [p for p in all_emls if str(p) not in processed]

    log(f"  総ファイル数: {total}  未処理: {len(pending)}")
    if not pending:
        log("  ✅ 新規ファイルなし。処理終了。")
        return

    # ── バッチ処理ループ ──
    # emails → chunks → embed (batch) → upsert (batch)
    ok = skip = err = 0
    chunk_buf   = []   # (text, payload, point_id, filepath)
    file_chunks = {}   # filepath → chunk数（最終集計用）

    def flush_buffer():
        """バッファをEmbed → Qdrant upsertする。"""
        nonlocal ok
        if not chunk_buf:
            return
        texts  = [c[0] for c in chunk_buf]
        vecs   = batch_embed(texts)

        points = []
        for (text, payload, pid, fp), vec in zip(chunk_buf, vecs):
            if vec and len(vec) == EMBED_DIM:
                points.append({"id": pid, "vector": vec, "payload": {
                    **payload, "ingested_at": datetime.now().isoformat()
                }})
                file_chunks[fp] = file_chunks.get(fp, 0) + 1

        if points:
            # Qdrant はバッチサイズ QDRANT_BATCH で分割
            for i in range(0, len(points), QDRANT_BATCH):
                batch_upsert(points[i:i + QDRANT_BATCH])
            ok += len(set(c[3] for c in chunk_buf))

        chunk_buf.clear()

    ingested_files = 0
    for i, path in enumerate(pending):
        try:
            meta = parse_eml(str(path))
            if not meta:
                processed[str(path)] = {"chunks": 0, "error": "parse_failed", "ts": datetime.now().isoformat()}
                skip += 1
                continue

            chunks = make_chunks(meta)
            if not chunks:
                processed[str(path)] = {"chunks": 0, "ts": datetime.now().isoformat()}
                skip += 1
                continue

            for (chunk_text, payload, pid) in chunks:
                chunk_buf.append((chunk_text, payload, pid, str(path)))

            # EMBED_BATCH 件ごとにフラッシュ
            if len(chunk_buf) >= EMBED_BATCH:
                flush_buffer()

            ingested_files += 1

            # 処理済みに登録
            processed[str(path)] = {
                "subject": meta["subject"][:80],
                "ts":      datetime.now().isoformat(),
            }

        except Exception as e:
            log(f"  [{i+1}] ERROR {Path(str(path)).name}: {e}", "ERROR")
            log(traceback.format_exc(), "ERROR")
            processed[str(path)] = {"error": str(e), "ts": datetime.now().isoformat()}
            err += 1

        # 進捗ログ & 状態保存
        if (i + 1) % LOG_INTERVAL == 0:
            flush_buffer()  # 残バッファも出力
            state["processed"] = processed
            save_state(state)
            pct = (i + 1) / len(pending) * 100
            log(f"  [{i+1}/{len(pending)}] {pct:.1f}%  ok={ok}  skip={skip}  err={err}  Qdrant points↑")

    # 残バッファをフラッシュ
    flush_buffer()

    # 最終状態保存
    state["processed"] = processed
    save_state(state)
    log(f"  ✅ 完了: ok={ok}  skip={skip}  err={err}  合計={len(pending)}")
    log(f"  Qdrant collection: {COLLECTION}")

if __name__ == "__main__":
    main()
