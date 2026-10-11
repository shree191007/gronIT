"""Each check takes real data and the simulator's assumption, and returns a verdict with numbers.

Verdicts: supported | marginal | contradicted | untestable. Thresholds live in config.THRESH.
"""
from __future__ import annotations
from dataclasses import dataclass, field, asdict
import numpy as np
import pandas as pd
from . import physics as P
from .config import SIM, HEAT, LIMITS, THRESH
from .cache import MissingData
from .data import SiteData


@dataclass
class Result:
    id: str
    title: str
    assumption: str
    observed: dict
    verdict: str
    finding: str
    sim_change: str = ""
    sources: list = field(default_factory=list)
    direction: str = "neutral"      # better | worse | neutral: which way the data differs from the assumption

    def to_dict(self):
        return asdict(self)


def _r(x, n=3):
    return None if x is None or (isinstance(x, float) and not np.isfinite(x)) else round(float(x), n)


def _pct(a, qs=(5, 50, 95)):
    return {f"p{q}": _r(np.percentile(a, q), 3) for q in qs}


SRC_ERA5 = "ECMWF ERA5 via Open-Meteo archive API (archive-api.open-meteo.com)"
SRC_WAVE = "Open-Meteo marine archive, wave model reanalysis from April 2021 (marine-api.open-meteo.com)"
SRC_HYCOM = "HYCOM GLBy0.08 expt 93.0 analysis, THREDDS NCSS (tds.hycom.org); a model, not observations"
SRC_ARGO = "Argo float profiles, Ifremer ERDDAP ArgoFloats (erddap.ifremer.fr), QC flag 1"
SRC_POWER = "NASA POWER hourly WS10M and WS50M, MERRA-2 reanalysis (power.larc.nasa.gov)"
SRC_PHYS = "Churchill-Bernstein / Churchill-Chu correlations; Sharqawy et al. 2010 seawater properties; TEOS-10 (gsw)"


# ------------------------------------------------------------------ C1 sea temperature
def c1_sea_temperature(d: SiteData) -> Result:
    a = d.argo
    T = a.temp.to_numpy()
    med = float(np.median(T))
    lo, hi = SIM["sea_T_range"]
    inside = float(np.mean((T >= lo) & (T <= hi)))
    err = abs(med - SIM["sea_T_C"])
    if err <= THRESH["sea_T_median_tol"] and inside >= 0.95:
        v = "supported"
    elif err <= THRESH["sea_T_marginal_tol"] and inside >= 0.80:
        v = "marginal"
    else:
        v = "contradicted"
    cold = "colder" if med < SIM["sea_T_C"] else "warmer"
    return Result("C1", "Sea temperature at pod depth", f"{SIM['sea_T_C']} C at {SIM['depth_m']:.0f} m, slider range {lo}-{hi} C",
                  dict(n_profiles=len(a), years=f"{a.time.min().year}-{a.time.max().year}", **_pct(T, (5, 25, 50, 75, 95)),
                       mean=_r(T.mean()), frac_inside_slider_range=_r(inside), salinity_median=_r(a.psal.median())),
                  v, f"Observed median {med:.1f} C, {cold} than the {SIM['sea_T_C']} C default; {inside * 100:.0f}% of profiles fall inside the slider range. "
                     f"Colder sea helps heat rejection, so a warm default is the conservative side.",
                  f"Set the default sea temperature to about {med:.1f} C for this site; keep the 0-10 C range.", [SRC_ARGO])


