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

BRIDGE_VERSION = "0.4.0"
PROG_IDS = ("synergy.Synergy", "Synergy.Synergy", "synergy.Synergy.2010")
ROOT = Path(__file__).resolve().parent
PROBE_SCRIPT = ROOT / "check_synergy_com.vbs"
STATE_INSPECT_SCRIPT = ROOT / "inspect_synergy_state.vbs"
MEMBER_INSPECT_SCRIPT = ROOT / "inspect_synergy_members.vbs"
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


def _run_vbs_code(
    vbs_code: str, timeout_sec: int = 45, bitness: int = 32
) -> dict[str, Any]:
    """Write temporary VBScript code and run it via 32-bit cscript.exe."""
    if bitness not in (32, 64):
        return {"ok": False, "error": "bitness must be 32 or 64"}
    temp_parent = DEFAULT_WORK_ROOT / "temp"
    temp_parent.mkdir(parents=True, exist_ok=True)
    try:
        with tempfile.TemporaryDirectory(prefix="moldflow_vbs_", dir=str(temp_parent)) as temp_dir:
            temp_vbs = Path(temp_dir) / "macro.vbs"
            # Moldflow 2010 cscript requires an ANSI-compatible script.
            temp_vbs.write_text(vbs_code, encoding="mbcs")
            cscript = _cscript_path(bitness)
            result = _run([str(cscript), "//nologo", str(temp_vbs)], timeout_sec)
            stderr = str(result.get("stderr") or "")
            if "Microsoft VBScript" in stderr:
                result["ok"] = False
                result["exit_code"] = 1
                result["failure_tag"] = "vbscript_runtime_error"
            return result
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
        "member_inspect_script_exists": MEMBER_INSPECT_SCRIPT.exists(),
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
def moldflow_inspect_active_study(timeout_sec: int = 180) -> str:
    """Read active-study mesh and gate data without modifying the study."""
    vbs = r'''Option Explicit
Dim Synergy, StudyDoc, Ent, Coord, DiagnosisManager, Summary, Project
Dim FS, TempFolder, UdmPath, UdmFile, Line, Words
Dim GateNodeIDs(), GateCount, GateType, GateNodeID, I, Found

On Error Resume Next
Set Synergy = CreateObject("synergy.Synergy")
If Err.Number <> 0 Then
    WScript.Echo "ERROR=CREATEOBJECT_FAILED:" & Err.Number & ":" & Err.Description
    WScript.Quit 2
End If

Err.Clear
Set StudyDoc = Synergy.StudyDoc()
If Err.Number <> 0 Or StudyDoc Is Nothing Then
    WScript.Echo "ERROR=NO_ACTIVE_STUDY:" & Err.Number & ":" & Err.Description
    WScript.Quit 3
End If

WScript.Echo "READ_ONLY=true"
Err.Clear
WScript.Echo "STUDY_NAME=" & CStr(StudyDoc.StudyName)
WScript.Echo "STUDY_NAME_ERROR=" & CStr(Err.Number)
Err.Clear
WScript.Echo "MESH_TYPE=" & CStr(StudyDoc.MeshType)
WScript.Echo "MESH_TYPE_ERROR=" & CStr(Err.Number)
Err.Clear
WScript.Echo "MOLDING_PROCESS=" & CStr(StudyDoc.MoldingProcess)
WScript.Echo "MOLDING_PROCESS_ERROR=" & CStr(Err.Number)
Err.Clear
WScript.Echo "ANALYSIS_SEQUENCE=" & CStr(StudyDoc.AnalysisSequence)
WScript.Echo "ANALYSIS_SEQUENCE_ERROR=" & CStr(Err.Number)
Err.Clear
WScript.Echo "NUMBER_OF_ANALYSES=" & CStr(StudyDoc.NumberOfAnalyses)
WScript.Echo "NUMBER_OF_ANALYSES_ERROR=" & CStr(Err.Number)
Err.Clear
WScript.Echo "MESH_STATUS=" & CStr(StudyDoc.MeshStatus())
WScript.Echo "MESH_STATUS_ERROR=" & CStr(Err.Number)

Err.Clear
Set Ent = StudyDoc.GetFirstNode()
If Not Ent Is Nothing Then
    WScript.Echo "FIRST_NODE_ID=" & CStr(StudyDoc.GetEntityID(Ent))
    Set Coord = StudyDoc.GetNodeCoord(Ent)
    If Not Coord Is Nothing Then
        WScript.Echo "FIRST_NODE_X=" & CStr(Coord.X)
        WScript.Echo "FIRST_NODE_Y=" & CStr(Coord.Y)
        WScript.Echo "FIRST_NODE_Z=" & CStr(Coord.Z)
    End If
End If
WScript.Echo "FIRST_NODE_ERROR=" & CStr(Err.Number)

Err.Clear
Set DiagnosisManager = Synergy.DiagnosisManager()
Set Summary = DiagnosisManager.GetMeshSummary(False)
If Err.Number <> 0 Or Summary Is Nothing Then
    WScript.Echo "MESH_SUMMARY_ERROR=" & CStr(Err.Number) & ":" & Err.Description
Else
    WScript.Echo "NODE_COUNT=" & CStr(Summary.NodesCount)
    WScript.Echo "TRI_COUNT=" & CStr(Summary.TrianglesCount)
    WScript.Echo "TET_COUNT=" & CStr(Summary.TetrasCount)
    WScript.Echo "BEAM_COUNT=" & CStr(Summary.BeamsCount)
    WScript.Echo "CONNECTIVITY_REGIONS=" & CStr(Summary.ConnectivityRegions)
    WScript.Echo "MESH_VOLUME=" & CStr(Summary.MeshVolume)
    WScript.Echo "RUNNER_VOLUME=" & CStr(Summary.RunnerVolume)
    WScript.Echo "MIN_ASPECT_RATIO=" & CStr(Summary.MinAspectRatio)
    WScript.Echo "MAX_ASPECT_RATIO=" & CStr(Summary.MaxAspectRatio)
    WScript.Echo "AVE_ASPECT_RATIO=" & CStr(Summary.AveAspectRatio)
    WScript.Echo "FREE_EDGES=" & CStr(Summary.FreeEdges)
    WScript.Echo "MANIFOLD_EDGES=" & CStr(Summary.ManifoldEdges)
    WScript.Echo "NONMANIFOLD_EDGES=" & CStr(Summary.NonManifoldEdges)
    WScript.Echo "UNORIENTED=" & CStr(Summary.Unoriented)
    WScript.Echo "INTERSECTION_ELEMENTS=" & CStr(Summary.IntersectionElements)
    WScript.Echo "OVERLAP_ELEMENTS=" & CStr(Summary.OverlapElements)
    WScript.Echo "ZERO_TRIANGLES=" & CStr(Summary.ZeroTriangles)
    WScript.Echo "ZERO_BEAMS=" & CStr(Summary.ZeroBeams)
End If

' Moldflow has no direct API getter for NDBC data. Autodesk's documented
' workaround is a read-only UDM export followed by parsing NDBC records.
GateCount = 0
Set FS = CreateObject("Scripting.FileSystemObject")
Set TempFolder = FS.GetSpecialFolder(2)
UdmPath = TempFolder.Path & "\moldflow_mcp_gate_" & _
    Replace(Replace(Replace(CStr(Now), "/", ""), ":", ""), " ", "_") & ".udm"

Err.Clear
Set Project = Synergy.Project()
Project.ExportModel UdmPath
If Err.Number <> 0 Or Not FS.FileExists(UdmPath) Then
    WScript.Echo "GATE_EXPORT_ERROR=" & CStr(Err.Number) & ":" & Err.Description
Else
    Err.Clear
    Set UdmFile = FS.OpenTextFile(UdmPath, 1, False)
    Do While Not UdmFile.AtEndOfStream
        Line = UdmFile.ReadLine
        If InStr(Line, "NDBC{") > 0 And Left(Trim(Line), 2) <> "//" Then
            Words = Split(Trim(Replace(Replace(Line, "{", " "), "}", " ")))
            If UBound(Words) >= 8 Then
                GateType = CLng(Words(6))
                If GateType = 40000 Or GateType = 40002 Or GateType = 40003 Then
                    GateNodeID = CLng(Words(8))
                    ReDim Preserve GateNodeIDs(GateCount)
                    GateNodeIDs(GateCount) = GateNodeID
                    GateCount = GateCount + 1
                End If
            End If
        End If
    Loop
    UdmFile.Close
End If

If FS.FileExists(UdmPath) Then
    Err.Clear
    FS.DeleteFile UdmPath, True
    WScript.Echo "GATE_TEMP_CLEANUP_ERROR=" & CStr(Err.Number)
End If

WScript.Echo "GATE_INSPECTION_SUPPORTED=true"
WScript.Echo "GATE_COUNT=" & CStr(GateCount)
For I = 0 To GateCount - 1
    GateNodeID = GateNodeIDs(I)
    WScript.Echo "GATE_" & CStr(I + 1) & "_NODE_ID=" & CStr(GateNodeID)
    Found = False
    Set Ent = StudyDoc.GetFirstNode()
    Do While Not Ent Is Nothing And Not Found
        If CLng(StudyDoc.GetEntityID(Ent)) = GateNodeID Then
            Set Coord = StudyDoc.GetNodeCoord(Ent)
            If Not Coord Is Nothing Then
                WScript.Echo "GATE_" & CStr(I + 1) & "_X=" & CStr(Coord.X)
                WScript.Echo "GATE_" & CStr(I + 1) & "_Y=" & CStr(Coord.Y)
                WScript.Echo "GATE_" & CStr(I + 1) & "_Z=" & CStr(Coord.Z)
            End If
            Found = True
        Else
            Set Ent = StudyDoc.GetNextNode(Ent)
        End If
    Loop
    WScript.Echo "GATE_" & CStr(I + 1) & "_COORD_FOUND=" & CStr(Found)
Next
'''
    result = _run_vbs_code(vbs, timeout_sec=max(10, min(int(timeout_sec), 180)))
    parsed: dict[str, Any] = {}
    for line in str(result.get("stdout") or "").splitlines():
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        parsed[key.strip().lower()] = value.strip()
    result["study"] = parsed
    result["read_only"] = True
    result["analysis_started"] = False
    result["study_created"] = False
    return json.dumps(result, ensure_ascii=False, indent=2)


