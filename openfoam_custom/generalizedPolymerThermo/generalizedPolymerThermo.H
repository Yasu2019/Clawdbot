#ifndef generalizedPolymerThermo_H
#define generalizedPolymerThermo_H
#include "dictionary.H"
#include "scalar.H"
namespace Foam
{
class generalizedPolymerThermo
{
    scalar D1_, D2_, D3_, A1_, A2_, tauStar_, n_;
    scalar A0_, A1p_, B0_, B1p_, C_, b_, Tref_;
public:
    explicit generalizedPolymerThermo(const dictionary& dict);
    scalar crossWLF(const scalar T, const scalar shearRate, const scalar pressureMPa) const;
    scalar taitSpecificVolume(const scalar T, const scalar pressureMPa) const;
    scalar taitDensity(const scalar T, const scalar pressureMPa) const;
    scalar taitPsi(const scalar T, const scalar pressureMPa) const;
    scalar coolingTemperature(const scalar time, const scalar rho, const scalar cp, const scalar k, const scalar wallThickness, const scalar meltT, const scalar wallT) const;
};
}
#endif
