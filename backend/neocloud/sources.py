"""Thin, cached clients for the public datasets used to test assumptions.

Wind and waves : Open-Meteo archive/marine APIs (ECMWF ERA5 / ERA5-wave reanalysis)
Wind cross-check: NASA POWER (MERRA-2 reanalysis), daily 50 m wind
Currents       : HYCOM global analysis GLBy0.08 expt 93.0 via THREDDS NetCDF Subset Service (model, not observation)
Temperature    : Argo floats via the Ifremer ERDDAP (in-situ observations, delayed-mode QC where available)
"""
from __future__ import annotations
import io
import numpy as np
import pandas as pd
from .cache import cached_frame, http_get
from .config import Site, ARGO_YEARS

OM_ARCHIVE = "https://archive-api.open-meteo.com/v1/archive"
OM_MARINE = "https://marine-api.open-meteo.com/v1/marine"
POWER_DAILY = "https://power.larc.nasa.gov/api/temporal/daily/point"
HYCOM_UV = "https://tds.hycom.org/thredds/ncss/GLBy0.08/expt_93.0/uv3z"
ARGO = "https://erddap.ifremer.fr/erddap/tabledap/ArgoFloats.csv"


def _om_frame(js: dict) -> pd.DataFrame:
    h = js["hourly"]
    df = pd.DataFrame(h)
    df["time"] = pd.to_datetime(df["time"])
    return df


def era5_wind(site: Site, year: int, offline=False) -> pd.DataFrame:
    def go():
        r = http_get(OM_ARCHIVE, dict(latitude=site.lat, longitude=site.lon, start_date=f"{year}-01-01",
                                      end_date=f"{year}-12-31", hourly="wind_speed_100m,wind_speed_10m",
                                      wind_speed_unit="ms", models="era5", timezone="GMT"))
        return _om_frame(r.json())
    return cached_frame(f"wind_{site.key}_{year}", go, offline)


def era5_waves(site: Site, year: int, offline=False) -> pd.DataFrame:
    def go():
        r = http_get(OM_MARINE, dict(latitude=site.lat, longitude=site.lon, start_date=f"{year}-01-01",
                                     end_date=f"{year}-12-31", hourly="wave_height", timezone="GMT"))
        return _om_frame(r.json())
    return cached_frame(f"waves_{site.key}_{year}", go, offline)


POWER_HOURLY = "https://power.larc.nasa.gov/api/temporal/hourly/point"


def power_hourly_wind(site: Site, year: int, offline=False) -> pd.DataFrame:
    """MERRA-2 hourly wind at 10 m and 50 m (m/s), UTC."""
    def go():
        r = http_get(POWER_HOURLY, dict(parameters="WS10M,WS50M", community="RE", longitude=site.lon, latitude=site.lat,
                                        start=f"{year}0101", end=f"{year}1231", format="JSON", **{"time-standard": "UTC"}))
        p = r.json()["properties"]["parameter"]
        df = pd.DataFrame({"time": pd.to_datetime(list(p["WS10M"].keys()), format="%Y%m%d%H"),
                           "v10": list(p["WS10M"].values()), "v50": list(p["WS50M"].values())})
        df[["v10", "v50"]] = df[["v10", "v50"]].where(df[["v10", "v50"]] > -900)
        return df
    return cached_frame(f"power_hourly_{site.key}_{year}", go, offline)


def power_wind50(site: Site, y0: int, y1: int, offline=False) -> pd.DataFrame:
    def go():
        r = http_get(POWER_DAILY, dict(parameters="WS50M", community="RE", longitude=site.lon, latitude=site.lat,
                                       start=f"{y0}0101", end=f"{y1}1231", format="JSON"))
        d = r.json()["properties"]["parameter"]["WS50M"]
        df = pd.DataFrame({"time": pd.to_datetime(list(d.keys()), format="%Y%m%d"), "ws50": list(d.values())})
        df.loc[df.ws50 < -900, "ws50"] = np.nan
        return df
    return cached_frame(f"power50_{site.key}_{y0}_{y1}", go, offline)


def hycom_uv(site: Site, year: int, month: int, depth_m: float, offline=False) -> pd.DataFrame:
    """3-hourly u/v (m/s) at one depth for one calendar month. The THREDDS server returns the raw
    int16 values (scale_factor 0.001) in the CSV, so rescale when values are implausibly large."""
    start = pd.Timestamp(year=year, month=month, day=1)
    end = (start + pd.offsets.MonthBegin(1)) - pd.Timedelta(hours=3)

    def go():
        r = http_get(HYCOM_UV, dict(var=["water_u", "water_v"], latitude=site.lat, longitude=site.lon360,
                                    time_start=start.strftime("%Y-%m-%dT%H:%M:%SZ"),
                                    time_end=end.strftime("%Y-%m-%dT%H:%M:%SZ"),
                                    vertCoord=depth_m, accept="csv"), timeout=600)
        df = pd.read_csv(io.StringIO(r.text))
        df.columns = ["time", "lat", "lon", "depth", "u", "v"]
        df["time"] = pd.to_datetime(df["time"], utc=True).dt.tz_localize(None)
        for c in ("u", "v"):
            df.loc[df[c] <= -29000, c] = np.nan
        if np.nanmax(np.abs(df[["u", "v"]].to_numpy())) > 20:     # raw units (mm/s)
            df[["u", "v"]] = df[["u", "v"]] * 0.001
        return df[["time", "u", "v"]]
    return cached_frame(f"hycom_{site.key}_{year}{month:02d}_{int(depth_m)}", go, offline)


def argo_profile_points(site: Site, depth_dbar=150.0, half_dlat=2.5, half_dlon=4.0, offline=False) -> pd.DataFrame:
    """Argo temperature/salinity within +-5 dbar of depth in a box around the site, QC flag 1 only."""
    def go():
        url = (f"{ARGO}?platform_number,time,latitude,longitude,pres,temp,psal,data_mode"
               f"&latitude>={site.lat - half_dlat}&latitude<={site.lat + half_dlat}"
               f"&longitude>={site.lon - half_dlon}&longitude<={site.lon + half_dlon}"
               f"&pres>={depth_dbar - 5}&pres<={depth_dbar + 5}"
               f"&time>={ARGO_YEARS[0]}-01-01T00:00:00Z&time<={ARGO_YEARS[1]}-12-31T00:00:00Z"
               f'&temp_qc="1"&psal_qc="1"')
        r = http_get(url, timeout=600)
        df = pd.read_csv(io.StringIO(r.text), skiprows=[1])
        df["time"] = pd.to_datetime(df["time"], utc=True).dt.tz_localize(None)
        return df
    return cached_frame(f"argo_{site.key}_{int(depth_dbar)}", go, offline)
