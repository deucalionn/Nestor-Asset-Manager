from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from nam_db.enums import IndexType

from nam_agentic.tools.services.boursorama.client import BoursoramaHttpClient
from nam_agentic.tools.services.boursorama.company_news_parser import (
    CompanyNewsHeadline,
    parse_company_news_html,
)
from nam_agentic.tools.services.boursorama.list_parser import parse_list_page
from nam_agentic.tools.services.boursorama.page_formatter import PageContentFormatter
from nam_agentic.tools.services.boursorama.urls import (
    classify_url,
    company_news_partial_url,
    extract_company_ticker_from_news_path,
    normalize_boursorama_url,
    validate_boursorama_url,
)


@dataclass(frozen=True)
class NewsIndexPage:
    url: str
    title: str
    headlines: list[CompanyNewsHeadline]
    fetched_at: datetime


@dataclass(frozen=True)
class ArticlePage:
    url: str
    title: str
    markdown: str
    fetched_at: datetime


class PageReader:
    def __init__(
        self,
        client: BoursoramaHttpClient | None = None,
        formatter: PageContentFormatter | None = None,
    ) -> None:
        self._client = client or BoursoramaHttpClient()
        self._formatter = formatter or PageContentFormatter()

    async def read(
        self,
        url: str,
        *,
        index_type: IndexType | None = None,
    ) -> NewsIndexPage | ArticlePage:
        normalized = normalize_boursorama_url(url)
        _, path = validate_boursorama_url(normalized)
        kind = classify_url(path)
        fetched_at = datetime.now(UTC)

        if kind == "company_news_index":
            if index_type == IndexType.ETF:
                msg = (
                    "ETF indices have no company news page — "
                    "use get_etf_composition and global news."
                )
                raise ValueError(msg)
            ticker = extract_company_ticker_from_news_path(path)
            if not ticker:
                raise ValueError(f"Could not extract ticker from {url}")
            partial_url = company_news_partial_url(ticker)
            html = await self._client.get(partial_url, referer=normalized)
            headlines = parse_company_news_html(html, page_url=partial_url)
            return NewsIndexPage(
                url=normalized,
                title=f"Actualités {ticker}",
                headlines=headlines,
                fetched_at=fetched_at,
            )

        if kind == "global_hub":
            html = await self._client.get(normalized)
            entries = parse_list_page(html, page_url=normalized)
            headlines = [
                CompanyNewsHeadline(
                    title=e.title,
                    summary=e.summary or e.title,
                    article_url=e.source_url,
                    published_at=e.published_at,
                    attribution=e.attribution,
                )
                for e in entries
            ]
            return NewsIndexPage(
                url=normalized,
                title="Actualités Boursorama",
                headlines=headlines,
                fetched_at=fetched_at,
            )

        html = await self._client.get(normalized)
        page_hint = "company_key_figures" if kind == "company_key_figures" else "article"
        title, markdown = await self._formatter.format(
            url=normalized,
            html=html,
            page_hint=page_hint if kind != "generic" else "generic",
        )
        return ArticlePage(url=normalized, title=title, markdown=markdown, fetched_at=fetched_at)
