# -*- coding: utf-8 -*-
"""Moldflow Phase 7: STEP bbox + gate_spec -> OpenFOAM case (blockMesh proxy cavity)."""

import sys

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import json
import hashlib
import math
import re
import shutil
import struct
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
DEFAULT_STEP = SAMPLES / "pp_plate/pp_plate_100x60x2.step"

MFALIGN_SNAPPY_TEMPLATE = WORKSPACE / "experiments" / "openfoam" / "mfalign_snappy_v001"

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


def stl_bbox_mm(stl_path: Path) -> dict[str, float]:
    """Parse axis-aligned bbox from a binary or ASCII STL. Units assumed mm."""
    data = stl_path.read_bytes()
    xs: list[float] = []
    ys: list[float] = []
    zs: list[float] = []
    n_tri = struct.unpack("<I", data[80:84])[0] if len(data) >= 84 else 0
    if n_tri and len(data) == 84 + 50 * n_tri:
        for i in range(n_tri):
            base = 84 + 50 * i + 12  # skip the facet normal
            v = struct.unpack("<9f", data[base:base + 36])
            xs.extend(v[0::3])
            ys.extend(v[1::3])
            zs.extend(v[2::3])
    else:
        for m in re.finditer(
            r"vertex\s+(\S+)\s+(\S+)\s+(\S+)",
            data.decode("utf-8", errors="replace"),
            flags=re.IGNORECASE,
        ):
            try:
                xs.append(float(m.group(1)))
                ys.append(float(m.group(2)))
                zs.append(float(m.group(3)))
            except ValueError:
                continue
    if not xs:
        raise ValueError(f"No vertices found in STL: {stl_path}")
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


def geometry_bbox_mm(path: Path) -> dict[str, float]:
    """Bbox for a STEP or STL geometry file."""
    if path.suffix.lower() == ".stl":
        return stl_bbox_mm(path)
    return step_bbox_mm(path)


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
FILE_NAME('pp_plate/pp_plate_100x60x2.step','2026-06-01',('Clawstack'),(''),
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
    # snappyHexMesh cases carry the gate/vent/moldflow patch set, which only the
    # MFALIGN template provides.
    if resolve_mesh_mode(params) == "snappyhexmesh":
        if not MFALIGN_SNAPPY_TEMPLATE.exists():
            raise RuntimeError(
                f"snappyhexmesh requires the MFALIGN template at {MFALIGN_SNAPPY_TEMPLATE}"
            )
        return MFALIGN_SNAPPY_TEMPLATE
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
        spec, require_patch_names=required_patch_names(params)
    )
    if issues:
        raise ValueError("gate_spec invalid: " + "; ".join(issues))
    if step_path and step_path.exists():
        bbox = geometry_bbox_mm(step_path)
    else:
        bbox = bbox_from_spec(spec)
    return {"bbox_mm": bbox, "gate_spec": spec, "template": str(template_dir)}


def resolve_mesh_mode(params: dict[str, Any]) -> str:
    mode = str(params.get("mesh_mode", "blockmesh_bbox")).lower().strip()
    if mode not in ("blockmesh_bbox", "gmsh_volume", "snappyhexmesh"):
        raise ValueError(f"mesh_mode must be blockmesh_bbox, gmsh_volume, or snappyhexmesh, got: {mode}")
    return mode


def required_patch_names(params: dict[str, Any]) -> list[str] | None:
    """snappy cases carve gate/vent out of the moldflow surface via topoSet."""
    if resolve_mesh_mode(params) == "snappyhexmesh":
        return None
    return ["inlet1", "inlet2", "inlet3", "outlet", "walls"]


def resolve_surface_stl(step_path: Path | None, params: dict[str, Any]) -> Path:
    """snappyHexMesh needs a triangulated surface; pyvista cannot read STEP."""
    candidates: list[Path] = []
    raw = params.get("stl_path")
    if raw:
        p = Path(str(raw))
        candidates.append(p)
        if not p.is_absolute():
            candidates.append(Path.cwd() / p)
    if step_path is not None:
        candidates.append(step_path)
    for cand in candidates:
        if cand.suffix.lower() == ".stl" and cand.exists():
            return cand
    raise ValueError(
        "snappyhexmesh requires an existing .stl surface (pyvista cannot read STEP): "
        f"stl_path={params.get('stl_path')!r}, step_path={step_path}"
    )


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
    if raw_end_time is None and params.get("mf_fill_time_s"):
        margin = float(params.get("fill_end_time_margin", 1.15))
        raw_end_time = float(params["mf_fill_time_s"]) * margin
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


REFERENCE_GEOMETRY_MM = (100.0, 60.0, 50.0)
REFERENCE_GEOMETRY_TOL = 0.01


def resolve_geometry_scale_to_m(bbox_raw: dict[str, float], params: dict[str, Any]) -> float:
    """Factor converting the surface file's units to metres."""
    units = str(params.get("geometry_units", "auto")).lower().strip()
    if units in ("m", "metre", "meter"):
        return 1.0
    if units in ("mm", "millimetre", "millimeter"):
        return 0.001
    if units != "auto":
        raise ValueError(f"geometry_units must be m, mm, or auto, got: {units}")
    span = max(bbox_raw["length"], bbox_raw["width"], bbox_raw["height"])
    return 1.0 if span <= 1.0 else 0.001


BOUNDARY_CONTRACT_SCHEMA = "clawstack.arbitrary.boundary.groups.v1"
BOUNDARY_ARTIFACT_SCHEMA = "clawstack.openfoam.boundary.surface_artifacts.v1"
BOUNDARY_TOPOLOGY_CHECKS = (
    "watertight",
    "manifold",
    "orientation_consistent",
    "nonzero_enclosed_volume",
)
BOUNDARY_ROLES = ("gate", "vent", "wall", "hole")


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _resolve_contract_file(raw_path: Any, *, base_dir: Path | None = None) -> Path:
    path = Path(str(raw_path)).expanduser()
    if path.is_absolute():
        return path.resolve()
    roots = [base_dir, Path.cwd(), ROOT]
    candidates = [(root / path).resolve() for root in roots if root is not None]
    existing = list(dict.fromkeys(candidate for candidate in candidates if candidate.is_file()))
    if len(existing) > 1:
        raise ValueError(
            f"boundary contract reference is ambiguous: {raw_path!r} -> "
            + ", ".join(str(item) for item in existing)
        )
    return existing[0] if existing else candidates[0]


