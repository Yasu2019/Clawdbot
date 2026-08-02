#!/usr/bin/env python3
"""Build a closed-gate cooling restart from an independent thermo fill case."""

import sys
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import argparse
import hashlib
import json
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path


REQUIRED_LATEST_FIELDS = ("U", "T", "alpha.polymer", "p_rgh")
REQUIRED_CONSTANT_FILES = ("thermophysicalProperties", "thermophysicalProperties.polymer")


def _numeric_time_dirs(case: Path) -> list[tuple[float, Path]]:
    found = []
    for child in case.iterdir():
        if not child.is_dir():
            continue
        try:
            found.append((float(child.name), child))
        except ValueError:
            continue
    return sorted(found, key=lambda item: item[0])


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _replace_dict_entry(text: str, key: str, value: str) -> str:
    pattern = rf"(?m)^(\s*){re.escape(key)}\s+[^;]+;"
    replacement = rf"\g<1>{key:<16}{value};"
    text, count = re.subn(pattern, replacement, text, count=1)
    if count != 1:
        raise ValueError(f"missing or duplicate controlDict entry: {key}")
    return text


def _patch_block_span(text: str, patch_name: str) -> tuple[int, int]:
    match = re.search(rf"(?m)^\s*{re.escape(patch_name)}\s*$", text)
    if not match:
        raise ValueError(f"boundary patch not found: {patch_name}")
    opening = text.find("{", match.end())
    if opening < 0:
        raise ValueError(f"opening brace not found for patch: {patch_name}")
    depth = 0
    for index in range(opening, len(text)):
        if text[index] == "{":
            depth += 1
        elif text[index] == "}":
            depth -= 1
            if depth == 0:
                return opening, index + 1
    raise ValueError(f"closing brace not found for patch: {patch_name}")


def _replace_patch(text: str, patch_name: str, body: str) -> str:
    start, end = _patch_block_span(text, patch_name)
    indented = "\n".join(f"        {line}" if line else "" for line in body.splitlines())
    return text[:start] + "{\n" + indented + "\n    }" + text[end:]


def _validate_source(source: Path) -> tuple[float, Path]:
    if not source.is_dir():
        raise ValueError(f"source case is not a directory: {source}")
    control = source / "system" / "controlDict"
    if not control.is_file():
        raise ValueError("source case has no system/controlDict")
    for name in REQUIRED_CONSTANT_FILES:
        if not (source / "constant" / name).is_file():
            raise ValueError(f"source is not a two-phase thermo case; missing constant/{name}")
    times = _numeric_time_dirs(source)
    if not times:
        raise ValueError("source case has no numeric result time")
    latest_value, latest_dir = times[-1]
    for name in REQUIRED_LATEST_FIELDS:
        if not (latest_dir / name).is_file():
            raise ValueError(f"latest time {latest_dir.name} is missing field {name}")
    return latest_value, latest_dir


def build_restart(
    source: Path,
    target: Path,
    *,
    gate_patch: str = "inlet",
    end_time: float = 30.0001,
    delta_t: float = 0.001,
    max_delta_t: float = 0.02,
    max_co: float = 0.5,
    max_alpha_co: float = 0.2,
    write_interval: float = 0.25,
    gate_temperature_k: float = 323.15,
) -> dict:
    source = source.resolve()
    target = target.resolve()
    latest_value, latest_source = _validate_source(source)
    if end_time <= latest_value:
        raise ValueError(f"end_time {end_time} must exceed latest source time {latest_value}")
    if target.exists():
        raise FileExistsError(f"target already exists; refusing overwrite: {target}")
    if target == source or source in target.parents:
        raise ValueError("target must be independent and outside the source case")

    try:
        shutil.copytree(source, target)
        latest = target / latest_source.name
        control_path = target / "system" / "controlDict"
        control = control_path.read_text(encoding="utf-8", errors="strict")
        for key, value in (
            ("startFrom", "latestTime"),
            ("startTime", f"{latest_value:g}"),
            ("stopAt", "endTime"),
            ("endTime", f"{end_time:g}"),
            ("deltaT", f"{delta_t:g}"),
            ("maxDeltaT", f"{max_delta_t:g}"),
            ("maxCo", f"{max_co:g}"),
            ("maxAlphaCo", f"{max_alpha_co:g}"),
            ("writeControl", "adjustableRunTime"),
            ("writeInterval", f"{write_interval:g}"),
        ):
            control = _replace_dict_entry(control, key, value)
        control_path.write_text(control, encoding="utf-8")

        boundary_bodies = {
            "U": "type            fixedValue;\nvalue           uniform (0 0 0);",
            "alpha.polymer": "type            zeroGradient;",
            "T": f"type            fixedValue;\nvalue           uniform {gate_temperature_k:g};",
            "p_rgh": "type            fixedFluxPressure;\nvalue           uniform 0;",
        }
        for field, body in boundary_bodies.items():
            path = latest / field
            updated = _replace_patch(path.read_text(encoding="utf-8", errors="strict"), gate_patch, body)
            path.write_text(updated, encoding="utf-8")

        manifest = {
            "schema": "openfoam_cooling_restart_v1",
            "created_at_utc": datetime.now(timezone.utc).isoformat(),
            "source_case": str(source),
            "target_case": str(target),
            "source_latest_time_s": latest_value,
            "source_control_dict_sha256": _sha256(source / "system" / "controlDict"),
            "gate_patch": gate_patch,
            "gate_state": "closed_no_slip_isothermal",
            "gate_temperature_k": gate_temperature_k,
            "cooling_end_time_s": end_time,
            "time_controls": {
                "deltaT": delta_t,
                "maxDeltaT": max_delta_t,
                "maxCo": max_co,
                "maxAlphaCo": max_alpha_co,
                "writeInterval": write_interval,
            },
            "accuracy_label": "PROXY_GAP",
            "promotion_blockers": [
                "solver run not yet completed",
                "Moldflow temperature and ejection-time tolerances not yet passed",
                "repeatability not yet demonstrated",
            ],
        }
        manifest_path = target / "cooling_restart_manifest.json"
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        return manifest
    except Exception:
        if target.exists():
            shutil.rmtree(target)
        raise


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("target", type=Path)
    parser.add_argument("--gate-patch", default="inlet")
    parser.add_argument("--end-time", type=float, default=30.0001)
    parser.add_argument("--delta-t", type=float, default=0.001)
    parser.add_argument("--max-delta-t", type=float, default=0.02)
    parser.add_argument("--max-co", type=float, default=0.5)
    parser.add_argument("--max-alpha-co", type=float, default=0.2)
    parser.add_argument("--write-interval", type=float, default=0.25)
    parser.add_argument("--gate-temperature-k", type=float, default=323.15)
    args = parser.parse_args()
    manifest = build_restart(
        args.source,
        args.target,
        gate_patch=args.gate_patch,
        end_time=args.end_time,
        delta_t=args.delta_t,
        max_delta_t=args.max_delta_t,
        max_co=args.max_co,
        max_alpha_co=args.max_alpha_co,
        write_interval=args.write_interval,
        gate_temperature_k=args.gate_temperature_k,
    )
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
