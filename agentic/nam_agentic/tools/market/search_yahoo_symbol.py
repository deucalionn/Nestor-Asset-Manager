from langchain_core.tools import BaseTool, tool
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from nam_agentic.tools.base import BaseNamTool
from nam_agentic.tools.schemas.market import SearchYahooSymbolInput, SearchYahooSymbolOutput
from nam_yahoo import YfinanceClient, YahooIndexResolver


class SearchYahooSymbolTool(BaseNamTool):
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        client: YfinanceClient | None = None,
    ) -> None:
        self._session_factory = session_factory
        self._client = client or YfinanceClient()

    def as_tool(self) -> BaseTool:
        session_factory = self._session_factory
        resolver = YahooIndexResolver(session_factory, client=self._client)

        @tool(args_schema=SearchYahooSymbolInput)
        async def search_yahoo_symbol(
            query: str | None = None,
            isin: str | None = None,
            index_id=None,
        ) -> SearchYahooSymbolOutput:
            """Resolve a Yahoo Finance symbol (DB-first via Lookup).

            Use when: you need yahoo_symbol before price, history, financials, or news tools.
            Do not use when: symbol is already on the index row — pass yahoo_symbol directly.
            Returns: yahoo_symbol, index_type, exchange, quote_type, and DB-cache flag.
            """
            resolved = await resolver.resolve(index_id=index_id, isin=isin, query=query)
            return SearchYahooSymbolOutput(
                yahoo_symbol=resolved.yahoo_symbol,
                name=resolved.name,
                isin=resolved.isin,
                index_id=resolved.index_id,
                index_type=resolved.index_type,
                exchange=resolved.exchange,
                quote_type=resolved.quote_type,
                resolved_from_db=resolved.resolved_from_db,
            )

        return search_yahoo_symbol
