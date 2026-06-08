# -*- coding: utf-8 -*-
"""LAVIE satellite job worker (SJP v1). Accepts structured jobs, returns Result JSON synchronously."""
from __future__ import annotations

import argparse
import json
import os
import re
import secrets
import subprocess
import sys
import threading
import urllib.request
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

os.environ.setdefault("PGCLIENTENCODING", "UTF8")

JST = timezone(timedelta(hours=9))
JOB_ID_RE = re.compile(r"^[A-Za-z0-9._-]{1,64}$")
ALLOWED_TYPES = {"shell", "docker", "cae_trial"}
TAIL_CHARS = 8000
DEFAULT_PORT = 5680
DEFAULT_BIND = "0.0.0.0"
DEFAULT_JOBS_ROOT_D = Path("D:/clawstack_satellite/data/work/jobs")
DEFAULT_JOBS_ROOT_E = Path("E:/clawstack_satellite/data/work/jobs")
DEFAULT_JOBS_ROOT_C = Path("C:/clawstack_satellite/data/work/jobs")
LOCAL_MONITOR_METRICS_URL = os.environ.get("LOCAL_MONITOR_METRICS_URL", "http://127.0.0.1:8111/metrics")


def _drive_exists(drive: str) -> bool:
    if not drive:
        return False
    root = drive if drive.endswith("/") or drive.endswith("\\") else f"{drive}/"
    return Path(root).exists()


def pick_default_jobs_root() -> Path:
    if _drive_exists("D:"):
        return DEFAULT_JOBS_ROOT_D
    if _drive_exists("E:"):
        return DEFAULT_JOBS_ROOT_E
    return DEFAULT_JOBS_ROOT_C


def _now_iso() -> str:
    return datetime.now(JST).isoformat()


def _tail(text: str, limit: int = TAIL_CHARS) -> str:
    if not text:
        return ""
    if len(text) <= limit:
        return text
    return text[-limit:]


def _as_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return str(value)


def _compact_monitor_metrics(data: dict[str, Any]) -> dict[str, Any]:
    keys = (
        "hostname",
        "cpu_usage_percent",
        "cpu_current_clock_mhz",
        "ram_usage_percent",
        "ram_used_gb",
        "ram_total_gb",
        "cpu_temp_celsius",
        "thermal_control_temp_c",
        "core_max_c",
        "lhm_ok",
        "temp_source",
        "thermal_throttle_label",
        "cpu_limit_percent",
        "is_throttling",
    )
    return {key: data.get(key) for key in keys if key in data}


def collect_resource_snapshot(phase: str, job_id: str, category: str = "") -> dict[str, Any]:
    snap: dict[str, Any] = {
        "schema": "clawstack.lavie_job_resource_snapshot.v1",
        "phase": phase,
        "job_id": job_id,
        "category": category,
        "timestamp": _now_iso(),
        "metrics_url": LOCAL_MONITOR_METRICS_URL,
    }
    try:
        req = urllib.request.Request(LOCAL_MONITOR_METRICS_URL, headers={"User-Agent": "lavie_job_worker/1"})
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read(256 * 1024).decode("utf-8", errors="replace"))
        if isinstance(data, dict):
            snap["ok"] = True
            snap["metrics"] = _compact_monitor_metrics(data)
        else:
            snap["ok"] = False
            snap["error"] = "metrics_json_not_object"
    except Exception as exc:
        snap["ok"] = False
        snap["error"] = str(exc)[:300]
    return snap


def append_resource_snapshot(work_dir: Path, snapshot: dict[str, Any]) -> None:
    try:
        path = work_dir / "resource_snapshots.jsonl"
        with path.open("a", encoding="utf-8", errors="replace") as f:
            json.dump(snapshot, f, ensure_ascii=False, separators=(",", ":"))
            f.write("\n")
    except Exception:
        pass


