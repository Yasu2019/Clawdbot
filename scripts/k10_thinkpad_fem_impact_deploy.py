# -*- coding: utf-8 -*-
"""Deploy Impact FEM bundle to ThinkPad, build, and run fem_impact trials.

Impact .in files are Impact Pre Processor format (not OpenRadioss .rad).
Console solver: java run.Impact <case.in>  (see Impact/Impact.sh).
Success for the simple sample: VTK series test.in_*.vtk in the case directory.
VTK -> PNG via Docker ParaView on ThinkPad (headless, no Impact GUI).
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
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
JST = timezone(timedelta(hours=9))
STATUS_PATH = WORKSPACE / "thinkpad_fem_impact_deploy_status.json"

BUNDLE_DIRNAME = "AUTO_FIX_ORIENTATION_20250804"
DEFAULT_BUNDLE_LOCAL = ROOT / f"\u5b8c\u5168\u6210\u529f_\u6c38\u4e45\u4fdd\u5b58\u7248_{BUNDLE_DIRNAME}"
DEFAULT_REMOTE_BUNDLE = f"/home/yasu/clawstack_satellite/impact_bundle/{BUNDLE_DIRNAME}"
PV_IMAGE = "clawstack-unified-paraview:latest"
PVPYTHON = "/opt/paraview/install/bin/pvpython"
PNG_SHELL_REMOTE = "/home/yasu/clawstack_satellite/scripts/thinkpad_fem_impact_png.sh"
RENDER_SCRIPT_LOCAL = ROOT / "scripts" / "impact_vtk_to_png.py"
RENDER_SCRIPT_REMOTE = "/home/yasu/clawstack_satellite/scripts/impact_vtk_to_png.py"
PNG_SHELL_LOCAL = ROOT / "scripts" / "thinkpad_fem_impact_png.sh"
QC_SCRIPT_LOCAL = ROOT / "scripts" / "impact_vtk_quality_gate.py"
QC_SCRIPT_REMOTE = "/home/yasu/clawstack_satellite/scripts/impact_vtk_quality_gate.py"

if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

import k10_satellite_dispatch as sjp
import thinkpad_ssh_common as tsc


def now_iso() -> str:
    return datetime.now(JST).isoformat()


def load_yaml_fem() -> dict[str, Any]:
    import yaml

    cfg = yaml.safe_load((WORKSPACE / "cae_workload_router.yaml").read_text(encoding="utf-8")) or {}
    return (cfg.get("tri_track_parallel") or {}).get("fem_impact") or {}


def save_status(payload: dict[str, Any]) -> None:
    payload = dict(payload)
    payload["updated_at"] = now_iso()
    WORKSPACE.mkdir(parents=True, exist_ok=True)
    STATUS_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def ssh_registry() -> dict[str, Any]:
    reg = tsc.read_registry()
    return {
        "ssh_user": reg.get("ssh_user") or "yasu",
        "ssh_host": reg.get("ssh_host") or reg.get("tailscale_ip") or "100.66.63.9",
        "ssh_key_path": reg.get("ssh_key_path") or str(Path.home() / ".ssh" / "id_ed25519"),
    }


def sync_render_script(*, dry_run: bool) -> dict[str, Any]:
    if not RENDER_SCRIPT_LOCAL.exists() or not PNG_SHELL_LOCAL.exists() or not QC_SCRIPT_LOCAL.exists():
        return {"ok": False, "error": "missing render scripts"}
    reg = ssh_registry()
    remote_dir = str(Path(RENDER_SCRIPT_REMOTE).parent).replace("\\", "/")
    if dry_run:
        return {"ok": True, "dry_run": True, "target": RENDER_SCRIPT_REMOTE}
    subprocess.run(
        [
            "ssh",
            "-i",
            reg["ssh_key_path"],
            "-o",
            "BatchMode=yes",
            "-o",
            "ConnectTimeout=20",
            f"{reg['ssh_user']}@{reg['ssh_host']}",
            f"mkdir -p {remote_dir}",
        ],
        check=False,
        timeout=30,
    )
    ok = True
    stderr_parts: list[str] = []
    for local, remote in (
        (RENDER_SCRIPT_LOCAL, RENDER_SCRIPT_REMOTE),
        (PNG_SHELL_LOCAL, PNG_SHELL_REMOTE),
        (QC_SCRIPT_LOCAL, QC_SCRIPT_REMOTE),
    ):
        proc = subprocess.run(
            [
                "scp",
                "-i",
                reg["ssh_key_path"],
                "-o",
                "BatchMode=yes",
                "-o",
                "ConnectTimeout=20",
                str(local),
                f"{reg['ssh_user']}@{reg['ssh_host']}:{remote}",
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=60,
        )
        ok = ok and proc.returncode == 0
        stderr_parts.append((proc.stderr or "")[-200:])
    chmod = subprocess.run(
        [
            "ssh",
            "-i",
            reg["ssh_key_path"],
            "-o",
            "BatchMode=yes",
            f"{reg['ssh_user']}@{reg['ssh_host']}",
            f"chmod +x {PNG_SHELL_REMOTE}",
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    ok = ok and chmod.returncode == 0
    return {
        "ok": ok,
        "remote": RENDER_SCRIPT_REMOTE,
        "png_shell": PNG_SHELL_REMOTE,
        "qc_script": QC_SCRIPT_REMOTE,
        "stderr": "".join(stderr_parts)[-400:],
    }


def sync_bundle(local_root: Path, remote_root: str, *, dry_run: bool) -> dict[str, Any]:
    if not local_root.exists():
        return {"ok": False, "error": f"bundle missing: {local_root}"}
    reg = ssh_registry()
    target = f"{reg['ssh_user']}@{reg['ssh_host']}:{remote_root}"
    mkdir = [
        "ssh",
        "-i",
        reg["ssh_key_path"],
        "-o",
        "BatchMode=yes",
        "-o",
        "ConnectTimeout=20",
        f"{reg['ssh_user']}@{reg['ssh_host']}",
        f"mkdir -p {remote_root}",
    ]
    if dry_run:
        return {"ok": True, "dry_run": True, "would_sync": str(local_root), "target": target}
    subprocess.run(mkdir, check=False, capture_output=True, text=True, encoding="utf-8", errors="replace")
    scp = [
        "scp",
        "-i",
        reg["ssh_key_path"],
        "-o",
        "BatchMode=yes",
        "-o",
        "ConnectTimeout=30",
        "-r",
        str(local_root) + "/.",
        target,
    ]
    print(f"[sync] {local_root} -> {target}", flush=True)
    proc = subprocess.run(scp, capture_output=True, text=True, encoding="utf-8", errors="replace")
    return {
        "ok": proc.returncode == 0,
        "local_root": str(local_root),
        "remote_root": remote_root,
        "stderr": (proc.stderr or "")[-800:],
    }


def dispatch_shell(command: str, *, job_id: str, timeout_sec: int) -> dict[str, Any]:
    node = sjp.load_node("thinkpad")
    base_url = sjp.worker_base_url(node)
    token = sjp.load_token()
    job = {
        "job_id": job_id,
        "type": "shell",
        "timeout_sec": timeout_sec,
        "payload": {"command": command},
        "report": {"mode": "sync"},
    }
    return sjp.dispatch_job(base_url, token, job, timeout_sec)


def impact_run_command(
    *,
    impact_home: str,
    case_dir: str,
    input_name: str,
    qc_limits: dict[str, float | int] | None = None,
) -> str:
    from impact_vtk_quality_gate import DEFAULT_QC_LIMITS

    lim = qc_limits or dict(DEFAULT_QC_LIMITS)
    lib_path = f"{impact_home}/lib_j3d/linux_amd64:{impact_home}/lib"
    qc_cmd = (
        f'VTK_QC=$(ls -1 "$CASE_DIR/${{INP}}"_surface_*.vtk 2>/dev/null | sort -V | tail -1 || true); '
        f'if [ -z "$VTK_QC" ]; then echo FEM_IMPACT_QC_VERDICT=FAILED_MESH_EXPLOSION; '
        f'echo FEM_IMPACT_QC_REASONS=vtk_missing; exit 20; fi; '
        f'echo FEM_IMPACT_QC_VTK=$VTK_QC; '
        f'python3 {QC_SCRIPT_REMOTE} "$VTK_QC" '
        f'--max-bbox-diag {float(lim["max_bbox_diag"]):g} '
        f'--max-coordinate-abs {float(lim["max_coordinate_abs"]):g} '
        f'--max-displacement-abs {float(lim["max_displacement_abs"]):g} '
        f'--min-points {int(lim["min_points"])}'
    )
    return (
        "bash -lc "
        f"'set -euo pipefail; "
        f"IMPACT_HOME={impact_home!r}; CASE_DIR={case_dir!r}; INP={input_name!r}; "
        f"export LD_LIBRARY_PATH={lib_path}:\"${{LD_LIBRARY_PATH:-}}\"; "
        f"export JAVA_TOOL_OPTIONS=\"-Dfile.encoding=UTF-8\"; "
        f"cd \"$IMPACT_HOME\"; "
        f"if ! command -v ant >/dev/null 2>&1; then echo ANT_NOT_INSTALLED; exit 3; fi; "
        f"if ! command -v java >/dev/null 2>&1; then echo JAVA_NOT_INSTALLED; exit 4; fi; "
        f"java -version 2>&1 | head -1; "
        f"if [ ! -f bin/run/Impact.class ]; then ant -q compile; fi; "
        f"cd \"$CASE_DIR\"; "
        f"test -f \"$INP\" || {{ echo INPUT_MISSING; exit 5; }}; "
        f"rm -f \"$CASE_DIR/${{INP}}\"_*.vtk \"$CASE_DIR/${{INP}}\"_*.vtu 2>/dev/null || true; "
        f"cd \"$IMPACT_HOME\"; "
        f"java -Xmx4096m -Xss2m -cp .:doc:bin run.Impact \"$CASE_DIR/$INP\"; "
        f"{qc_cmd}; "
        f"VTK_COUNT=$(ls -1 \"$CASE_DIR/${{INP}}\"_*.vtk 2>/dev/null | wc -l); "
        f"PNG_COUNT=$(ls -1 \"$CASE_DIR/${{INP}}\"*.png 2>/dev/null | wc -l); "
        f"echo FEM_IMPACT_VTK_COUNT=$VTK_COUNT; "
        f"echo FEM_IMPACT_PNG_COUNT=$PNG_COUNT; "
        f"ls -1 \"$CASE_DIR/${{INP}}\"_*.vtk 2>/dev/null | tail -3'"
    )


def paraview_png_command(*, case_dir: str, input_name: str, render_script: str = "") -> str:
    _ = render_script
    return f"bash -lc 'bash {PNG_SHELL_REMOTE} {case_dir!r} {input_name!r}'"


def parse_counts(stdout: str) -> tuple[int, int]:
    vtk = png = 0
    for line in (stdout or "").splitlines():
        if line.startswith("FEM_IMPACT_VTK_COUNT="):
            vtk = int(line.split("=", 1)[1].strip() or "0")
        if line.startswith("FEM_IMPACT_PNG_COUNT="):
            png = int(line.split("=", 1)[1].strip() or "0")
    return vtk, png


def exit_code_ok(exit_code: Any) -> bool:
    """True when worker exit code is exactly 0 (not falsy-or-1)."""
    if exit_code is None:
        return False
    return int(exit_code) == 0


def run_case(
    *,
    remote_bundle: str,
    case_subdir: str,
    input_name: str,
    timeout_sec: int,
    dry_run: bool,
    render_png: bool,
    fem_cfg: dict[str, Any] | None = None,
) -> dict[str, Any]:
    from impact_vtk_quality_gate import limits_from_fem_cfg, parse_qc_stdout

    impact_home = f"{remote_bundle}/Impact"
    case_dir = f"{impact_home}/{case_subdir}".replace("\\", "/")
    qc_limits = limits_from_fem_cfg(fem_cfg or load_yaml_fem())
    cmd = impact_run_command(
        impact_home=impact_home,
        case_dir=case_dir,
        input_name=input_name,
        qc_limits=qc_limits,
    )
    if dry_run:
        out = {
            "ok": True,
            "dry_run": True,
            "case_dir": case_dir,
            "input": input_name,
            "command_preview": cmd[:500],
        }
        if render_png:
            out["png_command_preview"] = paraview_png_command(
                case_dir=case_dir, input_name=input_name, render_script=RENDER_SCRIPT_REMOTE
            )[:500]
        return out
    job_id = f"fem-impact-{int(time.time())}"
    result = dispatch_shell(cmd, job_id=job_id, timeout_sec=timeout_sec)
    stdout = result.get("stdout_tail") or ""
    stderr = result.get("stderr_tail") or ""
    vtk_count, png_count = parse_counts(stdout)
    qc = parse_qc_stdout(stdout)
    qc_ok = qc.get("verdict") == "PASS" and "FAILED_MESH_EXPLOSION" not in stdout
    ok = (
        result.get("status") == "ok"
        and exit_code_ok(result.get("exit_code"))
        and vtk_count > 0
        and qc_ok
    )
    png_step: dict[str, Any] | None = None
    if ok and render_png:
        png_cmd = paraview_png_command(
            case_dir=case_dir, input_name=input_name, render_script=RENDER_SCRIPT_REMOTE
        )
        png_result = dispatch_shell(png_cmd, job_id=f"{job_id}-png", timeout_sec=min(timeout_sec, 900))
        png_stdout = png_result.get("stdout_tail") or ""
        _, png_count = parse_counts(png_stdout)
        png_step = {
            "ok": png_result.get("status") == "ok"
            and exit_code_ok(png_result.get("exit_code"))
            and png_count > 0,
            "png_count": png_count,
            "stdout_tail": png_stdout[-1500:],
            "stderr_tail": (png_result.get("stderr_tail") or "")[-800:],
        }
        ok = ok and bool(png_step and png_step.get("ok"))
    verdict = "SUCCESS" if ok else ("FAILED_MESH_EXPLOSION" if not qc_ok else "FAILED")
    return {
        "ok": ok,
        "case_dir": case_dir,
        "input": input_name,
        "vtk_count": vtk_count,
        "png_count": png_count,
        "png_step": png_step,
        "qc": qc,
        "exit_code": result.get("exit_code"),
        "worker_status": result.get("status"),
        "stdout_tail": stdout[-2500:],
        "stderr_tail": stderr[-1500:],
        "verdict": verdict,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="ThinkPad Impact FEM deploy and trial runner")
    parser.add_argument("--bundle-local", default=str(DEFAULT_BUNDLE_LOCAL))
    parser.add_argument("--remote-bundle", default=DEFAULT_REMOTE_BUNDLE)
    parser.add_argument("--sync-bundle", action="store_true", help="scp full bundle to ThinkPad")
    parser.add_argument(
        "--sample",
        action="store_true",
        help="Run no_solid_reqtangle_sample_20250806/test.in",
    )
    parser.add_argument(
        "--case-subdir",
        default="",
        help="Impact subdir e.g. 160um_Panel_20250725/Rough_Mesh",
    )
    parser.add_argument("--input", default="test.in", help="Input file name inside case dir")
    parser.add_argument("--timeout", type=int, default=7200)
    parser.add_argument("--png", action="store_true", help="Render latest VTK to PNG via ParaView Docker")
    parser.add_argument("--png-only", action="store_true", help="Skip Impact solve; render PNG from latest VTK")
    parser.add_argument("--sync-script", action="store_true", help="scp impact_paraview_render.py to ThinkPad")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    fem = load_yaml_fem()
    remote_bundle = args.remote_bundle or str(fem.get("remote_bundle_root") or DEFAULT_REMOTE_BUNDLE)
    local_bundle = Path(args.bundle_local)
    if fem.get("bundle_local"):
        local_bundle = Path(str(fem["bundle_local"]))

    out: dict[str, Any] = {
        "schema": "clawstack.thinkpad_fem_impact_deploy.v1",
        "remote_bundle": remote_bundle,
        "local_bundle": str(local_bundle),
        "steps": {},
    }

    if args.sync_script or args.png:
        out["steps"]["sync_script"] = sync_render_script(dry_run=args.dry_run)

    if args.sync_bundle:
        out["steps"]["sync"] = sync_bundle(local_bundle, remote_bundle, dry_run=args.dry_run)

    if args.png_only:
        subdir = "no_solid_reqtangle_sample_20250806" if args.sample else args.case_subdir
        if not subdir:
            print("[NG] --png-only requires --sample or --case-subdir", file=sys.stderr)
            return 2
        case_dir = f"{remote_bundle}/Impact/{subdir}".replace("\\", "/")
        inp = "test.in" if args.sample else args.input
        if not args.dry_run:
            png_cmd = paraview_png_command(
                case_dir=case_dir, input_name=inp, render_script=RENDER_SCRIPT_REMOTE
            )
            png_result = dispatch_shell(png_cmd, job_id=f"fem-png-{int(time.time())}", timeout_sec=min(args.timeout, 900))
            stdout = png_result.get("stdout_tail") or ""
            _, png_count = parse_counts(stdout)
            out["steps"]["png_only"] = {
                "ok": png_result.get("status") == "ok"
                and exit_code_ok(png_result.get("exit_code"))
                and png_count > 0,
                "case_dir": case_dir,
                "png_count": png_count,
                "stdout_tail": stdout[-2000:],
                "stderr_tail": (png_result.get("stderr_tail") or "")[-800:],
            }
        else:
            out["steps"]["png_only"] = {"ok": True, "dry_run": True, "case_dir": case_dir}
    elif args.sample:
        out["steps"]["sample"] = run_case(
            remote_bundle=remote_bundle,
            case_subdir="no_solid_reqtangle_sample_20250806",
            input_name="test.in",
            timeout_sec=args.timeout,
            dry_run=args.dry_run,
            render_png=args.png,
        )
    elif args.case_subdir:
        out["steps"]["case"] = run_case(
            remote_bundle=remote_bundle,
            case_subdir=args.case_subdir,
            input_name=args.input,
            timeout_sec=args.timeout,
            dry_run=args.dry_run,
            render_png=args.png,
        )

    out["ok"] = all(step.get("ok") for step in out["steps"].values()) if out["steps"] else False
    save_status(out)
    if args.json:
        print(json.dumps(out, ensure_ascii=False, indent=2))
    else:
        print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0 if out["ok"] or args.dry_run else 1


if __name__ == "__main__":
    raise SystemExit(main())
