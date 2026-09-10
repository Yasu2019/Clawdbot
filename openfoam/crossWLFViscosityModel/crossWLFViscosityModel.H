#ifndef crossWLFViscosityModel_H
#define crossWLFViscosityModel_H

#include "generalizedNewtonianViscosityModel.H"
#include "dimensionedScalar.H"

namespace Foam
{
namespace laminarModels
{
namespace generalizedNewtonianViscosityModels
{

class crossWLFViscosityModel : public generalizedNewtonianViscosityModel
{
    scalar n_, tauStar_, D1_, D2_, D3_, A1_, A2_;
    scalar rhoFloor_;

public:
    TypeName("crossWLFViscosityModel");
    explicit crossWLFViscosityModel(const dictionary& dict);
    virtual ~crossWLFViscosityModel() = default;
    virtual bool read(const dictionary& dict);
    virtual tmp<volScalarField> nu
    (
        const volScalarField& nu0,
        const volScalarField& strainRate
    ) const;
};

}
}
}

#endif
