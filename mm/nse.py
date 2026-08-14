"""NSE unofficial JSON endpoints: pre-open, FII/DII, bulk deals, indices.

NSE blocks bare requests; a session must first hit the homepage with a
browser User-Agent to collect cookies, then reuse them for /api calls.
Every fetcher degrades to None on failure — the report renders without
that section rather than crashing the morning run.
"""

import requests

BASE = "https://www.nseindia.com"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"
    ),
    "Accept": "application/json, text/html;q=0.9",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.nseindia.com/",
}


def _session() -> requests.Session:
    s = requests.Session()
    s.headers.update(HEADERS)
    s.get(BASE, timeout=15)  # prime cookies (nsit / nseappid)
    return s


def _get(s: requests.Session, path: str):
    try:
        r = s.get(f"{BASE}{path}", timeout=15)
        r.raise_for_status()
        return r.json()
    except Exception:
        return None


def fetch_all() -> dict:
    try:
        s = _session()
    except Exception:
        return {"pre_open": None, "fii_dii": None, "large_deals": None, "indices": None}
    return {
        "pre_open": _get(s, "/api/market-data-pre-open?key=ALL"),
        "fii_dii": _get(s, "/api/fiidiiTradeReact"),
        "large_deals": _get(s, "/api/snapshot-capital-market-largedeal"),
        "indices": _get(s, "/api/allIndices"),
    }


def top_pre_open_movers(pre_open: dict | None, n: int = 8) -> tuple[list, list]:
    """Return (gainers, losers) from pre-open data, each [{symbol, pct, price}]."""
    if not pre_open or "data" not in pre_open:
        return [], []
    rows = []
    for item in pre_open["data"]:
        meta = item.get("metadata", {})
        sym, pct, price = meta.get("symbol"), meta.get("pChange"), meta.get("lastPrice")
        if sym and pct is not None:
            rows.append({"symbol": sym, "pct": pct, "price": price})
    rows.sort(key=lambda r: r["pct"], reverse=True)
    return rows[:n], rows[-n:][::-1]


def key_indices(indices: dict | None) -> list[dict]:
    if not indices or "data" not in indices:
        return []
    keep = {
        "NIFTY 50", "NIFTY BANK", "NIFTY MIDCAP 100", "NIFTY SMALLCAP 100",
        "NIFTY IT", "NIFTY AUTO", "NIFTY PHARMA", "NIFTY FMCG", "NIFTY METAL",
        "NIFTY ENERGY", "NIFTY FIN SERVICE", "NIFTY REALTY",
    }
    out = []
    for d in indices["data"]:
        if d.get("index") in keep:
            out.append({
                "index": d["index"],
                "last": d.get("last"),
                "pct": d.get("percentChange"),
            })
    return out
