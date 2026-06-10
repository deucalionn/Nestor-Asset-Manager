from decimal import Decimal
from unittest.mock import AsyncMock, patch

import pandas as pd
import pytest
from nam_agentic.tools.market.get_asset_price_from_yf import GetAssetPriceFromYfTool
from nam_agentic.tools.market.get_company_financials_from_yf import GetCompanyFinancialsFromYfTool
from nam_agentic.tools.market.yahoo_helpers import (
    normalize_yahoo_news_item,
    normalize_yahoo_news_items,
)
from nam_agentic.tools.schemas.market import GetAssetNewsFromYfInput
from nam_db.enums import IndexType
from nam_db.models.index import Index
from nam_yahoo import (
    YahooIndexResolver,
    YahooSymbolNotFoundError,
    YfinanceClient,
    YfinanceMarketPriceProvider,
)
from nam_yahoo.lookup import dataframe_to_lookup_rows, pick_lookup_row
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

pytestmark = pytest.mark.asyncio


def _lookup_df() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "exchange": "PAR",
                "quoteType": "equity",
                "shortName": "AIR LIQUIDE",
                "regularMarketPrice": 168.0,
            },
            {
                "exchange": "DUS",
                "quoteType": "equity",
                "shortName": "AIR LIQUIDE DU",
                "regularMarketPrice": 168.0,
            },
        ],
        index=["AI.PA", "AILA.DU"],
    )


