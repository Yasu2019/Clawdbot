# -*- coding: utf-8 -*-
"""Moldflow Insight 2010 MCP readiness and operation bridge for Dynabook."""
from __future__ import annotations

import sys
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import base64
import hashlib
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
from typing import Any, Optional

from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings

BRIDGE_VERSION = "0.8.5"
PROG_IDS = ("synergy.Synergy", "Synergy.Synergy", "synergy.Synergy.2010")
ROOT = Path(__file__).resolve().parent
PROBE_SCRIPT = ROOT / "check_synergy_com.vbs"
STATE_INSPECT_SCRIPT = ROOT / "inspect_synergy_state.vbs"
MEMBER_INSPECT_SCRIPT = ROOT / "inspect_synergy_members.vbs"
DEFAULT_WORK_ROOT = Path(os.environ.get("MOLDFLOW_WORK_ROOT", r"G:\moldflow_bridge\work"))
# Thermoplastic System DB domain (NOT 20030 thermoset). Machines use UDB domain tag 30007.
MOLDFLOW_THERMOPLASTIC_DOMAIN = 21000
MOLDFLOW_MACHINE_DOMAIN_TAG = "30007"
# MF2010 Midplane COM-accepted AnalysisSequence strings (Dynabook probe 2026-07-20).
# UI label "Fill + Pack" maps to COM string "Flow" (not "Fill+Pack").
MOLDFLOW_COM_ACCEPTED_SEQUENCES: tuple[str, ...] = ("Fill", "Fast Fill", "Flow", "Cool")
ANALYSIS_SEQUENCE_CATALOG: tuple[dict[str, Any], ...] = (
    {
        "id": "fill",
        "synergy_label": "Fill",
        "com_string": "Fill",
        "com_set_support": "proven_property_assign",
        "mcp_run_support": "proven_runstudy",
        "of_proxy": "resin_fill_cad|resin_fill_vof",
        "notes": "Face-center Fill COMPLETED evidenced",
    },
    {
        "id": "fill_pack",
        "synergy_label": "Fill + Pack",
        "com_string": "Flow",
        "com_set_support": "proven_property_assign_as_Flow",
        "mcp_run_support": "proven_runstudy_flow_20260720",
        "of_proxy": "resin_fill_pack",
        "notes": "UI Fill+Pack -> COM Flow; velocity+pressure phases COMPLETE; packing_time~2.16s",
    },
    {
        "id": "fast_fill",
        "synergy_label": "Fast Fill",
        "com_string": "Fast Fill",
        "com_set_support": "proven_property_assign",
        "mcp_run_support": "proven_runstudy_fastfill_20260720",
        "of_proxy": "resin_fill_vof_fast_profile",
        "notes": "runstudy SUCCESS mf_fc_fastfill_20260720_120214; of1~424KB/~105s vs Fill of1~2.8MB/~506s",
    },
    {
        "id": "cool",
        "synergy_label": "Cool",
        "com_string": "Cool",
        "com_set_support": "proven_property_assign",
        "mcp_run_support": "proven_cool_exe_with_circuits_20260720",
        "of_proxy": "resin_fill_cool",
        "notes": "Strip CLAW_MF HARD_BLOCKED_GEOMETRY (0 channels). Cool SUCCESS via cool.exe on tutorial cpu_base (124 circuits). Prefer cwd=parent.",
    },
    {
        "id": "fill_pack_warp",
        "synergy_label": "Fill + Pack + Warp",
        "com_string": None,
        "com_set_support": "rejected_or_unknown",
        "mcp_run_support": "hard_blocked_error_200052",
        "of_proxy": "resin_fill_cool",
        "notes": "COM rejects Warp combos; warp.exe/warp3d ERROR 200052 interface not specified even with fresh Flow op2. Needs GUI Set Analysis Sequence.",
    },
    {
        "id": "cool_fill_pack_warp",
        "synergy_label": "Cool + Fill + Pack + Warp",
        "com_string": None,
        "com_set_support": "rejected_or_unknown",
        "mcp_run_support": "hard_blocked_error_200052",
        "of_proxy": "resin_fill_cool_orchestrated",
        "notes": "Same Warp COM/GUI dead-end; strip also lacks Cool circuits. Human GUI sequence + channels required.",
    },
)
MOLDFLOW_INSTALL_UDB = Path(
    os.environ.get(
        "MOLDFLOW_UDB_DIR",
        r"C:\Program Files\Autodesk\Moldflow Insight 2010\data\udb",
    )
)
MOLDFLOW_MATERIALS_DB = Path(
    os.environ.get(
        "MOLDFLOW_MATERIALS_DB",
        str(ROOT.parent / "moldflow_materials.db"),
    )
)

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
def moldflow_list_analysis_sequences() -> str:
    """Catalog Synergy Analysis Sequence targets and MF2010 COM support status.

    Read-only metadata. Does not change StudyDoc.AnalysisSequence.
    Canonical: docs/knowledge/moldflow_analysis_sequence_openfoam_roadmap_20260720.md
    """
    return json.dumps(
        {
            "ok": True,
            "bridge_version": BRIDGE_VERSION,
            "ui_path": "Analysis -> Set Analysis Sequence",
            "com_read": "StudyDoc.AnalysisSequence",
            "com_set": "StudyDoc.AnalysisSequence = <com_string> (accepted set only)",
            "com_accepted_strings": list(MOLDFLOW_COM_ACCEPTED_SEQUENCES),
            "fill_pack_com_alias": "Flow",
            "fill_launcher_proven": "runstudy.exe via moldflow_start_analysis",
            "canonical_doc": "docs/knowledge/moldflow_analysis_sequence_openfoam_roadmap_20260720.md",
            "sequences": list(ANALYSIS_SEQUENCE_CATALOG),
            "staged_order": [
                "fill",
                "fill_pack",
                "fast_fill",
                "cool",
                "fill_pack_warp",
                "cool_fill_pack_warp",
            ],
            "analysis_started": False,
        },
        ensure_ascii=False,
        indent=2,
    )


@mcp.tool()
def moldflow_set_analysis_sequence(
    sequence: str,
    expected_study_name: str = "",
    save: bool = True,
    timeout_sec: int = 90,
) -> str:
    """Set StudyDoc.AnalysisSequence on the active study (SaveAs copies preferred).

    Only MF2010 Midplane COM-accepted strings are allowed:
    Fill, Fast Fill, Flow, Cool.
    Use sequence='Flow' for UI Fill+Pack. Literal 'Fill+Pack' is rejected by COM.
    """
    if not _write_operations_enabled():
        return _write_operation_blocked()
    wanted = str(sequence or "").strip()
    if wanted not in MOLDFLOW_COM_ACCEPTED_SEQUENCES:
        return json.dumps(
            {
                "ok": False,
                "error": "sequence not in COM-accepted set for MF2010 Midplane",
                "requested": wanted,
                "accepted": list(MOLDFLOW_COM_ACCEPTED_SEQUENCES),
                "hint": "UI Fill+Pack -> COM Flow; Warp/combo strings were rejected in probe",
                "analysis_started": False,
            },
            ensure_ascii=False,
            indent=2,
        )
    expected = str(expected_study_name or "").strip()
    expected_canonical = re.sub(r"[^a-z0-9]", "", re.sub(r"(?i)\.sdy$", "", expected).lower())
    seq_lit = wanted.replace('"', "")
    expect_check = ""
    if expected_canonical:
        expect_check = f'''
If CanonicalName(CStr(StudyDoc.StudyName)) <> "{expected_canonical}" Then
    WScript.Echo "ERROR=ACTIVE_STUDY_MISMATCH:expected={expected}:actual=" & CStr(StudyDoc.StudyName)
    WScript.Quit 4
End If
'''
    save_block = ""
    if save:
        save_block = '''
Err.Clear
SaveOK = StudyDoc.Save()
WScript.Echo "SAVE_OK=" & CStr(SaveOK)
WScript.Echo "SAVE_ERR=" & CStr(Err.Number) & ":" & Err.Description
If Not SaveOK Or Err.Number <> 0 Then WScript.Quit 6
'''
    vbs = f'''Option Explicit
Dim Synergy, StudyDoc, SeqBefore, SeqAfter, SaveOK

Function CanonicalName(Value)
    Dim Regex
    Set Regex = New RegExp
    Regex.Global = True
    Regex.IgnoreCase = True
    Regex.Pattern = "[^a-z0-9]"
    CanonicalName = LCase(Regex.Replace(Replace(CStr(Value), ".sdy", ""), ""))
End Function

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
WScript.Echo "ACTIVE_STUDY=" & CStr(StudyDoc.StudyName)
{expect_check}
Err.Clear
SeqBefore = CStr(StudyDoc.AnalysisSequence)
WScript.Echo "SEQ_BEFORE=" & SeqBefore
Err.Clear
StudyDoc.AnalysisSequence = "{seq_lit}"
WScript.Echo "SET_ERR=" & CStr(Err.Number) & ":" & Err.Description
Err.Clear
SeqAfter = CStr(StudyDoc.AnalysisSequence)
WScript.Echo "SEQ_AFTER=" & SeqAfter
If SeqAfter <> "{seq_lit}" Then
    WScript.Echo "ERROR=SEQ_NOT_ACCEPTED:requested={seq_lit}:readback=" & SeqAfter
    WScript.Quit 5
End If
{save_block}
WScript.Echo "SET_OK=true"
WScript.Echo "ANALYSIS_STARTED=false"
'''
    result = _run_vbs_code(
        vbs,
        timeout_sec=max(30, min(int(timeout_sec), 180)),
        bitness=32,
    )
    stdout = str(result.get("stdout") or "")
    parsed: dict[str, Any] = {}
    for line in stdout.splitlines():
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        parsed[key.strip().lower()] = value.strip()
    result["operation"] = parsed
    result["requested_sequence"] = wanted
    result["analysis_started"] = False
    if parsed.get("set_ok") == "true" and parsed.get("seq_after") == wanted:
        result["ok"] = True
    else:
        result["ok"] = False
        result.setdefault("error", parsed.get("error") or "sequence set failed")
    return json.dumps(result, ensure_ascii=False, indent=2)


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
Dim GateNodeIDs(), GateCount, GateType, GateNodeID, I, Found, MeshStatusValue

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
MeshStatusValue = CStr(StudyDoc.MeshStatus())
WScript.Echo "MESH_STATUS=" & MeshStatusValue
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
If MeshStatusValue = "Running" Or MeshStatusValue = "Pending" Then
    WScript.Echo "GATE_INSPECTION_SUPPORTED=false"
    WScript.Echo "GATE_INSPECTION_SKIPPED=mesh_in_progress"
    WScript.Echo "GATE_COUNT=0"
