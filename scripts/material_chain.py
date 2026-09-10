"""Constitutive chain for virtual polymer molding screening.

The functions are deliberately independent of OpenFOAM so they can be used as
an oracle when checking a compiled thermo/transport plug-in.  Units are SI.
They implement a two-domain Tait-style PVT law, pressure-aware Cross-WLF
viscosity, monotone PVT-table interpolation, and thermo-mechanical shrinkage.
All inputs remain replaceable by measured material data.
"""
from __future__ import annotations

from dataclasses import dataclass
import bisect
import math


@dataclass(frozen=True)
class TaitTwoDomain:
    rho_ref: float
    t_ref: float
    alpha_melt: float
    alpha_solid: float
    transition_k: float
    width_k: float
    B_melt: float
    B_solid: float
    C: float = 0.0894
    p_ref: float = 101325.0

    def _blend(self, temperature_k: float) -> float:
        return 0.5 * (1.0 + math.tanh((temperature_k - self.transition_k) / max(self.width_k, 1e-9)))

    def density(self, pressure_pa: float, temperature_k: float) -> float:
        """Two-domain Tait density with continuous melt/solid transition."""
        p = max(0.0, float(pressure_pa))
        w = self._blend(temperature_k)
        alpha = w * self.alpha_melt + (1.0 - w) * self.alpha_solid
        B = w * self.B_melt + (1.0 - w) * self.B_solid
        v_thermal = (1.0 + alpha * (temperature_k - self.t_ref)) / self.rho_ref
        v_pressure = 1.0 - self.C * math.log((B + p) / (B + self.p_ref))
        if v_thermal <= 0.0 or v_pressure <= 0.0:
            raise ValueError("Tait specific volume became non-positive")
        return 1.0 / (v_thermal * v_pressure)

    def compressibility_pa_inv(self, pressure_pa: float, temperature_k: float) -> float:
        """Isothermal compressibility -1/rho * d rho/dp."""
        p = max(0.0, float(pressure_pa))
        w = self._blend(temperature_k)
        B = w * self.B_melt + (1.0 - w) * self.B_solid
        v_pressure = 1.0 - self.C * math.log((B + p) / (B + self.p_ref))
        return self.C / ((B + p) * v_pressure)

    def density_derivatives(self, pressure_pa: float, temperature_k: float) -> tuple[float, float]:
        """Return (dρ/dp, dρ/dT) for a consistent Newton update."""
        rho = self.density(pressure_pa, temperature_k)
        kappa = self.compressibility_pa_inv(pressure_pa, temperature_k)
        # The thermal derivative includes the smooth melt/solid blend.  A
        # centered derivative keeps the implementation consistent at the
        # transition and is suitable for a tabulated/custom EOS oracle.
        h = 1.0e-3
        rp = self.density(pressure_pa, temperature_k + h)
        rm = self.density(pressure_pa, temperature_k - h)
        return rho * kappa, (rp - rm) / (2.0 * h)

    def sound_speed_m_s(self, pressure_pa: float, temperature_k: float, *, bulk_modulus_pa: float | None = None) -> float:
        """Screening acoustic speed from isothermal or supplied bulk modulus."""
        rho = self.density(pressure_pa, temperature_k)
        bulk = bulk_modulus_pa if bulk_modulus_pa is not None else 1.0 / self.compressibility_pa_inv(pressure_pa, temperature_k)
        if bulk <= 0.0:
            raise ValueError("bulk modulus must be positive")
        return math.sqrt(bulk / rho)


