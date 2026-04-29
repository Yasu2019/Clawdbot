from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Optional, List
import os
import httpx

app = FastAPI(title="Meshy Remotion Proxy", version="0.1.2")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

if os.path.exists("/data/meshy_assets"):
    app.mount("/assets", StaticFiles(directory="/data/meshy_assets"), name="assets")

MESHY_API_KEY = (os.getenv("Meshy_AI_Secret_Key") or os.getenv("MESHY_API_KEY") or "").strip()
MESHY_API_BASE = "https://api.meshy.ai/openapi/v2"

@app.get("/health")
def health():
    return {"ok": True, "api_key_set": bool(MESHY_API_KEY)}

@app.post("/meshy/image-to-3d")
async def create_image_to_3d(image_path: str):
    if not MESHY_API_KEY:
        raise HTTPException(status_code=400, detail="MESHY_API_KEY is not set")

    # ホスト側のパスをコンテナ内のパスに変換
    internal_path = image_path.replace("D:\\Clawdbot_Docker_20260125\\data\\meshy_assets", "/data/meshy_assets")
    if not os.path.exists(internal_path):
         raise HTTPException(status_code=404, detail=f"File not found: {internal_path}")

    headers = {"Authorization": f"Bearer {MESHY_API_KEY}"}
    files = {
        'image': (os.path.basename(internal_path), open(internal_path, 'rb'), 'image/png')
    }
    data = {
        'enable_pbr': 'true'
    }

    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post(f"{MESHY_API_BASE}/image-to-3d", headers=headers, files=files, data=data)
        return resp.json()

@app.get("/meshy/task/{task_id}")
async def get_task(task_id: str):
    headers = {"Authorization": f"Bearer {MESHY_API_KEY}"}
    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.get(f"{MESHY_API_BASE}/image-to-3d/{task_id}", headers=headers)
        return resp.json()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
