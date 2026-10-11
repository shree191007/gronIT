import math
import numpy as np
from neocloud import physics as P
from neocloud.config import SIM


def test_seawater_matches_known_values():
    s = P.seawater(4.0, 35.0, 150.0)
    assert abs(s["rho"] - 1028) < 2.5                     # kg/m3
    assert abs(s["rho_cp"] - 4.1e6) / 4.1e6 < 0.01
    assert 1.5e-6 < s["nu"] < 1.75e-6
    assert 0.55 < s["k"] < 0.60
    assert 10 < s["Pr"] < 13


def test_churchill_bernstein_reference_point():
    # hand calculation of the correlation gives 214
    assert 205 < P.nusselt_cross(1e5, 0.7) < 225   # hand calc: 214


def test_U_rises_with_current_and_is_capped_by_series_resistance():
    u0 = P.U_overall(0.0, 27, 2)["U"]
    u1 = P.U_overall(0.5, 27, 2)["U"]
    assert u1 > u0
    cap = 1 / (0.030 / 45 + 3e-4 + 1 / 1500)
    assert u1 < cap


def test_lmtd_and_plume():
    assert abs(P.lmtd(32, 22, 2) - 24.66) < 0.05
    assert math.isclose(float(P.bulk_plume_rise(0.96e6, 0.2)), 0.96e6 / (4.1e6 * 0.2 * 3.2 * 12), rel_tol=1e-9)
    assert P.bulk_plume_rise(0.96e6, 0.0) == P.bulk_plume_rise(0.96e6, 0.02)       # floor


def test_capacity_factor_curve():
    cf = P.capacity_factor(np.array([0, 2.9, 3.0, 10.6, 15, 24.9, 25.0]))
    assert cf[0] == cf[1] == 0 and cf[2] == 0
    assert abs(cf[3] - 0.9) < 1e-9 and abs(cf[4] - 0.9) < 1e-9 and cf[6] == 0


def test_served_fraction_limits():
    flat = np.full(1000, 0.5)
    assert abs(P.served_fraction(flat, 2.0, 0) - 1.0) < 1e-9      # exactly meets load
    assert P.served_fraction(np.zeros(1000), 2.0, 12) == 0.0
    assert P.served_fraction(flat, 1.0, 0) == 0.5
    # storage can only help
    rng = np.random.default_rng(0)
    cf = np.clip(rng.normal(0.4, 0.3, 5000), 0, 0.9)
    assert P.served_fraction(cf, 2.0, 12) >= P.served_fraction(cf, 2.0, 0)


def test_served_fraction_conserves_energy():
    rng = np.random.default_rng(1)
    cf = np.clip(rng.normal(0.4, 0.3, 5000), 0, 0.9)
    over, eta = 2.0, 0.95
    served = P.served_fraction(cf, over, 12, eta) * len(cf)
    available = over * cf.sum()
    assert served <= available + 1e-6                              # cannot serve more than generated


def test_synthetic_wind_mean_and_persistence():
    v = P.synthetic_wind(10.0, years=20)
    assert abs(v.mean() - 10.0) < 0.3
    assert 0.9 < P.autocorr(v, 1) < 1.0


def test_shear_and_weibull_roundtrip():
    rng = np.random.default_rng(2)
    v100 = rng.weibull(2.2, 20000) * 11
    v10 = v100 * (0.1) ** 0.11
    assert abs(P.shear_exponent(v10, v100) - 0.11) < 1e-6
    k, lam = P.weibull_fit(v100)
    assert abs(k - 2.2) < 0.1 and abs(lam - 11) < 0.2


def test_lull_runs():
    v = np.array([9, 9, 1, 1, 1, 9, 1, 9])
    s = P.lull_stats(v, 3)
    assert s["longest_h"] == 3 and s["n_runs"] == 2
