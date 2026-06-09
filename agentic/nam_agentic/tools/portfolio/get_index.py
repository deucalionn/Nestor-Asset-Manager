from uuid import UUID

from langchain_core.tools import BaseTool, tool
from nam_db.models.index import Index
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from nam_agentic.tools.base import BaseNamTool
from nam_agentic.tools.errors import ToolError
from nam_agentic.tools.schemas.portfolio import GetIndexInput, IndexDetailOutput


class GetIndexTool(BaseNamTool):
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    def as_tool(self) -> BaseTool:
        session_factory = self._session_factory

        @tool(args_schema=GetIndexInput)
        async def get_index(
            index_id: UUID | None = None,
            isin: str | None = None,
        ) -> IndexDetailOutput:
            """Fetch a single index by id or ISIN.

            Use when: you need index_type and boursorama_ticker before search or news tools.
            Do not use when: you only need a lightweight name list — use list_indices instead.
            Returns: index metadata including index_type and optional boursorama_ticker.
            """
            async with session_factory() as session:
                if index_id is not None:
                    index = await session.get(Index, index_id)
                else:
                    index = await session.scalar(select(Index).where(Index.isin == isin))

                if index is None:
                    raise ToolError("Index not found")

            return IndexDetailOutput.model_validate(index)

        return get_index
