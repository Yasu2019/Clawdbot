# -*- coding: utf-8 -*-
"""Moldflow Phase 7: STEP bbox + gate_spec -> OpenFOAM case (blockMesh proxy cavity)."""

import sys

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import json
import re
import shutil
from pathlib import Path
from typing import Any

import moldflow_gate_spec as gate_spec_mod

try:
    import moldflow_cavity_mesh as cavity_mesh_mod
except ImportError:
    cavity_mesh_mod = None  # type: ignore

import moldflow_closed_cavity as closed_cavity_mod

import os

ROOT = Path(__file__).resolve().parents[1]
WORKSPACE = Path(os.environ.get("CAE_TE_WORKSPACE", str(ROOT / "data" / "cae_te_workspace")))
SAMPLES = WORKSPACE / "samples" / "moldflow"
DEFAULT_STEP = SAMPLES / "cavity_plate_100x10x2.step"

PHYSICS_TEMPLATES = {
    "resin_fill_vof": WORKSPACE / "experiments" / "openfoam" / "resin_fill_v003",
    "resin_fill_pack": WORKSPACE / "experiments" / "openfoam" / "resin_fill_v006",
    "resin_fill_closed_pack": WORKSPACE / "experiments" / "openfoam" / "resin_fill_v008",
    "resin_fill_cool": WORKSPACE / "experiments" / "openfoam" / "resin_fill_v007",
    "resin_fill_thermo": WORKSPACE / "experiments" / "openfoam" / "resin_fill_v004",
}


def step_bbox_mm(step_path: Path) -> dict[str, float]:
    """Parse axis-aligned bbox from ASCII STEP (CARTESIAN_POINT). Units assumed mm."""
    text = step_path.read_text(encoding="utf-8", errors="replace")
    coords: list[tuple[float, float, float]] = []
    for m in re.finditer(
        r"CARTESIAN_POINT\s*\([^)]*\(\s*([^;)]+)\s*\)",
        text,
        flags=re.IGNORECASE,
    ):
        parts = [p.strip() for p in m.group(1).split(",")]
        if len(parts) < 3:
            continue
        try:
            coords.append((float(parts[0]), float(parts[1]), float(parts[2])))
        except ValueError:
            continue
    if not coords:
        raise ValueError(f"No CARTESIAN_POINT found in STEP: {step_path}")
    xs = [c[0] for c in coords]
    ys = [c[1] for c in coords]
    zs = [c[2] for c in coords]
    return {
        "xmin": min(xs),
        "xmax": max(xs),
        "ymin": min(ys),
        "ymax": max(ys),
        "zmin": min(zs),
        "zmax": max(zs),
        "length": max(max(xs) - min(xs), 1e-3),
        "width": max(max(ys) - min(ys), 1e-3),
        "height": max(max(zs) - min(zs), 1e-3),
    }


def bbox_from_spec(spec: dict[str, Any]) -> dict[str, float]:
    bb = spec.get("bbox_mm") or {}
    if isinstance(bb, dict) and all(k in bb for k in ("length", "width", "height")):
        lx = float(bb["length"])
        ly = float(bb["width"])
        lz = float(bb["height"])
        return {
            "xmin": 0.0,
            "ymin": 0.0,
            "zmin": 0.0,
            "xmax": lx,
            "ymax": ly,
            "zmax": lz,
            "length": lx,
            "width": ly,
            "height": lz,
        }
    raise ValueError("gate_spec.bbox_mm {length,width,height} or step_path required")


