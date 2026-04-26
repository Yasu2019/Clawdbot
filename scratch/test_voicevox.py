import requests
import os

VOICEVOX_URL = "http://localhost:50021"

def test_vox():
    text = "テストです。"
    speaker = 3
    params = {"text": text, "speaker": speaker}
    try:
        print("Sending audio_query...")
        res = requests.post(f"{VOICEVOX_URL}/audio_query", params=params, timeout=10)
        print(f"Response: {res.status_code}")
        if res.status_code == 200:
            print("Success!")
        else:
            print(f"Fail: {res.text}")
    except Exception as e:
        print(f"Error: {e}")

test_vox()
