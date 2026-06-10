from __future__ import annotations

import pandas as pd
from nam_db.enums import IndexType

from nam_yahoo.client import LookupRow
from nam_yahoo.errors import YahooSymbolNotFoundError
from nam_yahoo.settings import settings

_PREFERRED_EXCHANGES = ("PAR", "EPA", "MIL", "AMS", "BRU", "LIS", "NYQ", "NMS", "NGM")


def dataframe_to_lookup_rows(df: pd.DataFrame) -> list[LookupRow]:
    if df is None or df.empty:
        return []
    rows: list[LookupRow] = []
    for symbol, row in df.iterrows():
        rows.append(
            LookupRow(
                yahoo_symbol=str(symbol),
                name=str(row.get("shortName") or symbol),
                exchange=str(row["exchange"]) if pd.notna(row.get("exchange")) else None,
                quote_type=str(row["quoteType"]) if pd.notna(row.get("quoteType")) else None,
            )
        )
    return rows


def filter_by_index_type(rows: list[LookupRow], index_type: IndexType | None) -> list[LookupRow]:
    if index_type is None:
        return rows
    if index_type == IndexType.ETF:
        return [row for row in rows if (row.quote_type or "").lower() == "etf"]
    return [row for row in rows if (row.quote_type or "").lower() == "equity"]


def _candidate_rank(row: LookupRow, *, suffix: str) -> tuple[int, int, int, int]:
    symbol = row.yahoo_symbol
    exchange = (row.exchange or "").upper()
    try:
        exchange_rank = _PREFERRED_EXCHANGES.index(exchange)
    except ValueError:
        exchange_rank = len(_PREFERRED_EXCHANGES)

    suffix_rank = 0 if symbol.endswith(suffix) else 1
    root = symbol.split(".", 1)[0]
    isin_style = (
        1 if root.isalnum() and any(ch.isdigit() for ch in root) and len(root) >= 10 else 0
    )
    return (suffix_rank, exchange_rank, isin_style, len(symbol))


def pick_lookup_row(
    rows: list[LookupRow],
    *,
    prefer_suffix: str | None = None,
) -> LookupRow:
    if not rows:
        msg = "No Yahoo symbol candidates found"
        raise YahooSymbolNotFoundError(msg)

    suffix = prefer_suffix if prefer_suffix is not None else settings.yahoo_resolve_prefer_suffix
    preferred = [row for row in rows if row.yahoo_symbol.endswith(suffix)]
    pool = preferred or rows
    ranked = sorted(pool, key=lambda row: _candidate_rank(row, suffix=suffix))

    if len(ranked) > 1 and _candidate_rank(ranked[0], suffix=suffix) == _candidate_rank(
        ranked[1], suffix=suffix
    ):
        symbols = ", ".join(row.yahoo_symbol for row in ranked)
        msg = f"Ambiguous Yahoo symbol lookup; candidates: {symbols}"
        raise YahooSymbolNotFoundError(msg)

    return ranked[0]