def load_token(explicit: str = "") -> str:
    if explicit:
        return explicit.strip()
    for env_path in (
        Path(os.environ.get("SATELLITE_INSTALL_ROOT", "C:/clawstack_satellite")) / ".env",
        Path.cwd() / ".env",
    ):
        if not env_path.exists():
            continue
        for line in env_path.read_text(encoding="utf-8-sig", errors="replace").splitlines():
            line = line.strip()
            if line.startswith("SATELLITE_JOB_TOKEN="):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    env_token = os.environ.get("SATELLITE_JOB_TOKEN", "").strip()
    if env_token:
        return env_token
    raise RuntimeError("SATELLITE_JOB_TOKEN missing (.env or --token)")


def _read_env_file_value(env_path: Path, key: str) -> str:
    if not env_path.exists():
        return ""
    for line in env_path.read_text(encoding="utf-8-sig", errors="replace").splitlines():
        line = line.strip()
        if line.startswith(f"{key}="):
            return line.split("=", 1)[1].strip().strip('"').strip("'")
    return ""


def default_jobs_root(install_root: Path | None = None) -> Path:
    env_override = os.environ.get("SATELLITE_JOBS_ROOT", "").strip()
    if env_override:
        return Path(env_override)
    install = install_root or Path(os.environ.get("SATELLITE_INSTALL_ROOT", "C:/clawstack_satellite"))
    from_env = _read_env_file_value(install / ".env", "SATELLITE_JOBS_ROOT")
    if from_env:
        return Path(from_env)
    return pick_default_jobs_root()


def load_jobs_root(explicit: str = "") -> Path:
    if explicit:
        return Path(explicit)
    return default_jobs_root()


def load_host_label(explicit: str = "") -> str:
    if explicit:
        return explicit
    return os.environ.get("SATELLITE_NODE_ID", "lavie")


def resolve_work_dir(jobs_root: Path, job_id: str, requested: str = "") -> Path:
    if requested:
        candidate = Path(requested).resolve()
    else:
        candidate = (jobs_root / job_id).resolve()
    jobs_root_resolved = jobs_root.resolve()
    if jobs_root_resolved not in candidate.parents and candidate != jobs_root_resolved:
        raise ValueError(f"work_dir must stay under {jobs_root_resolved}")
    candidate.mkdir(parents=True, exist_ok=True)
    return candidate


def run_shell(payload: dict[str, Any], work_dir: Path, timeout_sec: int) -> dict[str, Any]:
    command = (payload.get("command") or "").strip()
    if not command:
        raise ValueError("shell payload.command required")
    proc = subprocess.run(
        command,
        shell=True,
        cwd=str(work_dir),
        capture_output=True,
        text=True,
        timeout=timeout_sec,
        encoding="utf-8",
        errors="replace",
    )
    return {
        "exit_code": int(proc.returncode),
        "stdout_tail": _tail(proc.stdout),
        "stderr_tail": _tail(proc.stderr),
        "status": "ok" if proc.returncode == 0 else "failed",
    }


def run_docker(payload: dict[str, Any], work_dir: Path, timeout_sec: int) -> dict[str, Any]:
    image = (payload.get("image") or "").strip()
    command = (payload.get("command") or "").strip()
    if not image:
        raise ValueError("docker payload.image required")
    if not command:
        raise ValueError("docker payload.command required")
    docker_cmd = [
        "docker",
        "run",
        "--rm",
        "-v",
        f"{work_dir}:{work_dir}",
        "-w",
        str(work_dir),
        image,
        "sh",
        "-lc",
        command,
    ]
    proc = subprocess.run(
        docker_cmd,
        capture_output=True,
        text=True,
        timeout=timeout_sec,
        encoding="utf-8",
        errors="replace",
    )
    return {
        "exit_code": int(proc.returncode),
        "stdout_tail": _tail(proc.stdout),
        "stderr_tail": _tail(proc.stderr),
        "status": "ok" if proc.returncode == 0 else "failed",
    }


def default_repo_root() -> Path:
    env_root = os.environ.get("SATELLITE_REPO_ROOT", "").strip()
    if env_root:
        return Path(env_root)
    for candidate in (
        Path("C:/lavie_usb_pack"),
        Path(os.environ.get("SATELLITE_INSTALL_ROOT", "C:/clawstack_satellite")) / "repo",
    ):
        if (candidate / "scripts" / "cae_te_remote_trial.py").exists():
            return candidate
    return Path("C:/lavie_usb_pack")


