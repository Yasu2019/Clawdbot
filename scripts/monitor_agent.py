import sys
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import os
import json
import socket
import platform
import subprocess
import ctypes
import time
import threading
import urllib.error
import urllib.request
import re
import winreg
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

LHM_DATA_URL = os.environ.get("LHM_HTTP_URL", "http://127.0.0.1:8085/data.json")
PROGRAMDATA_ROOT = os.environ.get("PROGRAMDATA") or os.environ.get("TEMP") or r"C:\Temp"
FLEET_EVIDENCE_ROOT = os.environ.get(
    "FLEET_EVIDENCE_DIR",
    os.path.join(PROGRAMDATA_ROOT, "Clawstack", "monitor_agent", "fleet_evidence"),
)
FLEET_EVIDENCE_URL = os.environ.get("FLEET_EVIDENCE_URL", "http://100.119.18.40:8113/fleet_evidence")
FLEET_EVIDENCE_INTERVAL_SEC = int(os.environ.get("FLEET_EVIDENCE_INTERVAL_SEC", "300"))
FLEET_EVIDENCE_UPLOAD_ENABLED = os.environ.get("FLEET_EVIDENCE_UPLOAD", "1").strip().lower() not in (
    "0",
    "false",
    "no",
)
FLEET_EVIDENCE_MAX_POST_BYTES = 2 * 1024 * 1024

# RAM取得のためのctypes構造体
class MEMORYSTATUSEX(ctypes.Structure):
    _fields_ = [
        ("dwLength", ctypes.c_ulong),
        ("dwMemoryLoad", ctypes.c_ulong),
        ("ullTotalPhys", ctypes.c_ulonglong),
        ("ullAvailPhys", ctypes.c_ulonglong),
        ("ullTotalPageFile", ctypes.c_ulonglong),
        ("ullAvailPageFile", ctypes.c_ulonglong),
        ("ullTotalVirtual", ctypes.c_ulonglong),
        ("ullAvailVirtual", ctypes.c_ulonglong),
        ("sullAvailExtendedVirtual", ctypes.c_ulonglong),
    ]

def get_cpu_usage():
    try:
        # wmic is deprecated/removed in newer Windows 11. Use Get-CimInstance via PowerShell.
        # CREATE_NO_WINDOW (0x08000000) を指定して裏側でのフリーズを完全に防ぐ
        out = subprocess.check_output(
            ["powershell", "-NoProfile", "-Command", "Get-CimInstance Win32_Processor | Measure-Object -Property LoadPercentage -Average | Select-Object -ExpandProperty Average"],
            text=True,
            creationflags=0x08000000,
            timeout=5
        )
        val = out.strip()
        if val.isdigit() or val.replace('.', '', 1).isdigit():
            return float(val)
    except:
        pass
    return 0.0

def get_ram_info():
    try:
        stat = MEMORYSTATUSEX()
        stat.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
        ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(stat))
        
        total_gb = stat.ullTotalPhys / (1024**3)
        free_gb = stat.ullAvailPhys / (1024**3)
        used_gb = total_gb - free_gb
        percent = (used_gb / total_gb) * 100 if total_gb > 0 else 0
        return round(used_gb, 2), round(total_gb, 2), round(percent, 1)
    except:
        pass
    return 0.0, 0.0, 0.0


def get_cpu_hardware_info():
    fallback = _get_cpu_hardware_info_from_registry()
    try:
        script = (
            "$cpu=Get-CimInstance Win32_Processor | "
            "Select-Object Name,NumberOfCores,NumberOfLogicalProcessors,MaxClockSpeed,CurrentClockSpeed;"
            "$cpu | ConvertTo-Json -Depth 4 -Compress"
        )
        out = subprocess.check_output(
            ["powershell", "-NoProfile", "-Command", script],
            text=True,
            encoding="utf-8",
            errors="replace",
            creationflags=0x08000000,
            timeout=8,
        ).strip()
        if not out:
            return fallback
        data = json.loads(out)
        cpus = data if isinstance(data, list) else [data]
        cores = sum(int(c.get("NumberOfCores") or 0) for c in cpus)
        threads = sum(int(c.get("NumberOfLogicalProcessors") or 0) for c in cpus)
        max_clock = max((int(c.get("MaxClockSpeed") or 0) for c in cpus), default=0)
        current_clock = max((int(c.get("CurrentClockSpeed") or 0) for c in cpus), default=0)
        names = [str(c.get("Name") or "").strip() for c in cpus if c.get("Name")]
        return {
            "cpu_name": names[0] if names else platform.processor(),
            "cpu_physical_cores": cores or None,
            "cpu_logical_threads": threads or None,
            "cpu_max_clock_mhz": max_clock or None,
            "cpu_current_clock_mhz": current_clock or None,
        }
    except Exception as exc:
        fallback["cpu_hardware_error"] = str(exc)
        return fallback


