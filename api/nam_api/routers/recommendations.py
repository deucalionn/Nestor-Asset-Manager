from uuid import UUID

from fastapi import APIRouter, Depends, Query
from nam_db.enums import RecommendationStatus
from sqlalchemy.ext.asyncio import AsyncSession

from nam_api.dependencies import get_db_session, get_singleton_user_id
from nam_api.schemas.recommendation import RecommendationRead, RecommendationUpdate
from nam_api.services.recommendation_service import RecommendationService

router = APIRouter(prefix="/recommendations", tags=["recommendations"])


def get_recommendation_service() -> RecommendationService:
    return RecommendationService()


@router.get("", response_model=list[RecommendationRead])
async def list_recommendations(
    status: RecommendationStatus | None = Query(default=None),
    user_id: UUID = Depends(get_singleton_user_id),
    session: AsyncSession = Depends(get_db_session),
    service: RecommendationService = Depends(get_recommendation_service),
) -> list[RecommendationRead]:
    return await service.list_for_user(session, user_id, status=status)


@router.get("/{recommendation_id}", response_model=RecommendationRead)
async def get_recommendation(
    recommendation_id: UUID,
    user_id: UUID = Depends(get_singleton_user_id),
    session: AsyncSession = Depends(get_db_session),
    service: RecommendationService = Depends(get_recommendation_service),
) -> RecommendationRead:
    return await service.get(session, user_id, recommendation_id)


@router.patch("/{recommendation_id}", response_model=RecommendationRead)
async def update_recommendation(
    recommendation_id: UUID,
    body: RecommendationUpdate,
    user_id: UUID = Depends(get_singleton_user_id),
    session: AsyncSession = Depends(get_db_session),
    service: RecommendationService = Depends(get_recommendation_service),
) -> RecommendationRead:
    recommendation = await service.update_status(session, user_id, recommendation_id, body)
    await session.commit()
    return recommendation
