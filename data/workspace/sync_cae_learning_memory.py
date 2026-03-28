#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import requests


JST = timezone(timedelta(hours=9))
WORKSPACE_ROOT = Path(__file__).resolve().parent
STATUS_PATH = WORKSPACE_ROOT / "cae_learning_memory_sync_status.json"
STATE_PATH = WORKSPACE_ROOT / "cae_learning_memory_sync_state.json"
DEFAULT_BASE_URL = "http://localhost:8110"
DEFAULT_PATHS = [
    str(WORKSPACE_ROOT / "openradioss_run.log"),
    str(WORKSPACE_ROOT / "apps" / "molding_hub" / "test_sim" / "CFD_MeltFront" / "case.foam"),
]


def now_jst_iso() -> str:
    return datetime.now(JST).isoformat()


def write_status(payload: dict[str, Any]) -> None:
    STATUS_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def load_state() -> dict[str, Any]:
    if not STATE_PATH.exists():
        return {}
    return json.loads(STATE_PATH.read_text(encoding="utf-8"))


def save_state(payload: dict[str, Any]) -> None:
    STATE_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def normalize_space(value: str | None) -> str:
    return re.sub(r"\s+", " ", value or "").strip()


def safe_read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def slugify_id(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9._-]+", "_", value.strip())
    return slug.strip("._") or "item"


def parse_key_value_dict(text: str) -> dict[str, str]:
    result: dict[str, str] = {}
    for raw_line in text.splitlines():
        line = raw_line.split("//", 1)[0].strip()
        if not line or line in {"{", "}", "(", ")", "();"}:
            continue
        match = re.match(r"([A-Za-z0-9_]+)\s+(.+?);$", line)
        if match:
            result[match.group(1)] = normalize_space(match.group(2))
    return result


def parse_openfoam_boundaries(text: str) -> list[tuple[str, str]]:
    pairs: list[tuple[str, str]] = []
    current_name: str | None = None
    inside_block = False
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("//"):
            continue
        if line == "{":
            inside_block = True
            continue
        if line == "}":
            current_name = None
            inside_block = False
            continue
        if not inside_block and re.fullmatch(r"[A-Za-z0-9_]+", line) and line != "FoamFile":
            current_name = line
            continue
        if inside_block and current_name:
            type_match = re.match(r"type\s+([A-Za-z0-9_<>]+);", line)
            if type_match:
                pairs.append((current_name, type_match.group(1)))
                current_name = None
    return pairs


def resolve_openfoam_case_dir(path: Path) -> Path | None:
    candidate = path if path.is_dir() else path.parent
    if (candidate / "system" / "controlDict").exists():
        return candidate
    if path.is_file() and path.name == "case.foam" and (path.parent / "system" / "controlDict").exists():
        return path.parent
    if path.is_file() and path.name == "controlDict" and path.parent.name == "system":
        case_dir = path.parent.parent
        if (case_dir / "constant").exists():
            return case_dir
    return None


def healthcheck(base_url: str, request_timeout: int) -> dict[str, Any]:
    resp = requests.get(f"{base_url.rstrip('/')}/health", timeout=request_timeout)
    resp.raise_for_status()
    return resp.json()


def post_json(base_url: str, route: str, payload: dict[str, Any], request_timeout: int) -> dict[str, Any]:
    resp = requests.post(f"{base_url.rstrip('/')}{route}", json=payload, timeout=request_timeout)
    resp.raise_for_status()
    return resp.json()


def base_url_candidates(base_url: str) -> list[str]:
    text = normalize_space(base_url).rstrip("/")
    candidates: list[str] = []
    seen: set[str] = set()

    def push(value: str) -> None:
        value = normalize_space(value).rstrip("/")
        if not value or value in seen:
            return
        seen.add(value)
        candidates.append(value)

    push(text)
    if "localhost" in text:
        push(text.replace("localhost", "host.docker.internal"))
        push(text.replace("localhost", "127.0.0.1"))
    elif "127.0.0.1" in text:
        push(text.replace("127.0.0.1", "host.docker.internal"))
        push(text.replace("127.0.0.1", "localhost"))
    else:
        push(DEFAULT_BASE_URL)
        push(DEFAULT_BASE_URL.replace("localhost", "host.docker.internal"))
        push(DEFAULT_BASE_URL.replace("localhost", "127.0.0.1"))
    return candidates


