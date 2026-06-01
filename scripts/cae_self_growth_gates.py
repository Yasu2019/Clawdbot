# -*- coding: utf-8 -*-
"""
CAE Self-Growth: failure tags + pre-gates (minimal v1).

Goal:
  - Make self-growth suggestions more accurate by adding explicit failure tags.
  - Prevent runaway runs by failing fast on obvious input/template issues.

Design:
  - No destructive edits.
  - Pure functions: precheck_* (filesystem) + tag_* (log text).
  - Keep tags coarse and explainable; downstream can refine.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class PreGateResult:
    ok: bool
    tags: list[str]
    issues: list[str]
    evidence: dict[str, list[str]] | None = None


def _ok(tags: list[str], issues: list[str]) -> PreGateResult:
    return PreGateResult(ok=True, tags=tags, issues=issues, evidence=None)


def _ng(tags: list[str], issues: list[str]) -> PreGateResult:
    return PreGateResult(ok=False, tags=tags, issues=issues, evidence=None)


def precheck_openfoam_case(case_dir: Path) -> PreGateResult:
    """Fail-fast checks for OpenFOAM template/case structure."""
    tags: list[str] = []
    issues: list[str] = []

    if not case_dir.exists():
        return _ng(["precheck_missing_case_dir"], [f"Case dir not found: {case_dir}"])
    if not case_dir.is_dir():
        return _ng(["precheck_case_not_dir"], [f"Case path is not a directory: {case_dir}"])

    required = [
        ("system/controlDict", "precheck_missing_controlDict"),
        ("system/blockMeshDict", "precheck_missing_blockMeshDict"),
        ("constant/transportProperties", "precheck_missing_transportProperties"),
        ("0/U", "precheck_missing_U"),
    ]
    for rel, tag in required:
        if not (case_dir / rel).exists():
            tags.append(tag)
            issues.append(f"Missing: {rel}")

    if tags:
        return _ng(tags, issues)
    return _ok(["precheck_ok"], [])


def precheck_openfoam_interfoam_case(case_dir: Path) -> PreGateResult:
    """VOF / interFoam template checks (Phase 2 Moldflow fill front)."""
    base = precheck_openfoam_case(case_dir)
    if not base.ok:
        return base
    tags: list[str] = list(base.tags)
    issues: list[str] = list(base.issues)
    for rel, tag in (
        ("0/p_rgh", "precheck_missing_p_rgh"),
        ("0/alpha.polymer", "precheck_missing_alpha_polymer"),
        ("constant/g", "precheck_missing_g"),
        ("constant/turbulenceProperties", "precheck_missing_turbulence_properties"),
    ):
        if not (case_dir / rel).exists():
            tags.append(tag)
            issues.append(f"Missing: {rel}")
    if any(t.startswith("precheck_missing_") for t in tags if t != "precheck_ok"):
        return _ng(tags, issues)
    return _ok(["precheck_ok", "precheck_interfoam"], [])


def precheck_openfoam_thermo_case(case_dir: Path) -> PreGateResult:
    """Thermo VOF / compressibleInterFoam (Phase 3)."""
    base = precheck_openfoam_interfoam_case(case_dir)
    if not base.ok:
        return base
    tags: list[str] = list(base.tags)
    issues: list[str] = list(base.issues)
    for rel, tag in (
        ("0/T", "precheck_missing_T"),
        ("0/p", "precheck_missing_p"),
        ("constant/thermophysicalProperties", "precheck_missing_thermophysicalProperties"),
        ("constant/thermophysicalProperties.polymer", "precheck_missing_thermo_polymer"),
        ("constant/thermophysicalProperties.air", "precheck_missing_thermo_air"),
    ):
        if not (case_dir / rel).exists():
            tags.append(tag)
            issues.append(f"Missing: {rel}")
    if any(t.startswith("precheck_missing_") for t in tags if t != "precheck_ok"):
        return _ng(tags, issues)
    poly = case_dir / "constant" / "thermophysicalProperties.polymer"
    if poly.exists():
        ptxt = poly.read_text(encoding="utf-8", errors="replace")
        if not re.search(r"mu\s+[0-9.eE+-]+\s*;", ptxt) and "MU_CONST_PLACEHOLDER" not in ptxt:
            tags.append("precheck_thermo_missing_mu")
            issues.append("const transport requires mu in thermophysicalProperties.polymer")
    if any(t.startswith("precheck_") and t not in ("precheck_ok", "precheck_interfoam", "precheck_thermo") for t in tags):
        return _ng(tags, issues)
    tags = [t for t in tags if t != "precheck_interfoam"]
    tags.append("precheck_thermo")
    return _ok(tags, [])


def precheck_openradioss_case(case_dir: Path) -> PreGateResult:
    """Fail-fast checks for OpenRadioss template/case structure."""
    tags: list[str] = []
    issues: list[str] = []

    if not case_dir.exists():
        return _ng(["precheck_missing_case_dir"], [f"Case dir not found: {case_dir}"])
    if not case_dir.is_dir():
        return _ng(["precheck_case_not_dir"], [f"Case path is not a directory: {case_dir}"])

    rad_files = sorted(case_dir.glob("*.rad"))
    if not rad_files:
        return _ng(["precheck_missing_rad_files"], [f"No .rad files under: {case_dir}"])

    # Minimal sanity: this repo often uses *_0000.rad, but not all templates follow it.
    # For v1, only require that at least one .rad exists (fail-fast but not over-strict).
    has_0000 = any(p.name.endswith("_0000.rad") for p in rad_files)
    has_0001 = any(p.name.endswith("_0001.rad") for p in rad_files)
    if not has_0000:
        tags.append("precheck_missing_starter_0000")
        issues.append("No *_0000.rad starter file detected (non-fatal; check input_file naming)")
    if not has_0001:
        tags.append("precheck_missing_engine_0001")
        issues.append("No *_0001.rad engine file detected (non-fatal; may be generated later)")

    # Do not block execution on naming mismatch in v1.
    return _ok(["precheck_ok"] + sorted(tags), issues)


def tag_openfoam_log(text: str) -> list[str]:
    """Coarse failure tags from OpenFOAM stdout/stderr."""
    t = text or ""
    tags: set[str] = set()

    if "FOAM FATAL" in t or "FATAL ERROR" in t or "Fatal error" in t:
        tags.add("foam_fatal")
    if re.search(r"Cannot find file|cannot find file", t):
        tags.add("foam_missing_file")
    if "Check your boundary conditions" in t:
        tags.add("foam_bc_issue")
    if "Cannot find patchField" in t or "Unknown patchField type" in t:
        tags.add("foam_bc_type_issue")
    if "Floating point exception" in t:
        tags.add("foam_fpe")
    if "Segmentation fault" in t:
        tags.add("foam_segfault")
    if "negative volume" in t.lower():
        tags.add("mesh_negative_volume")
    if "not orthogonal" in t.lower() and "mesh" in t.lower():
        tags.add("mesh_non_orthogonal")
    if "End" in t.splitlines()[-5:]:
        tags.add("foam_end_marker")

    return sorted(tags)


def tag_openradioss_log(text: str) -> list[str]:
    """Coarse failure tags from OpenRadioss logs (starter/engine)."""
    t = text or ""
    tags: set[str] = set()

    upper = t.upper()
    if "ABNORMAL TERMINATION" in upper:
        tags.add("radioss_abnormal_termination")
    if "NORMAL TERMINATION" in upper:
        tags.add("radioss_normal_termination")
    if "ERROR" in upper:
        tags.add("radioss_error")
    if "NODAL VELOCITY" in upper and "TOO HIGH" in upper:
        tags.add("radioss_velocity_too_high")
    if "DT" in upper and ("TOO SMALL" in upper or "TIME STEP" in upper):
        tags.add("radioss_time_step_issue")
    if "NEGATIVE VOLUME" in upper:
        tags.add("mesh_negative_volume")
    if "CONTACT" in upper and "ERROR" in upper:
        tags.add("radioss_contact_issue")
    if "UNIT" in upper and "ERROR" in upper:
        tags.add("radioss_unit_issue")

    return sorted(tags)


def extract_openfoam_checkmesh_evidence(text: str, max_lines: int = 30) -> dict[str, list[str]]:
    """Extract key evidence lines from checkMesh output.

    Intended for: storing compact roots of failure in cae_te_log.json.
    """
    t = text or ""
    out: dict[str, list[str]] = {"checkMesh": []}
    if not t:
        return out
    lines = [ln.strip() for ln in t.splitlines() if ln.strip()]

    # Prefer final verdict + failure count summary. Keep it very short.
    verdict_lines: list[str] = []
    for ln in lines:
        low = ln.lower()
        if "mesh ok" in low:
            verdict_lines.append(ln)
        if "failed" in low and "mesh" in low and "check" in low:
            verdict_lines.append(ln)
        if "failed" in low and "checks" in low:
            verdict_lines.append(ln)

    # Add one or two key quality maxima if present (still short).
    quality_lines: list[str] = []
    for ln in lines:
        low = ln.lower()
        if "max" in low and ("non-orthogonality" in low or "skewness" in low):
            quality_lines.append(ln)
        if "negative" in low and "volume" in low:
            quality_lines.append(ln)

    picked = (verdict_lines[-3:] + quality_lines[-2:]) or []
    out["checkMesh"] = picked[:max_lines]
    return out


def extract_openfoam_fatal_evidence(text: str, max_lines: int = 10) -> dict[str, list[str]]:
    """Extract only the FOAM FATAL block (very compact)."""
    t = text or ""
    if not t:
        return {}
    lines = [ln.rstrip("\n") for ln in t.splitlines()]
    idxs = [i for i, ln in enumerate(lines) if "FOAM FATAL" in ln or "FATAL ERROR" in ln or "Fatal error" in ln]
    if not idxs:
        return {}
    i = idxs[-1]
    start = max(0, i - 2)
    end = min(len(lines), i + 8)
    block = [ln.strip() for ln in lines[start:end] if ln.strip()]
    return {"foam_fatal": block[:max_lines]}


def extract_openradioss_evidence(text: str, max_lines: int = 40) -> dict[str, list[str]]:
    """Extract evidence lines for contact/time-step issues from OpenRadioss combined log."""
    t = text or ""
    if not t:
        return {}
    lines = [ln.rstrip("\n") for ln in t.splitlines()]

    def take_matches(patterns: list[str]) -> list[str]:
        matches: list[str] = []
        for ln in lines:
            up = ln.upper()
            if any(p in up for p in patterns):
                matches.append(ln.strip())
        return matches[-max_lines:]

    return {
        "termination": take_matches(["NORMAL TERMINATION", "ABNORMAL TERMINATION"]),
        "time_step": take_matches(["WARNING: TIME STEP", "TIME STEP BELOW", "DT TOO", "DT", "CFL"]),
        "contact": take_matches(["CONTACT", "INTER", "GAP", "PENET", "SLAVE", "MASTER"]),
        "negative_volume": take_matches(["NEGATIVE VOLUME"]),
        "velocity": take_matches(["NODAL VELOCITY", "TOO HIGH"]),
        "unit": take_matches(["/UNIT", "UNIT", "SCALE"]),
        "error": take_matches(["ERROR", "ABORT"]),
    }

