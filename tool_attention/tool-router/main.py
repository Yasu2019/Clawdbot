import os
import requests
from typing import Dict, Any, List
from fastapi import FastAPI
from pydantic import BaseModel
from qdrant_client import QdrantClient
from sentence_transformers import SentenceTransformer

QDRANT_HOST = os.getenv("QDRANT_HOST", "qdrant")
QDRANT_PORT = int(os.getenv("QDRANT_PORT", "6333"))
COLLECTION = os.getenv("COLLECTION_NAME", "tool_registry")
LEARNING_URL = os.getenv("LEARNING_URL", "http://learning-store:8092")
ANOMALY_URL = os.getenv("ANOMALY_URL", "http://anomaly-guard:8093")

app = FastAPI(title="Clawstack Tool Attention Router")
client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)
model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")

class RouteRequest(BaseModel):
    text: str
    state: Dict[str, Any] = {}
    limit: int = 10

class FeedbackRequest(BaseModel):
    tool: str
    success: bool
    latency_ms: int = 0
    error: str | None = None
    task_type: str | None = None


def state_gate(tool: Dict[str, Any], state: Dict[str, Any]) -> bool:
    requires = tool.get("requires", []) or []
    for req in requires:
        if not state.get(req, False):
            return False
    if tool.get("risk") == "write" and not state.get("write_allowed", False):
        return False
    if tool.get("risk") == "dangerous" and not state.get("human_approved", False):
        return False
    return True


def learning_multiplier(tool_name: str) -> float:
    try:
        r = requests.get(f"{LEARNING_URL}/score/{tool_name}", timeout=1.5)
        if r.ok:
            return float(r.json().get("multiplier", 1.0))
    except Exception:
        pass
    return 1.0


def anomaly_filter(candidates: List[Dict[str, Any]], text: str, state: Dict[str, Any]) -> List[Dict[str, Any]]:
    try:
        r = requests.post(f"{ANOMALY_URL}/check", json={"text": text, "candidates": candidates, "state": state}, timeout=2.0)
        if r.ok:
            return r.json().get("allowed", candidates)
    except Exception:
        pass
    return candidates

@app.post("/route")
def route(req: RouteRequest):
    vector = model.encode(req.text).tolist()
    hits = client.search(collection_name=COLLECTION, query_vector=vector, limit=max(req.limit * 3, 20))
    candidates = []
    for h in hits:
        payload = h.payload or {}
        if not state_gate(payload, req.state):
            continue
        base = float(h.score)
        mult = learning_multiplier(payload.get("name", ""))
        candidates.append({
            "name": payload.get("name"),
            "summary": payload.get("summary"),
            "risk": payload.get("risk", "read"),
            "requires": payload.get("requires", []),
            "base_score": base,
            "learning_multiplier": mult,
            "final_score": base * mult,
        })
    candidates.sort(key=lambda x: x["final_score"], reverse=True)
    allowed = anomaly_filter(candidates[:req.limit], req.text, req.state)
    return {"selected": allowed, "count": len(allowed), "strategy": "iso + state_gating + outcome_learning + anomaly_guard"}

@app.post("/feedback")
def feedback(req: FeedbackRequest):
    try:
        r = requests.post(f"{LEARNING_URL}/feedback", json=req.model_dump(), timeout=2.0)
        return r.json()
    except Exception as e:
        return {"ok": False, "error": str(e)}
