
import os
import glob
import json
import time
import requests
from datetime import datetime
from email import message_from_file
import status_reporter

try:
    import google.generativeai as genai
    HAS_GENAI = True
except ImportError:
    HAS_GENAI = False

# ============================================================
# Configuration (Container-friendly paths)
# ============================================================
BASE_WORKSPACE = "/workspace"
EMAIL_DIR = os.path.join(BASE_WORKSPACE, "temp_eml")
LOCAL_EMAIL_DIR = "/local_emails"
REPORT_FILE = os.path.join(BASE_WORKSPACE, "Email_Analysis_Report.md")
TRACKER_FILE = os.path.join(BASE_WORKSPACE, "processed_emails.json")
DB_FILE = os.path.join(BASE_WORKSPACE, "email_analysis.db")

# Ollama (local fallback)
OLLAMA_URL = "http://ollama:11434/api/generate"
OLLAMA_MODEL = "qwen2.5-coder:7b"

# Gemini 2.0 Flash (primary) — via official SDK
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
if not GEMINI_API_KEY:
    env_path = "/workspace/.env" # Assuming .env is also here or passed
    if not os.path.exists(env_path):
        env_path = "/workspace/clawdbot-gateway/.env" # Fallback check
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                if line.startswith("GEMINI_API_KEY="):
                    GEMINI_API_KEY = line.split("=", 1)[1].strip().strip('"')

GEMINI_MODEL = None
if HAS_GENAI and GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    GEMINI_MODEL = genai.GenerativeModel("gemini-2.5-flash")
    print("  ✅ Gemini 2.5 Flash SDK initialized")

# Rate limiting: Gemini free tier = 15 RPM → 1 call per 6 seconds
GEMINI_CALL_INTERVAL = 6.0  # seconds between API calls
_last_gemini_call = 0.0

# Budget control (JPY)
BUDGET_LIMIT_JPY = 300
USD_TO_JPY = 150
GEMINI_INPUT_COST_PER_M = 0.10   # $/1M input tokens
GEMINI_OUTPUT_COST_PER_M = 0.40  # $/1M output tokens
AVG_INPUT_TOKENS = 1200
AVG_OUTPUT_TOKENS = 300

# Target folders (all 6 process areas)
TARGET_FOLDERS = ["品証", "製造", "お客様", "技術部", "IATF", "供給者"]


# ============================================================
# Database Management
# ============================================================
def init_db():
    """Initialize SQLite database for tracking analysis results."""
    import sqlite3
    conn = sqlite3.connect(DB_FILE, timeout=30000)
    c = conn.cursor()
    c.execute("PRAGMA journal_mode=WAL;")
    c.execute("""
        CREATE TABLE IF NOT EXISTS analyses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filepath TEXT UNIQUE,
            email_date TEXT,
            sender TEXT,
            recipient TEXT,
            subject TEXT,
            request_item TEXT,
            deadline TEXT,
            response TEXT,
            importance TEXT,
            kaizen TEXT,
            summary TEXT,
            is_resolved INTEGER DEFAULT 0,
            processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

def save_to_db(email_data, analysis):
    """Save analysis results to SQLite database."""
    import sqlite3
    conn = sqlite3.connect(DB_FILE, timeout=30000)
    c = conn.cursor()
    c.execute("PRAGMA journal_mode=WAL;")
    
    # Check resolution status
    ans_text = str(analysis.get('回答', '-'))
    is_resolved = 1 if ("完了" in ans_text or "解決" in ans_text or "済" in ans_text) else 0
    
    try:
        c.execute("""
            INSERT OR REPLACE INTO analyses 
            (filepath, email_date, sender, recipient, subject, request_item, deadline, response, importance, kaizen, summary, is_resolved)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            email_data['path'],
            email_data['date'],
            email_data['from'],
            email_data['to'],
            email_data['subject'],
            analysis.get('依頼事項', '-'),
            analysis.get('納期', '-'),
            analysis.get('回答', '-'),
            analysis.get('重要度', '-'),
            analysis.get('改善状況', '-'),
            analysis.get('要約', '-'),
            is_resolved
        ))
        conn.commit()
    except Exception as e:
        print(f"  ❌ DB Error: {e}")
    conn.close()

def get_pending_tasks():
    """Get all unresolved tasks from the database."""
    import sqlite3
    if not os.path.exists(DB_FILE): return []
    try:
        conn = sqlite3.connect(DB_FILE, timeout=30000)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        c.execute("PRAGMA journal_mode=WAL;")
        c.execute("SELECT * FROM analyses WHERE is_resolved = 0 ORDER BY email_date DESC LIMIT 10")
        rows = c.fetchall()
        conn.close()
        return rows
    except:
        return []

