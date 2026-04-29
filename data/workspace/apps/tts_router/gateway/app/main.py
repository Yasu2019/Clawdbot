from __future__ import annotations

import hashlib
import os
import time
from pathlib import Path
from typing import Literal

import requests
import yaml
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

OUTPUT_DIR = Path(os.getenv("TTS_OUTPUT_DIR", "/app/outputs"))
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
CONFIG_PATH = Path("/app/config/tts_routes.yaml")

app = FastAPI(title="OpenClaw TTS Router", version="1.0.0")


class SpeakRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=5000)
    purpose: str = "local_only"
    engine: str | None = None
    speaker: str | None = None
    speed: float = 1.0
    review_approved: bool = False


class SpeakResponse(BaseModel):
    ok: bool
    engine: str
    purpose: str
    file: str
    url: str
    warning: str | None = None


def load_routes() -> dict:
    if CONFIG_PATH.exists():
        return yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))
    return {"routes": {}, "fallback": {"engine": "voicevox"}}


def choose_engine(req: SpeakRequest, routes: dict) -> tuple[str, str | None]:
    if req.engine:
        return req.engine, None
    route = routes.get("routes", {}).get(req.purpose, {})
    allow_cloud = os.getenv("ALLOW_CLOUD_TTS", "false").lower() == "true"
    require_review = bool(route.get("require_review")) or os.getenv("REQUIRE_REVIEW_FOR_EXTERNAL", "true").lower() == "true"
    for candidate in route.get("preferred", []):
        cloud = candidate in {"fish_audio", "gemini"}
        if cloud and not allow_cloud:
            continue
        if cloud and require_review and not req.review_approved:
            continue
        return candidate, None
    fallback = routes.get("fallback", {}).get("engine", "voicevox")
    return fallback, "cloud_disabled_or_review_required"


def save_placeholder_wav(text: str, engine: str) -> Path:
    # 最小限のスタブ。実運用では各TTS APIの音声バイナリで置き換える。
    token = hashlib.sha256(f"{time.time()}:{engine}:{text}".encode("utf-8")).hexdigest()[:16]
    path = OUTPUT_DIR / f"tts_{engine}_{token}.txt"
    path.write_text(f"ENGINE={engine}\nTEXT={text}\n", encoding="utf-8")
    return path


def call_voicevox(req: SpeakRequest) -> Path:
    base = os.getenv("VOICEVOX_BASE_URL", "http://host.docker.internal:50021")
    speaker = int(req.speaker or 3)
    try:
        q = requests.post(f"{base}/audio_query", params={"text": req.text, "speaker": speaker}, timeout=10)
        q.raise_for_status()
        s = requests.post(f"{base}/synthesis", params={"speaker": speaker}, json=q.json(), timeout=60)
        s.raise_for_status()
        token = hashlib.sha256(f"{time.time()}:{req.text}".encode("utf-8")).hexdigest()[:16]
        path = OUTPUT_DIR / f"voicevox_{token}.wav"
        path.write_bytes(s.content)
        return path
    except Exception:
        return save_placeholder_wav(req.text, "voicevox_stub")


def synthesize(req: SpeakRequest, engine: str) -> Path:
    if engine == "voicevox":
        return call_voicevox(req)
    # 実装接続点: stylebert, gpt_sovits, fish_audio, gemini, irodori, miotts
    return save_placeholder_wav(req.text, engine)


@app.get("/health")
def health():
    return {"ok": True, "service": "openclaw-tts-router"}


@app.post("/tts/speak", response_model=SpeakResponse)
def speak(req: SpeakRequest):
    routes = load_routes()
    engine, warning = choose_engine(req, routes)
    path = synthesize(req, engine)
    return SpeakResponse(
        ok=True,
        engine=engine,
        purpose=req.purpose,
        file=path.name,
        url=f"/tts/audio/{path.name}",
        warning=warning,
    )


@app.get("/tts/audio/{filename}")
def audio(filename: str):
    path = OUTPUT_DIR / filename
    if not path.exists():
        raise HTTPException(status_code=404, detail="file not found")
    return FileResponse(path)
