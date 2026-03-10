
import os
import requests
import base64
import time
from glob import glob

INPUT_DIR = "/home/node/clawd/fischer_figures_wip"
OLLAMA_URL = "http://host.docker.internal:11434/api/generate"
MODEL = "llava"
KNOWLEDGE_FILE = "/home/node/clawd/Mechanical_Tolerance_Stackup_Knowledge.md"

def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

def analyze_image(path):
    print(f"Analyzing {os.path.basename(path)}...")
    try:
        b64 = encode_image(path)
        prompt = """
        Analyze this diagram from a Mechanical Tolerance Analysis textbook.
        1. Identify the type of diagram (GD&T Control Frame, Stackup Loop, Assembly Interface, etc.).
        2. Extract any visible mathematical formulas or tolerance values.
        3. Explain the mechanical concept being illustrated.
        4. If it's a specific stackup example (like R-A Assembly), detail the components and loop.
        """
        
        data = {
            "model": MODEL,
            "prompt": prompt,
            "images": [b64],
            "stream": False
        }
        
        res = requests.post(OLLAMA_URL, json=data, timeout=300)
        if res.status_code == 200:
            return res.json().get("response", "")
        return ""
    except Exception as e:
        print(f"Error: {e}")
        return ""

def main():
    if not os.path.exists(INPUT_DIR):
        print(f"Dir not found: {INPUT_DIR}")
        return

    images = sorted(glob(os.path.join(INPUT_DIR, "*")))
    print(f"Found {len(images)} images.")
    
    with open(KNOWLEDGE_FILE, "a", encoding="utf-8") as f:
        f.write("\n# Deep Figure Analysis (Automated VLM)\n\n")
        
        for img in images:
            # Skip likely icons based on size (double check, but we filtered in extraction)
            
            analysis = analyze_image(img)
            if analysis:
                f.write(f"## Figure: {os.path.basename(img)}\n\n")
                f.write(f"![Figure](file://{img})\n\n")
                f.write(analysis + "\n\n")
                f.write("---\n")
                f.flush()

if __name__ == "__main__":
    main()