def blockmesh_dict_text(
    lx: float,
    ly: float,
    lz: float,
    nx: int = 50,
    ny: int | None = None,
    gate_width_mm: float | None = None,
    vent_layout: str = "full_far_edge",
    nz: int = 1,
) -> str:
    """Three-segment inlet patches (inlet1/2/3) on ymin face, outlet on xmax.

    The legacy default keeps inlet2 at half width. For point-gate-style demos,
    gate_width_mm narrows inlet2 so the fill front can advance then spread.
    """
    if gate_width_mm is None:
        y1 = ly * 0.25
        y2 = ly * 0.75
    else:
        gate_w = max(min(float(gate_width_mm), ly * 0.95), max(0.1, ly * 0.02))
        y1 = (ly - gate_w) * 0.5
        y2 = y1 + gate_w
    total_ny = int(ny) if ny is not None else max(3, int(round(nx * ly / max(lx, 0.001))))
    total_ny = max(3, min(total_ny, 80))
    ny1 = max(1, int(round(total_ny * y1 / ly)))
    ny2 = max(1, int(round(total_ny * (y2 - y1) / ly)))
    ny3 = max(1, total_ny - ny1 - ny2)
    nz = max(1, min(int(nz), 20))
    thickness_patch_type = "wall" if nz > 1 else "empty"
    if vent_layout == "corner_far_edge":
        outlet_faces = "            (1 9 11 3)\n            (5 13 15 7)"
        extra_wall_faces = "            (3 11 13 5)\n"
    elif vent_layout == "full_far_edge":
        outlet_faces = (
            "            (1 9 11 3)\n"
            "            (3 11 13 5)\n"
            "            (5 13 15 7)"
        )
        extra_wall_faces = ""
    else:
        raise ValueError(f"unsupported vent_layout: {vent_layout}")
    return f"""/*--------------------------------*- C++ -*----------------------------------*\\
| Moldflow Phase 7: blockMesh from STEP bbox (auto-generated)                   |
\\*---------------------------------------------------------------------------*/
FoamFile
{{
    version     2.0;
    format      ascii;
    class       dictionary;
    object      blockMeshDict;
}}

convertToMeters 0.001;

vertices
(
    (0   0   0)
    ({lx:g} 0   0)
    (0   {y1:g} 0)
    ({lx:g} {y1:g} 0)
    (0   {y2:g} 0)
    ({lx:g} {y2:g} 0)
    (0   {ly:g} 0)
    ({lx:g} {ly:g} 0)
    (0   0   {lz:g})
    ({lx:g} 0   {lz:g})
    (0   {y1:g} {lz:g})
    ({lx:g} {y1:g} {lz:g})
    (0   {y2:g} {lz:g})
    ({lx:g} {y2:g} {lz:g})
    (0   {ly:g} {lz:g})
    ({lx:g} {ly:g} {lz:g})
);

blocks
(
    hex (0 1 3 2 8 9 11 10) ({nx} {ny1} {nz}) simpleGrading (1 1 1)
    hex (2 3 5 4 10 11 13 12) ({nx} {ny2} {nz}) simpleGrading (1 1 1)
    hex (4 5 7 6 12 13 15 14) ({nx} {ny3} {nz}) simpleGrading (1 1 1)
);

edges
(
);

boundary
(
    inlet1
    {{
        type patch;
        faces
        (
            (0 2 10 8)
        );
    }}
    inlet2
    {{
        type patch;
        faces
        (
            (2 4 12 10)
        );
    }}
    inlet3
    {{
        type patch;
        faces
        (
            (4 6 14 12)
        );
    }}
    outlet
    {{
        type patch;
        faces
        (
{outlet_faces}
        );
    }}
    walls
    {{
        type wall;
        faces
        (
{extra_wall_faces}            (0 1 9 8)
            (6 7 15 14)
        );
    }}
    frontAndBack
    {{
        type {thickness_patch_type};
        faces
        (
            (0 1 3 2)
            (2 3 5 4)
            (4 5 7 6)
            (8 10 11 9)
            (10 12 13 11)
            (12 14 15 13)
        );
    }}
);

mergePatchPairs
(
);
"""


