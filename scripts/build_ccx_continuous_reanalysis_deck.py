"""Build a multi-step CalculiX cooling/shrinkage/warpage reanalysis deck from mapped history includes."""
from __future__ import annotations

import sys
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import argparse
import csv
import json
import math
import re
import shutil
from pathlib import Path


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def strip_existing_steps(deck_text: str) -> str:
    upper = deck_text.upper()
    idx = upper.find("*STEP")
    return deck_text[:idx].rstrip() + "\n" if idx >= 0 else deck_text.rstrip() + "\n"


def _c3d4_element_ids(deck_text: str) -> set[int]:
    element_ids: set[int] = set()
    in_c3d4_block = False
    for line in deck_text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("**"):
            continue
        if stripped.startswith("*"):
            upper = stripped.upper().replace(" ", "")
            type_match = re.search(r"(?:^|,)TYPE=([^,]+)", upper)
            in_c3d4_block = upper.startswith("*ELEMENT") and type_match is not None and type_match.group(1) == "C3D4"
            continue
        if in_c3d4_block:
            try:
                element_id = int(stripped.split(",", 1)[0].strip())
            except ValueError as exc:
                raise ValueError("invalid C3D4 element row in base deck") from exc
            if element_id in element_ids:
                raise ValueError(f"duplicate C3D4 element ID in base deck: {element_id}")
            element_ids.add(element_id)
    return element_ids


def _reject_conflicting_initial_strain_state(deck_text: str) -> None:
    """Reject pre-step states that conflict with CalculiX initial-strain input."""
    for line in strip_existing_steps(deck_text).splitlines():
        normalized = line.strip().upper().replace(" ", "")
        if not normalized.startswith("*INITIALCONDITIONS"):
            continue
        if "TYPE=STRESS" in normalized or "TYPE=PLASTICSTRAIN" in normalized:
            raise ValueError(
                "base deck already defines initial stress/plastic strain; "
                "cannot safely add *INITIAL STRAIN INCREASE"
            )


def _integration_point_map(value: object, expected_count: int) -> dict[int, int]:
    if not isinstance(value, dict) or len(value) != expected_count:
        raise ValueError("element_integration_points must map every eigenstrain target")
    parsed: dict[int, int] = {}
    for raw_element_id, count in value.items():
        if not isinstance(raw_element_id, str) or re.fullmatch(r"[1-9][0-9]*", raw_element_id) is None:
            raise ValueError("element_integration_points keys must be canonical positive element IDs")
        element_id = int(raw_element_id)
        if element_id in parsed or type(count) is not int or count <= 0:
            raise ValueError("element_integration_points values must be positive integer counts")
        parsed[element_id] = count
    return parsed


def _history_source(history_manifest: Path, name: object) -> Path:
    if not isinstance(name, str) or not name or Path(name).is_absolute() or Path(name).name != name:
        raise ValueError(f"history include must be a local filename: {name!r}")
    source = history_manifest.parent / name
    if not source.is_file():
        raise FileNotFoundError(source)
    return source


