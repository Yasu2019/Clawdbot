# -*- coding: utf-8 -*-
"""DXF2STEP trial quality gate: QC / FMEA preflight + post-mortem (fail-closed, DB-backed).

Persists to:
- data/workspace/thinkpad_dxf2step_quality_analysis.jsonl
- data/workspace/universal_growth.db (dxf2step_trial_analyses, dxf2step_fmea_registry)

Rule-based analysis always runs. LLM enrich optional on failure only (local_fast default).
"""
from __future__ import annotations

import json
import os
import sqlite3
import sys
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

ROOT = Path(__file__).resolve().parents[1]
WORKSPACE = ROOT / "data" / "workspace"
JSONL_PATH = WORKSPACE / "thinkpad_dxf2step_quality_analysis.jsonl"
GROWTH_DB = WORKSPACE / "universal_growth.db"
TROUBLE_HISTORY = WORKSPACE / "memory" / "trouble_history.md"
LESSONS_DB = WORKSPACE / "iatf_generation_lessons.json"
PREFLIGHT_REGISTRY = WORKSPACE / "thinkpad_dxf2step_fmea_registry.json"

JST = timezone(timedelta(hours=9))
LITELLM_URL = os.getenv("LITELLM_URL", "http://localhost:4001")
LITELLM_KEY = os.getenv("LITELLM_MASTER_KEY", "yasu-fresh-token-2026-02-01")
LLM_MODEL = os.getenv("DXF2STEP_QUALITY_LLM_MODEL", "openai/gpt-4o")
LLM_TIMEOUT = int(os.getenv("DXF2STEP_QUALITY_LLM_TIMEOUT_SEC", "20"))

_FAIL_VERDICTS = frozenset({"FAILED", "PARTIAL", "ERROR", "TIMEOUT"})

PREFLIGHT_REQUIRED = (
    "qc_process_chart",
    "fmea",
    "fta_top_event",
    "fta_root_causes",
    "why_why",
    "fishbone",
    "logical_tree",
    "key_risks",
    "recommended_emphasis",
    "doe",
)

POSTMORTEM_REQUIRED = (
    "qc_process_chart",
    "fmea",
    "fta_top_event",
    "fta_root_causes",
    "why_why",
    "fishbone",
    "logical_tree",
    "doe",
    "key_risks",
    "countermeasures",
    "failure_class",
)

_DB_META_KEYS = frozenset(
    {
        "schema",
        "trial_id",
        "sample",
        "thickness_mm",
        "verdict",
        "analysis_source",
        "created_at",
        "llm_mode",
        "llm_enrich_skipped",
        "_validation",
    }
)
_DB_CONTENT_KEYS = frozenset(PREFLIGHT_REQUIRED) | frozenset(POSTMORTEM_REQUIRED)
_MAX_DB_STRING = 32_000


def slim_analysis_for_db(analysis: dict[str, Any], phase: str = "") -> dict[str, Any]:
    """Drop accidental megabyte embeds (e.g. trouble_history) before SQLite/JSONL."""
    if phase == "archive_meta":
        return analysis
    allowed = _DB_META_KEYS | _DB_CONTENT_KEYS
    out: dict[str, Any] = {}
    for key, val in analysis.items():
        if key not in allowed:
            continue
        if isinstance(val, str) and len(val) > _MAX_DB_STRING:
            out[key] = val[:_MAX_DB_STRING] + "...[truncated]"
        else:
            out[key] = val
    return out


class Dxf2StepQualityGateError(Exception):
    """Preflight validation failed -- trial must not start."""


def manifest_required() -> bool:
    return os.getenv("DXF2STEP_MANIFEST_REQUIRED", "1").strip().lower() not in (
        "0",
        "false",
        "no",
    )


def _validate_trial_manifest(archive_dir: Path | None, verdict: str) -> tuple[bool, list[str]]:
    if str(verdict or "").upper() != "SUCCESS":
        return True, []
    if not manifest_required():
        return True, ["manifest_check_skipped"]
    if archive_dir is None:
        return False, ["archive_dir_missing"]
    apps = ROOT / "data" / "workspace" / "apps" / "dxf2step"
    if str(apps) not in sys.path:
        sys.path.insert(0, str(apps))
    try:
        from part_geometry_contract import validate_manifest_file

        mf_path = archive_dir / "part_manifest.json"
        ok, issues, _ = validate_manifest_file(mf_path)
        if not ok:
            return False, [f"part_manifest:{i}" for i in issues]
        return True, []
    except Exception as exc:
        return False, [f"part_manifest_import:{exc}"]


def preflight_required() -> bool:
    return os.getenv("DXF2STEP_QUALITY_PREFLIGHT_REQUIRED", "1").strip().lower() not in (
        "0",
        "false",
        "no",
    )


