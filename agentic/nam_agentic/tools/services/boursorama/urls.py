from __future__ import annotations

import re
from urllib.parse import urlparse

from nam_db.enums import IndexType

BOURSORAMA_HOST = "www.boursorama.com"
BOURSOBANK_HOST = "bourse.boursobank.com"
ALLOWED_HOSTS = frozenset({BOURSORAMA_HOST, BOURSOBANK_HOST})
ALLOWED_PATH_PREFIXES = ("/bourse/", "/cours/")

_COMPANY_NEWS_RE = re.compile(r"^/cours/actualites/([^/]+)/?$")
_COMPANY_KEY_FIGURES_RE = re.compile(r"^/cours/societe/chiffres-cles/([^/]+)/?$")
_GLOBAL_HUB_RE = re.compile(r"^/bourse/actualites/?$")
_ARTICLE_RE = re.compile(r"^/bourse/actualites/[^/]+/?$")
_ETF_COMPOSITION_RE = re.compile(r"^/bourse/trackers/cours/composition/([^/]+)/?$")


def normalize_boursorama_url(url: str) -> str:
    parsed = urlparse(url.strip())
    if not parsed.scheme or not parsed.netloc:
        msg = f"URL must be absolute: {url}"
        raise ValueError(msg)
    return parsed._replace(fragment="", query="").geturl()


def validate_boursorama_url(url: str) -> tuple[str, str]:
    """Return (host, path) when URL is whitelisted."""
    parsed = urlparse(normalize_boursorama_url(url))
    host = parsed.netloc.lower()
    if host not in ALLOWED_HOSTS:
        msg = f"Host not allowed: {host}"
        raise ValueError(msg)
    path = parsed.path or "/"
    if not path.startswith(ALLOWED_PATH_PREFIXES):
        msg = f"Path not allowed: {path}"
        raise ValueError(msg)
    return host, path


def absolute_boursorama_url(path: str, *, host: str = BOURSORAMA_HOST) -> str:
    if path.startswith("http"):
        return normalize_boursorama_url(path)
    return f"https://{host}{path}"


def build_type_aware_urls(ticker: str, index_type: IndexType) -> dict[str, str | None]:
    if index_type == IndexType.COMPANY:
        return {
            "quote_url": absolute_boursorama_url(f"/cours/{ticker}/"),
            "news_url": absolute_boursorama_url(f"/cours/actualites/{ticker}/"),
            "key_figures_url": absolute_boursorama_url(f"/cours/societe/chiffres-cles/{ticker}/"),
            "composition_url": None,
        }
    return {
        "quote_url": absolute_boursorama_url(f"/bourse/trackers/cours/{ticker}/"),
        "composition_url": absolute_boursorama_url(f"/bourse/trackers/cours/composition/{ticker}/"),
        "news_url": None,
        "key_figures_url": None,
    }


def company_news_partial_url(ticker: str) -> str:
    return (
        "https://www.boursorama.com/actualites/_liste"
        "?offset=0&limit=60&filter=news&page=1"
        f"&symbol={ticker}&_stateless=1&_route=news.list.partial"
    )


def classify_url(path: str) -> str:
    if _COMPANY_NEWS_RE.match(path):
        return "company_news_index"
    if _GLOBAL_HUB_RE.match(path):
        return "global_hub"
    if _COMPANY_KEY_FIGURES_RE.match(path):
        return "company_key_figures"
    if _ETF_COMPOSITION_RE.match(path):
        return "etf_composition"
    if _ARTICLE_RE.match(path):
        return "article"
    return "generic"


def extract_company_ticker_from_news_path(path: str) -> str | None:
    match = _COMPANY_NEWS_RE.match(path)
    return match.group(1) if match else None
