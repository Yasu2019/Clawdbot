
import os
import glob
import json
import time
import requests
from datetime import datetime
from email import message_from_file
import status_reporter

# ============================================================
# Configuration
# ============================================================
EMAIL_DIR = r"D:\Clawdbot_Docker_20260125\clawstack_v2\data\paperless\consume\email"
REPORT_FILE = r"D:\Clawdbot_Docker_20260125\data\workspace\Email_Analysis_Report.md"
TRACKER_FILE = r"D:\Clawdbot_Docker_20260125\data\workspace\processed_emails.json"
COST_FILE = r"D:\Clawdbot_Docker_20260125\data\workspace\gemini_cost_tracker.json"

# Ollama (local fallback)
OLLAMA_URL = "http://127.0.0.1:11434/api/generate"
OLLAMA_MODEL = "llava:latest"

# Gemini 2.0 Flash (primary)
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
if not GEMINI_API_KEY:
    # Load from .env file
    env_path = r"D:\Clawdbot_Docker_20260125\.env"
    if os.path.exists(env_path):
        with open(env_path, "r") as f:
            for line in f:
                if line.startswith("GEMINI_API_KEY="):
                    GEMINI_API_KEY = line.split("=", 1)[1].strip().strip('"')

GEMINI_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GEMINI_API_KEY}"

# Budget control (JPY)
BUDGET_LIMIT_JPY = 300
USD_TO_JPY = 150  # approximate
GEMINI_INPUT_COST_PER_M = 0.10   # $/1M input tokens
GEMINI_OUTPUT_COST_PER_M = 0.40  # $/1M output tokens
AVG_INPUT_TOKENS = 1200   # per email (prompt + body)
AVG_OUTPUT_TOKENS = 300   # per email (JSON response)

# Target folders (all 6 process areas)
TARGET_FOLDERS = ["品証", "製造", "お客様", "技術部", "IATF", "供給者"]


# ============================================================
# Cost Tracker
# ============================================================
def load_cost():
    if os.path.exists(COST_FILE):
        try:
            with open(COST_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            pass
    return {"total_input_tokens": 0, "total_output_tokens": 0,
            "total_cost_usd": 0.0, "total_cost_jpy": 0.0,
            "gemini_calls": 0, "ollama_calls": 0,
            "switched_to_ollama_at": None}


def save_cost(cost_data):
    with open(COST_FILE, "w", encoding="utf-8") as f:
        json.dump(cost_data, f, indent=2, ensure_ascii=False)


def update_cost(cost_data, input_tokens, output_tokens):
    cost_data["total_input_tokens"] += input_tokens
    cost_data["total_output_tokens"] += output_tokens
    cost_data["gemini_calls"] += 1
    cost_usd = (input_tokens / 1_000_000 * GEMINI_INPUT_COST_PER_M +
                output_tokens / 1_000_000 * GEMINI_OUTPUT_COST_PER_M)
    cost_data["total_cost_usd"] += cost_usd
    cost_data["total_cost_jpy"] = round(cost_data["total_cost_usd"] * USD_TO_JPY, 1)
    save_cost(cost_data)
    return cost_data


def is_budget_exceeded(cost_data):
    return cost_data["total_cost_jpy"] >= BUDGET_LIMIT_JPY


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
    return f"""You are an expert industrial analyst. Analyze the following email and extract insights.

[Email Metadata]
From: {email_data['from']}
To: {email_data['to']}
Date: {email_data['date']}
Subject: {email_data['subject']}
Attachments: {', '.join(email_data['attachments']) if email_data['attachments'] else 'None'}

[Body]
{email_data['body'][:4000]}

Extract in JSON format:
1. quality_and_delivery_issues: Defects, QIF/PIF, non-conformities, delivery problems (品質や納期の問題点).
2. requests: Action/info requests between departments or customers (依頼事項).
3. request_deadlines: Deadline for the requests (依頼に対する納期).
4. response_details: WHEN, WHO, HOW requests were answered (いつ、だれが、どのように回答したか).
5. improvement_status: KAIZEN, process optimization discussions (改善活動の状況).
6. summary: 1-sentence summary.

Output JSON ONLY:
{{
    "quality_and_delivery_issues": "string or None",
    "requests": "string or None",
    "request_deadlines": "string or None",
    "response_details": "string or None",
    "improvement_status": "string or None",
    "summary": "string"
}}"""


def analyze_with_gemini(email_data, cost_data):
    """Analyze using Gemini 2.0 Flash API."""
    prompt = build_prompt(email_data)

    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.1,
            "responseMimeType": "application/json"
        }
    }

    try:
        resp = requests.post(GEMINI_URL, json=payload, timeout=30)
        resp.raise_for_status()
        data = resp.json()

        # Extract token usage
        usage = data.get("usageMetadata", {})
        input_tokens = usage.get("promptTokenCount", AVG_INPUT_TOKENS)
        output_tokens = usage.get("candidatesTokenCount", AVG_OUTPUT_TOKENS)
        update_cost(cost_data, input_tokens, output_tokens)

        # Extract response text
        text = data["candidates"][0]["content"]["parts"][0]["text"]
        return json.loads(text)

    except Exception as e:
        print(f"  ⚡ Gemini Error: {e}")
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
        resp = requests.post(OLLAMA_URL, json=payload, timeout=300)
        resp.raise_for_status()
        cost_data["ollama_calls"] += 1
        save_cost(cost_data)
        return json.loads(resp.json().get("response", "{}"))
    except Exception as e:
        print(f"  🐢 Ollama Error: {e}")
        return None


