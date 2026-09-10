#!/usr/bin/env python3
"""Build an OpenFOAM compressible resin/air VOF case with vent boundaries."""
from __future__ import annotations
import argparse, json, shutil
from pathlib import Path

def write(p: Path, s: str):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(s, encoding="utf-8")

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--template", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--end-time", type=float, default=0.5)
    ap.add_argument("--injection-speed", type=float, default=0.005)
    a = ap.parse_args()
    src, out = a.template.resolve(), a.out.resolve()
    out.mkdir(parents=True, exist_ok=True)
    for name in ("constant/polyMesh", "system"):
        shutil.copytree(src / name, out / name, dirs_exist_ok=True)
    for name in ("thermophysicalProperties.air", "thermophysicalProperties.polymer", "transportProperties"):
        shutil.copy2(src / "constant" / name, out / "constant" / name)
    shutil.copy2(src / "constant" / "g", out / "constant" / "g")
    for name in ("turbulenceProperties", "momentumTransport"):
        if (src / "constant" / name).exists():
            shutil.copy2(src / "constant" / name, out / "constant" / name)
    # OpenCFD 2512 initialises the base psiThermo before the phase-specific
    # thermo objects and therefore also expects this compatibility dictionary.
    base_thermo = (src / "constant" / "thermophysicalProperties.polymer").read_text(encoding="utf-8")
    write(out / "constant" / "thermophysicalProperties", "FoamFile { version 2.0; format ascii; class dictionary; object thermophysicalProperties; }\nphases (polymer air);\nsigma 0.04;\npMin 1000;\n" + base_thermo)
    write(out / "system/controlDict", f"""FoamFile {{ version 2.0; format ascii; class dictionary; object controlDict; }}
application compressibleInterFoam;
startFrom startTime; startTime 0; stopAt endTime; endTime {a.end_time:g};
deltaT 1e-7; adjustTimeStep yes; maxCo 0.02; maxAlphaCo 0.01; maxDeltaT 1e-5;
writeControl adjustableRunTime; writeInterval 0.01; writeFormat ascii; writePrecision 8;
runTimeModifiable false;
""")
    write(out / "0/alpha.polymer", """FoamFile { version 2.0; format ascii; class volScalarField; object alpha.polymer; }
dimensions [0 0 0 0 0 0 0];
internalField uniform 0;
boundaryField
{
    gate { type fixedValue; value uniform 1; }
    vent { type inletOutlet; inletValue uniform 0; value uniform 0; }
    cavity_wall { type zeroGradient; }
}
""")
    write(out / "0/U", """FoamFile { version 2.0; format ascii; class volVectorField; object U; }
dimensions [0 1 -1 0 0 0 0];
internalField uniform (0 0 0);
boundaryField
{
    gate { type fixedValue; value uniform ({a.injection_speed:g} 0 0); }
    vent { type pressureInletOutletVelocity; value uniform (0 0 0); }
    cavity_wall { type noSlip; }
}
""".replace("{a.injection_speed:g}", f"{a.injection_speed:g}"))
    write(out / "0/p_rgh", """FoamFile { version 2.0; format ascii; class volScalarField; object p_rgh; }
dimensions [1 -1 -2 0 0 0 0];
internalField uniform 101325;
boundaryField
{
    gate { type fixedFluxPressure; value uniform 101325; }
    vent { type totalPressure; p0 uniform 101325; value uniform 101325; }
    cavity_wall { type fixedFluxPressure; value uniform 101325; }
}
""")
    write(out / "0/p", """FoamFile { version 2.0; format ascii; class volScalarField; object p; }
dimensions [1 -1 -2 0 0 0 0];
internalField uniform 101325;
boundaryField
{
    gate { type fixedFluxPressure; value uniform 101325; }
    vent { type totalPressure; p0 uniform 101325; value uniform 101325; }
    cavity_wall { type fixedFluxPressure; value uniform 101325; }
}
""")
    write(out / "0/T", """FoamFile { version 2.0; format ascii; class volScalarField; object T; }
dimensions [0 0 0 1 0 0 0];
internalField uniform 508;
boundaryField
{
    gate { type fixedValue; value uniform 508; }
    vent { type inletOutlet; inletValue uniform 298; value uniform 298; }
    cavity_wall { type fixedValue; value uniform 313; }
}
""")
    write(out / "constant/taitPolymerProperties", """FoamFile { version 2.0; format ascii; class dictionary; object taitPolymerProperties; }
// Virtual screening coefficients; replace with measured PVT before production use.
rhoRef 900; Tref 508; C 0.0894; B 2.0e8; b0 1.0e-9; b1 0;
model twoDomainTait;
couplingStatus THERMO_LIBRARY_HOOK_REQUIRED;
""")
    (out / "CASE_STATUS.json").write_text(json.dumps({
        "status": "CASE_BUILT_NOT_RUN", "solver": "compressibleInterFoam",
        "compressible_phase": "air_perfectGas", "polymer_tait": "explicit_parameters_hook_required",
        "vent_boundary": "pressureInletOutletVelocity + totalPressure", "template": str(src)
    }, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"out": str(out), "status": "CASE_BUILT_NOT_RUN", "solver": "compressibleInterFoam"}, indent=2))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
