import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import capex_model as cm

B = 1
_cf_cache = {}
def get_f(mean_v, over, h):
    key = (mean_v, over, h)
    if key not in _cf_cache:
        cf = cm.simulate_cf(mean_v)
        _cf_cache[key] = cm.served_fraction(cf, over, h)
    return _cf_cache[key]

terr = cm.terrestrial(B)

def metrics(over=None, mean_v=None, wacc=None, cap=None, thr=1.0, overbuild=2.0, hours=12):
    over = over or {}
    saved = {}
    for k, v in over.items():
        saved[k] = getattr(cm, k)
        t = list(saved[k]); t[B] = v
        setattr(cm, k, tuple(t))
    orig_crf, orig_pue = cm.crf, cm.pue_sub
    if wacc is not None:
        cm.crf = lambda n, r=wacc: r*(1+r)**n/((1+r)**n-1)
    if cap is not None:
        cm.pue_sub = orig_pue * cap
    mv = mean_v or cm.wind_mean[B]
    f = get_f(mv, overbuild, hours)
    s = cm.subsea(B, overbuild, hours, f*thr)
    avg_load = cm.IT_MW * cm.pue_sub
    wind_MW = overbuild * avg_load
    wind = wind_MW*1000*cm.wind_kw[B]*cm.wind_uplift[B]/1e6
    stor = avg_load*hours*1000*cm.store_kwh[B]/1e6
    ann_power = (wind*cm.crf(cm.LIFE['wind']) + stor*cm.crf(cm.LIFE['storage'])
                 + wind_MW*1000*cm.wind_om_kw_yr[B]/1e6)
    kwh = avg_load*1000*f*8760
    out = (s["capex"], s["per_hr"], ann_power*1e6/kwh, f)
    cm.crf, cm.pue_sub = orig_crf, orig_pue
    for k, v in saved.items():
        setattr(cm, k, v)
    return out

def show(name, **kw):
    capex, hr, pk, f = metrics(**kw)
    print(f"{name:<62} {pk:5.2f} $/kWh | ${hr:5.2f}/hr ({(hr/terr['per_hr']-1)*100:+4.0f}%) | capex ${capex:5.0f}M | uptime {f*100:4.1f}%")

print(f"Terrestrial ${terr['per_hr']:.2f}/hr\n")
show("Base")
show("Financing: WACC 7% (concessional/green finance)", wacc=0.07)
show("Financing: WACC 5%", wacc=0.05)
show("Wind at $4,000/kW, no remote uplift (learning curve)", over={"wind_kw": 4000, "wind_uplift": 1.0})
show("Wind integrated on shared hull (uplift 1.15, platform $20M)", over={"wind_uplift": 1.15, "platform_M": 20})
show("Better site: mean hub wind 12 m/s", mean_v=12.0)
show("Cheaper storage $250/kWh", over={"store_kwh": 250})
show("Power-capped GPUs: 75% power for 90% throughput [A]", cap=0.75, thr=0.90)
show("Power-capped GPUs: 65% power for 85% throughput [A]", cap=0.65, thr=0.85)
show("Wind O&M halved ($125/kW-yr)", over={"wind_om_kw_yr": 125})

print("\nCombined stacks")
show("Finance 7% + wind $4,000/kW + shared hull + cap 75%",
     wacc=0.07, over={"wind_kw": 4000, "wind_uplift": 1.15, "platform_M": 20}, cap=0.75, thr=0.90)
show("...plus 12 m/s site + $250/kWh storage",
     wacc=0.07, over={"wind_kw": 4000, "wind_uplift": 1.15, "platform_M": 20, "store_kwh": 250},
     cap=0.75, thr=0.90, mean_v=12.0)

print("\nOverbuild/storage re-optimised under the combined stack (12 m/s site)")
best = None
for o in [1.25, 1.5, 2.0, 2.5]:
    for h in [0, 6, 12, 24]:
        capex, hr, pk, f = metrics(wacc=0.07, over={"wind_kw": 4000, "wind_uplift": 1.15, "platform_M": 20, "store_kwh": 250},
                                   cap=0.75, thr=0.90, mean_v=12.0, overbuild=o, hours=h)
        if best is None or hr < best[0]:
            best = (hr, o, h, pk, f, capex)
hr, o, h, pk, f, capex = best
print(f"best: overbuild {o}x, storage {h}h -> ${hr:.2f}/hr ({(hr/terr['per_hr']-1)*100:+.0f}%), {pk:.2f} $/kWh, uptime {f*100:.1f}%, capex ${capex:.0f}M")