Else
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
End If
'''
    result = _run_vbs_code(
        vbs,
        timeout_sec=max(10, min(int(timeout_sec), 180)),
        bitness=64,
    )
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
def moldflow_open_study_by_name(study_name: str, timeout_sec: int = 60) -> str:
    """Open an existing study by exact display name without modifying it."""
    if not _write_operations_enabled():
        return _write_operation_blocked()
    target = str(study_name or "").strip()
    if not target or any(char in target for char in ('"', "\r", "\n")):
        return json.dumps({"ok": False, "error": "study_name is invalid"})
    target_base = re.sub(r"(?i)\.sdy$", "", target)
    target_canonical = re.sub(r"[^a-z0-9]", "", target_base.lower())
    vbs = f'''Option Explicit
Dim Synergy, Project, StudyDoc, Name, DisplayName, OpenOK

Function CanonicalName(Value)
    Dim Regex
    Set Regex = New RegExp
    Regex.Global = True
    Regex.IgnoreCase = True
    Regex.Pattern = "[^a-z0-9]"
    CanonicalName = LCase(Regex.Replace(Replace(CStr(Value), ".sdy", ""), ""))
End Function

On Error Resume Next
Err.Clear
Set Synergy = CreateObject("synergy.Synergy")
If Err.Number <> 0 Then WScript.Echo "ERROR=CREATEOBJECT_FAILED:" & Err.Number & ":" & Err.Description: WScript.Quit 2
Set Project = Synergy.Project()
If Project Is Nothing Then WScript.Echo "ERROR=NO_PROJECT": WScript.Quit 3

DisplayName = ""
Name = Project.GetFirstStudyName()
Do While Name <> ""
    If CanonicalName(Name) = "{target_canonical}" Then DisplayName = CStr(Name)
    Name = Project.GetNextStudyName(Name)
Loop
If DisplayName = "" Then WScript.Echo "ERROR=STUDY_NOT_FOUND:{target}": WScript.Quit 4

Err.Clear
OpenOK = Project.OpenItemByName(DisplayName, "Study")
WScript.Echo "OPEN_OK=" & CStr(OpenOK)
WScript.Echo "OPEN_ERROR=" & CStr(Err.Number) & ":" & Err.Description
If Not OpenOK Or Err.Number <> 0 Then WScript.Quit 5
Set StudyDoc = Synergy.StudyDoc()
If StudyDoc Is Nothing Then WScript.Echo "ERROR=NO_ACTIVE_STUDY_AFTER_OPEN": WScript.Quit 6
WScript.Echo "ACTIVE_STUDY=" & CStr(StudyDoc.StudyName)
If CanonicalName(StudyDoc.StudyName) <> "{target_canonical}" Then WScript.Echo "ERROR=ACTIVE_STUDY_MISMATCH": WScript.Quit 7
WScript.Echo "STUDY_MODIFIED=false"
WScript.Echo "ANALYSIS_STARTED=false"
'''
    result = _run_vbs_code(vbs, timeout_sec=max(30, min(int(timeout_sec), 120)), bitness=64)
    result["study_modified"] = False
    result["analysis_started"] = False
    return json.dumps(result, ensure_ascii=False, indent=2)


@mcp.tool()
def moldflow_save_as_active_study_copy(
    expected_study_name: str,
    new_study_name: str,
    timeout_sec: int = 120,
) -> str:
    """Save the expected active study under a new name without starting analysis."""
    if not _write_operations_enabled():
        return _write_operation_blocked()
    expected = str(expected_study_name or "").strip()
    target = str(new_study_name or "").strip()
    if (
        not expected
        or not target
        or any(char in expected + target for char in ('"', "\r", "\n"))
    ):
        return json.dumps(
            {"ok": False, "error": "study name is invalid"},
            ensure_ascii=False,
            indent=2,
        )
    expected_base = re.sub(r"(?i)\.sdy$", "", expected)
    target_base = re.sub(r"(?i)\.sdy$", "", target)
    expected_canonical = re.sub(r"[^a-z0-9]", "", expected_base.lower())
    target_canonical = re.sub(r"[^a-z0-9]", "", target_base.lower())
    if expected_canonical == target_canonical:
        return json.dumps(
            {"ok": False, "error": "new_study_name must differ from active study"},
            ensure_ascii=False,
            indent=2,
        )
    vbs = f'''Option Explicit
Dim Synergy, StudyDoc, SaveOK, ActiveName

Function CanonicalName(Value)
    Dim Regex
    Set Regex = New RegExp
    Regex.Global = True
    Regex.IgnoreCase = True
    Regex.Pattern = "[^a-z0-9]"
    CanonicalName = LCase(Regex.Replace(Replace(CStr(Value), ".sdy", ""), ""))
End Function

On Error Resume Next
Err.Clear
Set Synergy = CreateObject("synergy.Synergy")
If Err.Number <> 0 Then
    WScript.Echo "ERROR=SYNERGY_ATTACH_FAILED:" & Err.Number & ":" & Err.Description
    WScript.Quit 2
End If

Set StudyDoc = Synergy.StudyDoc()
If StudyDoc Is Nothing Then
    WScript.Echo "ERROR=NO_ACTIVE_STUDY"
    WScript.Quit 3
End If
ActiveName = CStr(StudyDoc.StudyName)
WScript.Echo "ORIGINAL_STUDY=" & ActiveName
If CanonicalName(ActiveName) <> "{expected_canonical}" Then
    WScript.Echo "ERROR=ACTIVE_STUDY_MISMATCH:expected={expected}:actual=" & ActiveName
    WScript.Quit 4
End If

Err.Clear
SaveOK = StudyDoc.SaveAs("{target_base}")
WScript.Echo "SAVE_AS_OK=" & CStr(SaveOK)
WScript.Echo "SAVE_AS_ERROR=" & CStr(Err.Number) & ":" & Err.Description
If Not SaveOK Or Err.Number <> 0 Then WScript.Quit 5

Set StudyDoc = Synergy.StudyDoc()
If StudyDoc Is Nothing Then
    WScript.Echo "ERROR=NO_ACTIVE_STUDY_AFTER_SAVE_AS"
    WScript.Quit 6
End If
ActiveName = CStr(StudyDoc.StudyName)
WScript.Echo "ACTIVE_AFTER_SAVE_AS=" & ActiveName
If CanonicalName(ActiveName) <> "{target_canonical}" Then
    WScript.Echo "ERROR=SAVE_AS_NAME_MISMATCH:expected={target_base}:actual=" & ActiveName
    WScript.Quit 7
