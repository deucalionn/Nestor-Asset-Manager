from __future__ import annotations

import asyncio
import logging
import random
import time
from collections import deque
from urllib.parse import urlparse

import httpx

from nam_agentic.settings import settings
from nam_agentic.tools.services.boursorama.errors import (
    BoursoramaRateLimitError,
    BoursoramaUrlError,
)
from nam_agentic.tools.services.boursorama.urls import ALLOWED_HOSTS, ALLOWED_PATH_PREFIXES

logger = logging.getLogger(__name__)

DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
)


class BoursoramaHttpClient:
    """Singleton polite HTTP client for Boursorama hosts."""

    _instance: BoursoramaHttpClient | None = None

    def __new__(cls) -> BoursoramaHttpClient:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self) -> None:
        if getattr(self, "_initialized", False):
            return
        self._semaphore = asyncio.Semaphore(1)
        self._request_times: deque[float] = deque()
        self._client = httpx.AsyncClient(
            follow_redirects=True,
            timeout=httpx.Timeout(connect=10.0, read=30.0, write=10.0, pool=10.0),
            headers=self._default_headers(),
        )
        self._initialized = True

    @classmethod
    def reset_singleton(cls) -> None:
        """Test helper — drop cached client instance."""
        cls._instance = None

    def _default_headers(self) -> dict[str, str]:
        return {
            "User-Agent": settings.boursorama_user_agent or DEFAULT_USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "fr-FR,fr;q=0.9,en;q=0.8",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
        }

    def _validate_url(self, url: str) -> None:
        parsed = urlparse(url)
        host = parsed.netloc.lower()
        if host not in ALLOWED_HOSTS:
            raise BoursoramaUrlError(f"Host not allowed: {host}")
        path = parsed.path or "/"
        allowed = (
            path.startswith(ALLOWED_PATH_PREFIXES)
            or path.startswith("/actualites/")
            or path.startswith("/recherche/")
        )
        if not allowed:
            raise BoursoramaUrlError(f"Path not allowed: {path}")

    def _check_budget(self) -> None:
        now = time.monotonic()
        while self._request_times and now - self._request_times[0] > 3600:
            self._request_times.popleft()

        last_minute = [t for t in self._request_times if now - t <= 60]
        if len(last_minute) >= settings.boursorama_max_requests_per_minute:
            raise BoursoramaRateLimitError(
                f"Per-minute cap reached ({settings.boursorama_max_requests_per_minute} req/min)"
            )
        if len(self._request_times) >= settings.boursorama_max_requests_per_hour:
            raise BoursoramaRateLimitError(
                f"Per-hour cap reached ({settings.boursorama_max_requests_per_hour} req/hour)"
            )

    async def _throttled_request(
        self,
        url: str,
        *,
        referer: str | None = None,
        follow_redirects: bool = True,
    ) -> httpx.Response:
        self._validate_url(url)
        async with self._semaphore:
            self._check_budget()
            delay = random.uniform(
                settings.boursorama_min_delay_seconds,
                settings.boursorama_max_delay_seconds,
            )
            await asyncio.sleep(delay)

            headers: dict[str, str] = {}
            if referer or settings.boursorama_send_referer:
                headers["Referer"] = referer or "https://www.boursorama.com/"

            response = await self._client.get(
                url,
                headers=headers or None,
                follow_redirects=follow_redirects,
            )
            self._request_times.append(time.monotonic())

            if follow_redirects:
                final_host = urlparse(str(response.url)).netloc.lower()
                if final_host not in ALLOWED_HOSTS:
                    raise BoursoramaUrlError(f"Redirect landed on disallowed host: {final_host}")

            response.raise_for_status()
            return response

    async def get(self, url: str, *, referer: str | None = None) -> str:
        response = await self._throttled_request(url, referer=referer)
        return response.text

    async def get_redirect_location(self, url: str) -> str | None:
        response = await self._throttled_request(url, follow_redirects=False)
        if response.status_code in {301, 302, 303, 307, 308}:
            return response.headers.get("location")
        return None

    async def aclose(self) -> None:
        await self._client.aclose()
