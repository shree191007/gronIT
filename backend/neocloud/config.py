"""Sites, the assumptions under test (mirroring the simulator page and capex model), and verdict thresholds.

Everything tagged [A] is an assumption made by us, not a sourced fact. Change it here, rerun, and
the verdicts update.
"""
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CACHE_DIR = ROOT / "data_cache"
OUT_DIR = ROOT / "out"


@dataclass(frozen=True)
class Site:
    key: str
    name: str
    lat: float
    lon: float          # degrees east, -180..180
    note: str = ""

    @property
    def lon360(self) -> float:
        return self.lon % 360.0


SITES: dict[str, Site] = {s.key: s for s in [
    Site("drake", "Drake Passage", -58.5, -63.0, "Narrowest ACC choke point; strongest flow, roughest seas"),
    Site("kerguelen", "Kerguelen Plateau, south", -55.0, 75.0, "Indian-sector ACC, plateau-steered flow"),
    Site("pacific", "SE Pacific ACC", -57.0, -120.0, "Open Pacific sector, far from land"),
    Site("chile", "Offshore southern Chile", -53.5, -76.5, "Near-shore stage control; sits north of the ACC core"),
]}

# --------------------------------------------------------------------------------------
# Assumptions as they appear in the simulator page (template.html) and capex_model.py
# --------------------------------------------------------------------------------------
SIM = dict(
    pod_heat_W=0.96e6,          # 8 racks x 120 kW
    pod_D_m=3.2, pod_L_m=12.0,
    hull_area_m2=121.0,         # bare cylinder, pi*D*L
    fin_factor=1.5,             # default area multiplier
    rho_cp=4.1e6,               # J/m3/K
    sea_T_C=4.0, sea_T_range=(0.0, 10.0),
    depth_m=150.0,
    current_default=0.20, current_range=(0.01, 0.50),
    U_still=200.0, U_per_ms=1200.0,        # U = 200 + 1200 v   [A]
    supply_C=(18.0, 32.0), loop_dT_K=10.0,
    wind_mean_base=10.5, wind_mean_range=(9.0, 12.0),   # mean hub-height wind, m/s [A]
    weibull_k=2.2, ar1_rho=0.985,                        # synthetic wind generator [A]
    overbuild=2.0, storage_h=12.0, storage_eta=0.95,
    cut_in=3.0, rated=10.6, cut_out=25.0, wake_losses=0.90,
    hub_height_m=150.0,         # [A] 15 MW class hub height
    ref_height_m=100.0,         # ERA5 level used
)

# Physical inputs for the heat-transfer check (not from the sim; these are my screening values)
HEAT = dict(
    wall_thickness_m=0.030, wall_k=45.0,    # steel shell
    fouling_m2K_W=3.0e-4,                   # outside biofilm / coating [A]
    h_inner_W_m2K=1500.0,                   # glycol jacket side [A]
    coolant_supply_C=22.0, coolant_return_C=32.0,
)

# Design limits that are team choices, not facts [A]
LIMITS = dict(
    plume_dT_limit_K=0.5,        # bulk warming allowed for a 10-pod node (illustrative)
    service_Hs_m=2.5,            # max significant wave height for pod swap / ROV work
    service_window_h=72,
    slack_current_ms=0.05,
)

# Verdict thresholds (explicit so they can be argued with)
THRESH = dict(
    sea_T_median_tol=2.0, sea_T_marginal_tol=4.0,
    props_tol=0.03,
    U_ratio_ok=1.25, U_ratio_bad=2.0,
    supply_ok_C=27.0, supply_spec_C=32.0,      # supply temp needed: no throttling (Tj=Tc+38 K, throttle at 70 C) / vendor spec max
    capacity_time_ok=0.99, capacity_time_marginal=0.95,
    wind_mean_tol=1.0, wind_mean_marginal_tol=2.0,
    served_tol=0.03, served_marginal_tol=0.07,
    service_window_ok=0.25, service_window_marginal=0.10,
    current_median_tol=0.10,
    slack_fraction_flag=0.10,
)

YEARS = list(range(2015, 2025))
WAVE_YEARS = [2021, 2022, 2023, 2024]     # Open-Meteo marine archive starts April 2021; earlier requests return nulls
HYCOM_MONTHS = [(2023, 1), (2023, 4), (2023, 7), (2023, 10)]    # one per season, HYCOM expt 93.0 covers 2018-12..2024-09
ARGO_YEARS = (2019, 2024)