# ------------------------------------------------------------------ C2 currents
def c2_currents(d: SiteData) -> Result:
    u = d.uv
    s = u.speed.to_numpy()
    med = float(np.median(s))
    slack = float(np.mean(s < LIMITS["slack_current_ms"]))
    steadiness = float(np.hypot(u.u.mean(), u.v.mean()) / s.mean())
    lo, hi = SIM["current_range"]
    in_range = float(np.mean((s >= lo) & (s <= hi)))
    if abs(med - SIM["current_default"]) <= THRESH["current_median_tol"] and slack < THRESH["slack_fraction_flag"]:
        v = "supported"
    elif slack >= THRESH["slack_fraction_flag"] or med < 0.5 * SIM["current_default"]:
        v = "contradicted" if slack >= 2 * THRESH["slack_fraction_flag"] else "marginal"
    else:
        v = "marginal"
    return Result("C2", "Current speed at pod depth", f"{SIM['current_default']} m/s typical, slider {lo}-{hi} m/s",
                  dict(n_samples=len(u), months=sorted({f"{t.year}-{t.month:02d}" for t in u.time}), **_pct(s, (5, 25, 50, 75, 95, 99)),
                       max=_r(s.max()), frac_below_slack=_r(slack), slack_threshold=LIMITS["slack_current_ms"],
                       frac_inside_slider_range=_r(in_range), direction_steadiness=_r(steadiness),
                       mean_u=_r(u.u.mean()), mean_v=_r(u.v.mean())),
                  v, f"Median {med:.2f} m/s (P5 {np.percentile(s, 5):.2f}, P95 {np.percentile(s, 95):.2f}); "
                     f"{slack * 100:.1f}% of 3-hourly samples are below {LIMITS['slack_current_ms']} m/s; direction steadiness {steadiness:.2f} (1 = one-way flow).",
                  "Add this site's P5/P50/P95 as presets on the current slider; model slack water as a first-class case.",
                  [SRC_HYCOM])


# ------------------------------------------------------------------ C3 seawater properties
def c3_properties(d: SiteData) -> Result:
    T = float(np.median(d.argo.temp)); S = float(d.argo.psal.median())
    pr = P.seawater(T, S, SIM["depth_m"])
    err = abs(pr["rho_cp"] - SIM["rho_cp"]) / SIM["rho_cp"]
    v = "supported" if err <= THRESH["props_tol"] else ("marginal" if err <= 2 * THRESH["props_tol"] else "contradicted")
    nu_used = 1.56e-6
    return Result("C3", "Seawater volumetric heat capacity", f"rho*cp = {SIM['rho_cp'] / 1e6:.1f} MJ/m3/K; nu = 1.56e-6 m2/s in the Reynolds readout",
                  dict(T_C=_r(T, 2), S_psu=_r(S, 2), rho=_r(pr["rho"], 1), cp=_r(pr["cp"], 1), rho_cp_MJ=_r(pr["rho_cp"] / 1e6, 4),
                       nu_m2s=pr["nu"], k_W_mK=_r(pr["k"], 4), Pr=_r(pr["Pr"], 2), rho_cp_error=_r(err, 4),
                       nu_error=_r(abs(pr["nu"] - nu_used) / pr["nu"], 4)),
                  v, f"TEOS-10 gives rho*cp = {pr['rho_cp'] / 1e6:.3f} MJ/m3/K at {T:.1f} C ({err * 100:.1f}% from the sim). "
                     f"Kinematic viscosity is {pr['nu'] * 1e6:.2f}e-6 m2/s, so the Reynolds readout is {abs(pr['nu'] - nu_used) / pr['nu'] * 100:.0f}% high.",
                  "Change the Reynolds readout to use nu = 1.62e-6 m2/s at 4 C (minor).", [SRC_PHYS])


