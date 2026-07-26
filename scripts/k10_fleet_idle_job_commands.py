# -*- coding: utf-8 -*-
"""Allow-listed shell jobs for fleet idle dispatch (per node)."""
from __future__ import annotations

K10_HTTP = "http://100.119.18.40:8123"

RED_LAVIE_JOB_COMMANDS: dict[str, str] = {
    "health_snapshot": (
        "hostname & wmic os get Caption,Version /format:list & "
        "wmic cpu get LoadPercentage /value & echo HEALTH_OK"
    ),
    "monitor_local_probe": (
        "curl -fsSL http://127.0.0.1:8111/metrics 2>nul | findstr /C:\"cpu_usage\" /C:\"cpu_temp\" "
        "|| echo METRICS_NA"
    ),
    "document_parse_probe": (
        "if not exist C:\\clawstack_satellite\\data\\work\\document_parse "
        "mkdir C:\\clawstack_satellite\\data\\work\\document_parse & "
        "python --version 2>nul & echo DOC_PARSE_READY"
    ),
    "rag_index_probe": (
        "if not exist C:\\clawstack_satellite\\data\\work\\rag_index "
        "mkdir C:\\clawstack_satellite\\data\\work\\rag_index & echo RAG_INDEX_READY"
    ),
    "qms_iatf_probe": (
        "if not exist C:\\clawstack_satellite\\data\\work\\qms_iatf "
        "mkdir C:\\clawstack_satellite\\data\\work\\qms_iatf & echo QMS_IATF_READY"
    ),
    "web_research_probe": (
        f"curl -fsSL {K10_HTTP}/monitor_agent.py -o NUL 2>nul & echo WEB_RESEARCH_READY"
    ),
    "fleet_self_probe": (
        "curl -fsSL http://127.0.0.1:5682/healthz 2>nul || echo WORKER_NA"
    ),
}

THINKPAD_JOB_COMMANDS: dict[str, str] = {
    "health_snapshot": "hostname; uptime -p 2>/dev/null || uptime; echo HEALTH_OK",
    "monitor_local_probe": (
        "curl -fsSL --max-time 5 http://127.0.0.1:8111/metrics 2>/dev/null | head -c 400 || echo METRICS_NA"
    ),
    "fleet_self_probe": (
        "curl -fsSL --max-time 5 http://127.0.0.1:5683/healthz 2>/dev/null || echo WORKER_NA"
    ),
}

DYNABOOK_SHELL_JOBS: dict[str, str] = {
    "brv_sync_probe": (
        "if exist C:\\dynabook_satellite\\data\\work\\brv mkdir C:\\dynabook_satellite\\data\\work\\brv & "
        "echo BRV_SYNC_PROBE_OK"
    ),
}

LAVIE_I3_JOB_COMMANDS: dict[str, str] = {
    **RED_LAVIE_JOB_COMMANDS,
    "fleet_endpoint_audit": (
        "echo FLEET_ENDPOINT_AUDIT & "
        "curl --max-time 3 -fsS http://100.87.244.46:8111/metrics >nul "
        "&& echo LAVIE_OK || echo LAVIE_OFFLINE & "
        "curl --max-time 3 -fsS http://100.99.145.3:8111/metrics >nul "
        "&& echo RED_LAVIE_OK || echo RED_LAVIE_OFFLINE & "
        "curl --max-time 3 -fsS http://100.98.133.40:8111/metrics >nul "
        "&& echo DYNABOOK_OK || echo DYNABOOK_OFFLINE & "
        "curl --max-time 3 -fsS http://100.66.63.9:8111/metrics >nul "
        "&& echo THINKPAD_OK || echo THINKPAD_OFFLINE & "
        "echo FLEET_ENDPOINT_AUDIT_DONE"
    ),
    "job_history_audit": (
        "powershell -NoProfile -Command "
        "\"$p='C:\\clawstack_satellite\\data\\work\\jobs'; "
        "$d=Get-ChildItem -LiteralPath $p -Directory -ErrorAction SilentlyContinue; "
        "Write-Output ('JOB_DIR_COUNT='+$d.Count); "
        "$d | Sort-Object LastWriteTime -Descending | Select-Object -First 5 "
        "Name,LastWriteTime | Format-Table -HideTableHeaders; "
        "Write-Output 'JOB_HISTORY_AUDIT_OK'\""
    ),
    "workspace_capacity_audit": (
        "echo WORKSPACE_CAPACITY_AUDIT & "
        "wmic logicaldisk where \"DeviceID='C:'\" get FreeSpace,Size /value & "
        "if exist C:\\clawstack_satellite\\data\\work "
        "(echo WORKSPACE_OK) else (echo WORKSPACE_MISSING) & "
        "echo WORKSPACE_CAPACITY_AUDIT_DONE"
    ),
}

NODE_COMMAND_MAP: dict[str, dict[str, str]] = {
    "red_lavie": RED_LAVIE_JOB_COMMANDS,
    "lavie": RED_LAVIE_JOB_COMMANDS,
    "lavie_i3": LAVIE_I3_JOB_COMMANDS,
    "thinkpad": THINKPAD_JOB_COMMANDS,
    "dynabook": DYNABOOK_SHELL_JOBS,
}
