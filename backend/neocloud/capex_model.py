"""
Southern Ocean AI compute node: capex and cost-per-GPU-hour model (10 MW IT pilot node).
[S] = sourced benchmark, [A] = our assumption (to be replaced with real quotes/data).
Case index: 0 = optimistic, 1 = base, 2 = pessimistic.
"""
import numpy as np, math
from statistics import NormalDist

IT_MW = 10.0
CASES = ["optimistic", "base", "pessimistic"]

# ---------------- parameters (opt, base, pess) ----------------
rack_cost   = (3.1, 3.5, 3.9)        # $M per GB200-class NVL72 rack [S: ~3.1 bare / 3.9 all-in]
rack_kw     = 120.0                  # kW per rack [S]
spare_frac  = (0.05, 0.10, 0.15)     # fail-in-place spare IT [A]
marine_per_MW_ref = 9.3              # $M/MW HiCloud Shanghai: 1.6B yuan / 24 MW [S], shallow, facility-only(?)
marine_uplift = (1.2, 1.8, 3.0)      # Southern Ocean ruggedisation / depth uplift [A]
platform_M  = (20, 40, 80)           # compute platform hull, dynamic umbilicals, deep mooring [A]
wind_kw     = (4000, 7349, 10000)    # $/kW floating wind [S: WoodMac ~4k target, NREL 7,349, Japan up to 10k]
wind_uplift = (1.0, 1.3, 1.8)        # remote Southern Ocean install/logistics [A]
store_kwh   = (250, 400, 600)        # $/kWh installed marine-grade storage [A]
connect_M   = (2, 3, 6)              # satellite terminals, comms [A]
eco_M       = (8, 15, 30)            # baseline surveys, EIA, monitoring, mitigation design [A]
install_M   = (6, 15, 40)            # vessel campaign for pods/umbilicals [A; ice-class AHTS ~$100k/day S]
contingency = (0.15, 0.30, 0.45)     # on non-IT capex [A]
wind_mean   = (12.0, 10.5, 9.0)      # mean hub-height wind m/s [A - replace with ERA5]
pue_sub     = 1.10                   # [A]

# opex
wind_om_kw_yr = (150, 250, 400)      # $/kW-yr [A]
campaign_M    = (4, 8, 15)           # annual service/recovery campaign [A]
insure        = (0.01, 0.015, 0.025) # of non-IT capex per year [A]
staff_sat_M   = (2, 3, 5)            # [A]

# finance
WACC = 0.10
LIFE = dict(it=5, marine=12, platform=15, wind=25, storage=12, other=12, facility=15)
def crf(n, r=WACC): return r*(1+r)**n/((1+r)**n-1)

# terrestrial baseline
terr_facility_per_MW = (15.0, 20.0, 25.0)  # $M/MW AI-optimised, incl. liquid cooling [S: 15-25]
terr_pue = 1.2                              # [A]
terr_energy = (0.05, 0.07, 0.10)            # $/kWh [S band 0.05-0.10]
terr_opex_per_MW = 0.5                      # $M/MW-yr [A]
terr_avail = 0.99
UTIL = 0.85                                 # share of delivered hours actually sold, both [A]

gpus = IT_MW*1000/(rack_kw/72)
racks = IT_MW*1000/rack_kw

# ---------------- synthetic wind proxy ----------------
def simulate_cf(mean_v, years=20, k=2.2, rho=0.985, seed=11):
    rng = np.random.default_rng(seed)
    n = years*8760
    z = np.empty(n); z[0] = rng.normal()
    eps = rng.normal(size=n)*math.sqrt(1-rho**2)
    for t in range(1, n):
        z[t] = rho*z[t-1] + eps[t]
    u = np.array([NormalDist().cdf(x) for x in z])
    lam = mean_v/math.gamma(1+1/k)
    v = lam*(-np.log(1-np.clip(u, 1e-9, 1-1e-9)))**(1/k)
    cin, rated, cout = 3.0, 10.6, 25.0
    cf = np.where(v < cin, 0.0,
         np.where(v < rated, ((v**3-cin**3)/(rated**3-cin**3)),
         np.where(v < cout, 1.0, 0.0)))
    return cf*0.90   # wake/electrical/availability losses [A]

def served_fraction(cf, overbuild, store_h, eta=0.95):
    soc, cap, tot = 0.0, store_h, 0.0
    for c in cf:
        w = overbuild*c
        if w >= 1.0:
            tot += 1.0
            soc = min(cap, soc + (w-1.0)*eta)
        else:
            d = min(1.0-w, soc)
            soc -= d
            tot += w + d*eta
    return tot/len(cf)

