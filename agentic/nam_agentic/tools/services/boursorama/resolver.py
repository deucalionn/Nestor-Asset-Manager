from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from nam_db.enums import IndexType
from nam_db.models.index import Index
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from nam_agentic.tools.services.boursorama.client import BoursoramaHttpClient
from nam_agentic.tools.services.boursorama.search import search_boursorama
from nam_agentic.tools.services.boursorama.urls import build_type_aware_urls


@dataclass(frozen=True)
class ResolvedIndex:
    index_id: UUID | None
    name: str
    isin: str | None
    boursorama_ticker: str
    index_type: IndexType
    quote_url: str
    news_url: str | None
    key_figures_url: str | None
    composition_url: str | None
    resolved_from_db: bool


class BoursoramaIndexResolver:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        client: BoursoramaHttpClient | None = None,
    ) -> None:
        self._session_factory = session_factory
        self._client = client or BoursoramaHttpClient()

    async def resolve(
        self,
        *,
        index_id: UUID | None = None,
        isin: str | None = None,
        query: str | None = None,
        auto_persist: bool = True,
    ) -> ResolvedIndex:
        async with self._session_factory() as session:
            index = await self._load_index(session, index_id=index_id, isin=isin)
            if index is not None and index.boursorama_ticker:
                urls = build_type_aware_urls(index.boursorama_ticker, index.index_type)
                return ResolvedIndex(
                    index_id=index.id,
                    name=index.name,
                    isin=index.isin,
                    boursorama_ticker=index.boursorama_ticker,
                    index_type=index.index_type,
                    resolved_from_db=True,
                    **urls,
                )

            if index is not None:
                hit = await search_boursorama(self._client, query=index.name, isin=index.isin)
                if auto_persist:
                    index.boursorama_ticker = hit.ticker
                    await session.commit()
                urls = build_type_aware_urls(hit.ticker, index.index_type)
                return ResolvedIndex(
                    index_id=index.id,
                    name=index.name,
                    isin=index.isin,
                    boursorama_ticker=hit.ticker,
                    index_type=index.index_type,
                    resolved_from_db=False,
                    **urls,
                )

            hit = await search_boursorama(
                self._client,
                query=query,
                isin=isin,
            )
            index_type = IndexType.COMPANY if hit.is_company else IndexType.ETF
            urls = build_type_aware_urls(hit.ticker, index_type)
            return ResolvedIndex(
                index_id=None,
                name=hit.name,
                isin=isin,
                boursorama_ticker=hit.ticker,
                index_type=index_type,
                resolved_from_db=False,
                **urls,
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
