from datetime import UTC, datetime
from uuid import UUID

from langchain_core.tools import BaseTool, tool
from nam_db.enums import IndexType
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from nam_agentic.tools.base import BaseNamTool
from nam_agentic.tools.errors import ToolError
from nam_agentic.tools.market.yahoo_helpers import extract_info_subset, financials_frame_to_records
from nam_agentic.tools.schemas.market import (
    GetCompanyFinancialsFromYfInput,
    GetCompanyFinancialsFromYfOutput,
)
from nam_agentic.tools.services.yahoo.client import YfinanceClient
from nam_agentic.tools.services.yahoo.errors import YahooDataUnavailableError
from nam_agentic.tools.services.yahoo.resolver import YahooIndexResolver


class GetCompanyFinancialsFromYfTool(BaseNamTool):
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        client: YfinanceClient | None = None,
    ) -> None:
        self._session_factory = session_factory
        self._client = client or YfinanceClient()

    def as_tool(self) -> BaseTool:
        session_factory = self._session_factory
        client = self._client
        resolver = YahooIndexResolver(session_factory, client=client)

        @tool(args_schema=GetCompanyFinancialsFromYfInput)
        async def get_company_financials_from_yf(
            index_id: UUID | None = None,
            isin: str | None = None,
            yahoo_symbol: str | None = None,
            include_statements: bool = True,
        ) -> GetCompanyFinancialsFromYfOutput:
            """Fetch structured company financials from Yahoo Finance on demand.

            Use when: sector analysis needs statements, ratios, or market cap from Yahoo.
            Do not use when: index_type is ETF — use get_etf_composition and price tools instead.
            Do not use when: Bourso key figures suffice — get_data_from_url on key_figures_url.
            Returns: info subset plus optional income, balance, and cash-flow statement tables.
            """
            resolved = await resolver.resolve(
                index_id=index_id,
                isin=isin,
                yahoo_symbol=yahoo_symbol,
            )
            if resolved.index_type == IndexType.ETF:
                raise ToolError(
                    "get_company_financials_from_yf supports COMPANY indices only; "
                    "use get_etf_composition for ETF holdings"
                )

            info = await client.get_info(resolved.yahoo_symbol)
            income_statement = None
            balance_sheet = None
            cash_flow = None
            if include_statements:
                income_statement = await _try_statement(client, resolved.yahoo_symbol, "income")
                balance_sheet = await _try_statement(client, resolved.yahoo_symbol, "balance")
                cash_flow = await _try_statement(client, resolved.yahoo_symbol, "cashflow")

            return GetCompanyFinancialsFromYfOutput(
                yahoo_symbol=resolved.yahoo_symbol,
                index_type=resolved.index_type,
                info=extract_info_subset(info),
                income_statement=income_statement,
                balance_sheet=balance_sheet,
                cash_flow=cash_flow,
                fetched_at=datetime.now(UTC),
                resolved_from_db=resolved.resolved_from_db,
            )

        return get_company_financials_from_yf


async def _try_statement(
    client: YfinanceClient,
    symbol: str,
    statement: str,
) -> list[dict[str, object]] | None:
    try:
        frame = await client.get_financials(symbol, statement=statement, freq="annual")
    except YahooDataUnavailableError:
        return None
    return financials_frame_to_records(frame)
