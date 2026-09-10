import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "scripts"))
from material_chain import CrossWLF, PVTTable, TaitTwoDomain, constrained_shrinkage


def test_tait_reference_and_pressure_response():
    m = TaitTwoDomain(900.0, 503.15, 2.0e-4, 7.0e-5, 393.15, 5.0, 2.0e8, 4.0e8)
    rho0 = m.density(101325.0, 503.15)
    rho1 = m.density(30.0e6, 503.15)
    assert math.isclose(rho0, 900.0, rel_tol=2e-3)
    assert rho1 > rho0
    assert m.compressibility_pa_inv(30.0e6, 503.15) > 0.0
    drdp, drdt = m.density_derivatives(30.0e6, 503.15)
    assert drdp > 0.0
    assert drdt < 0.0
    assert m.sound_speed_m_s(30.0e6, 503.15) > 0.0


def test_cross_wlf_shear_thinning_and_pressure_shift():
    m = CrossWLF(0.35, 5.0e4, 1.0e10, 378.15, 0.0, 17.44, 51.6)
    low = m.viscosity(1.0, 503.15, 1.0e5)
    high = m.viscosity(1000.0, 503.15, 1.0e5)
    assert low > high > 0.0


def test_pvt_table_bilinear_interpolation():
    table = PVTTable((300.0, 500.0), (0.0, 1.0e6), ((1000.0, 900.0), (1100.0, 1000.0)))
    assert math.isclose(table.density(5.0e5, 400.0), 1000.0)
    assert table.validate()["valid"]


def test_shrinkage_is_bounded():
    assert -0.2 <= constrained_shrinkage(300.0, 30.0e6, t_ref=503.15, p_ref=1.0e5,
                                         cte_per_k=1e-4, pv_strain_per_pa=1e-10) <= 0.2