def _verified_hashed_reference(
    contract_path: Path, payload: dict[str, Any], label: str
) -> dict[str, str]:
    reference = payload.get(label)
    if not isinstance(reference, dict):
        raise ValueError(f"boundary contract {label} reference is missing")
    raw_path = reference.get("path")
    expected_hash = str(reference.get("sha256", "")).lower()
    if not raw_path:
        raise ValueError(f"boundary contract {label}.path is missing")
    if not re.fullmatch(r"[0-9a-f]{64}", expected_hash):
        raise ValueError(f"boundary contract {label}.sha256 is invalid")
    path = _resolve_contract_file(raw_path, base_dir=contract_path.parent)
    if not path.is_file():
        raise ValueError(f"boundary contract {label} file is missing: {path}")
    actual_hash = _sha256_file(path)
    if actual_hash != expected_hash:
        raise ValueError(
            f"boundary contract {label} sha256 mismatch: expected {expected_hash}, got {actual_hash}"
        )
    return {"path": str(path), "sha256": actual_hash}


def _contract_units_scale_to_m(
    contract: dict[str, Any], params: dict[str, Any]
) -> tuple[str, float]:
    aliases = {
        "m": ("m", 1.0),
        "metre": ("m", 1.0),
        "meter": ("m", 1.0),
        "mm": ("mm", 0.001),
        "millimetre": ("mm", 0.001),
        "millimeter": ("mm", 0.001),
    }
    contract_units = str(contract.get("units", "")).lower().strip()
    explicit_units = params.get("boundary_contract_units")
    geometry_units = str(params.get("geometry_units", "auto")).lower().strip()
    if explicit_units is None and geometry_units != "auto":
        explicit_units = geometry_units
    explicit_key = str(explicit_units).lower().strip() if explicit_units is not None else ""
    if contract_units in aliases:
        canonical, scale = aliases[contract_units]
        if explicit_key:
            if explicit_key not in aliases:
                raise ValueError(f"unsupported boundary_contract_units: {explicit_units!r}")
            if aliases[explicit_key][0] != canonical:
                raise ValueError(
                    "boundary contract units conflict with explicit geometry units: "
                    f"contract={contract_units}, explicit={explicit_units}"
                )
        return canonical, scale
    if explicit_key in aliases:
        return aliases[explicit_key]
    raise ValueError(
        "boundary contract units are not metrically defined; set "
        "boundary_contract_units to 'm' or 'mm'"
    )


