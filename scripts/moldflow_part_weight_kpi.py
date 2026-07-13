#!/usr/bin/env python3
"""Extract a density-based molded-part weight proxy from a VOF run."""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

SCHEMA = "clawstack.moldflow_part_weight_kpi.v1"


def _latest_time_dir(run_dir: Path) -> Path:
    rows = []
    for path in run_dir.iterdir():
        if not path.is_dir():
            continue
        try:
            time_s = float(path.name)
        except ValueError:
            continue
        if time_s > 0 and (path / "alpha.polymer").exists():
            rows.append((time_s, path))
    if not rows:
        raise ValueError("no written alpha.polymer time directory")
    return max(rows, key=lambda row: row[0])[1]


def _alpha_mean(path: Path) -> float:
    text = path.read_text(encoding="utf-8", errors="replace")
    uniform = re.search(r"internalField\s+uniform\s+([-+0-9.eE]+)\s*;", text)
    if uniform:
        return float(uniform.group(1))
    match = re.search(
        r"internalField\s+nonuniform\s+List<scalar>\s+\d+\s*\((.*?)\)\s*;",
        text,
        flags=re.DOTALL,
    )
    if not match:
        raise ValueError("cannot parse alpha.polymer internalField")
    values = [float(x) for x in re.findall(r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?", match.group(1))]
    if not values:
        raise ValueError("alpha.polymer has no cell values")
    return sum(values) / len(values)


def _polymer_density(run_dir: Path) -> float:
    path = run_dir / "constant" / "thermophysicalProperties.polymer"
    text = path.read_text(encoding="utf-8", errors="replace")
    match = re.search(r"\bequationOfState\s*\{[^}]*\brho\s+([-+0-9.eE]+)\s*;", text, re.DOTALL)
    if not match:
        raise ValueError("constant polymer density not found")
    return float(match.group(1))


def extract(run_dir: Path, commercial_reference_g: float | None = None) -> dict:
    run_dir = run_dir.resolve()
    manifest = json.loads((run_dir / "cad_manifest.json").read_text(encoding="utf-8-sig"))
    if manifest.get("mesh_mode") != "blockmesh_bbox":
        raise ValueError("weight extractor currently requires blockmesh_bbox")
    bbox = manifest["bbox_mm"]
    cavity_mm3 = float(bbox["length"]) * float(bbox["width"]) * float(bbox["height"])
    latest = _latest_time_dir(run_dir)
    alpha_mean = _alpha_mean(latest / "alpha.polymer")
    density = _polymer_density(run_dir)
    polymer_volume_mm3 = cavity_mm3 * alpha_mean
    # kg/m3 * mm3 = 1e-6 g
    weight_g = density * polymer_volume_mm3 * 1e-6
    result = {
        "schema": SCHEMA,
        "run_dir": str(run_dir),
        "definition": "cell-mean alpha times bbox cavity volume times constant polymer density",
        "comparison_validity": "proxy; equal-volume structured blockMesh cells and no runner volume",
        "time_s": float(latest.name),
        "cavity_volume_mm3": round(cavity_mm3, 6),
        "polymer_volume_mm3": round(polymer_volume_mm3, 6),
        "alpha_cell_mean": round(alpha_mean, 8),
        "polymer_density_kg_m3": density,
        "part_weight_proxy_g": round(weight_g, 6),
    }
    if commercial_reference_g is not None:
        delta = weight_g - commercial_reference_g
        result.update(
            {
                "commercial_reference_g": commercial_reference_g,
                "difference_g": round(delta, 6),
                "absolute_error_pct": round(abs(delta) / commercial_reference_g * 100.0, 4),
                "required_effective_density_kg_m3": round(
                    commercial_reference_g / (polymer_volume_mm3 * 1e-6), 6
                ),
            }
        )
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("run_dir", type=Path)
    parser.add_argument("--commercial-reference-g", type=float)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = extract(args.run_dir, args.commercial_reference_g)
    output = args.output or args.run_dir / "part_weight_kpi.json"
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
