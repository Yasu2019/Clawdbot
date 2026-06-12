#!/usr/bin/env python3
"""monitor_agent_linux.py -- Clawstack fleet monitor agent for Linux nodes."""
import json
import os
import platform
import socket
import subprocess
import sys
import time
import threading
from datetime import datetime, timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

PORT = int(os.environ.get("MONITOR_AGENT_PORT", "8111"))
UPDATE_INTERVAL = 10
DATA_ROOT = Path(os.environ.get("CLAWSTACK_DATA", Path.home() / ".local" / "share" / "clawstack"))
DIAG_LOG = DATA_ROOT / "node_diagnostics.jsonl"
NETWORK_LOG = DATA_ROOT / "network_telemetry.jsonl"
HEARTBEAT_FILE = DATA_ROOT / "thinkpad_keepalive_heartbeat.txt"
RETENTION_HOURS = 72

cached_metrics: dict = {}
metrics_lock = threading.Lock()
last_network_snapshot: dict = {}


def _now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _trim_jsonl(path: Path, hours: float = RETENTION_HOURS) -> None:
    if not path.exists():
        return
    cutoff = datetime.now() - timedelta(hours=hours)
    kept: list[str] = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if not line.strip():
            continue
        try:
            row = json.loads(line)
            ts = row.get("timestamp") or row.get("collected_at") or ""
            dt = datetime.fromisoformat(str(ts).replace("Z", "+00:00").split("+")[0])
            if dt >= cutoff.replace(tzinfo=None):
                kept.append(line)
        except Exception:
            kept.append(line)
    if len(kept) < 5000:
        path.write_text("\n".join(kept) + ("\n" if kept else ""), encoding="utf-8")


def _append_jsonl(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False) + "\n")
    if path.stat().st_size > 512_000:
        _trim_jsonl(path)


def get_cpu_temp() -> float | None:
    temps = []
    base = "/sys/class/thermal"
    try:
        for zone in sorted(os.listdir(base)):
            if not zone.startswith("thermal_zone"):
                continue
            ttype_path = os.path.join(base, zone, "type")
            temp_path = os.path.join(base, zone, "temp")
            try:
                ttype = open(ttype_path).read().strip()
                raw = int(open(temp_path).read().strip())
                c = raw / 1000.0
                if 10.0 < c < 120.0:
                    temps.append((ttype, c))
            except Exception:
                pass
    except Exception:
        pass

    if temps:
        for label, val in temps:
            if "pkg" in label.lower() or "package" in label.lower():
                return round(val, 1)
        for label, val in temps:
            if "core" in label.lower() or "cpu" in label.lower():
                return round(val, 1)
        return round(max(v for _, v in temps), 1)

    try:
        out = subprocess.check_output(["sensors", "-j"], text=True, timeout=5, stderr=subprocess.DEVNULL)
        data = json.loads(out)
        best = None
        for _chip, sensors in data.items():
            if not isinstance(sensors, dict):
                continue
            for _sname, sdata in sensors.items():
                if not isinstance(sdata, dict):
                    continue
                for k, v in sdata.items():
                    if "input" in k and isinstance(v, (int, float)) and 20.0 < v < 110.0:
                        if best is None or v > best:
                            best = float(v)
        if best is not None:
            return round(best, 1)
    except Exception:
        pass
    return None


def get_cpu_usage() -> float:
    try:
        import psutil
        return round(psutil.cpu_percent(interval=1), 1)
    except Exception:
        pass
    try:
        def _read_stat():
            with open("/proc/stat") as f:
                line = f.readline()
            vals = list(map(int, line.split()[1:]))
            idle = vals[3]
            total = sum(vals)
            return idle, total
        i1, t1 = _read_stat()
        time.sleep(0.5)
        i2, t2 = _read_stat()
        diff_total = t2 - t1
        diff_idle = i2 - i1
        if diff_total > 0:
            return round((1.0 - diff_idle / diff_total) * 100, 1)
    except Exception:
        pass
    return 0.0


def get_ram_info():
    try:
        import psutil
        vm = psutil.virtual_memory()
        total_gb = round(vm.total / 1024**3, 2)
        used_gb = round(vm.used / 1024**3, 2)
        pct = round(vm.percent, 1)
        return used_gb, total_gb, pct
    except Exception:
        pass
    try:
        with open("/proc/meminfo") as f:
            lines = f.readlines()
        info = {}
        for line in lines:
            k, v = line.split(":", 1)
            info[k.strip()] = int(v.strip().split()[0])
        total_kb = info.get("MemTotal", 0)
        free_kb = info.get("MemAvailable", info.get("MemFree", 0))
        used_kb = total_kb - free_kb
        total_gb = round(total_kb / 1024**2, 2)
        used_gb = round(used_kb / 1024**2, 2)
        pct = round(used_kb / total_kb * 100, 1) if total_kb else 0.0
        return used_gb, total_gb, pct
    except Exception:
        pass
    return 0.0, 0.0, 0.0


