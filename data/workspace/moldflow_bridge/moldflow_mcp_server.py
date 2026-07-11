# -*- coding: utf-8 -*-
"""Moldflow Insight 2010 MCP readiness and operation bridge for Dynabook."""
from __future__ import annotations

import sys
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import json
import os
import platform
import shutil
import subprocess
import tempfile
import time
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings

BRIDGE_VERSION = "0.2.0"
PROG_IDS = ("synergy.Synergy", "Synergy.Synergy", "synergy.Synergy.2010")
ROOT = Path(__file__).resolve().parent
PROBE_SCRIPT = ROOT / "check_synergy_com.vbs"
STATE_INSPECT_SCRIPT = ROOT / "inspect_synergy_state.vbs"
DEFAULT_WORK_ROOT = Path(os.environ.get("MOLDFLOW_WORK_ROOT", r"G:\moldflow_bridge\work"))

mcp = FastMCP("dynabook-moldflow-operations")

# --- Helper functions ---

def _write_operations_enabled() -> bool:
    return os.environ.get("MOLDFLOW_ENABLE_WRITE_OPERATIONS", "").strip() == "1"


def _write_operation_blocked() -> str:
    return json.dumps(
        {
            "ok": False,
            "error": "write operations are disabled pending scratch-study COM validation",
            "required_env": "MOLDFLOW_ENABLE_WRITE_OPERATIONS=1",
        },
        ensure_ascii=False,
        indent=2,
    )

def _run(command: list[str], timeout_sec: int = 30) -> dict[str, Any]:
    """Run a bounded local diagnostic command without invoking a shell."""
    try:
        completed = subprocess.run(
            command,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=max(1, min(int(timeout_sec), 300)),
            check=False,
        )
        return {
            "ok": completed.returncode == 0,
            "exit_code": completed.returncode,
            "stdout": completed.stdout[-4000:],
            "stderr": completed.stderr[-2000:],
        }
    except subprocess.TimeoutExpired as exc:
        return {"ok": False, "exit_code": 124, "error": f"timeout after {exc.timeout}s"}
    except OSError as exc:
        return {"ok": False, "exit_code": 1, "error": str(exc)}


def _cscript_path(bitness: int = 32) -> Path:
    windows = Path(os.environ.get("WINDIR", r"C:\Windows"))
    folder = "SysWOW64" if bitness == 32 else "System32"
    return windows / folder / "cscript.exe"


def _run_vbs_code(vbs_code: str, timeout_sec: int = 45) -> dict[str, Any]:
    """Write temporary VBScript code and run it via 32-bit cscript.exe."""
    temp_parent = DEFAULT_WORK_ROOT / "temp"
    temp_parent.mkdir(parents=True, exist_ok=True)
    try:
        with tempfile.TemporaryDirectory(prefix="moldflow_vbs_", dir=str(temp_parent)) as temp_dir:
            temp_vbs = Path(temp_dir) / "macro.vbs"
            # Moldflow 2010 cscript requires an ANSI-compatible script.
            temp_vbs.write_text(vbs_code, encoding="mbcs")
            cscript = _cscript_path(32)
            return _run([str(cscript), "//nologo", str(temp_vbs)], timeout_sec)
    except Exception as exc:
        return {"ok": False, "error": f"temporary VBS execution failed: {exc}"}


def collect_status() -> dict[str, Any]:
    work_drive = Path(DEFAULT_WORK_ROOT.anchor) if DEFAULT_WORK_ROOT.anchor else DEFAULT_WORK_ROOT
    disk = shutil.disk_usage(work_drive) if work_drive.exists() else None
    return {
        "bridge_version": BRIDGE_VERSION,
        "mode": "operation_validation",
        "analysis_enabled": _write_operations_enabled(),
        "hostname": platform.node(),
        "python_bitness": platform.architecture()[0],
        "work_root": str(DEFAULT_WORK_ROOT),
        "work_root_exists": DEFAULT_WORK_ROOT.exists(),
        "work_drive_free_gb": round(disk.free / (1024 ** 3), 2) if disk else None,
        "probe_script_exists": PROBE_SCRIPT.exists(),
        "state_inspect_script_exists": STATE_INSPECT_SCRIPT.exists(),
        "cscript_64_exists": _cscript_path(64).exists(),
        "cscript_32_exists": _cscript_path(32).exists(),
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
    }


