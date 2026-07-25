# -*- coding: utf-8 -*-
"""Submit a structured job to a satellite worker (LAVIE/K3) and log the sync result."""
from __future__ import annotations

import argparse
import json
import sys
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

ROOT = Path(__file__).resolve().parents[1]
REGISTRY_DIR = ROOT / "data" / "workspace"
JOB_LOG = REGISTRY_DIR / "satellite_job_log.jsonl"
JST = timezone(timedelta(hours=9))


def load_token(explicit: str = "") -> str:
    if explicit:
        return explicit.strip()
    for env_path in (ROOT / ".env", Path.cwd() / ".env"):
        if not env_path.exists():
            continue
        for line in env_path.read_text(encoding="utf-8-sig", errors="replace").splitlines():
            line = line.strip()
            if line.startswith("SATELLITE_JOB_TOKEN="):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    token = __import__("os").environ.get("SATELLITE_JOB_TOKEN", "").strip()
    if token:
        return token
    raise RuntimeError("SATELLITE_JOB_TOKEN missing in .env or --token")


def load_node(node_id: str) -> dict[str, Any]:
    path = REGISTRY_DIR / f"{node_id}_node_registry.json"
    if not path.exists() and node_id == "lavie":
        path = REGISTRY_DIR / "lavie_node_registry.json"
    if not path.exists():
        raise RuntimeError(f"registry not found for node: {node_id}")
    return json.loads(path.read_text(encoding="utf-8-sig"))


def worker_base_url(node: dict[str, Any], override: str = "") -> str:
    if override:
        return override.rstrip("/")
    if node.get("job_worker_url"):
        return str(node["job_worker_url"]).rstrip("/")
    ip = (node.get("lan_ip") or node.get("tailscale_ip") or "").strip()
    port = int(node.get("job_worker_port") or 5680)
    if not ip:
        raise RuntimeError("node worker URL/ip missing in registry")
    return f"http://{ip}:{port}"


def append_log(entry: dict[str, Any]) -> None:
    REGISTRY_DIR.mkdir(parents=True, exist_ok=True)
    entry = dict(entry)
    entry["logged_at"] = datetime.now(JST).isoformat()
    with JOB_LOG.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry, ensure_ascii=False) + "\n")


def build_job(args: argparse.Namespace) -> dict[str, Any]:
    if args.payload_file:
        job = json.loads(Path(args.payload_file).read_text(encoding="utf-8"))
    else:
        job_id = args.job_id or f"{args.node}-{uuid.uuid4().hex[:8]}"
        payload: dict[str, Any] = {}
        if args.type == "shell":
            if not args.command:
                raise RuntimeError("--command required for shell jobs")
            payload = {"command": args.command}
        elif args.type == "docker":
            if not args.image or not args.command:
                raise RuntimeError("--image and --command required for docker jobs")
            payload = {"image": args.image, "command": args.command}
            if args.work_dir:
                payload["work_dir"] = args.work_dir
        elif args.type == "cae_trial":
            if not args.command:
                raise RuntimeError("--command required as category for cae_trial (e.g. press_blanking)")
            payload = {"category": args.command, "dry_run": True}
        else:
            raise RuntimeError(f"unsupported --type {args.type}")
        job = {
            "job_id": job_id,
            "type": args.type,
            "timeout_sec": args.timeout,
            "payload": payload,
            "report": {"mode": "sync"},
        }
    if "report" not in job:
        job["report"] = {"mode": "sync"}
    return job