# ============================================================
# Email Tracker
# ============================================================
def load_tracker():
    if os.path.exists(TRACKER_FILE):
        try:
            with open(TRACKER_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return {}
    return {}


def save_tracker(tracker):
    with open(TRACKER_FILE, "w", encoding="utf-8") as f:
        json.dump(tracker, f, indent=2, ensure_ascii=False)


# ============================================================
# Email Parser
# ============================================================
def parse_eml(filepath):
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            msg = message_from_file(f)

        subject = msg.get('subject', 'No Subject')
        from_ = msg.get('from', 'Unknown')
        to = msg.get('to', 'Unknown')
        date = msg.get('date', 'Unknown')

        body = ""
        attachments = []

        if msg.is_multipart():
            for part in msg.walk():
                content_type = part.get_content_type()
                content_disposition = str(part.get("Content-Disposition"))

                if content_type == "text/plain" and "attachment" not in content_disposition:
                    payload = part.get_payload(decode=True)
                    if payload:
                        body += payload.decode('utf-8', errors='ignore')
                elif "attachment" in content_disposition:
                    filename = part.get_filename()
                    if filename:
                        attachments.append(filename)
        else:
            payload = msg.get_payload(decode=True)
            if payload:
                body = payload.decode('utf-8', errors='ignore')

        return {
            "subject": subject,
            "from": from_,
            "to": to,
            "date": date,
            "body": body,
            "attachments": attachments
        }
    except Exception as e:
        print(f"  ❌ Parse error {filepath}: {e}")
        return None


# ============================================================
# LLM Analysis
# ============================================================
def build_prompt(email_data):
    return f"""あなたは製造・営業支援の専門アナリストです。以下のメールを解析し、依頼事項とステータスを日本語で抽出してください。

[Email情報]
差出人: {email_data['from']}
受取人: {email_data['to']}
日付: {email_data['date']}
件名: {email_data['subject']}
添付: {', '.join(email_data['attachments']) if email_data['attachments'] else 'なし'}

[本文]
{email_data['body'][:4000]}

以下の JSON 形式でのみ出力してください（余計な説明は不要です）：
1. 依頼事項 (何をすべきか具体的に)
2. 納期 (いつまでか。不明なら不明)
3. 回答 (どのような返答があったか。未回答なら「回答待ち」)
4. 重要度 (高、中、低)
5. 改善状況 (改善活動に関連するか)
6. 要約 (1行で)

{{
    "依頼事項": "string",
    "納期": "string",
    "回答": "string",
    "重要度": "string",
    "改善状況": "string",
    "要約": "string"
}}"""


def analyze_with_gemini(email_data, cost_data):
    """Analyze using Gemini 2.0 Flash via official SDK with rate limiting."""
    global _last_gemini_call

    if not GEMINI_MODEL:
        return None

    prompt = build_prompt(email_data)

    # Rate limiting: wait if called too recently
    elapsed = time.time() - _last_gemini_call
    if elapsed < GEMINI_CALL_INTERVAL:
        time.sleep(GEMINI_CALL_INTERVAL - elapsed)

    max_retries = 3
    for attempt in range(max_retries):
        try:
            _last_gemini_call = time.time()
            response = GEMINI_MODEL.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.1,
                    response_mime_type="application/json",
                ),
            )

            # Extract token usage from response metadata
            usage = getattr(response, 'usage_metadata', None)
            if usage:
                input_tokens = getattr(usage, 'prompt_token_count', AVG_INPUT_TOKENS)
                output_tokens = getattr(usage, 'candidates_token_count', AVG_OUTPUT_TOKENS)
            else:
                input_tokens = AVG_INPUT_TOKENS
                output_tokens = AVG_OUTPUT_TOKENS

            update_cost(cost_data, input_tokens, output_tokens)

            text = response.text
            return json.loads(text)

        except Exception as e:
            err_str = str(e)
            if "429" in err_str or "quota" in err_str.lower() or "rate" in err_str.lower():
                wait = (2 ** attempt) * 10  # 10s, 20s, 40s
                print(f"  ⏳ Rate limited (attempt {attempt+1}/{max_retries}), waiting {wait}s...")
                time.sleep(wait)
                continue
            else:
                print(f"  ⚡ Gemini Error: {e}")
                return None

    print(f"  ⚡ Gemini: max retries exhausted")
    return None


def analyze_with_ollama(email_data, cost_data):
    """Analyze using local Ollama (fallback)."""
    prompt = build_prompt(email_data)

    payload = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False,
        "format": "json"
    }

    try:
        resp = requests.post(OLLAMA_URL, 
                             json={'model': OLLAMA_MODEL, 'prompt': prompt, 'stream': False, 'format': 'json', 'options': {'num_ctx': 1024}}, 
                             timeout=600)
        resp.raise_for_status()
        return json.loads(resp.json().get("response", "{}"))
    except Exception as e:
        print(f"  🐢 Ollama Error: {e}")
        return None


def analyze_content(email_data, cost_data, use_gemini=False):
    """Router: Forced to Ollama per user request for cost/stable processing."""
    # Gemini is completely bypassed here
    return analyze_with_ollama(email_data, cost_data)


