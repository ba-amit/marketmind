"""Daily OHLCV via yfinance bulk download for .NS symbols."""

import pandas as pd
import yfinance as yf

IST = "Asia/Kolkata"


def _drop_partial_bar(df: pd.DataFrame) -> pd.DataFrame:
    """Drop today's row — during a live session yfinance returns a partial
    bar whose Close is an intraday snapshot, which would corrupt every
    indicator keyed on the last candle."""
    today = pd.Timestamp.now(tz=IST).normalize().tz_localize(None)
    idx = df.index.tz_localize(None) if df.index.tz is not None else df.index
    return df[idx < today]


def fetch_daily(symbols: list[str], days: int = 400) -> dict[str, pd.DataFrame]:
    """Return {symbol: OHLCV DataFrame} of completed sessions only."""
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
        df = _drop_partial_bar(df)
        if len(df) < 60:  # not enough history for indicators
            continue
        out[sym] = df
    return out