def _get_cpu_hardware_info_from_registry():
    info = {
        "cpu_name": platform.processor() or None,
        "cpu_physical_cores": None,
        "cpu_logical_threads": os.cpu_count(),
        "cpu_max_clock_mhz": None,
        "cpu_current_clock_mhz": None,
    }
    try:
        key = winreg.OpenKey(
            winreg.HKEY_LOCAL_MACHINE,
            r"HARDWARE\DESCRIPTION\System\CentralProcessor\0",
        )
        try:
            info["cpu_name"] = str(winreg.QueryValueEx(key, "ProcessorNameString")[0]).strip()
        except OSError:
            pass
        try:
            mhz = int(winreg.QueryValueEx(key, "~MHz")[0])
            info["cpu_current_clock_mhz"] = mhz
            info["cpu_max_clock_mhz"] = mhz
        except OSError:
            pass
        winreg.CloseKey(key)
    except Exception as exc:
        info["cpu_hardware_error"] = str(exc)
    return info


CPU_HARDWARE_INFO = get_cpu_hardware_info()


def get_cpu_current_clock_mhz():
    try:
        out = subprocess.check_output(
            [
                "powershell",
                "-NoProfile",
                "-Command",
                "(Get-CimInstance Win32_Processor | Measure-Object -Property CurrentClockSpeed -Maximum).Maximum",
            ],
            text=True,
            creationflags=0x08000000,
            timeout=5,
        ).strip()
        if out and out.replace(".", "", 1).isdigit():
            return int(float(out))
    except Exception:
        pass
    return CPU_HARDWARE_INFO.get("cpu_current_clock_mhz")


def ensure_cpu_hardware_metrics():
    if cached_metrics.get("cpu_name") and cached_metrics.get("cpu_logical_threads"):
        return
    info = get_cpu_hardware_info()
    for key in (
        "cpu_name",
        "cpu_physical_cores",
        "cpu_logical_threads",
        "cpu_max_clock_mhz",
        "cpu_current_clock_mhz",
        "cpu_hardware_error",
    ):
        if info.get(key) is not None:
            cached_metrics[key] = info.get(key)


def _lhm_parse_number(value):
    """Parse LHM JSON Value fields (float or strings like '86.0 C' / '99.2 %')."""
    if value is None or value == "":
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        m = re.search(r"(-?\d+(?:\.\d+)?)", value.replace(",", "."))
        if m:
            return float(m.group(1))
    return None


def _lhm_sensor_type(node):
    """LHM uses 'Type' in web JSON; older builds may use SensorType."""
    raw = node.get("Type")
    if raw is None:
        raw = node.get("SensorType")
    if raw is None:
        return ""
    return str(raw)


def _lhm_is_temperature(node, parent_text=""):
    st = _lhm_sensor_type(node)
    if st == "Temperature" or st == "2":
        return True
    if parent_text == "Temperatures":
        return True
    sid = str(node.get("SensorId") or "")
    if "/temperature/" in sid.lower():
        return True
    return False


def _lhm_is_load(node, parent_text=""):
    st = _lhm_sensor_type(node)
    if st == "Load" or st == "6":
        return True
    if parent_text == "Load":
        return True
    sid = str(node.get("SensorId") or "")
    return "/load/" in sid.lower()


def _lhm_walk_sensors(node, temps, disk_warnings, ctx_device="", parent_text=""):
    text = (node.get("Text") or "").strip()
    st = _lhm_sensor_type(node)
    val = _lhm_parse_number(node.get("Value"))
    if val is None:
        val = _lhm_parse_number(node.get("RawValue"))
    children = node.get("Children") or []

    if text and not st and children and text not in ("Sensor", "Temperatures", "Load", "Data"):
        if any(_lhm_sensor_type(c) == "Temperatures" or c.get("Text") == "Temperatures" for c in children):
            ctx_device = text
        elif any(c.get("Text") == "Temperatures" for c in children):
            ctx_device = text

    if _lhm_is_temperature(node, parent_text) and val is not None and val > 0:
        if "Distance to TjMax" not in text and "Resolution" not in text and "Limit" not in text:
            temps.append({"name": text, "c": round(float(val), 1), "device": ctx_device})

    if text == "Used Space" and _lhm_is_load(node, parent_text) and val is not None and val >= 90:
        disk_warnings.append({"device": ctx_device, "used_pct": round(float(val), 1)})

    next_parent = text if text in ("Temperatures", "Load") else parent_text
    for child in children:
        _lhm_walk_sensors(child, temps, disk_warnings, ctx_device, next_parent)


def get_lhm_metrics():
    """Read CPU/storage sensors from LibreHardwareMonitor Remote Web Server."""
    try:
        req = urllib.request.Request(LHM_DATA_URL, headers={"User-Agent": "monitor_agent/1"})
        with urllib.request.urlopen(req, timeout=8) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError) as exc:
        return {"ok": False, "error": str(exc), "url": LHM_DATA_URL}

    temps = []
    disk_warnings = []
    for top in data.get("Children") or []:
        _lhm_walk_sensors(top, temps, disk_warnings)

    by_name = {t["name"]: t["c"] for t in temps}
    cpu_package = by_name.get("CPU Package")
    core_max = by_name.get("Core Max")
    core_avg = by_name.get("Core Average")
    primary = cpu_package or core_max
    if primary is None:
        cpu_candidates = [
            t["c"] for t in temps
            if any(k in t["name"] for k in ("Core", "CPU Package", "CPU"))
            and "DIMM" not in t["name"]
        ]
        if cpu_candidates:
            primary = max(cpu_candidates)
        elif temps:
            primary = max(t["c"] for t in temps)

    if primary is None:
        return {
            "ok": False,
            "error": "no_cpu_temperatures_in_json",
            "url": LHM_DATA_URL,
            "temp_sensor_count": len(temps),
        }

    nvme_temps = [
        t for t in temps
        if any(k in t["name"] for k in ("Composite", "Temperature #"))
        or (t.get("device") and "SSD" in str(t.get("device")))
    ]

    return {
        "ok": True,
        "cpu_temp_c": round(primary, 1),
        "cpu_package_c": cpu_package,
        "core_max_c": core_max,
        "core_avg_c": core_avg,
        "nvme_temps": nvme_temps[:8],
        "disk_warnings": disk_warnings,
        "source": "lhm_http",
        "url": LHM_DATA_URL,
    }


