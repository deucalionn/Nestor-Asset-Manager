from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import UTC, datetime
from html import unescape

from selectolax.parser import HTMLParser

from nam_agentic.tools.services.boursorama.errors import BoursoramaParseError
from nam_agentic.tools.services.boursorama.urls import absolute_boursorama_url


@dataclass(frozen=True)
class CompanyNewsHeadline:
    title: str
    summary: str
    article_url: str
    published_at: datetime | None
    attribution: str | None


def _parse_published_at(line_node) -> datetime | None:
    times = [t.text(strip=True) for t in line_node.css(".c-source__time")]
    date_value: datetime | None = None
    for token in times:
        if re.fullmatch(r"\d{2}\.\d{2}\.\d{4}", token):
            try:
                date_value = datetime.strptime(token, "%d.%m.%Y").replace(tzinfo=UTC)
            except ValueError:
                continue
    return date_value


def _clean_summary(raw: str) -> str:
    text = unescape(raw)
    text = re.sub(r"\s*Lire la suite\s*$", "", text, flags=re.IGNORECASE)
    return " ".join(text.split())


def parse_company_news_html(html: str, *, page_url: str) -> list[CompanyNewsHeadline]:
    """Parse company news partial/list HTML into structured headlines."""
    tree = HTMLParser(html)
    headlines: list[CompanyNewsHeadline] = []
    seen_urls: set[str] = set()

    for line in tree.css("li.c-list-details-news__line"):
        title_link = line.css_first(".c-list-details-news__title a[href]")
        if title_link is None:
            continue
        href = title_link.attributes.get("href", "").strip()
        title = unescape(title_link.text(strip=True))
        if not href or not title or title.lower() == "lire la suite":
            continue
        article_url = absolute_boursorama_url(href)
        if article_url in seen_urls:
            continue
        seen_urls.add(article_url)

        content = line.css_first("p.c-list-details-news__content")
        summary = _clean_summary(content.text()) if content is not None else title
        attribution_node = line.css_first(".c-source__name")
        headlines.append(
            CompanyNewsHeadline(
                title=title,
                summary=summary,
                article_url=article_url,
                published_at=_parse_published_at(line),
                attribution=(
                    unescape(attribution_node.text(strip=True)) if attribution_node else None
                ),
            )
        )

    if not headlines:
        raise BoursoramaParseError(f"No company headlines parsed from {page_url}")
    return headlines
