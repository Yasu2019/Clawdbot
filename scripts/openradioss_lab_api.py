# -*- coding: utf-8 -*-
"""OpenRadioss Lab API (host 127.0.0.1:8777).

Aggregates status JSON for the Lab UI and runs safe operator actions
against existing scripts. Does NOT silently reset meaning-gate fail_streak.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import threading
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

ROOT = Path(__file__).resolve().parents[1]
WS = ROOT / "data" / "workspace"
APP = WS / "apps" / "openradioss_lab"
IMAGES = ROOT / "data" / "cae_te_workspace" / "results" / "images"
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8777
JST = timezone(timedelta(hours=9))

STATUS_FILES = {
    "tri_track": "k10_tri_track_cae_status.json",
    "pdca": "openradioss_pdca_status.json",
    "self_heal": "self_heal_status.json",
    "progress": "openradioss_progress.json",
    "autonomous": "openradioss_autonomous_status.json",
    "te_state": "k10_openradioss_te_state.json",
    "evolution": "cae_trial_evolution_state.json",
    "overrides": "tri_track_param_overrides.json",
    "improver": "meaning_gate_auto_improver_status.json",
    "install": "red_lavie_openradioss_install_status.json",
    "node_registry": "red_lavie_node_registry.json",
    "urgent": "red_lavie_urgent_assy_run.json",
    "limits": "red_lavie_cae_resource_limits_pending.json",
    "contact": "openradioss_contact_diagnose.json",
    "satellite_live": "satellite_cae_live_status.json",
    "maturity": "apps/growth_dashboard/commercial_benchmark_maturity_latest.json",
}

ACTION_LOG = APP / "action_log.jsonl"


def now_iso() -> str:
    return datetime.now(JST).isoformat(timespec="seconds")


def load_json(rel: str) -> dict:
    path = WS / rel if not rel.startswith("apps/") else WS / rel
    if not path.exists():
        return {"_missing": True, "_path": str(path)}
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
        if isinstance(data, dict):
            data["_path"] = str(path)
            data["_mtime"] = datetime.fromtimestamp(path.stat().st_mtime, tz=JST).isoformat(
                timespec="seconds"
            )
        return data if isinstance(data, dict) else {"_raw": data, "_path": str(path)}
    except Exception as e:
        return {"_error": str(e)[:200], "_path": str(path)}


def append_action(entry: dict) -> None:
    APP.mkdir(parents=True, exist_ok=True)
    entry = dict(entry)
    entry["at"] = now_iso()
    with ACTION_LOG.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def list_videos(limit: int = 40) -> list[dict]:
    out: list[dict] = []
    if not IMAGES.exists():
        return out
    for p in sorted(IMAGES.rglob("*"), key=lambda x: x.stat().st_mtime if x.is_file() else 0, reverse=True):
        if not p.is_file():
            continue
        if p.suffix.lower() not in {".mp4", ".gif", ".png", ".jpg", ".jpeg", ".webp"}:
            continue
        if "openradioss" not in p.name.lower() and "radioss" not in str(p).lower() and "blank" not in p.name.lower():
            # keep openradioss-named or blanking; also keep top-level frames folders with openradioss
            if "openradioss" not in str(p).lower():
                continue
        rel = p.relative_to(IMAGES).as_posix()
        out.append(
            {
                "name": p.name,
                "rel": rel,
                "bytes": p.stat().st_size,
                "mtime": datetime.fromtimestamp(p.stat().st_mtime, tz=JST).isoformat(timespec="seconds"),
                "ext": p.suffix.lower(),
            }
        )
        if len(out) >= limit:
            break
    return out


def build_status() -> dict:
    bundle = {k: load_json(v) for k, v in STATUS_FILES.items()}
    track = ((bundle.get("tri_track") or {}).get("tracks") or {}).get("openradioss_red_lavie") or {}
    evo = ((bundle.get("evolution") or {}).get("tracks") or {}).get("openradioss_red_lavie") or {}
    maturity = bundle.get("maturity") or {}
    evidence = ((maturity.get("evidence_snapshot") or {}).get("openradioss")) if isinstance(maturity, dict) else None
    progress = bundle.get("progress") or {}
    counts = progress.get("counts") or {}
    pdca = bundle.get("pdca") or {}
    return {
        "ok": True,
        "at": now_iso(),
        "api": {"host": DEFAULT_HOST, "port": DEFAULT_PORT},
        "kpi": {
            "tri_verdict": (track.get("last") or {}).get("verdict"),
            "tri_fail_streak": track.get("fail_streak"),
            "tri_error": (track.get("last") or {}).get("error"),
            "tri_at": (track.get("last") or {}).get("at"),
            "orchestrator_running": (bundle.get("tri_track") or {}).get("running"),
            "pdca_gate": pdca.get("gate_passed"),
            "pdca_t_final_ms": (pdca.get("result") or {}).get("t_final_ms"),
            "progress_success": counts.get("success"),
            "progress_total": counts.get("total_seen") or counts.get("finished"),
            "evolution_verdict": evo.get("verdict"),
            "evolution_trial": evo.get("trial_id"),
            "gate_min_t_ms": 18.13,
        },
        "bundle": bundle,
        "videos": list_videos(),
        "north_star": {
            "category": "press_blanking_assy",
            "host": "red_lavie",
            "never": ["silent_fail_streak_reset", "MOLDFLOW_EQUIVALENT_claim"],
            "meaning_gate": "T019/P025/P026 -- T_final >= 18.13ms ASSY; no parametric-only SUCCESS",
        },
        "evidence_openradioss": evidence,
    }


def spawn_script(script_rel: str, args: list[str], job_id: str) -> dict:
    script = ROOT / script_rel
    if not script.exists():
        return {"ok": False, "error": f"missing {script_rel}"}
    log_dir = APP / "api_jobs"
    log_dir.mkdir(parents=True, exist_ok=True)
    out_log = log_dir / f"{job_id}.out.log"
    err_log = log_dir / f"{job_id}.err.log"
    cmd = [sys.executable, str(script), *args]

    def _run() -> None:
        with out_log.open("w", encoding="utf-8") as fo, err_log.open("w", encoding="utf-8") as fe:
            fo.write(f"# start {now_iso()} cmd={cmd}\n")
            fo.flush()
            try:
                p = subprocess.run(
                    cmd,
                    cwd=str(ROOT),
                    stdout=fo,
                    stderr=fe,
                    env={**os.environ, "PYTHONIOENCODING": "utf-8"},
                    check=False,
                )
                fo.write(f"\n# end {now_iso()} rc={p.returncode}\n")
            except Exception as e:
                fe.write(f"spawn_error: {e}\n")

    th = threading.Thread(target=_run, name=f"or-lab-{job_id}", daemon=True)
    th.start()
    meta = {
        "ok": True,
        "started": True,
        "job_id": job_id,
        "script": script_rel,
        "args": args,
        "out_log": str(out_log),
        "err_log": str(err_log),
    }
    append_action({"action": job_id, **meta})
    return meta


def run_sync(script_rel: str, args: list[str], timeout_s: int = 120) -> dict:
    script = ROOT / script_rel
    if not script.exists():
        # workspace-relative scripts
        alt = WS / script_rel
        if alt.exists():
            script = alt
            script_rel = str(alt.relative_to(ROOT))
        else:
            return {"ok": False, "error": f"missing {script_rel}"}
    try:
        p = subprocess.run(
            [sys.executable, str(script), *args],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout_s,
            env={**os.environ, "PYTHONIOENCODING": "utf-8"},
            check=False,
        )
        out = {
            "ok": p.returncode == 0,
            "rc": p.returncode,
            "stdout_tail": (p.stdout or "")[-2000:],
            "stderr_tail": (p.stderr or "")[-1000:],
            "script": script_rel,
        }
        append_action({"action": "sync:" + Path(script_rel).name, **out})
        return out
    except Exception as e:
        return {"ok": False, "error": str(e)[:240]}


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt: str, *args) -> None:
        sys.stderr.write("[openradioss_lab_api] " + (fmt % args) + "\n")

    def _cors(self) -> None:
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def do_OPTIONS(self) -> None:
        self.send_response(204)
        self._cors()
        self.end_headers()

    def _json(self, code: int, obj: dict) -> None:
        raw = json.dumps(obj, ensure_ascii=False, indent=2).encode("utf-8")
        self.send_response(code)
        self._cors()
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def _read_json(self) -> dict:
        n = int(self.headers.get("Content-Length") or 0)
        if n <= 0:
            return {}
        try:
            return json.loads(self.rfile.read(n).decode("utf-8", errors="replace"))
        except Exception:
            return {}

    def do_GET(self) -> None:
        path = urlparse(self.path).path.rstrip("/") or "/"
        if path in ("/api/health", "/health"):
            self._json(200, {"ok": True, "service": "openradioss_lab_api", "at": now_iso(), "port": DEFAULT_PORT})
            return
        if path == "/api/status":
            self._json(200, build_status())
            return
        if path == "/api/videos":
            self._json(200, {"ok": True, "videos": list_videos(80)})
            return
        if path == "/api/actions/log":
            lines = []
            if ACTION_LOG.exists():
                lines = ACTION_LOG.read_text(encoding="utf-8", errors="replace").splitlines()[-40:]
            self._json(200, {"ok": True, "lines": [json.loads(x) for x in lines if x.strip()]})
            return
        self._json(404, {"ok": False, "error": "not_found", "path": path})

    def do_POST(self) -> None:
        path = urlparse(self.path).path.rstrip("/") or "/"
        body = self._read_json()
        if path == "/api/actions/refresh-progress":
            # script lives under data/workspace
            r = run_sync("data/workspace/openradioss_progress_status.py", [], timeout_s=180)
            r["progress"] = load_json("openradioss_progress.json")
            self._json(200 if r.get("ok") else 500, r)
            return
        if path == "/api/actions/run-meaning-improver":
            # Never resets fail_streak; only proposes/applies bounded overrides when stopped.
            r = run_sync("scripts/meaning_gate_auto_improver.py", [], timeout_s=300)
            r["improver"] = load_json("meaning_gate_auto_improver_status.json")
            self._json(200 if r.get("ok") else 500, r)
            return
        if path == "/api/actions/launch-urgent-assy":
            if not body.get("confirm"):
                self._json(400, {"ok": False, "error": "confirm=true required"})
                return
            # Long job: spawn async. Optional skip-wait for operator override.
            args = ["--skip-wait"] if body.get("skip_wait") else []
            job = spawn_script(
                "scripts/k10_red_lavie_urgent_assy_pipeline.py",
                args,
                job_id=f"urgent_assy_{datetime.now(JST).strftime('%Y%m%d_%H%M%S')}",
            )
            self._json(202, job)
            return
        if path == "/api/actions/forbidden-reset-gate":
            self._json(
                403,
                {
                    "ok": False,
                    "error": "silent fail_streak reset is forbidden (T049/P025)",
                    "hint": "Fix root cause, then human-approve resume via improver/overrides",
                },
            )
            return
        self._json(404, {"ok": False, "error": "not_found", "path": path})


def main() -> int:
    host = os.environ.get("OPENRADIOSS_LAB_API_HOST", DEFAULT_HOST)
    port = int(os.environ.get("OPENRADIOSS_LAB_API_PORT", str(DEFAULT_PORT)))
    APP.mkdir(parents=True, exist_ok=True)
    httpd = ThreadingHTTPServer((host, port), Handler)
    print(json.dumps({"ok": True, "listening": f"http://{host}:{port}", "at": now_iso()}, ensure_ascii=False))
    httpd.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