def _in_docker_worker() -> bool:
    return Path("/.dockerenv").exists() or Path("/repo/scripts/cae_te_remote_trial.py").exists()


def _resolve_lavie_paths(repo_root: Path, workspace: Path) -> tuple[Path, Path]:
    """Map Windows paths to container mounts when worker runs in Docker on LAVIE."""
    if _in_docker_worker():
        repo = Path("/repo")
        ws = Path("/e/clawstack_satellite/data/work/cae_te_workspace")
        if repo.is_dir():
            return repo, ws
    return repo_root, workspace


def default_cae_workspace(install_root: Path | None = None) -> Path:
    env_ws = os.environ.get("CAE_TE_WORKSPACE", "").strip()
    if env_ws:
        return Path(env_ws)
    install = install_root or Path(os.environ.get("SATELLITE_INSTALL_ROOT", "C:/clawstack_satellite"))
    from_env = _read_env_file_value(install / ".env", "CAE_TE_WORKSPACE")
    if from_env:
        return Path(from_env)
    if _drive_exists("E:"):
        return Path("E:/clawstack_satellite/data/work/cae_te_workspace")
    return Path("C:/clawstack_satellite/data/work/cae_te_workspace")


def run_cae_trial(payload: dict[str, Any], work_dir: Path, timeout_sec: int, host: str) -> dict[str, Any]:
    category = (payload.get("category") or "").strip()
    if not category:
        raise ValueError("cae_trial payload.category required")

    repo_root = Path(str(payload.get("repo_root") or default_repo_root()))
    workspace = Path(str(payload.get("workspace_root") or default_cae_workspace()))
    repo_root, workspace = _resolve_lavie_paths(repo_root, workspace)
    os.environ["CAE_TE_WORKSPACE"] = str(workspace)
    os.environ.setdefault("SATELLITE_REPO_ROOT", str(repo_root))

    script_path = repo_root / "scripts" / "cae_te_remote_trial.py"
    if not script_path.exists():
        raise ValueError(f"cae_te_remote_trial.py not found under {repo_root}")
    trial_id = (payload.get("trial_id") or "").strip()
    dry_run = bool(payload.get("dry_run"))
    params = payload.get("params") or {}
    output_path = work_dir / "cae_trial_result.json"
    start_snapshot = collect_resource_snapshot("before", trial_id or "cae_trial", category)
    append_resource_snapshot(work_dir, start_snapshot)

    cmd = [
        sys.executable,
        str(script_path),
        "--category",
        category,
        "--host",
        host,
        "--workspace",
        str(workspace),
        "--timeout",
        str(timeout_sec),
        "--no-append-log",
        "--output",
        str(output_path),
    ]
    if trial_id:
        cmd.extend(["--trial-id", trial_id])
    if dry_run:
        cmd.append("--dry-run")
    if params:
        cmd.extend(["--params-json", json.dumps(params, ensure_ascii=False)])

    timeout_hit = False
    try:
        proc = subprocess.run(
            cmd,
            cwd=str(repo_root),
            capture_output=True,
            text=True,
            timeout=timeout_sec + 60,
            encoding="utf-8",
            errors="replace",
        )
    except subprocess.TimeoutExpired as exc:
        timeout_hit = True
        proc = subprocess.CompletedProcess(
            cmd,
            124,
            stdout=_as_text(exc.stdout),
            stderr=_as_text(exc.stderr) or f"worker timeout after {timeout_sec + 60}s",
        )
    end_snapshot = collect_resource_snapshot("after", trial_id or "cae_trial", category)
    append_resource_snapshot(work_dir, end_snapshot)

    trial_entry: dict[str, Any] = {}
    if output_path.exists():
        trial_entry = json.loads(output_path.read_text(encoding="utf-8-sig"))
    elif proc.stdout.strip():
        trial_entry = json.loads(proc.stdout.strip().splitlines()[-1])

    if timeout_hit and not trial_entry:
        trial_entry = {
            "id": trial_id,
            "category": category,
            "host": host,
            "verdict": "TIMEOUT",
            "error": f"worker timeout after {timeout_sec + 60}s",
        }

    verdict = trial_entry.get("verdict", "ERROR")
    ok_verdict = verdict in {"SUCCESS", "DRY_RUN", "FAILED", "SKIPPED", "PREGATE_FAIL"}
    status = "ok" if proc.returncode == 0 and ok_verdict else "failed"
    return {
        "exit_code": int(proc.returncode),
        "stdout_tail": _tail(proc.stdout),
        "stderr_tail": _tail(proc.stderr),
        "status": status,
        "metrics": {
            "cae_trial": trial_entry,
            "category": category,
            "workspace": str(workspace),
            "repo_root": str(repo_root),
            "verdict": verdict,
            "resource_snapshots": {
                "before": start_snapshot,
                "after": end_snapshot,
            },
        },
    }


