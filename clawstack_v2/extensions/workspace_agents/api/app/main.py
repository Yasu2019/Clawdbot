from fastapi import FastAPI
from pydantic import BaseModel
from .qa import analyze_csv
from .guards import assert_read_only_sql, require_hitl

app = FastAPI(title="OpenClaw Workspace Agents API", version="1.0.0")

class CsvAnalyzeRequest(BaseModel):
    file_path: str
    top_n: int = 10

class SqlCheckRequest(BaseModel):
    sql: str

class ReleaseRequest(BaseModel):
    action: str
    approved: bool = False

@app.get("/health")
def health():
    return {"status": "ok", "mode": "production_guarded", "read_only": True}

@app.post("/qa/analyze-csv")
def qa_analyze_csv(req: CsvAnalyzeRequest):
    return analyze_csv(req.file_path, req.top_n)

@app.post("/guard/sql-check")
def sql_check(req: SqlCheckRequest):
    assert_read_only_sql(req.sql)
    return {"ok": True, "message": "SQL is read-only"}

@app.post("/guard/release")
def guarded_release(req: ReleaseRequest):
    require_hitl(req.action, req.approved)
    return {"ok": True, "action": req.action}
