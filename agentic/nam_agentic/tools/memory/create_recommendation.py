from uuid import UUID

from langchain_core.tools import BaseTool, tool
from nam_db.enums import AgentRole, RecommendationStatus, RecommendationType
from nam_db.models.analysis import Analysis
from nam_db.models.recommendation import Recommendation
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from nam_agentic.tools.base import BaseNamTool
from nam_agentic.tools.errors import ToolError
from nam_agentic.tools.schemas.memory import CreateRecommendationInput, CreateRecommendationOutput


class CreateRecommendationTool(BaseNamTool):
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        user_id: UUID,
    ) -> None:
        self._session_factory = session_factory
        self._user_id = user_id

    def as_tool(self) -> BaseTool:
        session_factory = self._session_factory
        user_id = self._user_id

        @tool(args_schema=CreateRecommendationInput)
        async def create_recommendation(
            analysis_ids: list[UUID],
            content: str,
            type: RecommendationType,
        ) -> CreateRecommendationOutput:
            """Create a pending portfolio recommendation linked to analyses."""
            async with session_factory() as session:
                stmt = select(Analysis).where(
                    Analysis.id.in_(analysis_ids),
                    Analysis.user_id == user_id,
                )
                analyses = list((await session.scalars(stmt)).all())
                if len(analyses) != len(set(analysis_ids)):
                    raise ToolError("One or more analysis_ids are invalid for this user")

                recommendation = Recommendation(
                    user_id=user_id,
                    agent=AgentRole.PORTFOLIO_MANAGER,
                    content=content,
                    type=type,
                    status=RecommendationStatus.PENDING,
                )
                recommendation.analyses = analyses
                session.add(recommendation)
                await session.commit()
                await session.refresh(recommendation)

            return CreateRecommendationOutput(
                recommendation_id=recommendation.id,
                status=recommendation.status,
                created_at=recommendation.created_at,
            )

        return create_recommendation
