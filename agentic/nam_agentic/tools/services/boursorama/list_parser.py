from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import UTC, datetime
from html import unescape

from selectolax.parser import HTMLParser

from nam_agentic.tools.services.boursorama.errors import BoursoramaParseError
from nam_agentic.tools.services.boursorama.urls import absolute_boursorama_url


@dataclass(frozen=True)
class ListNewsEntry:
    title: str
    source_url: str
    summary: str | None
    published_at: datetime | None
    attribution: str | None


def _parse_source_times(node) -> datetime | None:
    times = [t.text(strip=True) for t in node.css(".c-source__time")]
    if not times:
        return None
    for token in times:
        if re.fullmatch(r"\d{2}\.\d{2}\.\d{4}", token):
            try:
                return datetime.strptime(token, "%d.%m.%Y").replace(tzinfo=UTC)
            except ValueError:
                continue
        if re.fullmatch(r"\d{2}:\d{2}", token):
            continue
    return None


def _extract_summary(container) -> str | None:
    noscript = container.css_first("noscript")
    if noscript is not None:
        alt = noscript.attributes.get("alt") or noscript.text(strip=True)
        if alt:
            return unescape(alt.strip())
    h2 = container.css_first("h2.c-event__link")
    if h2 is not None:
        return unescape(h2.text(strip=True))
    return None


def parse_list_page(html: str, *, page_url: str) -> list[ListNewsEntry]:
    """Parse Boursorama list/hub pages (markets, finances, calendars)."""
    tree = HTMLParser(html)
    body = tree.body
    if body is None:
        raise BoursoramaParseError("No body in list page HTML")

    entries: list[ListNewsEntry] = []
    seen_urls: set[str] = set()

    for container in body.css(".c-headlines__article-container"):
        link = container.css_first("a.c-headlines[href]")
        if link is None:
            continue
        href = link.attributes.get("href", "").strip()
        h2 = link.css_first("h2")
        title = unescape(link.attributes.get("title") or (h2.text(strip=True) if h2 else ""))
        if not href or not title:
            continue
        normalized_href = href.rstrip("/")
        if "page-" in href or normalized_href.endswith(("/marches", "/finances")):
            continue
        source_url = absolute_boursorama_url(href)
        if source_url in seen_urls:
            continue
        seen_urls.add(source_url)
        attribution_node = container.css_first(".c-source__name")
        entries.append(
            ListNewsEntry(
                title=title,
                source_url=source_url,
                summary=_extract_summary(container),
                published_at=_parse_source_times(container),
                attribution=(
                    unescape(attribution_node.text(strip=True)) if attribution_node else None
                ),
            )
        )

    if not entries:
        raise BoursoramaParseError(f"No list entries parsed from {page_url}")
    return entries
