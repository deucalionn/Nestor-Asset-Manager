from __future__ import annotations

import logging
from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from nam_agentic.tools.services.boursorama.client import BoursoramaHttpClient
from nam_agentic.tools.services.boursorama.errors import BoursoramaParseError
from nam_agentic.tools.services.boursorama.feeds import SESSION_FEEDS, IngestFeed
from nam_agentic.tools.services.boursorama.list_parser import parse_list_page
from nam_agentic.tools.services.embedding import EmbeddingService, OllamaEmbeddingService
from nam_agentic.tools.services.news_item_store import NewsItemStore, NewsUpsertPayload

logger = logging.getLogger(__name__)


class NewsIngestService:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        client: BoursoramaHttpClient | None = None,
        embedding_service: EmbeddingService | None = None,
    ) -> None:
        self._session_factory = session_factory
        self._client = client or BoursoramaHttpClient()
        self._store = NewsItemStore(embedding_service or OllamaEmbeddingService())

    async def ingest_session(self) -> UUID:
        return await self._ingest_feeds(SESSION_FEEDS)

    async def _ingest_feeds(self, feeds: tuple[IngestFeed, ...]) -> UUID:
        run_id = uuid4()
        fetched_at = datetime.now(UTC)
        upserted = 0
        errors = 0

        for feed in feeds:
            try:
                html = await self._client.get(feed.url)
                entries = parse_list_page(html, page_url=feed.url)
            except (BoursoramaParseError, Exception) as exc:
                errors += 1
                logger.error("Ingest failed for %s: %s", feed.url, exc)
                continue

            async with self._session_factory() as session:
                for entry in entries:
                    await self._store.upsert(
                        session,
                        NewsUpsertPayload(
                            title=entry.title,
                            source_url=entry.source_url,
                            category=feed.category,
                            summary=entry.summary,
                            published_at=entry.published_at,
                            fetched_at=fetched_at,
                            ingest_run_id=run_id,
                        ),
                    )
                    upserted += 1
                await session.commit()

        logger.info(
            "News ingest run_id=%s feeds=%s upserted=%s errors=%s",
            run_id,
            len(feeds),
            upserted,
            errors,
        )
        return run_id
