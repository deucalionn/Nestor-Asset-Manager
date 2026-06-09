from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any

import pandas as pd
from yfinance import Lookup, Search, Ticker

from nam_agentic.settings import settings
from nam_agentic.tools.services.yahoo.errors import YahooDataUnavailableError


@dataclass(frozen=True)
class LookupRow:
    yahoo_symbol: str
    name: str
    exchange: str | None
    quote_type: str | None


class YfinanceClient:
    """Async wrapper around sync yfinance calls."""

    def __init__(self, *, timeout_sec: int | None = None) -> None:
        self._timeout_sec = timeout_sec or settings.yahoo_request_timeout_sec

    async def lookup(self, query: str) -> pd.DataFrame:
        """Resolve an ISIN or name to Yahoo ticker candidates via yfinance ``Lookup``.

        Runs off the event loop (``asyncio.to_thread``). Returns the raw
        ``get_all()`` DataFrame; pass it through ``lookup.dataframe_to_lookup_rows``,
        ``filter_by_index_type``, and ``pick_lookup_row`` for disambiguation.
        """
        return await asyncio.to_thread(self._lookup_sync, query)

    async def get_fast_info(self, symbol: str) -> dict[str, Any]:
        return await asyncio.to_thread(self._get_fast_info_sync, symbol)

    async def get_history(
        self,
        symbol: str,
        *,
        period: str,
        interval: str,
    ) -> pd.DataFrame:
        return await asyncio.to_thread(
            self._get_history_sync,
            symbol,
            period,
            interval,
        )

    async def get_info(self, symbol: str) -> dict[str, Any]:
        return await asyncio.to_thread(self._get_info_sync, symbol)

    async def get_financials(
        self,
        symbol: str,
        *,
        statement: str,
        freq: str,
    ) -> pd.DataFrame:
        return await asyncio.to_thread(
            self._get_financials_sync,
            symbol,
            statement,
            freq,
        )

    async def get_news(self, symbol: str, *, count: int) -> list[dict[str, Any]]:
        return await asyncio.to_thread(self._get_news_sync, symbol, count)

    def _lookup_sync(self, query: str) -> pd.DataFrame:
        lookup = Lookup(query)
        return lookup.get_all()

    def _get_fast_info_sync(self, symbol: str) -> dict[str, Any]:
        ticker = Ticker(symbol)
        fast_info = ticker.fast_info
        if not fast_info:
            msg = f"No fast_info for symbol {symbol}"
            raise YahooDataUnavailableError(msg)
        return dict(fast_info)

    def _get_history_sync(self, symbol: str, period: str, interval: str) -> pd.DataFrame:
        ticker = Ticker(symbol)
        history = ticker.history(period=period, interval=interval)
        if history is None or history.empty:
            msg = f"No history for symbol {symbol}"
            raise YahooDataUnavailableError(msg)
        return history

    def _get_info_sync(self, symbol: str) -> dict[str, Any]:
        ticker = Ticker(symbol)
        info = ticker.info
        if not info:
            msg = f"No info for symbol {symbol}"
            raise YahooDataUnavailableError(msg)
        return dict(info)

    def _get_financials_sync(self, symbol: str, statement: str, freq: str) -> pd.DataFrame:
        ticker = Ticker(symbol)
        attr_map = {
            ("income", "annual"): "financials",
            ("income", "quarterly"): "quarterly_financials",
            ("balance", "annual"): "balance_sheet",
            ("balance", "quarterly"): "quarterly_balance_sheet",
            ("cashflow", "annual"): "cashflow",
            ("cashflow", "quarterly"): "quarterly_cashflow",
        }
        attr = attr_map.get((statement, freq))
        if attr is None:
            msg = f"Unsupported statement={statement} freq={freq}"
            raise YahooDataUnavailableError(msg)
        frame = getattr(ticker, attr, None)
        if frame is None or (isinstance(frame, pd.DataFrame) and frame.empty):
            msg = f"No {statement} ({freq}) for symbol {symbol}"
            raise YahooDataUnavailableError(msg)
        return frame

    def _get_news_sync(self, symbol: str, count: int) -> list[dict[str, Any]]:
        search = Search(symbol)
        news = search.news or []
        return news[:count]
