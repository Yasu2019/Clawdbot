import os
import sys
import json
import subprocess
import requests
import time
from pathlib import Path

# --- Configuration ---
BASE_DIR = Path(__file__).parent
WORKER_SCRIPT = BASE_DIR / "dxf2step_worker.py"
SCORER_SCRIPT = BASE_DIR / "tests" / "score.py"
MODEL = "qwen3.5:9b"  # ユーザー推奨モデル
OLLAMA_API = "http://localhost:11434/api/generate"
MAX_ITERATIONS = 5

def run_score():
    """Run scorer and return the results from the latest JSON."""
    print(f"\n[Step 1] Running scorer...")
    result = subprocess.run(["python", str(SCORER_SCRIPT), "1"], capture_output=True, text=True)
    
    # score.py saves to tests/results_round01.json
    results_path = BASE_DIR / "tests" / "results_round01.json"
    if results_path.exists():
        with open(results_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return None

def get_fix_from_ai(current_code, error_context):
    """Call Local LLM to get a fix."""
    print(f"[Step 2] Consulting Brain (Local LLM: {MODEL})...")
    
    prompt = f"""
You are an expert FreeCAD and Python developer. 
The current DXF-to-3D conversion script `dxf2step_worker.py` is failing some test cases.
Goal: Resolve holes (boolean subtraction), counterbores, and complex product shapes.

[Current Code]
{current_code}

[Test Failures]
{json.dumps(error_context, indent=2)}

[Instruction]
Based on the failures, provide the ENTIRE updated content of `dxf2step_worker.py`. 
Ensure you implement:
1. Support for 'Hole' layers (subtract from 'Plate' or main body).
2. Proper handling of layer-specific thicknesses.
3. Multi-view reconstruction intersection logic if missing.

Respond ONLY with the complete Python code inside a code block.
"""

    payload = {
        "model": MODEL,
        "prompt": prompt,
        "stream": False,
        "options": {
            "num_ctx": 8192,
            "temperature": 0.2
        }
    }
    
    try:
        response = requests.post(OLLAMA_API, json=payload, timeout=300)
        response.raise_for_status()
        data = response.json()
        full_response = data.get("response", "")
        
        # Extract code block
        if "```python" in full_response:
            code = full_response.split("```python")[1].split("```")[0].strip()
            return code
        elif "```" in full_response:
            code = full_response.split("```")[1].split("```")[0].strip()
            return code
        return full_response.strip()
    except Exception as e:
        print(f"Error calling Ollama: {e}")
        return None

def main():
    print(f"=== DXF Autonomous Engineering Loop Starting ===")
    
    for i in range(MAX_ITERATIONS):
        print(f"\n--- Iteration {i+1}/{MAX_ITERATIONS} ---")
        
        results = run_score()
        if not results:
            print("Failed to run scorer.")
            break
            
        score = results.get("overall", 0)
        print(f"Current Overall Score: {score}/100")
        
        if score >= 100.0:
            print("CONGRATULATIONS! 100% Score achieved.")
            break
            
        # Collect failures
        failures = {k: v for k, v in results["tests"].items() if v["score"]["total"] < 100}
        
        with open(WORKER_SCRIPT, "r", encoding="utf-8") as f:
            current_code = f.read()
            
        new_code = get_fix_from_ai(current_code, failures)
        
        if new_code and "import" in new_code:  # Basic validation
            print(f"[Step 3] Applying fix to {WORKER_SCRIPT.name}...")
            with open(WORKER_SCRIPT, "w", encoding="utf-8") as f:
                f.write(new_code)
        else:
            print("Failed to get a valid fix from AI.")
            break
            
    print("\n=== Autonomous Loop Finished ===")

if __name__ == "__main__":
    main()
