from fastapi import FastAPI
from pydantic import BaseModel
from typing import List, Dict, Any

app = FastAPI(title="Tool Anomaly Guard")

DANGEROUS_WORDS = ["delete", "drop", "truncate", "format", "全削除", "初期化", "破棄"]

class CheckRequest(BaseModel):
    text: str
    candidates: List[Dict[str, Any]]
    state: Dict[str, Any] = {}

@app.post("/check")
def check(req: CheckRequest):
    text_lower = req.text.lower()
    danger_intent = any(w in text_lower for w in DANGEROUS_WORDS)
    allowed = []
    blocked = []
    for c in req.candidates:
        risk = c.get("risk", "read")
        if risk in ["write", "dangerous"] and not req.state.get("human_approved", False):
            blocked.append({**c, "reason": "human approval required"})
            continue
        if danger_intent and risk != "read" and not req.state.get("maintenance_mode", False):
            blocked.append({**c, "reason": "dangerous intent outside maintenance mode"})
            continue
        allowed.append(c)
    return {"allowed": allowed, "blocked": blocked}