@dataclass(frozen=True)
class CrossWLF:
    n: float
    tau_star_pa: float
    d1_pa_s: float
    d2_k: float
    d3_k_pa: float
    a1: float
    a2_k: float

    def zero_shear_viscosity(self, temperature_k: float, pressure_pa: float) -> float:
        den = self.a2_k + temperature_k - self.d2_k
        if den <= 0.0:
            raise ValueError("Cross-WLF denominator <= 0 K")
        exponent = -self.a1 * (temperature_k - self.d2_k - self.d3_k_pa * pressure_pa) / den
        return self.d1_pa_s * math.exp(max(-700.0, min(700.0, exponent)))

    def viscosity(self, shear_rate_s: float, temperature_k: float, pressure_pa: float) -> float:
        if shear_rate_s < 0.0:
            raise ValueError("shear rate must be non-negative")
        eta0 = self.zero_shear_viscosity(temperature_k, pressure_pa)
        return eta0 / (1.0 + (eta0 * max(shear_rate_s, 1e-12) / self.tau_star_pa) ** (1.0 - self.n))


@dataclass(frozen=True)
class PVTTable:
    """Bilinear table over pressure rows and temperature columns."""
    temperatures_k: tuple[float, ...]
    pressures_pa: tuple[float, ...]
    density_kg_m3: tuple[tuple[float, ...], ...]

    def __post_init__(self) -> None:
        if len(self.temperatures_k) < 2 or len(self.pressures_pa) < 2:
            raise ValueError("PVT table needs at least a 2x2 grid")
        if any(b <= a for a, b in zip(self.temperatures_k, self.temperatures_k[1:])):
            raise ValueError("temperatures must be strictly increasing")
        if any(b <= a for a, b in zip(self.pressures_pa, self.pressures_pa[1:])):
            raise ValueError("pressures must be strictly increasing")
        if len(self.density_kg_m3) != len(self.pressures_pa) or any(len(r) != len(self.temperatures_k) for r in self.density_kg_m3):
            raise ValueError("density grid dimensions do not match axes")

    def density(self, pressure_pa: float, temperature_k: float) -> float:
        p = min(max(pressure_pa, self.pressures_pa[0]), self.pressures_pa[-1])
        t = min(max(temperature_k, self.temperatures_k[0]), self.temperatures_k[-1])
        ip = min(len(self.pressures_pa) - 2, bisect.bisect_right(self.pressures_pa, p) - 1)
        it = min(len(self.temperatures_k) - 2, bisect.bisect_right(self.temperatures_k, t) - 1)
        p0, p1 = self.pressures_pa[ip], self.pressures_pa[ip + 1]
        t0, t1 = self.temperatures_k[it], self.temperatures_k[it + 1]
        wp, wt = (p - p0) / (p1 - p0), (t - t0) / (t1 - t0)
        q00, q01 = self.density_kg_m3[ip][it], self.density_kg_m3[ip][it + 1]
        q10, q11 = self.density_kg_m3[ip + 1][it], self.density_kg_m3[ip + 1][it + 1]
        return (1 - wp) * ((1 - wt) * q00 + wt * q01) + wp * ((1 - wt) * q10 + wt * q11)

    def validate(self) -> dict[str, float | bool]:
        """Return monotonicity and positivity checks for a measured PVT table."""
        rows_ok = all(all(v > 0.0 for v in row) for row in self.density_kg_m3)
        temperature_ok = all(all(row[j + 1] <= row[j] for j in range(len(row) - 1)) for row in self.density_kg_m3)
        pressure_ok = all(all(self.density_kg_m3[i + 1][j] >= self.density_kg_m3[i][j] for i in range(len(self.pressures_pa) - 1)) for j in range(len(self.temperatures_k)))
        return {"positive": rows_ok, "non_increasing_with_temperature": temperature_ok,
                "non_decreasing_with_pressure": pressure_ok,
                "valid": rows_ok and pressure_ok and temperature_ok}


def constrained_shrinkage(temperature_k: float, pressure_pa: float, *, t_ref: float, p_ref: float,
                          cte_per_k: float, pv_strain_per_pa: float, solid_fraction: float = 0.0) -> float:
    """Small-strain volumetric-to-linear screening law, bounded for stability."""
    raw = cte_per_k * (temperature_k - t_ref) - pv_strain_per_pa * (pressure_pa - p_ref) - 0.006 * max(0.0, min(1.0, solid_fraction))
    return max(-0.2, min(0.2, raw))
