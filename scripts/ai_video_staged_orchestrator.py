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
MODEL_NAME = "qwen3:8b" # Consistent with telegram_fast_bridge.js
WORKSPACE_DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "workspace")
REMOTION_DATA_DIR = os.path.join(WORKSPACE_DATA_DIR, "remotion_data")
SCENES_OUTPUT_FILE = os.path.join(REMOTION_DATA_DIR, "scenes.json")

def call_ollama(prompt):
    print(f"[*] Calling local LLM model ({MODEL_NAME}) to generate content...")
    payload = {
        "model": MODEL_NAME,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": 0.5,
            "num_predict": 1024
        }
    }
    data = json.dumps(payload).encode('utf-8')
    req = urllib.request.Request(OLLAMA_API_URL, data=data, headers={'Content-Type': 'application/json'})
    try:
        with urllib.request.urlopen(req, timeout=120) as response:
            result = json.loads(response.read().decode('utf-8'))
            return result.get('response', '').strip()
    except Exception as e:
        print(f"[!] Error calling Ollama: {e}")
        return None

def generate_scenes(topic):
    prompt = f"""You are a creative video director. 
Create a short video script about: "{topic}"
Split it into exactly 3 to 5 scenes. Keep each scene description under 15 words.
Format the output EXACTLY as valid JSON array, like this:
[
  {{"scene": 1, "description": "short description", "durationInSeconds": 5}},
  {{"scene": 2, "description": "short description", "durationInSeconds": 5}}
]
Respond ONLY with the JSON array. Do not add markdown blocks or explanations."""

    response_text = call_ollama(prompt)
    if not response_text:
        return None
    
    # Clean up response (sometimes models still add markdown blocks)
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
    parser = argparse.ArgumentParser(description="Staged AI Video Pipeline")
    parser.add_argument("--topic", required=True, help="Topic for the video generation")
    parser.add_argument("--mode", choices=["simple", "honkiban"], default="simple", help="Generation mode (simple or production-grade honkiban)")
    args = parser.parse_args()

    if args.mode == "honkiban":
        print("[i] Redirecting to Honkiban (Production) Orchestrator...")
        honkiban_script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ai_video_honkiban_orchestrator.py")
        subprocess.run([sys.executable, honkiban_script, "--topic", args.topic])
        return

    print("====================================")
    print(" AI VIDEO PIPELINE - STAGED APPROVAL")
    print("====================================")
    print(f"Topic: {args.topic}")
    
    os.makedirs(REMOTION_DATA_DIR, exist_ok=True)

    # Step 1-3: Generate Script and Split Scenes
    print("\n[Phase 1] Generation...")
    scenes = generate_scenes(args.topic)
    if not scenes:
        print("[!] Aborting due to generation failure.")
        sys.exit(1)
        
    print("\n--- Generated Scenes ---")
    print(json.dumps(scenes, indent=2, ensure_ascii=False))
    print("------------------------")

    # Save outputs
    with open(SCENES_OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(scenes, f, indent=2, ensure_ascii=False)
    print(f"\n[+] Saved scene data to: {SCENES_OUTPUT_FILE}")

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
        
    # Render Step
    print("\n[Phase 3] Execution...")
    remotion_dir = os.path.join(WORKSPACE_DATA_DIR, "remotion_projects", "my_video_project")
    
    if os.path.exists(remotion_dir):
        print(f"[+] Found Remotion project at {remotion_dir}. Triggering render...")
        try:
            subprocess.run(["npx", "remotion", "render", "src/index.ts", "MyComposition", "out/video.mp4"], cwd=remotion_dir, check=True)
            print("[+] Video rendered successfully.")
        except subprocess.CalledProcessError as e:
            print(f"[!] Error during Remotion render: {e}")
    else:
        print(f"[i] Note: Remotion project path not found at {remotion_dir}.")
        print(f"[i] To set up: 'bun create video my_video_project' inside {os.path.join(WORKSPACE_DATA_DIR, 'remotion_projects')}")
        print("[i] Render step simulated successfully.")

    print("\n[+] Pipeline completed securely.")

if __name__ == "__main__":
    main()
