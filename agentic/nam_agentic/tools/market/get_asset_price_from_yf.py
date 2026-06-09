from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from langchain_core.tools import BaseTool, tool
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from nam_agentic.tools.base import BaseNamTool
from nam_agentic.tools.market.yahoo_helpers import price_from_fast_info
from nam_agentic.tools.schemas.market import GetAssetPriceFromYfInput, GetAssetPriceFromYfOutput
from nam_agentic.tools.services.yahoo.client import YfinanceClient
from nam_agentic.tools.services.yahoo.resolver import YahooIndexResolver


class GetAssetPriceFromYfTool(BaseNamTool):
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

        @tool(args_schema=GetAssetPriceFromYfInput)
        async def get_asset_price_from_yf(
            index_id: UUID | None = None,
            isin: str | None = None,
            yahoo_symbol: str | None = None,
        ) -> GetAssetPriceFromYfOutput:
            """Fetch live spot price from Yahoo Finance (delayed quotes).

            Use when: you need current price or previous close for an index or raw symbol.
            Do not use when: you need Bourso news or key figures — use Bourso tools instead.
            Returns: yahoo_symbol, last_price, previous_close, currency, and DB-cache flag.
            """
            resolved = await resolver.resolve(
                index_id=index_id,
                isin=isin,
                yahoo_symbol=yahoo_symbol,
            )
            fast_info = await client.get_fast_info(resolved.yahoo_symbol)
            previous = fast_info.get("previousClose")
            return GetAssetPriceFromYfOutput(
                yahoo_symbol=resolved.yahoo_symbol,
                currency=str(fast_info.get("currency")) if fast_info.get("currency") else None,
                last_price=price_from_fast_info(fast_info),
                previous_close=Decimal(str(previous)) if previous is not None else None,
                fetched_at=datetime.now(UTC),
                resolved_from_db=resolved.resolved_from_db,
            )

        return get_asset_price_from_yf