# ------------------------------------------------------------------ C4 heat-transfer coefficient
def c4_heat_transfer(d: SiteData) -> Result:
    Tsea = float(np.median(d.argo.temp)); S = float(d.argo.psal.median())
    Tc = 0.5 * (HEAT["coolant_supply_C"] + HEAT["coolant_return_C"])
    s = d.uv.speed.to_numpy()
    rows = {}
    ratios = []
    for q in (10, 50, 90):
        vq = float(np.percentile(s, q))
        u = P.U_overall(vq, Tc, Tsea, S_psu=S)
        us = float(P.U_sim(vq))
        rows[f"v_p{q}"] = dict(v=_r(vq, 3), U_physics=_r(u["U"], 0), U_sim=_r(us, 0), h_out=_r(u["h_out"], 0), ratio_sim_over_physics=_r(us / u["U"], 2))
        ratios.append(us / u["U"])
    still = P.U_overall(0.0, Tc, Tsea, S_psu=S)
    fast = P.U_overall(0.5, Tc, Tsea, S_psu=S)
    worst = max(ratios)
    v = "supported" if worst <= THRESH["U_ratio_ok"] else ("marginal" if worst <= THRESH["U_ratio_bad"] else "contradicted")
    cap = 1.0 / (HEAT["wall_thickness_m"] / HEAT["wall_k"] + HEAT["fouling_m2K_W"] + 1.0 / HEAT["h_inner_W_m2K"])
    return Result("C4", "Hull heat-transfer coefficient U", "U = 200 + 1200 v  W/m2K (200 still, 800 at 0.5 m/s)",
                  dict(**rows, U_physics_still=_r(still["U"], 0), U_physics_at_0_5=_r(fast["U"], 0), U_sim_still=200, U_sim_at_0_5=800,
                       series_resistance_cap_W_m2K=_r(cap, 0), coolant_C=Tc, sea_C=_r(Tsea, 2), wall_T_still_C=_r(still["T_wall"], 1)),
                  v, f"Still-water U matches ({still['U']:.0f} vs 200) because turbulent natural convection is strong at a 25 K wall-sea difference, "
                     f"but the sim's slope is too steep: at 0.5 m/s physics gives {fast['U']:.0f} against 800, since the glycol side, steel wall and fouling cap U at about {cap:.0f} W/m2K "
                     f"and the outside film is no longer the only resistance. Worst sim/physics ratio across P10-P90 currents is {worst:.1f}x.",
                  f"Replace the sim's U with a curve fitted to the physics: roughly {still['U']:.0f} W/m2K still rising to {fast['U']:.0f} at 0.5 m/s. "
                  "Inner-side h and fouling are my [A] values and the slope is sensitive to them.",
                  [SRC_PHYS, SRC_HYCOM, SRC_ARGO])


# ------------------------------------------------------------------ C5 rejection headroom
def _supply_needed(v: float, Tsea: float, S: float, Q: float, A_eff: float, use_sim_U: bool = False):
    """Lowest coolant supply temperature at which the hull rejects Q (return = supply + loop dT)."""
    dT = SIM["loop_dT_K"]

    def cap(Ts):
        Tm = Ts + dT / 2
        U = float(P.U_sim(v)) if use_sim_U else P.U_overall(v, Tm, Tsea, S_psu=S)["U"]
        return U * A_eff * P.lmtd(Ts + dT, Ts, Tsea)
    lo, hi = Tsea + 0.5, 90.0
    if cap(hi) < Q:
        return None
    for _ in range(45):
        mid = 0.5 * (lo + hi)
        lo, hi = (lo, mid) if cap(mid) >= Q else (mid, hi)
    return hi


