"""Generate and optionally solve a fail-closed CalculiX eigenstrain smoke case.

The fixture is a single C3D4 tetrahedron with minimum rigid-body constraints.
Two total isotropic contraction frames are passed through
``build_ccx_continuous_reanalysis_deck``.  A Docker solve is opt-in because
ordinary unit tests must not depend on a running Docker daemon.
"""
from __future__ import annotations

import sys
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import argparse
import hashlib
import json
import math
import os
import re
import shutil
import subprocess
from pathlib import Path

import build_ccx_continuous_reanalysis_deck as deck_builder


SCHEMA = "clawstack.ccx.eigenstrain.smoke.v1"
DEFAULT_IMAGE = "calculix/ccx:latest"
EDGE_LENGTH_M = 1.0e-2
TOTAL_EIGENSTRAINS = (-5.0e-3, -1.0e-2)
NODE_COORDINATES = {
    1: (0.0, 0.0, 0.0),
    2: (EDGE_LENGTH_M, 0.0, 0.0),
    3: (0.0, EDGE_LENGTH_M, 0.0),
    4: (0.0, 0.0, EDGE_LENGTH_M),
}
FREE_EDGE_COMPONENTS = ((2, 0), (3, 1), (4, 2))
ERROR_PATTERNS = ("*error", "nan", "segmentation fault", "aborted")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_fixture_inputs(root: Path) -> tuple[Path, Path]:
    source_dir = root / "source"
    history_dir = source_dir / "history"
    history_dir.mkdir(parents=True)
    base_deck = source_dir / "single_c3d4_base.inp"
    base_deck.write_text(
        "*HEADING\n"
        "Single C3D4 isotropic eigenstrain smoke; SI units (m, Pa)\n"
        "*NODE, NSET=ALLNODES\n"
        "1, 0., 0., 0.\n"
        "2, 1.000000000000e-02, 0., 0.\n"
        "3, 0., 1.000000000000e-02, 0.\n"
        "4, 0., 0., 1.000000000000e-02\n"
        "*ELEMENT, TYPE=C3D4, ELSET=POLYMER\n"
        "1, 1, 2, 3, 4\n"
        "*MATERIAL, NAME=POLYMER\n"
        "*ELASTIC\n"
        "2.000000000000e+09, 0.35\n"
        "*SOLID SECTION, ELSET=POLYMER, MATERIAL=POLYMER\n"
        "*BOUNDARY\n"
        "1, 1, 3, 0.\n"
        "2, 2, 3, 0.\n"
        "3, 3, 3, 0.\n",
        encoding="ascii",
    )

    frames = []
    for index, strain in enumerate(TOTAL_EIGENSTRAINS):
        temperature_name = f"temperature_element_{index:04d}.csv"
        eigenstrain_name = f"eigenstrain_{index:04d}.csv"
        (history_dir / temperature_name).write_text(
            "element_id,temperature_K\n1,293.15\n", encoding="ascii"
        )
        (history_dir / eigenstrain_name).write_text(
            f"target_id,eigenstrain\n1,{strain:.12e}\n", encoding="ascii"
        )
        frames.append(
            {
                "time_s": float(index + 1),
                "temperature_element_csv": temperature_name,
                "eigenstrain_csv": eigenstrain_name,
            }
        )
    manifest = {
        "schema": "clawstack.calculix.deck.export.v1",
        "status": "WRITTEN_NOT_SOLVED",
        "target_count": 1,
        "target_entity": "element",
        "element_integration_points": {"1": 1},
        "frames": frames,
        "reference_state": {
            "stress_free_temperature_K": 293.15,
            "shrinkage_counting": "eigenstrain_only",
            "eigenstrain_frame_semantics": "total_from_stress_free",
            "strain_measure": "green_lagrange",
            "reference_configuration": "stress_free_geometry",
            "eigenstrain_value_kind": "isotropic_normal_component",
        },
        "constraints": {
            "description": "minimum 3-2-1 constraints; orthogonal edges remain free to contract",
            "node_1": [1, 2, 3],
            "node_2": [2, 3],
            "node_3": [3],
        },
    }
    manifest_path = history_dir / "calculix_history_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return base_deck, manifest_path


