"""
LiteLLM前段で使う観測圧縮アダプタ例。
OpenClaw Gateway側で LLMへ渡す terminal observation に対して呼び出します。
"""
import requests, os

def compress_observation(text: str, domain='terminal') -> str:
    url=os.getenv('TACO_ENGINE_URL','http://taco-engine:8765/compress')
    try:
        r=requests.post(url, json={'text': text, 'domain': domain}, timeout=10)
        r.raise_for_status()
        return r.json()['text']
    except Exception:
        # 障害時は絶対にログを失わない
        return text