def llm_mode() -> str:
    legacy = os.getenv("DXF2STEP_QUALITY_LLM", "").strip().lower()
    if legacy in ("0", "false", "no"):
        return "never"
    mode = os.getenv("DXF2STEP_QUALITY_LLM_MODE", "failed").strip().lower()
    return mode if mode in ("always", "never", "failed") else "failed"


def now_iso() -> str:
    return datetime.now(JST).isoformat()


def _past_trouble_excerpt(max_chars: int = 2000) -> str:
    parts: list[str] = []
    if TROUBLE_HISTORY.exists():
        parts.append(TROUBLE_HISTORY.read_text(encoding="utf-8", errors="replace")[:max_chars])
    if LESSONS_DB.exists():
        try:
            data = json.loads(LESSONS_DB.read_text(encoding="utf-8"))
            lessons = data.get("lessons_learned") or []
            if lessons:
                parts.append(json.dumps(lessons[-5:], ensure_ascii=False)[:800])
        except Exception:
            pass
    return "\n".join(parts)[:max_chars] or "(no past trouble file)"


def _ensure_db_schema(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS dxf2step_trial_analyses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            trial_id TEXT NOT NULL,
            phase TEXT NOT NULL,
            sample TEXT,
            thickness_mm REAL,
            verdict TEXT,
            failure_class TEXT,
            analysis_json TEXT NOT NULL,
            validation_ok INTEGER,
            created_at TEXT,
            UNIQUE(trial_id, phase)
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS dxf2step_fmea_registry (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sample TEXT,
            failure_mode TEXT NOT NULL,
            cause TEXT,
            countermeasure TEXT NOT NULL,
            severity INTEGER,
            occurrence INTEGER,
            detection INTEGER,
            source_trial_id TEXT,
            created_at TEXT,
            UNIQUE(sample, failure_mode, countermeasure)
        )
        """
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_dxf2step_trial ON dxf2step_trial_analyses(trial_id)"
    )
    cols = {row[1] for row in conn.execute("PRAGMA table_info(dxf2step_trial_analyses)")}
    if "part_manifest_path" not in cols:
        conn.execute("ALTER TABLE dxf2step_trial_analyses ADD COLUMN part_manifest_path TEXT")


def fetch_past_analyses(*, sample: str | None = None, limit: int = 8) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if GROWTH_DB.exists():
        try:
            conn = sqlite3.connect(str(GROWTH_DB))
            _ensure_db_schema(conn)
            if sample:
                cur = conn.execute(
                    """
                    SELECT trial_id, phase, sample, verdict, failure_class, analysis_json, created_at
                    FROM dxf2step_trial_analyses
                    WHERE phase='postmortem' AND sample=?
                    ORDER BY id DESC LIMIT ?
                    """,
                    (sample, limit),
                )
            else:
                cur = conn.execute(
                    """
                    SELECT trial_id, phase, sample, verdict, failure_class, analysis_json, created_at
                    FROM dxf2step_trial_analyses
                    WHERE phase='postmortem'
                    ORDER BY id DESC LIMIT ?
                    """,
                    (limit,),
                )
            for row in cur.fetchall():
                try:
                    analysis = json.loads(row[5] or "{}")
                except json.JSONDecodeError:
                    analysis = {}
                rows.append(
                    {
                        "trial_id": row[0],
                        "phase": row[1],
                        "sample": row[2],
                        "verdict": row[3],
                        "failure_class": row[4],
                        "analysis": analysis,
                        "created_at": row[6],
                    }
                )
            conn.close()
        except Exception:
            pass

    if JSONL_PATH.exists() and len(rows) < limit:
        try:
            lines = JSONL_PATH.read_text(encoding="utf-8").splitlines()[-limit * 2 :]
            for line in reversed(lines):
                if not line.strip():
                    continue
                rec = json.loads(line)
                if sample and rec.get("sample") != sample:
                    continue
                if rec.get("phase") != "postmortem":
                    continue
                if any(r.get("trial_id") == rec.get("trial_id") for r in rows):
                    continue
                rows.append(rec)
                if len(rows) >= limit:
                    break
        except Exception:
            pass
    return rows[:limit]


def load_fmea_registry() -> dict[str, Any]:
    if PREFLIGHT_REGISTRY.exists():
        try:
            return json.loads(PREFLIGHT_REGISTRY.read_text(encoding="utf-8-sig"))
        except Exception:
            pass
    return {"schema": "clawstack.dxf2step_fmea_registry.v1", "rows": []}


def _merge_registry_rows(fmea_rows: list[dict[str, Any]], sample: str) -> list[dict[str, Any]]:
    reg = load_fmea_registry()
    existing = list(reg.get("rows") or [])
    # 2026-08-08: 入力側(fmea_rows)の重複を排除していなかったため、
    # _base_fmea_rows が過去試行のFMEAを取り込む→次の試行がそれを再度取り込む、
    # という雪だるま式の累積が起きていた。
    # 実測: 1レコードの fmea が 27,368要素(一意はわずか55件/重複率99.80%)まで膨張し、
    # dxf2step_trial_analyses だけで 35.15 GB(最大の1行が746MB)を占有していた。
    merged: list[dict[str, Any]] = []
    seen: set = set()
    for row in fmea_rows:
        key = (row.get("failure_mode"), row.get("countermeasure"))
        if key in seen:
            continue
        seen.add(key)
        merged.append(row)
    for row in existing:
        if sample and row.get("sample") not in (sample, "*", None, ""):
            continue
        key = (row.get("failure_mode"), row.get("countermeasure"))
        if key in seen:
            continue
        merged.append(row)
        seen.add(key)
    return merged


def _classify_failure(trial: dict[str, Any]) -> str:
    verdict = str(trial.get("verdict") or "UNKNOWN").upper()
    build_log = trial.get("build_log") or {}
    if build_log.get("reconstruction_status") == "compound_fallback" or build_log.get("reconstruction_warning"):
        return "multiview_compound_fallback"
    if build_log.get("combined_quality_ok") is False and build_log.get("combined_step"):
        return "combined_geometry_ng"
    if verdict == "SUCCESS":
        return "success"
    layers = build_log.get("layers") or {}
    stderr = str(trial.get("stderr_tail") or "")
    stdout = str(trial.get("stdout_tail") or "")
    if "ValueError" in stderr or "Traceback" in stderr:
        return "worker_script_error"
    if int(trial.get("exit_code") or 0) != 0 and not layers:
        return "freecad_execution_error"
    if not layers and "LWPOLYLINE" in str(trial.get("stdout_tail") or ""):
        return "unsupported_lwpolyline"
    failed_layers = [n for n, v in layers.items() if (v or {}).get("status") != "done"]
    if failed_layers and any(n.lower() in ("profile", "outline") for n in failed_layers):
        return "open_loop_profile"
    if failed_layers and any((layers.get(n) or {}).get("entities", 0) == 0 for n in failed_layers):
        return "tjunction_no_outer_edges"
    if verdict == "PARTIAL":
        return "partial_layer_success"
    if verdict == "FAILED":
        return "all_layers_failed"
    return "unknown"


def _layer_summary(build_log: dict[str, Any]) -> str:
    layers = build_log.get("layers") or {}
    parts = []
    for name, info in layers.items():
        parts.append(f"{name}:{(info or {}).get('status', '?')}")
    return ", ".join(parts) or "no layers"


def _suggest_next_thickness(trial: dict[str, Any], cfg_grid: list[float] | None = None) -> float | None:
    current = float(trial.get("thickness_mm") or 10.0)
    grid = cfg_grid or [5.0, 8.0, 10.0, 12.0, 15.0]
    failure_class = _classify_failure(trial)
    if failure_class == "open_loop_profile":
        return current
    try:
        idx = grid.index(current)
        if idx + 1 < len(grid):
            return float(grid[idx + 1])
        return float(grid[0])
    except ValueError:
        return float(grid[0]) if grid else current


def _base_fmea_rows(sample: str, thickness: float, past: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = [
        {
            "process": "DXF00_lwpolyline",
            "failure_mode": "LWPOLYLINE not expanded",
            "effect": "Zero outer edges; build_log layers empty",
            "cause": "Worker only handled LINE; DXF used closed=false LWPOLYLINE",
            "severity": 9,
            "occurrence": 8,
            "detection": 2,
            "countermeasure": "Expand LWPOLYLINE in resolve_tjunctions; fix_heatsink_dxf_closed.py",
        },
        {
            "process": "DXF01_geometry",
            "failure_mode": "Open profile / non-closed loop",
            "effect": "Layer extrude fails; PARTIAL or FAILED",
            "cause": "DXF drawn as overlapping boxes; T-junction not resolved",
            "severity": 8,
            "occurrence": 7,
            "detection": 3,
            "countermeasure": "Verify outer_edges>0 in build_log; fix DXF or T-junction tol",
        },
        {
            "process": "DXF02_freecad",
            "failure_mode": "FreeCAD extrude/sortEdges fail",
            "effect": "No STEP/FCStd output",
            "cause": "freecad.cmd timeout or invalid wire",
            "severity": 7,
            "occurrence": 4,
            "detection": 2,
            "countermeasure": "Use native FREECAD_CMD; increase DXF2STEP_FREECAD_TIMEOUT_SEC",
        },
        {
            "process": "DXF03_archive",
            "failure_mode": "FCStd not synced to K10",
            "effect": "User cannot edit parametric history locally",
            "cause": "SCP failure or retain_fcstd=false",
            "severity": 6,
            "occurrence": 2,
            "detection": 2,
            "countermeasure": "sync_trial_archive with retain_fcstd=true",
        },
        {
            "process": "DXF04_multiview",
            "failure_mode": "combined.step missing",
            "effect": "Single-layer solid only",
            "cause": "Fewer than 2 successful view layers",
            "severity": 5,
            "occurrence": 6,
            "detection": 3,
            "countermeasure": "Use multi-layer samples (heatsink/enclosure) or fix Profile layer",
        },
    ]
    for past_rec in past:
        analysis = past_rec.get("analysis") or {}
        for row in analysis.get("fmea") or []:
            if isinstance(row, dict) and row.get("countermeasure"):
                if row.get("process") == "DXF99_this_trial":
                    row = dict(row)
                    row["process"] = "DXF99_past"
                    rows.append(row)
    return _merge_registry_rows(rows, sample)


def build_preflight(trial_plan: dict[str, Any]) -> dict[str, Any]:
    sample = str(trial_plan.get("sample") or "unknown")
    thickness = float(trial_plan.get("thickness_mm") or 10.0)
    job_id = str(trial_plan.get("job_id") or "pending")
    past = fetch_past_analyses(sample=sample, limit=5)

    top_event = f"DXF2STEP trial {job_id} ({sample}) fails to produce editable FCStd at {thickness}mm"
    root_causes = [
        "DXF profile not closed after T-junction resolution",
        "FreeCAD native snap path misconfigured on Ubuntu 26.04",
    ]
    if past:
        fc = past[0].get("failure_class")
        if fc:
            root_causes.insert(0, f"Repeat risk: {fc} on sample {sample}")

    fmea = _base_fmea_rows(sample, thickness, past)
    qc_steps = [
        {
            "step": "DXF-QC01",
            "control_point": "ThinkPad resource guard",
            "standard": "CPU/RAM/temp below thresholds",
            "risk": "skip_guard if exceeded",
        },
        {
            "step": "DXF-QC02",
            "control_point": "Quality preflight (this gate)",
            "standard": "QC chart + FMEA validated before worker",
            "risk": "skip_quality_preflight if invalid",
        },
        {
            "step": "DXF-QC03",
            "control_point": "DXF input exists",
            "standard": f"local_dxf readable: {trial_plan.get('local_dxf', '')}",
            "risk": "missing sample file",
        },
        {
            "step": "DXF-QC04",
            "control_point": "FreeCAD worker",
            "standard": "freecad.cmd + ezdxf; layers produce STEP+FCStd",
            "risk": "open loop / extrude fail",
        },
        {
            "step": "DXF-QC05",
            "control_point": "Archive sync",
            "standard": "*.FCStd retained on K10 for user edit",
            "risk": "SCP or retain_fcstd disabled",
        },
    ]

    why_row = {
        "why1": f"Need editable 3D from {sample} DXF",
        "why2": "Closed loops required for Part.Face extrude",
        "why3": "Past failures stored in universal_growth.db not AI memory only",
        "why4": f"Thickness {thickness}mm affects volume KPI",
        "why5": root_causes[0],
        "action": "Run worker only after this preflight passes",
    }

    fishbone = {
        "problem": top_event,
        "man": ["Parameter grid selection", "Sample rotation policy"],
        "machine": ["ThinkPad L590", "snap freecad.cmd 1.1.0"],
        "method": ["dxf2step_worker T-junction", "quality preflight gate", "post-mortem DB"],
        "material": [f"sample={sample}", f"thickness_mm={thickness}"],
        "environment": ["SSH K10->ThinkPad", "Ubuntu 26.04 no apt freecad"],
    }

    logical_nodes = [
        {"id": "TOP", "text": top_event, "parent": None, "gate": "OR"},
        {"id": "N1", "text": "Geometry not manufacturable", "parent": "TOP", "gate": "OR"},
        {"id": "N2", "text": root_causes[0], "parent": "N1", "gate": "AND"},
    ]

    grid = trial_plan.get("thickness_grid_mm") or [5.0, 8.0, 10.0, 12.0, 15.0]
    doe = {
        "factors": ["thickness_mm", "sample"],
        "levels_current": {"thickness_mm": thickness, "sample": sample},
        "past_failure_count": len(past),
        "hypothesis": f"Thickness {thickness}mm on {sample} produces valid FCStd if layers close",
        "next_experiment": {"thickness_mm": _suggest_next_thickness(trial_plan, grid), "sample": sample},
    }

    key_risks = [
        f"Repeat {past[0].get('failure_class')}" if past else "First trial on sample",
        "Profile layer open loop on bracket-like DXFs",
        "Multi-view combined FCStd requires 2+ layer SUCCESS",
    ]
    recommended = [
        "Retain FCStd in archive for FreeCAD user edit",
        "Record post-mortem to DB before next trial",
        f"Monitor layer status in build_log for {sample}",
    ]

    return {
        "schema": "clawstack.dxf2step_quality_preflight.v1",
        "trial_id": job_id,
        "sample": sample,
        "thickness_mm": thickness,
        "qc_process_chart": qc_steps,
        "fmea": fmea,
        "fta_top_event": top_event,
        "fta_root_causes": root_causes,
        "why_why": [why_row],
        "fishbone": fishbone,
        "logical_tree": {"top_event": top_event, "nodes": logical_nodes},
        "doe": doe,
        "key_risks": key_risks,
        "recommended_emphasis": recommended,
        "past_trouble_excerpt": _past_trouble_excerpt(800),
        "analysis_source": "rules",
        "created_at": now_iso(),
    }


def build_postmortem(trial: dict[str, Any]) -> dict[str, Any]:
    sample = str(trial.get("sample") or "unknown")
    thickness = float(trial.get("thickness_mm") or 10.0)
    job_id = str(trial.get("job_id") or trial.get("trial_id") or "unknown")
    verdict = str(trial.get("verdict") or "UNKNOWN").upper()
    build_log = trial.get("build_log") or {}
    failure_class = _classify_failure(trial)
    layer_summary = _layer_summary(build_log)

    top_event = (
        f"DXF2STEP {job_id} ({sample} @ {thickness}mm) -> {verdict}"
        if verdict != "SUCCESS"
        else f"DXF2STEP {job_id} ({sample} @ {thickness}mm) succeeded with FCStd archive"
    )

    root_causes: list[str] = []
    if failure_class == "open_loop_profile":
        root_causes = ["Profile layer has zero outer edges after T-junction", "DXF not closed loops"]
    elif failure_class == "tjunction_no_outer_edges":
        root_causes = ["T-junction resolver removed all edges", "DXF topology incompatible"]
    elif failure_class == "worker_script_error":
        root_causes = ["Python exception in dxf2step_worker", "Check stderr_tail"]
    elif failure_class == "partial_layer_success":
        root_causes = [f"Only subset of layers done: {layer_summary}", "Need all layers for combined FCStd"]
    elif failure_class == "multiview_compound_fallback":
        root_causes = [
            "Front/top slabs misaligned or intersection empty; compound shows overlapping TOP VIEW profiles",
            f"view_assignments={build_log.get('view_assignments')}",
        ]
    elif failure_class == "combined_geometry_ng":
        root_causes = [
            "Combined STEP failed visual/geometry gate (overlapping silhouettes or compound fallback)",
            build_log.get("reconstruction_warning") or build_log.get("reconstruction_note") or layer_summary,
        ]
    elif failure_class == "success":
        root_causes = ["Layers closed and FreeCAD extrude succeeded"]
    else:
        root_causes = [failure_class, layer_summary or "see build_log"]

    fmea = _base_fmea_rows(sample, thickness, fetch_past_analyses(sample=sample, limit=3))
    for row in fmea:
        if row.get("failure_mode") and failure_class in str(row.get("failure_mode", "")).lower().replace(" ", "_"):
            row["occurrence"] = min(int(row.get("occurrence") or 5) + 1, 10)

    fmea.append(
        {
            "process": "DXF99_this_trial",
            "failure_mode": failure_class,
            "effect": f"verdict={verdict}; layers={layer_summary}",
            "cause": (trial.get("stderr_tail") or trial.get("stdout_tail") or "")[:300],
            "severity": 8 if verdict in _FAIL_VERDICTS else 3,
            "occurrence": 5,
            "detection": 2,
            "countermeasure": _countermeasure_for_class(failure_class, trial),
        }
    )

    why_row = {
        "why1": f"Verdict is {verdict}",
        "why2": f"Failure class: {failure_class}",
        "why3": f"Layers: {layer_summary}",
        "why4": f"exit_code={trial.get('exit_code')}",
        "why5": root_causes[0],
        "action": _countermeasure_for_class(failure_class, trial),
    }

    fishbone = {
        "problem": top_event,
        "man": ["Thickness grid", "Sample pick order"],
        "machine": ["ThinkPad FreeCAD snap", "SSH worker"],
        "method": ["T-junction clean", "generate_freecad_script", "quality gate"],
        "material": [f"sample={sample}", f"thickness={thickness}mm", f"layers={layer_summary}"],
        "environment": ["K10 orchestration", "Archive sync to workspace"],
    }

    logical_nodes = [
        {"id": "TOP", "text": top_event, "parent": None, "gate": "OR"},
        {"id": "N1", "text": failure_class, "parent": "TOP", "gate": "OR"},
        {"id": "N2", "text": root_causes[0], "parent": "N1", "gate": "AND"},
    ]
    if len(root_causes) > 1:
        logical_nodes.append({"id": "N3", "text": root_causes[1], "parent": "N1", "gate": "AND"})

    grid = trial.get("thickness_grid_mm") or [5.0, 8.0, 10.0, 12.0, 15.0]
    doe = {
        "factors": ["thickness_mm", "sample"],
        "levels_current": {"thickness_mm": thickness, "sample": sample},
        "failure_class": failure_class,
        "band_violations": [],
        "hypothesis": f"Address {failure_class} before repeating same combo",
        "next_experiment": {
            "thickness_mm": _suggest_next_thickness(trial, grid),
            "sample": _suggest_next_sample(trial),
        },
    }

    countermeasures = [
        _countermeasure_for_class(failure_class, trial),
        "Persist post-mortem to dxf2step_trial_analyses + fmea_registry",
        "Load registry rows into next preflight FMEA",
    ]
    if verdict == "SUCCESS":
        countermeasures.insert(0, "Keep FCStd in archive; proceed to next sample/thickness in grid")

    return {
        "schema": "clawstack.dxf2step_quality_postmortem.v1",
        "trial_id": job_id,
        "sample": sample,
        "thickness_mm": thickness,
        "verdict": verdict,
        "failure_class": failure_class,
        "qc_process_chart": [
            {
                "step": "DXF-PM01",
                "control_point": "Trial execution",
                "standard": "worker exit + build_log layers",
                "risk": layer_summary,
            },
            {
                "step": "DXF-PM02",
                "control_point": "FCStd retention",
                "standard": "primary_fcstd in archive",
                "risk": (trial.get("archive") or {}).get("primary_fcstd") or "missing",
            },
        ],
        "fmea": fmea,
        "fta_top_event": top_event,
        "fta_root_causes": root_causes,
        "why_why": [why_row],
        "fishbone": fishbone,
        "logical_tree": {"top_event": top_event, "nodes": logical_nodes},
        "doe": doe,
        "key_risks": [f"Repeat {failure_class} on {sample}", "Knowledge loss if DB not updated"],
        "countermeasures": countermeasures,
        "analysis_source": "rules",
        "created_at": now_iso(),
    }


def _countermeasure_for_class(failure_class: str, trial: dict[str, Any]) -> str:
    if failure_class == "open_loop_profile":
        return "Fix Profile DXF closed loop; try multi-view sample with valid front/top layers"
    if failure_class == "tjunction_no_outer_edges":
        return "Increase T-junction tolerance or simplify DXF layer geometry"
    if failure_class == "worker_script_error":
        return "Patch dxf2step_worker; redeploy via k10_thinkpad_dxf2step_setup.py"
    if failure_class == "partial_layer_success":
        return "Investigate failed layers in build_log; do not treat PARTIAL as North Star KPI met"
    if failure_class == "multiview_compound_fallback":
        return "Drop drawing-frame layers; use single profile extrude or fix front/top/right view pairing"
    if failure_class == "combined_geometry_ng":
        return "Do not ship combined FCStd; rerun after frame-layer filter or manual view-assignments"
    if failure_class == "success":
        return "Continue grid; ensure FCStd synced for user edit"
    return "Review stderr/build_log; rotate sample in DOE next_experiment"


def _suggest_next_sample(trial: dict[str, Any]) -> str:
    samples = trial.get("sample_list") or []
    current = str(trial.get("sample") or "")
    if not samples:
        return current
    try:
        idx = samples.index(current)
        return str(samples[(idx + 1) % len(samples)])
    except ValueError:
        return str(samples[0])


def validate_analysis(analysis: dict[str, Any], *, phase: str) -> tuple[bool, list[str]]:
    required = PREFLIGHT_REQUIRED if phase == "preflight" else POSTMORTEM_REQUIRED
    issues: list[str] = []
    for key in required:
        if key not in analysis:
            issues.append(f"missing:{key}")
    if len(analysis.get("qc_process_chart") or []) < 2:
        issues.append("qc_process_chart<2")
    if len(analysis.get("fmea") or []) < 2:
        issues.append("fmea<2")
    if not analysis.get("fta_top_event"):
        issues.append("fta_top_event empty")
    if len(analysis.get("fta_root_causes") or []) < 1:
        issues.append("fta_root_causes empty")
    if len(analysis.get("why_why") or []) < 1:
        issues.append("why_why empty")
    fish = analysis.get("fishbone") or {}
    for dim in ("man", "machine", "method", "material", "environment"):
        if not fish.get(dim):
            issues.append(f"fishbone.{dim} empty")
    lt = analysis.get("logical_tree") or {}
    if not lt.get("top_event") or len(lt.get("nodes") or []) < 2:
        issues.append("logical_tree incomplete")
    if phase == "preflight":
        if len(analysis.get("recommended_emphasis") or []) < 1:
            issues.append("recommended_emphasis empty")
    if phase == "postmortem":
        if not analysis.get("failure_class"):
            issues.append("failure_class empty")
        elif analysis.get("failure_class") != "success" and str(analysis.get("verdict", "")).upper() == "SUCCESS":
            issues.append(f"ai_defect_detected:{analysis.get('failure_class')}")
        if len(analysis.get("countermeasures") or []) < 1:
            issues.append("countermeasures empty")
    doe = analysis.get("doe") or {}
    if not doe.get("next_experiment"):
        issues.append("doe.next_experiment empty")
    return len(issues) == 0, issues


def _llm_enrich(trial: dict[str, Any], base: dict[str, Any], *, phase: str) -> dict[str, Any]:
    mode = llm_mode()
    verdict = str(trial.get("verdict") or "UNKNOWN").upper()
    base["llm_mode"] = mode
    if mode == "never":
        base["llm_enrich_skipped"] = "mode=never"
        return base
    if mode == "failed" and phase == "postmortem" and verdict not in _FAIL_VERDICTS:
        base["llm_enrich_skipped"] = f"mode=failed verdict={verdict}"
        return base
    if mode == "failed" and phase == "preflight":
        base["llm_enrich_skipped"] = "mode=failed preflight_rules_only"
        return base

    required = PREFLIGHT_REQUIRED if phase == "preflight" else POSTMORTEM_REQUIRED
    prompt = (
        f"You are a strict QA inspector for DXF-to-3D reconstruction. Inspect geometry metrics, FreeCAD logs, "
        f"and layer stats to verify that the solid is error-free, closed, has no missing features, and holes are NOT filled.\n"
        f"If you find any geometry errors, filled holes, self-intersections, or invalid volume/area, you MUST classify it as a defect (e.g., set failure_class to 'hole_filled_defect' or 'geometry_mismatch') and suggest countermeasures.\n"
        f"DXF2STEP {phase} quality analysis. Improve JSON only; keep all keys.\n"
        f"Trial: {json.dumps({k: trial.get(k) for k in ('job_id', 'sample', 'verdict', 'thickness_mm')}, ensure_ascii=False)}\n"
        f"Rule analysis: {json.dumps(base, ensure_ascii=False)[:3500]}\n"
        f"Past trouble:\n{_past_trouble_excerpt(1000)}\n"
        f"Return single JSON with keys: {', '.join(required)}"
    )
    body = {
        "model": LLM_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.2,
        "max_tokens": 1200,
    }
    req = urllib.request.Request(
        f"{LITELLM_URL.rstrip('/')}/v1/chat/completions",
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {LITELLM_KEY}"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=LLM_TIMEOUT) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
        text = (payload.get("choices") or [{}])[0].get("message", {}).get("content", "")
        start, end = text.find("{"), text.rfind("}")
        if start < 0 or end <= start:
            return base
        merged = json.loads(text[start : end + 1])
        for key in required:
            if key in merged and merged[key]:
                base[key] = merged[key]
        base["analysis_source"] = "rules+llm"
        base["llm_model"] = LLM_MODEL
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, KeyError) as exc:
        base["llm_enrich_error"] = str(exc)[:200]
    return base


def _update_fmea_registry(trial_id: str, sample: str, fmea_rows: list[dict[str, Any]]) -> None:
    reg = load_fmea_registry()
    rows = list(reg.get("rows") or [])
    seen = {(r.get("sample"), r.get("failure_mode"), r.get("countermeasure")) for r in rows}
    for row in fmea_rows:
        if not row.get("countermeasure"):
            continue
        key = (sample, row.get("failure_mode"), row.get("countermeasure"))
        if key in seen:
            continue
        entry = {
            "sample": sample,
            "failure_mode": row.get("failure_mode"),
            "cause": row.get("cause"),
            "countermeasure": row.get("countermeasure"),
            "severity": row.get("severity"),
            "occurrence": row.get("occurrence"),
            "detection": row.get("detection"),
            "source_trial_id": trial_id,
            "updated_at": now_iso(),
        }
        rows.append(entry)
        seen.add(key)
    reg["rows"] = rows[-500:]
    reg["updated_at"] = now_iso()
    PREFLIGHT_REGISTRY.parent.mkdir(parents=True, exist_ok=True)
    PREFLIGHT_REGISTRY.write_text(json.dumps(reg, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    try:
        conn = sqlite3.connect(str(GROWTH_DB))
        _ensure_db_schema(conn)
        for row in fmea_rows:
            if not row.get("countermeasure"):
                continue
            conn.execute(
                """
                INSERT INTO dxf2step_fmea_registry
                  (sample, failure_mode, cause, countermeasure, severity, occurrence, detection, source_trial_id, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(sample, failure_mode, countermeasure) DO UPDATE SET
                  occurrence=excluded.occurrence,
                  source_trial_id=excluded.source_trial_id,
                  created_at=excluded.created_at
                """,
                (
                    sample,
                    str(row.get("failure_mode") or "unknown"),
                    str(row.get("cause") or "")[:500],
                    str(row.get("countermeasure") or "")[:500],
                    int(row.get("severity") or 5),
                    int(row.get("occurrence") or 5),
                    int(row.get("detection") or 3),
                    trial_id,
                    now_iso(),
                ),
            )
        conn.commit()
        conn.close()
    except Exception as exc:
        print(f"[dxf2step-quality] fmea registry DB error: {exc}", flush=True)


def persist_analysis(
    *,
    trial_id: str,
    phase: str,
    trial: dict[str, Any],
    analysis: dict[str, Any],
    skip_jsonl: bool = False,
) -> dict[str, Any]:
    analysis = slim_analysis_for_db(analysis, phase)
    record = {
        "trial_id": trial_id,
        "phase": phase,
        "sample": trial.get("sample"),
        "thickness_mm": trial.get("thickness_mm"),
        "verdict": trial.get("verdict"),
        "failure_class": analysis.get("failure_class"),
        "analyzed_at": now_iso(),
        "analysis": analysis,
    }

    JSONL_PATH.parent.mkdir(parents=True, exist_ok=True)
    if not skip_jsonl:
        with JSONL_PATH.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")

    val_ok = 1 if (analysis.get("_validation") or {}).get("ok") else 0
    try:
        GROWTH_DB.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(GROWTH_DB))
        _ensure_db_schema(conn)
        conn.execute(
            """
            INSERT INTO dxf2step_trial_analyses
              (trial_id, phase, sample, thickness_mm, verdict, failure_class, analysis_json, validation_ok, created_at, part_manifest_path)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(trial_id, phase) DO UPDATE SET
              verdict=excluded.verdict,
              failure_class=excluded.failure_class,
              analysis_json=excluded.analysis_json,
              validation_ok=excluded.validation_ok,
              created_at=excluded.created_at,
              part_manifest_path=excluded.part_manifest_path
            """,
            (
                trial_id,
                phase,
                str(trial.get("sample") or ""),
                float(trial.get("thickness_mm") or 0),
                str(trial.get("verdict") or ""),
                str(analysis.get("failure_class") or ""),
                json.dumps(analysis, ensure_ascii=False),
                val_ok,
                now_iso(),
                str(trial.get("part_manifest_path") or ""),
            ),
        )
        conn.commit()
        conn.close()
        record["db"] = str(GROWTH_DB)
    except Exception as exc:
        record["db_error"] = str(exc)[:300]

    if phase == "postmortem":
        _update_fmea_registry(trial_id, str(trial.get("sample") or ""), analysis.get("fmea") or [])

    return record


def run_preflight_gate(trial_plan: dict[str, Any], *, archive_dir: Path | None = None) -> dict[str, Any]:
    analysis = build_preflight(trial_plan)
    analysis = _llm_enrich(trial_plan, analysis, phase="preflight")
    ok, issues = validate_analysis(analysis, phase="preflight")
    analysis["_validation"] = {"ok": ok, "issues": issues}

    trial_id = str(trial_plan.get("job_id") or "pending")
    rec = persist_analysis(trial_id=trial_id, phase="preflight", trial=trial_plan, analysis=analysis)

    if archive_dir:
        archive_dir.mkdir(parents=True, exist_ok=True)
        (archive_dir / "quality_preflight.json").write_text(
            json.dumps(analysis, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

    if preflight_required() and not ok:
        raise Dxf2StepQualityGateError(f"preflight invalid: {issues}")

    rec["analysis"] = analysis
    rec["gate_ok"] = ok
    return rec


def run_postmortem_gate(trial: dict[str, Any], *, archive_dir: Path | None = None) -> dict[str, Any]:
    analysis = build_postmortem(trial)
    analysis = _llm_enrich(trial, analysis, phase="postmortem")
    ok, issues = validate_analysis(analysis, phase="postmortem")
    manifest_ok, manifest_issues = _validate_trial_manifest(
        archive_dir, str(trial.get("verdict") or "")
    )
    if not manifest_ok:
        issues = list(issues) + list(manifest_issues)
    ok = ok and manifest_ok
    analysis["_validation"] = {"ok": ok, "issues": issues, "manifest_ok": manifest_ok}

    trial_id = str(trial.get("job_id") or trial.get("trial_id") or "unknown")
    rec = persist_analysis(trial_id=trial_id, phase="postmortem", trial=trial, analysis=analysis)

    if archive_dir:
        archive_dir.mkdir(parents=True, exist_ok=True)
        (archive_dir / "quality_postmortem.json").write_text(
            json.dumps(analysis, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

    rec["analysis"] = analysis
    rec["gate_ok"] = ok
    print(
        f"[dxf2step-quality] postmortem {trial_id} verdict={trial.get('verdict')} "
        f"class={analysis.get('failure_class')} ok={ok}",
        flush=True,
    )
    return rec


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description="DXF2STEP quality gate (preflight or postmortem)")
    parser.add_argument("--preflight-json", help="trial plan JSON path")
    parser.add_argument("--postmortem-json", help="completed trial JSON path")
    args = parser.parse_args()

    if args.preflight_json:
        plan = json.loads(Path(args.preflight_json).read_text(encoding="utf-8-sig"))
        rec = run_preflight_gate(plan)
        print(json.dumps(rec, ensure_ascii=False, indent=2))
        return 0 if rec.get("gate_ok") else 1

    if args.postmortem_json:
        trial = json.loads(Path(args.postmortem_json).read_text(encoding="utf-8-sig"))
        rec = run_postmortem_gate(trial)
        print(json.dumps(rec, ensure_ascii=False, indent=2))
        return 0 if rec.get("gate_ok") else 1

    parser.error("Specify --preflight-json or --postmortem-json")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
