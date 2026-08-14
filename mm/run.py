"""Morning pipeline orchestrator.

Usage: uv run python -m mm.run [--universe nifty50] [--no-fundamentals]
Writes reports/YYYY-MM-DD.md and prints the path.
"""

import argparse
import sys
from datetime import date
from pathlib import Path

import yaml

from . import fundamentals, news, nse, prices, report, technicals, universe

ROOT = Path(__file__).resolve().parent.parent


def main() -> None:
    cfg = yaml.safe_load((ROOT / "config.yaml").read_text())
    ap = argparse.ArgumentParser()
    ap.add_argument("--universe", default=cfg["universe"], choices=list(universe.INDEX_CSV))
    ap.add_argument("--no-fundamentals", action="store_true")
    args = ap.parse_args()

    print(f"[1/5] Universe: {args.universe}", file=sys.stderr)
    stocks = universe.get_universe(args.universe)
    symbols = [s["symbol"] for s in stocks]

    print(f"[2/5] NSE market data + news feeds", file=sys.stderr)
    nse_data = nse.fetch_all()
    headlines = news.fetch_headlines(cfg["news"]["feeds"], max_per_feed=6)
    headlines = headlines[: cfg["news"]["max_headlines"]]

    print(f"[3/5] Daily candles for {len(symbols)} stocks (yfinance)", file=sys.stderr)
    candles = prices.fetch_daily(symbols, days=cfg["history_days"])
    print(f"      got {len(candles)} usable histories", file=sys.stderr)

    print(f"[4/5] Technical signals", file=sys.stderr)
    scfg = cfg["signals"]
    results = [technicals.analyze(sym, df, scfg) for sym, df in candles.items()]
    buys = sorted(
        (r for r in results if r["buy_score"] >= scfg["min_score_buy"] and r["sell_score"] == 0),
        key=lambda r: r["buy_score"], reverse=True,
    )[: cfg["report"]["top_n"]]
    sells = sorted(
        (r for r in results if r["sell_score"] >= scfg["min_score_sell"]),
        key=lambda r: r["sell_score"], reverse=True,
    )[: cfg["report"]["top_n"]]

    if cfg["fundamentals"]["enabled"] and not args.no_fundamentals:
        print(f"[5/5] Fundamentals for {len(buys) + len(sells)} shortlisted", file=sys.stderr)
        for r in buys + sells:
            r["fund"] = fundamentals.check(r["symbol"], cfg["fundamentals"])
    else:
        print("[5/5] Fundamentals skipped", file=sys.stderr)

    md = report.render({
        "indices": nse.key_indices(nse_data["indices"]),
        "fii_dii": nse_data["fii_dii"],
        "gainers": nse.top_pre_open_movers(nse_data["pre_open"])[0],
        "losers": nse.top_pre_open_movers(nse_data["pre_open"])[1],
        "large_deals": nse_data["large_deals"],
        "buys": buys,
        "sells": sells,
        "news": headlines,
    })

    out_dir = ROOT / cfg["report"]["out_dir"]
    out_dir.mkdir(exist_ok=True)
    out = out_dir / f"{date.today().isoformat()}.md"
    out.write_text(md)
    print(out)


if __name__ == "__main__":
    main()