End If
WScript.Echo "COPY_CREATED=true"
WScript.Echo "ANALYSIS_STARTED=false"
'''
    result = _run_vbs_code(
        vbs,
        timeout_sec=max(30, min(int(timeout_sec), 300)),
        bitness=64,
    )
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
Dim DuplicateOK, OpenOK, RemovedCount, SaveOK, OriginalName, SourceName
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
SourceName = ""
Name = Project.GetFirstStudyName()
Do While Name <> ""
    BeforeNames.Add LCase(CStr(Name)), True
    If CanonicalName(Name) = "{expected_canonical}" Then SourceName = CStr(Name)
    Name = Project.GetNextStudyName(Name)
Loop
WScript.Echo "SOURCE_DISPLAY_NAME=" & SourceName
If SourceName = "" Then
    WScript.Echo "ERROR=SOURCE_DISPLAY_NAME_NOT_FOUND"
    WScript.Quit 5
End If

Err.Clear
DuplicateOK = Project.DuplicateStudyByName2(SourceName, True)
WScript.Echo "DUPLICATE_OK=" & CStr(DuplicateOK)
WScript.Echo "DUPLICATE_ERROR=" & CStr(Err.Number) & ":" & Err.Description
If Not DuplicateOK Or Err.Number <> 0 Then WScript.Quit 6

NewName = ""
Name = Project.GetFirstStudyName()
Do While Name <> ""
    If Not BeforeNames.Exists(LCase(CStr(Name))) Then NewName = CStr(Name)
    Name = Project.GetNextStudyName(Name)
Loop
If NewName = "" Then
    WScript.Echo "ERROR=DUPLICATE_NAME_NOT_FOUND"
    WScript.Quit 7
End If
WScript.Echo "COPY_STUDY=" & NewName

Err.Clear
OpenOK = Project.OpenItemByName(NewName, "Study")
WScript.Echo "COPY_OPEN_OK=" & CStr(OpenOK)
WScript.Echo "COPY_OPEN_ERROR=" & CStr(Err.Number) & ":" & Err.Description
If Not OpenOK Or Err.Number <> 0 Then WScript.Quit 8

Set StudyDoc = Synergy.StudyDoc()
WScript.Echo "ACTIVE_AFTER_OPEN=" & CStr(StudyDoc.StudyName)
If CanonicalName(CStr(StudyDoc.StudyName)) <> CanonicalName(NewName) Then
    WScript.Echo "ERROR=COPY_NOT_ACTIVE"
    WScript.Quit 9
End If
End If

Set MeshEditor = Synergy.MeshEditor()
Err.Clear
RemovedCount = MeshEditor.AutoFix()
WScript.Echo "AUTOFIX_REMOVED=" & CStr(RemovedCount)
WScript.Echo "AUTOFIX_ERROR=" & CStr(Err.Number) & ":" & Err.Description
If Err.Number <> 0 Then WScript.Quit 10

Err.Clear
SaveOK = StudyDoc.Save()
WScript.Echo "COPY_SAVE_OK=" & CStr(SaveOK)
WScript.Echo "COPY_SAVE_ERROR=" & CStr(Err.Number) & ":" & Err.Description
If Not SaveOK Or Err.Number <> 0 Then WScript.Quit 11

WScript.Echo "TARGET_COPY_MODIFIED=true"
WScript.Echo "ANALYSIS_STARTED=false"
'''
    result = _run_vbs_code(
        vbs,
        timeout_sec=max(30, min(int(timeout_sec), 300)),
        bitness=64,
    )
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
def moldflow_find_gate_candidate_active_study_copy(
    expected_study_name: str,
    use_bbox_center: bool = True,
    target_x_mm: float = 0.0,
    target_y_mm: float = 0.0,
    target_z_mm: float = 0.0,
    timeout_sec: int = 120,
) -> str:
    """Find the mesh node nearest a target point without modifying the study."""
    expected = str(expected_study_name or "").strip()
    if not expected or any(char in expected for char in ('"', "\r", "\n")):
        return json.dumps({"ok": False, "error": "expected_study_name is invalid"})
    expected_base = re.sub(r"(?i)\.sdy$", "", expected)
    expected_canonical = re.sub(r"[^a-z0-9]", "", expected_base.lower())
    bbox_flag = "True" if use_bbox_center else "False"
    try:
        target_x = float(target_x_mm)
        target_y = float(target_y_mm)
        target_z = float(target_z_mm)
    except (TypeError, ValueError):
        return json.dumps({"ok": False, "error": "target coordinates must be numeric"})
    vbs = f'''Option Explicit
Dim Synergy, StudyDoc, Ent, Coord, NodeID, BestNodeID, NodeCount
Dim MinX, MinY, MinZ, MaxX, MaxY, MaxZ, TX, TY, TZ, DX, DY, DZ, D2, BestD2
Dim FirstNode, UseBBoxCenter, Attempt

Function CanonicalName(Value)
    Dim Regex
    Set Regex = New RegExp
    Regex.Global = True
    Regex.IgnoreCase = True
    Regex.Pattern = "[^a-z0-9]"
    CanonicalName = LCase(Regex.Replace(Replace(CStr(Value), ".sdy", ""), ""))
End Function

On Error Resume Next
Err.Clear
Set Synergy = CreateObject("synergy.Synergy")
If Err.Number <> 0 Then WScript.Echo "ERROR=CREATEOBJECT_FAILED:" & Err.Number & ":" & Err.Description: WScript.Quit 2
Set StudyDoc = Synergy.StudyDoc()
If StudyDoc Is Nothing Then WScript.Echo "ERROR=NO_ACTIVE_STUDY": WScript.Quit 3
WScript.Echo "ACTIVE_STUDY=" & CStr(StudyDoc.StudyName)
If CanonicalName(StudyDoc.StudyName) <> "{expected_canonical}" Then
    WScript.Echo "ERROR=ACTIVE_STUDY_MISMATCH:expected={expected}:actual=" & CStr(StudyDoc.StudyName)
    WScript.Quit 4
End If
If CStr(StudyDoc.MeshStatus()) <> "Completed" Then WScript.Echo "ERROR=MESH_NOT_COMPLETED": WScript.Quit 5

FirstNode = True
NodeCount = 0
Set Ent = StudyDoc.GetFirstNode()
Do While Not Ent Is Nothing
    Set Coord = StudyDoc.GetNodeCoord(Ent)
    If Not Coord Is Nothing Then
        If FirstNode Then
            MinX = Coord.X: MaxX = Coord.X
            MinY = Coord.Y: MaxY = Coord.Y
            MinZ = Coord.Z: MaxZ = Coord.Z
            FirstNode = False
        Else
            If Coord.X < MinX Then MinX = Coord.X
            If Coord.X > MaxX Then MaxX = Coord.X
            If Coord.Y < MinY Then MinY = Coord.Y
            If Coord.Y > MaxY Then MaxY = Coord.Y
            If Coord.Z < MinZ Then MinZ = Coord.Z
            If Coord.Z > MaxZ Then MaxZ = Coord.Z
        End If
        NodeCount = NodeCount + 1
    End If
    Set Ent = StudyDoc.GetNextNode(Ent)
Loop
If NodeCount = 0 Then WScript.Echo "ERROR=EMPTY_MESH": WScript.Quit 6

UseBBoxCenter = {bbox_flag}
If UseBBoxCenter Then
    TX = (MinX + MaxX) / 2
    TY = (MinY + MaxY) / 2
    TZ = (MinZ + MaxZ) / 2
Else
    TX = {target_x:.15g}
    TY = {target_y:.15g}
    TZ = {target_z:.15g}
End If

BestNodeID = 0
Set Ent = StudyDoc.GetFirstNode()
Do While Not Ent Is Nothing
    Set Coord = StudyDoc.GetNodeCoord(Ent)
    If Not Coord Is Nothing Then
        DX = Coord.X - TX: DY = Coord.Y - TY: DZ = Coord.Z - TZ
        D2 = DX * DX + DY * DY + DZ * DZ
        If BestNodeID = 0 Or D2 < BestD2 Then
            BestD2 = D2
            BestNodeID = StudyDoc.GetEntityID(Ent)
            NodeID = BestNodeID
        End If
    End If
    Set Ent = StudyDoc.GetNextNode(Ent)
Loop

Set Ent = StudyDoc.GetFirstNode()
Do While Not Ent Is Nothing
    If CLng(StudyDoc.GetEntityID(Ent)) = CLng(BestNodeID) Then
        Set Coord = StudyDoc.GetNodeCoord(Ent)
        Exit Do
    End If
    Set Ent = StudyDoc.GetNextNode(Ent)
Loop
WScript.Echo "READ_ONLY=true"
WScript.Echo "NODE_COUNT=" & CStr(NodeCount)
WScript.Echo "BBOX_MIN=" & CStr(MinX) & "," & CStr(MinY) & "," & CStr(MinZ)
WScript.Echo "BBOX_MAX=" & CStr(MaxX) & "," & CStr(MaxY) & "," & CStr(MaxZ)
WScript.Echo "TARGET=" & CStr(TX) & "," & CStr(TY) & "," & CStr(TZ)
WScript.Echo "CANDIDATE_NODE_ID=" & CStr(BestNodeID)
WScript.Echo "CANDIDATE_COORD=" & CStr(Coord.X) & "," & CStr(Coord.Y) & "," & CStr(Coord.Z)
WScript.Echo "DISTANCE_SQUARED=" & CStr(BestD2)
WScript.Echo "ANALYSIS_STARTED=false"
'''
    result = _run_vbs_code(
        vbs,
        timeout_sec=max(30, min(int(timeout_sec), 180)),
        bitness=64,
    )
    parsed: dict[str, Any] = {}
    for line in str(result.get("stdout") or "").splitlines():
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        parsed[key.strip().lower()] = value.strip()
    result["candidate"] = parsed
    result["read_only"] = True
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
Err.Clear
Set Synergy = CreateObject("synergy.Synergy")
If Err.Number <> 0 Then WScript.Echo "ERROR=CREATEOBJECT_FAILED:" & Err.Number & ":" & Err.Description: WScript.Quit 2
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
SaveOK = StudyDoc.Save()
WScript.Echo "PRE_MESH_SAVE_OK=" & CStr(SaveOK)
WScript.Echo "PRE_MESH_SAVE_ERROR=" & CStr(Err.Number) & ":" & Err.Description
If Not SaveOK Or Err.Number <> 0 Then WScript.Quit 7

Err.Clear
StudyDoc.MeshNow False
WScript.Echo "MESH_NOW_ERROR=" & CStr(Err.Number) & ":" & Err.Description
If Err.Number <> 0 Then WScript.Quit 8
WScript.Echo "MESH_STATUS=" & CStr(StudyDoc.MeshStatus())
If CStr(StudyDoc.MeshStatus()) = "Running" Or CStr(StudyDoc.MeshStatus()) = "Pending" Then
    WScript.Echo "MESH_STARTED=true"
    WScript.Echo "CHECKPOINT=mesh_launched_from_saved_study"
    WScript.Echo "ANALYSIS_STARTED=false"
    WScript.Quit 0
End If

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
WScript.Echo "NODE_COUNT=" & CStr(NodeCount)
WScript.Echo "TRI_COUNT=" & CStr(TriCount)
If NodeCount = 0 Or TriCount = 0 Then WScript.Echo "ERROR=EMPTY_MESH": WScript.Quit 9
SaveOK = StudyDoc.Save()
WScript.Echo "SAVE_OK=" & CStr(SaveOK)
If Not SaveOK Then WScript.Quit 10
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
    timeout_sec: int = 180,
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
Dim Synergy, StudyDoc, Node, Ent, Found, NormalVector, BoundaryConditions, Inject, SaveOK, Attempt

Function CanonicalName(Value)
    Dim Regex
    Set Regex = New RegExp
    Regex.Global = True
    Regex.IgnoreCase = True
    Regex.Pattern = "[^a-z0-9]"
    CanonicalName = LCase(Regex.Replace(Replace(CStr(Value), ".sdy", ""), ""))
End Function

On Error Resume Next
Err.Clear
Set Synergy = CreateObject("synergy.Synergy")
If Err.Number <> 0 Then WScript.Echo "ERROR=CREATEOBJECT_FAILED:" & Err.Number & ":" & Err.Description: WScript.Quit 2
Set StudyDoc = Synergy.StudyDoc()
If StudyDoc Is Nothing Then WScript.Echo "ERROR=NO_ACTIVE_STUDY": WScript.Quit 3
WScript.Echo "ACTIVE_STUDY=" & CStr(StudyDoc.StudyName)
If CanonicalName(StudyDoc.StudyName) <> "{expected_canonical}" Then
    WScript.Echo "ERROR=ACTIVE_STUDY_MISMATCH:expected={expected}:actual=" & CStr(StudyDoc.StudyName)
    WScript.Quit 4
End If
If CStr(StudyDoc.MeshStatus()) = "Failed" Then WScript.Echo "ERROR=MESH_NOT_READY": WScript.Quit 5

Found = False
Set Ent = StudyDoc.GetFirstNode()
Do While Not Ent Is Nothing And Not Found
    If CLng(StudyDoc.GetEntityID(Ent)) = CLng({node_id}) Then
        Set Node = Ent
        Found = True
    Else
        Set Ent = StudyDoc.GetNextNode(Ent)
    End If
Loop
If Not Found Then WScript.Echo "ERROR=NODE_NOT_FOUND:N{node_id}": WScript.Quit 6
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
        timeout_sec=max(30, min(int(timeout_sec), 300)),
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
def moldflow_create_study_checkpoint(
    project_name: str, study_name: str, timeout_sec: int = 120
) -> str:
    """Create and save an empty scratch study before CAD import or meshing."""
    if not _write_operations_enabled():
        return _write_operation_blocked()
    project = str(project_name or "").strip()
    study = re.sub(r"(?i)\.sdy$", "", str(study_name or "").strip())
    if (not project or not study or
            any(char in project + study for char in ('"', "\r", "\n", "\\", "/"))):
        return json.dumps({"ok": False, "error": "project_name or study_name is invalid"})
    work_dir = DEFAULT_WORK_ROOT / project
    work_dir.mkdir(parents=True, exist_ok=True)
    vbs_work_dir = str(work_dir).replace("\\", "\\\\")
    vbs = f'''Option Explicit
Dim Synergy, Project, StudyDoc, SaveOK
On Error Resume Next
Set Synergy = CreateObject("synergy.Synergy")
If Err.Number <> 0 Then WScript.Echo "ERROR=CREATEOBJECT_FAILED:" & Err.Number & ":" & Err.Description: WScript.Quit 2
Err.Clear
Synergy.NewProject "{project}", "{vbs_work_dir}"
If Err.Number <> 0 Then WScript.Echo "ERROR=NEW_PROJECT_FAILED:" & Err.Number & ":" & Err.Description: WScript.Quit 3
Set Project = Synergy.Project()
If Project Is Nothing Then WScript.Echo "ERROR=NO_PROJECT": WScript.Quit 4
Err.Clear
Project.NewStudy "{study}"
If Err.Number <> 0 Then WScript.Echo "ERROR=NEW_STUDY_FAILED:" & Err.Number & ":" & Err.Description: WScript.Quit 5
Set StudyDoc = Synergy.StudyDoc()
If StudyDoc Is Nothing Then WScript.Echo "ERROR=NO_ACTIVE_STUDY": WScript.Quit 6
Err.Clear
SaveOK = StudyDoc.Save()
WScript.Echo "SAVE_OK=" & CStr(SaveOK)
WScript.Echo "SAVE_ERROR=" & CStr(Err.Number) & ":" & Err.Description
If Not SaveOK Or Err.Number <> 0 Then WScript.Quit 7
WScript.Echo "ACTIVE_STUDY=" & CStr(StudyDoc.StudyName)
WScript.Echo "CHECKPOINT=study_created_and_saved"
WScript.Echo "ANALYSIS_STARTED=false"
'''
    result = _run_vbs_code(vbs, timeout_sec=max(30, min(int(timeout_sec), 180)), bitness=64)
    result["checkpoint"] = "study_created_and_saved"
    result["project_dir"] = str(work_dir)
    result["analysis_started"] = False
    return json.dumps(result, ensure_ascii=False, indent=2)


