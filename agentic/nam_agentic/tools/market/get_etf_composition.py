from datetime import UTC, datetime
from uuid import UUID

from langchain_core.tools import BaseTool, tool
from nam_db.enums import IndexType
from nam_db.models.index import Index
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from nam_agentic.tools.base import BaseNamTool
from nam_agentic.tools.errors import ToolError
from nam_agentic.tools.schemas.market import (
    EtfHoldingItem,
    GetEtfCompositionInput,
    GetEtfCompositionOutput,
)
from nam_agentic.tools.services.boursorama.client import BoursoramaHttpClient
from nam_agentic.tools.services.boursorama.etf_composition_parser import parse_etf_composition_html
from nam_agentic.tools.services.boursorama.urls import absolute_boursorama_url


class GetEtfCompositionTool(BaseNamTool):
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        client: BoursoramaHttpClient | None = None,
    ) -> None:
        self._session_factory = session_factory
        self._client = client or BoursoramaHttpClient()

    def as_tool(self) -> BaseTool:
        session_factory = self._session_factory
        client = self._client

        @tool(args_schema=GetEtfCompositionInput)
        async def get_etf_composition(
            index_id: UUID | None = None,
            boursorama_ticker: str | None = None,
        ) -> GetEtfCompositionOutput:
            """Fetch ETF tracker composition (holdings and weights) from Boursorama.

            Use when: index_type is ETF and you need underlying exposure before company news.
            Do not use when: index_type is COMPANY — use search_boursorama and company news URLs.
            Returns: holdings list with name, weight_pct, and optional ticker per line.
            """
            resolved_index_id = index_id
            ticker = boursorama_ticker
            if index_id is not None:
                async with session_factory() as session:
                    index = await session.get(Index, index_id)
                    if index is None:
                        raise ToolError("Index not found")
                    if index.index_type != IndexType.ETF:
                        raise ToolError("get_etf_composition requires index_type=ETF")
                    ticker = index.boursorama_ticker or ticker
                    if not ticker:
                        raise ToolError(
                            "Index has no boursorama_ticker — run search_boursorama first"
                        )

            if not ticker:
                raise ToolError("boursorama_ticker is required")

            composition_url = absolute_boursorama_url(
                f"/bourse/trackers/cours/composition/{ticker}/"
            )
            html = await client.get(composition_url)
            rows = parse_etf_composition_html(html, page_url=composition_url)
            return GetEtfCompositionOutput(
                index_id=resolved_index_id,
                boursorama_ticker=ticker,
                composition_url=composition_url,
                holdings=[
                    EtfHoldingItem(
                        name=row.name,
                        weight_pct=row.weight_pct,
                        isin=row.isin,
                        boursorama_ticker=row.boursorama_ticker,
                    )
                    for row in rows
                ],
                fetched_at=datetime.now(UTC),
            )

        return get_etf_composition