def get_cpu_temp():
    lhm = get_lhm_metrics()
    if lhm.get("ok") and lhm.get("cpu_temp_c") is not None:
        return lhm["cpu_temp_c"]
    return _get_cpu_temp_fallback()


def _get_cpu_temp_fallback():
    temp_dir = os.environ.get('TEMP', 'C:\\')
    log_path = os.path.join(temp_dir, 'monitor_agent_debug.log')

    def _parse_kelvin_tenths(out):
        """tenths-of-Kelvin形式の出力をCelsiusにパースする"""
        temps = []
        for line in out.strip().split('\n'):
            val = line.strip()
            if val.replace('.', '', 1).isdigit():
                k_tenths = float(val)
                if k_tenths > 2000:  # 最低でも200K以上が有効
                    c = (k_tenths / 10.0) - 273.15
                    if -10 < c < 120:
                        temps.append(c)
        return temps

    # Method 1: Performance Counter (管理者権限不要)
    # try/catchをPS側にも入れてタスクスケジューラ実行時の終了コード-1を防ぐ
    try:
        out = subprocess.check_output(
            ["powershell", "-NoProfile", "-Command",
             "try {"
             " Get-Counter -Counter '\\Thermal Zone Information(*)\\Temperature'"
             " -ErrorAction SilentlyContinue"
             " | Select-Object -ExpandProperty CounterSamples"
             " | Select-Object -ExpandProperty CookedValue"
             "} catch {}"],
            text=True, creationflags=0x08000000, timeout=10
        )
        temps = []
        for line in out.strip().split('\n'):
            val = line.strip()
            if val.replace('.', '', 1).isdigit():
                k = float(val)
                if k > 200:
                    temps.append(k - 273.15)
        if temps:
            return round(max(temps), 1)
    except Exception as e:
        try:
            with open(log_path, "a") as df:
                df.write(f"[TempM1] {e}\n")
        except:
            pass

    # Method 2: WMI MSAcpi_ThermalZoneTemperature (tenths of Kelvin)
    try:
        out = subprocess.check_output(
            ["powershell", "-NoProfile", "-Command",
             "Get-CimInstance -Namespace 'root\\wmi'"
             " -Class MSAcpi_ThermalZoneTemperature"
             " -ErrorAction SilentlyContinue"
             " | Select-Object -ExpandProperty CurrentTemperature"],
            text=True, creationflags=0x08000000, timeout=6
        )
        temps = _parse_kelvin_tenths(out)
        if temps:
            return round(max(temps), 1)
    except Exception as e:
        try:
            with open(log_path, "a") as df:
                df.write(f"[TempM2] {e}\n")
        except:
            pass

    # Method 3: Win32_TemperatureProbe (tenths of Celsius, サーバ向けIPMI)
    try:
        out = subprocess.check_output(
            ["powershell", "-NoProfile", "-Command",
             "Get-CimInstance -ClassName Win32_TemperatureProbe"
             " -ErrorAction SilentlyContinue"
             " | Where-Object { $_.CurrentReading -gt 0 }"
             " | Select-Object -ExpandProperty CurrentReading"],
            text=True, creationflags=0x08000000, timeout=6
        )
        temps = []
        for line in out.strip().split('\n'):
            val = line.strip()
            if val.replace('.', '', 1).isdigit():
                celsius = float(val) / 10.0
                if 0 < celsius < 120:
                    temps.append(celsius)
        if temps:
            return round(max(temps), 1)
    except Exception:
        pass

    # Method 4: High Precision Temperature Performance Counter (tenths of Kelvin)
    try:
        out = subprocess.check_output(
            ["powershell", "-NoProfile", "-Command",
             "Get-Counter -Counter '\\Thermal Zone Information(*)\\High Precision Temperature'"
             " -ErrorAction SilentlyContinue"
             " | Select-Object -ExpandProperty CounterSamples"
             " | Select-Object -ExpandProperty CookedValue"],
            text=True, creationflags=0x08000000, timeout=8
        )
        temps = _parse_kelvin_tenths(out)
        if temps:
            return round(max(temps), 1)
    except Exception:
        pass

    # Method 5: psutil (LibreHardwareMonitor/OpenHardwareMonitor がサービス起動中なら使える)
    try:
        import psutil
        all_temps = psutil.sensors_temperatures()
        if all_temps:
            candidates = [
                e.current for entries in all_temps.values()
                for e in entries if e.current and 0 < e.current < 120
            ]
            if candidates:
                return round(max(candidates), 1)
    except Exception:
        pass

    # Method 6: LibreHardwareMonitor WMI namespace
    try:
        out = subprocess.check_output(
            ["powershell", "-NoProfile", "-Command",
             "Get-CimInstance -Namespace 'root\\LibreHardwareMonitor' -Class Sensor"
             " -ErrorAction SilentlyContinue"
             " | Where-Object { $_.SensorType -eq 'Temperature' -and $_.Value -gt 0 }"
             " | Select-Object -ExpandProperty Value"],
            text=True, creationflags=0x08000000, timeout=6
        )
        temps = []
        for line in out.strip().split('\n'):
            val = line.strip()
            if val.replace('.', '', 1).isdigit():
                celsius = float(val)
                if 0 < celsius < 120:
                    temps.append(celsius)
        if temps:
            return round(max(temps), 1)
    except Exception:
        pass

    # Method 7: LibreHardwareMonitorLib.dll を直接ロード（管理者権限で実行時のみ有効）
    lhm_dll = r"C:\LibreHardwareMonitor\LibreHardwareMonitorLib.dll"
    if os.path.exists(lhm_dll):
        try:
            ps_cmd = (
                f"Add-Type -Path '{lhm_dll}';"
                "$c=[LibreHardwareMonitor.Hardware.Computer]::new();"
                "$c.IsCpuEnabled=$true; $c.Open();"
                "foreach($hw in $c.Hardware){"
                " $hw.Update();"
                " foreach($s in $hw.Sensors){"
                "  if($s.SensorType -eq [LibreHardwareMonitor.Hardware.SensorType]::Temperature -and $s.Value -gt 0)"
                "  { Write-Output $s.Value }"
                " }"
                "} $c.Close()"
            )
            out = subprocess.check_output(
                ["powershell", "-NoProfile", "-Command", ps_cmd],
                text=True, creationflags=0x08000000, timeout=12
            )
            temps = []
            for line in out.strip().split('\n'):
                val = line.strip()
                if val.replace('.', '', 1).isdigit():
                    celsius = float(val)
                    if 0 < celsius < 120:
                        temps.append(celsius)
            if temps:
                return round(max(temps), 1)
        except Exception:
            pass

    return None

