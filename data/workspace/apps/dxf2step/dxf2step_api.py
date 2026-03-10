import os
import uuid
import shutil
import threading
import subprocess
from fastapi import FastAPI, UploadFile, File, Form, BackgroundTasks, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
from fastapi.responses import FileResponse, Response
import ezdxf
from ezdxf.addons.drawing import RenderContext, Frontend
from ezdxf.addons.drawing.matplotlib import MatplotlibBackend
import matplotlib.pyplot as plt
import io

app = FastAPI(title="Antigravity DXF2STEP API")

@app.get("/")
def read_root():
    return FileResponse(os.path.join(BASE_DIR, "index.html"))

# --- Configuration ---
BASE_DIR = r"D:\Clawdbot_Docker_20260125\data\workspace\apps\dxf2step"
JOBS_DIR = os.path.join(BASE_DIR, "jobs")
WORKER_SCRIPT = os.path.join(BASE_DIR, "dxf2step_worker.py")

os.makedirs(JOBS_DIR, exist_ok=True)

class JobStatus(BaseModel):
    job_id: str
    state: str
    progress: float
    current: str
    warnings: List[str] = []

# In-memory job state for prototype (should be persistent for production)
jobs_db = {}

def run_conversion(job_id: str, input_path: str, output_dir: str, thickness: float, layer_configs: str = "{}", manual_mode: bool = False, view_assignments: str = "[]"):
    jobs_db[job_id]["state"] = "running"
    jobs_db[job_id]["current"] = "Starting conversion..."

    # -u = unbuffered stdout so print() lines arrive immediately
    cmd = [
        "python", "-u", WORKER_SCRIPT,
        "--input", input_path,
        "--output", output_dir,
        "--thickness", str(thickness),
        "--layer-configs", layer_configs
    ]

    if manual_mode:
        cmd += ["--manual-mode", "--view-assignments", view_assignments]

    n_layers = 0
    layers_started = 0

    try:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,   # merge stderr into stdout stream
            text=True,
            bufsize=1                   # line-buffered
        )

        for raw_line in proc.stdout:
            line = raw_line.rstrip()
            if not line:
                continue

            # Always surface the latest line to the UI
            jobs_db[job_id]["current"] = line

            # ── Progress heuristics ──────────────────────────────────────
            if line.startswith("[DXF loaded]"):
                # "[DXF loaded] 3 layers: View, ProjItem, ..."
                try:
                    n_layers = int(line.split()[2])
                except Exception:
                    n_layers = 1
                jobs_db[job_id]["progress"] = 0.05

            elif line.startswith("[Layer "):
                # "[Layer 2/3] ProjItem — thickness 10.0mm"
                layers_started += 1
                base = 0.05 + (layers_started - 1) / max(n_layers, 1) * 0.65
                jobs_db[job_id]["progress"] = round(base, 2)

            elif line.startswith("[FreeCAD] STEP generation"):
                # bump slightly inside the layer slot
                jobs_db[job_id]["progress"] = round(
                    jobs_db[job_id]["progress"] + 0.04, 2)

            elif line.startswith("[FreeCAD] STEP done"):
                jobs_db[job_id]["progress"] = round(
                    jobs_db[job_id]["progress"] + 0.04, 2)

            elif "reconstruction starting" in line.lower():
                jobs_db[job_id]["progress"] = 0.78
                jobs_db[job_id]["current"] = "3D reconstruction — intersecting front/top/right slabs ..."

            elif line.startswith("[FreeCAD] Running multi-view"):
                jobs_db[job_id]["progress"] = 0.82

            elif line.startswith("[FreeCAD] Reconstruction STEP done"):
                jobs_db[job_id]["progress"] = 0.92

            elif "Combined STEP generated" in line:
                jobs_db[job_id]["progress"] = 0.95

        proc.wait()

        if proc.returncode == 0:
            jobs_db[job_id]["state"] = "done"
            jobs_db[job_id]["progress"] = 1.0
            jobs_db[job_id]["current"] = "Conversion complete."
        else:
            jobs_db[job_id]["state"] = "failed"
            # current already holds the last stdout line (likely an error message)

    except Exception as e:
        jobs_db[job_id]["state"] = "failed"
        jobs_db[job_id]["current"] = f"Runtime Error: {str(e)}"

@app.get("/api/dxf2step/health")
def healthcheck():
    # Attempt to check FreeCADCmd via docker
    try:
        cmd = ["docker", "exec", "clawstack-unified-clawdbot-gateway-1", "FreeCADCmd", "--version"]
        res = subprocess.run(cmd, capture_output=True, text=True)
        fc_version = res.stdout.strip() if res.returncode == 0 else "Not Found"
    except:
        fc_version = "Check Failed"

    return {
        "status": "ok",
        "engine": {
            "mode": "docker-gateway-exec",
            "freecadcmd": fc_version,
            "python": "3.12"
        }
    }

