from fastapi import FastAPI
from pydantic import BaseModel
import os, requests

app = FastAPI(title="Corpus2Skill API Gateway", version="0.1.0")

class QueryRequest(BaseModel):
    query: str
    domain: str = "general"
    require_evidence: bool = True

@app.get("/health")
def health():
    return {"status": "ok", "service": "api_gateway"}

@app.post("/ask")
def ask(req: QueryRequest):
    nav_url = os.getenv("C2S_NAVIGATOR_URL", "http://corpus2skill-navigator:18922/navigate")
    try:
        r = requests.post(nav_url, json=req.model_dump(), timeout=60)
        return r.json()
    except Exception as e:
        return {"status": "error", "message": str(e), "fallback": "navigator unavailable"}
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=18920)
