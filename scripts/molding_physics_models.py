"""Screening constitutive models for polymer filling/cooling coupling.

Parameters are explicit and replaceable by measured PA66-GF30 data. Results
are engineering screening until calibrated against experiments.
"""
from __future__ import annotations
import math

def wlf_shift_factor(temp_c: float, ref_c: float = 230.0, c1: float = 17.44, c2: float = 51.6) -> float:
    den = c2 + temp_c - ref_c
    if den <= 0: return 1.0e12
    return 10.0 ** (-c1 * (temp_c - ref_c) / den)

def cross_wlf_viscosity(temp_c: float, shear_rate: float, *, eta0_pa_s: float = 800.0,
                        tau_pa: float = 2.0e4, n: float = 0.35,
                        ref_c: float = 230.0, wlf_c1: float = 17.44,
                        wlf_c2: float = 51.6) -> float:
    """Cross-WLF viscosity surrogate, positive and finite for solver use."""
    g = max(1.0e-12, abs(shear_rate))
    eta_zero = max(1.0e-9, eta0_pa_s * wlf_shift_factor(temp_c, ref_c, wlf_c1, wlf_c2))
    return eta_zero / (1.0 + (eta_zero * g / max(1.0e-9, tau_pa)) ** (1.0 - n))

def thermal_conductivity(temp_c: float, *, k_ref: float = 0.32, slope: float = -2.0e-4) -> float:
    return max(0.05, k_ref + slope * (temp_c - 230.0))

def cooling_step(temp_c: float, mold_temp_c: float, dt_s: float, *, h_w_m2k: float = 450.0,
                 thickness_m: float = 0.002, rho_kg_m3: float = 1150.0,
                 cp_j_kgk: float = 1800.0) -> float:
    """Lumped cooling step with an explicit stability-safe exponential update."""
    if dt_s < 0 or thickness_m <= 0 or rho_kg_m3 <= 0 or cp_j_kgk <= 0: raise ValueError("invalid cooling parameters")
    tau = rho_kg_m3 * cp_j_kgk * thickness_m / max(1.0e-9, 2.0 * h_w_m2k)
    return mold_temp_c + (temp_c - mold_temp_c) * math.exp(-dt_s / tau)

def solidification_fraction(temp_c: float, *, melt_c: float = 260.0, solid_c: float = 180.0) -> float:
    if melt_c <= solid_c: raise ValueError("melt_c must exceed solid_c")
    return max(0.0, min(1.0, (melt_c - temp_c) / (melt_c - solid_c)))

def crystallization_fraction(temp_c: float, time_s: float, *, t_peak_c: float = 190.0,
                             rate_s_inv: float = 0.08, avrami_n: float = 2.2) -> float:
    """Isothermal Avrami-like screening fraction with a temperature window."""
    window = math.exp(-((temp_c - t_peak_c) / 35.0) ** 2)
    return max(0.0, min(1.0, 1.0 - math.exp(-max(0.0, rate_s_inv * window * time_s) ** avrami_n)))

def pvt_shrink_strain(temp_c: float, pressure_mpa: float, *, cte_1k: float = 6.0e-5,
                      pv_coeff_per_mpa: float = 1.2e-4, ref_temp_c: float = 230.0,
                      ref_pressure_mpa: float = 80.0, crystallinity: float = 0.0) -> float:
    thermal = cte_1k * (temp_c - ref_temp_c)
    pressure = -pv_coeff_per_mpa * (pressure_mpa - ref_pressure_mpa)
    crystal = -0.006 * max(0.0, min(1.0, crystallinity))
    return thermal + pressure + crystal

def void_candidate(pressure_mpa: float, temperature_c: float, *, vapor_pressure_mpa: float = 0.02,
                   solidification: float = 0.5) -> bool:
    return pressure_mpa <= vapor_pressure_mpa and solidification < 0.95 and temperature_c > 80.0

def weld_front_meeting(arrival_a_s: float, arrival_b_s: float, *, max_gap_s: float = 0.02) -> dict:
    gap = abs(arrival_a_s - arrival_b_s)
    return {"result": "CANDIDATE" if gap <= max_gap_s else "NO_CANDIDATE",
            "arrival_gap_s": gap, "threshold_s": max_gap_s,
            "status": "SCREENING_ONLY"}

def fiber_orientation_tensor(flow_direction: tuple[float, float, float], alignment: float = 0.7) -> tuple[tuple[float, ...], ...]:
    """Second-order orientation tensor surrogate for short GF; trace is one."""
    n = math.sqrt(sum(v*v for v in flow_direction))
    if n <= 0: raise ValueError("flow_direction must be non-zero")
    q = tuple(v/n for v in flow_direction); a = max(0.0, min(1.0, alignment))
    return tuple(tuple(a*q[i]*q[j] + (1-a)*(1.0 if i==j else 0.0)/3.0 for j in range(3)) for i in range(3))

def anisotropic_shrink_strain(base_strain: float, orientation: tuple[tuple[float, ...], ...], *, flow_ratio: float = 0.55) -> tuple[float, float, float]:
    """Split scalar shrinkage into flow/transverse/thickness components."""
    af = max(0.0, min(1.0, orientation[0][0])); ff = max(0.0, min(1.0, flow_ratio))
    flow = base_strain * (1.0 - ff * af)
    transverse = base_strain * (1.0 + ff * af)
    return (flow, transverse, base_strain)

def skin_core_weight(distance_from_wall_m: float, half_thickness_m: float = 0.001, skin_fraction: float = 0.25) -> float:
    """0=core, 1=skin; smooth wall-distance weight."""
    if half_thickness_m <= 0: raise ValueError("half_thickness_m must be positive")
    return max(0.0, min(1.0, 1.0 - distance_from_wall_m / max(1.0e-12, half_thickness_m*skin_fraction)))