async def test_yahoo_resolver_db_cache_hit(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with session_factory() as session:
        index = Index(
            name="Air Liquide",
            isin="FR0000120073",
            index_type=IndexType.COMPANY,
            yahoo_symbol="AI.PA",
        )
        session.add(index)
        await session.commit()
        await session.refresh(index)
        index_id = index.id

    client = AsyncMock(spec=YfinanceClient)
    resolver = YahooIndexResolver(session_factory, client=client)
    resolved = await resolver.resolve(index_id=index_id)

    assert resolved.resolved_from_db is True
    assert resolved.yahoo_symbol == "AI.PA"
    client.lookup.assert_not_called()


async def test_yahoo_resolver_auto_persist(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with session_factory() as session:
        index = Index(
            name="Air Liquide",
            isin="FR0000120073",
            index_type=IndexType.COMPANY,
        )
        session.add(index)
        await session.commit()
        await session.refresh(index)
        index_id = index.id

    client = AsyncMock(spec=YfinanceClient)
    client.lookup.return_value = _lookup_df()
    resolver = YahooIndexResolver(session_factory, client=client)
    resolved = await resolver.resolve(index_id=index_id)

    assert resolved.resolved_from_db is False
    assert resolved.yahoo_symbol == "AI.PA"

    async with session_factory() as session:
        row = await session.get(Index, index_id)
    assert row is not None
    assert row.yahoo_symbol == "AI.PA"


def test_filter_news_by_company_name_drops_generic_titles() -> None:
    from nam_agentic.tools.market.yahoo_helpers import filter_news_by_company_name

    items = [
        {"title": "Bolt, Pony.ai and Stellantis launch AV pilot", "link": "a"},
        {"title": "2 Cheap Stocks to Buy Now", "link": "b"},
        {"title": "Stellantis recalls vehicles in the US", "link": "c"},
    ]
    filtered = filter_news_by_company_name(items, company_name="STELLANTIS", limit=5)
    titles = [item["title"] for item in filtered]
    assert "2 Cheap Stocks to Buy Now" not in titles
    assert any("Stellantis" in title for title in titles)


def test_yahoo_identity_input_strips_na_and_keeps_symbol() -> None:
    parsed = GetAssetNewsFromYfInput(isin="N/A", yahoo_symbol="STLA", limit=5)
    assert parsed.yahoo_symbol == "STLA"
    assert parsed.isin is None
    assert parsed.limit == 5


def test_normalize_yahoo_news_item_nested_content() -> None:
    item = {
        "id": "abc",
        "content": {
            "title": "Bolt, Pony.ai and Stellantis launch AV pilot in Luxembourg",
            "pubDate": "2026-06-10T10:14:54Z",
            "provider": {"displayName": "Just Auto"},
            "clickThroughUrl": {
                "url": "https://finance.yahoo.com/sectors/technology/articles/stellantis.html",
            },
        },
    }
    row = normalize_yahoo_news_item(item)
    assert row is not None
    assert "Stellantis" in row["title"]
    assert row["publisher"] == "Just Auto"
    assert row["link"].endswith("stellantis.html")


def test_normalize_yahoo_news_item_legacy_flat() -> None:
    row = normalize_yahoo_news_item(
        {
            "title": "Stellantis Recalls Vehicles",
            "link": "https://finance.yahoo.com/news/stellantis.html",
            "publisher": "Reuters",
            "providerPublishTime": 1_700_000_000,
        }
    )
    assert row is not None
    assert row["title"] == "Stellantis Recalls Vehicles"
    assert row["publisher"] == "Reuters"


def test_normalize_yahoo_news_items_caps_limit() -> None:
    items = [
        {"title": f"Headline {i}", "link": f"https://example.com/{i}"}
        for i in range(5)
    ]
    rows = normalize_yahoo_news_items(items, limit=2)
    assert len(rows) == 2


async def test_pick_lookup_row_prefers_pa_suffix() -> None:
    rows = dataframe_to_lookup_rows(_lookup_df())
    hit = pick_lookup_row(rows, prefer_suffix=".PA")
    assert hit.yahoo_symbol == "AI.PA"


async def test_pick_lookup_row_ambiguous_raises() -> None:
    df = pd.DataFrame(
        [
            {"exchange": "PAR", "quoteType": "equity", "shortName": "A"},
            {"exchange": "PAR", "quoteType": "equity", "shortName": "B"},
        ],
        index=["AAA.PA", "BBB.PA"],
    )
    rows = dataframe_to_lookup_rows(df)
    with pytest.raises(YahooSymbolNotFoundError, match="Ambiguous"):
        pick_lookup_row(rows, prefer_suffix=".PA")


async def test_pick_lookup_row_prefers_milan_over_isin_style_ticker() -> None:
    df = pd.DataFrame(
        [
            {"exchange": "MIL", "quoteType": "equity", "shortName": "STELLANTIS"},
            {"exchange": "STU", "quoteType": "equity", "shortName": "Stellantis N.V."},
        ],
        index=["STLAM.MI", "NL00150001Q9.SG"],
    )
    rows = dataframe_to_lookup_rows(df)
    hit = pick_lookup_row(rows, prefer_suffix=".PA")
    assert hit.yahoo_symbol == "STLAM.MI"


async def test_yahoo_resolver_stellantis_isin_lookup(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with session_factory() as session:
        index = Index(
            name="STELLANTIS",
            isin="NL00150001Q9",
            index_type=IndexType.COMPANY,
        )
        session.add(index)
        await session.commit()
        await session.refresh(index)
        index_id = index.id

    stellantis_df = pd.DataFrame(
        [
            {"exchange": "MIL", "quoteType": "equity", "shortName": "STELLANTIS"},
            {"exchange": "STU", "quoteType": "equity", "shortName": "Stellantis N.V."},
        ],
        index=["STLAM.MI", "NL00150001Q9.SG"],
    )
    client = AsyncMock(spec=YfinanceClient)
    client.lookup.return_value = stellantis_df
    resolver = YahooIndexResolver(session_factory, client=client)
    resolved = await resolver.resolve(index_id=index_id)

    assert resolved.yahoo_symbol == "STLAM.MI"
    client.lookup.assert_awaited_once_with("NL00150001Q9")


async def test_yfinance_client_uses_to_thread() -> None:
    client = YfinanceClient()
    with patch(
        "nam_yahoo.client.asyncio.to_thread",
        new_callable=AsyncMock,
    ) as mock_thread:
        mock_thread.return_value = _lookup_df()
        result = await client.lookup("Air Liquide")
        mock_thread.assert_awaited_once()
    assert not result.empty


async def test_yfinance_market_price_provider(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with session_factory() as session:
        session.add(
            Index(
                name="Air Liquide",
                isin="FR0000120073",
                index_type=IndexType.COMPANY,
                yahoo_symbol="AI.PA",
            )
        )
        await session.commit()

    client = AsyncMock(spec=YfinanceClient)
    client.get_fast_info.return_value = {"lastPrice": 168.42, "currency": "EUR"}
    provider = YfinanceMarketPriceProvider(session_factory, client=client)

    price = await provider.get_price("FR0000120073")
    assert price == Decimal("168.42")


async def test_yfinance_market_price_provider_missing_symbol_returns_none(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    client = AsyncMock(spec=YfinanceClient)
    client.lookup.return_value = pd.DataFrame()
    provider = YfinanceMarketPriceProvider(session_factory, client=client)

    price = await provider.get_price("FR0000999999")
    assert price is None


async def test_get_asset_price_from_yf(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    client = AsyncMock(spec=YfinanceClient)
    client.get_fast_info.return_value = {
        "lastPrice": 100.0,
        "previousClose": 99.0,
        "currency": "EUR",
    }
    tool = GetAssetPriceFromYfTool(session_factory, client=client).as_tool()
    result = await tool.ainvoke({"yahoo_symbol": "AI.PA"})

    assert result.yahoo_symbol == "AI.PA"
    assert result.last_price == Decimal("100.0")
    client.lookup.assert_not_called()


async def test_get_asset_price_validation_error(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    tool = GetAssetPriceFromYfTool(session_factory, client=AsyncMock()).as_tool()
    with pytest.raises(Exception):
        await tool.ainvoke({"isin": "FR0000120073", "yahoo_symbol": "AI.PA"})


async def test_get_company_financials_rejects_etf(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with session_factory() as session:
        index = Index(
            name="Amundi MSCI World",
            isin="FR0010315770",
            index_type=IndexType.ETF,
            yahoo_symbol="CW8.PA",
        )
        session.add(index)
        await session.commit()
        await session.refresh(index)
        index_id = index.id

    tool = GetCompanyFinancialsFromYfTool(session_factory, client=AsyncMock()).as_tool()
    with pytest.raises(Exception, match="COMPANY"):
        await tool.ainvoke({"index_id": str(index_id)})