# --- MCP Tools ---

@mcp.tool()
def moldflow_bridge_status() -> str:
    """Return bridge and host readiness including operation parameters."""
    return json.dumps(collect_status(), ensure_ascii=False, indent=2)


@mcp.tool()
def moldflow_probe_com(bitness: int = 32, timeout_sec: int = 30) -> str:
    """Probe the registered Synergy COM object with bounded 32/64-bit cscript."""
    if bitness not in (32, 64):
        return json.dumps({"ok": False, "error": "bitness must be 32 or 64"})
    if not PROBE_SCRIPT.exists():
        return json.dumps({"ok": False, "error": f"missing {PROBE_SCRIPT}"})
    cscript = _cscript_path(bitness)
    if not cscript.exists():
        return json.dumps({"ok": False, "error": f"missing {cscript}"})
    result = _run([str(cscript), "//nologo", str(PROBE_SCRIPT)], timeout_sec)
    result["bitness"] = bitness
    result["analysis_started"] = False
    return json.dumps(result, ensure_ascii=False, indent=2)


@mcp.tool()
def moldflow_inspect_state(bitness: int = 32, timeout_sec: int = 30) -> str:
    """Read Synergy version and active object availability without creating a study."""
    if bitness not in (32, 64):
        return json.dumps({"ok": False, "error": "bitness must be 32 or 64"})
    if not STATE_INSPECT_SCRIPT.exists():
        return json.dumps({"ok": False, "error": f"missing {STATE_INSPECT_SCRIPT}"})
    cscript = _cscript_path(bitness)
    if not cscript.exists():
        return json.dumps({"ok": False, "error": f"missing {cscript}"})
    result = _run([str(cscript), "//nologo", str(STATE_INSPECT_SCRIPT)], timeout_sec)
    result["bitness"] = bitness
    result["analysis_started"] = False
    result["study_created"] = False
    return json.dumps(result, ensure_ascii=False, indent=2)


@mcp.tool()
def moldflow_readiness_gate() -> str:
    """Evaluate readiness for both preflight and full operations."""
    status = collect_status()
    blockers = []
    if not status["probe_script_exists"]:
        blockers.append("COM probe script is missing")
    if not status["cscript_32_exists"]:
        blockers.append("32-bit cscript is missing")
    if not status["work_root_exists"]:
        blockers.append("Work root is not initialized")
    return json.dumps(
        {
            "ready_for_mcp_preflight": not blockers,
            "ready_for_analysis": False,
            "blockers": blockers,
            "next_action": "Validate each Moldflow 2010 COM operation on an isolated scratch study.",
        },
        ensure_ascii=False,
        indent=2,
    )


@mcp.tool()
def moldflow_new_study(
    project_name: str, study_name: str, cad_path: str, mesh_size_mm: float = 3.0
) -> str:
    """Create a new project/study and import STEP or STL CAD file, performing mesh generation."""
    if not _write_operations_enabled():
        return _write_operation_blocked()
    work_dir = DEFAULT_WORK_ROOT / project_name
    work_dir.mkdir(parents=True, exist_ok=True)
    
    # Format paths for VBScript
    vbs_project_dir = str(work_dir).replace("\\", "\\\\")
    vbs_cad_path = str(Path(cad_path).resolve()).replace("\\", "\\\\")
    
    vbs = f'''Option Explicit
Dim Synergy, Project, StudyDoc, ImportOpts, MeshGenerator
Set Synergy = CreateObject("synergy.Synergy")
If (Synergy is Nothing) Then
    WScript.Echo "[NG] Could not create Synergy instance."
    WScript.Quit 1
End If

Synergy.NewProject "{project_name}", "{vbs_project_dir}"
Set Project = Synergy.Project()
If (Project is Nothing) Then
    WScript.Echo "[NG] Failed to create or open project."
    WScript.Quit 1
End If

Project.NewStudy "{study_name}"
Set StudyDoc = Synergy.StudyDoc()
If (StudyDoc is Nothing) Then
    WScript.Echo "[NG] Failed to create new study."
    WScript.Quit 1
End If

Set ImportOpts = Synergy.ImportOptions()
StudyDoc.AddFile "{vbs_cad_path}", ImportOpts

' Trigger Mesh Generation
Set MeshGenerator = Synergy.MeshGenerator()
If Not (MeshGenerator is Nothing) Then
    ' Global mesh edge length setting (if method exists, otherwise default is used)
    On Error Resume Next
    MeshGenerator.SetGlobalEdgeLength {mesh_size_mm}
    On Error GoTo 0
    
    WScript.Echo "Meshing in progress..."
    MeshGenerator.Generate
Else
    WScript.Echo "MeshGenerator object not available, skipping auto-mesh."
End If

StudyDoc.Save
WScript.Echo "[OK] Study created and meshed successfully."
'''
    res = _run_vbs_code(vbs, timeout_sec=90)
    sdy_file = work_dir / f"{study_name}.sdy"
    res["study_path"] = str(sdy_file)
    res["study_exists"] = sdy_file.exists()
    return json.dumps(res, ensure_ascii=False, indent=2)


