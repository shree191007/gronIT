"""Physics used by the checks: seawater properties, heat transfer on a hull, wind power, storage dispatch."""
from __future__ import annotations
import math
import numpy as np
import gsw
from .config import SIM, HEAT


# ---------------------------------------------------------------- seawater
def seawater(T_C: float, S_psu: float = 34.5, p_dbar: float = 150.0) -> dict:
    """Density, cp, viscosity, conductivity, expansion, Prandtl at T/S/p.

    rho, cp, alpha from TEOS-10 (gsw). Viscosity and conductivity from Sharqawy et al. (2010),
    which are valid 0-180 C, 0-150 g/kg.
    """
    SA = S_psu * 35.16504 / 35.0
    rho = float(gsw.rho_t_exact(SA, T_C, p_dbar))
    cp = float(gsw.cp_t_exact(SA, T_C, p_dbar))
    alpha = float(gsw.alpha_wrt_t_exact(SA, T_C, p_dbar))
    S = SA / 1000.0                                           # kg/kg
    mu_w = 4.2844e-5 + 1.0 / (0.157 * (T_C + 64.993) ** 2 - 91.296)
    A = 1.541 + 1.998e-2 * T_C - 9.52e-5 * T_C ** 2
    B = 7.974 - 7.561e-2 * T_C + 4.724e-4 * T_C ** 2
    mu = mu_w * (1 + A * S + B * S ** 2)
    TK = T_C + 273.15
    SA_g = SA
    log10_k = math.log10(240 + 0.0002 * SA_g) + 0.434 * (2.3 - (343.5 + 0.037 * SA_g) / TK) * \
        (1 - TK / (647.3 + 0.03 * SA_g)) ** (1 / 3)
    k = 10 ** log10_k * 1e-3                                  # mW/mK -> W/mK
    return dict(rho=rho, cp=cp, rho_cp=rho * cp, mu=mu, nu=mu / rho, k=k, alpha_T=alpha,
                kappa=k / (rho * cp), Pr=cp * mu / k)


# ---------------------------------------------------------------- heat transfer on a cylinder
def nusselt_cross(Re: float, Pr: float) -> float:
    """Churchill-Bernstein, cylinder in cross flow, valid for Re*Pr > 0.2."""
    if Re <= 0:
        return 0.0
    return 0.3 + (0.62 * Re ** 0.5 * Pr ** (1 / 3) / (1 + (0.4 / Pr) ** (2 / 3)) ** 0.25) * \
        (1 + (Re / 282000.0) ** (5 / 8)) ** (4 / 5)


def nusselt_natural(Ra: float, Pr: float) -> float:
    """Churchill-Chu, horizontal cylinder, whole Ra range."""
    if Ra <= 0:
        return 0.0
    return (0.6 + 0.387 * Ra ** (1 / 6) / (1 + (0.559 / Pr) ** (9 / 16)) ** (8 / 27)) ** 2


def h_outer(v: float, T_wall: float, T_sea: float, D: float, S_psu=34.5, p_dbar=150.0) -> dict:
    """Outside film coefficient: forced and natural convection blended as (Nu_f^3 + Nu_n^3)^(1/3)."""
    Tf = 0.5 * (T_wall + T_sea)
    pr = seawater(Tf, S_psu, p_dbar)
    Re = v * D / pr["nu"]
    dT = max(T_wall - T_sea, 0.0)
    Ra = 9.81 * pr["alpha_T"] * dT * D ** 3 / (pr["nu"] * pr["kappa"])
    nf, nn = nusselt_cross(Re, pr["Pr"]), nusselt_natural(Ra, pr["Pr"])
    nu_mix = (nf ** 3 + nn ** 3) ** (1 / 3)
    return dict(h=nu_mix * pr["k"] / D, h_forced=nf * pr["k"] / D, h_natural=nn * pr["k"] / D, Re=Re, Ra=Ra)


def U_overall(v: float, T_coolant: float, T_sea: float, D=SIM["pod_D_m"], S_psu=34.5, p_dbar=150.0,
              R_wall=HEAT["wall_thickness_m"] / HEAT["wall_k"], R_foul=HEAT["fouling_m2K_W"],
              h_in=HEAT["h_inner_W_m2K"]) -> dict:
    """Overall U referred to the bare outer area, solving the wall temperature self-consistently
    (natural convection depends on the wall-to-sea temperature difference)."""
    Tw = 0.5 * (T_coolant + T_sea)
    for _ in range(60):
        ho = h_outer(v, Tw, T_sea, D, S_psu, p_dbar)
        U = 1.0 / (1.0 / ho["h"] + R_wall + R_foul + 1.0 / h_in)
        Tw_new = T_sea + U * (T_coolant - T_sea) / ho["h"]
        if abs(Tw_new - Tw) < 1e-4:
            break
        Tw = 0.6 * Tw + 0.4 * Tw_new
    return dict(U=U, h_out=ho["h"], T_wall=Tw, Re=ho["Re"], Ra=ho["Ra"], h_forced=ho["h_forced"], h_natural=ho["h_natural"])


