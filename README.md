# MarketMind — daily Indian market research pipeline

**Live report: https://ba-amit.github.io/marketmind/** · [archive](https://ba-amit.github.io/marketmind/archive.html)

Every morning, one command produces a research report for NSE stocks:
index snapshot, FII/DII flows, pre-open movers, rule-based **buy/sell
signals** (technicals + fundamentals hygiene), bulk deals, and headlines.

## Run

```sh
uv run python -m mm.run                 # default universe from config.yaml
uv run python -m mm.run --universe nifty50
uv run python -m mm.run --no-fundamentals   # faster, skips yfinance info calls
```

Output: `reports/YYYY-MM-DD.md`.

## Hosting

`.github/workflows/morning-report.yml` runs the pipeline every weekday at
03:00 UTC (08:30 IST), writes `docs/index.md` plus a dated copy under
`docs/archive/`, and commits — GitHub Pages serves `main` `/docs`.

NSE's JSON endpoints sometimes block cloud runner IPs; those sections drop
out of the hosted report while candles, signals, and news still render.
Run locally for the full picture when that happens.

## Data sources (all free)

| Data | Source |
|---|---|
| Headlines | Zerodha Pulse RSS, Moneycontrol RSS, ET Markets RSS |
| Pre-open movers, FII/DII, bulk deals, indices | NSE unofficial JSON APIs (cookie-primed session) |
| Daily OHLCV | yfinance (`.NS` tickers, bulk download) |
| Index constituents | NSE archives CSV (cached 7 days in `.cache/`) |
| Fundamentals (PE, PB, ROE, D/E) | yfinance `info`, only for shortlisted stocks |

NSE endpoints are undocumented and can change; every fetcher degrades
gracefully — a failed section is dropped from the report, never fatal.

## Signals

Composite scoring per stock (`mm/technicals.py`), each condition +1:

- **Buy**: RSI(14) oversold / recovering, MACD bullish crossover, golden
  cross, momentum (near 52w high above 50/200 SMA), volume spike on an up
  day, bullish candle (hammer, bullish engulfing)
- **Sell**: RSI overbought, MACD bearish crossover, death cross, near 52w
  low below 50 SMA, volume spike on a down day, bearish candle
  (shooting star, hanging man, bearish engulfing)

Thresholds in `config.yaml` (`min_score_buy` / `min_score_sell`, default 3).
Shortlisted stocks get fundamentals **flags** (high PE / D/E, low ROE,
loss-making) — shown for judgment, not used as hard filters.

## Structure

```
config.yaml        # universe, feeds, thresholds
mm/universe.py     # index constituents
mm/news.py         # RSS aggregation
mm/nse.py          # NSE JSON endpoints
mm/prices.py       # yfinance candles
mm/technicals.py   # indicators + scoring
mm/fundamentals.py # yfinance hygiene flags
mm/report.py       # markdown rendering
mm/run.py          # orchestrator
```

## Roadmap

- Screener.in export ingestion for real fundamentals (Piotroski F-score,
  promoter pledging) — paid export ₹~5k/yr is the clean path
- NSE bhavcopy + delivery % via jugaad-data as yfinance cross-check
- Backtest harness for signal thresholds
- Scheduled pre-market run (cron / Claude scheduled agent)

_Signals are screens, not advice._