def blockmesh_independent_vent_dict_text(
    lx: float,
    ly: float,
    lz: float,
    nx: int = 50,
    ny: int | None = None,
    gate_width_mm: float = 4.0,
    vent_width_mm: float = 2.0,
    nz: int = 1,
) -> str:
    """Five y-segments: narrow corner vents independent of center gate width."""
    gate_w = max(0.2, min(float(gate_width_mm), ly * 0.70))
    vent_w = max(0.1, min(float(vent_width_mm), (ly - gate_w) * 0.20))
    gate_y1 = (ly - gate_w) * 0.5
    gate_y2 = gate_y1 + gate_w
    if vent_w >= gate_y1:
        raise ValueError("vent_width_mm overlaps the center gate segment")
    ys = [0.0, vent_w, gate_y1, gate_y2, ly - vent_w, ly]
    widths = [ys[i + 1] - ys[i] for i in range(5)]
    total_ny = int(ny) if ny is not None else max(5, int(round(nx * ly / max(lx, 0.001))))
    total_ny = max(5, min(total_ny, 100))
    counts = [max(1, int(round(total_ny * width / ly))) for width in widths]
    while sum(counts) > total_ny:
        idx = max(range(5), key=lambda i: counts[i] if counts[i] > 1 else -1)
        if counts[idx] <= 1:
            break
        counts[idx] -= 1
    while sum(counts) < total_ny:
        idx = max(range(5), key=lambda i: widths[i] / counts[i])
        counts[idx] += 1

    nz = max(1, min(int(nz), 20))
    thickness_patch_type = "wall" if nz > 1 else "empty"
    vertices = []
    for z in (0.0, lz):
        for y in ys:
            vertices.append(f"    (0 {y:g} {z:g})")
            vertices.append(f"    ({lx:g} {y:g} {z:g})")

    blocks = []
    inlet_faces = [[], [], []]
    outlet_faces = []
    far_wall_faces = []
    bottom_faces = []
    top_faces = []
    for i in range(5):
        b0, b1, b2, b3 = 2 * i, 2 * i + 1, 2 * i + 3, 2 * i + 2
        t0, t1, t2, t3 = b0 + 12, b1 + 12, b2 + 12, b3 + 12
        blocks.append(
            f"    hex ({b0} {b1} {b2} {b3} {t0} {t1} {t2} {t3}) "
            f"({nx} {counts[i]} {nz}) simpleGrading (1 1 1)"
        )
        inlet_group = 0 if i < 2 else 1 if i == 2 else 2
        inlet_faces[inlet_group].append(f"            ({b0} {b3} {t3} {t0})")
        far_face = f"            ({b1} {t1} {t2} {b2})"
        (outlet_faces if i in (0, 4) else far_wall_faces).append(far_face)
        bottom_faces.append(f"            ({b0} {b1} {b2} {b3})")
        top_faces.append(f"            ({t0} {t3} {t2} {t1})")

    lower_wall = "            (0 1 13 12)"
    upper_wall = "            (10 22 23 11)"
    return f"""/*--------------------------------*- C++ -*----------------------------------*\\
| Moldflow five-segment gate and corner-vent mesh                             |
\\*---------------------------------------------------------------------------*/
FoamFile
{{
    version 2.0;
    format ascii;
    class dictionary;
    object blockMeshDict;
}}

convertToMeters 0.001;

vertices
(
{chr(10).join(vertices)}
);

blocks
(
{chr(10).join(blocks)}
);

edges ();

boundary
(
    inlet1
    {{
        type patch;
        faces
        (
{chr(10).join(inlet_faces[0])}
        );
    }}
    inlet2
    {{
        type patch;
        faces
        (
{chr(10).join(inlet_faces[1])}
        );
    }}
    inlet3
    {{
        type patch;
        faces
        (
{chr(10).join(inlet_faces[2])}
        );
    }}
    outlet
    {{
        type patch;
        faces
        (
{chr(10).join(outlet_faces)}
        );
    }}
    walls
    {{
        type wall;
        faces
        (
{chr(10).join(far_wall_faces)}
{lower_wall}
{upper_wall}
        );
    }}
    frontAndBack
    {{
        type {thickness_patch_type};
        faces
        (
{chr(10).join(bottom_faces)}
{chr(10).join(top_faces)}
        );
    }}
);

mergePatchPairs ();
"""