@app.post("/api/dxf2step/jobs")
async def create_job(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    default_thickness_mm: float = Form(10.0),
    layer_configs: str = Form("{}"),
    manual_mode: bool = Form(False),
    view_assignments: str = Form("[]"),
):
    job_id = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
    job_dir = os.path.join(JOBS_DIR, job_id)
    input_dir = os.path.join(job_dir, "input")
    output_dir = os.path.join(job_dir, "output")
    
    os.makedirs(input_dir, exist_ok=True)
    os.makedirs(output_dir, exist_ok=True)
    
    input_path = os.path.join(input_dir, file.filename)
    with open(input_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    jobs_db[job_id] = {
        "job_id": job_id,
        "state": "pending",
        "progress": 0.0,
        "current": "Job received.",
        "warnings": []
    }
    
    background_tasks.add_task(run_conversion, job_id, input_path, output_dir, default_thickness_mm, layer_configs, manual_mode, view_assignments)
    
    return {"job_id": job_id}

@app.post("/api/dxf2step/scan-layers")
async def scan_layers(file: UploadFile = File(...)):
    """Extract layer names and suggested thicknesses from DXF."""
    import ezdxf
    import re
    
    # Temporary save
    temp_id = uuid.uuid4().hex
    temp_path = os.path.join(JOBS_DIR, f"temp_{temp_id}.dxf")
    with open(temp_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    try:
        doc = ezdxf.readfile(temp_path)
        layers = []
        for layer in doc.layers:
            name = layer.dxf.name
            # Suggest thickness
            thickness = 10.0
            match = re.search(r'([0-9]*\.?[0-9]+)\s*mm', name, re.IGNORECASE)
            if match: thickness = float(match.group(1))
            else:
                match = re.search(r'T\s*([0-9]*\.?[0-9]+)', name, re.IGNORECASE)
                if match: thickness = float(match.group(1))
                
            layers.append({"name": name, "suggested_thickness": thickness})
        return {"layers": layers}
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)

@app.get("/api/dxf2step/jobs/{job_id}", response_model=JobStatus)
def get_job_status(job_id: str):
    if job_id not in jobs_db:
        raise HTTPException(status_code=404, detail="Job not found")
    return jobs_db[job_id]

@app.get("/api/dxf2step/jobs/{job_id}/outputs")
def list_outputs(job_id: str):
    output_dir = os.path.join(JOBS_DIR, job_id, "output")
    if not os.path.exists(output_dir):
        raise HTTPException(status_code=404, detail="Outputs not found")
        
    # Only expose the combined 3D model and its preview image.
    # Per-layer STEP files are 2D extrusions only — not useful to the user.
    ALLOWED = {
        "combined.step":       "step",
        "combined_views.png":  "png",
    }

    outputs = []
    for f in os.listdir(output_dir):
        if f in ALLOWED:
            outputs.append({
                "type": ALLOWED[f],
                "name": f,
                "url": f"/api/dxf2step/jobs/{job_id}/download/{f}"
            })

    # Sort: STEP first, PNG second
    outputs.sort(key=lambda o: o["type"])
    return {"outputs": outputs}

@app.get("/api/dxf2step/jobs/{job_id}/download/{filename}")
def download_output(job_id: str, filename: str):
    file_path = os.path.join(JOBS_DIR, job_id, "output", filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(file_path)

@app.get("/api/dxf2step/preview-svg/{job_id}")
async def get_preview_svg(job_id: str):
    """Generate SVG preview for initial DXF."""
    input_dir = os.path.join(JOBS_DIR, job_id, "input")
    if not os.path.exists(input_dir):
        raise HTTPException(status_code=404, detail="Job directory not found")
        
    files = [f for f in os.listdir(input_dir) if f.lower().endswith('.dxf')]
    if not files:
        raise HTTPException(status_code=404, detail="DXF not found")
        
    dxf_path = os.path.join(input_dir, files[0])
    doc = ezdxf.readfile(dxf_path)
    msp = doc.modelspace()
    
    # Render to SVG using ezdxf.addons.drawing
    from ezdxf.addons.drawing import RenderContext, Frontend
    from ezdxf.addons.drawing.svg import SVGBackend
    
    out = io.StringIO()
    ctx = RenderContext(doc)
    backend = SVGBackend()
    Frontend(ctx, backend).draw_layout(msp)
    svg_str = backend.get_xml()
    
    return Response(content=svg_str, media_type="image/svg+xml")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8002)
