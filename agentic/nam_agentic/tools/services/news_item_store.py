from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from nam_db.enums import NewsCategory, NewsSource
from nam_db.models.news_item import NewsItem
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from nam_agentic.tools.services.boursorama.urls import (
    classify_url,
    extract_company_ticker_from_news_path,
    validate_boursorama_url,
)
from nam_agentic.tools.services.embedding import EmbeddingService, news_embed_text


@dataclass(frozen=True)
class NewsUpsertPayload:
    title: str
    source_url: str
    category: NewsCategory
    fetched_at: datetime
    summary: str | None = None
    content_markdown: str | None = None
    boursorama_ticker: str | None = None
    published_at: datetime | None = None
    ingest_run_id: UUID | None = None


def infer_news_metadata(url: str) -> tuple[NewsCategory, str | None]:
    _, path = validate_boursorama_url(url)
    kind = classify_url(path)
    if kind == "company_key_figures":
        ticker = path.rstrip("/").split("/")[-1]
        return NewsCategory.COMPANY_NEWS, ticker
    if kind == "company_news_index":
        return NewsCategory.COMPANY_NEWS, extract_company_ticker_from_news_path(path)
    if kind == "article" and path.startswith("/bourse/actualites/"):
        return NewsCategory.MARKETS, None
    return NewsCategory.COMPANY_NEWS, None


class NewsItemStore:
    def __init__(self, embedding_service: EmbeddingService) -> None:
        self._embedding_service = embedding_service

    async def upsert(self, session: AsyncSession, payload: NewsUpsertPayload) -> UUID:
        existing = await session.scalar(
            select(NewsItem).where(NewsItem.source_url == payload.source_url)
        )
        content_markdown = payload.content_markdown
        if content_markdown is None and existing is not None:
            content_markdown = existing.content_markdown

        vector = await self._embedding_service.embed(
            news_embed_text(payload.title, payload.summary, content_markdown)
        )

        update_fields: dict = {
            "title": payload.title,
            "summary": payload.summary,
            "fetched_at": payload.fetched_at,
            "ingest_run_id": payload.ingest_run_id,
            "category": payload.category,
            "content_embedding": vector,
        }
        if payload.content_markdown is not None:
            update_fields["content_markdown"] = payload.content_markdown
        if payload.boursorama_ticker is not None:
            update_fields["boursorama_ticker"] = payload.boursorama_ticker
        if payload.published_at is not None:
            update_fields["published_at"] = payload.published_at

        stmt = (
            insert(NewsItem)
            .values(
                source=NewsSource.BOURSORAMA,
                category=payload.category,
                title=payload.title,
                source_url=payload.source_url,
                summary=payload.summary,
                content_markdown=payload.content_markdown,
                boursorama_ticker=payload.boursorama_ticker,
                published_at=payload.published_at,
                fetched_at=payload.fetched_at,
                ingest_run_id=payload.ingest_run_id,
                content_embedding=vector,
            )
            .on_conflict_do_update(
                index_elements=[NewsItem.source_url],
                set_=update_fields,
            )
            .returning(NewsItem.id)
        )
        return (await session.execute(stmt)).scalar_one()
