
import os
import requests
import json
import base64
import time
from glob import glob

INPUT_DIR = "/home/node/clawd/consume/cetol_wip/extracted"
OLLAMA_URL = "http://host.docker.internal:11434/api/generate"
MODEL = "llava"
KNOWLEDGE_FILE = "/home/node/clawd/CETOL_6Sigma_Deep_Knowledge.md"

def get_processed_files():
    processed = set()
    if os.path.exists(KNOWLEDGE_FILE):
        with open(KNOWLEDGE_FILE, "r", encoding="utf-8") as f:
            for line in f:
                if line.startswith("## Figure: "):
                    filename = line.replace("## Figure: ", "").strip()
                    processed.add(filename)
    return processed

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

    # Find all images
    extensions = ["*.png", "*.jpg", "*.jpeg", "*.bmp"]
    all_files = []
    for ext in extensions:
        all_files.extend(glob(os.path.join(INPUT_DIR, ext)))
    
    processed_files = get_processed_files()
    print(f"Total images: {len(all_files)}")
    print(f"Already processed: {len(processed_files)}")
    
    remaining_files = [f for f in all_files if os.path.basename(f) not in processed_files]
    print(f"Remaining to process: {len(remaining_files)}")
    
    if not remaining_files:
        print("Nothing to do.")
        return

    # Sort to ensure order
    remaining_files.sort()

    with open(KNOWLEDGE_FILE, "a", encoding="utf-8") as f:
        f.write("\n\n--- [RESUME SESSION START] ---\n\n")
        
        for file in remaining_files:
            analysis = analyze_image(file)
            if analysis:
                f.write(f"## Figure: {os.path.basename(file)}\n\n")
                f.write(f"![Figure](file://{file})\n\n")
                f.write(analysis + "\n\n")
                f.write("---\n")
                f.flush() # Ensure write to disk
                
    print("Resume Analysis Complete.")

if __name__ == "__main__":
    main()
