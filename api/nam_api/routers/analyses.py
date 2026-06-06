from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from nam_api.dependencies import get_db_session, get_singleton_user_id
from nam_api.schemas.analysis import AnalysisListItem, AnalysisRead
from nam_api.services.analysis_service import AnalysisService

router = APIRouter(prefix="/analyses", tags=["analyses"])


def get_analysis_service() -> AnalysisService:
    return AnalysisService()


@router.get("", response_model=list[AnalysisListItem])
async def list_analyses(
    index_id: UUID | None = Query(default=None),
    user_id: UUID = Depends(get_singleton_user_id),
    session: AsyncSession = Depends(get_db_session),
    service: AnalysisService = Depends(get_analysis_service),
) -> list[AnalysisListItem]:
    return await service.list_for_user(session, user_id, index_id=index_id)


@router.get("/{analysis_id}", response_model=AnalysisRead)
async def get_analysis(
    analysis_id: UUID,
    user_id: UUID = Depends(get_singleton_user_id),
    session: AsyncSession = Depends(get_db_session),
    service: AnalysisService = Depends(get_analysis_service),
) -> AnalysisRead:
    return await service.get(session, user_id, analysis_id)
