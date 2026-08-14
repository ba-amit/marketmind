"""Fundamentals hygiene check via yfinance — fetched only for shortlisted
stocks (slow, one HTTP call each). Flags, not hard filters: the report
shows flags next to signals so the human decides.
"""

import yfinance as yf


def check(symbol: str, cfg: dict) -> dict:
    out = {"pe": None, "pb": None, "roe": None, "de": None, "mcap_cr": None, "flags": []}
    try:
        info = yf.Ticker(f"{symbol}.NS").info
    except Exception:
        out["flags"].append("fundamentals unavailable")
        return out

    pe = info.get("trailingPE")
    pb = info.get("priceToBook")
    roe = info.get("returnOnEquity")
    de = info.get("debtToEquity")  # percent, e.g. 150 = 1.5x
    mcap = info.get("marketCap")

    out.update({
        "pe": pe,
        "pb": pb,
        "roe": roe,
        "de": de,
        "mcap_cr": round(mcap / 1e7) if mcap else None,  # ₹ crore
    })
    if pe is not None and pe > cfg["max_pe"]:
        out["flags"].append(f"PE high ({pe:.0f})")
    if pe is not None and pe < 0:
        out["flags"].append("loss-making (negative PE)")
    if de is not None and de > cfg["max_debt_to_equity"]:
        out["flags"].append(f"D/E high ({de / 100:.1f}x)")
    if roe is not None and roe < cfg["min_roe"]:
        out["flags"].append(f"ROE low ({roe * 100:.0f}%)")
    return out
