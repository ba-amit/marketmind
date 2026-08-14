"""Daily OHLCV via yfinance bulk download for .NS symbols."""

import pandas as pd
import yfinance as yf


def fetch_daily(symbols: list[str], days: int = 400) -> dict[str, pd.DataFrame]:
    """Return {symbol: OHLCV DataFrame} (symbol without .NS suffix)."""
    tickers = [f"{s}.NS" for s in symbols]
    data = yf.download(
        tickers,
        period=f"{days}d",
        interval="1d",
        group_by="ticker",
        auto_adjust=True,
        threads=True,
        progress=False,
    )
    out = {}
    for sym, tkr in zip(symbols, tickers):
        try:
            df = data[tkr].dropna(how="all")
        except KeyError:
            continue
        if len(df) < 60:  # not enough history for indicators
            continue
        out[sym] = df
    return out