# サーマルスロットリング - 多段階制御 (LHM 必須 -- INC-096/T029)
# (閾値°C以上, CPU最大%, ラベル) を高温順に列挙
THERMAL_STEPS = [
    (95.0, 10, "CRITICAL"),  # 95°C以上 -> 10%
    (85.0, 30, "WARNING"),   # 85°C以上 -> 30%
    (80.0, 50, "WARM"),      # 80°C以上 -> 50% (K10 平常 84°C 付近で先行抑制)
]
THERMAL_RECOVER_C = 72.0  # 72°C未満で正常復帰 (ヒステリシス)
NORMAL_PERCENT = 100
THERMAL_POLL_SEC = 10
THERMAL_THROTTLE_ENABLED = os.environ.get("THERMAL_THROTTLE_ENABLED", "1").strip() not in ("0", "false", "False")

is_throttling = False
current_cpu_limit = NORMAL_PERCENT
thermal_throttle_label = "NORMAL"

cached_metrics = {
    "hostname": socket.gethostname(),
    "os": platform.system(),
    "cpu_name": CPU_HARDWARE_INFO.get("cpu_name"),
    "cpu_physical_cores": CPU_HARDWARE_INFO.get("cpu_physical_cores"),
    "cpu_logical_threads": CPU_HARDWARE_INFO.get("cpu_logical_threads"),
    "cpu_max_clock_mhz": CPU_HARDWARE_INFO.get("cpu_max_clock_mhz"),
    "cpu_current_clock_mhz": CPU_HARDWARE_INFO.get("cpu_current_clock_mhz"),
    "cpu_hardware_error": CPU_HARDWARE_INFO.get("cpu_hardware_error"),
    "cpu_usage_percent": 0.0,
    "ram_usage_percent": 0.0,
    "ram_used_gb": 0.0,
    "ram_total_gb": 0.0,
    "cpu_temp_celsius": None,
    "cpu_package_c": None,
    "core_max_c": None,
    "core_avg_c": None,
    "nvme_temps": [],
    "disk_warnings": [],
    "temp_source": None,
    "lhm_ok": False,
    "lhm_error": None,
    "is_throttling": False,
    "cpu_limit_percent": 100,
    "thermal_throttle_label": "NORMAL",
    "thermal_control_temp_c": None,
}

updater_logs = []
def log_debug(msg):
    updater_logs.append(f"[{datetime.now()}] {msg}")
    if len(updater_logs) > 50:
        updater_logs.pop(0)


def _run_powershell_json(script, timeout=15):
    try:
        out = subprocess.check_output(
            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", script],
            text=True,
            encoding="utf-8",
            errors="replace",
            creationflags=0x08000000,
            timeout=timeout,
        )
        text = out.strip()
        if not text:
            return None
        return json.loads(text)
    except Exception as exc:
        return {"error": str(exc)}


def _collect_windows_shutdown_events():
    script = (
        "$ids=41,42,1074,6005,6006,6008,109,1;"
        "$start=(Get-Date).AddHours(-48);"
        "$events=Get-WinEvent -FilterHashtable @{LogName='System'; Id=$ids; StartTime=$start} "
        "-MaxEvents 60 -ErrorAction SilentlyContinue | "
        "Select-Object TimeCreated,Id,ProviderName,LevelDisplayName,Message;"
        "$events | ConvertTo-Json -Depth 4 -Compress"
    )
    events = _run_powershell_json(script, timeout=20)
    if events is None:
        return []
    if isinstance(events, dict):
        if "error" in events:
            return events
        return [events]
    return events