def c5_rejection_headroom(d: SiteData, fin_eff: float = 0.85) -> Result:
    """Coolant supply temperature the hull needs to reject the full pod heat load, at low, median and high current."""
    Tsea = float(np.median(d.argo.temp)); S = float(d.argo.psal.median())
    s = d.uv.speed.to_numpy()
    Q = SIM["pod_heat_W"]
    A_eff = SIM["hull_area_m2"] * (1 + (SIM["fin_factor"] - 1) * fin_eff)
    need, need_sim = {}, {}
    for q in (5, 50, 95):
        vq = float(np.percentile(s, q))
        need[f"p{q}"] = dict(v=_r(vq, 3), supply_C=_r(_supply_needed(vq, Tsea, S, Q, A_eff), 1))
        need_sim[f"p{q}"] = _r(_supply_needed(vq, Tsea, S, Q, SIM["hull_area_m2"] * SIM["fin_factor"], use_sim_U=True), 1)
    worst = need["p5"]["supply_C"]
    # fixed-loop view: share of time a 22->32 C loop is enough
    Tc = 0.5 * (HEAT["coolant_supply_C"] + HEAT["coolant_return_C"])
    L = P.lmtd(HEAT["coolant_return_C"], HEAT["coolant_supply_C"], Tsea)
    grid = np.linspace(0, max(s.max(), 0.6), 25)
    Ug = np.array([P.U_overall(v, Tc, Tsea, S_psu=S)["U"] for v in grid])
    Qcap = np.interp(s, grid, Ug) * A_eff * L
    f_phys = float(np.mean(Qcap >= Q))
    req_factor = float(np.percentile(Q / (np.interp(s, grid, Ug) * SIM["hull_area_m2"] * L), 99))
    if worst is None or worst > THRESH["supply_spec_C"]:
        v = "contradicted"
    elif worst > THRESH["supply_ok_C"]:
        v = "marginal"
    else:
        v = "supported"
    ws = need_sim["p5"]
    return Result("C5", "Can the hull reject 0.96 MW?", f"Hull area x{SIM['fin_factor']} (U = 200 + 1200 v) rejects the full pod load at a normal 22 to 32 C loop",
                  dict(sea_C=_r(Tsea, 2), fin_efficiency_assumed=fin_eff, supply_temp_needed=need, supply_temp_needed_with_sim_U=need_sim,
                       limit_no_throttle_C=THRESH["supply_ok_C"], vendor_spec_max_C=THRESH["supply_spec_C"],
                       capacity_MW_p50_at_22_32C_loop=_r(np.percentile(Qcap, 50) / 1e6, 2), frac_time_22_32C_loop_enough=_r(f_phys, 4),
                       bare_hull_area_factor_needed_p99_at_22_32C=_r(req_factor, 2)),
                  v, f"To reject 0.96 MW with the x{SIM['fin_factor']} hull (fins at {fin_eff:.0%} efficiency) at this site's weakest-current case (P5, {need['p5']['v']} m/s), the coolant supply must be "
                     f"{worst if worst is not None else float('nan'):.1f} C; at the median current {need['p50']['supply_C']} C. The sim's own U would say {ws} C. "
                     f"Full-power operation without throttling needs a supply of {THRESH['supply_ok_C']:.0f} C or less (chip model Tj = coolant + 38 K, throttle at 70 C); the vendor maximum is {THRESH['supply_spec_C']:.0f} C.",
                  f"If the needed supply is above {THRESH['supply_ok_C']:.0f} C, add area (target bare-hull factor of about {req_factor:.1f} before fin efficiency) or plan on throttling during weak-current periods.",
                  [SRC_PHYS, SRC_HYCOM, SRC_ARGO])


# ------------------------------------------------------------------ C6 plume
def c6_plume(d: SiteData) -> Result:
    s = d.uv.speed.to_numpy()
    dT1 = P.bulk_plume_rise(SIM["pod_heat_W"], s)
    dT10 = dT1 * 10
    lim = LIMITS["plume_dT_limit_K"]
    p95 = float(np.percentile(dT10, 95)); p50 = float(np.percentile(dT10, 50))
    frac_over = float(np.mean(dT10 > lim))
    v = "supported" if p95 <= lim else ("marginal" if p50 <= lim else "contradicted")
    return Result("C6", "Bulk warming of the water passing a pod", "0.03 K for one pod at 0.2 m/s; 10 pods in the same stream add linearly",
                  dict(one_pod_K=_pct(dT1, (50, 95, 99)), ten_pods_in_line_K=_pct(dT10, (50, 95, 99)), limit_K=lim,
                       frac_time_ten_pods_over_limit=_r(frac_over, 4), v_floor_ms=0.02),
                  v, f"Ten in-line pods warm the passing water by {p50:.2f} K at the median current and {p95:.2f} K at P95; it exceeds the {lim} K illustrative limit {frac_over * 100:.1f}% of the time. "
                     "Values below 0.02 m/s are floored there, where the real plume turns buoyant and rises instead of diluting.",
                  "Stagger pods across the stream (cross-flow spacing) so no pod sits in another's wake, and agree a real ecological limit with the ecology team.",
                  [SRC_HYCOM])


