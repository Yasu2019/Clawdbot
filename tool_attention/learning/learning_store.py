import json, os, time
from fastapi import FastAPI
from pydantic import BaseModel

DB = "/data/tool_scores.json"
app = FastAPI(title="Tool Outcome Learning Store")

class Feedback(BaseModel):
    tool: str
    success: bool
    latency_ms: int = 0
    error: str | None = None
    task_type: str | None = None

def load():
    if os.path.exists(DB):
        with open(DB, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save(d):
    os.makedirs(os.path.dirname(DB), exist_ok=True)
    with open(DB, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False, indent=2)

@app.post("/feedback")
def feedback(fb: Feedback):
    d = load()
    item = d.setdefault(fb.tool, {"success": 0, "fail": 0, "latency_sum": 0, "events": []})
    if fb.success:
        item["success"] += 1
    else:
        item["fail"] += 1
    item["latency_sum"] += max(fb.latency_ms, 0)
    item["events"].append({"ts": time.time(), **fb.model_dump()})
    item["events"] = item["events"][-100:]
    save(d)
    return {"ok": True, "tool": fb.tool, "score": compute_multiplier(item)}

@app.get("/score/{tool}")
def score(tool: str):
    d = load()
    item = d.get(tool, {"success": 0, "fail": 0, "latency_sum": 0})
    return {"tool": tool, "multiplier": compute_multiplier(item), "raw": item}

@app.get("/ranking")
def ranking():
    d = load()
    rows = [{"tool": k, "multiplier": compute_multiplier(v), **{kk: vv for kk, vv in v.items() if kk != "events"}} for k, v in d.items()]
    return sorted(rows, key=lambda x: x["multiplier"], reverse=True)

def compute_multiplier(item):
    s = item.get("success", 0)
    f = item.get("fail", 0)
    total = s + f
    if total == 0:
        return 1.0
    rate = (s + 1) / (total + 2)
    penalty = min(f * 0.03, 0.30)
    return max(0.55, min(1.35, 0.7 + rate * 0.65 - penalty))
