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

import sys

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

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


def _read_text_if_exists(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="replace")


def _unresolved_placeholders(case_dir: Path, rel_paths: tuple[str, ...]) -> list[str]:
    bad: list[str] = []
    placeholder_re = re.compile(r"\b[A-Z][A-Z0-9_]*_PLACEHOLDER\b|PACK_P_GAUGE_PA")
    for rel in rel_paths:
        text = _read_text_if_exists(case_dir / rel)
        for match in placeholder_re.finditer(text):
            bad.append(f"{rel}:{match.group(0)}")
    return bad


def _nonuniform_field_size(path: Path) -> int | None:
    text = _read_text_if_exists(path)
    m = re.search(r"internalField\s+nonuniform\s+List<scalar>\s+(\d+)\s*\(", text, flags=re.S)
    if not m:
        return None
    try:
        return int(m.group(1))
    except ValueError:
        return None


def _blockmesh_cell_count(case_dir: Path) -> int | None:
    text = _read_text_if_exists(case_dir / "system" / "blockMeshDict")
    counts = re.findall(r"\(\s*(\d+)\s+(\d+)\s+(\d+)\s*\)\s+simpleGrading", text)
    if not counts:
        return None
    total = 0
    for nx, ny, nz in counts:
        total += int(nx) * int(ny) * int(nz)
    return total


def _initial_temperature_values(case_dir: Path) -> list[float]:
    text = _read_text_if_exists(case_dir / "0" / "T")
    values: list[float] = []
    for match in re.finditer(r"uniform\s+([-+0-9.eE]+)\s*;", text):
        try:
            values.append(float(match.group(1)))
        except ValueError:
            pass
    return values


def precheck_moldflow_cad_cooling_case(case_dir: Path, manifest: dict | None = None) -> PreGateResult:
    """Additional generated-CAD structure checks for resin_fill_cool before parameter injection."""
    tags: list[str] = ["precheck_cad_cool"]
    issues: list[str] = []

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

    expected_cells = _blockmesh_cell_count(case_dir)
    alpha_cells = _nonuniform_field_size(case_dir / "0" / "alpha.polymer")
    if alpha_cells is not None and expected_cells is not None and alpha_cells != expected_cells:
        tags.append("precheck_stale_alpha_cell_count")
        issues.append(f"0/alpha.polymer has {alpha_cells} values but blockMesh expects {expected_cells} cells")

    if manifest and str(manifest.get("physics_category", "")) == "resin_fill_cool":
        pass

    if len(tags) > 1:
        return _ng(tags, issues)
    return _ok(["precheck_ok", "precheck_cad_cool"], [])


