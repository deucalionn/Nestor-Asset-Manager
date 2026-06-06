from langchain_core.tools import BaseTool, tool
from nam_db.models.index import Index
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from nam_agentic.tools.base import BaseNamTool
from nam_agentic.tools.schemas.portfolio import CreateIndexInput, CreateIndexOutput


class CreateIndexTool(BaseNamTool):
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    def as_tool(self) -> BaseTool:
        session_factory = self._session_factory

        @tool(args_schema=CreateIndexInput)
        async def create_index(name: str, isin: str) -> CreateIndexOutput:
            """Create or return an existing index by ISIN."""
            async with session_factory() as session:
                existing = await session.scalar(
                    select(Index).where(Index.isin == isin)
                )
                if existing is not None:
                    return CreateIndexOutput(
                        index_id=existing.id,
                        name=existing.name,
                        isin=existing.isin,
                        created=False,
                    )

                index = Index(name=name, isin=isin)
                session.add(index)
                await session.commit()
                await session.refresh(index)

            return CreateIndexOutput(
                index_id=index.id,
                name=index.name,
                isin=index.isin,
                created=True,
            )

        return create_index
