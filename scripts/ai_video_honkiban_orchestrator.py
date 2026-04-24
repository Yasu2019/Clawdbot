import argparse
import json
import os
import urllib.request
import time
import sys

# Configuration
OLLAMA_API_URL = "http://localhost:11434/api/generate"
MODEL_NAME = "qwen3:8b" 
WORKSPACE_DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "workspace")
PROTOCOL_DIR = os.path.join(WORKSPACE_DATA_DIR, "apps", "ai_video_engine", "protocols")
OUTPUT_DIR = os.path.join(WORKSPACE_DATA_DIR, "ai_video_outputs")

def call_ollama(prompt):
    print(f"[*] Calling local LLM ({MODEL_NAME}) for production-grade prompt design...")
    payload = {
        "model": MODEL_NAME,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": 0.4, # Lower temperature for structural stability
            "num_predict": 2048
        }
    }
    data = json.dumps(payload).encode('utf-8')
    req = urllib.request.Request(OLLAMA_API_URL, data=data, headers={'Content-Type': 'application/json'})
    try:
        with urllib.request.urlopen(req, timeout=180) as response:
            result = json.loads(response.read().decode('utf-8'))
            return result.get('response', '').strip()
    except Exception as e:
        print(f"[!] Error calling Ollama: {e}")
        return None

def generate_honkiban_shot(topic):
    # Load schema template if available
    schema_path = os.path.join(PROTOCOL_DIR, "03_JSON_SCHEMA_TEMPLATE.json")
    schema_hint = ""
    if os.path.exists(schema_path):
        with open(schema_path, 'r', encoding='utf-8') as f:
            schema_hint = f.read()

    prompt = f"""You are a high-end AI Video Director.
Create a production-grade shot specification for the topic: "{topic}"
You MUST follow the "Honkiban" (Main Production) protocol schema below.

SCHEMA TEMPLATE:
{schema_hint}

REQUIREMENTS:
1. Ensure 'identity_lock' is true.
2. Define 'exclusions' to avoid typical AI artifacts (extra limbs, morphing).
3. Set 'quality_targets' to high levels.
4. Specify 'start_frame' and 'end_frame' pose concepts.
5. Focus on cinematic realism and physical consistency.

Respond ONLY with the filled JSON object. No markdown, no intro."""

    response_text = call_ollama(prompt)
    if not response_text:
        return None
    
    # Clean up response
    response_text = response_text.replace('```json', '').replace('```', '').strip()
    
    try:
        shot_data = json.loads(response_text)
        return shot_data
    except json.JSONDecodeError:
        print("[!] LLM did not return strict JSON.")
        return None

def main():
    parser = argparse.ArgumentParser(description="AI Video Honkiban Orchestrator")
    parser.add_argument("--topic", required=True, help="Topic for the production shot")
    parser.add_argument("--dry-run", action="store_true", help="Only generate JSON, don't simulate execution")
    args = parser.parse_args()

    print("==========================================")
    print(" AI VIDEO HONKIBAN (PRODUCTION) PIPELINE")
    print("==========================================")
    print(f"Topic: {args.topic}")
    
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    shot_data = generate_honkiban_shot(args.topic)
    if not shot_data:
        print("[!] Aborting due to generation failure.")
        sys.exit(1)
        
    print("\n--- Production Shot Specification ---")
    print(json.dumps(shot_data, indent=2, ensure_ascii=False))
    print("--------------------------------------")

    # Save outputs
    project_id = shot_data.get("project_id", "untitled_project")
    shot_id = shot_data.get("shot_id", "shot_001")
    output_file = os.path.join(OUTPUT_DIR, f"{project_id}_{shot_id}.json")
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(shot_data, f, indent=2, ensure_ascii=False)
    print(f"\n[+] Production JSON saved to: {output_file}")

    if args.dry_run:
        print("[*] Dry-run complete. No execution triggered.")
        return

    print("\n[Phase 2] Security Gate - Production Review")
    print("Awaiting manual confirmation for High-Quality Render...")
    try:
        choice = input("Approve this specification? [Y/n]: ")
        if choice.strip().lower() not in ['y', 'yes', '']:
            print("[!] Production halted by operator.")
            sys.exit(0)
    except KeyboardInterrupt:
        print("\n[!] Aborted.")
        sys.exit(1)

    print("\n[Phase 3] Production Dispatch...")
    print("[i] Integrating with Cloud/Local Render API (Simulation)...")
    time.sleep(2)
    print("[+] Render job dispatched successfully.")

if __name__ == "__main__":
    main()
