#!/usr/bin/env python3
"""
ask_specialist.py

This script serves as a bridge for OpenClaw to delegate heavy reasoning, 
complex coding, or extreme troubleshooting tasks to the container's 
built-in Specialist AI.

Currently runs via Local Ollama (qwen2.5-coder) to ensure unlimited 
and free execution within the sandboxed container environment, bypassing 
any cloud API rate limits.

Usage:
    python3 /work/scripts/ask_specialist.py "Please generate an OpenFOAM blockMeshDict for a 2D pipe"
    python3 /work/scripts/ask_specialist.py --file /work/error.log "Why did the solver diverge here?"
"""

import sys
import os
import json
import urllib.request
import argparse

def query_ollama(prompt):
    """
    Directly query the local Ollama instance running Qwen2.5-Coder.
    """
    url = "http://ollama:11434/api/generate"
    
    headers = {
        "Content-Type": "application/json"
    }
    
    data = {
        "model": "qwen2.5-coder:32b",
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": 0.2
        }
    }
    
    req = urllib.request.Request(url, data=json.dumps(data).encode('utf-8'), headers=headers, method='POST')
    
    try:
        # 300 seconds timeout allows the massive 19GB 32b model to load into memory on the first request
        with urllib.request.urlopen(req, timeout=300) as response:
            result = json.loads(response.read().decode('utf-8'))
            return result.get('response', '')
            
    except urllib.error.URLError as e:
        raise Exception(f"Failed to connect to Ollama service (http://ollama:11434): {str(e)}")
    except Exception as e:
        raise Exception(f"Request failed: {str(e)}")

def run_specialist(prompt, context_file=None):
    print(f"🤖 [Specialist Bridge] Forwarding task to Local Qwen2.5-Coder (Ollama)...")
    
    full_prompt = prompt
    if context_file:
        if not os.path.exists(context_file):
            print(f"❌ Error: Context file not found: {context_file}")
            sys.exit(1)
            
        with open(context_file, 'r', encoding='utf-8') as f:
            file_content = f.read()
            
        full_prompt = f"Context file ({os.path.basename(context_file)}):\n```\n{file_content[:50000]}\n```\n\nTask: {prompt}"
        
    try:
        response_text = query_ollama(full_prompt)
        
        print("\n" + "="*50)
        print("✅ [Specialist Response]:\n")
        print(response_text)
        print("="*50 + "\n")
            
    except Exception as e:
        print(f"\n❌ [Error executing Specialist]:\n{str(e)}")
        sys.exit(1)

def main():
    parser = argparse.ArgumentParser(description="Delegate heavy tasks to the internal AI Specialist.")
    parser.add_argument("prompt", type=str, help="The task or question to ask the Specialist.")
    parser.add_argument("--file", "-f", type=str, help="Optional text file to attach as context (e.g. logs/code).", default=None)
    
    args = parser.parse_args()
    run_specialist(args.prompt, args.file)

if __name__ == "__main__":
    main()
