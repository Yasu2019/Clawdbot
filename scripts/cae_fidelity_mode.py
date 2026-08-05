#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""User-selectable OpenFOAM fidelity ladder (extends existing mesh/physics; no removals).

Modes trade Moldflow-like speed vs thermo/3D fidelity. All remain PROXY_GAP unless
a later validation gate promotes the label.
"""
from __future__ import annotations

import argparse
import json
import sys
from copy import deepcopy
from pathlib import Path
from typing import Any

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

ROOT = Path(__file__).resolve().parents[1]
CATALOG_PATH = ROOT / "data" / "workspace" / "cae_fidelity_modes.json"

# Existing mesh_mode values are preserved. Presets only overlay defaults.
FIDELITY_PRESETS: dict[str, dict[str, Any]] = {
    "quick": {
        "label": "Quick / coarse isothermal",
        "description": "Fastest OF path: blockmesh_bbox + isothermal VOF, coarse cells. Trend check only.",
        "accuracy_band_label": "PROXY_GAP",
        "moldflow_analogy": "quick fill screen / early Midplane-like exploration",
        "params": {
            "physics_category": "resin_fill_vof",
            "mesh_mode": "blockmesh_bbox",
            "mesh_nx": 24,
            "mesh_ny": 12,
            "mesh_nz": 8,
            "max_global_cells": 40000,
            "analysis_end_time_s": 0.08,
            "write_interval_s": 0.02,
            "thermal_startup_smoke": False,
        },
    },
    "shell_proxy": {
        "label": "Shell / thin-wall proxy",
        "description": (
            "Thin-wall oriented coarse 3D (small through-thickness resolution). "
            "Not FEM shell elements; Hele-Shaw/Midplane-class exploration proxy."
        ),
        "accuracy_band_label": "PROXY_GAP",
        "moldflow_analogy": "Midplane / Dual Domain exploratory substitute",
        "params": {
            "physics_category": "resin_fill_vof",
            "mesh_mode": "blockmesh_bbox",
            "mesh_nx": 36,
            "mesh_ny": 16,
            "mesh_nz": 6,
            "max_global_cells": 60000,
            "analysis_end_time_s": 0.20,
            "write_interval_s": 0.04,
            "thermal_startup_smoke": False,
        },
    },
    "coarse_3d": {
        "label": "Coarse 3D VOF",
        "description": "Coarser snappy/block 3D isothermal cavity fill for gate/short-shot checks.",
        "accuracy_band_label": "PROXY_GAP",
        "moldflow_analogy": "3D fill shape check (not Cool/Warp)",
        "params": {
            "physics_category": "resin_fill_vof",
            "mesh_mode": "snappyhexmesh",
            "max_global_cells": 60000,
            "mesh_ny": 12,
            "mesh_nz": 12,
            "analysis_end_time_s": 0.40,
            "write_interval_s": 0.05,
            "thermal_startup_smoke": False,
        },
    },
    "thermo_3d": {
        "label": "Thermo 3D VOF",
        "description": "Current high-cost path: snappy + resin_fill_cool (temperature). Required before cooling/warpage proxy.",
        "accuracy_band_label": "PROXY_GAP",
        "moldflow_analogy": "Fill+Cool oriented (still PROXY_GAP vs commercial)",
        "params": {
            "physics_category": "resin_fill_cool",
            "mesh_mode": "snappyhexmesh",
            "max_global_cells": 120000,
            "mesh_ny": 16,
            "mesh_nz": 16,
            "thermal_startup_smoke": False,
        },
    },
}

ALIASES = {
    "fast": "quick",
    "midplane": "shell_proxy",
    "shell": "shell_proxy",
    "hele_shaw": "shell_proxy",
    "coarse": "coarse_3d",
    "thermo": "thermo_3d",
    "default": "thermo_3d",
}


def normalize_fidelity_mode(mode: str | None) -> str | None:
    if mode is None:
        return None
    key = str(mode).strip().lower()
    if not key:
        return None
    key = ALIASES.get(key, key)
    if key not in FIDELITY_PRESETS:
        raise ValueError(
            f"unknown fidelity_mode={mode!r}; choose one of {sorted(FIDELITY_PRESETS)} "
            f"(aliases: {sorted(ALIASES)})"
        )
    return key


def list_fidelity_modes() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for key, preset in FIDELITY_PRESETS.items():
        rows.append(
            {
                "id": key,
                "label": preset["label"],
                "description": preset["description"],
                "accuracy_band_label": preset["accuracy_band_label"],
                "moldflow_analogy": preset["moldflow_analogy"],
                "params": deepcopy(preset["params"]),
            }
        )
    return rows


def write_catalog(path: Path | None = None) -> Path:
    out = path or CATALOG_PATH
    out.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema": "clawstack.cae_fidelity_modes.v1",
        "accuracy_policy": "PROXY_GAP until commercial validation gate passes",
        "extends_existing": [
            "mesh_mode: blockmesh_bbox|gmsh_volume|snappyhexmesh",
            "physics_category: resin_fill_vof|resin_fill_cool|...",
        ],
        "modes": list_fidelity_modes(),
        "aliases": dict(ALIASES),
    }
    temporary = out.with_suffix(".tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(out)
    return out


def apply_fidelity_mode(
    params: dict[str, Any] | None,
    mode: str | None = None,
    *,
    force: bool = False,
) -> dict[str, Any]:
    """Overlay fidelity preset onto params. Existing explicit keys win unless force=True."""
    out = dict(params or {})
    chosen = normalize_fidelity_mode(mode if mode is not None else out.get("fidelity_mode"))
    if chosen is None:
        return out
    preset = FIDELITY_PRESETS[chosen]
    for key, value in preset["params"].items():
        if force or key not in out:
            out[key] = deepcopy(value)
    out["fidelity_mode"] = chosen
    out["fidelity_label"] = preset["label"]
    out["fidelity_description"] = preset["description"]
    out["moldflow_analogy"] = preset["moldflow_analogy"]
    # Label policy: never silently claim Moldflow equivalence
    out["accuracy_band_label"] = preset["accuracy_band_label"]
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description="List/apply CAE fidelity modes")
    parser.add_argument("--list", action="store_true", help="Print mode catalog JSON")
    parser.add_argument("--write-catalog", action="store_true", help=f"Write {CATALOG_PATH}")
    parser.add_argument("--mode", default="", help="Mode id to preview applied params")
    parser.add_argument("--params-file", default="", help="Optional base params JSON")
    parser.add_argument("--force", action="store_true", help="Preset overrides existing keys")
    args = parser.parse_args()

    if args.write_catalog:
        path = write_catalog()
        print(f"wrote {path}")
    if args.list or args.write_catalog:
        print(json.dumps({"modes": list_fidelity_modes(), "aliases": ALIASES}, ensure_ascii=False, indent=2))
        if not args.mode:
            return 0
    if args.mode:
        base: dict[str, Any] = {}
        if args.params_file:
            base = json.loads(Path(args.params_file).read_text(encoding="utf-8-sig"))
        applied = apply_fidelity_mode(base, args.mode, force=args.force)
        print(json.dumps(applied, ensure_ascii=False, indent=2))
        return 0
    if not args.list and not args.write_catalog:
        parser.print_help()
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