# ============================================================
# Main
def generate_report(total_processed):
    """Generate the Markdown report from current database state."""
    pending = get_pending_tasks()
    
    with open(REPORT_FILE, "w", encoding="utf-8") as f:
        f.write("# 📧 P016 Email分析レポート (統合版)\n\n")
        
        if pending:
            f.write("### ⚠️ 回答待ち・未完了の案件リスト\n")
            f.write("| 依頼日 | 差出人 | 依頼事項 | 納期 | 回答状況 | 重要度 |\n")
            f.write("| --- | --- | --- | --- | --- | --- |\n")
            for p in pending:
                # Handle dictionary or Row object
                sender = p['sender'] if hasattr(p, 'keys') and 'sender' in p.keys() else p[3]
                item = p['request_item'] if hasattr(p, 'keys') and 'request_item' in p.keys() else p[6]
                date = p['email_date'] if hasattr(p, 'keys') and 'email_date' in p.keys() else p[2]
                deadline = p['deadline'] if hasattr(p, 'keys') and 'deadline' in p.keys() else p[7]
                resp = p['response'] if hasattr(p, 'keys') and 'response' in p.keys() else p[8]
                imp = p['importance'] if hasattr(p, 'keys') and 'importance' in p.keys() else p[9]
                f.write(f"| {str(date)[:16]} | {str(sender)[:20]} | {str(item)} | {str(deadline)} | {str(resp)} | {str(imp)} |\n")
            f.write("\n---\n\n")
        
        f.write("### 📬 本日の要約\n")
        if total_processed > 0:
             f.write(f"本日、合計 {total_processed} 通のメールを処理・更新しました。\n")
        else:
             f.write("新規のメールはありませんでした。\n")
             
    print(f"  📝 Report updated ({total_processed} processed).")

# ============================================================
def main():
    print("=" * 60)
    print("  📧 Email Ingestion — Gemini 2.0 Flash + Ollama Hybrid")
    print(f"  Budget: ¥{BUDGET_LIMIT_JPY} (auto-switch to Ollama at limit)")
    print("=" * 60)

    init_db()
    tracker = load_tracker()
    
    cost_data = {"total_cost_jpy": 0, "gemini_calls": 0, "ollama_calls": 0}

    CUTOFF_DATE = datetime(2025, 1, 1).timestamp()

    all_emls = []
    
    # 1. Scan Container New Emails (Gmail via n8n)
    print(f"  📬 Scanning {EMAIL_DIR}...")
    if os.path.exists(EMAIL_DIR):
        files = glob.glob(os.path.join(EMAIL_DIR, "*.eml"))
        for f in files:
            if f not in tracker:
                all_emls.append({"path": f, "mtime": os.path.getmtime(f)})

    # 2. Scan Local Emails (Historical)
    if os.path.exists(LOCAL_EMAIL_DIR):
        print(f"  📬 Scanning {LOCAL_EMAIL_DIR} (recursive)...")
        # Scan ALL files recursively in LOCAL_EMAIL_DIR
        files = glob.glob(os.path.join(LOCAL_EMAIL_DIR, "**/*.eml"), recursive=True)
        for f in files:
            if f not in tracker:
                mtime = os.path.getmtime(f)
                if mtime >= CUTOFF_DATE:
                    all_emls.append({"path": f, "mtime": mtime})

    # Sort newest first
    all_emls.sort(key=lambda x: x['mtime'], reverse=True)

    total = len(all_emls)
    if total == 0:
        # Check if we should still send a report of existing pending tasks
        pending = get_pending_tasks()
        if pending:
             print("\n  ✅ No new emails, but pending tasks found.")
        else:
             print("\n  ✅ No new emails to process.")
             return

    print(f"\n  📬 Found {total} unprocessed emails.")

    # Initialize Report if needed
    if not os.path.exists(REPORT_FILE) or os.path.getsize(REPORT_FILE) < 100:
        with open(REPORT_FILE, "w", encoding="utf-8") as f:
            f.write("# Email Analysis Report - Quality, Delivery & Collaboration\n\n")
            f.write("| Date | From | Subject | Summary | Quality/Delivery | Requests | Deadlines | Response (Who/When/How) | KAIZEN Status |\n")
            f.write("| --- | --- | --- | --- | --- | --- | --- | --- | --- |\n")

    # Process emails...
    start_time = time.time()

    for i, item in enumerate(all_emls):
        filepath = item['path']
        basename = os.path.basename(filepath)
        print(f"  [{i+1}/{total}] 🐢Ollama | {basename[:50]}")

        email_data = parse_eml(filepath)
        if not email_data: continue
        email_data['path'] = filepath

        analysis = analyze_content(email_data, cost_data)
        if not analysis: continue

        # Save to SQLite
        save_to_db(email_data, analysis)

        # Update tracker
        tracker[filepath] = item['mtime']
        save_tracker(tracker)
        
        # Periodic report update
        if (i + 1) % 50 == 0:
            generate_report(i + 1)

    # FINAL REPORT GENERATION
    generate_report(total)

    print(f"\n  ✅ Processing complete. Report: {REPORT_FILE}")


if __name__ == "__main__":
    main()