def collect_network_snapshot() -> dict:
    snap = {
        "schema": "clawstack.linux_network_snapshot.v1",
        "timestamp": _now_iso(),
        "hostname": socket.gethostname(),
        "connected": False,
        "ssid": "",
        "signal": "",
        "device": "",
    }
    try:
        proc = subprocess.run(
            ["nmcli", "-t", "-f", "DEVICE,TYPE,STATE", "dev", "status"],
            capture_output=True,
            text=True,
            timeout=8,
        )
        for line in (proc.stdout or "").splitlines():
            parts = line.split(":")
            if len(parts) >= 3 and parts[1] == "wifi" and parts[2] == "connected":
                snap["device"] = parts[0]
                snap["connected"] = True
                break
        if snap["connected"]:
            wproc = subprocess.run(
                ["nmcli", "-t", "-f", "ACTIVE,SSID,SIGNAL", "dev", "wifi"],
                capture_output=True,
                text=True,
                timeout=8,
            )
            for line in (wproc.stdout or "").splitlines():
                parts = line.split(":")
                if len(parts) >= 3 and parts[0] == "yes":
                    snap["ssid"] = parts[1]
                    snap["signal"] = parts[2]
                    break
    except Exception as exc:
        snap["error"] = str(exc)[:200]
    return snap


def collect_metrics() -> dict:
    temp = get_cpu_temp()
    cpu = get_cpu_usage()
    used_gb, total_gb, ram_pct = get_ram_info()
    return {
        "hostname": socket.gethostname(),
        "platform": platform.system(),
        "cpu_temp_celsius": temp,
        "cpu_usage_percent": cpu,
        "ram_used_gb": used_gb,
        "ram_total_gb": total_gb,
        "ram_usage_percent": ram_pct,
        "cpu_limit_percent": 100,
        "timestamp": _now_iso(),
        "agent_version": "linux-1.1",
    }


def _tail_jsonl(path: Path, limit: int = 40) -> list[dict]:
    if not path.exists():
        return []
    rows: list[dict] = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines()[-limit:]:
        if not line.strip():
            continue
        try:
            rows.append(json.loads(line))
        except Exception:
            pass
    return rows


def build_outage_forensics_report() -> dict:
    global last_network_snapshot
    snap = dict(last_network_snapshot) if last_network_snapshot else collect_network_snapshot()
    heartbeat = ""
    if HEARTBEAT_FILE.exists():
        heartbeat = HEARTBEAT_FILE.read_text(encoding="utf-8", errors="replace").strip()[-500:]
    with metrics_lock:
        metrics = dict(cached_metrics)
    return {
        "schema": "clawstack.linux_outage_forensics.v1",
        "generated_at": _now_iso(),
        "hostname": socket.gethostname(),
        "network_snapshot_now": snap,
        "network_telemetry_tail": _tail_jsonl(NETWORK_LOG, 60),
        "diagnostic_status": _tail_jsonl(DIAG_LOG, 20),
        "keepalive_heartbeat": heartbeat,
        "metrics_now": metrics,
    }


def metrics_updater_loop():
    global cached_metrics, last_network_snapshot
    tick = 0
    while True:
        try:
            m = collect_metrics()
            with metrics_lock:
                cached_metrics = m
            tick += 1
            if tick % 6 == 0:
                snap = collect_network_snapshot()
                last_network_snapshot = snap
                _append_jsonl(NETWORK_LOG, snap)
                _append_jsonl(
                    DIAG_LOG,
                    {
                        "schema": "clawstack.linux_node_diagnostic.v1",
                        "timestamp": _now_iso(),
                        "network": snap,
                        "metrics": m,
                    },
                )
                HEARTBEAT_FILE.parent.mkdir(parents=True, exist_ok=True)
                HEARTBEAT_FILE.write_text(f"{_now_iso()} host={socket.gethostname()}\n", encoding="utf-8")
        except Exception:
            pass
        time.sleep(UPDATE_INTERVAL)


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def do_GET(self):
        path = self.path.split("?")[0]
        if path in ("/metrics", "/"):
            with metrics_lock:
                data = dict(cached_metrics)
            body = json.dumps(data, ensure_ascii=False).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(body)
        elif path == "/health":
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"ok")
        elif path == "/diagnostics":
            with metrics_lock:
                data = dict(cached_metrics)
            body = json.dumps({"status": "ok", "metrics": data, "network": last_network_snapshot}, ensure_ascii=False).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(body)
        elif path in ("/diagnostics/outage_forensics", "/outage_forensics"):
            payload = build_outage_forensics_report()
            body = json.dumps(payload, ensure_ascii=False).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(body)
        else:
            self.send_response(404)
            self.end_headers()


if __name__ == "__main__":
    DATA_ROOT.mkdir(parents=True, exist_ok=True)
    with metrics_lock:
        cached_metrics = collect_metrics()
        last_network_snapshot = collect_network_snapshot()

    t = threading.Thread(target=metrics_updater_loop, daemon=True)
    t.start()

    server = ThreadingHTTPServer(("0.0.0.0", PORT), Handler)
    print(f"monitor_agent_linux listening on :{PORT}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
