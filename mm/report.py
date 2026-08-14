"""Render the morning report as markdown."""

from datetime import date


def _fmt(v, spec=".1f", dash="—"):
    return format(v, spec) if isinstance(v, (int, float)) else dash


def _signal_table(rows: list[dict], kind: str) -> str:
    if not rows:
        return "_No candidates today._\n"
    lines = [
        "| Stock | Close | Chg% | RSI | Score | Reasons | Fundamental flags |",
        "|---|---:|---:|---:|---:|---|---|",
    ]
    for r in rows:
        f = r.get("fund", {})
        flags = ", ".join(f.get("flags", [])) or "clean"
        reasons = "; ".join(r[f"{kind}_reasons"])
        lines.append(
            f"| **{r['symbol']}** | {r['close']:.1f} | {r['chg_pct']:+.1f} "
            f"| {r['rsi']:.0f} | {r[f'{kind}_score']} | {reasons} | {flags} |"
        )
    return "\n".join(lines) + "\n"


def render(ctx: dict) -> str:
    today = date.today().strftime("%A, %d %B %Y")
    parts = [f"# Morning Market Report — {today}\n"]

    if ctx["indices"]:
        parts.append("## Index snapshot (prev close)\n")
        parts.append("| Index | Level | Chg% |\n|---|---:|---:|")
        for i in ctx["indices"]:
            parts.append(f"| {i['index']} | {_fmt(i['last'], ',.1f')} | {_fmt(i['pct'], '+.2f')} |")
        parts.append("")

    fii = ctx.get("fii_dii")
    if fii:
        parts.append("## FII / DII flows (₹ crore)\n")
        parts.append("| Category | Buy | Sell | Net |\n|---|---:|---:|---:|")
        for row in fii:
            parts.append(
                f"| {row.get('category', '?')} | {row.get('buyValue', '—')} "
                f"| {row.get('sellValue', '—')} | **{row.get('netValue', '—')}** |"
            )
        parts.append("")

    g, l = ctx.get("gainers", []), ctx.get("losers", [])
    if g or l:
        parts.append("## Pre-open movers\n")
        parts.append("**Gainers:** " + ", ".join(f"{r['symbol']} ({r['pct']:+.1f}%)" for r in g))
        parts.append("")
        parts.append("**Losers:** " + ", ".join(f"{r['symbol']} ({r['pct']:+.1f}%)" for r in l))
        parts.append("")

    parts.append("## Buy signals\n")
    parts.append(_signal_table(ctx["buys"], "buy"))
    parts.append("## Sell / caution signals\n")
    parts.append(_signal_table(ctx["sells"], "sell"))

    deals = ctx.get("large_deals")
    if deals:
        bulk = deals.get("BULK_DEALS_DATA") or []
        if bulk:
            parts.append("## Bulk deals (latest)\n")
            parts.append("| Stock | Client | Side | Qty | Price |\n|---|---|---|---:|---:|")
            for d in bulk[:10]:
                parts.append(
                    f"| {d.get('symbol', '?')} | {d.get('clientName', '?')} | {d.get('buySell', '?')} "
                    f"| {d.get('qty', '—')} | {d.get('watp', '—')} |"
                )
            parts.append("")

    if ctx["news"]:
        parts.append("## Headlines\n")
        for n in ctx["news"]:
            parts.append(f"- [{n['title']}]({n['link']}) — _{n['source']}_")
        parts.append("")

    parts.append("---")
    parts.append(
        "_Signals are rule-based screens on EOD data, not investment advice. "
        "Verify fundamentals (Screener.in) and news before acting._"
    )
    return "\n".join(parts) + "\n"