# ------------------------------------------------------------------ C7 wind resource
def _hub_wind(d: SiteData):
    """Hub-height wind from the 10 m and 50 m series: fit the shear exponent on the long-term means, extrapolate."""
    w = d.wind
    alpha = P.shear_exponent(w.v10, w.v50, d.Z_LOW, d.Z_HIGH)
    hub = P.scale_wind(w.v50.to_numpy(), alpha, z_ref=d.Z_HIGH, z_hub=SIM["hub_height_m"])
    return hub, alpha


def c7_wind_resource(d: SiteData) -> Result:
    w = d.wind
    hub, alpha = _hub_wind(d)
    mean = float(hub.mean())
    k, lam = P.weibull_fit(hub)
    cf = P.capacity_factor(hub)
    yearly = pd.Series(hub, index=w.time).groupby(lambda t: t.year).mean()
    lo, hi = SIM["wind_mean_range"]
    err = mean - SIM["wind_mean_base"]
    v = "supported" if abs(err) <= THRESH["wind_mean_tol"] else ("marginal" if abs(err) <= THRESH["wind_mean_marginal_tol"] else "contradicted")
    # independent cross-check: ERA5 100 m (years in cache) vs MERRA-2 extrapolated to 100 m on the same hours
    cross = {}
    try:
        e = d.wind_era5
        m = pd.DataFrame({"time": w.time, "m100": P.scale_wind(w.v50.to_numpy(), alpha, z_ref=d.Z_HIGH, z_hub=100.0)})
        j = e.merge(m, on="time")
        if len(j) > 1000:
            cross = dict(overlap_years=sorted({int(t.year) for t in j.time}), era5_100m_mean=_r(j.wind_speed_100m.mean(), 2),
                         merra2_100m_mean=_r(j.m100.mean(), 2), era5_over_merra2_pct=_r((j.wind_speed_100m.mean() / j.m100.mean() - 1) * 100, 1),
                         hourly_correlation=_r(np.corrcoef(j.wind_speed_100m, j.m100)[0, 1], 3))
    except (MissingData, AttributeError):
        pass
    note = "above" if err > 0 else "below"
    xc = (f" Cross-check: ERA5 100 m is {cross['era5_over_merra2_pct']:+.1f}% against MERRA-2 over {len(cross['overlap_years'])} common years (hourly correlation {cross['hourly_correlation']:.2f})."
          if cross else "")
    return Result("C7", "Hub-height wind resource", f"mean {SIM['wind_mean_base']} m/s (range {lo}-{hi}), Weibull k = {SIM['weibull_k']}",
                  dict(hours=len(w), years=f"{w.time.min().year}-{w.time.max().year}", mean_hub_ms=_r(mean, 2), shear_exponent_fitted=_r(alpha, 3),
                       weibull_k=_r(k, 2), weibull_scale=_r(lam, 2), capacity_factor_per_turbine=_r(cf.mean(), 3),
                       year_mean_min=_r(yearly.min(), 2), year_mean_max=_r(yearly.max(), 2), frac_hours_below_cut_in=_r((hub < SIM["cut_in"]).mean(), 3),
                       frac_hours_above_rated=_r((hub >= SIM["rated"]).mean(), 3), frac_hours_above_cut_out=_r((hub >= SIM["cut_out"]).mean(), 4), cross_check=cross),
                  v, f"MERRA-2 gives a mean of {mean:.1f} m/s at {SIM['hub_height_m']:.0f} m (shear exponent {alpha:.3f} fitted from 10 m and 50 m, extrapolated), "
                     f"{abs(err):.1f} m/s {note} the {SIM['wind_mean_base']} m/s base case. Weibull k fits at {k:.2f} (sim {SIM['weibull_k']}). "
                     f"Capacity factor per turbine {cf.mean() * 100:.0f}% with the capex model's power curve and 10% losses." + xc,
                  f"Use {mean:.1f} m/s as this site's base wind. Reanalyses smooth gusts and wakes, and the 50 m to 150 m extrapolation adds uncertainty, so treat it as slightly optimistic.",
                  [SRC_POWER, SRC_ERA5])


