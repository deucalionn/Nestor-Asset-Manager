from uuid import UUID

from langchain_core.tools import BaseTool, tool
from nam_db.enums import AgentRole, AnalysisTrigger, SubAgentRole
from nam_db.models.analysis import Analysis
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from nam_agentic.tools.base import BaseNamTool
from nam_agentic.tools.schemas.memory import CreateAnalysisInput, CreateAnalysisOutput
from nam_agentic.tools.services.embedding import EmbeddingService, canonical_embed_text


class CreateAnalysisTool(BaseNamTool):
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        user_id: UUID,
        embedding_service: EmbeddingService,
    ) -> None:
        self._session_factory = session_factory
        self._user_id = user_id
        self._embedding_service = embedding_service

    def as_tool(self) -> BaseTool:
        session_factory = self._session_factory
        user_id = self._user_id
        embedding_service = self._embedding_service

        @tool(args_schema=CreateAnalysisInput)
        async def create_analysis(
            agent: SubAgentRole,
            title: str,
            content: str,
            trigger: AnalysisTrigger,
            index_id: UUID | None = None,
        ) -> CreateAnalysisOutput:
            """Persist a sub-agent analysis with semantic embedding."""
            embed_text = canonical_embed_text(title, content)
            vector = await embedding_service.embed(embed_text)
            agent_role = AgentRole(agent.value)

            async with session_factory() as session:
                analysis = Analysis(
                    user_id=user_id,
                    agent=agent_role,
                    index_id=index_id,
                    title=title,
                    content=content,
                    content_embedding=vector,
                    trigger=trigger,
                )
                session.add(analysis)
                await session.commit()
                await session.refresh(analysis)

            return CreateAnalysisOutput(
                analysis_id=analysis.id,
                agent=analysis.agent,
                embedding_dimensions=len(vector),
                created_at=analysis.created_at,
            )

        return create_analysis
