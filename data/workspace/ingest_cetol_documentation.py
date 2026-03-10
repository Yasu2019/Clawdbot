
import os
import requests
import json
import base64
import time
from glob import glob
from PIL import Image
from io import BytesIO

# --- Config ---
# Path mapping: Windows Host -> Docker
# D:\Clawdbot_Docker_20260125\clawstack_v2\data\paperless\consume\cetol6sigma
# -> /home/node/clawd/consumption_staging (Assuming we need to mount or copy)
# OR we can just access it if it's in the workspace?
# Workspace is at D:\Clawdbot_Docker_20260125\data\workspace
# The target is OUTSIDE workspace... 
# Wait, user said "data\workspace" is the workspace ROOT.
# Clawstack_v2 is a sibling.
# We cannot access it directly from Docker unless mounted.
# I will assume I need to run this on the HOST or copy files first.
# BUT, I am running python inside Docker (/home/node/clawd).
# Check if the volume is mounted?
# Docker Compose usually mounts the whole directory?
# Let's check docker-compose.yml content from persistent context or view it.

# Assuming we can access via /home/node/clawd/../../clawstack_v2 if mounted at root?
# No, usually mounted at specific points.

# Hack: Use the "consume" folder in workspace which IS mounted.
# I will ask the user or just copy the files using `run_command` in Windows to the workspace consume folder.

INPUT_DIR = "/home/node/clawd/consume/cetol_wip/extracted"
OLLAMA_URL = "http://host.docker.internal:11434/api/generate"
MODEL = "llava"
KNOWLEDGE_FILE = "/home/node/clawd/CETOL_6Sigma_Deep_Knowledge.md"

def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

def analyze_image(path):
    print(f"Analyzing {os.path.basename(path)}...")
    try:
        b64 = encode_image(path)
        prompt = """
        You are an expert mechanical engineer specializing in Tolerance Analysis and GD&T.
        Analyze this diagram from the CETOL 6 Sigma manual.
        1. Describe the geometry and the tolerance loops shown.
        2. Identify the mathematical model implies (Vector Loop, DOF, Sensitivity).
        3. Extract any specific formulas or constraints visible.
        4. Explain the 'Deep Knowledge' or theoretical insight this figure conveys about tolerance stackups.
        """
        
        data = {
            "model": MODEL,
            "prompt": prompt,
            "images": [b64],
            "stream": False
        }
        
        load_start = time.time()
        res = requests.post(OLLAMA_URL, json=data, timeout=300)
        
        if res.status_code == 200:
            result = res.json().get("response", "")
            print(f"  -> Done in {time.time()-load_start:.1f}s")
            return result
        else:
            print(f"  -> Error: {res.status_code} {res.text}")
            return ""
            
    except Exception as e:
        print(f"  -> Exception: {e}")
        return ""

def main():
    if not os.path.exists(INPUT_DIR):
        print(f"Input dir not found: {INPUT_DIR}")
        return

    # Find images
    extensions = ["*.png", "*.jpg", "*.jpeg", "*.bmp"]
    files = []
    for ext in extensions:
        files.extend(glob(os.path.join(INPUT_DIR, ext)))
    
    print(f"Found {len(files)} images to analyze.")
    
    with open(KNOWLEDGE_FILE, "a", encoding="utf-8") as f:
        f.write("\n# CETOL 6 Sigma Figure Analysis (Automated)\n\n")
        
        for file in files:
            analysis = analyze_image(file)
            if analysis:
                f.write(f"## Figure: {os.path.basename(file)}\n\n")
                f.write(f"![Figure](file://{file})\n\n")
                f.write(analysis + "\n\n")
                f.write("---\n")
                
    print("Analysis Complete.")

if __name__ == "__main__":
    main()
