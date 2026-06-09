from uuid import UUID

from langchain_core.tools import BaseTool, tool
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from nam_agentic.tools.base import BaseNamTool
from nam_agentic.tools.market.yahoo_helpers import news_timestamp
from nam_agentic.tools.schemas.market import (
    GetAssetNewsFromYfInput,
    GetAssetNewsFromYfOutput,
    YahooNewsItem,
)
from nam_agentic.tools.services.yahoo.client import YfinanceClient
from nam_agentic.tools.services.yahoo.resolver import YahooIndexResolver


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
            """Fetch live ticker news from Yahoo Finance.

            Use when: you need fresh headlines for a specific symbol from Yahoo.
            Do not use when: you need Bourso macro headlines from SQL cache —
            use get_financials_news_from_bourso instead.
            Returns: list of Yahoo headlines (title, link, publisher, published_at).
            """
            resolved = await resolver.resolve(
                index_id=index_id,
                isin=isin,
                yahoo_symbol=yahoo_symbol,
            )
            raw_items = await client.get_news(resolved.yahoo_symbol, count=limit)
            items = [
                YahooNewsItem(
                    title=str(item.get("title") or ""),
                    link=str(item.get("link") or ""),
                    publisher=str(item.get("publisher")) if item.get("publisher") else None,
                    published_at=news_timestamp(item.get("providerPublishTime")),
                )
                for item in raw_items
            ]
            return GetAssetNewsFromYfOutput(
                yahoo_symbol=resolved.yahoo_symbol,
                items=items,
                count=len(items),
                resolved_from_db=resolved.resolved_from_db,
            )

        return get_asset_news_from_yf