def resolve_base_url(base_url: str, request_timeout: int) -> tuple[str, dict[str, Any]]:
    last_error: Exception | None = None
    for candidate in base_url_candidates(base_url):
        try:
            return candidate, healthcheck(candidate, request_timeout)
        except Exception as exc:
            last_error = exc
            continue
    if last_error:
        raise last_error
    raise RuntimeError("No reachable learning_engine base URL candidate")


def detect_tool_name(path: Path, text: str) -> str:
    lower = path.name.lower() + " " + text.lower()
    if "openradioss" in lower or "radioss" in lower:
        return "OpenRadioss"
    if "openfoam" in lower or "foam" in lower:
        return "OpenFOAM"
    return "CAE"


def parse_openradioss_log(path: Path, text: str, source_org: str) -> dict[str, Any]:
    root_match = re.search(r"ROOT:\s+(.+?)\s+RESTART:\s+(\d+)", text)
    run_root = normalize_space(root_match.group(1)) if root_match else path.stem
    tool_version_match = re.search(r"OpenRadioss Engine.*?Linux.*?\n.*?COPYRIGHT.*?1986-(\d{4})", text, re.DOTALL)
    tool_version = f"OpenRadioss {tool_version_match.group(1)}" if tool_version_match else "OpenRadioss"
    dt_match = re.search(r"DT=\s*([0-9.E+-]+)", text)
    last_nc_match = None
    for match in re.finditer(r"NC=\s*(\d+)\s*T=\s*([0-9.E+-]+)\s*DT=\s*([0-9.E+-]+)\s*ERR=\s*([^\s]+)", text):
        last_nc_match = match
    animation_count = len(re.findall(r"ANIMATION FILE:", text))
    elapsed_matches = list(re.finditer(r"ELAPSED TIME=\s*([0-9.]+)\s*s", text))
    wall_clock = f"{elapsed_matches[-1].group(1)} s" if elapsed_matches else ""
    result_status = "partial"
    failure_mode = ""
    error_signature = ""
    if re.search(r"\bERROR\b|\bFAILED\b|TERMINATION", text, re.IGNORECASE):
        result_status = "failed"
        failure_mode = "solver_failure"
        error_signature = "solver reported termination or error"
    elif last_nc_match and int(last_nc_match.group(1)) >= 1000:
        result_status = "success"
    summary = (
        f"OpenRadioss run {run_root} reached NC={last_nc_match.group(1) if last_nc_match else 'unknown'} "
        f"with dt={dt_match.group(1) if dt_match else 'unknown'} and {animation_count} animation outputs."
    )
    lesson = ""
    if result_status == "success":
        lesson = "Stable time-step progression maintained through the observed log window."
    elif result_status == "failed":
        lesson = "Review starter cards, contact settings, and time-step controls against similar failed runs."
    return {
        "run_id": f"cae:{path.name}",
        "source_org": source_org,
        "source_type": "cae_log",
        "review_status": "reviewed",
        "tool_name": "OpenRadioss",
        "tool_version": tool_version,
        "simulation_type": "explicit_structural",
        "project_name": run_root,
        "geometry_type": "assembly",
        "time_step": dt_match.group(1) if dt_match else None,
        "solver_settings": "Engine log parsed from external harness",
        "result_status": result_status,
        "failure_mode": failure_mode or None,
        "error_signature": error_signature or ("stable_explicit_progress" if result_status == "success" else None),
        "wall_clock_time": wall_clock or None,
        "output_files": [path.name],
        "summary": summary,
        "lesson": lesson or None,
        "tags": ["cae", "openradioss", f"status:{result_status}"],
        "extra": {
            "log_path": str(path),
            "animation_count": animation_count,
            "last_cycle": int(last_nc_match.group(1)) if last_nc_match else None,
            "last_simulation_time": last_nc_match.group(2) if last_nc_match else None,
        },
    }


def infer_openfoam_simulation(application: str | None, phases: list[str]) -> str:
    app = (application or "").lower()
    if "interfoam" in app:
        return "multiphase_cfd"
    if "simplefoam" in app or "pimplefoam" in app:
        return "flow_cfd"
    if "cht" in app:
        return "conjugate_heat_transfer"
    if phases:
        return "multiphase_cfd"
    return "cfd"


