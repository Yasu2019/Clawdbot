#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Task Gate:
ミニPCでタスクを実行する前に、UE5不要・Blender+RV6優先・FreeCAD優先などの受入れ判定を行います。
"""
import sys
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import argparse, json
from pathlib import Path
try:
    import yaml
except ImportError:
    yaml = None

def load_policy(path: Path) -> dict:
    if not path.exists():
        return {"task_classes":{"real_3d_video":{"allowed_engines":["blender","rv6","esrgan_ncnn_vulkan"],"blocked_engines":["ue5_headless"]},"dxf_to_step":{"allowed_engines":["freecad_headless"],"blocked_engines":["manual_uncontrolled_conversion"]}}}
    text = path.read_text(encoding="utf-8")
    if yaml:
        return yaml.safe_load(text)
    return {"task_classes":{"real_3d_video":{"allowed_engines":["blender","rv6","esrgan_ncnn_vulkan"],"blocked_engines":["ue5_headless"]},"dxf_to_step":{"allowed_engines":["freecad_headless"],"blocked_engines":["manual_uncontrolled_conversion"]}}}

def judge(task: str, requested_engine: str | None, policy: dict, ue5_challenge: bool = False) -> dict:
    task_policy = policy.get("task_classes", {}).get(task, {})
    allowed = set(task_policy.get("allowed_engines", []))
    blocked = set(task_policy.get("blocked_engines", []))
    result = {"task": task, "requested_engine": requested_engine, "decision": "accept_with_conditions", "recommended_route": [], "blocked_reason": None, "checks": []}
    
    if task == "real_3d_video":
        if requested_engine in ["ue5", "ue5_headless"] and ue5_challenge:
            result["decision"] = "accept_challenge_mode"
            result["recommended_route"] = ["UE5 Headless simulation", "Verify Unreal Engine 5 rendering confidence", "Fall back to Blender if confidence <= 0.8"]
            result["checks"] = ["Verify UE5 environment", "Verify system memory > 16GB", "Verify GPU supports DirectX 12 or Vulkan", "Run headless simulation", "Auto-fallback to Blender if UE5 crashes"]
            return result
        result["recommended_route"] = ["Blender scene generation", "Street-level camera", "RV6 strength 0.65", "ESRGAN NCNN Vulkan upscale", "Evening/Night HDRI optional"]
    if task == "dxf_to_step":
        result["recommended_route"] = ["FreeCAD headless importDXF", "Shape validation", "STEP export", "Log and checksum"]
        
    if requested_engine in blocked:
        result["decision"] = "reject_engine_use_alternative"
        result["blocked_reason"] = f"{requested_engine} is blocked for task {task}."
        return result
    if requested_engine and allowed and requested_engine not in allowed:
        result["decision"] = "hold_for_review"
        result["blocked_reason"] = f"{requested_engine} is not in allowed engines: {sorted(allowed)}"
        return result
    result["checks"] = ["Input files exist", "Output directory is writable", "No destructive operation without backup", "Retry count within limit", "UTF-8 log output enabled"]
    return result

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--task", required=True, choices=["real_3d_video", "dxf_to_step", "scheduled_task"])
    parser.add_argument("--engine", default=None)
    parser.add_argument("--config", default="configs/acceptance_policy.yaml")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--ue5-challenge", action="store_true", help="Enable experimental UE5 generation challenge mode if AI is confident")
    args = parser.parse_args()
    result = judge(args.task, args.engine, load_policy(Path(args.config)), args.ue5_challenge)
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print("=== Mini PC Task Gate Result ===")
        print(f"Task: {result['task']}")
        print(f"Decision: {result['decision']}")
        if result["blocked_reason"]: print(f"Reason: {result['blocked_reason']}")
        print("Recommended route:")
        for item in result["recommended_route"]: print(f"  - {item}")
        print("Checks:")
        for item in result["checks"]: print(f"  - {item}")
    return 0 if result["decision"] not in ["reject_engine_use_alternative"] else 2
if __name__ == "__main__":
    raise SystemExit(main())

