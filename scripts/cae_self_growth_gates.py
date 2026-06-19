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


def precheck_openfoam_interfoam_turb_case(case_dir: Path) -> PreGateResult:
    """VOF + RAS k-omega SST (Phase 4)."""
    base = precheck_openfoam_interfoam_case(case_dir)
    if not base.ok:
        return base
    tags: list[str] = list(base.tags)
    issues: list[str] = list(base.issues)
    for rel, tag in (
        ("0/k", "precheck_missing_k"),
        ("0/omega", "precheck_missing_omega"),
        ("0/nut", "precheck_missing_nut"),
    ):
        if not (case_dir / rel).exists():
            tags.append(tag)
            issues.append(f"Missing: {rel}")
    turb = case_dir / "constant" / "turbulenceProperties"
    if turb.exists():
        txt = turb.read_text(encoding="utf-8", errors="replace")
        if "simulationType  RAS" not in txt and "simulationType  RAS;" not in txt:
            tags.append("precheck_turb_not_ras")
            issues.append("turbulenceProperties must set simulationType RAS for Phase 4")
        if "kOmegaSST" not in txt:
            tags.append("precheck_turb_not_kOmegaSST")
            issues.append("RASModel must be kOmegaSST")
    if any(t.startswith("precheck_") and t not in ("precheck_ok", "precheck_interfoam") for t in tags):
        return _ng(tags, issues)
    tags.append("precheck_turb")
    return _ok(tags, issues)


