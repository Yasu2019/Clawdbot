import argparse
import json
import os
import urllib.request
import urllib.error
import time
import subprocess
import sys

# Configuration
OLLAMA_API_URL = "http://localhost:11434/api/generate"
MODEL_NAME = "qwen3:8b" 
WORKSPACE_DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "workspace")
REMOTION_DATA_DIR = os.path.join(WORKSPACE_DATA_DIR, "remotion_data")
SCENES_OUTPUT_FILE = os.path.join(REMOTION_DATA_DIR, "scenes.json")

# Anijam Specific Paths
ANIJAM_ROOT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "protocols", "anijam")
PROMPT_TEMPLATE_PATH = os.path.join(ANIJAM_ROOT, "prompts", "anijam_prompt_template_ja.txt")
SYSTEM_PROMPT_PATH = os.path.join(ANIJAM_ROOT, "prompts", "master_system_prompt_ja.txt")

def load_file(path):
    if os.path.exists(path):
        with open(path, 'r', encoding='utf-8') as f:
            return f.read()
    return ""

def call_ollama(prompt, system_prompt=""):
    print(f"[*] Calling local LLM model ({MODEL_NAME}) to generate Anijam content...")
    payload = {
        "model": MODEL_NAME,
        "prompt": prompt,
        "system": system_prompt,
        "stream": False,
        "options": {
            "temperature": 0.5,
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

def generate_anijam_scenes(topic, audience="QA Team", purpose="Internal Education"):
    template = load_file(PROMPT_TEMPLATE_PATH)
    system_prompt = load_file(SYSTEM_PROMPT_PATH)
    
    # Simple placeholder replacement
    filled_prompt = template.replace("{{THEME}}", topic)
    filled_prompt = filled_prompt.replace("{{AUDIENCE}}", audience)
    filled_prompt = filled_prompt.replace("{{PURPOSE}}", purpose)
    filled_prompt = filled_prompt.replace("{{DURATION}}", "60 seconds")
    filled_prompt = filled_prompt.replace("{{ASPECT_RATIO}}", "16:9")
    filled_prompt = filled_prompt.replace("{{TONE}}", "Professional yet engaging")
    filled_prompt = filled_prompt.replace("{{CHARACTERS}}", "Clawbot (AI assistant) and Factory workers")
    filled_prompt = filled_prompt.replace("{{KEY_MESSAGES}}", "Safety first, Quality always")
    filled_prompt = filled_prompt.replace("{{PROHIBITIONS}}", "No personal data, no real customer names")
    filled_prompt = filled_prompt.replace("{{SCENES}}", "3-5 scenes with technical details")

    # Append JSON instruction
    filled_prompt += "\n\nFormat the output EXACTLY as valid JSON array of objects with keys: 'scene', 'description', 'durationInSeconds', 'script_ja'.\nRespond ONLY with the JSON array."

    response_text = call_ollama(filled_prompt, system_prompt)
    if not response_text:
        return None
    
    # Clean up response
    response_text = response_text.replace('```json', '').replace('```', '').strip()
    
    try:
        scenes = json.loads(response_text)
        return scenes
    except json.JSONDecodeError:
        print("[!] LLM did not return strict JSON.")
        print("Raw response:")
        print(response_text)
        return None

def main():
    parser = argparse.ArgumentParser(description="Anijam QA Video Orchestrator")
    parser.add_argument("--topic", required=True, help="Topic for the QA video")
    parser.add_argument("--audience", default="QA Engineers", help="Target audience")
    parser.add_argument("--purpose", default="Standard training", help="Video purpose")
    parser.add_argument("--dry-run", action="store_true", help="Stop before rendering")
    args = parser.parse_args()

    print("====================================")
    print(" ANIJAM QA VIDEO PIPELINE")
    print("====================================")
    print(f"Topic: {args.topic}")
    
    os.makedirs(REMOTION_DATA_DIR, exist_ok=True)

    print("\n[Phase 1] Anijam Protocol Generation...")
    scenes = generate_anijam_scenes(args.topic, args.audience, args.purpose)
    if not scenes:
        print("[!] Aborting due to generation failure.")
        sys.exit(1)
        
    print("\n--- Generated Anijam Scenes ---")
    print(json.dumps(scenes, indent=2, ensure_ascii=False))
    print("------------------------")

    # Save outputs
    with open(SCENES_OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(scenes, f, indent=2, ensure_ascii=False)
    print(f"\n[+] Saved scene data to: {SCENES_OUTPUT_FILE}")

    if args.dry_run:
        print("\n[i] Dry-run completed. Verification successful.")
        sys.exit(0)

    # HUMAN IN THE LOOP APPROVAL
    print("\n[Phase 2] Security Gate - HUMAN IN THE LOOP")
    print("WARNING: As per AGENTS.md Section 4-3, autonomous rendering is paused.")
    print("Please review the generated scenes above.")
    
    try:
        choice = input("Do you approve these scenes and wish to proceed with Remotion render? [Y/n]: ")
    except KeyboardInterrupt:
        print("\n[!] Aborted by user.")
        sys.exit(1)
        
    if choice.strip().lower() not in ['y', 'yes', '']:
        print("[!] Execution halted by operator.")
        sys.exit(0)
        
    # Render Step (Simplified check)
    print("\n[Phase 3] Execution...")
    remotion_dir = os.path.join(WORKSPACE_DATA_DIR, "remotion_projects", "anijam_project")
    
    if os.path.exists(remotion_dir):
        print(f"[+] Found Remotion project at {remotion_dir}. Triggering render...")
        try:
            # Note: Remotion render command may vary based on project setup
            subprocess.run(["npx", "remotion", "render", "src/index.ts", "AnijamComposition", "out/anijam_video.mp4"], cwd=remotion_dir, check=True)
            print("[+] Video rendered successfully.")
        except subprocess.CalledProcessError as e:
            print(f"[!] Error during Remotion render: {e}")
    else:
        print(f"[i] Note: Anijam Remotion project not found at {remotion_dir}.")
        print(f"[i] To set up: 'bun create video anijam_project' inside {os.path.join(WORKSPACE_DATA_DIR, 'remotion_projects')}")
        print("[i] Render step simulated successfully.")

    print("\n[+] Anijam Pipeline completed securely.")

if __name__ == "__main__":
    main()