def _collect_power_snapshot():
    script = (
        "$os=Get-CimInstance Win32_OperatingSystem | "
        "Select-Object LastBootUpTime,LocalDateTime;"
        "$cs=Get-CimInstance Win32_ComputerSystem | "
        "Select-Object Manufacturer,Model,PowerState,ThermalState;"
        "$battery=Get-CimInstance Win32_Battery -ErrorAction SilentlyContinue | "
        "Select-Object Name,EstimatedChargeRemaining,BatteryStatus,Status;"
        "[PSCustomObject]@{os=$os; computer=$cs; battery=$battery} | "
        "ConvertTo-Json -Depth 5 -Compress"
    )
    snapshot = _run_powershell_json(script, timeout=15)
    return snapshot if snapshot is not None else {}


def _collect_tailscale_status():
    candidates = [
        r"C:\Program Files\Tailscale\tailscale.exe",
        r"C:\Program Files (x86)\Tailscale\tailscale.exe",
    ]
    tailscale = next((path for path in candidates if os.path.exists(path)), None)
    if not tailscale:
        return {"available": False, "reason": "tailscale.exe_not_found"}
    try:
        out = subprocess.check_output(
            [tailscale, "status", "--json"],
            text=True,
            encoding="utf-8",
            errors="replace",
            creationflags=0x08000000,
            timeout=10,
        )
        return json.loads(out)
    except Exception as exc:
        return {"available": True, "error": str(exc)}


def _safe_hostname(value):
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", str(value or "unknown"))[:80]


def _write_evidence_jsonl(snapshot, subdir=None):
    host = _safe_hostname(snapshot.get("hostname") or socket.gethostname())
    day = datetime.now().strftime("%Y%m%d")
    parts = [FLEET_EVIDENCE_ROOT]
    if subdir:
        parts.append(_safe_hostname(subdir))
    parts.append(host)
    evidence_dir = os.path.join(*parts)
    os.makedirs(evidence_dir, exist_ok=True)
    path = os.path.join(evidence_dir, f"evidence_{day}.jsonl")
    with open(path, "a", encoding="utf-8", errors="replace") as f:
        json.dump(snapshot, f, ensure_ascii=False, separators=(",", ":"))
        f.write("\n")
    return path


def _build_fleet_evidence(reason="periodic"):
    metrics = dict(cached_metrics)
    return {
        "schema": "clawstack.fleet_evidence.v1",
        "reason": reason,
        "hostname": socket.gethostname(),
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "metrics": metrics,
        "recent_agent_logs": list(updater_logs[-20:]),
        "windows_shutdown_events_48h": _collect_windows_shutdown_events(),
        "power_snapshot": _collect_power_snapshot(),
        "tailscale_status": _collect_tailscale_status(),
    }