def parse_openfoam_case(path: Path, source_org: str) -> dict[str, Any]:
    case_dir = resolve_openfoam_case_dir(path)
    if case_dir is None:
        raise FileNotFoundError(f"OpenFOAM case structure not found for {path}")

    control_dict_path = case_dir / "system" / "controlDict"
    transport_path = case_dir / "constant" / "transportProperties"
    boundary_path = case_dir / "constant" / "polyMesh" / "boundary"
    block_mesh_path = case_dir / "system" / "blockMeshDict"
    zero_dir = case_dir / "0"
    vtk_dir = case_dir / "VTK"

    control_text = safe_read_text(control_dict_path) if control_dict_path.exists() else ""
    transport_text = safe_read_text(transport_path) if transport_path.exists() else ""
    boundary_text = safe_read_text(boundary_path) if boundary_path.exists() else ""
    block_mesh_text = safe_read_text(block_mesh_path) if block_mesh_path.exists() else ""

    control_values = parse_key_value_dict(control_text)
    transport_values = parse_key_value_dict(transport_text)

    version_match = re.search(r"Version:\s*v?([0-9.]+)", control_text, re.IGNORECASE)
    tool_version = f"OpenFOAM {version_match.group(1)}" if version_match else "OpenFOAM"
    application = control_values.get("application")
    delta_t = control_values.get("deltaT")
    end_time = control_values.get("endTime")
    max_co = control_values.get("maxCo")
    max_alpha_co = control_values.get("maxAlphaCo")

    phase_match = re.search(r"phases\s*\(([^)]+)\);", transport_text)
    phases = re.findall(r"[A-Za-z0-9_.+-]+", phase_match.group(1)) if phase_match else []
    material = ", ".join(phases) if phases else None

    block_match = re.search(r"hex\s+\([^)]+\)\s+\((\d+)\s+(\d+)\s+(\d+)\)", block_mesh_text)
    mesh_size = None
    cell_count = None
    if block_match:
        dims = [int(block_match.group(i)) for i in range(1, 4)]
        cell_count = dims[0] * dims[1] * dims[2]
        mesh_size = f"{dims[0]}x{dims[1]}x{dims[2]} cells ({cell_count} total)"

    boundary_pairs = parse_openfoam_boundaries(boundary_text)
    boundary_names = [name for name, _ in boundary_pairs]
    boundary_summary = ", ".join(f"{name}:{boundary_type}" for name, boundary_type in boundary_pairs)

    field_names = sorted(item.name for item in zero_dir.iterdir() if item.is_file()) if zero_dir.exists() else []
    vtk_files = sorted(str(item.relative_to(case_dir)) for item in vtk_dir.rglob("*.vtk")) if vtk_dir.exists() else []

    result_status = "success" if vtk_files else "partial"
    lesson = (
        "Reusable OpenFOAM case captures stable output generation and can seed similar CFD setup comparisons."
        if vtk_files
        else "Case definition exists, but no VTK outputs were found yet; review solver execution and export steps."
    )
    summary_parts = [
        f"OpenFOAM case {case_dir.name}",
        f"solver={application or 'unknown'}",
        f"simulation={infer_openfoam_simulation(application, phases)}",
    ]
    if mesh_size:
        summary_parts.append(f"mesh={mesh_size}")
    if material:
        summary_parts.append(f"phases={material}")
    if vtk_files:
        summary_parts.append(f"vtkOutputs={len(vtk_files)}")
    summary = "; ".join(summary_parts) + "."

    solver_settings_parts = []
    if delta_t:
        solver_settings_parts.append(f"deltaT={delta_t}")
    if end_time:
        solver_settings_parts.append(f"endTime={end_time}")
    if max_co:
        solver_settings_parts.append(f"maxCo={max_co}")
    if max_alpha_co:
        solver_settings_parts.append(f"maxAlphaCo={max_alpha_co}")

    case_slug = slugify_id(case_dir.relative_to(WORKSPACE_ROOT).as_posix() if case_dir.is_relative_to(WORKSPACE_ROOT) else case_dir.name)
    return {
        "run_id": f"cae:openfoam:{case_slug}",
        "source_org": source_org,
        "source_type": "cae_case",
        "review_status": "reviewed",
        "tool_name": "OpenFOAM",
        "tool_version": tool_version,
        "simulation_type": infer_openfoam_simulation(application, phases),
        "project_name": case_dir.name,
        "material": material,
        "geometry_type": "cfd_case",
        "mesh_size": mesh_size,
        "element_type": "hex" if block_match else None,
        "time_step": delta_t,
        "solver_settings": "; ".join(solver_settings_parts) if solver_settings_parts else "OpenFOAM case parsed from external harness",
        "boundary_conditions": boundary_summary or None,
        "initial_conditions": ", ".join(field_names) if field_names else None,
        "result_status": result_status,
        "error_signature": "vtk_outputs_present" if vtk_files else None,
        "output_files": vtk_files[:20] or [path.name],
        "summary": summary,
        "lesson": lesson,
        "tags": ["cae", "openfoam", f"status:{result_status}"] + ([f"solver:{application}"] if application else []),
        "extra": {
            "case_path": str(case_dir),
            "application": application,
            "cell_count": cell_count,
            "field_names": field_names,
            "vtk_count": len(vtk_files),
            "boundary_names": boundary_names,
            "transport_keys": sorted(transport_values.keys()),
        },
    }


