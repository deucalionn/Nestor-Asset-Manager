from pathlib import Path
from unittest.mock import AsyncMock

import pytest
from nam_agentic.tools.market.get_etf_composition import GetEtfCompositionTool
from nam_agentic.tools.services.boursorama.client import BoursoramaHttpClient
from nam_agentic.tools.services.boursorama.company_news_parser import parse_company_news_html
from nam_agentic.tools.services.boursorama.errors import BoursoramaRateLimitError
from nam_agentic.tools.services.boursorama.etf_composition_parser import parse_etf_composition_html
from nam_agentic.tools.services.boursorama.list_parser import parse_list_page
from nam_agentic.tools.services.boursorama.page_formatter import PageContentFormatter
from nam_agentic.tools.services.boursorama.resolver import BoursoramaIndexResolver
from nam_agentic.tools.services.boursorama.urls import build_type_aware_urls
from nam_db.enums import IndexType, NewsCategory, NewsSource
from nam_db.models.index import Index
from nam_db.models.news_item import NewsItem
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

pytestmark = pytest.mark.asyncio
FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "boursorama"


def _read(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


async def test_list_parser_markets_fixture() -> None:
    entries = parse_list_page(_read("markets_list.html"), page_url="https://example/marches/")
    assert len(entries) == 1
    assert entries[0].title == "Wall Street ouvre en hausse"
    assert entries[0].source_url.startswith("https://www.boursorama.com/")


async def test_list_parser_global_hub_fixture() -> None:
    entries = parse_list_page(_read("global_hub.html"), page_url="https://example/hub/")
    assert entries[0].title == "Les marchés européens en hausse"


async def test_company_news_parser_fixture() -> None:
    headlines = parse_company_news_html(
        _read("company_news_partial.html"),
        page_url="https://example/partial/",
    )
    assert headlines[0].title.startswith("Air Liquide")
    assert "Quobly" in headlines[0].summary
    assert headlines[0].article_url.endswith("abc123")


async def test_etf_composition_parser_fixture() -> None:
    rows = parse_etf_composition_html(
        _read("etf_composition.html"),
        page_url="https://example/etf/",
    )
    assert len(rows) == 3
    assert rows[0].weight_pct == 9.0
    assert rows[2].boursorama_ticker == "1rPMSFT"


async def test_http_client_rate_limit() -> None:
    import time

    BoursoramaHttpClient.reset_singleton()
    client = BoursoramaHttpClient()
    now = time.monotonic()
    client._request_times.extend([now - i for i in range(12)])  # noqa: SLF001
    with pytest.raises(BoursoramaRateLimitError):
        client._check_budget()  # noqa: SLF001


async def test_build_type_aware_urls() -> None:
    company = build_type_aware_urls("1rPAI", IndexType.COMPANY)
    assert company["news_url"] is not None
    assert company["composition_url"] is None

    etf = build_type_aware_urls("1rTPUST", IndexType.ETF)
    assert etf["composition_url"] is not None
    assert etf["news_url"] is None


async def test_resolver_db_cache_hit(session_factory: async_sessionmaker[AsyncSession]) -> None:
    async with session_factory() as session:
        index = Index(
            name="Air Liquide",
            isin="FR0000120071",
            index_type=IndexType.COMPANY,
            boursorama_ticker="1rPAI",
        )
        session.add(index)
        await session.commit()
        await session.refresh(index)
        index_id = index.id

    resolver = BoursoramaIndexResolver(session_factory, client=AsyncMock())
    resolved = await resolver.resolve(index_id=index_id)
    assert resolved.resolved_from_db is True
    assert resolved.boursorama_ticker == "1rPAI"


async def test_get_etf_composition_rejects_company(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with session_factory() as session:
        index = Index(name="Air Liquide", isin="FR0000120071", index_type=IndexType.COMPANY)
        session.add(index)
        await session.commit()
        await session.refresh(index)
        index_id = index.id

    tool = GetEtfCompositionTool(session_factory, client=AsyncMock()).as_tool()
    with pytest.raises(Exception, match="ETF"):
        await tool.ainvoke({"index_id": str(index_id)})


async def test_page_formatter_empty_raises() -> None:
    formatter = PageContentFormatter()
    with pytest.raises(Exception):
        await formatter.format(
            url="https://www.boursorama.com/bourse/actualites/x/",
            html="<html></html>",
        )


async def test_news_ingest_upsert_idempotent(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    from nam_agentic.tools.services.boursorama.feeds import IngestFeed
    from nam_agentic.tools.services.boursorama.ingest import NewsIngestService
    from support.helpers import MockEmbeddingService

    entries = parse_list_page(_read("markets_list.html"), page_url="https://example/marches/")
    mock_client = AsyncMock()
    mock_client.get.return_value = _read("markets_list.html")
    feed = (IngestFeed("/bourse/actualites/marches/", NewsCategory.MARKETS),)

    service = NewsIngestService(
        session_factory,
        client=mock_client,
        embedding_service=MockEmbeddingService(),
    )
    await service._ingest_feeds(feed)  # noqa: SLF001
    await service._ingest_feeds(feed)  # noqa: SLF001

    async with session_factory() as session:
        count = await session.scalar(select(func.count()).select_from(NewsItem))
        assert count == len(entries)
        row = await session.scalar(
            select(NewsItem).where(NewsItem.source_url == entries[0].source_url)
        )
    assert row is not None
    assert row.content_embedding is not None


async def test_news_item_store_preserves_markdown_on_headline_refresh(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    from datetime import UTC, datetime

    from nam_agentic.tools.services.news_item_store import NewsItemStore, NewsUpsertPayload
    from support.helpers import MockEmbeddingService

    store = NewsItemStore(MockEmbeddingService())
    fetched_at = datetime.now(UTC)
    url = "https://www.boursorama.com/bourse/actualites/test-article/"

    async with session_factory() as session:
        await store.upsert(
            session,
            NewsUpsertPayload(
                title="Article title",
                source_url=url,
                category=NewsCategory.MARKETS,
                content_markdown="# Full body",
                fetched_at=fetched_at,
            ),
        )
        await store.upsert(
            session,
            NewsUpsertPayload(
                title="Article title (cron)",
                source_url=url,
                category=NewsCategory.MARKETS,
                summary="Teaser from list page",
                fetched_at=fetched_at,
            ),
        )
        await session.commit()
        row = await session.scalar(select(NewsItem).where(NewsItem.source_url == url))

    assert row is not None
    assert row.content_markdown == "# Full body"
    assert row.summary == "Teaser from list page"
    assert row.content_embedding is not None
    assert len(row.content_embedding) == 384


async def test_get_data_from_url_persists_article(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    from datetime import UTC, datetime

    from nam_agentic.tools.market.get_data_from_url import GetDataFromUrlTool
    from nam_agentic.tools.services.boursorama.page_reader import ArticlePage, PageReader
    from support.helpers import MockEmbeddingService, as_dict

    fetched_at = datetime.now(UTC)
    url = "https://www.boursorama.com/bourse/actualites/wall-street-ouvre/"
    reader = PageReader(client=AsyncMock())
    reader.read = AsyncMock(  # type: ignore[method-assign]
        return_value=ArticlePage(
            url=url,
            title="Wall Street ouvre en hausse",
            markdown="# Wall Street\n\nLe marché progresse.",
            fetched_at=fetched_at,
        )
    )

    tool = GetDataFromUrlTool(
        session_factory,
        page_reader=reader,
        embedding_service=MockEmbeddingService(),
    ).as_tool()
    result = as_dict(await tool.ainvoke({"url": url}))

    assert result["persisted"] is True
    assert result["news_item_id"] is not None
    assert result["content_type"] == "article"

    async with session_factory() as session:
        row = await session.scalar(select(NewsItem).where(NewsItem.source_url == url))
    assert row is not None
    assert row.content_markdown is not None
    assert row.content_embedding is not None


async def test_get_financials_news_semantic_search(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    from datetime import UTC, datetime

    from nam_agentic.tools.market.get_financials_news_from_bourso import (
        GetFinancialsNewsFromBoursoTool,
    )
    from support.helpers import MockEmbeddingService, as_dict

    vector = [1.0] + [0.0] * 383
    fetched_at = datetime.now(UTC)

    async with session_factory() as session:
        session.add(
            NewsItem(
                source=NewsSource.BOURSORAMA,
                category=NewsCategory.MARKETS,
                title="BCE et inflation",
                source_url="https://www.boursorama.com/bourse/actualites/bce-inflation/",
                summary="La BCE surveille l'inflation.",
                fetched_at=fetched_at,
                content_embedding=vector,
            )
        )
        await session.commit()

    tool = GetFinancialsNewsFromBoursoTool(
        session_factory,
        embedding_service=MockEmbeddingService(vector=vector),
    ).as_tool()
    result = as_dict(
        await tool.ainvoke(
            {
                "semantic_query": "inflation BCE",
                "since_hours": 48,
                "min_similarity": 0.7,
            }
        )
    )

    assert result["count"] == 1
    assert result["items"][0]["title"] == "BCE et inflation"
    assert result["items"][0]["similarity_score"] == pytest.approx(1.0)
