#!/usr/bin/env python3
import json
import subprocess
import os
import sys
from pathlib import Path

# Paths
WORKSPACE_DIR = Path(__file__).resolve().parent
REMOTION_DIR = WORKSPACE_DIR / "iatf_remotion_studio"
GET_METRICS_SCRIPT = WORKSPACE_DIR / "get_turso_metrics.py"
MULTICAD_PYTHON = WORKSPACE_DIR / "apps" / "3d_fab_forge" / "multicad_pipeline" / ".venv" / "Scripts" / "python.exe"

def main():
    print("--- Starting Growth Video Generation ---")
    
    # 1. Fetch Metrics
    print("Fetching Turso metrics...")
    try:
        res = subprocess.run(
            [str(MULTICAD_PYTHON), str(GET_METRICS_SCRIPT)],
            capture_output=True, text=True, check=True
        )
        metrics = json.loads(res.stdout)
    except Exception as e:
        print(f"Error fetching metrics: {e}")
        return

    if metrics.get("status") != "success":
        print(f"Metrics status error: {metrics.get('error')}")
        return

    count = metrics.get("record_count", 0)
    
    # 2. Render Goku Video (Growth Theme)
    props = {"text": f"Turso Knowledge: {count} Records", "isImportant": True}
    props_file = "props.json"
    props_path = REMOTION_DIR / props_file
    
    # Write props file
    print(f"Writing props to {props_path}")
    with open(props_path, "w", encoding="utf-8") as f:
        json.dump(props, f, ensure_ascii=False)
        f.flush()
        os.fsync(f.fileno())

    print(f"Rendering Goku video with text: {props['text']}")
    
    try:
        # Use npx remotion render <entry> <composition-id> <output> --props=<file>
        # We use relative path for props as remotion expects it relative to entry or cwd
        render_cmd = [
            "npx", "remotion", "render", "Root.tsx", "GokuMC", "out_goku.mp4",
            f"--props={props_file}"
        ]
        # We don't capture output so it streams to the parent
        subprocess.run(render_cmd, cwd=str(REMOTION_DIR), shell=True, check=True)
        print("Goku video rendered: out_goku.mp4")
    except Exception as e:
        print(f"Error rendering video: {e}")
    finally:
        if props_path.exists():
            try:
                props_path.unlink()
            except:
                pass

if __name__ == "__main__":
    main()
