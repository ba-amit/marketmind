"""RSS news aggregation (Zerodha Pulse, Moneycontrol, ET Markets)."""

import time

import feedparser


def fetch_headlines(feeds: list[dict], max_per_feed: int = 12) -> list[dict]:
    """Return [{source, title, link, published}] newest-first per feed."""
    out = []
    for feed in feeds:
        try:
            parsed = feedparser.parse(feed["url"])
        except Exception:
            continue
        for entry in parsed.entries[:max_per_feed]:
            ts = None
            for key in ("published_parsed", "updated_parsed"):
                if getattr(entry, key, None):
                    ts = time.mktime(getattr(entry, key))
                    break
            out.append({
                "source": feed["name"],
                "title": entry.get("title", "").strip(),
                "link": entry.get("link", ""),
                "ts": ts,
            })
    return out