@mcp.tool()
def moldflow_autofix_active_study_copy(
    expected_study_name: str = "moldflow_study.sdy",
    reuse_active_copy: bool = False,
    timeout_sec: int = 180,
) -> str:
    """Duplicate the expected active study, AutoFix only the copy, and save it."""
    if not _write_operations_enabled():
        return _write_operation_blocked()
    expected = str(expected_study_name or "").strip()
    if not expected or any(char in expected for char in ('"', "\r", "\n")):
        return json.dumps(
            {"ok": False, "error": "expected_study_name is invalid"},
            ensure_ascii=False,
            indent=2,
        )
    expected_base = re.sub(r"(?i)\.sdy$", "", expected)
    expected_canonical = re.sub(r"[^a-z0-9]", "", expected_base.lower())
    reuse_vbs = "True" if reuse_active_copy else "False"
    vbs = f'''Option Explicit
Dim Synergy, Project, StudyDoc, MeshEditor, BeforeNames, Name, NewName
Dim DuplicateOK, OpenOK, RemovedCount, SaveOK, OriginalName
Dim ReuseActiveCopy

Function CanonicalName(Value)
    Dim Regex
    Set Regex = New RegExp
    Regex.Global = True
    Regex.IgnoreCase = True
    Regex.Pattern = "[^a-z0-9]"
    CanonicalName = LCase(Regex.Replace(Replace(CStr(Value), ".sdy", ""), ""))
End Function

ReuseActiveCopy = {reuse_vbs}

On Error Resume Next
Set Synergy = CreateObject("synergy.Synergy")
If Err.Number <> 0 Then
    WScript.Echo "ERROR=CREATEOBJECT_FAILED:" & Err.Number & ":" & Err.Description
    WScript.Quit 2
End If

Set StudyDoc = Synergy.StudyDoc()
If StudyDoc Is Nothing Then
    WScript.Echo "ERROR=NO_ACTIVE_STUDY"
    WScript.Quit 3
End If
OriginalName = CStr(StudyDoc.StudyName)
WScript.Echo "ORIGINAL_STUDY=" & OriginalName
If CanonicalName(OriginalName) <> "{expected_canonical}" Then
    WScript.Echo "ERROR=ACTIVE_STUDY_MISMATCH:expected={expected}:actual=" & OriginalName
    WScript.Quit 4
End If

Set Project = Synergy.Project()
If ReuseActiveCopy Then
    NewName = OriginalName
    WScript.Echo "REUSED_ACTIVE_COPY=true"
Else
Set BeforeNames = CreateObject("Scripting.Dictionary")
Name = Project.GetFirstStudyName()
Do While Name <> ""
    BeforeNames.Add LCase(CStr(Name)), True
    Name = Project.GetNextStudyName(Name)
Loop

Err.Clear
DuplicateOK = Project.DuplicateStudyByName2("{expected_base}", True)
WScript.Echo "DUPLICATE_OK=" & CStr(DuplicateOK)
WScript.Echo "DUPLICATE_ERROR=" & CStr(Err.Number) & ":" & Err.Description
If Not DuplicateOK Or Err.Number <> 0 Then WScript.Quit 5

NewName = ""
Name = Project.GetFirstStudyName()
Do While Name <> ""
    If Not BeforeNames.Exists(LCase(CStr(Name))) Then NewName = CStr(Name)
    Name = Project.GetNextStudyName(Name)
Loop
If NewName = "" Then
    WScript.Echo "ERROR=DUPLICATE_NAME_NOT_FOUND"
    WScript.Quit 6
End If
WScript.Echo "COPY_STUDY=" & NewName

Err.Clear
OpenOK = Project.OpenItemByName(NewName, "Study")
WScript.Echo "COPY_OPEN_OK=" & CStr(OpenOK)
WScript.Echo "COPY_OPEN_ERROR=" & CStr(Err.Number) & ":" & Err.Description
If Not OpenOK Or Err.Number <> 0 Then WScript.Quit 7

Set StudyDoc = Synergy.StudyDoc()
WScript.Echo "ACTIVE_AFTER_OPEN=" & CStr(StudyDoc.StudyName)
If CanonicalName(CStr(StudyDoc.StudyName)) <> CanonicalName(NewName) Then
    WScript.Echo "ERROR=COPY_NOT_ACTIVE"
    WScript.Quit 8
End If
End If

Set MeshEditor = Synergy.MeshEditor()
Err.Clear
RemovedCount = MeshEditor.AutoFix()
WScript.Echo "AUTOFIX_REMOVED=" & CStr(RemovedCount)
WScript.Echo "AUTOFIX_ERROR=" & CStr(Err.Number) & ":" & Err.Description
If Err.Number <> 0 Then WScript.Quit 9

Err.Clear
SaveOK = StudyDoc.Save()
WScript.Echo "COPY_SAVE_OK=" & CStr(SaveOK)
WScript.Echo "COPY_SAVE_ERROR=" & CStr(Err.Number) & ":" & Err.Description
If Not SaveOK Or Err.Number <> 0 Then WScript.Quit 10

WScript.Echo "TARGET_COPY_MODIFIED=true"
WScript.Echo "ANALYSIS_STARTED=false"
'''
    result = _run_vbs_code(vbs, timeout_sec=max(30, min(int(timeout_sec), 300)))
    parsed: dict[str, Any] = {}
    for line in str(result.get("stdout") or "").splitlines():
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        parsed[key.strip().lower()] = value.strip()
    result["operation"] = parsed
    result["copy_only"] = True
    result["analysis_started"] = False
    return json.dumps(result, ensure_ascii=False, indent=2)


