#!/usr/bin/env python3
"""Extract a comparable gate-pressure KPI from an OpenFOAM Moldflow run.

The commercial reference reports maximum injection pressure.  For the
OpenFOAM proxy we use the maximum, over written time directories, of the
area-average absolute pressure on every enabled injection-gate patch, minus
the initial ambient absolute pressure.  With the current structured gate
mesh all faces on a gate patch have equal area, so the arithmetic face mean
is also the area mean.  The JSON explicitly records this limitation instead
of presenting the value as commercial-equivalent without qualification.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

SCHEMA = "clawstack.moldflow_injection_pressure_kpi.v1"


def _number_list(text: str) -> list[float]:
    return [float(x) for x in re.findall(r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?", text)]


def _patch_body(field_text: str, patch: str) -> str | None:
    boundary = field_text.find("boundaryField")
    if boundary < 0:
        return None
    match = re.search(rf"(?m)^\s*{re.escape(patch)}\s*$", field_text[boundary:])
    if not match:
        return None
    start = boundary + match.end()
    brace = field_text.find("{", start)
    if brace < 0:
        return None
    depth = 0
    for pos in range(brace, len(field_text)):
        char = field_text[pos]
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return field_text[brace + 1 : pos]
    return None


def _field_values(body: str) -> list[float]:
    nonuniform = re.search(
        r"\bvalue\s+nonuniform\s+List<scalar>\s+\d+\s*\((.*?)\)\s*;",
        body,
        flags=re.DOTALL,
    )
    if nonuniform:
        return _number_list(nonuniform.group(1))
    compact = re.search(
        r"\bvalue\s+nonuniform\s+List<scalar>\s+\d+\s*\((.*?)\)\s*;",
        body,
        flags=re.DOTALL,
    )
    if compact:
        return _number_list(compact.group(1))
    uniform = re.search(r"\bvalue\s+uniform\s+([-+0-9.eE]+)\s*;", body)
    return [float(uniform.group(1))] if uniform else []


def _ambient_pressure(run_dir: Path) -> float:
    initial = (run_dir / "0" / "p").read_text(encoding="utf-8", errors="replace")
    match = re.search(r"internalField\s+uniform\s+([-+0-9.eE]+)\s*;", initial)
    if not match:
        raise ValueError("0/p has no uniform initial absolute pressure")
    return float(match.group(1))


def _enabled_gate_patches(run_dir: Path) -> list[str]:
    spec = json.loads((run_dir / "gate_spec.resolved.json").read_text(encoding="utf-8-sig"))
    return [
        str(gate["patch"])
        for gate in spec.get("gates", [])
        if gate.get("enabled", True) and gate.get("patch")
    ]


def extract(run_dir: Path, commercial_reference_mpa: float | None = None) -> dict:
    run_dir = run_dir.resolve()
    ambient_pa = _ambient_pressure(run_dir)
    gates = _enabled_gate_patches(run_dir)
    if not gates:
        raise ValueError("no enabled injection gate patches")

    samples: list[dict] = []
    time_dirs = sorted(
        ((float(p.name), p) for p in run_dir.iterdir() if p.is_dir() and _is_float(p.name)),
        key=lambda row: row[0],
    )
    for time_s, time_dir in time_dirs:
        if time_s <= 0 or not (time_dir / "p").exists():
            continue
        field = (time_dir / "p").read_text(encoding="utf-8", errors="replace")
        for gate in gates:
            body = _patch_body(field, gate)
            values = _field_values(body or "")
            if not values:
                continue
            average_abs = sum(values) / len(values)
            samples.append(
                {
                    "time_s": time_s,
                    "gate_patch": gate,
                    "face_count": len(values),
                    "average_absolute_pa": average_abs,
                    "average_gauge_pa": average_abs - ambient_pa,
                    "maximum_face_absolute_pa": max(values),
                    "maximum_face_gauge_pa": max(values) - ambient_pa,
                }
            )
    if not samples:
        raise ValueError("no written gate pressure samples found")
    peak = max(samples, key=lambda row: row["average_gauge_pa"])
    measured_mpa = peak["average_gauge_pa"] / 1e6
    result = {
        "schema": SCHEMA,
        "run_dir": str(run_dir),
        "definition": "maximum written-time gate-patch face-average gauge pressure",
        "pressure_field": "p (absolute)",
        "ambient_absolute_pa": ambient_pa,
        "gate_patches": gates,
        "written_time_sample_count": len({row["time_s"] for row in samples}),
        "maximum_injection_pressure_proxy_mpa": round(measured_mpa, 6),
        "peak_time_s": peak["time_s"],
        "peak_gate_patch": peak["gate_patch"],
        "peak_face_average_absolute_pa": round(peak["average_absolute_pa"], 3),
        "peak_face_maximum_gauge_mpa": round(peak["maximum_face_gauge_pa"] / 1e6, 6),
        "comparison_validity": "proxy; written-time sampling and equal-area structured gate faces",
        "samples": samples,
    }
    if commercial_reference_mpa is not None:
        delta = measured_mpa - commercial_reference_mpa
        result["commercial_reference_mpa"] = commercial_reference_mpa
        result["difference_mpa"] = round(delta, 6)
        result["absolute_error_pct"] = round(abs(delta) / commercial_reference_mpa * 100.0, 4)
    return result


def _is_float(value: str) -> bool:
    try:
        float(value)
        return True
    except ValueError:
        return False


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("run_dir", type=Path)
    parser.add_argument("--commercial-reference-mpa", type=float)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = extract(args.run_dir, args.commercial_reference_mpa)
    output = args.output or args.run_dir / "injection_pressure_kpi.json"
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
