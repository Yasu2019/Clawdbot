# -*- coding: utf-8 -*-
import sys
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

"""JPEG/PNG robot image -> 3D mecha rig orchestration scaffold.

This is the safe outer harness for the integrated path:
image -> part-level 3D candidate -> clawstack.mecha_rig_spec.v1 -> Blender rig -> QA.

It deliberately does not download PartPacker weights or call cloud services unless
the config and command line both allow that in a later implementation pass.
"""

import argparse
import json
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any

import mecha_rig_spec as rig_spec


SCHEMA = "clawstack.jpeg_to_mecha_rig.status.v1"
DEFAULT_CONFIG = Path(__file__).with_name("jpeg_to_mecha_rig.example.json")


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _run_dir(work_root: Path) -> Path:
    return work_root / f"run_{datetime.now():%Y%m%d_%H%M%S}"


def _optional_path(value: Any) -> Path | None:
    text = str(value or "").strip()
    return Path(text) if text else None


def _normalize_inventory_object(obj: dict[str, Any], model_min: list[float], model_max: list[float]) -> dict[str, Any]:
    center = [float(v) for v in (obj.get("center") or [0, 0, 0])[:3]]
    size = [float(v) for v in (obj.get("size") or [0, 0, 0])[:3]]
    ext = [max(float(model_max[i]) - float(model_min[i]), 1e-9) for i in range(3)]
    centroid_norm = [
        round(((center[0] - float(model_min[0])) / ext[0]) * 2.0 - 1.0, 4),
        round(((center[1] - float(model_min[1])) / ext[1]) * 2.0 - 1.0, 4),
        round((center[2] - float(model_min[2])) / ext[2], 4),
    ]
    size_norm = [round(size[i] / ext[i], 4) for i in range(3)]
    return {
        "mesh": str(obj.get("name") or obj.get("mesh") or obj.get("semantic") or "part"),
        "name": str(obj.get("name") or obj.get("mesh") or "part"),
        "semantic": obj.get("semantic"),
        "centroid_norm": centroid_norm,
        "size_norm": size_norm,
        "vertices": obj.get("vertices"),
        "polygons": obj.get("polygons"),
    }


def partpacker_inventory_to_audit(inventory_path: Path, audit_path: Path) -> dict[str, Any]:
    inv = _read_json(inventory_path)
    bounds = inv.get("model_bounds") or {}
    model_min = bounds.get("min")
    model_max = bounds.get("max")
    if not model_min or not model_max:
        raise ValueError(f"inventory lacks model_bounds min/max: {inventory_path}")
    objects = inv.get("objects") or []
    segments = [_normalize_inventory_object(o, model_min, model_max) for o in objects]
    audit = {
        "schema": "clawstack.mecha_candidate_inventory_audit.v1",
        "source": str(inventory_path),
        "bounds_min": model_min,
        "bounds_max": model_max,
        "segment_assignments": segments,
    }
    _write_json(audit_path, audit)
    return audit


def build_spec_from_inventory(inventory_path: Path, out_spec: Path, out_audit: Path, model: str) -> dict[str, Any]:
    partpacker_inventory_to_audit(inventory_path, out_audit)
    spec = rig_spec.build_rig_spec_from_audit(out_audit, model=model)
    _write_json(out_spec, spec)
    ok, issues = rig_spec.validate_rig_spec(spec)
    return {
        "ok": ok,
        "issues": issues,
        "spec": str(out_spec),
        "audit": str(out_audit),
        "segments": len(spec.get("segments") or []),
        "joints": len(spec.get("joints") or []),
        "flagged": spec.get("review", {}).get("flagged_for_review", []),
    }


def _partpacker_command(cfg: dict[str, Any], run_dir: Path) -> list[str]:
    gen = cfg["generator"]
    return [
        str(Path(gen["partpacker_python"])),
        "flow/scripts/infer.py",
        "--config", "flow.configs.big_parts_strict_pvae",
        "--ckpt_path", str(Path(gen["partpacker_root"]) / gen.get("checkpoint", "pretrained/flow.pt")),
        "--input", str(Path(cfg["input_image"])),
        "--output_dir", str(run_dir / "10_partpacker"),
        "--grid_res", str(int(gen.get("grid_res", 256))),
        "--num_steps", str(int(gen.get("num_steps", 30))),
        "--num_repeats", str(int(gen.get("num_repeats", 3))),
    ]


def _blender_build_command(cfg: dict[str, Any], candidate_model: Path, spec_path: Path, run_dir: Path) -> list[str]:
    blender = cfg["blender"]
    return [
        str(Path(blender["exe"])),
        "--background",
        "--python", str(Path(__file__).with_name("mecha_rig_builder.py")),
        "--",
        "--spec", str(spec_path),
        "--fbx", str(candidate_model),
        "--out-fbx", str(run_dir / "50_rigged" / "rigged.fbx"),
        "--out-blend", str(run_dir / "50_rigged" / "rigged.blend"),
        "--report", str(run_dir / "50_rigged" / "build_report.json"),
        "--upright", str(blender.get("upright", "90,0,0")),
        "--target-height", str(float(blender.get("target_height", 18.0))),
    ]


