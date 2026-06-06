from datetime import UTC, datetime
from uuid import UUID

from nam_db.enums import RecommendationStatus
from nam_db.models.recommendation import Recommendation
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from nam_api.exceptions import ConflictError, NotFoundError, UnprocessableError
from nam_api.schemas.analysis import AnalysisListItem
from nam_api.schemas.recommendation import RecommendationRead, RecommendationUpdate


class RecommendationService:
    async def list_for_user(
        self,
        session: AsyncSession,
        user_id: UUID,
        *,
        status: RecommendationStatus | None = None,
    ) -> list[RecommendationRead]:
        stmt = (
            select(Recommendation)
            .where(Recommendation.user_id == user_id)
            .options(selectinload(Recommendation.analyses))
            .order_by(Recommendation.created_at.desc())
        )
        if status is not None:
            stmt = stmt.where(Recommendation.status == status)
        result = await session.execute(stmt)
        return [self._to_read(row) for row in result.scalars().all()]

    async def get(
        self, session: AsyncSession, user_id: UUID, recommendation_id: UUID
    ) -> RecommendationRead:
        stmt = (
            select(Recommendation)
            .where(
                Recommendation.id == recommendation_id,
                Recommendation.user_id == user_id,
            )
            .options(selectinload(Recommendation.analyses))
        )
        recommendation = await session.scalar(stmt)
        if recommendation is None:
            raise NotFoundError("Recommendation not found")
        return self._to_read(recommendation)

    async def update_status(
        self,
        session: AsyncSession,
        user_id: UUID,
        recommendation_id: UUID,
        data: RecommendationUpdate,
    ) -> RecommendationRead:
        stmt = (
            select(Recommendation)
            .where(
                Recommendation.id == recommendation_id,
                Recommendation.user_id == user_id,
            )
            .options(selectinload(Recommendation.analyses))
        )
        recommendation = await session.scalar(stmt)
        if recommendation is None:
            raise NotFoundError("Recommendation not found")

        if recommendation.status != RecommendationStatus.PENDING:
            raise ConflictError("Recommendation has already been resolved")

        if data.status not in (
            RecommendationStatus.APPLIED,
            RecommendationStatus.REJECTED,
        ):
            raise UnprocessableError("Status must be APPLIED or REJECTED")

        recommendation.status = data.status
        recommendation.user_comment = data.user_comment
        recommendation.resolved_at = datetime.now(UTC)
        await session.flush()
        return await self.get(session, user_id, recommendation_id)

    @staticmethod
    def _to_read(recommendation: Recommendation) -> RecommendationRead:
        return RecommendationRead(
            id=recommendation.id,
            user_id=recommendation.user_id,
            agent=recommendation.agent,
            content=recommendation.content,
            type=recommendation.type,
            status=recommendation.status,
            user_comment=recommendation.user_comment,
            created_at=recommendation.created_at,
            resolved_at=recommendation.resolved_at,
            analyses=[AnalysisListItem.model_validate(a) for a in recommendation.analyses],
        )
