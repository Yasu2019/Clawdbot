"""
Autonomous DXF2STEP Test Scorer
================================
1. Generate test DXFs
2. POST each to localhost:8002
3. Poll until done
4. Analyse STEP with FreeCAD (via docker exec)
5. Score and log results
6. Print overall score
"""
import json
import math
import os
import subprocess
import sys
import time
from pathlib import Path

import requests

BASE_DIR   = Path(__file__).parent.parent
TESTS_DIR  = Path(__file__).parent
DXF_DIR    = TESTS_DIR / "dxf_files"
JOBS_DIR   = BASE_DIR / "jobs"
API        = "http://localhost:8002"
CONTAINER  = "clawstack-unified-clawdbot-gateway-1"
REPORT_JSON = TESTS_DIR / "results_round01.json"

sys.path.insert(0, str(TESTS_DIR))
from test_cases import TESTS


# ── FreeCAD geometry analyser (runs inside container) ─────────────────────────

def analyse_step(step_host_path: str) -> dict:
    """Run FreeCAD inside container to get geometry stats of a STEP file."""
    # Map host path → container path
    container_path = step_host_path.replace("\\", "/").replace(
        "D:/Clawdbot_Docker_20260125/data/workspace", "/home/node/clawd"
    )
    # Write script with path embedded directly (FreeCADCmd ignores extra argv)
    script_host = step_host_path.replace(".step", "_analyse.py")
    script_container = script_host.replace("\\", "/").replace(
        "D:/Clawdbot_Docker_20260125/data/workspace", "/home/node/clawd"
    )
    script_content = (
        "import json\n"
        "import Part\n"
        f"step_path = '{container_path}'\n"
        "try:\n"
        "    shape = Part.read(step_path)\n"
        "    bb    = shape.BoundBox\n"
        "    result = {\n"
        '        "volume":  round(shape.Volume, 3),\n'
        '        "faces":   len(shape.Faces),\n'
        '        "bbox_x":  round(bb.XMax - bb.XMin, 3),\n'
        '        "bbox_y":  round(bb.YMax - bb.YMin, 3),\n'
        '        "bbox_z":  round(bb.ZMax - bb.ZMin, 3),\n'
        '        "is_valid": shape.isValid(),\n'
        '        "error":   None,\n'
        "    }\n"
        "except Exception as e:\n"
        '    result = {"volume": 0, "faces": 0, "bbox_x": 0, "bbox_y": 0,\n'
        '              "bbox_z": 0, "is_valid": False, "error": str(e)}\n'
        "print(json.dumps(result))\n"
    )
    with open(script_host, "w") as f:
        f.write(script_content)

    cmd = ["docker", "exec", CONTAINER, "bash", "-c",
           f"FreeCADCmd '{script_container}' 2>/dev/null"]
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=90)
        # Find JSON line in output
        for line in res.stdout.splitlines():
            line = line.strip()
            if line.startswith("{"):
                try:
                    return json.loads(line)
                except Exception:
                    pass
        return {"volume": 0, "faces": 0, "bbox_x": 0, "bbox_y": 0,
                "bbox_z": 0, "is_valid": False, "error": f"No JSON in output: {res.stdout[-300:]}"}
    except subprocess.TimeoutExpired:
        return {"volume": 0, "faces": 0, "is_valid": False, "error": "FreeCAD timeout"}
    except Exception as e:
        return {"volume": 0, "faces": 0, "is_valid": False, "error": str(e)}


