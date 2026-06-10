from __future__ import annotations

"""Normalize yfinance Lookup results into resolver-friendly candidates.

Yahoo returns a pandas DataFrame (symbol as index); these helpers turn that into
typed rows, filter by NAM index_type, and pick one symbol when several listings
match the same ISIN or company name (e.g. prefer ``AI.PA`` over ``AILA.DU``).
"""

import pandas as pd
from nam_db.enums import IndexType

from nam_agentic.settings import settings
from nam_agentic.tools.services.yahoo.client import LookupRow
from nam_agentic.tools.services.yahoo.errors import YahooSymbolNotFoundError

_PREFERRED_EXCHANGES = ("PAR", "EPA", "MIL", "AMS", "BRU", "LIS", "NYQ", "NMS", "NGM")


def dataframe_to_lookup_rows(df: pd.DataFrame) -> list[LookupRow]:
    """Convert a yfinance ``Lookup.get_all()`` DataFrame into ``LookupRow`` objects.

    The DataFrame index holds Yahoo tickers (``AI.PA``); row columns carry
    ``shortName``, ``exchange``, and ``quoteType``. Returns an empty list when
    the frame is missing or has no rows.
    """
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
    """Keep only candidates compatible with the index row's ``index_type``.

    When ``index_type`` is known from ``indices``, drop mismatched quote types:
    ``ETF`` → ``quoteType=etf`` only; ``COMPANY`` → ``equity`` only.
    Pass ``None`` to skip filtering (e.g. ad-hoc search without a DB row).
    """
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
    """Select a single Yahoo symbol from lookup candidates.

    Applies ``yahoo_resolve_prefer_suffix`` (default ``.PA``) so PEA/EU instruments
    resolve to Euronext Paris when available. When several symbols remain, ranks by
    suffix, liquid EU/US exchanges, and avoids ISIN-style tickers (e.g.
    ``NL00150001Q9.SG``). Raises only when the top two candidates are still tied.
    """
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
