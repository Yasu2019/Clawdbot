#!/usr/bin/env python3
"""Create VOF interFoam 3D cavity case on satellite node."""
import os, pathlib

BASE = pathlib.Path("/e/clawstack_satellite/data/work/vof_cavity_R1")

FILES = {}

FILES["system/blockMeshDict"] = """FoamFile
{
    version     2.0; format ascii; class dictionary; object blockMeshDict;
}
convertToMeters 0.001;
vertices ( (0 0 0) (20 0 0) (20 10 0) (0 10 0) (0 0 2) (20 0 2) (20 10 2) (0 10 2) );
blocks ( hex (0 1 2 3 4 5 6 7) (40 20 4) simpleGrading (1 1 1) );
edges ();
boundary (
  inlet  { type patch; faces ((0 3 7 4)); }
  outlet { type patch; faces ((1 2 6 5)); }
  walls  { type wall; faces ( (0 1 5 4) (3 7 6 2) (4 5 6 7) (0 1 2 3) ); }
);
mergePatchPairs ();
"""

FILES["system/controlDict"] = """FoamFile
{
    version 2.0; format ascii; class dictionary; object controlDict;
}
application interFoam;
startFrom startTime; startTime 0; stopAt endTime; endTime 0.5;
deltaT 1e-4;
writeControl adjustableRunTime; writeInterval 0.02;
purgeWrite 0; writeFormat ascii; writePrecision 8; writeCompression off;
timeFormat general; timePrecision 8; runTimeModifiable yes;
adjustTimeStep yes; maxCo 0.5; maxAlphaCo 0.5; maxDeltaT 1e-3;
"""

FILES["system/fvSchemes"] = """FoamFile
{
    version 2.0; format ascii; class dictionary; object fvSchemes;
}
ddtSchemes      { default Euler; }
gradSchemes     { default Gauss linear; }
divSchemes
{
    default             none;
    div(rhoPhi,U)       Gauss linearUpwind grad(U);
    div(phi,alpha)      Gauss vanLeer;
    div(phirb,alpha)    Gauss interfaceCompression;
    div(((rho*nuEff)*dev2(T(grad(U))))) Gauss linear;
}
laplacianSchemes { default Gauss linear corrected; }
interpolationSchemes { default linear; }
snGradSchemes   { default corrected; }
fluxRequired    { default no; p_rgh; pcorr; alpha.water; }
"""

FILES["system/fvSolution"] = """FoamFile
{
    version 2.0; format ascii; class dictionary; object fvSolution;
}
solvers
{
    "alpha.water.*"
    {
        nAlphaCorr      2;
        nAlphaSubCycles 1;
        cAlpha          1;
        MULESCorr       yes;
        nLimiterIter    3;
        solver          smoothSolver;
        smoother        symGaussSeidel;
        tolerance       1e-8;
        relTol          0;
        minIter         1;
    }
    pcorr
    {
        solver          PCG;
        preconditioner  DIC;
        tolerance       1e-5;
        relTol          0;
    }
    pcorrFinal { solver PCG; preconditioner DIC; tolerance 1e-5; relTol 0; }
    p_rgh
    {
        solver          PCG;
        preconditioner  DIC;
        tolerance       1e-7;
        relTol          0.05;
    }
    p_rghFinal { solver PCG; preconditioner DIC; tolerance 1e-7; relTol 0; }
    U
    {
        solver          smoothSolver;
        smoother        symGaussSeidel;
        tolerance       1e-6;
        relTol          0;
    }
    UFinal { solver smoothSolver; smoother symGaussSeidel; tolerance 1e-6; relTol 0; }
}
PIMPLE { momentumPredictor yes; nOuterCorrectors 1; nCorrectors 3; nNonOrthogonalCorrectors 0; }
relaxationFactors { fields { p_rgh 0.7; } equations { U 0.7; } }
"""

FILES["constant/transportProperties"] = """FoamFile
{
    version 2.0; format ascii; class dictionary; object transportProperties;
}
phases (water air);
water { transportModel Newtonian; nu 1e-06; rho 1000; }
air   { transportModel Newtonian; nu 1.5e-05; rho 1.2; }
sigma 0.072;
"""

FILES["constant/turbulenceProperties"] = """FoamFile
{
    version 2.0; format ascii; class dictionary; object turbulenceProperties;
}
simulationType laminar;
"""

FILES["constant/g"] = """FoamFile
{
    version 2.0; format ascii; class uniformDimensionedVectorField; object g;
}
dimensions [0 1 -2 0 0 0 0];
value (0 -9.81 0);
"""

FILES["0/alpha.water"] = """FoamFile
{
    version 2.0; format ascii; class volScalarField; object alpha.water;
}
dimensions [0 0 0 0 0 0 0];
internalField uniform 0;
boundaryField
{
    inlet  { type fixedValue; value uniform 1; }
    outlet { type inletOutlet; inletValue uniform 0; value uniform 0; }
    walls  { type zeroGradient; }
}
"""

FILES["0/U"] = """FoamFile
{
    version 2.0; format ascii; class volVectorField; object U;
}
dimensions [0 1 -1 0 0 0 0];
internalField uniform (0 0 0);
boundaryField
{
    inlet  { type fixedValue; value uniform (0.1 0 0); }
    outlet { type pressureInletOutletVelocity; value uniform (0 0 0); }
    walls  { type noSlip; }
}
"""

FILES["0/p_rgh"] = """FoamFile
{
    version 2.0; format ascii; class volScalarField; object p_rgh;
}
dimensions [1 -1 -2 0 0 0 0];
internalField uniform 0;
boundaryField
{
    inlet  { type fixedFluxPressure; value uniform 0; }
    outlet { type totalPressure; p0 uniform 0; }
    walls  { type fixedFluxPressure; value uniform 0; }
}
"""

FILES["0/p"] = """FoamFile
{
    version 2.0; format ascii; class volScalarField; object p;
}
dimensions [1 -1 -2 0 0 0 0];
internalField uniform 0;
boundaryField
{
    inlet  { type calculated; value uniform 0; }
    outlet { type calculated; value uniform 0; }
    walls  { type calculated; value uniform 0; }
}
"""

for rel, content in FILES.items():
    p = BASE / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")
    print(f"  wrote {p}")

print("VOF case setup complete:", BASE)
