from __future__ import annotations
import sys, time
from concurrent.futures import ThreadPoolExecutor, as_completed
from .config import SITES, SIM
from .data import SiteData


def fetch_site(key: str, what=("argo", "wind", "waves", "uv")) -> str:
    d = SiteData(SITES[key])
    t0 = time.time()
    steps = {"argo": lambda: d.argo, "wind": lambda: d.wind, "waves": lambda: d.waves, "uv": lambda: d.uv}
    for w in what:
        try:
            steps[w]()
            print(f"[{key}] {w} ok  ({time.time() - t0:.0f}s)", flush=True)
        except Exception as e:                               # keep going, report at the end
            print(f"[{key}] {w} FAILED: {e}", flush=True)
    return key


def fetch_all(sites=None, workers=4, what=("argo", "wind", "waves", "uv")):
    keys = sites or list(SITES)
    with ThreadPoolExecutor(max_workers=workers) as ex:
        futs = [ex.submit(fetch_site, k, what) for k in keys]
        for f in as_completed(futs):
            f.result()


if __name__ == "__main__":
    fetch_all(sys.argv[1:] or None)