def load_boundary_contract(params: dict[str, Any]) -> dict[str, Any] | None:
    """Load and verify an extractor boundary contract without accepting fallbacks."""
    raw_contract_path = params.get("boundary_contract_path")
    if raw_contract_path is None:
        return None
    contract_path = _resolve_contract_file(raw_contract_path)
    if not contract_path.is_file():
        raise ValueError(f"boundary contract file is missing: {contract_path}")
    try:
        contract = json.loads(contract_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"boundary contract is unreadable: {contract_path}: {exc}") from exc
    if not isinstance(contract, dict):
        raise ValueError("boundary contract root must be an object")
    if contract.get("schema") != BOUNDARY_CONTRACT_SCHEMA:
        raise ValueError(
            f"boundary contract schema must be {BOUNDARY_CONTRACT_SCHEMA!r}, "
            f"got {contract.get('schema')!r}"
        )
    if contract.get("status") != "PASS":
        raise ValueError(f"boundary contract status must be PASS, got {contract.get('status')!r}")

    topology = contract.get("surface_topology")
    topology_checks = topology.get("checks") if isinstance(topology, dict) else None
    if not isinstance(topology_checks, dict):
        raise ValueError("boundary contract surface_topology.checks is missing")
    failed_topology = [name for name in BOUNDARY_TOPOLOGY_CHECKS if topology_checks.get(name) is not True]
    if failed_topology:
        raise ValueError("boundary contract topology failed: " + ", ".join(failed_topology))
    checks = contract.get("checks")
    if not isinstance(checks, dict) or checks.get("surface_topology") is not True:
        raise ValueError("boundary contract checks.surface_topology must be true")
    if checks.get("all_faces_classified_once") is not True:
        raise ValueError("boundary contract checks.all_faces_classified_once must be true")

    face_count = contract.get("face_count")
    groups = contract.get("groups")
    if not isinstance(face_count, int) or face_count <= 0 or not isinstance(groups, dict):
        raise ValueError("boundary contract face_count/groups are invalid")
    face_ids: list[int] = []
    nonempty_groups: set[str] = set()
    for group_name, raw_ids in groups.items():
        if not isinstance(group_name, str) or not isinstance(raw_ids, list):
            raise ValueError("boundary contract groups must map names to face-id lists")
        if raw_ids:
            nonempty_groups.add(group_name)
        if any(not isinstance(face_id, int) for face_id in raw_ids):
            raise ValueError(f"boundary contract group {group_name!r} has non-integer face ids")
        face_ids.extend(raw_ids)
    if len(face_ids) != face_count or len(set(face_ids)) != face_count or set(face_ids) != set(range(face_count)):
        raise ValueError("boundary contract face groups do not classify every face exactly once")

    roles = contract.get("roles")
    if not isinstance(roles, dict):
        raise ValueError("boundary contract roles are missing")
    role_by_group: dict[str, str] = {}
    normalized_roles: dict[str, list[str]] = {role: [] for role in BOUNDARY_ROLES}
    for role, raw_names in roles.items():
        if role not in BOUNDARY_ROLES:
            raise ValueError(f"boundary contract contains unsupported role: {role!r}")
        if not isinstance(raw_names, list) or any(not isinstance(name, str) for name in raw_names):
            raise ValueError(f"boundary contract role {role!r} must contain group names")
        for group_name in raw_names:
            if group_name in role_by_group:
                raise ValueError(f"boundary contract group has multiple roles: {group_name!r}")
            if group_name not in groups:
                raise ValueError(f"boundary contract role references unknown group: {group_name!r}")
            role_by_group[group_name] = role
            normalized_roles[role].append(group_name)
    missing_roles = sorted(nonempty_groups - set(role_by_group))
    if missing_roles:
        raise ValueError("boundary contract groups have no role: " + ", ".join(missing_roles))
    for required_role in ("gate", "vent", "wall"):
        if not any(groups.get(name) for name in normalized_roles[required_role]):
            raise ValueError(f"boundary contract has no non-empty {required_role} patch")

    embedded_artifact = contract.get("openfoam_artifacts")
    if not isinstance(embedded_artifact, dict):
        raise ValueError("boundary contract openfoam_artifacts is missing")
    if embedded_artifact.get("schema") != BOUNDARY_ARTIFACT_SCHEMA:
        raise ValueError(
            f"boundary artifact schema must be {BOUNDARY_ARTIFACT_SCHEMA!r}, "
            f"got {embedded_artifact.get('schema')!r}"
        )
    if embedded_artifact.get("status") != "PASS":
        raise ValueError("boundary artifact status must be PASS")
    artifact_path = contract_path.parent / "openfoam_patch_artifacts.json"
    if not artifact_path.is_file():
        raise ValueError(f"boundary patch artifact manifest is missing: {artifact_path}")
    try:
        artifact = json.loads(artifact_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"boundary patch artifact manifest is unreadable: {exc}") from exc
    if artifact != embedded_artifact:
        raise ValueError("boundary patch artifact manifest differs from the embedded contract artifact")

    raw_patches = artifact.get("patches")
    if not isinstance(raw_patches, dict) or set(raw_patches) != nonempty_groups:
        raise ValueError("boundary patch artifacts do not match non-empty contract groups")
    patches: dict[str, dict[str, Any]] = {}
    used_patch_names: set[str] = set()
    for group_name in sorted(raw_patches):
        patch = raw_patches[group_name]
        if not isinstance(patch, dict):
            raise ValueError(f"boundary patch artifact is invalid: {group_name!r}")
        patch_name = str(patch.get("patch_name", ""))
        if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", patch_name):
            raise ValueError(f"boundary patch name is not OpenFOAM-safe: {patch_name!r}")
        lowered_name = patch_name.lower()
        if lowered_name in used_patch_names:
            raise ValueError(f"boundary patch names are not unique: {patch_name!r}")
        used_patch_names.add(lowered_name)
        role = role_by_group[group_name]
        if patch.get("role") != role:
            raise ValueError(
                f"boundary patch role mismatch for {group_name!r}: "
                f"contract={role!r}, artifact={patch.get('role')!r}"
            )
        expected_patch_type = "patch" if role in ("gate", "vent") else "wall"
        if patch.get("openfoam_patch_type") != expected_patch_type:
            raise ValueError(f"boundary patch type mismatch for {group_name!r}")
        if patch.get("face_count") != len(groups[group_name]) or len(groups[group_name]) <= 0:
            raise ValueError(f"boundary patch face count mismatch for {group_name!r}")
        try:
            area = float(patch.get("area_model_units2"))
        except (TypeError, ValueError) as exc:
            raise ValueError(f"boundary patch area is invalid for {group_name!r}") from exc
        if not math.isfinite(area) or area <= 0.0:
            raise ValueError(f"boundary patch area must be positive for {group_name!r}")
        surface_file = patch.get("surface_file")
        if not surface_file:
            raise ValueError(f"boundary patch surface_file is missing for {group_name!r}")
        surface_path = _resolve_contract_file(surface_file, base_dir=contract_path.parent)
        if not surface_path.is_file() or surface_path.suffix.lower() != ".stl":
            raise ValueError(f"boundary patch STL is missing for {group_name!r}: {surface_path}")
        patches[group_name] = {
            **patch,
            "role": role,
            "source_path": surface_path,
            "source_sha256": _sha256_file(surface_path),
        }

    model = _verified_hashed_reference(contract_path, contract, "model")
    spec_reference = _verified_hashed_reference(contract_path, contract, "spec")
    canonical_units, scale = _contract_units_scale_to_m(contract, params)
    return {
        "path": contract_path,
        "sha256": _sha256_file(contract_path),
        "artifact_path": artifact_path.resolve(),
        "artifact_sha256": _sha256_file(artifact_path),
        "model": model,
        "spec": spec_reference,
        "units": canonical_units,
        "scale_to_m": scale,
        "roles": normalized_roles,
        "patches": patches,
        "topology": topology,
    }


def _combined_patch_bbox(patches: dict[str, dict[str, Any]]) -> dict[str, float]:
    boxes = [stl_bbox_mm(Path(patch["source_path"])) for patch in patches.values()]
    if not boxes:
        raise ValueError("boundary contract contains no patch STL files")
    xmin = min(box["xmin"] for box in boxes)
    xmax = max(box["xmax"] for box in boxes)
    ymin = min(box["ymin"] for box in boxes)
    ymax = max(box["ymax"] for box in boxes)
    zmin = min(box["zmin"] for box in boxes)
    zmax = max(box["zmax"] for box in boxes)
    return {
        "xmin": xmin,
        "xmax": xmax,
        "ymin": ymin,
        "ymax": ymax,
        "zmin": zmin,
        "zmax": zmax,
        "length": max(xmax - xmin, 1e-12),
        "width": max(ymax - ymin, 1e-12),
        "height": max(zmax - zmin, 1e-12),
    }


def _copy_scaled_contract_surfaces(
    tri_dir: Path, patches: dict[str, dict[str, Any]], scale: float
) -> dict[str, dict[str, Any]]:
    copied: dict[str, dict[str, Any]] = {}
    for group_name, patch in patches.items():
        target = tri_dir / f"{patch['patch_name']}.stl"
        source = Path(patch["source_path"])
        if scale == 1.0:
            shutil.copy2(source, target)
        else:
            import pyvista as pv

            mesh = pv.read(source)
            if mesh.n_points <= 0:
                raise ValueError(f"boundary patch STL has no points: {source}")
            mesh.points *= scale
            mesh.save(target)
        copied[group_name] = {
            "group_name": group_name,
            "patch_name": patch["patch_name"],
            "role": patch["role"],
            "openfoam_patch_type": patch["openfoam_patch_type"],
            "face_count": patch["face_count"],
            "area_model_units2": patch["area_model_units2"],
            "source_path": str(source),
            "source_sha256": patch["source_sha256"],
            "case_surface_file": str(target.relative_to(tri_dir.parent.parent)).replace("\\", "/"),
            "case_surface_sha256": _sha256_file(target),
        }
    return copied


