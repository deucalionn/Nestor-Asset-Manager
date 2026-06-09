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


def pick_lookup_row(
    rows: list[LookupRow],
    *,
    prefer_suffix: str | None = None,
) -> LookupRow:
    """Select a single Yahoo symbol from lookup candidates.

    Applies ``yahoo_resolve_prefer_suffix`` (default ``.PA``) so PEA/EU instruments
    resolve to Euronext Paris when available. If several symbols still tie after
    suffix preference, raises ``YahooSymbolNotFoundError`` with the candidate list
    so the agent can call ``update_index_yahoo_symbol`` manually.
    """
    if not rows:
        msg = "No Yahoo symbol candidates found"
        raise YahooSymbolNotFoundError(msg)

    suffix = prefer_suffix if prefer_suffix is not None else settings.yahoo_resolve_prefer_suffix
    preferred = [row for row in rows if row.yahoo_symbol.endswith(suffix)]
    candidates = preferred or rows

    if len(candidates) > 1:
        symbols = ", ".join(row.yahoo_symbol for row in candidates)
        msg = f"Ambiguous Yahoo symbol lookup; candidates: {symbols}"
        raise YahooSymbolNotFoundError(msg)

    return candidates[0]
