#!/usr/bin/env python3
"""Extract traceable polymer bulk-temperature proxies from a VOF fill run."""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

SCHEMA = "clawstack.moldflow_bulk_temperature_kpi.v1"
NUMBER = r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?"


def _values(path: Path) -> list[float]:
    text = path.read_text(encoding="utf-8", errors="replace")
    uniform = re.search(r"internalField\s+uniform\s+(" + NUMBER + r")\s*;", text)
    if uniform:
        return [float(uniform.group(1))]
    match = re.search(
        r"internalField\s+nonuniform\s+List<scalar>\s+\d+\s*\((.*?)\)\s*;",
        text,
        re.DOTALL,
    )
    if not match:
        raise ValueError(f"cannot parse internalField: {path}")
    return [float(x) for x in re.findall(NUMBER, match.group(1))]


def _latest_time(run_dir: Path) -> Path:
    rows = []
    for path in run_dir.iterdir():
        if not path.is_dir() or not (path / "T").exists() or not (path / "alpha.polymer").exists():
            continue
        try:
            rows.append((float(path.name), path))
        except ValueError:
            pass
    if not rows:
        raise ValueError("no paired T and alpha.polymer time directory")
    return max(rows, key=lambda row: row[0])[1]


def _data_rows(path: Path) -> list[list[float]]:
    rows = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        values = [float(x) for x in re.findall(NUMBER, line)]
        if values:
            rows.append(values)
    return rows


def _history(run_dir: Path) -> tuple[float | None, float | None, int]:
    peak_k = None
    bulk_peak_k = None
    samples = 0
    for path in (run_dir / "postProcessing" / "thermalFieldMinMax").rglob("*.dat") if (run_dir / "postProcessing" / "thermalFieldMinMax").exists() else []:
        pattern = re.compile(
            r"^\s*(" + NUMBER + r")\s+T\s+(" + NUMBER + r")\s+\([^)]*\)\s+(" + NUMBER + r")\s+\([^)]*\)",
            re.MULTILINE,
        )
        for match in pattern.finditer(path.read_text(encoding="utf-8", errors="replace")):
            maximum_k = float(match.group(3))
            peak_k = max(peak_k or maximum_k, maximum_k)
            samples += 1
    for path in (run_dir / "postProcessing" / "polymerBulkTemperature").rglob("*.dat") if (run_dir / "postProcessing" / "polymerBulkTemperature").exists() else []:
        for row in _data_rows(path):
            if len(row) >= 2:
                bulk_peak_k = max(bulk_peak_k or row[-1], row[-1])
    return peak_k, bulk_peak_k, samples


def extract(run_dir: Path, commercial_reference_c: float | None = None) -> dict:
    run_dir = run_dir.resolve()
    latest = _latest_time(run_dir)
    alpha = _values(latest / "alpha.polymer")
    temperature = _values(latest / "T")
    if len(alpha) != len(temperature):
        raise ValueError("T and alpha.polymer cell counts differ")
    polymer_cells = [t for a, t in zip(alpha, temperature) if a >= 0.5]
    if not polymer_cells:
        raise ValueError("no polymer-dominant cells (alpha >= 0.5)")
    alpha_sum = sum(alpha)
    weighted_k = sum(a * t for a, t in zip(alpha, temperature)) / alpha_sum
    history_peak_k, history_bulk_peak_k, history_samples = _history(run_dir)
    selected_k = history_peak_k if history_peak_k is not None else max(polymer_cells)
    source = "runtime fieldMinMax(T) history" if history_peak_k is not None else "latest polymer-dominant cell maximum"
    selected_c = selected_k - 273.15
    result = {
        "schema": SCHEMA,
        "run_dir": str(run_dir),
        "definition": "maximum bulk-temperature proxy with polymer-phase diagnostics",
        "comparison_validity": "proxy; one-cell thickness makes polymer cell T a through-thickness bulk approximation",
        "time_s": float(latest.name),
        "polymer_cell_alpha_threshold": 0.5,
        "latest_polymer_max_temperature_c": round(max(polymer_cells) - 273.15, 6),
        "latest_alpha_weighted_mean_temperature_c": round(weighted_k - 273.15, 6),
        "history_max_temperature_c": round(history_peak_k - 273.15, 6) if history_peak_k is not None else None,
        "history_peak_alpha_weighted_bulk_temperature_c": round(history_bulk_peak_k - 273.15, 6) if history_bulk_peak_k is not None else None,
        "history_sample_count": history_samples,
        "maximum_bulk_temperature_proxy_c": round(selected_c, 6),
        "kpi_source": source,
    }
    if commercial_reference_c is not None:
        delta = selected_c - commercial_reference_c
        result.update(
            {
                "commercial_reference_c": commercial_reference_c,
                "difference_c": round(delta, 6),
                "absolute_error_pct": round(abs(delta) / commercial_reference_c * 100.0, 4),
            }
        )
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("run_dir", type=Path)
    parser.add_argument("--commercial-reference-c", type=float)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = extract(args.run_dir, args.commercial_reference_c)
    output = args.output or args.run_dir / "bulk_temperature_kpi.json"
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
