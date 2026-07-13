#!/usr/bin/env python3
"""Extract shear-rate and mold-wall shear-stress proxies from a 3-D VOF run."""
from __future__ import annotations

import argparse
import json
import math
import re
from pathlib import Path

SCHEMA = "clawstack.moldflow_shear_kpi.v1"
NUMBER = r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?"


def _shear_rate_history(run_dir: Path) -> list[dict]:
    root = run_dir / "postProcessing" / "shearRateMinMax"
    pattern = re.compile(
        r"^\s*(" + NUMBER + r")\s+shearRateProxy\s+(" + NUMBER + r")\s+\(([^)]*)\)\s+(" + NUMBER + r")\s+\(([^)]*)\)",
        re.MULTILINE,
    )
    rows = []
    for path in root.rglob("*.dat") if root.exists() else []:
        for match in pattern.finditer(path.read_text(encoding="utf-8", errors="replace")):
            rows.append(
                {
                    "time_s": float(match.group(1)),
                    "maximum_1_s": float(match.group(4)),
                    "location_m": [float(x) for x in match.group(5).split()],
                }
            )
    return rows


def _wall_history(run_dir: Path) -> list[dict]:
    root = run_dir / "postProcessing" / "moldWallShearStress"
    pattern = re.compile(
        r"^\s*(" + NUMBER + r")\s+frontAndBack\s+\(([^)]*)\)\s+\(([^)]*)\)",
        re.MULTILINE,
    )
    rows = []
    for path in root.rglob("*.dat") if root.exists() else []:
        for match in pattern.finditer(path.read_text(encoding="utf-8", errors="replace")):
            vectors = [[float(x) for x in match.group(i).split()] for i in (2, 3)]
            rows.append(
                {
                    "time_s": float(match.group(1)),
                    "component_extrema_vector_magnitudes_pa": [
                        math.sqrt(sum(value * value for value in vector)) for vector in vectors
                    ],
                }
            )
    return rows


def _latest_wall_exact_max(run_dir: Path) -> tuple[float | None, float | None]:
    times = []
    for path in run_dir.iterdir():
        if not path.is_dir() or not (path / "wallShearStress").exists():
            continue
        try:
            times.append((float(path.name), path))
        except ValueError:
            pass
    if not times:
        return None, None
    time_s, latest = max(times, key=lambda row: row[0])
    text = (latest / "wallShearStress").read_text(encoding="utf-8", errors="replace")
    boundary = text.find("boundaryField")
    match = re.search(r"(?m)^\s*frontAndBack\s*$", text[boundary:])
    if not match:
        return time_s, None
    start = boundary + match.end()
    brace = text.find("{", start)
    if brace < 0:
        return time_s, None
    depth = 0
    end = None
    for position in range(brace, len(text)):
        if text[position] == "{":
            depth += 1
        elif text[position] == "}":
            depth -= 1
            if depth == 0:
                end = position
                break
    if end is None:
        return time_s, None
    body = text[brace + 1 : end]
    marker = re.search(r"List<vector>\s+\d+", body)
    if not marker:
        return time_s, None
    outer_start = body.find("(", marker.end())
    if outer_start < 0:
        return time_s, None
    depth = 0
    outer_end = None
    for position in range(outer_start, len(body)):
        if body[position] == "(":
            depth += 1
        elif body[position] == ")":
            depth -= 1
            if depth == 0:
                outer_end = position
                break
    if outer_end is None:
        return time_s, None
    vectors = re.findall(r"\(([^()]*)\)", body[outer_start + 1 : outer_end])
    magnitudes = []
    for vector in vectors:
        components = [float(x) for x in vector.split()]
        if len(components) == 3:
            magnitudes.append(math.sqrt(sum(value * value for value in components)))
    return time_s, max(magnitudes) if magnitudes else None


def extract(
    run_dir: Path,
    commercial_shear_rate_1_s: float | None = None,
    commercial_wall_stress_mpa: float | None = None,
    startup_exclusion_s: float = 0.01,
) -> dict:
    run_dir = run_dir.resolve()
    manifest = json.loads((run_dir / "cad_manifest.json").read_text(encoding="utf-8-sig"))
    if int(manifest.get("mesh_nz", 1)) <= 1:
        raise ValueError("wall shear requires resolved thickness (mesh_nz > 1)")
    shear_rows = _shear_rate_history(run_dir)
    wall_rows = _wall_history(run_dir)
    if not shear_rows or not wall_rows:
        raise ValueError("shear runtime histories are missing")
    global_peak = max(shear_rows, key=lambda row: row["maximum_1_s"])
    stable_rows = [row for row in shear_rows if row["time_s"] >= startup_exclusion_s]
    if not stable_rows:
        raise ValueError("no shear-rate samples after startup exclusion")
    stable_peak = max(stable_rows, key=lambda row: row["maximum_1_s"])
    wall_conservative = max(
        max(row["component_extrema_vector_magnitudes_pa"]) for row in wall_rows
    )
    wall_time, wall_exact_latest = _latest_wall_exact_max(run_dir)
    wall_selected_pa = wall_conservative
    result = {
        "schema": SCHEMA,
        "run_dir": str(run_dir),
        "definition": "resolved-thickness grad(U) magnitude and mold-wall stress histories",
        "comparison_validity": "proxy; startup exclusion removes the first 1% fill transient, wall history is conservative component-extrema magnitude",
        "mesh_nz": int(manifest["mesh_nz"]),
        "startup_exclusion_s": startup_exclusion_s,
        "history_sample_count": len(shear_rows),
        "startup_global_max_shear_rate_1_s": round(global_peak["maximum_1_s"], 6),
        "startup_global_peak_time_s": global_peak["time_s"],
        "startup_global_peak_location_m": global_peak["location_m"],
        "max_shear_rate_proxy_1_s": round(stable_peak["maximum_1_s"], 6),
        "max_shear_rate_peak_time_s": stable_peak["time_s"],
        "max_shear_rate_peak_location_m": stable_peak["location_m"],
        "max_wall_shear_stress_proxy_mpa": round(wall_selected_pa / 1e6, 6),
        "latest_exact_wall_shear_stress_mpa": (
            round(wall_exact_latest / 1e6, 6) if wall_exact_latest is not None else None
        ),
        "latest_wall_shear_time_s": wall_time,
    }
    if commercial_shear_rate_1_s is not None:
        measured = stable_peak["maximum_1_s"]
        result["commercial_max_shear_rate_1_s"] = commercial_shear_rate_1_s
        result["max_shear_rate_error_pct"] = round(
            abs(measured - commercial_shear_rate_1_s) / commercial_shear_rate_1_s * 100.0, 4
        )
    if commercial_wall_stress_mpa is not None:
        measured = wall_selected_pa / 1e6
        result["commercial_max_wall_shear_stress_mpa"] = commercial_wall_stress_mpa
        result["max_wall_shear_stress_error_pct"] = round(
            abs(measured - commercial_wall_stress_mpa) / commercial_wall_stress_mpa * 100.0, 4
        )
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("run_dir", type=Path)
    parser.add_argument("--commercial-shear-rate-1-s", type=float)
    parser.add_argument("--commercial-wall-stress-mpa", type=float)
    parser.add_argument("--startup-exclusion-s", type=float, default=0.01)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = extract(
        args.run_dir,
        args.commercial_shear_rate_1_s,
        args.commercial_wall_stress_mpa,
        args.startup_exclusion_s,
    )
    output = args.output or args.run_dir / "shear_kpi.json"
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
