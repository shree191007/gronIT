from __future__ import annotations
import json, datetime as dt
import numpy as np
from .config import SITES, OUT_DIR, SIM
from .data import SiteData
from . import checks

def icon(r: dict) -> str:
    v, dr = r["verdict"], r.get("direction", "neutral")
    if v == "supported": return "OK"
    if v == "untestable": return "n/a"
    if v == "marginal": return "WATCH, better" if dr == "better" else "WATCH"
    return "OFF, better than assumed" if dr == "better" else "FAIL"


def run(sites=None, only=None, offline=True) -> dict:
    res = {}
    for key in sites or SITES:
        d = SiteData(SITES[key], offline=offline)
        res[key] = [r.to_dict() for r in checks.run_site(d, only)]
    return dict(generated=dt.datetime.utcnow().isoformat(timespec="seconds") + "Z", sim_assumptions=SIM,
                sites={k: SITES[k].__dict__ for k in res}, results=res)


def presets(report: dict) -> dict:
    """Per-site slider presets for the simulator page, taken from the real distributions."""
    out = {}
    for k, rs in report["results"].items():
        by = {r["id"]: r for r in rs}
        c1, c2 = by.get("C1"), by.get("C2")
        if not (c1 and c2) or c1["verdict"] == "untestable" or c2["verdict"] == "untestable":
            continue
        out[k] = dict(name=SITES[k].name, sea_T_C=c1["observed"]["p50"], current_p5=c2["observed"]["p5"],
                      current_p50=c2["observed"]["p50"], current_p95=c2["observed"]["p95"])
    return out


def to_markdown(report: dict) -> str:
    L = [f"# Neocloud assumption tests", "", f"Generated {report['generated']}. Verdicts: OK = data supports the assumption, WATCH = marginal, FAIL = data contradicts it in the unfavourable direction, OFF (better) = data differs in our favour.", ""]
    keys = list(report["results"])
    ids = [r["id"] for r in report["results"][keys[0]]]
    L += ["| Check | " + " | ".join(SITES[k].name for k in keys) + " |", "|---|" + "---|" * len(keys)]
    for i, cid in enumerate(ids):
        title = report["results"][keys[0]][i]["title"]
        L.append(f"| {cid} {title} | " + " | ".join(icon(report["results"][k][i]) for k in keys) + " |")
    for k in keys:
        L += ["", f"## {SITES[k].name} ({SITES[k].lat}, {SITES[k].lon})", ""]
        for r in report["results"][k]:
            L += [f"**{r['id']} {r['title']}: {icon(r)}**  ", f"Assumed: {r['assumption']}  ", r["finding"] + "  "]
            if r["sim_change"]:
                L.append(f"Change: {r['sim_change']}")
            L.append("")
    L += ["## Limits of this test", "",
          "- Currents are HYCOM model output (not measurements) for four months of 2023 only; treat site rankings as indicative and validate with moorings or glider data before design freeze.",
          "- Wind is reanalysis (MERRA-2 10 m and 50 m, extrapolated to 150 m; ERA5 agrees within about 3%). Reanalyses smooth gusts, and storm shutdowns, icing and platform-motion downtime are not modelled.",
          "- Wave data begin in April 2021 (about 3.5 years), so extremes are under-sampled.",
          "- Hull U uses assumed inner-side h (1,500 W/m2K) and fouling (3e-4 m2K/W); natural-convection h is good to roughly +-30%. Fins are credited at 85% efficiency.",
          "- Design limits for plume warming (0.5 K) and service sea state (Hs 2.5 m, 72 h) are our own placeholders and drive those verdicts.",
          "- Not testable with open data: GPU rack price and power, satellite link capacity and cost, floating-wind capex, EM and ecological thresholds.", ""]
    L += ["## Data sources", ""] + sorted({s for rs in report["results"].values() for r in rs for s in r.get("sources", [])})
    return "\n".join(L)


def write(report: dict):
    OUT_DIR.mkdir(exist_ok=True, parents=True)
    (OUT_DIR / "report.json").write_text(json.dumps(report, indent=1, default=float))
    (OUT_DIR / "report.md").write_text(to_markdown(report))
    (OUT_DIR / "site_presets.json").write_text(json.dumps(presets(report), indent=1))