def _contract_snappy_dict(
    patches: dict[str, dict[str, Any]], params: dict[str, Any], location: tuple[float, float, float]
) -> str:
    min_level = int(params.get("surface_refinement_min_level", 1))
    max_level = int(params.get("surface_refinement_max_level", 2))
    feature_level = int(params.get("feature_refinement_level", max_level))
    if not 0 <= min_level <= max_level <= 8 or not 0 <= feature_level <= 8:
        raise ValueError("boundary contract refinement levels must be between 0 and 8")
    geometry_lines: list[str] = []
    feature_lines: list[str] = []
    refinement_lines: list[str] = []
    for patch in patches.values():
        name = patch["patch_name"]
        patch_type = patch["openfoam_patch_type"]
        geometry_lines.append(f"    {name}.stl {{ type triSurfaceMesh; name {name}; }}")
        feature_lines.append(f'        {{ file "{name}.eMesh"; level {feature_level}; }}')
        refinement_lines.append(
            f"        {name} {{ level ({min_level} {max_level}); patchInfo {{ type {patch_type}; }} }}"
        )
    lx, ly, lz = location
    return (
        "FoamFile { version 2.0; format ascii; class dictionary; object snappyHexMeshDict; }\n"
        "castellatedMesh true; snap true; addLayers false;\n"
        "geometry\n{\n"
        + "\n".join(geometry_lines)
        + "\n}\n"
        "castellatedMeshControls\n{\n"
        f"    maxLocalCells {int(params.get('max_local_cells', 80000))};\n"
        f"    maxGlobalCells {int(params.get('max_global_cells', 120000))};\n"
        "    minRefinementCells 10;\n"
        "    maxLoadUnbalance 0.10;\n"
        "    nCellsBetweenLevels 1;\n"
        "    features\n    (\n"
        + "\n".join(feature_lines)
        + "\n    );\n"
        "    refinementSurfaces\n    {\n"
        + "\n".join(refinement_lines)
        + "\n    }\n"
        "    resolveFeatureAngle 30;\n"
        "    refinementRegions {}\n"
        f"    locationInMesh ({lx:g} {ly:g} {lz:g});\n"
        "    allowFreeStandingZoneFaces true;\n"
        "}\n"
        "snapControls\n{\n"
        "    nSmoothPatch 3; tolerance 2.0; nSolveIter 30; nRelaxIter 5; nFeatureSnapIter 10;\n"
        "    implicitFeatureSnap false; explicitFeatureSnap true; multiRegionFeatureSnap false;\n"
        "}\n"
        "addLayersControls { relativeSizes true; layers {}; expansionRatio 1.0; "
        "finalLayerThickness 0.3; minThickness 0.1; nGrow 0; }\n"
        "meshQualityControls\n{\n"
        "    maxNonOrtho 65; maxBoundarySkewness 20; maxInternalSkewness 4; maxConcave 80;\n"
        "    minVol 1e-13; minTetQuality 1e-30; minArea -1; minTwist 0.05;\n"
        "    minTriangleTwist -1; minDeterminant 0.001; minFaceWeight 0.05;\n"
        "    minVolRatio 0.01; triangleTwist false; errorReduction 0.75; nSmoothScale 4;\n"
        "}\n"
        "mergeTolerance 1e-6;\n"
    )


def _contract_surface_feature_dict(
    patches: dict[str, dict[str, Any]], params: dict[str, Any]
) -> str:
    included_angle = float(params.get("feature_included_angle_deg", 150.0))
    if not 0.0 < included_angle < 180.0:
        raise ValueError("feature_included_angle_deg must be between 0 and 180")
    blocks = []
    for patch in patches.values():
        name = patch["patch_name"]
        blocks.append(
            f"{name}.stl\n{{\n"
            "    extractionMethod extractFromSurface;\n"
            "    extractFromSurfaceCoeffs\n    {\n"
            f"        includedAngle {included_angle:g};\n"
            "    }\n"
            "    writeObj yes;\n"
            "}"
        )
    return (
        "FoamFile\n{\n"
        "    version 2.0;\n"
        "    format ascii;\n"
        "    class dictionary;\n"
        "    object surfaceFeatureExtractDict;\n"
        "}\n\n"
        + "\n\n".join(blocks)
        + "\n"
    )


def _write_noop_legacy_patch_dicts(run_dir: Path) -> None:
    """Keep legacy runner commands harmless when snappy creates final patches."""
    (run_dir / "system" / "topoSetDict").write_text(
        "FoamFile { version 2.0; format ascii; class dictionary; object topoSetDict; }\n"
        "actions ();\n",
        encoding="utf-8",
    )
    (run_dir / "system" / "createPatchDict").write_text(
        "FoamFile { version 2.0; format ascii; class dictionary; object createPatchDict; }\n"
        "pointSync false;\npatches ();\n",
        encoding="utf-8",
    )


def _replace_boundary_field(text: str, entries: list[str], path: Path) -> str:
    match = re.search(r"\bboundaryField\s*\{", text)
    if match is None:
        raise ValueError(f"boundaryField not found in {path}")
    opening = text.find("{", match.start())
    depth = 0
    closing = -1
    for index in range(opening, len(text)):
        if text[index] == "{":
            depth += 1
        elif text[index] == "}":
            depth -= 1
            if depth == 0:
                closing = index
                break
    if closing < 0:
        raise ValueError(f"boundaryField is unbalanced in {path}")
    body = "boundaryField\n{\n" + "\n".join(entries) + "\n}"
    return text[: match.start()] + body + text[closing + 1 :]