def ensure_sample_step() -> Path:
    SAMPLES.mkdir(parents=True, exist_ok=True)
    if DEFAULT_STEP.exists():
        return DEFAULT_STEP
    lx, ly, lz = 100.0, 10.0, 2.0
    step = f"""ISO-10303-21;
HEADER;
FILE_DESCRIPTION(('Moldflow sample cavity plate'),'2;1');
FILE_NAME('cavity_plate_100x10x2.step','2026-06-01',('Clawstack'),(''),
  'Open CASCADE STEP processor','Open CASCADE','');
ENDSEC;
DATA;
#1 = CARTESIAN_POINT('', (0., 0., 0.));
#2 = CARTESIAN_POINT('', ({lx}, 0., 0.));
#3 = CARTESIAN_POINT('', (0., {ly}, 0.));
#4 = CARTESIAN_POINT('', ({lx}, {ly}, 0.));
#5 = CARTESIAN_POINT('', (0., 0., {lz}));
#6 = CARTESIAN_POINT('', ({lx}, 0., {lz}));
#7 = CARTESIAN_POINT('', (0., {ly}, {lz}));
#8 = CARTESIAN_POINT('', ({lx}, {ly}, {lz}));
ENDSEC;
END-ISO-10303-21;
"""
    DEFAULT_STEP.write_text(step, encoding="utf-8")
    return DEFAULT_STEP


def resolve_physics_template(params: dict[str, Any]) -> Path:
    key = str(params.get("physics_category", "resin_fill_vof"))
    path = PHYSICS_TEMPLATES.get(key)
    if path and path.exists():
        return path
    return PHYSICS_TEMPLATES["resin_fill_vof"]


def validate_build(
    template_dir: Path,
    gate_spec_path: Path,
    step_path: Path | None,
    params: dict[str, Any],
) -> dict[str, Any]:
    spec = gate_spec_mod.load_gate_spec(gate_spec_path)
    issues = gate_spec_mod.validate_gate_spec(
        spec, require_patch_names=["inlet1", "inlet2", "inlet3", "outlet", "walls"]
    )
    if issues:
        raise ValueError("gate_spec invalid: " + "; ".join(issues))
    if step_path and step_path.exists():
        bbox = step_bbox_mm(step_path)
    else:
        bbox = bbox_from_spec(spec)
    return {"bbox_mm": bbox, "gate_spec": spec, "template": str(template_dir)}


def resolve_mesh_mode(params: dict[str, Any]) -> str:
    mode = str(params.get("mesh_mode", "blockmesh_bbox")).lower().strip()
    if mode not in ("blockmesh_bbox", "gmsh_volume"):
        raise ValueError(f"mesh_mode must be blockmesh_bbox or gmsh_volume, got: {mode}")
    return mode


def apply_vof_stability_options(run_dir: Path, params: dict[str, Any]) -> None:
    """Optional per-case bounded-alpha settings for aggressive point-gate demos."""
    if not params.get("bounded_alpha"):
        return
    schemes = run_dir / "system" / "fvSchemes"
    schemes_ascii = run_dir / "system" / "fvSchemes.ascii"
    for path in (schemes, schemes_ascii):
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        text = text.replace("interfaceCompression vanLeer 1", "interfaceCompression vanLeer01 0.5")
        text = text.replace("Gauss vanLeer;", "Gauss vanLeer01;")
        path.write_text(text, encoding="utf-8")

    solution = run_dir / "system" / "fvSolution"
    solution_ascii = run_dir / "system" / "fvSolution.ascii"
    for path in (solution, solution_ascii):
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        text = re.sub(r"nAlphaCorr\s+\d+;", "nAlphaCorr      2;", text)
        text = re.sub(r"nAlphaSubCycles\s+\d+;", "nAlphaSubCycles 4;", text)
        text = re.sub(r"cAlpha\s+[0-9.eE+-]+;", "cAlpha          0.5;", text)
        path.write_text(text, encoding="utf-8")

    control = run_dir / "system" / "controlDict"
    control_ascii = run_dir / "system" / "controlDict.ascii"
    for path in (control, control_ascii):
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        text = re.sub(r"maxAlphaCo\s+[0-9.eE+-]+;", "maxAlphaCo      0.1;", text)
        path.write_text(text, encoding="utf-8")

    if params.get("alpha_transport_scheme") == "bounded_split":
        for path in (schemes, schemes_ascii):
            if not path.exists():
                continue
            text = path.read_text(encoding="utf-8", errors="replace")
            text = re.sub(
                r"div\(phi,alpha\)\s+Gauss\s+[^;]+;",
                "div(phi,alpha)  Gauss vanLeer01;",
                text,
            )
            text = re.sub(
                r"div\(phirb,alpha\)\s+Gauss\s+[^;]+;",
                "div(phirb,alpha) Gauss interfaceCompression;",
                text,
            )
            path.write_text(text, encoding="utf-8")