def score_one(tc: dict, geo: dict) -> dict:
    """Score a single test case. Returns dict with breakdown and total."""
    s = {"step_generated": 0, "volume": 0, "faces": 0, "bbox": 0, "total": 0, "notes": []}

    if geo.get("error"):
        s["notes"].append(f"STEP analysis error: {geo['error']}")
        return s

    # 30 pts: STEP generated + valid shape
    if geo.get("is_valid"):
        s["step_generated"] = 30
    else:
        s["step_generated"] = 15
        s["notes"].append("Shape not valid")

    # 30 pts: volume within tolerance
    exp_vol = tc["expected_volume"]
    got_vol = geo.get("volume", 0)
    if exp_vol > 0 and got_vol > 0:
        rel_err = abs(got_vol - exp_vol) / exp_vol
        if rel_err <= tc.get("vol_tol", 0.05):
            s["volume"] = 30
        elif rel_err <= tc.get("vol_tol", 0.05) * 3:
            s["volume"] = 15
            s["notes"].append(f"Volume off: got {got_vol:.1f}, expected {exp_vol:.1f} ({rel_err:.1%})")
        else:
            s["notes"].append(f"Volume WRONG: got {got_vol:.1f}, expected {exp_vol:.1f} ({rel_err:.1%})")
    else:
        s["notes"].append(f"Volume zero or missing (got {got_vol})")

    # 20 pts: face count within ±1
    exp_f = tc["expected_faces"]
    got_f = geo.get("faces", 0)
    if abs(got_f - exp_f) <= 1:
        s["faces"] = 20
    elif abs(got_f - exp_f) <= 3:
        s["faces"] = 10
        s["notes"].append(f"Faces off: got {got_f}, expected {exp_f}")
    else:
        s["notes"].append(f"Faces WRONG: got {got_f}, expected {exp_f}")

    # 20 pts: bounding box (each axis within tol, 20/3 pts each, sorted axes)
    exp_bb = sorted(tc.get("expected_bbox", (0, 0, 0)), reverse=True)
    got_bb = sorted([geo.get("bbox_x", 0), geo.get("bbox_y", 0), geo.get("bbox_z", 0)],
                    reverse=True)
    tol = tc.get("bbox_tol", 0.02)
    axis_score = 0
    for exp_a, got_a in zip(exp_bb, got_bb):
        if exp_a > 0:
            err = abs(got_a - exp_a) / exp_a
            if err <= tol:
                axis_score += 1
            else:
                s["notes"].append(f"BBox axis off: got {got_a:.2f}, expected {exp_a:.2f} ({err:.1%})")
    s["bbox"] = round(axis_score / 3 * 20)

    s["total"] = s["step_generated"] + s["volume"] + s["faces"] + s["bbox"]
    return s


def submit_job(dxf_path: Path, thickness: float, multiview: bool = False) -> str | None:
    """POST a DXF to the API. Returns job_id or None on failure."""
    with open(dxf_path, "rb") as f:
        try:
            resp = requests.post(
                f"{API}/api/dxf2step/jobs",
                files={"file": (dxf_path.name, f, "application/octet-stream")},
                data={
                    "default_thickness_mm": thickness,
                    "manual_mode": False,
                },
                timeout=15,
            )
            resp.raise_for_status()
            return resp.json()["job_id"]
        except Exception as e:
            print(f"    Submit failed: {e}")
            return None


def wait_for_job(job_id: str, timeout: int = 180) -> dict:
    """Poll job status until done or timeout."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            r = requests.get(f"{API}/api/dxf2step/jobs/{job_id}", timeout=10)
            status = r.json()
            state = status.get("state", "")
            prog  = status.get("progress", 0)
            cur   = status.get("current", "")[:60]
            print(f"\r    [{state}] {prog:.0%}  {cur:<60}", end="", flush=True)
            if state in ("done", "failed"):
                print()
                return status
        except Exception:
            pass
        time.sleep(3)
    print("\n    TIMEOUT")
    return {"state": "timeout"}


def find_step(job_id: str, tc_id: str) -> str | None:
    """Return host path to the best STEP file in this job's output."""
    job_dir = JOBS_DIR / job_id / "output"
    if not job_dir.exists():
        return None
    # Prefer combined.step (multi-view), else first *.step
    preferred = job_dir / "combined.step"
    if preferred.exists():
        return str(preferred)
    steps = list(job_dir.glob("*.step"))
    if steps:
        return str(steps[0])
    return None


