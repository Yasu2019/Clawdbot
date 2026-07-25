#!/usr/bin/env python3
"""
Nightly Email Enrichment Batch (Plan B)
========================================
1. Scan email_search.db (raw) for emails not yet analyzed in email_analysis.db.
2. Use qwen3:8b (default) to generate summary, categorization, and unresolved points.
3. Update email_analysis.db and Qdrant.

Usage: python nightly_email_enrichment.py [--limit 100] [--days 7] [--model qwen3:14b]
"""

import os
import json
import sqlite3
import requests
import argparse
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path
import time
import sys

# --- Configuration ---
WORKSPACE = Path(__file__).parent
SEARCH_DB_PATH = WORKSPACE / "email_search.db"
ANALYSIS_DB_PATH = WORKSPACE / "email_analysis.db"

# Internal container names
GATEWAY_CONTAINER = "clawstack-unified-clawdbot-gateway-1"
OLLAMA_HOST = "ollama:11434"
QDRANT_HOST = "qdrant:6333"
INFINITY_URL = "http://localhost:7997/embeddings" # Mapped to host

DEFAULT_MODEL = "qwen2.5:14b" # High-accuracy 14B model for RTX 5060 Ti 16GB
EMBED_MODEL = "mixedbread-ai/mxbai-embed-large-v1"
COLLECTION = "email_analysis_enriched"

JST = timezone(timedelta(hours=9))

PROMPT_TEMPLATE = """
以下のメール内容を解析し、IATF16949に関連する品質・コンプライアンスの観点で要約・整理してください。

【メール内容】
件名: {subject}
差出人: {sender}
日付: {date}
本文:
{body}

【出力フォーマット (JSONのみ)】
{{
  "summary": "内容の簡潔な要約（150文字程度）",
  "request_item": "具体的な依頼事項や課題",
  "deadline": "期限があればその日付、なければ「なし」",
  "importance": "高・中・低の3段階",
  "kaizen": "改善案や特記事項",
  "is_resolved": 0 or 1 (完了・解決済みなら1、未完了なら0)
}}
"""

def log(msg):
    ts = datetime.now(JST).strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{ts}] {msg}", flush=True)

def run_docker_curl(container, method, url, data=None):
    cmd = ["docker", "exec", container, "curl", "-s", "-X", method, url]
    if data:
        cmd += ["-H", "Content-Type: application/json", "-d", json.dumps(data)]
    
    result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
    if result.returncode != 0:
        raise Exception(f"Docker curl failed (Code {result.returncode}): {result.stderr}")
    
    out = result.stdout.strip()
    if not out:
        return {}
    try:
        return json.loads(out)
    except:
        return {"raw": out}

def get_unprocessed_emails(limit=100, days=7):
    # Use URI for read-only to avoid lock issues with active ingestion
    search_uri = f"file:{SEARCH_DB_PATH}?mode=ro"
    con_s = sqlite3.connect(search_uri, uri=True)
    con_s.row_factory = sqlite3.Row
    
    con_a = sqlite3.connect(ANALYSIS_DB_PATH)
    processed = {row[0] for row in con_a.execute("SELECT filepath FROM analyses").fetchall()}
    con_a.close()
    
    cutoff = (datetime.now(JST) - timedelta(days=days)).isoformat()
    query = "SELECT * FROM emails WHERE indexed_at >= ? LIMIT ?"
    emails = con_s.execute(query, (cutoff, limit * 4)).fetchall()
    con_s.close()
    
    pending = [e for e in emails if e["filepath"] not in processed]
    log(f"  Checked {len(emails)} recent emails, found {len(pending)} pending.")
    return pending[:limit]

def analyze_with_llm(email, model):
    body_limit = 3000 # Reduce slightly to speed up CPU inference
    body = email["body_text"][:body_limit].replace('"', "'")
    
    prompt = PROMPT_TEMPLATE.format(
        subject=email["subject"].replace('"', "'"),
        sender=email["sender"].replace('"', "'"),
        date=email["email_date"],
        body=body
    )
    
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "stream": False,
        "format": "json"
    }
    
    try:
        url = f"http://{OLLAMA_HOST}/api/chat"
        res = run_docker_curl(GATEWAY_CONTAINER, "POST", url, payload)
        if "message" in res and "content" in res["message"]:
            return json.loads(res["message"]["content"])
        return None
    except Exception as e:
        log(f"  LLM Error: {e}")
        return None

