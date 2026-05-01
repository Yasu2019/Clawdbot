from fastapi import FastAPI
from pydantic import BaseModel
import hashlib, time

app = FastAPI(title="Corpus2Skill Tree Builder", version="0.1.0")

class BuildRequest(BaseModel):
    source_id: str
    source_name: str
    text: str
    domain: str = "general"

@app.get("/health")
def health():
    return {"status": "ok", "service": "tree_builder"}

@app.post("/build_tree")
def build_tree(req: BuildRequest):
    # Minimal safe template. Replace summarizer with local Ollama in production.
    text_hash = hashlib.sha256(req.text.encode("utf-8", errors="ignore")).hexdigest()
    root_id = f"{req.domain}:{req.source_id}:root"
    return {
        "tree_id": f"tree-{text_hash[:12]}",
        "created_at": int(time.time()),
        "root": {
            "node_id": root_id,
            "parent_id": None,
            "node_type": "root",
            "domain": req.domain,
            "title": req.source_name,
            "summary": req.text[:500],
            "keywords": [],
            "source_refs": [{"source_id": req.source_id, "source_name": req.source_name, "locator": "full_text", "text_hash": text_hash}],
            "children": [],
            "confidence": 0.5,
            "human_verified": False
        }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=18921)
