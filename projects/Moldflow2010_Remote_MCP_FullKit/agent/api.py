from __future__ import annotations
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import sqlite3
import argparse, threading, traceback
from pathlib import Path
from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel
import uvicorn

from .config import load_config, AgentConfig
from .security import verify_token, safe_resolve, SecurityError
from .audit import write_audit
from .discovery import discover
from .moldflow_cli import run_study, export_log, modify_study
from .job_store import JobStore
from .process_runner import run_process

VBS_DIR = Path(__file__).resolve().parents[1] / "moldflow" / "vbs"

class StudyRequest(BaseModel):
    study_path: str

class ExportLogRequest(BaseModel):
    study_path: str
    output_path: str

class ModifyRequest(BaseModel):
    source_path: str
    target_path: str
    modifier_xml_path: str

class CreateTestStudyRequest(BaseModel):
    source_path: str
    project_dir: str
    project_name: str
    study_name: str
    confirm_create: bool = False

class ImportCurrentStudyRequest(BaseModel):
    source_path: str
    confirm_import: bool = False

class MaterialSearchRequest(BaseModel):
    query: str | None = None
    vendor: str | None = None
    source_kind: str | None = None
    extension: str | None = None
    limit: int = 20

class MaterialSelectRequest(BaseModel):
    query: str
    vendor: str | None = None
    source_kind: str | None = None
    limit: int = 10

def _material_db_path(cfg: AgentConfig):
    return cfg.material_db_path or (cfg.workspace_root / "moldflow_materials.db")

def _material_rows(cfg: AgentConfig, req: MaterialSearchRequest):
    db_path = _material_db_path(cfg)
    if not db_path.exists():
        raise HTTPException(404, f"Material DB not found: {db_path}")
    limit = max(1, min(int(req.limit or 20), 100))
    clauses = []
    params: list[object] = []
    if req.query:
        clauses.append("(vendor LIKE ? OR file_name LIKE ? OR relative_path LIKE ?)")
        like = f"%{req.query}%"
        params.extend([like, like, like])
    if req.vendor:
        clauses.append("vendor LIKE ?")
        params.append(f"%{req.vendor}%")
    if req.source_kind:
        clauses.append("source_kind = ?")
        params.append(req.source_kind)
    if req.extension:
        clauses.append("extension = ?")
        params.append(req.extension.lstrip(".").lower())
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    sql = f"""
        SELECT source_path, relative_path, file_name, source_kind, vendor, version_tag,
               extension, size_bytes, sha256, modified_utc, imported_utc
        FROM moldflow_material_files
        {where}
        ORDER BY vendor COLLATE NOCASE, file_name COLLATE NOCASE
        LIMIT ?
    """
    params.append(limit)
    con = sqlite3.connect(str(db_path))
    con.row_factory = sqlite3.Row
    try:
        rows = con.execute(sql, params).fetchall()
        total = con.execute(
            f"SELECT COUNT(*) FROM moldflow_material_files {where}",
            params[:-1],
        ).fetchone()[0]
        return {
            "db_path": str(db_path),
            "total": int(total),
            "limit": limit,
            "items": [dict(row) for row in rows],
        }
    finally:
        con.close()

def _score_material(item: dict, query: str) -> tuple[int, str]:
    q = query.strip().lower()
    vendor = str(item.get("vendor", "")).lower()
    file_name = str(item.get("file_name", "")).lower()
    relative_path = str(item.get("relative_path", "")).lower()
    score = 0
    reasons: list[str] = []
    if q and q == vendor:
        score += 100
        reasons.append("vendor_exact")
    if q and q in file_name:
        score += 50
        reasons.append("file_match")
    if q and q in relative_path:
        score += 20
        reasons.append("path_match")
    q_tokens = [t for t in q.split() if t]
    hay = f"{vendor} {file_name} {relative_path}"
    for token in q_tokens:
        if token in hay:
            score += 5
    return score, ",".join(reasons) if reasons else "keyword"

