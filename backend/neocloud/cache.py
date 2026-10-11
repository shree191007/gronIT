from __future__ import annotations
import io, time
from typing import Callable
import pandas as pd
import requests
from .config import CACHE_DIR


class MissingData(RuntimeError):
    """Raised in offline mode when a dataset is not in the local cache."""


class DailyLimit(RuntimeError):
    """The provider's free daily quota is used up; retrying today is pointless."""


def http_get(url: str, params: dict | None = None, tries: int = 6, timeout: int = 300) -> requests.Response:
    last = None
    for i in range(tries):
        try:
            r = requests.get(url, params=params, timeout=timeout)
        except requests.RequestException as e:      # network hiccup
            last = e
            time.sleep(min(60, 2 ** i))
            continue
        if r.status_code == 429 and "Daily" in r.text:
            raise DailyLimit(f"daily request limit reached at {url.split('?')[0]}")
        if r.status_code in (429, 500, 502, 503, 504):
            last = RuntimeError(f"{r.status_code} from {url}: {r.text[:120]}")
            time.sleep(min(90, 4 * 2 ** i))
            continue
        r.raise_for_status()
        return r
    raise RuntimeError(f"giving up on {url}: {last}")


def cached_frame(key: str, producer: Callable[[], pd.DataFrame], offline: bool = False) -> pd.DataFrame:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    path = CACHE_DIR / f"{key}.csv.gz"
    if path.exists():
        df = pd.read_csv(path)
        if "time" in df.columns:
            df["time"] = pd.to_datetime(df["time"], utc=True).dt.tz_localize(None)
        return df
    if offline:
        raise MissingData(key)
    df = producer()
    df.to_csv(path, index=False, compression="gzip")
    return df
