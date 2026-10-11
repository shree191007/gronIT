"""Verdict logic on synthetic site data (no network)."""
import numpy as np
import pandas as pd
from neocloud import checks
from neocloud.config import Site
from neocloud.cache import MissingData
from neocloud import physics as P


class FakeData:
    def __init__(self, T=4.0, speed=0.2, hub_mean=10.5, hs=2.0, n=2400):
        self.site = Site("t", "Test", -55, 0)
        self.years = [2020, 2021]
        rng = np.random.default_rng(3)
        self.argo = pd.DataFrame({"temp": rng.normal(T, 0.5, 200), "psal": 34.4,
                                  "time": pd.date_range("2020-01-01", periods=200, freq="7D")})
        sp = np.abs(rng.normal(speed, speed * 0.3, n))
        ang = rng.normal(0, 0.2, n)
        self.uv = pd.DataFrame({"u": sp * np.cos(ang), "v": sp * np.sin(ang), "speed": sp,
                                "time": pd.date_range("2023-01-01", periods=n, freq="3h")})
        t = pd.date_range("2020-01-01", periods=2 * 8760, freq="h")
        hub = P.synthetic_wind(hub_mean, years=2, seed=5)[: len(t)]
        v50 = hub / 3.0 ** 0.11
        self.Z_LOW, self.Z_HIGH = 10.0, 50.0
        self.wind = pd.DataFrame({"time": t, "v50": v50, "v10": v50 * (10 / 50) ** 0.11})
        self.waves = pd.DataFrame({"time": t, "wave_height": np.abs(rng.normal(hs, 0.3, len(t))), "wave_period": 9.0})

    @property
    def wind_era5(self):
        raise MissingData("no era5 in fake")


def test_sea_temp_verdicts():
    assert checks.c1_sea_temperature(FakeData(T=4.0)).verdict == "supported"
    assert checks.c1_sea_temperature(FakeData(T=1.0)).verdict in ("marginal", "supported")
    assert checks.c1_sea_temperature(FakeData(T=12.0)).verdict == "contradicted"


def test_properties_supported():
    assert checks.c3_properties(FakeData()).verdict == "supported"


def test_heat_transfer_flags_optimistic_slope():
    r = checks.c4_heat_transfer(FakeData(speed=0.4))
    assert r.verdict in ("marginal", "contradicted")          # sim's 1200 W/m2K per m/s is too steep
    assert r.observed["U_physics_at_0_5"] < r.observed["U_sim_at_0_5"]


def test_headroom_needs_current():
    slow = checks.c5_rejection_headroom(FakeData(speed=0.05))
    fast = checks.c5_rejection_headroom(FakeData(speed=0.45))
    assert slow.observed["supply_temp_needed"]["p50"]["supply_C"] >= fast.observed["supply_temp_needed"]["p50"]["supply_C"]
    assert slow.observed["supply_temp_needed"]["p50"]["supply_C"] > 18          # hull must run warmer than sea


def test_plume_gets_worse_with_slow_current():
    a = checks.c6_plume(FakeData(speed=0.5)).observed["ten_pods_in_line_K"]["p50"]
    b = checks.c6_plume(FakeData(speed=0.05)).observed["ten_pods_in_line_K"]["p50"]
    assert b > a


def test_wind_resource_detects_mean():
    ok = checks.c7_wind_resource(FakeData(hub_mean=10.5))
    bad = checks.c7_wind_resource(FakeData(hub_mean=6.0))
    assert ok.verdict == "supported" and bad.verdict == "contradicted"


def test_served_fraction_close_to_synthetic_when_data_is_synthetic():
    r = checks.c8_served_fraction(FakeData(hub_mean=10.5))
    assert abs(r.observed["difference"]) < 0.08


def test_service_windows_fail_in_big_seas():
    calm = checks.c9_service_windows(FakeData(hs=1.0))
    rough = checks.c9_service_windows(FakeData(hs=5.0))
    assert calm.verdict == "supported" and rough.verdict == "contradicted"


def test_supply_temp_solver_is_consistent():
    from neocloud.checks import _supply_needed
    ts = _supply_needed(0.2, 2.0, 34.4, 0.96e6, 121 * 1.425)
    assert ts is not None and 15 < ts < 40
    # a larger hull needs a cooler loop to be sufficient, never a warmer one
    assert _supply_needed(0.2, 2.0, 34.4, 0.96e6, 121 * 3) < ts
    # impossible load returns None
    assert _supply_needed(0.2, 2.0, 34.4, 50e6, 121) is None


def test_direction_flags():
    r = checks.BY_ID["C7"](FakeData(hub_mean=14.0))
    assert r.direction == "better"
    r = checks.BY_ID["C9"](FakeData(hs=5.0))
    assert r.direction == "worse"
    r = checks.BY_ID["C1"](FakeData(T=1.0))
    assert r.direction == "better"


def test_economics_improves_with_better_wind():
    good = checks.BY_ID["C10"](FakeData(hub_mean=14.0))
    assert good.observed["cost_change_pct"] < 0 and good.direction == "better"
