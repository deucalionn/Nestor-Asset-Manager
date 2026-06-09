from __future__ import annotations

from pathlib import Path

import trafilatura
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_ollama import ChatOllama

from nam_agentic.settings import settings
from nam_agentic.tools.services.boursorama.errors import BoursoramaParseError

_PROMPT_PATH = Path(__file__).resolve().parents[3] / "prompts" / "PAGE_FORMATTER.md"


class PageContentFormatter:
    def __init__(self) -> None:
        self._system_prompt = _PROMPT_PATH.read_text(encoding="utf-8")

    async def format(
        self,
        *,
        url: str,
        html: str,
        page_hint: str = "generic",
    ) -> tuple[str, str]:
        extracted = trafilatura.extract(
            html,
            url=url,
            include_comments=False,
            include_tables=True,
            favor_precision=True,
        )
        if not extracted or not extracted.strip():
            raise BoursoramaParseError(f"Trafilatura returned empty content for {url}")

        text = extracted[: settings.news_format_max_chars]
        if not settings.news_format_llm_enabled:
            return _title_from_text(text), text

        model = settings.llm_model.removeprefix("ollama:")
        llm = ChatOllama(model=model, base_url=settings.llm_base_url)
        response = await llm.ainvoke(
            [
                SystemMessage(content=self._system_prompt),
                HumanMessage(
                    content=(
                        f"URL: {url}\n"
                        f"Page hint: {page_hint}\n\n"
                        f"Extracted text:\n{text}"
                    )
                ),
            ]
        )
        markdown = str(response.content).strip()
        if not markdown:
            raise BoursoramaParseError(f"LLM returned empty markdown for {url}")
        return _title_from_text(markdown), markdown


def _title_from_text(text: str) -> str:
    for line in text.splitlines():
        cleaned = line.strip().lstrip("#").strip()
        if cleaned:
            return cleaned[:255]
    return "Boursorama page"
