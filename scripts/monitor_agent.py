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
from datetime import datetime, timedelta
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
K10_SCRIPTS_BASE = os.environ.get("CLAWSTACK_K10_SCRIPTS", "http://100.119.18.40:8123").rstrip("/")
_last_lhm_bootstrap_at = 0.0
LHM_BOOTSTRAP_COOLDOWN_SEC = 600
NODE_DIAGNOSTIC_ROOT = os.environ.get(
    "NODE_DIAGNOSTIC_DIR",
    os.path.join(PROGRAMDATA_ROOT, "Clawstack", "monitor_agent", "node_diagnostics"),
)
NODE_DIAGNOSTIC_RETENTION_HOURS = max(1, int(os.environ.get("NODE_DIAGNOSTIC_RETENTION_HOURS", "72")))
NODE_DIAGNOSTIC_METRICS_INTERVAL_SEC = max(
    15,
    int(os.environ.get("NODE_DIAGNOSTIC_METRICS_INTERVAL_SEC", "60")),
)
NODE_DIAGNOSTIC_ENABLED = os.environ.get("NODE_DIAGNOSTIC_LOG", "1").strip().lower() not in (
    "0",
    "false",
    "no",
)

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

def _parse_cpu_percent_text(raw: str) -> float | None:
    text = (raw or "").strip().replace(",", ".")
    if not text:
        return None
    try:
        value = float(text)
    except ValueError:
        return None
    if 0.0 <= value <= 100.0:
        return round(value, 1)
    return None


_last_cpu_usage_source = "unknown"


def get_cpu_usage():
    """Windows CPU usage with CIM -> typeperf -> PDH fallbacks (INC-096 / main LAVIE 0% bug)."""
    global _last_cpu_usage_source
    _last_cpu_usage_source = "zero_or_unavailable"
    if platform.system() != "Windows":
        return 0.0

    ps_flags = 0x08000000

    try:
        out = subprocess.check_output(
            [
                "powershell",
                "-NoProfile",
                "-Command",
                "Get-CimInstance Win32_Processor | "
                "Measure-Object -Property LoadPercentage -Average | "
                "Select-Object -ExpandProperty Average",
            ],
            text=True,
            creationflags=ps_flags,
            timeout=6,
        )
        parsed = _parse_cpu_percent_text(out)
        if parsed is not None:
            _last_cpu_usage_source = "cim_load_percentage"
            return parsed
    except Exception:
        pass

    try:
        out = subprocess.check_output(
            ["typeperf", r"\Processor(_Total)\% Processor Time", "-sc", "1"],
            text=True,
            encoding="utf-8",
            errors="replace",
            creationflags=ps_flags,
            timeout=8,
        )
        for line in reversed((out or "").splitlines()):
            line = line.strip()
            if not line or not line.startswith('"'):
                continue
            parts = [p.strip().strip('"') for p in line.split(",")]
            if len(parts) >= 2:
                parsed = _parse_cpu_percent_text(parts[-1])
                if parsed is not None:
                    _last_cpu_usage_source = "typeperf_processor_time"
                    return parsed
    except Exception:
        pass

    try:
        out = subprocess.check_output(
            [
                "powershell",
                "-NoProfile",
                "-Command",
                "(Get-Counter '\\Processor(_Total)\\% Processor Time' -SampleInterval 1 -MaxSamples 1)"
                ".CounterSamples.CookedValue",
            ],
            text=True,
            creationflags=ps_flags,
            timeout=10,
        )
        parsed = _parse_cpu_percent_text(out)
        if parsed is not None:
            _last_cpu_usage_source = "pdh_processor_time"
            return parsed
    except Exception:
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


def _lhm_walk_sensors(node, temps, disk_warnings, loads, ctx_device="", parent_text=""):
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

    if _lhm_is_load(node, parent_text) and val is not None and 0.0 <= float(val) <= 100.0:
        if text == "Used Space" and val >= 90:
            disk_warnings.append({"device": ctx_device, "used_pct": round(float(val), 1)})
        elif text in ("CPU Total", "Total CPU Load") or (
            parent_text == "Load" and ctx_device and "cpu" in ctx_device.lower()
        ):
            loads.append({"name": text, "pct": round(float(val), 1), "device": ctx_device})

    next_parent = text if text in ("Temperatures", "Load") else parent_text
    for child in children:
        _lhm_walk_sensors(child, temps, disk_warnings, loads, ctx_device, next_parent)


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
    loads: list[dict] = []
    for top in data.get("Children") or []:
        _lhm_walk_sensors(top, temps, disk_warnings, loads)

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
    cpu_total_load = None
    for item in loads:
        if item.get("name") == "CPU Total":
            cpu_total_load = item.get("pct")
            break
    if cpu_total_load is None and loads:
        cpu_total_load = max(item.get("pct") or 0 for item in loads)

    return {
        "ok": True,
        "cpu_temp_c": round(primary, 1),
        "cpu_package_c": cpu_package,
        "core_max_c": core_max,
        "core_avg_c": core_avg,
        "cpu_total_load_pct": cpu_total_load,
        "nvme_temps": nvme_temps[:8],
        "disk_warnings": disk_warnings,
        "source": "lhm_http",
        "url": LHM_DATA_URL,
    }