def analyze_content(email_data, cost_data, use_gemini=True):
    """Smart router: Gemini first, Ollama fallback."""
    if use_gemini and GEMINI_API_KEY and not is_budget_exceeded(cost_data):
        result = analyze_with_gemini(email_data, cost_data)
        if result:
            return result
        # Gemini failed → try Ollama
        print("  ⚠️ Gemini failed, falling back to Ollama...")

    return analyze_with_ollama(email_data, cost_data)


# ============================================================
# Main
# ============================================================
def main():
    print("=" * 60)
    print("  📧 Email Ingestion — Gemini 2.0 Flash + Ollama Hybrid")
    print(f"  Budget: ¥{BUDGET_LIMIT_JPY} (auto-switch to Ollama at limit)")
    print("=" * 60)

    tracker = load_tracker()
    cost_data = load_cost()

    print(f"\n  💰 Current spend: ¥{cost_data['total_cost_jpy']:.1f} / ¥{BUDGET_LIMIT_JPY}")
    print(f"  📊 Gemini calls: {cost_data['gemini_calls']} | Ollama calls: {cost_data['ollama_calls']}")

    # Collect all unprocessed EMLs from ALL target folders
    all_emls = []
    for folder in TARGET_FOLDERS:
        path = os.path.join(EMAIL_DIR, folder)
        if os.path.exists(path):
            files = glob.glob(os.path.join(path, "**/*.eml"), recursive=True)
            for f in files:
                mtime = os.path.getmtime(f)
                if f in tracker and tracker[f] == mtime:
                    continue
                all_emls.append({"path": f, "mtime": mtime})

    # Sort newest first
    all_emls.sort(key=lambda x: x['mtime'], reverse=True)

    # NO LIMIT — process ALL unprocessed emails
    total = len(all_emls)
    if total == 0:
        print("\n  ✅ No new emails to process.")
        return

    print(f"\n  📬 Found {total} unprocessed emails across {len(TARGET_FOLDERS)} folders")

    # Initialize Report if needed
    if not os.path.exists(REPORT_FILE) or os.path.getsize(REPORT_FILE) < 100:
        with open(REPORT_FILE, "w", encoding="utf-8") as f:
            f.write("# Email Analysis Report - Quality, Delivery & Collaboration\n\n")
            f.write("| Date | From | Subject | Summary | Quality/Delivery | Requests | Deadlines | Response (Who/When/How) | KAIZEN Status |\n")
            f.write("| --- | --- | --- | --- | --- | --- | --- | --- | --- |\n")

    switched_to_ollama = False
    start_time = time.time()

    for i, item in enumerate(all_emls):
        filepath = item['path']
        basename = os.path.basename(filepath)

        # Check budget before each call
        use_gemini = not is_budget_exceeded(cost_data)
        if not use_gemini and not switched_to_ollama:
            switched_to_ollama = True
            cost_data["switched_to_ollama_at"] = datetime.now().isoformat()
            save_cost(cost_data)
            print(f"\n  🔄 ¥{BUDGET_LIMIT_JPY} budget reached! Switching to Ollama...")
            print(f"     Gemini processed: {cost_data['gemini_calls']} emails")
            print(f"     Total cost: ¥{cost_data['total_cost_jpy']:.1f}\n")

        engine = "⚡Gemini" if use_gemini else "🐢Ollama"
        status_reporter.update_status("Email Ingestion", i + 1, total,
                                      f"[{engine}] {basename}")
        print(f"  [{i+1}/{total}] {engine} | ¥{cost_data['total_cost_jpy']:.1f} | {basename[:50]}")

        email_data = parse_eml(filepath)
        if not email_data:
            continue

        analysis = analyze_content(email_data, cost_data, use_gemini=use_gemini)
        if not analysis:
            continue

        # Write to report
        def clean(text):
            if not text or text == "None" or text == "null":
                return "-"
            return str(text).replace("\n", " ").replace("|", "\\|")

        with open(REPORT_FILE, "a", encoding="utf-8") as f:
            f.write(f"| {clean(email_data['date'])} | {clean(email_data['from'])} | "
                    f"{clean(email_data['subject'])} | {clean(analysis.get('summary'))} | "
                    f"{clean(analysis.get('quality_and_delivery_issues'))} | "
                    f"{clean(analysis.get('requests'))} | "
                    f"{clean(analysis.get('request_deadlines'))} | "
                    f"{clean(analysis.get('response_details'))} | "
                    f"{clean(analysis.get('improvement_status'))} |\n")

        # Update tracker
        tracker[filepath] = item['mtime']
        save_tracker(tracker)

    elapsed = time.time() - start_time
    print(f"\n{'=' * 60}")
    print(f"  ✅ Ingestion complete!")
    print(f"  📊 Total processed: {total}")
    print(f"  ⚡ Gemini calls: {cost_data['gemini_calls']}")
    print(f"  🐢 Ollama calls: {cost_data['ollama_calls']}")
    print(f"  💰 Total cost: ¥{cost_data['total_cost_jpy']:.1f}")
    print(f"  ⏱  Elapsed: {elapsed/60:.1f} min")
    print(f"  📁 Report: {REPORT_FILE}")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