@mcp.tool()
def moldflow_mesh_active_study_copy(
    expected_study_name: str,
    mesh_size_mm: float = 3.0,
    timeout_sec: int = 300,
) -> str:
    """Generate a Fusion mesh only when the expected copy is active."""
    if not _write_operations_enabled():
        return _write_operation_blocked()
    expected = str(expected_study_name or "").strip()
    if not expected or any(char in expected for char in ('"', "\r", "\n")):
        return json.dumps({"ok": False, "error": "expected_study_name is invalid"})
    try:
        mesh_size = float(mesh_size_mm)
    except (TypeError, ValueError):
        return json.dumps({"ok": False, "error": "mesh_size_mm must be numeric"})
    if not 0.01 <= mesh_size <= 1000.0:
        return json.dumps({"ok": False, "error": "mesh_size_mm must be between 0.01 and 1000"})
    expected_base = re.sub(r"(?i)\.sdy$", "", expected)
    expected_canonical = re.sub(r"[^a-z0-9]", "", expected_base.lower())
    vbs = f'''Option Explicit
Dim Synergy, StudyDoc, MeshGenerator, Ent, NodeCount, TriCount, SaveOK, Attempt

Function CanonicalName(Value)
    Dim Regex
    Set Regex = New RegExp
    Regex.Global = True
    Regex.IgnoreCase = True
    Regex.Pattern = "[^a-z0-9]"
    CanonicalName = LCase(Regex.Replace(Replace(CStr(Value), ".sdy", ""), ""))
End Function

On Error Resume Next
Set Synergy = GetObject(, "synergy.Synergy")
If Synergy Is Nothing Then
    For Attempt = 1 To 3
        Err.Clear
        Set Synergy = CreateObject("synergy.Synergy")
        If Not Synergy Is Nothing Then Exit For
        WScript.Sleep 2000
    Next
End If
If Synergy Is Nothing Then WScript.Echo "ERROR=CREATEOBJECT_FAILED_AFTER_3_ATTEMPTS:" & Err.Number & ":" & Err.Description: WScript.Quit 2
Set StudyDoc = Synergy.StudyDoc()
If StudyDoc Is Nothing Then WScript.Echo "ERROR=NO_ACTIVE_STUDY": WScript.Quit 3
WScript.Echo "ACTIVE_STUDY=" & CStr(StudyDoc.StudyName)
If CanonicalName(StudyDoc.StudyName) <> "{expected_canonical}" Then
    WScript.Echo "ERROR=ACTIVE_STUDY_MISMATCH:expected={expected}:actual=" & CStr(StudyDoc.StudyName)
    WScript.Quit 4
End If

Set MeshGenerator = Synergy.MeshGenerator()
If MeshGenerator Is Nothing Then WScript.Echo "ERROR=MESH_GENERATOR_UNAVAILABLE": WScript.Quit 5
MeshGenerator.EdgeLength = {mesh_size}
MeshGenerator.MergeTolerance = 0.1
MeshGenerator.Match = True
MeshGenerator.Smoothing = True
MeshGenerator.ElementReduction = False
MeshGenerator.SurfaceOptimization = True
MeshGenerator.PostMeshActions = True
MeshGenerator.RemeshAll = False
MeshGenerator.UseActiveLayer = False
MeshGenerator.SaveOptions
If Err.Number <> 0 Then WScript.Echo "ERROR=MESH_OPTIONS:" & Err.Number & ":" & Err.Description: WScript.Quit 6

Err.Clear
StudyDoc.MeshNow False
WScript.Echo "MESH_NOW_ERROR=" & CStr(Err.Number) & ":" & Err.Description
If Err.Number <> 0 Then WScript.Quit 7

NodeCount = 0
Set Ent = StudyDoc.GetFirstNode()
Do While Not Ent Is Nothing
    NodeCount = NodeCount + 1
    Set Ent = StudyDoc.GetNextNode(Ent)
Loop
TriCount = 0
Set Ent = StudyDoc.GetFirstTriangle()
Do While Not Ent Is Nothing
    TriCount = TriCount + 1
    Set Ent = StudyDoc.GetNextTriangle(Ent)
Loop
WScript.Echo "MESH_STATUS=" & CStr(StudyDoc.MeshStatus())
WScript.Echo "NODE_COUNT=" & CStr(NodeCount)
WScript.Echo "TRI_COUNT=" & CStr(TriCount)
If NodeCount = 0 Or TriCount = 0 Then WScript.Echo "ERROR=EMPTY_MESH": WScript.Quit 8
SaveOK = StudyDoc.Save()
WScript.Echo "SAVE_OK=" & CStr(SaveOK)
If Not SaveOK Then WScript.Quit 9
WScript.Echo "TARGET_COPY_MODIFIED=true"
WScript.Echo "ANALYSIS_STARTED=false"
'''
    result = _run_vbs_code(
        vbs,
        timeout_sec=max(30, min(int(timeout_sec), 300)),
        bitness=64,
    )
    result["copy_only"] = True
    result["analysis_started"] = False
    result["mesh_size_mm"] = mesh_size
    return json.dumps(result, ensure_ascii=False, indent=2)