def apply_runtime_options(run_dir: Path, params: dict[str, Any]) -> None:
    """Apply a per-case analysis horizon without modifying shared templates."""
    raw_end_time = params.get("analysis_end_time_s")
    if raw_end_time is None:
        return
    end_time = float(raw_end_time)
    if not 1e-6 <= end_time <= 3600.0:
        raise ValueError("analysis_end_time_s must be between 1e-6 and 3600 seconds")
    replacement = f"endTime         {end_time:g};"
    for path in (run_dir / "system" / "controlDict", run_dir / "system" / "controlDict.ascii"):
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        text, count = re.subn(r"endTime\s+[0-9.eE+-]+;", replacement, text, count=1)
        if count != 1:
            raise ValueError(f"endTime entry not found in {path}")
        raw_write_interval = params.get("write_interval_steps")
        if raw_write_interval is not None:
            write_interval = int(raw_write_interval)
            if not 1 <= write_interval <= 100000:
                raise ValueError("write_interval_steps must be between 1 and 100000")
            text, count = re.subn(
                r"writeInterval\s+[0-9]+;",
                f"writeInterval   {write_interval};",
                text,
                count=1,
            )
            if count != 1:
                raise ValueError(f"writeInterval entry not found in {path}")
        raw_write_interval_s = params.get("write_interval_s")
        if raw_write_interval_s is not None:
            write_interval_s = float(raw_write_interval_s)
            if not 1e-6 <= write_interval_s <= end_time:
                raise ValueError("write_interval_s must be positive and <= analysis_end_time_s")
            text, control_count = re.subn(
                r"writeControl\s+\w+;",
                "writeControl    adjustableRunTime;",
                text,
                count=1,
            )
            text, interval_count = re.subn(
                r"writeInterval\s+[0-9.eE+-]+;",
                f"writeInterval   {write_interval_s:g};",
                text,
                count=1,
            )
            if control_count != 1 or interval_count != 1:
                raise ValueError(f"write controls not found in {path}")
        path.write_text(text, encoding="utf-8")


def apply_thermal_history_function_objects(run_dir: Path, params: dict[str, Any]) -> None:
    """Record lightweight thermal/rheology histories without full-field retention."""
    if not (params.get("record_thermal_history") or params.get("record_shear_history")):
        return
    block = r'''

functions
{
    thermalFieldMinMax
    {
        type              fieldMinMax;
        libs              (fieldFunctionObjects);
        fields            (T);
        mode              magnitude;
        location          true;
        executeControl    timeStep;
        executeInterval   1;
        writeControl      timeStep;
        writeInterval     1;
        writeToFile       true;
        log               false;
    }

    polymerBulkTemperature
    {
        type              volFieldValue;
        libs              (fieldFunctionObjects);
        fields            (T);
        operation         weightedVolAverage;
        weightField       alpha.polymer;
        regionType        all;
        executeControl    timeStep;
        executeInterval   1;
        writeControl      timeStep;
        writeInterval     1;
        writeFields       false;
        writeToFile       true;
        log               false;
    }
}
'''
    if params.get("record_shear_history"):
        shear = r'''

    gradVelocity
    {
        type              grad;
        libs              (fieldFunctionObjects);
        field             U;
        result            gradU;
        executeControl    timeStep;
        executeInterval   1;
        writeControl      none;
    }

    shearRateMagnitude
    {
        type              mag;
        libs              (fieldFunctionObjects);
        field             gradU;
        result            shearRateProxy;
        executeControl    timeStep;
        executeInterval   1;
        writeControl      none;
    }

    shearRateMinMax
    {
        type              fieldMinMax;
        libs              (fieldFunctionObjects);
        fields            (shearRateProxy);
        mode              magnitude;
        location          true;
        executeControl    timeStep;
        executeInterval   1;
        writeControl      timeStep;
        writeInterval     1;
        writeToFile       true;
        log               false;
    }

    moldWallShearStress
    {
        type              wallShearStress;
        libs              (fieldFunctionObjects);
        patches           (frontAndBack);
        executeControl    timeStep;
        executeInterval   1;
        writeControl      timeStep;
        writeInterval     1;
        writeToFile       true;
        log               false;
    }
'''
        block = block.rsplit("\n}", 1)[0] + shear + "\n}\n"
    for path in (run_dir / "system" / "controlDict", run_dir / "system" / "controlDict.ascii"):
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        if re.search(r"(?m)^\s*functions\s*$", text):
            raise ValueError(f"functions dictionary already exists in {path}")
        marker = "// ************************************************************************* //"
        if marker not in text:
            raise ValueError(f"controlDict footer not found in {path}")
        path.write_text(text.replace(marker, block + "\n" + marker, 1), encoding="utf-8")