def execute_job(job: dict[str, Any], jobs_root: Path, state: WorkerState) -> dict[str, Any]:
    job_id = str(job.get("job_id") or "").strip()
    job_type = str(job.get("type") or "").strip()
    timeout_sec = int(job.get("timeout_sec") or 600)
    timeout_sec = max(1, min(timeout_sec, 86400))
    if state.max_job_timeout:
        timeout_sec = min(timeout_sec, state.max_job_timeout)
    payload = job.get("payload") or {}
    host = state.host

    started = _now_iso()
    base: dict[str, Any] = {
        "job_id": job_id,
        "host": host,
        "type": job_type,
        "started_at": started,
        "metrics": {},
        "artifacts": [],
        "failure_tags": [],
    }

    if not JOB_ID_RE.match(job_id):
        base.update(
            {
                "status": "pregate_fail",
                "exit_code": 1,
                "finished_at": _now_iso(),
                "error": "invalid job_id",
                "failure_tags": ["invalid_job_id"],
            }
        )
        return base

    if job_type not in ALLOWED_TYPES:
        base.update(
            {
                "status": "pregate_fail",
                "exit_code": 1,
                "finished_at": _now_iso(),
                "error": f"unsupported type: {job_type}",
                "failure_tags": ["unsupported_type"],
            }
        )
        return base

    if state.no_docker and job_type == "docker":
        base.update(
            {
                "status": "pregate_fail",
                "exit_code": 1,
                "finished_at": _now_iso(),
                "error": "docker jobs disabled on this worker profile",
                "failure_tags": ["docker_disabled"],
            }
        )
        return base

    if state.cae_dry_run_only and job_type == "cae_trial" and not bool(payload.get("dry_run")):
        base.update(
            {
                "status": "pregate_fail",
                "exit_code": 1,
                "finished_at": _now_iso(),
                "error": "cae_trial requires dry_run on this worker profile",
                "failure_tags": ["cae_dry_run_required"],
            }
        )
        return base

    try:
        work_dir = resolve_work_dir(jobs_root, job_id, str(payload.get("work_dir") or ""))
        if job_type == "shell":
            outcome = run_shell(payload, work_dir, timeout_sec)
        elif job_type == "docker":
            outcome = run_docker(payload, work_dir, timeout_sec)
        else:
            outcome = run_cae_trial(payload, work_dir, timeout_sec, host)
        base.update(outcome)
        base["finished_at"] = _now_iso()
        summary_path = work_dir / "result_summary.json"
        summary_path.write_text(json.dumps(base, ensure_ascii=False, indent=2), encoding="utf-8")
        base["artifacts"] = [{"path": str(summary_path), "kind": "result_summary"}]
        return base
    except subprocess.TimeoutExpired:
        base.update(
            {
                "status": "timeout",
                "exit_code": 124,
                "finished_at": _now_iso(),
                "error": f"timeout after {timeout_sec}s",
                "failure_tags": ["timeout"],
            }
        )
        return base
    except Exception as exc:
        base.update(
            {
                "status": "error",
                "exit_code": 1,
                "finished_at": _now_iso(),
                "error": str(exc),
                "failure_tags": ["worker_error"],
            }
        )
        return base