@mcp.tool()
def moldflow_set_gate_active_study_copy(
    expected_study_name: str,
    injection_node_id: int,
    timeout_sec: int = 60,
) -> str:
    """Create one injection-location NDBC on an explicit node of the active copy."""
    if not _write_operations_enabled():
        return _write_operation_blocked()
    expected = str(expected_study_name or "").strip()
    if not expected or any(char in expected for char in ('"', "\r", "\n")):
        return json.dumps({"ok": False, "error": "expected_study_name is invalid"})
    try:
        node_id = int(injection_node_id)
    except (TypeError, ValueError):
        return json.dumps({"ok": False, "error": "injection_node_id must be an integer"})
    if node_id <= 0:
        return json.dumps({"ok": False, "error": "injection_node_id must be positive"})
    expected_base = re.sub(r"(?i)\.sdy$", "", expected)
    expected_canonical = re.sub(r"[^a-z0-9]", "", expected_base.lower())
    vbs = f'''Option Explicit
Dim Synergy, StudyDoc, SelectList, Node, NormalVector, BoundaryConditions, Inject, SaveOK, Attempt

Function CanonicalName(Value)
    Dim Regex
    Set Regex = New RegExp
    Regex.Global = True
    Regex.IgnoreCase = True
    Regex.Pattern = "[^a-z0-9]"
    CanonicalName = LCase(Regex.Replace(Replace(CStr(Value), ".sdy", ""), ""))
End Function

On Error Resume Next
Set Synergy = GetObject(, "synergy.Synergy")
If Synergy Is Nothing Then
    For Attempt = 1 To 3
        Err.Clear
        Set Synergy = CreateObject("synergy.Synergy")
        If Not Synergy Is Nothing Then Exit For
        WScript.Sleep 2000
    Next
End If
If Synergy Is Nothing Then WScript.Echo "ERROR=CREATEOBJECT_FAILED_AFTER_3_ATTEMPTS:" & Err.Number & ":" & Err.Description: WScript.Quit 2
Set StudyDoc = Synergy.StudyDoc()
If StudyDoc Is Nothing Then WScript.Echo "ERROR=NO_ACTIVE_STUDY": WScript.Quit 3
WScript.Echo "ACTIVE_STUDY=" & CStr(StudyDoc.StudyName)
If CanonicalName(StudyDoc.StudyName) <> "{expected_canonical}" Then
    WScript.Echo "ERROR=ACTIVE_STUDY_MISMATCH:expected={expected}:actual=" & CStr(StudyDoc.StudyName)
    WScript.Quit 4
End If
If CStr(StudyDoc.MeshStatus()) = "Failed" Then WScript.Echo "ERROR=MESH_NOT_READY": WScript.Quit 5

Set SelectList = StudyDoc.CreateEntityList()
SelectList.Add "N{node_id}"
If SelectList.Size = 0 Then WScript.Echo "ERROR=NODE_NOT_FOUND:N{node_id}": WScript.Quit 6
Set Node = SelectList.Entity(0)
Set NormalVector = Synergy.CreateVector()
NormalVector.SetXYZ 0, 0, 1
Set BoundaryConditions = Synergy.BoundaryConditions()
Set Inject = BoundaryConditions.CreateNDBC(Node, NormalVector, 40000, Nothing)
If Inject Is Nothing Or Err.Number <> 0 Then WScript.Echo "ERROR=GATE_CREATE_FAILED:" & Err.Number & ":" & Err.Description: WScript.Quit 7
SaveOK = StudyDoc.Save()
WScript.Echo "SAVE_OK=" & CStr(SaveOK)
If Not SaveOK Then WScript.Quit 8
WScript.Echo "GATE_NODE_ID={node_id}"
WScript.Echo "TARGET_COPY_MODIFIED=true"
WScript.Echo "ANALYSIS_STARTED=false"
'''
    result = _run_vbs_code(
        vbs,
        timeout_sec=max(30, min(int(timeout_sec), 120)),
        bitness=64,
    )
    result["copy_only"] = True
    result["analysis_started"] = False
    result["injection_node_id"] = node_id
    return json.dumps(result, ensure_ascii=False, indent=2)


