# -*- coding: utf-8 -*-
from __future__ import annotations

import sys
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import json
import math
import random
import sys
import time
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class RunResult:
    artifact_path: str
    runtime_sec: float
    log_text: str
    ok: bool


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _stable_seed(domain: str, difficulty: int, params: dict) -> int:
    key = json.dumps({"domain": domain, "difficulty": difficulty, "params": params}, sort_keys=True)
    h = 2166136261
    for ch in key:
        h ^= ord(ch)
        h = (h * 16777619) & 0xFFFFFFFF
    return int(h)


def run_resin_flow_proxy(out_dir: Path, difficulty: int, params: dict) -> RunResult:
    """Lightweight proxy run that emits measurable KPIs as an artifact JSON.

    Note: This is NOT a real OpenFOAM injection molding simulation. It exists to:
    - generate repeatable artifacts
    - test KPI extraction + pass/fail logic
    - allow difficulty progression without heavy compute
    """
    t0 = time.time()
    seed = _stable_seed("RESIN_FLOW", difficulty, params)
    rng = random.Random(seed)

    mesh = int(params.get("mesh_cells_target", 200000))
    variants = int(params.get("boundary_variants", 3))

    # Proxy metrics: scale with mesh and variants, plus small deterministic noise.
    # Lower is better for all except converged.
    base_fill = 3.0 + 0.15 * (difficulty - 1) + 0.3 * math.log10(max(mesh, 1000) / 200000.0 + 1.0)
    fill_time = max(1.5, base_fill + rng.uniform(-0.25, 0.25))

    base_p = 1.35e8 + (difficulty - 1) * 8.0e6 + 2.0e6 * math.log10(max(mesh, 1000) / 200000.0 + 1.0)
    max_pressure = max(6.0e7, base_p + rng.uniform(-8.0e6, 8.0e6))

    mass_balance = max(0.5, 7.0 - (difficulty - 1) * 1.2 + rng.uniform(-1.2, 1.2))

    # Convergence probability decreases as difficulty rises (proxy).
    conv_roll = rng.random()
    converged = conv_roll > (0.06 + 0.04 * (difficulty - 1) + 0.005 * max(0, variants - 3))

    artifact = {
        "domain": "RESIN_FLOW",
        "difficulty": difficulty,
        "params": params,
        "kpi_values": {
            "kpi_converged": bool(converged),
            "kpi_fill_time_sec": float(fill_time),
            "kpi_max_pressure_pa": float(max_pressure),
            "kpi_mass_balance_err_pct": float(mass_balance),
        },
        "notes": "proxy_run_v1",
    }
    artifact_path = out_dir / "resin_flow_proxy.json"
    _write_json(artifact_path, artifact)

    runtime = time.time() - t0
    log = f"RESIN_FLOW proxy: converged={converged} fill_time={fill_time:.3f}s maxP={max_pressure:.1f}Pa mass_err={mass_balance:.2f}%"
    return RunResult(artifact_path=str(artifact_path), runtime_sec=float(runtime), log_text=log, ok=bool(converged))


def run_progressive_die_proxy(out_dir: Path, difficulty: int, params: dict) -> RunResult:
    """Lightweight proxy run that emits measurable KPIs as an artifact JSON."""
    t0 = time.time()
    seed = _stable_seed("PROGRESSIVE_DIE", difficulty, params)
    rng = random.Random(seed)

    mesh_size = float(params.get("mesh_shell_size_mm", 6.0))
    steps = int(params.get("process_steps", 2))

    # Proxy metrics (lower is better): thinning, wrinkling risk, springback, force.
    thinning = max(8.0, 18.0 + 2.8 * (difficulty - 1) + rng.uniform(-3.0, 3.0))
    wrinkling = min(1.0, max(0.05, 0.35 + 0.08 * (difficulty - 1) + rng.uniform(-0.08, 0.08)))
    springback = max(0.2, 1.2 + 0.25 * (difficulty - 1) + 0.08 * math.log(max(1.0, 6.0 / max(0.5, mesh_size))) + rng.uniform(-0.12, 0.12))
    force = max(50.0, 180.0 + 40.0 * (difficulty - 1) + 10.0 * math.log(max(1, steps)) + rng.uniform(-25.0, 25.0))

    conv_roll = rng.random()
    converged = conv_roll > (0.05 + 0.05 * (difficulty - 1) + 0.01 * max(0, steps - 2))

    artifact = {
        "domain": "PROGRESSIVE_DIE",
        "difficulty": difficulty,
        "params": params,
        "kpi_values": {
            "kpi_converged": bool(converged),
            "kpi_thinning_max_pct": float(thinning),
            "kpi_wrinkling_risk_score": float(wrinkling),
            "kpi_springback_mm": float(springback),
            "kpi_press_force_kn_peak": float(force),
        },
        "notes": "proxy_run_v1",
    }
    artifact_path = out_dir / "progressive_die_proxy.json"
    _write_json(artifact_path, artifact)

    runtime = time.time() - t0
    log = f"PROGRESSIVE_DIE proxy: converged={converged} thinning={thinning:.2f}% wrinkle={wrinkling:.3f} springback={springback:.3f}mm force={force:.1f}kN"
    return RunResult(artifact_path=str(artifact_path), runtime_sec=float(runtime), log_text=log, ok=bool(converged))