@mcp.tool()
def moldflow_import_cad_checkpoint(
    expected_study_name: str,
    cad_path: str,
    mesh_type: str = "Fusion",
    timeout_sec: int = 300,
) -> str:
    """Import CAD into the expected active scratch study and save before meshing."""
    if not _write_operations_enabled():
        return _write_operation_blocked()
    expected = str(expected_study_name or "").strip()
    cad = Path(str(cad_path or "").strip())
    requested_mesh = str(mesh_type or "Fusion").strip()
    if not expected or any(char in expected for char in ('"', "\r", "\n")):
        return json.dumps({"ok": False, "error": "expected_study_name is invalid"})
    if requested_mesh not in {"Fusion", "Midplane", "3D"}:
        return json.dumps({"ok": False, "error": "mesh_type must be Fusion, Midplane, or 3D"})
    if not cad.is_file():
        return json.dumps({"ok": False, "error": f"CAD file not found: {cad}"})
    expected_base = re.sub(r"(?i)\.sdy$", "", expected)
    expected_canonical = re.sub(r"[^a-z0-9]", "", expected_base.lower())
    vbs_cad = str(cad).replace("\\", "\\\\").replace('"', '""')
    vbs = f'''Option Explicit
Dim Synergy, StudyDoc, ImportOpts, ImportOK, SaveOK
Function CanonicalName(Value)
    Dim Regex
    Set Regex = New RegExp
    Regex.Global = True
    Regex.IgnoreCase = True
    Regex.Pattern = "[^a-z0-9]"
    CanonicalName = LCase(Regex.Replace(Replace(CStr(Value), ".sdy", ""), ""))
End Function
On Error Resume Next
Set Synergy = CreateObject("synergy.Synergy")
If Err.Number <> 0 Then WScript.Echo "ERROR=CREATEOBJECT_FAILED:" & Err.Number & ":" & Err.Description: WScript.Quit 2
Set StudyDoc = Synergy.StudyDoc()
If StudyDoc Is Nothing Then WScript.Echo "ERROR=NO_ACTIVE_STUDY": WScript.Quit 3
WScript.Echo "ACTIVE_STUDY=" & CStr(StudyDoc.StudyName)
If CanonicalName(StudyDoc.StudyName) <> "{expected_canonical}" Then WScript.Echo "ERROR=ACTIVE_STUDY_MISMATCH": WScript.Quit 4
Set ImportOpts = Synergy.ImportOptions()
ImportOpts.MeshType = "{requested_mesh}"
ImportOpts.Units = "mm"
ImportOpts.UseMDL = False
Err.Clear
ImportOK = Synergy.ImportFile2("{vbs_cad}", ImportOpts, False, False)
WScript.Echo "IMPORT_OK=" & CStr(ImportOK)
WScript.Echo "IMPORT_ERROR=" & CStr(Err.Number) & ":" & Err.Description
If Not ImportOK Or Err.Number <> 0 Then WScript.Quit 5
Err.Clear
SaveOK = StudyDoc.Save()
WScript.Echo "SAVE_OK=" & CStr(SaveOK)
WScript.Echo "SAVE_ERROR=" & CStr(Err.Number) & ":" & Err.Description
If Not SaveOK Or Err.Number <> 0 Then WScript.Quit 6
WScript.Echo "CHECKPOINT=cad_imported_and_saved"
WScript.Echo "ANALYSIS_STARTED=false"
'''
    result = _run_vbs_code(vbs, timeout_sec=max(30, min(int(timeout_sec), 300)), bitness=64)
    result["checkpoint"] = "cad_imported_and_saved"
    result["cad_path"] = str(cad)
    result["analysis_started"] = False
    return json.dumps(result, ensure_ascii=False, indent=2)


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
ImportOpts.MeshType = "Fusion"
ImportOpts.Units = "mm"
ImportOpts.UseMDL = False
If Not Synergy.ImportFile2("{vbs_cad_path}", ImportOpts, False, False) Then
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
    res = _run_vbs_code(vbs, timeout_sec=300, bitness=64)
    sdy_file = work_dir / f"{study_name}.sdy"
    res["study_path"] = str(sdy_file)
    res["study_exists"] = sdy_file.exists()
    return json.dumps(res, ensure_ascii=False, indent=2)


def _vbs_escape(value: str) -> str:
    """Escape a string for safe embedding inside a VBScript double-quoted literal."""
    return str(value or "").replace('"', '""')


def _load_machine_file_catalog(limit: int = 200) -> dict[str, Any]:
    """Inventory *.30007.udb machine files (file catalog only; NOT a property database)."""
    limit = max(1, min(int(limit), 1000))
    files: list[dict[str, Any]] = []
    source = "none"
    note = (
        "Catalog of machine UDB filenames only. Do not treat as Synergy property DB. "
        "Analysis still uses Synergy built-in System DB / process conditions."
    )

    db_path = MOLDFLOW_MATERIALS_DB
    if db_path.exists():
        try:
            import sqlite3

            con = sqlite3.connect(str(db_path))
            con.row_factory = sqlite3.Row
            try:
                total = con.execute(
                    "SELECT COUNT(*) FROM moldflow_material_files "
                    "WHERE file_name LIKE '%.30007.udb'"
                ).fetchone()[0]
                rows = con.execute(
                    "SELECT file_name, relative_path, source_kind, vendor, version_tag, "
                    "size_bytes, sha256, modified_utc FROM moldflow_material_files "
                    "WHERE file_name LIKE '%.30007.udb' "
                    "ORDER BY vendor, file_name LIMIT ?",
                    (limit,),
                ).fetchall()
                files = [dict(r) for r in rows]
                source = f"sqlite:{db_path}"
                return {
                    "ok": True,
                    "domain_tag": MOLDFLOW_MACHINE_DOMAIN_TAG,
                    "source": source,
                    "total": int(total),
                    "returned": len(files),
                    "machines": files,
                    "note": note,
                }
            finally:
                con.close()
        except Exception as exc:
            source = f"sqlite_error:{exc}"

    udb_dir = MOLDFLOW_INSTALL_UDB
    if udb_dir.is_dir():
        paths = sorted(udb_dir.glob("*.30007.udb"))
        for p in paths[:limit]:
            files.append(
                {
                    "file_name": p.name,
                    "relative_path": str(p),
                    "vendor": p.name.replace(".30007.udb", ""),
                    "version_tag": MOLDFLOW_MACHINE_DOMAIN_TAG,
                    "size_bytes": p.stat().st_size,
                }
            )
        return {
            "ok": True,
            "domain_tag": MOLDFLOW_MACHINE_DOMAIN_TAG,
            "source": f"filesystem:{udb_dir}",
            "total": len(paths),
            "returned": len(files),
            "machines": files,
            "note": note,
            "sqlite_fallback": source,
        }

    return {
        "ok": False,
        "domain_tag": MOLDFLOW_MACHINE_DOMAIN_TAG,
        "source": source,
        "total": 0,
        "returned": 0,
        "machines": [],
        "note": note,
        "error": f"no machine catalog: db={db_path} udb_dir={udb_dir}",
    }


