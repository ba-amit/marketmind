"""Indicator computation + composite buy/sell scoring per stock.

All indicators hand-rolled on pandas — no TA-Lib dependency.
Scoring: each bullish condition +1 to buy score, each bearish +1 to sell
score; reasons are recorded so the report can explain every signal.
"""

import pandas as pd


def rsi(close: pd.Series, period: int = 14) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0).ewm(alpha=1 / period, adjust=False).mean()
    loss = (-delta.clip(upper=0)).ewm(alpha=1 / period, adjust=False).mean()
    rs = gain / loss
    return 100 - 100 / (1 + rs)


def macd(close: pd.Series):
    ema12 = close.ewm(span=12, adjust=False).mean()
    ema26 = close.ewm(span=26, adjust=False).mean()
    line = ema12 - ema26
    signal = line.ewm(span=9, adjust=False).mean()
    return line, signal


def candle_pattern(df: pd.DataFrame) -> str | None:
    """Detect a simple 1–2 candle pattern on the latest bar."""
    if len(df) < 2:
        return None
    prev, cur = df.iloc[-2], df.iloc[-1]
    o, h, l, c = cur["Open"], cur["High"], cur["Low"], cur["Close"]
    body = abs(c - o)
    rng = h - l
    if rng <= 0:
        return None
    upper = h - max(o, c)
    lower = min(o, c) - l

    if body / rng < 0.1:
        return "doji"
    if lower > 2 * body and upper < body:
        return "hammer" if c > o else "hanging-man"
    if upper > 2 * body and lower < body:
        return "shooting-star"
    # engulfing: current body engulfs previous body, opposite colors
    po, pc = prev["Open"], prev["Close"]
    if pc < po and c > o and c >= po and o <= pc:
        return "bullish-engulfing"
    if pc > po and c < o and c <= po and o >= pc:
        return "bearish-engulfing"
    return None


BULLISH_PATTERNS = {"hammer", "bullish-engulfing"}
BEARISH_PATTERNS = {"shooting-star", "hanging-man", "bearish-engulfing"}


def analyze(sym: str, df: pd.DataFrame, cfg: dict) -> dict:
    close, vol = df["Close"], df["Volume"]
    last = float(close.iloc[-1])
    chg_pct = float(close.pct_change().iloc[-1] * 100)

    r = rsi(close, cfg["rsi_period"])
    r_now, r_prev = float(r.iloc[-1]), float(r.iloc[-2])

    macd_line, macd_sig = macd(close)
    macd_cross_up = macd_line.iloc[-2] <= macd_sig.iloc[-2] and macd_line.iloc[-1] > macd_sig.iloc[-1]
    macd_cross_dn = macd_line.iloc[-2] >= macd_sig.iloc[-2] and macd_line.iloc[-1] < macd_sig.iloc[-1]

    sma20 = close.rolling(20).mean()
    sma50 = close.rolling(50).mean()
    sma200 = close.rolling(200).mean()
    above50 = last > float(sma50.iloc[-1])
    above200 = bool(sma200.notna().iloc[-1]) and last > float(sma200.iloc[-1])
    golden_cross = (
        sma200.notna().iloc[-1]
        and sma50.iloc[-6] <= sma200.iloc[-6]
        and sma50.iloc[-1] > sma200.iloc[-1]
    )
    death_cross = (
        sma200.notna().iloc[-1]
        and sma50.iloc[-6] >= sma200.iloc[-6]
        and sma50.iloc[-1] < sma200.iloc[-1]
    )

    vol_avg20 = float(vol.rolling(20).mean().iloc[-2])
    vol_spike = vol_avg20 > 0 and float(vol.iloc[-1]) > cfg["volume_spike_mult"] * vol_avg20

    hi52 = float(close.rolling(250, min_periods=60).max().iloc[-1])
    lo52 = float(close.rolling(250, min_periods=60).min().iloc[-1])
    near_high = (hi52 - last) / hi52 * 100 <= cfg["near_high_pct"]
    near_low = (last - lo52) / lo52 * 100 <= cfg["near_high_pct"]

    pattern = candle_pattern(df)

    uptrend = above50 and above200 and float(sma50.iloc[-1]) > float(sma200.iloc[-1])
    downtrend = (
        bool(sma200.notna().iloc[-1])
        and not above50 and not above200
        and float(sma50.iloc[-1]) < float(sma200.iloc[-1])
    )
    crossed_up_20 = close.iloc[-2] <= sma20.iloc[-2] and last > float(sma20.iloc[-1])
    crossed_dn_20 = close.iloc[-2] >= sma20.iloc[-2] and last < float(sma20.iloc[-1])

    buy, sell = [], []
    if uptrend:
        buy.append("Uptrend (above rising 50/200 SMA)")
    if uptrend and 35 <= r_now <= 50:
        buy.append(f"Pullback in uptrend (RSI {r_now:.0f})")
    if crossed_up_20:
        buy.append("Closed back above 20 SMA")
    if downtrend:
        sell.append("Downtrend (below falling 50/200 SMA)")
    if crossed_dn_20:
        sell.append("Closed below 20 SMA")
    if r_now < cfg["rsi_oversold"]:
        buy.append(f"RSI oversold ({r_now:.0f})")
    if r_prev < cfg["rsi_oversold"] <= r_now:
        buy.append("RSI recovering from oversold")
    if macd_cross_up:
        buy.append("MACD bullish crossover")
    if golden_cross:
        buy.append("Golden cross (50/200 SMA)")
    if near_high and above50 and above200:
        buy.append("Momentum: near 52w high, above 50/200 SMA")
    if vol_spike and chg_pct > 0:
        buy.append(f"Volume spike on up day ({chg_pct:+.1f}%)")
    if pattern in BULLISH_PATTERNS:
        buy.append(f"Bullish candle: {pattern}")

    if r_now > cfg["rsi_overbought"]:
        sell.append(f"RSI overbought ({r_now:.0f})")
    if macd_cross_dn:
        sell.append("MACD bearish crossover")
    if death_cross:
        sell.append("Death cross (50/200 SMA)")
    if near_low and not above50:
        sell.append("Weakness: near 52w low, below 50 SMA")
    if vol_spike and chg_pct < 0:
        sell.append(f"Volume spike on down day ({chg_pct:+.1f}%)")
    if pattern in BEARISH_PATTERNS:
        sell.append(f"Bearish candle: {pattern}")

    return {
        "symbol": sym,
        "close": last,
        "chg_pct": chg_pct,
        "rsi": r_now,
        "above50": above50,
        "above200": above200,
        "pattern": pattern,
        "buy_score": len(buy),
        "sell_score": len(sell),
        "buy_reasons": buy,
        "sell_reasons": sell,
    }
