from __future__ import annotations

"""Serialize yfinance payloads into Pydantic-friendly shapes for Yahoo market tools.

yfinance returns pandas DataFrames and large ``Ticker.info`` dicts; these helpers
trim, normalize, and convert them before tools build their output models.
"""

import re
from datetime import UTC, datetime
from decimal import Decimal

import pandas as pd

# Subset of ``Ticker.info`` fields exposed to agents (keeps tool output small).
INFO_KEYS = (
    "sector",
    "industry",
    "marketCap",
    "trailingPE",
    "forwardPE",
    "dividendYield",
    "beta",
    "fiftyTwoWeekHigh",
    "fiftyTwoWeekLow",
    "currency",
    "longName",
    "shortName",
)


def extract_info_subset(info: dict[str, object]) -> dict[str, object]:
    """Return agent-relevant keys from a full yfinance ``Ticker.info`` dict.

    Omits null values and any field not listed in ``INFO_KEYS``.
    """
    return {key: info[key] for key in INFO_KEYS if key in info and info[key] is not None}


def history_frame_to_bars(frame: pd.DataFrame, *, max_bars: int = 252) -> list[dict[str, object]]:
    """Convert a ``Ticker.history()`` DataFrame into OHLCV bar dicts.

    Keeps the most recent ``max_bars`` rows (default 252 ≈ one year of dailies),
    ordered oldest-first. Each dict matches ``HistoryBar`` fields for
    ``GetAssetHistoryFromYfTool``.
    """
    trimmed = frame.tail(max_bars)
    bars: list[dict[str, object]] = []
    for ts, row in trimmed.iterrows():
        ts_dt = ts.to_pydatetime() if hasattr(ts, "to_pydatetime") else datetime.now(UTC)
        bars.append(
            {
                "date": ts_dt,
                "open": _float_or_none(row.get("Open")),
                "high": _float_or_none(row.get("High")),
                "low": _float_or_none(row.get("Low")),
                "close": _float_or_none(row.get("Close")),
                "volume": _float_or_none(row.get("Volume")),
            }
        )
    return bars


def financials_frame_to_records(frame: pd.DataFrame) -> list[dict[str, object]]:
    """Flatten a yfinance statement DataFrame into JSON-serializable records.

    yfinance uses metrics as rows and fiscal periods as columns; each output
    record has a ``metric`` key plus one entry per period (ISO date string).
    """
    records: list[dict[str, object]] = []
    for metric, row in frame.iterrows():
        entry: dict[str, object] = {"metric": str(metric)}
        for col, value in row.items():
            col_key = col.date().isoformat() if hasattr(col, "date") else str(col)
            entry[col_key] = _serialize_value(value)
        records.append(entry)
    return records


def news_timestamp(raw: int | float | None) -> datetime | None:
    """Parse Yahoo ``providerPublishTime`` (Unix seconds) into UTC ``datetime``."""
    if raw is None:
        return None
    return datetime.fromtimestamp(float(raw), tz=UTC)


def parse_news_datetime(raw: object) -> datetime | None:
    """Parse Yahoo news timestamps (Unix seconds or ISO-8601 strings)."""
    if raw is None:
        return None
    if isinstance(raw, (int, float)):
        return news_timestamp(raw)
    if isinstance(raw, str):
        return datetime.fromisoformat(raw.replace("Z", "+00:00"))
    return None


def normalize_yahoo_news_item(item: dict[str, object]) -> dict[str, object] | None:
    """Map yfinance news payloads (legacy or nested ``content``) to tool fields."""
    content = item.get("content")
    if isinstance(content, dict):
        title = str(content.get("title") or "")
        link = _news_link_from_content(content)
        provider = content.get("provider")
        publisher = (
            str(provider.get("displayName"))
            if isinstance(provider, dict) and provider.get("displayName")
            else None
        )
        published_at = parse_news_datetime(content.get("pubDate") or content.get("displayTime"))
        if not title:
            return None
        return {
            "title": title,
            "link": link,
            "publisher": publisher,
            "published_at": published_at,
        }

    title = str(item.get("title") or "")
    if not title:
        return None
    return {
        "title": title,
        "link": str(item.get("link") or ""),
        "publisher": str(item["publisher"]) if item.get("publisher") else None,
        "published_at": parse_news_datetime(item.get("providerPublishTime")),
    }


def normalize_yahoo_news_items(
    items: list[dict[str, object]],
    *,
    limit: int,
) -> list[dict[str, object]]:
    """Normalize and cap Yahoo news items for ``GetAssetNewsFromYfTool``."""
    normalized: list[dict[str, object]] = []
    for item in items:
        row = normalize_yahoo_news_item(item)
        if row is None:
            continue
        normalized.append(row)
        if len(normalized) >= limit:
            break
    return normalized


def _news_link_from_content(content: dict[str, object]) -> str:
    for key in ("clickThroughUrl", "canonicalUrl"):
        url_holder = content.get(key)
        if isinstance(url_holder, dict) and url_holder.get("url"):
            return str(url_holder["url"])
    return ""


def _company_match_tokens(company_name: str) -> set[str]:
    stopwords = {
        "sa",
        "nv",
        "se",
        "plc",
        "inc",
        "corp",
        "ltd",
        "the",
        "and",
        "ucits",
        "etf",
        "acc",
        "dist",
    }
    tokens: set[str] = set()
    for raw in re.split(r"[\W_]+", company_name.lower()):
        token = raw.strip()
        if len(token) >= 4 and token not in stopwords:
            tokens.add(token)
    return tokens


def _title_matches_company(title: str, tokens: set[str]) -> bool:
    lowered = title.lower()
    return any(token in lowered for token in tokens)


def filter_news_by_company_name(
    items: list[dict[str, object]],
    *,
    company_name: str,
    limit: int,
) -> list[dict[str, object]]:
    """Keep headlines that mention the company; drop generic ticker-sidecar articles."""
    tokens = _company_match_tokens(company_name)
    if not tokens:
        return items[:limit]
    matched = [item for item in items if _title_matches_company(str(item.get("title", "")), tokens)]
    if matched:
        return matched[:limit]
    return items[:limit]


def price_from_fast_info(fast_info: dict[str, object]) -> Decimal | None:
    """Extract spot price from ``Ticker.fast_info`` for tools and the price provider.

    Tries ``lastPrice`` first, then ``regularMarketPrice``. Returns ``None`` when
    neither field is present.
    """
    price = fast_info.get("lastPrice") or fast_info.get("regularMarketPrice")
    if price is None:
        return None
    return Decimal(str(price))


def _float_or_none(value: object) -> float | None:
    """Coerce a history cell to ``float``, treating NaN and missing as ``None``."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    return float(value)


def _serialize_value(value: object) -> object:
    """Coerce a financial statement cell to a JSON-safe scalar."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    return str(value)
