"""FastAPI service. Run:  uvicorn neocloud.api:app --reload"""
from __future__ import annotations
import json
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from . import report as rep, checks
from .config import SITES, SIM, HEAT, LIMITS, THRESH, OUT_DIR
from .data import SiteData

app = FastAPI(title="Neocloud assumption tester", version="0.1.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["GET", "POST"], allow_headers=["*"])
_cache: dict = {}


def _site(key: str):
    if key not in SITES:
        raise HTTPException(404, f"unknown site {key}; choose from {list(SITES)}")
    return SITES[key]


@app.get("/health")
def health():
    return {"ok": True}


@app.get("/sites")
def sites():
    return {k: s.__dict__ for k, s in SITES.items()}


@app.get("/assumptions")
def assumptions():
    return dict(simulator=SIM, heat_transfer_inputs=HEAT, design_limits=LIMITS, verdict_thresholds=THRESH,
                checks={cid: (fn.__doc__ or fn.__name__) for cid, fn in checks.BY_ID.items()})


@app.get("/check/{check_id}")
def one_check(check_id: str, site: str, offline: bool = True):
    _site(site)
    cid = check_id.upper()
    if cid not in checks.BY_ID:
        raise HTTPException(404, f"unknown check {cid}")
    key = (site, cid, offline)
    if key not in _cache:
        _cache[key] = checks.BY_ID[cid](SiteData(SITES[site], offline=offline)).to_dict()
    return _cache[key]


@app.get("/report")
def report(site: str | None = None, offline: bool = True, refresh: bool = False):
    """Full report from out/report.json, or recomputed (refresh=true / missing)."""
    path = OUT_DIR / "report.json"
    if refresh or not path.exists():
        r = rep.run([site] if site else None, offline=offline)
        rep.write(r)
    r = json.loads(path.read_text())
    if site:
        _site(site)
        r = {**r, "results": {site: r["results"][site]}, "sites": {site: r["sites"][site]}}
    return r


@app.get("/presets")
def presets():
    path = OUT_DIR / "site_presets.json"
    if not path.exists():
        raise HTTPException(404, "run the report first")
    return json.loads(path.read_text())