def precheck_moldflow_cad_case(case_dir: Path) -> PreGateResult:
    """Phase 7: CAD-built case (cad_manifest.json + interFoam VOF)."""
    manifest = case_dir / "cad_manifest.json"
    if not manifest.exists():
        return _ng(
            ["precheck_missing_cad_manifest"],
            ["Missing cad_manifest.json (run moldflow_step_case_builder)"],
        )
    mesh_mode = ""
    try:
        import json

        mesh_mode = str(json.loads(manifest.read_text(encoding="utf-8")).get("mesh_mode", ""))
    except Exception:
        pass

    if mesh_mode == "gmsh_volume":
        tags: list[str] = []
        issues: list[str] = []
        for rel, tag in (
            ("system/controlDict", "precheck_missing_controlDict"),
            ("constant/transportProperties", "precheck_missing_transportProperties"),
            ("0/U", "precheck_missing_U"),
            ("0/p_rgh", "precheck_missing_p_rgh"),
            ("0/alpha.polymer", "precheck_missing_alpha_polymer"),
            ("constant/g", "precheck_missing_g"),
            ("constant/turbulenceProperties", "precheck_missing_turbulence_properties"),
            ("cavity.msh", "precheck_missing_cavity_msh"),
            ("system/topoSetDict.splitInlets", "precheck_missing_split_topo"),
        ):
            if not (case_dir / rel).exists():
                tags.append(tag)
                issues.append(f"Missing: {rel}")
        if tags:
            return _ng(tags, issues)
        tags = ["precheck_ok"]
        issues = []
    else:
        base = precheck_openfoam_interfoam_case(case_dir)
        if not base.ok:
            return base
        tags = list(base.tags)
        issues = list(base.issues)

    gate_resolved = case_dir / "gate_spec.resolved.json"
    if not gate_resolved.exists():
        tags.append("precheck_missing_gate_spec_resolved")
        issues.append("Missing gate_spec.resolved.json")
        return _ng(tags, issues)
    poly = case_dir / "constant" / "polyMesh" / "points"
    bmd = case_dir / "system" / "blockMeshDict"
    mesh_mode = ""
    try:
        import json

        mf = json.loads(manifest.read_text(encoding="utf-8"))
        mesh_mode = str(mf.get("mesh_mode", ""))
    except Exception:
        pass
    if mesh_mode == "gmsh_volume":
        pass
    elif not bmd.exists():
        tags.append("precheck_missing_blockMeshDict")
        issues.append("Missing system/blockMeshDict")
        return _ng(tags, issues)
    tags.append("precheck_cad")
    return _ok(tags, issues)


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

    starter_files = [p for p in rad_files if p.name.endswith("_0000.rad")]
    for starter in starter_files or rad_files:
        text = starter.read_text(encoding="utf-8", errors="replace")
        upper = text.upper()
        for bad in ("/OUTP/", "/H3D/", "/ANIM/ELOUT"):
            if bad in upper:
                tags.append("precheck_engine_block_in_starter")
                issues.append(f"{starter.name}: engine-only block {bad} must not be in starter deck")
        node_ids: set[int] = set()
        in_node = False
        for line in text.splitlines():
            if line.strip().startswith("/NODE"):
                in_node = True
                continue
            if in_node and line.strip().startswith("/"):
                in_node = False
            if in_node:
                parts = line.split()
                if parts and parts[0].isdigit():
                    node_ids.add(int(parts[0]))
        assy_deck = "4MMX4MM_ASSY" in starter.name.upper()
        for m in re.finditer(r"/GRNOD/NODE/(\d+)", text, flags=re.IGNORECASE):
            if assy_deck:
                continue
            gid = int(m.group(1))
            if gid in node_ids and gid >= 10:
                tags.append("precheck_grnod_id_clash")
                issues.append(
                    f"{starter.name}: /GRNOD/NODE/{gid} clashes with node id {gid} (use id>=100 or rename)"
                )

        # INC-094: shell thickness must live in /PROP/SHELL, not as node offset (ERROR 21).
        prop_h: float | None = None
        in_prop = False
        expect_h = False
        expect_hm = False
        expect_thick = False
        for line in text.splitlines():
            if re.match(r"/PROP/SHELL/\d+", line.strip(), flags=re.IGNORECASE):
                in_prop = True
                expect_h = False
                expect_hm = False
                expect_thick = False
                continue
            if in_prop and line.strip().startswith("/"):
                in_prop = False
                expect_h = False
                expect_hm = False
                expect_thick = False
            if not in_prop:
                continue
            if line.strip().startswith("#") and re.search(r"\bhm\b", line, flags=re.IGNORECASE):
                expect_hm = True
                continue
            if line.strip().startswith("#") and re.search(r"\bThick\b", line, flags=re.IGNORECASE):
                expect_thick = True
                continue
            if (expect_h or expect_hm or expect_thick) and prop_h is None:
                parts = line.split()
                if parts:
                    try:
                        if expect_thick and len(parts) >= 3:
                            prop_h = float(parts[2])
                        else:
                            prop_h = float(parts[0])
                        expect_h = False
                        expect_hm = False
                        expect_thick = False
                    except ValueError:
                        pass
        imp_dir: int | None = None
        in_imp = False
        for line in text.splitlines():
            if re.match(r"/IMPDISP/\d+", line.strip(), flags=re.IGNORECASE):
                in_imp = True
                continue
            if in_imp and line.strip().startswith("/"):
                in_imp = False
            if in_imp and imp_dir is None and not line.strip().startswith(("#", "$")):
                parts = line.split()
                if len(parts) >= 4:
                    try:
                        imp_dir = int(parts[2])
                    except ValueError:
                        pass
        node_coords: dict[int, tuple[float, float, float]] = {}
        in_node = False
        for line in text.splitlines():
            if line.strip().startswith("/NODE"):
                in_node = True
                continue
            if in_node and line.strip().startswith("/"):
                in_node = False
            if in_node:
                parts = line.split()
                if len(parts) >= 4 and parts[0].isdigit():
                    node_coords[int(parts[0])] = (
                        float(parts[1]),
                        float(parts[2]),
                        float(parts[3]),
                    )
        if prop_h and prop_h > 0 and node_coords and imp_dir in (1, 2, 3):
            axis = imp_dir - 1
            vals = [c[axis] for c in node_coords.values()]
            spread = max(vals) - min(vals)
            if spread > 1e-6 and abs(spread - prop_h) / prop_h < 0.05:
                tags.append("precheck_shell_thickness_in_geometry")
                issues.append(
                    f"{starter.name}: node spread along punch axis ({spread:.4g} mm) "
                    f"matches PROP thickness ({prop_h:.4g} mm); use mid-surface mesh only"
                )

    if issues:
        return _ng(sorted(set(tags)), issues)

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

