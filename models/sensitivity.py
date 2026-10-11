import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import capex_model as cm

BASE = 1
cf = cm.simulate_cf(cm.wind_mean[BASE])
f_base = cm.served_fraction(cf, 2.0, 12)
terr = cm.terrestrial(BASE)

def run(over=None, frac=None, extra_energy_M=0.0):
    over = over or {}
    saved = {}
    for k, v in over.items():
        saved[k] = getattr(cm, k)
        t = list(saved[k])
        t[BASE] = v
        setattr(cm, k, tuple(t))
    s = cm.subsea(BASE, 2.0, 12, f_base if frac is None else frac)
    for k, v in saved.items():
        setattr(cm, k, v)
    annual = s["annual"] + extra_energy_M
    sold = cm.gpus * 8760 * (f_base if frac is None else frac) * cm.UTIL
    return s["capex"], annual * 1e6 / sold

rows = []
rows.append(("Base (Southern Ocean, off-grid wind)", *run()))
rows.append(("Marine uplift 1.0 (coastal-level build cost)", *run({"marine_uplift": 1.0})))
rows.append(("No deep-mooring platform premium", *run({"platform_M": 0})))
rows.append(("Contingency 15% instead of 30%", *run({"contingency": 0.15})))
rows.append(("Floating wind at $4,000/kW, no remote uplift", *run({"wind_kw": 4000, "wind_uplift": 1.0})))
rows.append(("Cheaper storage ($250/kWh)", *run({"store_kwh": 250})))
rows.append(("Free perfect power (no wind/storage, 100% uptime)",
             *run({"wind_kw": 0, "store_kwh": 0, "wind_om_kw_yr": 0}, frac=1.0)))
rows.append(("All levers optimistic at once (opt-case params, base wind)",
             *run({"marine_uplift": 1.2, "platform_M": 20, "contingency": 0.15, "wind_kw": 4000,
                   "wind_uplift": 1.0, "store_kwh": 250, "campaign_M": 4, "install_M": 6, "eco_M": 8})))
grid_energy = 10 * cm.pue_sub * 8760 * 0.07 / 1e6
rows.append(("Near-shore, grid/wind-farm fed, HiCloud-style (no own wind)",
             *run({"marine_uplift": 1.0, "platform_M": 10, "contingency": 0.15, "wind_kw": 0,
                   "store_kwh": 0, "wind_om_kw_yr": 0, "campaign_M": 3, "install_M": 5, "eco_M": 8},
                  frac=0.99, extra_energy_M=grid_energy)))

print(f"Terrestrial base: capex ${terr['capex']:.0f}M, ${terr['per_hr']:.2f}/sold GPU-hr")
print(f"Terrestrial cost if power were free: ${(terr['annual']-terr['energy'])*1e6/(cm.gpus*8760*cm.terr_avail*cm.UTIL):.2f}/hr "
      f"({terr['energy']/terr['annual']*100:.1f}% saving)")
print(f"Base delivered fraction (2.0x, 12h): {f_base*100:.1f}%\n")
for name, capex, hr in rows:
    print(f"{name:<68} capex ${capex:6.0f}M  ${hr:5.2f}/hr  vs terr {(hr/terr['per_hr']-1)*100:+5.0f}%")

# effective power cost, base
i = BASE
avg_load = cm.IT_MW * cm.pue_sub
wind_MW = 2.0 * avg_load
wind = wind_MW * 1000 * cm.wind_kw[i] * cm.wind_uplift[i] / 1e6
stor = avg_load * 12 * 1000 * cm.store_kwh[i] / 1e6
ann_power = wind*cm.crf(cm.LIFE['wind']) + stor*cm.crf(cm.LIFE['storage']) + wind_MW*1000*cm.wind_om_kw_yr[i]/1e6
kwh = avg_load*1000*f_base*8760
print(f"\nBase effective power system cost: ${ann_power:.1f}M/yr over {kwh/1e6:.1f} GWh = ${ann_power*1e6/kwh:.2f}/kWh (terrestrial $0.05-0.10)")

# idle-GPU cost
it_ann = cm.racks*cm.rack_cost[i]*(1+cm.spare_frac[i])*cm.crf(cm.LIFE['it'])
print(f"Annualised GPU capital (base subsea): ${it_ann:.0f}M/yr; idle share from wind gaps ({(1-f_base)*100:.0f}%) = ${it_ann*(1-f_base):.0f}M/yr")

# data-light check
print(f"\n1 PB over 1 Gbps: {8e15/1e9/86400:.0f} days")
print(f"Text inference at ~4 KB round trip per request over 1 Gbps: {1e9/8/4000:,.0f} requests/s")