def U_sim(v) -> np.ndarray:
    return SIM["U_still"] + SIM["U_per_ms"] * np.asarray(v, dtype=float)


def lmtd(T_in: float, T_out: float, T_sea: float) -> float:
    a, b = T_in - T_sea, T_out - T_sea
    if a <= 0 or b <= 0:
        return 0.0
    return (a - b) / math.log(a / b) if abs(a - b) > 1e-9 else a


def bulk_plume_rise(Q_W: float, v, D=SIM["pod_D_m"], L=SIM["pod_L_m"], rho_cp=SIM["rho_cp"], v_floor=0.02):
    v = np.maximum(np.asarray(v, dtype=float), v_floor)
    return Q_W / (rho_cp * v * D * L)


# ---------------------------------------------------------------- wind and storage
def scale_wind(v_ref, alpha: float, z_ref=SIM["ref_height_m"], z_hub=SIM["hub_height_m"]):
    return np.asarray(v_ref, dtype=float) * (z_hub / z_ref) ** alpha


def shear_exponent(v_low, v_high, z_low=10.0, z_high=100.0) -> float:
    """Power-law exponent from the long-term mean wind at two heights."""
    return math.log(float(np.mean(v_high)) / float(np.mean(v_low))) / math.log(z_high / z_low)


def capacity_factor(v, cin=SIM["cut_in"], rated=SIM["rated"], cout=SIM["cut_out"], losses=SIM["wake_losses"]):
    v = np.asarray(v, dtype=float)
    cf = np.where(v < cin, 0.0, np.where(v < rated, (v ** 3 - cin ** 3) / (rated ** 3 - cin ** 3),
                                         np.where(v < cout, 1.0, 0.0)))
    return cf * losses


def served_fraction(cf, overbuild=SIM["overbuild"], store_h=SIM["storage_h"], eta=SIM["storage_eta"]) -> float:
    """Fraction of the (constant) load served by wind plus storage. Same dispatch as capex_model.py:
    store hours are expressed in units of average load, wind is overbuilt relative to load."""
    soc, tot = 0.0, 0.0
    for c in np.asarray(cf, dtype=float):
        w = overbuild * c
        if w >= 1.0:
            tot += 1.0
            soc = min(store_h, soc + (w - 1.0) * eta)
        else:
            d = min(1.0 - w, soc)
            soc -= d
            tot += w + d * eta
    return tot / len(cf)


def synthetic_wind(mean_v: float, years=10, k=SIM["weibull_k"], rho=SIM["ar1_rho"], seed=11) -> np.ndarray:
    """Weibull marginal with AR(1) Gaussian-copula persistence: what the capex model assumed."""
    from statistics import NormalDist
    from scipy.special import ndtr
    rng = np.random.default_rng(seed)
    n = int(years * 8760)
    z = np.empty(n)
    z[0] = rng.normal()
    eps = rng.normal(size=n) * math.sqrt(1 - rho ** 2)
    for t in range(1, n):
        z[t] = rho * z[t - 1] + eps[t]
    u = np.clip(ndtr(z), 1e-9, 1 - 1e-9)
    lam = mean_v / math.gamma(1 + 1 / k)
    return lam * (-np.log(1 - u)) ** (1 / k)


def weibull_fit(v) -> tuple[float, float]:
    """Maximum-likelihood Weibull shape k and scale lambda."""
    from scipy.stats import weibull_min
    v = np.asarray(v, dtype=float)
    v = v[v > 0.05]
    k, _, lam = weibull_min.fit(v, floc=0)
    return float(k), float(lam)


def lull_stats(v, thr: float) -> dict:
    """Run-length statistics of consecutive hours below thr (hours)."""
    below = np.asarray(v) < thr
    runs, n = [], 0
    for b in below:
        if b:
            n += 1
        elif n:
            runs.append(n); n = 0
    if n:
        runs.append(n)
    runs = np.array(runs) if runs else np.array([0])
    return dict(frac_below=float(below.mean()), n_runs=int(len(runs)), longest_h=int(runs.max()),
                p95_run_h=float(np.percentile(runs, 95)), mean_run_h=float(runs.mean()))


def autocorr(x, lag=1) -> float:
    x = np.asarray(x, dtype=float)
    x = x - x.mean()
    return float(np.dot(x[:-lag], x[lag:]) / np.dot(x, x))