def precheck_openfoam_injected_cooling_case(case_dir: Path) -> PreGateResult:
    """Runtime safety checks for resin_fill_cool after placeholders are injected."""
    tags: list[str] = ["precheck_cad_cool_runtime"]
    issues: list[str] = []

    unresolved = _unresolved_placeholders(
        case_dir,
        (
            "0/T",
            "0/p",
            "0/p_rgh",
            "constant/thermophysicalProperties.polymer",
            "constant/thermophysicalProperties.air",
            "system/controlDict",
            "system/controlDict.ascii",
        ),
    )
    if unresolved:
        tags.append("precheck_unresolved_cooling_placeholders")
        issues.append("Unresolved cooling placeholders: " + ", ".join(unresolved[:8]))

    temps = _initial_temperature_values(case_dir)
    if not temps:
        tags.append("precheck_missing_numeric_temperature")
        issues.append("0/T must contain at least one numeric uniform temperature after injection")
    elif min(temps) <= 0 or max(temps) > 800:
        tags.append("precheck_invalid_temperature_range")
        issues.append(f"0/T contains out-of-range temperatures: min={min(temps):.2f}, max={max(temps):.2f} K")

    poly_text = _read_text_if_exists(case_dir / "constant" / "thermophysicalProperties.polymer")
    mu_match = re.search(r"\bmu\s+([-+0-9.eE]+)\s*;", poly_text)
    if not mu_match:
        tags.append("precheck_thermo_missing_mu")
        issues.append("thermophysicalProperties.polymer must contain numeric mu")
    else:
        mu = float(mu_match.group(1))
        if mu <= 0 or mu > 100.0:
            tags.append("precheck_thermo_mu_out_of_demo_range")
            issues.append(f"polymer mu={mu:g} Pa*s is outside safe generated-demo range (0, 100]")

    solution_text = _read_text_if_exists(case_dir / "system" / "fvSolution")
    relaxation_match = re.search(
        r"\brelaxationFactors\b[\s\S]*?\bequations\b[\s\S]*?\bT\s+([-+0-9.eE]+)\s*;",
        solution_text,
    )
    if not relaxation_match:
        tags.append("precheck_missing_temperature_relaxation")
        issues.append("system/fvSolution must define an equation relaxation factor for T")
    else:
        relaxation = float(relaxation_match.group(1))
        if not 0.0 < relaxation <= 1.0:
            tags.append("precheck_invalid_temperature_relaxation")
            issues.append(f"temperature relaxation factor invalid: T={relaxation:g}")

    expected_cells = _blockmesh_cell_count(case_dir)
    alpha_cells = _nonuniform_field_size(case_dir / "0" / "alpha.polymer")
    if alpha_cells is not None and expected_cells is not None and alpha_cells != expected_cells:
        tags.append("precheck_stale_alpha_cell_count")
        issues.append(f"0/alpha.polymer has {alpha_cells} values but blockMesh expects {expected_cells} cells")

    if len(tags) > 1:
        return _ng(tags, issues)
    return _ok(["precheck_ok", "precheck_cad_cool_runtime"], [])


def precheck_moldflow_cad_case(case_dir: Path) -> PreGateResult:
    """Phase 7: CAD-built case (cad_manifest.json + interFoam VOF)."""
    manifest = case_dir / "cad_manifest.json"
    if not manifest.exists():
        return _ng(
            ["precheck_missing_cad_manifest"],
            ["Missing cad_manifest.json (run moldflow_step_case_builder)"],
        )
    mesh_mode = ""
    manifest_data: dict = {}
    try:
        import json

        manifest_data = json.loads(manifest.read_text(encoding="utf-8"))
        mesh_mode = str(manifest_data.get("mesh_mode", ""))
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
    if str(manifest_data.get("physics_category", "")) == "resin_fill_cool":
        cool = precheck_moldflow_cad_cooling_case(case_dir, manifest_data)
        if not cool.ok:
            return cool
        tags.extend([t for t in cool.tags if t != "precheck_ok"])
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
    # Startup normally reports that exception trapping is enabled. That is
    # informational and must not be classified as a solver crash.
    if re.search(r"(?im)^(?!.*\btrapping\b).*Floating point exception", t):
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


OPENRADIOSS_ASSY_MIN_T_MS = 18.13
OPENRADIOSS_ASSY_MAX_DELETED_ELEMENTS = 8000
OPENRADIOSS_ASSY_MAX_VELOCITY_WARNINGS = 40
# T060: 8連敗の主因=質量スケーリング暴走(DM/M 36-62倍)を直接検出するゲート。
# 健全な explicit 解析は DM/M < 2-5% が目安。10%超は動力学が汚染されているとみなす。
OPENRADIOSS_ASSY_MAX_DM_M = 0.10
OPENRADIOSS_ASSY_MIN_ERR_PCT = -85.0
OPENRADIOSS_HARD_FAIL_TAGS = frozenset(
    {
        "radioss_abnormal_termination",
        "radioss_velocity_too_high",
        "radioss_time_step_issue",
        "mesh_negative_volume",
        "radioss_unit_issue",
    }
)
OPENRADIOSS_BLANKING_CATEGORIES = frozenset(
    {"press_blanking", "press_blanking_stripper", "press_blanking_assy"}
)