def _explicit_gate_velocity(params: dict[str, Any], patch_name: str) -> tuple[float, float, float]:
    patch_settings = params.get("boundary_patch_conditions", {})
    if patch_settings is None:
        patch_settings = {}
    if not isinstance(patch_settings, dict):
        raise ValueError("boundary_patch_conditions must be an object")
    settings = patch_settings.get(patch_name, {})
    if not isinstance(settings, dict):
        raise ValueError(f"boundary_patch_conditions[{patch_name!r}] must be an object")
    vector = settings.get("inlet_velocity_xyz", params.get("inlet_velocity_xyz"))
    if isinstance(vector, (list, tuple)) and len(vector) == 3:
        try:
            values = tuple(float(value) for value in vector)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"gate velocity vector is invalid for {patch_name!r}") from exc
        if all(math.isfinite(value) for value in values) and any(abs(value) > 0.0 for value in values):
            return values  # type: ignore[return-value]
    speed = settings.get("inlet_velocity", params.get("inlet_velocity"))
    direction = settings.get("gate_inflow_direction", params.get("gate_inflow_direction"))
    if speed is not None and isinstance(direction, (list, tuple)) and len(direction) == 3:
        speed_value = float(speed)
        direction_values = tuple(float(value) for value in direction)
        norm = math.sqrt(sum(value * value for value in direction_values))
        if math.isfinite(speed_value) and speed_value > 0.0 and norm > 1e-12:
            return tuple(speed_value * value / norm for value in direction_values)  # type: ignore[return-value]
    raise ValueError(
        f"explicit inlet_velocity_xyz or inlet_velocity plus gate_inflow_direction is required "
        f"for contract gate {patch_name!r}"
    )


def _apply_contract_zero_boundaries(
    run_dir: Path, patches: dict[str, dict[str, Any]], params: dict[str, Any]
) -> None:
    ordered = list(patches.values())
    gate_velocities = {
        patch["patch_name"]: _explicit_gate_velocity(params, patch["patch_name"])
        for patch in ordered
        if patch["role"] == "gate"
    }

    def entries_for(field_name: str, internal_value: str | None) -> list[str]:
        entries: list[str] = []
        for patch in ordered:
            name = patch["patch_name"]
            role = patch["role"]
            if field_name == "U":
                if role == "gate":
                    velocity = gate_velocities[name]
                    body = f"type fixedValue; value uniform ({velocity[0]:g} {velocity[1]:g} {velocity[2]:g});"
                elif role == "vent":
                    body = "type pressureInletOutletVelocity; value uniform (0 0 0);"
                else:
                    body = "type noSlip;"
            elif field_name == "alpha.polymer":
                if role == "gate":
                    body = "type fixedValue; value uniform 1;"
                elif role == "vent":
                    body = "type inletOutlet; inletValue uniform 0; value uniform 0;"
                else:
                    body = "type zeroGradient;"
            elif field_name == "p_rgh":
                if internal_value is None:
                    raise ValueError("p_rgh requires a uniform numeric internalField")
                if role == "vent":
                    body = f"type totalPressure; p0 uniform {internal_value}; value uniform {internal_value};"
                else:
                    body = f"type fixedFluxPressure; value uniform {internal_value};"
            elif field_name == "p":
                pressure = params.get("initial_cavity_pressure_pa")
                if pressure is None:
                    raise ValueError("initial_cavity_pressure_pa is required for contract p boundaries")
                pressure_value = float(pressure)
                if not math.isfinite(pressure_value) or pressure_value <= 0.0:
                    raise ValueError("initial_cavity_pressure_pa must be positive")
                body = (
                    f"type fixedValue; value uniform {pressure_value:g};"
                    if role == "vent"
                    else f"type calculated; value uniform {pressure_value:g};"
                )
            elif field_name in ("T", "T.air", "T.polymer"):
                if "T_melt" not in params or "T_mold" not in params:
                    raise ValueError(f"T_melt and T_mold are required for contract {field_name} boundaries")
                temperature = float(params["T_melt"] if role == "gate" else params["T_mold"])
                if not math.isfinite(temperature) or temperature <= 0.0:
                    raise ValueError(f"temperature is invalid for {name!r}")
                if role == "vent":
                    body = f"type inletOutlet; inletValue uniform {temperature:g}; value uniform {temperature:g};"
                else:
                    body = f"type fixedValue; value uniform {temperature:g};"
            else:
                raise ValueError(f"unsupported contract boundary field: {field_name}")
            entries.append(f"    {name}\n    {{\n        {body}\n    }}")
        return entries

    for field_name in ("U", "alpha.polymer", "p_rgh", "p", "T", "T.air", "T.polymer"):
        path = run_dir / "0" / field_name
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        internal_match = re.search(r"internalField\s+uniform\s+([-+0-9.eE]+)\s*;", text)
        internal_value = internal_match.group(1) if internal_match else None
        if field_name == "p":
            pressure = float(params.get("initial_cavity_pressure_pa", 0.0))
            if pressure <= 0.0:
                raise ValueError("initial_cavity_pressure_pa is required for contract p boundaries")
            text, count = re.subn(
                r"internalField\s+uniform\s+[^;]+;",
                f"internalField uniform {pressure:g};",
                text,
                count=1,
            )
            if count != 1:
                raise ValueError(f"uniform internalField not found in {path}")
        elif field_name in ("T", "T.air", "T.polymer"):
            if "T_mold" not in params:
                raise ValueError(f"T_mold is required for contract {field_name} internalField")
            text, count = re.subn(
                r"internalField\s+uniform\s+[^;]+;",
                f"internalField uniform {float(params['T_mold']):g};",
                text,
                count=1,
            )
            if count != 1:
                raise ValueError(f"uniform internalField not found in {path}")
        text = _replace_boundary_field(text, entries_for(field_name, internal_value), path)
        path.write_text(text, encoding="utf-8")


