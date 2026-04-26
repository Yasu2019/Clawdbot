from fastapi import FastAPI
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path
import os
from generator import LPRequest, generate_lp, list_outputs
from rag_client import rag_suggest_context
from ai_client import ai_refine_brief

app = FastAPI(title="OpenClaw Auto LP Generator", version="1.0.0")
BASE_DIR = Path(__file__).resolve().parent
GENERATED_DIR = BASE_DIR / "generated"
STATIC_DIR = BASE_DIR / "static"
GENERATED_DIR.mkdir(exist_ok=True)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
app.mount("/generated", StaticFiles(directory=GENERATED_DIR), name="generated")

@app.get("/")
def root():
    return {"status":"running","service":"OpenClaw Auto LP Generator","mode":os.getenv("AI_MODE","local_template"),"ui":"/ui","outputs":"/outputs"}

@app.get("/health")
def health(): return {"ok": True}

@app.get("/ui", response_class=HTMLResponse)
def ui(): return HTMLResponse((STATIC_DIR / "ui.html").read_text(encoding="utf-8"))

@app.post("/api/generate")
def api_generate(req: LPRequest): return generate_lp(req)

@app.post("/api/suggest")
def api_suggest(payload: dict):
    theme = payload.get("theme", "")
    source_hint = payload.get("source_hint", "")
    rag_context = rag_suggest_context(theme, source_hint)
    refined = ai_refine_brief(theme, rag_context)
    return {"theme": theme, "rag_context": rag_context, "refined_brief": refined}

@app.get("/outputs")
def outputs(): return list_outputs()

@app.get("/download/{filename}")
def download(filename: str):
    target = GENERATED_DIR / filename
    if not target.exists(): return JSONResponse({"error":"file not found"}, status_code=404)
    return FileResponse(target, filename=filename)
