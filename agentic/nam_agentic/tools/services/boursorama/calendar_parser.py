from __future__ import annotations

from dataclasses import dataclass
from html import unescape

from selectolax.parser import HTMLParser

_IMPORTANCE_CLASS_SCORES: tuple[tuple[str, int], ...] = (
    ("weight--higher", 4),
    ("weight--high", 3),
    ("weight--medium", 2),
    ("weight--low", 1),
)

_IMPORTANCE_TEXT_SCORES: dict[str, int] = {
    "faible": 1,
    "moyenne": 2,
    "haute": 3,
    "très haute": 4,
}


@dataclass(frozen=True)
class ParsedCalendarRow:
    time: str | None
    event: str
    previous: str | None
    last: str | None
    importance: int | None


def _importance_from_cell(cell) -> int | None:
    classes = cell.attributes.get("class", "")
    for token, score in _IMPORTANCE_CLASS_SCORES:
        if token in classes:
            return score
    text = cell.text(strip=True).lower()
    return _IMPORTANCE_TEXT_SCORES.get(text)


def _is_header_row(cells: list) -> bool:
    if not cells:
        return True
    first = cells[0].text(strip=True).lower()
    return first in {"heure", "hour", "time"}


def _parse_data_row(cells: list) -> ParsedCalendarRow | None:
    values = [unescape(cell.text(strip=True)) for cell in cells]
    if len(values) < 2:
        return None
    event = values[1]
    if not event:
        return None

    previous = values[3] if len(values) > 3 else None
    last = values[4] if len(values) > 4 else None
    importance = _importance_from_cell(cells[-1]) if cells else None

    period = values[2] if len(values) > 2 else None
    if period and period not in {"-", "—"}:
        event = f"{event} ({period})"

    return ParsedCalendarRow(
        time=values[0] or None,
        event=event,
        previous=previous if previous not in {"", "-", "—"} else None,
        last=last if last not in {"", "-", "—"} else None,
        importance=importance,
    )


def parse_calendar_page(html: str, *, page_url: str) -> list[ParsedCalendarRow]:
    """Parse Boursorama calendar table HTML into structured rows."""
    _ = page_url
    tree = HTMLParser(html)
    calendar_root = tree.css_first(".c-trading-calendar") or tree.body
    if calendar_root is None:
        return []

    rows: list[ParsedCalendarRow] = []
    seen: set[tuple[str | None, str]] = set()

    for table in calendar_root.css("table.c-table"):
        for row in table.css("tr.c-table__row"):
            cells = row.css("td.c-table__cell, th.c-table__cell")
            if _is_header_row(cells):
                continue
            parsed = _parse_data_row(cells)
            if parsed is None:
                continue
            key = (parsed.time, parsed.event)
            if key in seen:
                continue
            seen.add(key)
            rows.append(parsed)

    if not rows:
        for table in tree.css("table.c-table"):
            for row in table.css("tr.c-table__row"):
                cells = row.css("td.c-table__cell, th.c-table__cell")
                if _is_header_row(cells):
                    continue
                parsed = _parse_data_row(cells)
                if parsed is None:
                    continue
                key = (parsed.time, parsed.event)
                if key in seen:
                    continue
                seen.add(key)
                rows.append(parsed)

    return rows


def importance_stars(level: int | None) -> str:
    if level is None:
        return "—"
    return "★" * max(1, min(level, 4))
