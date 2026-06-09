from uuid import UUID

from langchain_core.tools import BaseTool, tool
from nam_db.models.index import Index
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from nam_agentic.tools.base import BaseNamTool
from nam_agentic.tools.errors import ToolError
from nam_agentic.tools.schemas.market import (
    UpdateIndexBoursoramaInput,
    UpdateIndexBoursoramaOutput,
)


class UpdateIndexBoursoramaTool(BaseNamTool):
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    def as_tool(self) -> BaseTool:
        session_factory = self._session_factory

        @tool(args_schema=UpdateIndexBoursoramaInput)
        async def update_index_boursorama(
            index_id: UUID,
            boursorama_ticker: str,
        ) -> UpdateIndexBoursoramaOutput:
            """Manually override indices.boursorama_ticker after a bad auto-resolve.

            Use when: search_boursorama returned the wrong ticker and you need a correction.
            Do not use when: ticker is missing — search_boursorama auto-persists on first resolve.
            Returns: updated index identifiers including the new ticker.
            """
            async with session_factory() as session:
                index = await session.get(Index, index_id)
                if index is None:
                    raise ToolError("Index not found")
                index.boursorama_ticker = boursorama_ticker
                await session.commit()
                await session.refresh(index)
                return UpdateIndexBoursoramaOutput(
                    index_id=index.id,
                    name=index.name,
                    isin=index.isin,
                    index_type=index.index_type,
                    boursorama_ticker=index.boursorama_ticker,
                )

        return update_index_boursorama