def run_round(round_num: int) -> dict:
    """Run all tests, return {tc_id: {score, geo, status}} dict."""
    print(f"\n{'='*60}")
    print(f"  ROUND {round_num}")
    print(f"{'='*60}")

    results = {}

    for tc in TESTS:
        tc_id  = tc["id"]
        dxf_p  = DXF_DIR / f"{tc_id}.dxf"
        print(f"\n[{tc_id}] {tc['desc']}")

        if not dxf_p.exists():
            print(f"  DXF not found: {dxf_p}")
            results[tc_id] = {"score": {"total": 0}, "geo": {}, "state": "no_dxf"}
            continue

        # Submit
        job_id = submit_job(dxf_p, tc["thickness"], tc.get("multiview", False))
        if not job_id:
            results[tc_id] = {"score": {"total": 0}, "geo": {}, "state": "submit_failed"}
            continue

        print(f"  job_id: {job_id}")

        # Wait
        status = wait_for_job(job_id)
        state  = status.get("state", "unknown")

        if state != "done":
            print(f"  FAILED: {status.get('current', '')}")
            results[tc_id] = {"score": {"total": 0}, "geo": {}, "state": state,
                              "error": status.get("current", "")}
            continue

        # Find STEP
        step_path = find_step(job_id, tc_id)
        if not step_path:
            print("  No STEP file found in output")
            results[tc_id] = {"score": {"total": 0}, "geo": {}, "state": "no_step"}
            continue

        print(f"  STEP: {Path(step_path).name}")

        # Analyse
        geo = analyse_step(step_path)
        print(f"  Geometry: vol={geo.get('volume',0):.1f}  faces={geo.get('faces',0)}"
              f"  bbox=({geo.get('bbox_x',0):.1f},{geo.get('bbox_y',0):.1f},{geo.get('bbox_z',0):.1f})"
              f"  valid={geo.get('is_valid',False)}")
        if geo.get("error"):
            print(f"  Analysis error: {geo['error']}")

        # Score
        sc = score_one(tc, geo)
        for note in sc.get("notes", []):
            print(f"  NOTE: {note}")
        print(f"  SCORE: {sc['total']}/100"
              f"  (step={sc['step_generated']} vol={sc['volume']} "
              f"faces={sc['faces']} bbox={sc['bbox']})")

        results[tc_id] = {"score": sc, "geo": geo, "state": state, "job_id": job_id}

    return results


def overall(results: dict) -> float:
    scores = [v["score"]["total"] for v in results.values()]
    return round(sum(scores) / len(scores), 1) if scores else 0.0


def save_results(results: dict, round_num: int, score: float):
    path = TESTS_DIR / f"results_round{round_num:02d}.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"round": round_num, "overall": score, "tests": results},
                  f, ensure_ascii=False, indent=2)
    print(f"\nResults saved: {path.name}")


if __name__ == "__main__":
    import generate_dxfs
    print("Generating DXF test files...")
    generate_dxfs.gen_circle()
    generate_dxfs.gen_semicircle()
    generate_dxfs.gen_right_triangle()
    generate_dxfs.gen_rect_simple()
    generate_dxfs.gen_pentagon()
    generate_dxfs.gen_hexagon()
    generate_dxfs.gen_l_shape()
    generate_dxfs.gen_u_shape()
    generate_dxfs.gen_arc_rect()
    generate_dxfs.gen_t_shape()
    generate_dxfs.gen_multiview_cube()
    generate_dxfs.gen_multiview_lbracket()

    round_num = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    results = run_round(round_num)
    sc = overall(results)
    save_results(results, round_num, sc)

    print(f"\n{'='*60}")
    print(f"  OVERALL SCORE: {sc:.1f}/100")
    print(f"{'='*60}")

    # Per-test summary table
    print(f"\n{'ID':<22} {'Score':>6}  Breakdown")
    for tc in TESTS:
        tid = tc["id"]
        r = results.get(tid, {})
        s = r.get("score", {})
        tot = s.get("total", 0)
        notes = "; ".join(s.get("notes", [])) or "OK"
        print(f"  {tid:<20} {tot:>5}/100  {notes}")