def parse_openradioss_run_metrics(log_text: str) -> dict:
    """Parse final time, termination class, and coarse failure signals from engine log."""
    t = log_text or ""
    upper = t.upper()
    out: dict = {
        "velocity_high_count": 0,
        "velocity_warning_count": 0,
        "failure_start_count": 0,
        "deleted_element_events": 0,
        "total_deleted_elements": 0,
        "termination": "UNKNOWN",
    }
    nc_lines = re.findall(
        r"NC=\s*(\d+)\s+T=\s*([\d.E+\-]+)\s+DT=[^\n]*?ERR=\s*([-\d.]+)%[^\n]*?DM/M=\s*([\d.E+\-]+)",
        t,
        flags=re.IGNORECASE,
    )
    if not nc_lines:
        for line in t.splitlines():
            match = re.match(
                r"^\s*(\d+)\s+([\d.E+\-]+)\s+([\d.E+\-]+)\s+\S+\s+\d+\s+([-\d.]+)%\s+(.+)$",
                line,
            )
            if not match:
                continue
            tail_values = match.group(5).split()
            if len(tail_values) < 3:
                continue
            nc_lines.append(
                (
                    match.group(1),
                    match.group(2),
                    match.group(4),
                    tail_values[-3],
                )
            )
    if nc_lines:
        nc, tval, err_pct, dm_m = nc_lines[-1]
        out["nc_final"] = int(nc)
        out["t_final_ms"] = float(tval) * 1000.0
        try:
            out["last_err_pct"] = float(err_pct)
            out["last_dm_m"] = float(dm_m)
        except ValueError:
            pass
        # Blanking intentionally deletes material after fracture starts. Energy
        # error after that topology change is not a forming-stability KPI, so
        # retain the last cycle immediately before the first failure event.
        failure_times = re.findall(
            r"FAILURE START AT TIME:\s*([\d.E+\-]+)",
            t,
            flags=re.IGNORECASE,
        )
        if failure_times:
            try:
                first_failure_time = min(float(value) for value in failure_times)
                out["first_failure_time_ms"] = first_failure_time * 1000.0
                stable_cutoff = 0.99 * first_failure_time
                for nc_w, tv_w, err_w, dm_w in reversed(nc_lines):
                    if float(tv_w) <= stable_cutoff:
                        out["err_pct_pre_failure"] = float(err_w)
                        out["dm_m_pre_failure"] = float(dm_w)
                        out["t_pre_failure_ms"] = float(tv_w) * 1000.0
                        out["nc_pre_failure"] = int(nc_w)
                        break
            except ValueError:
                pass
        # T064-gates (2026-07-15): energy error evaluated inside the forming
        # window (<= 90% of reached time). After full slug separation the ERR
        # column loses physical meaning for blanking; final-cycle ERR produced
        # false FAILs on otherwise healthy runs.
        try:
            t_last = float(tval)
            cutoff = 0.9 * t_last
            for nc_w, tv_w, err_w, _dm_w in reversed(nc_lines):
                if float(tv_w) <= cutoff:
                    out["err_pct_at_90"] = float(err_w)
                    out["t_at_90_ms"] = float(tv_w) * 1000.0
                    out["nc_at_90"] = int(nc_w)
                    break
        except ValueError:
            pass
    out["velocity_high_count"] = len(
        re.findall(r"NODAL VELOCITY IS TOO HIGH", upper)
    )
    out["velocity_warning_count"] = len(
        re.findall(r"NODAL VELOCITY MAY BE TOO HIGH", upper)
    )
    out["failure_start_count"] = len(re.findall(r"FAILURE START AT TIME", upper))
    out["deleted_element_events"] = len(
        re.findall(r"ELEMENTS?\s+DELETED|ELEMENT\s+DELETED", upper)
    )
    deleted_totals: list[int] = []
    for pat in (
        r"(\d+)\s+ELEMENTS?\s+(?:HAVE BEEN\s+)?DELETED",
        r"NUMBER OF DELETED ELEMENTS\s*[=:]\s*(\d+)",
        r"TOTAL NUMBER OF DELETED ELEMENTS\s*[=:]\s*(\d+)",
        r"(\d+)\s+ELEMENTS?\s+DELETED DUE TO",
    ):
        for m in re.finditer(pat, upper):
            try:
                deleted_totals.append(int(m.group(1)))
            except ValueError:
                pass
    if deleted_totals:
        out["total_deleted_elements"] = max(deleted_totals)
    if "NORMAL TERMINATION" in upper:
        out["termination"] = (
            "NORMAL_VELOCITY" if out["velocity_high_count"] > 0 else "NORMAL_TSTOP"
        )
    elif "ABNORMAL TERMINATION" in upper:
        out["termination"] = "ABNORMAL"
    elif "ERROR TERMINATION" in upper or "ERROR TERMINATION" in t:
        out["termination"] = "ERROR"
    return out


