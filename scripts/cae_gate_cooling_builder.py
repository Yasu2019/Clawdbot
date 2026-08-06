# -*- coding: utf-8 -*-
"""Hybrid Gate & Cooling System Builder: Supports both GUI Interactive placement & External CAD (STEP/STL) import."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


HOTRUNNER_BRANDS = {
    "mold_masters": {
        "name": "Mold-Masters (Master-Series / E-Multi)",
        "valve_types": ["electric_servo", "pneumatic", "hydraulic"],
        "max_temp_C": 380.0,
        "manifold_heater_zones": 4,
    },
    "yudo": {
        "name": "YUDO (Hot Runner Valve Gate System)",
        "valve_types": ["pneumatic", "hydraulic"],
        "max_temp_C": 350.0,
        "manifold_heater_zones": 4,
    },
    "synventive": {
        "name": "Synventive (SVG Active Control Valve Gate)",
        "valve_types": ["electric_servo", "hydraulic_synchro"],
        "max_temp_C": 400.0,
        "manifold_heater_zones": 6,
    },
    "incoe": {
        "name": "INCOE (Soft-Stop Direct Flow Valve Gate)",
        "valve_types": ["pneumatic", "hydraulic"],
        "max_temp_C": 360.0,
        "manifold_heater_zones": 4,
    },
    "husky": {
        "name": "HUSKY (Ultra-Flow Hot Runner System)",
        "valve_types": ["electric_servo", "pneumatic"],
        "max_temp_C": 390.0,
        "manifold_heater_zones": 8,
    },
}

def build_gate_cooling_specification(
    mode: str = "hybrid",
    gui_params: dict[str, Any] | None = None,
    cad_files: dict[str, str] | None = None,
    hotrunner_brand: str = "mold_masters",
    actuation_type: str = "electric_servo",
) -> dict[str, Any]:
    """Build unified gate & cooling configuration for OpenFOAM + CalculiX pipeline.
    
    Modes:
      - 'gui': Interactive 3D click position & parameter forms
      - 'cad_import': Direct STEP/STL CAD model & cooling channel import
      - 'hybrid': External CAD part + GUI interactive gate & cooling placement
    """
    mode = (mode or "hybrid").lower()
    brand_info = HOTRUNNER_BRANDS.get(hotrunner_brand, HOTRUNNER_BRANDS["mold_masters"])
    spec: dict[str, Any] = {
        "builder_schema": "clawstack.gate_cooling_builder.v2",
        "mode": mode,
        "hotrunner_system": {
            "brand_key": hotrunner_brand,
            "brand_name": brand_info["name"],
            "actuation_type": actuation_type,
            "max_manifold_temp_C": brand_info["max_temp_C"],
            "heater_zones": brand_info["manifold_heater_zones"],
        },
        "part_geometry": {},
        "gates": [],
        "cooling_channels": [],
    }

    # 1. Handle Part Geometry
    if mode in ("cad_import", "hybrid") and cad_files:
        part_step = cad_files.get("part_step") or cad_files.get("part_stl")
        spec["part_geometry"] = {
            "source": "external_cad_import",
            "file_path": str(part_step) if part_step else None,
            "runner_cad_file": cad_files.get("runner_step") or cad_files.get("runner_stl"),
        }
    else:
        spec["part_geometry"] = {
            "source": "gui_default_sample",
            "sample_type": "plate_100x60x2",
        }

    # 2. Handle Gates (GUI Interactive or CAD imported)
    if mode in ("gui", "hybrid") and gui_params and "gates" in gui_params:
        for item in gui_params["gates"]:
            spec["gates"].append(
                {
                    "source": "gui_interactive_click",
                    "gate_type": item.get("gate_type", "side_gate"),
                    "position_xyz_mm": item.get("position_xyz_mm", [0.0, 30.0, 1.0]),
                    "dimensions_mm": {
                        "width": item.get("width_mm", 2.5),
                        "height": item.get("height_mm", 1.0),
                        "length": item.get("length_mm", 1.5),
                    },
                    "valve_control": item.get("valve_control", {"enabled": False}),
                }
            )
    elif mode == "cad_import" and cad_files and "gate_cad_file" in cad_files:
        spec["gates"].append(
            {
                "source": "cad_import_geometry",
                "file_path": cad_files["gate_cad_file"],
            }
        )
    else:
        # Default fallback gate
        spec["gates"].append(
            {
                "source": "default_side_gate",
                "gate_type": "side_gate",
                "position_xyz_mm": [0.0, 30.0, 1.0],
                "dimensions_mm": {"width": 2.5, "height": 1.0, "length": 1.5},
            }
        )

    # 3. Handle Cooling System (GUI Interactive parameters or External 3D Conformal Channel)
    if mode in ("cad_import", "hybrid") and cad_files and "cooling_step" in cad_files:
        spec["cooling_channels"].append(
            {
                "source": "external_3d_conformal_cad_import",
                "type": "3d_conformal_cooling",
                "file_path": cad_files["cooling_step"],
                "coolant": "water",
                "inlet_temp_C": 20.0,
                "flow_rate_Lmin": 10.0,
            }
        )

    if mode in ("gui", "hybrid") and gui_params and "cooling_channels" in gui_params:
        for item in gui_params["cooling_channels"]:
            spec["cooling_channels"].append(
                {
                    "source": "gui_interactive_parameters",
                    "type": item.get("type", "straight_channel"),
                    "diameter_mm": item.get("diameter_mm", 8.0),
                    "distance_from_cavity_mm": item.get("distance_mm", 15.0),
                    "pitch_mm": item.get("pitch_mm", 30.0),
                    "inlet_temp_C": item.get("inlet_temp_C", 20.0),
                    "flow_rate_Lmin": item.get("flow_rate_Lmin", 10.0),
                }
            )

    if not spec["cooling_channels"]:
        # Default straight cooling line
        spec["cooling_channels"].append(
            {
                "source": "default_straight_cooling",
                "type": "straight_channel",
                "diameter_mm": 8.0,
                "inlet_temp_C": 20.0,
                "flow_rate_Lmin": 10.0,
            }
        )

    return spec


def main() -> int:
    parser = argparse.ArgumentParser(description="Hybrid Gate & Cooling System Builder")
    parser.add_argument("--mode", choices=["gui", "cad_import", "hybrid"], default="hybrid")
    parser.add_argument("--json-out", default="", help="Output JSON spec path")
    args = parser.parse_args()

    # Test sample inputs
    sample_gui = {
        "gates": [
            {
                "gate_type": "pin_gate",
                "position_xyz_mm": [50.0, 30.0, 2.0],
                "width_mm": 1.2,
                "height_mm": 1.2,
                "valve_control": {"enabled": True, "open_time_s": 0.4},
            }
        ],
        "cooling_channels": [
            {
                "type": "straight_channel",
                "diameter_mm": 10.0,
                "inlet_temp_C": 25.0,
                "flow_rate_Lmin": 12.0,
            }
        ],
    }

    sample_cad = {
        "part_step": "data/cae_te_workspace/samples/moldflow/pp_plate/pp_plate_100x60x2.step",
        "cooling_step": "data/cae_te_workspace/samples/moldflow/cooling/3d_conformal_channel.step",
    }

    spec = build_gate_cooling_specification(
        mode=args.mode, gui_params=sample_gui, cad_files=sample_cad
    )
    payload = json.dumps(spec, ensure_ascii=False, indent=2)
    print(payload)

    if args.json_out:
        out = Path(args.json_out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(payload, encoding="utf-8")
        print(f"wrote gate & cooling specification -> {out}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