def _upload_fleet_evidence(snapshot):
    if not FLEET_EVIDENCE_UPLOAD_ENABLED or not FLEET_EVIDENCE_URL:
        return {"enabled": False}
    try:
        payload = json.dumps(snapshot, ensure_ascii=False).encode("utf-8")
        req = urllib.request.Request(
            FLEET_EVIDENCE_URL,
            data=payload,
            headers={"Content-Type": "application/json", "User-Agent": "monitor_agent/1"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=12) as resp:
            body = resp.read(512).decode("utf-8", errors="replace")
            return {"ok": True, "status": resp.status, "body": body}
    except Exception as exc:
        return {"ok": False, "error": str(exc), "url": FLEET_EVIDENCE_URL}


def fleet_evidence_loop():
    while True:
        try:
            snapshot = _build_fleet_evidence("periodic")
            local_path = _write_evidence_jsonl(snapshot, subdir="local")
            upload_status = _upload_fleet_evidence(snapshot)
            cached_metrics["fleet_evidence"] = {
                "last_local_path": local_path,
                "last_upload": upload_status,
                "last_at": snapshot["timestamp"],
                "url": FLEET_EVIDENCE_URL,
            }
            log_debug(f"Fleet evidence saved: {local_path}; upload={upload_status}")
        except Exception as exc:
            cached_metrics["fleet_evidence"] = {"error": str(exc), "last_at": datetime.now().isoformat()}
            log_debug(f"Fleet evidence loop error: {exc}")
        time.sleep(max(60, FLEET_EVIDENCE_INTERVAL_SEC))


def _thermal_control_temp_from_cache(metrics):
    """LHM 時は core_max / cpu_package の最大値で制御 (fallback 温度は使わない)."""
    if not metrics.get("lhm_ok"):
        return None
    candidates = []
    for key in ("core_max_c", "cpu_package_c", "cpu_temp_celsius"):
        val = metrics.get(key)
        if isinstance(val, (int, float)) and val > 0:
            candidates.append(float(val))
    return round(max(candidates), 1) if candidates else None


def metrics_updater_loop():
    global cached_metrics
    while True:
        try:
            used_gb, total_gb, ram_percent = get_ram_info()
            cpu_usage = get_cpu_usage()
            lhm = get_lhm_metrics()
            lhm_ok = bool(lhm.get("ok"))
            cpu_temp = lhm["cpu_temp_c"] if lhm_ok else _get_cpu_temp_fallback()
            log_debug(f"Metrics check: cpu_usage={cpu_usage}, cpu_temp={cpu_temp}, lhm_ok={lhm_ok}")

            cached_metrics["cpu_usage_percent"] = cpu_usage
            cached_metrics["cpu_current_clock_mhz"] = get_cpu_current_clock_mhz()
            cached_metrics["ram_usage_percent"] = ram_percent
            cached_metrics["ram_used_gb"] = used_gb
            cached_metrics["ram_total_gb"] = total_gb
            cached_metrics["cpu_temp_celsius"] = cpu_temp
            cached_metrics["cpu_package_c"] = lhm.get("cpu_package_c") if lhm_ok else None
            cached_metrics["core_max_c"] = lhm.get("core_max_c") if lhm_ok else None
            cached_metrics["core_avg_c"] = lhm.get("core_avg_c") if lhm_ok else None
            cached_metrics["nvme_temps"] = lhm.get("nvme_temps", []) if lhm_ok else []
            cached_metrics["disk_warnings"] = lhm.get("disk_warnings", []) if lhm_ok else []
            cached_metrics["temp_source"] = lhm.get("source") if lhm_ok else ("fallback" if cpu_temp is not None else None)
            cached_metrics["lhm_ok"] = lhm_ok
            cached_metrics["lhm_error"] = None if lhm_ok else lhm.get("error")
            cached_metrics["is_throttling"] = is_throttling
            cached_metrics["cpu_limit_percent"] = current_cpu_limit
            cached_metrics["thermal_throttle_label"] = thermal_throttle_label
            cached_metrics["thermal_control_temp_c"] = _thermal_control_temp_from_cache(cached_metrics)
        except Exception as e:
            log_debug(f"Loop error: {e}")
            print("Error in metrics updater:", e)
        time.sleep(15)

def set_cpu_limit(percent):
    """Windows 電源設定で CPU 最大動作状態 (PROCTHROTTLEMAX) を強制変更."""
    percent = max(5, min(100, int(percent)))
    try:
        cmds = [
            ["powercfg", "-setacvalueindex", "SCHEME_CURRENT", "SUB_PROCESSOR", "PROCTHROTTLEMAX", str(percent)],
            ["powercfg", "-setdcvalueindex", "SCHEME_CURRENT", "SUB_PROCESSOR", "PROCTHROTTLEMAX", str(percent)],
            ["powercfg", "-setactive", "SCHEME_CURRENT"],
        ]
        for cmd in cmds:
            subprocess.check_output(cmd, text=True, creationflags=0x08000000, timeout=5)
        log_debug(f"set_cpu_limit OK -> {percent}%")
        return True
    except Exception as exc:
        log_debug(f"set_cpu_limit FAILED -> {percent}%: {exc}")
        print(f"[Thermal] powercfg failed at {percent}%: {exc}")
        return False


def thermal_watchdog_loop():
    global is_throttling, current_cpu_limit, thermal_throttle_label
    while True:
        if not THERMAL_THROTTLE_ENABLED:
            time.sleep(THERMAL_POLL_SEC)
            continue

        temp = _thermal_control_temp_from_cache(cached_metrics)
        if temp is not None:
            target_limit = NORMAL_PERCENT
            target_label = "NORMAL"
            for threshold, limit, label in THERMAL_STEPS:
                if temp >= threshold:
                    target_limit = limit
                    target_label = label
                    break

            if current_cpu_limit < NORMAL_PERCENT and target_limit == NORMAL_PERCENT:
                if temp > THERMAL_RECOVER_C:
                    target_limit = current_cpu_limit
                    target_label = "HOLD"

            if target_limit != current_cpu_limit:
                if set_cpu_limit(target_limit):
                    current_cpu_limit = target_limit
                    is_throttling = target_limit < NORMAL_PERCENT
                    thermal_throttle_label = target_label
                    print(
                        f"[{datetime.now()}] Thermal [{target_label}]: "
                        f"{temp:.1f}C -> CPU max {target_limit}% (lhm_http)"
                    )
                    log_debug(f"Thermal throttle {target_label} {temp}C -> {target_limit}%")

        time.sleep(THERMAL_POLL_SEC)

def harvester_watchdog_loop():
    becky_script = r"D:\Clawdbot_Docker_20260125\scripts\asus_becky_harvester.py"
    gmail_script = r"D:\Clawdbot_Docker_20260125\data\workspace\run_priority_gmail_backfill.py"
    if not os.path.exists(becky_script) and not os.path.exists(gmail_script):
        return  # K10以外のノードでは不要
    becky_proc = None
    gmail_proc = None
    while True:
        try:
            if os.path.exists(becky_script) and (becky_proc is None or becky_proc.poll() is not None):
                becky_proc = subprocess.Popen(["python", becky_script])
            if os.path.exists(gmail_script) and (gmail_proc is None or gmail_proc.poll() is not None):
                gmail_proc = subprocess.Popen(["python", gmail_script])
        except Exception as e:
            print("Error in harvester watchdog:", e)
        time.sleep(600)

class MetricsHandler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'X-Requested-With, Content-Type')
        self.end_headers()

    def do_GET(self):
        if self.path == "/metrics":
            ensure_cpu_hardware_metrics()
            cached_metrics["hostname"] = socket.gethostname()
            cached_metrics["os"] = platform.system()
            
            response = json.dumps(cached_metrics).encode('utf-8')
            
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Content-Length', str(len(response)))
            self.end_headers()
            self.wfile.write(response)
        elif self.path == "/debug":
            debug_info = {
                "cached_metrics": cached_metrics,
                "updater_logs": updater_logs
            }
            response = json.dumps(debug_info).encode('utf-8')
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Content-Length', str(len(response)))
            self.end_headers()
            self.wfile.write(response)
        elif self.path == "/download_db":
            db_path = r"D:\Clawdbot_Docker_20260125\data\workspace\universal_growth.db"
            if os.path.exists(db_path):
                file_size = os.path.getsize(db_path)
                self.send_response(200)
                self.send_header('Content-Type', 'application/octet-stream')
                self.send_header('Content-Disposition', 'attachment; filename="universal_growth.db"')
                self.send_header('Content-Length', str(file_size))
                self.end_headers()
                with open(db_path, 'rb') as f:
                    self.wfile.write(f.read())
            else:
                self.send_response(404)
                self.end_headers()
                self.wfile.write(b"Database file not found.")
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        if self.path == "/fleet_evidence":
            content_length = int(self.headers.get('Content-Length', 0))
            if content_length <= 0 or content_length > FLEET_EVIDENCE_MAX_POST_BYTES:
                self.send_response(400)
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(b"Invalid fleet evidence payload size.")
                return
            try:
                post_data = self.rfile.read(content_length).decode("utf-8", errors="replace")
                snapshot = json.loads(post_data)
                if not isinstance(snapshot, dict):
                    raise ValueError("payload must be a JSON object")
                snapshot.setdefault("received_at", datetime.now().isoformat(timespec="seconds"))
                snapshot.setdefault("receiver_hostname", socket.gethostname())
                saved_path = _write_evidence_jsonl(snapshot, subdir="received")
                response = json.dumps({"ok": True, "saved_path": saved_path}).encode("utf-8")
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.send_header('Content-Length', str(len(response)))
                self.end_headers()
                self.wfile.write(response)
            except Exception as exc:
                response = json.dumps({"ok": False, "error": str(exc)}).encode("utf-8")
                self.send_response(400)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.send_header('Content-Length', str(len(response)))
                self.end_headers()
                self.wfile.write(response)

        elif self.path == "/upload_eml":
            content_length = int(self.headers.get('Content-Length', 0))
            if content_length > 0:
                post_data = self.rfile.read(content_length)
                
                # Setup EML directory with hour-based subdirectories to avoid overloading a single folder
                hour_str = time.strftime('%Y%m%d_%H')
                eml_dir = rf"D:\Clawdbot_Docker_20260125\data\workspace\paperless_consume\email\vivobook\{hour_str}"
                os.makedirs(eml_dir, exist_ok=True)
                
                # Generate unique filename
                filename = f"vivobook_{int(time.time()*1000)}_{content_length}.eml"
                file_path = os.path.join(eml_dir, filename)
                
                # Save the raw EML data
                with open(file_path, 'wb') as f:
                    f.write(post_data)
                
                self.send_response(200)
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(b'EML uploaded successfully\n')
            else:
                self.send_response(400)
                self.end_headers()

        elif self.path == "/upload_harvest":
            content_length = int(self.headers.get('Content-Length', 0))
            if content_length > 0:
                post_data = self.rfile.read(content_length).decode('utf-8')
                
                # Setup inbox directory
                inbox_dir = r"D:\Clawdbot_Docker_20260125\data\workspace\knowledge_ingestion\inbox"
                os.makedirs(inbox_dir, exist_ok=True)
                
                # Generate unique filename
                filename = f"harvest_{socket.gethostname()}_{int(time.time())}.txt"
                file_path = os.path.join(inbox_dir, filename)
                
                # Save the harvested data
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(post_data)
                
                # Update Dashboard JSON
                try:
                    title = "Unknown Title"
                    keyword = "UNKNOWN"
                    content = ""
                    for line in post_data.split('\n'):
                        if line.startswith("TITLE:"): title = line.replace("TITLE:", "").strip()
                        elif line.startswith("KEYWORD:"): keyword = line.replace("KEYWORD:", "").strip()
                    
                    content_idx = post_data.find("CONTENT:")
                    if content_idx != -1:
                        content = post_data[content_idx+8:].strip()
                        
                    # Handle full transcripts separately
                    is_transcript = False
                    is_email = False
                    email_subject = ""
                    for line in post_data.split('\n'):
                        if line.startswith("TYPE:") and "YOUTUBE_TRANSCRIPT" in line:
                            is_transcript = True
                        elif line.startswith("TYPE:") and "INTERNAL_EMAIL" in line:
                            is_email = True
                        elif line.startswith("SUBJECT:"):
                            email_subject = line.replace("SUBJECT:", "").strip()
                    
                    if is_transcript:
                        transcript_dir = r"D:\Clawdbot_Docker_20260125\data\workspace\transcripts"
                        os.makedirs(transcript_dir, exist_ok=True)
                        ts_file = os.path.join(transcript_dir, f"transcript_{socket.gethostname()}_{int(time.time())}.txt")
                        with open(ts_file, 'w', encoding='utf-8') as f:
                            f.write(post_data)
                        print(f"[{datetime.now()}] Received full transcript, saved to {ts_file}")
                        # Skip adding full transcripts to dashboard to avoid clutter
                    elif is_email:
                        stats_path = r"D:\Clawdbot_Docker_20260125\data\workspace\apps\growth_dashboard\growth_stats.json"
                        if os.path.exists(stats_path):
                            with open(stats_path, 'r', encoding='utf-8') as sf:
                                stats = json.load(sf)
                                
                            new_entry = {
                                "domain": "INTERNAL_KNOWHOW",
                                "challenge": f"【Becky!過去メール】{email_subject}",
                                "know_how": content[:120] + "...",
                                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                            }
                            
                            if "recent_know_how" not in stats:
                                stats["recent_know_how"] = []
                            stats["recent_know_how"].insert(0, new_entry)
                            stats["recent_know_how"] = stats["recent_know_how"][:20]
                            
                            if "domain_stats" not in stats:
                                stats["domain_stats"] = {}
                            stats["domain_stats"]["INTERNAL_KNOWHOW"] = stats["domain_stats"].get("INTERNAL_KNOWHOW", 0) + 1
                            
                            try:
                                import sqlite3
                                db_path = r"D:\Clawdbot_Docker_20260125\data\workspace\universal_growth.db"
                                conn = sqlite3.connect(db_path)
                                conn.row_factory = sqlite3.Row
                                rows = conn.execute("SELECT date(timestamp) as day, COUNT(*) as count FROM growth_records WHERE timestamp >= date('now', '-30 days', 'localtime') GROUP BY day ORDER BY day ASC").fetchall()
                                stats["history"] = [{"day": r["day"], "count": r["count"]} for r in rows]
                                conn.close()
                            except Exception as e:
                                print(f"Error syncing history: {e}")

                            stats["updated_at"] = datetime.now().isoformat()
                            with open(stats_path, 'w', encoding='utf-8') as sf:
                                json.dump(stats, sf, indent=2, ensure_ascii=False)
                        print(f"[{datetime.now()}] Received internal email: {email_subject}")
                    else:
                        stats_path = r"D:\Clawdbot_Docker_20260125\data\workspace\apps\growth_dashboard\growth_stats.json"
                        if os.path.exists(stats_path):
                            with open(stats_path, 'r', encoding='utf-8') as sf:
                                stats = json.load(sf)
                                
                            # Format for dashboard
                            # Format for dashboard
                            domain_key = "IATF" if "IATF" in keyword else ("CAE_MATERIAL" if "Mold" in keyword else "GENERAL")
                            new_entry = {
                                "domain": domain_key,
                                "challenge": f"【Dynabook自動収集】{title}",
                                "know_how": content[:120] + "...",
                                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                            }
                            
                            if "recent_know_how" not in stats:
                                stats["recent_know_how"] = []
                            stats["recent_know_how"].insert(0, new_entry)
                            stats["recent_know_how"] = stats["recent_know_how"][:20] # keep latest 20
                            
                            if "domain_stats" not in stats:
                                stats["domain_stats"] = {}
                            stats["domain_stats"][domain_key] = stats["domain_stats"].get(domain_key, 0) + 1
                            
                            try:
                                import sqlite3
                                db_path = r"D:\Clawdbot_Docker_20260125\data\workspace\universal_growth.db"
                                conn = sqlite3.connect(db_path)
                                conn.row_factory = sqlite3.Row
                                rows = conn.execute("SELECT date(timestamp) as day, COUNT(*) as count FROM growth_records WHERE timestamp >= date('now', '-30 days', 'localtime') GROUP BY day ORDER BY day ASC").fetchall()
                                stats["history"] = [{"day": r["day"], "count": r["count"]} for r in rows]
                                conn.close()
                            except Exception as e:
                                print(f"Error syncing history: {e}")

                            stats["updated_at"] = datetime.now().isoformat()
                            
                            with open(stats_path, 'w', encoding='utf-8') as sf:
                                json.dump(stats, sf, indent=2, ensure_ascii=False)
                except Exception as e:
                    print(f"Failed to update dashboard JSON: {e}")

                print(f"[{datetime.now()}] Received and saved harvest data to {filename}")
                self.send_response(200)
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(b"Harvest data received successfully.")
            else:
                self.send_response(400)
                self.end_headers()
                self.wfile.write(b"Empty payload.")
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        pass

def run(server_class=ThreadingHTTPServer, handler_class=MetricsHandler, port=8111):
    server_address = ('0.0.0.0', port)
    httpd = server_class(server_address, handler_class)
    
    # Start metrics updater thread
    updater_thread = threading.Thread(target=metrics_updater_loop, daemon=True)
    updater_thread.start()
    
    # Start thermal watchdog
    watchdog_thread = threading.Thread(target=thermal_watchdog_loop, daemon=True)
    watchdog_thread.start()
    
    # Start harvester watchdog
    harvester_thread = threading.Thread(target=harvester_watchdog_loop, daemon=True)
    harvester_thread.start()

    # Start fleet evidence collection/uplink
    evidence_thread = threading.Thread(target=fleet_evidence_loop, daemon=True)
    evidence_thread.start()
    
    print(f"Starting Fast Monitor Agent on {socket.gethostname()}:{port}...")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    httpd.server_close()

if __name__ == "__main__":
    run(port=int(os.environ.get("MONITOR_AGENT_PORT", "8111")))
