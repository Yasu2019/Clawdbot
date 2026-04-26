from __future__ import annotations

import os
import re
import json
import uuid
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, PlainTextResponse
from pydantic import BaseModel, Field

APP_NAME = "OpenClaw SPICE Lab"
WORKDIR = Path(os.getenv("SPICE_LAB_WORKDIR", "/work"))
MAX_NETLIST_BYTES = int(os.getenv("SPICE_LAB_MAX_NETLIST_BYTES", "200000"))
TIMEOUT_SEC = int(os.getenv("SPICE_LAB_TIMEOUT_SEC", "60"))
RUNS = WORKDIR / "runs"
REPORTS = WORKDIR / "reports"
RUNS.mkdir(parents=True, exist_ok=True)
REPORTS.mkdir(parents=True, exist_ok=True)

app = FastAPI(title=APP_NAME, version="2026-04-26-v1")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:8088", "http://localhost:8088",
        "http://127.0.0.1:8765", "http://localhost:8765",
    ],
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

class SimRequest(BaseModel):
    name: str = Field(default="unnamed", max_length=80)
    netlist: str = Field(..., description="SPICE netlist text")
    timeout_sec: int | None = Field(default=None, ge=1, le=600)
    keep_files: bool = True

class SimResponse(BaseModel):
    run_id: str
    name: str
    ok: bool
    exit_code: int | None
    elapsed_sec: float
    files: dict[str, str]
    measurements: dict[str, Any]
    log_tail: str
    warnings: list[str]

class ExampleResponse(BaseModel):
    name: str
    netlist: str


def _safe_name(name: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", name.strip())[:80] or "unnamed"


def _parse_meas(log_text: str) -> dict[str, Any]:
    """Parse common .meas output lines from ngspice/LTspice style logs."""
    out: dict[str, Any] = {}
    # Examples: vmax_out = 4.999 at=...
    for line in log_text.splitlines():
        m = re.match(r"\s*([A-Za-z_][\w.$-]*)\s*=\s*([-+]?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?)\b(.*)$", line)
        if m:
            key, val, rest = m.groups()
            try:
                out[key] = {"value": float(val), "raw": line.strip(), "extra": rest.strip()}
            except ValueError:
                pass
    return out


def _tail(text: str, max_chars: int = 6000) -> str:
    if len(text) <= max_chars:
        return text
    return text[-max_chars:]


@app.get("/")
def root() -> dict[str, Any]:
    return {
        "name": APP_NAME,
        "usage": "POST /simulate with {name, netlist}",
        "examples": ["/examples/rc_lowpass", "/examples/divider_tolerance"],
        "health": "/health",
    }


@app.get("/health")
def health() -> dict[str, Any]:
    ng = shutil.which("ngspice")
    version = None
    if ng:
        try:
            p = subprocess.run([ng, "-v"], capture_output=True, text=True, timeout=5)
            version = (p.stdout + p.stderr).strip().splitlines()[0:3]
        except Exception as exc:  # pragma: no cover
            version = [f"version check failed: {exc}"]
    return {"ok": bool(ng), "ngspice": ng, "version": version, "workdir": str(WORKDIR)}


@app.get("/examples/{example_name}", response_model=ExampleResponse)
def example(example_name: str) -> ExampleResponse:
    examples_dir = Path("/app/examples")
    mapping = {
        "rc_lowpass": examples_dir / "rc_lowpass_ngspice.cir",
        "divider_tolerance": examples_dir / "divider_tolerance_sweep.cir",
        "sensor_input_filter": examples_dir / "sensor_input_filter.cir",
    }
    if example_name not in mapping:
        raise HTTPException(status_code=404, detail=f"Unknown example: {example_name}")
    return ExampleResponse(name=example_name, netlist=mapping[example_name].read_text(encoding="utf-8"))


@app.post("/simulate", response_model=SimResponse)
def simulate(req: SimRequest) -> SimResponse:
    netlist_bytes = req.netlist.encode("utf-8")
    if len(netlist_bytes) > MAX_NETLIST_BYTES:
        raise HTTPException(status_code=413, detail=f"Netlist too large: {len(netlist_bytes)} bytes")
    if ".shell" in req.netlist.lower() or "shell" in req.netlist.lower():
        raise HTTPException(status_code=400, detail="Shell commands are blocked in netlists")

    ng = shutil.which("ngspice")
    if not ng:
        raise HTTPException(status_code=500, detail="ngspice not found")

    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "_" + uuid.uuid4().hex[:8]
    safe = _safe_name(req.name)
    run_dir = RUNS / f"{run_id}_{safe}"
    run_dir.mkdir(parents=True, exist_ok=True)
    cir = run_dir / "input.cir"
    log = run_dir / "run.log"
    meta = run_dir / "metadata.json"
    cir.write_text(req.netlist, encoding="utf-8")

    timeout = min(req.timeout_sec or TIMEOUT_SEC, 600)
    start = datetime.now(timezone.utc)
    warnings: list[str] = []
    exit_code: int | None = None
    try:
        p = subprocess.run(
            [ng, "-b", "-o", str(log), str(cir)],
            cwd=str(run_dir),
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        exit_code = p.returncode
        if p.stdout.strip():
            (run_dir / "stdout.txt").write_text(p.stdout, encoding="utf-8")
        if p.stderr.strip():
            (run_dir / "stderr.txt").write_text(p.stderr, encoding="utf-8")
    except subprocess.TimeoutExpired:
        warnings.append(f"Simulation timed out after {timeout} sec")
        exit_code = None

    elapsed = (datetime.now(timezone.utc) - start).total_seconds()
    log_text = log.read_text(encoding="utf-8", errors="replace") if log.exists() else ""
    measurements = _parse_meas(log_text)
    files = {p.name: str(p) for p in run_dir.iterdir() if p.is_file()}
    metadata = {
        "run_id": run_id,
        "name": req.name,
        "created_at_utc": start.isoformat(),
        "elapsed_sec": elapsed,
        "exit_code": exit_code,
        "files": files,
        "measurements": measurements,
        "warnings": warnings,
    }
    meta.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
    files["metadata.json"] = str(meta)

    return SimResponse(
        run_id=run_id,
        name=req.name,
        ok=(exit_code == 0 and not warnings),
        exit_code=exit_code,
        elapsed_sec=elapsed,
        files=files,
        measurements=measurements,
        log_tail=_tail(log_text),
        warnings=warnings,
    )


@app.get("/runs/{run_id}/file/{filename}")
def get_run_file(run_id: str, filename: str):
    # Resolve run directory by prefix. Avoid exposing arbitrary paths.
    candidates = [p for p in RUNS.iterdir() if p.is_dir() and p.name.startswith(run_id)]
    if not candidates:
        raise HTTPException(status_code=404, detail="run not found")
    target = (candidates[0] / filename).resolve()
    if candidates[0].resolve() not in target.parents and target != candidates[0].resolve():
        raise HTTPException(status_code=400, detail="invalid path")
    if not target.exists() or not target.is_file():
        raise HTTPException(status_code=404, detail="file not found")
    return FileResponse(str(target))


@app.get("/runs/{run_id}/log", response_class=PlainTextResponse)
def get_run_log(run_id: str) -> str:
    candidates = [p for p in RUNS.iterdir() if p.is_dir() and p.name.startswith(run_id)]
    if not candidates:
        raise HTTPException(status_code=404, detail="run not found")
    log = candidates[0] / "run.log"
    return log.read_text(encoding="utf-8", errors="replace") if log.exists() else ""