# ------------------------------------------------------------------ C8 lulls, storage, served fraction
def c8_served_fraction(d: SiteData) -> Result:
    hub, _ = _hub_wind(d)
    cf = P.capacity_factor(hub)
    mean = float(hub.mean())
    real = P.served_fraction(cf)
    syn_v = P.synthetic_wind(mean, years=len(d.years))
    syn = P.served_fraction(P.capacity_factor(syn_v))
    by_year = pd.Series(cf, index=d.wind.time).groupby(lambda t: t.year).apply(lambda x: P.served_fraction(x.to_numpy()))
    lulls_real = P.lull_stats(hub, SIM["cut_in"] + 2.0)
    lulls_syn = P.lull_stats(syn_v, SIM["cut_in"] + 2.0)
    ac_real, ac_syn = P.autocorr(hub, 1), P.autocorr(syn_v, 1)
    base_syn = P.served_fraction(P.capacity_factor(P.synthetic_wind(SIM["wind_mean_base"], years=len(d.years))))
    min_over = {}
    for target in (0.90, 0.95):
        for ob in np.arange(1.0, 3.01, 0.1):
            if P.served_fraction(cf, float(ob), SIM["storage_h"]) >= target:
                min_over[f"served_{int(target * 100)}pct"] = _r(ob, 1)
                break
        else:
            min_over[f"served_{int(target * 100)}pct"] = None
    table = {}
    for ob in (1.5, 2.0, 3.0):
        for sh in (0, 12, 24, 48):
            table[f"over{ob}_store{sh}h"] = _r(P.served_fraction(cf, ob, sh), 3)
    diff = real - syn
    v = "supported" if abs(diff) <= THRESH["served_tol"] else ("marginal" if abs(diff) <= THRESH["served_marginal_tol"] else "contradicted")
    direction = "more" if diff > 0 else "less"
    return Result("C8", "Wind gaps: share of load served at 2x overbuild + 12 h storage", "Synthetic Weibull + AR(1, rho 0.985) wind, served fraction from the capex model",
                  dict(served_real=_r(real, 3), served_synthetic_same_mean=_r(syn, 3), served_capex_base_case_synthetic=_r(base_syn, 3), difference=_r(diff, 3),
                       min_overbuild_at_12h_storage=min_over,
                       served_by_year_min=_r(by_year.min(), 3), served_by_year_max=_r(by_year.max(), 3),
                       lull_below_5ms_real=lulls_real, lull_below_5ms_synthetic=lulls_syn,
                       lag1_autocorr_real=_r(ac_real, 4), lag1_autocorr_synthetic=_r(ac_syn, 4), served_grid=table),
                  v, f"With real hourly wind the 2x/12 h design serves {real * 100:.1f}% of the load, against {syn * 100:.1f}% for the synthetic series at the same mean "
                     f"({abs(diff) * 100:.1f} points {direction}). Years vary from {by_year.min() * 100:.1f}% to {by_year.max() * 100:.1f}%. "
                     f"Longest stretch below 5 m/s is {lulls_real['longest_h']} h in reality versus {lulls_syn['longest_h']} h synthetic. The capex base case (synthetic, 10.5 m/s mean) serves {base_syn * 100:.1f}%. "
                     f"A 90% served fraction needs only {min_over['served_90pct']}x overbuild with 12 h storage here.",
                  "Replace the synthetic wind in capex_model.py with this site's ERA5 series; use the served_grid to re-pick overbuild and storage.",
                  [SRC_ERA5])


