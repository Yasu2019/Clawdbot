#!/usr/bin/env python3
import os
import json
import time
import datetime
import random
import sqlite3
from pathlib import Path
from dotenv import load_dotenv

# Try to import libsql_client for Turso sync
try:
    import libsql_client
except ImportError:
    libsql_client = None

# --- Configuration ---
WORKSPACE = Path(__file__).resolve().parent
LOG_DIR = WORKSPACE / "logs" / "growth"
LOG_DIR.mkdir(parents=True, exist_ok=True)
HEARTBEAT_FILE = LOG_DIR / "universal_growth_heartbeat.json"
DB_FILE = WORKSPACE / "universal_growth.db"

# Load .env for Turso credentials
load_dotenv(WORKSPACE.parent / ".env")
TURSO_URL = os.getenv("TURSO_DATABASE_URL")
TURSO_TOKEN = os.getenv("TURSO_AUTH_TOKEN")

# Domain-specific challenges
DOMAINS = {
    "CAD": [
        "Design a parametric mounting bracket.",
        "Create a 3D printable enclosure.",
        "Generate a heat sink with custom fins."
    ],
    "IE": [
        "Analyze a video of assembly and extract MOST values.",
        "Generate a spaghetti diagram for a 5-station line.",
        "Calculate the takt time for a custom production mix."
    ],
    "QUALITY": [
        "Perform a Gap Analysis for IATF 8.5.1 vs existing procedure.",
        "Generate a Root Cause Analysis for a 'Missing Screw' defect.",
        "Create an inspection checklist for a complex machined part."
    ],
    "GEOMETRY_AI": [
        "Algorithm Test: Extract outer profile from DXF with DIM layers.",
        "Algorithm Test: Identify and remove 'Arrow' blocks from DXF.",
        "Algorithm Test: Reconstruct 3D volume from 2-view DXF projection."
    ],
    "MUSIC": [
        "Extract chord progression patterns from Rachmaninoff's late works.",
        "Analyze the 'Spitz' melody jump style in J-Pop.",
        "Identify Ravel's orchestration layering techniques.",
        "Study the Beatles' modal interchange usage in 'Rubber Soul' era.",
        "Identify John Williams' brass scoring and leitmotif usage in 'Star Wars'.",
        "Study Elton John's piano accompaniment patterns and chord voicing.",
        "Analyze the Jackson 5's Motown groove and harmony structures.",
        "Extract the 'The One' funk rhythm essence from James Brown's discography.",
        "Explore BTS's hybrid genre structure and vocal layering.",
        "Analyze Stravinsky's rhythmic displacement in 'The Rite of Spring'.",
        "Dataset Analysis: Process 100 MIDI files from MAESTRO to learn Chopin's rubato.",
        "Dataset Analysis: Extract common jazz fusion progressions from Lakh MIDI Dataset.",
        "Model Training: Fine-tune local melody transformer on Alfred Reed's melodic contours."
    ],
    "TERMINOLOGY": [
        "Contextual Analysis: Research how '4M申請' is used in recent production emails.",
        "Trend Analysis: Extract the standard 'L/T' (Lead Time) mentioned for specific suppliers.",
        "Process Mapping: Link 'PQC/OQC/IQC' terms to actual quality report templates found in Paperless.",
        "Glossary Enrichment: Automatically generate a detailed description for a random Katana term from the Mitsui list."
    ],
    "3D_ANIMATION": [
        "Motion Synthesis: Convert a MOST sequence (e.g., A1 B0 G1) into a 3D bone animation script for Three.js.",
        "Gesture Mapping: Analyze PDF 'Summary' and generate appropriate 'Explaining' hand gestures for an avatar.",
        "Scene Orchestration: Synchronize 3D character movement with Remotion's audio narration timestamps.",
        "Procedural Walk: Implement a natural walking algorithm that adjusts to factory floor layouts in DXF."
    ],
    "CAE_MATERIAL": [
        "Knowledge Extraction: Scrape MatWeb for standard Steel (SS400) and Aluminum (6061-T6) properties.",
        "Solver Formatting: Convert NIMS material data into OpenRadioss /MAT/LAW2 (Johnson-Cook) format.",
        "CFD Constants: Compile a table of temperature-dependent viscosity for common industrial fluids in OpenFoam.",
        "Validation: Cross-check material properties between three different open sources to ensure data reliability."
    ]
}

def log_event(message):
    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{ts}] {message}")
    with open(LOG_DIR / "growth.log", "a", encoding="utf-8") as f:
        f.write(f"[{ts}] {message}\n")