class WorkerState:
    def __init__(
        self,
        token: str,
        jobs_root: Path,
        host: str,
        *,
        no_docker: bool = False,
        cae_dry_run_only: bool = False,
        max_job_timeout: int = 0,
    ) -> None:
        self.token = token
        self.jobs_root = jobs_root
        self.host = host
        self.no_docker = no_docker
        self.cae_dry_run_only = cae_dry_run_only
        self.max_job_timeout = max(0, int(max_job_timeout))
        self.lock = threading.Lock()


def make_handler(state: WorkerState):
    class JobHandler(BaseHTTPRequestHandler):
        server_version = "SatelliteJobWorker/1.0"

        def log_message(self, fmt: str, *args: Any) -> None:
            print(f"[worker] {self.address_string()} {fmt % args}", flush=True)

        def _send_json(self, code: int, payload: dict[str, Any]) -> None:
            body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _authorized(self) -> bool:
            header = self.headers.get("X-Satellite-Token") or self.headers.get("Authorization") or ""
            if header.lower().startswith("bearer "):
                header = header[7:].strip()
            return secrets.compare_digest(header.strip(), state.token)

        def do_GET(self) -> None:
            path = urlparse(self.path).path
            if path == "/healthz":
                self._send_json(
                    200,
                    {
                        "status": "ok",
                        "host": state.host,
                        "jobs_root": str(state.jobs_root),
                        "profile": "light" if state.no_docker else "full",
                        "no_docker": state.no_docker,
                        "cae_dry_run_only": state.cae_dry_run_only,
                        "max_job_timeout": state.max_job_timeout or None,
                    },
                )
                return
            self._send_json(404, {"error": "not_found"})

        def do_POST(self) -> None:
            path = urlparse(self.path).path
            if path not in {"/jobs", "/jobs/"}:
                self._send_json(404, {"error": "not_found"})
                return
            if not self._authorized():
                self._send_json(401, {"error": "unauthorized"})
                return
            length = int(self.headers.get("Content-Length") or "0")
            raw = self.rfile.read(length)
            try:
                job = json.loads(raw.decode("utf-8"))
            except json.JSONDecodeError as exc:
                self._send_json(400, {"error": f"invalid json: {exc}"})
                return
            with state.lock:
                result = execute_job(job, state.jobs_root, state)
            code = 200 if result.get("status") in {"ok"} else 500
            self._send_json(code, result)

    return JobHandler


def main() -> int:
    parser = argparse.ArgumentParser(description="LAVIE satellite job worker (SJP v1/v2)")
    parser.add_argument("--bind", default=DEFAULT_BIND)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--token", default="")
    parser.add_argument("--jobs-root", default="")
    parser.add_argument("--host", default="")
    parser.add_argument("--no-docker", action="store_true", help="Reject docker jobs (light satellite)")
    parser.add_argument(
        "--cae-dry-run-only",
        action="store_true",
        help="Reject cae_trial unless payload.dry_run is true",
    )
    parser.add_argument(
        "--max-timeout",
        type=int,
        default=0,
        help="Cap per-job timeout_sec (0 = no extra cap)",
    )
    args = parser.parse_args()

    try:
        token = load_token(args.token)
        jobs_root = load_jobs_root(args.jobs_root)
        host = load_host_label(args.host)
        jobs_root.mkdir(parents=True, exist_ok=True)
    except Exception as exc:
        print(f"[NG] {exc}", file=sys.stderr)
        return 1

    worker_state = WorkerState(
        token,
        jobs_root,
        host,
        no_docker=bool(args.no_docker),
        cae_dry_run_only=bool(args.cae_dry_run_only),
        max_job_timeout=int(args.max_timeout or 0),
    )
    handler = make_handler(worker_state)
    server = ThreadingHTTPServer((args.bind, args.port), handler)
    print(f"[OK] Satellite job worker listening on http://{args.bind}:{args.port}", flush=True)
    print(f"[OK] jobs_root={jobs_root} host={host}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("[OK] stopped", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
