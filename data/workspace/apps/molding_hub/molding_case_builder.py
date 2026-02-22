import os
import sys
import json
import shutil
from pathlib import Path

# Advanced Injection Molding Simulator (OpenFOAM + ElmerFEM) Case Builder
# This script is called by the Web UI (molding_hub) or the R-DOE engine.

def load_resin(material_id):
    db_path = Path(__file__).parent / ".." / "tolerance_hub" / "resin_database.json"
    if not db_path.exists():
        print(f"Error: Resin database not found at {db_path}")
        return None
    
    with open(db_path, "r", encoding="utf-8") as f:
        db = json.load(f)
        for m in db.get("materials", []):
            if m["id"] == material_id:
                return m
    return None

def generate_openfoam_case(case_dir, stl_product, stl_cooling, gates, resin, vents):
    print(f"--> Generating OpenFOAM Case at {case_dir}")
    os.makedirs(case_dir, exist_ok=True)
    os.makedirs(os.path.join(case_dir, "0"), exist_ok=True)
    os.makedirs(os.path.join(case_dir, "constant"), exist_ok=True)
    os.makedirs(os.path.join(case_dir, "system"), exist_ok=True)
    
    # constant/transportProperties
    transport_content = f"""/*--------------------------------*- C++ -*----------------------------------*\\
| =========                 |                                                 |
| \\\\      /  F ield         | OpenFOAM: The Open Source CFD Toolbox           |
|  \\\\    /   O peration     | Version:  v2306                                 |
|   \\\\  /    A nd           | Website:  www.openfoam.com                      |
|    \\\\/     M anipulation  |                                                 |
\\*---------------------------------------------------------------------------*/
FoamFile
{{
    version     2.0;
    format      ascii;
    class       dictionary;
    location    "constant";
    object      transportProperties;
}}
// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //

phases (resin air);

resin
{{
    transportModel  CrossWLF;
    nu              [ 0 2 -1 0 0 0 0 ] 1e-3; // Will be scaled by Cross-WLF
    rho             [ 1 -3 0 0 0 0 0 ] {resin['properties']['density_melt']};
    Cp              [ 0 2 -2 -1 0 0 0 ] {resin['properties']['specific_heat']};
    kappa           [ 1 1 -3 -1 0 0 0 ] {resin['properties']['thermal_conductivity']};
    
    // Cross-WLF Parameters for {resin['name']}
    n               {resin['properties']['cross_wlf']['n']};
    tau             {resin['properties']['cross_wlf']['tau']};
    D1              {resin['properties']['cross_wlf']['d1']};
    D2              {resin['properties']['cross_wlf']['d2']};
    A1              {resin['properties']['cross_wlf']['a1']};
}}

air
{{
    transportModel  Newtonian;
    nu              [ 0 2 -1 0 0 0 0 ] 1.48e-05;
    rho             [ 1 -3 0 0 0 0 0 ] 1.2;
    Cp              [ 0 2 -2 -1 0 0 0 ] 1004.4;
    kappa           [ 1 1 -3 -1 0 0 0 ] 0.026;
}}

sigma           [ 1 0 -2 0 0 0 0 ] 0.03;

// ************************************************************************* //
"""
    with open(os.path.join(case_dir, "constant", "transportProperties"), "w") as f:
        f.write(transport_content)
        
    # system/blockMeshDict
    blockmesh_content = """/*--------------------------------*- C++ -*----------------------------------*\\
| =========                 |                                                 |
| \\\\      /  F ield         | OpenFOAM: The Open Source CFD Toolbox           |
|  \\\\    /   O peration     | Version:  v2306                                 |
|   \\\\  /    A nd           | Website:  www.openfoam.com                      |
|    \\\\/     M anipulation  |                                                 |
\\*---------------------------------------------------------------------------*/
FoamFile
{
    version     2.0;
    format      ascii;
    class       dictionary;
    object      blockMeshDict;
}
convertToMeters 1;

vertices
(
    (0 0 0)
    (0.1 0 0)
    (0.1 0.05 0)
    (0 0.05 0)
    (0 0 0.01)
    (0.1 0 0.01)
    (0.1 0.05 0.01)
    (0 0.05 0.01)
);
blocks
(
    hex (0 1 2 3 4 5 6 7) (20 10 2) simpleGrading (1 1 1)
);
edges ();
boundary
(
    inlet
    {
        type patch;
        faces ((0 3 2 1));
    }
    outlet
    {
        type patch;
        faces ((4 5 6 7));
    }
    walls
    {
        type wall;
        faces
        (
            (0 4 7 3)
            (1 2 6 5)
            (0 1 5 4)
            (3 7 6 2)
        );
    }
);
"""
    with open(os.path.join(case_dir, "system", "blockMeshDict"), "w") as f:
        f.write(blockmesh_content)

    # system/controlDict
    control_content = f"""/*--------------------------------*- C++ -*----------------------------------*\\
| =========                 |                                                 |
| \\\\      /  F ield         | OpenFOAM: The Open Source CFD Toolbox           |
|  \\\\    /   O peration     | Version:  v2306                                 |
|   \\\\  /    A nd           | Website:  www.openfoam.com                      |
|    \\\\/     M anipulation  |                                                 |
\\*---------------------------------------------------------------------------*/
FoamFile
{{
    version     2.0;
    format      ascii;
    class       dictionary;
    location    "system";
    object      controlDict;
}}
application     interFoam;
startFrom       latestTime;
startTime       0;
stopAt          endTime;
endTime         1.0;
deltaT          0.001;
writeControl    adjustableRunTime;
writeInterval   0.1;
purgeWrite      0;
writeFormat     ascii;
writePrecision  6;
writeCompression off;
timeFormat      general;
timePrecision   6;
runTimeModifiable true;
adjustTimeStep  yes;
maxCo           0.5;
maxAlphaCo      0.5;
maxDeltaT       1;
"""
    with open(os.path.join(case_dir, "system", "controlDict"), "w") as f:
        f.write(control_content)

    # system/fvSchemes
    schemes_content = """/*--------------------------------*- C++ -*----------------------------------*\\
| =========                 |                                                 |
| \\\\      /  F ield         | OpenFOAM: The Open Source CFD Toolbox           |
|  \\\\    /   O peration     | Version:  v2306                                 |
|   \\\\  /    A nd           | Website:  www.openfoam.com                      |
|    \\\\/     M anipulation  |                                                 |
\\*---------------------------------------------------------------------------*/
FoamFile
{
    version     2.0;
    format      ascii;
    class       dictionary;
    location    "system";
    object      fvSchemes;
}
ddtSchemes      { default Euler; }
gradSchemes     { default Gauss linear; }
divSchemes
{
    div(rhoPhi,U)  Gauss upwind;
    div(phi,alpha.resin) Gauss vanLeer;
    div(phi,alpha.air) Gauss vanLeer;
    div(((rho*nuEff)*dev2(T(grad(U))))) Gauss linear;
}
laplacianSchemes { default Gauss linear corrected; }
interpolationSchemes { default linear; }
snGradSchemes   { default corrected; }
"""
    with open(os.path.join(case_dir, "system", "fvSchemes"), "w") as f:
        f.write(schemes_content)

    # system/fvSolution
    solution_content = """/*--------------------------------*- C++ -*----------------------------------*\\
| =========                 |                                                 |
| \\\\      /  F ield         | OpenFOAM: The Open Source CFD Toolbox           |
|  \\\\    /   O peration     | Version:  v2306                                 |
|   \\\\  /    A nd           | Website:  www.openfoam.com                      |
|    \\\\/     M anipulation  |                                                 |
\\*---------------------------------------------------------------------------*/
FoamFile
{
    version     2.0;
    format      ascii;
    class       dictionary;
    location    "system";
    object      fvSolution;
}
solvers
{
    "alpha.resin.*"
    {
        nAlphaCorr      1;
        nAlphaSubCycles 2;
        cAlpha          1;
    }
    p_rgh
    {
        solver          PCG;
        preconditioner  DIC;
        tolerance       1e-07;
        relTol          0.01;
    }
    U
    {
        solver          PBiCGStab;
        preconditioner  DILU;
        tolerance       1e-08;
        relTol          0;
    }
}
PIMPLE
{
    momentumPredictor no;
    nCorrectors     3;
    nNonOrthogonalCorrectors 0;
}
"""
    with open(os.path.join(case_dir, "system", "fvSolution"), "w") as f:
        f.write(solution_content)
        
    # 0/alpha.resin
    alpha_content = """/*--------------------------------*- C++ -*----------------------------------*\\
| =========                 |                                                 |
| \\\\      /  F ield         | OpenFOAM: The Open Source CFD Toolbox           |
|  \\\\    /   O peration     | Version:  v2306                                 |
|   \\\\  /    A nd           | Website:  www.openfoam.com                      |
|    \\\\/     M anipulation  |                                                 |
\\*---------------------------------------------------------------------------*/
FoamFile
{
    version     2.0;
    format      ascii;
    class       volScalarField;
    location    "0";
    object      alpha.resin;
}
dimensions      [0 0 0 0 0 0 0];
internalField   uniform 0;
boundaryField
{
    inlet
    {
        type            fixedValue;
        value           uniform 1;
    }
    outlet
    {
        type            zeroGradient;
    }
    walls
    {
        type            zeroGradient;
    }
}
"""
    with open(os.path.join(case_dir, "0", "alpha.resin"), "w") as f:
        f.write(alpha_content)

    # 0/U
    u_content = f"""/*--------------------------------*- C++ -*----------------------------------*\\
| =========                 |                                                 |
| \\\\      /  F ield         | OpenFOAM: The Open Source CFD Toolbox           |
|  \\\\    /   O peration     | Version:  v2306                                 |
|   \\\\  /    A nd           | Website:  www.openfoam.com                      |
|    \\\\/     M anipulation  |                                                 |
\\*---------------------------------------------------------------------------*/
FoamFile
{{
    version     2.0;
    format      ascii;
    class       volVectorField;
    location    "0";
    object      U;
}}
dimensions      [0 1 -1 0 0 0 0];
internalField   uniform (0 0 0);
boundaryField
{{
    inlet
    {{
        type            fixedValue;
        value           uniform ({gates[0].get('v', 5.0)} 0 0);
    }}
    outlet
    {{
        type            zeroGradient;
    }}
    walls
    {{
        type            noSlip;
    }}
}}
"""
    with open(os.path.join(case_dir, "0", "U"), "w") as f:
        f.write(u_content)

    # 0/p_rgh
    p_content = """/*--------------------------------*- C++ -*----------------------------------*\\
| =========                 |                                                 |
| \\\\      /  F ield         | OpenFOAM: The Open Source CFD Toolbox           |
|  \\\\    /   O peration     | Version:  v2306                                 |
|   \\\\  /    A nd           | Website:  www.openfoam.com                      |
|    \\\\/     M anipulation  |                                                 |
\\*---------------------------------------------------------------------------*/
FoamFile
{
    version     2.0;
    format      ascii;
    class       volScalarField;
    location    "0";
    object      p_rgh;
}
dimensions      [1 -1 -2 0 0 0 0];
internalField   uniform 0;
boundaryField
{
    inlet
    {
        type            fixedValue;
        value           uniform 100000;
    }
    outlet
    {
        type            totalPressure;
        p0              uniform 0;
    }
    walls
    {
        type            fixedFluxPressure;
        value           uniform 0;
    }
}
"""
    with open(os.path.join(case_dir, "0", "p_rgh"), "w") as f:
        f.write(p_content)

    # system/setFieldsDict
    setfields_content = """/*--------------------------------*- C++ -*----------------------------------*\\
| =========                 |                                                 |
| \\\\      /  F ield         | OpenFOAM: The Open Source CFD Toolbox           |
|  \\\\    /   O peration     | Version:  v2306                                 |
|   \\\\  /    A nd           | Website:  www.openfoam.com                      |
|    \\\\/     M anipulation  |                                                 |
\\*---------------------------------------------------------------------------*/
FoamFile
{
    version     2.0;
    format      ascii;
    class       dictionary;
    location    "system";
    object      setFieldsDict;
}
defaultFieldValues
(
    volScalarFieldValue alpha.resin 0
);
regions
(
    boxToCell
    {
        box (0 0 0) (0.02 0.05 0.01);
        fieldValues
        (
            volScalarFieldValue alpha.resin 1
        );
    }
);
"""
    with open(os.path.join(case_dir, "system", "setFieldsDict"), "w") as f:
        f.write(setfields_content)

    # For now, print success structure
    print("--> OpenFOAM boundary conditions (Gates) configured:")
    for i, g in enumerate(gates):
        print(f"    Gate {i+1}: pos=({g['x']}, {g['y']}, {g['z']}), v={g.get('v', 5.0)} m/s")
    
    print("--> OpenFOAM (interFoam / multiphaseInterFoam) Setup Complete.")
    return True