@mcp.tool()
def moldflow_configure_study(
    study_path: str,
    injection_node_id: int,
    material_manufacturer: str = "",
    material_trade_name: str = "",
    material_id: int = 0,
    melt_temp_c: float = 0.0,
    mold_temp_c: float = 0.0,
    fill_time_s: float = 0.0,
    max_injection_pressure_mpa: float = 0.0,
    clamp_force_tonne: float = 0.0,
    skip_gate_if_exists: bool = True,
) -> str:
    """Configure thermoplastic material (domain 21000) + optional process conditions + gate.

    Prefer material_id when known (proven path: id 1007). Otherwise manufacturer+trade_name
    via FieldDescription(1997/1998/1991). Process params are best-effort ProcessSettings
    writes (fail-soft); machine UDB select is not claimed here -- use catalog + probe tools.
    """
    if not _write_operations_enabled():
        return _write_operation_blocked()
    sdy = Path(study_path)
    if not sdy.exists():
        return json.dumps({"ok": False, "error": f"study file not found: {study_path}"})

    mid = int(material_id or 0)
    mfg = _vbs_escape(material_manufacturer)
    trade = _vbs_escape(material_trade_name)
    if mid <= 0 and (not mfg.strip() or not trade.strip()):
        return json.dumps(
            {
                "ok": False,
                "error": "provide material_id > 0 or both material_manufacturer and material_trade_name",
            },
            ensure_ascii=False,
            indent=2,
        )

    project_dir = sdy.parent
    project_file = next(project_dir.glob("*.mpi"), None)
    if not project_file:
        return json.dumps({"ok": False, "error": f"project file (.mpi) not found in: {project_dir}"})

    vbs_project_path = str(project_file).replace("\\", "\\\\")
    vbs_study_name = sdy.stem
    skip_gate = "True" if skip_gate_if_exists else "False"

    # Moldflow 2010 MaterialData has no Manufacturer/TradeName properties.
    # Use FieldDescription tcode IDs: 1997=Manufacturer, 1998=TradeName, 1991=MaterialID.
    # Domain MUST be 21000 (thermoplastic). Domain 20030 is thermoset and yields wrong DB.
    vbs = f"""Option Explicit
Dim Synergy, Project, StudyDoc, BoundaryConditions, SelectList, Node, NormalVector, Inject
Dim Finder, Selector, Mat, PS, found, matId, manufacturer, tradeName, family, wantId, curId
Dim meltC, moldC, fillS, maxP, clampT, skipGate
On Error Resume Next
wantId = {mid}
meltC = {float(melt_temp_c or 0.0)}
moldC = {float(mold_temp_c or 0.0)}
fillS = {float(fill_time_s or 0.0)}
maxP = {float(max_injection_pressure_mpa or 0.0)}
clampT = {float(clamp_force_tonne or 0.0)}
skipGate = {skip_gate}
Set Synergy = CreateObject("synergy.Synergy")
Synergy.OpenProject "{vbs_project_path}"
Set Project = Synergy.Project()
Project.OpenItemByName "{vbs_study_name}", "Study"
Set StudyDoc = Synergy.StudyDoc()

' 1. Material Assignment (thermoplastic System DB domain 21000)
Set Finder = Synergy.MaterialFinder()
Finder.SetDataDomain {MOLDFLOW_THERMOPLASTIC_DOMAIN}, "System"
found = False
manufacturer = ""
tradeName = ""
family = ""
matId = 0

If wantId > 0 Then
    Set Selector = Synergy.MaterialSelector()
    Err.Clear
    Selector.Select "", "System", wantId, 0
    If Err.Number = 0 Then
        matId = wantId
        found = True
        WScript.Echo "Selected material ID: " & matId
        WScript.Echo "Selected by: material_id"
        ' Best-effort bounded label resolve for logs (avoid unbounded COM scan hang)
        Dim scanN
        scanN = 0
        Set Mat = Finder.GetFirstMaterial()
        Do While Not (Mat Is Nothing) And scanN < 400
            scanN = scanN + 1
            Err.Clear
            curId = Mat.ID
            If Err.Number <> 0 Or IsEmpty(curId) Or CStr(curId) = "" Then
                Err.Clear
                curId = Mat.FieldDescription(1991)
            End If
            If CLng(curId) = CLng(wantId) Then
                manufacturer = CStr(Mat.FieldDescription(1997))
                tradeName = CStr(Mat.FieldDescription(1998))
                family = CStr(Mat.FieldDescription(1992))
                Exit Do
            End If
            Set Mat = Finder.GetNextMaterial(Mat)
        Loop
        WScript.Echo "LABEL_SCAN_ROWS=" & CStr(scanN)
        If manufacturer <> "" Then WScript.Echo "Selected manufacturer: " & manufacturer
        If tradeName <> "" Then WScript.Echo "Selected trade_name: " & tradeName
        If family <> "" Then WScript.Echo "Selected family: " & family
    Else
        WScript.Echo "[NG] MaterialSelector failed for id=" & wantId & " err=" & Err.Number & ":" & Err.Description
        WScript.Quit 1
    End If
Else
    Set Mat = Finder.GetFirstMaterial()
    Do While Not (Mat Is Nothing)
        Err.Clear
        manufacturer = CStr(Mat.FieldDescription(1997))
        tradeName = CStr(Mat.FieldDescription(1998))
        If UCase(manufacturer) = UCase("{mfg}") And UCase(tradeName) = UCase("{trade}") Then
            Err.Clear
            matId = Mat.ID
            If Err.Number <> 0 Or IsEmpty(matId) Or CStr(matId) = "" Then
                Err.Clear
                matId = CLng(Mat.FieldDescription(1991))
            End If
            family = CStr(Mat.FieldDescription(1992))
            found = True
            Exit Do
        End If
        Set Mat = Finder.GetNextMaterial(Mat)
    Loop
    If found Then
        Set Selector = Synergy.MaterialSelector()
        Selector.Select "", "System", matId, 0
        WScript.Echo "Selected material ID: " & matId
        WScript.Echo "Selected manufacturer: " & manufacturer
        WScript.Echo "Selected trade_name: " & tradeName
        WScript.Echo "Selected family: " & family
        WScript.Echo "Selected by: manufacturer_trade_name"
    Else
        WScript.Echo "[NG] Material not found: {mfg} / {trade}"
        WScript.Quit 1
    End If
End If

' 2. Optional process conditions (fail-soft; MF2010 COM surface varies by install)
If meltC > 0 Or moldC > 0 Or fillS > 0 Or maxP > 0 Or clampT > 0 Then
    Err.Clear
    Set PS = Synergy.ProcessSettings()
    If PS Is Nothing Or Err.Number <> 0 Then
        WScript.Echo "PROCESS_SETTINGS_WARN=" & CStr(Err.Number) & ":" & Err.Description
    Else
        If meltC > 0 Then
            Err.Clear
            PS.MeltTemperature = meltC
            If Err.Number <> 0 Then Err.Clear: PS.SetDouble "Melt temperature", meltC
            WScript.Echo "PROCESS_MELT_C=" & CStr(meltC) & " err=" & CStr(Err.Number)
        End If
        If moldC > 0 Then
            Err.Clear
            PS.MoldSurfaceTemperature = moldC
            If Err.Number <> 0 Then Err.Clear: PS.SetDouble "Mold surface temperature", moldC
            WScript.Echo "PROCESS_MOLD_C=" & CStr(moldC) & " err=" & CStr(Err.Number)
        End If
        If fillS > 0 Then
            Err.Clear
            PS.InjectionTime = fillS
            If Err.Number <> 0 Then Err.Clear: PS.SetDouble "Injection time", fillS
            WScript.Echo "PROCESS_FILL_S=" & CStr(fillS) & " err=" & CStr(Err.Number)
        End If
        If maxP > 0 Then
            Err.Clear
            PS.MaximumMachineInjectionPressure = maxP
            If Err.Number <> 0 Then Err.Clear: PS.SetDouble "Maximum machine injection pressure", maxP
            WScript.Echo "PROCESS_MAX_P_MPA=" & CStr(maxP) & " err=" & CStr(Err.Number)
        End If
        If clampT > 0 Then
            Err.Clear
            PS.MaximumMachineClampForce = clampT
            If Err.Number <> 0 Then Err.Clear: PS.SetDouble "Maximum machine clamp force", clampT
            WScript.Echo "PROCESS_CLAMP_TONNE=" & CStr(clampT) & " err=" & CStr(Err.Number)
        End If
    End If
End If

' 3. Injection Location (skip-soft when skip_gate_if_exists and node missing)
Set SelectList = StudyDoc.CreateEntityList()
SelectList.Add "N{injection_node_id}"
If SelectList.Size = 0 Then
    WScript.Echo "GATE_NODE_WARN=N{injection_node_id} not found"
    If Not skipGate Then
        WScript.Echo "[NG] Node N{injection_node_id} not found."
        WScript.Quit 1
    End If
Else
    Set Node = SelectList.Entity(0)
    Set NormalVector = Synergy.CreateVector()
    NormalVector.SetXYZ 0, 0, 1
    Set BoundaryConditions = Synergy.BoundaryConditions()
    Err.Clear
    Set Inject = BoundaryConditions.CreateNDBC(Node, NormalVector, 40000, Nothing)
    If (Inject Is Nothing) Or Err.Number <> 0 Then
        WScript.Echo "GATE_CREATE_WARN=" & CStr(Err.Number) & ":" & Err.Description
        If Not skipGate Then
            WScript.Quit 1
        End If
    Else
        WScript.Echo "GATE_NODE_ID={injection_node_id}"
    End If
End If

Err.Clear
StudyDoc.Save
WScript.Echo "SAVE_OK=" & CStr(Err.Number = 0)
If Err.Number = 0 Then
    WScript.Echo "[OK] Study configured."
Else
    WScript.Echo "[NG] Study save failed err=" & Err.Number & ":" & Err.Description
    WScript.Quit 1
End If
"""
    res = _run_vbs_code(vbs, timeout_sec=180, bitness=64)
    res["material_id_requested"] = mid
    res["thermoplastic_domain"] = MOLDFLOW_THERMOPLASTIC_DOMAIN
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
    
    # 1. Export Image via Synergy Viewer COM (64-bit; no OpenProject -- hangs on 2010)
    vbs = f"""Option Explicit
Dim Synergy, Project, Viewer, StudyDoc
On Error Resume Next
Set Synergy = CreateObject("synergy.Synergy")
Set Project = Synergy.Project()
Project.OpenItemByName "{vbs_study_name}", "Study"
Set StudyDoc = Synergy.StudyDoc()
WScript.Echo "ACTIVE_STUDY=" & StudyDoc.StudyName
Set Viewer = Synergy.Viewer()
Err.Clear
Viewer.ShowResult 1540
If Err.Number <> 0 Then
    Err.Clear
    Viewer.ShowResultByName "Fill time"
End If
Err.Clear
Viewer.ExportImage "{vbs_img_path}", "PNG"
If Err.Number <> 0 Then
    WScript.Echo "[NG] ExportImage err=" & Err.Number & " " & Err.Description
    WScript.Quit 1
End If
On Error GoTo 0
WScript.Echo "[OK] Image exported."
"""
    res = _run_vbs_code(vbs, timeout_sec=90, bitness=64)
    
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


def _parse_fill_time_sec_from_log(log_file: Path) -> Optional[float]:
    candidates = [log_file]
    # Moldflow 2010 often writes study~1.out instead of study.log
    stem = log_file.with_suffix("")
    candidates.append(Path(str(stem) + "~1.out"))
    candidates.append(log_file.with_suffix(".out"))
    candidates.append(Path(str(stem) + "~1.fpo"))
    candidates.append(log_file.with_suffix(".fpo"))
    content = ""
    for path in candidates:
        if not path.exists():
            continue
        try:
            content = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        if content.strip():
            break
    if not content:
        return None
    match = re.search(r"3DFLOW_RESULT_FILL_TIME\s*[:=]\s*([\d\.]+)", content, re.IGNORECASE)
    if not match:
        match = re.search(r"Fill time\s+=\s+([\d\.]+)\s+s", content, re.IGNORECASE)
    if not match:
        match = re.search(r"Fill time\s*[:=]\s*([\d\.]+)", content, re.IGNORECASE)
    if not match:
        return None
    try:
        return float(match.group(1))
    except ValueError:
        return None


def _default_fill_stages() -> list[dict[str, Any]]:
    return [
        {"key": "initial", "label_ja": "初期", "fraction": 0.10},
        {"key": "mid", "label_ja": "中期", "fraction": 0.50},
        {"key": "final", "label_ja": "最終", "fraction": 1.00},
    ]


