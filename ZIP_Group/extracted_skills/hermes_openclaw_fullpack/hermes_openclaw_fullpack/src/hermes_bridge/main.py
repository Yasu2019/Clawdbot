from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from src.safety_harness.command_guard import validate_command
from src.qa_memory.memory_store import MemoryStore

app = FastAPI(title="Hermes OpenClaw Bridge", version="0.1.0")
memory = MemoryStore()

class CommandRequest(BaseModel):
    command: str = Field(..., description="Command proposed by Hermes/OpenClaw")
    reason: str = Field(default="", description="Why the command is needed")

class MemoryRequest(BaseModel):
    category: str
    title: str
    body: str
    source: str = "manual"

@app.get("/health")
def health():
    return {"status": "ok", "service": "hermes-openclaw-bridge"}

@app.post("/guard/check-command")
def check_command(req: CommandRequest):
    result = validate_command(req.command)
    return result

@app.post("/memory/add")
def add_memory(req: MemoryRequest):
    try:
        item = memory.add(req.category, req.title, req.body, req.source)
        return {"ok": True, "item": item}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

@app.get("/memory/search")
def search_memory(q: str, limit: int = 10):
    return {"items": memory.search(q, limit=limit)}
