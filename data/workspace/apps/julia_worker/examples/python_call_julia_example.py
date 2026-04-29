import requests

payload = {
    "thickness_mm": 0.8,
    "yield_mpa": 85,
    "roller_diameter_mm": 12,
    "pitch_mm": 16,
    "entry_gap_mm": 0.7,
    "exit_gap_mm": 1.1,
    "stages": 11,
    "friction": 0.05,
}

r = requests.post("http://localhost:8097/leveler/estimate", json=payload, timeout=30)
r.raise_for_status()
print(r.json())
