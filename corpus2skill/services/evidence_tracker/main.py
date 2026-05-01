from fastapi import FastAPI
from pydantic import BaseModel
import hashlib, time

app = FastAPI(title="Corpus2Skill Evidence Tracker", version="0.1.0")

class EvidenceRequest(BaseModel):
    source_id: str
    source_name: str
    locator: str
    quote: str
    note: str = ""

@app.get("/health")
def health():
    return {"status": "ok", "service": "evidence_tracker"}

@app.post("/evidence")
def create_evidence(req: EvidenceRequest):
    h = hashlib.sha256((req.source_id + req.locator + req.quote).encode("utf-8", errors="ignore")).hexdigest()
    return {
        "evidence_id": f"ev-{h[:16]}",
        "source_id": req.source_id,
        "source_name": req.source_name,
        "locator": req.locator,
        "quote_hash": h,
        "note": req.note,
        "created_at": int(time.time())
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=18923)
