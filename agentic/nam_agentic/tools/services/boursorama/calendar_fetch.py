from __future__ import annotations

import logging
from datetime import UTC, datetime

from nam_db.enums import NewsCategory

from nam_agentic.settings import settings
from nam_agentic.tools.schemas.market import (
    CalendarEventRow,
    CalendarSectionOutput,
    FetchCalendarFromBoursoOutput,
)
from nam_agentic.tools.services.boursorama.calendar_markdown import (
    feeds_for_categories,
    render_calendar_markdown,
)
from nam_agentic.tools.services.boursorama.calendar_parser import parse_calendar_page
from nam_agentic.tools.services.boursorama.client import BoursoramaHttpClient
from nam_agentic.tools.services.boursorama.feeds import IngestFeed

logger = logging.getLogger(__name__)


class CalendarFetchService:
    def __init__(self, client: BoursoramaHttpClient | None = None) -> None:
        self._client = client or BoursoramaHttpClient()

    async def fetch(
        self,
        *,
        include_categories: list[NewsCategory] | None = None,
    ) -> FetchCalendarFromBoursoOutput:
        fetched_at = datetime.now(UTC)
        feeds = feeds_for_categories(include_categories)
        section_payloads: list[tuple[NewsCategory, str, list]] = []
        sections: list[CalendarSectionOutput] = []

        for feed in feeds:
            rows = await self._fetch_feed(feed)
            section_payloads.append((feed.category, feed.url, rows))
            sections.append(
                CalendarSectionOutput(
                    category=feed.category,
                    source_url=feed.url,
                    rows=[
                        CalendarEventRow(
                            time=row.time,
                            event=row.event,
                            previous=row.previous,
                            last=row.last,
                            importance=row.importance,
                        )
                        for row in rows
                    ],
                )
            )

        markdown = render_calendar_markdown(
            section_payloads,
            fetched_at=fetched_at,
            timezone=settings.market_timezone,
        )
        return FetchCalendarFromBoursoOutput(
            markdown=markdown,
            fetched_at=fetched_at,
            sections=sections,
        )

    async def _fetch_feed(self, feed: IngestFeed):
        try:
            html = await self._client.get(feed.url)
            return parse_calendar_page(html, page_url=feed.url)
        except Exception as exc:
            logger.warning("Calendar fetch failed for %s: %s", feed.url, exc)
            return []
