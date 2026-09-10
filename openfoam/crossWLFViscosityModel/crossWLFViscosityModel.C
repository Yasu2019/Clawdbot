#include "crossWLFViscosityModel.H"
#include "volFields.H"
#include "addToRunTimeSelectionTable.H"
#include "mathematicalConstants.H"

namespace Foam
{
namespace laminarModels
{
namespace generalizedNewtonianViscosityModels
{
defineTypeNameAndDebug(crossWLFViscosityModel, 0);
addToRunTimeSelectionTable
(
    generalizedNewtonianViscosityModel,
    crossWLFViscosityModel,
    dictionary
);

crossWLFViscosityModel::crossWLFViscosityModel(const dictionary& dict)
:
    generalizedNewtonianViscosityModel(dict),
    n_(dict.get<scalar>("n")),
    tauStar_(dict.get<scalar>("tauStar")),
    D1_(dict.get<scalar>("D1")),
    D2_(dict.get<scalar>("D2")),
    D3_(dict.get<scalar>("D3")),
    A1_(dict.get<scalar>("A1")),
    A2_(dict.get<scalar>("A2")),
    rhoFloor_(dict.getOrDefault<scalar>("rhoFloor", 1e-9))
{}

bool crossWLFViscosityModel::read(const dictionary& dict)
{
    generalizedNewtonianViscosityModel::read(dict);
    n_ = dict.get<scalar>("n"); tauStar_ = dict.get<scalar>("tauStar");
    D1_ = dict.get<scalar>("D1"); D2_ = dict.get<scalar>("D2");
    D3_ = dict.get<scalar>("D3"); A1_ = dict.get<scalar>("A1");
    A2_ = dict.get<scalar>("A2");
    rhoFloor_ = dict.getOrDefault<scalar>("rhoFloor", rhoFloor_);
    return true;
}

tmp<volScalarField> crossWLFViscosityModel::nu
(
    const volScalarField& nu0,
    const volScalarField& strainRate
) const
{
    const fvMesh& mesh = nu0.mesh();
    const volScalarField& T = mesh.lookupObject<volScalarField>("T");
    const volScalarField& rho = mesh.lookupObject<volScalarField>("rho");
    const volScalarField* pPtr = mesh.cfindObject<volScalarField>("p");
    if (!pPtr) pPtr = &mesh.lookupObject<volScalarField>("p_rgh");

    tmp<volScalarField> resultPtr
    (
        new volScalarField
        (
            IOobject
            (
                IOobject::groupName("crossWLF:nu", nu0.group()),
                nu0.time().timeName(),
                mesh,
                IOobject::NO_READ,
                IOobject::AUTO_WRITE
            ),
            nu0
        )
    );
    volScalarField& result = resultPtr.ref();

    forAll(result, celli)
    {
        const scalar den = A2_ + T[celli] - D2_;
        const scalar safeDen = (mag(den) < SMALL ? (den < 0 ? -SMALL : SMALL) : den);
        const scalar exponent = -A1_*(T[celli] - D2_ - D3_*(*pPtr)[celli])/safeDen;
        const scalar eta0 = D1_*exp(max(scalar(-700), min(scalar(700), exponent)));
        const scalar shear = max(strainRate[celli], scalar(1e-12));
        const scalar eta = eta0/(1 + pow(eta0*shear/max(tauStar_, scalar(SMALL)), 1 - n_));
        result[celli] = eta/max(rho[celli], rhoFloor_);
    }
    return resultPtr;
}

}
}
}
