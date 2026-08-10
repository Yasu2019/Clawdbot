# -*- coding: utf-8 -*-
from __future__ import annotations
import json
import urllib.request
import urllib.error


def chat(base_url: str, model: str, prompt: str, timeout: int = 120) -> str:
    url = base_url.rstrip("/") + "/api/chat"
    payload = {
        "model": model,
        "stream": False,
        "messages": [
            {"role": "system", "content": "You are a cautious local AI systems architect. Return only valid JSON."},
            {"role": "user", "content": prompt},
        ],
        "options": {"temperature": 0.2}
    }
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json; charset=utf-8"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        body = json.loads(resp.read().decode("utf-8"))
    return body.get("message", {}).get("content", "")