def create_app(cfg: AgentConfig) -> FastAPI:
    app = FastAPI(title="Moldflow 2010 Remote Agent", version="1.0.0")
    jobs = JobStore(cfg.workspace_root)
    cache = {"value": None}

    def auth(token: str | None):
        try:
            verify_token(token, cfg.api_token)
        except SecurityError as exc:
            raise HTTPException(401, str(exc))

    def get_discovery():
        if cache["value"] is None:
            cache["value"] = discover(cfg.moldflow_search_roots, cfg.explicit_paths)
        return cache["value"]

    @app.get("/health")
    def health(x_api_token: str | None = Header(default=None)):
        auth(x_api_token)
        return {"ok": True, "dry_run": cfg.dry_run, "workspace": str(cfg.workspace_root)}

    @app.post("/discover")
    def do_discover(x_api_token: str | None = Header(default=None)):
        auth(x_api_token)
        cache["value"] = discover(cfg.moldflow_search_roots, cfg.explicit_paths)
        write_audit(cfg.log_dir, "discover", cache["value"])
        return cache["value"]

    @app.post("/automation/probe-createobject")
    def probe_createobject(x_api_token: str | None = Header(default=None)):
        """Read-only Synergy COM activation probe in the agent's desktop session."""
        auth(x_api_token)
        log_path = cfg.workspace_root / "automation" / "createobject_agent_probe.log"
        log_path.parent.mkdir(parents=True, exist_ok=True)
        log_path.unlink(missing_ok=True)
        script = VBS_DIR / "07_probe_createobject_logged.vbs"
        result = run_process(
            [r"C:\Windows\System32\cscript.exe", "//nologo", str(script), str(log_path)],
            VBS_DIR,
            cfg.timeouts_seconds.short,
            False,
        )
        payload = result.to_dict()
        payload["probe_log"] = log_path.read_text(encoding="utf-8", errors="replace") if log_path.exists() else ""
        write_audit(cfg.log_dir, "probe_createobject", payload)
        return payload

    @app.post("/automation/create-test-study")
    def create_test_study(req: CreateTestStudyRequest, x_api_token: str | None = Header(default=None)):
        """Create a new, isolated test study; never runs mesh or analysis."""
        auth(x_api_token)
        if not req.confirm_create:
            raise HTTPException(400, "confirm_create=true is required")
        source = safe_resolve(cfg.workspace_root, req.source_path, must_exist=True)
        project_dir = safe_resolve(cfg.workspace_root, req.project_dir, must_exist=False)
        if project_dir.exists() and any(project_dir.iterdir()):
            raise HTTPException(409, f"project directory is not empty: {project_dir}")
        project_dir.mkdir(parents=True, exist_ok=True)
        for value, label in ((req.project_name, "project_name"), (req.study_name, "study_name")):
            if not value or any(ch not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-" for ch in value):
                raise HTTPException(400, f"unsafe {label}")
        script = VBS_DIR / "04_create_test_study.vbs"
        result = run_process(
            [r"C:\Windows\System32\cscript.exe", "//nologo", str(script), str(source),
             str(project_dir), req.project_name, req.study_name],
            VBS_DIR,
            cfg.timeouts_seconds.gui,
            False,
        )
        payload = result.to_dict()
        payload["created_files"] = [str(path) for path in project_dir.rglob("*") if path.is_file()]
        write_audit(cfg.log_dir, "create_test_study", payload)
        return payload

    @app.post("/automation/import-into-current-test-study")
    def import_into_current_test_study(req: ImportCurrentStudyRequest, x_api_token: str | None = Header(default=None)):
        auth(x_api_token)
        if not req.confirm_import:
            raise HTTPException(400, "confirm_import=true is required")
        source = safe_resolve(cfg.workspace_root, req.source_path, must_exist=True)
        log_path = cfg.workspace_root / "automation" / "import_current_study.log"
        log_path.unlink(missing_ok=True)
        script = VBS_DIR / "08_import_into_current_study.vbs"
        result = run_process(
            [r"C:\Windows\System32\cscript.exe", "//nologo", str(script), str(source), str(log_path)],
            VBS_DIR,
            cfg.timeouts_seconds.gui,
            False,
        )
        payload = result.to_dict()
        payload["operation_log"] = log_path.read_text(encoding="utf-8", errors="replace") if log_path.exists() else ""
        write_audit(cfg.log_dir, "import_into_current_test_study", payload)
        return payload

    @app.post("/automation/export-current-test-logs")
    def export_current_test_logs(x_api_token: str | None = Header(default=None)):
        auth(x_api_token)
        output = cfg.workspace_root / "results" / "pp_plate_fusion.log"
        output.parent.mkdir(parents=True, exist_ok=True)
        script = VBS_DIR / "09_export_current_logs.vbs"
        result = run_process(
            [r"C:\Windows\System32\cscript.exe", "//nologo", str(script), str(output)],
            VBS_DIR,
            cfg.timeouts_seconds.short,
            False,
        )
        payload = result.to_dict()
        payload["files"] = [str(path) for path in output.parent.glob("pp_plate_fusion.log*")]
        write_audit(cfg.log_dir, "export_current_test_logs", payload)
        return payload

    @app.post("/automation/mesh-current-test-study")
    def mesh_current_test_study(x_api_token: str | None = Header(default=None)):
        auth(x_api_token)
        log_path = cfg.workspace_root / "automation" / "mesh_current_study.log"
        log_path.unlink(missing_ok=True)
        script = VBS_DIR / "10_mesh_current_study.vbs"
        result = run_process(
            [r"C:\Windows\System32\cscript.exe", "//nologo", str(script), str(log_path)],
            VBS_DIR,
            cfg.timeouts_seconds.gui,
            False,
        )
        payload = result.to_dict()
        payload["operation_log"] = log_path.read_text(encoding="utf-8", errors="replace") if log_path.exists() else ""
        write_audit(cfg.log_dir, "mesh_current_test_study", payload)
        return payload

    @app.post("/automation/check-current-test-analysis")
    def check_current_test_analysis(x_api_token: str | None = Header(default=None)):
        auth(x_api_token)
        log_path = cfg.workspace_root / "automation" / "check_current_analysis.log"
        log_path.unlink(missing_ok=True)
        script = VBS_DIR / "11_check_current_analysis.vbs"
        result = run_process(
            [r"C:\Windows\System32\cscript.exe", "//nologo", str(script), str(log_path)],
            VBS_DIR,
            cfg.timeouts_seconds.short,
            False,
        )
        payload = result.to_dict()
        payload["operation_log"] = log_path.read_text(encoding="utf-8", errors="replace") if log_path.exists() else ""
        write_audit(cfg.log_dir, "check_current_test_analysis", payload)
        return payload

    @app.post("/automation/run-current-test-analysis")
    def run_current_test_analysis(x_api_token: str | None = Header(default=None)):
        auth(x_api_token)
        log_path = cfg.workspace_root / "automation" / "run_current_analysis.log"
        log_path.unlink(missing_ok=True)
        script = VBS_DIR / "12_run_current_analysis.vbs"
        result = run_process(
            [r"C:\Windows\System32\cscript.exe", "//nologo", str(script), str(log_path)],
            VBS_DIR,
            cfg.timeouts_seconds.short,
            False,
        )
        payload = result.to_dict()
        payload["operation_log"] = log_path.read_text(encoding="utf-8", errors="replace") if log_path.exists() else ""
        write_audit(cfg.log_dir, "run_current_test_analysis", payload)
        return payload

    @app.post("/automation/save-current-study-copy")
    def save_current_study_copy(name: str, x_api_token: str | None = Header(default=None)):
        auth(x_api_token)
        if not name or any(ch in name for ch in '\\/:*?"<>|'):
            raise HTTPException(status_code=400, detail="Invalid study name")
        log_path = cfg.workspace_root / "automation" / "save_current_study_copy.log"
        log_path.unlink(missing_ok=True)
        script = VBS_DIR / "13_save_current_study_as.vbs"
        result = run_process(
            [r"C:\Windows\System32\cscript.exe", "//nologo", str(script), name, str(log_path)],
            VBS_DIR,
            cfg.timeouts_seconds.gui,
            False,
        )
        payload = result.to_dict()
        payload["operation_log"] = log_path.read_text(encoding="utf-8", errors="replace") if log_path.exists() else ""
        write_audit(cfg.log_dir, "save_current_study_copy", payload)
        return payload

    @app.post("/jobs/run")
    def submit_run(req: StudyRequest, x_api_token: str | None = Header(default=None)):
        auth(x_api_token)
        study = safe_resolve(cfg.workspace_root, req.study_path, must_exist=True)
        job = jobs.create("run", req.model_dump())

        def worker():
            job["status"] = "running"; jobs.save(job)
            try:
                result = run_study(get_discovery(), study, cfg.timeouts_seconds.analysis, cfg.dry_run)
                job["result"] = result.to_dict()
                job["status"] = "succeeded" if result.returncode == 0 and not result.timed_out else "failed"
            except Exception as exc:
                job["status"] = "failed"
                job["error"] = {"message": str(exc), "traceback": traceback.format_exc()}
            jobs.save(job)
            write_audit(cfg.log_dir, "job_finished", job)

        threading.Thread(target=worker, daemon=True).start()
        write_audit(cfg.log_dir, "job_submitted", job)
        return job

    @app.post("/results/export-log")
    def result_export(req: ExportLogRequest, x_api_token: str | None = Header(default=None)):
        auth(x_api_token)
        study = safe_resolve(cfg.workspace_root, req.study_path, True)
        output = safe_resolve(cfg.workspace_root, req.output_path, False)
        output.parent.mkdir(parents=True, exist_ok=True)
        result = export_log(get_discovery(), study, output, cfg.timeouts_seconds.short, cfg.dry_run)
        write_audit(cfg.log_dir, "export_log", result.to_dict())
        return result.to_dict()

    @app.post("/studies/modify")
    def study_modify(req: ModifyRequest, x_api_token: str | None = Header(default=None)):
        auth(x_api_token)
        source = safe_resolve(cfg.workspace_root, req.source_path, True)
        target = safe_resolve(cfg.workspace_root, req.target_path, False)
        modifier = safe_resolve(cfg.workspace_root, req.modifier_xml_path, True)
        result = modify_study(get_discovery(), source, target, modifier,
                              cfg.timeouts_seconds.short, cfg.dry_run)
        write_audit(cfg.log_dir, "modify_study", result.to_dict())
        return result.to_dict()

    @app.get("/jobs/{job_id}")
    def get_job(job_id: str, x_api_token: str | None = Header(default=None)):
        auth(x_api_token)
        try:
            return jobs.get(job_id)
        except KeyError:
            raise HTTPException(404, "Job not found")

    @app.get("/jobs")
    def list_jobs(x_api_token: str | None = Header(default=None)):
        auth(x_api_token)
        return jobs.list()

    @app.post("/materials/search")
    def materials_search(req: MaterialSearchRequest, x_api_token: str | None = Header(default=None)):
        auth(x_api_token)
        result = _material_rows(cfg, req)
        write_audit(cfg.log_dir, "materials_search", {"query": req.model_dump(), "count": result["total"]})
        return result

    @app.post("/materials/select")
    def materials_select(req: MaterialSelectRequest, x_api_token: str | None = Header(default=None)):
        auth(x_api_token)
        result = _material_rows(
            cfg,
            MaterialSearchRequest(
                query=req.query,
                vendor=req.vendor,
                source_kind=req.source_kind,
                limit=req.limit,
            ),
        )
        scored = []
        for item in result["items"]:
            score, reason = _score_material(item, req.query)
            item = dict(item)
            item["score"] = score
            item["match_reason"] = reason
            scored.append(item)
        scored.sort(key=lambda r: (-int(r["score"]), str(r["vendor"]).lower(), str(r["file_name"]).lower()))
        chosen = scored[0] if scored else None
        payload = {
            "query": req.query,
            "selected": chosen,
            "candidates": scored,
            "total": result["total"],
            "db_path": result["db_path"],
        }
        write_audit(cfg.log_dir, "materials_select", {"query": req.model_dump(), "selected": chosen["source_path"] if chosen else None})
        return payload

    return app

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    args = parser.parse_args()
    cfg = load_config(args.config)
    uvicorn.run(create_app(cfg), host=cfg.bind_host, port=cfg.bind_port)

if __name__ == "__main__":
    main()
