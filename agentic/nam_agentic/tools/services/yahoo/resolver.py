from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from nam_db.enums import IndexType
from nam_db.models.index import Index
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from nam_agentic.tools.services.yahoo.client import YfinanceClient
from nam_agentic.tools.services.yahoo.errors import YahooSymbolNotFoundError
from nam_agentic.tools.services.yahoo.lookup import (
    dataframe_to_lookup_rows,
    filter_by_index_type,
    pick_lookup_row,
)


@dataclass(frozen=True)
class ResolvedYahooIndex:
    index_id: UUID | None
    name: str
    isin: str | None
    yahoo_symbol: str
    index_type: IndexType
    exchange: str | None
    quote_type: str | None
    resolved_from_db: bool


class YahooIndexResolver:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        client: YfinanceClient | None = None,
    ) -> None:
        self._session_factory = session_factory
        self._client = client or YfinanceClient()

    async def resolve(
        self,
        *,
        index_id: UUID | None = None,
        isin: str | None = None,
        query: str | None = None,
        yahoo_symbol: str | None = None,
        auto_persist: bool = True,
    ) -> ResolvedYahooIndex:
        if yahoo_symbol is not None:
            return ResolvedYahooIndex(
                index_id=index_id,
                name=query or yahoo_symbol,
                isin=isin,
                yahoo_symbol=yahoo_symbol,
                index_type=IndexType.COMPANY,
                exchange=None,
                quote_type=None,
                resolved_from_db=False,
            )

        async with self._session_factory() as session:
            index = await self._load_index(session, index_id=index_id, isin=isin)
            if index is not None and index.yahoo_symbol:
                return self._from_index(index, resolved_from_db=True)

            lookup_query = self._lookup_query(index=index, query=query, isin=isin)
            if lookup_query is None:
                msg = "Provide index_id, isin, query, or yahoo_symbol"
                raise YahooSymbolNotFoundError(msg)

            df = await self._client.lookup(lookup_query)
            rows = filter_by_index_type(
                dataframe_to_lookup_rows(df),
                index.index_type if index is not None else None,
            )
            hit = pick_lookup_row(rows)

            if index is not None:
                if auto_persist:
                    index.yahoo_symbol = hit.yahoo_symbol
                    await session.commit()
                return ResolvedYahooIndex(
                    index_id=index.id,
                    name=index.name,
                    isin=index.isin,
                    yahoo_symbol=hit.yahoo_symbol,
                    index_type=index.index_type,
                    exchange=hit.exchange,
                    quote_type=hit.quote_type,
                    resolved_from_db=False,
                )

            index_type = (
                IndexType.ETF
                if (hit.quote_type or "").lower() == "etf"
                else IndexType.COMPANY
            )
            return ResolvedYahooIndex(
                index_id=None,
                name=hit.name,
                isin=isin,
                yahoo_symbol=hit.yahoo_symbol,
                index_type=index_type,
                exchange=hit.exchange,
                quote_type=hit.quote_type,
                resolved_from_db=False,
            )

    async def _load_index(
        self,
        session: AsyncSession,
        *,
        index_id: UUID | None,
        isin: str | None,
    ) -> Index | None:
        if index_id is not None:
            return await session.get(Index, index_id)
        if isin is not None:
            return await session.scalar(select(Index).where(Index.isin == isin))
        return None

    @staticmethod
    def _lookup_query(
        *,
        index: Index | None,
        query: str | None,
        isin: str | None,
    ) -> str | None:
        if index is not None:
            return index.isin or index.name
        return isin or query

    @staticmethod
    def _from_index(index: Index, *, resolved_from_db: bool) -> ResolvedYahooIndex:
        return ResolvedYahooIndex(
            index_id=index.id,
            name=index.name,
            isin=index.isin,
            yahoo_symbol=index.yahoo_symbol or "",
            index_type=index.index_type,
            exchange=None,
            quote_type=None,
            resolved_from_db=resolved_from_db,
        )
