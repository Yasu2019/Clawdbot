#!/usr/bin/env python3
"""Batch Reprocessor for all past DXF-to-3D jobs.

Scans all trials in the jobs/ directory, reads their thickness from build_log.json,
and re-runs the upgraded dxf2step_worker.py to regenerate all 3D STEP models
and aligned preview drawings using the new 3D counterbore and scaling features.
"""
import os
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent
JOBS_DIR = ROOT / "jobs"
WORKER_PY = ROOT / "dxf2step_worker.py"

def main():
    print(f"Scanning jobs directory: {JOBS_DIR}")
    if not JOBS_DIR.exists():
        print("[Error] Jobs directory not found.")
        return
        
    trials = sorted([d for d in JOBS_DIR.iterdir() if d.is_dir()])
    print(f"Found {len(trials)} past trials.")
    
    success_count = 0
    for trial in trials:
        input_dir = trial / "input"
        output_dir = trial / "output"
        build_log_path = output_dir / "build_log.json"
        
        if not input_dir.exists() or not output_dir.exists():
            continue
            
        # Find the input DXF file
        dxf_files = list(input_dir.glob("*.dxf"))
        if not dxf_files:
            print(f"[{trial.name}] No DXF file found in input/")
            continue
        dxf_path = dxf_files[0]
        
        # Read thickness from build_log.json
        thickness = 10.0 # Default fallback
        if build_log_path.exists():
            try:
                log_data = json.loads(build_log_path.read_text(encoding="utf-8"))
                layers = log_data.get("layers", {})
                if layers:
                    # Get thickness from the first layer
                    first_layer_name = list(layers.keys())[0]
                    thickness = layers[first_layer_name].get("thickness", 10.0)
            except Exception as e:
                print(f"[{trial.name}] Failed to read build_log.json: {e}")
                
        print(f"\nReprocessing: {trial.name}")
        print(f"  - DXF: {dxf_path.name}")
        print(f"  - Thickness: {thickness} mm")
        
        # Re-run dxf2step_worker.py to regenerate everything
        cmd = [
            "python", str(WORKER_PY),
            "--input", str(dxf_path),
            "--output", str(output_dir),
            "--thickness", str(thickness)
        ]
        
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=180)
            if r.returncode == 0:
                print(f"  SUCCESS: {trial.name}")
                success_count += 1
            else:
                print(f"  FAILED: {trial.name} (exit {r.returncode})")
                print(f"  stderr: {r.stderr[:300]}")
        except Exception as e:
            print(f"  ERROR: {trial.name} - {e}")
            
    print(f"\nCompleted re-processing. Successfully updated {success_count} / {len(trials)} past trials.")

if __name__ == "__main__":
    main()