def apply_openradioss_meaning_gate(
    *,
    verdict: str,
    category: str,
    exp: dict,
    log_text: str,
    failure_tags: list[str],
    defects: dict,
    kpi_values: dict | None,
) -> tuple[str, dict, list[str]]:
    """Fail-closed North Star gate for OpenRadioss blanking (no cosmetic SUCCESS)."""
    reasons: list[str] = []
    metrics = parse_openradioss_run_metrics(log_text)
    defects = dict(defects or {})
    defects["run_metrics"] = metrics
    defects["kpi_source"] = defects.get("kpi_source") or "none"

    tag_set = set(failure_tags or [])
    hard_hits = sorted(tag_set & OPENRADIOSS_HARD_FAIL_TAGS)
    if hard_hits:
        reasons.append(f"hard_fail_tags:{','.join(hard_hits)}")

    if metrics.get("velocity_high_count", 0) > 0:
        reasons.append(f"nodal_velocity_high_count={metrics['velocity_high_count']}")
    if metrics.get("termination") == "ABNORMAL":
        reasons.append("abnormal_termination")
    if metrics.get("termination") == "ERROR":
        reasons.append("error_termination")
    if metrics.get("termination") == "NORMAL_VELOCITY":
        reasons.append("normal_termination_but_velocity_stop")

    mesh_events = int(metrics.get("failure_start_count") or 0) + int(
        metrics.get("deleted_element_events") or 0
    )
    total_deleted = int(metrics.get("total_deleted_elements") or 0)
    if total_deleted > 0:
        defects["solver_eliminated_elements"] = total_deleted
    elif mesh_events > 0:
        defects["solver_mesh_failure_events"] = mesh_events

    is_assy = bool(exp.get("assy_deck")) or category == "press_blanking_assy"
    gate_cfg = exp.get("meaning_gate") if isinstance(exp.get("meaning_gate"), dict) else {}
    max_deleted = int(
        gate_cfg.get("max_deleted_elements")
        if gate_cfg.get("max_deleted_elements") is not None
        else (OPENRADIOSS_ASSY_MAX_DELETED_ELEMENTS if is_assy else 500)
    )
    if total_deleted > max_deleted:
        reasons.append(f"total_deleted_elements={total_deleted}>{max_deleted}")
    elif not is_assy and mesh_events > 3:
        reasons.append(f"mesh_failure_events={mesh_events}")

    vel_warn = int(metrics.get("velocity_warning_count") or 0)
    if is_assy and vel_warn > OPENRADIOSS_ASSY_MAX_VELOCITY_WARNINGS:
        reasons.append(f"velocity_warning_count={vel_warn}")
    # T064-gates (2026-07-15): gate on ERR inside the forming window (90% of
    # reached time) instead of the final cycle; post-separation ERR is not a
    # valid health signal for blanking. Falls back to last_err_pct when the
    # windowed value is unavailable (short/failed runs).
    err_gate_val = metrics.get(
        "err_pct_pre_failure",
        metrics.get("err_pct_at_90", metrics.get("last_err_pct")),
    )
    if is_assy and err_gate_val is not None and float(err_gate_val) < OPENRADIOSS_ASSY_MIN_ERR_PCT:
        reasons.append(
            f"forming_window_err_pct={float(err_gate_val):.1f}<{OPENRADIOSS_ASSY_MIN_ERR_PCT}"
        )
    last_dm = metrics.get("last_dm_m")
    if is_assy and last_dm is not None and float(last_dm) > OPENRADIOSS_ASSY_MAX_DM_M:
        reasons.append(f"last_dm_m={float(last_dm):.3f}>{OPENRADIOSS_ASSY_MAX_DM_M} (mass_scaling_runaway)")

    min_t = float(
        gate_cfg.get("min_t_final_ms")
        or (OPENRADIOSS_ASSY_MIN_T_MS if is_assy else 5.0)
    )
    t_final = metrics.get("t_final_ms")
    if is_assy:
        if t_final is None:
            reasons.append("missing_t_final_ms")
        elif float(t_final) < min_t:
            reasons.append(f"t_final_ms={float(t_final):.3f}<{min_t}")
        if metrics.get("termination") != "NORMAL_TSTOP":
            reasons.append(f"termination={metrics.get('termination')}")

    if category in OPENRADIOSS_BLANKING_CATEGORIES:
        has_real_kpi = bool(kpi_values)
        if defects.get("shear_zone_pct") and not has_real_kpi:
            defects["kpi_source"] = "parametric_estimate"
            reasons.append("shear_kpi_parametric_only")
        elif has_real_kpi:
            defects["kpi_source"] = "solver_or_geometry"

    if reasons and verdict in ("SUCCESS", "UNKNOWN"):
        return "FAILED_MEANING_GATE", defects, reasons
    return verdict, defects, reasons


