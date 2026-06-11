#!/usr/bin/env python3
"""monitor_agent_linux.py — Clawstack fleet monitor agent for Linux nodes.
Serves the same JSON schema as the Windows monitor_agent on port 8111.
"""
import json
import os
import platform
import socket
import subprocess
import time
import threading
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

PORT = int(os.environ.get("MONITOR_AGENT_PORT", "8111"))
UPDATE_INTERVAL = 10

cached_metrics: dict = {}
metrics_lock = threading.Lock()


def get_cpu_temp() -> float | None:
    # Method 1: /sys/class/thermal thermal zones — pick the highest non-ambient reading
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
        # Prefer x86_pkg_temp (Intel CPU package), then coretemp, then highest
        for label, val in temps:
            if "pkg" in label.lower() or "package" in label.lower():
                return round(val, 1)
        for label, val in temps:
            if "core" in label.lower() or "cpu" in label.lower():
                return round(val, 1)
        return round(max(v for _, v in temps), 1)

    # Method 2: sensors command
    try:
        out = subprocess.check_output(
            ["sensors", "-j"], text=True, timeout=5, stderr=subprocess.DEVNULL
        )
        data = json.loads(out)
        best = None
        for chip, sensors in data.items():
            if not isinstance(sensors, dict):
                continue
            for sname, sdata in sensors.items():
                if not isinstance(sdata, dict):
                    continue
                for k, v in sdata.items():
                    if "input" in k and isinstance(v, (int, float)):
                        if 20.0 < v < 110.0:
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
    # Fallback: /proc/stat
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
        "timestamp": datetime.now().isoformat(),
        "agent_version": "linux-1.0",
    }


def metrics_updater_loop():
    global cached_metrics
    while True:
        try:
            m = collect_metrics()
            with metrics_lock:
                cached_metrics = m
        except Exception:
            pass
        time.sleep(UPDATE_INTERVAL)


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass  # suppress access logs

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
            body = json.dumps({"status": "ok", "metrics": data}, ensure_ascii=False).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(body)
        else:
            self.send_response(404)
            self.end_headers()


if __name__ == "__main__":
    # Initial metrics collection (blocking)
    with metrics_lock:
        cached_metrics = collect_metrics()

    t = threading.Thread(target=metrics_updater_loop, daemon=True)
    t.start()

    server = ThreadingHTTPServer(("0.0.0.0", PORT), Handler)
    print(f"monitor_agent_linux listening on :{PORT}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