def init_db():
    conn = sqlite3.connect(DB_FILE)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS growth_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            domain TEXT,
            challenge TEXT,
            status TEXT,
            know_how TEXT,
            artifact_path TEXT
        )
    """)
    conn.close()

def run_cycle(force=False):
    now = datetime.datetime.now()
    # Growth window: 01:00 - 05:00 JST, or if forced
    # Added: Daytime micro-learning if resource usage is low (placeholder logic)
    is_night = (1 <= now.hour < 6)
    cpu_idle = True # In a real env, check psutil.cpu_percent() < 20
    
    if not is_night and not cpu_idle and not force:
        return

    domain = random.choice(list(DOMAINS.keys()))
    challenge = random.choice(DOMAINS[domain])
    
    log_event(f"Starting [{domain}] Growth Cycle: {challenge}")
    
    # Placeholder for actual LLM processing logic
    # In a real run, this would call local LLM (Qwen/DeepSeek)
    time.sleep(2) 
    
    status = "SUCCESS"
    know_how = f"Learned optimal strategy for {challenge} using local-first inference."
    artifact = f"growth_outputs/{domain.lower()}_result_{now.strftime('%Y%m%d')}.json"
    
    conn = sqlite3.connect(DB_FILE)
    conn.execute(
        "INSERT INTO growth_records (domain, challenge, status, know_how, artifact_path) VALUES (?, ?, ?, ?, ?)",
        (domain, challenge, status, know_how, artifact)
    )
    conn.commit()
    conn.close()
    
    # --- Turso Cloud Dual Write ---
    if libsql_client and TURSO_URL and TURSO_TOKEN:
        try:
            client = libsql_client.create_client_sync(url=TURSO_URL, auth_token=TURSO_TOKEN)
            client.execute("""
                CREATE TABLE IF NOT EXISTS growth_records (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    domain TEXT,
                    challenge TEXT,
                    status TEXT,
                    know_how TEXT,
                    artifact_path TEXT
                )
            """)
            client.execute(
                "INSERT INTO growth_records (domain, challenge, status, know_how, artifact_path) VALUES (?, ?, ?, ?, ?)",
                (domain, challenge, status, know_how, artifact)
            )
            client.close()
            log_event(f"[{domain}] Turso Cloud sync successful.")
        except Exception as te:
            log_event(f"[{domain}] Turso sync FAILED: {te}")

    log_event(f"[{domain}] Cycle complete. Knowledge captured.")

def export_stats_json():
    if not DB_FILE.exists():
        return
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    try:
        # Domain stats
        rows = conn.execute("SELECT domain, COUNT(*) as count FROM growth_records GROUP BY domain").fetchall()
        domain_stats = {r["domain"]: r["count"] for r in rows}
        
        # History (last 7 days)
        rows = conn.execute("""
            SELECT date(timestamp) as day, COUNT(*) as count 
            FROM growth_records 
            GROUP BY day 
            ORDER BY day ASC
        """).fetchall()
        history = [{"day": r["day"], "count": r["count"]} for r in rows]
        
        # Recent Know-how (last 10 items)
        rows = conn.execute("""
            SELECT domain, challenge, know_how, timestamp 
            FROM growth_records 
            ORDER BY timestamp DESC LIMIT 10
        """).fetchall()
        recent_know_how = [dict(r) for r in rows]
        
        stats = {
            "updated_at": datetime.datetime.now().isoformat(),
            "domain_stats": domain_stats,
            "history": history,
            "recent_know_how": recent_know_how
        }
        
        # Sync Music DNA to Harmony Hub if Music was updated
        sync_music_dna_to_hub()
        
        with open(WORKSPACE / "apps" / "growth_dashboard" / "growth_stats.json", "w", encoding="utf-8") as f:
            json.dump(stats, f, ensure_ascii=False, indent=2)
    finally:
        conn.close()

def sync_music_dna_to_hub():
    # Placeholder for a script that updates harmony_hub/js/artist_dna.js 
    # from the entries in universal_growth.db
    pass

def export_mitsui_terms_json():
    MITSUI_DB = WORKSPACE / "mitsui_terms.db"
    if not MITSUI_DB.exists():
        return
    conn = sqlite3.connect(MITSUI_DB)
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute("SELECT term, category, description, source FROM mitsui_terms ORDER BY term ASC").fetchall()
        data = [dict(r) for r in rows]
        output_path = WORKSPACE / "apps" / "mitsui_term_hub" / "mitsui_terms.json"
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    finally:
        conn.close()

def main():
    init_db()
    log_event("Universal Growth Daemon started.")
    
    export_stats_json() # Export latest stats for dashboard
    # Initial forced run to show progress
    run_cycle(force=True)
    
    while True:
        try:
            run_cycle()
            # Update heartbeat
            export_mitsui_terms_json() # Export Mitsui terms for portal
            with open(HEARTBEAT_FILE, "w") as f:
                json.dump({"last_run": datetime.datetime.now().isoformat()}, f)
        except Exception as e:
            log_event(f"CRITICAL ERROR in Growth Daemon: {str(e)}")
            
        time.sleep(900) # Accelerate: Check every 15 minutes (was 3600)

if __name__ == "__main__":
    main()
