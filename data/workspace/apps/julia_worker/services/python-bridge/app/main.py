import os
from typing import Any, Dict

import httpx
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

JULIA_WORKER_URL = os.getenv("JULIA_WORKER_URL", "http://localhost:8096").rstrip("/")

app = FastAPI(
    title="Clawstack Julia Python Bridge",
    version="2026.04.29-regenerated",
    description="Python側/OpenClaw側からJulia Numerical Workerを安全に呼び出すための薄いBridgeです。",
)


class LevelerInput(BaseModel):
    thickness_mm: float = Field(0.8, gt=0)
    yield_mpa: float = Field(85.0, gt=0)
    roller_diameter_mm: float = Field(12.0, gt=0)
    pitch_mm: float = Field(16.0, gt=0)
    entry_gap_mm: float = Field(0.7, gt=0)
    exit_gap_mm: float = Field(1.1, gt=0)
    stages: int = Field(11, ge=1, le=99)
    friction: float = Field(0.05, ge=0, le=1)


class DOEInput(BaseModel):
    n: int = Field(10, ge=1, le=500)
    seed: int = 42
    variables: Dict[str, list[float]]


@app.get("/health")
async def health() -> Dict[str, Any]:
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            r = await client.get(f"{JULIA_WORKER_URL}/health")
            r.raise_for_status()
            julia = r.json()
        except Exception as exc:
            julia = {"ok": False, "error": str(exc)}
    return {
        "ok": True,
        "service": "clawstack-julia-python-bridge",
        "julia_worker_url": JULIA_WORKER_URL,
        "julia": julia,
    }


@app.post("/leveler/estimate")
async def leveler_estimate(data: LevelerInput) -> Dict[str, Any]:
    return await post_to_julia("/leveler/estimate", data.model_dump())


@app.post("/doe/latin_hypercube")
async def doe_latin_hypercube(data: DOEInput) -> Dict[str, Any]:
    return await post_to_julia("/doe/latin_hypercube", data.model_dump())


@app.post("/optimize/leveler_grid")
async def optimize_leveler_grid(payload: Dict[str, Any]) -> Dict[str, Any]:
    return await post_to_julia("/optimize/leveler_grid", payload)


async def post_to_julia(path: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            r = await client.post(f"{JULIA_WORKER_URL}{path}", json=payload)
            r.raise_for_status()
            return r.json()
        except httpx.HTTPStatusError as exc:
            raise HTTPException(status_code=exc.response.status_code, detail=exc.response.text)
        except Exception as exc:
            raise HTTPException(status_code=502, detail=f"Julia worker call failed: {exc}")