def _part_geometry_contract_module():
    apps = Path(__file__).resolve().parent / "apps" / "dxf2step"
    apps_str = str(apps)
    if apps_str not in sys.path:
        sys.path.insert(0, apps_str)
    import part_geometry_contract as pgc

    return pgc


def _load_part_manifest_from_params(params: dict) -> tuple[dict | None, str | None]:
    inline = params.get("part_manifest")
    if isinstance(inline, dict):
        return inline, params.get("part_manifest_path") or params.get("manifest_path")
    manifest_path = params.get("part_manifest_path") or params.get("manifest_path")
    if not manifest_path:
        return None, None
    pgc = _part_geometry_contract_module()
    manifest = pgc.load_part_manifest(manifest_path)
    return manifest, str(manifest_path)


def run_tolerance_analysis_proxy(out_dir: Path, difficulty: int, params: dict) -> RunResult:
    """CETOL-style 1D stack-up (theory pack + tolerance_stackup_engine)."""
    t0 = time.time()
    chain_len = int(params.get("chain_length", 3))
    gdt_features = int(params.get("gdt_feature_count", 2))
    include_gdt = str(params.get("include_gdt", "1")).strip().lower() not in ("0", "false", "no")
    spec_limit_mm = float(params.get("spec_limit_mm", 0.5))
    nominal_gap_mm = float(params.get("nominal_gap_mm", 0.2))
    per_dim_tol = 0.04 + 0.02 * (difficulty - 1)
    dim_source = "synthetic"
    part_manifest, manifest_path = _load_part_manifest_from_params(params)

    use_l10 = str(params.get("tolerance_l10", "1")).strip().lower() not in ("0", "false", "no")
    dims: list = []
    stack: dict = {}
    engine_note = "tolerance_stackup_engine.v1"

    try:
        if use_l10 and part_manifest:
            import tolerance_l10_assembly as l10

            lsl = nominal_gap_mm - spec_limit_mm / 2.0
            usl = nominal_gap_mm + spec_limit_mm / 2.0
            stack = l10.analyze_l10_assembly_from_manifest(
                part_manifest,
                nominal_target=nominal_gap_mm,
                lsl=lsl,
                usl=usl,
                n=50_000,
                include_gdt=include_gdt,
            )
            dim_source = "measured"
            dims = stack.get("dimensions") or []
            gdt_n = sum(1 for d in dims if str(d.get("source", "")).startswith("gdt"))
            print(
                f"[tolerance] L10 assembly dims={len(dims)} gdt_dims={gdt_n} "
                f"maturity={stack.get('maturity_level')} factory_kpi={(stack.get('factory_kpi') or {}).get('verdict')}",
                flush=True,
            )
            engine_note = "tolerance_l10_assembly.v1"
        else:
            import tolerance_stackup_engine as tse

            tse_dims: list[tse.StackDimension] = []
            if part_manifest:
                pgc = _part_geometry_contract_module()
                spec_rows = pgc.merged_tolerance_dims(
                    part_manifest,
                    difficulty=difficulty,
                    default_tol=per_dim_tol,
                    include_gdt=include_gdt,
                )
                if spec_rows:
                    tse_dims = [
                        tse.StackDimension(
                            name=str(row["name"]),
                            mean=float(row["mean"]),
                            tolerance=float(row["tolerance"]),
                            coef=float(row.get("coef") or 1.0),
                            distribution=str(row.get("distribution") or "normal"),
                            source=str(row.get("source") or "measured"),
                        )
                        for row in spec_rows
                    ]
                    dim_source = "measured"
                    gdt_n = sum(1 for r in spec_rows if str(r.get("source", "")).startswith("gdt"))
                    print(
                        f"[tolerance] manifest dims: {[d.name for d in tse_dims]} "
                        f"geometry_source=measured gdt_dims={gdt_n} include_gdt={include_gdt}",
                        flush=True,
                    )
                else:
                    print(
                        "[tolerance] WARN manifest has no usable nominal dims; fallback synthetic",
                        flush=True,
                    )
            elif manifest_path:
                print(
                    f"[tolerance] WARN manifest invalid or missing at {manifest_path}; fallback synthetic",
                    flush=True,
                )

            if not tse_dims:
                tse_dims = [
                    tse.StackDimension(
                        f"dim_{i}",
                        0.0,
                        per_dim_tol,
                        1.0 if i % 2 == 0 else -1.0,
                        source="synthetic",
                    )
                    for i in range(max(chain_len, 2))
                ]

            lsl = nominal_gap_mm - spec_limit_mm / 2.0
            usl = nominal_gap_mm + spec_limit_mm / 2.0
            stack = tse.analyze_stack(tse_dims, nominal_target=nominal_gap_mm, lsl=lsl, usl=usl, n=50_000)
            if part_manifest:
                pgc = _part_geometry_contract_module()
                stack["maturity_level"] = pgc.detect_maturity_level(part_manifest, include_gdt=include_gdt)
            else:
                stack["maturity_level"] = "L2_gdt_proxy" if include_gdt else "L1_nominal_only"
            stack["gdt_included"] = include_gdt
            dims = tse_dims
            engine_note = "tolerance_stackup_engine.v1"

        mc = stack.get("monte_carlo") or {}
        within_spec = bool(stack.get("within_spec_mc") or stack.get("within_spec_worst_case"))
        worst_case_gap = float(stack.get("worst_case_stack_mm", 0)) + nominal_gap_mm
        utility = min(100.0, max(0.0, float(mc.get("yield_rate", 0) or 0) * 100.0))
    except Exception as exc:
        print(f"[tolerance] engine error: {exc}; fallback proxy", flush=True)
        seed = _stable_seed("TOLERANCE_ANALYSIS", difficulty, params)
        rng = random.Random(seed)
        rss = math.sqrt(chain_len * gdt_features) * per_dim_tol
        worst_case_gap = nominal_gap_mm + rss + rng.uniform(-0.02, 0.04)
        within_spec = worst_case_gap <= spec_limit_mm
        margin = max(0.0, spec_limit_mm - worst_case_gap)
        utility = min(100.0, max(0.0, 40.0 + 120.0 * (margin / max(spec_limit_mm, 0.01)) - 8.0 * (difficulty - 1)))
        stack = {}
        engine_note = "tolerance_proxy_fallback"
        dim_source = "synthetic"

    animation_frames = int(params.get("animation_frames_target", 12 + 8 * difficulty))
    freecad_linked = bool(params.get("freecad_integration", True))

    artifact = {
        "domain": "TOLERANCE_ANALYSIS",
        "difficulty": difficulty,
        "params": params,
        "geometry_source": dim_source,
        "part_manifest_path": manifest_path,
        "part_id": (part_manifest or {}).get("source_dxf") if part_manifest else None,
        "stack_analysis": stack,
        "factory_kpi": (stack.get("factory_kpi") if isinstance(stack, dict) else None),
        "kpi_values": {
            "kpi_within_spec": bool(within_spec),
            "kpi_worst_case_gap_mm": float(worst_case_gap),
            "kpi_spec_limit_mm": float(spec_limit_mm),
            "kpi_chain_length": int(chain_len),
            "kpi_gdt_feature_count": int(
                sum(
                    1
                    for d in dims
                    if str(
                        d.get("source") if isinstance(d, dict) else getattr(d, "source", "")
                    ).startswith("gdt")
                )
                if dims
                else gdt_features
            ),
            "kpi_include_gdt": bool(include_gdt),
            "kpi_animation_frames": int(animation_frames),
            "kpi_freecad_linked": bool(freecad_linked),
            "kpi_factory_utility_pct": float(utility),
            "kpi_dims_measured": dim_source == "measured",
        },
        "roadmap": {
            "target": "Cetol6Sigma-like: 3D + GD&T + FreeCAD + animation",
            "reference_protocol": "clawstack_v2/docs/knowledge/tolerance_analysis_protocol.md",
        },
        "notes": engine_note,
    }
    artifact_path = out_dir / "tolerance_analysis_proxy.json"
    _write_json(artifact_path, artifact)

    runtime = time.time() - t0
    log = (
        f"TOLERANCE_ANALYSIS proxy: within_spec={within_spec} gap={worst_case_gap:.4f}mm "
        f"limit={spec_limit_mm:.4f}mm utility={utility:.1f}% anim_frames={animation_frames}"
    )
    return RunResult(artifact_path=str(artifact_path), runtime_sec=float(runtime), log_text=log, ok=bool(within_spec))


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Growth domain runners (CLI)")
    parser.add_argument("--domain", required=True, help="RESIN_FLOW | PROGRESSIVE_DIE | TOLERANCE_ANALYSIS")
    parser.add_argument("--manifest", help="part_manifest.json path (TOLERANCE_ANALYSIS)")
    parser.add_argument("--out-dir", default=".", help="Output directory for artifact JSON")
    parser.add_argument("--difficulty", type=int, default=1)
    args = parser.parse_args()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    params: dict = {}
    if args.manifest:
        params["part_manifest_path"] = str(Path(args.manifest).resolve())

    domain = args.domain.upper()
    if domain == "TOLERANCE_ANALYSIS":
        result = run_tolerance_analysis_proxy(out_dir, args.difficulty, params)
    elif domain == "RESIN_FLOW":
        result = run_resin_flow_proxy(out_dir, args.difficulty, params)
    elif domain == "PROGRESSIVE_DIE":
        result = run_progressive_die_proxy(out_dir, args.difficulty, params)
    else:
        parser.error(f"Unknown domain: {args.domain}")
        return 2

    print(result.log_text)
    print(f"artifact={result.artifact_path} ok={result.ok}")
    return 0 if result.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
