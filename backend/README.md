# Neocloud assumption tester

A Python backend that pulls real-world ocean and weather data and tests the assumptions behind the
pod simulator and the capex model. Each check returns a verdict (supported, marginal, contradicted)
with the numbers behind it, and says what to change in the simulator.

## Quick start
```
pip install -r requirements.txt
python -m neocloud fetch            # downloads and caches data (about 15 minutes, needs internet)
python -m neocloud run              # runs all checks from the cache, writes out/report.md, report.json, site_presets.json
python -m neocloud serve            # API on http://localhost:8000/docs
pytest -q                           # offline unit tests
```
`data_cache/` ships with the downloaded data, so `run`, `serve` and `pytest` work offline.

## Data sources
| Quantity | Source | Notes |
|---|---|---|
| Wind at 10 m and 100 m, hourly 2015-2024 | ERA5 via Open-Meteo archive API | reanalysis; extrapolated to 150 m with the shear exponent fitted from the same data |
| Wind cross-check | NASA POWER daily WS50M (MERRA-2) | independent reanalysis |
| Significant wave height and period | ERA5-wave via Open-Meteo marine API | reanalysis |
| Current u, v at 150 m, 3-hourly | HYCOM GLBy0.08 expt 93.0 via THREDDS NCSS | an assimilating model, not measurements; Jan/Apr/Jul/Oct 2023 |
| Temperature and salinity near 150 dbar | Argo floats via Ifremer ERDDAP | in-situ, QC flag 1, 2019-2024 |
| Seawater properties | TEOS-10 (gsw) and Sharqawy et al. 2010 | |
| Hull heat transfer | Churchill-Bernstein and Churchill-Chu correlations | inner-side h and fouling resistance are assumed values |

## Checks
C1 sea temperature, C2 current speed and slack water, C3 seawater properties, C4 hull U vs the sim's U,
C5 can the hull reject 0.96 MW, C6 bulk plume warming, C7 wind resource, C8 wind gaps and storage
(real hourly wind vs the synthetic wind in the capex model), C9 sea state for pod swaps.

Assumptions tagged [A] in `neocloud/config.py` are our own (fouling, inner-side h, service sea-state
limit, plume limit) and drive some verdicts; thresholds are in `THRESH`. Edit and rerun.

## API
`GET /sites`, `/assumptions`, `/check/{C1..C9}?site=drake`, `/report?site=drake&refresh=false`, `/presets`

## Not testable with open data (needs a source or a quote)
GPU rack price and 120 kW per rack, satellite link capacity and cost, floating-wind capex, EM and
ecological thresholds, GPU attrition in sealed pods.