def dispatch_job(base_url: str, token: str, job: dict[str, Any], timeout: int) -> dict[str, Any]:
    import urllib.request
    import urllib.error
    import socket
    import http.client

    class KeepAliveHTTPConnection(http.client.HTTPConnection):
        def connect(self):
            super().connect()
            self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
            try:
                self.sock.ioctl(socket.SIO_KEEPALIVE_VALS, (1, 60000, 10000))
            except Exception:
                pass

    class KeepAliveHTTPHandler(urllib.request.HTTPHandler):
        def http_open(self, req):
            return self.do_open(KeepAliveHTTPConnection, req)

    opener = urllib.request.build_opener(KeepAliveHTTPHandler)
    urllib.request.install_opener(opener)

    headers = {"X-Satellite-Token": token, "Content-Type": "application/json"}
    job_timeout = int(job.get("timeout_sec") or timeout) + 30
    
    req = urllib.request.Request(
        f"{base_url}/jobs",
        data=json.dumps(job).encode('utf-8'),
        headers=headers,
        method="POST"
    )
    
    try:
        with urllib.request.urlopen(req, timeout=job_timeout) as response:
            body_bytes = response.read()
            try:
                body = json.loads(body_bytes.decode('utf-8'))
            except json.JSONDecodeError:
                body = {"status": "error", "error": body_bytes.decode('utf-8')[:500], "exit_code": 1}
            body["_http_status"] = response.status
    except urllib.error.HTTPError as e:
        body_bytes = e.read()
        try:
            body = json.loads(body_bytes.decode('utf-8'))
        except Exception:
            body = {"status": "error", "error": str(e), "exit_code": 1}
        body["_http_status"] = e.code
    except Exception as e:
        body = {"status": "error", "error": str(e), "exit_code": 1}
        body["_http_status"] = 500
        
    return body


def probe_worker(base_url: str, token: str = "") -> tuple[bool, str]:
    import urllib.error
    import urllib.request

    headers = {"X-Satellite-Token": token} if token else {}
    try:
        request = urllib.request.Request(f"{base_url}/healthz", headers=headers)
        with urllib.request.urlopen(request, timeout=8) as response:
            body = response.read().decode("utf-8", errors="replace")
            if response.status != 200:
                return False, f"healthz {response.status}"
            return True, body[:120]
    except urllib.error.HTTPError as exc:
        return False, f"healthz {exc.code}"
    except Exception as exc:
        return False, str(exc)


def main() -> int:
    parser = argparse.ArgumentParser(description="Dispatch satellite job (SJP v1)")
    parser.add_argument("--node", default="lavie", help="Node id (registry file)")
    parser.add_argument("--base-url", default="", help="Override worker base URL")
    parser.add_argument("--token", default="", help="Override SATELLITE_JOB_TOKEN")
    parser.add_argument("--job-id", default="")
    parser.add_argument("--type", default="shell", choices=["shell", "docker", "cae_trial"])
    parser.add_argument("--command", default="")
    parser.add_argument("--image", default="")
    parser.add_argument("--work-dir", default="")
    parser.add_argument("--payload-file", default="")
    parser.add_argument("--timeout", type=int, default=600)
    parser.add_argument("--probe", action="store_true", help="Only probe worker /healthz")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    try:
        token = load_token(args.token)
        node = load_node(args.node)
        base_url = worker_base_url(node, args.base_url)
    except Exception as exc:
        print(f"[NG] {exc}", file=sys.stderr)
        return 1

    if args.probe:
        ok, reason = probe_worker(base_url, token)
        out = {"node": args.node, "base_url": base_url, "ok": ok, "detail": reason}
        print(json.dumps(out, ensure_ascii=False, indent=2) if args.json else f"ok={ok} {reason}")
        return 0 if ok else 1

    try:
        job = build_job(args)
    except Exception as exc:
        print(f"[NG] {exc}", file=sys.stderr)
        return 1

    print(f"[dispatch] node={args.node} url={base_url} job_id={job.get('job_id')} type={job.get('type')}")
    result = dispatch_job(base_url, token, job, args.timeout)
    append_log({"node": args.node, "base_url": base_url, "request": job, "result": result})

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"status={result.get('status')} exit_code={result.get('exit_code')}")
        if result.get("stdout_tail"):
            print((result.get("stdout_tail") or "")[:500])
        if result.get("error"):
            print(f"error={result.get('error')}")

    exit_code = result.get("exit_code")
    if exit_code is None:
        exit_code = 1
    ok = result.get("status") == "ok" and int(exit_code) == 0
    print(f"\nRESULT: {'PASS' if ok else 'FAIL'}")
    print(f"log: {JOB_LOG}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