def ensure_lhm_running() -> dict | None:
    """Best-effort LHM install/start on Windows host (monitor runs on host, not Docker)."""
    global _last_lhm_bootstrap_at
    if platform.system() != "Windows":
        return None
    k10_base = os.environ.get("CLAWSTACK_K10_SCRIPTS", "http://100.119.18.40:8123").rstrip("/")
    try:
        req = urllib.request.Request(LHM_DATA_URL, headers={"User-Agent": "monitor_agent/lhm-probe"})
        with urllib.request.urlopen(req, timeout=3) as resp:
            if resp.status == 200 and len(resp.read()) > 200:
                return {"step": "lhm_bootstrap", "ok": True, "skipped": "already_up"}
    except Exception:
        pass
    now = time.time()
    if now - _last_lhm_bootstrap_at < LHM_BOOTSTRAP_COOLDOWN_SEC:
        return None
    _last_lhm_bootstrap_at = now
    ps1_dest = os.path.join(os.environ.get("TEMP", "."), "lhm_setup_monitor_agent.ps1")
    try:
        url = f"{k10_base}/lhm_setup.ps1"
        req = urllib.request.Request(url, headers={"User-Agent": "monitor_agent/lhm-bootstrap"})
        with urllib.request.urlopen(req, timeout=45) as resp:
            data = resp.read()
        if len(data) < 200:
            return {"step": "lhm_bootstrap", "ok": False, "error": "lhm_setup.ps1 too small"}
        with open(ps1_dest, "wb") as handle:
            handle.write(data)
    except Exception as exc:
        return {"step": "lhm_bootstrap", "ok": False, "error": str(exc)[:200]}
    try:
        proc = subprocess.run(
            f'powershell -NoProfile -ExecutionPolicy Bypass -File "{ps1_dest}"',
            shell=True,
            capture_output=True,
            text=True,
            timeout=180,
            creationflags=0x08000000,
        )
        out = (proc.stdout or "") + (proc.stderr or "")
        ok = proc.returncode == 0 or "Remote Web Server is UP" in out or "already on :8085" in out
        return {"step": "lhm_bootstrap", "ok": ok, "exit_code": proc.returncode, "detail": out[-400:]}
    except Exception as exc:
        return {"step": "lhm_bootstrap", "ok": False, "error": str(exc)[:200]}


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


diagnostic_lock = threading.Lock()
last_diagnostic_prune_at = 0.0
last_diagnostic_metrics_at = 0.0
last_diagnostic_alert_key = ""
last_wlan_diagnostic_at = 0.0
last_wlan_signature = ""
WLAN_TELEMETRY_ROOT = os.path.join(PROGRAMDATA_ROOT, "Clawstack", "stability")


def _diagnostic_host_dir():
    host = _safe_hostname(socket.gethostname())
    return os.path.join(NODE_DIAGNOSTIC_ROOT, host)


def _diagnostic_path_for_now():
    day = datetime.now().strftime("%Y%m%d")
    return os.path.join(_diagnostic_host_dir(), f"diagnostic_{day}.jsonl")


def _parse_record_time(record):
    raw = record.get("timestamp") if isinstance(record, dict) else None
    if not raw:
        return None
    try:
        return datetime.fromisoformat(str(raw))
    except Exception:
        return None


def _prune_node_diagnostics(force=False):
    global last_diagnostic_prune_at
    now = time.time()
    if not force and now - last_diagnostic_prune_at < 3600:
        return
    last_diagnostic_prune_at = now
    cutoff = datetime.now() - timedelta(hours=NODE_DIAGNOSTIC_RETENTION_HOURS)
    root = _diagnostic_host_dir()
    if not os.path.isdir(root):
        return
    for name in os.listdir(root):
        if not name.startswith("diagnostic_") or not name.endswith(".jsonl"):
            continue
        path = os.path.join(root, name)
        try:
            kept = []
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        record = json.loads(line)
                    except Exception:
                        continue
                    ts = _parse_record_time(record)
                    if ts is None or ts >= cutoff:
                        kept.append(record)
            if not kept:
                os.remove(path)
                continue
            tmp_path = path + ".tmp"
            try:
                with open(tmp_path, "w", encoding="utf-8", errors="replace") as f:
                    for record in kept:
                        json.dump(record, f, ensure_ascii=False, separators=(",", ":"))
                        f.write("\n")
                os.replace(tmp_path, path)
            finally:
                if os.path.exists(tmp_path):
                    try:
                        os.remove(tmp_path)
                    except Exception:
                        pass
        except Exception as exc:
            log_debug(f"diagnostic prune error {path}: {exc}")


def _append_node_diagnostic(event, payload=None, severity="info"):
    if not NODE_DIAGNOSTIC_ENABLED:
        return None
    record = {
        "schema": "clawstack.node_diagnostic.v1",
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "hostname": socket.gethostname(),
        "event": str(event),
        "severity": str(severity),
        "payload": payload or {},
    }
    with diagnostic_lock:
        path = _diagnostic_path_for_now()
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "a", encoding="utf-8", errors="replace") as f:
            json.dump(record, f, ensure_ascii=False, separators=(",", ":"))
            f.write("\n")
        _prune_node_diagnostics()
    return path


def _diagnostic_status():
    root = _diagnostic_host_dir()
    files = []
    total_bytes = 0
    if os.path.isdir(root):
        for name in os.listdir(root):
            if not name.endswith(".jsonl"):
                continue
            path = os.path.join(root, name)
            try:
                size = os.path.getsize(path)
                total_bytes += size
                files.append({"name": name, "bytes": size, "modified": datetime.fromtimestamp(os.path.getmtime(path)).isoformat(timespec="seconds")})
            except Exception:
                pass
    return {
        "enabled": NODE_DIAGNOSTIC_ENABLED,
        "root": root,
        "retention_hours": NODE_DIAGNOSTIC_RETENTION_HOURS,
        "metrics_interval_sec": NODE_DIAGNOSTIC_METRICS_INTERVAL_SEC,
        "files": sorted(files, key=lambda item: item["name"]),
        "total_bytes": total_bytes,
    }


def _read_recent_node_diagnostics(limit=200):
    root = _diagnostic_host_dir()
    if not os.path.isdir(root):
        return []
    paths = [
        os.path.join(root, name)
        for name in os.listdir(root)
        if name.startswith("diagnostic_") and name.endswith(".jsonl")
    ]
    records = []
    for path in sorted(paths)[-3:]:
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        records.append(json.loads(line))
                    except Exception:
                        pass
        except Exception:
            pass
    return records[-limit:]