def save_analysis(email, analysis):
    con = sqlite3.connect(ANALYSIS_DB_PATH)
    try:
        con.execute("""
            INSERT INTO analyses (
                filepath, email_date, sender, subject, 
                request_item, deadline, summary, 
                importance, kaizen, is_resolved, processed_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            email["filepath"], 
            email["email_date"], 
            email["sender"], 
            email["subject"],
            analysis.get("request_item", ""),
            analysis.get("deadline", ""),
            analysis.get("summary", ""),
            analysis.get("importance", "中"),
            analysis.get("kaizen", ""),
            analysis.get("is_resolved", 0),
            datetime.now(JST).strftime("%Y-%m-%d %H:%M:%S")
        ))
        con.commit()
    except Exception as e:
        log(f"  DB Save Error: {e}")
    finally:
        con.close()

def ensure_qdrant_collection():
    try:
        url = f"http://{QDRANT_HOST}/collections/{COLLECTION}"
        cmd = ["docker", "exec", GATEWAY_CONTAINER, "curl", "-s", "-o", "/dev/null", "-w", "%{http_code}", url]
        res = subprocess.run(cmd, capture_output=True, text=True).stdout.strip()
        
        if res == "200":
            return
        
        log(f"Creating Qdrant collection: {COLLECTION}")
        run_docker_curl(GATEWAY_CONTAINER, "PUT", url, {
            "vectors": {"size": 1024, "distance": "Cosine"}
        })
    except Exception as e:
        log(f"  Qdrant Setup Error: {e}")

def embed_text(text):
    try:
        resp = requests.post(INFINITY_URL, json={
            "model": EMBED_MODEL,
            "input": text
        }, timeout=30)
        resp.raise_for_status()
        return resp.json()["data"][0]["embedding"]
    except Exception as e:
        log(f"  Embed Error: {e}")
        return None

def upsert_to_qdrant(email, analysis):
    vec = embed_text(f"{analysis['summary']} {analysis['request_item']}")
    if not vec:
        return
    
    import hashlib
    point_id = int(hashlib.md5(email["filepath"].encode()).hexdigest()[:15], 16)
    
    payload = {
        "filepath": email["filepath"],
        "subject": email["subject"],
        "summary": analysis["summary"],
        "request_item": analysis["request_item"],
        "importance": analysis["importance"],
        "processed_at": datetime.now(JST).isoformat()
    }
    
    try:
        url = f"http://{QDRANT_HOST}/collections/{COLLECTION}/points"
        run_docker_curl(GATEWAY_CONTAINER, "PUT", url, {"points": [{"id": point_id, "vector": vec, "payload": payload}]})
    except Exception as e:
        log(f"  Qdrant Upsert Error: {e}")

def main():
    if sys.platform == "win32":
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=50)
    parser.add_argument("--days", type=int, default=3)
    parser.add_argument("--model", type=str, default=DEFAULT_MODEL)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    log(f"Starting enrichment batch (Lim: {args.limit}, Days: {args.days}, Model: {args.model})")
    
    try:
        emails = get_unprocessed_emails(args.limit, args.days)
    except Exception as e:
        log(f"CRITICAL: Failed to fetch emails: {e}")
        return

    if not emails:
        log("No pending emails found.")
        return

    if not args.dry_run:
        ensure_qdrant_collection()

    count = 0
    for email in emails:
        log(f"Processing ({count+1}/{len(emails)}): {email['subject'][:40]}...")
        if args.dry_run:
            count += 1
            continue
            
        analysis = analyze_with_llm(email, args.model)
        if analysis:
            save_analysis(email, analysis)
            upsert_to_qdrant(email, analysis)
            log("  Done.")
        else:
            log("  Failed (Check Ollama/Network).")
        count += 1
        
    log("Batch finished.")

if __name__ == "__main__":
    main()
