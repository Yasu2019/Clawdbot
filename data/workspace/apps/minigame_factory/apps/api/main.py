from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import os, json, uuid
from redis import Redis
from rq import Queue
from jsonschema import validate, ValidationError

REDIS_URL = os.environ["REDIS_URL"]
PROJECTS_DIR = os.environ["PROJECTS_DIR"]
OUTPUT_DIR = os.environ["OUTPUT_DIR"]
SCHEMA_PATH = os.environ["SCHEMA_PATH"]

redis_conn = Redis.from_url(REDIS_URL)
q = Queue("build", connection=redis_conn)

app = FastAPI(title="MiniGame Factory API", version="1.1")

with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
    SCHEMA = json.load(f)

class SpecIn(BaseModel):
    spec: dict

def _project_path(project_id: str) -> str:
    return os.path.join(PROJECTS_DIR, project_id)

@app.get("/health")
def health():
    return {"ok": True}

@app.post("/projects")
def create_project():
    project_id = uuid.uuid4().hex
    os.makedirs(_project_path(project_id), exist_ok=True)
    os.makedirs(os.path.join(OUTPUT_DIR, project_id), exist_ok=True)
    return {"project_id": project_id}

@app.post("/projects/{project_id}/spec")
def set_spec(project_id: str, body: SpecIn):
    pdir = _project_path(project_id)
    if not os.path.isdir(pdir):
        raise HTTPException(404, "project not found")

    spec = body.spec
    try:
        validate(instance=spec, schema=SCHEMA)
    except ValidationError as e:
        raise HTTPException(400, {"schema_error": e.message})

    with open(os.path.join(pdir, "game_spec.json"), "w", encoding="utf-8") as f:
        json.dump(spec, f, ensure_ascii=False, indent=2)

    job = q.enqueue("tasks.build_project", project_id)
    return {"enqueued": True, "job_id": job.id}

@app.get("/projects/{project_id}")
def get_project(project_id: str):
    pdir = _project_path(project_id)
    if not os.path.isdir(pdir):
        raise HTTPException(404, "project not found")

    outdir = os.path.join(OUTPUT_DIR, project_id)
    artifacts = []
    for root, _, files in os.walk(outdir):
        for fn in files:
            artifacts.append(os.path.relpath(os.path.join(root, fn), outdir))

    status = "succeeded" if artifacts else "pending"
    return {"project_id": project_id, "status": status, "artifacts": sorted(artifacts)}

@app.get("/jobs/{job_id}")
def get_job(job_id: str):
    # lightweight: fetch via redis if needed later; v1.1 keeps it simple
    return {"job_id": job_id, "note": "Use RQ dashboard/logs or extend this endpoint in v1.2."}
