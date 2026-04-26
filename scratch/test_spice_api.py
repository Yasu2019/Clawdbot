import requests
import json
import os

netlist_path = r"D:\Clawdbot_Docker_20260125\integrations\spice_lab\04_examples\rc_lowpass_ngspice.cir"
url = "http://127.0.0.1:8765/simulate"

with open(netlist_path, "r", encoding="utf-8") as f:
    netlist = f.read()

payload = {
    "name": "rc_lowpass_test_python",
    "netlist": netlist
}

print(f"Sending simulation request to {url}...")
response = requests.post(url, json=payload)

if response.status_code == 200:
    print("Simulation successful!")
    data = response.json()
    print(json.dumps(data, indent=2, ensure_ascii=False))
else:
    print(f"Simulation failed with status {response.status_code}")
    print(response.text)