OVER = [1.5, 2.0, 2.5, 3.0, 4.0]
STOR = [0, 4, 12, 24]

def subsea(case, overbuild, store_h, frac):
    i = case
    avg_load = IT_MW*pue_sub
    it = racks*rack_cost[i]*(1+spare_frac[i])
    marine = IT_MW*marine_per_MW_ref*marine_uplift[i]
    plat = platform_M[i]
    wind_MW = overbuild*avg_load
    wind = wind_MW*1000*wind_kw[i]*wind_uplift[i]/1e6
    stor = avg_load*store_h*1000*store_kwh[i]/1e6
    other = connect_M[i]+eco_M[i]+install_M[i]
    nonit_pre = marine+plat+wind+stor+other
    cont = contingency[i]*nonit_pre
    nonit = nonit_pre+cont
    capex = it+nonit
    ann_cap = (it*crf(LIFE['it']) + marine*crf(LIFE['marine']) + plat*crf(LIFE['platform'])
               + wind*crf(LIFE['wind']) + stor*crf(LIFE['storage'])
               + (other+cont)*crf(LIFE['other']))
    opex = (wind_MW*1000*wind_om_kw_yr[i]/1e6 + campaign_M[i] + insure[i]*nonit + staff_sat_M[i])
    annual = ann_cap+opex
    sold_hrs = gpus*8760*frac*UTIL
    return dict(it=it, marine=marine, plat=plat, wind=wind, stor=stor, other=other, cont=cont,
                capex=capex, nonit=nonit, annual=annual, opex=opex, ann_cap=ann_cap,
                per_hr=annual*1e6/sold_hrs, wind_MW=wind_MW, frac=frac)

def terrestrial(case):
    i = case
    it = racks*rack_cost[i]
    fac = IT_MW*terr_facility_per_MW[i]
    energy = IT_MW*1000*terr_pue*8760*terr_energy[i]/1e6
    ann = it*crf(LIFE['it']) + fac*crf(LIFE['facility']) + energy + terr_opex_per_MW*IT_MW
    sold = gpus*8760*terr_avail*UTIL
    return dict(it=it, fac=fac, capex=it+fac, energy=energy, annual=ann,
                per_hr=ann*1e6/sold, gpu_share=it*crf(LIFE['it'])/ann)

if __name__ == "__main__":
    print(f"GPUs per 10 MW node: {gpus:,.0f}; racks: {racks:.1f}")
    for ci, cname in enumerate(CASES):
        t = terrestrial(ci)
        print(f"\n=== {cname.upper()} ===")
        print(f"TERRESTRIAL 10MW: capex ${t['capex']:.0f}M (IT {t['it']:.0f} + facility {t['fac']:.0f}); "
              f"annual ${t['annual']:.0f}M; ${t['per_hr']:.2f}/sold GPU-hr; GPU share of cost {t['gpu_share']*100:.0f}%; "
              f"energy ${t['energy']:.1f}M/yr = {t['energy']/t['annual']*100:.1f}% of annual cost")
        cf = simulate_cf(wind_mean[ci])
        print(f"synthetic wind: mean CF (after losses) = {cf.mean():.2f}")
        best = None
        rows = []
        for o in OVER:
            for h in STOR:
                f = served_fraction(cf, o, h)
                s = subsea(ci, o, h, f)
                rows.append((o, h, f, s))
                if best is None or s['per_hr'] < best[3]['per_hr']:
                    best = (o, h, f, s)
        print("overbuild x storage(h) -> delivered fraction | capex $M | $/sold GPU-hr")
        for o, h, f, s in rows:
            if h in (0, 12) or (o, h) == best[:2]:
                print(f"  {o:>3}x {h:>2}h -> {f*100:5.1f}% | {s['capex']:6.0f} | {s['per_hr']:.2f}")
        o, h, f, s = best
        print(f"BEST: overbuild {o}x, storage {h}h -> delivered {f*100:.1f}%, wind {s['wind_MW']:.0f} MW, "
              f"capex ${s['capex']:.0f}M (IT {s['it']:.0f}, marine {s['marine']:.0f}, platform {s['plat']:.0f}, "
              f"wind {s['wind']:.0f}, storage {s['stor']:.0f}, other {s['other']:.0f}, contingency {s['cont']:.0f}); "
              f"annual ${s['annual']:.0f}M (opex {s['opex']:.0f}); ${s['per_hr']:.2f}/sold GPU-hr; "
              f"premium vs terrestrial {(s['per_hr']/t['per_hr']-1)*100:.0f}%")
        # ecological safeguard share
        print(f"eco/monitoring line = ${eco_M[ci]}M = {eco_M[ci]/s['capex']*100:.1f}% of capex")