# ------------------------------------------------------------------ C9 sea state and service windows
def c9_service_windows(d: SiteData) -> Result:
    w = d.waves.copy()
    hs = w.set_index("time").wave_height.asfreq("h")
    win = LIMITS["service_window_h"]
    out = {}
    for lim in (2.0, 2.5, 3.0, 3.5):
        # window opens at hour t if Hs stays below lim for the next `win` hours
        fut_max = hs[::-1].rolling(win, min_periods=win).max()[::-1]
        ok = (fut_max < lim)
        monthly = ok.groupby(ok.index.month).mean()
        out[f"Hs<{lim}"] = dict(annual=_r(ok.mean(), 3), best_month=int(monthly.idxmax()), best_month_frac=_r(monthly.max(), 3),
                                best_3mo_frac=_r(max(monthly.rolling(3, min_periods=3).mean().dropna().max(), 0), 3))
    key = out[f"Hs<{LIMITS['service_Hs_m']}"]
    f = key["best_3mo_frac"]
    v = "supported" if f >= THRESH["service_window_ok"] else ("marginal" if f >= THRESH["service_window_marginal"] else "contradicted")
    return Result("C9", f"Sea state for pod swaps ({win} h windows)", "An annual service/recovery campaign is possible (capex model: $8M/yr)",
                  dict(hours=len(hs.dropna()), period=f"{w.time.min():%Y-%m} to {w.time.max():%Y-%m}", Hs_p50=_r(hs.quantile(0.5), 2), Hs_p95=_r(hs.quantile(0.95), 2), Hs_p99=_r(hs.quantile(0.99), 2),
                       Hs_max=_r(hs.max(), 2), service_limit_Hs=LIMITS["service_Hs_m"], windows=out),
                  v, f"Median significant wave height is {hs.quantile(0.5):.1f} m and the 99th percentile {hs.quantile(0.99):.1f} m (max {hs.max():.1f} m). "
                     f"A {win} h window with Hs under {LIMITS['service_Hs_m']} m is open {key['annual'] * 100:.1f}% of hours over the year and {f * 100:.1f}% in the best three months (month {key['best_month']}).",
                  "Budget weather standby days in the campaign cost, size the work for Hs 3 m or more with a DP vessel, or shorten the swap procedure below 72 h.",
                  [SRC_WAVE])


# ------------------------------------------------------------------ C10 economics of real wind
_BASE_CACHE: dict = {}


def _base_case():
    if not _BASE_CACHE:
        from . import capex_model as cm
        f0 = P.served_fraction(cm.simulate_cf(cm.wind_mean[1]), SIM["overbuild"], SIM["storage_h"])
        _BASE_CACHE.update(f0=f0, s0=cm.subsea(1, SIM["overbuild"], SIM["storage_h"], f0), terr=cm.terrestrial(1))
    return _BASE_CACHE


