from datetime import UTC, datetime
from uuid import UUID

from langchain_core.tools import BaseTool, tool
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from nam_agentic.tools.base import BaseNamTool
from nam_agentic.tools.market.yahoo_helpers import history_frame_to_bars
from nam_agentic.tools.schemas.market import (
    GetAssetHistoryFromYfInput,
    GetAssetHistoryFromYfOutput,
    HistoryBar,
)
from nam_yahoo import YfinanceClient, YahooIndexResolver


class GetAssetHistoryFromYfTool(BaseNamTool):
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

        @tool(args_schema=GetAssetHistoryFromYfInput)
        async def get_asset_history_from_yf(
            index_id: UUID | None = None,
            isin: str | None = None,
            yahoo_symbol: str | None = None,
            period: str = "1y",
            interval: str = "1d",
        ) -> GetAssetHistoryFromYfOutput:
            """Fetch OHLCV price history from Yahoo Finance.

            Use when: trend analysis, drawdown, or return calculations need historical bars.
            Do not use when: you only need the latest spot price — use get_asset_price_from_yf.
            Returns: up to 252 daily bars (date, open, high, low, close, volume) oldest-first.
            """
            resolved = await resolver.resolve(
                index_id=index_id,
                isin=isin,
                yahoo_symbol=yahoo_symbol,
            )
            frame = await client.get_history(
                resolved.yahoo_symbol,
                period=period,
                interval=interval,
            )
            bars = [HistoryBar(**row) for row in history_frame_to_bars(frame)]
            return GetAssetHistoryFromYfOutput(
                yahoo_symbol=resolved.yahoo_symbol,
                period=period,
                interval=interval,
                bars=bars,
                count=len(bars),
                fetched_at=datetime.now(UTC),
                resolved_from_db=resolved.resolved_from_db,
            )

        return get_asset_history_from_yf
