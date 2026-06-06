from decimal import Decimal
from typing import Protocol


class MarketPriceProvider(Protocol):
    async def get_price(self, isin: str) -> Decimal | None: ...


class StubMarketPriceProvider:
    async def get_price(self, isin: str) -> Decimal | None:
        return None


class FakeMarketPriceProvider:
    def __init__(self, prices: dict[str, Decimal]) -> None:
        self._prices = prices

    async def get_price(self, isin: str) -> Decimal | None:
        return self._prices.get(isin)