def apply_vented_outlet_options(run_dir: Path, params: dict[str, Any]) -> None:
    """Use a consistent pressure vent that lets air and finally polymer leave."""
    if not params.get("vented_outlet"):
        return

    def replace_outlet(path: Path, body: str) -> None:
        if not path.exists():
            return
        text = path.read_text(encoding="utf-8", errors="replace")
        text, count = re.subn(
            r"(\n\s*outlet\s*\{)[^}]*(\})",
            rf"\1\n{body}    \2",
            text,
            count=1,
        )
        if count != 1:
            raise ValueError(f"outlet boundary not found in {path}")
        path.write_text(text, encoding="utf-8")

    replace_outlet(
        run_dir / "0" / "U",
        "        type            pressureInletOutletVelocity;\n"
        "        value           uniform (0 0 0);\n",
    )
    replace_outlet(
        run_dir / "0" / "alpha.polymer",
        "        type            inletOutlet;\n"
        "        inletValue      uniform 0;\n"
        "        value           uniform 0;\n",
    )


def apply_compressible_closed_cavity_options(
    run_dir: Path, params: dict[str, Any]
) -> None:
    """Close the cavity while allowing the compressible air phase to pressurize."""
    if not params.get("compressible_closed_cavity"):
        return

    initial_pressure_pa = float(params.get("initial_cavity_pressure_pa", 101325.0))
    if not 50000.0 <= initial_pressure_pa <= 200000.0:
        raise ValueError("initial_cavity_pressure_pa must be between 50000 and 200000 Pa")
    initial_pressure = f"{initial_pressure_pa:g}"

    replacements = {
        "U": "        type            noSlip;\n",
        "alpha.polymer": "        type            zeroGradient;\n",
        "p": (
            "        type            calculated;\n"
            f"        value           uniform {initial_pressure};\n"
        ),
        "p_rgh": (
            "        type            fixedFluxPressure;\n"
            f"        value           uniform {initial_pressure};\n"
        ),
    }
    for field_name, body in replacements.items():
        path = run_dir / "0" / field_name
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        text, count = re.subn(
            r"(\n\s*outlet\s*\{)[^}]*(\})",
            rf"\1\n{body}    \2",
            text,
            count=1,
        )
        if count != 1:
            raise ValueError(f"outlet boundary not found in {path}")
        path.write_text(text, encoding="utf-8")

    # With g=(0 0 0), p_rgh=p. Keeping p_rgh=0 while p is atmospheric
    # creates an inconsistent compressible initial state.
    for field_name in ("p", "p_rgh"):
        path = run_dir / "0" / field_name
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        text, count = re.subn(
            r"internalField\s+uniform\s+[-+0-9.eE]+\s*;",
            f"internalField   uniform {initial_pressure};",
            text,
            count=1,
        )
        if count != 1:
            raise ValueError(f"uniform initial pressure not found in {path}")
        text = re.sub(
            r"(value\s+uniform\s+)[-+0-9.eE]+(\s*;)",
            rf"\g<1>{initial_pressure}\2",
            text,
        )
        path.write_text(text, encoding="utf-8")