def c10_wind_economics(d: SiteData) -> Result:
    """Cost per sold GPU-hour using the capex model with this site's real wind instead of the synthetic series."""
    from . import capex_model as cm
    hub, _ = _hub_wind(d)
    cf = P.capacity_factor(hub)
    b = _base_case()
    f_same = P.served_fraction(cf, SIM["overbuild"], SIM["storage_h"])
    s_same = cm.subsea(1, SIM["overbuild"], SIM["storage_h"], f_same)
    best = None
    for o in (1.0, 1.25, 1.5, 2.0, 2.5):
        for h in (0, 4, 12, 24):
            f = P.served_fraction(cf, o, h)
            sc = cm.subsea(1, o, h, f)
            if best is None or sc["per_hr"] < best[3]["per_hr"]:
                best = (o, h, f, sc)
    o, h, f, sc = best
    chg = s_same["per_hr"] / b["s0"]["per_hr"] - 1
    chg_best = sc["per_hr"] / b["s0"]["per_hr"] - 1
    terr = b["terr"]["per_hr"]
    v = "supported" if abs(chg) <= 0.05 else ("marginal" if abs(chg) <= 0.10 else "contradicted")
    return Result("C10", "Cost per GPU-hour with real wind", f"Base case: ${b['s0']['per_hr']:.2f} per sold GPU-hour (synthetic wind, 2x overbuild, 12 h storage), terrestrial ${terr:.2f}",
                  dict(base_per_hr=_r(b["s0"]["per_hr"], 2), base_served=_r(b["f0"], 3), real_wind_same_config_per_hr=_r(s_same["per_hr"], 2), real_wind_served=_r(f_same, 3),
                       cost_change_pct=_r(chg * 100, 1), best_config=dict(overbuild=o, storage_h=h, served=_r(f, 3), per_hr=_r(sc["per_hr"], 2), capex_M=_r(sc["capex"], 0)),
                       best_vs_base_pct=_r(chg_best * 100, 1), terrestrial_per_hr=_r(terr, 2), best_premium_vs_terrestrial_pct=_r((sc["per_hr"] / terr - 1) * 100, 0)),
                  v, f"With this site's real wind the base design costs ${s_same['per_hr']:.2f} per sold GPU-hour ({chg * 100:+.0f}% against the capex base case ${b['s0']['per_hr']:.2f}) because it serves {f_same * 100:.0f}% instead of {b['f0'] * 100:.0f}%. "
                     f"Re-optimised ({o}x overbuild, {h} h storage) it reaches ${sc['per_hr']:.2f}, {chg_best * 100:+.0f}% against base and {(sc['per_hr'] / terr - 1) * 100:+.0f}% against terrestrial (${terr:.2f}). Everything else in the capex model is unchanged.",
                  "Feed each site's wind series into capex_model.py and re-pick overbuild and storage; wind capex and storage are the levers that move.",
                  [SRC_POWER])


def _direction(cid: str, r: Result) -> str:
    o = r.observed
    try:
        if cid == "C1":
            return "better" if o["p50"] < SIM["sea_T_C"] else "worse"
        if cid == "C2":
            return "worse" if o["p50"] < SIM["current_default"] else "better"
        if cid == "C4":
            return "worse" if o["v_p50"]["ratio_sim_over_physics"] > 1 else "better"
        if cid in ("C5", "C6", "C9"):
            return "neutral" if r.verdict == "supported" else "worse"
        if cid == "C7":
            return "better" if o["mean_hub_ms"] > SIM["wind_mean_base"] else "worse"
        if cid == "C8":
            return "better" if o["difference"] > 0 else "worse"
        if cid == "C10":
            return "better" if o["cost_change_pct"] < 0 else "worse"
    except (KeyError, TypeError):
        pass
    return "neutral"


def _wrap(fn):
    cid = fn.__name__.split("_")[0].upper()

    def inner(d, *a, **k):
        r = fn(d, *a, **k)
        r.direction = _direction(cid, r) if r.verdict != "supported" or cid in ("C1", "C2", "C4") else "neutral"
        return r
    inner.__name__, inner.__doc__ = fn.__name__, fn.__doc__
    return inner


ALL = [_wrap(f) for f in [c1_sea_temperature, c2_currents, c3_properties, c4_heat_transfer, c5_rejection_headroom, c6_plume,
                          c7_wind_resource, c8_served_fraction, c9_service_windows, c10_wind_economics]]
BY_ID = {f.__name__.split("_")[0].upper(): f for f in ALL}


def run_site(d: SiteData, only: list[str] | None = None) -> list[Result]:
    out = []
    for fn in ALL:
        cid = fn.__name__.split("_")[0].upper()
        if only and cid not in only:
            continue
        try:
            out.append(fn(d))
        except MissingData as e:
            out.append(Result(cid, fn.__name__, "", {"missing_dataset": str(e)}, "untestable", f"Dataset not available offline: {e}"))
    return out
