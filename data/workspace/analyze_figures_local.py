import os
import json
import base64
import requests
import sys
import time

# Configuration
IMAGE_DIR = "/home/node/clawd/fischer_diagrams_full"
OUTPUT_MD = "/home/node/clawd/Mechanical_Tolerance_Stackup_Knowledge.md"
OLLAMA_API = "http://host.docker.internal:11434/api/generate"
# Note: If running inside container, host.docker.internal reaches host's Ollama if set up.
# Alternatively use localhost if Ollama is IN the container.
# Based on previous context, user has Ollama running?
# Let's try localhost first, if fails, fallback? 
# The Dockerfile has OLLAMA_BASE_URL=${OLLAMA_BASE_URL}.
# Let's assume localhost inside container if the user installed it there, OR host.docker.internal.
# Safe bet: Try localhost, if connection refused, try host.docker.internal.

MODEL = "llava"

def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

def analyze_image(image_path, prompt):
    try:
        base64_image = encode_image(image_path)
        
        payload = {
            "model": MODEL,
            "prompt": prompt,
            "images": [base64_image],
            "stream": False
        }
        
        # Try localhost (if Ollama in container)
        try:
            response = requests.post("http://localhost:11434/api/generate", json=payload, timeout=120)
        except requests.exceptions.ConnectionError:
             # Try host gateway (if Ollama on Windows)
            response = requests.post("http://host.docker.internal:11434/api/generate", json=payload, timeout=120)

        response.raise_for_status()
        return response.json().get("response", "")
    except Exception as e:
        return f"Error: {str(e)}"

def main():
    if not os.path.exists(IMAGE_DIR):
        print(f"Directory not found: {IMAGE_DIR}")
        return

    images = sorted([f for f in os.listdir(IMAGE_DIR) if f.endswith(".png")])
    total_images = len(images)
    
    print(f"Found {total_images} images to analyze.")
    print(f"Model: {MODEL}")
    
    with open(OUTPUT_MD, "a", encoding="utf-8") as f:
        f.write("\n\n# Automated Diagram Analysis (Local LLM: llava)\n")
        f.write(f"**Date:** {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")

    for i, img_name in enumerate(images):
        img_path = os.path.join(IMAGE_DIR, img_name)
        
        # Display Progress
        sys.stdout.write(f"\r[Analyzing] {i+1}/{total_images}: {img_name} ... ")
        sys.stdout.flush()
        
        # Construct specific prompt
        prompt = "Describe this engineering diagram. Identify any GD&T symbols, datums, or tolerance stackup formulas shown. Summarize the key mechanical relationships."
        
        start_time = time.time()
        description = analyze_image(img_path, prompt)
        elapsed = time.time() - start_time
        
        # Write to file (incremental)
        with open(OUTPUT_MD, "a", encoding="utf-8") as f:
            f.write(f"### Image: {img_name}\n")
            f.write(f"![{img_name}]({img_path})\n\n")
            f.write(f"**Analysis ({elapsed:.1f}s):**\n{description}\n\n---\n\n")
            
        sys.stdout.write(f"Done ({elapsed:.1f}s)\n")

    print("\nAnalysis Complete!")

if __name__ == "__main__":
    main()