def apply_resolved_thickness_boundaries(run_dir: Path, params: dict[str, Any]) -> None:
    """Turn the former 2-D empty faces into physical mold walls for nz > 1."""
    nz = int(params.get("mesh_nz", 1))
    if nz <= 1:
        return
    if nz > 20:
        raise ValueError("mesh_nz must be <= 20")
    mold_temperature = float(params.get("T_mold", 323.0))
    initial_pressure = float(params.get("initial_cavity_pressure_pa", 101325.0))
    bodies = {
        "U": "        type            noSlip;\n",
        "alpha.polymer": "        type            zeroGradient;\n",
        "p": (
            "        type            calculated;\n"
            f"        value           uniform {initial_pressure:g};\n"
        ),
        "p_rgh": (
            "        type            fixedFluxPressure;\n"
            f"        value           uniform {initial_pressure:g};\n"
        ),
        "T": (
            "        type            fixedValue;\n"
            f"        value           uniform {mold_temperature:g};\n"
        ),
        "T.air": (
            "        type            fixedValue;\n"
            f"        value           uniform {mold_temperature:g};\n"
        ),
        "T.polymer": (
            "        type            fixedValue;\n"
            f"        value           uniform {mold_temperature:g};\n"
        ),
    }
    for field_name, body in bodies.items():
        path = run_dir / "0" / field_name
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        text, count = re.subn(
            r"(\n\s*frontAndBack\s*\{)[^}]*(\})",
            rf"\1\n{body}    \2",
            text,
            count=1,
        )
        if count != 1:
            raise ValueError(f"frontAndBack boundary not found in {path}")
        path.write_text(text, encoding="utf-8")

def normalize_generated_initial_fields(run_dir: Path, params: dict[str, Any]) -> None:
    """Reset mesh-size-specific template alpha fields for generated CAD meshes."""
    if (
        str(params.get("physics_category", "")) != "resin_fill_cool"
        and not params.get("reset_initial_alpha")
    ):
        return
    alpha_path = run_dir / "0" / "alpha.polymer"
    if not alpha_path.exists():
        return
    text = alpha_path.read_text(encoding="utf-8", errors="replace")
    text = re.sub(
        r"internalField\s+nonuniform\s+List<scalar>\s+\d+\s*\([\s\S]*?\)\s*;",
        "internalField   uniform 0;",
        text,
        count=1,
    )
    alpha_path.write_text(text, encoding="utf-8")


