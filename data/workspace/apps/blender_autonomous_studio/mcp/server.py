"""
Minimal Blender MCP-like HTTP server skeleton.
Run outside Blender for planning; call Blender Python runner for execution.
Production integration should be reviewed by Codex before use.
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any, Dict

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

ROOT = Path(__file__).resolve().parents[1]
WORKSPACE = ROOT / "workspace"
REQUESTS = WORKSPACE / "requests"
EXPORTS = WORKSPACE / "exports"
BLENDER_SCRIPT = ROOT / "command_layer" / "blender_runner.py"

for p in [REQUESTS, EXPORTS]:
    p.mkdir(parents=True, exist_ok=True)

app = FastAPI(title="OpenClaw Blender MCP Server", version="0.1.0")


class CommandRequest(BaseModel):
    scene_name: str = "scene"
    dry_run: bool = True
    commands: list[Dict[str, Any]]


@app.get("/health")
def health() -> Dict[str, str]:
    return {"status": "ok", "service": "openclaw-blender-mcp"}


@app.post("/execute")
def execute(req: CommandRequest) -> Dict[str, Any]:
    payload = req.model_dump()
    safe_name = "".join(c for c in req.scene_name if c.isalnum() or c in "-_")[:80] or "scene"
    request_path = REQUESTS / f"{safe_name}.json"
    request_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    if req.dry_run:
        return {"status": "dry_run", "request_path": str(request_path), "command_count": len(req.commands)}

    # Adjust blender executable path for Windows/K10 environment if needed.
    blender_exe = "blender"
    cmd = [blender_exe, "--background", "--python", str(BLENDER_SCRIPT), "--", str(request_path)]
    try:
        completed = subprocess.run(cmd, capture_output=True, text=True, timeout=300, check=False)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=500, detail="Blender executable not found. Set blender path.") from exc

    return {
        "status": "completed" if completed.returncode == 0 else "failed",
        "returncode": completed.returncode,
        "stdout_tail": completed.stdout[-4000:],
        "stderr_tail": completed.stderr[-4000:],
    }