def _parse_fill_stages_json(stages_json: str) -> list[dict[str, Any]]:
    if not str(stages_json or "").strip():
        return _default_fill_stages()
    raw = json.loads(stages_json)
    if not isinstance(raw, list) or not raw:
        raise ValueError("stages_json must be a non-empty JSON list")
    stages: list[dict[str, Any]] = []
    for item in raw:
        if not isinstance(item, dict):
            raise ValueError("each stage must be an object")
        key = str(item.get("key") or "").strip()
        if not key or not re.match(r"^[A-Za-z0-9_\-]{1,32}$", key):
            raise ValueError(f"invalid stage key: {key!r}")
        fraction = float(item.get("fraction"))
        if fraction <= 0 or fraction > 1.0:
            raise ValueError(f"stage {key}: fraction must be in (0, 1]")
        label = str(item.get("label_ja") or key).strip() or key
        stages.append({"key": key, "label_ja": label, "fraction": fraction})
    return stages


def _extract_gif_stage_pngs(
    gif_path: Path,
    stages: list[dict[str, Any]],
    out_dir: Path,
    study_stem: str,
) -> tuple[list[dict[str, Any]], Optional[str]]:
    """Extract progressive Fill frames from Viewer.SaveAnimation GIF."""
    try:
        from PIL import Image  # type: ignore
    except Exception as exc:  # pragma: no cover - runtime dependency
        return [], f"Pillow required to extract Fill animation frames: {exc}"

    if not gif_path.exists() or gif_path.stat().st_size <= 0:
        return [], f"animation gif missing or empty: {gif_path}"

    try:
        im = Image.open(gif_path)
    except Exception as exc:
        return [], f"cannot open animation gif: {exc}"

    n_frames = int(getattr(im, "n_frames", 1) or 1)
    if n_frames < 2:
        return [], f"animation gif has too few frames: {n_frames}"

    results: list[dict[str, Any]] = []
    hashes: list[str] = []
    for stage in stages:
        key = stage["key"]
        fraction = float(stage["fraction"])
        frame_idx = max(0, min(n_frames - 1, int(round(fraction * (n_frames - 1)))))
        img_path = out_dir / f"{study_stem}_fill_{key}.png"
        if img_path.exists():
            try:
                img_path.unlink()
            except OSError:
                pass
        try:
            im.seek(frame_idx)
            frame = im.convert("RGB")
            frame.save(img_path, format="PNG")
        except Exception as exc:
            results.append(
                {
                    "key": key,
                    "label_ja": stage.get("label_ja") or key,
                    "fraction": fraction,
                    "image_path": str(img_path),
                    "image_exists": False,
                    "image_bytes": 0,
                    "method": "save_animation_gif",
                    "ok": False,
                    "frame_idx": frame_idx,
                    "error": f"frame extract failed: {exc}",
                }
            )
            continue
        exists = img_path.exists() and img_path.stat().st_size > 0
        digest = hashlib.sha256(img_path.read_bytes()).hexdigest() if exists else ""
        if digest:
            hashes.append(digest)
        results.append(
            {
                "key": key,
                "label_ja": stage.get("label_ja") or key,
                "fraction": fraction,
                "image_path": str(img_path),
                "image_exists": exists,
                "image_bytes": img_path.stat().st_size if exists else 0,
                "method": "save_animation_gif",
                "ok": exists,
                "frame_idx": frame_idx,
                "gif_n_frames": n_frames,
                "sha256_16": digest[:16] if digest else "",
            }
        )

    if len(hashes) >= 2 and len(set(hashes)) < 2:
        return results, "extracted Fill stage PNGs are identical (animation not progressive)"
    return results, None