def _parse_netsh_wlan_interfaces(text: str) -> dict:
    snapshot = {
        "connected": False,
        "state_text": "",
        "ssid": "",
        "profile": "",
        "signal_percent": None,
        "rssi_dbm": None,
        "band": "",
        "rx_mbps": None,
        "tx_mbps": None,
        "interface_name": "",
    }
    if not text:
        return snapshot
    block: dict[str, str] = {}
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            if block:
                break
            continue
        if ":" in line:
            key, val = line.split(":", 1)
            block[key.strip().lower()] = val.strip()
    key_map = {
        "state": "state_text",
        "状態": "state_text",
        "ssid": "ssid",
        "profile": "profile",
        "プロファイル": "profile",
        "signal": "signal_percent",
        "シグナル": "signal_percent",
        "rssi": "rssi_dbm",
        "band": "band",
        "バンド": "band",
        "receive rate (mbps)": "rx_mbps",
        "受信速度 (mbps)": "rx_mbps",
        "transmit rate (mbps)": "tx_mbps",
        "送信速度 (mbps)": "tx_mbps",
        "name": "interface_name",
        "名前": "interface_name",
    }
    for src, dst in key_map.items():
        if src in block and not snapshot.get(dst):
            snapshot[dst] = block[src]
    state = str(snapshot.get("state_text") or "").lower()
    snapshot["connected"] = _wlan_is_connected(text)
    sig = str(snapshot.get("signal_percent") or "")
    m = re.search(r"(\d+)", sig)
    if m:
        snapshot["signal_percent"] = int(m.group(1))
    rssi = str(snapshot.get("rssi_dbm") or "")
    m = re.search(r"-?\d+", rssi)
    if m:
        snapshot["rssi_dbm"] = int(m.group(0))
    for rate_key in ("rx_mbps", "tx_mbps"):
        m = re.search(r"(\d+(?:\.\d+)?)", str(snapshot.get(rate_key) or ""))
        if m:
            snapshot[rate_key] = float(m.group(1))
    if snapshot.get("ssid") and not snapshot.get("profile"):
        snapshot["profile"] = snapshot["ssid"]
    snapshot["band_label"] = "5g" if "-5G" in str(snapshot.get("ssid") or "").upper() else (
        "2g" if "-2G" in str(snapshot.get("ssid") or "").upper() else "unknown"
    )
    return snapshot