@mcp.tool()
def moldflow_inspect_members(timeout_sec: int = 30) -> str:
    """List relevant Synergy COM members through TLI without changing a study."""
    if not MEMBER_INSPECT_SCRIPT.exists():
        return json.dumps({"ok": False, "error": f"missing {MEMBER_INSPECT_SCRIPT}"})
    cscript = _cscript_path(32)
    result = _run([str(cscript), "//nologo", str(MEMBER_INSPECT_SCRIPT)], timeout_sec)
    stderr = str(result.get("stderr") or "")
    if "Microsoft VBScript" in stderr:
        result["ok"] = False
        result["failure_tag"] = "vbscript_runtime_error"
    result["read_only"] = True
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
If Not StudyDoc.AddFile("{vbs_cad_path}", ImportOpts) Then
    WScript.Echo "[NG] STL import failed."
    WScript.Quit 2
End If

' Configure the documented Moldflow 2010 mesh generator, then mesh through
' StudyDoc.MeshNow(False) so the completion dialog is suppressed.
Set MeshGenerator = Synergy.MeshGenerator()
If Not (MeshGenerator is Nothing) Then
    MeshGenerator.EdgeLength = {mesh_size_mm}
    MeshGenerator.MergeTolerance = 0.1
    MeshGenerator.Match = True
    MeshGenerator.Smoothing = True
    MeshGenerator.ElementReduction = False
    MeshGenerator.SurfaceOptimization = True
    MeshGenerator.PostMeshActions = True
    MeshGenerator.RemeshAll = False
    MeshGenerator.UseActiveLayer = False
    MeshGenerator.SaveOptions
    WScript.Echo "MESH_STARTED=true"
    StudyDoc.MeshNow False
Else
    WScript.Echo "[NG] MeshGenerator object not available."
    WScript.Quit 3
End If

WScript.Echo "MESH_STATUS=" & CStr(StudyDoc.MeshStatus())
WScript.Echo "SAVE_OK=" & CStr(StudyDoc.Save())
WScript.Echo "ANALYSIS_STARTED=false"
'''
    res = _run_vbs_code(vbs, timeout_sec=300)
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
