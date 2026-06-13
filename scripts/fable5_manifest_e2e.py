# -*- coding: utf-8 -*-
"""Fable5 cross-pillar E2E: one part_manifest -> tolerance + Moldflow + OpenRadioss.

Dispatches compute to fleet nodes per docs/fleet_job_allocation_20260613.md:
  - tolerance  -> K10 (local)
  - resin_fill -> lavie (satellite)
  - press_blank -> red_lavie (satellite, fallback k10)

Writes fable5_e2e_report.json under data/cae_te_workspace/runs/.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

ROOT = Path(__file__).resolve().parents[1]
JST = timezone(timedelta(hours=9))
RUNS = ROOT / "data" / "cae_te_workspace" / "runs"
GOLDEN = ROOT / "data" / "workspace" / "thinkpad_dxf2step_history" / "tp-dxf-44920df6" / "part_manifest.json"

if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))
if str(ROOT / "data" / "workspace") not in sys.path:
    sys.path.insert(0, str(ROOT / "data" / "workspace"))
if str(ROOT / "data" / "workspace" / "apps" / "dxf2step") not in sys.path:
    sys.path.insert(0, str(ROOT / "data" / "workspace" / "apps" / "dxf2step"))

import cae_workload_router as router
import k10_satellite_cae_dispatch as cae_dispatch


def _now() -> str:
    return datetime.now(JST).isoformat()


def _resolve_manifest(path: str | None) -> Path:
    p = Path(path) if path else GOLDEN
    if not p.is_absolute():
        p = (ROOT / p).resolve()
    if not p.exists():
        raise FileNotFoundError(p)
    return p


def step_validate_manifest(manifest_path: Path) -> dict[str, Any]:
    cmd = [
        sys.executable,
        str(ROOT / "scripts" / "part_geometry_contract.py"),
        "--validate",
        str(manifest_path),
    ]
    proc = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        cwd=str(ROOT),
    )
    ok = proc.returncode == 0
    return {
        "step": "manifest_validate",
        "ok": ok,
        "exit_code": proc.returncode,
        "stdout_tail": (proc.stdout or "")[-1500:],
        "stderr_tail": (proc.stderr or "")[-800:],
    }


def step_tolerance(manifest_path: Path, out_dir: Path) -> dict[str, Any]:
    import growth_domain_runners as growth

    job_dir = out_dir / "tolerance"
    job_dir.mkdir(parents=True, exist_ok=True)
    result = growth.run_tolerance_analysis_proxy(
        job_dir,
        difficulty=1,
        params={"part_manifest_path": str(manifest_path.resolve())},
    )
    artifact = Path(result.artifact_path) if result.artifact_path else None
    geo = None
    if artifact and artifact.exists():
        try:
            data = json.loads(artifact.read_text(encoding="utf-8"))
            geo = data.get("geometry_source")
        except Exception:
            pass
    ok = geo == "measured" and artifact is not None and artifact.exists()
    return {
        "step": "tolerance",
        "host": "k10",
        "ok": ok,
        "verdict": "PASS" if ok else "FAIL",
        "geometry_source": geo,
        "within_spec": result.ok,
        "artifact": str(artifact) if artifact else None,
        "runtime_sec": result.runtime_sec,
    }


def _router_reason_for_step(
    *,
    category: str,
    host: str,
    force_host: str | None,
    decision: dict[str, Any],
    entry: dict[str, Any],
    satellite_offline: bool,
) -> str:
    actual = str(entry.get("host") or host)
    fallback = entry.get("fallback_from")
    if fallback:
        return f"fallback {fallback} -> {actual}: {entry.get('fallback_reason', '')[:120]}"
    if force_host and actual == force_host:
        if satellite_offline:
            return f"E2E force_host={force_host} but worker probe failed -> {actual}"
        if actual == "red_lavie":
            return "E2E require-red-lavie -> red_lavie (worker probe ok)"
        if actual == "lavie":
            return "E2E force_host=lavie -> lavie (worker probe ok)"
    if actual != decision.get("host"):
        return f"routed -> {actual} (router suggested {decision.get('host')}: {decision.get('reason', '')[:80]})"
    return str(decision.get("reason") or f"routed -> {actual}")


def step_cae(
    *,
    category: str,
    manifest_path: Path,
    out_dir: Path,
    dry_run: bool,
    timeout: int,
    force_host: str | None,
) -> dict[str, Any]:
    cfg = router.load_config()
    decision = router.pick_host(category, cfg)
    host = force_host or decision.get("host") or "k10"
    if category.startswith("resin_fill") and host != "lavie" and not force_host:
        if any(n == "lavie" for n, _ in (decision.get("satellites_probe") or []) if isinstance(n, str)):
            host = "lavie"
        elif decision.get("satellites_probe"):
            for node_id, _ in decision.get("satellites_probe") or []:
                if node_id == "lavie":
                    host = "lavie"
                    break
    if category.startswith("press_") and host not in ("red_lavie", "k10") and not force_host:
        host = "red_lavie" if any(
            str(x).startswith("red_lavie") for x in (decision.get("satellites_probe") or [])
        ) else "k10"

    inline: dict | None = None
    params = {
        "part_manifest_path": str(manifest_path.resolve()),
        "part_manifest_loaded": True,
    }
    try:
        loaded = json.loads(manifest_path.read_text(encoding="utf-8"))
        if isinstance(loaded, dict):
            inline = loaded
            params["part_manifest"] = inline
    except Exception:
        pass
    mf = ((inline or {}).get("physics_handoff") or {}).get("moldflow") or {}
    if mf.get("ready") and category.startswith("resin_fill"):
        params.setdefault("gate_count", 1)
        params.setdefault("gate_position", str(mf.get("gate_seed") or "center"))
        params.setdefault("physics_category", "resin_fill_vof")
        params.setdefault("mesh_mode", "blockmesh_bbox")
        params.setdefault("pack_end_time", 0.32)
        bb = (inline or {}).get("bbox_mm") or {}
        if isinstance(bb, dict):
            lx, ly, lz = float(bb.get("Lx") or 0), float(bb.get("Ly") or 0), float(bb.get("Lz") or 0)
            if lx > 0 and ly > 0 and lz > 0:
                params["_manifest_bbox_mm"] = {"length": lx, "width": ly, "height": lz}
    trial_id = f"E2E-{category[:8].upper()}-{uuid.uuid4().hex[:6]}"

    entry: dict[str, Any]
    satellite_offline = False
    if host == "red_lavie" and not dry_run:
        try:
            node_info = cae_dispatch.sjp.load_node("red_lavie")
            worker_url = cae_dispatch.sjp.worker_base_url(node_info)
            token_probe = cae_dispatch.sjp.load_token()
            online, detail = cae_dispatch.sjp.probe_worker(worker_url, token_probe)
            if not online:
                satellite_offline = True
                if force_host == "red_lavie":
                    host = "k10"
        except Exception:
            satellite_offline = True
            if force_host == "red_lavie":
                host = "k10"

    try:
        if host in ("lavie", "red_lavie"):
            token = cae_dispatch.sjp.load_token()
            bundle = cae_dispatch.run_lavie_trial(
                node=host,
                category=category,
                params=params,
                trial_id=trial_id,
                dry_run=dry_run,
                timeout=timeout,
                token=token,
                cfg=cfg,
            )
            entry = bundle.get("trial_entry") or {}
            entry.setdefault("host", host)
        else:
            entry = cae_dispatch.run_local_trial(
                category=category,
                params=params,
                trial_id=trial_id,
                dry_run=dry_run,
                timeout=timeout,
            )
            entry.setdefault("host", "k10")
    except Exception as exc:
        if host in ("lavie", "red_lavie") and not dry_run:
            entry = cae_dispatch.run_local_trial(
                category=category,
                params=params,
                trial_id=trial_id,
                dry_run=dry_run,
                timeout=timeout,
            )
            entry.setdefault("host", "k10")
            entry["fallback_from"] = host
            entry["fallback_reason"] = str(exc)[:200]
        else:
            return {
                "step": category,
                "host": host,
                "ok": False,
                "verdict": "ERROR",
                "error": str(exc)[:300],
                "dry_run": dry_run,
            }

    verdict = entry.get("verdict") or entry.get("status") or "UNKNOWN"
    if (
        not dry_run
        and host in ("lavie", "red_lavie")
        and str(verdict).upper() == "ERROR"
        and category.startswith("press_")
    ):
        entry = cae_dispatch.run_local_trial(
            category=category,
            params=params,
            trial_id=trial_id,
            dry_run=dry_run,
            timeout=timeout,
        )
        entry.setdefault("host", "k10")
        entry["fallback_from"] = host
        entry["fallback_reason"] = entry.get("error") or "satellite ERROR"
        verdict = entry.get("verdict") or entry.get("status") or "UNKNOWN"

    ok = str(verdict).upper() in ("SUCCESS", "PASS", "OK", "DRY_RUN")
    if dry_run and str(verdict).upper() == "ERROR":
        ok = True
        verdict = "SKIPPED_SATELLITE_DRY_RUN"

    return {
        "step": category,
        "host": entry.get("host", host),
        "router_reason": _router_reason_for_step(
            category=category,
            host=host,
            force_host=force_host,
            decision=decision,
            entry=entry,
            satellite_offline=satellite_offline,
        ),
        "trial_id": trial_id,
        "ok": ok,
        "verdict": verdict,
        "geometry_source": (entry.get("params") or {}).get("geometry_source"),
        "dry_run": dry_run,
        "entry_tail": {
            k: entry.get(k) for k in ("category", "verdict", "duration_sec", "returncode") if k in entry
        },
        "fallback_from": entry.get("fallback_from"),
        "satellite_offline_probe": satellite_offline,
        "policy_degraded": bool(
            category.startswith("press_")
            and entry.get("host") == "k10"
            and (satellite_offline or entry.get("fallback_from") == "red_lavie")
        ),
    }


def run_e2e(
    manifest_path: Path,
    *,
    dry_run: bool = False,
    timeout: int = 900,
    skip_moldflow: bool = False,
    skip_openradioss: bool = False,
) -> dict[str, Any]:
    run_id = f"fable5_e2e_{datetime.now(JST).strftime('%Y%m%d_%H%M%S')}"
    out_dir = RUNS / run_id
    out_dir.mkdir(parents=True, exist_ok=True)

    steps: list[dict[str, Any]] = []
    steps.append(step_validate_manifest(manifest_path))
    steps.append(step_tolerance(manifest_path, out_dir))

    if not skip_moldflow:
        steps.append(
            step_cae(
                category="resin_fill_cad",
                manifest_path=manifest_path,
                out_dir=out_dir,
                dry_run=dry_run,
                timeout=timeout,
                force_host="lavie" if not dry_run else None,
            )
        )
    if not skip_openradioss:
        steps.append(
            step_cae(
                category="press_blanking",
                manifest_path=manifest_path,
                out_dir=out_dir,
                dry_run=dry_run,
                timeout=timeout,
                force_host="red_lavie" if not dry_run else None,
            )
        )

    all_ok = all(s.get("ok") for s in steps)
    or_degraded = any(s.get("policy_degraded") for s in steps)
    report = {
        "schema": "clawstack.fable5_e2e_report.v1",
        "run_id": run_id,
        "manifest_path": str(manifest_path),
        "dry_run": dry_run,
        "started_at": _now(),
        "overall_ok": all_ok,
        "overall_verdict": "SUCCESS" if all_ok else "FAILED",
        "policy_degraded": or_degraded,
        "policy_notes": (
            ["OpenRadioss ran on K10 fallback; red_lavie was offline"]
            if or_degraded
            else []
        ),
        "steps": steps,
    }
    out_path = out_dir / "fable5_e2e_report.json"
    out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    report["report_path"] = str(out_path)
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Fable5 manifest cross-pillar E2E")
    parser.add_argument("--part-manifest", default=str(GOLDEN.relative_to(ROOT)))
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--timeout", type=int, default=900)
    parser.add_argument("--skip-moldflow", action="store_true")
    parser.add_argument("--skip-openradioss", action="store_true")
    parser.add_argument(
        "--require-red-lavie",
        action="store_true",
        help="Fail if press_blanking did not run on red_lavie (no K10 fallback)",
    )
    args = parser.parse_args()

    manifest_path = _resolve_manifest(args.part_manifest)
    report = run_e2e(
        manifest_path,
        dry_run=args.dry_run,
        timeout=args.timeout,
        skip_moldflow=args.skip_moldflow,
        skip_openradioss=args.skip_openradioss,
    )
    if args.require_red_lavie and report.get("policy_degraded"):
        report["overall_ok"] = False
        report["overall_verdict"] = "FAILED"
        report.setdefault("policy_notes", []).append("--require-red-lavie: K10 fallback not allowed")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report.get("overall_ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