def _add_result_requests(deck: Path, expected_steps: int) -> None:
    """Add FRD field requests without changing the production deck builder."""
    text = deck.read_text(encoding="utf-8")
    if text.upper().count("*END STEP") != expected_steps:
        raise ValueError("generated deck step count does not match the fixture contract")
    result_cards = "*NODE FILE\nU\n*EL FILE\nS\n*END STEP"
    text = re.sub(r"(?im)^\*END STEP\s*$", result_cards, text)
    deck.write_text(text, encoding="utf-8")


def generate_case(output_dir: Path) -> dict:
    if output_dir.exists() and any(output_dir.iterdir()):
        raise FileExistsError(f"output directory must be new or empty: {output_dir}")
    output_dir.mkdir(parents=True, exist_ok=True)
    base_deck, history_manifest = _write_fixture_inputs(output_dir)
    generated_dir = output_dir / "generated"
    build_report = deck_builder.run(
        base_deck,
        history_manifest,
        generated_dir,
        include_pressure_csv=False,
    )
    deck = Path(build_report["deck"])
    _add_result_requests(deck, expected_steps=len(TOTAL_EIGENSTRAINS))
    return {
        "base_deck": str(base_deck.resolve()),
        "history_manifest": str(history_manifest.resolve()),
        "generated_dir": str(generated_dir.resolve()),
        "deck": str(deck.resolve()),
        "deck_sha256": sha256(deck),
        "builder_schema": build_report["schema"],
        "builder_status": build_report["status"],
        "step_count": build_report["step_count"],
    }


def docker_mount_source(path: Path, *, platform_name: str | None = None) -> str:
    resolved = path.resolve(strict=True)
    if not resolved.is_dir():
        raise NotADirectoryError(resolved)
    text = str(resolved)
    if any(character in text for character in ("\x00", "\n", "\r", ",")):
        raise ValueError("Docker mount source contains an unsupported character")
    if (platform_name or os.name) == "nt":
        text = text.replace("\\", "/")
    return text


