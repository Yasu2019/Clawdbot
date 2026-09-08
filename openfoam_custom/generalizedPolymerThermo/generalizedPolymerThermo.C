#include "generalizedPolymerThermo.H"
#include "mathematicalConstants.H"
#include "IOstreams.H"
using namespace Foam;
generalizedPolymerThermo::generalizedPolymerThermo(const dictionary& d)
:
 D1_(d.lookupOrDefault<scalar>("D1",1e10)), D2_(d.lookupOrDefault<scalar>("D2_C",105)), D3_(d.lookupOrDefault<scalar>("D3_C_MPa",0)),
 A1_(d.lookupOrDefault<scalar>("A1",17.44)), A2_(d.lookupOrDefault<scalar>("A2_C",51.6)), tauStar_(d.lookupOrDefault<scalar>("tauStar_Pa",5e4)), n_(d.lookupOrDefault<scalar>("n",0.35)),
 A0_(d.lookupOrDefault<scalar>("A0",1.11e-3)), A1p_(d.lookupOrDefault<scalar>("A1p",6e-7)), B0_(d.lookupOrDefault<scalar>("B0",2e8)), B1p_(d.lookupOrDefault<scalar>("B1p",0)), C_(d.lookupOrDefault<scalar>("C",0.0894)), b_(d.lookupOrDefault<scalar>("b",0)), Tref_(d.lookupOrDefault<scalar>("Tref_K",503.15)) {}
scalar generalizedPolymerThermo::crossWLF(const scalar T, const scalar g, const scalar p) const
{
 const scalar Tg=D2_+D3_*p, tc=T-273.15, den=max(A2_+tc-Tg,scalar(1e-6));
 const scalar eta0=min(scalar(1e50),D1_*exp(max(scalar(-50),min(scalar(50),-A1_*(tc-Tg)/den))));
 return max(scalar(1e-4),eta0/(1+pow(eta0*max(g,scalar(1e-12))/max(tauStar_,scalar(1e-9)),1-n_)));
}
scalar generalizedPolymerThermo::taitSpecificVolume(const scalar T,const scalar p) const
{
 const scalar A=A0_+A1p_*(T-Tref_), B=max(B0_+B1p_*(T-Tref_),scalar(1));
 return A*(1-C_*log1p(max(p,scalar(0))*1e6/B))+b_;
}
scalar generalizedPolymerThermo::taitDensity(const scalar T,const scalar p) const
{
 const scalar v=max(taitSpecificVolume(T,p), scalar(1e-9));
 return 1.0/v;
}
scalar generalizedPolymerThermo::taitPsi(const scalar T,const scalar p) const
{
 const scalar dT=T-Tref_;
 const scalar A=A0_+A1p_*dT, B=max(B0_+B1p_*dT,scalar(1));
 const scalar pPa=max(p,scalar(0))*1e6;
 const scalar v=max(taitSpecificVolume(T,p),scalar(1e-9));
 return A*C_*1e6/(B+pPa)/(v*v);
}
scalar generalizedPolymerThermo::coolingTemperature(const scalar t,const scalar rho,const scalar cp,const scalar k,const scalar h,const scalar melt,const scalar wall) const
{
 const scalar tau=rho*cp*sqr(h)/(constant::mathematical::pi*constant::mathematical::pi*k);
 return wall+(melt-wall)*exp(-t/max(tau,scalar(1e-12)));
}