def parse_generic_log(path: Path, text: str, source_org: str) -> dict[str, Any]:
    tool_name = detect_tool_name(path, text)
    result_status = "failed" if re.search(r"error|failed|fatal", text, re.IGNORECASE) else "partial"
    error_signature = ""
    if result_status == "failed":
        first_error = re.search(r"^.*(?:error|failed|fatal).*$", text, re.IGNORECASE | re.MULTILINE)
        error_signature = normalize_space(first_error.group(0))[:200] if first_error else "generic_solver_error"
    summary = normalize_space(text[:800])[:600]
    return {
        "run_id": f"cae:{path.name}",
        "source_org": source_org,
        "source_type": "cae_log",
        "review_status": "reviewed",
        "tool_name": tool_name,
        "simulation_type": "unknown",
        "result_status": result_status,
        "failure_mode": "solver_failure" if result_status == "failed" else None,
        "error_signature": error_signature or None,
        "output_files": [path.name],
        "summary": summary,
        "lesson": None,
        "tags": ["cae", tool_name.lower(), f"status:{result_status}"],
        "extra": {"log_path": str(path)},
    }


def build_payload(path: Path, source_org: str) -> dict[str, Any]:
    case_dir = resolve_openfoam_case_dir(path)
    if case_dir is not None:
        return parse_openfoam_case(case_dir, source_org)
    text = safe_read_text(path)
    if "OpenRadioss Engine" in text:
        return parse_openradioss_log(path, text, source_org)
    return parse_generic_log(path, text, source_org)


def main() -> None:
    parser = argparse.ArgumentParser(description="Sync CAE log summaries into learning_engine memory")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--source-org", default="Mitsui")
    parser.add_argument("--request-timeout", type=int, default=45)
    parser.add_argument("--paths", nargs="*", default=DEFAULT_PATHS)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    status: dict[str, Any] = {
        "startedAt": now_jst_iso(),
        "stage": "starting",
        "baseUrl": args.base_url,
        "dryRun": args.dry_run,
        "paths": args.paths,
    }
    write_status(status)

    state = load_state()
    try:
        resolved_base_url, health = resolve_base_url(args.base_url, args.request_timeout)
        status["resolvedBaseUrl"] = resolved_base_url
        status["health"] = health
    except Exception as exc:
        status["stage"] = "skipped"
        status["reason"] = f"learning_engine unavailable: {exc}"
        status["finishedAt"] = now_jst_iso()
        write_status(status)
        return

    payloads = []
    for raw_path in args.paths:
        path = Path(raw_path)
        if not path.exists():
            continue
        payloads.append(build_payload(path, args.source_org))

    status["stage"] = "loaded"
    status["candidates"] = len(payloads)
    status["postedRuns"] = 0
    status["errors"] = []
    write_status(status)

    last_run_id = normalize_space(state.get("last_run_id"))
    for payload in payloads:
        try:
            if not args.dry_run:
                post_json(resolved_base_url, "/ingest/cae-run", payload, args.request_timeout)
            status["postedRuns"] += 1
            status["currentRunId"] = payload["run_id"]
            last_run_id = payload["run_id"]
            write_status(status)
        except Exception as exc:
            status["errors"].append({"id": payload["run_id"], "detail": str(exc)})
            write_status(status)

    new_state = {
        "last_run_id": last_run_id,
        "lastRunAt": now_jst_iso(),
        "lastPostedRuns": status["postedRuns"],
    }
    if not args.dry_run:
        save_state(new_state)

    status["stage"] = "completed"
    status["state"] = new_state
    status["finishedAt"] = now_jst_iso()
    write_status(status)


if __name__ == "__main__":
    main()
