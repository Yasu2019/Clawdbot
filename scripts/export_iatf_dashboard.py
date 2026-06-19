# -*- coding: utf-8 -*-
import sys
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import json
import re
import sqlite3
from datetime import datetime, timezone, timedelta
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "data" / "workspace" / "universal_growth.db"
DASHBOARD_DIR = ROOT / "data" / "workspace" / "apps" / "growth_dashboard"
OUT_PATH = DASHBOARD_DIR / "iatf_youtube_summary.json"
PROCESSED_PATH = DASHBOARD_DIR / "processed_youtube_videos.json"
INDEX_PATH = ROOT / "data" / "workspace" / "iatf_auditing_youtube_index.json"
JST = timezone(timedelta(hours=9))


CLAUSE_RE = re.compile(r"(?:IATF\s*)?(?:Clause\s*)?(\d+(?:\.\d+){1,3})(?:\.\w)?", re.IGNORECASE)


def now_jst():
    return datetime.now(JST).replace(microsecond=0).isoformat()


def load_json(path, default):
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception:
        return default


def clean_title(challenge):
    title = (challenge or "").strip()
    for prefix in ("IATF Auditing Study: ", "OpenRadioss Community Study: "):
        if title.startswith(prefix):
            title = title[len(prefix):]
    return title


def extract_video_id(evidence):
    try:
        data = json.loads(evidence or "{}")
    except Exception:
        return "", ""
    url = str(data.get("video_url") or "")
    if "v=" in url:
        return url.split("v=", 1)[1].split("&", 1)[0], url
    return "", url


def split_summary(text):
    text = " ".join((text or "").split())
    if not text:
        return "要約なし", "再解析待ち"
    failed = "要約の生成に失敗" in text or "生成に失敗" in text
    if failed:
        return "要約生成失敗", "字幕またはローカルLLM応答を再確認する"
    sentences = re.split(r"(?<=[。.!?])\s*", text)
    if len(sentences) >= 2:
        mid = max(1, len(sentences) // 2)
        return "".join(sentences[:mid])[:450], "".join(sentences[mid:])[:450]
    midpoint = max(80, len(text) // 2)
    return text[:midpoint], text[midpoint:midpoint + 450]


def parse_structured_summary(text):
    text = (text or "").strip()
    sections = {
        "clause_explain": "",
        "audit_trail": "",
        "problem": "",
        "improvement": ""
    }
    
    tags = [
        ("clause_explain", "【該当箇条と要求事項の背景意図】"),
        ("audit_trail", "【内部監査の進め方と着眼点】"),
        ("problem", "【不適合事例の詳細解説】"),
        ("improvement", "【是正処置・予防処置の実務】")
    ]
    
    has_any = any(tag in text for _, tag in tags)
    if not has_any:
        # Fallback to legacy split
        p, imp = split_summary(text)
        sections["problem"] = p
        sections["improvement"] = imp
        return sections
        
    positions = []
    for key, tag in tags:
        pos = text.find(tag)
        if pos != -1:
            positions.append((pos, key, tag))
            
    positions.sort()
    
    for i, (pos, key, tag) in enumerate(positions):
        start = pos + len(tag)
        end = positions[i+1][0] if i + 1 < len(positions) else len(text)
        val = text[start:end].strip()
        # Clean potential leading/trailing colons or empty lines
        if val.startswith(":") or val.startswith("："):
            val = val[1:].strip()
        sections[key] = val
        
    return sections


def clause_label(text):
    clauses = sorted(set(CLAUSE_RE.findall(text or "")))
    if clauses:
        return "IATF " + ", ".join(clauses[:4])
    return "IATF Core"


def fetch_rows():
    if not DB_PATH.exists():
        return []
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        """
        SELECT id, timestamp, domain, challenge, know_how, evidence
        FROM growth_records
        WHERE source='iatf_youtube_monitor'
          AND domain='IATF_AUDITING_YT'
        ORDER BY timestamp DESC, id DESC
        """
    ).fetchall()
    conn.close()
    return rows


def export_dashboard_json():
    rows = fetch_rows()
    index = load_json(INDEX_PATH, {})
    index_videos = index.get("video_ids", []) if isinstance(index.get("video_ids"), list) else []
    index_ids = {str(v.get("id")) for v in index_videos if isinstance(v, dict) and v.get("id")}
    processed = set(load_json(PROCESSED_PATH, []))

    items = []
    db_video_ids = set()
    failed_count = 0
    for row in rows:
        video_id, video_url = extract_video_id(row["evidence"])
        if video_id:
            db_video_ids.add(video_id)
        
        parsed = parse_structured_summary(row["know_how"])
        problem = parsed["problem"]
        improvement = parsed["improvement"]
        if problem == "要約生成失敗":
            failed_count += 1
        title = clean_title(row["challenge"])
        items.append(
            {
                "record_id": row["id"],
                "timestamp": row["timestamp"],
                "video_id": video_id,
                "video_url": video_url,
                "program_name": title,
                "clause": clause_label(row["know_how"]),
                "problem": problem,
                "improvement": improvement,
                "clause_explain": parsed["clause_explain"],
                "audit_trail": parsed["audit_trail"],
                "status": "summary_failed" if problem == "要約生成失敗" else "analyzed",
            }
        )

    unanalyzed_index = sorted(index_ids - db_video_ids)
    processed_without_summary = sorted(processed - db_video_ids)
    index_title_map = {
        str(v.get("id")): str(v.get("title", ""))
        for v in index_videos
        if isinstance(v, dict) and v.get("id")
    }
    missing_examples = [
        {
            "video_id": video_id,
            "title": index_title_map.get(video_id, ""),
            "video_url": f"https://www.youtube.com/watch?v={video_id}",
            "reason": "No DB summary. Transcript may be disabled, unavailable in en/ja, or previous analysis was skipped.",
        }
        for video_id in unanalyzed_index[:10]
    ]
    payload = {
        "schema": "clawstack.iatf_youtube_summary.v2",
        "generated_at": now_jst(),
        "channel_url": index.get("channel_url", "https://www.youtube.com/@IATFAuditing/videos"),
        "index_fetched_at": index.get("fetched_at"),
        "estimated_total_videos": index.get("estimated_total_videos") or len(index_ids),
        "indexed_video_count": len(index_ids),
        "processed_video_count": len(processed),
        "analyzed_record_count": len(rows),
        "unique_analyzed_video_count": len(db_video_ids),
        "summary_failed_count": failed_count,
        "index_without_summary_count": len(unanalyzed_index),
        "processed_without_summary_count": len(processed_without_summary),
        "missing_summary_examples": missing_examples,
        "latest_db_timestamp": rows[0]["timestamp"] if rows else None,
        "display_limit": 80,
        "items": items[:80],
        "action_needed": [
            "Run scripts/update_iatf_auditing_youtube_index.py to refresh channel index.",
            "Run scripts/iatf_youtube_monitor.py to process new videos or retry failed summaries.",
            "Review summary_failed_count and processed_without_summary_count before marking progress complete.",
        ],
    }
    OUT_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        "[OK] exported "
        f"items={len(payload['items'])} analyzed={payload['analyzed_record_count']} "
        f"indexed={payload['indexed_video_count']} failed={payload['summary_failed_count']} "
        f"out={OUT_PATH}"
    )


if __name__ == "__main__":
    export_dashboard_json()
