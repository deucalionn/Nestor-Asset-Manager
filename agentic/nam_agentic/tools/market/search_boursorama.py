from langchain_core.tools import BaseTool, tool
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from nam_agentic.tools.base import BaseNamTool
from nam_agentic.tools.schemas.market import SearchBoursoramaInput, SearchBoursoramaOutput
from nam_agentic.tools.services.boursorama.resolver import BoursoramaIndexResolver


class SearchBoursoramaTool(BaseNamTool):
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    def as_tool(self) -> BaseTool:
        resolver = BoursoramaIndexResolver(self._session_factory)

        @tool(args_schema=SearchBoursoramaInput)
        async def search_boursorama(
            query: str | None = None,
            isin: str | None = None,
            index_id=None,
        ) -> SearchBoursoramaOutput:
            """Resolve a Boursorama ticker and canonical URLs (DB-first).

            Use when: you need quote, news, key figures, or composition URLs for an index.
            Do not use when: ticker is already known from get_index — use get_data_from_url.
            Returns: ticker, index_type, type-aware URLs, and whether the ticker came from DB cache.
            """
            resolved = await resolver.resolve(index_id=index_id, isin=isin, query=query)
            return SearchBoursoramaOutput(
                boursorama_ticker=resolved.boursorama_ticker,
                name=resolved.name,
                isin=resolved.isin,
                index_id=resolved.index_id,
                index_type=resolved.index_type,
                quote_url=resolved.quote_url,
                news_url=resolved.news_url,
                key_figures_url=resolved.key_figures_url,
                composition_url=resolved.composition_url,
                resolved_from_db=resolved.resolved_from_db,
            )

        return search_boursorama