def run_checked(command: list[str], cwd: Path | None, timeout_seconds: int, log_path: Path) -> int:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    proc = subprocess.run(
        command,
        cwd=str(cwd) if cwd else None,
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        timeout=timeout_seconds,
        check=False,
    )
    log_path.write_text(
        "COMMAND:\n" + subprocess.list2cmdline(command) +
        "\n\nSTDOUT:\n" + proc.stdout +
        "\n\nSTDERR:\n" + proc.stderr +
        f"\n\nRETURNCODE:\n{proc.returncode}\n",
        encoding="utf-8",
    )
    return int(proc.returncode)


def main() -> int:
    parser = argparse.ArgumentParser(description="Safe JPEG to 3D mecha rig orchestrator")
    parser.add_argument("--config", default=str(DEFAULT_CONFIG))
    parser.add_argument("--execute", action="store_true", help="Run enabled local steps. External generation remains gated.")
    parser.add_argument("--inventory", help="Convert an existing PartPacker-style inventory JSON to rig_spec.")
    parser.add_argument("--candidate", help="Existing local FBX/GLB candidate to pass to Blender builder.")
    args = parser.parse_args()

    cfg_path = Path(args.config).resolve()
    cfg = _read_json(cfg_path)
    run_dir = _run_dir(Path(cfg["work_root"]))
    for rel in ("00_input", "10_partpacker", "20_candidate", "30_spec", "40_qa", "50_rigged", "logs"):
        (run_dir / rel).mkdir(parents=True, exist_ok=True)

    status: dict[str, Any] = {
        "schema": SCHEMA,
        "config": str(cfg_path),
        "run_dir": str(run_dir),
        "model": cfg.get("model", "robot_from_jpeg"),
        "dry_run": bool(cfg.get("runtime", {}).get("dry_run", True)) or not args.execute,
        "steps": [],
        "blocked": [],
        "next_action": "review_status",
    }

    image = Path(cfg["input_image"])
    if image.exists():
        status["steps"].append({"name": "input_image", "status": "ready", "path": str(image)})
    else:
        status["blocked"].append(f"missing_input_image:{image}")

    inventory = _optional_path(args.inventory or cfg.get("candidate", {}).get("partpacker_inventory"))
    spec_path = run_dir / "30_spec" / "mecha_rig_spec.json"
    audit_path = run_dir / "30_spec" / "candidate_audit.json"
    if inventory and inventory.exists():
        result = build_spec_from_inventory(inventory, spec_path, audit_path, str(cfg.get("model", "robot_from_jpeg")))
        status["steps"].append({"name": "inventory_to_spec", "status": "completed", **result})
        if not result["ok"]:
            status["blocked"].append("rig_spec_requires_human_review")
    else:
        status["steps"].append({"name": "inventory_to_spec", "status": "waiting", "reason": "no inventory JSON supplied"})

    gen = cfg.get("generator", {})
    runtime = cfg.get("runtime", {})
    if gen.get("provider") == "partpacker":
        command = _partpacker_command(cfg, run_dir)
        status["steps"].append({"name": "partpacker_generation", "status": "planned", "command": command})
        if not gen.get("enabled"):
            status["blocked"].append("partpacker_generator_disabled")
        if not runtime.get("allow_external_downloads"):
            status["blocked"].append("external_downloads_not_allowed")
        if args.execute and gen.get("enabled") and runtime.get("allow_external_downloads"):
            timeout = int(gen.get("timeout_minutes", 90)) * 60
            rc = run_checked(command, Path(gen["partpacker_root"]), timeout, run_dir / "logs" / "partpacker.log")
            status["steps"].append({"name": "partpacker_generation_run", "status": "completed" if rc == 0 else "failed", "returncode": rc})

    candidate = _optional_path(args.candidate or cfg.get("candidate", {}).get("manual_model"))
    if candidate and candidate.exists() and spec_path.exists():
        command = _blender_build_command(cfg, candidate, spec_path, run_dir)
        status["steps"].append({"name": "blender_build", "status": "planned", "command": command})
        if args.execute and not status["dry_run"]:
            rc = run_checked(command, None, 45 * 60, run_dir / "logs" / "blender_build.log")
            status["steps"].append({"name": "blender_build_run", "status": "completed" if rc == 0 else "failed", "returncode": rc})
    else:
        status["steps"].append({"name": "blender_build", "status": "waiting", "reason": "needs candidate model and valid rig spec"})

    if status["blocked"]:
        status["next_action"] = "resolve_blockers_then_execute_local_smoke"
    elif status["dry_run"]:
        status["next_action"] = "rerun_with_execute_for_local_steps"
    else:
        status["next_action"] = "review_visual_and_joint_qa"

    _write_json(run_dir / "harness_status.json", status)
    print(json.dumps({"status": "ok", "run_dir": str(run_dir), "next_action": status["next_action"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
