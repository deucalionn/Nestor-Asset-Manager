from langchain_core.tools import BaseTool, tool
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from nam_agentic.tools.base import BaseNamTool
from nam_agentic.tools.schemas.market import (
    CompanyNewsHeadlineOutput,
    GetDataFromUrlInput,
    GetDataFromUrlOutput,
)
from nam_agentic.tools.services.boursorama.page_reader import ArticlePage, NewsIndexPage, PageReader
from nam_agentic.tools.services.boursorama.urls import normalize_boursorama_url
from nam_agentic.tools.services.embedding import EmbeddingService, OllamaEmbeddingService
from nam_agentic.tools.services.news_item_store import (
    NewsItemStore,
    NewsUpsertPayload,
    infer_news_metadata,
)


class GetDataFromUrlTool(BaseNamTool):
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        page_reader: PageReader | None = None,
        embedding_service: EmbeddingService | None = None,
    ) -> None:
        self._session_factory = session_factory
        self._page_reader = page_reader or PageReader()
        self._store = NewsItemStore(embedding_service or OllamaEmbeddingService())

    def as_tool(self) -> BaseTool:
        session_factory = self._session_factory
        page_reader = self._page_reader
        store = self._store

        @tool(args_schema=GetDataFromUrlInput)
        async def get_data_from_url(url: str, persist: bool = True) -> GetDataFromUrlOutput:
            """Fetch and parse one whitelisted Boursorama URL.

            Use when: reading company news index, global hub, article deep-read, or key figures.
            Do not use when: ETF index and company news URL — use global news instead.
            Returns: news_index with headlines[] or article markdown; articles persist by default.
            """
            result = await page_reader.read(url)
            if isinstance(result, NewsIndexPage):
                return GetDataFromUrlOutput(
                    url=result.url,
                    title=result.title,
                    content_type="news_index",
                    headlines=[
                        CompanyNewsHeadlineOutput(
                            title=h.title,
                            summary=h.summary,
                            article_url=h.article_url,
                            published_at=h.published_at,
                            attribution=h.attribution,
                        )
                        for h in result.headlines
                    ],
                    fetched_at=result.fetched_at,
                )
            assert isinstance(result, ArticlePage)
            news_item_id = None
            persisted = False
            if persist:
                normalized = normalize_boursorama_url(url)
                category, ticker = infer_news_metadata(normalized)
                async with session_factory() as session:
                    news_item_id = await store.upsert(
                        session,
                        NewsUpsertPayload(
                            title=result.title,
                            source_url=normalized,
                            category=category,
                            summary=None,
                            content_markdown=result.markdown,
                            boursorama_ticker=ticker,
                            fetched_at=result.fetched_at,
                        ),
                    )
                    await session.commit()
                persisted = True
            return GetDataFromUrlOutput(
                url=result.url,
                title=result.title,
                content_type="article",
                markdown=result.markdown,
                fetched_at=result.fetched_at,
                persisted=persisted,
                news_item_id=news_item_id,
            )

        return get_data_from_url