def overlay_snappy_thermo_physics(run_dir: Path, params: dict[str, Any]) -> None:
    """Overlay thermo dictionaries without replacing proven snappy mesh/patch fields."""
    physics = str(params.get("physics_category", "resin_fill_vof"))
    if physics not in ("resin_fill_cool", "resin_fill_thermo"):
        return
    source = PHYSICS_TEMPLATES[physics]
    required = (
        "constant/thermophysicalProperties",
        "constant/thermophysicalProperties.air",
        "constant/thermophysicalProperties.polymer",
        "system/controlDict",
        "system/controlDict.ascii",
        "system/fvSchemes",
        "system/fvSchemes.ascii",
        "system/fvSolution",
        "system/fvSolution.ascii",
    )
    missing = [rel for rel in required if not (source / rel).is_file()]
    if missing:
        raise ValueError("thermo overlay source missing: " + ", ".join(missing))
    for rel in required:
        destination = run_dir / rel
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source / rel, destination)

    thermal_max_co = float(params.get("thermal_max_co", 0.02))
    if not 0.0 < thermal_max_co <= 0.5:
        raise ValueError("thermal_max_co must be in (0, 0.5]")
    thermal_max_alpha_co = float(params.get("thermal_max_alpha_co", 0.05))
    if not 0.0 < thermal_max_alpha_co <= 0.5:
        raise ValueError("thermal_max_alpha_co must be in (0, 0.5]")
    thermal_initial_delta_t = float(params.get("thermal_initial_delta_t_s", 1e-6))
    if not 0.0 < thermal_initial_delta_t <= 1e-4:
        raise ValueError("thermal_initial_delta_t_s must be in (0, 1e-4]")
    for control_name in ("controlDict", "controlDict.ascii"):
        control_path = run_dir / "system" / control_name
        control = control_path.read_text(encoding="utf-8", errors="replace")
        control, count = re.subn(
            r"maxCo\s+[0-9.eE+-]+;",
            f"maxCo           {thermal_max_co:g};",
            control,
            count=1,
        )
        if count != 1:
            raise ValueError(f"maxCo entry not found in {control_path}")
        control, alpha_count = re.subn(
            r"maxAlphaCo\s+[0-9.eE+-]+;",
            f"maxAlphaCo      {thermal_max_alpha_co:g};",
            control,
            count=1,
        )
        control, delta_count = re.subn(
            r"deltaT\s+[0-9.eE+-]+;",
            f"deltaT          {thermal_initial_delta_t:g};",
            control,
            count=1,
        )
        if alpha_count != 1 or delta_count != 1:
            raise ValueError(f"thermal time controls not found in {control_path}")
        control_path.write_text(control, encoding="utf-8")

    temperature_relaxation = float(params.get("temperature_relaxation", 0.1))
    if not 0.0 < temperature_relaxation <= 1.0:
        raise ValueError("temperature_relaxation must be in (0, 1]")
    for solution_name in ("fvSolution", "fvSolution.ascii"):
        solution_path = run_dir / "system" / solution_name
        solution = solution_path.read_text(encoding="utf-8", errors="replace")
        if re.search(r"\brelaxationFactors\b", solution):
            raise ValueError(f"unexpected existing relaxationFactors in {solution_path}")
        solution += (
            "\nrelaxationFactors\n"
            "{\n"
            "    equations\n"
            "    {\n"
            f"        T       {temperature_relaxation:g};\n"
            "    }\n"
            "}\n"
        )
        solution_path.write_text(solution, encoding="utf-8")

    (run_dir / "0").mkdir(parents=True, exist_ok=True)
    (run_dir / "0" / "T").write_text(
        "FoamFile { version 2.0; format ascii; class volScalarField; object T; }\n"
        "dimensions [0 0 0 1 0 0 0];\n"
        "internalField uniform T_MOLD_PLACEHOLDER;\n"
        "boundaryField\n{\n"
        "    gate { type fixedValue; value uniform T_MELT_PLACEHOLDER; }\n"
        "    vent { type inletOutlet; inletValue uniform T_MOLD_PLACEHOLDER; value uniform T_MOLD_PLACEHOLDER; }\n"
        "    moldflow { type fixedValue; value uniform T_MOLD_PLACEHOLDER; }\n"
        "}\n",
        encoding="utf-8",
    )
    (run_dir / "0" / "p").write_text(
        "FoamFile { version 2.0; format ascii; class volScalarField; object p; }\n"
        "dimensions [1 -1 -2 0 0 0 0];\n"
        "internalField uniform 101325;\n"
        "boundaryField\n{\n"
        "    gate { type calculated; value uniform 101325; }\n"
        "    vent { type fixedValue; value uniform 101325; }\n"
        "    moldflow { type calculated; value uniform 101325; }\n"
        "}\n",
        encoding="utf-8",
    )


def apply_mfalign_control_overrides(run_dir: Path, params: dict[str, Any]) -> None:
    """Apply time controls consistently to runtime and restore-source dictionaries."""
    for cd_path in (
        run_dir / "system" / "controlDict",
        run_dir / "system" / "controlDict.ascii",
    ):
        if not cd_path.is_file():
            continue
        cd = cd_path.read_text(encoding="utf-8")
        end_time = params.get("analysis_end_time_s")
        if end_time is not None:
            cd, count = re.subn(
                r"endTime\s+[^;]+;",
                f"endTime         {float(end_time)};",
                cd,
                count=1,
            )
            if count != 1:
                raise ValueError(f"endTime entry not found in {cd_path}")
        write_interval = params.get("write_interval_s")
        if write_interval is not None:
            interval = float(write_interval)
            if interval <= 0:
                raise ValueError("write_interval_s must be positive")
            cd, control_count = re.subn(
                r"writeControl\s+\w+;",
                "writeControl    adjustableRunTime;",
                cd,
                count=1,
            )
            cd, interval_count = re.subn(
                r"writeInterval\s+[0-9.eE+-]+;",
                f"writeInterval   {interval:g};",
                cd,
                count=1,
            )
            if control_count != 1 or interval_count != 1:
                raise ValueError(f"write controls not found in {cd_path}")
        cd_path.write_text(cd, encoding="utf-8")


