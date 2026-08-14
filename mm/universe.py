"""Index constituent lists, fetched from NSE archives and cached locally."""

import io
import json
import time
from pathlib import Path

import pandas as pd
import requests

CACHE_DIR = Path(__file__).resolve().parent.parent / ".cache"
CACHE_TTL = 7 * 86400  # constituents change rarely

INDEX_CSV = {
    "nifty50": "https://archives.nseindia.com/content/indices/ind_nifty50list.csv",
    "nifty100": "https://archives.nseindia.com/content/indices/ind_nifty100list.csv",
    "nifty200": "https://archives.nseindia.com/content/indices/ind_nifty200list.csv",
    "nifty500": "https://archives.nseindia.com/content/indices/ind_nifty500list.csv",
}

HEADERS = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"}


def get_universe(name: str) -> list[dict]:
    """Return [{symbol, name, industry}] for the given index."""
    CACHE_DIR.mkdir(exist_ok=True)
    cache = CACHE_DIR / f"universe_{name}.json"
    if cache.exists() and time.time() - cache.stat().st_mtime < CACHE_TTL:
        return json.loads(cache.read_text())

    url = INDEX_CSV[name]
    resp = requests.get(url, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    df = pd.read_csv(io.StringIO(resp.text))
    out = [
        {
            "symbol": row["Symbol"].strip(),
            "name": row["Company Name"].strip(),
            "industry": str(row.get("Industry", "")).strip(),
        }
        for _, row in df.iterrows()
    ]
    cache.write_text(json.dumps(out))
    return out