def _read_eigenstrain_csv(path: Path, expected_count: int) -> list[tuple[int, float]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames != ["target_id", "eigenstrain"]:
            raise ValueError(f"invalid eigenstrain CSV header: {path}")
        rows = []
        for row in reader:
            try:
                target_id = int(row["target_id"])
                eigenstrain = float(row["eigenstrain"])
            except (TypeError, ValueError) as exc:
                raise ValueError(f"invalid eigenstrain CSV row: {path}") from exc
            if target_id <= 0 or not math.isfinite(eigenstrain):
                raise ValueError(f"invalid eigenstrain target/value: {path}")
            rows.append((target_id, eigenstrain))
    ids = [target_id for target_id, _ in rows]
    if len(rows) != expected_count or len(set(ids)) != len(ids):
        raise ValueError(f"eigenstrain CSV must contain {expected_count} unique target IDs: {path}")
    return rows


def _initial_plastic_strain_include(target_ids: list[int], integration_points: dict[int, int]) -> str:
    return (
        "** Zero initial strain state required by CalculiX *INITIAL STRAIN INCREASE\n"
        "*INITIAL CONDITIONS, TYPE=PLASTIC STRAIN\n"
        + "".join(
            f"{target_id}, {point}, 0., 0., 0., 0., 0., 0.\n"
            for target_id in target_ids
            for point in range(1, integration_points[target_id] + 1)
        )
    )


def _initial_strain_increase_include(
    rows: list[tuple[int, float]],
    previous: dict[int, float],
    integration_points: dict[int, int],
) -> tuple[str, dict[int, float]]:
    current = dict(rows)
    increments = {target_id: value - previous.get(target_id, 0.0) for target_id, value in rows}
    content = (
        "** Increment from the previous total isotropic eigenstrain frame\n"
        "*INITIAL STRAIN INCREASE\n"
        + "".join(
            f"{target_id}, {point}, {increment:.12e}, {increment:.12e}, {increment:.12e}, 0., 0., 0.\n"
            for target_id, increment in increments.items()
            for point in range(1, integration_points[target_id] + 1)
        )
    )
    return content, current


def build_steps(manifest: dict, *, include_pressure_csv: bool) -> str:
    reference_state = manifest.get("reference_state") or {}
    shrinkage_counting = reference_state.get("shrinkage_counting")
    if shrinkage_counting not in {"cte_only", "eigenstrain_only"}:
        raise ValueError("reference_state.shrinkage_counting must be cte_only or eigenstrain_only")
    lines = [
        "** Continuous OpenFOAM-history-driven cooling/solidification/shrinkage/warpage reanalysis",
        "** Pressure CSV files are recorded for audit; face loading requires a validated face map.",
    ]
    previous = 0.0
    for i, frame in enumerate(manifest["frames"], start=1):
        time_s = float(frame["time_s"])
        dt = max(time_s - previous, 1e-9)
        previous = time_s
        lines.extend([
            f"*STEP, NLGEOM=YES, INC=100",
            f"*STATIC",
            f"{dt:.12e}, {dt:.12e}, 1e-09, {max(dt, 1e-9):.12e}",
        ])
        if shrinkage_counting == "eigenstrain_only":
            if not frame.get("eigenstrain_increment_include"):
                raise ValueError("every eigenstrain_only frame requires an initial-strain-increase include")
            lines.extend([
                f"*INCLUDE, INPUT={frame['eigenstrain_increment_include']}",
                f"** Element-mapped physical temperature retained for audit only: {frame['temperature_element_csv']}",
            ])
        else:
            if frame.get("eigenstrain_csv") or frame.get("eigenstrain_increment_include"):
                raise ValueError("cte_only frame must not contain eigenstrain loading")
            lines.append(f"*INCLUDE, INPUT={frame['temperature_include']}")
        if include_pressure_csv and frame.get("pressure_csv"):
            lines.append(f"** Pressure CSV for this frame: {frame['pressure_csv']}")
        lines.extend([
            "*NODE PRINT, NSET=ALLNODES",
            "U",
            "*EL PRINT, ELSET=POLYMER",
            "S",
            "*END STEP",
        ])
    return "\n".join(lines) + "\n"


def run(base_deck: Path, history_manifest: Path, output_dir: Path, *, include_pressure_csv: bool = True) -> dict:
    if output_dir.exists():
        raise FileExistsError(output_dir)
    base_text = _read_text(base_deck)
    manifest = json.loads(history_manifest.read_text(encoding="utf-8"))
    frames = manifest.get("frames")
    if (
        manifest.get("schema") != "clawstack.calculix.deck.export.v1"
        or manifest.get("status") != "WRITTEN_NOT_SOLVED"
        or not isinstance(frames, list)
        or not frames
    ):
        raise ValueError("CalculiX history manifest with frames is required")
    target_count = manifest.get("target_count")
    if type(target_count) is not int or target_count <= 0:
        raise ValueError("positive integer target_count is required")
    reference_state = manifest.get("reference_state")
    reference_state = reference_state if isinstance(reference_state, dict) else {}
    shrinkage_counting = reference_state.get("shrinkage_counting")
    if shrinkage_counting not in {"cte_only", "eigenstrain_only"}:
        raise ValueError("reference_state.shrinkage_counting must be cte_only or eigenstrain_only")
    if (
        shrinkage_counting == "eigenstrain_only"
        and reference_state.get("eigenstrain_frame_semantics") != "total_from_stress_free"
    ):
        raise ValueError("eigenstrain_frame_semantics must be total_from_stress_free")
    if shrinkage_counting == "eigenstrain_only" and reference_state.get("strain_measure") != "green_lagrange":
        raise ValueError("strain_measure must be green_lagrange for NLGEOM eigenstrain loading")
    if (
        shrinkage_counting == "eigenstrain_only"
        and reference_state.get("reference_configuration") != "stress_free_geometry"
    ):
        raise ValueError("reference_configuration must be stress_free_geometry")
    if (
        shrinkage_counting == "eigenstrain_only"
        and reference_state.get("eigenstrain_value_kind") != "isotropic_normal_component"
    ):
        raise ValueError("eigenstrain_value_kind must be isotropic_normal_component")
    expected_target_entity = "element" if shrinkage_counting == "eigenstrain_only" else "node"
    if manifest.get("target_entity") != expected_target_entity:
        raise ValueError(f"{shrinkage_counting} requires target_entity={expected_target_entity}")
    integration_points = (
        _integration_point_map(manifest.get("element_integration_points"), target_count)
        if shrinkage_counting == "eigenstrain_only"
        else {}
    )
    if shrinkage_counting == "eigenstrain_only":
        _reject_conflicting_initial_strain_state(base_text)

    times = []
    sources: list[Path] = []
    eigenstrain_rows: list[list[tuple[int, float]]] = []
    for frame in frames:
        time_s = float(frame.get("time_s"))
        if not math.isfinite(time_s):
            raise ValueError("history frame times must be finite")
        times.append(time_s)
        temperature_source_key = (
            "temperature_element_csv" if shrinkage_counting == "eigenstrain_only" else "temperature_include"
        )
        sources.append(_history_source(history_manifest, frame.get(temperature_source_key)))
        if include_pressure_csv:
            sources.append(_history_source(history_manifest, frame.get("pressure_csv")))
        if shrinkage_counting == "eigenstrain_only":
            source = _history_source(history_manifest, frame.get("eigenstrain_csv"))
            sources.append(source)
            eigenstrain_rows.append(_read_eigenstrain_csv(source, target_count))
        elif frame.get("eigenstrain_csv"):
            raise ValueError("eigenstrain loading is forbidden when shrinkage_counting=cte_only")
    if any(right <= left for left, right in zip(times, times[1:])):
        raise ValueError("history frame times must be strictly increasing")

    strain_includes: list[tuple[str, str]] = []
    initialization_include = None
    if shrinkage_counting == "eigenstrain_only":
        target_ids = [target_id for target_id, _ in eigenstrain_rows[0]]
        if any([target_id for target_id, _ in rows] != target_ids for rows in eigenstrain_rows[1:]):
            raise ValueError("eigenstrain target IDs/order must match in every frame")
        if set(target_ids) != set(integration_points):
            raise ValueError("element_integration_points must exactly match eigenstrain target IDs")
        missing_elements = sorted(set(target_ids) - _c3d4_element_ids(base_text))
        if missing_elements:
            raise ValueError(f"eigenstrain targets must be C3D4 element IDs: {missing_elements[:10]}")
        invalid_point_counts = {
            element_id: integration_points[element_id]
            for element_id in target_ids
            if integration_points[element_id] != 1
        }
        if invalid_point_counts:
            raise ValueError(f"C3D4 eigenstrain targets require exactly one integration point: {invalid_point_counts}")
        initialization_include = "eigenstrain_initial.inc"
        previous: dict[int, float] = {}
        for index, rows in enumerate(eigenstrain_rows):
            name = f"eigenstrain_increment_{index:04d}.inc"
            content, previous = _initial_strain_increase_include(rows, previous, integration_points)
            frames[index]["eigenstrain_increment_include"] = name
            strain_includes.append((name, content))

    output_dir.mkdir(parents=True)
    copied = set()
    for source in sources:
        if source.name not in copied:
            shutil.copy2(source, output_dir / source.name)
            copied.add(source.name)
    if initialization_include:
        target_ids = [target_id for target_id, _ in eigenstrain_rows[0]]
        (output_dir / initialization_include).write_text(
            _initial_plastic_strain_include(target_ids, integration_points),
            encoding="ascii",
        )
    for name, content in strain_includes:
        (output_dir / name).write_text(content, encoding="ascii")
    body = strip_existing_steps(base_text)
    if initialization_include:
        body += f"*INCLUDE, INPUT={initialization_include}\n"
    body += build_steps(manifest, include_pressure_csv=include_pressure_csv)
    target = output_dir / "continuous_reanalysis.inp"
    target.write_text(body, encoding="utf-8")
    report = {
        "schema": "clawstack.ccx.continuous.reanalysis.deck.v1",
        "status": "WRITTEN_NOT_SOLVED",
        "deck": str(target.resolve()),
        "step_count": len(manifest["frames"]),
        "history_manifest": str(history_manifest.resolve()),
        "reference_state": manifest.get("reference_state"),
        "constraints": manifest.get("constraints"),
        "pressure_policy": "pressure_csv_audit_only_until_face_loading_map_is_validated" if include_pressure_csv else "disabled",
        "shrinkage_policy": {
            "counting": shrinkage_counting,
            "representation": "initial_strain_increase_isotropic_c3d4" if shrinkage_counting == "eigenstrain_only" else "mapped_temperature_with_material_cte",
            "physical_temperature_applied": shrinkage_counting == "cte_only",
            "target_entity": expected_target_entity,
            "element_integration_points": (
                {str(element_id): count for element_id, count in integration_points.items()}
                if shrinkage_counting == "eigenstrain_only"
                else None
            ),
        },
        "limitations": [
            "deck generation does not execute ccx",
            "pressure CSV is retained for audit; production DLOAD requires validated inner/outer face orientation mapping",
            "eigenstrain_only currently supports isotropic total strain histories on C3D4 elements with one integration point",
            "eigenstrain_only retains mapped physical temperature for audit but does not apply it because the current contract maps one target entity only",
            "true sink/warpage accuracy still depends on material calibration and constraint semantics",
        ],
    }
    (output_dir / "continuous_reanalysis_manifest.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-deck", type=Path, required=True)
    parser.add_argument("--history-manifest", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--no-pressure-csv", action="store_true")
    args = parser.parse_args()
    print(json.dumps(run(args.base_deck, args.history_manifest, args.output_dir, include_pressure_csv=not args.no_pressure_csv), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
