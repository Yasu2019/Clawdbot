from fastapi import FastAPI
from pydantic import BaseModel
import os, time

app = FastAPI(title="Corpus2Skill Navigator", version="0.1.0")

class QueryRequest(BaseModel):
    query: str
    domain: str = "general"
    require_evidence: bool = True

@app.get("/health")
def health():
    return {"status": "ok", "service": "navigator"}

@app.post("/navigate")
def navigate(req: QueryRequest):
    # Production implementation should load tree index and navigate branch/leaf nodes.
    return {
        "status": "partial",
        "answer": "Navigator scaffold is running. Connect corpus tree store and Qdrant hybrid search before production use.",
        "query": req.query,
        "domain": req.domain,
        "navigation_log": {
            "query": req.query,
            "steps": [
                {"step": 1, "node_id": "root", "action": "read", "reason": "initial overview"},
                {"step": 2, "node_id": "hybrid_search", "action": "compare", "reason": "tree store not yet connected"}
            ],
            "final_evidence": [],
            "answer_status": "partial"
        },
        "created_at": int(time.time())
    }
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=18922)