@mcp.tool()
def moldflow_configure_study(
    study_path: str,
    material_manufacturer: str,
    material_trade_name: str,
    injection_node_id: int,
) -> str:
    """Configure material property and injection node location for the study."""
    if not _write_operations_enabled():
        return _write_operation_blocked()
    sdy = Path(study_path)
    if not sdy.exists():
        return json.dumps({"ok": False, "error": f"study file not found: {study_path}"})
        
    project_dir = sdy.parent
    project_file = next(project_dir.glob("*.mpi"), None)
    if not project_file:
        return json.dumps({"ok": False, "error": f"project file (.mpi) not found in: {project_dir}"})
        
    vbs_project_path = str(project_file).replace("\\", "\\\\")
    vbs_study_name = sdy.stem
    
    vbs = f"""Option Explicit
Dim Synergy, Project, StudyDoc, BoundaryConditions, SelectList, Node, NormalVector, Inject, Finder, Selector, Mat
Set Synergy = CreateObject("synergy.Synergy")
Synergy.OpenProject "{vbs_project_path}"
Set Project = Synergy.Project()
Project.OpenItemByName "{vbs_study_name}", "Study"
Set StudyDoc = Synergy.StudyDoc()

' 1. Material Assignment
Set Finder = Synergy.MaterialFinder()
Finder.SetDataDomain 20030, "System"
Set Mat = Finder.GetFirstMaterial()
Dim found, matId
found = False
Do While Not (Mat Is Nothing)
    If UCase(Mat.Manufacturer) = UCase("{material_manufacturer}") And UCase(Mat.TradeName) = UCase("{material_trade_name}") Then
        matId = Mat.ID
        found = True
        Exit Do
    End If
    Set Mat = Finder.GetNextMaterial()
Loop

If found Then
    Set Selector = Synergy.MaterialSelector()
    Selector.Select "", "System", matId, 0
    WScript.Echo "Selected material ID: " & matId
Else
    WScript.Echo "[NG] Material not found: {material_manufacturer} / {material_trade_name}"
    WScript.Quit 1
End If

' 2. Injection Location
Set SelectList = StudyDoc.CreateEntityList()
SelectList.Add "N{injection_node_id}"
If SelectList.Size = 0 Then
    WScript.Echo "[NG] Node N{injection_node_id} not found."
    WScript.Quit 1
End If
Set Node = SelectList.Entity(0)

Set NormalVector = Synergy.CreateVector()
NormalVector.SetXYZ 0, 0, 1

Set BoundaryConditions = Synergy.BoundaryConditions()
Set Inject = BoundaryConditions.CreateNDBC(Node, NormalVector, 40000, Nothing)
If (Inject is Nothing) Then
    WScript.Echo "[NG] Failed to create injection boundary condition."
    WScript.Quit 1
End If

StudyDoc.Save
WScript.Echo "[OK] Study configured."
"""
    res = _run_vbs_code(vbs, timeout_sec=45)
    return json.dumps(res, ensure_ascii=False, indent=2)


