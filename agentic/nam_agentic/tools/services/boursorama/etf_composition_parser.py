from __future__ import annotations

import re
from dataclasses import dataclass
from html import unescape

from selectolax.parser import HTMLParser

from nam_agentic.tools.services.boursorama.errors import BoursoramaParseError


@dataclass(frozen=True)
class EtfHoldingRow:
    name: str
    weight_pct: float | None
    isin: str | None
    boursorama_ticker: str | None


def _parse_weight_pct(row) -> float | None:
    for cell in row.css("td"):
        step = cell.attributes.get("data-gauge-current-step")
        if step and step.isdigit():
            return float(step)
    gauge = row.css_first("[data-gauge-current-step]")
    step = gauge.attributes.get("data-gauge-current-step") if gauge else None
    if step and step.isdigit():
        return float(step)
    increment = row.css_first("[data-gauge-increment]")
    if increment is not None:
        text = increment.text(strip=True).replace(",", ".")
        match = re.search(r"(\d+(?:\.\d+)?)", text)
        if match:
            return float(match.group(1))
    return None


def parse_etf_composition_html(html: str, *, page_url: str) -> list[EtfHoldingRow]:
    """Parse ETF composition page gauge table rows."""
    tree = HTMLParser(html)
    holdings: list[EtfHoldingRow] = []

    for row in tree.css("table.c-table tbody tr"):
        header = row.css_first("td.c-table-gauge__cell--header")
        if header is None:
            link = row.css_first("a[href*='/cours/']")
            name = unescape(link.text(strip=True)) if link else None
            href = link.attributes.get("href", "") if link else ""
            ticker_match = re.search(r"/cours/([^/]+)/", href) if link else None
            if name:
                holdings.append(
                    EtfHoldingRow(
                        name=name,
                        weight_pct=_parse_weight_pct(row),
                        isin=None,
                        boursorama_ticker=ticker_match.group(1) if ticker_match else None,
                    )
                )
            continue

        name = unescape(header.text(strip=True))
        if not name:
            continue
        holdings.append(
            EtfHoldingRow(
                name=name,
                weight_pct=_parse_weight_pct(row),
                isin=None,
                boursorama_ticker=None,
            )
        )

    if not holdings:
        raise BoursoramaParseError(f"No ETF holdings parsed from {page_url}")
    return holdings
