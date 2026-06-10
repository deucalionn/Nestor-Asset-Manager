from decimal import Decimal
from typing import Protocol

from nam_db.models.index import Index
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from nam_yahoo.client import YfinanceClient
from nam_yahoo.errors import YahooDataUnavailableError, YahooSymbolNotFoundError
from nam_yahoo.resolver import YahooIndexResolver


class MarketPriceProvider(Protocol):
    async def get_price(self, isin: str) -> Decimal | None: ...

    async def get_price_for_index(
        self,
        session: AsyncSession,
        index: Index,
    ) -> Decimal | None: ...


class StubMarketPriceProvider:
    async def get_price(self, isin: str) -> Decimal | None:
        return None

    async def get_price_for_index(self, session: AsyncSession, index: Index) -> Decimal | None:
        return None


class FakeMarketPriceProvider:
    def __init__(self, prices: dict[str, Decimal]) -> None:
        self._prices = prices

    async def get_price(self, isin: str) -> Decimal | None:
        return self._prices.get(isin)

    async def get_price_for_index(self, session: AsyncSession, index: Index) -> Decimal | None:
        if index.isin in self._prices:
            return self._prices[index.isin]
        if index.yahoo_symbol and index.yahoo_symbol in self._prices:
            return self._prices[index.yahoo_symbol]
        return None


class YfinanceMarketPriceProvider:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        *,
        client: YfinanceClient | None = None,
    ) -> None:
        self._session_factory = session_factory
        self._client = client or YfinanceClient()
        self._resolver = YahooIndexResolver(session_factory, client=self._client)

    async def get_price(self, isin: str) -> Decimal | None:
        async with self._session_factory() as session:
            index = await session.scalar(select(Index).where(Index.isin == isin))
            if index is None:
                return None
            return await self.get_price_for_index(session, index)

    async def get_price_for_index(self, session: AsyncSession, index: Index) -> Decimal | None:
        try:
            if index.yahoo_symbol:
                symbol = index.yahoo_symbol
            else:
                resolved = await self._resolver.resolve(
                    isin=index.isin,
                    index_id=index.id,
                    auto_persist=True,
                )
                symbol = resolved.yahoo_symbol
            fast_info = await self._client.get_fast_info(symbol)
            price = fast_info.get("lastPrice") or fast_info.get("regularMarketPrice")
            if price is None:
                return None
            return Decimal(str(price))
        except (YahooSymbolNotFoundError, YahooDataUnavailableError):
            return None