def tag_openradioss_log(text: str) -> list[str]:
    """Coarse failure tags from OpenRadioss logs (starter/engine)."""
    t = text or ""
    tags: set[str] = set()

    upper = t.upper()
    if "ABNORMAL TERMINATION" in upper:
        tags.add("radioss_abnormal_termination")
    if "NORMAL TERMINATION" in upper:
        tags.add("radioss_normal_termination")
    # T064-gates (2026-07-15): error tags are line-scoped. The previous
    # whole-log substring pairing ("UNIT" anywhere + "ERROR" anywhere) fired on
    # every engine log ("UNIT SYSTEM" header + "ENERGY ERROR" summary), making
    # radioss_unit_issue a permanent false hard-fail (8-loss streak on 07-14).
    error_line_re = re.compile(r"(?:\*\*+\s*ERROR|\bERROR\s+(?:ID\b|TERMINATION\b|\d+)|^\s*ERROR\b)")
    error_lines = [ln for ln in upper.splitlines() if error_line_re.search(ln)]
    if error_lines:
        tags.add("radioss_error")
        if any("CONTACT" in ln or "INTERFACE" in ln for ln in error_lines):
            tags.add("radioss_contact_issue")
        if any("UNIT" in ln for ln in error_lines):
            tags.add("radioss_unit_issue")
    if "NODAL VELOCITY IS TOO HIGH" in upper:
        tags.add("radioss_velocity_too_high")
    if re.search(
        r"(?:WARNING|ERROR)[^\n]*TIME[ -]?STEP|TIME[ -]?STEP\s+(?:IS\s+)?TOO SMALL|DT[^\n]*TOO SMALL",
        upper,
    ):
        tags.add("radioss_time_step_issue")
    if "NEGATIVE VOLUME" in upper:
        tags.add("mesh_negative_volume")

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
