from __future__ import annotations

import re
from dataclasses import dataclass
from html import unescape
from urllib.parse import quote

from selectolax.parser import HTMLParser

from nam_agentic.tools.services.boursorama.client import BoursoramaHttpClient
from nam_agentic.tools.services.boursorama.errors import BoursoramaParseError


@dataclass(frozen=True)
class SearchHit:
    ticker: str
    name: str
    is_company: bool


_TICKER_FROM_COURS = re.compile(r"/cours/([^/]+)/?")
_TICKER_FROM_TRACKER = re.compile(r"/bourse/trackers/cours/([^/]+)/?")


def _hit_from_path(path_or_url: str) -> SearchHit | None:
    if not path_or_url:
        return None
    tracker = _TICKER_FROM_TRACKER.search(path_or_url)
    if tracker:
        return SearchHit(ticker=tracker.group(1), name=tracker.group(1), is_company=False)
    cours = _TICKER_FROM_COURS.search(path_or_url)
    if cours:
        return SearchHit(ticker=cours.group(1), name=cours.group(1), is_company=True)
    return None


def _parse_instruments_html(html: str) -> SearchHit | None:
    tree = HTMLParser(html)
    for link in tree.css("a[href]"):
        href = link.attributes.get("href", "")
        hit = _hit_from_path(href)
        if hit is None:
            continue
        name = unescape(link.text(strip=True)) or hit.name
        return SearchHit(ticker=hit.ticker, name=name, is_company=hit.is_company)
    return None


async def search_boursorama(
    client: BoursoramaHttpClient,
    *,
    query: str | None = None,
    isin: str | None = None,
) -> SearchHit:
    term = (query or isin or "").strip()
    if not term:
        raise BoursoramaParseError("Search term is empty")

    redirect_url = f"https://www.boursorama.com/recherche/?query={quote(term)}"
    location = await client.get_redirect_location(redirect_url)
    if location:
        hit = _hit_from_path(location)
        if hit is not None:
            return hit

    partial_url = f"https://www.boursorama.com/recherche/_instruments/{quote(term)}"
    html = await client.get(partial_url)
    hit = _parse_instruments_html(html)
    if hit is None:
        raise BoursoramaParseError(f"No Boursorama match for: {term}")
    return hit