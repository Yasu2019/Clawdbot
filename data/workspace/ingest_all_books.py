import os
import io
import base64
import json
import requests
import pypdf
import time
from PIL import Image
from datetime import datetime

# Configuration
CONSUME_DIR = r"D:\Clawdbot_Docker_20260125\clawstack_v2\data\paperless\consume"
OUTPUT_DIR = r"D:\Clawdbot_Docker_20260125\data\workspace\ingested_books"
DASHBOARD_PATH = r"D:\Clawdbot_Docker_20260125\data\workspace\ingest_dashboard.html"
MODEL = "minicpm-v:latest"
OLLAMA_API = "http://127.0.0.1:11434/api/generate"
TIMEOUT = 400
RETRIES = 2

# Global stats
stats = {
    "total_files": 0,
    "processed_files": 0,
    "current_file": "Waiting...",
    "current_page": 0,
    "current_total_pages": 0,
    "start_time": time.time(),
    "last_update": "",
    "history": []
}

def update_dashboard():
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    progress_pct = (stats["processed_files"] / stats["total_files"] * 100) if stats["total_files"] > 0 else 0
    
    html = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <meta http-equiv="refresh" content="15">
        <title>Ingestion Dashboard - Clawstack V3</title>
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600&display=swap" rel="stylesheet">
        <style>
            :root {{
                --bg: #0f172a;
                --card: rgba(30, 41, 59, 0.7);
                --accent: #38bdf8;
                --text: #f8fafc;
                --subtext: #94a3b8;
            }}
            body {{
                background-color: var(--bg);
                color: var(--text);
                font-family: 'Inter', sans-serif;
                margin: 0;
                padding: 40px;
                display: flex;
                flex-direction: column;
                align-items: center;
                min-height: 100vh;
            }}
            .container {{
                max-width: 900px;
                width: 100%;
                background: var(--card);
                backdrop-filter: blur(12px);
                border-radius: 24px;
                border: 1px solid rgba(255, 255, 255, 0.1);
                padding: 40px;
                box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.5);
            }}
            h1 {{
                font-size: 2.5rem;
                font-weight: 600;
                margin-top: 0;
                background: linear-gradient(to right, #38bdf8, #818cf8);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
            }}
            .stats-grid {{
                display: grid;
                grid-template-columns: repeat(2, 1fr);
                gap: 20px;
                margin: 30px 0;
            }}
            .stat-card {{
                background: rgba(255, 255, 255, 0.05);
                padding: 20px;
                border-radius: 16px;
                border: 1px solid rgba(255, 255, 255, 0.05);
            }}
            .stat-label {{
                font-size: 0.875rem;
                color: var(--subtext);
                margin-bottom: 8px;
            }}
            .stat-value {{
                font-size: 1.5rem;
                font-weight: 600;
                color: var(--accent);
            }}
            .progress-container {{
                margin: 40px 0;
            }}
            .progress-bar-bg {{
                height: 12px;
                background: rgba(255, 255, 255, 0.1);
                border-radius: 6px;
                overflow: hidden;
                position: relative;
            }}
            .progress-bar-fill {{
                height: 100%;
                width: {progress_pct}%;
                background: linear-gradient(to right, #38bdf8, #818cf8);
                border-radius: 6px;
                transition: width 1s ease-in-out;
                box-shadow: 0 0 20px rgba(56, 189, 248, 0.5);
            }}
            .current-task {{
                background: rgba(56, 189, 248, 0.1);
                border-left: 4px solid var(--accent);
                padding: 15px 20px;
                border-radius: 0 12px 12px 0;
                margin-bottom: 30px;
            }}
            .history {{
                margin-top: 30px;
            }}
            .history-item {{
                font-size: 0.875rem;
                padding: 10px 0;
                border-bottom: 1px solid rgba(255, 255, 255, 0.05);
                color: var(--subtext);
            }}
            .history-item span {{
                color: #4ade80;
                margin-right: 10px;
            }}
            .footer {{
                margin-top: 40px;
                text-align: center;
                font-size: 0.75rem;
                color: var(--subtext);
            }}
            .pulse {{
                display: inline-block;
                width: 8px;
                height: 8px;
                background: #4ade80;
                border-radius: 50%;
                margin-right: 10px;
                animation: pulse 2s infinite;
            }}
            @keyframes pulse {{
                0% {{ transform: scale(0.95); box-shadow: 0 0 0 0 rgba(74, 222, 128, 0.7); }}
                70% {{ transform: scale(1); box-shadow: 0 0 0 10px rgba(74, 222, 128, 0); }}
                100% {{ transform: scale(0.95); box-shadow: 0 0 0 0 rgba(74, 222, 128, 0); }}
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>Ingestion Dashboard</h1>
            <p style="color: var(--subtext); margin-top: -10px;">Automated Knowledge Discovery Pipeline</p>
            
            <div class="stats-grid">
                <div class="stat-card">
                    <div class="stat-label">Total Books</div>
                    <div class="stat-value">{stats["total_files"]}</div>
                </div>
                <div class="stat-card">
                    <div class="stat-label">Processed</div>
                    <div class="stat-value">{stats["processed_files"]} / {stats["total_files"]}</div>
                </div>
            </div>

            <div class="progress-container">
                <div style="display: flex; justify-content: space-between; margin-bottom: 8px;">
                    <span class="stat-label">Overall Progress</span>
                    <span class="stat-label">{progress_pct:.1f}%</span>
                </div>
                <div class="progress-bar-bg">
                    <div class="progress-bar-fill"></div>
                </div>
            </div>

            <div class="current-task">
                <div class="stat-label"><span class="pulse"></span>Now Processing</div>
                <div style="font-weight: 600; margin-bottom: 5px;">{stats["current_file"]}</div>
                <div class="stat-label">Page {stats["current_page"]} / {stats["current_total_pages"]}</div>
            </div>

            <div class="history">
                <div class="stat-label">Recently Ingested</div>
                {"".join(f'<div class="history-item"><span>✓</span> {item}</div>' for item in stats["history"][-5:][::-1])}
            </div>

            <div class="footer">
                Last update: {now} | Model: {MODEL}
            </div>
        </div>
    </body>
    </html>
    """
    with open(DASHBOARD_PATH, "w", encoding="utf-8") as f:
        f.write(html)

def encode_image(image):
    buffered = io.BytesIO()
    image.save(buffered, format="JPEG")
    return base64.b64encode(buffered.getvalue()).decode('utf-8')

def analyze_image(region_img, context_text=""):
    if region_img.width > 1200 or region_img.height > 1200:
        region_img.thumbnail((1200, 1200))
    base64_img = encode_image(region_img)
    prompt = f"Analyze this figure in detail. Extract math/charts. Context: {context_text[:300]}"
    for attempt in range(RETRIES):
        try:
            payload = {"model": MODEL, "prompt": prompt, "images": [base64_img], "stream": False, "options": {"temperature": 0}}
            response = requests.post(OLLAMA_API, json=payload, timeout=TIMEOUT)
            response.raise_for_status()
            return response.json().get("response", "").strip()
        except:
            time.sleep(5)
    return "[Failed]"

def get_or_create_ai_tag():
    """Retrieve or create the 'AI-Processed' tag in Paperless-ngx."""
    tag_name = "AI-Processed"
    try:
        # Check if exists
        response = requests.get(f"{PAPERLESS_API_URL}/tags/", auth=(PAPERLESS_USER, PAPERLESS_PASS), params={"name__iexact": tag_name})
        results = response.json().get("results", [])
        if results:
            return results[0]["id"]
        
        # Create if not exists (green color)
        data = {"name": tag_name, "color": "#4ade80", "matching_algorithm": 0}
        response = requests.post(f"{PAPERLESS_API_URL}/tags/", auth=(PAPERLESS_USER, PAPERLESS_PASS), json=data)
        return response.json().get("id")
    except Exception as e:
        print(f"Tag API Error: {e}")
    return None

def apply_tag_to_document(doc_id, tag_id):
    """Add the AI-Processed tag to a specific document."""
    if not doc_id or not tag_id: return
    try:
        # Get current tags
        response = requests.get(f"{PAPERLESS_API_URL}/documents/{doc_id}/", auth=(PAPERLESS_USER, PAPERLESS_PASS))
        current_tags = response.json().get("tags", [])
        if tag_id not in current_tags:
            current_tags.append(tag_id)
            requests.patch(f"{PAPERLESS_API_URL}/documents/{doc_id}/", auth=(PAPERLESS_USER, PAPERLESS_PASS), json={"tags": current_tags})
    except Exception as e:
        print(f"Apply Tag Error: {e}")

def process_pdf(pdf_path, output_md, doc_id=None):
    stats["current_file"] = os.path.basename(pdf_path)
    update_dashboard()
    try:
        reader = pypdf.PdfReader(pdf_path)
        stats["current_total_pages"] = len(reader.pages)
        with open(output_md, 'w', encoding='utf-8') as f:
            f.write(f"# Document: {os.path.basename(pdf_path)}\n\n")
            if doc_id: f.write(f"Paperless-ngx ID: {doc_id}\n\n")
            
            for i, page in enumerate(reader.pages):
                stats["current_page"] = i + 1
                update_dashboard()
                f.write(f"\n--- Page {i+1} ---\n\n")
                try:
                    text = page.extract_text() or ""
                    if text.strip(): f.write(f"### Text:\n{text}\n\n")
                except: text = ""
                try:
                    for img_idx, img_file_obj in enumerate(page.images):
                        if img_idx > 5: break
                        img_data = img_file_obj.data
                        image = Image.open(io.BytesIO(img_data))
                        if image.width < 150 or image.height < 150: continue
                        analysis = analyze_image(image, text)
                        f.write(f"#### Figure {img_idx+1} Analysis:\n> {analysis}\n\n")
                except: pass
                f.flush()
        
        # Tagging in Paperless-ngx
        if doc_id:
            tag_id = get_or_create_ai_tag()
            apply_tag_to_document(doc_id, tag_id)

        stats["processed_files"] += 1
        stats["history"].append(os.path.basename(pdf_path))
        update_dashboard()
    except Exception as e:
        print(f"Error: {e}")

def get_db_documents():
    """Extract document info from Paperless-ngx database using docker exec psql."""
    docs = []
    try:
        # Command to get ID, Title, and Filename from PostgreSQL
        # Added -q and -t for cleaner output
        cmd = 'docker exec clawstack-unified-postgres-1 psql -U postgres -d postgres -t -q -c "SELECT id, title, filename FROM documents_document;"'
        import subprocess
        # Use explicit encoding and error handling for Windows/Docker piping
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, encoding='utf-8', errors='replace')
        
        if result.returncode == 0 and result.stdout:
            for line in result.stdout.strip().split('\n'):
                if not line.strip(): continue
                parts = [p.strip() for p in line.split('|')]
                if len(parts) >= 3:
                    doc_id, title, filename = parts[0], parts[1], parts[2]
                    # Physical path in originals folder
                    originals_dir = r"D:\Clawdbot_Docker_20260125\clawstack_v2\data\paperless\media\documents\originals"
                    file_path = os.path.join(originals_dir, filename)
                    if os.path.exists(file_path):
                        docs.append({
                            "path": file_path,
                            "title": title,
                            "id": doc_id,
                            "source": "database"
                        })
    except Exception as e:
        print(f"DB Fetch Error: {e}")
    return docs

def main():
    if not os.path.exists(OUTPUT_DIR): os.makedirs(OUTPUT_DIR)
    
    # 1. Scan Consume Directory (Legacy Folder Monitoring)
    candidates = []
    for root, dirs, files in os.walk(CONSUME_DIR):
        for file in files:
            if file.lower().endswith('.pdf'):
                candidates.append({
                    "path": os.path.join(root, file),
                    "title": os.path.splitext(file)[0],
                    "source": "consume"
                })
    
    # 2. Scan Database (New DB Reference)
    db_docs = get_db_documents()
    candidates.extend(db_docs)
    
    stats["total_files"] = len(candidates)
    
    # Filter out already processed
    to_process = []
    for item in candidates:
        if item["source"] == "consume":
            rel_path = os.path.relpath(os.path.dirname(item["path"]), CONSUME_DIR)
            target_dir = os.path.join(OUTPUT_DIR, rel_path)
            output_md = os.path.join(target_dir, item["title"] + ".md")
        else:
            # For DB items, use a specific 'originals' output subfolder
            target_dir = os.path.join(OUTPUT_DIR, "paperless_db")
            output_md = os.path.join(target_dir, f"db_{item['id']}_{item['title']}.md")
        
        if os.path.exists(output_md):
            stats["processed_files"] += 1
            if item["title"] not in stats["history"]:
                stats["history"].append(item["title"])
        else:
            to_process.append((item, output_md, target_dir))

    update_dashboard()
        
    for item, output_md, target_dir in to_process:
        if not os.path.exists(target_dir): os.makedirs(target_dir)
        # Pass doc_id if source is database, else None
        doc_id = item.get("id") if item["source"] == "database" else None
        process_pdf(item["path"], output_md, doc_id=doc_id)

if __name__ == "__main__":
    main()