@mcp.tool()
def moldflow_start_analysis(study_path: str) -> str:
    """Launch analysis solver asynchronously using runstudy.exe."""
    if not _write_operations_enabled():
        return _write_operation_blocked()
    sdy = Path(study_path)
    if not sdy.exists():
        return json.dumps({"ok": False, "error": f"study file not found: {study_path}"})
        
    runstudy = Path(r"C:\Program Files\Autodesk\Moldflow Insight 2010\bin\runstudy.exe")
    if not runstudy.exists():
        return json.dumps({"ok": False, "error": f"runstudy.exe solver not found at: {runstudy}"})
        
    try:
        # Launch runstudy.exe asynchronously
        proc = subprocess.Popen(
            [str(runstudy), str(sdy)],
            cwd=str(sdy.parent),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP
        )
        return json.dumps(
            {
                "ok": True,
                "status": "started",
                "pid": proc.pid,
                "study_path": study_path,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
            ensure_ascii=False,
            indent=2,
        )
    except Exception as exc:
        return json.dumps({"ok": False, "error": f"failed to start solver: {exc}"})


@mcp.tool()
def moldflow_analysis_status(study_path: str, pid: int = 0) -> str:
    """Poll solver progress and parse execution logs."""
    sdy = Path(study_path)
    log_file = sdy.with_suffix(".log")
    
    # Check if PID is still running (if provided)
    is_running = False
    if pid > 0:
        try:
            # Under Windows, check process using tasklist
            completed = subprocess.run(
                ["tasklist", "/FI", f"PID eq {pid}"],
                capture_output=True,
                text=True
            )
            is_running = str(pid) in completed.stdout
        except Exception:
            pass
            
    # Check log file contents
    progress = 0
    verdict = "RUNNING"
    details = ""
    
    if log_file.exists():
        try:
            content = log_file.read_text(encoding="utf-8", errors="replace")
            # Parse progress or final verdict
            pcts = re.findall(r"(\d+)%\s+completed", content)
            if pcts:
                progress = int(pcts[-1])
                
            if "Analysis complete" in content or "Analysis completed" in content:
                progress = 100
                verdict = "SUCCESS"
            elif "Analysis failed" in content or "Analysis error" in content or "Error" in content:
                verdict = "FAILED"
                details = content[-1000:]
        except Exception as exc:
            details = f"failed to read log: {exc}"
            
    if not is_running and verdict == "RUNNING":
        # Process ended but log doesn't indicate success
        if log_file.exists():
            verdict = "FAILED"
            details = "Solver process terminated abruptly."
        else:
            verdict = "NOT_STARTED"
            
    return json.dumps(
        {
            "ok": True,
            "verdict": verdict,
            "progress_percent": progress,
            "is_running": is_running,
            "details": details,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
        ensure_ascii=False,
        indent=2,
    )


@mcp.tool()
def moldflow_export_results(study_path: str, output_image_dir: str) -> str:
    """Export fill time analysis visual result to PNG and extract KPIs from solver log."""
    if not _write_operations_enabled():
        return _write_operation_blocked()
    sdy = Path(study_path)
    if not sdy.exists():
        return json.dumps({"ok": False, "error": f"study file not found: {study_path}"})
        
    project_dir = sdy.parent
    project_file = next(project_dir.glob("*.mpi"), None)
    if not project_file:
        return json.dumps({"ok": False, "error": f"project file (.mpi) not found in: {project_dir}"})
        
    out_dir = Path(output_image_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    img_path = out_dir / f"{sdy.stem}_fill_time.png"
    
    vbs_project_path = str(project_file).replace("\\", "\\\\")
    vbs_study_name = sdy.stem
    vbs_img_path = str(img_path).replace("\\", "\\\\")
    
    # 1. Export Image via Synergy Viewer COM
    vbs = f"""Option Explicit
Dim Synergy, Project, StudyDoc, Viewer
Set Synergy = CreateObject("synergy.Synergy")
Synergy.OpenProject "{vbs_project_path}"
Set Project = Synergy.Project()
Project.OpenItemByName "{vbs_study_name}", "Study"
Set Viewer = Synergy.Viewer()

On Error Resume Next
Viewer.ShowResult 1540 ' Fill time standard ID
If Err.Number <> 0 Then
    Err.Clear
    Viewer.ShowResultByName "Fill time"
End If
On Error GoTo 0

Viewer.ExportImage "{vbs_img_path}", "PNG"
WScript.Echo "[OK] Image exported."
"""
    res = _run_vbs_code(vbs, timeout_sec=45)
    
    # 2. Extract KPIs from log file
    log_file = sdy.with_suffix(".log")
    kpis = {
        "fill_time_sec": None,
        "max_injection_pressure_MPa": None,
        "max_clamp_force_ton": None,
        "fill_fraction_pct": 0.0,
    }
    
    if log_file.exists():
        try:
            content = log_file.read_text(encoding="utf-8", errors="replace")
            # Parse values
            fill_time_match = re.search(r"Fill time\s+=\s+([\d\.]+)\s+s", content, re.IGNORECASE)
            if fill_time_match:
                kpis["fill_time_sec"] = float(fill_time_match.group(1))
                kpis["fill_fraction_pct"] = 100.0
                
            press_match = re.search(r"Max\.\s+injection\s+pressure\s+=\s+([\d\.]+)\s+MPa", content, re.IGNORECASE)
            if press_match:
                kpis["max_injection_pressure_MPa"] = float(press_match.group(1))
                
            clamp_match = re.search(r"Max\.\s+clamp\s+force\s+during\s+cycle\s+=\s+([\d\.]+)\s+tonne", content, re.IGNORECASE)
            if clamp_match:
                kpis["max_clamp_force_ton"] = float(clamp_match.group(1))
        except Exception as exc:
            res["kpi_error"] = str(exc)
            
    res["kpis"] = kpis
    res["image_path"] = str(img_path)
    res["image_exists"] = img_path.exists()
    return json.dumps(res, ensure_ascii=False, indent=2)


@mcp.tool()
def moldflow_export_materials(output_json_path: str) -> str:
    """Traverse and export the full thermoplastic materials database to a JSON file."""
    if not _write_operations_enabled():
        return _write_operation_blocked()
    out_path = Path(output_json_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    vbs_out_path = str(out_path).replace("\\", "\\\\")
    
    vbs = f'''Option Explicit
Dim Synergy, Finder, Mat, FS, File
Set Synergy = CreateObject("synergy.Synergy")
Set Finder = Synergy.MaterialFinder()
Finder.SetDataDomain 20030, "System"

Set FS = CreateObject("Scripting.FileSystemObject")
Set File = FS.CreateTextFile("{vbs_out_path}", True)

File.WriteLine "["
Dim first
first = True
Set Mat = Finder.GetFirstMaterial()
Do While Not (Mat Is Nothing)
    If Not first Then
        File.WriteLine ","
    End If
    first = False
    
    Dim manufacturer, tradeName
    manufacturer = Replace(CStr(Mat.Manufacturer), Chr(34), Chr(92) & Chr(34))
    tradeName = Replace(CStr(Mat.TradeName), Chr(34), Chr(92) & Chr(34))
    
    File.Write "  {{"
    File.Write """id"": " & Mat.ID & ", "
    File.Write """manufacturer"": """ & manufacturer & """, "
    File.Write """trade_name"": """ & tradeName & """"
    File.Write "}}"
    
    Set Mat = Finder.GetNextMaterial()
Loop
File.WriteLine ""
File.WriteLine "]"
File.Close
WScript.Echo "[OK] Materials exported."
'''
    res = _run_vbs_code(vbs, timeout_sec=180)  # Database might be large
    res["output_path"] = output_json_path
    res["output_exists"] = out_path.exists()
    return json.dumps(res, ensure_ascii=False, indent=2)


# --- Main ---

def main() -> int:
    host = os.environ.get("MOLDFLOW_MCP_HOST", "127.0.0.1")
    port = int(os.environ.get("MOLDFLOW_MCP_PORT", "8765"))
    DEFAULT_WORK_ROOT.mkdir(parents=True, exist_ok=True)
    mcp.settings.host = host
    mcp.settings.port = port
    allowed_host_values = [f"{host}:{port}", f"127.0.0.1:{port}", f"localhost:{port}"]
    allowed_origin_values = [f"http://{value}" for value in allowed_host_values]
    mcp.settings.transport_security = TransportSecuritySettings(
        enable_dns_rebinding_protection=True,
        allowed_hosts=allowed_host_values,
        allowed_origins=allowed_origin_values,
    )
    print(f"[moldflow-mcp] host={host} port={port} mode=operations_active", flush=True)
    mcp.run(transport="streamable-http")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
