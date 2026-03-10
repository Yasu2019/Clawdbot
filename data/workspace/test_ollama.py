import requests
import json

payload = {
    "model": "qwen2.5:32b",
    "prompt": "Hi, answer in one Japanese word.",
    "stream": False,
    "format": "json"
}
try:
    print("Testing connection to http://ollama:11434/api/generate ...")
    resp = requests.post("http://ollama:11434/api/generate", json=payload, timeout=60)
    print("Status:", resp.status_code)
    print("Response:", resp.json())
except Exception as e:
    print("Error:", e)
