from langchain_core.tools import BaseTool, tool
from nam_db.models.index import Index
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from nam_agentic.tools.base import BaseNamTool
from nam_agentic.tools.schemas.portfolio import IndexListItem, ListIndicesInput, ListIndicesOutput


class ListIndicesTool(BaseNamTool):
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    def as_tool(self) -> BaseTool:
        session_factory = self._session_factory

        @tool(args_schema=ListIndicesInput)
        async def list_indices(name_query: str | None = None) -> ListIndicesOutput:
            """List indices, optionally filtered by name substring.

            Use when: browsing available instruments or matching a name before get_index.
            Do not use when: you already have index_id or isin — use get_index directly.
            Returns: indices with index_type and optional boursorama_ticker per row.
            """
            async with session_factory() as session:
                stmt = select(Index).order_by(Index.name)
                if name_query:
                    stmt = stmt.where(Index.name.ilike(f"%{name_query}%"))
                indices = list((await session.scalars(stmt)).all())

            return ListIndicesOutput(
                indices=[IndexListItem.model_validate(row) for row in indices]
            )

        return list_indices