def _collect_wlan_snapshot() -> dict:
    try:
        proc = subprocess.run(
            ["netsh", "wlan", "show", "interfaces"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=15,
            creationflags=0x08000000,
        )
        text = proc.stdout or ""
        snap = _parse_netsh_wlan_interfaces(text)
        snap["raw_len"] = len(text)
        snap["exit_code"] = proc.returncode
        return snap
    except Exception as exc:
        return {"connected": False, "error": str(exc)[:200]}


def _collect_wlan_recent_events(max_events: int = 20) -> list[dict]:
    script = (
        f"$max={int(max_events)};"
        "$start=(Get-Date).AddHours(-48);"
        "$events=Get-WinEvent -LogName 'Microsoft-Windows-WLAN-AutoConfig/Operational' "
        "-MaxEvents $max -ErrorAction SilentlyContinue | "
        "Where-Object { $_.TimeCreated -ge $start } | "
        "Select-Object TimeCreated,Id,LevelDisplayName,Message;"
        "if (-not $events) { '[]' } else { $events | ConvertTo-Json -Depth 3 -Compress }"
    )
    data = _run_powershell_json(script, timeout=25)
    if data is None:
        return []
    if isinstance(data, dict):
        if "error" in data:
            return [data]
        return [data]
    if isinstance(data, list):
        return data
    return []


def _append_wlan_telemetry_file(snapshot: dict) -> str | None:
    try:
        os.makedirs(WLAN_TELEMETRY_ROOT, exist_ok=True)
        day = datetime.now().strftime("%Y%m%d")
        path = os.path.join(WLAN_TELEMETRY_ROOT, f"wlan_telemetry_{day}.jsonl")
        record = {
            "schema": "clawstack.lavie_wlan_telemetry.v1",
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "hostname": socket.gethostname(),
            **snapshot,
        }
        with open(path, "a", encoding="utf-8", errors="replace") as handle:
            json.dump(record, handle, ensure_ascii=False, separators=(",", ":"))
            handle.write("\n")
        return path
    except Exception:
        return None


def _read_wlan_telemetry_tail(limit: int = 120) -> list[dict]:
    if not os.path.isdir(WLAN_TELEMETRY_ROOT):
        return []
    paths = sorted(
        [
            os.path.join(WLAN_TELEMETRY_ROOT, name)
            for name in os.listdir(WLAN_TELEMETRY_ROOT)
            if name.startswith("wlan_telemetry_") and name.endswith(".jsonl")
        ]
    )
    records: list[dict] = []
    for path in paths[-3:]:
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as handle:
                for line in handle:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        records.append(json.loads(line))
                    except Exception:
                        pass
        except Exception:
            pass
    return records[-limit:]


def _maybe_log_wlan_diagnostic(force: bool = False) -> dict | None:
    global last_wlan_diagnostic_at, last_wlan_signature
    now = time.time()
    interval = max(30, NODE_DIAGNOSTIC_METRICS_INTERVAL_SEC)
    if not force and now - last_wlan_diagnostic_at < interval:
        return None
    last_wlan_diagnostic_at = now
    wlan = _collect_wlan_snapshot()
    tailscale = _collect_tailscale_status()
    payload = {
        **wlan,
        "tailscale_online": bool((tailscale or {}).get("Self", {}).get("Online"))
        if isinstance(tailscale, dict) and "Self" in tailscale
        else None,
        "tailscale_tun": (tailscale or {}).get("Self", {}).get("TUN")
        if isinstance(tailscale, dict) and isinstance(tailscale.get("Self"), dict)
        else None,
    }
    signature = "|".join(
        [
            str(payload.get("ssid") or ""),
            str(payload.get("band_label") or ""),
            "1" if payload.get("connected") else "0",
            str(payload.get("signal_percent") or ""),
        ]
    )
    severity = "info"
    if not payload.get("connected"):
        severity = "warn"
    elif last_wlan_signature and signature != last_wlan_signature:
        prev_ssid = (last_wlan_signature.split("|") or [""])[0]
        cur_ssid = str(payload.get("ssid") or "")
        if prev_ssid and cur_ssid and prev_ssid != cur_ssid:
            _append_node_diagnostic(
                "wlan_band_or_ssid_switch",
                {"from": last_wlan_signature, "to": signature, "snapshot": payload},
                severity="warn",
            )
    last_wlan_signature = signature
    _append_node_diagnostic("wlan_snapshot", payload, severity=severity)
    _append_wlan_telemetry_file(payload)
    return payload


def build_outage_forensics_report() -> dict:
    recent = _read_recent_node_diagnostics(400)
    wlan_tail = _read_wlan_telemetry_tail(200)
    wlan_events = _collect_wlan_recent_events(30)
    keepalive = os.path.join(WLAN_TELEMETRY_ROOT, "lavie_keepalive_heartbeat.txt")
    keepalive_text = ""
    if os.path.isfile(keepalive):
        try:
            with open(keepalive, encoding="utf-8", errors="replace") as handle:
                keepalive_text = handle.read().strip()
        except Exception:
            pass
    return {
        "schema": "clawstack.lavie_outage_forensics.v1",
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "hostname": socket.gethostname(),
        "diagnostic_status": _diagnostic_status(),
        "wlan_snapshot_now": _collect_wlan_snapshot(),
        "wlan_telemetry_tail": wlan_tail[-80:],
        "wlan_recent_events_48h": wlan_events,
        "keepalive_heartbeat": keepalive_text,
        "tailscale_status": _collect_tailscale_status(),
        "power_snapshot": _collect_power_snapshot(),
        "windows_event_summary_6h": _collect_windows_event_summary(window_hours=6),
        "windows_shutdown_events_48h": _collect_windows_shutdown_events(),
        "recent_diagnostics": recent,
    }


def _metrics_alerts(metrics):
    alerts = []
    cpu = metrics.get("cpu_usage_percent")
    ram = metrics.get("ram_usage_percent")
    temp = metrics.get("thermal_control_temp_c")
    if isinstance(cpu, (int, float)) and cpu >= 90:
        alerts.append(f"cpu_high:{round(float(cpu), 1)}")
    if isinstance(ram, (int, float)) and ram >= 85:
        alerts.append(f"ram_high:{round(float(ram), 1)}")
    if isinstance(temp, (int, float)) and temp >= 80:
        alerts.append(f"temp_high:{round(float(temp), 1)}")
    if metrics.get("disk_warnings"):
        alerts.append("disk_warning")
    wlan = metrics.get("wlan") or {}
    if wlan and not wlan.get("connected"):
        alerts.append("wlan_disconnected")
    if not metrics.get("lhm_ok") and metrics.get("lhm_error"):
        alerts.append("lhm_error")
    return alerts


def _maybe_log_metrics_diagnostic(metrics):
    global last_diagnostic_metrics_at, last_diagnostic_alert_key
    now = time.time()
    alerts = _metrics_alerts(metrics)
    alert_key = "|".join(alerts)
    should_log = now - last_diagnostic_metrics_at >= NODE_DIAGNOSTIC_METRICS_INTERVAL_SEC
    if alert_key and alert_key != last_diagnostic_alert_key:
        should_log = True
    if not should_log:
        return
    last_diagnostic_metrics_at = now
    last_diagnostic_alert_key = alert_key
    payload = {
        "cpu_usage_percent": metrics.get("cpu_usage_percent"),
        "cpu_current_clock_mhz": metrics.get("cpu_current_clock_mhz"),
        "ram_usage_percent": metrics.get("ram_usage_percent"),
        "ram_used_gb": metrics.get("ram_used_gb"),
        "ram_total_gb": metrics.get("ram_total_gb"),
        "thermal_control_temp_c": metrics.get("thermal_control_temp_c"),
        "cpu_package_c": metrics.get("cpu_package_c"),
        "core_max_c": metrics.get("core_max_c"),
        "temp_source": metrics.get("temp_source"),
        "lhm_ok": metrics.get("lhm_ok"),
        "lhm_error": metrics.get("lhm_error"),
        "is_throttling": metrics.get("is_throttling"),
        "cpu_limit_percent": metrics.get("cpu_limit_percent"),
        "thermal_throttle_label": metrics.get("thermal_throttle_label"),
        "disk_warnings": metrics.get("disk_warnings"),
        "alerts": alerts,
    }
    severity = "warn" if alerts else "info"
    _append_node_diagnostic("metrics_snapshot", payload, severity=severity)


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


def _classify_windows_event(event):
    provider = str(event.get("ProviderName") or "")
    try:
        event_id = int(event.get("Id") or 0)
    except Exception:
        event_id = 0
    if event_id in {41, 42, 107, 109, 506, 507, 6005, 6006, 6008, 1074}:
        return "power"
    if "Power" in provider or "Kernel-General" in provider:
        return "power"
    if "Tailscale" in provider or event_id in {7031, 7034, 7035, 7036}:
        return "service"
    if "Tcpip" in provider or "Network" in provider or "WLAN" in provider:
        return "network"
    return "system"


def _collect_windows_event_summary(window_hours=6, max_events=120, max_compact=40):
    script = (
        f"$start=(Get-Date).AddHours(-{int(window_hours)});"
        "$providers=@('Microsoft-Windows-Kernel-Power','Microsoft-Windows-Power-Troubleshooter',"
        "'Microsoft-Windows-Kernel-General','Service Control Manager','Tcpip','Netwtw10','Netwtw08',"
        "'Microsoft-Windows-WLAN-AutoConfig','Tailscale');"
        "$events=Get-WinEvent -FilterHashtable @{LogName='System'; StartTime=$start} "
        f"-MaxEvents {int(max_events)} -ErrorAction SilentlyContinue | "
        "Where-Object { $providers -contains $_.ProviderName -or $_.ProviderName -like '*Network*' } | "
        f"Select-Object -First {int(max_compact)} TimeCreated,Id,ProviderName,LevelDisplayName; "
        "$events | ConvertTo-Json -Depth 4 -Compress"
    )
    events = _run_powershell_json(script, timeout=20)
    if events is None:
        rows = []
    elif isinstance(events, dict):
        if "error" in events:
            return events
        rows = [events]
    else:
        rows = events
    counts = {}
    compact = []
    for event in rows[:max_compact]:
        if not isinstance(event, dict):
            continue
        category = _classify_windows_event(event)
        counts[category] = counts.get(category, 0) + 1
        compact.append(
            {
                "time": event.get("TimeCreated"),
                "id": event.get("Id"),
                "provider": event.get("ProviderName"),
                "level": event.get("LevelDisplayName"),
                "category": category,
            }
        )
    return {"window_hours": int(window_hours), "counts": counts, "events": compact}


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
        "windows_event_summary_6h": _collect_windows_event_summary(),
        "wlan_snapshot": _collect_wlan_snapshot(),
        "wlan_recent_events_48h": _collect_wlan_recent_events(20),
        "node_diagnostic_status": _diagnostic_status(),
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
            severity = "info" if upload_status.get("ok") or upload_status.get("enabled") is False else "warn"
            _append_node_diagnostic(
                "fleet_evidence",
                {
                    "local_path": local_path,
                    "upload": upload_status,
                    "windows_event_summary_24h": _collect_windows_event_summary(24, 200, 60),
                },
                severity=severity,
            )
            cached_metrics["fleet_evidence"] = {
                "last_local_path": local_path,
                "last_upload": upload_status,
                "last_at": snapshot["timestamp"],
                "url": FLEET_EVIDENCE_URL,
            }
            log_debug(f"Fleet evidence saved: {local_path}; upload={upload_status}")
        except Exception as exc:
            cached_metrics["fleet_evidence"] = {"error": str(exc), "last_at": datetime.now().isoformat()}
            _append_node_diagnostic("fleet_evidence_error", {"error": str(exc)}, severity="error")
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
            lhm = get_lhm_metrics()
            lhm_ok = bool(lhm.get("ok"))
            if not lhm_ok:
                ensure_lhm_running()
                lhm = get_lhm_metrics()
                lhm_ok = bool(lhm.get("ok"))
            cpu_usage = get_cpu_usage()
            cached_metrics["cpu_usage_source"] = _last_cpu_usage_source
            if (cpu_usage is None or cpu_usage <= 0.0) and lhm_ok:
                lhm_cpu = lhm.get("cpu_total_load_pct")
                if isinstance(lhm_cpu, (int, float)) and lhm_cpu > 0:
                    cpu_usage = float(lhm_cpu)
                    cached_metrics["cpu_usage_source"] = "lhm_cpu_total_load"
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
            cached_metrics["node_diagnostic"] = _diagnostic_status()
            wlan = _maybe_log_wlan_diagnostic()
            if wlan:
                cached_metrics["wlan"] = wlan
            _maybe_log_metrics_diagnostic(cached_metrics)
        except Exception as e:
            log_debug(f"Loop error: {e}")
            _append_node_diagnostic("metrics_loop_error", {"error": str(e)}, severity="error")
            print("Error in metrics updater:", e)
        time.sleep(15)

def _run_powercfg(args: list[str]) -> None:
    subprocess.check_output(
        ["powercfg", *args],
        text=True,
        creationflags=0x08000000,
        timeout=15,
    )


def _wlan_is_connected(wlan_out: str) -> bool:
    text = wlan_out or ""
    lower = text.lower()
    if "disconnected" in lower or "切断" in text or "未接続" in text:
        for line in text.splitlines():
            if "state" in line.lower() or "状態" in line:
                if "disconnected" in line.lower() or "切断" in line or "未接続" in line:
                    return False
                if "connected" in line.lower() or "接続" in line:
                    return True
        return False
    if "connected" in lower or "接続され" in text or "接続済" in text:
        return True
    for line in text.splitlines():
        if "state" in line.lower() or "状態" in line:
            if "connected" in line.lower() or "接続" in line:
                return True
    return False


def apply_host_stability() -> dict:
    """Anti-sleep / keepalive on Windows host (K10 calls GET /host_stability/apply)."""
    reload = _maybe_reload_monitor_from_disk()
    if reload:
        return {
            "ok": True,
            "schema": "clawstack.lavie_host_stability.v1",
            "hostname": socket.gethostname(),
            "steps": [reload],
            "message": "MONITOR_RELOADING",
        }
    steps: list[dict] = []
    ok = True
    sync_step = _sync_stability_scripts_from_k10()
    if sync_step:
        steps.append(sync_step)
    power_cmds = [
        ["/change", "standby-timeout-ac", "0"],
        ["/change", "standby-timeout-dc", "0"],
        ["/change", "hibernate-timeout-ac", "0"],
        ["/change", "hibernate-timeout-dc", "0"],
        ["/change", "disk-timeout-ac", "0"],
        ["/change", "disk-timeout-dc", "0"],
        ["/change", "monitor-timeout-ac", "45"],
        ["/SETACVALUEINDEX", "SCHEME_CURRENT", "SUB_BUTTONS", "LIDACTION", "0"],
        ["/SETDCVALUEINDEX", "SCHEME_CURRENT", "SUB_BUTTONS", "LIDACTION", "0"],
        ["/SETACTIVE", "SCHEME_CURRENT"],
    ]
    for args in power_cmds:
        label = " ".join(args)
        try:
            _run_powercfg(args)
            steps.append({"step": label, "ok": True})
        except Exception as exc:
            ok = False
            steps.append({"step": label, "ok": False, "error": str(exc)[:200]})
    try:
        key = winreg.OpenKey(
            winreg.HKEY_LOCAL_MACHINE,
            r"SYSTEM\CurrentControlSet\Control\Session Manager\Power",
            0,
            winreg.KEY_SET_VALUE,
        )
        winreg.SetValueEx(key, "HiberbootEnabled", 0, winreg.REG_DWORD, 0)
        winreg.CloseKey(key)
        steps.append({"step": "fast_startup_off", "ok": True})
    except Exception as exc:
        ok = False
        steps.append({"step": "fast_startup_off", "ok": False, "error": str(exc)[:200]})
    try:
        subprocess.run(
            ["sc", "config", "Tailscale", "start=", "auto"],
            capture_output=True,
            text=True,
            timeout=15,
            creationflags=0x08000000,
        )
        subprocess.run(
            ["sc", "start", "Tailscale"],
            capture_output=True,
            text=True,
            timeout=15,
            creationflags=0x08000000,
        )
        steps.append({"step": "tailscale_service", "ok": True})
    except Exception as exc:
        steps.append({"step": "tailscale_service", "ok": False, "error": str(exc)[:200]})
    try:
        default_wifi_2g = "E440973A1E43-2G"
        profile_file = os.path.join(PROGRAMDATA_ROOT, "Clawstack", "stability", "wifi_profile.txt")
        os.makedirs(os.path.dirname(profile_file), exist_ok=True)
        if not os.path.isfile(profile_file):
            with open(profile_file, "w", encoding="utf-8") as pf:
                pf.write(default_wifi_2g)
        preferred = os.environ.get("LAVIE_WIFI_PROFILE", "").strip()
        if not preferred and os.path.isfile(profile_file):
            with open(profile_file, encoding="utf-8") as pf:
                preferred = pf.read().strip()
        if not preferred:
            preferred = default_wifi_2g
        wlan = subprocess.run(
            ["netsh", "wlan", "show", "interfaces"],
            capture_output=True,
            text=True,
            timeout=15,
            creationflags=0x08000000,
        )
        wlan_out = wlan.stdout or ""
        wifi_ok = _wlan_is_connected(wlan_out)
        current_ssid = ""
        for line in wlan_out.splitlines():
            if line.strip().startswith("SSID") and "BSSID" not in line and ":" in line:
                current_ssid = line.split(":", 1)[1].strip()
                break
        prefer_2g = os.environ.get("LAVIE_PREFER_WIFI_2G", "1") != "0"
        if prefer_2g and current_ssid.endswith("-5G"):
            preferred = default_wifi_2g
            subprocess.run(
                ["netsh", "wlan", "connect", f"name={preferred}"],
                capture_output=True,
                text=True,
                timeout=20,
                creationflags=0x08000000,
            )
            time.sleep(4)
            wlan = subprocess.run(
                ["netsh", "wlan", "show", "interfaces"],
                capture_output=True,
                text=True,
                timeout=15,
                creationflags=0x08000000,
            )
            wlan_out = wlan.stdout or ""
            wifi_ok = _wlan_is_connected(wlan_out)
        if not wifi_ok:
            if prefer_2g and preferred.endswith("-5G"):
                preferred = default_wifi_2g
            subprocess.run(
                ["netsh", "wlan", "connect", f"name={preferred}"],
                capture_output=True,
                text=True,
                timeout=20,
                creationflags=0x08000000,
            )
            wlan = subprocess.run(
                ["netsh", "wlan", "show", "interfaces"],
                capture_output=True,
                text=True,
                timeout=15,
                creationflags=0x08000000,
            )
            wlan_out = wlan.stdout or ""
            wifi_ok = _wlan_is_connected(wlan_out)
        if wifi_ok:
            for line in wlan_out.splitlines():
                if line.strip().startswith("SSID") and "BSSID" not in line and ":" in line:
                    ssid = line.split(":", 1)[1].strip()
                    if ssid:
                        with open(profile_file, "w", encoding="utf-8") as pf:
                            pf.write(ssid)
                        break
        realtek_ps = (
            "Get-PnpDevice -Class Net -EA SilentlyContinue | Where-Object { $_.FriendlyName -match 'Realtek|8822BE' } | "
            "ForEach-Object { $p = 'HKLM:\\SYSTEM\\CurrentControlSet\\Enum\\' + $_.InstanceId + '\\Device Parameters'; "
            "if (Test-Path $p) { Set-ItemProperty -Path $p -Name PnPCapabilities -Value 24 -Type DWord -Force -EA SilentlyContinue } }; "
            "Get-NetAdapter -EA SilentlyContinue | Where-Object { $_.InterfaceDescription -match 'Realtek|8822BE' } | "
            "ForEach-Object { Disable-NetAdapterPowerManagement -Name $_.Name -EA SilentlyContinue | Out-Null }"
        )
        rt = subprocess.run(
            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", realtek_ps],
            capture_output=True,
            text=True,
            timeout=45,
            creationflags=0x08000000,
        )
        steps.append(
            {
                "step": "realtek_wifi_power_save_off",
                "ok": rt.returncode == 0,
                "detail": (rt.stdout or rt.stderr or "")[:120],
            }
        )
        steps.append({"step": "wifi_reconnect", "ok": wifi_ok, "detail": wlan_out[:200], "profile": preferred})
        if not wifi_ok:
            ok = False
    except Exception as exc:
        ok = False
        steps.append({"step": "wifi_reconnect", "ok": False, "error": str(exc)[:200]})
    stab_root = os.path.join(PROGRAMDATA_ROOT, "Clawstack", "stability")
    os.makedirs(stab_root, exist_ok=True)
    heartbeat = os.path.join(stab_root, "host_keepalive_heartbeat.txt")
    for hb_name in (
        "dynabook_keepalive_heartbeat.txt",
        "g3_keepalive_heartbeat.txt",
        "red_lavie_keepalive_heartbeat.txt",
        "lavie_keepalive_heartbeat.txt",
    ):
        hb_path = os.path.join(stab_root, hb_name)
        if os.path.isfile(hb_path):
            heartbeat = hb_path
            break
    with open(heartbeat, "w", encoding="utf-8") as handle:
        handle.write(f"{datetime.now().isoformat(timespec='seconds')} host={socket.gethostname()}\n")
    steps.append({"step": "heartbeat", "ok": True, "path": heartbeat})
    ps1_candidates = [
        os.environ.get("CLAWSTACK_STABILITY_PS1", "").strip(),
        os.path.join(stab_root, "lavie_host_stability.ps1"),
        os.path.join(stab_root, "red_lavie_host_stability.ps1"),
        os.path.join(stab_root, "g3_host_stability.ps1"),
        os.path.join(stab_root, "dynabook_host_stability.ps1"),
    ]
    ps1_path = next((p for p in ps1_candidates if p and os.path.isfile(p)), None)
    ps1_ok_token = "HOST_STABILITY_OK"
    if ps1_path:
        try:
            ps1 = subprocess.run(
                [
                    "powershell",
                    "-NoProfile",
                    "-ExecutionPolicy",
                    "Bypass",
                    "-File",
                    ps1_path,
                ],
                capture_output=True,
                text=True,
                timeout=180,
                creationflags=0x08000000,
            )
            ps1_out = ps1.stdout or ""
            ps1_ok = ps1.returncode == 0 and ps1_ok_token in ps1_out
            steps.append(
                {
                    "step": "host_stability_ps1",
                    "ok": ps1_ok,
                    "path": ps1_path,
                    "detail": ps1_out[-400:],
                }
            )
            ok = ok and ps1_ok
        except Exception as exc:
            steps.append({"step": "host_stability_ps1", "ok": False, "error": str(exc)[:200]})
            ok = False
    worker_step = ensure_satellite_job_worker()
    if worker_step:
        steps.append(worker_step)
        if not worker_step.get("ok"):
            ok = False
    return {
        "ok": ok,
        "schema": "clawstack.lavie_host_stability.v1",
        "hostname": socket.gethostname(),
        "steps": steps,
        "message": "HOST_STABILITY_OK" if ok else "HOST_STABILITY_PARTIAL",
    }


RED_LAVIE_WORKER_PORT = int(os.environ.get("SATELLITE_JOB_WORKER_PORT", "5682"))


def _is_red_lavie_host() -> bool:
    node_id = os.environ.get("SATELLITE_NODE_ID", "").strip().lower()
    if node_id == "red_lavie":
        return True
    host = socket.gethostname().upper()
    return "DERCN1N" in host or host.startswith("DESKTOP-DERCN1N")


def _load_satellite_job_token() -> str:
    token = os.environ.get("SATELLITE_JOB_TOKEN", "").strip()
    if token:
        return token
    for env_path in (
        r"C:\clawstack_satellite\.env",
        os.path.join(PROGRAMDATA_ROOT, "Clawstack", "satellite.env"),
    ):
        if not os.path.isfile(env_path):
            continue
        try:
            with open(env_path, encoding="utf-8", errors="replace") as handle:
                for line in handle:
                    if line.startswith("SATELLITE_JOB_TOKEN="):
                        return line.split("=", 1)[1].strip()
        except OSError:
            continue
    return ""


def _worker_health_ok(port: int = RED_LAVIE_WORKER_PORT) -> bool:
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/healthz", timeout=2) as resp:
            return resp.status == 200
    except Exception:
        return False


def _sync_stability_scripts_from_k10() -> dict | None:
    if not _is_red_lavie_host():
        return None
    dest_root = os.path.join(PROGRAMDATA_ROOT, "Clawstack", "stability")
    os.makedirs(dest_root, exist_ok=True)
    synced: list[str] = []
    errors: list[str] = []
    for name in ("clawstack_windows_host_stability.ps1", "red_lavie_host_stability.ps1"):
        try:
            url = f"{K10_SCRIPTS_BASE}/{name}"
            dest = os.path.join(dest_root, name)
            req = urllib.request.Request(url, headers={"User-Agent": "monitor_agent/sync"})
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = resp.read()
            if len(data) < 200:
                raise ValueError(f"script too small: {name}")
            with open(dest, "wb") as handle:
                handle.write(data)
            synced.append(name)
        except Exception as exc:
            errors.append(f"{name}:{str(exc)[:120]}")
    return {"step": "sync_stability_scripts", "ok": bool(synced), "synced": synced, "errors": errors}


def ensure_satellite_job_worker() -> dict | None:
    """Start lavie_job_worker on red_lavie when monitor is up but :5682 is down."""
    if not _is_red_lavie_host():
        return None
    if _worker_health_ok():
        return {"step": "job_worker", "ok": True, "skipped": "already_up", "port": RED_LAVIE_WORKER_PORT}
    token = _load_satellite_job_token()
    if not token:
        return {"step": "job_worker", "ok": False, "error": "SATELLITE_JOB_TOKEN missing"}
    ps1_dest = os.path.join(os.environ.get("TEMP", "."), "red_lavie_start_job_worker.ps1")
    try:
        url = f"{K10_SCRIPTS_BASE}/red_lavie_start_job_worker.ps1"
        req = urllib.request.Request(url, headers={"User-Agent": "monitor_agent/recover"})
        with urllib.request.urlopen(req, timeout=45) as resp:
            data = resp.read()
        if len(data) < 200:
            raise ValueError("worker script too small")
        with open(ps1_dest, "wb") as handle:
            handle.write(data)
    except Exception as exc:
        return {"step": "job_worker", "ok": False, "error": f"download_failed: {exc}"[:200]}
    cmd = (
        f'powershell -NoProfile -ExecutionPolicy Bypass -File "{ps1_dest}" '
        f'-K10 "{K10_SCRIPTS_BASE}" -Token "{token}" -Port {RED_LAVIE_WORKER_PORT}'
    )
    try:
        proc = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=150,
            creationflags=0x08000000,
        )
        out = (proc.stdout or "") + (proc.stderr or "")
        ok = proc.returncode == 0 and _worker_health_ok()
        return {
            "step": "job_worker",
            "ok": ok,
            "exit_code": proc.returncode,
            "detail": out[-500:],
            "port": RED_LAVIE_WORKER_PORT,
        }
    except Exception as exc:
        return {"step": "job_worker", "ok": False, "error": str(exc)[:200]}


