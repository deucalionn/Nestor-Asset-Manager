from __future__ import annotations

"""Serialize yfinance payloads into Pydantic-friendly shapes for Yahoo market tools.

yfinance returns pandas DataFrames and large ``Ticker.info`` dicts; these helpers
trim, normalize, and convert them before tools build their output models.
"""

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