def build_mfalign_snappy_case(
    run_dir: Path,
    template_dir: Path,
    step_path: Path | None,
    gate_spec_path: Path,
    spec: dict[str, Any],
    params: dict[str, Any],
) -> dict[str, Any]:
    """Instantiate the proven MFALIGN closed-cavity case for a triangulated surface.

    The template carries hand-tuned values (locationInMesh inside the 2 mm shell
    wall, topoSet gate/vent cylinders) that are only valid for the reference
    geometry, so a differing surface must supply them explicitly.
    """
    boundary_contract = load_boundary_contract(params)
    if boundary_contract is None:
        surface_stl = resolve_surface_stl(step_path, params)
        bbox_raw = stl_bbox_mm(surface_stl)
        scale = resolve_geometry_scale_to_m(bbox_raw, params)
    else:
        surface_stl = None
        bbox_raw = _combined_patch_bbox(boundary_contract["patches"])
        scale = float(boundary_contract["scale_to_m"])
    bbox_m = {k: v * scale for k, v in bbox_raw.items()}
    bbox = {k: v * 1000.0 for k, v in bbox_m.items()}

    dims_mm = (bbox["length"], bbox["width"], bbox["height"])
    matches_reference = all(
        abs(got - ref) <= REFERENCE_GEOMETRY_TOL * ref
        for got, ref in zip(dims_mm, REFERENCE_GEOMETRY_MM)
    )
    location = params.get("location_in_mesh_m")
    if boundary_contract is not None and location is None:
        raise ValueError(
            "location_in_mesh_m is required with boundary_contract_path; "
            "the contract classifies surfaces but does not certify the retained volume"
        )
    if location is None and not matches_reference:
        raise ValueError(
            "location_in_mesh_m is required for a non-reference geometry "
            f"(bbox {dims_mm[0]:.1f}x{dims_mm[1]:.1f}x{dims_mm[2]:.1f} mm vs reference "
            f"{REFERENCE_GEOMETRY_MM[0]:.0f}x{REFERENCE_GEOMETRY_MM[1]:.0f}x"
            f"{REFERENCE_GEOMETRY_MM[2]:.0f} mm); the template value sits inside the "
            "reference shell wall and would select the wrong volume"
        )
    if location is not None:
        if not isinstance(location, (list, tuple)) or len(location) != 3:
            raise ValueError("location_in_mesh_m must contain three coordinates")
        location_values = tuple(float(value) for value in location)
        if not all(math.isfinite(value) for value in location_values):
            raise ValueError("location_in_mesh_m must contain finite coordinates")
    else:
        location_values = None

    if run_dir.exists():
        shutil.rmtree(run_dir, ignore_errors=True)
    shutil.copytree(template_dir, run_dir)
    overlay_snappy_thermo_physics(run_dir, params)

    tri_dir = run_dir / "constant" / "triSurface"
    tri_dir.mkdir(parents=True, exist_ok=True)
    contract_case_patches: dict[str, dict[str, Any]] | None = None
    if boundary_contract is not None:
        for existing_surface in tri_dir.glob("*.stl"):
            existing_surface.unlink()
        contract_case_patches = _copy_scaled_contract_surfaces(
            tri_dir, boundary_contract["patches"], scale
        )
    else:
        stl_target = tri_dir / "Moldflow.stl"
        if scale == 1.0:
            shutil.copy2(surface_stl, stl_target)
        else:
            import pyvista as pv

            mesh = pv.read(surface_stl)
            mesh.points *= scale
            mesh.save(stl_target)

    margin = float(params.get("background_margin_m", 0.002))
    x_min, x_max = bbox_m["xmin"] - margin, bbox_m["xmax"] + margin
    y_min, y_max = bbox_m["ymin"] - margin, bbox_m["ymax"] + margin
    z_min, z_max = bbox_m["zmin"] - margin, bbox_m["zmax"] + margin
    nx = int(params.get("mesh_nx", 18))
    ny = int(params.get("mesh_ny", 12))
    nz = int(params.get("mesh_nz", 12))
    (run_dir / "system" / "blockMeshDict").write_text(
        "FoamFile { version 2.0; format ascii; class dictionary; object blockMeshDict; }\n"
        "convertToMeters 1;\n"
        "vertices (\n"
        f"    ({x_min} {y_min} {z_min}) ({x_max} {y_min} {z_min})"
        f" ({x_max} {y_max} {z_min}) ({x_min} {y_max} {z_min})\n"
        f"    ({x_min} {y_min} {z_max}) ({x_max} {y_min} {z_max})"
        f" ({x_max} {y_max} {z_max}) ({x_min} {y_max} {z_max})\n"
        ");\n"
        f"blocks ( hex (0 1 2 3 4 5 6 7) ({nx} {ny} {nz}) simpleGrading (1 1 1) );\n"
        "edges ();\n"
        "boundary (\n"
        "    inlet { type patch; faces ((0 4 7 3)); }\n"
        "    outlet { type patch; faces ((1 2 6 5)); }\n"
        "    walls { type wall; faces ((0 1 5 4) (3 7 6 2) (0 3 2 1) (4 5 6 7)); }\n"
        ");\n"
        "mergePatchPairs ();\n",
        encoding="utf-8",
    )

    snappy_path = run_dir / "system" / "snappyHexMeshDict"
    location_source = "template_reference"
    if boundary_contract is not None:
        assert location_values is not None
        snappy = _contract_snappy_dict(
            boundary_contract["patches"], params, location_values
        )
        (run_dir / "system" / "surfaceFeatureExtractDict").write_text(
            _contract_surface_feature_dict(boundary_contract["patches"], params),
            encoding="utf-8",
        )
        _write_noop_legacy_patch_dicts(run_dir)
        location_source = "boundary_contract_params"
    else:
        snappy = snappy_path.read_text(encoding="utf-8")
        snappy = re.sub(
            r"maxLocalCells\s+\d+;",
            f"maxLocalCells {int(params.get('max_local_cells', 80000))};",
            snappy,
        )
        snappy = re.sub(
            r"maxGlobalCells\s+\d+;",
            f"maxGlobalCells {int(params.get('max_global_cells', 120000))};",
            snappy,
        )
        if location_values is not None:
            lx, ly, lz = location_values
            snappy = re.sub(
                r"locationInMesh\s+\([^)]*\);",
                f"locationInMesh ({lx} {ly} {lz});",
                snappy,
            )
            location_source = "params"
    snappy_path.write_text(snappy, encoding="utf-8")
    location_used = re.search(r"locationInMesh\s+\(([^)]*)\)", snappy)

    u_path = run_dir / "0" / "U"
    if boundary_contract is not None:
        _apply_contract_zero_boundaries(run_dir, boundary_contract["patches"], params)
        gate_speeds = []
        for patch in boundary_contract["patches"].values():
            if patch["role"] == "gate":
                velocity = _explicit_gate_velocity(params, patch["patch_name"])
                gate_speeds.append(math.sqrt(sum(component * component for component in velocity)))
        inlet_velocity = max(gate_speeds)
    else:
        inlet_velocity = float(params.get("inlet_velocity", 6.51))
        # Prefer MF-aligned gate_inflow_direction / inlet_velocity_xyz; legacy default -X.
        try:
            import moldflow_gate_spec as _gate_spec

            u_triple = _gate_spec.inlet_velocity_triple(params, speed=inlet_velocity)
        except Exception:
            u_triple = f"(-{inlet_velocity} 0 0)"
        u_text = re.sub(
            r"(gate\s*\{\s*type fixedValue; value uniform )\([^)]*\)",
            rf"\g<1>{u_triple}",
            u_path.read_text(encoding="utf-8"),
        )
        u_path.write_text(u_text, encoding="utf-8")

    apply_mfalign_control_overrides(run_dir, params)

    tp_path = run_dir / "constant" / "transportProperties"
    tp = tp_path.read_text(encoding="utf-8")
    for key, param_key in (
        ("k", "power_law_k"),
        ("n", "power_law_n"),
        ("nuMax", "power_law_nuMax"),
        ("nuMin", "power_law_nuMin"),
    ):
        val = params.get(param_key)
        if val is not None:
            tp = re.sub(
                rf"^(\s*{key}\s+\[[^\]]*\]\s+)[0-9.eE+-]+;",
                rf"\g<1>{float(val)};",
                tp,
                count=1,
                flags=re.MULTILINE,
            )
    rho = params.get("polymer_density_kg_m3")
    if rho is not None:
        tp = re.sub(
            r"^(\s*rho\s+\[[^\]]*\]\s+)[0-9.eE+-]+;",
            rf"\g<1>{float(rho)};",
            tp,
            count=1,
            flags=re.MULTILINE,
        )
    tp_path.write_text(tp, encoding="utf-8")

    if boundary_contract is not None:
        assert contract_case_patches is not None
        manifest_patches = {
            f"{role}s": [
                boundary_contract["patches"][group_name]["patch_name"]
                for group_name in boundary_contract["roles"][role]
                if group_name in boundary_contract["patches"]
            ]
            for role in BOUNDARY_ROLES
        }
        contract_manifest = {
            "schema": BOUNDARY_CONTRACT_SCHEMA,
            "status": "PASS",
            "path": str(boundary_contract["path"]),
            "sha256": boundary_contract["sha256"],
            "artifact_path": str(boundary_contract["artifact_path"]),
            "artifact_sha256": boundary_contract["artifact_sha256"],
            "model": boundary_contract["model"],
            "spec": boundary_contract["spec"],
            "units": boundary_contract["units"],
            "surface_units_scale_to_m": scale,
            "topology": boundary_contract["topology"],
            "roles": boundary_contract["roles"],
            "patches": contract_case_patches,
            "legacy_patch_split": "disabled_noop_dictionaries",
        }
        surface_manifest: Any = [
            patch["case_surface_file"] for patch in contract_case_patches.values()
        ]
        source_path = boundary_contract["model"]["path"]
        bbox_source = "boundary_contract_patch_surfaces"
    else:
        manifest_patches = {"gates": ["gate"], "vents": ["vent"], "walls": ["moldflow"]}
        contract_manifest = None
        surface_manifest = str(surface_stl)
        source_path = str(surface_stl)
        bbox_source = "stl"

    manifest = {
        "phase": 7,
        "bbox_mm": bbox,
        "bbox_source": bbox_source,
        "mesh_mode": "snappyhexmesh",
        "mesh_info": {
            "template": "mfalign_snappy_v001",
            "surface_stl": surface_manifest,
            "surface_units_scale_to_m": scale,
            "background_block": [nx, ny, nz],
            "background_margin_m": margin,
            "location_in_mesh": location_used.group(1) if location_used else None,
            "location_in_mesh_source": location_source,
            "matches_reference_geometry": matches_reference,
        },
        "mesh_nx": nx,
        "mesh_nz": nz,
        "inlet_velocity_m_s": inlet_velocity,
        "step_path": source_path,
        "gate_spec_path": str(gate_spec_path),
        "physics_category": params.get("physics_category", "resin_fill_vof"),
        "template_dir": str(template_dir),
        "patches": manifest_patches,
    }
    if contract_manifest is not None:
        manifest["boundary_contract"] = contract_manifest
    (run_dir / "cad_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (run_dir / "gate_spec.resolved.json").write_text(
        json.dumps(spec, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return manifest


def build_case(
    run_dir: Path,
    template_dir: Path,
    step_path: Path | None,
    gate_spec_path: Path,
    params: dict[str, Any],
) -> dict[str, Any]:
    # Optional fidelity ladder (extends mesh_mode/physics; never removes modes).
    try:
        import cae_fidelity_mode as _cfm

        params.update(_cfm.apply_fidelity_mode(params))
    except Exception:
        pass

    spec = gate_spec_mod.load_gate_spec(gate_spec_path)
    issues = gate_spec_mod.validate_gate_spec(
        spec, require_patch_names=required_patch_names(params)
    )
    if issues:
        raise ValueError("gate_spec invalid: " + "; ".join(issues))

    if resolve_mesh_mode(params) == "snappyhexmesh":
        return build_mfalign_snappy_case(
            run_dir, template_dir, step_path, gate_spec_path, spec, params
        )

    if params.get("_manifest_bbox_mm"):
        bbox = params["_manifest_bbox_mm"]
        bbox_source = "manifest"
    elif step_path and step_path.exists():
        bbox = geometry_bbox_mm(step_path)
        bbox_source = "stl" if step_path.suffix.lower() == ".stl" else "step"
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
        "mesh_nx": int(params.get("mesh_nx", 50)),
        "mesh_nz": int(params.get("mesh_nz", 1)),
        "inlet_velocity_m_s": float(params.get("inlet_velocity", 1.0)),
        "wall_shear_calibration_factor": float(
            params.get("wall_shear_calibration_factor", 1.0)
        ),
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