def recover_satellite_worker_endpoint() -> dict:
    sync = _sync_stability_scripts_from_k10()
    worker = ensure_satellite_job_worker() or {"step": "job_worker", "ok": False, "error": "not_red_lavie"}
    steps = [item for item in (sync, worker) if item]
    ok = all(step.get("ok") for step in steps if step)
    return {
        "ok": ok,
        "schema": "clawstack.satellite_recover_worker.v1",
        "hostname": socket.gethostname(),
        "steps": steps,
        "message": "SATELLITE_WORKER_RECOVERED" if ok else "SATELLITE_WORKER_RECOVER_FAILED",
    }


def _monitor_deploy_paths() -> list[str]:
    return [
        os.path.join("C:\\", "clawstack_satellite", "scripts", "monitor_agent.py"),
        os.path.join("C:\\", "lavie_usb_pack", "scripts", "monitor_agent.py"),
        os.path.join(PROGRAMDATA_ROOT, "Clawstack", "monitor_agent", "monitor_agent.py"),
    ]


def _maybe_reload_monitor_from_disk():
    try:
        this_mtime = os.path.getmtime(__file__)
    except OSError:
        return None
    for path in _monitor_deploy_paths():
        if not os.path.isfile(path):
            continue
        try:
            if os.path.getmtime(path) <= this_mtime + 2:
                continue
        except OSError:
            continue
        subprocess.Popen(
            ["pythonw.exe", path],
            creationflags=0x08000000,
            close_fds=True,
        )

        def _exit_later() -> None:
            time.sleep(2)
            os._exit(0)

        threading.Thread(target=_exit_later, daemon=True).start()
        return {"ok": True, "step": "monitor_reload", "path": path}
    return None


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
                    _append_node_diagnostic(
                        "thermal_throttle",
                        {"label": target_label, "temp_c": temp, "cpu_limit_percent": target_limit},
                        severity="warn" if target_limit < NORMAL_PERCENT else "info",
                    )

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
                _append_node_diagnostic("harvester_started", {"script": becky_script}, severity="info")
            if os.path.exists(gmail_script) and (gmail_proc is None or gmail_proc.poll() is not None):
                gmail_proc = subprocess.Popen(["python", gmail_script])
                _append_node_diagnostic("harvester_started", {"script": gmail_script}, severity="info")
        except Exception as e:
            _append_node_diagnostic("harvester_watchdog_error", {"error": str(e)}, severity="error")
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
                "updater_logs": updater_logs,
                "node_diagnostic": _diagnostic_status(),
            }
            response = json.dumps(debug_info).encode('utf-8')
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Content-Length', str(len(response)))
            self.end_headers()
            self.wfile.write(response)
        elif self.path == "/diagnostics":
            payload = {
                "status": _diagnostic_status(),
                "recent": _read_recent_node_diagnostics(200),
                "wlan_snapshot": _collect_wlan_snapshot(),
                "wlan_telemetry_tail": _read_wlan_telemetry_tail(80),
                "wlan_recent_events_48h": _collect_wlan_recent_events(20),
            }
            response = json.dumps(payload, ensure_ascii=False).encode('utf-8')
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Content-Length', str(len(response)))
            self.end_headers()
            self.wfile.write(response)
        elif self.path in ("/diagnostics/outage_forensics", "/outage_forensics"):
            payload = build_outage_forensics_report()
            response = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Content-Length", str(len(response)))
            self.end_headers()
            self.wfile.write(response)
        elif self.path in ("/host_stability/apply", "/host_stability"):
            payload = apply_host_stability()
            response = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            self.send_response(200 if payload.get("ok") else 207)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Content-Length", str(len(response)))
            self.end_headers()
            self.wfile.write(response)
        elif self.path in ("/satellite/recover_worker", "/recover_worker"):
            payload = recover_satellite_worker_endpoint()
            response = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            self.send_response(200 if payload.get("ok") else 503)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Content-Length", str(len(response)))
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
    _append_node_diagnostic(
        "agent_start",
        {
            "port": port,
            "pid": os.getpid(),
            "programdata_root": PROGRAMDATA_ROOT,
            "fleet_evidence_url": FLEET_EVIDENCE_URL,
            "diagnostic_retention_hours": NODE_DIAGNOSTIC_RETENTION_HOURS,
        },
        severity="info",
    )
    
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
    _append_node_diagnostic("agent_stop", {"port": port, "pid": os.getpid()}, severity="warn")
    httpd.server_close()

if __name__ == "__main__":
    run(port=int(os.environ.get("MONITOR_AGENT_PORT", "8111")))