@mcp.tool()
def moldflow_export_fill_stages(
    study_path: str,
    output_image_dir: str,
    stages_json: str = "",
    fill_time_sec: float = 0.0,
    include_base64: bool = False,
    max_base64_bytes: int = 1500000,
) -> str:
    """Export Fill-time PNGs at progressive fill fractions (初期/中期/最終).

    Proven Moldflow Insight 2010 path:
    open study by canonical name (no OpenProject), show Fill time plot,
    Viewer.SaveAnimation to GIF, then extract frames at stage fractions.
    ExportImage is unsupported (438); SetMaxValue does not change progressive fill visuals.
    """
    if not _write_operations_enabled():
        return _write_operation_blocked()
    sdy = Path(study_path)
    if not sdy.exists():
        return json.dumps({"ok": False, "error": f"study file not found: {study_path}"})
    project_dir = sdy.parent
    project_file = next(project_dir.glob("*.mpi"), None)
    if not project_file:
        return json.dumps({"ok": False, "error": f"project file (.mpi) not found in: {project_dir}"})
    try:
        stages = _parse_fill_stages_json(stages_json)
    except (ValueError, json.JSONDecodeError, TypeError) as exc:
        return json.dumps({"ok": False, "error": f"invalid stages_json: {exc}"})

    out_dir = Path(output_image_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    log_file = sdy.with_suffix(".log")
    fill_time = float(fill_time_sec or 0.0)
    if fill_time <= 0:
        parsed = _parse_fill_time_sec_from_log(log_file)
        if parsed and parsed > 0:
            fill_time = parsed

    target_canonical = re.sub(r"[^a-z0-9]", "", re.sub(r"(?i)\.sdy$", "", sdy.stem).lower())
    gif_path = out_dir / f"{sdy.stem}_fill_anim.gif"
    if gif_path.exists():
        try:
            gif_path.unlink()
        except OSError:
            pass
    vbs_gif_path = str(gif_path).replace("\\", "\\\\")

    vbs = f"""Option Explicit
Dim Synergy, Project, Viewer, PlotManager, Plot, StudyDoc
Dim Name, DisplayName, FS, Regex, OpenOK, fillMax

Function CanonicalName(Value)
    Set Regex = New RegExp
    Regex.Global = True
    Regex.IgnoreCase = True
    Regex.Pattern = "[^a-z0-9]"
    CanonicalName = LCase(Regex.Replace(Replace(CStr(Value), ".sdy", ""), ""))
End Function

On Error Resume Next
Set FS = CreateObject("Scripting.FileSystemObject")
Set Synergy = CreateObject("synergy.Synergy")
If Err.Number <> 0 Then WScript.Echo "ERROR=CREATEOBJECT_FAILED:" & Err.Number: WScript.Quit 2
Synergy.SetUnits "Metric"
Set Project = Synergy.Project()
If Project Is Nothing Then WScript.Echo "ERROR=NO_PROJECT": WScript.Quit 3

DisplayName = ""
Name = Project.GetFirstStudyName()
Do While Name <> ""
    If CanonicalName(Name) = "{target_canonical}" Then DisplayName = CStr(Name)
    Name = Project.GetNextStudyName(Name)
Loop
If DisplayName = "" Then WScript.Echo "ERROR=STUDY_NOT_FOUND:{sdy.stem}": WScript.Quit 4
Err.Clear
OpenOK = Project.OpenItemByName(DisplayName, "Study")
WScript.Echo "OPEN_OK=" & CStr(OpenOK) & " DISPLAY=" & DisplayName
Set StudyDoc = Synergy.StudyDoc()
If StudyDoc Is Nothing Then WScript.Echo "ERROR=NO_ACTIVE_STUDY": WScript.Quit 5
WScript.Echo "ACTIVE_STUDY=" & StudyDoc.StudyName
If CanonicalName(StudyDoc.StudyName) <> "{target_canonical}" Then
    WScript.Echo "ERROR=ACTIVE_STUDY_MISMATCH": WScript.Quit 6
End If

Set Viewer = Synergy.Viewer()
Set PlotManager = Synergy.PlotManager()
Set Plot = Nothing
If Not PlotManager Is Nothing Then
    Err.Clear
    Set Plot = PlotManager.FindPlotByName2("Fill time", "Fill time")
    If Plot Is Nothing Then
        Err.Clear
        Set Plot = PlotManager.FindPlotByName("Fill time")
    End If
    If Plot Is Nothing Then
        Err.Clear
        Set Plot = PlotManager.CreatePlotByDsID2(1610, 19)
        WScript.Echo "CREATE_1610_19 nothing=" & (Plot Is Nothing) & " err=" & Err.Number
    End If
End If
If Plot Is Nothing Then WScript.Echo "ERROR=NO_FILL_PLOT": WScript.Quit 7
Viewer.ShowPlot Plot
WScript.Sleep 1000
fillMax = Plot.GetMaxValue
WScript.Echo "PLOT_MAX=" & fillMax
WScript.Echo "PLOT_FRAMES=" & Plot.GetNumberOfFrames
If fillMax <= 0 Then WScript.Echo "ERROR=FILL_PLOT_EMPTY": WScript.Quit 8

Err.Clear
Viewer.SaveAnimation "{vbs_gif_path}"
WScript.Echo "SAVE_ANIM_ERR=" & Err.Number
If Err.Number <> 0 Or Not FS.FileExists("{vbs_gif_path}") Then
    WScript.Echo "ERROR=SAVE_ANIMATION_FAILED"
    WScript.Quit 9
End If
WScript.Echo "GIF_OK size=" & FS.GetFile("{vbs_gif_path}").Size
WScript.Echo "[DONE] fill_stages"
"""
    res = _run_vbs_code(vbs, timeout_sec=240, bitness=64)
    stdout = str(res.get("stdout") or "")
    m_max = re.search(r"PLOT_MAX=([\d\.]+)", stdout)
    if m_max:
        try:
            plot_max = float(m_max.group(1))
            if plot_max > 0:
                fill_time = plot_max
        except ValueError:
            pass

    stage_results, extract_err = _extract_gif_stage_pngs(gif_path, stages, out_dir, sdy.stem)
    if extract_err and not stage_results:
        return json.dumps(
            {
                "ok": False,
                "error": extract_err,
                "study_path": str(sdy),
                "gif_path": str(gif_path),
                "gif_exists": gif_path.exists(),
                "vbs_ok": bool(res.get("ok")),
                "vbs_stdout_tail": stdout[-1000:],
                "bridge_version": BRIDGE_VERSION,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
            ensure_ascii=False,
            indent=2,
        )

    vbs_ok_count = 0
    for entry in stage_results:
        if include_base64 and entry.get("ok"):
            size = int(entry.get("image_bytes") or 0)
            if size <= int(max_base64_bytes):
                entry["image_base64"] = base64.b64encode(
                    Path(str(entry["image_path"])).read_bytes()
                ).decode("ascii")
            else:
                entry["image_base64"] = None
                entry["base64_skipped"] = (
                    f"image_bytes={size} > max_base64_bytes={max_base64_bytes}"
                )
        if entry.get("ok"):
            vbs_ok_count += 1
        max_t = fill_time * float(entry.get("fraction") or 0) if fill_time > 0 else 0.0
        entry["max_t"] = max_t

    payload = {
        "ok": vbs_ok_count == len(stages) and not extract_err,
        "study_path": str(sdy),
        "fill_time_sec": fill_time if fill_time > 0 else None,
        "stages_requested": len(stages),
        "stages_ok": vbs_ok_count,
        "stages": stage_results,
        "gif_path": str(gif_path),
        "gif_bytes": gif_path.stat().st_size if gif_path.exists() else 0,
        "method": "save_animation_gif",
        "vbs_ok": bool(res.get("ok")),
        "vbs_stdout_tail": stdout[-1000:],
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "bridge_version": BRIDGE_VERSION,
    }
    if extract_err:
        payload["error"] = extract_err
        payload["ok"] = False
    elif vbs_ok_count == 0:
        payload["error"] = res.get("error") or "all fill-stage PNG exports failed"
        payload["ok"] = False
    elif vbs_ok_count < len(stages):
        payload["error"] = f"only {vbs_ok_count}/{len(stages)} stage PNGs exported"
        payload["ok"] = False
    return json.dumps(payload, ensure_ascii=False, indent=2)


@mcp.tool()
def moldflow_export_plot_animation(
    study_path: str,
    output_image_dir: str,
    plot_candidates_json: str = "",
    label: str = "plot",
) -> str:
    """Export Viewer.SaveAnimation GIF for the first matching result plot.

    Used for Cool / Warp (and other) sequences where ExportImage is unsupported (438).
    plot_candidates_json: JSON list of plot name strings to try via FindPlotByName2/FindPlotByName.
    """
    if not _write_operations_enabled():
        return _write_operation_blocked()
    sdy = Path(study_path)
    if not sdy.exists():
        return json.dumps({"ok": False, "error": f"study file not found: {study_path}"})
    project_dir = sdy.parent
    if not next(project_dir.glob("*.mpi"), None):
        return json.dumps({"ok": False, "error": f"project file (.mpi) not found in: {project_dir}"})

    candidates: list[str] = []
    raw = (plot_candidates_json or "").strip()
    if raw:
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, list):
                candidates = [str(x).strip() for x in parsed if str(x).strip()]
        except (json.JSONDecodeError, TypeError) as exc:
            return json.dumps({"ok": False, "error": f"invalid plot_candidates_json: {exc}"})
    if not candidates:
        candidates = [
            "Fill time",
            "Average temperature, part",
            "Temperature, part",
            "Circuit coolant temperature",
            "Mold temperature",
            "Deflection, all effects",
            "Deflection",
            "Total deflection",
        ]

    out_dir = Path(output_image_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    safe_label = re.sub(r"[^a-zA-Z0-9_-]+", "_", (label or "plot").strip())[:40] or "plot"
    gif_path = out_dir / f"{sdy.stem}_{safe_label}_anim.gif"
    if gif_path.exists():
        try:
            gif_path.unlink()
        except OSError:
            pass

    target_canonical = re.sub(r"[^a-z0-9]", "", re.sub(r"(?i)\.sdy$", "", sdy.stem).lower())
    vbs_gif_path = str(gif_path).replace("\\", "\\\\")
    # Build VBS array of candidates
    vbs_names = ", ".join(f'"{n.replace(chr(34), "")}"' for n in candidates)

    vbs = f"""Option Explicit
Dim Synergy, Project, Viewer, PlotManager, Plot, StudyDoc
Dim Name, DisplayName, FS, Regex, OpenOK, fillMax, cand, i, foundName

Function CanonicalName(Value)
    Set Regex = New RegExp
    Regex.Global = True
    Regex.IgnoreCase = True
    Regex.Pattern = "[^a-z0-9]"
    CanonicalName = LCase(Regex.Replace(Replace(CStr(Value), ".sdy", ""), ""))
End Function

On Error Resume Next
Set FS = CreateObject("Scripting.FileSystemObject")
Set Synergy = CreateObject("synergy.Synergy")
If Err.Number <> 0 Then WScript.Echo "ERROR=CREATEOBJECT_FAILED:" & Err.Number: WScript.Quit 2
Synergy.SetUnits "Metric"
Set Project = Synergy.Project()
If Project Is Nothing Then WScript.Echo "ERROR=NO_PROJECT": WScript.Quit 3

DisplayName = ""
Name = Project.GetFirstStudyName()
Do While Name <> ""
    If CanonicalName(Name) = "{target_canonical}" Then DisplayName = CStr(Name)
    Name = Project.GetNextStudyName(Name)
Loop
If DisplayName = "" Then WScript.Echo "ERROR=STUDY_NOT_FOUND:{sdy.stem}": WScript.Quit 4
Err.Clear
OpenOK = Project.OpenItemByName(DisplayName, "Study")
WScript.Echo "OPEN_OK=" & CStr(OpenOK) & " DISPLAY=" & DisplayName
Set StudyDoc = Synergy.StudyDoc()
If StudyDoc Is Nothing Then WScript.Echo "ERROR=NO_ACTIVE_STUDY": WScript.Quit 5
WScript.Echo "ACTIVE_STUDY=" & StudyDoc.StudyName

Set Viewer = Synergy.Viewer()
Set PlotManager = Synergy.PlotManager()
Set Plot = Nothing
foundName = ""
Dim cands
cands = Array({vbs_names})
For i = 0 To UBound(cands)
    cand = CStr(cands(i))
    Err.Clear
    Set Plot = Nothing
    If Not PlotManager Is Nothing Then
        Set Plot = PlotManager.FindPlotByName2(cand, cand)
        If Plot Is Nothing Then
            Err.Clear
            Set Plot = PlotManager.FindPlotByName(cand)
        End If
    End If
    If Not Plot Is Nothing Then
        foundName = cand
        WScript.Echo "PLOT_FOUND=" & cand
        Exit For
    End If
    WScript.Echo "PLOT_MISS=" & cand & " err=" & Err.Number
Next
If Plot Is Nothing Then WScript.Echo "ERROR=NO_PLOT": WScript.Quit 7
Viewer.ShowPlot Plot
WScript.Sleep 1500
fillMax = Plot.GetMaxValue
WScript.Echo "PLOT_NAME=" & foundName
WScript.Echo "PLOT_MAX=" & fillMax
WScript.Echo "PLOT_FRAMES=" & Plot.GetNumberOfFrames
If fillMax <= 0 And Plot.GetNumberOfFrames <= 1 Then
    WScript.Echo "WARN=PLOT_MAY_BE_EMPTY"
End If

Err.Clear
Viewer.SaveAnimation "{vbs_gif_path}"
WScript.Echo "SAVE_ANIM_ERR=" & Err.Number
If Err.Number <> 0 Or Not FS.FileExists("{vbs_gif_path}") Then
    WScript.Echo "ERROR=SAVE_ANIMATION_FAILED"
    WScript.Quit 9
End If
WScript.Echo "GIF_OK size=" & FS.GetFile("{vbs_gif_path}").Size
WScript.Echo "[DONE] plot_animation"
"""
    res = _run_vbs_code(vbs, timeout_sec=300, bitness=64)
    stdout = str(res.get("stdout") or "")
    m_name = re.search(r"PLOT_NAME=(.+)", stdout)
    plot_used = m_name.group(1).strip() if m_name else ""
    m_frames = re.search(r"PLOT_FRAMES=(\d+)", stdout)
    n_frames = int(m_frames.group(1)) if m_frames else 0
    gif_ok = gif_path.exists() and gif_path.stat().st_size > 0
    payload = {
        "ok": bool(res.get("ok")) and gif_ok and "ERROR=" not in stdout.split("[DONE]")[0],
        "study_path": str(sdy),
        "label": label,
        "plot_used": plot_used,
        "plot_candidates": candidates,
        "gif_path": str(gif_path),
        "gif_bytes": gif_path.stat().st_size if gif_ok else 0,
        "gif_exists": gif_ok,
        "plot_frames": n_frames,
        "method": "save_animation_gif",
        "vbs_ok": bool(res.get("ok")),
        "vbs_stdout_tail": stdout[-1500:],
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "bridge_version": BRIDGE_VERSION,
    }
    if not payload["ok"]:
        payload["error"] = (
            "SaveAnimation failed or plot not found"
            if "ERROR=NO_PLOT" in stdout
            else (res.get("error") or "plot animation export failed")
        )
    return json.dumps(payload, ensure_ascii=False, indent=2)


@mcp.tool()
def moldflow_fetch_file_base64(path: str, max_bytes: int = 1500000) -> str:
    """Read a local result file under the Moldflow work root and return base64."""
    target = Path(path)
    try:
        resolved = target.resolve()
    except OSError as exc:
        return json.dumps({"ok": False, "error": str(exc)})
    work_root = DEFAULT_WORK_ROOT.resolve()
    if work_root not in resolved.parents and resolved != work_root:
        return json.dumps({"ok": False, "error": "path must be under MOLDFLOW_WORK_ROOT"})
    if not resolved.exists() or not resolved.is_file():
        return json.dumps({"ok": False, "error": f"file not found: {path}"})
    size = resolved.stat().st_size
    if size <= 0:
        return json.dumps({"ok": False, "error": "empty file"})
    if size > int(max_bytes):
        return json.dumps(
            {"ok": False, "error": f"file too large: {size} > {max_bytes}", "image_bytes": size}
        )
    data = base64.b64encode(resolved.read_bytes()).decode("ascii")
    return json.dumps(
        {
            "ok": True,
            "path": str(resolved),
            "image_bytes": size,
            "image_base64": data,
        },
        ensure_ascii=False,
        indent=2,
    )


@mcp.tool()
def moldflow_export_materials(output_json_path: str) -> str:
    """Traverse and export thermoplastic materials (domain 21000) to a JSON file."""
    if not _write_operations_enabled():
        return _write_operation_blocked()
    out_path = Path(output_json_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    vbs_out_path = str(out_path).replace("\\", "\\\\")

    # Moldflow 2010: FieldDescription(1997/1998/1991/1992); GetNextMaterial(Mat); domain 21000.
    vbs = f'''Option Explicit
Dim Synergy, Finder, Mat, FS, File, first, manufacturer, tradeName, matId, family
On Error Resume Next
Set Synergy = CreateObject("synergy.Synergy")
Set Finder = Synergy.MaterialFinder()
Finder.SetDataDomain {MOLDFLOW_THERMOPLASTIC_DOMAIN}, "System"

Set FS = CreateObject("Scripting.FileSystemObject")
Set File = FS.CreateTextFile("{vbs_out_path}", True)

File.WriteLine "["
first = True
Set Mat = Finder.GetFirstMaterial()
Do While Not (Mat Is Nothing)
    If Not first Then
        File.WriteLine ","
    End If
    first = False

    Err.Clear
    manufacturer = Replace(CStr(Mat.FieldDescription(1997)), Chr(34), Chr(92) & Chr(34))
    tradeName = Replace(CStr(Mat.FieldDescription(1998)), Chr(34), Chr(92) & Chr(34))
    family = Replace(CStr(Mat.FieldDescription(1992)), Chr(34), Chr(92) & Chr(34))
    Err.Clear
    matId = Mat.ID
    If Err.Number <> 0 Or IsEmpty(matId) Or CStr(matId) = "" Then
        Err.Clear
        matId = Mat.FieldDescription(1991)
    End If

    File.Write "  {{"
    File.Write """id"": " & CStr(matId) & ", "
    File.Write """manufacturer"": """ & manufacturer & """, "
    File.Write """trade_name"": """ & tradeName & """, "
    File.Write """family"": """ & family & """"
    File.Write "}}"

    Set Mat = Finder.GetNextMaterial(Mat)
Loop
File.WriteLine ""
File.WriteLine "]"
File.Close
WScript.Echo "[OK] Materials exported."
WScript.Echo "DOMAIN={MOLDFLOW_THERMOPLASTIC_DOMAIN}"
'''
    res = _run_vbs_code(vbs, timeout_sec=180, bitness=64)
    res["output_path"] = output_json_path
    res["output_exists"] = out_path.exists()
    res["thermoplastic_domain"] = MOLDFLOW_THERMOPLASTIC_DOMAIN
    res["note"] = (
        "Synergy System thermoplastic catalog (domain 21000). "
        "SQLite moldflow_materials.db is a file index only, not a property DB."
    )
    return json.dumps(res, ensure_ascii=False, indent=2)


@mcp.tool()
def moldflow_list_machine_catalog(limit: int = 200) -> str:
    """List machine UDB files (*.30007.udb) from SQLite index or install udb folder.

    File inventory only -- does NOT expose machine properties or claim Synergy selection.
    """
    return json.dumps(_load_machine_file_catalog(limit), ensure_ascii=False, indent=2)


@mcp.tool()
def moldflow_probe_machine_com(timeout_sec: int = 60) -> str:
    """Probe whether Synergy exposes MachineFinder/MachineSelector (domain 30007).

    Read-only COM probe. Does not select a machine or write a study.
    """
    vbs = f'''Option Explicit
Dim Synergy, MF, MS, MatF, Mach, n, manufacturer, tradeName
On Error Resume Next
Set Synergy = CreateObject("synergy.Synergy")
If Synergy Is Nothing Or Err.Number <> 0 Then
  WScript.Echo "ERROR=CREATEOBJECT:" & Err.Number & ":" & Err.Description
  WScript.Quit 2
End If

Err.Clear
Set MF = Synergy.MachineFinder()
WScript.Echo "MachineFinder_ok=" & CStr(Not (MF Is Nothing))
WScript.Echo "MachineFinder_err=" & CStr(Err.Number) & ":" & Err.Description

Err.Clear
Set MS = Synergy.MachineSelector()
WScript.Echo "MachineSelector_ok=" & CStr(Not (MS Is Nothing))
WScript.Echo "MachineSelector_err=" & CStr(Err.Number) & ":" & Err.Description

If Not (MF Is Nothing) Then
  Err.Clear
  MF.SetDataDomain {MOLDFLOW_MACHINE_DOMAIN_TAG}, "System"
  WScript.Echo "MachineFinder_SetDataDomain_{MOLDFLOW_MACHINE_DOMAIN_TAG}_err=" & CStr(Err.Number) & ":" & Err.Description
  Err.Clear
  Set Mach = MF.GetFirstMachine()
  WScript.Echo "GetFirstMachine_ok=" & CStr(Not (Mach Is Nothing))
  WScript.Echo "GetFirstMachine_err=" & CStr(Err.Number) & ":" & Err.Description
  n = 0
  Do While (Not (Mach Is Nothing)) And n < 3
    Err.Clear
    manufacturer = ""
    tradeName = ""
    On Error Resume Next
    manufacturer = CStr(Mach.Manufacturer)
    If Err.Number <> 0 Then Err.Clear: manufacturer = CStr(Mach.FieldDescription(1997))
    Err.Clear
    tradeName = CStr(Mach.TradeName)
    If Err.Number <> 0 Then Err.Clear: tradeName = CStr(Mach.FieldDescription(1998))
    WScript.Echo "SAMPLE_" & CStr(n) & "_mfg=" & manufacturer
    WScript.Echo "SAMPLE_" & CStr(n) & "_trade=" & tradeName
    n = n + 1
    Err.Clear
    Set Mach = MF.GetNextMachine(Mach)
    If Err.Number <> 0 Then
      Err.Clear
      Set Mach = MF.GetNextMachine()
    End If
  Loop
  WScript.Echo "Machine_samples=" & CStr(n)
End If

' Also report if MaterialFinder accepts domain 30007 (diagnostic only)
Err.Clear
Set MatF = Synergy.MaterialFinder()
If Not MatF Is Nothing Then
  Err.Clear
  MatF.SetDataDomain {MOLDFLOW_MACHINE_DOMAIN_TAG}, "System"
  WScript.Echo "MaterialFinder_SetDataDomain_{MOLDFLOW_MACHINE_DOMAIN_TAG}_err=" & CStr(Err.Number) & ":" & Err.Description
End If
WScript.Echo "PROBE_OK=true"
'''
    res = _run_vbs_code(vbs, timeout_sec=max(15, min(int(timeout_sec), 120)), bitness=64)
    res["read_only"] = True
    res["domain_tag"] = MOLDFLOW_MACHINE_DOMAIN_TAG
    stdout = str(res.get("stdout") or "")
    res["machine_finder_present"] = "MachineFinder_ok=True" in stdout or "MachineFinder_ok=true" in stdout
    res["guidance"] = (
        "If MachineFinder is absent, use moldflow_list_machine_catalog for inventory "
        "and moldflow_configure_study process-condition params (clamp/pressure/temps) instead of claiming UDB properties."
    )
    return json.dumps(res, ensure_ascii=False, indent=2)


@mcp.tool()
def moldflow_select_machine(
    study_path: str,
    machine_manufacturer: str = "",
    machine_trade_name: str = "",
    machine_id: int = 0,
) -> str:
    """Attempt MachineSelector assignment when COM supports it (write-gated).

    Fail-closed if MachineFinder/MachineSelector is missing. Prefer process-condition
    params on moldflow_configure_study when this returns com_api_unavailable.
    """
    if not _write_operations_enabled():
        return _write_operation_blocked()
    sdy = Path(study_path)
    if not sdy.exists():
        return json.dumps({"ok": False, "error": f"study file not found: {study_path}"})
    mid = int(machine_id or 0)
    mfg = _vbs_escape(machine_manufacturer)
    trade = _vbs_escape(machine_trade_name)
    if mid <= 0 and not mfg.strip():
        return json.dumps(
            {"ok": False, "error": "provide machine_id > 0 or machine_manufacturer"},
            ensure_ascii=False,
            indent=2,
        )

    project_dir = sdy.parent
    project_file = next(project_dir.glob("*.mpi"), None)
    if not project_file:
        return json.dumps({"ok": False, "error": f"project file (.mpi) not found in: {project_dir}"})
    vbs_project_path = str(project_file).replace("\\", "\\\\")
    vbs_study_name = sdy.stem

    vbs = f'''Option Explicit
Dim Synergy, Project, StudyDoc, MF, MS, Mach, found, curId, manufacturer, tradeName, wantId
On Error Resume Next
wantId = {mid}
Set Synergy = CreateObject("synergy.Synergy")
Synergy.OpenProject "{vbs_project_path}"
Set Project = Synergy.Project()
Project.OpenItemByName "{vbs_study_name}", "Study"
Set StudyDoc = Synergy.StudyDoc()

Err.Clear
Set MF = Synergy.MachineFinder()
Set MS = Synergy.MachineSelector()
If MF Is Nothing Or MS Is Nothing Then
  WScript.Echo "ERROR=com_api_unavailable"
  WScript.Echo "MachineFinder_ok=" & CStr(Not MF Is Nothing)
  WScript.Echo "MachineSelector_ok=" & CStr(Not MS Is Nothing)
  WScript.Quit 3
End If

Err.Clear
MF.SetDataDomain {MOLDFLOW_MACHINE_DOMAIN_TAG}, "System"
found = False
If wantId > 0 Then
  Err.Clear
  MS.Select "", "System", wantId, 0
  If Err.Number = 0 Then
    found = True
    WScript.Echo "Selected machine ID: " & wantId
  Else
    WScript.Echo "ERROR=select_by_id_failed:" & Err.Number & ":" & Err.Description
    WScript.Quit 4
  End If
Else
  Set Mach = MF.GetFirstMachine()
  Do While Not (Mach Is Nothing)
    Err.Clear
    manufacturer = CStr(Mach.Manufacturer)
    If Err.Number <> 0 Then Err.Clear: manufacturer = CStr(Mach.FieldDescription(1997))
    Err.Clear
    tradeName = CStr(Mach.TradeName)
    If Err.Number <> 0 Then Err.Clear: tradeName = CStr(Mach.FieldDescription(1998))
    If UCase(manufacturer) = UCase("{mfg}") Then
      If "{trade}" = "" Or UCase(tradeName) = UCase("{trade}") Then
        Err.Clear
        curId = Mach.ID
        If Err.Number <> 0 Or IsEmpty(curId) Or CStr(curId) = "" Then
          Err.Clear
          curId = Mach.FieldDescription(1991)
        End If
        Err.Clear
        MS.Select "", "System", curId, 0
        If Err.Number = 0 Then
          found = True
          WScript.Echo "Selected machine ID: " & curId
          WScript.Echo "Selected manufacturer: " & manufacturer
          WScript.Echo "Selected trade_name: " & tradeName
          Exit Do
        End If
      End If
    End If
    Err.Clear
    Set Mach = MF.GetNextMachine(Mach)
    If Err.Number <> 0 Then Err.Clear: Set Mach = MF.GetNextMachine()
  Loop
End If

If Not found Then
  WScript.Echo "[NG] Machine not found / select failed"
  WScript.Quit 5
End If
Err.Clear
StudyDoc.Save
WScript.Echo "SAVE_OK=" & CStr(Err.Number = 0)
WScript.Echo "[OK] Machine configured."
'''
    res = _run_vbs_code(vbs, timeout_sec=120, bitness=64)
    stdout = str(res.get("stdout") or "")
    if "com_api_unavailable" in stdout:
        res["ok"] = False
        res["error"] = "com_api_unavailable"
        res["fallback"] = (
            "Use moldflow_list_machine_catalog + moldflow_configure_study process-condition params"
        )
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
