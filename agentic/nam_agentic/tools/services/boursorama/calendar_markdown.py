from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from nam_db.enums import NewsCategory

from nam_agentic.tools.services.boursorama.calendar_parser import (
    ParsedCalendarRow,
    importance_stars,
)
from nam_agentic.tools.services.boursorama.feeds import CALENDAR_FEEDS, IngestFeed


def render_calendar_markdown(
    sections: list[tuple[NewsCategory, str, list[ParsedCalendarRow]]],
    *,
    fetched_at: datetime,
    timezone: str,
) -> str:
    tz = ZoneInfo(timezone)
    local_now = fetched_at.astimezone(tz)
    lines = [
        f"# Market calendar — {local_now.date().isoformat()} ({timezone})",
        "",
        f"_fetched_at: {local_now.isoformat()}_",
        "",
    ]
    for category, source_url, rows in sections:
        lines.append(f"## {category.value}")
        lines.append(f"_source: {source_url}_")
        lines.append("")
        if not rows:
            lines.append("_No events parsed._")
            lines.append("")
            continue
        lines.append("| Time | Event | Previous | Last | Importance |")
        lines.append("|------|-------|----------|------|------------|")
        for row in rows:
            lines.append(
                "| {time} | {event} | {previous} | {last} | {importance} |".format(
                    time=row.time or "—",
                    event=_escape_md_cell(row.event),
                    previous=row.previous or "—",
                    last=row.last or "—",
                    importance=importance_stars(row.importance),
                )
            )
        lines.append("")
    return "\n".join(lines).strip() + "\n"


def _escape_md_cell(value: str) -> str:
    return value.replace("|", "\\|")


def feeds_for_categories(
    categories: list[NewsCategory] | None,
) -> tuple[IngestFeed, ...]:
    if not categories:
        return CALENDAR_FEEDS
    allowed = set(categories)
    return tuple(feed for feed in CALENDAR_FEEDS if feed.category in allowed)