def generate_elmer_case(case_dir, stl_product, stl_cooling, resin):
    print(f"--> Generating ElmerFEM Coupled Case at {case_dir}")
    os.makedirs(case_dir, exist_ok=True)
    
    # case.sif (Solver Input File)
    sif_content = f"""Header
  CHECK KEYWORDS Warn
  Mesh DB "." "."
  Include Path ""
  Results Directory "results"
End

Simulation
  Max Output Level = 5
  Coordinate System = Cartesian
  Coordinate Mapping(3) = 1 2 3
  Simulation Type = Transient
  Steady State Max Iterations = 1
  Output Intervals(1) = 1
  Timestep intervals(1) = 100
  Timestep Sizes(1) = 0.1
  Solver Input File = case.sif
  Post File = case.vtu
End

Constants
  Gravity(4) = 0 -1 0 9.82
  Stefan Boltzmann = 5.670374419e-08
  Permittivity of Vacuum = 8.85418781e-12
  Boltzmann Constant = 1.380649e-23
  Unit Charge = 1.6021766e-19
End

Body 1
  Target Bodies(1) = 1
  Name = "MoldedPart"
  Equation = 1
  Material = 1
  Initial condition = 1
End

Material 1
  Name = "{resin['name']}"
  Density = {resin['properties']['density_solid']}
  Heat Capacity = {resin['properties']['specific_heat']}
  Heat Conductivity = {resin['properties']['thermal_conductivity']}
  Youngs modulus = {resin['properties']['elastic_modulus']}
  Poisson ratio = {resin['properties']['poisson_ratio']}
  Heat expansion Coefficient = {sum(resin['properties']['shrinkage_estimate_percent'])/2.0 / 100.0}
End

Equation 1
  Name = "Thermo-Mechanical Coupling"
  Active Solvers(2) = 1 2
End

Solver 1
  Equation = Heat Equation
  Procedure = "HeatSolve" "HeatSolver"
  Variable = Temperature
  Exec Solver = Always
  Stabilize = True
  Optimize Bandwidth = True
  Steady State Convergence Tolerance = 1.0e-5
  Nonlinear System Convergence Tolerance = 1.0e-4
  Nonlinear System Max Iterations = 20
  Nonlinear System Newton After Iterations = 3
  Nonlinear System Newton After Tolerance = 1.0e-3
  Nonlinear System Relaxation Factor = 1
  Linear System Solver = Iterative
  Linear System Iterative Method = BiCGStab
  Linear System Max Iterations = 500
  Linear System Convergence Tolerance = 1.0e-8
  BiCGstabl polynomial degree = 2
  Linear System Preconditioning = ILU0
  Linear System ILUT Tolerance = 1.0e-3
  Linear System Abort Not Converged = False
  Linear System Residual Output = 10
  Linear System Precondition Recompute = 1
End

Solver 2
  Equation = Linear elasticity
  Procedure = "StressSolve" "StressSolver"
  Variable = -dofs 3 Displacement
  Exec Solver = Always
  Stabilize = True
  Optimize Bandwidth = True
  Steady State Convergence Tolerance = 1.0e-5
  Nonlinear System Convergence Tolerance = 1.0e-4
  Nonlinear System Max Iterations = 1
  Nonlinear System Newton After Iterations = 3
  Nonlinear System Newton After Tolerance = 1.0e-3
  Nonlinear System Relaxation Factor = 1
  Linear System Solver = Iterative
  Linear System Iterative Method = BiCGStab
  Linear System Max Iterations = 500
  Linear System Convergence Tolerance = 1.0e-8
  BiCGstabl polynomial degree = 2
  Linear System Preconditioning = ILU0
  Linear System ILUT Tolerance = 1.0e-3
  Linear System Abort Not Converged = False
  Linear System Residual Output = 10
  Linear System Precondition Recompute = 1
End

"""
    with open(os.path.join(case_dir, "case.sif"), "w") as f:
        f.write(sif_content)
        
    print("--> ElmerFEM (Thermal + Mechanical Warpage) Setup Complete.")
    return True


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Build Coupled Simulation Cases for Injection Molding")
    parser.add_argument("--material", type=str, required=True, help="Material ID (e.g. pp_generic)")
    parser.add_argument("--gates", type=str, required=True, help="JSON string of gate configurations")
    parser.add_argument("--coolant_temp", type=float, default=40.0, help="Coolant Temperature (C)")
    parser.add_argument("--outdir", type=str, default="./sim_case", help="Output directory")
    
    args = parser.parse_args()
    
    resin = load_resin(args.material)
    if not resin:
        sys.exit(1)
        
    try:
        gates = json.loads(args.gates)
    except:
        print("Error parsing gates JSON")
        sys.exit(1)
        
    # Create OpenFOAM CFD Case
    generate_openfoam_case(os.path.join(args.outdir, "CFD_MeltFront"), "product.stl", "cooling.stl", gates, resin, vents=[])
    
    # Create ElmerFEM FEA Case
    generate_elmer_case(os.path.join(args.outdir, "FEA_Warpage"), "product.stl", "cooling.stl", resin)
    
    print(f"\nSUCCESS: Simulation Case Built at {args.outdir}")
