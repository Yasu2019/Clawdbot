/*---------------------------------------------------------------------------*\
  =========                 |
  \\      /  F ield         | OpenFOAM: The Open Source CFD Toolbox
   \\    /   O peration     |
    \\  /    A nd           | www.openfoam.com
     \\/     M anipulation  |
-------------------------------------------------------------------------------
    Copyright (C) 2011-2017 OpenFOAM Foundation
    Copyright (C) OpenCFD OpenCFD Ltd.
-------------------------------------------------------------------------------
License
    This file is part of OpenFOAM.

    OpenFOAM is free software: you can redistribute it and/or modify it
    under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    OpenFOAM is distributed in the hope that it will be useful, but WITHOUT
    ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
    FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License
    for more details.

    You should have received a copy of the GNU General Public License
    along with OpenFOAM.  If not, see <http://www.gnu.org/licenses/>.

Application
    compressibleInterFoam

Group
    grpMultiphaseSolvers

Description
    Solver for two compressible, non-isothermal immiscible fluids using a VOF
    (volume of fluid) phase-fraction based interface capturing approach.

    The momentum and other fluid properties are of the "mixture" and a single
    momentum equation is solved.

    Either mixture or two-phase transport modelling may be selected.  In the
    mixture approach a single laminar, RAS or LES model is selected to model the
    momentum stress.  In the Euler-Euler two-phase approach separate laminar,
    RAS or LES selected models are selected for each of the phases.

\*---------------------------------------------------------------------------*/

#include "fvCFD.H"
#include "CMULES.H"
#include "EulerDdtScheme.H"
#include "localEulerDdtScheme.H"
#include "CrankNicolsonDdtScheme.H"
#include "subCycle.H"
#include "compressibleInterPhaseTransportModel.H"
#include "pimpleControl.H"
#include "fvOptions.H"
#include "fvcSmooth.H"
#include "generalizedPolymerThermo.H"

// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //

int main(int argc, char *argv[])
{
    argList::addNote
    (
        "Solver for two compressible, non-isothermal immiscible fluids"
        " using VOF phase-fraction based interface capturing."
    );

    #include "postProcess.H"

    #include "addCheckCaseOptions.H"
    #include "setRootCaseLists.H"
    #include "createTime.H"
    #include "createMesh.H"
    #include "createControl.H"
    #include "createTimeControls.H"
    #include "createFields.H"

    IOdictionary polymerThermoDict
    (
        IOobject("generalizedPolymerThermo", runTime.constant(), mesh,
            IOobject::MUST_READ, IOobject::NO_WRITE)
    );
    generalizedPolymerThermo polymerThermo(polymerThermoDict);
    volScalarField etaCrossWLF
    (
        IOobject("etaCrossWLF", runTime.timeName(), mesh, IOobject::NO_READ, IOobject::AUTO_WRITE),
        mesh, dimensionedScalar("zero", dimDynamicViscosity, 1e-3)
    );
    const Switch coupleCrossWLF
    (
        polymerThermoDict.lookupOrDefault<Switch>("coupleCrossWLF", false)
    );
    if (!coupleCrossWLF)
    {
        etaCrossWLF = dimensionedScalar("zero", dimDynamicViscosity, 0.0);
    }

    volScalarField& p = mixture.p();
    volScalarField& T = mixture.T();
    const volScalarField& rhoAir = mixture.thermo2().rho();
    const volScalarField& psi2 = mixture.thermo2().psi();
    volScalarField rhoPolymer
    (
        IOobject("rhoPolymer", runTime.timeName(), mesh, IOobject::NO_READ, IOobject::NO_WRITE),
        mixture.thermo1().rho()
    );
    volScalarField psiPolymer
    (
        IOobject("psiPolymer", runTime.timeName(), mesh, IOobject::NO_READ, IOobject::NO_WRITE),
        mesh, dimensionedScalar("zero", dimDensity/dimPressure, 0.0)
    );

    if (!LTS)
    {
        #include "readTimeControls.H"
        #include "CourantNo.H"
        #include "setInitialDeltaT.H"
    }

    // * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //

    Info<< "\nStarting time loop\n" << endl;

    while (runTime.run())
    {
        #include "readTimeControls.H"

        if (LTS)
        {
            #include "setRDeltaT.H"
        }
        else
        {
            #include "CourantNo.H"
            #include "alphaCourantNo.H"
            #include "setDeltaT.H"
        }

        ++runTime;

        tmp<volTensorField> tGradU = fvc::grad(U);
        const volTensorField& gradU = tGradU();
        forAll(etaCrossWLF, celli)
        {
            etaCrossWLF[celli] = polymerThermo.crossWLF
            (
                T[celli], mag(gradU[celli]), p[celli]/1e6
            );
            const scalar polymerRho = polymerThermo.taitDensity(T[celli], p[celli]/1e6);
            const scalar polymerPsi = polymerThermo.taitPsi(T[celli], p[celli]/1e6);
            rhoPolymer[celli] = min(max(polymerRho, scalar(100.0)), scalar(2000.0));
            psiPolymer[celli] = max(polymerPsi, scalar(1e-12));
            const scalar rhoTait = min(max
            (
                mixture.alpha1()[celli]*polymerRho
              + mixture.alpha2()[celli]*rhoAir[celli],
                scalar(0.1)
            ), scalar(2000.0));
            // Under-relax the EOS update to prevent an initial pressure-matrix
            // singularity while retaining the Tait density contribution.
            rho[celli] = 0.8*rho[celli] + 0.2*rhoTait;
        }
        etaCrossWLF.correctBoundaryConditions();

        Info<< "Time = " << runTime.timeName() << nl << endl;

        // --- Pressure-velocity PIMPLE corrector loop
        while (pimple.loop())
        {
            #include "alphaControls.H"
            #include "compressibleAlphaEqnSubCycle.H"

            turbulence.correctPhasePhi();

            #include "UEqn.H"
            volScalarField divUp("divUp", fvc::div(fvc::absolute(phi, U), p));
            #include "TEqn.H"

            // --- Pressure corrector loop
            while (pimple.correct())
            {
                #include "pEqn.H"
            }

            if (pimple.turbCorr())
            {
                turbulence.correct();
            }
        }

        runTime.write();

        runTime.printExecutionTime(Info);
    }

    Info<< "End\n" << endl;

    return 0;
}


// ************************************************************************* //