def probe_docker(image: str, *, pull: bool, timeout_s: int) -> dict:
    binary = shutil.which("docker")
    if binary is None:
        return {"available": False, "image_available": False, "reason": "docker_not_found"}
    try:
        version = subprocess.run(
            [binary, "version", "--format", "{{.Server.Version}}"],
            capture_output=True,
            text=True,
            timeout=min(timeout_s, 30),
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {
            "available": False,
            "image_available": False,
            "reason": "docker_daemon_unavailable",
            "detail": type(exc).__name__,
        }
    if version.returncode != 0:
        return {
            "available": False,
            "image_available": False,
            "reason": "docker_daemon_unavailable",
            "detail": (version.stderr or version.stdout or "").strip(),
        }

    inspect = subprocess.run(
        [binary, "image", "inspect", image, "--format", "{{.Id}}"],
        capture_output=True,
        text=True,
        timeout=min(timeout_s, 30),
    )
    pull_report = None
    if inspect.returncode != 0 and pull:
        pull_proc = subprocess.run(
            [binary, "pull", image],
            capture_output=True,
            text=True,
            timeout=timeout_s,
        )
        pull_report = {
            "returncode": pull_proc.returncode,
            "stdout_tail": (pull_proc.stdout or "")[-2000:],
            "stderr_tail": (pull_proc.stderr or "")[-2000:],
        }
        inspect = subprocess.run(
            [binary, "image", "inspect", image, "--format", "{{.Id}}"],
            capture_output=True,
            text=True,
            timeout=min(timeout_s, 30),
        )
    result = {
        "available": True,
        "image_available": inspect.returncode == 0,
        "docker_binary": binary,
        "server_version": version.stdout.strip(),
        "image": image,
        "image_id": inspect.stdout.strip() if inspect.returncode == 0 else None,
    }
    if pull_report is not None:
        result["pull"] = pull_report
    if inspect.returncode != 0:
        result["reason"] = "docker_image_not_found"
    return result


def _nonempty(path: Path) -> bool:
    return path.is_file() and path.stat().st_size > 0


def solve_with_docker(
    generated_dir: Path,
    *,
    image: str,
    docker_binary: str,
    timeout_s: int,
) -> dict:
    stem = "continuous_reanalysis"
    mount_source = docker_mount_source(generated_dir)
    command = [
        docker_binary,
        "run",
        "--rm",
        "--network",
        "none",
        "--mount",
        f"type=bind,source={mount_source},target=/work",
        "-w",
        "/work",
        image,
        "ccx",
        stem,
    ]
    try:
        proc = subprocess.run(command, capture_output=True, text=True, timeout=timeout_s)
        returncode = proc.returncode
        stdout = proc.stdout or ""
        stderr = proc.stderr or ""
        timed_out = False
    except subprocess.TimeoutExpired as exc:
        returncode = None
        stdout = exc.stdout.decode(errors="replace") if isinstance(exc.stdout, bytes) else (exc.stdout or "")
        stderr = exc.stderr.decode(errors="replace") if isinstance(exc.stderr, bytes) else (exc.stderr or "")
        stderr += f"\nDocker CalculiX solve timed out after {timeout_s} s\n"
        timed_out = True
    log_path = generated_dir / f"{stem}.log"
    log_path.write_text(stdout + "\n" + stderr, encoding="utf-8", errors="replace")
    paths = {suffix: generated_dir / f"{stem}.{suffix}" for suffix in ("dat", "frd", "sta")}
    present = {suffix: _nonempty(path) for suffix, path in paths.items()}
    combined = "\n".join(
        [stdout, stderr]
        + [path.read_text(encoding="utf-8", errors="replace") for path in paths.values() if path.is_file()]
    )
    clean = not any(pattern in combined.lower() for pattern in ERROR_PATTERNS)
    finished = "job finished" in combined.lower()
    frd_has_displacement = present["frd"] and "DISP" in paths["frd"].read_text(
        encoding="utf-8", errors="replace"
    ).upper()
    passed = (
        returncode == 0
        and all(present.values())
        and clean
        and finished
        and frd_has_displacement
        and not timed_out
    )
    return {
        "status": "SOLVER_PASS_UNVALIDATED" if passed else "HOLD",
        "returncode": returncode,
        "timed_out": timed_out,
        "files_present": present,
        "clean_text": clean,
        "finished": finished,
        "frd_has_displacement": frd_has_displacement,
        "command_argv": command,
        "mount_source": mount_source,
        "log": str(log_path.resolve()),
        "sha256": {
            suffix: sha256(path) for suffix, path in paths.items() if path.is_file()
        },
    }


def parse_dat_displacements(path: Path) -> list[dict]:
    blocks: list[dict] = []
    active: dict | None = None
    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw.strip()
        lower = line.lower()
        if lower.startswith("displacements "):
            if active is not None and active["nodes"]:
                blocks.append(active)
            time_match = re.search(r"\btime\s+([-+0-9.eE]+)", line, flags=re.IGNORECASE)
            active = {
                "time_s": float(time_match.group(1)) if time_match else None,
                "nodes": {},
            }
            continue
        if active is None:
            continue
        parts = line.split()
        if len(parts) >= 4 and parts[0].isdigit():
            try:
                values = [float(parts[index]) for index in range(1, 4)]
            except ValueError:
                continue
            if all(math.isfinite(value) for value in values):
                active["nodes"][int(parts[0])] = values
        elif lower.startswith("stresses ") and active["nodes"]:
            blocks.append(active)
            active = None
    if active is not None and active["nodes"]:
        blocks.append(active)
    return blocks


def _distance(a: list[float], b: list[float]) -> float:
    return math.sqrt(sum((left - right) ** 2 for left, right in zip(a, b)))


def evaluate_analytical_smoke(dat_path: Path) -> dict:
    blocks = parse_dat_displacements(dat_path)
    checks: dict[str, bool] = {"two_displacement_frames": len(blocks) >= 2}
    frame_reports = []
    if len(blocks) < 2:
        return {
            "status": "HOLD",
            "checks": checks,
            "frames_found": len(blocks),
            "frames": frame_reports,
            "reason": "DAT does not contain both displacement frames",
        }

    selected = blocks[-len(TOTAL_EIGENSTRAINS):]
    for frame_index, (block, strain) in enumerate(zip(selected, TOTAL_EIGENSTRAINS), start=1):
        nodes = block["nodes"]
        complete = set(NODE_COORDINATES).issubset(nodes)
        checks[f"frame_{frame_index}_all_nodes"] = complete
        if not complete:
            frame_reports.append({"frame": frame_index, "missing_nodes": sorted(set(NODE_COORDINATES) - set(nodes))})
            continue
        displaced = {
            node_id: [coordinate + displacement for coordinate, displacement in zip(NODE_COORDINATES[node_id], nodes[node_id])]
            for node_id in NODE_COORDINATES
        }
        expected_length_ratio = math.sqrt(1.0 + 2.0 * strain)
        expected_component = (expected_length_ratio - 1.0) * EDGE_LENGTH_M
        expected_displacement = abs(expected_component)
        anchor_norm = math.sqrt(sum(value * value for value in nodes[1]))
        checks[f"frame_{frame_index}_anchor_fixed"] = anchor_norm <= 1.0e-10
        edge_reports = []
        for node_id, axis in FREE_EDGE_COMPONENTS:
            component = nodes[node_id][axis]
            magnitude_ratio = abs(component) / expected_displacement
            cross_norm = math.sqrt(sum(value * value for index, value in enumerate(nodes[node_id]) if index != axis))
            length_ratio = _distance(displaced[1], displaced[node_id]) / EDGE_LENGTH_M
            prefix = f"frame_{frame_index}_node_{node_id}"
            checks[f"{prefix}_negative"] = component < 0.0
            checks[f"{prefix}_magnitude"] = 0.98 <= magnitude_ratio <= 1.02
            checks[f"{prefix}_axis_aligned"] = cross_norm <= max(expected_displacement * 0.02, 1.0e-12)
            checks[f"{prefix}_edge_length"] = abs(length_ratio - expected_length_ratio) <= 2.0e-5
            edge_reports.append(
                {
                    "node": node_id,
                    "axis": axis,
                    "displacement_m": component,
                    "expected_green_lagrange_displacement_m": expected_component,
                    "magnitude_ratio": magnitude_ratio,
                    "free_edge_length_m": length_ratio * EDGE_LENGTH_M,
                    "expected_green_lagrange_edge_length_m": expected_length_ratio * EDGE_LENGTH_M,
                }
            )
        frame_reports.append(
            {
                "frame": frame_index,
                "time_s": block["time_s"],
                "total_isotropic_eigenstrain": strain,
                "anchor_displacement_norm_m": anchor_norm,
                "edges": edge_reports,
            }
        )

    if len(frame_reports) == 2 and all("edges" in frame for frame in frame_reports):
        first = [abs(edge["displacement_m"]) for edge in frame_reports[0]["edges"]]
        second = [abs(edge["displacement_m"]) for edge in frame_reports[1]["edges"]]
        checks["contraction_grows_in_second_frame"] = all(right > left for left, right in zip(first, second))
    else:
        checks["contraction_grows_in_second_frame"] = False
    passed = bool(checks) and all(checks.values())
    return {
        "status": "ANALYTICAL_SMOKE_PASS_UNVALIDATED" if passed else "HOLD",
        "checks": checks,
        "frames_found": len(blocks),
        "frames": frame_reports,
        "tolerances": {
            "displacement_magnitude_ratio": [0.98, 1.02],
            "edge_length_ratio_absolute": 2.0e-5,
            "cross_axis_fraction": 0.02,
            "anchor_displacement_m": 1.0e-10,
        },
    }


def _write_report(output_dir: Path, report: dict) -> None:
    (output_dir / "ccx_eigenstrain_smoke_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def run(
    output_dir: Path,
    *,
    solve: bool = False,
    image: str = DEFAULT_IMAGE,
    timeout_s: int = 300,
    pull: bool = False,
) -> dict:
    generated = generate_case(output_dir)
    report = {
        "schema": SCHEMA,
        "status": "HOLD",
        "stage": "GENERATED_NOT_SOLVED",
        "scope": "single_C3D4_two_frame_isotropic_eigenstrain_smoke_only",
        "geometry": {
            "element_type": "C3D4",
            "element_count": 1,
            "node_count": 4,
            "orthogonal_edge_length_m": EDGE_LENGTH_M,
        },
        "material": {"model": "linear_elastic", "young_modulus_Pa": 2.0e9, "poisson_ratio": 0.35},
        "loading": {
            "kind": "isotropic_initial_strain_increase",
            "total_eigenstrain_frames": list(TOTAL_EIGENSTRAINS),
            "strain_measure_contract": "green_lagrange",
        },
        "generation": generated,
        "limitations": [
            "This is a one-element implementation smoke, not a product validation.",
            "The analytical gate checks sign, free-edge length, and order-of-magnitude only.",
            "Material calibration, mesh convergence, contact, fixtures, and measured comparison are outside this smoke.",
        ],
    }
    if not solve:
        report["hold_reason"] = "docker_solve_not_requested; rerun with --solve"
        _write_report(output_dir, report)
        return report

    probe = probe_docker(image, pull=pull, timeout_s=timeout_s)
    report["docker"] = probe
    if not probe.get("available") or not probe.get("image_available"):
        report["stage"] = "DOCKER_UNAVAILABLE"
        report["hold_reason"] = probe.get("reason", "docker_unavailable")
        _write_report(output_dir, report)
        return report

    execution = solve_with_docker(
        Path(generated["generated_dir"]),
        image=image,
        docker_binary=str(probe["docker_binary"]),
        timeout_s=timeout_s,
    )
    report["execution"] = execution
    if execution["status"] != "SOLVER_PASS_UNVALIDATED":
        report["stage"] = "FAILED_NUMERICS"
        report["hold_reason"] = "ccx execution or DAT/FRD/STA evidence gate failed"
        _write_report(output_dir, report)
        return report

    dat_path = Path(generated["generated_dir"]) / "continuous_reanalysis.dat"
    analytical = evaluate_analytical_smoke(dat_path)
    report["analytical_comparison"] = analytical
    if analytical["status"] != "ANALYTICAL_SMOKE_PASS_UNVALIDATED":
        report["stage"] = "FAILED_PHYSICS"
        report["hold_reason"] = "single-element displacement/edge-length analytical gate failed"
    else:
        report["status"] = "SOLVER_PASS_UNVALIDATED"
        report["stage"] = "SOLVED_ANALYTICAL_SMOKE_PASS"
    _write_report(output_dir, report)
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--solve", action="store_true", help="Run Docker ccx and enforce output/analytical gates")
    parser.add_argument("--image", default=DEFAULT_IMAGE)
    parser.add_argument("--timeout-s", type=int, default=300)
    parser.add_argument("--pull", action="store_true", help="Explicitly pull the image when it is absent")
    args = parser.parse_args()
    result = run(**vars(args))
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if not args.solve:
        return 0
    return 0 if result["status"] == "SOLVER_PASS_UNVALIDATED" else 2


if __name__ == "__main__":
    raise SystemExit(main())
