from uuid import UUID

from nam_db.models.analysis import Analysis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from nam_api.exceptions import NotFoundError
from nam_api.schemas.analysis import AnalysisListItem, AnalysisRead


class AnalysisService:
    async def list_for_user(
        self,
        session: AsyncSession,
        user_id: UUID,
        *,
        index_id: UUID | None = None,
    ) -> list[AnalysisListItem]:
        stmt = select(Analysis).where(Analysis.user_id == user_id)
        if index_id is not None:
            stmt = stmt.where(Analysis.index_id == index_id)
        stmt = stmt.order_by(Analysis.created_at.desc())
        result = await session.execute(stmt)
        return [AnalysisListItem.model_validate(row) for row in result.scalars().all()]

    async def get(
        self, session: AsyncSession, user_id: UUID, analysis_id: UUID
    ) -> AnalysisRead:
        analysis = await session.get(Analysis, analysis_id)
        if analysis is None or analysis.user_id != user_id:
            raise NotFoundError("Analysis not found")
        return AnalysisRead.model_validate(analysis)
