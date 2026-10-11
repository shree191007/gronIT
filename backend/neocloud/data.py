from __future__ import annotations
from functools import cached_property
import numpy as np
import pandas as pd
from . import sources
from .config import Site, YEARS, HYCOM_MONTHS, SIM, WAVE_YEARS
from .cache import MissingData, DailyLimit


class SiteData:
    """Lazy, cached bundle of the real datasets for one site."""

    def __init__(self, site: Site, years=None, hycom_months=None, offline=False):
        self.site, self.offline = site, offline
        self.years = list(years or YEARS)
        self.hycom_months = list(hycom_months or HYCOM_MONTHS)

    Z_LOW, Z_HIGH = 10.0, 50.0

    @cached_property
    def wind(self) -> pd.DataFrame:
        """Primary wind record: MERRA-2 hourly 10 m and 50 m (v10, v50) for the full period."""
        frames = []
        for y in self.years:
            try:
                frames.append(sources.power_hourly_wind(self.site, y, self.offline))
            except (MissingData, DailyLimit):
                continue
        if not frames:
            raise MissingData(f"power_hourly_{self.site.key}")
        df = pd.concat(frames, ignore_index=True).dropna().sort_values("time").reset_index(drop=True)
        return df

    @cached_property
    def wind_era5(self) -> pd.DataFrame:
        """ERA5 10 m / 100 m wind for whichever years are in the cache (cross-check only)."""
        frames = []
        for y in self.years:
            try:
                frames.append(sources.era5_wind(self.site, y, offline=True))
            except MissingData:
                continue
        if not frames:
            raise MissingData(f"wind_{self.site.key}")
        return pd.concat(frames, ignore_index=True).dropna().sort_values("time").reset_index(drop=True)

    @cached_property
    def waves(self) -> pd.DataFrame:
        frames = []
        for y in WAVE_YEARS:
            try:
                frames.append(sources.era5_waves(self.site, y, self.offline))
            except (MissingData, DailyLimit):
                continue
        if not frames:
            raise MissingData(f"waves_{self.site.key}")
        df = pd.concat(frames, ignore_index=True)
        return df.dropna(subset=["wave_height"]).sort_values("time").reset_index(drop=True)

    @cached_property
    def wind50_power(self) -> pd.DataFrame:
        return sources.power_wind50(self.site, self.years[0], self.years[-1], self.offline)

    @cached_property
    def uv(self) -> pd.DataFrame:
        df = pd.concat([sources.hycom_uv(self.site, y, m, SIM["depth_m"], self.offline) for y, m in self.hycom_months],
                       ignore_index=True)
        df = df.dropna().sort_values("time").reset_index(drop=True)
        df["speed"] = np.hypot(df.u, df.v)
        return df

    @cached_property
    def argo(self) -> pd.DataFrame:
        """One row per profile (mean of the samples within +-5 dbar)."""
        raw = sources.argo_profile_points(self.site, SIM["depth_m"], offline=self.offline)
        raw = raw.dropna(subset=["temp"])
        g = raw.groupby(["platform_number", "time"], as_index=False).agg(
            temp=("temp", "mean"), psal=("psal", "mean"), lat=("latitude", "mean"), lon=("longitude", "mean"))
        return g
