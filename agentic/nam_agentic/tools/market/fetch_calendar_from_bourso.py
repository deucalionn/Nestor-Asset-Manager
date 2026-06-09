from langchain_core.tools import BaseTool, tool

from nam_agentic.tools.base import BaseNamTool
from nam_agentic.tools.schemas.market import (
    FetchCalendarFromBoursoInput,
    FetchCalendarFromBoursoOutput,
)
from nam_agentic.tools.services.boursorama.calendar_fetch import CalendarFetchService


class FetchCalendarFromBoursoTool(BaseNamTool):
    def __init__(self, service: CalendarFetchService | None = None) -> None:
        self._service = service or CalendarFetchService()

    def as_tool(self) -> BaseTool:
        service = self._service

        @tool(args_schema=FetchCalendarFromBoursoInput)
        async def fetch_calendar_from_bourso(
            include_categories=None,
        ) -> FetchCalendarFromBoursoOutput:
            """Fetch Boursorama calendar tables and return combined markdown.

            Use when: refreshing /shared/calendar/today.md for the current session.
            Do not use when: reading an already-fresh shared calendar file — use read_file.
            Returns: markdown string plus structured sections — persist via write_file yourself.
            """
            return await service.fetch(include_categories=include_categories)

        return fetch_calendar_from_bourso