def build_case(
    run_dir: Path,
    template_dir: Path,
    step_path: Path | None,
    gate_spec_path: Path,
    params: dict[str, Any],
) -> dict[str, Any]:
    spec = gate_spec_mod.load_gate_spec(gate_spec_path)
    issues = gate_spec_mod.validate_gate_spec(
        spec, require_patch_names=["inlet1", "inlet2", "inlet3", "outlet", "walls"]
    )
    if issues:
        raise ValueError("gate_spec invalid: " + "; ".join(issues))

    if step_path and step_path.exists():
        bbox = step_bbox_mm(step_path)
        bbox_source = "step"
    else:
        bbox = bbox_from_spec(spec)
        bbox_source = "gate_spec.bbox_mm"

    if run_dir.exists():
        shutil.rmtree(run_dir, ignore_errors=True)
    shutil.copytree(template_dir, run_dir)

    mesh_mode = resolve_mesh_mode(params)
    mesh_info: dict[str, Any] = {}
    lx, ly, lz = bbox["length"], bbox["width"], bbox["height"]

    if mesh_mode == "gmsh_volume":
        if cavity_mesh_mod is None:
            raise RuntimeError("moldflow_cavity_mesh not available; pip install gmsh")
        ms = params.get("mesh_size_mm")
        mesh_size = float(ms) if ms is not None else None
        cavity_mesh_mod.write_inlet_split_dicts(run_dir, bbox)
        mesh_info = cavity_mesh_mod.apply_cavity_mesh_to_case(
            run_dir,
            bbox,
            step_path=step_path,
            mesh_size_mm=mesh_size,
            run_gmsh_to_foam=bool(params.get("run_gmsh_to_foam_on_host")),
        )
        preview_stl = SAMPLES / "cavity_preview.stl"
        try:
            cavity_mesh_mod.export_stl_preview(
                preview_stl, bbox, step_path=step_path, mesh_size_mm=mesh_size
            )
            mesh_info["preview_stl"] = str(preview_stl)
        except Exception:
            pass
    else:
        nx = int(params.get("mesh_nx", 50))
        nx = max(20, min(nx, 80))
        ny_raw = params.get("mesh_ny")
        ny = int(ny_raw) if ny_raw is not None else None
        gate_width = params.get("gate_width_mm")
        vent_layout = str(params.get("vent_layout", "full_far_edge"))
        vent_width = params.get("vent_width_mm")
        nz = int(params.get("mesh_nz", 1))
        if vent_width is not None:
            blockmesh_text = blockmesh_independent_vent_dict_text(
                lx,
                ly,
                lz,
                nx=nx,
                ny=ny,
                gate_width_mm=float(gate_width if gate_width is not None else 4.0),
                vent_width_mm=float(vent_width),
                nz=nz,
            )
        else:
            blockmesh_text = blockmesh_dict_text(
                lx,
                ly,
                lz,
                nx=nx,
                ny=ny,
                gate_width_mm=gate_width,
                vent_layout=vent_layout,
                nz=nz,
            )
        (run_dir / "system" / "blockMeshDict").write_text(
            blockmesh_text,
            encoding="utf-8",
        )

    params = dict(params)
    params["gate_position"] = gate_spec_mod.gate_position_from_spec(spec)
    params["gate_patch_velocities"] = gate_spec_mod.gate_patch_velocities(
        spec, float(params.get("inlet_velocity", 1.0))
    )

    gate_spec_mod.apply_gate_spec_to_openfoam_fields(run_dir, spec, params)
    normalize_generated_initial_fields(run_dir, params)
    closed_cavity_mod.patch_closed_cavity_on_build(run_dir, spec, params)
    apply_vof_stability_options(run_dir, params)
    apply_runtime_options(run_dir, params)
    apply_thermal_history_function_objects(run_dir, params)
    apply_vented_outlet_options(run_dir, params)
    apply_compressible_closed_cavity_options(run_dir, params)
    apply_resolved_thickness_boundaries(run_dir, params)

    manifest = {
        "phase": 7,
        "bbox_mm": bbox,
        "bbox_source": bbox_source,
        "mesh_mode": mesh_mode,
        "mesh_info": mesh_info,
        "mesh_nz": int(params.get("mesh_nz", 1)),
        "step_path": str(step_path) if step_path else None,
        "gate_spec_path": str(gate_spec_path),
        "physics_category": params.get("physics_category", "resin_fill_vof"),
        "template_dir": str(template_dir),
        "gate_position_legacy": params["gate_position"],
        "patches": {
            "gates": [g.get("patch") for g in spec.get("gates") or []],
            "vents": [v.get("patch") for v in spec.get("vents") or []],
        },
    }
    (run_dir / "cad_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (run_dir / "gate_spec.resolved.json").write_text(
        json.dumps(spec, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return manifest


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Build Moldflow OpenFOAM case from STEP + gate_spec")
    parser.add_argument("--run-dir", default="")
    parser.add_argument("--gate-spec", required=True)
    parser.add_argument("--step", default="")
    parser.add_argument("--physics", default="resin_fill_vof")
    parser.add_argument("--ensure-sample-step", action="store_true")
    parser.add_argument("--validate-only", action="store_true")
    args = parser.parse_args()

    step_p = Path(args.step) if args.step else None
    if args.ensure_sample_step and not step_p:
        step_p = ensure_sample_step()

    tmpl = resolve_physics_template({"physics_category": args.physics})
    gate_p = Path(args.gate_spec)
    params = {"physics_category": args.physics, "inlet_velocity": 1.0, "gate_position": "center"}

    if args.validate_only:
        info = validate_build(tmpl, gate_p, step_p, params)
        print(json.dumps(info, ensure_ascii=False, indent=2))
        return 0

    if not args.run_dir:
        print("error: --run-dir is required unless --validate-only", file=sys.stderr)
        return 2

    manifest = build_case(Path(args.run_dir), tmpl, step_p, gate_p, params)
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
