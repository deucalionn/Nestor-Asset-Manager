from uuid import UUID

from langchain_core.tools import BaseTool, tool
from nam_db.models.index import Index
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from nam_agentic.tools.base import BaseNamTool
from nam_agentic.tools.errors import ToolError
from nam_agentic.tools.schemas.market import (
    UpdateIndexYahooSymbolInput,
    UpdateIndexYahooSymbolOutput,
)


class UpdateIndexYahooSymbolTool(BaseNamTool):
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    def as_tool(self) -> BaseTool:
        session_factory = self._session_factory

        @tool(args_schema=UpdateIndexYahooSymbolInput)
        async def update_index_yahoo_symbol(
            index_id: UUID,
            yahoo_symbol: str,
        ) -> UpdateIndexYahooSymbolOutput:
            """Manually override indices.yahoo_symbol after a bad auto-resolve.

            Use when: search_yahoo_symbol returned the wrong ticker and you need a correction.
            Do not use when: symbol is missing — search_yahoo_symbol auto-persists on first resolve.
            Returns: updated index identifiers including the new yahoo_symbol.
            """
            async with session_factory() as session:
                index = await session.get(Index, index_id)
                if index is None:
                    raise ToolError("Index not found")
                index.yahoo_symbol = yahoo_symbol
                await session.commit()
                await session.refresh(index)
                return UpdateIndexYahooSymbolOutput(
                    index_id=index.id,
                    name=index.name,
                    isin=index.isin,
                    index_type=index.index_type,
                    yahoo_symbol=index.yahoo_symbol,
                )

        return update_index_yahoo_symbol
