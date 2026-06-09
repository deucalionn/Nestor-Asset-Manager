from pathlib import Path
from unittest.mock import AsyncMock

import pytest
from nam_agentic.tools.market.fetch_calendar_from_bourso import FetchCalendarFromBoursoTool
from nam_agentic.tools.services.boursorama.calendar_fetch import CalendarFetchService
from nam_agentic.tools.services.boursorama.calendar_parser import parse_calendar_page
from nam_db.enums import NewsCategory

pytestmark = pytest.mark.asyncio
FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "boursorama"


def _read(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


async def test_calendar_parser_macro_fixture() -> None:
    rows = parse_calendar_page(
        _read("calendar_macro.html"),
        page_url="https://www.boursorama.com/bourse/actualites/calendriers/macroeconomique",
    )
    assert rows
    assert any("Commandes" in row.event for row in rows)
    assert rows[0].time == "08:00"
    assert rows[0].importance == 2


async def test_calendar_parser_listed_companies_fixture() -> None:
    rows = parse_calendar_page(
        _read("calendar_listed_companies.html"),
        page_url="https://www.boursorama.com/bourse/actualites/calendriers/societes-cotees",
    )
    assert rows
    assert all(row.event for row in rows)


async def test_calendar_parser_empty_html() -> None:
    rows = parse_calendar_page("<html><body></body></html>", page_url="https://example/")
    assert rows == []


async def test_fetch_calendar_from_bourso_tool() -> None:
    mock_client = AsyncMock()
    mock_client.get.side_effect = [
        _read("calendar_macro.html"),
        _read("calendar_listed_companies.html"),
        _read("calendar_macro.html"),
        _read("calendar_listed_companies.html"),
    ]

    service = CalendarFetchService(client=mock_client)
    tool = FetchCalendarFromBoursoTool(service=service).as_tool()
    result = await tool.ainvoke({})

    assert result.markdown
    assert "_fetched_at:" in result.markdown
    assert "## CALENDAR_MACRO" in result.markdown
    assert len(result.sections) == 4
    assert mock_client.get.await_count == 4


async def test_fetch_calendar_subset_categories() -> None:
    mock_client = AsyncMock()
    mock_client.get.return_value = _read("calendar_macro.html")

    service = CalendarFetchService(client=mock_client)
    tool = FetchCalendarFromBoursoTool(service=service).as_tool()
    result = await tool.ainvoke({"include_categories": [NewsCategory.CALENDAR_MACRO]})

    assert mock_client.get.await_count == 1
    assert len(result.sections) == 1
    assert result.sections[0].category == NewsCategory.CALENDAR_MACRO
