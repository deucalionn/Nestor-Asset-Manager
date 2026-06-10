from uuid import UUID

from langchain_core.tools import BaseTool, tool
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from nam_agentic.tools.base import BaseNamTool
from nam_agentic.tools.market.yahoo_helpers import (
    filter_news_by_company_name,
    normalize_yahoo_news_items,
)
from nam_agentic.tools.schemas.market import (
    GetAssetNewsFromYfInput,
    GetAssetNewsFromYfOutput,
    YahooNewsItem,
)
from nam_yahoo import YfinanceClient, YahooIndexResolver


class GetAssetNewsFromYfTool(BaseNamTool):
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        client: YfinanceClient | None = None,
    ) -> None:
        self._session_factory = session_factory
        self._client = client or YfinanceClient()

    def as_tool(self) -> BaseTool:
        session_factory = self._session_factory
        client = self._client
        resolver = YahooIndexResolver(session_factory, client=client)

        @tool(args_schema=GetAssetNewsFromYfInput)
        async def get_asset_news_from_yf(
            index_id: UUID | None = None,
            isin: str | None = None,
            yahoo_symbol: str | None = None,
            limit: int = 10,
        ) -> GetAssetNewsFromYfOutput:
            """Fetch recent ticker headlines from Yahoo Finance.

            Use when: you need headlines for a specific symbol.
            Headlines are available anytime — market session open/closed does not matter.
            Do not use when: Bourso macro cache suffices — use get_financials_news_from_bourso.
            Pass exactly ONE of index_id, isin (from get_index), or yahoo_symbol — not several.
            Returns: list of Yahoo headlines (title, link, publisher, published_at).
            """
            resolved = await resolver.resolve(
                index_id=index_id,
                isin=isin,
                yahoo_symbol=yahoo_symbol,
            )
            raw_items = await client.get_news(resolved.yahoo_symbol, count=min(limit * 3, 25))
            normalized = normalize_yahoo_news_items(raw_items, limit=min(limit * 3, 25))
            filtered = filter_news_by_company_name(
                normalized,
                company_name=resolved.name,
                limit=limit,
            )
            items = [YahooNewsItem.model_validate(row) for row in filtered]
            return GetAssetNewsFromYfOutput(
                yahoo_symbol=resolved.yahoo_symbol,
                items=items,
                count=len(items),
                resolved_from_db=resolved.resolved_from_db,
            )

        return get_asset_news_from_yf
