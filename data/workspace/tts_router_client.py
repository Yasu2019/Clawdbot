#!/usr/bin/env python3
"""
OpenClaw TTS Router Client
==========================
TTS Router (port 18081) 経由で音声を生成するための簡易クライアント。

使い方:
    from tts_router_client import speak
    speak("設備異常を確認してください。", purpose="factory_alert")
"""
import requests
import os
import sys

TTS_ROUTER_URL = os.getenv("TTS_ROUTER_URL", "http://openclaw-tts-router:8080")
# ホストから実行する場合は http://localhost:18081

def speak(text: str, purpose: str = "local_only", engine: str = None, speaker: str = None):
    """
    TTS Router に音声合成を依頼する。
    
    Args:
        text: 読み上げテキスト
        purpose: 用途 (factory_alert, iatf_training, customer_presentation, realtime_agent, local_only)
        engine: エンジン強制指定 (voicevox, fish_audio, stylebert, etc.)
        speaker: 話者 ID または名前 (VOICEVOXなら 3 等)
    """
    payload = {
        "text": text,
        "purpose": purpose,
        "engine": engine,
        "speaker": speaker
    }
    
    # 接続先決定 (Docker 内部 vs ホスト)
    url = f"{TTS_ROUTER_URL}/tts/speak"
    if "openclaw-tts-router" in url and os.name == "nt": # Windows ホストからの場合
        url = "http://localhost:18081/tts/speak"

    try:
        res = requests.post(url, json=payload, timeout=60)
        res.raise_for_status()
        data = res.json()
        print(f"[TTS] Generated: {data['file']} (Engine: {data['engine']}, Purpose: {data['purpose']})")
        return data
    except Exception as e:
        print(f"[TTS] Error: {e}", file=sys.stderr)
        return None

if __name__ == "__main__":
    if len(sys.argv) > 1:
        text = sys.argv[1]
        purpose = sys.argv[2] if len(sys.argv) > 2 else "local_only"
        speak(text, purpose=purpose)
    else:
        print("Usage: python tts_router_client.py \"Text to speak\" [purpose]")
