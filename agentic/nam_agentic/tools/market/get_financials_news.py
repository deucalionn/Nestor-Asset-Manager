from datetime import UTC, datetime, timedelta

from langchain_core.tools import BaseTool, tool
from nam_db.models.news_item import NewsItem
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from nam_agentic.tools.base import BaseNamTool
from nam_agentic.tools.schemas.market import (
    GetFinancialsNewsInput,
    GetFinancialsNewsOutput,
    NewsItemOutput,
)
from nam_agentic.tools.services.embedding import EmbeddingService, OllamaEmbeddingService
from nam_agentic.tools.services.news_search import NewsSearchService


class GetFinancialsNewsTool(BaseNamTool):
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        embedding_service: EmbeddingService | None = None,
        search_service: NewsSearchService | None = None,
    ) -> None:
        self._session_factory = session_factory
        self._embedding_service = embedding_service or OllamaEmbeddingService()
        self._search_service = search_service or NewsSearchService()

    def as_tool(self) -> BaseTool:
        session_factory = self._session_factory
        embedding_service = self._embedding_service
        search_service = self._search_service

        @tool(args_schema=GetFinancialsNewsInput)
        async def get_financials_news(
            category=None,
            keyword: str | None = None,
            semantic_query: str | None = None,
            since_hours: int = 48,
            boursorama_ticker: str | None = None,
            limit: int = 20,
            min_similarity: float = 0.7,
        ) -> GetFinancialsNewsOutput:
            """Read cached Boursorama news and calendars from PostgreSQL.

            Use when: macro brief, market headlines, ETF context, or semantic news recall.
            Do not use when: you need a fresh article not yet cached — use get_data_from_url first.
            Returns: list of news items (title, summary, category, dates) newest or by similarity.
            """
            async with session_factory() as session:
                if semantic_query:
                    query_vector = await embedding_service.embed(semantic_query)
                    items = await search_service.search(
                        session,
                        query_vector=query_vector,
                        since_hours=since_hours,
                        top_k=limit,
                        min_similarity=min_similarity,
                        category=category,
                        boursorama_ticker=boursorama_ticker,
                        keyword=keyword,
                    )
                else:
                    cutoff = datetime.now(UTC) - timedelta(hours=since_hours)
                    stmt = select(NewsItem).where(NewsItem.fetched_at >= cutoff)
                    if category is not None:
                        stmt = stmt.where(NewsItem.category == category)
                    if boursorama_ticker:
                        stmt = stmt.where(NewsItem.boursorama_ticker == boursorama_ticker)
                    if keyword:
                        pattern = f"%{keyword}%"
                        stmt = stmt.where(
                            or_(NewsItem.title.ilike(pattern), NewsItem.summary.ilike(pattern))
                        )
                    stmt = stmt.order_by(
                        func.coalesce(NewsItem.published_at, NewsItem.fetched_at).desc()
                    ).limit(limit)
                    rows = (await session.scalars(stmt)).all()
                    items = [NewsItemOutput.model_validate(row) for row in rows]

            return GetFinancialsNewsOutput(items=items, count=len(items))

        return get_financials_news
