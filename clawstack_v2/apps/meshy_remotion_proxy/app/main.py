from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional, List
import os
import httpx

app = FastAPI(title="Meshy Remotion Proxy", version="0.1.0")

MESHY_API_KEY = os.getenv("MESHY_API_KEY", "")
MESHY_API_BASE = os.getenv("MESHY_API_BASE", "https://api.meshy.ai/openapi/v2")
MESHY_DRY_RUN = os.getenv("MESHY_DRY_RUN", "true").lower() == "true"

class TextTo3DRequest(BaseModel):
    prompt: str
    art_style: Optional[str] = "realistic"
    negative_prompt: Optional[str] = None
    should_remesh: Optional[bool] = True
    metadata_tags: Optional[List[str]] = None

@app.get("/health")
def health():
    return {
        "ok": True,
        "dry_run": MESHY_DRY_RUN,
        "api_base": MESHY_API_BASE,
        "api_key_set": bool(MESHY_API_KEY),
    }

@app.post("/meshy/text-to-3d")
async def create_text_to_3d(req: TextTo3DRequest):
    if MESHY_DRY_RUN:
        return {
            "dry_run": True,
            "message": "Dry run mode. No credits consumed.",
            "request": req.model_dump(),
            "suggested_asset_name": req.prompt[:40].replace(" ", "_")
        }

    if not MESHY_API_KEY:
        raise HTTPException(status_code=400, detail="MESHY_API_KEY is not set")

    headers = {
        "Authorization": f"Bearer {MESHY_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "mode": "preview",
        "prompt": req.prompt,
        "art_style": req.art_style,
        "negative_prompt": req.negative_prompt,
        "should_remesh": req.should_remesh,
    }

    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post(f"{MESHY_API_BASE}/text-to-3d", headers=headers, json=payload)
        resp.raise_for_status()
        return resp.json()

@app.get("/meshy/task/{task_id}")
async def get_task(task_id: str):
    if MESHY_DRY_RUN:
        return {
            "dry_run": True,
            "task_id": task_id,
            "status": "SUCCEEDED",
            "asset": {
                "preview_url": "/static/dummy-preview.png",
                "model_url": "/static/dummy.glb"
            }
        }

    if not MESHY_API_KEY:
        raise HTTPException(status_code=400, detail="MESHY_API_KEY is not set")

    headers = {
        "Authorization": f"Bearer {MESHY_API_KEY}",
    }
    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.get(f"{MESHY_API_BASE}/text-to-3d/{task_id}", headers=headers)
        resp.raise_for_status()
        return resp.json()
